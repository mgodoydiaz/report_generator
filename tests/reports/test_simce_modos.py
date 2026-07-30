"""Tests del módulo SIMCE del motor único (`reports/custom/simce.py`).

Plan §5.1 del contrato: se testea la LISTA DE SECCIONES por modo, no el PDF
renderizado (WeasyPrint no está en todos los hosts). El módulo expone
`_secciones(modo, dataframes) -> (fijas, dinamicas)` justamente para esto.

También cubre los helpers compartidos de `custom/_secciones.py` (N6), que
son puros y se testean con DataFrames armados a mano.
"""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from backend.rgenerator.reports import periodos
from backend.rgenerator.reports.charts import CHART_REGISTRY
from backend.rgenerator.reports.custom import _secciones as sec
from backend.rgenerator.reports.custom import simce
from backend.rgenerator.reports.tables import TABLE_REGISTRY


def _df_estudiantes(meses=("ABRIL", "MAYO"), anio=2026) -> pd.DataFrame:
    filas = []
    for mes in meses:
        for rut, rend, logro in (("1-1", 0.30, "Insuficiente"), ("2-2", 0.80, "Adecuado")):
            filas.append({
                "Curso": "II A", "RUT": rut, "Nombre": f"Alumno {rut}",
                "Mes": mes, "Año": str(anio), "Rend": rend,
                "Simce": int(rend * 400), "Logro": logro,
            })
    return pd.DataFrame(filas)


def _dataframes(meses=("ABRIL", "MAYO")) -> dict:
    df = _df_estudiantes(meses)
    return {
        "estudiantes": df,
        "estudiantes_periodo": df,
        "estudiantes_prueba": df[df["Mes"] == meses[-1]],
        "estudiantes_previo": df.iloc[0:0],
        "preguntas": df,
        "preguntas_periodo": df,
        "preguntas_prueba": df[df["Mes"] == meses[-1]],
    }


def _titulos(secciones) -> list[str]:
    return [s.get("titulo") for s in secciones]


# ─────────────────────────────────────────────────────────────────────────
# Declaración de modos
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestModosDeclarados:
    def test_modos_son_tipos_de_periodo_validos(self):
        assert set(simce.MODOS) <= set(periodos.TIPOS_PERIODO)

    def test_simce_sirve_los_cuatro(self):
        assert simce.MODOS == ["ultima_prueba", "semestral", "anual", "personalizado"]
        assert simce.MOTIVO_MODO_NO_DISPONIBLE == {}

    def test_modo_desconocido_levanta_valueerror(self):
        with pytest.raises(ValueError) as exc:
            simce._secciones("trimestral", {})
        assert "no genera el modo" in str(exc.value)
        assert "trimestral" in str(exc.value)


