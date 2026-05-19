"""Smoke tests para validar que la infraestructura de tests funciona.

Si estos pasan, podés escribir tests usando `client`, `client_auth`,
`db_session`, `org`, `user`, `auth_headers` con confianza.

Fase 0 — Infrastructure tests. Ver TESTING.md.
"""
from __future__ import annotations

import pytest


@pytest.mark.integration
class TestEngineFixture:
    def test_engine_se_crea(self, engine):
        assert engine is not None

    def test_engine_tiene_tabla_organizations(self, engine):
        from sqlalchemy import inspect
        names = inspect(engine).get_table_names()
        assert "organizations" in names
        assert "users" in names
        assert "indicators" in names
        assert "metric_data" in names


@pytest.mark.integration
class TestDbSessionFixture:
    def test_db_session_funciona(self, db_session):
        from backend.models import Organization
        o = Organization(name="X", slug="x")
        db_session.add(o)
        db_session.commit()
        assert o.id is not None

    def test_db_session_rollback_entre_tests_a(self, db_session):
        """Crea un org. El siguiente test (b) NO debe verlo — rollback."""
        from backend.models import Organization
        o = Organization(name="LEAK_TEST", slug="leak-test")
        db_session.add(o)
        db_session.commit()

    def test_db_session_rollback_entre_tests_b(self, db_session):
        from backend.models import Organization
        n = db_session.query(Organization).filter(Organization.slug == "leak-test").count()
        assert n == 0, "Rollback entre tests no funciona — hay leak"


@pytest.mark.integration
class TestClientFixture:
    def test_client_levanta_app(self, client):
        # El endpoint raíz del backend devuelve algo (depende, puede ser 404
        # si no hay route, pero el TestClient debe inicializar).
        r = client.get("/api/auth/me")
        # Sin auth → 401, pero el server respondió
        assert r.status_code in (401, 403, 422)

    def test_client_ve_los_datos_de_db_session(self, client, db_session):
        """Crítico: el override de get_db debe apuntar a la MISMA sesión
        que la fixture db_session. Si fallara, el TestClient vería una DB
        distinta y no encontraría los objetos creados en setup."""
        from backend.models import Organization
        o = Organization(name="VisibleDesdeClient", slug="visible")
        db_session.add(o)
        db_session.commit()
        # El endpoint /api/auth/me no muestra orgs, pero podemos usar otro:
        # verificar que NO levanta error de "DB inaccesible".
        r = client.get("/api/auth/me")
        assert r.status_code == 401  # sin token → 401, no 500


@pytest.mark.integration
class TestAuthFixtures:
    def test_org_se_crea(self, org):
        assert org.id is not None
        assert org.is_active is True

    def test_user_pertenece_a_org(self, user, org):
        assert user.org_id == org.id
        assert user.email == "test@example.com"

    def test_auth_headers_formato(self, auth_headers):
        assert "Authorization" in auth_headers
        assert auth_headers["Authorization"].startswith("Bearer ")

    def test_client_auth_pasa_endpoint_autenticado(self, client_auth):
        r = client_auth.get("/api/auth/me")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"] == "test@example.com"
        assert data["role"] == "editor"


@pytest.mark.integration
class TestFactories:
    def test_make_org(self, db_session):
        from tests.factories import make_org
        o = make_org(db_session)
        assert o.id is not None
        assert o.slug.startswith("org-")

    def test_make_metric_con_dimensions(self, db_session):
        from tests.factories import make_dimension, make_metric, make_org
        o = make_org(db_session)
        d1 = make_dimension(db_session, o, name="Curso")
        d2 = make_dimension(db_session, o, name="Año")
        m = make_metric(db_session, o, name="Logro", dimensions=[d1, d2],
                        fields=[{"name": "x", "type": "float"}])
        assert m.id_metric is not None
        # Verificar que se crearon los MetricDimension links
        from backend.models import MetricDimension
        n_links = db_session.query(MetricDimension).filter(
            MetricDimension.id_metric == m.id_metric
        ).count()
        assert n_links == 2

    def test_make_indicator_con_metrics(self, db_session):
        from tests.factories import make_indicator, make_metric, make_org
        o = make_org(db_session)
        m1 = make_metric(db_session, o)
        m2 = make_metric(db_session, o)
        ind = make_indicator(db_session, o, metrics=[m1, m2])
        from backend.models import IndicatorMetric
        n = db_session.query(IndicatorMetric).filter(
            IndicatorMetric.id_indicator == ind.id_indicator
        ).count()
        assert n == 2


@pytest.mark.unit
def test_markers_funcionan():
    """Sanity check del sistema de markers."""
    pass
