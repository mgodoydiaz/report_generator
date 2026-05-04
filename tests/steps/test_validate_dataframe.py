"""Tests del step ValidateDataframe."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from rgenerator.core.validate_steps import ValidateDataframe


def _make_ctx(artifacts: dict, params: dict | None = None, last_key: str | None = None):
    return SimpleNamespace(
        artifacts=dict(artifacts),
        params=dict(params or {}),
        last_artifact_key=last_key,
        last_step=None,
    )


@pytest.fixture
def df_valido():
    return pd.DataFrame([
        {"Logro": 0.45, "Curso": "1A", "Hito": "DIAGNOSTICO"},
        {"Logro": 0.80, "Curso": "II B", "Hito": "INTERMEDIO"},
    ])


def test_passthrough_sin_schema(df_valido):
    ctx = _make_ctx({"df": df_valido})
    step = ValidateDataframe(input_key="df")
    step.run(ctx)  # no schema → passthrough
    # El artifact original sigue ahí
    assert id(ctx.artifacts["df"]) == id(df_valido)


def test_validacion_ok_no_lanza(df_valido):
    ctx = _make_ctx({"df": df_valido})
    step = ValidateDataframe(
        input_key="df",
        schema={
            "required_columns": ["Logro", "Curso", "Hito"],
            "columns": {
                "Logro": {"type": "float", "min": 0, "max": 1, "nullable": False},
                "Hito": {"allowed": ["DIAGNOSTICO", "INTERMEDIO", "FINAL"]},
            },
        },
    )
    step.run(ctx)  # no debe lanzar


def test_required_columns_faltantes_strict_lanza():
    ctx = _make_ctx({"df": pd.DataFrame({"X": [1]})})
    step = ValidateDataframe(
        input_key="df",
        schema={"required_columns": ["Logro", "Curso"]},
    )
    with pytest.raises(ValueError, match="requeridas"):
        step.run(ctx)


def test_min_rows_strict_lanza():
    ctx = _make_ctx({"df": pd.DataFrame({"x": []})})
    step = ValidateDataframe(input_key="df", schema={"min_rows": 1})
    with pytest.raises(ValueError, match="Filas insuficientes"):
        step.run(ctx)


def test_nullable_false_detecta_nulls(df_valido):
    df = df_valido.copy()
    df.loc[0, "Logro"] = np.nan
    ctx = _make_ctx({"df": df})
    step = ValidateDataframe(
        input_key="df",
        schema={"columns": {"Logro": {"nullable": False}}},
    )
    with pytest.raises(ValueError, match="nulos"):
        step.run(ctx)


def test_rango_fuera_lanza():
    ctx = _make_ctx({"df": pd.DataFrame({"Logro": [0.5, 1.5, -0.1]})})
    step = ValidateDataframe(
        input_key="df",
        schema={"columns": {"Logro": {"min": 0, "max": 1}}},
    )
    with pytest.raises(ValueError, match="fuera de rango"):
        step.run(ctx)


def test_regex_no_match_lanza():
    ctx = _make_ctx({"df": pd.DataFrame({"Curso": ["1A", "BASURA"]})})
    step = ValidateDataframe(
        input_key="df",
        schema={"columns": {"Curso": {"type": "str", "regex": r"^[1-9I]+ ?[A-Z]?$"}}},
    )
    with pytest.raises(ValueError, match="regex"):
        step.run(ctx)


def test_allowed_values_no_match_lanza():
    ctx = _make_ctx({"df": pd.DataFrame({"Hito": ["DIAGNOSTICO", "FOO"]})})
    step = ValidateDataframe(
        input_key="df",
        schema={"columns": {"Hito": {"allowed": ["DIAGNOSTICO", "INTERMEDIO", "FINAL"]}}},
    )
    with pytest.raises(ValueError, match="no permitidos"):
        step.run(ctx)


def test_modo_warn_no_lanza(df_valido, capsys):
    df = df_valido.copy()
    df.loc[0, "Logro"] = 99
    ctx = _make_ctx({"df": df})
    step = ValidateDataframe(
        input_key="df",
        schema={"columns": {"Logro": {"max": 1}}},
        mode="warn",
    )
    step.run(ctx)  # no lanza, solo loguea
    out = capsys.readouterr().out
    assert "Validación falló" in out


def test_modo_invalido_lanza_en_init():
    with pytest.raises(ValueError, match="mode"):
        ValidateDataframe(input_key="df", mode="lalala")


def test_input_key_no_resolvable_lanza():
    ctx = _make_ctx({})
    step = ValidateDataframe(schema={"min_rows": 1})
    with pytest.raises(ValueError, match="input_key"):
        step.run(ctx)


def test_schema_desde_ctx_params(df_valido):
    ctx = _make_ctx(
        {"df": df_valido},
        params={"validation_schema": {"required_columns": ["Logro", "Curso", "Hito"]}},
    )
    step = ValidateDataframe(input_key="df")
    step.run(ctx)


def test_tipo_int_detecta_floats():
    ctx = _make_ctx({"df": pd.DataFrame({"x": [1, 2.5, 3]})})
    step = ValidateDataframe(
        input_key="df",
        schema={"columns": {"x": {"type": "int"}}},
    )
    with pytest.raises(ValueError, match="tipo 'int'"):
        step.run(ctx)


def test_step_registrado_en_pipeline_mapping():
    from rgenerator.tooling.pipeline_tools import STEP_MAPPING
    assert "ValidateDataframe" in STEP_MAPPING
