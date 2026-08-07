# -*- coding: utf-8 -*-
"""
dia_establecimiento_canonico.py
===============================
Agrega al pipeline DIA (id 21) la normalizacion del nombre de establecimiento.

Problema: los archivos fuente traen el nombre largo institucional
  - XLS celda B5:  'LICEO TECNICO PROFESIONAL PEOPLE HELP PEOPLE DE PANGUIPULLI'
                   'LICEO TECNICO PROFESIONAL PEOPLE HELP PEOPLE PULLINQUE'
  - PDF campo "Establecimiento:" (extraido por RunDIAPDFExtraction)
pero la base historica guarda los nombres canonicos cortos 'Liceo PHP Panguipulli'
y 'Liceo PHP Pullinque'. La config actual no tenia ningun paso que tradujera, o sea
que una carga nueva habria quedado con OTRO establecimiento que el historico y los
dashboards habrian partido los datos en dos colegios distintos.

Solucion: un ModifyColumnValues por artifact (estudiantes_raw y preguntas_raw),
insertado inmediatamente despues del paso que produce cada artifact. Mapea por
substring, en mayusculas, con fallback que conserva el valor original:

    'PANGUIPULLI' in valor  -> 'Liceo PHP Panguipulli'
    'PULLINQUE'  in valor   -> 'Liceo PHP Pullinque'
    otro                    -> se deja tal cual

Idempotente (si el paso ya existe, no duplica). Uso:
    docker cp scripts/dia_establecimiento_canonico.py report_generator-backend-1:/tmp/e.py
    docker exec -e PYTHONPATH=/app report_generator-backend-1 sh -lc 'cd /app && python /tmp/e.py --dry-run'
"""
from __future__ import annotations

import argparse
import json

PIPELINE_ID = 21
ORG = 1
MARCA = "canoniza Establecimiento"   # va en la description del paso; llave de idempotencia

TRANSFORMACION = {
    "columna": "Establecimiento",
    "operacion": "math",
    "usa_fila": True,
    "valores": [
        {"condicion": "'PANGUIPULLI' in str(row['Establecimiento']).upper()",
         "expresion": "'Liceo PHP Panguipulli'"},
        {"condicion": "'PULLINQUE' in str(row['Establecimiento']).upper()",
         "expresion": "'Liceo PHP Pullinque'"},
        {"condicion": "*",
         "expresion": "str(row['Establecimiento'])"},
    ],
}

# artifact -> step que lo produce (el paso nuevo se inserta justo despues)
OBJETIVOS = {"estudiantes_raw": "RunExcelETL", "preguntas_raw": "RunDIAPDFExtraction"}


def paso_nuevo(artifact: str) -> dict:
    return {
        "step": "ModifyColumnValues",
        "description": f"{MARCA} en {artifact} (nombre largo del archivo -> 'Liceo PHP ...')",
        "params": {
            "input_key": artifact,
            "output_key": artifact,
            "transformations": [json.loads(json.dumps(TRANSFORMACION))],
        },
    }


def transformar(cfg: dict) -> tuple[dict, list[str]]:
    notas, pasos = [], cfg["pipeline"]
    ya = {s["params"]["input_key"] for s in pasos
          if s["step"] == "ModifyColumnValues" and MARCA in (s.get("description") or "")}
    nuevos = []
    for s in pasos:
        nuevos.append(s)
        out = (s.get("params") or {}).get("output_key")
        if out in OBJETIVOS and s["step"] == OBJETIVOS[out]:
            if out in ya:
                notas.append(f"{out}: el paso ya existia, no se duplica")
            else:
                nuevos.append(paso_nuevo(out))
                notas.append(f"{out}: insertado ModifyColumnValues tras {s['step']}")
    cfg["pipeline"] = nuevos
    return cfg, notas


def verificar(cfg: dict) -> None:
    pasos = cfg["pipeline"]
    mios = [s for s in pasos if s["step"] == "ModifyColumnValues"
            and MARCA in (s.get("description") or "")]
    assert len(mios) == 2, f"se esperaban 2 pasos de canonizacion, hay {len(mios)}"
    for s in mios:
        assert s["params"]["input_key"] == s["params"]["output_key"], "no debe renombrar el artifact"
        conds = [v["condicion"] for v in s["params"]["transformations"][0]["valores"]]
        assert conds[-1] == "*", "falta el fallback que conserva el valor"
        idx = pasos.index(s)
        assert (pasos[idx - 1].get("params") or {}).get("output_key") == s["params"]["input_key"], \
            f"el paso de {s['params']['input_key']} no quedo pegado a su productor"
    # la cadena posterior no cambia
    metricas = sorted(s["params"]["metric_id"] for s in pasos if s["step"] == "SaveToMetric")
    assert metricas == [6, 7], f"metricas destino: {metricas}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from backend.database import SessionLocal
    from backend.models import Pipeline

    db = SessionLocal()
    try:
        p = db.query(Pipeline).filter(
            Pipeline.pipeline_id == PIPELINE_ID, Pipeline.org_id == ORG).first()
        if not p:
            print(f"ERROR: no existe el pipeline {PIPELINE_ID}"); return 2

        cfg = json.loads(p.config_json)
        antes = len(cfg["pipeline"])
        cfg, notas = transformar(cfg)
        verificar(cfg)

        print(f"Pipeline {PIPELINE_ID}: '{p.pipeline}'   pasos {antes} -> {len(cfg['pipeline'])}")
        for n in notas:
            print(f"  · {n}")
        print("\n  cadena resultante:")
        for i, s in enumerate(cfg["pipeline"], 1):
            pr = s.get("params") or {}
            io_ = f"{pr.get('input_key','-')} -> {pr.get('output_key','-')}" if pr.get("input_key") or pr.get("output_key") else ""
            if s["step"] == "SaveToMetric":
                io_ = f"{pr.get('input_key')} -> metrica {pr.get('metric_id')}"
            marca = "  «canoniza»" if MARCA in (s.get("description") or "") else ""
            print(f"   {i:2d}. {s['step']:22s} {io_}{marca}")

        if args.dry_run:
            print("\n--dry-run: no se escribio nada."); return 0
        p.config_json = json.dumps(cfg, ensure_ascii=False, indent=2)
        db.commit()
        print("\nAplicado.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
