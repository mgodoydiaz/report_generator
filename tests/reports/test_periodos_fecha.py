"""Tests del tipo de dato de dimensión "fecha" en el resolver de períodos.

Caso que lo motivó: Fluidez Lectora NO tiene dimensión "Año" — el tiempo
vive solo en la columna "Fecha" — así que los informes semestral y anual
salían "estructuralmente" no disponibles. Con una columna de tipo fecha
el resolver deriva el año y el mes y ambos vuelven a funcionar.

Funciones puras: no tocan DB ni filesystem. `hoy` se inyecta siempre.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backend.rgenerator.reports.periodos import (
    clave_temporal,
    clave_temporal_detallada,
    detectar_columnas_temporales,
    detectar_columnas_temporales_df,
    parsear_fecha,
    resolver_periodo,
    tasa_parseo_fecha,
)


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture
def df_fluidez():
    """Réplica de los datos reales de Fluidez Lectora: NO hay dimensión Año.

    El tiempo vive solo en "Fecha" (ISO con hora, como la guarda el ETL) y
    en "N Prueba", que además es texto ("Ensayo 1") y no aporta orden.
    """
    return pd.DataFrame([
        {"Curso": "I A", "Fecha": "2026-04-09 00:00:00", "N Prueba": "Ensayo 1", "PPM": 120},
        {"Curso": "I A", "Fecha": "2026-04-13 00:00:00", "N Prueba": "Ensayo 1", "PPM": 131},
        {"Curso": "I B", "Fecha": "2026-04-02 00:00:00", "N Prueba": "Ensayo 1", "PPM": 118},
        {"Curso": "I B", "Fecha": "2025-10-23 00:00:00", "N Prueba": "Ensayo 2", "PPM": 99},
        {"Curso": "I B", "Fecha": "2026-09-15 00:00:00", "N Prueba": "Ensayo 3", "PPM": 140},
    ])


@pytest.fixture
def df_simce():
    """Indicador con Año/Mes explícitos — no debe cambiar de comportamiento."""
    return pd.DataFrame([
        {"Curso": "II A", "Año": "2025", "Mes": "ABRIL", "N Prueba": "1", "Logro": 0.4},
        {"Curso": "II A", "Año": "2025", "Mes": "AGOSTO", "N Prueba": "3", "Logro": 0.5},
        {"Curso": "II B", "Año": "2025", "Mes": "NOVIEMBRE", "N Prueba": "5", "Logro": 0.6},
        {"Curso": "II A", "Año": "2026", "Mes": "MARZO", "N Prueba": "1", "Logro": 0.7},
    ])


# ─────────────────────────────────────────────────────────────────────────
# Parseo
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestParsearFecha:
    @pytest.mark.parametrize("valor,esperado", [
        # ISO, con y sin hora
        ("2026-04-07", date(2026, 4, 7)),
        ("2026-04-07 00:00:00", date(2026, 4, 7)),
        ("2026-04-07T10:30:00", date(2026, 4, 7)),
        ("2026/04/07", date(2026, 4, 7)),
        # Latino: el día va PRIMERO
        ("07-04-2026", date(2026, 4, 7)),
        ("07/04/2026", date(2026, 4, 7)),
        ("7/4/2026", date(2026, 4, 7)),
        # Nativos
        (pd.Timestamp("2026-04-07"), date(2026, 4, 7)),
        (date(2026, 4, 7), date(2026, 4, 7)),
    ])
    def test_formatos_validos(self, valor, esperado):
        assert parsear_fecha(valor) == esperado

    @pytest.mark.parametrize("valor", [
        None, "", "   ", "abril", "2026", "2026-04", "13", 13, 13.0,
        "2026-13-01",   # mes inexistente
        "2026-02-30",   # dia inexistente
        "32-01-2026",   # dia inexistente (latino)
        "23467191-K",   # un RUT no es una fecha
        pd.NaT, float("nan"),
    ])
    def test_valores_invalidos(self, valor):
        assert parsear_fecha(valor) is None

    def test_no_confunde_el_dia_con_el_mes(self):
        # "07-04-2026" es 7 de ABRIL. pandas, con inferencia, lo leería
        # como 4 de julio: por eso el parseo es propio y determinista.
        assert parsear_fecha("07-04-2026").month == 4
        assert parsear_fecha("07-04-2026").day == 7

    def test_tasa_de_parseo(self):
        assert tasa_parseo_fecha(["2026-04-07", "2026-04-08"]) == 1.0
        assert tasa_parseo_fecha(["2026-04-07", "hola"]) == 0.5
        assert tasa_parseo_fecha(["hola", "chao"]) == 0.0
        assert tasa_parseo_fecha([]) == 0.0
        # Los vacíos no cuentan en el denominador
        assert tasa_parseo_fecha(["2026-04-07", "", None]) == 1.0


# ─────────────────────────────────────────────────────────────────────────
# Detección
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestDetectarColumnaFecha:
    def test_por_nombre_y_valores(self, df_fluidez):
        cols = detectar_columnas_temporales_df(df_fluidez)
        assert cols["fecha"] == "Fecha"
        assert cols["anio"] is None          # FL no tiene dimensión Año
        assert cols["mes_like"] == "Fecha"   # la fecha también aporta el mes

    def test_por_metadata_aunque_el_nombre_no_delate(self):
        cols = detectar_columnas_temporales(
            ["Curso", "Aplicación"], tipos={"Aplicación": "date"}
        )
        assert cols["fecha"] == "Aplicación"
        assert cols["mes_like"] == "Aplicación"

    def test_metadata_acepta_el_alias_en_espanol(self):
        cols = detectar_columnas_temporales(["Toma"], tipos={"Toma": "fecha"})
        assert cols["fecha"] == "Toma"

    def test_metadata_tolera_tildes_en_la_clave(self):
        cols = detectar_columnas_temporales(
            ["Aplicación"], tipos={"Aplicacion": "date"}
        )
        assert cols["fecha"] == "Aplicación"

    def test_heuristica_sin_metadata(self):
        df = pd.DataFrame([{"Curso": "I A", "Toma": "2026-04-07", "PPM": 120}])
        assert detectar_columnas_temporales_df(df)["fecha"] == "Toma"

    def test_una_columna_fecha_con_basura_no_se_marca(self):
        # El nombre propone, los valores disponen (umbral 90%).
        df = pd.DataFrame([
            {"Fecha": v} for v in ["sin dato", "pendiente", "s/i", "2026-04-07"]
        ])
        assert detectar_columnas_temporales_df(df)["fecha"] is None

    def test_columna_de_texto_no_se_confunde_con_fecha(self):
        df = pd.DataFrame([{"RUT": "23467191-K", "Curso": "I A"}])
        assert detectar_columnas_temporales_df(df)["fecha"] is None

    def test_el_anio_explicito_gana_sobre_la_fecha(self, df_simce):
        cols = detectar_columnas_temporales_df(df_simce)
        assert cols["anio"] == "Año"
        assert cols["mes_like"] == "Mes"
        assert cols["fecha"] is None


@pytest.mark.unit
class TestDerivarAnioYMesDeLaFecha:
    def test_clave_temporal_deriva_anio_y_mes(self, df_fluidez):
        cols = detectar_columnas_temporales_df(df_fluidez)
        assert clave_temporal({"Fecha": "2026-04-13 00:00:00"}, cols)[:2] == (2026, 4)

    def test_clave_detallada_incluye_el_dia(self, df_fluidez):
        cols = detectar_columnas_temporales_df(df_fluidez)
        assert clave_temporal_detallada(
            {"Fecha": "2026-04-13 00:00:00"}, cols
        )[:3] == (2026, 4, 13)

    def test_sin_columna_fecha_el_dia_es_menos_uno(self):
        cols = {"anio": "Año", "mes_like": "Mes", "ordinal": None, "fecha": None}
        assert clave_temporal_detallada(
            {"Año": "2025", "Mes": "ABRIL"}, cols
        ) == (2025, 4, -1, -1)


# ─────────────────────────────────────────────────────────────────────────
# Resolución de períodos con SOLO una columna fecha
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestFluidezLectoraSoloConFecha:
    def test_ultima_prueba_ordena_por_fecha_real(self, df_fluidez):
        res = resolver_periodo(df_fluidez, {"tipo": "ultima_prueba"}, date(2026, 12, 1))
        assert res.disponible is True
        assert res.filtros["Fecha"] == "2026-09-15 00:00:00"
        assert res.descripcion.startswith("15-09-2026")

    def test_el_orden_string_daria_otra_respuesta(self):
        # Con fechas latinas el orden alfabético elige mal: "13-…" > "09-…"
        # como string, pero mayo es posterior a abril.
        df = pd.DataFrame([
            {"Curso": "I A", "Fecha": "13-04-2026", "PPM": 100},
            {"Curso": "I A", "Fecha": "09-05-2026", "PPM": 110},
        ])
        res = resolver_periodo(df, {"tipo": "ultima_prueba"}, date(2026, 12, 1))
        assert res.filtros["Fecha"] == "09-05-2026"
        assert res.descripcion == "09-05-2026"

    def test_anual_deriva_el_anio_de_la_fecha(self, df_fluidez):
        res = resolver_periodo(df_fluidez, {"tipo": "anual"}, date(2026, 7, 30))
        assert res.disponible is True
        assert res.tipo_layout == "historico"
        assert res.descripcion == "2026"
        assert res.filtros["Fecha"] == [
            "2026-04-02 00:00:00", "2026-04-09 00:00:00",
            "2026-04-13 00:00:00", "2026-09-15 00:00:00",
        ]

    def test_semestral_deriva_anio_y_mes_de_la_fecha(self, df_fluidez):
        res = resolver_periodo(df_fluidez, {"tipo": "semestral"}, date(2026, 7, 30))
        assert res.disponible is True
        assert res.descripcion == "1er semestre 2026 (enero–julio)"
        # Abril entra; septiembre 2026 (2º semestre) y octubre 2025 quedan fuera
        assert res.filtros["Fecha"] == [
            "2026-04-02 00:00:00", "2026-04-09 00:00:00", "2026-04-13 00:00:00",
        ]

    def test_semestral_del_segundo_semestre(self, df_fluidez):
        res = resolver_periodo(df_fluidez, {"tipo": "semestral"}, date(2026, 10, 1))
        assert res.disponible is True
        assert res.filtros["Fecha"] == ["2026-09-15 00:00:00"]

    def test_semestral_y_anual_no_dan_el_mismo_recorte(self, df_fluidez):
        semestral = resolver_periodo(df_fluidez, {"tipo": "semestral"}, date(2026, 10, 1))
        anual = resolver_periodo(df_fluidez, {"tipo": "anual"}, date(2026, 10, 1))
        assert semestral.filtros != anual.filtros

    def test_anual_sin_datos_del_anio_en_curso(self, df_fluidez):
        res = resolver_periodo(df_fluidez, {"tipo": "anual"}, date(2030, 1, 15))
        assert res.disponible is False
        assert "2030" in res.motivo

    def test_personalizado_con_rango_usa_la_fecha(self, df_fluidez):
        res = resolver_periodo(df_fluidez, {
            "tipo": "personalizado",
            "fecha_inicio": "2026-01", "fecha_fin": "2026-06",
        }, date(2026, 7, 30))
        assert res.disponible is True
        assert res.filtros["Fecha"] == [
            "2026-04-02 00:00:00", "2026-04-09 00:00:00", "2026-04-13 00:00:00",
        ]

    def test_metadata_habilita_una_columna_de_nombre_neutro(self):
        df = pd.DataFrame([
            {"Curso": "I A", "Toma": "01-03-2026", "PPM": 100},
            {"Curso": "I A", "Toma": "01-06-2026", "PPM": 120},
        ])
        res = resolver_periodo(
            df, {"tipo": "anual"}, date(2026, 7, 30), tipos={"Toma": "date"}
        )
        assert res.disponible is True
        assert res.filtros["Toma"] == ["01-03-2026", "01-06-2026"]


# ─────────────────────────────────────────────────────────────────────────
# No regresión: indicadores con Año/Mes explícitos
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestNoRegresionSinFecha:
    def test_simce_anual(self, df_simce):
        res = resolver_periodo(df_simce, {"tipo": "anual"}, date(2026, 7, 29))
        assert res.filtros == {"Año": "2026"}

    def test_simce_semestral(self, df_simce):
        res = resolver_periodo(df_simce, {"tipo": "semestral"}, date(2026, 5, 10))
        assert res.filtros == {"Año": "2026", "Mes": ["MARZO"]}

    def test_simce_ultima_prueba(self, df_simce):
        res = resolver_periodo(df_simce, {"tipo": "ultima_prueba"}, date(2026, 7, 29))
        assert res.filtros == {"Año": "2026", "Mes": "MARZO", "N Prueba": "1"}

    def test_sin_ninguna_columna_temporal(self):
        df = pd.DataFrame([{"Curso": "I A", "Logro": 0.3}])
        res = resolver_periodo(df, {"tipo": "anual"}, date(2026, 7, 29))
        assert res.disponible is False
        assert "año" in res.motivo.lower()


@pytest.mark.unit
class TestConAnioYFechaALaVez:
    """Cálculo Veloz: tiene Año, Mes, N Prueba **y** Fecha.

    Con Año/Mes/N Prueba la evaluación ya queda identificada; fijar además
    el día acotaría de más (una prueba aplicada en varias jornadas perdería
    filas). La fecha solo entra al filtro cuando es la fuente del año.
    """

    @pytest.fixture
    def df_calculo_veloz(self):
        return pd.DataFrame([
            {"Curso": "I A", "Año": "2025", "Mes": "OCTUBRE", "N Prueba": "2",
             "Fecha": "2025-10-23 00:00:00", "Puntaje": 30},
            {"Curso": "I A", "Año": "2025", "Mes": "OCTUBRE", "N Prueba": "2",
             "Fecha": "2025-10-24 00:00:00", "Puntaje": 28},
            {"Curso": "I A", "Año": "2025", "Mes": "AGOSTO", "N Prueba": "1",
             "Fecha": "2025-08-12 00:00:00", "Puntaje": 25},
        ])

    def test_ultima_prueba_no_fija_el_dia(self, df_calculo_veloz):
        res = resolver_periodo(df_calculo_veloz, {"tipo": "ultima_prueba"},
                               date(2025, 12, 1))
        assert res.filtros == {"Año": "2025", "Mes": "OCTUBRE", "N Prueba": "2"}
        assert res.descripcion == "OCTUBRE 2025 (prueba 2)"

    def test_anual_usa_la_columna_anio(self, df_calculo_veloz):
        res = resolver_periodo(df_calculo_veloz, {"tipo": "anual"}, date(2025, 6, 1))
        assert res.filtros == {"Año": "2025"}

    def test_semestral_usa_anio_y_mes(self, df_calculo_veloz):
        res = resolver_periodo(df_calculo_veloz, {"tipo": "semestral"},
                               date(2025, 10, 1))
        assert res.filtros == {"Año": "2025", "Mes": ["AGOSTO", "OCTUBRE"]}
