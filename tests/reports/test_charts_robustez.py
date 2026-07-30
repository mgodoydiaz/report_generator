"""Tests de robustez y orden de `reports/charts.py`.

Reproducen los crashes del informe DIA oficial y el orden alfabético de los
gráficos de "evolución" (P0-2, P0-9 y P0-12 del QA visual 2026-07-30).

Los gráficos escriben un PNG: los tests verifican que la función NO lance y
que el PNG exista. El orden y los conteos se verifican leyendo los artistas
de matplotlib a través del `Figure` que la función deja en el PNG — para eso
se interceptan los `plt.subplots` con un spy liviano.
"""
from __future__ import annotations

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backend.rgenerator.reports import charts

pytestmark = pytest.mark.unit


@pytest.fixture
def png(tmp_path):
    return str(tmp_path / "grafico.png")


@pytest.fixture
def espia_figuras(monkeypatch):
    """Captura las figuras creadas y evita que `plt.close` las destruya."""
    figuras: list[plt.Figure] = []
    subplots_real = plt.subplots

    def _subplots(*args, **kwargs):
        fig, ax = subplots_real(*args, **kwargs)
        figuras.append(fig)
        return fig, ax

    monkeypatch.setattr(plt, "subplots", _subplots)
    monkeypatch.setattr(plt, "close", lambda *a, **k: None)
    return figuras


def _etiquetas_x(fig):
    ax = fig.axes[0]
    return [t.get_text() for t in ax.get_xticklabels()]


def _series_leyenda(fig):
    ax = fig.axes[0]
    leg = ax.get_legend()
    return [t.get_text() for t in leg.get_texts()] if leg else []


# ── P0-2: crashes de valor_promedio_agrupado_por ─────────────────────────

@pytest.fixture
def df_preguntas_dia():
    """18 cursos × ejes temáticos desiguales, con nulos en el eje.

    Reproduce las dos excepciones del informe DIA oficial:
      - 14 ejes distintos > 8 colores de Set2 → IndexError
      - un eje presente en solo 2 de 18 cursos → shape mismatch (18,) vs (2,)
    """
    cursos = [f"Curso {i}" for i in range(18)]
    ejes_comunes = [
        "Narración", "Poema", "Texto dramático", "Texto no literario",
        "Texto de los medios", "Geometría", "Números", "Números y Operaciones",
        "Probabilidad y Estadística", "Álgebra y Funciones",
        "Datos y Probabilidades", "Texto medios argumentativo",
    ]
    filas = []
    for i, curso in enumerate(cursos):
        for eje in ejes_comunes:
            filas.append({"Curso": curso, "Eje Temático": eje, "Logro": 0.4 + i / 100})
        # "Medición" solo en 2 cursos, "Patrones y Álgebra" en 1
        if i < 2:
            filas.append({"Curso": curso, "Eje Temático": "Medición", "Logro": 0.5})
        if i == 0:
            filas.append({"Curso": curso, "Eje Temático": "Patrones y Álgebra", "Logro": 0.6})
        # Filas con el eje nulo (1320/2386 en los datos reales)
        filas.append({"Curso": curso, "Eje Temático": None, "Logro": 0.3})
        filas.append({"Curso": curso, "Eje Temático": "  ", "Logro": 0.3})
    return pd.DataFrame(filas)


def test_agrupado_no_crashea_con_mas_de_8_series(df_preguntas_dia, png):
    """Antes: IndexError: tuple index out of range (Set2 tiene 8 colores)."""
    charts.valor_promedio_agrupado_por(
        df_preguntas_dia,
        columna_valor="Logro",
        agrupar_principal_por="Curso",
        agrupar_secundario_por="Eje Temático",
        formato="percent",
        nombre_grafico=png,
    )
    assert df_preguntas_dia["Eje Temático"].nunique() > 8


