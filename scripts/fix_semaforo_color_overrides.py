#!/usr/bin/env python
"""Repara semáforos invertidos en specs de gráficos: escribe
`aesthetics.color_overrides` desde `Indicator.achievement_levels`.

PROBLEMA
--------
Un spec de gráfico (Spec.type='Gráficos') que colorea por categoría y NO
define `aesthetics.color_overrides` cae a la paleta indexada
(`ChartRenderer.pickSeriesColor` → `palette[i]`). Con `color_palette:
"semaforo"` (verde, ámbar, rojo) y `stack_order: ["Insuficiente",
"Elemental", "Adecuado"]` el resultado es el semáforo INVERTIDO:
Insuficiente sale verde y Adecuado rojo.

La corrección es la misma que ya aplican los seeders de dashboards v2
(`scripts/_oneshot/dashboards_v2/helpers.py:color_overrides_from_indicator`):
copiar {nombre_nivel: color_hex} desde `Indicator.achievement_levels` a
`aesthetics.color_overrides`, que tiene precedencia sobre la paleta.

RUNBOOK (3 líneas)
------------------
  1) Dry-run:  python scripts/fix_semaforo_color_overrides.py --org 1
  2) Aplicar:  python scripts/fix_semaforo_color_overrides.py --org 1 --apply
  3) Verificar: GET /api/charts/<id>/data → aesthetics.color_overrides debe
     traer los niveles con los colores del indicador (Insuficiente rojo,
     Adecuado verde). Re-correr el paso 1 debe reportar 0 pendientes.

En producción, apuntando a la DB externa sin tocar el .env del entorno:
  python scripts/fix_semaforo_color_overrides.py --org 1 --apply \
      --database-url "postgresql://..."

ALCANCE / GARANTÍAS
-------------------
- Org-scoped: solo toca specs de `--org`.
- Dry-run por defecto: sin `--apply` no escribe nada (no hace commit).
- Idempotente: un spec que ya tiene `color_overrides` no vuelve a tocarse
  (los de IDEL, CV y Fluidez Lectora quedan intactos).
- Solo toca los tipos de gráfico que realmente consumen `color_overrides`
  en el renderer: stacked_bar, stacked_grouped_bar y pie. heatmap /
  pivot_matrix usan otro mecanismo de color y se ignoran.
- Solo toca specs cuyo campo categórico coincide con los niveles de logro
  del indicador asociado (umbral: ≥2 coincidencias y ≥60% de cobertura).
- La asociación spec→indicador NO se adivina: se deriva por las dos rutas
  que usa el propio dashboard (ver `_resolve_indicator`). Si es ambigua,
  el spec se salta y se reporta.
- No modifica `color_palette` ni `stack_order`; `color_overrides` tiene
  precedencia sobre la paleta en `ChartRenderer` y en el motor de informes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────
# Constantes de dominio
# ─────────────────────────────────────────────────────────────────────────

SPEC_TYPE_CHART = "Gráficos"

# Tipos de gráfico cuyo renderer consulta `aesthetics.color_overrides`
# (frontend/src/components/charts/ChartRenderer.jsx → pickSeriesColor).
# El resto colorea por índice fijo (bar/box/line/grouped_bar) o por escala
# continua (heatmap), así que un color_overrides ahí sería letra muerta.
COLORABLE_TYPES = {"stacked_bar", "stacked_grouped_bar", "pie"}

# Umbrales del test "el mapeo usa niveles de logro del indicador".
MIN_MATCHES = 2
MIN_COVERAGE = 0.6


# ─────────────────────────────────────────────────────────────────────────
# Helpers de parsing
# ─────────────────────────────────────────────────────────────────────────


def _loads(raw: Optional[str], default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _category_field(chart_type: str, mapping: Dict[str, Any]) -> Optional[str]:
    """Campo cuyo valor determina el color de cada serie/porción."""
    if chart_type in ("stacked_bar", "stacked_grouped_bar"):
        return mapping.get("stack_field")
    if chart_type == "pie":
        return mapping.get("category_field") or mapping.get("x_field")
    return None


def _levels_from_indicator(ind) -> Dict[str, str]:
    """{nombre_nivel: color_hex} desde `Indicator.achievement_levels`.

    Mismo contrato que
    `scripts/_oneshot/dashboards_v2/helpers.py:color_overrides_from_indicator`.
    """
    levels = _loads(ind.achievement_levels, [])
    out: Dict[str, str] = {}
    if not isinstance(levels, list):
        return out
    for lv in levels:
        if not isinstance(lv, dict):
            continue
        name, color = lv.get("name"), lv.get("color")
        if name and color:
            out[str(name)] = str(color)
    return out


# ─────────────────────────────────────────────────────────────────────────
# Asociación spec → indicador
# ─────────────────────────────────────────────────────────────────────────


def _layout_spec_ids(node: Any, acc: Set[int]) -> None:
    """Recolecta los spec_id de todos los items `configured_chart` de un
    `dashboard_layout` (estructura anidada tabs → rows → items)."""
    if isinstance(node, dict):
        if node.get("type") == "configured_chart" and node.get("spec_id") is not None:
            try:
                acc.add(int(node["spec_id"]))
            except (TypeError, ValueError):
                pass
        for v in node.values():
            _layout_spec_ids(v, acc)
    elif isinstance(node, list):
        for v in node:
            _layout_spec_ids(v, acc)


def _build_association_index(db, org_id: int, Indicator, IndicatorMetric):
    """Devuelve (por_layout, por_metrica).

    - `por_layout[spec_id] = {id_indicator, ...}`: el indicador referencia el
      spec como `configured_chart` en su `dashboard_layout`. Es la relación
      que arma el seeder (`helpers.cfg_chart_item` + `update_indicator_layout`)
      y la que usa la página de Indicadores para pintar el dashboard.
    - `por_metrica[metric_id] = {id_indicator, ...}`: vía la junction
      `IndicatorMetric`. Es la misma ruta que usa
      `backend/routers/charts.py:_render_chart_data` para heredar
      `derived_columns` del indicador dueño de la métrica del chart.
    """
    por_layout: Dict[int, Set[int]] = {}
    for ind in db.query(Indicator).filter(Indicator.org_id == org_id).all():
        found: Set[int] = set()
        _layout_spec_ids(_loads(ind.dashboard_layout, {}), found)
        for sid in found:
            por_layout.setdefault(sid, set()).add(ind.id_indicator)

    org_ind_ids = {
        i.id_indicator
        for i in db.query(Indicator).filter(Indicator.org_id == org_id).all()
    }
    por_metrica: Dict[int, Set[int]] = {}
    for link in db.query(IndicatorMetric).all():
        if link.id_indicator in org_ind_ids:
            por_metrica.setdefault(link.id_metric, set()).add(link.id_indicator)

    return por_layout, por_metrica


def _resolve_indicator(
    spec_id: int,
    metric_id: Optional[int],
    por_layout: Dict[int, Set[int]],
    por_metrica: Dict[int, Set[int]],
) -> Tuple[Optional[int], str]:
    """Resuelve el indicador dueño de un spec de gráfico.

    Cruza las dos rutas del dashboard. Si ambas dan candidatos, se exige que
    coincidan (intersección). Cualquier ambigüedad devuelve (None, motivo)
    para que el caller salte el spec en vez de adivinar.
    """
    by_layout = por_layout.get(spec_id, set())
    by_metric = por_metrica.get(metric_id, set()) if metric_id is not None else set()

    if by_layout and by_metric:
        inter = by_layout & by_metric
        if not inter:
            return None, (
                f"conflicto: layout apunta a {sorted(by_layout)} y la métrica "
                f"{metric_id} a {sorted(by_metric)}"
            )
        cand, via = inter, "layout+métrica"
    elif by_layout:
        cand, via = by_layout, "layout"
    elif by_metric:
        cand, via = by_metric, "métrica"
    else:
        return None, "sin indicador asociado (ni por layout ni por métrica)"

    if len(cand) != 1:
        return None, f"ambiguo: {len(cand)} indicadores candidatos {sorted(cand)} (vía {via})"
    return next(iter(cand)), via


# ─────────────────────────────────────────────────────────────────────────
# Valores categóricos del gráfico
# ─────────────────────────────────────────────────────────────────────────


def _rendered_categories(db, org_id: int, cfg: Dict[str, Any]) -> Optional[List[str]]:
    """Categorías que el dashboard realmente colorea, obtenidas del MISMO
    render que sirve `GET /api/charts/{id}/data`
    (`backend/routers/charts.py:_render_chart_data`).

    Hay que pasar por ahí y no por un `SELECT DISTINCT` sobre la métrica:
    varias columnas categóricas (ej `Nivel_Logro` en SIMCE Panguipulli) no
    existen en `metric_data` — las produce el motor de `derived_columns` del
    indicador durante el render. Devuelve None si no se pudo renderizar
    (métrica sin datos, config inválida).
    """
    try:
        from backend.routers.charts import _render_chart_data
        from backend.schemas_chart import ChartConfig

        out = _render_chart_data(db, org_id, ChartConfig(**cfg), None)
    except Exception:
        return None
    ds = out.get("dataset") or {}
    if ds.get("empty"):
        return None
    names = [str(s.get("name")) for s in ds.get("stacks", []) if s.get("name") is not None]
    if not names:
        names = [str(x) for x in ds.get("labels", [])]
    return names or None


# ─────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────


def run(org_id: int, apply: bool, only_ids: Optional[List[int]] = None) -> int:
    from backend.database import SessionLocal
    from backend.models import Indicator, IndicatorMetric, Spec

    db = SessionLocal()
    try:
        por_layout, por_metrica = _build_association_index(
            db, org_id, Indicator, IndicatorMetric
        )
        inds = {
            i.id_indicator: i
            for i in db.query(Indicator).filter(Indicator.org_id == org_id).all()
        }

        specs = (
            db.query(Spec)
            .filter(Spec.org_id == org_id, Spec.type == SPEC_TYPE_CHART)
            .order_by(Spec.id_spec)
            .all()
        )
        if only_ids:
            specs = [s for s in specs if s.id_spec in set(only_ids)]

        print(f"→ Org {org_id}: {len(specs)} specs de tipo {SPEC_TYPE_CHART!r}")
        print(f"→ Modo: {'APPLY (escribe)' if apply else 'DRY-RUN (no escribe)'}")
        print()

        to_fix: List[Tuple[int, str, Dict[str, str]]] = []
        skipped: List[Tuple[int, str, str]] = []
        already: List[int] = []

        for spec in specs:
            charts = _loads(spec.charts_list, [])
            if not isinstance(charts, list) or not charts or not isinstance(charts[0], dict):
                skipped.append((spec.id_spec, spec.name, "charts_list vacío o inválido"))
                continue
            cfg = charts[0]
            ctype = cfg.get("chart_type")
            aes = cfg.get("aesthetics") or {}
            mapping = cfg.get("mapping") or {}
            metric_id = (cfg.get("data_source") or {}).get("metric_id")

            if ctype not in COLORABLE_TYPES:
                skipped.append(
                    (spec.id_spec, spec.name, f"chart_type {ctype!r} no usa color_overrides")
                )
                continue
            if aes.get("color_overrides"):
                already.append(spec.id_spec)
                continue

            field = _category_field(ctype, mapping)
            if not field:
                skipped.append(
                    (spec.id_spec, spec.name, f"{ctype} sin campo categórico en mapping")
                )
                continue

            ind_id, via = _resolve_indicator(spec.id_spec, metric_id, por_layout, por_metrica)
            if ind_id is None:
                skipped.append((spec.id_spec, spec.name, via))
                continue
            ind = inds[ind_id]
            levels = _levels_from_indicator(ind)
            if not levels:
                skipped.append(
                    (spec.id_spec, spec.name, f"indicador {ind_id} sin achievement_levels")
                )
                continue

            # Fuente de verdad: las categorías que el render del dashboard
            # produce de verdad. Fallback a stack_order si la métrica está
            # vacía en este entorno (así el fix sigue siendo aplicable).
            values = _rendered_categories(db, org_id, cfg)
            origen = "render"
            if not values:
                declared = aes.get("stack_order")
                values = [str(v) for v in declared] if declared else None
                origen = "stack_order"
            if not values:
                skipped.append(
                    (
                        spec.id_spec,
                        spec.name,
                        f"sin valores para el campo {field!r} (ni render ni stack_order)",
                    )
                )
                continue

            matched = [v for v in values if v in levels]
            coverage = len(matched) / len(values)
            if len(matched) < MIN_MATCHES or coverage < MIN_COVERAGE:
                skipped.append(
                    (
                        spec.id_spec,
                        spec.name,
                        f"campo {field!r} ({origen}) no son niveles de "
                        f"'{ind.name}': {len(matched)}/{len(values)} coinciden",
                    )
                )
                continue

            to_fix.append((spec.id_spec, spec.name, levels))
            print(f"  [FIX] spec {spec.id_spec} — {spec.name}")
            print(f"        tipo={ctype} campo={field!r} ({origen}) metric_id={metric_id}")
            print(f"        indicador={ind_id} '{ind.name}' (vía {via}), match {len(matched)}/{len(values)}")
            print(f"        color_overrides ← {json.dumps(levels, ensure_ascii=False)}")

            if apply:
                aes["color_overrides"] = dict(levels)
                cfg["aesthetics"] = aes
                charts[0] = cfg
                spec.charts_list = json.dumps(charts, ensure_ascii=False)
                meta = _loads(spec.metadata_, {})
                if isinstance(meta, dict):
                    from datetime import datetime

                    meta["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    spec.metadata_ = json.dumps(meta, ensure_ascii=False)

        if apply and to_fix:
            db.commit()

        print()
        print("─" * 72)
        print(f"A reparar        : {len(to_fix)} → {[s for s, _, _ in to_fix]}")
        print(f"Ya tenían colores: {len(already)} → {already}")
        print(f"Fuera de alcance : {len(skipped)}")
        for sid, name, why in skipped:
            print(f"   - {sid:>4}  {name[:48]:<48}  {why}")
        print("─" * 72)
        if apply and to_fix:
            print(f"✔ COMMIT aplicado sobre {len(to_fix)} specs.")
        elif apply:
            print("Nada que reparar: no se escribió nada (idempotente).")
        else:
            print("Dry-run: no se escribió nada. Re-correr con --apply para persistir.")
        return 0
    finally:
        db.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--org", type=int, required=True, help="org_id a reparar")
    p.add_argument("--apply", action="store_true", help="escribe (default: dry-run)")
    p.add_argument(
        "--database-url",
        default=None,
        help="DATABASE_URL a usar (default: la del entorno/.env)",
    )
    p.add_argument(
        "--chart-id",
        type=int,
        action="append",
        default=None,
        help="limitar a estos id_spec (repetible). Default: todos los de la org",
    )
    args = p.parse_args()

    # Debe setearse ANTES de importar backend.database (lee DATABASE_URL al importar).
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    return run(args.org, args.apply, args.chart_id)


if __name__ == "__main__":
    raise SystemExit(main())
