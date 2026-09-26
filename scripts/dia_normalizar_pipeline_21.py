# -*- coding: utf-8 -*-
"""
dia_normalizar_pipeline_21.py
=============================
Alinea el pipeline DIA de producción (id 21, Lectura + Matemática unificados)
con la convención vigente del repo (sept 2026). Tres cambios, todos idempotentes:

1. Logro de estudiantes (`row_mean_dynamic`):
   - `value_map {"L": 100, "NL": 0}`: 1° básico Lectura reporta Logrado / No
     Logrado en vez de %, y sin mapeo la fila quedaba sin Logro (criterio
     acordado con Miguel 2026-09-26).
   - `exclude_columns` suma "NIVEL DE LOGRO" y "Porcentaje total de respuestas
     correctas" (este último es un promedio ya calculado que sesgaba el mean).

2. Retiro de `Nombre_Norm` (convención del 2026-08-07): el `normalize_name` pasa a
   `copy` → `Nombre` (texto original del XLS) y el `agg` de "Logro Promedio"
   agrupa por `["Año", "Curso", "Nombre"]` con `entity_normalize: ["Nombre"]`.
   Antes agrupaba por `["Curso", "Nombre_Norm"]`, sin Año, y mezclaba años.

3. Establecimiento canónico: un `ModifyColumnValues` justo después de
   `RunExcelETL` y otro después de `RunDIAPDFExtraction`. Los archivos traen el
   nombre largo institucional, pero la base guarda los nombres cortos. El
   Colegio Básico y el Liceo de Panguipulli comparten RBD (16843) y el mismo
   texto en B5 ("... DE PANGUIPULLI"), así que se separan por curso: 1° a 6°
   básico → 'Colegio Básico'; 7°, 8° y media → 'Liceo PHP Panguipulli'. Es la
   misma partición que tiene hoy la data de prod.

Reemplaza a `dia_establecimiento_canonico.py`, cuya regla solo por substring
habría mandado el Colegio Básico al Liceo.

Uso:
    DATABASE_URL=... PYTHONPATH=. python scripts/dia_normalizar_pipeline_21.py --dry-run
    DATABASE_URL=... PYTHONPATH=. python scripts/dia_normalizar_pipeline_21.py [--respaldo archivo.json]
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

PIPELINE_ID = 21
ORG = 1
MARCA = "canoniza Establecimiento"   # llave de idempotencia (en la description)

EXCLUIR_EXTRA = ["NIVEL DE LOGRO", "Porcentaje total de respuestas correctas"]
VALUE_MAP = {"L": 100, "NL": 0}

# Primer carácter del curso: "1 A".."6 A" = básica del Colegio Básico. "7 A",
# "8 A" y los romanos de media ("I A (TPT-610)", "II B ...") son del Liceo.
_ES_BASICA = "str(row['Curso']).strip()[:1] in ('1', '2', '3', '4', '5', '6')"
TRANSFORMACION = {
    "columna": "Establecimiento",
    "operacion": "math",
    "usa_fila": True,
    "valores": [
        {"condicion": "'PULLINQUE' in str(row['Establecimiento']).upper()",
         "expresion": "'Liceo PHP Pullinque'"},
        {"condicion": f"'PANGUIPULLI' in str(row['Establecimiento']).upper() and {_ES_BASICA}",
         "expresion": "'Colegio Básico'"},
        {"condicion": "'PANGUIPULLI' in str(row['Establecimiento']).upper()",
         "expresion": "'Liceo PHP Panguipulli'"},
        {"condicion": "*",
         "expresion": "str(row['Establecimiento'])"},
    ],
}

# artifact -> step que lo produce (el paso nuevo va inmediatamente después)
OBJETIVOS = {"estudiantes_raw": "RunExcelETL", "preguntas_raw": "RunDIAPDFExtraction"}


def paso_canonico(artifact: str) -> dict:
    return {
        "step": "ModifyColumnValues",
        "description": f"{MARCA} en {artifact} (nombre largo del archivo -> nombre corto de la base, "
                       "Colegio Básico vs Liceo por curso)",
        "params": {
            "input_key": artifact,
            "output_key": artifact,
            "transformations": [copy.deepcopy(TRANSFORMACION)],
        },
    }


def _derivados_estudiantes(pasos: list) -> list:
    for s in pasos:
        if s["step"] == "ApplyDerivedFields" and (s.get("params") or {}).get("output_key") == "estudiantes_derived":
            return s["params"]["derived_fields"]
    raise AssertionError("no se encontró el ApplyDerivedFields de estudiantes")


def transformar(cfg: dict) -> tuple[dict, list[str]]:
    notas = []
    cfg = copy.deepcopy(cfg)
    pasos = cfg["pipeline"]

    # 1 + 2. Derivados de estudiantes
    derivados = _derivados_estudiantes(pasos)
    for f in derivados:
        if f.get("kind") == "row_mean_dynamic" and f.get("name") == "Logro":
            faltan = [c for c in EXCLUIR_EXTRA if c not in f["exclude_columns"]]
            if faltan:
                f["exclude_columns"].extend(faltan)
                notas.append(f"Logro: exclude_columns + {faltan}")
            if f.get("value_map") != VALUE_MAP:
                f["value_map"] = dict(VALUE_MAP)
                notas.append("Logro: value_map L=100 / NL=0")
    nuevos = []
    for f in derivados:
        if f.get("kind") == "normalize_name":
            nuevos.append({"kind": "copy", "name": "Nombre", "value_field": f["value_field"]})
            notas.append("normalize_name → Nombre_Norm reemplazado por copy → Nombre")
            continue
        if f.get("kind") == "agg" and f.get("name") == "Logro Promedio":
            objetivo = {"entity_field": ["Año", "Curso", "Nombre"], "entity_normalize": ["Nombre"]}
            if any(f.get(k) != v for k, v in objetivo.items()):
                f.update(copy.deepcopy(objetivo))
                notas.append("Logro Promedio: agrupa por Año+Curso+Nombre con entity_normalize")
        nuevos.append(f)
    derivados[:] = nuevos
    for s in pasos:
        if "Nombre_Norm" in (s.get("description") or ""):
            s["description"] = s["description"].replace("Nombre_Norm", "Nombre (texto original)")

    # 3. Establecimiento canónico
    ya = {s["params"]["input_key"] for s in pasos
          if s["step"] == "ModifyColumnValues" and MARCA in (s.get("description") or "")}
    resultado = []
    for s in pasos:
        resultado.append(s)
        out = (s.get("params") or {}).get("output_key")
        if out in OBJETIVOS and s["step"] == OBJETIVOS[out]:
            if out in ya:
                notas.append(f"{out}: canonización ya existía, no se duplica")
            else:
                resultado.append(paso_canonico(out))
                notas.append(f"{out}: insertado ModifyColumnValues tras {s['step']}")
    cfg["pipeline"] = resultado
    return cfg, notas


def verificar(cfg: dict) -> None:
    pasos = cfg["pipeline"]
    mios = [s for s in pasos if s["step"] == "ModifyColumnValues" and MARCA in (s.get("description") or "")]
    assert len(mios) == 2, f"se esperaban 2 pasos de canonización, hay {len(mios)}"
    for s in mios:
        idx = pasos.index(s)
        assert (pasos[idx - 1].get("params") or {}).get("output_key") == s["params"]["input_key"], \
            f"la canonización de {s['params']['input_key']} no quedó pegada a su productor"
    derivados = _derivados_estudiantes(pasos)
    kinds = [f["kind"] for f in derivados]
    assert "normalize_name" not in kinds, "quedó un normalize_name"
    assert any(f["kind"] == "copy" and f["name"] == "Nombre" for f in derivados), "falta copy → Nombre"
    logro = next(f for f in derivados if f["kind"] == "row_mean_dynamic")
    assert logro.get("value_map") == VALUE_MAP
    assert all(c in logro["exclude_columns"] for c in EXCLUIR_EXTRA)
    assert "Nombre_Norm" not in json.dumps(cfg), "quedó una referencia a Nombre_Norm"
    metricas = sorted(s["params"]["metric_id"] for s in pasos if s["step"] == "SaveToMetric")
    assert metricas == [6, 7], f"métricas destino: {metricas}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--respaldo", help="guarda aquí la config previa (JSON) antes de escribir")
    ap.add_argument("--salida", help="guarda aquí la config resultante (JSON)")
    args = ap.parse_args()

    from backend.database import SessionLocal
    from backend.models import Pipeline

    db = SessionLocal()
    try:
        p = db.query(Pipeline).filter(Pipeline.pipeline_id == PIPELINE_ID, Pipeline.org_id == ORG).first()
        if not p:
            print(f"ERROR: no existe el pipeline {PIPELINE_ID}")
            return 2
        previo = json.loads(p.config_json)
        cfg, notas = transformar(previo)
        verificar(cfg)

        print(f"Pipeline {PIPELINE_ID}: '{p.pipeline}'   pasos {len(previo['pipeline'])} -> {len(cfg['pipeline'])}")
        for n in notas or ["sin cambios (ya estaba normalizado)"]:
            print(f"  · {n}")
        for i, s in enumerate(cfg["pipeline"], 1):
            pr = s.get("params") or {}
            io_ = f"{pr.get('input_key', '-')} -> {pr.get('output_key', pr.get('metric_id', '-'))}"
            print(f"   {i:2d}. {s['step']:22s} {io_}")
        if args.salida:
            Path(args.salida).write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

        if args.dry_run or not notas:
            print("\nNo se escribió nada." if args.dry_run else "\nNada que aplicar.")
            return 0
        if args.respaldo:
            Path(args.respaldo).write_text(json.dumps(previo, ensure_ascii=False, indent=2), encoding="utf-8")
        p.config_json = json.dumps(cfg, ensure_ascii=False, indent=2)
        db.commit()
        print("\nAplicado.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