def test_agrupado_no_crashea_con_series_incompletas(df_preguntas_dia, png, espia_figuras):
    """Antes: ValueError shape mismatch 'x' (18,) vs 'height' (2,)."""
    charts.valor_promedio_agrupado_por(
        df_preguntas_dia,
        columna_valor="Logro",
        agrupar_principal_por="Curso",
        agrupar_secundario_por="Eje Temático",
        formato="percent",
        nombre_grafico=png,
    )
    fig = espia_figuras[-1]
    # Una serie por eje temático no nulo, todas del largo del eje X
    assert len(_series_leyenda(fig)) == 14
    assert len(_etiquetas_x(fig)) == 18


def test_agrupado_ignora_filas_con_eje_principal_nulo(png, espia_figuras):
    df = pd.DataFrame([
        {"Curso": "II A", "Mes": "ABRIL", "Rend": 0.5},
        {"Curso": None, "Mes": "ABRIL", "Rend": 0.9},
        {"Curso": "II B", "Mes": "ABRIL", "Rend": 0.4},
    ])
    charts.valor_promedio_agrupado_por(
        df, columna_valor="Rend", agrupar_principal_por="Curso",
        agrupar_secundario_por="Mes", nombre_grafico=png,
    )
    assert _etiquetas_x(espia_figuras[-1]) == ["II A", "II B"]


def test_agrupado_sin_datos_devuelve_placeholder(png):
    df = pd.DataFrame({"Curso": ["II A"], "Eje Temático": [None], "Logro": [0.4]})
    charts.valor_promedio_agrupado_por(
        df, columna_valor="Logro", agrupar_principal_por="Curso",
        agrupar_secundario_por="Eje Temático", nombre_grafico=png,
    )
    import os
    assert os.path.getsize(png) > 0


# ── P0-9: orden del eje temporal ─────────────────────────────────────────

@pytest.fixture
def df_evolucion():
    """Un curso con 4 meses cargados en orden NO cronológico."""
    filas = []
    for mes, rend in [("SEPTIEMBRE", 0.60), ("ABRIL", 0.55), ("MAYO", 0.45),
                      ("AGOSTO", 0.62)]:
        filas.append({"Curso": "II° medio C", "Mes": mes, "Rend": rend})
    return pd.DataFrame(filas)


def test_evolucion_ordena_meses_cronologicamente(df_evolucion, png, espia_figuras):
    """Panguipulli pág 2: se leía 55 → 62 → 45 → 60 en vez de 55 → 45 → 62 → 60."""
    charts.valor_promedio_agrupado_por(
        df_evolucion,
        columna_valor="Rend",
        agrupar_principal_por="Curso",
        agrupar_secundario_por="Mes",
        formato="percent",
        nombre_grafico=png,
    )
    assert _series_leyenda(espia_figuras[-1]) == ["ABRIL", "MAYO", "AGOSTO", "SEPTIEMBRE"]


def test_evolucion_ordena_hitos_dia(png, espia_figuras):
    df = pd.DataFrame([
        {"Curso": "7 A", "Hito": "CIERRE", "Logro": 0.7},
        {"Curso": "7 A", "Hito": "DIAGNOSTICO", "Logro": 0.4},
        {"Curso": "7 A", "Hito": "INTERMEDIO", "Logro": 0.55},
    ])
    charts.valor_promedio_agrupado_por(
        df, columna_valor="Logro", agrupar_principal_por="Curso",
        agrupar_secundario_por="Hito", nombre_grafico=png,
    )
    assert _series_leyenda(espia_figuras[-1]) == ["DIAGNOSTICO", "INTERMEDIO", "CIERRE"]


def test_evolucion_eje_x_temporal_se_ordena(png, espia_figuras):
    df = pd.DataFrame([
        {"Mes": "OCTUBRE", "Curso": "II A", "Rend": 0.6},
        {"Mes": "ABRIL", "Curso": "II A", "Rend": 0.4},
        {"Mes": "MAYO", "Curso": "II A", "Rend": 0.5},
    ])
    charts.valor_promedio_agrupado_por(
        df, columna_valor="Rend", agrupar_principal_por="Mes",
        agrupar_secundario_por="Curso", nombre_grafico=png,
    )
    assert _etiquetas_x(espia_figuras[-1]) == ["ABRIL", "MAYO", "OCTUBRE"]


