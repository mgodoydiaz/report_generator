"""Tests de rgenerator.tooling.curso_order.

Regresión del QA visual del orden de cursos: `curso_sort_key` daba el
mismo nivel al romano "I" y al arábigo "1", así que un informe DIA con
básica y media mezcladas intercalaba los cursos
("1 A, I A, 2 A, II A…") en vez de poner toda la básica primero.
El mismo defecto hacía que "1° MEDIO" saliera antes que "5° BÁSICO".
"""
from __future__ import annotations

import pytest

from backend.rgenerator.tooling.curso_order import curso_sort_key, sort_cursos

pytestmark = pytest.mark.unit


# ── Básica antes que media ───────────────────────────────────────────────

def test_basica_va_completa_antes_que_la_media():
    """Mezcla real del QA (DIA con básica y media en el mismo informe)."""
    etiquetas = [
        "1 A", "I A (TPI-510)", "2 A", "II A (TPI-510)",
        "I E (TPI-510)", "7 A", "3 A",
    ]
    assert sort_cursos(etiquetas) == [
        "1 A", "2 A", "3 A", "7 A",
        "I A (TPI-510)", "I E (TPI-510)", "II A (TPI-510)",
    ]


def test_romano_y_arabigo_del_mismo_digito_no_colisionan():
    assert curso_sort_key("1 A") != curso_sort_key("I A (TPI-510)")
    assert curso_sort_key("1 A") < curso_sort_key("I A (TPI-510)")


def test_media_en_arabigo_con_la_palabra_medio():
    """El defecto conocido: "1° MEDIO" ordenaba antes que "5° BÁSICO"."""
    assert sort_cursos(["1° MEDIO", "5° BÁSICO"]) == ["5° BÁSICO", "1° MEDIO"]


def test_media_en_arabigo_ordena_entre_si_y_tras_la_basica():
    cursos = ["2° MEDIO", "8° BÁSICO", "1° MEDIO", "4° MEDIO", "1° BÁSICO"]
    assert sort_cursos(cursos) == [
        "1° BÁSICO", "8° BÁSICO", "1° MEDIO", "2° MEDIO", "4° MEDIO",
    ]


def test_niveles_normalizados_al_grado_chileno():
    """Básica 1–8, media 9–12: I° medio es el grado 9 mire como mire."""
    assert curso_sort_key("8° BÁSICO")[0] == 8
    assert curso_sort_key("I A")[0] == 9
    assert curso_sort_key("1° MEDIO")[0] == 9
    assert curso_sort_key("IV B")[0] == 12
    # El romano no se desplaza dos veces por decir además "MEDIO".
    assert curso_sort_key("IV° MEDIO B")[0] == 12


def test_palabra_medio_no_se_confunde_con_otras():
    """Límite de palabra: "PROMEDIO" y un paralelo "MA" no son media."""
    assert curso_sort_key("3° PROMEDIO")[0] == 3
    assert curso_sort_key("3 MA")[0] == 3


# ── Lo ya validado no cambia (DIA 2026, SIMCE) ───────────────────────────

def test_solo_media_conserva_el_orden_romano():
    assert sort_cursos(["III°A", "I°B", "II°C", "I°A"]) == [
        "I°A", "I°B", "II°C", "III°A",
    ]


def test_solo_media_con_codigo_de_prueba():
    etiquetas = [
        "I A (TPI-510)", "I D (TPI-510)", "II A (TPI-510)", "II D (TPI-510)",
        "I B (TPA-710)", "I C (TPA-710)", "II B (TPA-710)", "II C (TPA-710)",
    ]
    assert sort_cursos(etiquetas) == [
        "I A (TPI-510)", "I B (TPA-710)", "I C (TPA-710)", "I D (TPI-510)",
        "II A (TPI-510)", "II B (TPA-710)", "II C (TPA-710)", "II D (TPI-510)",
    ]


def test_solo_basica_conserva_el_orden_numerico():
    assert sort_cursos(["7 B", "2 A", "10 A", "7 A", "2 B"]) == [
        "2 A", "2 B", "7 A", "7 B", "10 A",
    ]


# ── Fallback intacto ─────────────────────────────────────────────────────

@pytest.mark.parametrize("valor", ["KINDER", "TALLER DE LECTURA", "PRE-KINDER"])
def test_no_parseables_van_al_final_con_su_texto(valor):
    assert curso_sort_key(valor) == (999, valor)


def test_nulos_y_vacios_no_rompen_el_sort():
    assert curso_sort_key(None) == (999, "")
    assert curso_sort_key("   ") == (999, "")
    assert sort_cursos(["I A", None, "", "1 A", "KINDER"]) == [
        "1 A", "I A", "KINDER",
    ]
