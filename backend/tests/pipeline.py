from __future__ import annotations

from pathlib import Path

from rgenerator.etl.core.context import RunContext
from rgenerator.etl.core.pipeline_steps import (
    InitRun,
    LoadConfig,
    DiscoverInputs,
    RunExcelETL,
    EnrichWithContext,
)
from rgenerator.tooling.etl_tools import limpiar_columnas


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_context(base_dir: Path) -> RunContext:
    return RunContext(evaluation="simce", run_id="test", base_dir=base_dir)


def run_pipeline_estudiantes() -> RunContext:
    repo_root = _repo_root()
    base_dir = Path(__file__).resolve().parent / "input_test"
    config_path = repo_root / "config" / "simce_estudiantes_lenguaje.json"

    ctx = _build_context(base_dir)

    steps = [
        InitRun(
            evaluation="simce",
            base_dir=base_dir,
            year=2025,
            asignatura="Lenguaje",
            numero_prueba=5,
        ),
        LoadConfig(config_path=config_path),
    ]

    for step in steps:
        step.run(ctx)

    directorio_archivos = ctx.params.get("directorio_archivos")
    if directorio_archivos:
        ctx.inputs_dir = ctx.base_dir / "inputs" / Path(directorio_archivos)

    if "linea_header" in ctx.params and "header_row" not in ctx.params:
        ctx.params["header_row"] = int(ctx.params["linea_header"])

    discover = DiscoverInputs(
        rules={
            "estudiantes": {
                "extension": ".xlsx",
                "contains": "Resultados",
                "exclude_prefix": "~$",
            },
        }
    )
    print(f"Params de contexto: {ctx.params}")
    print()
    run_excel = RunExcelETL(input_key="estudiantes", output_key="df_estudiantes_raw")
    enrich = EnrichWithContext(
        input_key="df_estudiantes_raw",
        output_key="df_estudiantes_clean",
        context_mapping={
            "Asignatura": "asignatura",
            "Mes": "mes",
            "Numero_Prueba": "numero_prueba",
        },
        columns_param_key="columnas_relevantes",
        cleaning_func=limpiar_columnas,
    )

    for step in [discover, run_excel, enrich]:
        step.run(ctx)

    df_clean = ctx.artifacts.get("df_estudiantes_clean")
    assert df_clean is not None, "df_estudiantes_clean no fue generado"
    assert not df_clean.empty, "df_estudiantes_clean quedo vacio"

    return ctx


if __name__ == "__main__":
    run_pipeline_estudiantes()
    print("Pipeline test OK.")
