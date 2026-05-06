"""Snapshot/restore de dashboards y catálogos.

Backup focalizado de los componentes que cambias frecuentemente y que
quieres poder revertir:
    - specs Tablas + Gráficos (catálogo /tables y /charts)
    - indicators con dashboard_layout, column_roles, achievement_levels,
      derived_columns, pdf_layout, etc.
    - dimensions (definiciones, no values — los values se infieren de
      metric_data que NO se exporta acá)

NO incluye metric_data (eso es trabajo de scripts/db_seed.py o pg_dump).
La idea es preservar SOLO la *configuración visual y semántica* — la
parte que se pierde cuando el seed_dashboards_v2 sobre-escribe.

Uso:
    # Snapshot de la DB local (escribe backups/dashboards/<timestamp>.json)
    python scripts/snapshot_dashboards.py export

    # Snapshot de prod
    python scripts/snapshot_dashboards.py export \\
        --target-url "postgresql://..." --output backups/dashboards/prod.json

    # Listar snapshots disponibles
    python scripts/snapshot_dashboards.py list

    # Restaurar desde un snapshot (overwrite por id_spec / id_indicator)
    python scripts/snapshot_dashboards.py restore \\
        --input backups/dashboards/2026-05-06_153012.json
        [--target-url "postgresql://..."]   # destino (default: $DATABASE_URL)
        [--dry-run]                          # ver qué cambiaría sin commit

Restore strategy:
    - specs: si el id_spec existe en destino, su config se reemplaza;
      si no, se inserta con un nuevo id (los layouts de los indicators
      en el snapshot pueden quedar apuntando a ids que no existen en
      destino — restore prioriza preservar ids cuando es posible).
    - indicators: por nombre (campo único en una org). Reemplaza
      dashboard_layout, column_roles, achievement_levels, derived_columns,
      pdf_layout, pdf_layout_historico, role_labels, role_formats,
      filter_dimensions, temporal_config.
    - NO toca: metric_data, users, pipelines, organization_assets.

Idempotente: ejecutar restore N veces produce el mismo resultado.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.models import Dimension, Indicator, Spec


SNAPSHOT_DIR = ROOT / "backups" / "dashboards"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────
# Conexión
# ─────────────────────────────────────────────────────────────────────────


def make_session(url: Optional[str] = None) -> Session:
    target = url or os.getenv("DATABASE_URL", "")
    if not target:
        raise RuntimeError(
            "No DATABASE_URL configurada. Pasa --target-url o setea la env var."
        )
    engine = create_engine(target)
    return sessionmaker(bind=engine)()


# ─────────────────────────────────────────────────────────────────────────
# Export
# ─────────────────────────────────────────────────────────────────────────


def _spec_to_dict(s: Spec) -> Dict[str, Any]:
    return {
        "id_spec": s.id_spec,
        "name": s.name,
        "type": s.type,
        "metadata": s.metadata_,
        "charts_list": s.charts_list,
        "tables_list": s.tables_list,
        "org_id": s.org_id,
    }


def _indicator_to_dict(i: Indicator) -> Dict[str, Any]:
    return {
        "id_indicator": i.id_indicator,
        "name": i.name,
        "type": i.type,
        "description": i.description,
        "column_roles": i.column_roles,
        "role_labels": i.role_labels,
        "role_formats": i.role_formats,
        "filter_dimensions": i.filter_dimensions,
        "temporal_config": i.temporal_config,
        "achievement_levels": i.achievement_levels,
        "dashboard_layout": i.dashboard_layout,
        "derived_columns": i.derived_columns,
        "pdf_layout": i.pdf_layout,
        "pdf_layout_historico": i.pdf_layout_historico,
        "org_id": i.org_id,
    }


def _dimension_to_dict(d: Dimension) -> Dict[str, Any]:
    return {
        "id_dimension": d.id_dimension,
        "name": d.name,
        "data_type": d.data_type,
        "validation_mode": d.validation_mode,
        "description": d.description,
        "org_id": d.org_id,
    }


def export_snapshot(target_url: Optional[str], output: Optional[str]) -> Path:
    db = make_session(target_url)
    try:
        specs = db.query(Spec).filter(
            Spec.type.in_(("Tablas", "Gráficos"))
        ).all()
        indicators = db.query(Indicator).all()
        dimensions = db.query(Dimension).all()

        snapshot = {
            "version": 1,
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "source_url_redacted": _redact_url(target_url or os.getenv("DATABASE_URL", "")),
            "counts": {
                "specs_tablas": sum(1 for s in specs if s.type == "Tablas"),
                "specs_graficos": sum(1 for s in specs if s.type == "Gráficos"),
                "indicators": len(indicators),
                "dimensions": len(dimensions),
            },
            "specs": [_spec_to_dict(s) for s in specs],
            "indicators": [_indicator_to_dict(i) for i in indicators],
            "dimensions": [_dimension_to_dict(d) for d in dimensions],
        }

        if output:
            out_path = Path(output)
            if not out_path.is_absolute():
                out_path = ROOT / out_path
        else:
            ts = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
            label = "local" if not target_url else "remote"
            out_path = SNAPSHOT_DIR / f"{ts}_{label}.json"

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"✓ Snapshot escrito: {out_path}")
        for k, v in snapshot["counts"].items():
            print(f"    {k}: {v}")
        return out_path
    finally:
        db.close()


def _redact_url(url: str) -> str:
    """Oculta password en la URL para que el snapshot no la incluya plana."""
    import re
    return re.sub(r"://([^:]+):[^@]+@", r"://\1:***@", url)


# ─────────────────────────────────────────────────────────────────────────
# List
# ─────────────────────────────────────────────────────────────────────────


def list_snapshots() -> None:
    files = sorted(SNAPSHOT_DIR.glob("*.json"))
    if not files:
        print(f"(sin snapshots en {SNAPSHOT_DIR})")
        return
    print(f"Snapshots en {SNAPSHOT_DIR}:")
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            counts = data.get("counts", {})
            ts = data.get("exported_at", "?")
            src = data.get("source_url_redacted", "?")
            print(f"  {f.name}")
            print(f"      exported_at={ts}  source={src}")
            print(f"      {counts}")
        except Exception as e:
            print(f"  {f.name}  (corrupto: {e})")


# ─────────────────────────────────────────────────────────────────────────
# Restore
# ─────────────────────────────────────────────────────────────────────────


def restore_snapshot(input_path: str, target_url: Optional[str], dry_run: bool) -> None:
    p = Path(input_path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        raise FileNotFoundError(f"No existe: {p}")

    snapshot = json.loads(p.read_text(encoding="utf-8"))
    print(f"→ Restaurando desde {p.name}")
    print(f"  Origen: {snapshot.get('source_url_redacted', '?')}")
    print(f"  Exported_at: {snapshot.get('exported_at', '?')}")
    print(f"  Counts: {snapshot.get('counts', {})}")

    db = make_session(target_url)
    try:
        # Restore specs (Tablas + Gráficos): por id_spec si existe, si no insert.
        for s_dict in snapshot.get("specs", []):
            existing = db.get(Spec, s_dict["id_spec"])
            if existing is not None:
                existing.name = s_dict["name"]
                existing.type = s_dict["type"]
                existing.metadata_ = s_dict["metadata"]
                existing.charts_list = s_dict["charts_list"]
                existing.tables_list = s_dict["tables_list"]
            else:
                # Match alternativo por (org_id, name, type)
                alt = db.query(Spec).filter(
                    Spec.org_id == s_dict["org_id"],
                    Spec.name == s_dict["name"],
                    Spec.type == s_dict["type"],
                ).first()
                if alt is not None:
                    alt.metadata_ = s_dict["metadata"]
                    alt.charts_list = s_dict["charts_list"]
                    alt.tables_list = s_dict["tables_list"]
                else:
                    new = Spec(
                        name=s_dict["name"],
                        type=s_dict["type"],
                        metadata_=s_dict["metadata"],
                        charts_list=s_dict["charts_list"],
                        tables_list=s_dict["tables_list"],
                        org_id=s_dict["org_id"],
                    )
                    db.add(new)

        # Restore indicators por (org_id, name)
        for i_dict in snapshot.get("indicators", []):
            ind = db.query(Indicator).filter(
                Indicator.org_id == i_dict["org_id"],
                Indicator.name == i_dict["name"],
            ).first()
            if ind is None:
                print(f"  ! Indicador {i_dict['name']!r} no encontrado en destino — skip")
                continue
            ind.description = i_dict["description"]
            ind.column_roles = i_dict["column_roles"]
            ind.role_labels = i_dict["role_labels"]
            ind.role_formats = i_dict["role_formats"]
            ind.filter_dimensions = i_dict["filter_dimensions"]
            ind.temporal_config = i_dict["temporal_config"]
            ind.achievement_levels = i_dict["achievement_levels"]
            ind.dashboard_layout = i_dict["dashboard_layout"]
            ind.derived_columns = i_dict["derived_columns"]
            ind.pdf_layout = i_dict["pdf_layout"]
            ind.pdf_layout_historico = i_dict["pdf_layout_historico"]

        # Dimensions: solo agregamos las que no existen por (org_id, name).
        # NO mutamos dims existentes (sus id_dimension están referenciadas por
        # metric_data y dimension_values via FK).
        for d_dict in snapshot.get("dimensions", []):
            existing = db.query(Dimension).filter(
                Dimension.org_id == d_dict["org_id"],
                Dimension.name == d_dict["name"],
            ).first()
            if existing is None:
                new = Dimension(
                    name=d_dict["name"],
                    data_type=d_dict.get("data_type") or "str",
                    validation_mode=d_dict.get("validation_mode") or "free",
                    description=d_dict.get("description") or "",
                    org_id=d_dict["org_id"],
                )
                db.add(new)

        if dry_run:
            print("→ Dry-run: rollback de la transacción")
            db.rollback()
        else:
            db.commit()
            print("→ Commit exitoso")
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Snapshot/restore de dashboards.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("export", help="Exporta un snapshot a JSON")
    ex.add_argument("--target-url", help="URL de la DB origen (default: $DATABASE_URL)")
    ex.add_argument("--output", help="Ruta del archivo de salida (default: backups/dashboards/<ts>_<label>.json)")

    sub.add_parser("list", help="Lista snapshots disponibles")

    rs = sub.add_parser("restore", help="Restaura desde un snapshot JSON")
    rs.add_argument("--input", required=True, help="Ruta del snapshot JSON")
    rs.add_argument("--target-url", help="URL de la DB destino (default: $DATABASE_URL)")
    rs.add_argument("--dry-run", action="store_true", help="Valida sin commitear")

    args = parser.parse_args()
    if args.cmd == "export":
        export_snapshot(args.target_url, args.output)
    elif args.cmd == "list":
        list_snapshots()
    elif args.cmd == "restore":
        restore_snapshot(args.input, args.target_url, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
