"""
Re-migra specs.xlsx leyendo la columna correcta: config_json (no metadata).
Actualiza los registros existentes en PostgreSQL.
"""
import sys
import pandas as pd
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from backend.database import SessionLocal
from backend import models

DB_DIR = ROOT / "data" / "database"

def safe_json(val, default="{}"):
    if val is None or (isinstance(val, float) and __import__('math').isnan(val)):
        return default
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, str) and val.strip():
        try:
            json.loads(val)
            return val
        except Exception:
            try:
                return json.dumps(json.loads(val.replace("'", '"')), ensure_ascii=False)
            except Exception:
                return default
    return default

df = pd.read_excel(DB_DIR / "specs.xlsx")
df = df.where(pd.notnull(df), None)

db = SessionLocal()
try:
    org = db.query(models.Organization).filter_by(slug="fundacion-php").first()
    org_id = org.id

    for _, row in df.iterrows():
        old_id = int(row["id_spec"])
        spec = db.query(models.Spec).filter_by(id_spec=old_id, org_id=org_id).first()

        config_json_str = safe_json(row.get("config_json"), "{}")

        if spec:
            spec.name = str(row["name"])
            spec.type = str(row.get("type") or "Evaluación")
            spec.metadata_ = config_json_str
            print(f"  Actualizado id={old_id} name={row['name']} config={config_json_str[:80]}...")
        else:
            spec = models.Spec(
                id_spec=old_id,
                name=str(row["name"]),
                type=str(row.get("type") or "Evaluación"),
                metadata_=config_json_str,
                charts_list="[]",
                tables_list="[]",
                org_id=org_id,
            )
            db.add(spec)
            print(f"  Creado id={old_id} name={row['name']}")

    db.commit()
    print(f"\n✅ {len(df)} specs actualizadas correctamente.")
except Exception as e:
    db.rollback()
    import traceback; traceback.print_exc()
    print(f"\n❌ Error: {e}")
finally:
    db.close()
