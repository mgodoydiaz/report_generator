"""Tests de GET /api/indicators/{id}/report-options y del campo report_engine_type.

Fase 1 del selector de tipo de informe (docs/qa/QA_MAESTRO.md → decisión 1,
hallazgos informes H3/H5): catálogo único de informes disponibles por
indicador, con el motor especializado como campo explícito y fallback a
la heurística por nombre solo para retrocompatibilidad.
"""
from __future__ import annotations

import json

import pytest

from tests.factories import make_indicator, make_org


def _opciones_por_id(body):
    return {o["id"]: o for o in body["opciones"]}


@pytest.mark.integration
class TestReportOptions:
    def test_cross_org_404(self, client_auth, db_session):
        otra = make_org(db_session, name="Org Ajena RO")
        ajeno = make_indicator(db_session, otra, name="Ajeno")
        resp = client_auth.get(f"/api/indicators/{ajeno.id_indicator}/report-options")
        assert resp.status_code == 404

    def test_indicador_generico_sin_layouts(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Asistencia Mensual")
        resp = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options")
        assert resp.status_code == 200
        body = resp.json()
        assert body["engine_type"] is None
        ops = _opciones_por_id(body)
        # Los PDF v1 se listan pero no disponibles (sin secciones), con motivo accionable
        assert ops["pdf_evaluacion"]["disponible"] is False
        assert "Editor de Layout" in ops["pdf_evaluacion"]["motivo_no_disponible"]
        assert ops["pdf_historico"]["disponible"] is False
        # Sin tipo especializado: ni v2 ni pdl_idel
        assert not any(o["motor"] in ("v2", "pdl_idel") for o in body["opciones"])
        # El informe Word registrado aparece
        assert any(o["formato"] == "word" for o in body["opciones"])

    def test_pdf_v1_disponible_con_secciones(self, client_auth, db_session, org):
        ind = make_indicator(
            db_session, org, name="Con Layout",
            pdf_layout=json.dumps({"sections": [{"type": "kpi"}]}),
        )
        resp = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options")
        ops = _opciones_por_id(resp.json())
        assert ops["pdf_evaluacion"]["disponible"] is True
        assert ops["pdf_evaluacion"]["invocacion"]["params"]["tipo"] == "evaluacion"

    def test_engine_type_inferido_por_nombre(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="SIMCE Lenguaje 2026")
        body = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        assert body["engine_type"] == "simce"
        assert body["engine_type_origen"] == "inferido"
        ops = _opciones_por_id(body)
        assert ops["v2_simce"]["disponible"] is True
        assert "Mes" in ops["v2_simce"]["requiere_filtro_temporal"]

    def test_campo_explicito_gana_al_nombre(self, client_auth, db_session, org):
        # El nombre sugiere SIMCE pero el campo dice dia → manda el campo (fix H5)
        ind = make_indicator(
            db_session, org, name="Comparativo DIA-SIMCE",
            report_engine_type="dia",
        )
        body = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        assert body["engine_type"] == "dia"
        assert body["engine_type_origen"] == "campo"
        ops = _opciones_por_id(body)
        assert "v2_dia" in ops
        assert "v2_simce" not in ops
        assert ops["v2_dia"]["requiere_filtro_temporal"] == ["Hito", "Año"]

    def test_pdl_idel_agrega_opcion_especializada(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Lectura", report_engine_type="pdl_idel")
        body = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        ops = _opciones_por_id(body)
        assert ops["pdl_idel"]["disponible"] is True
        assert ops["pdl_idel"]["invocacion"]["params"]["engine"] == "pdl_idel"


@pytest.mark.integration
class TestReportEngineTypeCRUD:
    def test_create_persiste_campo(self, client_auth):
        resp = client_auth.post("/api/indicators/", json={
            "name": "Nuevo IDEL", "type": "Evaluación",
            "report_engine_type": "pdl_idel", "metric_ids": [],
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["report_engine_type"] == "pdl_idel"

    def test_update_setea_y_limpia_campo(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Editable")
        base = {"name": "Editable", "type": "Evaluación"}

        resp = client_auth.put(
            f"/api/indicators/{ind.id_indicator}",
            json={**base, "report_engine_type": "simce"},
        )
        assert resp.status_code == 200
        db_session.refresh(ind)
        assert ind.report_engine_type == "simce"

        # "" explícito limpia el campo → vuelve a genérico
        resp = client_auth.put(
            f"/api/indicators/{ind.id_indicator}",
            json={**base, "report_engine_type": ""},
        )
        assert resp.status_code == 200
        db_session.refresh(ind)
        assert ind.report_engine_type is None
