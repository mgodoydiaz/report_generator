"""
db_seed.py — Export/import de datos vía SQLAlchemy (portátil, sin pg_dump).

Útil para:
  - Cargar datos iniciales en Render u otro entorno remoto
  - Migrar datos entre ambientes sin acceso directo a psql/pg_dump

Uso:
    python scripts/db_seed.py export                          # → db_seed.json
    python scripts/db_seed.py export --output mi_seed.json
    python scripts/db_seed.py import                          # ← db_seed.json
    python scripts/db_seed.py import --input mi_seed.json --clear
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine, text, inspect as sa_inspect
from sqlalchemy.orm import sessionmaker

from backend.models import (
    Organization, User, Pipeline, Spec,
    Dimension, DimensionValue,
    Metric, MetricDimension, MetricData,
    Indicator, IndicatorMetric,
)
from backend.database import Base

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL no está configurada en .env")
    sys.exit(1)

# Orden de tablas respetando dependencias FK
TABLE_ORDER = [
    ("organizations", Organization),
    ("users", User),
    ("pipelines", Pipeline),
    ("specs", Spec),
    ("dimensions", Dimension),
    ("dimension_values", DimensionValue),
    ("metrics", Metric),
    ("metric_dimensions", MetricDimension),
    ("metric_data", MetricData),
    ("indicators", Indicator),
    ("indicator_metrics", IndicatorMetric),
]


def _serialize(obj):
    """Convierte un objeto ORM a dict serializable usando el mapper de SQLAlchemy."""
    d = {}
    for attr in sa_inspect(obj.__class__).column_attrs:
        val = getattr(obj, attr.key)
        if isinstance(val, datetime):
            val = val.isoformat()
        d[attr.key] = val
    return d


def run_export(output_path: Path):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    data = {}
    total = 0

    for table_name, model in TABLE_ORDER:
        rows = db.query(model).all()
        data[table_name] = [_serialize(r) for r in rows]
        count = len(data[table_name])
        total += count
        print(f"  {table_name}: {count} registros")

    db.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    size_kb = output_path.stat().st_size // 1024
    print(f"\nExportados {total} registros totales → {output_path} ({size_kb} KB)")


def _parse_datetimes(rows, model):
    """Convierte strings ISO a datetime en las columnas DateTime."""
    datetime_cols = {
        col.key for col in model.__table__.columns
        if hasattr(col.type, "python_type") and col.type.python_type == datetime
    }
    for row in rows:
        for col_key in datetime_cols:
            val = row.get(col_key)
            if val and isinstance(val, str):
                try:
                    row[col_key] = datetime.fromisoformat(val)
                except (ValueError, TypeError):
                    pass
    return rows


def run_import(input_path: Path, clear: bool = False, batch_size: int = 500):
    if not input_path.exists():
        print(f"ERROR: Archivo no encontrado: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)

    if clear:
        print("Limpiando tablas existentes...")
        with engine.begin() as conn:
            for table_name, model in reversed(TABLE_ORDER):
                result = conn.execute(text(f"DELETE FROM {table_name}"))
                if result.rowcount:
                    print(f"  {table_name}: {result.rowcount} eliminados")

    total = 0
    for table_name, model in TABLE_ORDER:
        rows = data.get(table_name, [])
        if not rows:
            continue

        rows = _parse_datetimes(rows, model)

        count = len(rows)
        n_batches = (count + batch_size - 1) // batch_size
        table = model.__table__

        with engine.begin() as conn:
            for batch_num, i in enumerate(range(0, count, batch_size), 1):
                batch = rows[i:i + batch_size]
                stmt = text(
                    f"INSERT INTO {table_name} ({', '.join(batch[0].keys())}) "
                    f"VALUES ({', '.join(':' + k for k in batch[0].keys())}) "
                    f"ON CONFLICT DO NOTHING"
                )
                conn.execute(stmt, batch)
                done = min(i + batch_size, count)
                pct = int(done / count * 20)
                bar = "█" * pct + "░" * (20 - pct)
                print(f"  {table_name}: [{bar}] {done}/{count}", end="\r", flush=True)

        print(f"  {table_name}: [{('█' * 20)}] {count}/{count} ✓")
        total += count

    # Resetear secuencias de auto-increment para PostgreSQL
    with engine.begin() as conn:
        for table_name, model in TABLE_ORDER:
            pk_col = list(model.__table__.primary_key.columns)[0]
            seq_name = f"{table_name}_{pk_col.name}_seq"
            try:
                conn.execute(text(
                    f"SELECT setval('{seq_name}', COALESCE((SELECT MAX({pk_col.name}) FROM {table_name}), 0) + 1, false)"
                ))
            except Exception:
                pass

    print(f"\nImportados {total} registros totales desde {input_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export/import de datos vía SQLAlchemy")
    subparsers = parser.add_subparsers(dest="command")

    export_p = subparsers.add_parser("export", help="Exportar DB a JSON")
    export_p.add_argument("--output", default="db_seed.json", help="Archivo de salida")

    import_p = subparsers.add_parser("import", help="Importar JSON a DB")
    import_p.add_argument("--input", default="db_seed.json", help="Archivo de entrada")
    import_p.add_argument("--clear", action="store_true", help="Limpiar tablas antes de importar")

    args = parser.parse_args()

    if args.command == "export":
        run_export(Path(args.output))
    elif args.command == "import":
        run_import(Path(args.input), clear=args.clear)
    else:
        parser.print_help()