# ─────────────────────────────────────────────────────────────────────────
# Estructura de las secciones por modo (§4.1 / §4.2)
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestEstructuraDeSecciones:
    def test_ultima_prueba_orden_exacto(self):
        fijas, dinamicas = simce._secciones("ultima_prueba", _dataframes())
        assert _titulos(fijas) == [
            "Resumen de Logro por Curso",
            "Resumen de Puntaje SIMCE por Curso",
            "Rendimiento Promedio por Curso",
            "Distribución de Puntaje SIMCE por Curso",
            "Cantidad de Alumnos por Nivel de Logro y Curso",
            "Composición Global por Nivel",
            "Logro Promedio por Habilidad",
            "Logro Promedio por Eje Temático",
            "Estudiantes en Riesgo",
            "Estadística por Pregunta del Establecimiento",
        ]
        assert dinamicas["iterar_por"] == "Curso"

    def test_semestral_orden_exacto(self):
        fijas, dinamicas = simce._secciones(
            "semestral", _dataframes(), etiqueta_previa="2º sem. 2025"
        )
        assert _titulos(fijas) == [
            "Resumen de Logro por Curso (vs 2º sem. 2025)",
            "Resumen de Puntaje SIMCE por Curso",
            "Rendimiento Promedio por Curso",
            "Distribución de Puntaje SIMCE por Curso",
            "Cantidad de Alumnos por Nivel de Logro y Curso",
            "Composición Global por Nivel",
            "Logro Promedio por Habilidad",
            "Logro Promedio por Eje Temático",
            "Evolución del Logro Promedio por Curso y Mes",
            "Evolución del Puntaje SIMCE Promedio por Curso y Mes",
            "Evolución de Niveles por Curso y Mes",
        ]
        assert dinamicas == {}

    def test_anual_agrega_riesgo_persistente_al_final(self):
        dfs = _dataframes()
        dfs["riesgo_persistente"] = pd.DataFrame([{"Curso": "II A", "Estudiante": "X"}])
        fijas, _ = simce._secciones("anual", dfs)
        assert fijas[-1]["titulo"] == "Estudiantes en Riesgo Persistente"
        assert fijas[-1]["tipo"] == "table"
        assert fijas[-1]["df_input"] == "riesgo_persistente"

    def test_personalizado_es_igual_a_anual(self):
        dfs = _dataframes()
        dfs["riesgo_persistente"] = pd.DataFrame([{"Curso": "II A", "Estudiante": "X"}])
        assert _titulos(simce._secciones("personalizado", dfs)[0]) == _titulos(
            simce._secciones("anual", dfs)[0]
        )

    def test_todas_las_fn_existen_en_los_registries(self):
        dfs = _dataframes()
        dfs["riesgo_persistente"] = pd.DataFrame([{"Curso": "II A"}])
        for modo in simce.MODOS:
            fijas, dinamicas = simce._secciones(modo, dfs)
            secciones = list(fijas) + list(dinamicas.get("secciones", []))
            for s in secciones:
                if s["tipo"] == "chart":
                    assert s["fn"] in CHART_REGISTRY, (modo, s["titulo"])
                elif s["tipo"] == "table":
                    assert s["fn"] in TABLE_REGISTRY, (modo, s["titulo"])

    def test_todos_los_df_input_existen(self):
        dfs = _dataframes()
        dfs["resumen_logro_comparado"] = pd.DataFrame()
        dfs["riesgo_persistente"] = pd.DataFrame([{"Curso": "II A"}])
        for modo in simce.MODOS:
            fijas, dinamicas = simce._secciones(modo, dfs)
            secciones = list(fijas) + list(dinamicas.get("secciones", []))
            for s in secciones:
                if s["tipo"] in ("chart", "table"):
                    assert s["df_input"] in dfs, (modo, s["titulo"], s["df_input"])
            if dinamicas:
                assert dinamicas["df_iterar"] in dfs

    def test_detalle_por_curso_solo_en_ultima_prueba(self):
        """Decisión 1: el detalle por alumno/pregunta/curso no va al histórico."""
        _, dinamicas = simce._secciones("ultima_prueba", _dataframes())
        assert dinamicas["secciones"]
        for modo in ("semestral", "anual", "personalizado"):
            fijas, dinamicas = simce._secciones(modo, _dataframes())
            assert dinamicas == {}
            assert "Estadística por Pregunta del Establecimiento" not in _titulos(fijas)
            assert "Estudiantes en Riesgo" not in _titulos(fijas)

    def test_riesgo_persistente_solo_en_anual_y_personalizado(self):
        dfs = _dataframes()
        dfs["riesgo_persistente"] = pd.DataFrame([{"Curso": "II A"}])
        for modo in ("ultima_prueba", "semestral"):
            titulos = _titulos(simce._secciones(modo, dfs)[0])
            assert "Estudiantes en Riesgo Persistente" not in titulos
        for modo in ("anual", "personalizado"):
            titulos = _titulos(simce._secciones(modo, dfs)[0])
            assert titulos[-1] == "Estudiantes en Riesgo Persistente"

    def test_riesgo_persistente_vacio_degrada_a_nota(self):
        """Sin 2 evaluaciones consecutivas se explica, no se deja hueco."""
        dfs = _dataframes()
        dfs["riesgo_persistente"] = pd.DataFrame()
        ultima = simce._secciones("anual", dfs)[0][-1]
        assert ultima["tipo"] == "nota"
        assert "dos evaluaciones consecutivas" in ultima["texto"]


