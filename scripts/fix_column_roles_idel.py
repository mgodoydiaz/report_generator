#!/usr/bin/env python
"""Repara `Indicator.column_roles` cuando falta un rol que el `pdf_layout`
sí referencia (caso IDEL: rol `logro_1` ausente).

PROBLEMA
--------
El `pdf_layout` del indicador IDEL (id 3, org 1) referencia `_logro_1` en
sus secciones (SummaryTable.valueField, BarByGroup.valueField), pero
`column_roles` no define el rol `logro_1`. El motor v1 resuelve los campos
`_<rol>` con `backend/rgenerator/core/report_steps.py:_resolve_field`, que
al no encontrar el rol devuelve el literal `'_logro_1'`; ese campo no
existe en los records y el informe imprime 0.0 donde el promedio real de
`Puntaje` es ~21.5.

`role_labels` y `role_formats` del indicador YA declaran
`logro_1: "Puntaje"` / `"#.0"`, o sea el rol estaba previsto y solo faltó
la entrada en `column_roles`.

FORMATO DE `column_roles` (verificado contra `backend/models.py` y el
indicador sano SIMCE id 1):

    {"<rol>": [{"metric_id": <int>, "column": "<nombre columna>"}, ...]}

`_resolve_field` y `metric_id_del_rol` usan SIEMPRE `entries[0]`; las
entradas extra sirven para otras métricas del mismo indicador.

RUNBOOK (3 líneas)
------------------
  1) Dry-run:  python scripts/fix_column_roles_idel.py --org 1
  2) Aplicar:  python scripts/fix_column_roles_idel.py --org 1 --apply
  3) Verificar: POST /api/indicators/3/export-pdf → el informe debe mostrar
     el promedio de Puntaje (~21.5) en vez de 0.0. Re-correr el paso 1 debe
     reportar "ya presente / nada que hacer".

En producción, apuntando a la DB externa sin tocar el .env del entorno:
  python scripts/fix_column_roles_idel.py --org 1 --apply \
      --database-url "postgresql://..."

ALCANCE / GARANTÍAS
-------------------
- Org-scoped: el indicador se busca filtrando por `--org`.
- Dry-run por defecto: sin `--apply` no escribe nada.
- Idempotente: si el rol ya existe con esa entrada, no hace nada. Si existe
  con OTRA entrada, no la pisa: aborta y lo reporta (no se asume que la
  config manual del usuario esté mal).
- Pre-chequeos antes de escribir: el indicador existe, la métrica está
  vinculada al indicador (`IndicatorMetric`) y la columna existe realmente
  en los datos de la métrica.
- Solo toca `column_roles`. No modifica pdf_layout, dashboard_layout,
  achievement_levels ni datos.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# Defaults = el caso diagnosticado (IDEL org 1).
DEF_INDICATOR_ID = 3
DEF_ROLE = "logro_1"
DEF_METRIC_ID = 8
DEF_COLUMN = "Puntaje"


def _loads(raw: Optional[str], default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _pdf_layout_refs(layout: Any, token: str, acc: List[str], path: str = "") -> None:
    """Rutas del pdf_layout que referencian `token` (ej '_logro_1')."""
    if isinstance(layout, dict):
        for k, v in layout.items():
            _pdf_layout_refs(v, token, acc, f"{path}.{k}" if path else k)
    elif isinstance(layout, list):
        for i, v in enumerate(layout):
            _pdf_layout_refs(v, token, acc, f"{path}[{i}]")
    elif isinstance(layout, str) and layout == token:
        acc.append(path)


def run(
    org_id: int,
    indicator_id: int,
    role: str,
    metric_id: int,
    column: str,
    apply: bool,
) -> int:
    from backend.database import SessionLocal
    from backend.models import Indicator, IndicatorMetric, Metric
    from backend.rgenerator.core.report_steps import _KNOWN_ROLES

    db = SessionLocal()
    try:
        ind = (
            db.query(Indicator)
            .filter(Indicator.id_indicator == indicator_id, Indicator.org_id == org_id)
            .first()
        )
        if ind is None:
            print(f"✗ Indicador {indicator_id} no existe en org {org_id}. Nada que hacer.")
            return 1

        print(f"→ Org {org_id} · Indicador {indicator_id} '{ind.name}'")
        print(f"→ Modo: {'APPLY (escribe)' if apply else 'DRY-RUN (no escribe)'}")
        print()

        # ── Pre-chequeo 0: el rol es conocido por el motor ─────────────────
        if role not in _KNOWN_ROLES:
            print(f"✗ Rol {role!r} no está en _KNOWN_ROLES del motor {sorted(_KNOWN_ROLES)}.")
            return 1

        roles: Dict[str, Any] = _loads(ind.column_roles, {})
        if not isinstance(roles, dict):
            print(f"✗ column_roles no es un objeto JSON: {ind.column_roles!r}")
            return 1

        print(f"  column_roles actual : {json.dumps(roles, ensure_ascii=False)}")
        print(f"  role_labels         : {ind.role_labels}")
        print(f"  role_formats        : {ind.role_formats}")

        refs: List[str] = []
        _pdf_layout_refs(_loads(ind.pdf_layout, {}), f"_{role}", refs)
        refs_h: List[str] = []
        _pdf_layout_refs(_loads(ind.pdf_layout_historico, {}), f"_{role}", refs_h)
        print(f"  pdf_layout referencia '_{role}' en    : {refs or '(ninguna)'}")
        print(f"  pdf_layout_historico  '_{role}' en    : {refs_h or '(ninguna)'}")
        print()

        entry = {"metric_id": metric_id, "column": column}

        # ── Idempotencia ──────────────────────────────────────────────────
        existing = roles.get(role)
        if isinstance(existing, list) and existing:
            if any(
                isinstance(e, dict)
                and e.get("metric_id") == metric_id
                and e.get("column") == column
                for e in existing
            ):
                print(f"✔ El rol {role!r} ya contiene {entry} — nada que hacer (idempotente).")
                return 0
            print(
                f"✗ El rol {role!r} ya existe con otra config "
                f"({json.dumps(existing, ensure_ascii=False)}). No se pisa. Revisar a mano."
            )
            return 1

        # ── Pre-chequeo 1: la métrica está vinculada al indicador ─────────
        link = (
            db.query(IndicatorMetric)
            .filter(
                IndicatorMetric.id_indicator == indicator_id,
                IndicatorMetric.id_metric == metric_id,
            )
            .first()
        )
        if link is None:
            linked = [
                l.id_metric
                for l in db.query(IndicatorMetric)
                .filter(IndicatorMetric.id_indicator == indicator_id)
                .all()
            ]
            print(
                f"✗ La métrica {metric_id} no está vinculada al indicador "
                f"{indicator_id}. Métricas vinculadas: {linked}"
            )
            return 1
        met = db.query(Metric).filter(Metric.id_metric == metric_id).first()
        print(f"  ✓ métrica {metric_id} ('{met.name if met else '?'}') vinculada al indicador")

        # ── Pre-chequeo 2: la columna existe en los datos de la métrica ───
        try:
            from backend.routers.tables import _load_metric_to_df

            df = _load_metric_to_df(db, org_id, metric_id, None)
        except Exception as exc:  # pragma: no cover — defensivo
            print(f"✗ No se pudo cargar la métrica {metric_id}: {exc}")
            return 1
        if df is None or df.empty:
            print(f"✗ La métrica {metric_id} no tiene datos en org {org_id}.")
            return 1
        if column not in df.columns:
            print(f"✗ La columna {column!r} no existe. Columnas: {list(df.columns)}")
            return 1
        import pandas as pd

        prom = pd.to_numeric(df[column], errors="coerce").mean()
        print(
            f"  ✓ columna {column!r} presente ({len(df)} filas, "
            f"promedio global {prom:.2f})"
        )
        print()

        # ── Escritura ─────────────────────────────────────────────────────
        roles[role] = [entry]
        nuevo = json.dumps(roles, ensure_ascii=False)
        print(f"  [FIX] column_roles[{role!r}] ← [{json.dumps(entry, ensure_ascii=False)}]")
        print(f"        column_roles nuevo: {nuevo}")
        print()

        if apply:
            ind.column_roles = nuevo
            db.commit()
            print(f"✔ COMMIT aplicado sobre el indicador {indicator_id}.")
        else:
            print("Dry-run: no se escribió nada. Re-correr con --apply para persistir.")
        return 0
    finally:
        db.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--org", type=int, required=True, help="org_id del indicador")
    p.add_argument("--apply", action="store_true", help="escribe (default: dry-run)")
    p.add_argument(
        "--database-url",
        default=None,
        help="DATABASE_URL a usar (default: la del entorno/.env)",
    )
    p.add_argument("--indicator-id", type=int, default=DEF_INDICATOR_ID)
    p.add_argument("--role", default=DEF_ROLE)
    p.add_argument("--metric-id", type=int, default=DEF_METRIC_ID)
    p.add_argument("--column", default=DEF_COLUMN)
    args = p.parse_args()

    # Debe setearse ANTES de importar backend.database (lee DATABASE_URL al importar).
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    return run(
        args.org, args.indicator_id, args.role, args.metric_id, args.column, args.apply
    )


if __name__ == "__main__":
    raise SystemExit(main())
