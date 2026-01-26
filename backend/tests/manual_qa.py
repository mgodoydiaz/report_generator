# %%
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


# %%
# Contexto y Pipeline para Simce Lenguaje
simce_context = RunContext(
    evaluation="simce", 
    run_id="test_id", 
    base_dir=Path(".") / "backend" / "tests" 
)
pipeline_simce_lenguaje = []

simce_context.show_attrs()

# %%
# InitRun
step = InitRun(
        run_id="simce_estudiantes_lenguaje",
        evaluation="simce",
        year=2025,
        asignatura="Lenguaje",
        inputs_dir=simce_context.base_dir / "input_test" / "inputs" / "Lenguaje" / "inputs",
    )
step.run(simce_context)


step.show_attrs()
print('-------')
simce_context.show_attrs()

# %%
# LoadConfig
step = LoadConfig(config_path=simce_context.base_dir / "config_dir/simce_estudiantes_lenguaje.json")

step.run(simce_context)

step.show_attrs()
print('-------')
simce_context.show_attrs()


# %%
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
os.system("cls" if os.name == "nt" else "clear")
step.run(simce_context)
step.show_attrs()
print('-------')
simce_context.show_attrs()

# %%
# RunExcelETL

step = RunExcelETL("estudiantes", "df_consolidado_estudiantes")
os.system("cls" if os.name == "nt" else "clear")
step.run(simce_context)
step.show_attrs()
print('-------')
simce_context.show_attrs()

# %%
# EnrichWithContext
os.system("cls" if os.name == "nt" else "clear")
step = EnrichWithContext(
    "df_consolidado_estudiantes", 
    "df_enriched_estudiantes"
    )

step.run(simce_context)
step.show_attrs()
print('-------')
simce_context.show_attrs()

# %%
# ExportConsolidatedExcel

step = ExportConsolidatedExcel("df_enriched_estudiantes", "consolidado_estudiantes.xlsx")
os.system("cls" if os.name == "nt" else "clear")
step.run(simce_context)
step.show_attrs()
print('-------')
simce_context.show_attrs()