def test_barras_simples_ordena_eje_temporal(png, espia_figuras):
    df = pd.DataFrame([
        {"Versión": "3", "Puntaje": 40.0},
        {"Versión": "1", "Puntaje": 20.0},
        {"Versión": "2", "Puntaje": 30.0},
    ])
    charts.grafico_barras_promedio_por(
        df, columna_valor="Puntaje", agrupar_por="Versión", nombre_grafico=png,
    )
    assert _etiquetas_x(espia_figuras[-1]) == ["1", "2", "3"]


def test_barras_simples_no_crashea_con_mas_de_8_categorias(png):
    df = pd.DataFrame({
        "Curso": [f"C{i}" for i in range(18)],
        "Logro": np.linspace(0.2, 0.9, 18),
    })
    charts.grafico_barras_promedio_por(
        df, columna_valor="Logro", agrupar_por="Curso", nombre_grafico=png,
    )


def test_boxplot_ordena_eje_temporal(png, espia_figuras):
    df = pd.DataFrame([
        {"Mes": "AGOSTO", "Rend": 0.6}, {"Mes": "ABRIL", "Rend": 0.4},
        {"Mes": "AGOSTO", "Rend": 0.7}, {"Mes": "ABRIL", "Rend": 0.5},
    ])
    charts.boxplot_valor_por_curso(
        df, columna_valor="Rend", agrupar_por="Mes", nombre_grafico=png,
    )
    assert _etiquetas_x(espia_figuras[-1]) == ["ABRIL", "AGOSTO"]


def test_boxplot_sin_observaciones_no_crashea(png):
    """Antes: ValueError List of boxplot statistics and 'positions'…"""
    df = pd.DataFrame({"Curso": ["II A", "II B"], "Rend": [np.nan, np.nan]})
    charts.boxplot_valor_por_curso(
        df, columna_valor="Rend", agrupar_por="Curso", nombre_grafico=png,
    )


# ── P0-12: conteos de alumnos ────────────────────────────────────────────

@pytest.fixture
def df_por_subprueba():
    """19 estudiantes × 6 subpruebas en un curso = 114 filas."""
    filas = []
    for i in range(19):
        for sub in ("CT", "FLO", "FNL", "FSF", "ILP", "VSD"):
            filas.append({
                "Curso": "1° BÁSICO",
                "Nombre": f"Alumno {i}",
                "Subprueba": sub,
                "Nivel": "Bajo Riesgo" if i % 2 else "Crítico",
            })
    return pd.DataFrame(filas)


def test_stacked_cuenta_estudiantes_no_filas(df_por_subprueba, png, espia_figuras):
    """El gráfico decía 114 "alumnos" donde hay 19."""
    charts.alumnos_por_nivel_cualitativo(
        df_por_subprueba,
        columna_nivel="Nivel",
        agrupar_por="Curso",
        lista_niveles=["Bajo Riesgo", "Crítico"],
        nombre_grafico=png,
    )
    ax = espia_figuras[-1].axes[0]
    total = sum(b.get_height() for b in ax.patches)
    assert total == 19


def test_stacked_una_fila_por_alumno_no_cambia(png, espia_figuras):
    """Cálculo Veloz: 22 = 9+9+4 debe seguir cuadrando."""
    filas = (
        [{"Curso": "III°C", "Nombre": f"a{i}", "Nivel": "AVANZADO"} for i in range(9)]
        + [{"Curso": "III°C", "Nombre": f"b{i}", "Nivel": "INTERMEDIO"} for i in range(9)]
        + [{"Curso": "III°C", "Nombre": f"c{i}", "Nivel": "INICIAL"} for i in range(4)]
    )
    charts.alumnos_por_nivel_cualitativo(
        pd.DataFrame(filas), columna_nivel="Nivel", agrupar_por="Curso",
        lista_niveles=["AVANZADO", "INTERMEDIO", "INICIAL"], nombre_grafico=png,
    )
    ax = espia_figuras[-1].axes[0]
    assert sum(b.get_height() for b in ax.patches) == 22