@pytest.mark.unit
class TestEvolucionAutoOmitida:
    """Decisión 16: con un solo punto temporal no hay evolución que graficar."""

    def test_evolucion_se_omite_con_un_punto(self):
        fijas, _ = simce._secciones("semestral", _dataframes(meses=("MAYO",)))
        graficos = [s for s in fijas if s["tipo"] == "chart"]
        assert not [s for s in graficos if s["titulo"].startswith("Evolución")]

    def test_y_el_informe_lo_explica(self):
        fijas, _ = simce._secciones("semestral", _dataframes(meses=("MAYO",)))
        nota = fijas[-1]
        assert nota["tipo"] == "nota"
        assert nota["titulo"] == "Evolución del período"
        assert "una sola evaluación" in nota["texto"]

    def test_con_dos_puntos_las_tres_secciones_estan(self):
        fijas, _ = simce._secciones("anual", _dataframes(meses=("ABRIL", "MAYO")))
        evolucion = [t for t in _titulos(fijas) if t.startswith("Evolución")]
        assert len(evolucion) == 3


# ─────────────────────────────────────────────────────────────────────────
# Helpers compartidos (N6)
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestBloqueTitulo:
    def test_no_emite_pagina_de_portada(self):
        """Salvedad del dueño: bloque de título, no una página dedicada."""
        bloque = sec.bloque_titulo(
            titulo="Informe Ensayo SIMCE", establecimiento="Pullinque",
            asignatura="Matemáticas", periodo_desc="MAYO 2026",
        )
        assert bloque == {
            "title": "Informe Ensayo SIMCE — Matemáticas",
            "subtitle": "Pullinque",
            "filters_label": "MAYO 2026",
        }
        assert "secciones_fijas" not in bloque

    def test_sin_asignatura_ni_establecimiento(self):
        bloque = sec.bloque_titulo(titulo="Informe X", periodo_desc="2025")
        assert bloque["title"] == "Informe X"
        assert bloque["subtitle"] == ""


@pytest.mark.unit
class TestPuntosTemporales:
    def test_un_mes_es_un_punto(self):
        assert sec.puntos_temporales(_df_estudiantes(meses=("MAYO",))) == 1

    def test_dos_meses_son_dos_puntos(self):
        assert sec.puntos_temporales(_df_estudiantes()) == 2

    def test_mismo_mes_en_dos_anios_no_colapsa(self):
        df = pd.concat([
            _df_estudiantes(meses=("MAYO",), anio=2025),
            _df_estudiantes(meses=("MAYO",), anio=2026),
        ])
        assert sec.puntos_temporales(df) == 2

    def test_df_vacio(self):
        assert sec.puntos_temporales(pd.DataFrame()) == 0
        assert sec.puntos_temporales(None) == 0


@pytest.mark.unit
class TestSeccionEvolucion:
    _SECCION = {"tipo": "chart", "titulo": "Evolución", "fn": "x", "df_input": "y",
                "params": {}}

    def test_omite_con_un_punto(self):
        assert sec.seccion_evolucion(self._SECCION, _df_estudiantes(meses=("MAYO",))) == []

    def test_conserva_con_dos_puntos(self):
        assert sec.seccion_evolucion(self._SECCION, _df_estudiantes()) == [self._SECCION]


@pytest.mark.unit
class TestResumenComparado:
    def test_columna_previa_con_datos(self):
        actual = _df_estudiantes(meses=("MAYO",), anio=2026)
        previo = _df_estudiantes(meses=("NOVIEMBRE",), anio=2025)
        tabla = sec.tabla_resumen_comparado(
            actual, previo, columna="Rend",
            etiqueta_actual="Promedio 2026", etiqueta_previo="Promedio 2025",
        )
        assert "Promedio 2026" in tabla.columns
        assert "Promedio 2025" in tabla.columns
        assert tabla.loc[0, "Promedio 2025"] == "55%"

    def test_sin_periodo_previo_la_columna_sale_con_raya(self):
        tabla = sec.tabla_resumen_comparado(
            _df_estudiantes(meses=("MAYO",)), None, columna="Rend",
            etiqueta_previo="Promedio 2025",
        )
        assert list(tabla["Promedio 2025"]) == [sec.MARCA_SIN_DATO]

    def test_nunca_imprime_nan(self):
        actual = _df_estudiantes(meses=("MAYO",))
        previo = pd.DataFrame([{"Curso": "II Z", "Rend": 0.5}])
        tabla = sec.tabla_resumen_comparado(
            actual, previo, columna="Rend", etiqueta_previo="Anterior",
        )
        assert list(tabla["Anterior"]) == [sec.MARCA_SIN_DATO]


