"""
migrate_excel_to_pg.py — Migración one-time de Excel → PostgreSQL.

Uso:
    conda activate rgenerator
    python scripts/migrate_excel_to_pg.py

Crea todas las tablas, inserta una organización por defecto (Fundación PHP)
y migra los datos existentes de los 8 archivos Excel.
"""

import sys
import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# Ajustar path para importar desde backend/
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from backend.database import engine, SessionLocal, init_db
from backend import models

DB_DIR = ROOT / "data" / "database"

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def read_excel(name: str) -> pd.DataFrame:
    path = DB_DIR / name
    if not path.exists():
        print(f"  ⚠️  {name} no existe, se omite.")
        return pd.DataFrame()
    df = pd.read_excel(path)
    # Reemplazar NaN por None para SQLAlchemy
    df = df.where(pd.notnull(df), None)
    return df


def safe_json(val, default="{}"):
    """Convierte un valor a string JSON limpio."""
    if val is None:
        return default
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, str) and val.strip():
        try:
            # Validar que es JSON válido
            json.loads(val)
            return val
        except Exception:
            # Intentar reparar comillas simples
            try:
                json.loads(val.replace("'", '"'))
                return val.replace("'", '"')
            except Exception:
                return default
    return default


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    print("🚀 Iniciando migración Excel → PostgreSQL\n")

    # 1. Crear todas las tablas
    print("📋 Creando tablas en PostgreSQL...")
    init_db()
    print("   ✅ Tablas creadas\n")

    db = SessionLocal()

    try:
        # ── 2. Organización por defecto ──────────────────────────
        print("🏢 Creando organización por defecto...")
        org = db.query(models.Organization).filter_by(slug="fundacion-php").first()
        if not org:
            org = models.Organization(
                name="Fundación PHP",
                slug="fundacion-php",
                is_active=True,
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"   ✅ Org creada: id={org.id}")
        else:
            print(f"   ℹ️  Org ya existe: id={org.id}")
        org_id = org.id

        # ── 3. Usuario admin por defecto ─────────────────────────
        print("\n👤 Creando usuario admin...")
        import bcrypt as _bcrypt

        admin = db.query(models.User).filter_by(email="admin@fundacionphp.cl").first()
        if not admin:
            hashed = _bcrypt.hashpw(b"admin1234", _bcrypt.gensalt()).decode()
            admin = models.User(
                email="admin@fundacionphp.cl",
                password_hash=hashed,
                org_id=org_id,
                role="admin",
            )
            db.add(admin)
            db.commit()
            print("   ✅ Admin creado: admin@fundacionphp.cl / admin1234")
            print("   ⚠️  Cambia la contraseña después del primer login!")
        else:
            print("   ℹ️  Admin ya existe.")

        # ── 4. Dimensions ─────────────────────────────────────────
        print("\n📐 Migrando dimensions.xlsx...")
        df = read_excel("dimensions.xlsx")
        id_map_dim = {}  # old_id → new_id (por si cambian)
        for _, row in df.iterrows():
            old_id = int(row["id_dimension"])
            existing = db.query(models.Dimension).filter_by(
                id_dimension=old_id, org_id=org_id
            ).first()
            if existing:
                id_map_dim[old_id] = old_id
                continue
            dim = models.Dimension(
                id_dimension=old_id,
                name=str(row["name"]),
                data_type=str(row.get("data_type") or "str"),
                validation_mode=str(row.get("validation_mode") or "free"),
                description=str(row.get("description") or ""),
                org_id=org_id,
            )
            db.add(dim)
            id_map_dim[old_id] = old_id
        db.commit()
        print(f"   ✅ {len(df)} dimensiones migradas")

        # ── 5. Dimension Values ───────────────────────────────────
        print("\n📋 Migrando dimension_values.xlsx...")
        df = read_excel("dimension_values.xlsx")
        for _, row in df.iterrows():
            old_id = int(row["id_value"])
            existing = db.query(models.DimensionValue).filter_by(id_value=old_id).first()
            if existing:
                continue
            dv = models.DimensionValue(
                id_value=old_id,
                id_dimension=int(row["id_dimension"]),
                value=str(row["value"]),
                is_active=bool(row.get("is_active", True)),
            )
            db.add(dv)
        db.commit()
        print(f"   ✅ {len(df)} valores de dimensión migrados")

        # ── 6. Metrics ────────────────────────────────────────────
        print("\n📊 Migrando metrics.xlsx...")
        df = read_excel("metrics.xlsx")
        for _, row in df.iterrows():
            old_id = int(row["id_metric"])
            existing = db.query(models.Metric).filter_by(
                id_metric=old_id, org_id=org_id
            ).first()
            if existing:
                continue
            m = models.Metric(
                id_metric=old_id,
                name=str(row["name"]),
                data_type=str(row.get("data_type") or "float"),
                meta_json=safe_json(row.get("meta_json"), "{}"),
                description=str(row.get("description") or ""),
                unit=str(row.get("unit") or ""),
                org_id=org_id,
            )
            db.add(m)
        db.commit()
        print(f"   ✅ {len(df)} métricas migradas")

        # ── 7. Metric Dimensions ──────────────────────────────────
        print("\n🔗 Migrando metric_dimensions.xlsx...")
        df = read_excel("metric_dimensions.xlsx")
        for _, row in df.iterrows():
            existing = db.query(models.MetricDimension).filter_by(
                id_metric=int(row["id_metric"]),
                id_dimension=int(row["id_dimension"]),
            ).first()
            if existing:
                continue
            md = models.MetricDimension(
                id_metric=int(row["id_metric"]),
                id_dimension=int(row["id_dimension"]),
            )
            db.add(md)
        db.commit()
        print(f"   ✅ {len(df)} relaciones metric-dimension migradas")

        # ── 8. Metric Data ────────────────────────────────────────
        print("\n💾 Migrando metric_data.xlsx...")
        df = read_excel("metric_data.xlsx")
        count = 0
        for _, row in df.iterrows():
            old_id = int(row["id_data"])
            existing = db.query(models.MetricData).filter_by(id_data=old_id).first()
            if existing:
                continue
            created = row.get("created_at")
            if pd.isna(created) or created is None:
                created = datetime.utcnow()
            elif not isinstance(created, datetime):
                try:
                    created = pd.to_datetime(created).to_pydatetime()
                except Exception:
                    created = datetime.utcnow()
            md = models.MetricData(
                id_data=old_id,
                id_metric=int(row["id_metric"]),
                value=str(row["value"]) if row.get("value") is not None else None,
                dimensions_json=safe_json(row.get("dimensions_json"), "{}"),
                created_at=created,
                org_id=org_id,
            )
            db.add(md)
            count += 1
        db.commit()
        print(f"   ✅ {count} puntos de datos migrados")

        # ── 9. Indicators ─────────────────────────────────────────
        print("\n📈 Migrando indicators.xlsx...")
        df = read_excel("indicators.xlsx")
        for _, row in df.iterrows():
            old_id = int(row["id_indicator"])
            existing = db.query(models.Indicator).filter_by(
                id_indicator=old_id, org_id=org_id
            ).first()
            if existing:
                continue
            ind = models.Indicator(
                id_indicator=old_id,
                name=str(row["name"]),
                description=str(row.get("description") or ""),
                type=str(row.get("type") or "Evaluación"),
                column_roles=safe_json(row.get("column_roles"), "{}"),
                role_labels=safe_json(row.get("role_labels"), "{}"),
                role_formats=safe_json(row.get("role_formats"), "{}"),
                filter_dimensions=safe_json(row.get("filter_dimensions"), "[]"),
                temporal_config=safe_json(row.get("temporal_config"), "{}"),
                achievement_levels=safe_json(row.get("achievement_levels"), "[]"),
                dashboard_layout=safe_json(row.get("dashboard_layout"), "{}"),
                org_id=org_id,
            )
            db.add(ind)
        db.commit()
        print(f"   ✅ {len(df)} indicadores migrados")

        # ── 10. Indicator Metrics ─────────────────────────────────
        print("\n🔗 Migrando indicator_metrics.xlsx...")
        df = read_excel("indicator_metrics.xlsx")
        for _, row in df.iterrows():
            existing = db.query(models.IndicatorMetric).filter_by(
                id_indicator=int(row["id_indicator"]),
                id_metric=int(row["id_metric"]),
            ).first()
            if existing:
                continue
            im = models.IndicatorMetric(
                id_indicator=int(row["id_indicator"]),
                id_metric=int(row["id_metric"]),
            )
            db.add(im)
        db.commit()
        print(f"   ✅ {len(df)} relaciones indicator-metric migradas")

        # ── 11. Specs ─────────────────────────────────────────────
        print("\n📄 Migrando specs.xlsx...")
        df = read_excel("specs.xlsx")
        for _, row in df.iterrows():
            old_id = int(row["id_spec"])
            existing = db.query(models.Spec).filter_by(
                id_spec=old_id, org_id=org_id
            ).first()
            if existing:
                continue
            sp = models.Spec(
                id_spec=old_id,
                name=str(row["name"]),
                type=str(row.get("type") or "Evaluación"),
                metadata_=safe_json(row.get("metadata"), "{}"),
                charts_list=safe_json(row.get("charts_list"), "[]"),
                tables_list=safe_json(row.get("tables_list"), "[]"),
                org_id=org_id,
            )
            db.add(sp)
        db.commit()
        print(f"   ✅ {len(df)} specs migradas")

        # ── 12. Pipelines ─────────────────────────────────────────
        print("\n⚙️  Migrando pipelines.xlsx...")
        df = read_excel("pipelines.xlsx")
        for _, row in df.iterrows():
            old_id = int(row["pipeline_id"])
            existing = db.query(models.Pipeline).filter_by(
                pipeline_id=old_id, org_id=org_id
            ).first()
            if existing:
                continue
            last_run = row.get("last_run")
            if pd.isna(last_run) or last_run is None:
                last_run = None
            elif not isinstance(last_run, datetime):
                try:
                    last_run = pd.to_datetime(last_run).to_pydatetime()
                except Exception:
                    last_run = None
            pl = models.Pipeline(
                pipeline_id=old_id,
                pipeline=str(row["pipeline"]),
                description=str(row.get("description") or ""),
                config_json=safe_json(row.get("config_json"), "{}"),
                hidden=bool(row.get("hidden", False)),
                last_run=last_run,
                org_id=org_id,
            )
            db.add(pl)
        db.commit()
        print(f"   ✅ {len(df)} pipelines migrados")

        print("\n" + "="*50)
        print("✅ Migración completada exitosamente!")
        print(f"   Organización: Fundación PHP (id={org_id})")
        print("   Admin: admin@fundacionphp.cl / admin1234")
        print("="*50)

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error durante la migración: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
