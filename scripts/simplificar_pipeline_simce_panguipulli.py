# -*- coding: utf-8 -*-
"""
simplificar_pipeline_simce_panguipulli.py
=========================================
Deja UN SOLO pipeline de SIMCE Panguipulli (Aptus), que recibe **dos archivos**
(Estudiante y Habilidad) y carga directo a las metricas 24 y 26.

Cambios que aplica:

  1. Pipeline 26 "SIMCE Panguipulli (Aptus)": elimina por completo el grupo de
     pasos del informe **OA** (6 pasos), porque la metrica 25 no la consume
     ningun indicador, dashboard ni informe. Queda de 19 -> 13 pasos y de 3 -> 2
     pausas de archivos.
  2. Elimina el pipeline "…- Archivos importables" (el que solo generaba
     archivos descargables). Se puede recrear con
     `scripts/crear_pipeline_emn_importables.py` si algun dia se necesita.
  3. Renombra el pipeline 26 a "SIMCE Panguipulli (Aptus)" — al quedar uno solo,
     el sufijo "- Carga directa" ya no distingue nada.

NO se toca la metrica 25 ni sus 921 filas ya cargadas: solo se deja de pedir el
archivo que la alimentaba.

Es IDEMPOTENTE: si ya se aplico, no vuelve a cambiar nada.

Uso
---
    # dev (dentro del contenedor backend, que ya apunta a la DB canonica)
    docker cp scripts/simplificar_pipeline_simce_panguipulli.py report_generator-backend-1:/tmp/s.py
    docker exec -e PYTHONPATH=/app report_generator-backend-1 sh -lc 'cd /app && python /tmp/s.py --dry-run'
    docker exec -e PYTHONPATH=/app report_generator-backend-1 sh -lc 'cd /app && python /tmp/s.py'

    # produccion (Supabase)
    export DATABASE_URL="<el de .env.railway>"
    python scripts/simplificar_pipeline_simce_panguipulli.py --dry-run
    python scripts/simplificar_pipeline_simce_panguipulli.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys

PIPELINE_ID = 26
NOMBRE_FINAL = "SIMCE Panguipulli (Aptus)"
NOMBRE_IMPORTABLES = "SIMCE Panguipulli (Aptus) - Archivos importables"
METRIC_OA = 25
GRUPO_OA = "oa"

DESCRIPCION_FINAL = (
    "Carga los ensayos SIMCE Panguipulli que aplica Aptus. Recibe 2 archivos por mes "
    "(Informe de logros por Estudiante y por Habilidad) y los guarda en las metricas 24 y 26. "
    "1 ejecucion = 1 mes. La carga es acumulativa: repetir un mes duplica sus filas."
)


def es_paso_de_oa(step: dict) -> bool:
    """True si el paso pertenece al grupo del informe OA."""
    p = step.get("params", {}) or {}
    if p.get("config_key") == GRUPO_OA:
        return True
    if p.get("input_key") == GRUPO_OA:
        return True
    if p.get("metric_id") == METRIC_OA:
        return True
    for spec in p.get("file_specs", []) or []:
        if spec.get("id") == GRUPO_OA:
            return True
    return False


def simplificar(cfg: dict) -> tuple[dict, int]:
    pasos = cfg.get("pipeline", [])
    quedan = [s for s in pasos if not es_paso_de_oa(s)]
    eliminados = len(pasos) - len(quedan)
    cfg["pipeline"] = quedan

    meta = cfg.setdefault("pipeline_metadata", {})
    meta["name"] = NOMBRE_FINAL
    meta["description"] = DESCRIPCION_FINAL

    # etiquetas sin el "(1 archivo del mes)" heredado, que ya se explica en la descripcion
    for s in quedan:
        if s.get("step") != "RequestUserFiles":
            continue
        for spec in s["params"].get("file_specs", []):
            if spec.get("id") == "estudiantes":
                spec["label"] = "Informe de logros por Estudiante"
            elif spec.get("id") == "habilidad":
                spec["label"] = "Informe de logros por Habilidad"
    return cfg, eliminados


def verificar(cfg: dict) -> None:
    pasos = cfg["pipeline"]
    nombres = [s["step"] for s in pasos]
    assert len(pasos) == 13, f"se esperaban 13 pasos, hay {len(pasos)}"
    assert nombres.count("RequestUserFiles") == 2, "deben quedar 2 pausas de archivos"
    assert nombres.count("SaveToMetric") == 2, "deben quedar 2 SaveToMetric"
    metricas = sorted(s["params"]["metric_id"] for s in pasos if s["step"] == "SaveToMetric")
    assert metricas == [24, 26], f"las metricas destino quedaron en {metricas}"
    assert not any(es_paso_de_oa(s) for s in pasos), "quedo algun paso de OA"
    roles = [sp["id"] for s in pasos if s["step"] == "RequestUserFiles"
             for sp in s["params"]["file_specs"]]
    assert roles == ["estudiantes", "habilidad"], f"roles inesperados: {roles}"
    # las transformaciones deben seguir intactas
    for s in pasos:
        if s["step"] == "ModifyColumnValues":
            cols = [t["columna"] for t in s["params"]["transformations"]]
            assert "Mes" in cols and "N Prueba" in cols, f"faltan derivaciones en {cols}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="no escribe, solo muestra el plan")
    ap.add_argument("--org", type=int, default=1)
    args = ap.parse_args()

    from backend.database import SessionLocal
    from backend.models import Pipeline

    db = SessionLocal()
    try:
        p = db.query(Pipeline).filter(
            Pipeline.pipeline_id == PIPELINE_ID, Pipeline.org_id == args.org).first()
        if not p:
            print(f"ERROR: no existe el pipeline {PIPELINE_ID} en la org {args.org}")
            return 2

        cfg = json.loads(p.config_json)
        antes = len(cfg.get("pipeline", []))
        cfg, eliminados = simplificar(cfg)
        verificar(cfg)

        print(f"Pipeline {PIPELINE_ID}: '{p.pipeline}'")
        print(f"  pasos: {antes} -> {len(cfg['pipeline'])}  (eliminados {eliminados} del grupo OA)")
        print(f"  nombre -> '{NOMBRE_FINAL}'")
        for i, s in enumerate(cfg["pipeline"], 1):
            extra = ""
            if s["step"] == "RequestUserFiles":
                extra = "  <- " + s["params"]["file_specs"][0]["label"]
            elif s["step"] == "SaveToMetric":
                extra = f"  -> metrica {s['params']['metric_id']}"
            print(f"   {i:2d}. {s['step']}{extra}")

        otro = db.query(Pipeline).filter(
            Pipeline.pipeline == NOMBRE_IMPORTABLES, Pipeline.org_id == args.org).first()
        print(f"\n  '{NOMBRE_IMPORTABLES}': " +
              (f"existe (id={otro.pipeline_id}) -> se elimina" if otro else "no existe, nada que hacer"))

        if args.dry_run:
            print("\n--dry-run: no se escribio nada.")
            return 0

        p.config_json = json.dumps(cfg, ensure_ascii=False, indent=2)
        p.pipeline = NOMBRE_FINAL
        p.description = DESCRIPCION_FINAL
        if otro:
            db.delete(otro)
        db.commit()

        restantes = db.query(Pipeline).filter(
            Pipeline.org_id == args.org, Pipeline.pipeline.ilike("%Panguipulli%")).all()
        print("\nAplicado. Pipelines de Panguipulli que quedan:")
        for r in restantes:
            print(f"   {r.pipeline_id} | {r.pipeline}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
