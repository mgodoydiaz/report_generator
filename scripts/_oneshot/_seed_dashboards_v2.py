"""Seed v2 de dashboards para las 5 evaluaciones.

Crea/actualiza specs (Tablas + Gráficos) y reescribe el dashboard_layout
de cada Indicador para que use exclusivamente `configured_table` y
`configured_chart` apuntando al catálogo /tables y /charts.

Uso:
    docker exec report_generator-backend-1 python scripts/_oneshot/_seed_dashboards_v2.py [--org-id 1] [--dry-run]

Idempotente: cada spec se upsertea por (org_id, name, type). Si ya existe
con ese nombre, se reemplaza su config; si no, se crea.

NO toca:
    - users
    - metric_data
    - pipelines
    - indicators.column_roles, achievement_levels, derived_columns
      (estos se preservan tal como están)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Asegurar que el paquete backend esté en el path cuando se ejecuta como script
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Indicator
from scripts._oneshot.dashboards_v2.cv import seed_cv
from scripts._oneshot.dashboards_v2.dia import seed_dia
from scripts._oneshot.dashboards_v2.fl import seed_fl
from scripts._oneshot.dashboards_v2.idel import seed_idel
from scripts._oneshot.dashboards_v2.simce import seed_simce


def _get_indicator_id(db: Session, org_id: int, name: str) -> int:
    ind = db.query(Indicator).filter(
        Indicator.org_id == org_id, Indicator.name == name
    ).first()
    if ind is None:
        raise RuntimeError(f"Indicador {name!r} no encontrado en org {org_id}")
    return ind.id_indicator


def main(org_id: int = 1, dry_run: bool = False) -> int:
    db = SessionLocal()
    try:
        simce_id = _get_indicator_id(db, org_id, "SIMCE")
        dia_id = _get_indicator_id(db, org_id, "DIA")
        idel_id = _get_indicator_id(db, org_id, "IDEL")
        cv_id = _get_indicator_id(db, org_id, "Cálculo Veloz")
        fl_id = _get_indicator_id(db, org_id, "Fluidez Lectora")

        print(f"→ Seedeando dashboards v2 (org_id={org_id})")
        print(f"  Indicadores: SIMCE={simce_id} DIA={dia_id} IDEL={idel_id} CV={cv_id} FL={fl_id}")

        results = {}
        results["DIA"] = seed_dia(db, org_id, dia_id)
        results["SIMCE"] = seed_simce(db, org_id, simce_id)
        results["IDEL"] = seed_idel(db, org_id, idel_id)
        results["CV"] = seed_cv(db, org_id, cv_id)
        results["FL"] = seed_fl(db, org_id, fl_id)

        for name, ids in results.items():
            print(f"  ✓ {name}: {len(ids)} specs (tablas + gráficos)")
            for k, v in ids.items():
                print(f"      {k}: id_spec={v}")

        if dry_run:
            print("→ Dry-run: rollback de la transacción")
            db.rollback()
        else:
            db.commit()
            print("→ Commit exitoso")
        return 0
    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed v2 de dashboards (5 evaluaciones).")
    parser.add_argument("--org-id", type=int, default=1, help="Organización destino (default 1)")
    parser.add_argument("--dry-run", action="store_true", help="No commitea, solo valida que la lógica corre")
    args = parser.parse_args()
    sys.exit(main(org_id=args.org_id, dry_run=args.dry_run))
