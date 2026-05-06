"""Sincroniza un subset filtrado de metric_data entre dos DBs.

Útil cuando ambientes (local / prod) tienen datos cargados de forma
asimétrica y necesitas copiar un subconjunto específico de uno a otro
sin tocar el resto.

Patrón de filtros:
    --metric-id N                         metric_data.id_metric = N (requerido)
    --dim-eq '{"4":"2026","8":"LECTURA"}'  filtros sobre dimensions_json (claves = id_dimension como str)

Idempotencia:
    Antes de insertar, borra filas en destino que cumplan EXACTAMENTE
    el mismo conjunto de filtros (mismo id_metric + mismos filtros de
    dim). Esto evita duplicar al re-ejecutar.

Uso:
    # Pang Lectura 2026 desde prod hacia local
    python scripts/_oneshot/_sync_metric_subset.py \\
        --source-url "$PROD_URL" \\
        --target-url "$LOCAL_URL" \\
        --metric-id 6 \\
        --dim-eq '{"4":"2026","8":"LECTURA","3":"LICEO TECNICO PROFESIONAL PEOPLE HELP PEOPLE DE PANGUIPULLI"}' \\
        --label "DIA Pang Lectura 2026"

    # Dry-run primero (no commitea)
    ... --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session


def _connect(url: str) -> Session:
    return sessionmaker(bind=create_engine(url))()


def _filter_clause(dim_eq: Dict[str, str]) -> str:
    """Construye un fragmento WHERE para los filtros sobre dimensions_json.

    Cada clave es un id_dimension como str. Compara igualdad de string.
    Devuelve la cláusula sin el `WHERE` inicial (se concatena al WHERE
    existente con AND).
    """
    parts = []
    for dim_id in dim_eq.keys():
        parts.append(f"(dimensions_json::jsonb)->>{dim_id!r} = :dim_{dim_id}")
    return " AND ".join(parts) if parts else "TRUE"


def _filter_params(dim_eq: Dict[str, str]) -> Dict[str, Any]:
    return {f"dim_{k}": v for k, v in dim_eq.items()}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-url", required=True)
    p.add_argument("--target-url", required=True)
    p.add_argument("--metric-id", type=int, required=True)
    p.add_argument(
        "--dim-eq", required=True,
        help='JSON dict {"<id_dimension>": "<value>"}',
    )
    p.add_argument("--label", default="(sin etiqueta)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    dim_eq = json.loads(args.dim_eq)
    where_dim = _filter_clause(dim_eq)
    params = _filter_params(dim_eq)
    params["mid"] = args.metric_id

    src = _connect(args.source_url)
    dst = _connect(args.target_url)

    try:
        # 1) Read from source
        sel = text(f"""
            SELECT id_metric, value, dimensions_json, created_at, org_id,
                   created_by_user_id, created_via, created_from_ip
              FROM metric_data
             WHERE id_metric = :mid AND {where_dim}
             ORDER BY id_data
        """)
        rows: List[Dict[str, Any]] = [dict(r._mapping) for r in src.execute(sel, params)]
        print(f"→ [{args.label}] origen: {len(rows)} filas")

        # 2) Count what's currently in target with same filter
        existing = dst.execute(
            text(f"SELECT COUNT(*) FROM metric_data WHERE id_metric=:mid AND {where_dim}"),
            params,
        ).scalar() or 0
        print(f"  destino actual con mismo filtro: {existing} filas (se borrarán antes de insertar)")

        if not rows:
            print("  ! origen vacío — no se hace nada")
            if args.dry_run:
                src.rollback(); dst.rollback()
            return 0

        # 3) Delete current rows in target (idempotency)
        dst.execute(
            text(f"DELETE FROM metric_data WHERE id_metric=:mid AND {where_dim}"),
            params,
        )

        # 4) Insert
        ins = text("""
            INSERT INTO metric_data
                (id_metric, value, dimensions_json, created_at, org_id,
                 created_by_user_id, created_via, created_from_ip)
            VALUES
                (:id_metric, :value, :dimensions_json, :created_at, :org_id,
                 :created_by_user_id, :created_via, :created_from_ip)
        """)
        for r in rows:
            dst.execute(ins, r)

        if args.dry_run:
            print("→ Dry-run: rollback")
            dst.rollback()
        else:
            dst.commit()
            print(f"✓ Commit: {len(rows)} filas insertadas")
        return 0
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    sys.exit(main())
