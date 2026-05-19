"""Tests del router /api/metrics."""
from __future__ import annotations

import pytest

from tests.factories import make_dimension, make_metric, make_metric_data, make_org


@pytest.mark.integration
class TestListMetrics:
    def test_sin_auth_401(self, client):
        r = client.get("/api/metrics/")
        assert r.status_code == 401

    def test_lista_vacia(self, client_auth):
        r = client_auth.get("/api/metrics/")
        assert r.status_code == 200
        assert r.json() == []

    def test_lista_filtra_por_org(self, client_auth, db_session, org):
        make_metric(db_session, org, name="Mia")
        other = make_org(db_session)
        make_metric(db_session, other, name="Ajena")
        r = client_auth.get("/api/metrics/")
        names = [m["name"] for m in r.json()]
        assert "Mia" in names
        assert "Ajena" not in names


@pytest.mark.integration
class TestCreateMetric:
    def test_crear_metric_basico(self, client_auth):
        r = client_auth.post("/api/metrics/", json={
            "name": "Logro",
            "data_type": "float",
            "meta_json": {},
            "description": "",
            "unit": "",
            "dimension_ids": [],
        })
        assert r.status_code == 200, r.text


@pytest.mark.integration
class TestGetMetricData:
    def test_get_data_metric_inexistente_404(self, client_auth):
        r = client_auth.get("/api/metrics/99999/data")
        assert r.status_code == 404

    def test_get_data_metric_de_otra_org_404(self, client_auth, db_session):
        other = make_org(db_session)
        m = make_metric(db_session, other, name="X")
        r = client_auth.get(f"/api/metrics/{m.id_metric}/data")
        assert r.status_code == 404


@pytest.mark.integration
class TestAddDataPoint:
    def test_add_punto_a_metric_de_otra_org_404(self, client_auth, db_session):
        other = make_org(db_session)
        m = make_metric(db_session, other, name="X")
        r = client_auth.post(f"/api/metrics/{m.id_metric}/data", json={
            "value": "1.0",
            "dimensions_json": {},
        })
        assert r.status_code == 404


@pytest.mark.integration
class TestClearMetricData:
    def test_clear_borra_todos_los_data_points(self, client_auth, db_session, org):
        m = make_metric(db_session, org, name="Borrar")
        make_metric_data(db_session, m, value="1.0")
        make_metric_data(db_session, m, value="2.0")
        # Confirmar 2 antes
        from backend.models import MetricData
        n_before = db_session.query(MetricData).filter(MetricData.id_metric == m.id_metric).count()
        assert n_before == 2
        r = client_auth.post(f"/api/metrics/{m.id_metric}/clear")
        assert r.status_code == 200
        db_session.expire_all()
        n_after = db_session.query(MetricData).filter(MetricData.id_metric == m.id_metric).count()
        assert n_after == 0
