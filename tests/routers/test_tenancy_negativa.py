"""Tests de aislamiento multi-tenant NEGATIVO (QA gate W0).

Verifica que un usuario de la Org A nunca pueda leer, editar ni borrar
recursos de la Org B. Cubre los routers de mayor riesgo detectados en el
recorrido: data_ops, organizations, users y superadmin.

Garantía de seguridad verificada en cada caso:
  - lecturas cross-org devuelven 403/404 (nunca 200 con datos ajenos), y
  - escrituras cross-org NO producen modificación efectiva en la Org B
    (se comprueba el estado real en la DB después de la llamada).
"""
from __future__ import annotations

import json

import pytest

from tests.factories import (
    auth_header_for,
    make_metric,
    make_metric_data,
    make_org,
    make_user,
)


# ─────────────────────────────────────────────────────────────────────────
# data_ops — operaciones masivas sobre metric_data de otra org
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestDataOpsTenancy:
    def _setup_orgs(self, db_session):
        org_a = make_org(db_session, name="Org A", slug="org-a")
        org_b = make_org(db_session, name="Org B", slug="org-b")
        # admin: /api/data-ops/replace exige `require_admin`. Lo que se prueba
        # acá es el aislamiento entre orgs, no el gate de rol — con un editor
        # el 403 taparía el 404 de tenancy que queremos verificar.
        user_a = make_user(db_session, org_a, role="admin")
        # Métrica + dato en la Org B (víctima potencial)
        metric_b = make_metric(
            db_session, org_b, name="Metric B", data_type="object",
            fields=[{"name": "Nivel", "type": "str"}],
        )
        data_b = make_metric_data(
            db_session, metric_b, value={"Nivel": "Bajo"},
        )
        return org_a, org_b, user_a, metric_b, data_b

    def test_distinct_cross_org_404(self, client, db_session):
        _, _, user_a, metric_b, _ = self._setup_orgs(db_session)
        res = client.post(
            "/api/data-ops/distinct",
            json={"metric_id": metric_b.id_metric, "column_name": "Nivel"},
            headers=auth_header_for(user_a),
        )
        assert res.status_code == 404
        # Nunca debe filtrar datos de la métrica ajena
        assert "values" not in res.json()

    def test_replace_cross_org_no_modifica(self, client, db_session):
        _, _, user_a, metric_b, data_b = self._setup_orgs(db_session)
        res = client.post(
            "/api/data-ops/replace",
            json={
                "metric_id": metric_b.id_metric,
                "column_name": "Nivel",
                "find": "Bajo",
                "replace": "Alto",
                "match_type": "exact",
                "dry_run": False,  # intento de modificación REAL
            },
            headers=auth_header_for(user_a),
        )
        assert res.status_code == 404
        # Garantía dura: el dato de la Org B quedó intacto.
        from backend.models import MetricData
        db_session.refresh(data_b)
        row = db_session.query(MetricData).filter_by(id_data=data_b.id_data).first()
        assert json.loads(row.value) == {"Nivel": "Bajo"}


# ─────────────────────────────────────────────────────────────────────────
# organizations — assets de otra org
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestOrganizationsTenancy:
    def test_listar_assets_de_otra_org_403(self, client, db_session):
        org_a = make_org(db_session, name="OA", slug="oa")
        org_b = make_org(db_session, name="OB", slug="ob")
        # admin de A: aún así no puede ver assets de B
        admin_a = make_user(db_session, org_a, role="admin")
        res = client.get(
            f"/api/organizations/{org_b.id}/assets",
            headers=auth_header_for(admin_a),
        )
        assert res.status_code == 403

    def test_borrar_asset_de_otra_org_403_no_modifica(self, client, db_session):
        from backend.models import OrganizationAsset
        org_a = make_org(db_session, name="OA2", slug="oa2")
        org_b = make_org(db_session, name="OB2", slug="ob2")
        admin_a = make_user(db_session, org_a, role="admin")
        asset_b = OrganizationAsset(
            org_id=org_b.id, kind="logo", name="logo-b",
            filename="logo-b.png", content_type="image/png",
        )
        db_session.add(asset_b)
        db_session.commit()
        db_session.refresh(asset_b)

        res = client.delete(
            f"/api/organizations/{org_b.id}/assets/{asset_b.id}",
            headers=auth_header_for(admin_a),
        )
        assert res.status_code == 403
        # El asset de B sigue existiendo
        still = db_session.query(OrganizationAsset).filter_by(id=asset_b.id).first()
        assert still is not None


# ─────────────────────────────────────────────────────────────────────────
# users — CRUD de usuarios de otra org (admin de A vs usuario de B)
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestUsersTenancy:
    def _setup(self, db_session):
        org_a = make_org(db_session, name="UA", slug="ua")
        org_b = make_org(db_session, name="UB", slug="ub")
        admin_a = make_user(db_session, org_a, role="admin")
        user_b = make_user(db_session, org_b, role="editor", email="victima@b.com")
        return org_a, org_b, admin_a, user_b

    def test_listar_no_incluye_usuarios_de_otra_org(self, client, db_session):
        _, _, admin_a, user_b = self._setup(db_session)
        res = client.get("/api/users/", headers=auth_header_for(admin_a))
        assert res.status_code == 200
        emails = [u["email"] for u in res.json()]
        assert user_b.email not in emails

    def test_editar_usuario_de_otra_org_404_no_modifica(self, client, db_session):
        from backend.models import User
        _, _, admin_a, user_b = self._setup(db_session)
        res = client.put(
            f"/api/users/{user_b.id}",
            json={"role": "admin", "name": "hackeado"},
            headers=auth_header_for(admin_a),
        )
        assert res.status_code == 404
        db_session.refresh(user_b)
        fresh = db_session.query(User).filter_by(id=user_b.id).first()
        assert fresh.role == "editor"
        assert fresh.name != "hackeado"

    def test_borrar_usuario_de_otra_org_404_no_desactiva(self, client, db_session):
        from backend.models import User
        _, _, admin_a, user_b = self._setup(db_session)
        res = client.delete(
            f"/api/users/{user_b.id}",
            headers=auth_header_for(admin_a),
        )
        assert res.status_code == 404
        db_session.refresh(user_b)
        fresh = db_session.query(User).filter_by(id=user_b.id).first()
        assert fresh.is_active is True


# ─────────────────────────────────────────────────────────────────────────
# superadmin — un no-superadmin de A no puede tocar recursos cross-org
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestSuperadminTenancy:
    def test_admin_org_a_no_lista_organizaciones(self, client, db_session):
        org_a = make_org(db_session, name="SA", slug="sa")
        admin_a = make_user(db_session, org_a, role="admin")  # NO superadmin
        res = client.get(
            "/api/superadmin/organizations",
            headers=auth_header_for(admin_a),
        )
        assert res.status_code == 403

    def test_admin_org_a_no_edita_usuario_de_otra_org(self, client, db_session):
        from backend.models import User
        org_a = make_org(db_session, name="SA2", slug="sa2")
        org_b = make_org(db_session, name="SB2", slug="sb2")
        admin_a = make_user(db_session, org_a, role="admin")
        user_b = make_user(db_session, org_b, role="editor", email="v2@b.com")
        res = client.put(
            f"/api/superadmin/users/{user_b.id}",
            json={"is_superadmin": True},
            headers=auth_header_for(admin_a),
        )
        assert res.status_code == 403
        db_session.refresh(user_b)
        fresh = db_session.query(User).filter_by(id=user_b.id).first()
        assert bool(fresh.is_superadmin) is False
