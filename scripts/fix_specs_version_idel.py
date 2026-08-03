#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Alinea los specs de dashboard con los valores reales de la dimensión
`Versión`: reemplaza los literales `v1`/`v2`/`v3` por `1`/`2`/`3`.

PROBLEMA
--------
La dimensión `Versión` (IDEL) almacena en `metric_data` los valores `"1"`,
`"2"` y `"3"`. Varios specs del dashboard y los `derived_columns` del
indicador declaran en cambio `"v1"`, `"v2"`, `"v3"`. El desajuste no
produce ningún error: `backend/routers/charts.py:_build_dataset` filtra el
`x_order` contra las x existentes (`[x for x in x_order if x in existing]`)
y luego rellena las celdas faltantes con `.get(x, 0)`. Resultado: HTTP 200,
ejes con las 3 versiones dibujadas y **todas las barras en 0**.

Daño verificado en el QA 2026-08-03 (`docs/reportes/qa_dashboards_2026-08-03.md`),
indicador 3 (IDEL, org 1), 25/100:

  - spec 141 "Niveles de Riesgo por Versión"  → 12 barras en 0
  - spec 142 "Niveles por Curso y Versión"    → 72 barras en 0
  - spec 144 "Roster"                          → 6.120 celdas "N/A"
  - spec 147 "Matriz de Transición"            → dataset {"x":[],"y":[],"z":[]}
    (los derivados `nivel_inicial`/`nivel_final` usan
     `time_ordinal_levels: ["v1","v2","v3"]` contra valores `1/2/3`, así que
     `_as_numeric` devuelve NaN y `min_points: 2` descarta todas las filas)

DECISIÓN DE PRODUCTO
--------------------
Se cambian los **specs**, no los datos: la dimensión sigue guardando
`1/2/3`. Este script implementa esa decisión.

RUNBOOK
-------
  1) Dry-run (no escribe nada):
       python scripts/fix_specs_version_idel.py --org 1

  2) Aplicar:
       python scripts/fix_specs_version_idel.py --org 1 --apply

  3) Idempotencia: re-correr el paso 1 debe reportar
     "0 reemplazos pendientes".

  4) Verificar en el dashboard (indicador 3):
       GET /api/charts/141/data → las 12 barras con valores reales
                                  (v1=1.620, v2=1.487, v3=783 evaluaciones)
       GET /api/charts/144/data → celdas del Roster dejan de ser todas None
       GET /api/charts/147/data → `z` no vacío (matriz de transición)

  En dev el backend corre en Docker, así que hay que ejecutarlo adentro:
       docker compose -f docker-compose.dev.yml exec -T \
           -e PYTHONPATH=/app backend \
           python scripts/fix_specs_version_idel.py --org 1 --apply

  Apuntando a otra DB sin tocar el .env del entorno:
       python scripts/fix_specs_version_idel.py --org 1 --apply \
           --database-url "postgresql://..."

ALCANCE / GARANTÍAS
-------------------
- **Org-scoped**: solo toca specs e indicadores de `--org`.
- **Dry-run por defecto**: sin `--apply` no hay commit.
- **Idempotente**: los valores destino (`1/2/3`) ya no matchean el patrón
  de origen, así que una segunda corrida no encuentra nada.
- **Sin falsos positivos**: NUNCA se reemplaza por búsqueda-y-reemplazo de
  texto. Un literal solo se toca si está en una **posición de valor** cuyo
  **campo gobernante** es la dimensión `Versión`. El campo gobernante se
  deriva de la semántica real del renderer:
      aesthetics.x_order          → mapping.x_field
      aesthetics.stack_order      → mapping.stack_field (o group_field)
      aesthetics.color_overrides  → mapping.stack_field / category_field
      data_source.filters[F]      → F
      columns[j].value_aliases    → columns[j].source_key | key
      pivot.order[F]              → F
      derived.time_ordinal_levels → derived.time_field
      derived.mapping (lookup)    → derived.value_field
      temporal_config.levels[k].order → levels[k].label
  El texto libre (`metadata.description`, `aesthetics.titulo`, notas del
  layout) **no se toca**: se reporta al final como "revisión manual".
