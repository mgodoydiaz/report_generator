"""Tests del step ApplyDerivedFields.

Cobertura: integración con el ctx del pipeline (artifacts, params,
last_artifact_key). El engine ya está cubierto por su propia suite.
"""
from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from rgenerator.core.etl_steps import ApplyDerivedFields


def _make_ctx(artifacts: dict | None = None, params: dict | None = None, last_key: str | None = None):
    """Crea un ctx mínimo compatible con la API que usa el step."""
    ctx = SimpleNamespace(
        artifacts=dict(artifacts or {}),
        params=dict(params or {}),
        last_artifact_key=last_key,
        last_step=None,
    )
    return ctx


@pytest.fixture
def df_basico():
    return pd.DataFrame([
        {"Rut": "R1", "Numero_Prueba": 1, "Rend": 0.40},
        {"Rut": "R1", "Numero_Prueba": 2, "Rend": 0.50},
        {"Rut": "R2", "Numero_Prueba": 1, "Rend": 0.60},
        {"Rut": "R2", "Numero_Prueba": 2, "Rend": 0.70},
    ])


def test_aplica_derived_fields_desde_init(df_basico):
    ctx = _make_ctx(artifacts={"df_in": df_basico}, last_key="df_in")
    step = ApplyDerivedFields(
        input_key="df_in",
        derived_fields=[
            {"kind": "agg", "name": "Logro_Promedio",
             "value_field": "Rend", "entity_field": "Rut", "agg": "mean"},
        ],
    )
    step.run(ctx)
    out = ctx.artifacts["df_derived_df_in"]
    assert "Logro_Promedio" in out.columns
    r1 = out[out["Rut"] == "R1"]["Logro_Promedio"].iloc[0]
    assert r1 == pytest.approx(0.45)
    # last_artifact_key actualizado
    assert ctx.last_artifact_key == "df_derived_df_in"


def test_aplica_derived_fields_desde_ctx_params(df_basico):
    ctx = _make_ctx(
        artifacts={"df_in": df_basico},
        params={"derived_fields": [
            {"kind": "delta", "name": "Mejora",
             "value_field": "Rend", "entity_field": "Rut", "time_field": "Numero_Prueba"},
        ]},
        last_key="df_in",
    )
    step = ApplyDerivedFields()  # sin args, deriva todo del ctx
    step.run(ctx)
    out = ctx.artifacts["df_derived_df_in"]
    assert "Mejora" in out.columns
    assert out[out["Rut"] == "R1"]["Mejora"].iloc[0] == pytest.approx(0.10)


def test_passthrough_si_no_hay_derived_fields(df_basico):
    ctx = _make_ctx(artifacts={"df_in": df_basico}, last_key="df_in")
    step = ApplyDerivedFields(input_key="df_in")  # sin derived_fields
    step.run(ctx)
    out = ctx.artifacts["df_derived_df_in"]
    # Sin cambios estructurales, mismas columnas
    assert list(out.columns) == list(df_basico.columns)
    assert len(out) == len(df_basico)


def test_dataframe_vacio_no_falla():
    ctx = _make_ctx(artifacts={"df_in": pd.DataFrame()}, last_key="df_in")
    step = ApplyDerivedFields(
        input_key="df_in",
        derived_fields=[
            {"kind": "agg", "name": "X", "value_field": "Rend", "entity_field": "Rut"},
        ],
    )
    step.run(ctx)  # no debe lanzar
    out = ctx.artifacts["df_derived_df_in"]
    assert isinstance(out, pd.DataFrame)
    assert out.empty


def test_encadenamiento_de_dos_funciones(df_basico):
    ctx = _make_ctx(artifacts={"df_in": df_basico}, last_key="df_in")
    step = ApplyDerivedFields(
        input_key="df_in",
        derived_fields=[
            {"kind": "agg", "name": "Logro_Promedio",
             "value_field": "Rend", "entity_field": "Rut", "agg": "mean"},
            {"kind": "slope", "name": "Avance",
             "value_field": "Rend", "entity_field": "Rut",
             "time_field": "Numero_Prueba"},
        ],
    )
    step.run(ctx)
    out = ctx.artifacts["df_derived_df_in"]
    assert "Logro_Promedio" in out.columns
    assert "Avance" in out.columns


def test_input_key_no_resolvable_lanza():
    ctx = _make_ctx(artifacts={}, last_key=None)
    step = ApplyDerivedFields()
    with pytest.raises(ValueError, match="input_key"):
        step.run(ctx)
