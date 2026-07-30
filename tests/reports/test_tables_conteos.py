"""Tests de `reports/tables.py`: conteos de alumnos y ausencia de `nan`.

Hallazgos del QA visual 2026-07-30:
    P0-12 `Alumnos` contaba filas (SIMCE decía 31 y los niveles sumaban 58)
    P0-3  la columna Estudiante salía `nan` y `Promedio Hito` salía `nan%`
    P0-4  la columna Avance salía `nan%` en el 100 % de las filas
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.rgenerator.reports import tables
from backend.rgenerator.reports.helpers import MARCA_SIN_DATO

pytestmark = pytest.mark.unit


# ── resumen_estadistico_basico ───────────────────────────────────────────

@pytest.fixture
def df_multiasignatura():
    """31 estudiantes de II A, cada uno con 2 filas (Lenguaje y Matemática)."""
    filas = []
    for i in range(31):
        for asignatura, rend in (("LENGUAJE", 0.4), ("MATEMATICA", 0.5)):
            filas.append({
                "Curso": "II A", "Asignatura": asignatura,
                "Rut": f"{i}-K", "Nombre": f"Alumno {i}", "Rend": rend,
            })
    return pd.DataFrame(filas)


def test_resumen_cuenta_estudiantes_distintos(df_multiasignatura):
    out = tables.resumen_estadistico_basico(
        df_multiasignatura, columna="Rend", agrupar_por="Curso",
    )
    assert len(df_multiasignatura) == 62
    assert out.loc[0, "Alumnos"] == 31


def test_resumen_una_fila_por_alumno_sin_cambios():
    df = pd.DataFrame({
        "Curso": ["III°C"] * 22 + ["IV°A"] * 30,
        "Nombre": [f"a{i}" for i in range(52)],
        "Puntaje": [40.0] * 52,
    })
    out = tables.resumen_estadistico_basico(
        df, columna="Puntaje", formato="number", agrupar_por="Curso",
    )
    assert out.set_index("Curso")["Alumnos"].to_dict() == {"III°C": 22, "IV°A": 30}


def test_resumen_sin_columna_de_identidad_cuenta_filas():
    df = pd.DataFrame({"Nivel": ["A", "A", "B"], "Logro": [0.1, 0.2, 0.3]})
    out = tables.resumen_estadistico_basico(
        df, columna="Logro", agrupar_por="Nivel",
    )
    assert out.set_index("Nivel")["Alumnos"].to_dict() == {"A": 2, "B": 1}


def test_resumen_columnas_esperadas(df_multiasignatura):
    out = tables.resumen_estadistico_basico(
        df_multiasignatura, columna="Rend", agrupar_por="Curso",
    )
    assert list(out.columns) == ["Curso", "Alumnos", "Promedio", "Minimo", "Maximo"]


def test_resumen_sin_valores_numericos_no_imprime_nan():
    df = pd.DataFrame({
        "Curso": ["II A", "II A"],
        "Nombre": ["a", "b"],
        "Rend": [np.nan, np.nan],
    })
    out = tables.resumen_estadistico_basico(df, columna="Rend", agrupar_por="Curso")
    assert out.loc[0, "Promedio"] == MARCA_SIN_DATO
    assert out.loc[0, "Minimo"] == MARCA_SIN_DATO


def test_resumen_ordena_grupo_temporal_cronologicamente():
    df = pd.DataFrame({
        "Mes": ["OCTUBRE", "ABRIL", "MAYO"],
        "Nombre": ["a", "b", "c"],
        "Rend": [0.6, 0.4, 0.5],
    })
    out = tables.resumen_estadistico_basico(df, columna="Rend", agrupar_por="Mes")
    assert out["Mes"].tolist() == ["ABRIL", "MAYO", "OCTUBRE"]


def test_resumen_ordena_grupo_no_temporal_alfabeticamente():
    df = pd.DataFrame({
        "Curso": ["II C", "II A", "II B"],
        "Nombre": ["a", "b", "c"],
        "Rend": [0.6, 0.4, 0.5],
    })
    out = tables.resumen_estadistico_basico(df, columna="Rend", agrupar_por="Curso")
    assert out["Curso"].tolist() == ["II A", "II B", "II C"]


# ── tabla_logro_por_alumno ───────────────────────────────────────────────

def test_logro_por_alumno_coalesce_nombre_norm():
    """DIA 2026: `Nombre` nulo con `Nombre_Norm` poblado → salía `nan`."""
    df = pd.DataFrame({
        "Curso": ["7 A", "7 A"],
        "Numero Lista": [None, 2],
        "Nombre": [None, "Beto"],
        "Nombre_Norm": ["ANA PEREZ", None],
        "Logro": [0.8, 0.4],
    })
    out = tables.tabla_logro_por_alumno(
        df,
        parametros={"Curso": "7 A"},
        sort_by="Logro",
        formatos={"Logro": "percent"},
        columnas=["Numero Lista", "Nombre", "Logro"],
        columnas_renombrar={"Numero Lista": "N° Lista", "Nombre": "Estudiante"},
    )
    assert out["Estudiante"].tolist() == ["ANA PEREZ", "Beto"]


def test_logro_por_alumno_faltantes_no_salen_como_nan_porcentaje():
    """P0-4: `Avance` es un slope sin valor en el primer punto temporal."""
    df = pd.DataFrame({
        "Curso": ["II A", "II A"],
        "Nombre": ["Ana", "Beto"],
        "Rend": [0.5, 0.4],
        "Avance": [np.nan, np.nan],
    })
    out = tables.tabla_logro_por_alumno(
        df,
        parametros={},
        sort_by="Rend",
        formatos={"Rend": "percent", "Avance": "percent"},
        columnas=["Nombre", "Rend", "Avance"],
        columnas_renombrar={"Nombre": "Estudiante"},
    )
    assert out["Avance"].tolist() == [MARCA_SIN_DATO, MARCA_SIN_DATO]
    assert out["Rend"].tolist() == ["50%", "40%"]


def test_logro_por_pregunta_faltantes_como_guion():
    df = pd.DataFrame({
        "Curso": ["7 A", "7 A"],
        "N° Pregunta": [1, 2],
        "Habilidad": ["Localizar", None],
        "Logro": [0.5, np.nan],
    })
    out = tables.tabla_logro_por_pregunta(
        df, valor_agrupacion="7 A", agrupar_por="Curso", sort_by="N° Pregunta",
        formatos={"Logro": "percent"},
        columnas=["N° Pregunta", "Habilidad", "Logro"],
    )
    assert MARCA_SIN_DATO in out["Logro"].tolist()
    assert "nan%" not in out["Logro"].tolist()


def test_estadistica_por_pregunta_sin_respuestas_no_da_nan():
    df = pd.DataFrame({
        "Pregunta": [1, 2],
        "A": [0, 3], "B": [0, 1], "C": [0, 0], "D": [0, 0], "E": [0, 0],
        "Correcta": ["A", "B"], "Distractor": ["B", "A"],
    })
    out = tables.crear_tabla_estadistica_por_pregunta(df, parametros={})
    assert out.loc[0, "%A"] == MARCA_SIN_DATO
    assert out.loc[1, "%A"] == "75%"
