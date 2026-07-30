"""Tests de POST /api/indicators/{id}/export-pdf con el campo `periodo`.

El período declarativo se resuelve contra los datos reales
(`rgenerator/reports/periodos.py`), decide el `tipo_layout` (ignorando el
`tipo` del body) y aporta filtros temporales traducidos a
`{id_dimension: valor}`, que es el contrato que consume `build_pdf_bytes`.

`build_pdf_bytes` se mockea (weasyprint no está instalado en todos los
hosts) y se usa como sonda para verificar QUÉ filtros y QUÉ layout llegan.
"""
from __future__ import annotations

import json
from datetime import date
from unittest.mock import patch

import pytest

from backend.rgenerator.reports.periodos import NUMERO_A_MES
from tests.factories import (
    make_dimension, make_indicator, make_metric, make_metric_data,
)

FAKE_PDF = b"%PDF-1.4 periodo\n"
LAYOUT_EVAL = json.dumps({"sections": [{"type": "kpi"}], "marca": "evaluacion"})
LAYOUT_HIST = json.dumps({"sections": [{"type": "line"}], "marca": "historico"})


@pytest.fixture
def hoy():
    return date.today()


@pytest.fixture
def indicador(db_session, org, hoy):
    """Indicador con Curso/Año/Mes/N Prueba y datos del año en curso.

    Deliberadamente SIN `report_engine_type` y con un nombre que no dispara
    la heurística de `engine_types.inferir_engine_type`: estos tests cubren
    el camino v1 (`build_pdf_bytes`), que es el fallback cuando el
    indicador no tiene módulo del motor único. El despacho al módulo lo
    cubre `tests/reports/test_despacho_modos.py`.
    """
    dims = {n: make_dimension(db_session, org, name=n)
            for n in ("Curso", "Año", "Mes", "N Prueba")}
    metric = make_metric(
        db_session, org, name="Resultados SIMCE por Estudiante",
        data_type="object", fields=[{"name": "Logro", "type": "float"}],
        dimensions=list(dims.values()),
    )
    ident = {n: str(d.id_dimension) for n, d in dims.items()}
    make_metric_data(db_session, metric, value={"Logro": 0.4}, dimensions_json={
        ident["Curso"]: "II A", ident["Año"]: str(hoy.year - 1),
        ident["Mes"]: "ABRIL", ident["N Prueba"]: "1",
    })
    make_metric_data(db_session, metric, value={"Logro": 0.7}, dimensions_json={
        ident["Curso"]: "II B", ident["Año"]: str(hoy.year),
        ident["Mes"]: NUMERO_A_MES[hoy.month], ident["N Prueba"]: "3",
    })
    ind = make_indicator(
        db_session, org, name="Ensayo Lenguaje", metrics=[metric],
        pdf_layout=LAYOUT_EVAL, pdf_layout_historico=LAYOUT_HIST,
    )
    ind._ident = ident
    return ind


def _exportar(client_auth, indicator_id, body):
    """POST export-pdf con build_pdf_bytes mockeado. Devuelve (resp, mock)."""
    with patch(
        "backend.rgenerator.core.report_steps.build_pdf_bytes",
        return_value=FAKE_PDF,
    ) as mock:
        resp = client_auth.post(
            f"/api/indicators/{indicator_id}/export-pdf", json=body
        )
    return resp, mock


