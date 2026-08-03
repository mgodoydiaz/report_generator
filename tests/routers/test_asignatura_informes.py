"""Informes separados por asignatura — contrato de API.

Un indicador puede traer varias asignaturas en las mismas metrics (el DIA
de la fundación carga LECTURA y MATEMATICA del mismo alumno). Generar el
informe sin fijarla convierte cada alumno en tantos "alumnos" como pruebas
rindió, así que:

    GET  /api/indicators/{id}/report-options   publica el campo `asignatura`
                                               en las cards PDF.
    POST /api/indicators/{id}/export-pdf       400 si no se fija a UNA.
    POST /api/reports/custom/{nombre}          idem, vía `dispatch_v2`.

Con 0 ó 1 asignatura NADA cambia: es la no-regresión de IDEL / Fluidez
Lectora / Cálculo Veloz, que tienen una sola.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from backend.rgenerator.reports.periodos import NUMERO_A_MES
from tests.factories import (
    make_dimension, make_indicator, make_metric, make_metric_data,
)

FAKE_PDF = b"%PDF-1.4 asignatura\n"
LAYOUT_EVAL = json.dumps({"sections": [{"type": "kpi"}], "marca": "evaluacion"})
LAYOUT_HIST = json.dumps({"sections": [{"type": "line"}], "marca": "historico"})


def _indicador_dia(db_session, org, hoy, asignaturas: list[str]):
    """Indicador DIA con una fila por (asignatura × alumno) del año en curso.

    Replica la forma real de los datos: la misma metric guarda LECTURA y
    MATEMATICA del mismo `Nombre`, que es exactamente lo que duplicaba los
    conteos de alumnos.
    """
    dims = {n: make_dimension(db_session, org, name=n)
            for n in ("Curso", "Nombre", "Asignatura", "Año", "Mes", "Hito")}
    m_est = make_metric(
        db_session, org, name="Resultados DIA por Estudiante", data_type="object",
        fields=[{"name": "Logro", "type": "float"}],
        dimensions=list(dims.values()),
    )
    m_preg = make_metric(
        db_session, org, name="Resultados DIA por Pregunta", data_type="object",
        fields=[{"name": "Logro", "type": "float"}],
        dimensions=list(dims.values()),
    )
    ident = {n: str(d.id_dimension) for n, d in dims.items()}
    for asignatura in asignaturas:
        base = {
            ident["Curso"]: "II A", ident["Nombre"]: "Ana Perez",
            ident["Asignatura"]: asignatura, ident["Año"]: str(hoy.year),
            ident["Mes"]: NUMERO_A_MES[hoy.month], ident["Hito"]: "DIAGNOSTICO",
        }
        make_metric_data(db_session, m_est, value={"Logro": 0.5}, dimensions_json=base)
        make_metric_data(db_session, m_preg, value={"Logro": 0.6}, dimensions_json=base)

    ind = make_indicator(
        db_session, org, name="DIA Test", metrics=[m_est, m_preg],
        report_engine_type="dia", pdf_layout=LAYOUT_EVAL,
        pdf_layout_historico=LAYOUT_HIST,
    )
    ind._ident = ident
    return ind


@pytest.fixture
def indicador_multi(db_session, org, hoy):
    """DIA con LECTURA + MATEMATICA → elegir asignatura es obligatorio."""
    return _indicador_dia(db_session, org, hoy, ["LECTURA", "MATEMATICA"])


@pytest.fixture
def indicador_mono(db_session, org, hoy):
    """DIA con una sola asignatura → nada cambia (no-regresión)."""
    return _indicador_dia(db_session, org, hoy, ["LECTURA"])


def _report_options(client_auth, indicador):
    return client_auth.get(
        f"/api/indicators/{indicador.id_indicator}/report-options"
    ).json()


def _exportar(client_auth, indicator_id, body):
    """POST export-pdf con `build_pdf_bytes` mockeado. Devuelve (resp, mock)."""
    with patch(
        "backend.rgenerator.core.report_steps.build_pdf_bytes",
        return_value=FAKE_PDF,
    ) as mock:
        resp = client_auth.post(
            f"/api/indicators/{indicator_id}/export-pdf", json=body
        )
    return resp, mock


# ─────────────────────────────────────────────────────────────────────────
# GET /report-options
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestReportOptionsConAsignatura:
    def test_las_cards_de_periodo_traen_el_campo(self, client_auth, indicador_multi):
        cards = _report_options(client_auth, indicador_multi)["grupos"]["periodo"]
        assert len(cards) == 3   # semestral retirado del selector el 2026-08-03
        for card in cards:
            assert card["asignatura"] == {
                "requerida": True,
                "dimension": "Asignatura",
                "valores": ["LECTURA", "MATEMATICA"],
            }, card["id"]

    def test_la_card_custom_dia_trae_el_campo(self, client_auth, indicador_multi):
        ops = {o["id"]: o for o in _report_options(client_auth, indicador_multi)["opciones"]}
        assert ops["custom_dia"]["asignatura"]["requerida"] is True
        assert ops["custom_dia"]["asignatura"]["valores"] == ["LECTURA", "MATEMATICA"]

    def test_los_informes_word_no_aparecen(self, client_auth, indicador_multi):
        """Word está pospuesto (decisión del dueño 2026-07-30): no se lista
        en el selector, así que tampoco puede declarar asignatura."""
        body = _report_options(client_auth, indicador_multi)
        word = [o for o in body["grupos"]["especializados"] if o["formato"] == "word"]
        assert word == []


@pytest.mark.integration
class TestReportOptionsSinAsignatura:
    """No-regresión: un indicador con UNA asignatura no ve el campo."""

    def test_ninguna_card_trae_el_campo(self, client_auth, indicador_mono):
        body = _report_options(client_auth, indicador_mono)
        for opcion in body["opciones"]:
            assert "asignatura" not in opcion, opcion["id"]

    def test_indicador_sin_dimension_de_asignatura(self, client_auth, db_session, org, hoy):
        dims = {n: make_dimension(db_session, org, name=n) for n in ("Curso", "Año", "Mes")}
        metric = make_metric(
            db_session, org, name="Fluidez Lectora por Estudiante", data_type="object",
            fields=[{"name": "Logro", "type": "float"}], dimensions=list(dims.values()),
        )
        make_metric_data(db_session, metric, value={"Logro": 0.8}, dimensions_json={
            str(dims["Curso"].id_dimension): "II A",
            str(dims["Año"].id_dimension): str(hoy.year),
            str(dims["Mes"].id_dimension): NUMERO_A_MES[hoy.month],
        })
        ind = make_indicator(db_session, org, name="Fluidez Lectora", metrics=[metric],
                             pdf_layout=LAYOUT_EVAL, pdf_layout_historico=LAYOUT_HIST)
        body = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        assert all("asignatura" not in o for o in body["opciones"])


# ─────────────────────────────────────────────────────────────────────────
# POST /export-pdf
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestExportPDFExigeUnaAsignatura:
    def test_sin_asignatura_400_accionable(self, client_auth, indicador_multi):
        resp, mock = _exportar(client_auth, indicador_multi.id_indicator, {
            "periodo": {"tipo": "ultima_prueba"},
        })
        assert resp.status_code == 400, resp.text
        detalle = resp.json()["detail"]
        assert "varias asignaturas" in detalle
        assert "LECTURA" in detalle and "MATEMATICA" in detalle
        assert "Selecciona una asignatura" in detalle
        mock.assert_not_called()

    def test_multi_valor_tambien_400(self, client_auth, indicador_multi):
        resp, mock = _exportar(client_auth, indicador_multi.id_indicator, {
            "periodo": {
                "tipo": "ultima_prueba",
                "filtros": {"Asignatura": ["LECTURA", "MATEMATICA"]},
            },
        })
        assert resp.status_code == 400, resp.text
        assert "UNA sola asignatura" in resp.json()["detail"]
        mock.assert_not_called()

    def test_con_una_asignatura_200_y_filtro_traducido(
        self, client_auth, indicador_multi
    ):
        resp, mock = _exportar(client_auth, indicador_multi.id_indicator, {
            "periodo": {"tipo": "ultima_prueba", "filtros": {"Asignatura": ["LECTURA"]}},
        })
        assert resp.status_code == 200, resp.text
        assert resp.content == FAKE_PDF
        filtros = mock.call_args.kwargs["filters"]
        # `build_pdf_bytes` filtra por id_dimension, no por nombre de columna.
        assert filtros[indicador_multi._ident["Asignatura"]] == ["LECTURA"]
        assert "Asignatura" not in filtros

    def test_la_asignatura_puede_venir_en_filters_por_id(
        self, client_auth, indicador_multi
    ):
        ident = indicador_multi._ident
        resp, mock = _exportar(client_auth, indicador_multi.id_indicator, {
            "filters": {ident["Asignatura"]: "MATEMATICA"},
            "periodo": {"tipo": "ultima_prueba"},
        })
        assert resp.status_code == 200, resp.text
        assert mock.call_args.kwargs["filters"][ident["Asignatura"]] == "MATEMATICA"

    def test_sin_periodo_tambien_se_valida(self, client_auth, indicador_multi):
        resp, _ = _exportar(client_auth, indicador_multi.id_indicator, {
            "tipo": "evaluacion",
        })
        assert resp.status_code == 400, resp.text
        assert "varias asignaturas" in resp.json()["detail"]


@pytest.mark.integration
class TestExportPDFNoRegresion:
    """Un indicador con UNA asignatura exporta igual que siempre."""

    def test_sin_elegir_asignatura_200(self, client_auth, indicador_mono):
        resp, mock = _exportar(client_auth, indicador_mono.id_indicator, {
            "periodo": {"tipo": "ultima_prueba"},
        })
        assert resp.status_code == 200, resp.text
        # No se inyecta ningún filtro de asignatura que el usuario no pidió.
        assert indicador_mono._ident["Asignatura"] not in (
            mock.call_args.kwargs["filters"] or {}
        )


# ─────────────────────────────────────────────────────────────────────────
# POST /api/reports/custom/{nombre} y /api/reports/{tipo}
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestInformesCustomPorAsignatura:
    def test_custom_sin_asignatura_400(self, client_auth, indicador_multi):
        resp = client_auth.post("/api/reports/custom/dia", json={
            "indicator_id": indicador_multi.id_indicator,
            "filtros": {"Hito": "DIAGNOSTICO"},
        })
        assert resp.status_code == 400, resp.text
        assert "varias asignaturas" in resp.json()["detail"]

    def test_custom_multi_valor_400(self, client_auth, indicador_multi):
        resp = client_auth.post("/api/reports/custom/dia", json={
            "indicator_id": indicador_multi.id_indicator,
            "filtros": {"Hito": "DIAGNOSTICO", "Asignatura": ["LECTURA", "MATEMATICA"]},
        })
        assert resp.status_code == 400, resp.text
        assert "UNA sola asignatura" in resp.json()["detail"]

    def test_custom_con_una_asignatura_200_y_datos_recortados(
        self, client_auth, indicador_multi
    ):
        with patch(
            "backend.rgenerator.reports.runtime.construir_pdf",
            return_value=FAKE_PDF,
        ) as mock:
            resp = client_auth.post("/api/reports/custom/dia", json={
                "indicator_id": indicador_multi.id_indicator,
                "filtros": {"Hito": "DIAGNOSTICO", "Asignatura": "LECTURA"},
            })
        assert resp.status_code == 200, resp.text
        dataframes = mock.call_args.args[1]
        # El informe solo ve LECTURA: sin esto, la misma alumna se contaría
        # dos veces (una por asignatura rendida).
        assert set(dataframes["estudiantes"]["Asignatura"]) == {"LECTURA"}
        assert len(dataframes["estudiantes"]) == 1

    def test_endpoint_legacy_comparte_la_validacion(self, client_auth, indicador_multi):
        resp = client_auth.post("/api/reports/dia", json={
            "indicator_id": indicador_multi.id_indicator,
            "filtros": {"Hito": "DIAGNOSTICO"},
        })
        assert resp.status_code == 400, resp.text
        assert "varias asignaturas" in resp.json()["detail"]

    def test_endpoint_legacy_con_asignatura_200(self, client_auth, indicador_multi):
        with patch(
            "backend.rgenerator.reports.runtime.construir_pdf",
            return_value=FAKE_PDF,
        ):
            resp = client_auth.post("/api/reports/dia", json={
                "indicator_id": indicador_multi.id_indicator,
                "filtros": {"Hito": "DIAGNOSTICO", "Asignatura": "MATEMATICA"},
            })
        assert resp.status_code == 200, resp.text

    def test_una_sola_asignatura_no_exige_elegir(self, client_auth, indicador_mono):
        with patch(
            "backend.rgenerator.reports.runtime.construir_pdf",
            return_value=FAKE_PDF,
        ):
            resp = client_auth.post("/api/reports/custom/dia", json={
                "indicator_id": indicador_mono.id_indicator,
                "filtros": {"Hito": "DIAGNOSTICO"},
            })
        assert resp.status_code == 200, resp.text


@pytest.mark.integration
class TestSinDefaultLenguaje:
    """El motor v2 pasaba `asignatura="LENGUAJE"` cuando el filtro no venía:
    un informe de Matemática salía rotulado como Lenguaje y, peor, el filtro
    interno del SIMCE lo dejaba vacío."""

    @pytest.fixture
    def simce_matematica(self, db_session, org):
        dims = {n: make_dimension(db_session, org, name=n)
                for n in ("Curso", "RUT", "Nombre", "Asignatura", "Mes")}
        m_est = make_metric(
            db_session, org, name="Resultados SIMCE por Estudiante", data_type="object",
            fields=[{"name": "Rend", "type": "float"}], dimensions=list(dims.values()),
        )
        m_preg = make_metric(
            db_session, org, name="Resultados SIMCE por Pregunta", data_type="object",
            fields=[{"name": "Logro", "type": "float"}], dimensions=list(dims.values()),
        )
        ident = {n: str(d.id_dimension) for n, d in dims.items()}
        base = {
            ident["Curso"]: "II A", ident["RUT"]: "1-1", ident["Nombre"]: "Ana",
            ident["Asignatura"]: "MATEMATICA", ident["Mes"]: "ABRIL",
        }
        make_metric_data(db_session, m_est, value={"Rend": 0.5}, dimensions_json=base)
        make_metric_data(db_session, m_preg, value={"Logro": 0.6}, dimensions_json=base)
        return make_indicator(db_session, org, name="SIMCE Mate",
                              metrics=[m_est, m_preg], report_engine_type="simce")

    def test_usa_la_asignatura_real_del_dataset(self, client_auth, simce_matematica):
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            return_value=FAKE_PDF,
        ) as mock:
            resp = client_auth.post("/api/reports/custom/simce", json={
                "indicator_id": simce_matematica.id_indicator,
                "filtros": {"Mes": "ABRIL"},
            })
        assert resp.status_code == 200, resp.text
        header = mock.call_args.kwargs["overrides"]["branding"]["center_header"]
        assert any("MATEMATICA" in linea for linea in header)
        assert not any("LENGUAJE" in linea.upper() for linea in header)
