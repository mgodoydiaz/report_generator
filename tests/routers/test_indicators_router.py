"""Tests del router /api/indicators."""
from __future__ import annotations

import json

import pytest

from tests.factories import make_indicator, make_metric, make_org, make_user


@pytest.mark.integration
class TestListIndicators:
    def test_sin_auth_401(self, client):
        r = client.get("/api/indicators/")
        assert r.status_code == 401

    def test_lista_vacia_si_no_hay_indicators(self, client_auth):
        r = client_auth.get("/api/indicators/")
        assert r.status_code == 200
        assert r.json() == []

    def test_lista_solo_los_de_mi_org(self, client_auth, db_session, org):
        """Multi-tenancy: nunca debe filtrar indicadores de otra org."""
        # Mi org
        make_indicator(db_session, org, name="Mio")
        # Otra org
        other = make_org(db_session)
        make_indicator(db_session, other, name="DeOtraOrg")

        r = client_auth.get("/api/indicators/")
        assert r.status_code == 200
        names = [i["name"] for i in r.json()]
        assert "Mio" in names
        assert "DeOtraOrg" not in names

    def test_lista_incluye_metric_ids(self, client_auth, db_session, org):
        m1 = make_metric(db_session, org, name="M1")
        m2 = make_metric(db_session, org, name="M2")
        ind = make_indicator(db_session, org, name="Con metrics", metrics=[m1, m2])
        r = client_auth.get("/api/indicators/")
        assert r.status_code == 200
        data = r.json()
        rec = next(x for x in data if x["id_indicator"] == ind.id_indicator)
        assert sorted(rec["metric_ids"]) == sorted([m1.id_metric, m2.id_metric])


@pytest.mark.integration
class TestCreateIndicator:
    def test_crear_minimo(self, client_auth, org):
        r = client_auth.post("/api/indicators/", json={"name": "Nuevo"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["name"] == "Nuevo"
        assert data["type"] == "Evaluación"  # default

    def test_crear_con_metric_ids_valida(self, client_auth, db_session, org):
        m = make_metric(db_session, org, name="X")
        r = client_auth.post("/api/indicators/", json={
            "name": "Con Metric",
            "metric_ids": [m.id_metric],
        })
        assert r.status_code == 200
        assert r.json()["data"]["metric_ids"] == [m.id_metric]

    def test_crear_con_metric_de_otra_org_400(self, client_auth, db_session):
        """Si referencia metric_id de otra org, rechaza."""
        other = make_org(db_session)
        m_foreign = make_metric(db_session, other, name="Foreign")
        r = client_auth.post("/api/indicators/", json={
            "name": "Mal",
            "metric_ids": [m_foreign.id_metric],
        })
        assert r.status_code == 400

    def test_crear_con_metric_inexistente_400(self, client_auth):
        r = client_auth.post("/api/indicators/", json={
            "name": "Mal",
            "metric_ids": [99999],
        })
        assert r.status_code == 400


@pytest.mark.integration
class TestUpdateIndicator:
    def test_update_nombre(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Original")
        r = client_auth.put(f"/api/indicators/{ind.id_indicator}", json={
            "name": "Cambiado",
            "type": "Evaluación",
        })
        assert r.status_code == 200, r.text
        # PUT solo devuelve {"status": "success"} — verificar via GET
        db_session.expire(ind)
        from backend.models import Indicator
        refreshed = db_session.query(Indicator).filter(
            Indicator.id_indicator == ind.id_indicator
        ).first()
        assert refreshed.name == "Cambiado"

    def test_update_indicator_de_otra_org_404(self, client_auth, db_session):
        other = make_org(db_session)
        ind = make_indicator(db_session, other, name="Foreign")
        r = client_auth.put(f"/api/indicators/{ind.id_indicator}", json={
            "name": "Hack",
            "type": "Evaluación",
        })
        assert r.status_code == 404

    def test_update_inexistente_404(self, client_auth):
        r = client_auth.put("/api/indicators/99999", json={
            "name": "X",
            "type": "Evaluación",
        })
        assert r.status_code == 404


@pytest.mark.integration
class TestDeleteIndicator:
    def test_delete_funciona(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Borrame")
        r = client_auth.delete(f"/api/indicators/{ind.id_indicator}")
        assert r.status_code == 200
        # Verificar borrado
        from backend.models import Indicator
        n = db_session.query(Indicator).filter(
            Indicator.id_indicator == ind.id_indicator
        ).count()
        assert n == 0

    def test_delete_de_otra_org_404(self, client_auth, db_session):
        other = make_org(db_session)
        ind = make_indicator(db_session, other, name="X")
        r = client_auth.delete(f"/api/indicators/{ind.id_indicator}")
        assert r.status_code == 404


@pytest.mark.integration
class TestSelectinloadNoNPlus1:
    """Regresión del fix f8e9234: GET /indicators usa selectinload de
    metric_links. Con N indicadores, debe hacer ~2 queries totales (1 para
    indicators + 1 para metric_links IN), no N+1.
    """

    def test_get_indicators_no_genera_extra_queries_por_indicador(
        self, client_auth, db_session, org
    ):
        from sqlalchemy import event
        # Crear 5 indicators con metrics asociadas
        for i in range(5):
            m = make_metric(db_session, org, name=f"M{i}")
            make_indicator(db_session, org, name=f"Ind{i}", metrics=[m])

        # Contar queries durante la request
        queries: list[str] = []

        def _track(conn, cursor, statement, *args, **kwargs):
            # Filtrar las queries relevantes al modelo IndicatorMetric
            if "indicator_metrics" in statement.lower():
                queries.append(statement)

        from backend.database import engine
        # En tests el engine real no se usa (TestClient hace override del db),
        # pero podemos contar queries del db_session.
        event.listen(db_session.bind, "before_cursor_execute", _track)
        try:
            r = client_auth.get("/api/indicators/")
            assert r.status_code == 200
            assert len(r.json()) == 5
        finally:
            event.remove(db_session.bind, "before_cursor_execute", _track)

        # selectinload: 1 query con WHERE id_indicator IN (...) — no 5 individuales
        indicator_metrics_queries = [q for q in queries if "indicator_metrics" in q.lower()]
        # Con selectinload: 1 query. Con lazy N+1: 5+ queries.
        # Toleramos 1-2 (puede haber alguna verificación extra) pero NO 5+.
        assert len(indicator_metrics_queries) <= 2, (
            f"Demasiadas queries a indicator_metrics: {len(indicator_metrics_queries)}. "
            f"Verificar que GET /indicators sigue usando selectinload."
        )
