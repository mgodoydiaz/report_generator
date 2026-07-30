"""Tests del step EnrichWithLookup.

Regresión principal: cuando `left_on` y `right_on` se llaman IGUAL, pandas
colapsa las dos llaves en UNA sola columna del resultado. El paso borraba esa
columna creyendo que era la copia del lado derecho y se llevaba puesta la
llave del DataFrame principal. Ese bug hizo que la carga SIMCE de mayo 2026
guardara 260 filas sin la dimensión `Pregunta`.
"""
from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from backend.rgenerator.core.etl_steps import EnrichWithLookup


def _ctx(artifacts: dict):
    return SimpleNamespace(artifacts=dict(artifacts), params={}, last_artifact_key=None,
                           last_step=None)


@pytest.mark.unit
def test_llave_homonima_sobrevive_al_merge():
    """left_on == right_on: la llave debe seguir en el resultado."""
    ctx = _ctx({
        "preguntas": pd.DataFrame({"Pregunta": [1, 2, 3], "Logro": [0.1, 0.2, 0.3]}),
        "habilidades": pd.DataFrame({
            "Pregunta": [1, 2, 3],
            "Habilidad": ["Localizar", "Interpretar", "Reflexionar"],
            "Eje Temático": ["TMC", "TMC", "TMCFA"],
        }),
    })
    EnrichWithLookup(
        input_key="preguntas",
        lookup_key="habilidades",
        left_on="Pregunta",
        right_on="Pregunta",
        columns=["Habilidad", "Eje Temático"],
        output_key="preguntas",
        how="left",
    ).run(ctx)

    df = ctx.artifacts["preguntas"]
    assert "Pregunta" in df.columns, "la llave del DataFrame principal se perdió"
    assert df["Pregunta"].tolist() == [1, 2, 3]
    assert df["Habilidad"].tolist() == ["Localizar", "Interpretar", "Reflexionar"]
    assert df["Eje Temático"].tolist() == ["TMC", "TMC", "TMCFA"]


@pytest.mark.unit
def test_llave_derecha_distinta_si_se_descarta():
    """left_on != right_on y right_on no pedido: se limpia la llave derecha."""
    ctx = _ctx({
        "estudiantes": pd.DataFrame({"CursoID": ["a", "b"], "Nombre": ["Ana", "Beto"]}),
        "cursos": pd.DataFrame({"ID_Curso": ["a", "b"], "Nivel": ["II", "III"]}),
    })
    EnrichWithLookup(
        input_key="estudiantes",
        lookup_key="cursos",
        left_on="CursoID",
        right_on="ID_Curso",
        columns=["Nivel"],
        output_key="salida",
        how="left",
    ).run(ctx)

    df = ctx.artifacts["salida"]
    assert "ID_Curso" not in df.columns
    assert "CursoID" in df.columns
    assert df["Nivel"].tolist() == ["II", "III"]


@pytest.mark.unit
def test_llave_homonima_pedida_en_columns():
    """Pedir la llave explícitamente en `columns` también la conserva."""
    ctx = _ctx({
        "preguntas": pd.DataFrame({"Pregunta": [1, 2], "Logro": [0.5, 0.6]}),
        "habilidades": pd.DataFrame({"Pregunta": [1, 2], "Habilidad": ["X", "Y"]}),
    })
    EnrichWithLookup(
        input_key="preguntas",
        lookup_key="habilidades",
        left_on="Pregunta",
        right_on="Pregunta",
        columns=["Pregunta", "Habilidad"],
        output_key="preguntas",
        how="left",
    ).run(ctx)

    df = ctx.artifacts["preguntas"]
    assert df["Pregunta"].tolist() == [1, 2]
    assert df["Habilidad"].tolist() == ["X", "Y"]


@pytest.mark.unit
def test_join_con_on_conserva_la_llave():
    """El camino `on=` (misma columna en ambos lados) nunca dropea la llave."""
    ctx = _ctx({
        "preguntas": pd.DataFrame({"Pregunta": [1, 2], "Logro": [0.5, 0.6]}),
        "habilidades": pd.DataFrame({"Pregunta": [1, 2], "Habilidad": ["X", "Y"]}),
    })
    EnrichWithLookup(
        input_key="preguntas",
        lookup_key="habilidades",
        on="Pregunta",
        columns=["Pregunta", "Habilidad"],
        output_key="preguntas",
        how="left",
    ).run(ctx)

    assert ctx.artifacts["preguntas"]["Pregunta"].tolist() == [1, 2]
