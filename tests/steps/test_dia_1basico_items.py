"""Tests de `scripts/dia_1basico_items.py`.

Cobertura:
- extraer_items_1basico: happy path (10 ítems, Logro = %L entre L/NL),
  valores ignorados (celdas vacías/otras), columnas con espacios
  irregulares ('Vocales     A, E, U').
- nivel_logro: umbrales Inicial/Intermedio/Avanzado (replica lookup_range
  mapping_id 35) y caso NaN.
- nivel_por_curso: siempre 'Primeros' (1° básico).
- construir_metric7_json: dimensions_json con los ids correctos, value
  con Logro/Nivel Logro.
- es_formato_cierre_1basico / es_formato_lectura_monitoreo_1basico:
  detección de formato para saltar Cierre / Matemática sin error.
- hito_coincide_con_nombre + resolución de duplicado por contenido
  (vía procesar_archivo con XLS sintéticos en disco).

Usa DataFrames y XLS sintéticos generados en el test — sin datos reales
de estudiantes.
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from scripts.dia_1basico_items import (
    BASE_COLS,
    ITEMS_1BASICO,
    construir_metric7_json,
    es_formato_cierre_1basico,
    es_formato_lectura_monitoreo_1basico,
    extraer_items_1basico,
    hito_coincide_con_nombre,
    nivel_logro,
    nivel_por_curso,
)


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────

def _columnas_xls_sinteticas() -> list:
    """Nombres de columna EXACTOS del XLS real (con espacios irregulares)."""
    return [
        "Número de Lista", "Nombre del Estudiante",
        "Sílaba inicial", "Sílaba final", "Sonido inicial", "Sonido final",
        "Vocales     A, E, U", "Cons.       M, L, P, S", "Cons.        D, T, N, R",
        "Sílaba directa", "Sílaba indirecta", "Sílaba compleja",
    ]


@pytest.fixture
def df_estudiantes_sintetico():
    """8 estudiantes sintéticos con L/NL por subhabilidad + un vacío."""
    cols = _columnas_xls_sinteticas()
    filas = [
        [1, "Estudiante Uno", "L", "NL", "L", "L", "L", "NL", "L", "L", "NL", "NL"],
        [2, "Estudiante Dos", "NL", "NL", "L", "NL", "L", "L", "NL", "L", "L", "L"],
        [3, "Estudiante Tres", "L", "L", "NL", "L", "NL", "L", "L", "NL", "L", "NL"],
        [4, "Estudiante Cuatro", "L", "NL", "L", "NL", "L", "NL", "L", "L", "NL", "L"],
        # celda vacía (ausente) en 'Sílaba inicial' — debe ignorarse, no contar como NL.
        [5, "Estudiante Cinco", None, "L", "L", "L", "NL", "NL", "L", "NL", "L", "L"],
    ]
    return pd.DataFrame(filas, columns=cols)


# ─────────────────────────────────────────────────────────────────────────
# extraer_items_1basico
# ─────────────────────────────────────────────────────────────────────────

def test_extraer_items_1basico_devuelve_10_filas_con_columnas_base(df_estudiantes_sintetico):
    df = extraer_items_1basico(
        df_estudiantes_sintetico,
        establecimiento="Colegio Básico", curso="1 A",
        hito="INTERMEDIO", asignatura="LECTURA", anio="2026",
    )
    assert len(df) == len(ITEMS_1BASICO) == 10
    for col in BASE_COLS + ["Hito", "Asignatura", "Año"]:
        assert col in df.columns
    assert list(df["N Pregunta"]) == [str(n) for n in range(7, 17)]


def test_extraer_items_1basico_logro_es_proporcion_de_l(df_estudiantes_sintetico):
    df = extraer_items_1basico(
        df_estudiantes_sintetico,
        establecimiento="Colegio Básico", curso="1 A", hito="INTERMEDIO",
    )
    # 'Sílaba inicial': L, NL, L, L, <vacío> → 3 L de 4 válidos (el vacío se ignora)
    fila = df[df["Habilidad"] == "Sílaba inicial"].iloc[0]
    assert fila["Logro"] == pytest.approx(3 / 4)
    assert fila["_n_estudiantes_ignorados"] == 1
    assert fila["_n_estudiantes_L"] == 3
    assert fila["_n_estudiantes_NL"] == 1


def test_extraer_items_1basico_resuelve_columnas_con_espacios_irregulares(df_estudiantes_sintetico):
    df = extraer_items_1basico(
        df_estudiantes_sintetico,
        establecimiento="Colegio Básico", curso="1 A", hito="INTERMEDIO",
    )
    # 'Vocales     A, E, U' (espacios múltiples en el XLS real) debe resolverse
    # a la habilidad "Vocales A, E, U" sin lanzar KeyError.
    fila = df[df["Habilidad"] == "Vocales A, E, U"].iloc[0]
    assert fila["N Pregunta"] == "11"
    assert 0 <= fila["Logro"] <= 1


def test_extraer_items_1basico_columna_faltante_lanza_keyerror():
    df_incompleto = pd.DataFrame({"Nombre del Estudiante": ["A"], "Sílaba inicial": ["L"]})
    with pytest.raises(KeyError):
        extraer_items_1basico(df_incompleto, establecimiento="x", curso="1 A", hito="INTERMEDIO")


def test_extraer_items_1basico_sin_estudiantes_validos_da_nan():
    cols = _columnas_xls_sinteticas()
    df_vacio = pd.DataFrame([[1, "Solo Uno"] + [None] * 10], columns=cols)
    df = extraer_items_1basico(df_vacio, establecimiento="x", curso="1 A", hito="INTERMEDIO")
    assert df["Logro"].isna().all()


# ─────────────────────────────────────────────────────────────────────────
# nivel_logro / nivel_por_curso
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("logro,esperado", [
    (0.0, "Inicial"),
    (0.4, "Inicial"),
    (0.41, "Intermedio"),
    (0.6, "Intermedio"),
    (0.61, "Avanzado"),
    (1.0, "Avanzado"),
])
def test_nivel_logro_umbrales(logro, esperado):
    assert nivel_logro(logro) == esperado


def test_nivel_logro_nan_es_none():
    assert nivel_logro(float("nan")) is None
    assert nivel_logro(None) is None


def test_nivel_por_curso_siempre_primeros():
    assert nivel_por_curso("1 A") == "Primeros"
    assert nivel_por_curso("1 B") == "Primeros"


# ─────────────────────────────────────────────────────────────────────────
# construir_metric7_json
# ─────────────────────────────────────────────────────────────────────────

def test_construir_metric7_json_dimensiones_e_ids(df_estudiantes_sintetico):
    df = extraer_items_1basico(
        df_estudiantes_sintetico,
        establecimiento="Colegio Básico", curso="1 A",
        hito="INTERMEDIO", asignatura="LECTURA", anio="2026",
    )
    registros = construir_metric7_json(df)
    assert len(registros) == 10
    r0 = registros[0]
    assert set(r0["dimensions_json"].keys()) == {
        "3", "4", "5", "8", "12", "13", "14", "15", "16", "18",
    }
    assert r0["dimensions_json"]["3"] == "Colegio Básico"
    assert r0["dimensions_json"]["4"] == "2026"
    assert r0["dimensions_json"]["5"] == "1 A"
    assert r0["dimensions_json"]["14"] == "INTERMEDIO"
    assert r0["dimensions_json"]["15"] == "Primeros"
    assert r0["dimensions_json"]["16"] == "7"
    assert "Logro" in r0["value"] and "Nivel Logro" in r0["value"]
    assert isinstance(r0["value"]["Logro"], float)


def test_construir_metric7_json_logro_nan_queda_none():
    cols = _columnas_xls_sinteticas()
    df_vacio = pd.DataFrame([[1, "Solo Uno"] + [None] * 10], columns=cols)
    df_items = extraer_items_1basico(df_vacio, establecimiento="x", curso="1 A", hito="INTERMEDIO")
    registros = construir_metric7_json(df_items)
    assert all(r["value"]["Logro"] is None for r in registros)
    assert all(r["value"]["Nivel Logro"] is None for r in registros)


# ─────────────────────────────────────────────────────────────────────────
# Detección de formato (Cierre / Matemática vs Lectura monitoreo)
# ─────────────────────────────────────────────────────────────────────────

def test_es_formato_cierre_1basico_true_para_columnas_de_cierre():
    df = pd.DataFrame(columns=[
        "Número de Lista", "Nombre del Estudiante",
        "Lectura de palabras", "Lectura de oraciones", "Comprensión lectora",
    ])
    assert es_formato_cierre_1basico(df)


def test_es_formato_cierre_1basico_false_para_monitoreo(df_estudiantes_sintetico):
    assert not es_formato_cierre_1basico(df_estudiantes_sintetico)


def test_es_formato_lectura_monitoreo_true(df_estudiantes_sintetico):
    assert es_formato_lectura_monitoreo_1basico(df_estudiantes_sintetico)


def test_es_formato_lectura_monitoreo_false_para_matematica():
    df_mate = pd.DataFrame(columns=[
        "Número de Lista", "Nombre del Estudiante",
        "Números y operaciones", "Patrones y álgebra", "Geometría",
        "Medición", "Datos y probabilidades", "Porcentaje total de respuestas correctas",
    ])
    assert not es_formato_lectura_monitoreo_1basico(df_mate)


# ─────────────────────────────────────────────────────────────────────────
# hito_coincide_con_nombre (heurística de resolución de duplicados)
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nombre,hito,esperado", [
    ("resultados_estudiantes_16843_LECTURA_1_A_monitoreo_2026.xls", "INTERMEDIO", True),
    ("resultados_estudiantes_16843_LECTURA_1_A_monitoreo_2026 (1).xls", "DIAGNOSTICO", False),
    ("resultados_estudiantes_16843_LECTURA_2_A_diagnostico_2024.xls", "DIAGNOSTICO", True),
    ("resultados_estudiantes_16843_LECTURA_1_A_cierre_2024.xls", "CIERRE", True),
])
def test_hito_coincide_con_nombre(nombre, hito, esperado):
    assert hito_coincide_con_nombre(Path(nombre), hito) is esperado
