"""Tests del semáforo semántico de niveles de logro (`reports/colores.py`).

Lo que se protege acá:

1. El color de un nivel sale de su NOMBRE, no de su posición. Invertir
   `lista_niveles` en un esquema ya no puede invertir el semáforo (era el
   bug P1-5 del QA 2026-08-03: el formato oficial DIA pintaba Inicial de
   verde-agua y Avanzado de tomate según el orden declarado).
2. Los niveles reales de DIA (`Inicial` / `Intermedio` / `Avanzado`, en
   `backend/rgenerator/reports/dia/esquema.json`) dan rojo / amarillo /
   verde pastel.
3. El matching tolera mayúsculas, tildes y espacios sobrantes.
4. `color_overrides` y `lista_paleta` conservan su precedencia sobre el
   mapa semántico.
5. Los tonos pastel siguen admitiendo etiquetas legibles (WCAG AA 4.5:1)
   con el color que elige `charts.color_texto_sobre`.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_hex

from backend.rgenerator.reports import charts, colores

pytestmark = pytest.mark.unit


#: Niveles de DIA tal como los declara `dia/esquema.json` (mejor → peor).
NIVELES_DIA = ["Avanzado", "Intermedio", "Inicial"]

#: El mapping que el usuario pidió: rojo el más bajo, amarillo el medio,
#: verde el más alto — en pastel.
ESPERADO_DIA = {
    "Inicial": "#e57373",
    "Intermedio": "#f6d55c",
    "Avanzado": "#81c784",
}


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


def _colores_por_serie(fig) -> dict[str, str]:
    """`{etiqueta de leyenda: color hex}` de los contenedores de barras."""
    ax = fig.axes[0]
    salida = {}
    for cont in ax.containers:
        etiqueta = cont.get_label()
        if not etiqueta or etiqueta.startswith("_"):
            continue
        salida[etiqueta] = to_hex(cont.patches[0].get_facecolor())
    return salida


# ── El mapping nivel → color ─────────────────────────────────────────────

class TestMappingSemantico:

    @pytest.mark.parametrize("nivel,hex_esperado", sorted(ESPERADO_DIA.items()))
    def test_niveles_dia(self, nivel, hex_esperado):
        assert colores.color_semantico_nivel(nivel) == hex_esperado

    @pytest.mark.parametrize("nivel,hex_esperado", [
        # SIMCE — 3 niveles
        ("Insuficiente", "#e57373"),
        ("Elemental", "#f6d55c"),
        ("Adecuado", "#81c784"),
        # Escala "logrado"
        ("No Logrado", "#e57373"),
        ("Medianamente Logrado", "#f6d55c"),
        ("Logrado", "#81c784"),
        # IDEL — 4 niveles: la escala se extiende con naranja
        ("Crítico", "#e57373"),
        ("Alto Riesgo", "#efa06b"),
        ("Cierto Riesgo", "#f6d55c"),
        ("Bajo Riesgo", "#81c784"),
    ])
    def test_otras_familias_de_niveles(self, nivel, hex_esperado):
        assert colores.color_semantico_nivel(nivel) == hex_esperado

    @pytest.mark.parametrize("variante", [
        "inicial", "INICIAL", "  Inicial  ", "Inicial", "iNiCiAl",
    ])
    def test_matching_insensible_a_mayusculas_y_espacios(self, variante):
        assert colores.color_semantico_nivel(variante) == ESPERADO_DIA["Inicial"]

    @pytest.mark.parametrize("variante", ["Crítico", "CRITICO", "critico", "Critico"])
    def test_matching_insensible_a_tildes(self, variante):
        assert colores.color_semantico_nivel(variante) == "#e57373"

    def test_nombre_desconocido_no_inventa_color(self):
        assert colores.color_semantico_nivel("Eje Temático") is None
        assert colores.color_semantico_nivel(None) is None

    def test_bajo_riesgo_es_verde_pese_a_contener_bajo(self):
        """En IDEL "Bajo Riesgo" es el MEJOR nivel: el match es por nombre
        completo, no por la palabra suelta."""
        assert colores.color_semantico_nivel("Bajo Riesgo") == colores.VERDE_PASTEL

    def test_el_esquema_dia_declara_los_niveles_que_el_mapa_conoce(self):
        """Guardia contra la deriva: si alguien renombra los niveles en
        `dia/esquema.json`, el mapa semántico deja de aplicar y este test
        avisa antes de que el informe salga con colores por posición."""
        esquema_path = (
            Path(__file__).resolve().parents[2]
            / "backend" / "rgenerator" / "reports" / "dia" / "esquema.json"
        )
        esquema = json.loads(esquema_path.read_text(encoding="utf-8"))
        declarados = [
            s["params"]["lista_niveles"]
            for s in esquema["secciones_fijas"]
            if "lista_niveles" in (s.get("params") or {})
        ]
        assert declarados, "el esquema DIA ya no declara lista_niveles"
        for niveles in declarados:
            assert sorted(niveles) == sorted(NIVELES_DIA)
            for nivel in niveles:
                assert colores.color_semantico_nivel(nivel) == ESPERADO_DIA[nivel]


# ── Escala y resolución de precedencias ──────────────────────────────────

class TestEscalaYPrecedencia:

    def test_escala_de_3_es_rojo_amarillo_verde(self):
        assert colores.escala_pastel(3) == ["#e57373", "#f6d55c", "#81c784"]

    def test_escala_de_4_intercala_naranja(self):
        assert colores.escala_pastel(4) == [
            "#e57373", "#efa06b", "#f6d55c", "#81c784",
        ]

    def test_mejor_primero_invierte_la_escala(self):
        assert colores.escala_pastel(3, mejor_primero=True) == [
            "#81c784", "#f6d55c", "#e57373",
        ]

    def test_cantidad_fuera_de_rango_cae_a_la_escala_de_5(self):
        assert colores.escala_pastel(9) == colores.ESCALAS_PASTEL[5]

    def test_orden_declarado_no_cambia_el_color(self):
        """Mejor→peor y peor→mejor deben dar EXACTAMENTE el mismo mapa."""
        a = colores.colores_para_niveles(NIVELES_DIA, mejor_primero=True)
        b = colores.colores_para_niveles(NIVELES_DIA[::-1], mejor_primero=False)
        assert a == b == ESPERADO_DIA

    def test_color_overrides_gana_sobre_el_mapa_semantico(self):
        out = colores.colores_para_niveles(
            NIVELES_DIA, color_overrides={"Inicial": "#dc2626"},
        )
        assert out["Inicial"] == "#dc2626"
        assert out["Avanzado"] == ESPERADO_DIA["Avanzado"]

    def test_color_overrides_matchea_sin_tildes_ni_mayusculas(self):
        out = colores.colores_para_niveles(
            ["Crítico", "Bajo Riesgo"], color_overrides={"CRITICO": "#dc2626"},
        )
        assert out["Crítico"] == "#dc2626"

    def test_lista_paleta_explicita_gana_sobre_el_mapa_semantico(self):
        out = colores.colores_para_niveles(
            NIVELES_DIA, lista_paleta=["#111111", "#222222", "#333333"],
        )
        assert out == {
            "Avanzado": "#111111",
            "Intermedio": "#222222",
            "Inicial": "#333333",
        }

    def test_nivel_desconocido_cae_al_fallback_posicional(self):
        out = colores.colores_para_niveles(
            ["Avanzado", "Otro", "Inicial"], mejor_primero=True,
        )
        assert out["Avanzado"] == ESPERADO_DIA["Avanzado"]
        assert out["Inicial"] == ESPERADO_DIA["Inicial"]
        # "Otro" está en la posición 1 de una escala mejor→peor de 3.
        assert out["Otro"] == colores.escala_pastel(3, mejor_primero=True)[1]


# ── Contraste de las etiquetas sobre los tonos pastel ────────────────────

class TestContraste:

    @pytest.mark.parametrize("color", sorted(set(colores.COLORES_NIVEL_LOGRO.values())))
    def test_cada_tono_admite_una_etiqueta_AA(self, color):
        elegido = charts.color_texto_sobre(color)
        assert charts.contraste_wcag(color, elegido) >= charts.CONTRASTE_MINIMO_WCAG

    @pytest.mark.parametrize("color", sorted(set(colores.COLORES_NIVEL_LOGRO.values())))
    def test_los_pasteles_piden_texto_oscuro(self, color):
        """Todos los tonos son claros: la etiqueta va en gris oscuro, no en
        blanco (el blanco sobre el amarillo daba 2,3:1 — QA P1-5)."""
        assert charts.color_texto_sobre(color) == charts.TEXTO_SOBRE_CLARO


# ── Los gráficos del informe DIA ─────────────────────────────────────────

@pytest.fixture
def df_dia():
    """Estudiantes de 2 cursos con los 3 niveles de DIA."""
    filas = []
    for curso in ("II A", "II B"):
        for nivel, n in (("Inicial", 3), ("Intermedio", 4), ("Avanzado", 5)):
            filas += [
                {"Curso": curso, "Nombre": f"{curso}-{nivel}-{i}", "Nivel Logro": nivel}
                for i in range(n)
            ]
    return pd.DataFrame(filas)


class TestGraficosDIA:

    def test_stacked_pinta_cada_nivel_con_su_color(self, df_dia, png, espia_figuras):
        charts.alumnos_por_nivel_cualitativo(
            df_dia, columna_nivel="Nivel Logro", agrupar_por="Curso",
            lista_niveles=NIVELES_DIA, nombre_grafico=png,
        )
        assert _colores_por_serie(espia_figuras[-1]) == ESPERADO_DIA

    def test_stacked_ignora_el_orden_declarado(self, df_dia, png, espia_figuras):
        """Mismo gráfico con `lista_niveles` invertida: mismos colores."""
        charts.alumnos_por_nivel_cualitativo(
            df_dia, columna_nivel="Nivel Logro", agrupar_por="Curso",
            lista_niveles=NIVELES_DIA[::-1], nombre_grafico=png,
        )
        assert _colores_por_serie(espia_figuras[-1]) == ESPERADO_DIA

    def test_composicion_pinta_cada_nivel_con_su_color(
        self, df_dia, png, espia_figuras
    ):
        charts.composicion_por_nivel(
            df_dia, columna_nivel="Nivel Logro",
            lista_niveles=NIVELES_DIA, nombre_grafico=png,
        )
        assert _colores_por_serie(espia_figuras[-1]) == ESPERADO_DIA

    def test_los_dos_graficos_coinciden_en_la_misma_pagina(
        self, df_dia, png, espia_figuras
    ):
        charts.alumnos_por_nivel_cualitativo(
            df_dia, columna_nivel="Nivel Logro", agrupar_por="Curso",
            lista_niveles=NIVELES_DIA, nombre_grafico=png,
        )
        charts.composicion_por_nivel(
            df_dia, columna_nivel="Nivel Logro",
            lista_niveles=NIVELES_DIA, nombre_grafico=png,
        )
        stacked, composicion = espia_figuras[-2], espia_figuras[-1]
        assert _colores_por_serie(stacked) == _colores_por_serie(composicion)

    def test_achievement_levels_inyectados_siguen_ganando(
        self, df_dia, png, espia_figuras
    ):
        """Un informe que inyecta `Indicator.achievement_levels` conserva sus
        colores oficiales: el pastel es el DEFAULT, no una imposición."""
        oficiales = {
            "Inicial": "#dc2626", "Intermedio": "#eab308", "Avanzado": "#22c55e",
        }
        charts.alumnos_por_nivel_cualitativo(
            df_dia, columna_nivel="Nivel Logro", agrupar_por="Curso",
            lista_niveles=NIVELES_DIA, color_overrides=oficiales,
            nombre_grafico=png,
        )
        assert _colores_por_serie(espia_figuras[-1]) == oficiales
