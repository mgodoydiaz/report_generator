"""E2E smoke tests — el path crítico que un usuario haría.

Estos tests recorren el flow completo (login → dashboard → PDF) usando
el TestClient con DB SQLite + datos seedados via factories. Detectan
regresiones cross-stack (router + ORM + engine + motor PDF).

Marcados `@pytest.mark.slow` — corren en CI pero pueden saltarse en
pre-commit con `-m "not slow"`.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.factories import (
    make_dimension, make_indicator, make_metric, make_metric_data,
    make_org, make_user,
)


@pytest.fixture
def seed_simce_lenguaje(db_session):
    """Setup completo de una org SIMCE Pullinque con usuarios + indicator
    + 2 metrics + datos reales para 2 estudiantes × 2 meses."""
    org = make_org(db_session, name="Org SIMCE", slug="org-simce")
    make_user(db_session, org, email="user@simce.com", password="pwd123")

    dims = {
        n: make_dimension(db_session, org, name=n)
        for n in ("Curso", "RUT", "Nombre", "Asignatura", "Mes", "N Prueba")
    }
    m_est = make_metric(
        db_session, org, name="Resultados SIMCE por Estudiante",
        data_type="object",
        fields=[
            {"name": "Buenas", "type": "int"},
            {"name": "Rend", "type": "float"},
        ],
        dimensions=list(dims.values()),
    )
    m_preg = make_metric(
        db_session, org, name="Resultados SIMCE por Pregunta",
        data_type="object",
        fields=[{"name": "Logro", "type": "float"}],
        dimensions=list(dims.values()),
    )
    ind = make_indicator(db_session, org, name="SIMCE Test", metrics=[m_est, m_preg])

    # 2 estudiantes × 2 meses
    for rut in ("1-1", "2-2"):
        for mes, npr, rend in [("ABRIL", 1, 0.5), ("JUNIO", 2, 0.7)]:
            make_metric_data(
                db_session, m_est, value={"Buenas": 8, "Rend": rend},
                dimensions_json={
                    str(dims["Curso"].id_dimension): "II A",
                    str(dims["RUT"].id_dimension): rut,
                    str(dims["Nombre"].id_dimension): f"Est-{rut}",
                    str(dims["Asignatura"].id_dimension): "Lenguaje",
                    str(dims["Mes"].id_dimension): mes,
                    str(dims["N Prueba"].id_dimension): str(npr),
                },
            )

    # 1 fila de preguntas (necesario: el endpoint /api/reports/simce
    # requiere que el indicator tenga ambas metrics con datos)
    for mes, npr in [("ABRIL", 1), ("JUNIO", 2)]:
        make_metric_data(
            db_session, m_preg, value={"Logro": 0.6},
            dimensions_json={
                str(dims["Asignatura"].id_dimension): "Lenguaje",
                str(dims["Mes"].id_dimension): mes,
                str(dims["N Prueba"].id_dimension): str(npr),
            },
        )

    return {"org": org, "indicator": ind, "metric_est": m_est, "metric_preg": m_preg}


@pytest.mark.slow
class TestE2ESmokeFlow:
    def test_login_then_get_indicators_then_results_then_pdf(
        self, client, seed_simce_lenguaje
    ):
        """El path crítico end-to-end completo."""
        ind = seed_simce_lenguaje["indicator"]

        # ── 1. LOGIN ──
        r = client.post("/api/auth/login", json={
            "email": "user@simce.com", "password": "pwd123",
        })
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # ── 2. /me confirma sesión ──
        r = client.get("/api/auth/me", headers=headers)
        assert r.status_code == 200
        assert r.json()["email"] == "user@simce.com"

        # ── 3. Listar indicators de la org ──
        r = client.get("/api/indicators/", headers=headers)
        assert r.status_code == 200
        ids = [i["id_indicator"] for i in r.json()]
        assert ind.id_indicator in ids

        # ── 4. Cargar dashboard data del indicator ──
        r = client.get(
            f"/api/results/indicator/{ind.id_indicator}/data",
            headers=headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["metrics"]) == 2
        # 4 rows en estudiantes (2 ruts × 2 meses)
        m_est_id = seed_simce_lenguaje["metric_est"].id_metric
        assert len(data["data"][str(m_est_id)]) == 4

        # ── 5. Generar PDF v2 SIMCE (mock de WeasyPrint) ──
        fake_pdf = b"%PDF-1.4 fake"
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            return_value=fake_pdf,
        ):
            r = client.post(
                "/api/reports/simce",
                headers=headers,
                json={
                    "indicator_id": ind.id_indicator,
                    "filtros": {"Mes": "ABRIL", "Asignatura": "Lenguaje"},
                },
            )
        assert r.status_code == 200, r.text
        assert r.content == fake_pdf

    def test_login_falla_credenciales_no_genera_token(self, client, seed_simce_lenguaje):
        r = client.post("/api/auth/login", json={
            "email": "user@simce.com", "password": "wrong",
        })
        assert r.status_code == 401

    def test_endpoint_results_sin_token_es_401(self, client, seed_simce_lenguaje):
        ind = seed_simce_lenguaje["indicator"]
        r = client.get(f"/api/results/indicator/{ind.id_indicator}/data")
        assert r.status_code == 401

    def test_pdf_sin_filtro_asignatura_usa_default_case_insensitive(
        self, client, seed_simce_lenguaje
    ):
        """Regresión: el default 'LENGUAJE' (uppercase) debe matchear
        'Lenguaje' (capitalizado) en BD. Antes del fix: KeyError 'Rut'."""
        ind = seed_simce_lenguaje["indicator"]
        r = client.post("/api/auth/login", json={
            "email": "user@simce.com", "password": "pwd123",
        })
        token = r.json()["access_token"]

        fake_pdf = b"%PDF ok"
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            return_value=fake_pdf,
        ):
            r = client.post(
                "/api/reports/simce",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "indicator_id": ind.id_indicator,
                    # SIN Asignatura → backend usa default "LENGUAJE"
                    # con case-insensitive matchea las rows BD "Lenguaje".
                    "filtros": {"Mes": "ABRIL"},
                },
            )
        # Antes del fix: 500 con KeyError 'Rut'. Ahora: 200.
        assert r.status_code == 200, r.text
