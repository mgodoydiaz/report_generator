"""
db_seed.py — Export/import/push de datos vía SQLAlchemy (portátil, sin pg_dump).

Útil para:
  - Cargar datos iniciales en Render u otro entorno remoto
  - Migrar datos entre ambientes sin acceso directo a psql/pg_dump

Uso:
    # Exportar a JSON
    python scripts/db_seed.py export                          # → db_seed.json
    python scripts/db_seed.py export --output mi_seed.json --sanitize-nan

    # Importar desde JSON
    python scripts/db_seed.py import                          # ← db_seed.json
    python scripts/db_seed.py import --input mi_seed.json --clear
    python scripts/db_seed.py import --input mi_seed.json --clear \\
        --target-url "postgresql://user:pass@host:5432/db"

    # Push directo de local → remoto (sin archivo intermedio)
    python scripts/db_seed.py push --target-url "postgresql://..." --clear --sanitize-nan
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine, text, inspect as sa_inspect
from sqlalchemy.orm import sessionmaker
from psycopg2.extras import execute_values

from backend.models import (
    Organization, OrganizationAsset, User, Pipeline, Spec,
    Dimension, DimensionValue,
    Metric, MetricDimension, MetricData,
    Indicator, IndicatorMetric,
)
from backend.database import Base

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Orden de tablas respetando dependencias FK
TABLE_ORDER = [
    ("organizations", Organization),
    ("organization_assets", OrganizationAsset),
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

# Strings que pandas/ETL dejan como marcadores de "sin dato" — los tratamos como NULL.
NAN_STRINGS = {"nan", "none", "null", "nat", "n/a", "na"}


# ═══════════════════════════════════════════════════════════════════════════
# Sanitización (opcional, --sanitize-nan)
# ═══════════════════════════════════════════════════════════════════════════

def _sanitize_parsed(obj):
    """Sanitiza un objeto ya parseado (dict/list/primitivos) recursivamente."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _sanitize_parsed(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_parsed(v) for v in obj]
    if isinstance(obj, str):
        if obj.strip().lower() in NAN_STRINGS:
            return None
        return obj
    if isinstance(obj, float):
        # pandas NaN (x != x)
        if obj != obj:
            return None
    return obj


def _sanitize_value(val):
    """
    Normaliza un valor de columna:
      - None pasa.
      - String 'nan'/'none'/'null'/... → None.
      - String que empieza con '{' o '[' se intenta parsear como JSON; si
        parsea, se sanitiza recursivamente y se re-serializa.
      - Cualquier otro valor pasa sin cambios.
    """
    if val is None:
        return None
    if isinstance(val, str):
        stripped = val.strip()
        if stripped.lower() in NAN_STRINGS:
            return None
        # JSON embebido
        if stripped and stripped[0] in "{[":
            try:
                parsed = json.loads(val)
                cleaned = _sanitize_parsed(parsed)
                return json.dumps(cleaned, ensure_ascii=False)
            except (ValueError, TypeError):
                pass
    return val


# ═══════════════════════════════════════════════════════════════════════════
# Serialización ORM → dict
# ═══════════════════════════════════════════════════════════════════════════

def _serialize(obj, sanitize: bool = False):
    """Convierte un objeto ORM a dict serializable. Si sanitize, normaliza 'nan' → None."""
    d = {}
    for attr in sa_inspect(obj.__class__).column_attrs:
        val = getattr(obj, attr.key)
        if isinstance(val, datetime):
            val = val.isoformat()
        if sanitize:
            val = _sanitize_value(val)
        d[attr.key] = val
    return d


def _get_attr_to_col_map(model):
    """Retorna mapa {attr_python: nombre_columna_db} para columnas con nombre distinto."""
    mapping = {}
    for attr in sa_inspect(model).column_attrs:
        col = attr.columns[0]
        if attr.key != col.name:
            mapping[attr.key] = col.name
    return mapping


def _prepare_rows(rows, model):
    """Parsea datetimes y renombra claves Python a nombres de columna DB."""
    datetime_cols = {
        attr.key for attr in sa_inspect(model).column_attrs
        if hasattr(attr.columns[0].type, "python_type")
        and attr.columns[0].type.python_type == datetime
    }
    attr_to_col = _get_attr_to_col_map(model)

    result = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            col_name = attr_to_col.get(k, k)
            if k in datetime_cols and v and isinstance(v, str):
                try:
                    v = datetime.fromisoformat(v)
                except (ValueError, TypeError):
                    pass
            new_row[col_name] = v
        result.append(new_row)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Etapas reusables (usadas por export, import y push)
# ═══════════════════════════════════════════════════════════════════════════