@pytest.mark.integration
class TestExportPDFConPeriodo:
    def test_ultima_prueba_filtra_al_punto_mas_reciente(self, client_auth, indicador, hoy):
        resp, mock = _exportar(client_auth, indicador.id_indicator, {
            "periodo": {"tipo": "ultima_prueba"},
        })
        assert resp.status_code == 200, resp.text
        assert resp.content == FAKE_PDF

        filtros = mock.call_args.kwargs["filters"]
        ident = indicador._ident
        assert filtros == {
            ident["Año"]: str(hoy.year),
            ident["Mes"]: NUMERO_A_MES[hoy.month],
            ident["N Prueba"]: "3",
        }
        # ultima_prueba → layout por evaluación
        assert mock.call_args.kwargs["pdf_layout_override"]["marca"] == "evaluacion"

    def test_anual_usa_layout_historico_e_ignora_el_tipo_del_body(
        self, client_auth, indicador, hoy
    ):
        resp, mock = _exportar(client_auth, indicador.id_indicator, {
            "tipo": "evaluacion",              # debe ser ignorado
            "periodo": {"tipo": "anual"},
        })
        assert resp.status_code == 200, resp.text
        assert mock.call_args.kwargs["pdf_layout_override"]["marca"] == "historico"
        assert mock.call_args.kwargs["filters"] == {
            indicador._ident["Año"]: str(hoy.year)
        }

    def test_semestral_manda_lista_de_meses_permitidos(self, client_auth, indicador, hoy):
        resp, mock = _exportar(client_auth, indicador.id_indicator, {
            "periodo": {"tipo": "semestral"},
        })
        assert resp.status_code == 200, resp.text
        filtros = mock.call_args.kwargs["filters"]
        assert filtros[indicador._ident["Año"]] == str(hoy.year)
        assert filtros[indicador._ident["Mes"]] == [NUMERO_A_MES[hoy.month]]
        assert mock.call_args.kwargs["pdf_layout_override"]["marca"] == "historico"

    def test_personalizado_con_rango(self, client_auth, indicador, hoy):
        resp, mock = _exportar(client_auth, indicador.id_indicator, {
            "periodo": {
                "tipo": "personalizado",
                "fecha_inicio": f"{hoy.year - 1}-01",
                "fecha_fin": f"{hoy.year - 1}-12",
            },
        })
        assert resp.status_code == 200, resp.text
        filtros = mock.call_args.kwargs["filters"]
        assert filtros[indicador._ident["Año"]] == [str(hoy.year - 1)]
        assert filtros[indicador._ident["Mes"]] == ["ABRIL"]

    def test_filtros_del_body_se_combinan_con_los_del_periodo(
        self, client_auth, indicador, hoy
    ):
        ident = indicador._ident
        resp, mock = _exportar(client_auth, indicador.id_indicator, {
            "filters": {ident["Curso"]: "II B"},
            "periodo": {"tipo": "ultima_prueba"},
        })
        assert resp.status_code == 200, resp.text
        filtros = mock.call_args.kwargs["filters"]
        assert filtros[ident["Curso"]] == "II B"          # el del body sobrevive
        assert filtros[ident["Año"]] == str(hoy.year)     # el del período se agrega

    def test_el_periodo_gana_sobre_un_filtro_temporal_del_body(
        self, client_auth, indicador, hoy
    ):
        ident = indicador._ident
        resp, mock = _exportar(client_auth, indicador.id_indicator, {
            "filters": {ident["Mes"]: "ABRIL"},
            "periodo": {"tipo": "ultima_prueba"},
        })
        assert resp.status_code == 200, resp.text
        assert mock.call_args.kwargs["filters"][ident["Mes"]] == NUMERO_A_MES[hoy.month]

    def test_sin_periodo_el_comportamiento_no_cambia(self, client_auth, indicador):
        resp, mock = _exportar(client_auth, indicador.id_indicator, {
            "tipo": "historico",
        })
        assert resp.status_code == 200, resp.text
        assert mock.call_args.kwargs["pdf_layout_override"]["marca"] == "historico"
        assert mock.call_args.kwargs["filters"] is None


