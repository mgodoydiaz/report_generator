"""Tests del router /api/charts."""
from __future__ import annotations

import pytest

from tests.factories import make_metric, make_org


@pytest.fixture
def chart_config_minimal():
    return {
        "chart_type": "bar",
        "data_source": {"metric_id": None, "filters": {}},
        "mapping": {"x_field": "Curso", "y_field": "Logro", "aggregation": "mean"},
        "aesthetics": {},
    }


@pytest.mark.integration
class TestListAndCreateChart:
    def test_sin_auth_401(self, client):
        r = client.get("/api/charts/")
        assert r.status_code == 401

    def test_lista_vacia(self, client_auth):
        r = client_auth.get("/api/charts/")
        assert r.status_code == 200
        assert r.json() == []

    def test_crear_chart_basico(self, client_auth, db_session, org, chart_config_minimal):
        m = make_metric(db_session, org, name="Logro")
        chart_config_minimal["data_source"]["metric_id"] = m.id_metric
        r = client_auth.post("/api/charts/", json={
            "name": "Mi Chart",
            "description": "test",
            "config": chart_config_minimal,
        })
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "success"
        assert "id_spec" in r.json()


@pytest.mark.integration
class TestGetChartTypes:
    def test_lista_metadata_chart_types(self, client_auth):
        r = client_auth.get("/api/charts/types")
        assert r.status_code == 200
        data = r.json()
        # Debe haber al menos bar, pie, line
        chart_types = list(data.keys()) if isinstance(data, dict) else [c.get("type") for c in data]
        assert "bar" in chart_types or any("bar" in str(c) for c in chart_types)


@pytest.mark.integration
class TestDeleteChart:
    def test_delete_chart_inexistente_404(self, client_auth):
        r = client_auth.delete("/api/charts/99999")
        assert r.status_code == 404
