"""Tests de los dos P0 del informe SIMCE formato oficial (2026-07-30).

    P0-A  el N° de pregunta se ordenaba como texto: 1, 10, 11, … 2, 20
    P0-B  la tabla "Estadística por Pregunta" (13 columnas) se salía del
          margen derecho y perdía D, E, Correcta y Distractor

Referencia visual: informe del dueño, "Pullinque Matemáticas Mayo", pág. 6.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.rgenerator.reports.helpers import (
    ANCHO_CONTENIDO_CM,
    MARCA_SIN_DATO,
    _ancho_estimado_cm,
    clave_orden_natural,
    df_a_html_table,
    escalon_tabla,
    ordenar_df_por,
    ordenar_valores_categoricos,
    ordenar_valores_naturales,
    redondear_decimales_para_ancho,
)
from backend.rgenerator.reports.tables import (
    crear_tabla_estadistica_por_pregunta,
    tabla_logro_por_pregunta,
)

pytestmark = pytest.mark.unit


# ── P0-A · orden natural ─────────────────────────────────────────────────

def test_orden_natural_de_preguntas_numericas():
    preguntas = [str(n) for n in (10, 2, 1, 21, 3, 20, 11)]
    assert ordenar_valores_naturales(preguntas) == [
        "1", "2", "3", "10", "11", "20", "21",
    ]


def test_orden_natural_mezcla_numerico_y_no_numerico():
    # Los códigos con letra no rompen el orden: los puramente numéricos van
    # primero y el resto queda agrupado por prefijo, también numérico.
    mezcla = ["P10", "2", "P2", "10", "P1a", "1"]
    assert ordenar_valores_naturales(mezcla) == [
        "1", "2", "10", "P1a", "P2", "P10",
    ]


def test_orden_natural_sin_numeros_es_alfabetico():
    assert ordenar_valores_naturales(["Modelar", "Argumentar"]) == [
        "Argumentar", "Modelar",
    ]


@pytest.mark.parametrize("valor", [None, "", "   ", np.nan])
def test_clave_orden_natural_tolera_valores_vacios(valor):
    # No debe reventar y tiene que ser comparable con cualquier otra clave:
    # una celda vacía no puede tumbar el orden de una tabla entera.
    clave = clave_orden_natural(valor)
    assert isinstance(clave, tuple)
    assert (clave < clave_orden_natural("3")) or (clave > clave_orden_natural("3"))


def test_orden_categorico_respeta_lo_temporal():
    assert ordenar_valores_categoricos(["OCTUBRE", "ABRIL"], "Mes") == [
        "ABRIL", "OCTUBRE",
    ]


def test_orden_categorico_no_reordena_series_sin_numeros():
    # Habilidad / Eje Temático conservan el orden que trae el caller: sus
    # colores se asignan por posición y no se tocan desde este fix.
    series = ["Representar", "Modelar", "Argumentar y comunicar"]
    assert ordenar_valores_categoricos(series, "Habilidad") == series


def test_orden_categorico_numera_cursos():
    assert ordenar_valores_categoricos(["10 A", "9 A", "2 B"], "Curso") == [
        "2 B", "9 A", "10 A",
    ]


def test_ordenar_df_por_columna_de_texto_es_numerico():
    df = pd.DataFrame({"Pregunta": ["10", "2", "1"], "Logro": [0.1, 0.2, 0.3]})
    assert ordenar_df_por(df, "Pregunta")["Pregunta"].tolist() == ["1", "2", "10"]


def test_ordenar_df_por_columna_numerica_no_cambia():
    df = pd.DataFrame({"Rend": [0.5, 0.9, 0.1]})
    assert ordenar_df_por(df, "Rend", ascending=False)["Rend"].tolist() == [
        0.9, 0.5, 0.1,
    ]


def test_ordenar_df_por_columna_inexistente_devuelve_el_df():
    df = pd.DataFrame({"Rend": [0.5]})
    assert ordenar_df_por(df, "NoExiste") is df


def _df_preguntas(n: int = 12) -> pd.DataFrame:
    """DataFrame por pregunta con la numeración guardada como texto."""
    return pd.DataFrame({
        "Pregunta": [str(i) for i in range(1, n + 1)],
        "Curso": ["II A"] * n,
        "Habilidad": ["Representar"] * n,
        "Logro": [0.5] * n,
        "Correcta": ["a"] * n,
        "Distractor": ["b"] * n,
        "A": [0.57] * n,
        "B": [0.29] * n,
        "C": [0.14] * n,
        "D": [0.0] * n,
        "E": [0.0] * n,
    })


def test_estadistica_por_pregunta_sale_en_orden_numerico():
    df = _df_preguntas(12).sample(frac=1, random_state=0)  # entrada desordenada
    salida = crear_tabla_estadistica_por_pregunta(df, {})
    assert salida["Pregunta"].tolist() == [str(i) for i in range(1, 13)]


def test_logro_por_pregunta_ordenado_por_numero_de_pregunta():
    df = _df_preguntas(12)
    salida = tabla_logro_por_pregunta(df, "II A", sort_by="Pregunta")
    # Descendente por N° de pregunta, numérico y no lexicográfico.
    assert salida["N° Pregunta"].tolist()[:3] == ["12", "11", "10"]


def test_logro_por_pregunta_ordenado_por_logro_no_cambia():
    df = _df_preguntas(3)
    df["Logro"] = [0.1, 0.9, 0.5]
    salida = tabla_logro_por_pregunta(df, "II A", sort_by="Logro")
    assert salida["Logro"].tolist() == ["90%", "50%", "10%"]


# ── P0-B · ancho de la tabla ─────────────────────────────────────────────

def test_estadistica_por_pregunta_recorta_decimales():
    # La métrica guarda proporciones: sin recorte la celda sale
    # "0.5700000000000001" y empuja las últimas columnas fuera del margen.
    df = _df_preguntas(3)
    salida = crear_tabla_estadistica_por_pregunta(df, {})
    for celda in salida["A"]:
        assert celda == "0.57"
    assert salida["%A"].tolist() == ["57%", "57%", "57%"]


def test_estadistica_por_pregunta_mantiene_conteos_enteros():
    # Cuando la carga trae conteos (como el informe de referencia), se
    # imprimen enteros, no "62.00".
    df = _df_preguntas(2)
    for col, valor in (("A", 62), ("B", 15), ("C", 11), ("D", 7), ("E", 0)):
        df[col] = float(valor)
    salida = crear_tabla_estadistica_por_pregunta(df, {})
    assert salida["A"].tolist() == ["62", "62"]
    assert salida["E"].tolist() == ["0", "0"]


def test_tabla_de_estadistica_cabe_en_el_ancho_de_pagina():
    """13 columnas con el contenido real del informe deben caber."""
    df = crear_tabla_estadistica_por_pregunta(_df_preguntas(30), {})
    ancho = _ancho_estimado_cm(df, 9.0, 6.0)
    assert ancho <= ANCHO_CONTENIDO_CM, f"{ancho:.2f} cm no cabe"
    assert escalon_tabla(df) is None  # no hace falta compactar


def test_tabla_angosta_no_se_compacta():
    df = pd.DataFrame({"Curso": ["II A", "II B"], "Logro": ["40%", "31%"]})
    html = df_a_html_table(df)
    assert 'class="report-table"' in html
    assert "tabla-compacta" not in html


def test_tabla_muy_ancha_recibe_clase_compacta():
    ancho = pd.DataFrame({
        f"Columna larga {i}": ["texto de relleno bastante largo"] * 3
        for i in range(12)
    })
    html = df_a_html_table(ancho)
    assert "tabla-compacta" in html


def test_ajustar_ancho_desactivado_no_agrega_clase():
    ancho = pd.DataFrame({
        f"Columna larga {i}": ["texto de relleno bastante largo"] * 3
        for i in range(12)
    })
    html = df_a_html_table(ancho, ajustar_ancho=False)
    assert "tabla-compacta" not in html


def test_redondeo_a_dos_decimales_es_por_columna_completa():
    df = pd.DataFrame({
        "A": [0.5700000000000001, 0.5, np.nan],
        "Nombre": ["Ana", "Beto", "Cid"],
        "%A": ["57%", "50%", "—"],
    })
    salida = redondear_decimales_para_ancho(df)
    assert salida["A"].tolist() == ["0.57", "0.50", MARCA_SIN_DATO]
    # Las columnas de texto y las ya formateadas quedan intactas.
    assert salida["Nombre"].tolist() == ["Ana", "Beto", "Cid"]
    assert salida["%A"].tolist() == ["57%", "50%", "—"]


def test_redondeo_no_toca_columnas_enteras():
    df = pd.DataFrame({"Alumnos": [29, 24, 21]})
    assert redondear_decimales_para_ancho(df) is df


def test_df_a_html_table_recorta_decimales_cuando_no_cabe():
    """El ruido de coma flotante desaparece de una tabla desbordada."""
    columnas = {"Pregunta": [str(i) for i in range(1, 6)]}
    for letra in "ABCDEFGHIJ":
        columnas[f"Alternativa {letra}"] = [0.5700000000000001] * 5
    html = df_a_html_table(pd.DataFrame(columnas))
    assert "0.5700000000000001" not in html
    assert ">0.57<" in html
