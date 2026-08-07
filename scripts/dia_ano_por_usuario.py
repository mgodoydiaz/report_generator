# -*- coding: utf-8 -*-
"""
dia_ano_por_usuario.py
======================
Hace que el pipeline DIA **pregunte el año** en vez de guardarlo fijo en 2026.

Situacion previa (pipeline 21, 11 pasos):
  - paso 2  EnrichWithUserInput (mode once) pedia solo Hito y Asignatura.
  - pasos 6 y 7  EnrichWithContext con `context_mapping {"Año": 2026}`, uno por
    cada artifact (estudiantes y preguntas). Ademas de fijar el año, esos pasos
    renombraban el artifact: `*_raw` -> `*_enriched`.

Cambios:
  1. Se agrega `Año` al `enrich_data` del paso 2, **sin `options`**, para que sea
     un campo de texto escribible (no un desplegable). Default "2026".
  2. Se eliminan los dos `EnrichWithContext`.
  3. Los `ApplyDerivedFields` pasan a leer `*_raw` en vez de `*_enriched`.

Por que eliminarlos y no solo sacarles el año: si `context_mapping` queda vacio,
`EnrichWithContext` cae a un fallback que busca `enrich_data` en el spec o en
`ctx.params` global (etl_steps.py:565-580). El DIA no carga ningun spec, asi que
hoy no inyectaria nada — pero es una bomba de tiempo: cualquier cambio futuro que
deje un `enrich_data` global se aplicaria aca sin que nadie lo pida.

El año lo aplican `RunExcelETL` (etl_steps.py:281) y `RunDIAPDFExtraction`
(pdf_steps.py:347), que leen `ctx.user_inputs["enrich_global"]` y agregan las
columnas a sus DataFrames. Por eso el valor llega igual sin los pasos borrados.

Idempotente. Uso:
    docker cp scripts/dia_ano_por_usuario.py report_generator-backend-1:/tmp/d.py
    docker exec -e PYTHONPATH=/app report_generator-backend-1 sh -lc 'cd /app && python /tmp/d.py --dry-run'
"""
from __future__ import annotations

import argparse
import json

PIPELINE_ID = 21
ORG = 1
CAMPO_ANIO = {"key": "Año", "label": "Año", "val": "2026", "user_input": True}
RENOMBRES = {"estudiantes_enriched": "estudiantes_raw", "preguntas_enriched": "preguntas_raw"}


def transformar(cfg: dict) -> tuple[dict, list[str]]:
    notas = []
    pasos = cfg["pipeline"]

    # 1. agregar el campo Año al paso que pregunta
    for s in pasos:
        if s["step"] != "EnrichWithUserInput":
            continue
        campos = s["params"].setdefault("enrich_data", [])
        if any(f.get("key") == "Año" for f in campos):
            notas.append("el campo 'Año' ya estaba en EnrichWithUserInput")
        else:
            campos.append(dict(CAMPO_ANIO))
            notas.append("agregado el campo 'Año' (texto libre) a EnrichWithUserInput")

    # 2. eliminar los EnrichWithContext que solo fijaban el año
    quedan = []
    for s in pasos:
        if (s["step"] == "EnrichWithContext"
                and list((s["params"].get("context_mapping") or {}).keys()) == ["Año"]):
            notas.append(f"eliminado EnrichWithContext {s['params'].get('input_key')} "
                         f"-> {s['params'].get('output_key')} (fijaba Año)")
            continue
        quedan.append(s)
    cfg["pipeline"] = quedan

    # 3. reconectar los consumidores a los artifacts *_raw
    for s in quedan:
        ik = s.get("params", {}).get("input_key")
        if ik in RENOMBRES:
            s["params"]["input_key"] = RENOMBRES[ik]
            notas.append(f"{s['step']}: input_key {ik} -> {RENOMBRES[ik]}")
    return cfg, notas


def verificar(cfg: dict) -> None:
    pasos = cfg["pipeline"]
    nombres = [s["step"] for s in pasos]

    eui = [s for s in pasos if s["step"] == "EnrichWithUserInput"]
    assert len(eui) == 1, f"se esperaba 1 EnrichWithUserInput, hay {len(eui)}"
    campos = eui[0]["params"]["enrich_data"]
    anio = [f for f in campos if f.get("key") == "Año"]
    assert len(anio) == 1, "debe haber exactamente un campo 'Año'"
    assert anio[0].get("user_input") is True, "'Año' debe tener user_input: true"
    assert "options" not in anio[0], "'Año' NO debe tener options (tiene que ser escribible)"
    assert eui[0]["params"].get("mode") == "once", "el modo debe seguir siendo 'once'"

    assert not any(s["step"] == "EnrichWithContext" for s in pasos), \
        "quedo algun EnrichWithContext"

    # ningun paso puede seguir apuntando a un artifact que ya no se produce
    producidos = {s["params"].get("output_key") for s in pasos if s.get("params")}
    for s in pasos:
        ik = s.get("params", {}).get("input_key")
        if ik and ik.endswith("_enriched"):
            raise AssertionError(f"{s['step']} sigue leyendo '{ik}', que ya nadie produce")
        if ik and ik.endswith(("_raw", "_derived")) and ik not in producidos:
            raise AssertionError(f"{s['step']} lee '{ik}' pero ningun paso lo produce")

    # los destinos no cambian
    metricas = sorted(s["params"]["metric_id"] for s in pasos if s["step"] == "SaveToMetric")
    assert metricas == [6, 7], f"las metricas destino cambiaron: {metricas}"
    assert nombres.count("ApplyDerivedFields") == 2, "deben quedar los 2 ApplyDerivedFields"


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
            print(f"ERROR: no existe el pipeline {PIPELINE_ID}")
            return 2

        cfg = json.loads(p.config_json)
        antes = len(cfg["pipeline"])
        cfg, notas = transformar(cfg)
        verificar(cfg)

        print(f"Pipeline {PIPELINE_ID}: '{p.pipeline}'   pasos {antes} -> {len(cfg['pipeline'])}\n")
        for n in notas:
            print(f"  · {n}")

        print("\n  campos que pedira al usuario:")
        for f in [s for s in cfg["pipeline"] if s["step"] == "EnrichWithUserInput"][0]["params"]["enrich_data"]:
            tipo = f"lista {f['options']}" if f.get("options") else "texto libre"
            print(f"     - {f['key']:12s} default={f['val']!r:14s} {tipo}")

        print("\n  pipeline resultante:")
        for i, s in enumerate(cfg["pipeline"], 1):
            pr = s.get("params", {}) or {}
            io_ = ""
            if pr.get("input_key") or pr.get("output_key"):
                io_ = f"{pr.get('input_key','-')} -> {pr.get('output_key','-')}"
            if s["step"] == "SaveToMetric":
                io_ = f"{pr.get('input_key')} -> metrica {pr.get('metric_id')}"
            print(f"   {i:2d}. {s['step']:22s} {io_}")

        if args.dry_run:
            print("\n--dry-run: no se escribio nada.")
            return 0

        p.config_json = json.dumps(cfg, ensure_ascii=False, indent=2)
        db.commit()
        print("\nAplicado.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