@pytest.mark.unit
class TestRiesgoPersistente:
    def _df(self):
        return pd.DataFrame([
            # Persistente: Insuficiente en ABRIL y MAYO (consecutivos)
            {"Curso": "II A", "RUT": "1-1", "Nombre": "Persistente",
             "Mes": "ABRIL", "Logro": "Insuficiente", "Rend": 0.30, "Simce": 120},
            {"Curso": "II A", "RUT": "1-1", "Nombre": "Persistente",
             "Mes": "MAYO", "Logro": "Insuficiente", "Rend": 0.32, "Simce": 128},
            # Mejoró: no entra
            {"Curso": "II A", "RUT": "2-2", "Nombre": "Mejoro",
             "Mes": "ABRIL", "Logro": "Insuficiente", "Rend": 0.35, "Simce": 140},
            {"Curso": "II A", "RUT": "2-2", "Nombre": "Mejoro",
             "Mes": "MAYO", "Logro": "Adecuado", "Rend": 0.80, "Simce": 320},
            # Una sola evaluación: no entra
            {"Curso": "II B", "RUT": "3-3", "Nombre": "Unico",
             "Mes": "MAYO", "Logro": "Insuficiente", "Rend": 0.20, "Simce": 80},
        ])

    def test_solo_los_persistentes(self):
        tabla = sec.tabla_riesgo_persistente(
            self._df(), columna_nivel="Logro", nivel_objetivo="Insuficiente",
            columna_temporal="Mes", columnas_puntaje=["Rend", "Simce"],
        )
        assert list(tabla["Estudiante"]) == ["Persistente"]
        assert tabla.loc[0, "Nivel"] == "Insuficiente"

    def test_columnas_posicionales_no_una_por_mes(self):
        """Con encabezados por mes la tabla explotaba a 11 columnas casi vacías."""
        tabla = sec.tabla_riesgo_persistente(
            self._df(), columna_nivel="Logro", nivel_objetivo="Insuficiente",
            columna_temporal="Mes", columnas_puntaje=["Rend", "Simce"],
        )
        assert list(tabla.columns) == [
            "Curso", "Estudiante", "Evaluaciones",
            "Rend previo", "Rend actual", "Simce previo", "Simce actual",
            "Nivel",
        ]
        assert tabla.loc[0, "Evaluaciones"] == "ABRIL → MAYO"

    def test_alumnos_con_pares_distintos_comparten_columnas(self):
        df = pd.concat([
            self._df(),
            pd.DataFrame([
                {"Curso": "II C", "RUT": "7-7", "Nombre": "Otro Par",
                 "Mes": "OCTUBRE", "Logro": "Insuficiente", "Rend": 0.25,
                 "Simce": 100},
                {"Curso": "II C", "RUT": "7-7", "Nombre": "Otro Par",
                 "Mes": "NOVIEMBRE", "Logro": "Insuficiente", "Rend": 0.28,
                 "Simce": 110},
            ]),
        ])
        tabla = sec.tabla_riesgo_persistente(
            df, columna_nivel="Logro", nivel_objetivo="Insuficiente",
            columna_temporal="Mes", columnas_puntaje=["Rend"],
        )
        assert len(tabla) == 2
        assert set(tabla["Evaluaciones"]) == {"ABRIL → MAYO", "OCTUBRE → NOVIEMBRE"}
        assert list(tabla.columns) == [
            "Curso", "Estudiante", "Evaluaciones", "Rend previo", "Rend actual",
            "Nivel",
        ]
        assert not tabla["Rend previo"].isna().any()

    def test_sin_segunda_evaluacion_devuelve_vacio(self):
        df = self._df()
        df = df[df["Mes"] == "MAYO"]
        tabla = sec.tabla_riesgo_persistente(
            df, columna_nivel="Logro", nivel_objetivo="Insuficiente",
            columna_temporal="Mes", columnas_puntaje=["Rend"],
        )
        assert tabla.empty

    def test_evaluaciones_no_consecutivas_no_cuentan(self):
        df = pd.DataFrame([
            {"Curso": "II A", "RUT": "1-1", "Nombre": "Saltea", "Mes": "ABRIL",
             "Logro": "Insuficiente", "Rend": 0.3},
            {"Curso": "II A", "RUT": "9-9", "Nombre": "Relleno", "Mes": "JUNIO",
             "Logro": "Adecuado", "Rend": 0.9},
            {"Curso": "II A", "RUT": "1-1", "Nombre": "Saltea", "Mes": "AGOSTO",
             "Logro": "Insuficiente", "Rend": 0.3},
        ])
        tabla = sec.tabla_riesgo_persistente(
            df, columna_nivel="Logro", nivel_objetivo="Insuficiente",
            columna_temporal="Mes", columnas_puntaje=["Rend"],
        )
        assert tabla.empty

    def test_formatos_aplicados(self):
        tabla = sec.tabla_riesgo_persistente(
            self._df(), columna_nivel="Logro", nivel_objetivo="Insuficiente",
            columna_temporal="Mes", columnas_puntaje=["Rend", "Simce"],
            formatos={"Rend": "percent", "Simce": "number"},
        )
        assert tabla.loc[0, "Rend previo"] == "30%"
        assert tabla.loc[0, "Simce previo"] == "120"