def test_stacked_curso_mes_cuenta_estudiantes_y_ordena_meses(png, espia_figuras):
    filas = []
    for mes in ("OCTUBRE", "ABRIL"):
        for i in range(5):
            for asignatura in ("LENGUAJE", "MATEMATICA"):  # 2 filas por alumno
                filas.append({
                    "Curso": "II A", "Mes": mes, "Asignatura": asignatura,
                    "Nombre": f"Alumno {i}", "Logro": "Adecuado",
                })
    charts.alumnos_por_nivel_curso_y_mes(
        pd.DataFrame(filas),
        columna_nivel="Logro", columna_curso="Curso", columna_mes="Mes",
        lista_niveles=("Adecuado",),
        orden_meses=None,
        nombre_grafico=png,
    )
    ax = espia_figuras[-1].axes[0]
    alturas = [b.get_height() for b in ax.patches if b.get_height() > 0]
    assert alturas == [5, 5]          # 5 alumnos por mes, no 10 filas
    assert _etiquetas_x(ax.figure)[:2] == ["ABRIL", "OCTUBRE"]


def test_stacked_curso_mes_no_descarta_meses_fuera_del_orden(png, espia_figuras):
    """MAYO no está en el `orden_meses` default y desaparecía en silencio."""
    filas = [
        {"Curso": "II A", "Mes": "ABRIL", "Nombre": "a", "Logro": "Adecuado"},
        {"Curso": "II A", "Mes": "MAYO", "Nombre": "b", "Logro": "Adecuado"},
    ]
    charts.alumnos_por_nivel_curso_y_mes(
        pd.DataFrame(filas),
        columna_nivel="Logro", columna_curso="Curso", columna_mes="Mes",
        lista_niveles=("Adecuado",),
        nombre_grafico=png,
    )
    assert "MAYO" in _etiquetas_x(espia_figuras[-1])


# ─────────────────────────────────────────────────────────────────────────
# Contraste de las etiquetas sobre los segmentos de color
# (QA piloto SIMCE 2026-07-30, P2-1)
# ─────────────────────────────────────────────────────────────────────────

#: Colores reales de `Indicator.achievement_levels` en producción.
NIVELES_SIMCE = {
    "Insuficiente": "#dc2626",
    "Elemental": "#eab308",
    "Adecuado": "#22c55e",
}
NIVELES_DIA = {
    "Crítico": "#dc2626",
    "Alto Riesgo": "#ea580c",
    "Cierto Riesgo": "#eab308",
    "Bajo Riesgo": "#22c55e",
}


