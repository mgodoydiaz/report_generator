"""Backfill SIMCE: agregar dimensión Establecimiento + N Prueba retroactivo.

Idempotente — si los rows ya tienen valor, no los toca.

Origen del backfill:
- Las métricas SIMCE 4 (estudiantes) y 5 (preguntas) NO tenían la
  dimensión Establecimiento asociada. Todos los datos cargados eran de
  Pullinque (LICEO TECNICO PROFESIONAL PEOPLE HELP PEOPLE DE PULLINQUE).
- N Prueba estaba vacío en todos los rows aunque el spec del pipeline
  lo declara. El usuario confirmó el mapeo Mes → N Prueba:
    Abril=1 / Junio=2 / Agosto=3 / Octubre=4 / Octubre 2=5

Ejecutar (dentro del container):
    python /app/scripts/backfill_simce_establecimiento.py
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, "/app")

from backend.database import SessionLocal
from backend.models import MetricData, MetricDimension, User


# IDs de dimensiones (verificadas via psql)
EST_DIM = 3        # Establecimiento
MES_DIM = 9        # Mes
NPRUEBA_DIM = 10   # N Prueba

MES_TO_NPRUEBA = {
    "ABRIL": 1, "JUNIO": 2, "AGOSTO": 3, "OCTUBRE": 4, "OCTUBRE 2": 5,
    "Abril": 1, "Junio": 2, "Agosto": 3, "Octubre": 4, "Octubre 2": 5,
}


def main() -> None:
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        org_id = admin.org_id

        # 1. Asociar Establecimiento a metrics 4 y 5
        print("== Asociar Establecimiento ==")
        for mid in (4, 5):
            link = db.query(MetricDimension).filter(
                MetricDimension.id_metric == mid,
                MetricDimension.id_dimension == EST_DIM,
            ).first()
            if link:
                print(f"  metric {mid}: ya asociada")
            else:
                db.add(MetricDimension(id_metric=mid, id_dimension=EST_DIM))
                print(f"  metric {mid}: + asociada")
        db.commit()

        # 2. Backfill Establecimiento="Pullinque"
        print("\n== Backfill Establecimiento=Pullinque ==")
        for mid in (4, 5):
            rows = db.query(MetricData).filter(MetricData.id_metric == mid).all()
            n = 0
            for r in rows:
                try:
                    dims = json.loads(r.dimensions_json) if isinstance(r.dimensions_json, str) else (r.dimensions_json or {})
                except Exception:
                    dims = {}
                if str(EST_DIM) in dims:
                    continue
                dims[str(EST_DIM)] = "Pullinque"
                r.dimensions_json = json.dumps(dims, ensure_ascii=False)
                n += 1
            db.commit()
            print(f"  metric {mid}: {n}/{len(rows)} rows actualizados")

        # 3. Backfill N Prueba según Mes
        print("\n== Backfill N Prueba (Abril=1..Octubre 2=5) ==")
        for mid in (4, 5):
            rows = db.query(MetricData).filter(MetricData.id_metric == mid).all()
            n = 0
            for r in rows:
                try:
                    dims = json.loads(r.dimensions_json) if isinstance(r.dimensions_json, str) else (r.dimensions_json or {})
                except Exception:
                    dims = {}
                existing = dims.get(str(NPRUEBA_DIM))
                if existing not in (None, "", "nan", "None"):
                    continue
                mes = dims.get(str(MES_DIM))
                if mes and mes in MES_TO_NPRUEBA:
                    dims[str(NPRUEBA_DIM)] = str(MES_TO_NPRUEBA[mes])
                    r.dimensions_json = json.dumps(dims, ensure_ascii=False)
                    n += 1
            db.commit()
            print(f"  metric {mid}: {n}/{len(rows)} rows con N Prueba")

        print("\nDONE")
    finally:
        db.close()


if __name__ == "__main__":
    main()
