"""Regresión de los hallazgos del QA visual de informes (2026-07-30).

Informe fuente: `docs/reportes/calidad_informes_selector_2026-07-30.md`.

Cubre los hallazgos cuya causa era código o configuración del repo:

P0-1  · combinación de filtros sin datos devolvía HTTP 200 con un PDF vacío,
        y la excepción de la sección se imprimía literal en el PDF.
P0-10 /
P0-11 · el `center_header` de los esquemas traía literales muertos
        ("Asignatura - Curso", "Mes Año") que salían impresos en 91/167
        páginas, y el hito/asignatura del encabezado contradecía el cuerpo.
P0-4b · `simce/esquema.json` declaraba `time_ordinal_levels` que no
        coincidían con los datos (faltaban MAYO y NOVIEMBRE, sobraba
        "OCTUBRE 2") → Avance y Mejora_vs_Inicio 100% nulos en esos meses.
P1-1  · el pie izquierdo decía "Miguel Godoy Díaz" (venía de los layouts
        persistidos en la DB, donde el fallback a la org no actuaba).
P1-2  · los subtítulos mostraban el `repr` de listas de Python.
P1-3  · las versiones IDEL ("1"/"2"/"3") se leían como enero/febrero/marzo,
        así que los informes semestral y anual salían idénticos.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from backend.rgenerator.reports import runtime
from backend.rgenerator.reports.branding import (
    LEFT_FOOTER_DENYLIST,
    aplicar_center_header,
    center_header_dinamico,
    es_pie_denegado,
    formatear_filtros,
    formatear_valor_filtro,
    lineas_encabezado_prueba,
    pie_saneado,
    reemplazar_ultima_linea,
    valor_unico,
)
from backend.rgenerator.reports.errores import DatosInsuficientes

RAIZ = Path(__file__).resolve().parents[2]
REPORTS_DIR = RAIZ / "backend" / "rgenerator" / "reports"
TIPOS_V2 = ("simce", "simce_panguipulli", "dia")


def _esquema(tipo: str) -> dict:
    return json.loads((REPORTS_DIR / tipo / "esquema.json").read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────────────────
# P1-1 · pie izquierdo con nombre personal
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestDenylistDelPie:
    def test_la_denylist_no_esta_vacia(self):
        assert "Miguel Godoy Díaz" in LEFT_FOOTER_DENYLIST

    @pytest.mark.parametrize("valor", [
        "Miguel Godoy Díaz",
        "miguel godoy diaz",          # sin tildes ni mayúsculas
        "  Miguel   Godoy   Díaz  ",  # espacios repetidos
        "Miguel Godoy",
    ])
    def test_reconoce_las_variantes_del_pie_legacy(self, valor):
        assert es_pie_denegado(valor) is True
        assert pie_saneado(valor) == ""

    @pytest.mark.parametrize("valor", ["Fundación PHP", "Colegio X", "", None, "  "])
    def test_no_toca_pies_legitimos(self, valor):
        assert es_pie_denegado(valor) is False
        assert pie_saneado(valor) == str(valor or "").strip()

    def test_dispatch_v2_cae_al_nombre_de_la_org(self, db_session, org):
        """El pie legacy se trata como vacío ⇒ gana el nombre de la org."""
        from backend.rgenerator.reports.dispatch_v2 import aplicar_pie_organizacion

        out = aplicar_pie_organizacion(
            db_session, org.id,
            {"branding": {"left_footer": "Miguel Godoy Díaz"}},
        )
        assert out["branding"]["left_footer"] == org.name

    def test_motor_v1_deja_el_pie_vacio_para_que_gane_la_org(self, db_session, org):
        """`_load_branding` (motor weasyprint por layout) sanea el pie.

        El template `report_base.html` renderiza `org_name` cuando
        `branding.left_footer` viene vacío.
        """
        from backend.rgenerator.core.report_steps import _load_branding

        branding = _load_branding(
            {"branding": {"left_footer": "Miguel Godoy Díaz", "center_header": ["X"]}},
            db_session, org.id,
        )
        assert branding is not None
        assert branding["left_footer"] == ""

    def test_motor_v1_respeta_un_pie_legitimo(self, db_session, org):
        from backend.rgenerator.core.report_steps import _load_branding

        branding = _load_branding(
            {"branding": {"left_footer": "Escuela Rural Pullinque"}}, db_session, org.id
        )
        assert branding["left_footer"] == "Escuela Rural Pullinque"


# ─────────────────────────────────────────────────────────────────────────
# P1-2 · subtítulos con repr de listas
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestEtiquetaDeFiltros:
    @pytest.mark.parametrize("valor,esperado", [
        (["MAYO"], "MAYO"),
        ("MAYO", "MAYO"),
        (["1", "2", "3"], "1, 2 y 3"),
        (["DIAGNOSTICO", "INTERMEDIO", "CIERRE"], "DIAGNOSTICO, INTERMEDIO y CIERRE"),
        (["ABRIL", "MAYO", "JUNIO", "AGOSTO", "OCTUBRE", "NOVIEMBRE"],
         "ABRIL, MAYO y 4 más"),
        ([], ""),
        (None, ""),
        (2026, "2026"),
    ])
    def test_formatea_valores(self, valor, esperado):
        assert formatear_valor_filtro(valor) == esperado

    def test_nunca_emite_repr_de_lista(self):
        etiqueta = formatear_filtros({"Año": "2026", "Mes": ["MAYO"]})
        assert etiqueta == "Año: 2026 · Mes: MAYO"
        assert "[" not in etiqueta and "'" not in etiqueta

    def test_omite_filtros_vacios(self):
        assert formatear_filtros({"Curso": "", "Mes": ["MAYO"], "Año": None}) == "Mes: MAYO"

    @pytest.mark.parametrize("valor,esperado", [
        ("2026-04-07 00:00:00", "2026-04-07"),
        ("2026-04-07T00:00:00", "2026-04-07"),
        ("2026-04-07 00:00:00.000", "2026-04-07"),
        ("2026-04-07 08:30:00", "2026-04-07 08:30:00"),  # una hora real se conserva
        ("2026-04-07", "2026-04-07"),
    ])
    def test_recorta_la_medianoche_de_las_fechas(self, valor, esperado):
        """QA P1-12: `Fecha: 2026-04-07 00:00:00` en el subtítulo."""
        assert formatear_valor_filtro(valor) == esperado

    def test_el_subtitulo_del_motor_v1_es_legible(self, db_session, org):
        """`build_pdf_bytes` arma `filters_label` desde {id_dimension: valor}."""
        from backend.rgenerator.core.report_steps import _etiquetas_de_filtros
        from tests.factories import make_dimension

        mes = make_dimension(db_session, org, name="Mes")
        etiquetas = _etiquetas_de_filtros(db_session, {str(mes.id_dimension): ["MAYO"]})
        assert formatear_filtros(etiquetas) == "Mes: MAYO"


# ─────────────────────────────────────────────────────────────────────────
# P0-10 / P0-11 · encabezado con placeholders muertos
# ─────────────────────────────────────────────────────────────────────────

# Literales que NO deben quedar en ningún center_header del repo: se
# imprimen tal cual en todas las páginas del informe.
_LITERALES_MUERTOS = (
    "Asignatura - Curso",
    "Asignatura Nivel Medio",
    "Mes Año",
)


@pytest.mark.unit
class TestCenterHeaderSinPlaceholders:
    @pytest.mark.parametrize("tipo", TIPOS_V2)
    def test_el_esquema_no_trae_literales_muertos(self, tipo):
        header = (_esquema(tipo).get("branding") or {}).get("center_header") or []
        for linea in header:
            assert linea not in _LITERALES_MUERTOS, (
                f"{tipo}/esquema.json trae el placeholder muerto {linea!r} en "
                "center_header. Las líneas dinámicas las construye crear_informe.py."
            )

    @pytest.mark.parametrize("tipo", TIPOS_V2)
    def test_el_esquema_solo_declara_el_nombre_del_informe(self, tipo):
        header = (_esquema(tipo).get("branding") or {}).get("center_header") or []
        assert len(header) == 1, (
            f"{tipo}/esquema.json debe declarar SOLO el nombre del informe; "
            f"el resto lo construye crear_informe.py. Actual: {header}"
        )

    def test_center_header_dinamico_conserva_solo_el_nombre_base(self):
        assert center_header_dinamico(
            ["Informe Ensayo SIMCE", "Asignatura - Curso", "Mes Año"],
            ["Lenguaje - II A", "MAYO 2026"],
        ) == ["Informe Ensayo SIMCE", "Lenguaje - II A", "MAYO 2026"]

    def test_center_header_descarta_lineas_vacias(self):
        assert center_header_dinamico(["Informe DIA"], ["", None, "DIAGNOSTICO 2026"]) == [
            "Informe DIA", "DIAGNOSTICO 2026",
        ]

    def test_el_override_del_usuario_manda(self):
        out = aplicar_center_header(
            {"branding": {"center_header": ["Lo que puso el usuario"]}},
            base=["Informe DIA"], lineas=["DIAGNOSTICO", "2026"],
        )
        assert out["branding"]["center_header"] == ["Lo que puso el usuario"]

    def test_sin_override_se_construye_el_header(self):
        out = aplicar_center_header(
            {"branding": {"left_footer": "Fundación PHP"}},
            base=["Informe DIA"], lineas=["Lenguaje", "DIAGNOSTICO 2026"],
        )
        assert out["branding"]["center_header"] == [
            "Informe DIA", "Lenguaje", "DIAGNOSTICO 2026",
        ]
        assert out["branding"]["left_footer"] == "Fundación PHP"

    def test_valor_unico_solo_cuando_hay_uno(self):
        df = pd.DataFrame({"Curso": ["II A", "II A"], "Mes": ["MAYO", "JUNIO"]})
        assert valor_unico(df, "Curso") == "II A"
        assert valor_unico(df, "Mes") is None
        assert valor_unico(df, "NoExiste") is None

    def test_lineas_encabezado_de_una_prueba(self):
        df = pd.DataFrame({
            "Curso": ["II A", "II A"], "Mes": ["MAYO", "MAYO"], "Año": ["2026", "2026"],
        })
        assert lineas_encabezado_prueba(df, "Lenguaje", 1, "MAYO") == [
            "Lenguaje - II A", "MAYO 2026",
        ]

    def test_lineas_encabezado_omite_el_curso_si_hay_varios(self):
        df = pd.DataFrame({"Curso": ["II A", "II B"], "Año": ["2026", "2026"]})
        lineas = lineas_encabezado_prueba(df, "Lenguaje", 3, None)
        assert lineas[0] == "Lenguaje"
        assert lineas[1] == "Prueba N° 3 · 2026"


@pytest.mark.unit
class TestUltimaLineaDelHeader:
    def test_reemplaza_solo_la_ultima(self):
        assert reemplazar_ultima_linea(
            ["Informe DIA", "Lectura Nivel Medio", "Octubre 2025"], "DIAGNOSTICO 2026"
        ) == ["Informe DIA", "Lectura Nivel Medio", "DIAGNOSTICO 2026"]

    def test_con_una_sola_linea_agrega_el_periodo(self):
        assert reemplazar_ultima_linea(["Informe DIA"], "DIAGNOSTICO 2026") == [
            "Informe DIA", "DIAGNOSTICO 2026",
        ]

    def test_sin_header_no_inventa_uno(self):
        assert reemplazar_ultima_linea(None, "DIAGNOSTICO 2026") == []
        assert reemplazar_ultima_linea([], "DIAGNOSTICO 2026") == []

    def test_sin_descripcion_deja_el_header_igual(self):
        assert reemplazar_ultima_linea(["A", "B"], "") == ["A", "B"]


# ─────────────────────────────────────────────────────────────────────────
# P0-4b · time_ordinal_levels desincronizados
# ─────────────────────────────────────────────────────────────────────────

# Valores reales de la dimensión Mes/Hito en la DB dev (2026-07-30), en
# orden cronológico. Si los datos incorporan un mes nuevo hay que agregarlo
# acá Y en el esquema: un mes ausente deja slope/delta nulos para ese mes.
_NIVELES_ESPERADOS = {
    "simce": ["ABRIL", "MAYO", "JUNIO", "AGOSTO", "OCTUBRE", "NOVIEMBRE"],
    "simce_panguipulli": ["ABRIL", "MAYO", "AGOSTO", "SEPTIEMBRE"],
    "dia": ["DIAGNOSTICO", "INTERMEDIO", "CIERRE"],
}


@pytest.mark.unit
class TestNivelesOrdinales:
    @pytest.mark.parametrize("tipo", TIPOS_V2)
    def test_los_niveles_del_esquema_matchean_los_datos(self, tipo):
        esperados = _NIVELES_ESPERADOS[tipo]
        encontrados = []
        for entry in _esquema(tipo).get("derived_fields") or []:
            for cfg in entry.get("configs") or []:
                niveles = cfg.get("time_ordinal_levels")
                if niveles is not None:
                    encontrados.append((cfg.get("name"), niveles))
        assert encontrados, f"{tipo}/esquema.json sin configs ordinales"
        for nombre, niveles in encontrados:
            assert niveles == esperados, (
                f"{tipo}/esquema.json → {nombre}.time_ordinal_levels desincronizado "
                f"con los datos.\n  esquema: {niveles}\n  datos:   {esperados}"
            )

    def test_simce_ya_no_declara_octubre_2(self):
        """"OCTUBRE 2" no existe en los datos: era un nivel fantasma."""
        for entry in _esquema("simce").get("derived_fields") or []:
            for cfg in entry.get("configs") or []:
                assert "OCTUBRE 2" not in (cfg.get("time_ordinal_levels") or [])


# ─────────────────────────────────────────────────────────────────────────
# P0-1 · sección fallida y dataset vacío
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestSeccionFallidaNoFiltraElTraceback:
    def test_el_pdf_recibe_un_aviso_neutro(self, caplog):
        """La excepción va al log; al PDF solo el aviso neutro."""
        def _explota(df, **kwargs):
            raise ValueError(
                "List of boxplot statistics and 'positions' values must have "
                "same the length"
            )

        with pytest.MonkeyPatch.context() as mp:
            mp.setitem(
                runtime.charts.CHART_REGISTRY, "_chart_qa_boom",
                {"fn": _explota, "label": "boom"},
            )
            with caplog.at_level("ERROR"):
                out = runtime._ejecutar_seccion(
                    {"tipo": "chart", "titulo": "Logro por Eje", "fn": "_chart_qa_boom",
                     "df_input": "estudiantes", "params": {}},
                    {"estudiantes": pd.DataFrame({"a": [1]})},
                    Path("."),
                )

        assert out["tipo"] == "error"
        assert out["msg"] == runtime.AVISO_SECCION_FALLIDA
        assert "ValueError" not in out["msg"]
        assert "boxplot" not in out["msg"]
        assert out["titulo"] == "Logro por Eje"
        # el detalle técnico sí queda registrado
        assert "boxplot" in caplog.text

    def test_df_faltante_tambien_da_aviso_neutro(self):
        out = runtime._ejecutar_seccion(
            {"tipo": "chart", "titulo": "X", "fn": "lo_que_sea",
             "df_input": "no_existe", "params": {}},
            {}, Path("."),
        )
        assert out["msg"] == runtime.AVISO_SECCION_FALLIDA

    def test_chart_inexistente_tambien_da_aviso_neutro(self):
        out = runtime._ejecutar_seccion(
            {"tipo": "chart", "titulo": "X", "fn": "no_registrado",
             "df_input": "estudiantes", "params": {}},
            {"estudiantes": pd.DataFrame({"a": [1]})}, Path("."),
        )
        assert out["msg"] == runtime.AVISO_SECCION_FALLIDA


@pytest.mark.unit
class TestDatasetVacioNoGeneraPdf:
    def test_construir_pdf_aborta_si_el_df_principal_esta_vacio(self):
        with pytest.raises(DatosInsuficientes) as exc:
            runtime.construir_pdf(
                "dia",
                {"estudiantes": pd.DataFrame({"Hito": []}), "preguntas": pd.DataFrame()},
                df_principal="estudiantes",
                filtros_desc="Hito: INTERMEDIO · Año: 2026",
            )
        detalle = str(exc.value)
        assert "no tienen datos" in detalle
        assert "Hito: INTERMEDIO" in detalle and "Año: 2026" in detalle

    def test_sin_filtros_el_mensaje_habla_de_datos_no_cargados(self):
        with pytest.raises(DatosInsuficientes) as exc:
            runtime.construir_pdf(
                "dia", {"estudiantes": pd.DataFrame()}, df_principal="estudiantes"
            )
        assert "no tiene datos cargados" in str(exc.value)

    def test_dia_construir_con_combo_hito_anio_inexistente(self):
        """Repro exacto del QA: INTERMEDIO existe, 2026 existe, el cruce no.

        No se mockea weasyprint: la guardia corta ANTES de renderizar.
        """
        df_est = pd.DataFrame({
            "Hito": ["INTERMEDIO", "DIAGNOSTICO"],
            "Año": ["2025", "2026"],
            "Curso": ["7 A", "7 A"],
            "Nombre": ["Ana", "Ana"],
            "Asignatura": ["Lenguaje", "Lenguaje"],
            "Logro": [0.5, 0.6],
        })
        from backend.rgenerator.reports.dia import crear_informe as dia_informe

        with pytest.raises(DatosInsuficientes) as exc:
            dia_informe.construir(df_est, df_est.copy(), hito="INTERMEDIO", anio="2026")
        assert "INTERMEDIO" in str(exc.value) and "2026" in str(exc.value)

    def test_datos_insuficientes_es_un_valueerror(self):
        """Los routers lo traducen a 400 vía `except (DatosInsuficientes, ValueError)`."""
        assert issubclass(DatosInsuficientes, ValueError)