- **Auditoría exhaustiva**: además del plan dirigido, el script recorre el
  JSON COMPLETO de cada spec / del indicador y lista toda ocurrencia de
  `v1`/`v2`/`v3` que el plan NO haya cubierto, para que nada quede oculto.
- **Verifica contra la DB**: antes de planificar comprueba que los valores
  destino (`1/2/3`) existan de verdad en `metric_data` para la dimensión
  `Versión`. Si no existen, aborta (usar `--force` para saltarlo).
- No toca `metric_data`, ni dimensiones, ni valores de dimensión.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field as dc_field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────
# Constantes de dominio
# ─────────────────────────────────────────────────────────────────────────

# Nombre normalizado (sin acentos, minúsculas) de la dimensión objetivo.
VERSION_DIM_HINT = "version"

# El reemplazo. Claves normalizadas: matchea "v1", "V1", " v1 ".
VALUE_MAP: Dict[str, str] = {"v1": "1", "v2": "2", "v3": "3"}


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _loads(raw: Optional[str], default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _norm(s: Any) -> str:
    """minúsculas + sin acentos + strip. Para comparar nombres de campo."""
    if s is None:
        return ""
    txt = unicodedata.normalize("NFKD", str(s))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt.strip().lower()


def _map_value(v: Any) -> Optional[str]:
    """`"v1"` → `"1"`. None si el valor no es un literal de versión completo.

    Deliberadamente exige match del string ENTERO (tras strip): un texto
    libre que *contenga* "v1" nunca entra por acá.
    """
    if not isinstance(v, str):
        return None
    return VALUE_MAP.get(_norm(v))


def _looks_like_version_literal(v: Any) -> bool:
    return isinstance(v, str) and _norm(v) in VALUE_MAP


# ─────────────────────────────────────────────────────────────────────────
# Plan de reemplazos
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class Repl:
    """Un reemplazo planificado, con su ruta JSON y cómo aplicarlo."""
    path: str            # ruta JSON legible, ej "charts_list[0].aesthetics.x_order[1]"
    before: Any
    after: Any
    why: str             # campo gobernante que justifica el reemplazo
    apply: Callable[[], None]


@dataclass
class ObjPlan:
    """Reemplazos planificados sobre un objeto de la DB (spec o indicador)."""
    kind: str                        # "spec" | "indicator"
    obj_id: int
    name: str
    extra: str = ""                  # tipo de spec / indicador asociado
    repls: List[Repl] = dc_field(default_factory=list)
    # Ocurrencias de vN encontradas en el JSON que el plan NO cubre.
    unhandled: List[Tuple[str, str]] = dc_field(default_factory=list)
    freetext: List[Tuple[str, str]] = dc_field(default_factory=list)


def _setter_list(lst: List[Any], idx: int, new: Any) -> Callable[[], None]:
    def _apply() -> None:
        lst[idx] = new
    return _apply


def _setter_dict_value(d: Dict[str, Any], key: str, new: Any) -> Callable[[], None]:
    def _apply() -> None:
        d[key] = new
    return _apply


def _setter_dict_key(d: Dict[str, Any], old: str, new: str) -> Callable[[], None]:
    """Renombra una clave preservando el orden de inserción del dict."""
    def _apply() -> None:
        items = [(new if k == old else k, v) for k, v in d.items()]
        d.clear()
        d.update(items)
    return _apply


def _plan_list(
    container: Any, key: str, base_path: str, why: str, out: List[Repl]
) -> None:
    """Planifica reemplazos sobre `container[key]` cuando es lista de valores."""
    if not isinstance(container, dict):
        return
    lst = container.get(key)
    if not isinstance(lst, list):
        return
    for i, v in enumerate(lst):
        nv = _map_value(v)
        if nv is None:
            continue
        out.append(
            Repl(f"{base_path}.{key}[{i}]", v, nv, why, _setter_list(lst, i, nv))
        )


def _plan_dict_keys(
    d: Any, base_path: str, why: str, out: List[Repl]
) -> None:
    """Planifica renombres de CLAVE cuando las claves son valores de la
    dimensión (color_overrides, value_aliases, lookup_dict.mapping)."""
    if not isinstance(d, dict):
        return
    for k in list(d.keys()):
        nk = _map_value(k)
        if nk is None:
            continue
        out.append(
            Repl(f"{base_path}.{{{k}}}", k, nk, why, _setter_dict_key(d, k, nk))
        )


def _plan_filters(
    filters: Any, base_path: str, aliases: Set[str], out: List[Repl]
) -> None:
    """`filters` es {nombre_de_campo: valor | [valores]}. El campo gobernante
    es la propia clave, así que el filtrado por dimensión es directo."""
    if not isinstance(filters, dict):
        return
    for fname, fval in filters.items():
        if _norm(fname) not in aliases:
            continue
        why = f"filters key {fname!r}"
        path = f"{base_path}.{fname}"
        if isinstance(fval, list):
            for i, v in enumerate(fval):
                nv = _map_value(v)
                if nv is None:
                    continue
                out.append(Repl(f"{path}[{i}]", v, nv, why, _setter_list(fval, i, nv)))
        else:
            nv = _map_value(fval)
            if nv is not None:
                out.append(
                    Repl(path, fval, nv, why, _setter_dict_value(filters, fname, nv))
                )


def _plan_derived_config(
    cfg: Any, base_path: str, aliases: Set[str], out: List[Repl]
) -> None:
    """Un config de `derived_columns` / `derived_fields_override`.

    - `time_ordinal_levels` enumera valores de `time_field` (slope, delta,
      temporal_value_at). Es lo que rompe la matriz de transición.
    - `mapping` de un `lookup_dict` tiene por claves los valores de
      `value_field`.
    """
    if not isinstance(cfg, dict):
        return
    tf = cfg.get("time_field")
    if _norm(tf) in aliases:
        _plan_list(
            cfg, "time_ordinal_levels", base_path, f"time_field={tf!r}", out
        )
    vf = cfg.get("value_field")
    if _norm(vf) in aliases and cfg.get("kind") == "lookup_dict":
        _plan_dict_keys(
            cfg.get("mapping"), f"{base_path}.mapping", f"value_field={vf!r}", out
        )


def _plan_data_source(
    ds: Any, base_path: str, aliases: Set[str], out: List[Repl]
) -> None:
    if not isinstance(ds, dict):
        return
    _plan_filters(ds.get("filters"), f"{base_path}.filters", aliases, out)
    for j, dfo in enumerate(ds.get("derived_fields_override") or []):
        _plan_derived_config(
            dfo, f"{base_path}.derived_fields_override[{j}]", aliases, out
        )


def _plan_chart(cfg: Any, base_path: str, aliases: Set[str], out: List[Repl]) -> None:
    """Un ChartConfig (`Spec.charts_list[i]`).

    Semántica del renderer (`backend/routers/charts.py:_build_dataset`):
      - `x_order` ordena SIEMPRE los valores de `mapping.x_field`
        (bar / stacked_bar / stacked_grouped_bar / line, cols del heatmap
        y del pivot_matrix).
      - `stack_order` ordena `mapping.stack_field`; en heatmap y
        pivot_matrix — que no tienen stack_field — ordena `group_field`
        (filas / agrupador externo).
      - `color_overrides` se indexa por el valor del campo que define el
        color: `stack_field` en los apilados, `category_field` en el pie.
    """
    if not isinstance(cfg, dict):
        return
    _plan_data_source(cfg.get("data_source"), f"{base_path}.data_source", aliases, out)

    m = cfg.get("mapping") or {}
    aes = cfg.get("aesthetics")
    if not isinstance(aes, dict):
        return
    aes_path = f"{base_path}.aesthetics"

    x_field = m.get("x_field")
    if _norm(x_field) in aliases:
        _plan_list(aes, "x_order", aes_path, f"mapping.x_field={x_field!r}", out)

    stack_gov = m.get("stack_field") or m.get("group_field")
    if _norm(stack_gov) in aliases:
        _plan_list(
            aes, "stack_order", aes_path,
            f"mapping.{'stack_field' if m.get('stack_field') else 'group_field'}"
            f"={stack_gov!r}",
            out,
        )

    color_gov = m.get("stack_field") or m.get("category_field")
    if _norm(color_gov) in aliases:
        _plan_dict_keys(
            aes.get("color_overrides"), f"{aes_path}.color_overrides",
            f"campo de color={color_gov!r}", out,
        )


def _plan_table(cfg: Any, base_path: str, aliases: Set[str], out: List[Repl]) -> None:
    """Un TableConfig (`Spec.tables_list[i]`), clásico o pivote."""
    if not isinstance(cfg, dict):
        return
    _plan_data_source(cfg.get("data_source"), f"{base_path}.data_source", aliases, out)

    for j, col in enumerate(cfg.get("columns") or []):
        if not isinstance(col, dict):
            continue
        key = col.get("source_key") or col.get("key")
        if _norm(key) in aliases:
            _plan_dict_keys(
                col.get("value_aliases"),
                f"{base_path}.columns[{j}].value_aliases",
                f"columns[{j}].key={key!r}",
                out,
            )

    piv = cfg.get("pivot")
    if isinstance(piv, dict):
        order = piv.get("order")
        if isinstance(order, dict):
            for fname, lst in order.items():
                if _norm(fname) not in aliases or not isinstance(lst, list):
                    continue
                for i, v in enumerate(lst):
                    nv = _map_value(v)
                    if nv is None:
                        continue
                    out.append(
                        Repl(
                            f"{base_path}.pivot.order.{fname}[{i}]", v, nv,
                            f"pivot.order key {fname!r}", _setter_list(lst, i, nv),
                        )
                    )


def _plan_layout(node: Any, base_path: str, aliases: Set[str], out: List[Repl]) -> None:
    """`Indicator.dashboard_layout`: solo las posiciones de valor que el
    layout puede embeber (`filters` / `default_filters` de un item). Los
    textos de las notas quedan fuera a propósito."""
    if isinstance(node, dict):
        for k in ("filters", "default_filters"):
            if isinstance(node.get(k), dict):
                _plan_filters(node[k], f"{base_path}.{k}", aliases, out)
        for k, v in node.items():
            if k in ("filters", "default_filters"):
                continue
            _plan_layout(v, f"{base_path}.{k}", aliases, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _plan_layout(v, f"{base_path}[{i}]", aliases, out)


# ─────────────────────────────────────────────────────────────────────────
# Auditoría exhaustiva (lo que el plan NO cubrió)
# ─────────────────────────────────────────────────────────────────────────


def _walk(node: Any, path: str = ""):
    """Recorre el JSON completo emitiendo (ruta, valor) por hoja y por clave."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield f"{path}.{{{k}}}", k          # la clave, como valor potencial
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, node


def _audit(data: Any, base_path: str, planned: Set[str], plan: ObjPlan) -> None:
    for path, val in _walk(data, base_path):
        if not isinstance(val, str):
            continue
        if _looks_like_version_literal(val):
            if path not in planned:
                plan.unhandled.append((path, val))
        elif len(val) <= 400 and any(
            tok in _norm(val) for tok in VALUE_MAP
        ):
            plan.freetext.append((path, val))


# ─────────────────────────────────────────────────────────────────────────
# Resolución de la dimensión objetivo y sus alias de campo
# ─────────────────────────────────────────────────────────────────────────


def _resolve_version_aliases(db, org_id: int) -> Tuple[Any, Set[str]]:
    """Devuelve (Dimension, {nombres normalizados que refieren a Versión}).

    Además del nombre propio de la dimensión, acepta los alias de rol
    declarados en `Indicator.column_roles` (`{rol: [{metric_id, column}]}`)
    y su forma `_rol`, que es como el layout referencia campos por rol.
    """
    from backend.models import Dimension, Indicator

    dims = [
        d
        for d in db.query(Dimension).filter(Dimension.org_id == org_id).all()
        if _norm(d.name) == VERSION_DIM_HINT
    ]
    if not dims:
        return None, set()
    if len(dims) > 1:
        print(
            f"  ! {len(dims)} dimensiones normalizan a {VERSION_DIM_HINT!r}: "
            f"{[(d.id_dimension, d.name) for d in dims]}"
        )
    dim = dims[0]
    aliases: Set[str] = {_norm(dim.name)}

    for ind in db.query(Indicator).filter(Indicator.org_id == org_id).all():
        roles = _loads(ind.column_roles, {})
        if not isinstance(roles, dict):
            continue
        for role, entries in roles.items():
            cols = entries if isinstance(entries, list) else [entries]
            for e in cols:
                col = e.get("column") if isinstance(e, dict) else e
                if _norm(col) == _norm(dim.name):
                    aliases.add(_norm(role))
                    aliases.add(_norm(f"_{role}"))
    return dim, aliases


def _verify_db_values(db, dim, org_id: int) -> Tuple[bool, str]:
    """Comprueba que los valores destino (1/2/3) existan de verdad en
    `metric_data` para esta dimensión. `dimensions_json` está keyeado por
    id_dimension (string), no por nombre."""
    from backend.models import Metric, MetricData, MetricDimension

    key = str(dim.id_dimension)
    metric_ids = [
        md.id_metric
        for md in db.query(MetricDimension)
        .filter(MetricDimension.id_dimension == dim.id_dimension)
        .all()
    ]
    if not metric_ids:
        return False, "ninguna métrica declara la dimensión"

    org_metric_ids = {
        m.id_metric
        for m in db.query(Metric).filter(Metric.org_id == org_id).all()
    }
    metric_ids = [m for m in metric_ids if m in org_metric_ids]
    if not metric_ids:
        return False, "ninguna métrica de la org declara la dimensión"

    counts: Counter = Counter()
    rows = (
        db.query(MetricData.dimensions_json)
        .filter(MetricData.id_metric.in_(metric_ids))
        .all()
    )
    for (raw,) in rows:
        d = _loads(raw, {})
        if isinstance(d, dict):
            counts[d.get(key)] += 1

    print(f"  métricas con la dimensión : {sorted(metric_ids)}")
    print(f"  valores en metric_data     : {dict(sorted(counts.items(), key=lambda kv: str(kv[0])))}")

    present = {str(k) for k in counts if k is not None}
    targets = set(VALUE_MAP.values())
    missing = targets - present
    stale = {v for v in present if _norm(v) in VALUE_MAP}
    if stale:
        return False, (
            f"los datos AÚN contienen literales de origen {sorted(stale)}; "
            "este script asume que los datos ya están en 1/2/3"
        )
    if missing:
        return False, f"faltan en los datos los valores destino {sorted(missing)}"
    return True, "los valores destino 1/2/3 están presentes en los datos"


# ─────────────────────────────────────────────────────────────────────────
# Asociación spec → indicador (solo informativa, para el reporte)
# ─────────────────────────────────────────────────────────────────────────


def _layout_spec_ids(node: Any, acc: Set[int]) -> None:
    if isinstance(node, dict):
        if node.get("type") in ("configured_chart", "configured_table") and node.get("spec_id") is not None:
            try:
                acc.add(int(node["spec_id"]))
            except (TypeError, ValueError):
                pass
        for v in node.values():
            _layout_spec_ids(v, acc)
    elif isinstance(node, list):
        for v in node:
            _layout_spec_ids(v, acc)


def _spec_to_indicator(db, org_id: int) -> Dict[int, List[Tuple[int, str]]]:
    from backend.models import Indicator

    out: Dict[int, List[Tuple[int, str]]] = {}
    for ind in db.query(Indicator).filter(Indicator.org_id == org_id).all():
        found: Set[int] = set()
        _layout_spec_ids(_loads(ind.dashboard_layout, {}), found)
        for sid in found:
            out.setdefault(sid, []).append((ind.id_indicator, ind.name))
    return out


# ─────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────


def run(
    org_id: int,
    apply: bool,
    only_specs: Optional[List[int]],
    only_indicator: Optional[int],
    force: bool,
) -> int:
    from backend.database import SessionLocal
    from backend.models import Indicator, Spec

    db = SessionLocal()
    try:
        print("=" * 76)
        print(f"fix_specs_version_idel — org {org_id} — "
              f"{'APPLY (escribe)' if apply else 'DRY-RUN (no escribe)'}")
        print(f"reemplazo: {', '.join(f'{k}→{v}' for k, v in VALUE_MAP.items())}")
        print("=" * 76)

        dim, aliases = _resolve_version_aliases(db, org_id)
        if dim is None:
            print(f"✖ No existe dimensión {VERSION_DIM_HINT!r} en la org {org_id}. Nada que hacer.")
            return 1
        print(f"\n[1] Dimensión objetivo: id={dim.id_dimension} name={dim.name!r} "
              f"data_type={dim.data_type}")
        print(f"    alias de campo aceptados: {sorted(aliases)}")

        print("\n[2] Verificación contra los datos reales")
        ok, msg = _verify_db_values(db, dim, org_id)
        print(f"    → {'OK' if ok else 'FALLA'}: {msg}")
        if not ok and not force:
            print("\n✖ Abortado. Re-correr con --force para ignorar esta verificación.")
            return 2

        assoc = _spec_to_indicator(db, org_id)
        plans: List[ObjPlan] = []

        # ── Specs ────────────────────────────────────────────────────────
        specs = db.query(Spec).filter(Spec.org_id == org_id).order_by(Spec.id_spec).all()
        if only_specs:
            specs = [s for s in specs if s.id_spec in set(only_specs)]
        if only_indicator is not None:
            keep = {
                sid for sid, inds in assoc.items()
                if any(i == only_indicator for i, _ in inds)
            }
            specs = [s for s in specs if s.id_spec in keep]

        print(f"\n[3] Specs en alcance: {len(specs)}")

        for s in specs:
            inds = assoc.get(s.id_spec, [])
            extra = (
                ", ".join(f"ind {i} '{n}'" for i, n in inds)
                if inds else "sin indicador en layout"
            )
            plan = ObjPlan("spec", s.id_spec, s.name, extra)

            charts = _loads(s.charts_list, [])
            tables = _loads(s.tables_list, [])
            meta = _loads(s.metadata_, {})

            if isinstance(charts, list):
                for i, cfg in enumerate(charts):
                    _plan_chart(cfg, f"charts_list[{i}]", aliases, plan.repls)
            if isinstance(tables, list):
                for i, cfg in enumerate(tables):
                    _plan_table(cfg, f"tables_list[{i}]", aliases, plan.repls)

            planned_paths = {r.path for r in plan.repls}
            _audit(charts, "charts_list", planned_paths, plan)
            _audit(tables, "tables_list", planned_paths, plan)
            _audit(meta, "metadata", planned_paths, plan)

            if plan.repls or plan.unhandled or plan.freetext:
                plans.append(plan)

        # ── Indicadores ──────────────────────────────────────────────────
        inds_q = db.query(Indicator).filter(Indicator.org_id == org_id)
        if only_indicator is not None:
            inds_q = inds_q.filter(Indicator.id_indicator == only_indicator)
        indicators = inds_q.order_by(Indicator.id_indicator).all()
        print(f"[3] Indicadores en alcance: {len(indicators)}")

        for ind in indicators:
            plan = ObjPlan("indicator", ind.id_indicator, ind.name)
            derived = _loads(ind.derived_columns, [])
            temporal = _loads(ind.temporal_config, {})
            layout = _loads(ind.dashboard_layout, {})

            if isinstance(derived, list):
                for i, entry in enumerate(derived):
                    if not isinstance(entry, dict):
                        continue
                    for j, c in enumerate(entry.get("configs") or []):
                        _plan_derived_config(
                            c, f"derived_columns[{i}].configs[{j}]", aliases, plan.repls
                        )
            if isinstance(temporal, dict):
                for k, lvl in enumerate(temporal.get("levels") or []):
                    if isinstance(lvl, dict) and _norm(lvl.get("label")) in aliases:
                        _plan_list(
                            lvl, "order", f"temporal_config.levels[{k}]",
                            f"levels[{k}].label={lvl.get('label')!r}", plan.repls,
                        )
            _plan_layout(layout, "dashboard_layout", aliases, plan.repls)

            planned_paths = {r.path for r in plan.repls}
            _audit(derived, "derived_columns", planned_paths, plan)
            _audit(temporal, "temporal_config", planned_paths, plan)
            _audit(layout, "dashboard_layout", planned_paths, plan)

            if plan.repls or plan.unhandled or plan.freetext:
                plans.append(plan)

        # ── Reporte ──────────────────────────────────────────────────────
        total = sum(len(p.repls) for p in plans)
        print("\n[4] Plan de reemplazos")
        print("-" * 76)
        if not total:
            print("    (ninguno — nada que reemplazar)")
        for p in plans:
            if not p.repls:
                continue
            head = f"{p.kind} {p.obj_id} — {p.name}"
            if p.extra:
                head += f"  [{p.extra}]"
            print(f"\n  {head}")
            for r in p.repls:
                print(f"     {r.path}")
                print(f"        {r.before!r} → {r.after!r}   ({r.why})")

        # ── Aplicar ──────────────────────────────────────────────────────
        # La fase de planificación trabaja sobre copias en memoria
        # (`json.loads`), así que hasta acá NO se tocó ningún objeto ORM.
        if apply and total:
            n = _apply_definitivo(db, plans, org_id, aliases)
            print(f"\n✔ COMMIT aplicado: {n} reemplazos "
                  f"sobre {len({(p.kind, p.obj_id) for p in plans if p.repls})} objetos.")
        elif apply:
            print("\nNada que aplicar (idempotente): no se escribió nada.")
        else:
            print(f"\nDry-run: {total} reemplazos pendientes. No se escribió nada.")

        # ── Revisión manual ──────────────────────────────────────────────
        unhandled = [(p, u) for p in plans for u in p.unhandled]
        freetext = [(p, f) for p in plans for f in p.freetext]
        print("\n[5] Revisión manual")
        print("-" * 76)
        if unhandled:
            print(f"  ⚠ {len(unhandled)} literal(es) vN en posición de valor NO cubiertos por el plan:")
            for p, (path, val) in unhandled:
                print(f"     {p.kind} {p.obj_id}  {path} = {val!r}")
        else:
            print("  ✓ 0 literales vN en posición de valor quedaron sin cubrir.")
        if freetext:
            print(f"\n  ℹ {len(freetext)} mención(es) de vN en TEXTO LIBRE (no se tocan):")
            for p, (path, val) in freetext:
                short = val if len(val) <= 110 else val[:107] + "..."
                print(f"     {p.kind} {p.obj_id}  {path}")
                print(f"        {short!r}")
        print("-" * 76)
        return 0
    finally:
        db.close()


def _apply_definitivo(db, plans, org_id: int, aliases: Set[str]) -> int:
    """Segunda pasada: re-planifica sobre objetos frescos y escribe.

    Se hace en dos pasadas a propósito. La primera (planificación) solo
    reporta y trabaja sobre copias en memoria; la segunda vuelve a leer,
    vuelve a planificar con las MISMAS reglas y escribe. Así el reporte que
    ve el operador y lo que se persiste salen del mismo código, y un
    dry-run nunca puede dejar el ORM sucio.
    """
    from backend.models import Indicator, Spec

    touched = {(p.kind, p.obj_id) for p in plans if p.repls}
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    applied = 0

    for kind, oid in sorted(touched):
        if kind == "spec":
            s = db.query(Spec).filter(Spec.id_spec == oid, Spec.org_id == org_id).first()
            if s is None:
                continue
            charts = _loads(s.charts_list, [])
            tables = _loads(s.tables_list, [])
            repls: List[Repl] = []
            if isinstance(charts, list):
                for i, cfg in enumerate(charts):
                    _plan_chart(cfg, f"charts_list[{i}]", aliases, repls)
            if isinstance(tables, list):
                for i, cfg in enumerate(tables):
                    _plan_table(cfg, f"tables_list[{i}]", aliases, repls)
            for r in repls:
                r.apply()
                applied += 1
            s.charts_list = _dumps(charts)
            s.tables_list = _dumps(tables)
            meta = _loads(s.metadata_, {})
            if isinstance(meta, dict):
                meta["updated_at"] = now
                s.metadata_ = _dumps(meta)
        else:
            ind = (
                db.query(Indicator)
                .filter(Indicator.id_indicator == oid, Indicator.org_id == org_id)
                .first()
            )
            if ind is None:
                continue
            derived = _loads(ind.derived_columns, [])
            temporal = _loads(ind.temporal_config, {})
            layout = _loads(ind.dashboard_layout, {})
            repls = []
            if isinstance(derived, list):
                for i, entry in enumerate(derived):
                    if not isinstance(entry, dict):
                        continue
                    for j, c in enumerate(entry.get("configs") or []):
                        _plan_derived_config(
                            c, f"derived_columns[{i}].configs[{j}]", aliases, repls
                        )
            if isinstance(temporal, dict):
                for k, lvl in enumerate(temporal.get("levels") or []):
                    if isinstance(lvl, dict) and _norm(lvl.get("label")) in aliases:
                        _plan_list(lvl, "order", f"temporal_config.levels[{k}]", "", repls)
            _plan_layout(layout, "dashboard_layout", aliases, repls)
            for r in repls:
                r.apply()
                applied += 1
            ind.derived_columns = _dumps(derived)
            ind.temporal_config = _dumps(temporal)
            ind.dashboard_layout = _dumps(layout)

    db.commit()
    return applied


def main() -> int:
    p = argparse.ArgumentParser(
        description=(__doc__ or "").strip().split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--org", type=int, required=True, help="org_id a reparar")
    p.add_argument("--apply", action="store_true", help="escribe (default: dry-run)")
    p.add_argument(
        "--database-url", default=None,
        help="DATABASE_URL a usar (default: la del entorno/.env)",
    )
    p.add_argument(
        "--spec", type=int, action="append", default=None,
        help="limitar a estos id_spec (repetible). Default: todos los de la org",
    )
    p.add_argument(
        "--indicator", type=int, default=None,
        help="limitar a los specs de este indicador (y al indicador mismo)",
    )
    p.add_argument(
        "--force", action="store_true",
        help="aplicar aunque la verificación contra metric_data falle",
    )
    args = p.parse_args()

    # Debe setearse ANTES de importar backend.database (lee DATABASE_URL al importar).
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    return run(args.org, args.apply, args.spec, args.indicator, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