@pytest.mark.unit
class TestSeccionesPorCurso:
    def test_estructura_del_bloque(self):
        bloque = sec.secciones_por_curso([{"tipo": "table"}], df_iterar="estudiantes")
        assert bloque == {
            "iterar_por": "Curso",
            "df_iterar": "estudiantes",
            "secciones": [{"tipo": "table"}],
        }


# ─────────────────────────────────────────────────────────────────────────
# Render end-to-end (mockeado): qué recibe `runtime.construir_pdf`
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestGenerarPorModo:
    def _generar(self, db, ind, modo, filtros, params=None):
        with patch(
            "backend.rgenerator.reports.runtime.construir_pdf",
            return_value=b"%PDF-1.4\n",
        ) as mock:
            pdf = simce.generar(
                db, indicator_id=ind.id_indicator, org_id=ind.org_id,
                modo=modo, filtros=filtros, params=params,
            )
        assert pdf == b"%PDF-1.4\n"
        return mock.call_args

    def test_ultima_prueba_pasa_esquema_en_memoria(
        self, db_session, simce_indicator_historico
    ):
        from datetime import date
        args = self._generar(
            db_session, simce_indicator_historico, "ultima_prueba",
            {"Asignatura": "Lenguaje", "Mes": "MAYO", "Año": str(date.today().year)},
        )
        esquema = args.kwargs["esquema"]
        assert args.kwargs["df_principal"] == "estudiantes_prueba"
        assert esquema["title"].startswith("Informe Ensayo SIMCE")
        assert esquema["secciones_dinamicas"]["iterar_por"] == "Curso"
        # El bloque de título NO introduce un salto de página propio.
        assert not any(
            s.get("tipo") == "page_break" for s in esquema["secciones_fijas"]
        )

    def test_anual_usa_el_periodo_completo(self, db_session, simce_indicator_historico):
        from datetime import date
        args = self._generar(
            db_session, simce_indicator_historico, "anual",
            {"Asignatura": "Lenguaje", "Año": str(date.today().year)},
        )
        assert args.kwargs["df_principal"] == "estudiantes_periodo"
        dataframes = args.args[1]
        # Dos meses del año en curso ⇒ evolución presente
        titulos = [s.get("titulo") for s in args.kwargs["esquema"]["secciones_fijas"]]
        assert "Evolución del Logro Promedio por Curso y Mes" in titulos
        assert len(dataframes["estudiantes_periodo"]) == 4

    def test_anual_calcula_el_riesgo_persistente(
        self, db_session, simce_indicator_historico
    ):
        from datetime import date
        args = self._generar(
            db_session, simce_indicator_historico, "anual",
            {"Asignatura": "Lenguaje", "Año": str(date.today().year)},
        )
        riesgo = args.args[1]["riesgo_persistente"]
        assert list(riesgo["Estudiante"]) == ["Alumno Uno"]
        assert args.kwargs["esquema"]["secciones_fijas"][-1]["titulo"] == (
            "Estudiantes en Riesgo Persistente"
        )

    def test_anual_compara_con_el_anio_anterior(
        self, db_session, simce_indicator_historico
    ):
        from datetime import date
        anio = date.today().year
        args = self._generar(
            db_session, simce_indicator_historico, "anual",
            {"Asignatura": "Lenguaje", "Año": str(anio)},
        )
        comparado = args.args[1]["resumen_logro_comparado"]
        assert f"Promedio {anio - 1}" in comparado.columns
        assert comparado.loc[0, f"Promedio {anio - 1}"] == "40%"

    def test_el_pie_es_la_organizacion(self, db_session, simce_indicator_historico, org):
        from datetime import date
        args = self._generar(
            db_session, simce_indicator_historico, "ultima_prueba",
            {"Asignatura": "Lenguaje", "Año": str(date.today().year)},
        )
        assert args.kwargs["overrides"]["branding"]["left_footer"] == org.name

    def test_modo_desconocido_400(self, db_session, simce_indicator_historico):
        with pytest.raises(ValueError):
            simce.generar(
                db_session, indicator_id=simce_indicator_historico.id_indicator,
                org_id=simce_indicator_historico.org_id, modo="trimestral",
            )

    def test_sin_datos_del_periodo_levanta_datos_insuficientes(
        self, db_session, simce_indicator_historico
    ):
        from backend.rgenerator.reports.errores import DatosInsuficientes
        with pytest.raises(DatosInsuficientes):
            simce.generar(
                db_session, indicator_id=simce_indicator_historico.id_indicator,
                org_id=simce_indicator_historico.org_id, modo="anual",
                filtros={"Asignatura": "Lenguaje", "Año": "1999"},
            )


