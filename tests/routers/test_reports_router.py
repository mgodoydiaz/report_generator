"""Tests del router /api/reports/{tipo}."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.factories import (
    make_dimension, make_indicator, make_metric, make_metric_data, make_org,
)


@pytest.fixture
def simce_indicator(db_session, org):
    """Indicador SIMCE con 2 métricas (estudiantes + preguntas) y dimensiones."""
    dims = {}
    for name in ("Curso", "RUT", "Nombre", "Asignatura", "Mes", "N Prueba"):
        d = make_dimension(db_session, org, name=name)
        dims[name] = d

    m_est = make_metric(
        db_session, org,
        name="Resultados SIMCE por Estudiante",
        data_type="object",
        fields=[
            {"name": "Buenas", "type": "int"},
            {"name": "Rend", "type": "float"},
        ],
        dimensions=list(dims.values()),
    )
    m_preg = make_metric(
        db_session, org,
        name="Resultados SIMCE por Pregunta",
        data_type="object",
        fields=[{"name": "Logro", "type": "float"}],
        dimensions=list(dims.values()),
    )
    ind = make_indicator(db_session, org, name="SIMCE Test", metrics=[m_est, m_preg])

    # Insertar al menos 1 row con todas las dimensiones, para que apply_delta
    # tenga algo con qué groupby
    dim_to_id = {n: str(d.id_dimension) for n, d in dims.items()}
    base_dims = {
        dim_to_id["Curso"]: "II A",
        dim_to_id["RUT"]: "1-1",
        dim_to_id["Nombre"]: "Test",
        dim_to_id["Asignatura"]: "Lenguaje",
        dim_to_id["Mes"]: "ABRIL",
        dim_to_id["N Prueba"]: "1",
    }
    make_metric_data(
        db_session, m_est, value={"Buenas": 8, "Rend": 0.5},
        dimensions_json=base_dims,
    )
    make_metric_data(
        db_session, m_preg, value={"Logro": 0.6},
        dimensions_json={**base_dims, dim_to_id["Curso"]: ""},  # preguntas no van por curso
    )
    return ind


@pytest.mark.integration
class TestExportEngines:
    def test_lista_motores_disponibles(self, client_auth):
        r = client_auth.get("/api/indicators/export-pdf/engines")
        assert r.status_code == 200
        engines = r.json()
        assert isinstance(engines, list)
        engine_ids = [e["id"] for e in engines]
        assert "weasyprint" in engine_ids


@pytest.mark.integration
class TestReportsV2:
    def test_sin_auth_401(self, client):
        r = client.post("/api/reports/simce", json={"indicator_id": 1, "filtros": {"Mes": "ABRIL"}})
        assert r.status_code == 401

    def test_tipo_inexistente_404(self, client_auth):
        r = client_auth.post("/api/reports/inventado", json={"indicator_id": 1, "filtros": {"Mes": "ABRIL"}})
        assert r.status_code == 404

    def test_sin_filtro_temporal_400(self, client_auth, simce_indicator):
        """El motor v2 requiere al menos un filtro temporal por tipo."""
        r = client_auth.post(
            "/api/reports/simce",
            json={"indicator_id": simce_indicator.id_indicator, "filtros": {}},
        )
        assert r.status_code == 400
        assert "temporal" in r.json()["detail"].lower()

    def test_genera_pdf_con_mocks(self, client_auth, simce_indicator):
        """Path feliz: con datos en BD y mock de WeasyPrint, devuelve PDF bytes."""
        fake_pdf = b"%PDF-1.4 fake\n"
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            return_value=fake_pdf,
        ):
            r = client_auth.post("/api/reports/simce", json={
                "indicator_id": simce_indicator.id_indicator,
                "filtros": {"Mes": "ABRIL"},
            })
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")
