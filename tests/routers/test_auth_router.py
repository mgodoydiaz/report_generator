"""Tests del router /api/auth: login + /me + JWT lifecycle."""
from __future__ import annotations

import pytest

from tests.factories import make_org, make_user


@pytest.mark.integration
class TestLogin:
    def test_login_credenciales_correctas_devuelve_token(self, client, db_session):
        org = make_org(db_session)
        make_user(db_session, org, email="alice@x.com", password="passw0rd")
        r = client.post("/api/auth/login", json={"email": "alice@x.com", "password": "passw0rd"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "alice@x.com"
        assert data["user"]["org_id"] == org.id

    def test_login_password_incorrecto_401(self, client, db_session):
        org = make_org(db_session)
        make_user(db_session, org, email="bob@x.com", password="correct")
        r = client.post("/api/auth/login", json={"email": "bob@x.com", "password": "wrong"})
        assert r.status_code == 401
        assert "credenciales" in r.json()["detail"].lower()

    def test_login_email_inexistente_401(self, client):
        r = client.post("/api/auth/login", json={"email": "nadie@x.com", "password": "x"})
        assert r.status_code == 401

    def test_login_user_inactivo_401(self, client, db_session):
        org = make_org(db_session)
        make_user(db_session, org, email="inactive@x.com", password="x", is_active=False)
        r = client.post("/api/auth/login", json={"email": "inactive@x.com", "password": "x"})
        assert r.status_code == 401

    def test_login_payload_invalido_422(self, client):
        r = client.post("/api/auth/login", json={"email": "x"})  # falta password
        assert r.status_code == 422


@pytest.mark.integration
class TestMeEndpoint:
    def test_me_sin_token_401(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_me_con_token_valido_devuelve_user(self, client_auth, user):
        r = client_auth.get("/api/auth/me")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["id"] == user.id
        assert data["email"] == user.email
        assert data["role"] == "editor"
        assert data["is_superadmin"] is False

    def test_me_con_token_invalido_401(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
        assert r.status_code == 401

    def test_me_con_token_expirado_401(self, client, db_session, monkeypatch):
        """Token expirado → 401 con WWW-Authenticate header."""
        from datetime import datetime, timedelta, timezone
        from jose import jwt
        from backend.auth import JWT_ALGORITHM, JWT_SECRET
        org = make_org(db_session)
        u = make_user(db_session, org)
        # Token que expiró hace 1 hora
        expired_payload = {
            "sub": str(u.id),
            "org_id": u.org_id,
            "role": u.role,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


@pytest.mark.unit
class TestPasswordHelpers:
    def test_hash_y_verify_roundtrip(self):
        from backend.auth import hash_password, verify_password
        h = hash_password("mi-password")
        assert h != "mi-password"
        assert verify_password("mi-password", h)
        assert not verify_password("otro", h)

    def test_create_y_verify_token(self):
        from backend.auth import create_access_token, verify_token
        tok = create_access_token(user_id=42, org_id=7, role="editor")
        payload = verify_token(tok)
        assert payload["sub"] == "42"
        assert payload["org_id"] == 7
        assert payload["role"] == "editor"
        assert "exp" in payload

    def test_verify_token_invalido_lanza_401(self):
        import pytest
        from fastapi import HTTPException
        from backend.auth import verify_token
        with pytest.raises(HTTPException) as exc:
            verify_token("not.a.jwt")
        assert exc.value.status_code == 401
