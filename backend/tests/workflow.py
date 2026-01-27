import os
from pathlib import Path

# Se importa rgenerator, Step, RunContext
from rgenerator.etl.core.step import Step
from rgenerator.etl.core.context import RunContext

# Se agregan los pasos al pipeline
from rgenerator.etl.core.pipeline_steps import (
    InitRun,
    LoadConfig,
    DiscoverInputs,
    RunExcelETL,
    EnrichWithContext,
    ExportConsolidatedExcel,
    DeleteTempFiles)


# Contexto y Pipeline para Simce Lenguaje

simce_context = RunContext(
    evaluation="simce", 
    run_id="test_id", 
    base_dir=Path(".") / "backend" / "tests" 
)
pipeline_simce_lenguaje = []

# InitRun
step = InitRun(
        run_id="simce_estudiantes_lenguaje",
        evaluation="simce",
        year=2025,
        asignatura="Lenguaje",
        inputs_dir=simce_context.base_dir / "input_test" / "inputs" / "Lenguaje" / "inputs",
    )
pipeline_simce_lenguaje.append(step)

# LoadConfig
step = LoadConfig(config_path=simce_context.base_dir / "config_dir/simce_estudiantes_lenguaje.json")
pipeline_simce_lenguaje.append(step)

# DiscoverInputs
step = DiscoverInputs(
    rules={
        "estudiantes": {
            "extension": ".xlsx", 
            "contains": "Resultados",
        },
        "preguntas": {
            "extension": ".xlsx", 
            "contains": "ReportePregunta",
        },
        "habilidades": {
            "extension": ".xlsx", 
            "contains": "habilidades",
        },
        })
pipeline_simce_lenguaje.append(step)

# RunExcelETL

step = RunExcelETL("estudiantes", "df_consolidado_estudiantes")
pipeline_simce_lenguaje.append(step)

# EnrichWithContext

step = EnrichWithContext(
    "df_consolidado_estudiantes", 
    "df_enriched_estudiantes"
    )
pipeline_simce_lenguaje.append(step)

# ExportConsolidatedExcel

step = ExportConsolidatedExcel("df_enriched_estudiantes", "consolidado_estudiantes.xlsx")
pipeline_simce_lenguaje.append(step)

for step in pipeline_simce_lenguaje:
    step.run(simce_context)