@pytest.mark.integration
class TestExportPDFPeriodoErrores:
    def test_periodo_no_resoluble_400_con_motivo(self, client_auth, db_session, org):
        """Indicador sin dimensión temporal → 400 explicativo."""
        dim = make_dimension(db_session, org, name="Curso")
        metric = make_metric(db_session, org, name="Asistencia por Estudiante",
                             data_type="float", dimensions=[dim])
        make_metric_data(db_session, metric, value=0.9,
                         dimensions_json={str(dim.id_dimension): "II A"})
        ind = make_indicator(db_session, org, name="Asistencia", metrics=[metric],
                             pdf_layout=LAYOUT_EVAL)
        resp, _ = _exportar(client_auth, ind.id_indicator, {
            "periodo": {"tipo": "ultima_prueba"},
        })
        assert resp.status_code == 400
        assert "dimensión temporal" in resp.json()["detail"]

    def test_anual_sin_datos_del_anio_400(self, client_auth, db_session, org, hoy):
        dims = {n: make_dimension(db_session, org, name=n) for n in ("Año", "Mes")}
        metric = make_metric(db_session, org, name="M por Estudiante",
                             data_type="float", dimensions=list(dims.values()))
        make_metric_data(db_session, metric, value=1.0, dimensions_json={
            str(dims["Año"].id_dimension): "2019",
            str(dims["Mes"].id_dimension): "ABRIL",
        })
        ind = make_indicator(db_session, org, name="Viejo", metrics=[metric],
                            pdf_layout_historico=LAYOUT_HIST)
        resp, _ = _exportar(client_auth, ind.id_indicator, {
            "periodo": {"tipo": "anual"},
        })
        assert resp.status_code == 400
        assert "Sin datos del año en curso" in resp.json()["detail"]

    def test_indicador_sin_datos_400(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Sin Datos", pdf_layout=LAYOUT_EVAL)
        resp, _ = _exportar(client_auth, ind.id_indicator, {
            "periodo": {"tipo": "ultima_prueba"},
        })
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Sin datos cargados para este indicador."

    def test_tipo_de_periodo_invalido_400(self, client_auth, indicador):
        resp, _ = _exportar(client_auth, indicador.id_indicator, {
            "periodo": {"tipo": "trimestral"},
        })
        assert resp.status_code == 400
        assert "desconocido" in resp.json()["detail"]

    def test_periodo_que_resuelve_a_historico_sin_layout_422(
        self, client_auth, db_session, org, hoy
    ):
        """Sin pdf_layout_historico, el informe anual no se puede renderizar."""
        dims = {n: make_dimension(db_session, org, name=n) for n in ("Año", "Mes")}
        metric = make_metric(db_session, org, name="M por Estudiante",
                             data_type="float", dimensions=list(dims.values()))
        make_metric_data(db_session, metric, value=1.0, dimensions_json={
            str(dims["Año"].id_dimension): str(hoy.year),
            str(dims["Mes"].id_dimension): NUMERO_A_MES[hoy.month],
        })
        ind = make_indicator(db_session, org, name="Solo Eval", metrics=[metric],
                             pdf_layout=LAYOUT_EVAL)
        resp, _ = _exportar(client_auth, ind.id_indicator, {
            "periodo": {"tipo": "anual"},
        })
        assert resp.status_code == 422
        assert "histórico" in resp.json()["detail"]

    def test_cross_org_404(self, client_auth, db_session):
        from tests.factories import make_org
        otra = make_org(db_session, name="Org Ajena Export")
        ajeno = make_indicator(db_session, otra, name="Ajeno", pdf_layout=LAYOUT_EVAL)
        resp, _ = _exportar(client_auth, ajeno.id_indicator, {
            "periodo": {"tipo": "ultima_prueba"},
        })
        assert resp.status_code == 404


LAYOUT_CON_HEADER = json.dumps({
    "sections": [{"type": "kpi"}],
    "marca": "evaluacion",
    "branding": {
        "center_header": ["Informe DIA", "Lectura Nivel Medio", "Octubre 2025"],
        "left_footer": "",
    },
})


@pytest.mark.integration
class TestEncabezadoConElPeriodoResuelto:
    """QA 2026-07-30 (P0-10): el encabezado decía "Octubre 2025" mientras el
    cuerpo mostraba datos de 2026. La última línea del `center_header` la
    resuelve el backend contra los datos; las demás son configuración del
    usuario y no se tocan."""

    @pytest.fixture
    def indicador_con_header(self, db_session, org, indicador):
        indicador.pdf_layout = LAYOUT_CON_HEADER
        db_session.commit()
        return indicador

    def test_reemplaza_solo_la_ultima_linea(self, client_auth, indicador_con_header, hoy):
        resp, mock = _exportar(client_auth, indicador_con_header.id_indicator, {
            "periodo": {"tipo": "ultima_prueba"},
        })
        assert resp.status_code == 200, resp.text
        header = mock.call_args.kwargs["branding_override"]["center_header"]
        assert header[:2] == ["Informe DIA", "Lectura Nivel Medio"]
        assert header[2] != "Octubre 2025"
        assert NUMERO_A_MES[hoy.month] in header[2] and str(hoy.year) in header[2]

    def test_el_branding_del_usuario_no_se_pisa(self, client_auth, indicador_con_header):
        resp, mock = _exportar(client_auth, indicador_con_header.id_indicator, {
            "periodo": {"tipo": "ultima_prueba"},
            "branding_override": {"center_header": ["Solo lo mío"]},
        })
        assert resp.status_code == 200, resp.text
        assert mock.call_args.kwargs["branding_override"]["center_header"] == ["Solo lo mío"]

    def test_sin_center_header_configurado_no_se_inventa(self, client_auth, indicador):
        """`LAYOUT_EVAL` no declara branding: el informe sigue sin encabezado."""
        resp, mock = _exportar(client_auth, indicador.id_indicator, {
            "periodo": {"tipo": "ultima_prueba"},
        })
        assert resp.status_code == 200, resp.text
        assert mock.call_args.kwargs["branding_override"] is None

    def test_sin_periodo_el_header_no_se_toca(self, client_auth, indicador_con_header):
        resp, mock = _exportar(client_auth, indicador_con_header.id_indicator, {
            "tipo": "evaluacion",
        })
        assert resp.status_code == 200, resp.text
        assert mock.call_args.kwargs["branding_override"] is None


@pytest.mark.integration
class TestExportPDFSinDatosDa400:
    """QA 2026-07-30 (P0-1): un PDF con gráficos en blanco es peor que un error."""

    def test_datos_insuficientes_se_traduce_a_400(self, client_auth, indicador):
        from backend.rgenerator.reports.errores import DatosInsuficientes

        with patch(
            "backend.rgenerator.core.report_steps.build_pdf_bytes",
            side_effect=DatosInsuficientes(
                "Los filtros seleccionados no tienen datos: Curso: ZZZ."
            ),
        ):
            resp = client_auth.post(
                f"/api/indicators/{indicador.id_indicator}/export-pdf",
                json={"tipo": "evaluacion"},
            )
        assert resp.status_code == 400, resp.text
        assert "no tienen datos" in resp.json()["detail"]

    def test_build_pdf_bytes_aborta_con_records_vacios(self, db_session, org, indicador):
        """La guardia real, sin mocks (requiere weasyprint operativo).

        `build_pdf_bytes` importa weasyprint al entrar, y en hosts Windows
        sin las libs nativas de Pango/Cairo eso levanta OSError — de ahí el
        skip explícito en vez de `importorskip` (que solo captura
        ImportError).
        """
        try:
            import weasyprint  # noqa: F401
        except Exception as e:  # pragma: no cover — depende del host
            pytest.skip(f"weasyprint no operativo en este host: {e}")
        from backend.rgenerator.core.report_steps import build_pdf_bytes
        from backend.rgenerator.reports.errores import DatosInsuficientes

        ident = indicador._ident
        with pytest.raises(DatosInsuficientes) as exc:
            build_pdf_bytes(
                indicador, db_session, org.id,
                filters={ident["Curso"]: "CURSO QUE NO EXISTE"},
            )
        assert "no tienen datos" in str(exc.value)
        assert "Curso: CURSO QUE NO EXISTE" in str(exc.value)