def _collect_data(source_url: str, sanitize: bool = False) -> dict:
    """Conecta a source_url, serializa todas las tablas y retorna dict {tabla: [rows]}."""
    engine = create_engine(source_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    data = {}
    total = 0
    try:
        for table_name, model in TABLE_ORDER:
            rows = db.query(model).all()
            data[table_name] = [_serialize(r, sanitize=sanitize) for r in rows]
            count = len(data[table_name])
            total += count
            print(f"  {table_name}: {count} registros")
    finally:
        db.close()

    print(f"Total: {total} registros recolectados" + (" (sanitizados)" if sanitize else ""))
    return data


def _load_data(target_url: str, data: dict, clear: bool = False, batch_size: int = 500):
    """
    Importa data a target_url en una sola transacción global usando
    psycopg2.execute_values. Optimizado para BD remota con fsync caro:
      - execute_values envía VALUES (r1),(r2),... en una query por batch,
        3-5x más rápido que INSERT parametrizado fila a fila.
      - Un solo commit al final → 1 solo fsync en vez de N por tabla.
      - Si algo falla, rollback total: staging queda intacta, puedes reintentar.
    """
    engine = create_engine(target_url)
    Base.metadata.create_all(bind=engine)

    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()

        if clear:
            print("Limpiando tablas existentes en destino...")
            for table_name, _model in reversed(TABLE_ORDER):
                cursor.execute(f"DELETE FROM {table_name}")
                if cursor.rowcount:
                    print(f"  {table_name}: {cursor.rowcount} eliminados")

        total = 0
        for table_name, model in TABLE_ORDER:
            rows = data.get(table_name, [])
            if not rows:
                continue

            rows = _prepare_rows(rows, model)
            count = len(rows)
            col_names = list(rows[0].keys())
            insert_sql = (
                f"INSERT INTO {table_name} ({', '.join(col_names)}) "
                f"VALUES %s ON CONFLICT DO NOTHING"
            )

            for i in range(0, count, batch_size):
                batch = rows[i:i + batch_size]
                values = [tuple(r.get(c) for c in col_names) for r in batch]
                execute_values(cursor, insert_sql, values, page_size=batch_size)
                done = min(i + batch_size, count)
                pct = int(done / count * 20)
                bar = "█" * pct + "░" * (20 - pct)
                print(f"  {table_name}: [{bar}] {done}/{count}", end="\r", flush=True)

            print(f"  {table_name}: [{('█' * 20)}] {count}/{count} ✓")
            total += count

        # Resetear secuencias de auto-increment (dentro de la misma transacción)
        for table_name, model in TABLE_ORDER:
            pk_col = list(model.__table__.primary_key.columns)[0]
            seq_name = f"{table_name}_{pk_col.name}_seq"
            try:
                cursor.execute(
                    f"SELECT setval(%s, COALESCE((SELECT MAX({pk_col.name}) FROM {table_name}), 0) + 1, false)",
                    (seq_name,),
                )
            except Exception:
                pass

        # UN SOLO commit al final → 1 fsync, no 12
        raw_conn.commit()
        print(f"\nImportados {total} registros totales")
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# Subcomandos CLI
# ═══════════════════════════════════════════════════════════════════════════

def run_export(output_path: Path, sanitize: bool = False):
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL no configurada en .env")
        sys.exit(1)

    data = _collect_data(DATABASE_URL, sanitize=sanitize)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    size_kb = output_path.stat().st_size // 1024
    print(f"Escrito a {output_path} ({size_kb} KB)")


def run_import(input_path: Path, clear: bool = False, target_url: Optional[str] = None,
               batch_size: int = 500):
    if not input_path.exists():
        print(f"ERROR: Archivo no encontrado: {input_path}")
        sys.exit(1)

    url = target_url or DATABASE_URL
    if not url:
        print("ERROR: no hay DATABASE_URL ni --target-url")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    _load_data(url, data, clear=clear, batch_size=batch_size)


def run_push(target_url: str, clear: bool = False, sanitize: bool = False,
             batch_size: int = 500):
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL (origen) no configurada en .env")
        sys.exit(1)
    if not target_url:
        print("ERROR: falta --target-url (destino)")
        sys.exit(1)

    print(f"→ Origen:  {DATABASE_URL.split('@')[-1]}")
    print(f"→ Destino: {target_url.split('@')[-1]}")
    print()

    data = _collect_data(DATABASE_URL, sanitize=sanitize)
    print()
    _load_data(target_url, data, clear=clear, batch_size=batch_size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export/import/push de datos vía SQLAlchemy")
    subparsers = parser.add_subparsers(dest="command")

    export_p = subparsers.add_parser("export", help="Exportar DB a JSON")
    export_p.add_argument("--output", default="db_seed.json", help="Archivo de salida")
    export_p.add_argument("--sanitize-nan", action="store_true",
                          help="Normaliza 'nan'/'none'/'NaT' (y floats NaN) a NULL/None antes de escribir")

    import_p = subparsers.add_parser("import", help="Importar JSON a DB")
    import_p.add_argument("--input", default="db_seed.json", help="Archivo de entrada")
    import_p.add_argument("--clear", action="store_true", help="DELETE FROM en todas las tablas antes de importar")
    import_p.add_argument("--target-url", default=None,
                          help="Override de DATABASE_URL para el destino (útil para push a staging/prod)")
    import_p.add_argument("--batch-size", type=int, default=1000,
                          help="Filas por batch de execute_values (default: 500)")

    push_p = subparsers.add_parser("push", help="Export + import directo (local → remoto sin archivo)")
    push_p.add_argument("--target-url", required=True, help="URL de la DB destino (ej. Render External URL)")
    push_p.add_argument("--clear", action="store_true", help="DELETE FROM destino antes de importar")
    push_p.add_argument("--sanitize-nan", action="store_true",
                        help="Normaliza 'nan'/'none'/'NaT' (y floats NaN) a NULL/None durante la transferencia")
    push_p.add_argument("--batch-size", type=int, default=1000,
                        help="Filas por batch de execute_values (default: 500)")

    args = parser.parse_args()

    if args.command == "export":
        run_export(Path(args.output), sanitize=args.sanitize_nan)
    elif args.command == "import":
        run_import(Path(args.input), clear=args.clear, target_url=args.target_url,
                   batch_size=args.batch_size)
    elif args.command == "push":
        run_push(target_url=args.target_url, clear=args.clear, sanitize=args.sanitize_nan,
                 batch_size=args.batch_size)
    else:
        parser.print_help()
