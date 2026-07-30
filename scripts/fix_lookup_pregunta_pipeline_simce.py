"""Blinda el EnrichWithLookup del pipeline SIMCE (id 14) en la DB.

El bug real se corrigió en `EnrichWithLookup` (backend/rgenerator/core/etl_steps.py):
cuando `left_on == right_on` pandas colapsa las dos llaves en una sola columna
y el paso la borraba, dejando el DataFrame sin `Pregunta`.

Este script agrega además `"Pregunta"` a `columns` del step, que es el camino
explícito: con la llave pedida en `columns` el paso nunca la dropea, aun con
versiones viejas del código. Idempotente.

Ejecutar:
    docker exec report_generator-backend-1 \
        python /app/scripts/_oneshot/_fix_lookup_pregunta_pipeline_simce.py
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, "/app")

from backend.database import SessionLocal
from backend.models import Pipeline

PIPELINE_ID = 14


def main() -> int:
    db = SessionLocal()
    try:
        p = db.query(Pipeline).filter(Pipeline.pipeline_id == PIPELINE_ID).first()
        if not p:
            print(f"Pipeline {PIPELINE_ID} no existe")
            return 1

        cfg = json.loads(p.config_json)
        cambios = 0
        for i, step in enumerate(cfg.get("pipeline", [])):
            if step.get("step") != "EnrichWithLookup":
                continue
            params = step.get("params", {})
            llave = params.get("left_on") or params.get("on")
            cols = params.get("columns") or []
            if llave and llave not in cols:
                params["columns"] = [llave] + cols
                print(f"  step#{i}: columns {cols} → {params['columns']}")
                cambios += 1
            else:
                print(f"  step#{i}: ya incluye la llave {llave!r} en columns, sin cambios")

        if not cambios:
            print("Nada que cambiar (idempotente).")
            return 0

        p.config_json = json.dumps(cfg, ensure_ascii=False)
        db.commit()
        print(f"Pipeline {PIPELINE_ID} actualizado ({cambios} step(s)).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
