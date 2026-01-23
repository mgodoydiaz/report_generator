from __future__ import annotations

from pathlib import Path

import pandas as pd

from rgenerator.etl.core.context import RunContext
from rgenerator.etl.core.pipeline_steps import (
    InitRun,
    LoadConfig,
    DiscoverInputs,
    RunExcelETL,
    EnrichWithContext,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _make_context(base_dir: Path) -> RunContext:
    return RunContext(evaluation="simce", run_id="test", base_dir=base_dir)


def test_init_run_creates_context_dirs(tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    step = InitRun(
        evaluation="simce",
        base_dir=tmp_path,
        year=2025,
        asignatura="Lenguaje",
        numero_prueba=5,
    )

    step.run(ctx)

    assert ctx.status == "RUNNING"
    assert ctx.params["year"] == 2025
    assert ctx.params["asignatura"] == "Lenguaje"
    assert ctx.params["numero_prueba"] == 5
    assert ctx.work_dir.exists()
    assert ctx.inputs_dir.exists()
    assert ctx.aux_dir.exists()
    assert ctx.outputs_dir.exists()


def test_load_config_parses_lists(tmp_path: Path) -> None:
    config_text = "\n".join(
        [
            "tipo_etl = estudiantes",
            "nombre_salida = salida.xlsx",
            "columnas_relevantes = Nombre,RUT,Curso",
        ]
    )
    config_path = tmp_path / "config.txt"
    config_path.write_text(config_text, encoding="utf-8")

    ctx = _make_context(tmp_path)
    ctx.outputs_dir = tmp_path / "outputs"
    ctx.outputs_dir.mkdir(parents=True, exist_ok=True)

    step = LoadConfig(config_path=config_path)
    step.run(ctx)

    assert ctx.params["tipo_etl"] == "estudiantes"
    assert ctx.params["nombre_salida"] == "salida.xlsx"
    assert ctx.params["columnas_relevantes"] == ["Nombre", "RUT", "Curso"]
    assert ctx.outputs["excel_salida"] == ctx.outputs_dir / "salida.xlsx"


def test_discover_inputs_classifies_files() -> None:
    base_dir = _repo_root() / "backend" / "tests" / "input_test"
    ctx = _make_context(base_dir)
    ctx.inputs_dir = base_dir / "inputs" / "Lenguaje" / "inputs"

    step = DiscoverInputs(
        rules={
            "estudiantes": {
                "extension": ".xlsx",
                "contains": "Resultados",
                "exclude_prefix": "~$",
            },
            "preguntas": {
                "extension": ".xlsx",
                "contains": "ReportePregunta",
                "exclude_prefix": "~$",
            },
        }
    )
    step.run(ctx)

    assert "estudiantes" in ctx.inputs
    assert "preguntas" in ctx.inputs
    assert len(ctx.inputs["estudiantes"]) > 0
    assert len(ctx.inputs["preguntas"]) > 0


def test_run_excel_etl_consolidates() -> None:
    base_dir = _repo_root() / "backend" / "tests" / "input_test"
    inputs_dir = base_dir / "inputs" / "Lenguaje" / "inputs"
    files = sorted(p for p in inputs_dir.glob("*.xlsx") if "Resultados" in p.name)

    ctx = _make_context(base_dir)
    ctx.inputs["estudiantes"] = files[:2]
    ctx.params["header_row"] = 23

    step = RunExcelETL(input_key="estudiantes", output_key="df_estudiantes_raw")
    step.run(ctx)

    df = ctx.artifacts.get("df_estudiantes_raw")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty


def test_enrich_with_context_adds_columns_and_filters() -> None:
    ctx = _make_context(Path.cwd())
    ctx.params.update(
        {
            "asignatura": "Lenguaje",
            "mes": "Noviembre",
            "numero_prueba": 5,
            "columnas_relevantes": ["Nombre", "RUT", "Curso", "Puntaje"],
        }
    )
    ctx.artifacts["df_estudiantes_raw"] = pd.DataFrame(
        [
            {
                "Nombre": "Alumno 1",
                "RUT": "1-9",
                "Curso": "2A",
                "Puntaje": 100,
                "Rend": 0.8,
            }
        ]
    )

    step = EnrichWithContext(
        input_key="df_estudiantes_raw",
        output_key="df_estudiantes_clean",
        context_mapping={
            "Asignatura": "asignatura",
            "Mes": "mes",
            "Numero_Prueba": "numero_prueba",
        },
        columns_param_key="columnas_relevantes",
        cleaning_func=None,
    )
    step.run(ctx)

    df = ctx.artifacts.get("df_estudiantes_clean")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "Asignatura" in df.columns
    assert "Mes" in df.columns
    assert "Numero_Prueba" in df.columns
