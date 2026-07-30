"""Tests de `reports/helpers.py`: sin dato, identidad y orden temporal.

Cubren los hallazgos transversales del QA visual 2026-07-30:
    P0-3  ningún informe debe imprimir "nan" ni "nan%"
    P0-9  los ejes temporales se ordenan cronológicamente
    P0-12 los conteos de alumnos cuentan estudiantes, no filas
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.rgenerator.reports.helpers import (
    MARCA_SIN_DATO,
    clave_orden_temporal,
    coalescer_nombre_estudiante,
    columnas_identidad_estudiante,
    contar_estudiantes,
    df_a_html_table,
    es_columna_temporal,
    es_sin_dato,
    formatear_valor,
    ordenar_valores_temporales,
    texto_celda,
)

pytestmark = pytest.mark.unit


# ── Ausencia de dato ─────────────────────────────────────────────────────

@pytest.mark.parametrize("valor", [
    None, np.nan, float("nan"), pd.NA, pd.NaT, "", "   ",
    "nan", "NaN", "nan%", "NAN%", "NaT", "None", "<NA>", "inf", "-inf",
])
def test_es_sin_dato_detecta_faltantes(valor):
    assert es_sin_dato(valor) is True


@pytest.mark.parametrize("valor", [0, 0.0, "0", "0%", "—", "No Aplica", "MAYO", -1])
def test_es_sin_dato_no_marca_valores_legitimos(valor):
    assert es_sin_dato(valor) is False


def test_texto_celda_reemplaza_faltantes_por_guion():
    assert texto_celda(np.nan) == MARCA_SIN_DATO
    assert texto_celda("nan%") == MARCA_SIN_DATO
    assert texto_celda(0.42) == "0.42"


def test_formatear_valor_decide_antes_de_formatear():
    # El bug original: f"{nan:.0%}" → "nan%"
    assert formatear_valor(np.nan, "percent") == MARCA_SIN_DATO
    assert formatear_valor(None, "number") == MARCA_SIN_DATO
    assert formatear_valor(0.47, "percent") == "47%"
    assert formatear_valor(56.6, "number") == "57"
    assert formatear_valor(56.64, "decimal") == "56.6"


def test_df_a_html_table_nunca_imprime_nan():
    df = pd.DataFrame({
        "N° Lista": [1, np.nan],
        "Estudiante": ["Ana", None],
        "Promedio Hito": ["47%", "nan%"],
    })
    html = df_a_html_table(df)
    assert "nan" not in html.lower()
    assert html.count(MARCA_SIN_DATO) == 3


def test_df_a_html_table_alinea_a_derecha_columna_numerica_con_faltantes():
    df = pd.DataFrame({"Logro": [0.4, np.nan], "Curso": ["II A", "II B"]})
    html = df_a_html_table(df)
    assert '<th class="al-right">Logro</th>' in html
    assert '<th class="al-left">Curso</th>' in html


# ── Identidad del estudiante ─────────────────────────────────────────────

def test_columnas_identidad_respeta_prioridad():
    df = pd.DataFrame(columns=["Curso", "Nombre", "Nombre_Norm", "Rut", "Logro"])
    assert columnas_identidad_estudiante(df) == ["Rut", "Nombre_Norm", "Nombre"]


def test_contar_estudiantes_deduplica_filas_por_subprueba():
    # 2 estudiantes × 6 subpruebas = 12 filas, pero son 2 alumnos.
    filas = [
        {"Curso": "1° BÁSICO", "Nombre": nombre, "Subprueba": sub}
        for nombre in ("Ana", "Beto")
        for sub in ("CT", "FLO", "FNL", "FSF", "ILP", "VSD")
    ]
    df = pd.DataFrame(filas)
    assert len(df) == 12
    assert contar_estudiantes(df) == 2
    assert contar_estudiantes(df, agrupar_por="Curso").tolist() == [2]


def test_contar_estudiantes_no_altera_una_fila_por_alumno():
    """Cálculo Veloz tiene una fila por estudiante: nunique == size."""
    df = pd.DataFrame({
        "Curso": ["III°C"] * 3 + ["IV°A"] * 2,
        "Nombre": ["a", "b", "c", "d", "e"],
    })
    conteo = contar_estudiantes(df, agrupar_por="Curso")
    assert conteo["III°C"] == 3
    assert conteo["IV°A"] == 2


def test_contar_estudiantes_coalesce_entre_cargas_distintas():
    """DIA: unas filas traen Nombre y otras Nombre_Norm, nunca las dos."""
    df = pd.DataFrame({
        "Curso": ["7 A"] * 4,
        "Nombre": ["Ana", "Ana", None, None],
        "Nombre_Norm": [None, None, "BETO PEREZ", "BETO PEREZ"],
    })
    assert contar_estudiantes(df) == 2


def test_contar_estudiantes_degrada_a_filas_sin_identidad():
    df = pd.DataFrame({"Grupo": ["x", "x", "y"], "Logro": [1, 2, 3]})
    assert contar_estudiantes(df) == 3
    assert contar_estudiantes(df, agrupar_por="Grupo").tolist() == [2, 1]


def test_contar_estudiantes_usa_lista_y_curso_como_clave_compuesta():
    df = pd.DataFrame({
        "Curso": ["7 A", "7 A", "7 B"],
        "N° Lista": [1, 1, 1],
        "Asignatura": ["LENG", "MAT", "LENG"],
    })
    assert contar_estudiantes(df) == 2


def test_coalescer_nombre_estudiante_rellena_desde_nombre_norm():
    df = pd.DataFrame({
        "Nombre": ["Ana", None],
        "Nombre_Norm": [None, "BETO PEREZ"],
    })
    out = coalescer_nombre_estudiante(df, "Nombre")
    assert out["Nombre"].tolist() == ["Ana", "BETO PEREZ"]
    # No muta el original
    assert df["Nombre"].isna().sum() == 1


# ── Orden temporal ───────────────────────────────────────────────────────

@pytest.mark.parametrize("nombre", ["Mes", "Año", "Hito", "Versión", "N° Prueba",
                                    "Fecha", "eval_id", "Periodo"])
def test_es_columna_temporal(nombre):
    assert es_columna_temporal(nombre) is True


@pytest.mark.parametrize("nombre", ["Curso", "Habilidad", "Eje Temático", "Nivel",
                                    "Establecimiento", None])
def test_es_columna_temporal_falso(nombre):
    assert es_columna_temporal(nombre) is False


def test_orden_meses_es_calendario_no_alfabetico():
    desordenado = ["OCTUBRE", "ABRIL", "NOVIEMBRE", "AGOSTO", "JUNIO", "MAYO"]
    assert ordenar_valores_temporales(desordenado, "Mes") == [
        "ABRIL", "MAYO", "JUNIO", "AGOSTO", "OCTUBRE", "NOVIEMBRE",
    ]


def test_orden_hitos_dia():
    assert ordenar_valores_temporales(
        ["CIERRE", "DIAGNOSTICO", "INTERMEDIO"], "Hito"
    ) == ["DIAGNOSTICO", "INTERMEDIO", "CIERRE"]
    assert ordenar_valores_temporales(
        ["CIERRE", "INICIO", "INTERMEDIO"], "Hito"
    ) == ["INICIO", "INTERMEDIO", "CIERRE"]


def test_orden_versiones_idel():
    assert ordenar_valores_temporales(["v3", "v1", "v2"], "Versión") == ["v1", "v2", "v3"]
    # Los datos IDEL guardan la versión como "1"/"2"/"3"
    assert ordenar_valores_temporales(["3", "1", "2"], "Versión") == ["1", "2", "3"]


def test_orden_numero_prueba_es_numerico_no_lexicografico():
    assert ordenar_valores_temporales(["10", "2", "1", "13"], "N Prueba") == [
        "1", "2", "10", "13",
    ]
    assert ordenar_valores_temporales(
        ["Ensayo 10", "Ensayo 2", "Ensayo 1"], "N Prueba"
    ) == ["Ensayo 1", "Ensayo 2", "Ensayo 10"]


def test_orden_anio_es_numerico():
    assert ordenar_valores_temporales(["2026", "2024", "2025"], "Año") == [
        "2024", "2025", "2026",
    ]


def test_orden_combinacion_anio_mas_version():
    desordenado = ["2025/v1", "2024/v2", "2026/v1", "2024/v1", "2025/v3"]
    assert ordenar_valores_temporales(desordenado, "eval_id") == [
        "2024/v1", "2024/v2", "2025/v1", "2025/v3", "2026/v1",
    ]


def test_orden_combinacion_anio_mas_mes():
    desordenado = ["2026 MAYO", "2025 NOVIEMBRE", "2025 ABRIL"]
    assert ordenar_valores_temporales(desordenado, "Periodo") == [
        "2025 ABRIL", "2025 NOVIEMBRE", "2026 MAYO",
    ]


def test_orden_fechas_iso():
    assert ordenar_valores_temporales(
        ["2026-04-07 00:00:00", "2025-11-04 00:00:00"], "Fecha"
    ) == ["2025-11-04 00:00:00", "2026-04-07 00:00:00"]


def test_no_reordena_ejes_categoricos():
    cursos = ["II C", "II A", "II B"]
    assert ordenar_valores_temporales(cursos, "Curso") == cursos


def test_clave_orden_temporal_es_comparable():
    assert clave_orden_temporal("MAYO") < clave_orden_temporal("AGOSTO")
    assert clave_orden_temporal("2024/v2") < clave_orden_temporal("2025/v1")
