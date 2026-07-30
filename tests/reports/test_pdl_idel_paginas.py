"""Tests del informe PDL IDEL-Woodcock (`scripts/report_pdl_idel.py`).

Hallazgos del QA visual 2026-07-30:
    P0-14 la tabla "Promedios y medianas por subprueba" era ilegible (18
          columnas comprimidas en el ancho de página)
    P1-4  la "Tasa de mejora por curso" de la síntesis salía sin barras
"""
from __future__ import annotations

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scripts import report_pdl_idel as pdl

pytestmark = pytest.mark.unit


def _fila(curso, estudiante, anio, version, subprueba, puntaje, nivel="Bajo Riesgo"):
    return {
        "curso": curso, "estudiante": estudiante, "año": anio, "version": version,
        "eval_id": f"{anio}/v{version}", "subprueba": subprueba,
        "puntaje": puntaje, "nivel": nivel, "establecimiento": "Panguipulli",
    }


@pytest.fixture
def df_cohorte_discontinua():
    """Cohortes distintas por año: nadie aparece en 2025 y en 2026.

    Es la forma real de los datos IDEL cargados (verificado 2026-07-30):
    el cruce de estudiantes entre años es 0 en los 6 cursos.
    """
    filas = []
    for anio, prefijo in ((2025, "A"), (2026, "B")):
        for version in (1, 2, 3):
            for i in range(4):
                for sub in pdl.SUBPRUEBAS_ORDER:
                    filas.append(_fila(
                        "1° BÁSICO", f"{prefijo}lumno {i}", anio, version, sub,
                        puntaje=10 + version,
                        nivel="Crítico" if version == 1 else "Bajo Riesgo",
                    ))
    return pd.DataFrame(filas)


# ── par de evaluaciones comparables ──────────────────────────────────────

def test_par_comparables_elige_el_mayor_lapso_con_seguimiento(df_cohorte_discontinua):
    """Antes se comparaba 2025/v1 → 2026/v3: 0 estudiantes en común."""
    first, latest = pdl.par_evaluaciones_comparables(df_cohorte_discontinua)
    assert (first, latest) == ("2026/v1", "2026/v3")


def test_par_comparables_prefiere_el_par_mas_reciente():
    filas = (
        [_fila("1° BÁSICO", "Ana", 2025, v, "CT", 10) for v in (1, 2)]
        + [_fila("1° BÁSICO", "Beto", 2026, v, "CT", 10) for v in (1, 2)]
    )
    assert pdl.par_evaluaciones_comparables(pd.DataFrame(filas)) == ("2026/v1", "2026/v2")


def test_par_comparables_sin_seguimiento_devuelve_none():
    filas = [
        _fila("1° BÁSICO", "Ana", 2025, 1, "CT", 10),
        _fila("1° BÁSICO", "Beto", 2026, 1, "CT", 12),
    ]
    assert pdl.par_evaluaciones_comparables(pd.DataFrame(filas)) == (None, None)


def test_par_comparables_una_sola_evaluacion():
    filas = [_fila("1° BÁSICO", "Ana", 2025, 1, "CT", 10)]
    assert pdl.par_evaluaciones_comparables(pd.DataFrame(filas)) == (None, None)


def test_etiqueta_par_compacta_cuando_comparten_anio():
    assert pdl.etiqueta_par_evaluaciones("2026/v1", "2026/v3") == "2026/v1 → v3"
    assert pdl.etiqueta_par_evaluaciones("2025/v3", "2026/v1") == "2025/v3 → 2026/v1"
    assert pdl.etiqueta_par_evaluaciones(None, None) == "—"


# ── tabla de promedios / medianas ────────────────────────────────────────

def _tablas_de_la_figura(fig):
    """Devuelve las matplotlib Tables dibujadas en la figura."""
    return [t for ax in fig.axes for t in ax.tables]


def test_tabla_estadistico_se_parte_en_dos_y_cabe_en_la_pagina(df_cohorte_discontinua):
    """8 evaluaciones daban 18 columnas en una sola tabla → ilegible."""
    evals = pdl.eval_ids_sorted(df_cohorte_discontinua)
    assert len(evals) == 6

    fig = plt.figure(figsize=(pdl.PAGE_W_IN, pdl.PAGE_H_IN))
    pdl._render_tabla_estadistico(
        fig, df_cohorte_discontinua, evals, "mean",
        titulo="Promedio", titulo_y=0.5,
        axes_rect=[pdl.CONTENT_L, 0.3, pdl.CONTENT_W, 0.18],
    )
    tablas = _tablas_de_la_figura(fig)
    assert len(tablas) == 1

    columnas = [c for (fila, c) in tablas[0].get_celld() if fila == 0]
    # Sub. + Descripción + una columna por evaluación (no dos)
    assert len(set(columnas)) == 2 + len(evals)
    plt.close(fig)


def test_tabla_estadistico_encabezado_en_dos_lineas(df_cohorte_discontinua):
    evals = pdl.eval_ids_sorted(df_cohorte_discontinua)
    fig = plt.figure(figsize=(pdl.PAGE_W_IN, pdl.PAGE_H_IN))
    pdl._render_tabla_estadistico(
        fig, df_cohorte_discontinua, evals, "median",
        titulo="Mediana", titulo_y=0.5,
        axes_rect=[pdl.CONTENT_L, 0.3, pdl.CONTENT_W, 0.18],
    )
    encabezados = [
        celda.get_text().get_text()
        for (fila, _), celda in _tablas_de_la_figura(fig)[0].get_celld().items()
        if fila == 0
    ]
    assert "2026\nv3" in encabezados
    assert not any("Prom." in e or "Med." in e for e in encabezados)
    plt.close(fig)