# ─────────────────────────────────────────────────────────────────────────
# Fuente única del período (QA piloto SIMCE 2026-07-30, P1-1)
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestFuenteUnicaDelPeriodo(TestGenerarPorModo):
    """El período del bloque de título y el del encabezado son EL MISMO.

    Antes el router inyectaba `ResultadoPeriodo.descripcion` en el
    encabezado corrido y el módulo recalculaba el suyo para el título: en
    `personalizado` el título decía "2025" y el encabezado
    "ENERO 2025 – JULIO 2025".
    """

    def _ultima_linea_header(self, args) -> str:
        return args.kwargs["overrides"]["branding"]["center_header"][-1]

    def test_periodo_desc_inyectado_manda_sobre_el_calculo_propio(
        self, db_session, simce_indicator_historico
    ):
        from datetime import date
        anio = date.today().year
        desc = f"ENERO {anio} – JULIO {anio}"
        args = self._generar(
            db_session, simce_indicator_historico, "personalizado",
            {"Asignatura": "Lenguaje", "Año": str(anio)},
            params={"periodo_desc": desc},
        )
        assert args.kwargs["esquema"]["filters_label"] == desc
        assert self._ultima_linea_header(args) == desc

    def test_titulo_y_encabezado_coinciden_en_todos_los_modos(
        self, db_session, simce_indicator_historico
    ):
        from datetime import date
        anio = date.today().year
        for modo, desc in (
            ("ultima_prueba", f"MAYO {anio} (prueba 2)"),
            ("anual", str(anio)),
            ("personalizado", f"ENERO {anio} – JULIO {anio}"),
        ):
            args = self._generar(
                db_session, simce_indicator_historico, modo,
                {"Asignatura": "Lenguaje", "Año": str(anio)},
                params={"periodo_desc": desc},
            )
            assert args.kwargs["esquema"]["filters_label"] == desc, modo
            assert self._ultima_linea_header(args) == desc, modo

    def test_sin_periodo_desc_cae_al_calculo_propio(
        self, db_session, simce_indicator_historico
    ):
        """Invocación directa del módulo: el fallback sigue vivo."""
        from datetime import date
        anio = date.today().year
        args = self._generar(
            db_session, simce_indicator_historico, "anual",
            {"Asignatura": "Lenguaje", "Año": str(anio)},
        )
        assert args.kwargs["esquema"]["filters_label"] == str(anio)
