"""Tests de la PARTE A del workstream W1 — núcleo de seguridad de API keys.

Cubre tres capas:
  - Crypto (`backend/api_keys.py`): generación, verificación, scopes.
  - Gestión (`backend/routers/api_keys.py`): crear/listar/revocar, admin-only,
    aislamiento cross-org.
  - Auth (`backend/auth.py`): dependency `get_org_from_api_key` + factory
    `require_scope` — 401 sin/mala/revocada/expirada key, 403 scope faltante,
    200 con key válida y scope correcto.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from backend.api_keys import (
    deserializar_scopes,
    extraer_prefix,
    generar_api_key,
    serializar_scopes,
    verificar_api_key,
)
from tests.factories import auth_header_for, make_org, make_user


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture
def admin(db_session, org):
    return make_user(db_session, org, role="admin", email="admin@example.com")


@pytest.fixture
def admin_headers(admin):
    return auth_header_for(admin)


def _crear_api_key_row(db, org, *, scopes=None, revoked=False, expires_at=None, name="Key"):
    """Inserta una ApiKey directamente y devuelve (fila, secreto_claro)."""
    from backend.models import ApiKey

    secreto, prefix, key_hash = generar_api_key()
    row = ApiKey(
        org_id=org.id,
        name=name,
        prefix=prefix,
        key_hash=key_hash,
        scopes=serializar_scopes(scopes or []),
        revoked=revoked,
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, secreto


# ─────────────────────────────────────────────────────────────────────────
# Crypto
# ─────────────────────────────────────────────────────────────────────────

class TestCrypto:
    def test_key_verifica_contra_su_hash(self):
        secreto, prefix, key_hash = generar_api_key()
        assert verificar_api_key(secreto, key_hash) is True

    def test_key_alterada_no_verifica(self):
        secreto, prefix, key_hash = generar_api_key()
        assert verificar_api_key(secreto + "x", key_hash) is False
        assert verificar_api_key("rg_live_zzzznope", key_hash) is False

    def test_formato_y_prefix(self):
        secreto, prefix, key_hash = generar_api_key()
        assert secreto.startswith("rg_live_")
        assert prefix.startswith("rg_live_")
        assert len(prefix) <= 12
        # el prefix es el comienzo del secreto y extraer_prefix lo recupera
        assert secreto.startswith(prefix)
        assert extraer_prefix(secreto) == prefix

    def test_entropia_suficiente(self):
        # Dos keys consecutivas nunca deben coincidir; la cola aleatoria es larga.
        s1, _, _ = generar_api_key()
        s2, _, _ = generar_api_key()
        assert s1 != s2
        assert len(s1) > 40

    def test_hash_no_es_el_secreto(self):
        secreto, prefix, key_hash = generar_api_key()
        assert secreto not in key_hash
        assert key_hash.startswith("$2")  # bcrypt

    def test_verificar_tolera_hash_corrupto(self):
        assert verificar_api_key("rg_live_abcd123", "no-es-un-hash") is False

    def test_scopes_roundtrip(self):
        scopes = ["ingest:write", "metrics:read"]
        assert deserializar_scopes(serializar_scopes(scopes)) == scopes
        assert deserializar_scopes("") == []
        assert deserializar_scopes("corrupto{") == []
        assert deserializar_scopes(None) == []


# ─────────────────────────────────────────────────────────────────────────
# Gestión (router JWT admin-only)
# ─────────────────────────────────────────────────────────────────────────

class TestGestion:
    def test_crear_devuelve_secreto_una_vez(self, client, admin_headers):
        resp = client.post(
            "/api/api-keys/",
            json={"name": "Integración Forms", "scopes": ["ingest:write"]},
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["secret"].startswith("rg_live_")
        assert body["prefix"].startswith("rg_live_")
        assert body["scopes"] == ["ingest:write"]
        assert body["revoked"] is False

    def test_listar_no_expone_secreto(self, client, admin_headers):
        create = client.post(
            "/api/api-keys/",
            json={"name": "K1", "scopes": ["metrics:read"]},
            headers=admin_headers,
        )
        secreto = create.json()["secret"]

        resp = client.get("/api/api-keys/", headers=admin_headers)
        assert resp.status_code == 200
        listado = resp.json()
        assert len(listado) == 1
        item = listado[0]
        assert "secret" not in item
        assert secreto not in resp.text
        assert item["prefix"].startswith("rg_live_")

    def test_scope_invalido_rechazado(self, client, admin_headers):
        resp = client.post(
            "/api/api-keys/",
            json={"name": "K", "scopes": ["superpoder:todo"]},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_revocar(self, client, admin_headers, db_session, org):
        create = client.post(
            "/api/api-keys/", json={"name": "K", "scopes": []}, headers=admin_headers
        )
        key_id = create.json()["id"]

        resp = client.delete(f"/api/api-keys/{key_id}", headers=admin_headers)
        assert resp.status_code == 200

        from backend.models import ApiKey
        row = db_session.query(ApiKey).filter(ApiKey.id == key_id).first()
        assert row.revoked is True

    def test_editor_no_puede_gestionar(self, client, auth_headers):
        # `auth_headers` es del user editor por defecto de conftest.
        assert client.post(
            "/api/api-keys/", json={"name": "X", "scopes": []}, headers=auth_headers
        ).status_code == 403
        assert client.get("/api/api-keys/", headers=auth_headers).status_code == 403

    def test_sin_jwt_401(self, client):
        assert client.get("/api/api-keys/").status_code == 401

    def test_aislamiento_cross_org(self, client, db_session, admin_headers, org):
        # Key de la org del admin.
        client.post(
            "/api/api-keys/", json={"name": "propia", "scopes": []}, headers=admin_headers
        )
        # Otra org con su propia key + admin.
        org_b = make_org(db_session)
        admin_b = make_user(db_session, org_b, role="admin", email="admin_b@example.com")
        _crear_api_key_row(db_session, org_b, name="ajena")

        # El admin de la org original solo ve la suya.
        propio = client.get("/api/api-keys/", headers=admin_headers).json()
        assert [k["name"] for k in propio] == ["propia"]

        # El admin de B solo ve la de B.
        ajeno = client.get("/api/api-keys/", headers=auth_header_for(admin_b)).json()
        assert [k["name"] for k in ajeno] == ["ajena"]

    def test_revocar_key_de_otra_org_404(self, client, db_session, admin_headers, org):
        org_b = make_org(db_session)
        row, _ = _crear_api_key_row(db_session, org_b, name="ajena")
        resp = client.delete(f"/api/api-keys/{row.id}", headers=admin_headers)
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────
# Auth: dependency get_org_from_api_key + require_scope
#
# Montamos una mini-app aislada con un endpoint protegido por
# require_scope("ingest:write") para no depender de los endpoints de ingesta
# (PARTE B, aún no implementados).
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture
def api_key_client(db_session):
    """TestClient sobre una app mínima que ejerce la dependency de scope."""
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from backend.auth import ApiKeyContext, get_org_from_api_key, require_scope
    from backend.database import get_db

    app = FastAPI()

    @app.get("/protegido")
    def protegido(ctx: ApiKeyContext = Depends(require_scope("ingest:write"))):
        return {"org_id": ctx.org_id, "api_key_id": ctx.api_key_id, "scopes": ctx.scopes}

    @app.get("/solo-auth")
    def solo_auth(ctx: ApiKeyContext = Depends(get_org_from_api_key)):
        return {"org_id": ctx.org_id}

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


class TestAuthDependency:
    def test_sin_key_401(self, api_key_client):
        assert api_key_client.get("/solo-auth").status_code == 401

    def test_key_invalida_401(self, api_key_client):
        resp = api_key_client.get("/solo-auth", headers={"X-API-Key": "rg_live_xxxxnope"})
        assert resp.status_code == 401

    def test_key_valida_pasa(self, api_key_client, db_session, org):
        _, secreto = _crear_api_key_row(db_session, org, scopes=["ingest:write"])
        resp = api_key_client.get("/solo-auth", headers={"X-API-Key": secreto})
        assert resp.status_code == 200
        assert resp.json()["org_id"] == org.id

    def test_key_revocada_401(self, api_key_client, db_session, org):
        _, secreto = _crear_api_key_row(db_session, org, scopes=["ingest:write"], revoked=True)
        resp = api_key_client.get("/solo-auth", headers={"X-API-Key": secreto})
        assert resp.status_code == 401

    def test_key_expirada_401(self, api_key_client, db_session, org):
        _, secreto = _crear_api_key_row(
            db_session, org, scopes=["ingest:write"],
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        resp = api_key_client.get("/solo-auth", headers={"X-API-Key": secreto})
        assert resp.status_code == 401

    def test_scope_faltante_403(self, api_key_client, db_session, org):
        _, secreto = _crear_api_key_row(db_session, org, scopes=["metrics:read"])
        resp = api_key_client.get("/protegido", headers={"X-API-Key": secreto})
        assert resp.status_code == 403

    def test_scope_presente_200(self, api_key_client, db_session, org):
        row, secreto = _crear_api_key_row(db_session, org, scopes=["ingest:write"])
        resp = api_key_client.get("/protegido", headers={"X-API-Key": secreto})
        assert resp.status_code == 200
        body = resp.json()
        assert body["org_id"] == org.id
        assert body["api_key_id"] == row.id
        assert "ingest:write" in body["scopes"]

    def test_context_org_sale_de_la_key(self, api_key_client, db_session, org):
        # El org_id del contexto es el de la key, garantía de tenancy dura.
        org_b = make_org(db_session)
        row_b, secreto_b = _crear_api_key_row(db_session, org_b, scopes=["ingest:write"])
        resp = api_key_client.get("/protegido", headers={"X-API-Key": secreto_b})
        assert resp.status_code == 200
        assert resp.json()["org_id"] == org_b.id

    def test_last_used_at_se_actualiza(self, api_key_client, db_session, org):
        from backend.models import ApiKey

        row, secreto = _crear_api_key_row(db_session, org, scopes=["ingest:write"])
        assert row.last_used_at is None
        api_key_client.get("/solo-auth", headers={"X-API-Key": secreto})
        db_session.refresh(row)
        assert row.last_used_at is not None
