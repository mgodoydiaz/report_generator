# -*- coding: utf-8 -*-
"""
crear_pipeline_emn_importables.py
=================================
Crea el pipeline **"SIMCE Panguipulli (Aptus) - Archivos importables"**: toma los 3 Excel crudos
que se descargan de Aptus y deja 3 artifacts descargables, ya transformados y
listos para subir por `Valores -> Importar` a las metricas 24 / 25 / 26.

Diferencia con el pipeline 26 ("SIMCE Panguipulli (Aptus) - Carga directa"):

    26   -> RunExcelETL -> ModifyColumnValues -> EnrichWithContext -> SaveToMetric
            (escribe directo en la DB, sin paso previo de revision)

    este -> RunExcelETL -> ModifyColumnValues -> EnrichWithContext
            (termina en el artifact; el usuario revisa y luego importa)

Se deriva del `config_json` del pipeline 26 leido de la DB, de modo que las
transformaciones (derivacion de Mes / N Prueba / Asignatura / Curso / Nombre y
la conversion de coma a punto decimal) sean IDENTICAS y no se dupliquen a mano.

Cambios aplicados sobre esa base:
  1. `SaveToMetric` x3  -> eliminados.
  2. `multiple: false` -> `true` en los 3 `file_specs`: permite consolidar varios
     meses en una sola corrida (RunExcelETL recibe una lista y la concatena).
  3. output_key de cada grupo -> `Importar_metric{N}_{tipo}`, porque el endpoint
     `GET /api/pipelines/{id}/artifact/{key}` nombra la descarga como
     `{artifact_key}.xlsx`. Asi el archivo bajado dice a que metrica va.
  4. `EnrichWithContext` recibe `context_mapping` EXPLICITO.
     Por que: con `config_key`, `LoadConfigFromSpec` guarda `enrich_data` solo en
     `ctx.params["_config"][config_key]` y nunca en el global (init_steps.py:228).
     `EnrichWithContext` lo busca como `_config[input_key]` con fallback al global
     (etl_steps.py:569-570). Al renombrar las claves, ese lookup fallaria y el
     `Establecimiento` se perderia EN SILENCIO. Pasarlo explicito lo evita.

El script NO toca la base de datos: lee el `config_json` del pipeline 26 desde un
archivo y escribe el nuevo `config_json` en otro archivo. El insert se hace aparte
con `docker exec ... psql`, porque el `DATABASE_URL` del `.env` apunta a
localhost:5432 (instancia stale) y la DB canonica es el contenedor Docker.

Para obtener el config de origen:
    docker exec report_generator-db-1 psql -U mgodoy -d rgenerator_dev -t -A \
        -c "SELECT config_json FROM pipelines WHERE pipeline_id=26" > origen.json

Uso:
    python scripts/crear_pipeline_emn_importables.py \
        --config-origen origen.json --salida nuevo.json

Y luego el insert (dollar-quoting para no pelear con el escapado):

    INSERT INTO pipelines (pipeline, description, config_json, hidden, org_id)
    SELECT $d$SIMCE Panguipulli (Aptus) - Archivos importables$d$, $d$<descripcion>$d$,
           $json$<contenido de nuevo.json>$json$, false, 1
    WHERE NOT EXISTS (SELECT 1 FROM pipelines
                      WHERE pipeline = $d$SIMCE Panguipulli (Aptus) - Archivos importables$d$ AND org_id = 1);
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

PIPELINE_ORIGEN = 26
NOMBRE = "SIMCE Panguipulli (Aptus) - Archivos importables"
DESCRIPCION = (
    "Transforma los 3 informes crudos de Aptus (Estudiante, OA, Habilidad) y deja "
    "3 archivos descargables listos para subir por Valores -> Importar a las metricas "
    "24, 25 y 26. NO escribe en la base de datos: sirve para revisar antes de cargar, "
    "y admite varios meses en una sola corrida. Para cargar directo, usar 'SIMCE Panguipulli (Aptus) - Carga directa'."
)

# grupo -> (metric_id de destino, sufijo del artifact)
DESTINOS = {
    "estudiantes": (24, "estudiante"),
    "oa": (25, "oa"),
    "habilidad": (26, "habilidad"),
}

ESTABLECIMIENTO = "Panguipulli"

# Rotulos de las 3 pausas de archivos. Se reescriben (en vez de anexar al del
# pipeline 26) porque los del 26 dicen "(1 archivo del mes)" y aca si se admiten
# varios meses: anexar dejaria un rotulo contradictorio.
ETIQUETAS = {
    "estudiantes": "Informe Estudiante",
    "oa": "Informe OA",
    "habilidad": "Informe Habilidad",
}


def artifact_key(grupo: str) -> str:
    metric_id, sufijo = DESTINOS[grupo]
    return f"Importar_metric{metric_id}_{sufijo}"


def construir_config(config_origen: dict) -> dict:
    cfg = copy.deepcopy(config_origen)

    cfg["pipeline_metadata"] = {
        "name": NOMBRE,
        "description": DESCRIPCION,
        "input": "EXCEL",
        "output": "XLSX",
    }
    cfg.setdefault("context", {})["evaluation"] = "emn_aptus_export"

    nuevos_steps = []
    for step in cfg.get("pipeline", []):
        nombre_step = step.get("step")
        params = step.setdefault("params", {})

        # 1. fuera los SaveToMetric
        if nombre_step == "SaveToMetric":
            continue

        if nombre_step == "InitRun":
            params["evaluation"] = "emn_aptus_export"

        # 2. permitir varios meses por corrida
        elif nombre_step == "RequestUserFiles":
            for spec in params.get("file_specs", []):
                spec["multiple"] = True
                grupo = spec.get("id")
                if grupo in DESTINOS:
                    spec["label"] = f"{ETIQUETAS[grupo]} — uno o varios meses"

        # 3. redirigir la salida al nombre final.
        #    input_key se mantiene como el rol del archivo SOLO en RunExcelETL,
        #    porque de ahi resuelve la config del spec (_config[input_key]).
        elif nombre_step == "RunExcelETL":
            grupo = params.get("input_key")
            if grupo in DESTINOS:
                params["output_key"] = artifact_key(grupo)

        elif nombre_step == "ModifyColumnValues":
            grupo = params.get("input_key")
            if grupo in DESTINOS:
                params["input_key"] = artifact_key(grupo)
                params["output_key"] = artifact_key(grupo)

        # 4. context_mapping explicito: ver docstring
        elif nombre_step == "EnrichWithContext":
            grupo = params.get("input_key")
            if grupo in DESTINOS:
                params["input_key"] = artifact_key(grupo)
                params["output_key"] = artifact_key(grupo)
                params["context_mapping"] = {"Establecimiento": ESTABLECIMIENTO}
                step["description"] = (
                    f"Inyecta Establecimiento={ESTABLECIMIENTO} (explicito, no via spec)"
                )

        nuevos_steps.append(step)

    cfg["pipeline"] = nuevos_steps
    return cfg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config-origen", type=Path, required=True,
                    help="Archivo con el config_json del pipeline 26.")
    ap.add_argument("--salida", type=Path, required=True,
                    help="Donde escribir el config_json nuevo.")
    args = ap.parse_args()

    origen_raw = args.config_origen.read_text(encoding="utf-8").strip()
    if not origen_raw:
        print(f"ERROR: {args.config_origen} esta vacio.")
        return 2

    cfg_origen = json.loads(origen_raw)
    if cfg_origen.get("pipeline_metadata", {}).get("name") != "SIMCE Panguipulli (Aptus) - Carga directa":
        print("ERROR: el config de origen no es el del pipeline 26 'SIMCE Panguipulli (Aptus) - Carga directa'.")
        return 2

    cfg = construir_config(cfg_origen)

    # --- chequeos: que el resultado sea exactamente lo que se busca ---
    steps = [s["step"] for s in cfg["pipeline"]]
    assert "SaveToMetric" not in steps, "quedo un SaveToMetric: escribiria en la DB"

    enrich = [s for s in cfg["pipeline"] if s["step"] == "EnrichWithContext"]
    assert len(enrich) == 3, f"se esperaban 3 EnrichWithContext, hay {len(enrich)}"
    salidas = {s["params"]["output_key"] for s in enrich}
    assert salidas == {artifact_key(g) for g in DESTINOS}, \
        f"artifacts finales inesperados: {salidas}"
    for s in enrich:
        assert s["params"]["context_mapping"] == {"Establecimiento": ESTABLECIMIENTO}, \
            "falta el context_mapping explicito"

    for s in cfg["pipeline"]:
        if s["step"] == "RequestUserFiles":
            for spec in s["params"]["file_specs"]:
                assert spec["multiple"] is True, f"file_spec {spec['id']} no admite varios meses"

    # las transformaciones deben venir intactas del pipeline 26
    orig_tr = [s["params"]["transformations"] for s in cfg_origen["pipeline"]
               if s["step"] == "ModifyColumnValues"]
    nuevo_tr = [s["params"]["transformations"] for s in cfg["pipeline"]
                if s["step"] == "ModifyColumnValues"]
    assert orig_tr == nuevo_tr, "las transformaciones cambiaron respecto al pipeline 26"

    args.salida.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Steps ({len(steps)}):")
    for i, s in enumerate(steps, 1):
        print(f"  {i:2d}. {s}")
    print(f"\nArtifacts finales descargables: {sorted(salidas)}")
    print(f"Transformaciones identicas al pipeline 26: OK ({len(nuevo_tr)} bloques)")
    print(f"\nEscrito: {args.salida} ({args.salida.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