def test_tabla_estadistico_anchos_suman_uno(df_cohorte_discontinua):
    evals = pdl.eval_ids_sorted(df_cohorte_discontinua)
    fig = plt.figure(figsize=(pdl.PAGE_W_IN, pdl.PAGE_H_IN))
    pdl._render_tabla_estadistico(
        fig, df_cohorte_discontinua, evals, "mean",
        titulo="Promedio", titulo_y=0.5,
        axes_rect=[pdl.CONTENT_L, 0.3, pdl.CONTENT_W, 0.18],
    )
    anchos = [
        celda.get_width()
        for (fila, _), celda in _tablas_de_la_figura(fig)[0].get_celld().items()
        if fila == 0
    ]
    assert sum(anchos) == pytest.approx(1.0, abs=1e-6)
    plt.close(fig)


def test_tabla_estadistico_marca_faltantes_con_guion():
    """Una subprueba sin registros en una evaluación no imprime 'nan'."""
    filas = [
        _fila("1° BÁSICO", "Ana", 2025, 1, "CT", 10),
        _fila("1° BÁSICO", "Ana", 2025, 2, "CT", 12),
        _fila("1° BÁSICO", "Ana", 2025, 1, "FLO", 30),
    ]
    df = pd.DataFrame(filas)
    fig = plt.figure(figsize=(pdl.PAGE_W_IN, pdl.PAGE_H_IN))
    pdl._render_tabla_estadistico(
        fig, df, pdl.eval_ids_sorted(df), "mean",
        titulo="Promedio", titulo_y=0.5,
        axes_rect=[pdl.CONTENT_L, 0.3, pdl.CONTENT_W, 0.18],
    )
    textos = [
        celda.get_text().get_text()
        for celda in _tablas_de_la_figura(fig)[0].get_celld().values()
    ]
    assert "—" in textos
    assert not any("nan" in t.lower() for t in textos)
    plt.close(fig)


# ── panorama: mapa de riesgo ─────────────────────────────────────────────

def _capturar_paginas(fn, df, tmp_path):
    """Ejecuta un renderer de página y devuelve las figuras que produjo."""
    from matplotlib.backends.backend_pdf import PdfPages

    figuras: list[plt.Figure] = []
    with PdfPages(tmp_path / "pagina.pdf") as pdf:
        original = pdf.savefig

        def _capturar(fig=None, **kwargs):
            figuras.append(fig)
            return original(fig, **kwargs)

        pdf.savefig = _capturar  # type: ignore[method-assign]
        fn(pdf, df, pdl.PageCounter())
    return figuras


def test_mapa_de_riesgo_usa_la_ultima_evaluacion_de_cada_curso(tmp_path):
    """Con la última evaluación global 5 de 6 filas quedaban en blanco."""
    filas = (
        # 1° BÁSICO llega hasta 2026/v3
        [_fila("1° BÁSICO", "Ana", 2026, v, sub, 10, "Crítico")
         for v in (1, 2, 3) for sub in pdl.SUBPRUEBAS_ORDER]
        # 2° BÁSICO solo hasta 2025/v3
        + [_fila("2° BÁSICO", "Beto", 2025, v, sub, 20, "Bajo Riesgo")
           for v in (1, 2, 3) for sub in pdl.SUBPRUEBAS_ORDER]
    )
    figuras = _capturar_paginas(pdl.render_panorama, pd.DataFrame(filas), tmp_path)
    etiquetas = [t.get_text() for t in figuras[0].axes[0].get_yticklabels()]
    assert etiquetas == ["1° BÁSICO\n2026/v3", "2° BÁSICO\n2025/v3"]

    # Ambas filas tienen valores (antes 2° BÁSICO salía vacía)
    textos = [t.get_text() for t in figuras[0].axes[0].texts]
    assert textos.count("100") == len(pdl.SUBPRUEBAS_ORDER)   # 1° BÁSICO, todo crítico
    assert textos.count("0") == len(pdl.SUBPRUEBAS_ORDER)     # 2° BÁSICO, sin riesgo


# ── síntesis: tasa de mejora ─────────────────────────────────────────────

def test_sintesis_dibuja_barras_con_cohorte_discontinua(df_cohorte_discontinua, tmp_path):
    """Antes: 0 barras porque comparaba 2025/v1 con 2026/v3."""
    from matplotlib.backends.backend_pdf import PdfPages

    figuras: list[plt.Figure] = []
    salida = tmp_path / "sintesis.pdf"
    with PdfPages(salida) as pdf:
        original = pdf.savefig

        def _capturar(fig=None, **kwargs):
            figuras.append(fig)
            return original(fig, **kwargs)

        pdf.savefig = _capturar  # type: ignore[method-assign]
        pdl.render_closing(pdf, df_cohorte_discontinua, pdl.PageCounter())

    ax = figuras[0].axes[0]
    alturas = [b.get_height() for b in ax.patches if b.get_height() > 0]
    assert alturas, "la tasa de mejora no dibujó ninguna barra"
    assert sum(alturas) == pytest.approx(100.0, abs=0.5)


def test_sintesis_rotula_el_par_usado(df_cohorte_discontinua, tmp_path):
    from matplotlib.backends.backend_pdf import PdfPages

    figuras: list[plt.Figure] = []
    with PdfPages(tmp_path / "sintesis.pdf") as pdf:
        original = pdf.savefig

        def _capturar(fig=None, **kwargs):
            figuras.append(fig)
            return original(fig, **kwargs)

        pdf.savefig = _capturar  # type: ignore[method-assign]
        pdl.render_closing(pdf, df_cohorte_discontinua, pdl.PageCounter())

    etiquetas = [t.get_text() for t in figuras[0].axes[0].get_xticklabels()]
    assert etiquetas == ["1° BÁSICO\n2026/v1 → v3"]
