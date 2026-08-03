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


# ═════════════════════════════════════════════════════════════════════════
# Parte 3 — Matriz de roles sobre los routers de dominio
#
# Cierre del P0 de autorización: antes, un `viewer` podía crear y borrar
# cualquier cosa. Ahora cada endpoint de escritura lleva `require_editor`
# o `require_admin`.
#
# Diseño: el gate de rol es una *sub-dependencia* de FastAPI, así que se
# resuelve ANTES de validar el body y ANTES de que el handler consulte la
# DB. Por eso la matriz puede usar IDs inexistentes y bodies vacíos: un rol
# insuficiente recibe 403 sin necesidad de sembrar datos, y un rol
# suficiente cae en 404/422/200 — nunca 403. Los tests son baratos y no
# dependen de fixtures de dominio.
# ═════════════════════════════════════════════════════════════════════════

#: ID que no existe en ninguna tabla. Si el gate está bien puesto, el rol
#: insuficiente ni siquiera llega a la query que devolvería 404.
NO_EXISTE = 99999

#: `{org_id}` se sustituye por la org del usuario bajo test (los endpoints
#: de organizations rechazan con 403 una org ajena, lo que enmascararía el
#: gate de rol).
_PH = "{org_id}"


# (método, path, kwargs para client.request)
ENDPOINTS_EDITOR = [
    # charts
    ("POST", "/api/charts/", {"json": {}}),
    ("PUT", f"/api/charts/{NO_EXISTE}", {"json": {}}),
    ("DELETE", f"/api/charts/{NO_EXISTE}", {}),
    ("POST", f"/api/charts/{NO_EXISTE}/duplicate", {}),
    # tables
    ("POST", "/api/tables/", {"json": {}}),
    ("PUT", f"/api/tables/{NO_EXISTE}", {"json": {}}),
    ("DELETE", f"/api/tables/{NO_EXISTE}", {}),
    ("POST", f"/api/tables/{NO_EXISTE}/duplicate", {}),
    # mappings
    ("POST", "/api/mappings/", {"json": {}}),
    ("PUT", f"/api/mappings/{NO_EXISTE}", {"json": {}}),
    ("DELETE", f"/api/mappings/{NO_EXISTE}", {}),
    ("POST", f"/api/mappings/{NO_EXISTE}/duplicate", {}),
    # specs
    ("POST", "/api/specs/config", {"json": {}}),
    ("POST", f"/api/specs/{NO_EXISTE}/config", {"json": {}}),
    ("POST", f"/api/specs/{NO_EXISTE}/duplicate", {}),
    ("DELETE", f"/api/specs/{NO_EXISTE}", {}),
    # dimensions
    ("POST", "/api/dimensions/", {"json": {}}),
    ("PUT", f"/api/dimensions/{NO_EXISTE}", {"json": {}}),
    ("POST", f"/api/dimensions/{NO_EXISTE}/values", {"json": {}}),
    ("DELETE", f"/api/dimensions/values/{NO_EXISTE}", {}),
    # metrics
    ("POST", "/api/metrics/", {"json": {}}),
    ("PUT", f"/api/metrics/{NO_EXISTE}", {"json": {}}),
    ("POST", f"/api/metrics/{NO_EXISTE}/data", {"json": {}}),
    ("DELETE", f"/api/metrics/data/{NO_EXISTE}", {}),
    ("PUT", f"/api/metrics/data/{NO_EXISTE}", {"json": {}}),
    ("POST", f"/api/metrics/{NO_EXISTE}/import", {}),
    # indicators
    ("POST", "/api/indicators/", {"json": {}}),
    ("PUT", f"/api/indicators/{NO_EXISTE}", {"json": {}}),
    ("POST", f"/api/indicators/{NO_EXISTE}/layout", {"json": {}}),
    # pipelines
    ("POST", f"/api/pipelines/{NO_EXISTE}/upload", {}),
    ("POST", f"/api/pipelines/{NO_EXISTE}/run", {}),
    ("POST", f"/api/pipelines/{NO_EXISTE}/input", {"json": {}}),
    ("POST", f"/api/pipelines/{NO_EXISTE}/step", {}),
    ("POST", f"/api/pipelines/{NO_EXISTE}/reset", {}),
    ("POST", "/api/pipelines/config", {"json": {}}),
    ("POST", f"/api/pipelines/{NO_EXISTE}/config", {"json": {}}),
    ("PATCH", f"/api/pipelines/{NO_EXISTE}/hidden", {"json": {}}),
]

ENDPOINTS_ADMIN = [
    ("DELETE", f"/api/metrics/{NO_EXISTE}", {}),
    ("POST", f"/api/metrics/{NO_EXISTE}/clear", {}),
    ("POST", "/api/metrics/data/batch-delete", {"json": {"ids": []}}),
    ("DELETE", f"/api/dimensions/{NO_EXISTE}", {}),
    ("DELETE", f"/api/indicators/{NO_EXISTE}", {}),
    ("DELETE", f"/api/pipelines/{NO_EXISTE}", {}),
    ("POST", "/api/data-ops/replace", {"json": {}}),
    ("POST", "/api/data-ops/recalculate", {"json": {}}),
    ("POST", f"/api/organizations/{_PH}/assets", {}),
    ("DELETE", f"/api/organizations/{_PH}/assets/{NO_EXISTE}", {}),
]

