"""Tests del despacho compartido del motor v2 (`reports/dispatch_v2.py`).

Es la lógica que usan TANTO el endpoint legacy `POST /api/reports/{tipo}`
COMO los informes del registro `reports/custom/`, así que un bug acá rompe
ambos caminos.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.rgenerator.reports.dispatch_v2 import (
    DatosInsuficientes,
    FILTROS_TEMPORALES_V2,
    TIPOS_V2,
    TipoNoSoportado,
    aplicar_pie_organizacion,
    separar_filtros,
    validar_tipo,
)


@pytest.mark.unit
class TestValidaciones:
    def test_tipos_soportados(self):
        assert TIPOS_V2 == ("simce", "simce_panguipulli", "dia")

    def test_validar_tipo_ok(self):
        for tipo in TIPOS_V2:
            validar_tipo(tipo)  # no levanta

    def test_validar_tipo_desconocido(self):
        with pytest.raises(TipoNoSoportado) as exc:
            validar_tipo("inventado")
        assert "no soportado" in str(exc.value)

    def test_filtros_temporales_por_tipo(self):
        assert FILTROS_TEMPORALES_V2["simce"] == ["Mes", "N Prueba", "Numero_Prueba"]
        assert FILTROS_TEMPORALES_V2["dia"] == ["Hito", "Año"]

    def test_separar_filtros_sin_temporal_falla(self):
        with pytest.raises(DatosInsuficientes) as exc:
            separar_filtros("simce", {"Curso": "II A"})
        assert "temporal" in str(exc.value).lower()

    def test_separar_filtros_sin_filtros_falla(self):
        with pytest.raises(DatosInsuficientes):
            separar_filtros("dia", None)

    def test_separar_filtros_divide_por_rol(self):
        estructurales, temporales = separar_filtros(
            "simce", {"Curso": "II A", "Asignatura": "LENGUAJE", "Mes": "ABRIL"}
        )
        assert estructurales == {"Curso": "II A", "Asignatura": "LENGUAJE"}
        assert temporales == {"Mes": "ABRIL"}

    def test_separar_filtros_dia_acepta_solo_anio(self):
        estructurales, temporales = separar_filtros("dia", {"Año": "2025"})
        assert estructurales == {}
        assert temporales == {"Año": "2025"}


@pytest.mark.integration
class TestPieDeOrganizacion:
    def test_inyecta_org_name_cuando_no_viene(self, db_session, org):
        out = aplicar_pie_organizacion(db_session, org.id, None)
        assert out["branding"]["left_footer"] == org.name

    def test_inyecta_org_name_cuando_viene_vacio(self, db_session, org):
        out = aplicar_pie_organizacion(db_session, org.id, {"branding": {"left_footer": "  "}})
        assert out["branding"]["left_footer"] == org.name

    def test_respeta_el_pie_explicito(self, db_session, org):
        out = aplicar_pie_organizacion(
            db_session, org.id, {"branding": {"left_footer": "Colegio X"}}
        )
        assert out["branding"]["left_footer"] == "Colegio X"

    def test_no_pisa_otros_overrides(self, db_session, org):
        out = aplicar_pie_organizacion(db_session, org.id, {
            "title": "Mi informe",
            "branding": {"center_header": ["a", "b", "c"]},
        })
        assert out["title"] == "Mi informe"
        assert out["branding"]["center_header"] == ["a", "b", "c"]
        assert out["branding"]["left_footer"] == org.name

    def test_org_inexistente_no_rompe(self, db_session):
        out = aplicar_pie_organizacion(db_session, 999_999, None)
        assert out == {}


# El fixture `simce_indicator` vive en `tests/conftest.py` desde el piloto
# del motor único (contrato N9): lo comparten estos tests, los del despacho
# por modos y los del módulo SIMCE.


@pytest.mark.integration
class TestPieEnLosDosCaminos:
    """El pie izquierdo debe salir del nombre de la org en ambos endpoints."""

    def test_endpoint_legacy_inyecta_el_pie(self, client_auth, simce_indicator, org):
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            return_value=b"%PDF-1.4\n",
        ) as mock:
            r = client_auth.post("/api/reports/simce", json={
                "indicator_id": simce_indicator.id_indicator,
                "filtros": {"Mes": "ABRIL"},
            })
        assert r.status_code == 200, r.text
        overrides = mock.call_args.kwargs["overrides"]
        assert overrides["branding"]["left_footer"] == org.name

    def test_endpoint_custom_inyecta_el_pie(self, client_auth, simce_indicator, org):
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            return_value=b"%PDF-1.4\n",
        ) as mock:
            r = client_auth.post("/api/reports/custom/simce", json={
                "indicator_id": simce_indicator.id_indicator,
                "filtros": {"Mes": "ABRIL"},
            })
        assert r.status_code == 200, r.text
        overrides = mock.call_args.kwargs["overrides"]
        assert overrides["branding"]["left_footer"] == org.name

    def test_pie_explicito_del_usuario_manda(self, client_auth, simce_indicator):
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            return_value=b"%PDF-1.4\n",
        ) as mock:
            r = client_auth.post("/api/reports/custom/simce", json={
                "indicator_id": simce_indicator.id_indicator,
                "filtros": {"Mes": "ABRIL"},
                "overrides": {"branding": {"left_footer": "Escuela Pullinque"}},
            })
        assert r.status_code == 200, r.text
        assert mock.call_args.kwargs["overrides"]["branding"]["left_footer"] == "Escuela Pullinque"

    def test_custom_sin_filtro_temporal_400(self, client_auth, simce_indicator):
        r = client_auth.post("/api/reports/custom/simce", json={
            "indicator_id": simce_indicator.id_indicator,
            "filtros": {},
        })
        assert r.status_code == 400
        assert "temporal" in r.json()["detail"].lower()


@pytest.mark.integration
class TestPieLegacyDeLaDB:
    """QA 2026-07-30 (P1-1): los layouts persistidos traían el nombre del
    desarrollador en `branding.left_footer`, y como venía con valor el
    fallback al nombre de la organización nunca se activaba."""

    def test_el_pie_legacy_se_ignora_y_gana_la_org(self, db_session, org):
        out = aplicar_pie_organizacion(
            db_session, org.id, {"branding": {"left_footer": "Miguel Godoy Díaz"}}
        )
        assert out["branding"]["left_footer"] == org.name

    def test_el_pie_legacy_tambien_se_ignora_desde_el_endpoint(
        self, client_auth, simce_indicator, org
    ):
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            return_value=b"%PDF-1.4\n",
        ) as mock:
            r = client_auth.post("/api/reports/custom/simce", json={
                "indicator_id": simce_indicator.id_indicator,
                "filtros": {"Mes": "ABRIL"},
                "overrides": {"branding": {"left_footer": "Miguel Godoy Díaz"}},
            })
        assert r.status_code == 200, r.text
        assert mock.call_args.kwargs["overrides"]["branding"]["left_footer"] == org.name


@pytest.mark.integration
class TestFiltrosSinDatosDan400:
    """QA 2026-07-30 (P0-1): HTTP 200 con un PDF vacío de 552 KB.

    El informe salía con tablas de solo encabezados, gráficos en blanco y
    el traceback impreso en la página 2.
    """

    def test_filtro_estructural_sin_datos_400(self, client_auth, simce_indicator):
        """Curso inexistente + mes válido → 400 accionable, no un PDF vacío."""
        r = client_auth.post("/api/reports/custom/simce", json={
            "indicator_id": simce_indicator.id_indicator,
            "filtros": {"Mes": "ABRIL", "Curso": "NO EXISTE"},
        })
        assert r.status_code == 400, r.text
        detalle = r.json()["detail"]
        assert "no tienen datos" in detalle
        assert "Curso: NO EXISTE" in detalle

    def test_filtro_temporal_sin_datos_400(self, client_auth, simce_indicator):
        """Mes inexistente (el filtro temporal lo aplica crear_informe)."""
        r = client_auth.post("/api/reports/custom/simce", json={
            "indicator_id": simce_indicator.id_indicator,
            "filtros": {"Mes": "DICIEMBRE"},
        })
        assert r.status_code == 400, r.text
        assert "no tienen datos" in r.json()["detail"]

    def test_el_endpoint_legacy_tambien_devuelve_400(self, client_auth, simce_indicator):
        r = client_auth.post("/api/reports/simce", json={
            "indicator_id": simce_indicator.id_indicator,
            "filtros": {"Mes": "DICIEMBRE"},
        })
        assert r.status_code == 400, r.text

    def test_el_caso_valido_sigue_devolviendo_200(self, client_auth, simce_indicator):
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            return_value=b"%PDF-1.4\n",
        ):
            r = client_auth.post("/api/reports/custom/simce", json={
                "indicator_id": simce_indicator.id_indicator,
                "filtros": {"Mes": "ABRIL"},
            })
        assert r.status_code == 200, r.text


@pytest.mark.integration
class TestCenterHeaderRealEnElDespacho:
    """QA 2026-07-30 (P0-11): el encabezado salía con "Asignatura - Curso"
    y "Mes Año" literales en las 14/14 páginas del informe SIMCE."""

    def test_se_construye_con_los_params_de_la_corrida(
        self, client_auth, simce_indicator
    ):
        with patch(
            "backend.rgenerator.reports.runtime.construir_pdf",
            return_value=b"%PDF-1.4\n",
        ) as mock:
            r = client_auth.post("/api/reports/custom/simce", json={
                "indicator_id": simce_indicator.id_indicator,
                "filtros": {"Mes": "ABRIL", "Asignatura": "Lenguaje"},
            })
        assert r.status_code == 200, r.text
        header = mock.call_args.kwargs["overrides"]["branding"]["center_header"]
        assert header[0] == "Informe Ensayo SIMCE"
        assert "Asignatura - Curso" not in header
        assert "Mes Año" not in header
        assert "Lenguaje" in header[1] and "II A" in header[1]
        assert header[2].startswith("ABRIL")

    def test_el_override_del_usuario_manda(self, client_auth, simce_indicator):
        with patch(
            "backend.rgenerator.reports.runtime.construir_pdf",
            return_value=b"%PDF-1.4\n",
        ) as mock:
            r = client_auth.post("/api/reports/custom/simce", json={
                "indicator_id": simce_indicator.id_indicator,
                "filtros": {"Mes": "ABRIL"},
                "overrides": {"branding": {"center_header": ["Mi título"]}},
            })
        assert r.status_code == 200, r.text
        assert mock.call_args.kwargs["overrides"]["branding"]["center_header"] == ["Mi título"]