class TestContrasteDeEtiquetas:
    @pytest.mark.parametrize("nivel,color", sorted(
        {**NIVELES_SIMCE, **NIVELES_DIA}.items()
    ))
    def test_siempre_elige_el_color_de_mayor_contraste(self, nivel, color):
        """La garantía dura del helper: nunca deja el peor de los dos."""
        elegido = charts.color_texto_sobre(color)
        otro = (
            charts.TEXTO_SOBRE_OSCURO if elegido == charts.TEXTO_SOBRE_CLARO
            else charts.TEXTO_SOBRE_CLARO
        )
        assert charts.contraste_wcag(color, elegido) >= charts.contraste_wcag(color, otro), (
            f"{nivel} ({color})"
        )

    @pytest.mark.parametrize("nivel,color", [
        ("Elemental / Cierto Riesgo", "#eab308"),   # antes 1.92:1
        ("Adecuado / Bajo Riesgo", "#22c55e"),      # antes 2.28:1
        ("Insuficiente / Crítico", "#dc2626"),
    ])
    def test_los_niveles_que_marco_el_qa_ya_cumplen_aa(self, nivel, color):
        elegido = charts.color_texto_sobre(color)
        assert charts.contraste_wcag(color, elegido) >= charts.CONTRASTE_MINIMO_WCAG, (
            f"{nivel} ({color}) con {elegido}"
        )
        # ...y con el blanco fijo de antes NO cumplían.
        if color != "#dc2626":
            assert charts.contraste_wcag(color, "#ffffff") < charts.CONTRASTE_MINIMO_WCAG

    def test_naranja_alto_riesgo_mejora_aunque_no_llegue_a_aa(self):
        """`#ea580c` (Alto Riesgo, DIA) no alcanza 4.5:1 con NINGÚN texto.

        Es un límite de la paleta, no del helper: la decisión sobre el matiz
        de los niveles es del dueño y quedó fuera de alcance. Lo que sí
        garantizamos es que pasa de 3.2:1 (blanco) a 4.1:1 (oscuro).
        """
        elegido = charts.color_texto_sobre("#ea580c")
        assert elegido == charts.TEXTO_SOBRE_CLARO
        assert (
            charts.contraste_wcag("#ea580c", elegido)
            > charts.contraste_wcag("#ea580c", "#ffffff")
        )

    @pytest.mark.parametrize("color,esperado", [
        ("#eab308", charts.TEXTO_SOBRE_CLARO),    # Elemental / Cierto Riesgo
        ("#22c55e", charts.TEXTO_SOBRE_CLARO),    # Adecuado / Bajo Riesgo
        ("#dc2626", charts.TEXTO_SOBRE_OSCURO),   # Insuficiente / Crítico
        ("#e64b35", charts.TEXTO_SOBRE_OSCURO),   # tomate de la referencia
        ("#1f9e89", charts.TEXTO_SOBRE_CLARO),    # teal de la referencia
        ("#ffffff", charts.TEXTO_SOBRE_CLARO),
        ("#000000", charts.TEXTO_SOBRE_OSCURO),
    ])
    def test_eleccion_por_luminancia(self, color, esperado):
        assert charts.color_texto_sobre(color) == esperado

    def test_color_ilegible_no_revienta(self):
        assert charts.color_texto_sobre("no-es-un-color") == charts.TEXTO_SOBRE_OSCURO

    def test_las_etiquetas_del_stacked_usan_el_color_elegido(
        self, png, espia_figuras
    ):
        filas = (
            [{"Curso": "II A", "Nombre": f"a{i}", "Logro": "Adecuado"} for i in range(3)]
            + [{"Curso": "II A", "Nombre": f"b{i}", "Logro": "Insuficiente"} for i in range(2)]
        )
        charts.alumnos_por_nivel_cualitativo(
            pd.DataFrame(filas), columna_nivel="Logro", agrupar_por="Curso",
            lista_niveles=["Adecuado", "Elemental", "Insuficiente"],
            color_overrides=NIVELES_SIMCE, nombre_grafico=png,
        )
        ax = espia_figuras[-1].axes[0]
        por_texto = {t.get_text(): t.get_color() for t in ax.texts}
        assert por_texto["3"] == charts.TEXTO_SOBRE_CLARO   # verde Adecuado
        assert por_texto["2"] == charts.TEXTO_SOBRE_OSCURO  # rojo Insuficiente

    def test_las_etiquetas_de_composicion_usan_el_color_elegido(
        self, png, espia_figuras
    ):
        filas = (
            [{"Nombre": f"a{i}", "Logro": "Adecuado"} for i in range(6)]
            + [{"Nombre": f"b{i}", "Logro": "Insuficiente"} for i in range(4)]
        )
        charts.composicion_por_nivel(
            pd.DataFrame(filas), columna_nivel="Logro",
            lista_niveles=["Adecuado", "Elemental", "Insuficiente"],
            color_overrides=NIVELES_SIMCE, nombre_grafico=png,
        )
        ax = espia_figuras[-1].axes[0]
        colores = {t.get_text(): t.get_color() for t in ax.texts}
        assert colores["60%\n(6)"] == charts.TEXTO_SOBRE_CLARO
        assert colores["40%\n(4)"] == charts.TEXTO_SOBRE_OSCURO