#: Endpoints de LECTURA que son POST solo porque llevan filtros en el body.
#: Un viewer NO debe quedar bloqueado: el P0 no debía tocar el solo-lectura.
ENDPOINTS_LECTURA = [
    ("POST", "/api/charts/preview", {"json": {}}),
    ("POST", "/api/tables/preview", {"json": {}}),
    ("POST", "/api/mappings/preview", {"json": {}}),
    ("POST", "/api/data-ops/distinct", {"json": {}}),
]


def _ids(casos):
    """IDs legibles para pytest: `POST /api/charts/`."""
    return [f"{m} {p}" for m, p, _ in casos]


@pytest.mark.integration
class TestMatrizRoles:
    """Un caso por (endpoint, rol). Ver el comentario de cabecera de Parte 3."""

    @staticmethod
    def _llamar(client, db_session, role, method, path, kwargs):
        org = make_org(db_session)
        u = make_user(db_session, org, role=role)
        return client.request(
            method,
            path.replace(_PH, str(u.org_id)),
            headers=auth_header_for(u),
            **kwargs,
        )

    # ── Nivel EDITOR ────────────────────────────────────────────────────
    @pytest.mark.parametrize("method,path,kwargs", ENDPOINTS_EDITOR,
                             ids=_ids(ENDPOINTS_EDITOR))
    def test_viewer_403_en_endpoint_de_editor(
        self, client, db_session, method, path, kwargs
    ):
        res = self._llamar(client, db_session, "viewer", method, path, kwargs)
        assert res.status_code == 403, (
            f"{method} {path} sin gate para viewer: devolvió {res.status_code}"
        )

    @pytest.mark.parametrize("method,path,kwargs", ENDPOINTS_EDITOR,
                             ids=_ids(ENDPOINTS_EDITOR))
    def test_editor_no_recibe_403_en_endpoint_de_editor(
        self, client, db_session, method, path, kwargs
    ):
        res = self._llamar(client, db_session, "editor", method, path, kwargs)
        assert res.status_code != 403, f"{method} {path} bloqueó a un editor"

    @pytest.mark.parametrize("method,path,kwargs", ENDPOINTS_EDITOR,
                             ids=_ids(ENDPOINTS_EDITOR))
    def test_admin_no_recibe_403_en_endpoint_de_editor(
        self, client, db_session, method, path, kwargs
    ):
        res = self._llamar(client, db_session, "admin", method, path, kwargs)
        assert res.status_code != 403, f"{method} {path} bloqueó a un admin"

    # ── Nivel ADMIN ─────────────────────────────────────────────────────
    @pytest.mark.parametrize("method,path,kwargs", ENDPOINTS_ADMIN,
                             ids=_ids(ENDPOINTS_ADMIN))
    def test_viewer_403_en_endpoint_de_admin(
        self, client, db_session, method, path, kwargs
    ):
        res = self._llamar(client, db_session, "viewer", method, path, kwargs)
        assert res.status_code == 403, (
            f"{method} {path} sin gate para viewer: devolvió {res.status_code}"
        )

    @pytest.mark.parametrize("method,path,kwargs", ENDPOINTS_ADMIN,
                             ids=_ids(ENDPOINTS_ADMIN))
    def test_editor_403_en_endpoint_de_admin(
        self, client, db_session, method, path, kwargs
    ):
        res = self._llamar(client, db_session, "editor", method, path, kwargs)
        assert res.status_code == 403, (
            f"{method} {path} sin gate admin: un editor recibió {res.status_code}"
        )

    @pytest.mark.parametrize("method,path,kwargs", ENDPOINTS_ADMIN,
                             ids=_ids(ENDPOINTS_ADMIN))
    def test_admin_no_recibe_403_en_endpoint_de_admin(
        self, client, db_session, method, path, kwargs
    ):
        res = self._llamar(client, db_session, "admin", method, path, kwargs)
        assert res.status_code != 403, f"{method} {path} bloqueó a un admin"

    # ── Nivel LECTURA ───────────────────────────────────────────────────
    @pytest.mark.parametrize("method,path,kwargs", ENDPOINTS_LECTURA,
                             ids=_ids(ENDPOINTS_LECTURA))
    def test_viewer_no_recibe_403_en_endpoint_de_lectura(
        self, client, db_session, method, path, kwargs
    ):
        res = self._llamar(client, db_session, "viewer", method, path, kwargs)
        assert res.status_code != 403, (
            f"{method} {path} es de solo lectura pero bloqueó a un viewer"
        )
