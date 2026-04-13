import sys
import json
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from backend.database import SessionLocal
from backend import models

db = SessionLocal()

specs = db.query(models.Spec).all()
print(f"\n=== SPECS ({len(specs)}) ===")
for s in specs:
    try:
        meta = json.loads(s.metadata_ or "{}")
        has_charts = "charts_schema" in meta or "charts_list" in meta
        has_tables = "tables_list" in meta
        has_etl = "etlParams" in meta
        flags = []
        if has_charts: flags.append("charts")
        if has_tables: flags.append("tables")
        if has_etl: flags.append("etlParams")
        info = ", ".join(flags) if flags else "sin config"
    except Exception:
        info = "metadata inválida"
    print(f"  id={s.id_spec} name={s.name} [{info}]")

pipelines = db.query(models.Pipeline).all()
print(f"\n=== PIPELINES ({len(pipelines)}) ===")
for p in pipelines:
    has_config = bool(p.config_json and p.config_json.strip() not in ("{}", ""))
    print(f"  id={p.pipeline_id} name={p.pipeline} config={'OK' if has_config else 'vacío'}")

metrics = db.query(models.Metric).all()
print(f"\n=== METRICS ({len(metrics)}) ===")
for m in metrics:
    print(f"  id={m.id_metric} name={m.name} type={m.data_type}")

dimensions = db.query(models.Dimension).all()
print(f"\n=== DIMENSIONS ({len(dimensions)}) ===")
for d in dimensions:
    print(f"  id={d.id_dimension} name={d.name} type={d.data_type}")

indicators = db.query(models.Indicator).all()
print(f"\n=== INDICATORS ({len(indicators)}) ===")
for i in indicators:
    try:
        col_roles = json.loads(i.column_roles or "{}")
        n_roles = len(col_roles)
    except Exception:
        n_roles = "?"
    print(f"  id={i.id_indicator} name={i.name} column_roles={n_roles}")

metric_data = db.query(models.MetricData).count()
print(f"\n=== METRIC DATA ({metric_data} registros) ===")

db.close()
print("\nDone.")
