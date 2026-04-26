"""
db_sync.py — Sincronizador incremental entre BDs Postgres.

Flujo: snapshot(origen) + snapshot(destino) → diff → apply(destino).

Subcomandos:
    snapshot   Genera un JSON con el estado actual de una BD.
    diff       Compara dos snapshots y genera el archivo de cambios.
    apply      Aplica un diff a una BD (con dry-run + confirmación).
    sync       End-to-end: snapshot origen + destino + diff + apply.

Flags relevantes:
    --skip-deletes       No propaga DELETEs (solo INSERT/UPDATE).
    --include-sensitive  Incluye users y organizations (por default se saltan).
    --exclude T1,T2      Omite tablas especificadas (ej: --exclude metric_data
                         para sync "estructural" sin datos masivos).
    --dry-run            Apply muestra el plan pero no modifica.
    --yes                Apply aplica sin pedir confirmación interactiva.

URLs:
    Aceptan literal o $VAR (env vars expandidas). Preferir env vars para
    no exponer credenciales en el shell history.

Ejemplos:
    # Snapshot local a archivo
    python scripts/db_sync.py snapshot --url "$DATABASE_URL" --output local.json

    # Sync local -> staging (modo réplica exacta, con confirmación)
    python scripts/db_sync.py sync \\
        --source-url "$DATABASE_URL" \\
        --target-url "$STAGING_DB_URL"

    # Sync "solo estructural" (sin los 16k registros de metric_data)
    python scripts/db_sync.py sync \\
        --source-url "$DATABASE_URL" \\
        --target-url "$STAGING_DB_URL" \\
        --exclude metric_data \\
        --yes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.orm import sessionmaker
from psycopg2.extras import execute_values

from backend.models import (
    Organization, OrganizationAsset, User, Pipeline, Spec,
    Dimension, DimensionValue,
    Metric, MetricDimension, MetricData,
    Indicator, IndicatorMetric,
)

# Reuso desde db_seed.py (helpers ya probados)
from scripts.db_seed import (
    TABLE_ORDER,
    _serialize as serialize_row,
    _prepare_rows as prepare_rows,
)


# ═══════════════════════════════════════════════════════════════════════════
# Constantes y configuración
# ═══════════════════════════════════════════════════════════════════════════

SENSITIVE_TABLES = {"users", "organizations"}

# Campos que se ignoran al detectar UPDATE (cambian todo el tiempo).
IGNORE_FIELDS_ON_UPDATE = {"created_at", "updated_at", "uploaded_at", "last_run"}

# Estrategia de identidad por tabla.
#   kind: "pk"                 → identidad por PK surrogate. Simple.
#         "natural_col"        → identidad por columna natural única (slug, email).
#         "natural_compound"   → identidad por tupla de FKs (metric_dimensions).
#         "natural_hashed"     → identidad por natural key con JSON normalizado
#                                (solo metric_data).
#   cols: columnas que forman la identidad.
#   hashed_cols: subconjunto cuyas strings deben normalizarse como JSON canonical.
IDENTITY_STRATEGY: Dict[str, Dict[str, Any]] = {
    "organizations":      {"kind": "natural_col",       "cols": ["slug"]},
    "organization_assets":{"kind": "pk",                "cols": ["id"]},
    "users":              {"kind": "natural_col",       "cols": ["email"]},
    "pipelines":          {"kind": "pk",                "cols": ["pipeline_id"]},
    "specs":              {"kind": "pk",                "cols": ["id_spec"]},
    "dimensions":         {"kind": "pk",                "cols": ["id_dimension"]},
    "dimension_values":   {"kind": "pk",                "cols": ["id_value"]},
    "metrics":            {"kind": "pk",                "cols": ["id_metric"]},
    "metric_dimensions":  {"kind": "natural_compound",  "cols": ["id_metric", "id_dimension"]},
    "metric_data":        {
        "kind": "natural_hashed",
        "cols": ["id_metric", "dimensions_json", "value"],
        "hashed_cols": ["dimensions_json", "value"],
    },
    "indicators":         {"kind": "pk",                "cols": ["id_indicator"]},
    "indicator_metrics":  {"kind": "natural_compound",  "cols": ["id_indicator", "id_metric"]},
}

TABLE_TO_MODEL: Dict[str, Any] = {
    "organizations": Organization,
    "organization_assets": OrganizationAsset,
    "users": User,
    "pipelines": Pipeline,
    "specs": Spec,
    "dimensions": Dimension,
    "dimension_values": DimensionValue,
    "metrics": Metric,
    "metric_dimensions": MetricDimension,
    "metric_data": MetricData,
    "indicators": Indicator,
    "indicator_metrics": IndicatorMetric,
}


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def canonical(value: Any) -> Any:
    """Normaliza un valor para comparación semántica.

    - Strings JSON: se parsean y re-serializan con sort_keys.
    - Otros valores: se devuelven tal cual.
    """
    if not isinstance(value, str):
        return value
    s = value.strip()
    if s and s[0] in "{[":
        try:
            return json.dumps(json.loads(s), sort_keys=True, ensure_ascii=False)
        except (ValueError, TypeError):
            pass
    return value


def expand_url(url_or_var: str) -> str:
    """Expande $VAR en la URL. Si no hay var, la retorna tal cual."""
    if not url_or_var:
        return url_or_var
    return os.path.expandvars(url_or_var)


def sanitize_host(url: str) -> str:
    """Extrae 'host[:port]/db' de una URL, sin credenciales."""
    try:
        p = urlparse(url)
        host = p.hostname or "?"
        port = f":{p.port}" if p.port else ""
        db = (p.path or "").lstrip("/")
        return f"{host}{port}/{db}"
    except Exception:
        return url.rsplit("@", 1)[-1] if "@" in url else url


def get_alembic_version(engine) -> Optional[str]:
    """Retorna la última migración aplicada, o None si la tabla no existe."""
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
            return row[0] if row else None
    except Exception:
        return None


def row_identity(table: str, row: dict) -> tuple:
    """Retorna una tupla identificadora estable para la fila."""
    cfg = IDENTITY_STRATEGY[table]
    hashed_cols = set(cfg.get("hashed_cols", []))
    values = []
    for col in cfg["cols"]:
        v = row.get(col)
        if col in hashed_cols:
            v = canonical(v)
        values.append(v)
    return (table, *values)


def _attr_to_col_map(model) -> Dict[str, str]:
    """Mapa attr python → nombre de columna DB."""
    return {attr.key: attr.columns[0].name for attr in sa_inspect(model).column_attrs}


def _pk_info(table: str) -> Tuple[str, str]:
    """Retorna (attr_python, col_name_db) del PK de la tabla."""
    model = TABLE_TO_MODEL[table]
    pk_col = list(model.__table__.primary_key.columns)[0]
    for attr in sa_inspect(model).column_attrs:
        if attr.columns[0].name == pk_col.name:
            return attr.key, pk_col.name
    return pk_col.name, pk_col.name


def _find_target_pk(cursor, table: str, identity: tuple) -> Optional[int]:
    """Busca el PK real en el target dado un identity tuple."""
    cfg = IDENTITY_STRATEGY[table]
    _, pk_col = _pk_info(table)

    # identity = (table, val1, val2, ...)
    values = list(identity[1:])
    cols = cfg["cols"]
    hashed_cols = set(cfg.get("hashed_cols", []))

    if cfg["kind"] == "pk":
        return values[0]

    if cfg["kind"] in ("natural_col", "natural_compound"):
        where_parts = [f"{c} = %s" for c in cols]
        cursor.execute(
            f"SELECT {pk_col} FROM {table} WHERE {' AND '.join(where_parts)}",
            tuple(values),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    if cfg["kind"] == "natural_hashed":
        # metric_data: filtrar por cols no-hashed (id_metric, indexed) y comparar
        # las hashed en Python.
        where_parts, where_vals = [], []
        for c, v in zip(cols, values):
            if c not in hashed_cols:
                where_parts.append(f"{c} = %s")
                where_vals.append(v)
        select_cols = [pk_col] + list(hashed_cols)
        where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
        cursor.execute(
            f"SELECT {', '.join(select_cols)} FROM {table}{where_sql}",
            tuple(where_vals),
        )
        target_hashes = tuple(
            canonical(values[cols.index(hc)]) for hc in hashed_cols
        )
        for db_row in cursor.fetchall():
            db_pk = db_row[0]
            db_hashes = tuple(canonical(db_row[i + 1]) for i in range(len(hashed_cols)))
            if db_hashes == target_hashes:
                return db_pk
        return None

    return None


def _parse_exclude(raw: Optional[str]) -> set[str]:
    if not raw:
        return set()
    return {t.strip() for t in raw.split(",") if t.strip()}


# ═══════════════════════════════════════════════════════════════════════════
# snapshot
# ═══════════════════════════════════════════════════════════════════════════

def run_snapshot(url: str, output_path: Optional[Path], exclude: set[str] = frozenset()) -> dict:
    """Genera el snapshot de una BD y opcionalmente lo escribe a disco."""
    url = expand_url(url)
    if not url:
        raise ValueError("URL vacía")

    engine = create_engine(url)
    Session = sessionmaker(bind=engine)
    db = Session()

    tables: Dict[str, list] = {}
    row_counts: Dict[str, int] = {}
    total = 0
    try:
        for table_name, model in TABLE_ORDER:
            if table_name in exclude:
                tables[table_name] = []
                row_counts[table_name] = 0
                print(f"  {table_name}: (excluida)")
                continue
            rows = db.query(model).all()
            serialized = [serialize_row(r, sanitize=False) for r in rows]
            tables[table_name] = serialized
            row_counts[table_name] = len(serialized)
            total += len(serialized)
            print(f"  {table_name}: {len(serialized)} filas")
    finally:
        db.close()

    snapshot = {
        "metadata": {
            "host": sanitize_host(url),
            "timestamp": datetime.utcnow().isoformat(),
            "alembic_version": get_alembic_version(engine),
            "row_counts": row_counts,
            "total_rows": total,
            "excluded": sorted(exclude),
        },
        "tables": tables,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2, default=str)
        size_kb = output_path.stat().st_size // 1024
        print(f"\n✓ Snapshot en {output_path} ({size_kb} KB, {total} filas)")

    return snapshot


# ═══════════════════════════════════════════════════════════════════════════
# diff
# ═══════════════════════════════════════════════════════════════════════════

def diff_table(
    table: str,
    rows_src: list,
    rows_tgt: list,
    skip_deletes: bool = False,
) -> dict:
    """Calcula inserts/updates/deletes entre source y target para una tabla."""
    src_by_key = {row_identity(table, r): r for r in rows_src}
    tgt_by_key = {row_identity(table, r): r for r in rows_tgt}

    inserts = [src_by_key[k] for k in src_by_key.keys() - tgt_by_key.keys()]
    deletes: list = []
    if not skip_deletes:
        for k, r in tgt_by_key.items():
            if k not in src_by_key:
                deletes.append({"key": list(k), "row": r})

    updates = []
    unchanged = 0
    for k in src_by_key.keys() & tgt_by_key.keys():
        src_row, tgt_row = src_by_key[k], tgt_by_key[k]
        changed = {}
        for field, src_val in src_row.items():
            if field in IGNORE_FIELDS_ON_UPDATE:
                continue
            if canonical(src_val) != canonical(tgt_row.get(field)):
                changed[field] = src_val
        if changed:
            updates.append({"key": list(k), "fields": changed})
        else:
            unchanged += 1

    return {
        "insert": inserts,
        "update": updates,
        "delete": deletes,
        "_counts": {
            "insert": len(inserts),
            "update": len(updates),
            "delete": len(deletes),
            "unchanged": unchanged,
        },
    }


def run_diff(
    source: dict,
    target: dict,
    output_path: Optional[Path] = None,
    skip_deletes: bool = False,
    include_sensitive: bool = False,
    exclude: set[str] = frozenset(),
) -> dict:
    """Compara dos snapshots y genera el archivo de cambios."""
    changes: Dict[str, dict] = {}
    summary: Dict[str, Any] = {}

    src_alembic = source.get("metadata", {}).get("alembic_version")
    tgt_alembic = target.get("metadata", {}).get("alembic_version")
    if src_alembic and tgt_alembic and src_alembic != tgt_alembic:
        print(f"⚠ alembic_version distintos: source={src_alembic} / target={tgt_alembic}")
        print("  Corre 'alembic upgrade head' en el target antes de aplicar.")

    src_tables = source.get("tables", {})
    tgt_tables = target.get("tables", {})

    for table_name, _model in TABLE_ORDER:
        if table_name in exclude:
            summary[table_name] = "skipped (excluded)"
            continue
        if table_name in SENSITIVE_TABLES and not include_sensitive:
            summary[table_name] = "skipped (sensitive)"
            continue
        result = diff_table(
            table_name,
            src_tables.get(table_name, []),
            tgt_tables.get(table_name, []),
            skip_deletes=skip_deletes,
        )
        changes[table_name] = {
            "insert": result["insert"],
            "update": result["update"],
            "delete": result["delete"],
        }
        summary[table_name] = result["_counts"]

    diff = {
        "metadata": {
            "source_host": source.get("metadata", {}).get("host"),
            "target_host": target.get("metadata", {}).get("host"),
            "alembic_version": src_alembic,
            "flags": {
                "skip_deletes": skip_deletes,
                "include_sensitive": include_sensitive,
                "excluded": sorted(exclude),
            },
            "timestamp": datetime.utcnow().isoformat(),
        },
        "changes": changes,
        "summary": summary,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(diff, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n✓ Diff en {output_path}")

    _print_summary(summary)
    return diff


def _print_summary(summary: dict) -> None:
    print("\n--- Resumen del diff ---")
    for table, info in summary.items():
        if isinstance(info, str):
            print(f"  {table}: {info}")
            continue
        ins = info.get("insert", 0)
        upd = info.get("update", 0)
        dele = info.get("delete", 0)
        unc = info.get("unchanged", 0)
        if ins == upd == dele == 0:
            print(f"  {table}: sin cambios ({unc} iguales)")
        else:
            print(f"  {table}: +{ins} ~{upd} -{dele} ({unc} iguales)")


# ═══════════════════════════════════════════════════════════════════════════
# apply
# ═══════════════════════════════════════════════════════════════════════════

def run_apply(
    diff: dict,
    target_url: str,
    dry_run: bool = False,
    yes: bool = False,
    batch_size: int = 500,
) -> None:
    """Aplica el diff a target_url. Usa transacción global con rollback on error."""
    target_url = expand_url(target_url)
    engine = create_engine(target_url)

    # Pre-check alembic_version
    diff_alembic = diff.get("metadata", {}).get("alembic_version")
    target_alembic = get_alembic_version(engine)
    if diff_alembic and target_alembic and diff_alembic != target_alembic:
        print("ABORT: alembic_version mismatch.")
        print(f"  Diff:   {diff_alembic}")
        print(f"  Target: {target_alembic}")
        print("  Corre 'alembic upgrade head' en el target antes.")
        sys.exit(1)

    _print_summary(diff.get("summary", {}))

    if dry_run:
        print("\n--dry-run: no se aplicaron cambios.")
        return

    if not yes:
        ans = input("\n¿Aplicar estos cambios? [y/N]: ").strip().lower()
        if ans not in ("y", "yes", "s", "si", "sí"):
            print("Cancelado.")
            return

    changes = diff.get("changes", {})

    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        totals = {"delete": 0, "insert": 0, "update": 0}

        # 1) DELETEs en orden reverso (hijos antes que padres)
        print("\n→ DELETEs")
        for table_name, _model in reversed(TABLE_ORDER):
            deletes = changes.get(table_name, {}).get("delete", [])
            if not deletes:
                continue
            _, pk_col = _pk_info(table_name)
            pk_attr, _ = _pk_info(table_name)
            count = 0
            for d in deletes:
                row = d.get("row", {})
                pk_val = row.get(pk_attr)
                if pk_val is None:
                    continue
                cursor.execute(f"DELETE FROM {table_name} WHERE {pk_col} = %s", (pk_val,))
                count += 1
            totals["delete"] += count
            print(f"  {table_name}: {count} filas")

        # 2) INSERTs en orden directo (padres antes que hijos)
        print("→ INSERTs")
        for table_name, model in TABLE_ORDER:
            inserts = changes.get(table_name, {}).get("insert", [])
            if not inserts:
                continue
            rows = prepare_rows(inserts, model)
            col_names = list(rows[0].keys())
            sql = (
                f"INSERT INTO {table_name} ({', '.join(col_names)}) "
                f"VALUES %s ON CONFLICT DO NOTHING"
            )
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                values = [tuple(r.get(c) for c in col_names) for r in batch]
                execute_values(cursor, sql, values, page_size=batch_size)
            totals["insert"] += len(inserts)
            print(f"  {table_name}: {len(inserts)} filas")

        # 3) UPDATEs
        print("→ UPDATEs")
        for table_name, model in TABLE_ORDER:
            updates = changes.get(table_name, {}).get("update", [])
            if not updates:
                continue
            pk_attr, pk_col = _pk_info(table_name)
            attr_to_col = _attr_to_col_map(model)
            count = 0
            for upd in updates:
                fields: dict = upd.get("fields", {})
                identity = tuple(upd.get("key", []))
                pk_val = _find_target_pk(cursor, table_name, identity)
                if pk_val is None:
                    continue
                set_parts, vals = [], []
                for field, val in fields.items():
                    if field == pk_attr:
                        continue  # no mover el PK
                    col = attr_to_col.get(field, field)
                    set_parts.append(f"{col} = %s")
                    vals.append(val)
                if not set_parts:
                    continue
                vals.append(pk_val)
                cursor.execute(
                    f"UPDATE {table_name} SET {', '.join(set_parts)} WHERE {pk_col} = %s",
                    tuple(vals),
                )
                count += 1
            totals["update"] += count
            print(f"  {table_name}: {count} filas")

        # 4) Reset secuencias (auto-increment)
        for table_name, model in TABLE_ORDER:
            pk_col_obj = list(model.__table__.primary_key.columns)[0]
            seq_name = f"{table_name}_{pk_col_obj.name}_seq"
            try:
                cursor.execute(
                    f"SELECT setval(%s, COALESCE((SELECT MAX({pk_col_obj.name}) FROM {table_name}), 0) + 1, false)",
                    (seq_name,),
                )
            except Exception:
                pass

        raw_conn.commit()
        print(f"\n✓ Apply exitoso: +{totals['insert']} ~{totals['update']} -{totals['delete']}")
    except Exception as e:
        raw_conn.rollback()
        print(f"\n✗ ERROR — rollback completo. {e}")
        raise
    finally:
        raw_conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# sync (all-in-one)
# ═══════════════════════════════════════════════════════════════════════════

def run_sync(
    source_url: str,
    target_url: str,
    skip_deletes: bool = False,
    include_sensitive: bool = False,
    exclude: set[str] = frozenset(),
    dry_run: bool = False,
    yes: bool = False,
    output_dir: Optional[Path] = None,
) -> None:
    src_url = expand_url(source_url)
    tgt_url = expand_url(target_url)
    print(f"→ Source: {sanitize_host(src_url)}")
    print(f"→ Target: {sanitize_host(tgt_url)}")
    if exclude:
        print(f"→ Excluidas: {', '.join(sorted(exclude))}")
    print()

    print("=== Snapshot del origen ===")
    src_path = (output_dir / "source.json") if output_dir else None
    source = run_snapshot(source_url, src_path, exclude=exclude)

    print("\n=== Snapshot del destino ===")
    tgt_path = (output_dir / "target.json") if output_dir else None
    target = run_snapshot(target_url, tgt_path, exclude=exclude)

    print("\n=== Diff ===")
    diff_path = (output_dir / "diff.json") if output_dir else None
    diff = run_diff(
        source, target, diff_path,
        skip_deletes=skip_deletes,
        include_sensitive=include_sensitive,
        exclude=exclude,
    )

    print("\n=== Apply ===")
    run_apply(diff, target_url, dry_run=dry_run, yes=yes)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="db_sync",
        description="Sincronizador incremental de Postgres (snapshot → diff → apply).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "URLs aceptan $VAR (env vars) — preferir sobre hardcodear credenciales.\n"
            "Ejemplo estructural (sin cargar metric_data):\n"
            "  db_sync sync --source-url $DATABASE_URL --target-url $STAGING_DB_URL "
            "--exclude metric_data --yes"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # snapshot
    sp = sub.add_parser("snapshot", help="Genera snapshot de una BD")
    sp.add_argument("--url", required=True, help="URL de la BD (acepta $VAR)")
    sp.add_argument("--output", required=True, type=Path, help="Archivo JSON de salida")
    sp.add_argument("--exclude", default=None,
                    help="Tablas a excluir (coma-separadas), ej: metric_data,users")

    # diff
    d = sub.add_parser("diff", help="Calcula diff entre dos snapshots")
    d.add_argument("--source", required=True, type=Path, help="Snapshot del origen")
    d.add_argument("--target", required=True, type=Path, help="Snapshot del destino")
    d.add_argument("--output", required=True, type=Path, help="Archivo de diff")
    d.add_argument("--skip-deletes", action="store_true",
                   help="No incluir DELETEs (solo INSERT/UPDATE)")
    d.add_argument("--include-sensitive", action="store_true",
                   help="Incluir users y organizations (default: se saltan)")
    d.add_argument("--exclude", default=None,
                   help="Tablas a excluir (coma-separadas)")

    # apply
    a = sub.add_parser("apply", help="Aplica un diff a una BD")
    a.add_argument("--diff", required=True, type=Path, help="Archivo de diff")
    a.add_argument("--target-url", required=True, help="URL BD destino (acepta $VAR)")
    a.add_argument("--dry-run", action="store_true", help="Mostrar plan sin aplicar")
    a.add_argument("--yes", action="store_true", help="No pedir confirmación")
    a.add_argument("--batch-size", type=int, default=500,
                   help="Filas por batch de INSERT (default: 500)")

    # sync (all-in-one)
    s = sub.add_parser("sync", help="Ejecuta snapshot + diff + apply end-to-end")
    s.add_argument("--source-url", required=True, help="URL BD origen")
    s.add_argument("--target-url", required=True, help="URL BD destino")
    s.add_argument("--skip-deletes", action="store_true",
                   help="No propagar DELETEs")
    s.add_argument("--include-sensitive", action="store_true",
                   help="Incluir users y organizations")
    s.add_argument("--exclude", default=None,
                   help="Tablas a excluir (ej: --exclude metric_data)")
    s.add_argument("--dry-run", action="store_true", help="No aplicar")
    s.add_argument("--yes", action="store_true", help="Omitir confirmación")
    s.add_argument("--output-dir", type=Path, default=None,
                   help="Directorio para guardar artefactos (source.json, target.json, diff.json)")

    args = parser.parse_args()

    if args.command == "snapshot":
        run_snapshot(args.url, args.output, exclude=_parse_exclude(args.exclude))
    elif args.command == "diff":
        with open(args.source, encoding="utf-8") as f:
            source = json.load(f)
        with open(args.target, encoding="utf-8") as f:
            target = json.load(f)
        run_diff(
            source, target, args.output,
            skip_deletes=args.skip_deletes,
            include_sensitive=args.include_sensitive,
            exclude=_parse_exclude(args.exclude),
        )
    elif args.command == "apply":
        with open(args.diff, encoding="utf-8") as f:
            diff = json.load(f)
        run_apply(diff, args.target_url,
                  dry_run=args.dry_run, yes=args.yes,
                  batch_size=args.batch_size)
    elif args.command == "sync":
        run_sync(
            args.source_url, args.target_url,
            skip_deletes=args.skip_deletes,
            include_sensitive=args.include_sensitive,
            exclude=_parse_exclude(args.exclude),
            dry_run=args.dry_run, yes=args.yes,
            output_dir=args.output_dir,
        )


if __name__ == "__main__":
    main()
