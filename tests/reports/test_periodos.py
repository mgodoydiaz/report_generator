"""Tests del resolver de períodos (`backend/rgenerator/reports/periodos.py`).

Funciones puras: no tocan DB ni filesystem. `hoy` se inyecta siempre para
que los tests no dependan de la fecha real.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backend.rgenerator.reports.periodos import (
    HITO_A_MES,
    MESES_A_NUMERO,
    VERSION_A_MES,
    a_numero_mes,
    clave_temporal,
    detectar_columnas_temporales,
    parsear_ym,
    resolver_periodo,
    resolver_periodo_multi,
    semestre_de_mes,
    tipo_mes_like,
)


# ─────────────────────────────────────────────────────────────────────────
# Mapeos
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestMapeos:
    def test_hito_a_mes_es_el_protocolo_de_la_fundacion(self):
        assert HITO_A_MES == {"INICIO": 3, "INTERMEDIO": 6, "CIERRE": 11}

    def test_version_a_mes_idel(self):
        assert VERSION_A_MES == {"v1": 4, "v2": 8, "v3": 11}

    def test_doce_meses_mas_alias_setiembre(self):
        assert len(set(MESES_A_NUMERO.values())) == 12
        assert MESES_A_NUMERO["SETIEMBRE"] == MESES_A_NUMERO["SEPTIEMBRE"] == 9

    @pytest.mark.parametrize("valor,esperado", [
        ("MARZO", 3), ("marzo", 3), ("Marzo", 3),
        ("3", 3), ("03", 3), (3, 3), (3.0, 3),
        ("NOVIEMBRE", 11),
        ("INICIO", 3), ("INTERMEDIO", 6), ("CIERRE", 11),
        ("DIAGNOSTICO", 3), ("Diagnóstico", 3),  # alias del pipeline DIA
        ("v1", 4), ("V2", 8), ("v3", 11),
        ("2025-11-04", 11), ("04/11/2025", 11),
        ("", None), (None, None), ("cualquier cosa", None),
    ])
    def test_a_numero_mes(self, valor, esperado):
        assert a_numero_mes(valor) == esperado

    def test_semestre_escolar_chileno(self):
        assert [semestre_de_mes(m) for m in range(1, 8)] == [1] * 7
        assert [semestre_de_mes(m) for m in range(8, 13)] == [2] * 5

    @pytest.mark.parametrize("texto,esperado", [
        ("2026-03", (2026, 3)), ("2026-3", (2026, 3)), ("2026/11", (2026, 11)),
        ("2026", (2026, 0)), ("2026-13", None), ("marzo", None), (None, None),
        # Fechas completas: es lo que manda el frontend y lo que usó el QA
        # adversarial. Antes devolvían None y el rango se descartaba EN
        # SILENCIO (P0-2 del piloto SIMCE).
        ("2019-01-01", (2019, 1)), ("2019-12-31", (2019, 12)),
        ("07-04-2026", (2026, 4)), ("2026/03/15", (2026, 3)),
        ("", None), ("   ", None),
    ])
    def test_parsear_ym(self, texto, esperado):
        assert parsear_ym(texto) == esperado


# ─────────────────────────────────────────────────────────────────────────
# Detección de columnas
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestDetectarColumnas:
    def test_caso_simce(self):
        cols = detectar_columnas_temporales(["Curso", "Nombre", "Año", "Mes", "N Prueba"])
        assert cols == {
            "anio": "Año", "mes_like": "Mes", "ordinal": "N Prueba", "fecha": None
        }

    def test_anio_sin_tilde_y_year(self):
        assert detectar_columnas_temporales(["Anio"])["anio"] == "Anio"
        assert detectar_columnas_temporales(["Year"])["anio"] == "Year"

    def test_preferencia_mes_sobre_fecha_hito_version(self):
        cols = ["Versión", "Hito", "Fecha", "Mes"]
        assert detectar_columnas_temporales(cols)["mes_like"] == "Mes"
        assert detectar_columnas_temporales(["Versión", "Hito", "Fecha"])["mes_like"] == "Fecha"
        assert detectar_columnas_temporales(["Versión", "Hito"])["mes_like"] == "Hito"
        assert detectar_columnas_temporales(["Versión"])["mes_like"] == "Versión"

    def test_ordinal_prueba_o_ensayo(self):
        assert detectar_columnas_temporales(["N° Prueba"])["ordinal"] == "N° Prueba"
        assert detectar_columnas_temporales(["Ensayo"])["ordinal"] == "Ensayo"

    def test_sin_columnas_temporales(self):
        assert detectar_columnas_temporales(["Curso", "RUT", "Logro"]) == {
            "anio": None, "mes_like": None, "ordinal": None, "fecha": None
        }

    def test_no_confunde_palabras_que_contienen_ano(self):
        # "Plano" contiene "ano" como substring pero no es un año
        assert detectar_columnas_temporales(["Plano", "Año"])["anio"] == "Año"


@pytest.mark.unit
class TestClaveTemporal:
    def test_completa(self):
        cols = {"anio": "Año", "mes_like": "Mes", "ordinal": "N Prueba"}
        row = {"Año": "2025", "Mes": "NOVIEMBRE", "N Prueba": "5"}
        assert clave_temporal(row, cols) == (2025, 11, 5)

    def test_faltantes_degradan_a_menos_uno(self):
        cols = {"anio": "Año", "mes_like": "Mes", "ordinal": None}
        assert clave_temporal({"Año": "", "Mes": "zzz"}, cols) == (-1, -1, -1)

    def test_ordena_cronologicamente(self):
        cols = {"anio": "Año", "mes_like": "Mes", "ordinal": None}
        claves = [
            clave_temporal({"Año": "2025", "Mes": "ABRIL"}, cols),
            clave_temporal({"Año": "2026", "Mes": "MARZO"}, cols),
            clave_temporal({"Año": "2025", "Mes": "NOVIEMBRE"}, cols),
        ]
        assert max(claves) == (2026, 3, -1)


# ─────────────────────────────────────────────────────────────────────────
# Fixtures de datos
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture
def df_simce():
    """3 pruebas de 2025 + 1 de 2026, con Año/Mes/N Prueba."""
    return pd.DataFrame([
        {"Curso": "II A", "Año": "2025", "Mes": "ABRIL", "N Prueba": "1", "Logro": 0.4},
        {"Curso": "II A", "Año": "2025", "Mes": "AGOSTO", "N Prueba": "3", "Logro": 0.5},
        {"Curso": "II B", "Año": "2025", "Mes": "NOVIEMBRE", "N Prueba": "5", "Logro": 0.6},
        {"Curso": "II A", "Año": "2026", "Mes": "MARZO", "N Prueba": "1", "Logro": 0.7},
    ])


@pytest.fixture
def df_solo_ordinal():
    return pd.DataFrame([
        {"Curso": "I A", "N Prueba": "1", "Logro": 0.3},
        {"Curso": "I A", "N Prueba": "4", "Logro": 0.8},
    ])


@pytest.fixture
def df_sin_tiempo():
    return pd.DataFrame([{"Curso": "I A", "Logro": 0.3}, {"Curso": "I B", "Logro": 0.5}])


# ─────────────────────────────────────────────────────────────────────────
# ultima_prueba
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestUltimaPrueba:
    def test_con_mes_y_anio(self, df_simce):
        res = resolver_periodo(df_simce, {"tipo": "ultima_prueba"}, date(2026, 7, 29))
        assert res.disponible is True
        assert res.tipo_layout == "evaluacion"
        # 2026/MARZO es la clave máxima
        assert res.filtros == {"Año": "2026", "Mes": "MARZO", "N Prueba": "1"}
        assert "MARZO 2026" in res.descripcion

    def test_descripcion_formato_mes_anio(self):
        df = pd.DataFrame([{"Año": "2025", "Mes": "NOVIEMBRE", "Logro": 1}])
        res = resolver_periodo(df, {"tipo": "ultima_prueba"}, date(2026, 7, 29))
        assert res.descripcion == "NOVIEMBRE 2025"

    def test_solo_ordinal(self, df_solo_ordinal):
        res = resolver_periodo(df_solo_ordinal, {"tipo": "ultima_prueba"}, date(2026, 7, 29))
        assert res.disponible is True
        assert res.filtros == {"N Prueba": "4"}
        assert res.tipo_layout == "evaluacion"
        assert "4" in res.descripcion

    def test_sin_dimension_temporal_no_disponible(self, df_sin_tiempo):
        res = resolver_periodo(df_sin_tiempo, {"tipo": "ultima_prueba"}, date(2026, 7, 29))
        assert res.disponible is False
        assert res.filtros == {}
        assert "dimensión temporal" in res.motivo

    def test_df_vacio_no_disponible(self):
        df = pd.DataFrame(columns=["Año", "Mes"])
        res = resolver_periodo(df, {"tipo": "ultima_prueba"}, date(2026, 7, 29))
        assert res.disponible is False
        assert "Sin datos" in res.motivo


# ─────────────────────────────────────────────────────────────────────────
# anual
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestAnual:
    def test_anio_en_curso(self, df_simce):
        res = resolver_periodo(df_simce, {"tipo": "anual"}, date(2026, 7, 29))
        assert res.disponible is True
        assert res.filtros == {"Año": "2026"}
        assert res.tipo_layout == "historico"
        assert res.descripcion == "2026"

    def test_sin_datos_del_anio_en_curso(self, df_simce):
        res = resolver_periodo(df_simce, {"tipo": "anual"}, date(2030, 1, 15))
        assert res.disponible is False
        assert "Sin datos del año en curso" in res.motivo
        assert res.tipo_layout == "historico"

    def test_sin_columna_de_anio(self, df_solo_ordinal):
        res = resolver_periodo(df_solo_ordinal, {"tipo": "anual"}, date(2026, 7, 29))
        assert res.disponible is False
        assert "dimensión de año" in res.motivo


# ─────────────────────────────────────────────────────────────────────────
# semestral
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestSemestral:
    def test_primer_semestre_con_datos(self, df_simce):
        res = resolver_periodo(df_simce, {"tipo": "semestral"}, date(2026, 5, 10))
        assert res.disponible is True
        assert res.tipo_layout == "historico"
        assert res.filtros["Año"] == "2026"
        assert res.filtros["Mes"] == ["MARZO"]
        assert res.descripcion == "1er semestre 2026 (enero–julio)"

    def test_segundo_semestre_sin_datos(self, df_simce):
        # 2026 solo tiene MARZO (1er semestre) → el 2º semestre no aplica
        res = resolver_periodo(df_simce, {"tipo": "semestral"}, date(2026, 9, 1))
        assert res.disponible is False
        assert "2º semestre 2026" in res.motivo

    def test_segundo_semestre_de_2025_agrupa_agosto_y_noviembre(self, df_simce):
        res = resolver_periodo(df_simce, {"tipo": "semestral"}, date(2025, 12, 1))
        assert res.disponible is True
        assert res.filtros["Año"] == "2025"
        assert res.filtros["Mes"] == ["AGOSTO", "NOVIEMBRE"]
        assert res.descripcion == "2º semestre 2025 (agosto–diciembre)"

    def test_sin_mes_like_no_disponible(self):
        df = pd.DataFrame([{"Año": "2026", "N Prueba": "1", "Logro": 1}])
        res = resolver_periodo(df, {"tipo": "semestral"}, date(2026, 5, 10))
        assert res.disponible is False
        assert "dimensión de mes" in res.motivo

    def test_sin_columna_anio_no_disponible(self):
        df = pd.DataFrame([{"Mes": "ABRIL", "Logro": 1}])
        res = resolver_periodo(df, {"tipo": "semestral"}, date(2026, 5, 10))
        assert res.disponible is False
        assert "dimensión de año" in res.motivo

    def test_hito_dia_cuenta_como_mes(self):
        df = pd.DataFrame([
            {"Año": "2026", "Hito": "INICIO", "Logro": 1},     # mes 3 → 1er sem
            {"Año": "2026", "Hito": "CIERRE", "Logro": 2},     # mes 11 → 2º sem
        ])
        res = resolver_periodo(df, {"tipo": "semestral"}, date(2026, 5, 10))
        assert res.disponible is True
        assert res.filtros["Hito"] == ["INICIO"]


# ─────────────────────────────────────────────────────────────────────────
# personalizado
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestPersonalizado:
    def test_rango_ym_recorta_y_marca_historico(self, df_simce):
        res = resolver_periodo(
            df_simce,
            {"tipo": "personalizado", "fecha_inicio": "2025-08", "fecha_fin": "2025-12"},
            date(2026, 7, 29),
        )
        assert res.disponible is True
        assert res.filtros["Año"] == ["2025"]
        assert res.filtros["Mes"] == ["AGOSTO", "NOVIEMBRE"]
        assert res.tipo_layout == "historico"  # 2 claves temporales distintas

    def test_rango_de_una_sola_clave_es_evaluacion(self, df_simce):
        res = resolver_periodo(
            df_simce,
            {"tipo": "personalizado", "fecha_inicio": "2025-11", "fecha_fin": "2025-11"},
            date(2026, 7, 29),
        )
        assert res.filtros["Mes"] == ["NOVIEMBRE"]
        assert res.tipo_layout == "evaluacion"
        assert res.descripcion == "NOVIEMBRE 2025"

    def test_filas_sin_mes_conocido_entran_por_anio(self):
        df = pd.DataFrame([
            {"Año": "2025", "Mes": "", "Logro": 1},          # mes desconocido
            {"Año": "2024", "Mes": "", "Logro": 2},          # fuera del rango de años
            {"Año": "2025", "Mes": "NOVIEMBRE", "Logro": 3},
        ])
        res = resolver_periodo(
            df,
            {"tipo": "personalizado", "fecha_inicio": "2025-01", "fecha_fin": "2025-12"},
            date(2026, 7, 29),
        )
        assert res.disponible is True
        assert res.filtros["Año"] == ["2025"]
        # La fila sin mes no aporta valor de mes al filtro, pero se contó
        assert res.filtros["Mes"] == ["NOVIEMBRE"]

    def test_filtros_de_dimension_combinados_con_rango(self, df_simce):
        res = resolver_periodo(
            df_simce,
            {
                "tipo": "personalizado",
                "fecha_inicio": "2025-01",
                "fecha_fin": "2025-12",
                "filtros": {"Curso": "II A"},
            },
            date(2026, 7, 29),
        )
        assert res.disponible is True
        assert res.filtros["Curso"] == "II A"
        # II A en 2025 tiene ABRIL y AGOSTO (NOVIEMBRE es de II B)
        assert res.filtros["Mes"] == ["ABRIL", "AGOSTO"]

    def test_solo_filtros_sin_rango(self, df_simce):
        res = resolver_periodo(
            df_simce,
            {"tipo": "personalizado", "filtros": {"Curso": ["II B"]}},
            date(2026, 7, 29),
        )
        assert res.disponible is True
        assert res.filtros == {"Curso": ["II B"]}
        assert res.tipo_layout == "evaluacion"  # II B tiene 1 sola clave

    def test_rango_sin_datos_no_disponible(self, df_simce):
        res = resolver_periodo(
            df_simce,
            {"tipo": "personalizado", "fecha_inicio": "2019-01", "fecha_fin": "2019-12"},
            date(2026, 7, 29),
        )
        assert res.disponible is False
        assert "No hay datos en el período seleccionado" in res.motivo
        # El motivo nombra el rango pedido: sin eso el usuario no sabe qué
        # corregir.
        assert "ENERO 2019" in res.motivo and "DICIEMBRE 2019" in res.motivo
        assert res.filtros == {}

    @pytest.mark.parametrize("inicio,fin", [
        ("2019-01-01", "2019-12-31"),   # el formato que manda el frontend
        ("2019-01", "2019-12"),
        ("2019", "2019"),
    ])
    def test_rango_vacio_nunca_degrada_a_todos_los_datos(self, df_simce, inicio, fin):
        """P0-2: un rango sin datos NO puede devolver el dataset entero.

        Antes, "2019-01-01" no parseaba como YYYY-MM, el rango se
        descartaba y el informe salía con TODOS los datos del indicador —
        con aspecto legítimo y sin ninguna marca.
        """
        res = resolver_periodo(
            df_simce,
            {"tipo": "personalizado", "fecha_inicio": inicio, "fecha_fin": fin},
            date(2026, 7, 29),
        )
        assert res.disponible is False
        assert res.filtros == {}

    def test_rango_invertido_no_disponible(self, df_simce):
        res = resolver_periodo(
            df_simce,
            {"tipo": "personalizado",
             "fecha_inicio": "2025-12-01", "fecha_fin": "2025-01-01"},
            date(2026, 7, 29),
        )
        assert res.disponible is False
        assert "invertido" in res.motivo
        assert res.filtros == {}

    def test_rango_invertido_por_anio(self, df_simce):
        res = resolver_periodo(
            df_simce,
            {"tipo": "personalizado", "fecha_inicio": "2026-01", "fecha_fin": "2025-12"},
            date(2026, 7, 29),
        )
        assert res.disponible is False
        assert "invertido" in res.motivo

    def test_rango_valido_con_datos_sigue_disponible(self, df_simce):
        """Contraparte de los dos anteriores: el camino feliz no se rompe."""
        res = resolver_periodo(
            df_simce,
            {"tipo": "personalizado",
             "fecha_inicio": "2025-01-01", "fecha_fin": "2025-07-31"},
            date(2026, 7, 29),
        )
        assert res.disponible is True
        assert res.filtros["Año"] == ["2025"]
        assert res.filtros["Mes"] == ["ABRIL"]

    @pytest.mark.parametrize("campo", ["fecha_inicio", "fecha_fin"])
    def test_fecha_ilegible_no_disponible(self, df_simce, campo):
        """Una fecha que no se entiende se rechaza; jamás se ignora."""
        res = resolver_periodo(
            df_simce,
            {"tipo": "personalizado", campo: "el año pasado"},
            date(2026, 7, 29),
        )
        assert res.disponible is False
        assert "No se pudo interpretar el rango de fechas" in res.motivo

    def test_extremo_vacio_no_es_ilegible(self, df_simce):
        """`fecha_fin: ""` = rango abierto, no un error de formato."""
        res = resolver_periodo(
            df_simce,
            {"tipo": "personalizado", "fecha_inicio": "2025-01", "fecha_fin": ""},
            date(2026, 7, 29),
        )
        assert res.disponible is True

    def test_rango_sin_dimension_temporal_no_disponible(self, df_sin_tiempo):
        res = resolver_periodo(
            df_sin_tiempo,
            {"tipo": "personalizado", "fecha_inicio": "2026-01"},
            date(2026, 7, 29),
        )
        assert res.disponible is False
        assert "dimensión temporal" in res.motivo


# ─────────────────────────────────────────────────────────────────────────
# Varios
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestVarios:
    def test_tipo_desconocido_no_disponible(self, df_simce):
        res = resolver_periodo(df_simce, {"tipo": "trimestral"}, date(2026, 7, 29))
        assert res.disponible is False
        assert "desconocido" in res.motivo

    def test_default_es_ultima_prueba(self, df_simce):
        res = resolver_periodo(df_simce, {}, date(2026, 7, 29))
        assert res.tipo == "ultima_prueba"

    def test_multi_prefiere_estudiantes(self, df_simce, df_sin_tiempo):
        res = resolver_periodo_multi(
            {"preguntas": df_sin_tiempo, "estudiantes": df_simce},
            {"tipo": "ultima_prueba"},
            date(2026, 7, 29),
        )
        assert res.disponible is True
        assert res.filtros["Mes"] == "MARZO"

    def test_multi_cae_al_df_con_mas_columnas_temporales(self, df_simce, df_sin_tiempo):
        res = resolver_periodo_multi(
            {"otros": df_sin_tiempo, "metric_9": df_simce},
            {"tipo": "ultima_prueba"},
            date(2026, 7, 29),
        )
        assert res.disponible is True

    def test_multi_sin_dataframes(self):
        res = resolver_periodo_multi({}, {"tipo": "anual"}, date(2026, 7, 29))
        assert res.disponible is False
        assert "Sin datos" in res.motivo

    def test_to_dict_serializable(self, df_simce):
        d = resolver_periodo(df_simce, {"tipo": "anual"}, date(2026, 7, 29)).to_dict()
        assert set(d) == {"tipo", "filtros", "tipo_layout", "descripcion", "disponible", "motivo"}


# ─────────────────────────────────────────────────────────────────────────
# Semántica por columna: Versión (QA 2026-07-30, P1-3)
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestSemanticaDeVersion:
    """En una columna "Versión", "1" es v1 (abril) — NO enero.

    Los datos IDEL guardan la versión como "1"/"2"/"3". Antes la rama
    numérica de `a_numero_mes` ganaba y las tres versiones caían en el 1er
    semestre, así que los informes semestral y anual salían idénticos.
    """

    @pytest.mark.parametrize("nombre,esperado", [
        ("Mes", "mes"),
        ("Fecha", "fecha"),
        ("Fecha Aplicación", "fecha"),
        ("Hito", "hito"),
        ("Versión", "version"),
        ("version", "version"),
        ("Curso", None),
        (None, None),
    ])
    def test_tipo_mes_like(self, nombre, esperado):
        assert tipo_mes_like(nombre) == esperado

    @pytest.mark.parametrize("valor,esperado", [
        ("1", 4), ("2", 8), ("3", 11),          # como vienen en la DB
        (1, 4), (2, 8), (3, 11),                # numéricos
        (1.0, 4), ("2.0", 8),                   # casteados por pandas
        ("v1", 4), ("V2", 8), ("v3", 11),       # con prefijo
    ])
    def test_version_se_mapea_a_su_mes(self, valor, esperado):
        assert a_numero_mes(valor, "version") == esperado

    def test_sin_semantica_los_numericos_siguen_siendo_meses(self):
        """Retrocompatibilidad: en una columna "Mes", "3" es marzo."""
        assert a_numero_mes("3") == 3
        assert a_numero_mes("3", "mes") == 3

    def test_hito_con_semantica_explicita(self):
        assert a_numero_mes("DIAGNOSTICO", "hito") == 3
        assert a_numero_mes("CIERRE", "hito") == 11

    @pytest.fixture
    def df_idel(self):
        """IDEL: 3 versiones por año, guardadas como "1"/"2"/"3"."""
        filas = []
        for anio in ("2025", "2026"):
            for version in ("1", "2", "3"):
                filas.append({
                    "Curso": "1° BÁSICO", "Año": anio, "Versión": version,
                    "Evaluación": "CT", "Puntaje": 30,
                })
        return pd.DataFrame(filas)

    @pytest.fixture
    def df_idel_con_v(self, df_idel):
        """Misma forma, pero con la versión escrita "v1"/"v2"/"v3"."""
        df = df_idel.copy()
        df["Versión"] = "v" + df["Versión"].astype(str)
        return df

    def test_semestral_solo_toma_v1_en_el_primer_semestre(self, df_idel):
        res = resolver_periodo(df_idel, {"tipo": "semestral"}, date(2026, 5, 10))
        assert res.disponible is True
        assert res.filtros["Versión"] == ["1"], (
            "v1 → abril: es la única versión del 1er semestre"
        )

    def test_semestral_toma_v2_y_v3_en_el_segundo(self, df_idel):
        res = resolver_periodo(df_idel, {"tipo": "semestral"}, date(2026, 9, 10))
        assert res.disponible is True
        assert res.filtros["Versión"] == ["2", "3"]  # agosto y noviembre

    def test_semestral_y_anual_ya_no_son_el_mismo_informe(self, df_idel):
        semestral = resolver_periodo(df_idel, {"tipo": "semestral"}, date(2026, 5, 10))
        anual = resolver_periodo(df_idel, {"tipo": "anual"}, date(2026, 5, 10))
        assert semestral.filtros != anual.filtros
        assert "Versión" not in anual.filtros  # el anual no acota la versión

    def test_funciona_igual_con_el_prefijo_v(self, df_idel_con_v):
        res = resolver_periodo(df_idel_con_v, {"tipo": "semestral"}, date(2026, 5, 10))
        assert res.filtros["Versión"] == ["v1"]
        res2 = resolver_periodo(df_idel_con_v, {"tipo": "semestral"}, date(2026, 9, 10))
        assert res2.filtros["Versión"] == ["v2", "v3"]

    def test_ultima_prueba_es_la_v3_no_la_v1(self, df_idel):
        res = resolver_periodo(df_idel, {"tipo": "ultima_prueba"}, date(2026, 12, 1))
        assert res.filtros == {"Año": "2026", "Versión": "3"}

    def test_la_descripcion_de_la_version_es_legible(self, df_idel):
        """Antes: "3 2026". Ahora: "v3 2026" (QA P2-1)."""
        res = resolver_periodo(df_idel, {"tipo": "ultima_prueba"}, date(2026, 12, 1))
        assert res.descripcion == "v3 2026"

    def test_personalizado_ordena_las_versiones_cronologicamente(self, df_idel):
        res = resolver_periodo(df_idel, {
            "tipo": "personalizado",
            "fecha_inicio": "2026-01", "fecha_fin": "2026-12",
        }, date(2026, 12, 1))
        assert res.disponible is True
        assert res.filtros["Versión"] == ["1", "2", "3"]


@pytest.mark.unit
class TestDescripcionDeFecha:
    """QA P1-12: `Fecha: 2026-04-07 00:00:00` en el subtítulo."""

    def test_la_hora_no_aparece_en_la_descripcion(self):
        df = pd.DataFrame([
            {"Curso": "II°E", "Fecha": pd.Timestamp("2026-04-07"), "Cantidad": 142},
        ])
        res = resolver_periodo(df, {"tipo": "ultima_prueba"}, date(2026, 7, 30))
        assert "00:00:00" not in res.descripcion
        assert res.descripcion == "07-04-2026"
