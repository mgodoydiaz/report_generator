"""Tests de autorización por rol y de validación de JWT (QA gate W0).

Parte 1 — require_admin / require_superadmin: un rol insuficiente recibe 403
en los endpoints que exigen esos privilegios (users, superadmin).

Parte 2 — JWT: sin token, firma inválida y token expirado devuelven 401.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from backend.auth import JWT_ALGORITHM, JWT_SECRET, create_access_token
from tests.factories import auth_header_for, make_org, make_user


# ─────────────────────────────────────────────────────────────────────────
# require_admin — router /api/users (escritura solo admin)
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestRequireAdmin:
    def _editor(self, db_session):
        org = make_org(db_session, name="RA", slug="ra")
        return make_user(db_session, org, role="editor")

    def test_editor_no_crea_usuario_403(self, client, db_session):
        editor = self._editor(db_session)
        res = client.post(
            "/api/users/",
            json={"email": "nuevo@x.com", "password": "x", "role": "editor"},
            headers=auth_header_for(editor),
        )
        assert res.status_code == 403

    def test_editor_no_edita_usuario_403(self, client, db_session):
        editor = self._editor(db_session)
        res = client.put(
            f"/api/users/{editor.id}",
            json={"name": "yo"},
            headers=auth_header_for(editor),
        )
        assert res.status_code == 403

    def test_editor_no_borra_usuario_403(self, client, db_session):
        editor = self._editor(db_session)
        res = client.delete(
            f"/api/users/{editor.id}",
            headers=auth_header_for(editor),
        )
        assert res.status_code == 403

    def test_admin_si_crea_usuario(self, client, db_session):
        org = make_org(db_session, name="RA2", slug="ra2")
        admin = make_user(db_session, org, role="admin")
        res = client.post(
            "/api/users/",
            json={"email": "creado@x.com", "password": "secreta", "role": "viewer"},
            headers=auth_header_for(admin),
        )
        assert res.status_code == 201, res.text
        assert res.json()["email"] == "creado@x.com"


# ─────────────────────────────────────────────────────────────────────────
# require_superadmin — router /api/superadmin
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestRequireSuperadmin:
    def test_admin_normal_no_accede_403(self, client, db_session):
        org = make_org(db_session, name="RS", slug="rs")
        admin = make_user(db_session, org, role="admin")  # admin pero NO superadmin
        res = client.get(
            "/api/superadmin/organizations",
            headers=auth_header_for(admin),
        )
        assert res.status_code == 403

    def test_superadmin_si_accede(self, client, db_session):
        org = make_org(db_session, name="RS2", slug="rs2")
        sadmin = make_user(db_session, org, role="admin", is_superadmin=True)
        res = client.get(
            "/api/superadmin/organizations",
            headers=auth_header_for(sadmin),
        )
        assert res.status_code == 200


# ─────────────────────────────────────────────────────────────────────────
# JWT — validación de token en get_current_user
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestJWTValidacion:
    def test_sin_token_401(self, client):
        res = client.get("/api/users/")
        assert res.status_code == 401

    def test_firma_invalida_401(self, client, db_session):
        org = make_org(db_session, name="JW", slug="jw")
        user = make_user(db_session, org, role="admin")
        # Token bien formado pero firmado con OTRO secreto → firma inválida
        forged = jwt.encode(
            {"sub": str(user.id), "org_id": user.org_id, "role": user.role,
             "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "secreto-equivocado",
            algorithm=JWT_ALGORITHM,
        )
        res = client.get("/api/users/", headers={"Authorization": f"Bearer {forged}"})
        assert res.status_code == 401

    def test_token_expirado_401(self, client, db_session):
        org = make_org(db_session, name="JW2", slug="jw2")
        user = make_user(db_session, org, role="admin")
        expired = jwt.encode(
            {"sub": str(user.id), "org_id": user.org_id, "role": user.role,
             "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        res = client.get("/api/users/", headers={"Authorization": f"Bearer {expired}"})
        assert res.status_code == 401

    def test_token_valido_de_usuario_inexistente_401(self, client):
        # Firma válida pero el sub no corresponde a ningún usuario activo.
        token = create_access_token(user_id=99999999, org_id=1, role="editor")
        res = client.get("/api/users/", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
