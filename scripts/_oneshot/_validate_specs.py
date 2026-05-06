"""Valida que cada spec del catálogo renderice sin errores.

- Gráficos: invoca _render_chart_data y verifica que no lance.
- Tablas: carga la metric_data y verifica que las columnas referidas existan.

Lo usa el seed v2 para confirmar consistencia post-creación.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal  # noqa: E402
from backend.models import Spec  # noqa: E402
from backend.routers.charts import _render_chart_data  # noqa: E402
from backend.routers.tables import _load_metric_to_df  # noqa: E402
from backend.schemas_chart import ChartConfig  # noqa: E402


def main(org_id: int = 1) -> int:
    db = SessionLocal()
    rc = 0
    try:
        # Charts
        ch_ok, ch_empty, ch_err = 0, [], []
        charts = db.query(Spec).filter(
            Spec.org_id == org_id, Spec.type == "Gráficos"
        ).all()
        for s in charts:
            try:
                lst = json.loads(s.charts_list or "[]")
                if not lst:
                    ch_err.append((s.id_spec, s.name, "charts_list vacío"))
                    continue
                cfg = ChartConfig(**lst[0])
                out = _render_chart_data(db, org_id, cfg)
                if out["dataset"].get("empty"):
                    ch_empty.append((s.id_spec, s.name, out["n_rows"]))
                else:
                    ch_ok += 1
            except Exception as e:
                ch_err.append((s.id_spec, s.name, str(e)[:160]))

        # Tables
        tb_ok, tb_missing, tb_err, tb_empty = 0, [], [], []
        tables = db.query(Spec).filter(
            Spec.org_id == org_id, Spec.type == "Tablas"
        ).all()
        for s in tables:
            try:
                lst = json.loads(s.tables_list or "[]")
                if not lst:
                    tb_err.append((s.id_spec, s.name, "tables_list vacío"))
                    continue
                cfg = lst[0]
                ds = cfg["data_source"]
                df = _load_metric_to_df(db, org_id, ds["metric_id"], ds.get("filters") or {})
                if df.empty:
                    tb_empty.append((s.id_spec, s.name))
                    continue
                cols_in_df = set(df.columns)
                missing = []
                for c in cfg.get("columns", []):
                    src = c.get("source_key") or c["key"]
                    if src not in cols_in_df:
                        missing.append(src)
                if missing:
                    tb_missing.append((s.id_spec, s.name, missing))
                else:
                    tb_ok += 1
            except Exception as e:
                tb_err.append((s.id_spec, s.name, str(e)[:160]))

        # Reporte
        print(f"Charts: {len(charts)} totales | {ch_ok} OK | {len(ch_empty)} vacíos | {len(ch_err)} errores")
        print(f"Tables: {len(tables)} totales | {tb_ok} OK | {len(tb_empty)} vacíos | {len(tb_missing)} con cols faltantes | {len(tb_err)} errores")

        if ch_err:
            print("\n-- CHART ERRORS --")
            for e in ch_err:
                print(f"  id={e[0]} {e[1]}: {e[2]}")
            rc = 1

        if ch_empty:
            print("\n-- CHARTS VACÍOS --")
            for e in ch_empty:
                print(f"  id={e[0]} {e[1]} (n_rows={e[2]})")

        if tb_missing:
            print("\n-- TABLE COLS FALTANTES --")
            for t in tb_missing:
                print(f"  id={t[0]} {t[1]} faltan: {t[2]}")
            rc = 1

        if tb_err:
            print("\n-- TABLE ERRORS --")
            for t in tb_err:
                print(f"  id={t[0]} {t[1]}: {t[2]}")
            rc = 1

        if tb_empty:
            print("\n-- TABLES VACÍAS --")
            for t in tb_empty:
                print(f"  id={t[0]} {t[1]}")

        return rc
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
