"""Tests del router /api/pipelines — Sprint 5 (cobertura 19% → ~50%).

Cubre los endpoints CRUD básicos:

    GET    /api/pipelines/                     list (por org)
    GET    /api/pipelines/{id}/config           leer config completa
    POST   /api/pipelines/config                crear pipeline
    POST   /api/pipelines/{id}/config           guardar pipeline existente
    PATCH  /api/pipelines/{id}/hidden           toggle hidden flag
    DELETE /api/pipelines/{id}

Saltea los endpoints de ejecución (run, step, input, reset, artifact,
upload) — requieren un PipelineRunner activo en memoria + uploads
filesystem, lo que merece un sprint dedicado.

Detalle de contrato peculiar de este router: muchos endpoints devuelven
`{"error": "..."}` con status 200 en lugar de levantar HTTPException(404).
Los tests documentan ese comportamiento actual (sin "corregirlo" — un
refactor posterior podría unificar a HTTPException, pero no es la
responsabilidad del Sprint 5).
"""
from __future__ import annotations

import json

import pytest

from tests.factories import make_org


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────


def _make_pipeline(db_session, org, *, name="Mi Pipeline", config=None, hidden=False):
    from backend.models import Pipeline
    cfg_text = json.dumps(config) if config else "{}"
    p = Pipeline(
        pipeline=name,
        description=f"desc de {name}",
        config_json=cfg_text,
        hidden=hidden,
        org_id=org.id,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def pipeline_simple(db_session, org):
    return _make_pipeline(db_session, org, name="Pipeline Simple")


@pytest.fixture
def pipeline_con_config(db_session, org):
    cfg = {
        "pipeline_metadata": {
            "name": "Pipeline Con Config",
            "description": "test full config",
            "input": "EXCEL",
            "output": "XLSX",
        },
        "context": {"base_dir": "/tmp/run"},
        "pipeline": [
            {"step": "DiscoverInputs", "params": {"roles": ["estudiantes"]}},
            {"step": "RunExcelETL", "params": {}},
        ],
    }
    return _make_pipeline(db_session, org, name="Pipeline Con Config", config=cfg)


@pytest.fixture
def pipeline_de_otra_org(db_session):
    other = make_org(db_session, name="Otra Org Pipe")
    p = _make_pipeline(db_session, other, name="Ajeno")
    return other, p


# ─────────────────────────────────────────────────────────────────────────
# GET /api/pipelines/
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestListPipelines:
    def test_sin_auth_401(self, client):
        assert client.get("/api/pipelines/").status_code == 401

    def test_lista_vacia(self, client_auth):
        r = client_auth.get("/api/pipelines/")
        assert r.status_code == 200
        assert r.json() == []

    def test_lista_devuelve_pipelines_de_mi_org(self, client_auth, pipeline_simple):
        r = client_auth.get("/api/pipelines/")
        assert r.status_code == 200
        names = [p["pipeline"] for p in r.json()]
        assert "Pipeline Simple" in names

    def test_lista_no_devuelve_pipelines_otra_org(self, client_auth, pipeline_simple, pipeline_de_otra_org):
        r = client_auth.get("/api/pipelines/")
        names = [p["pipeline"] for p in r.json()]
        assert "Ajeno" not in names
        assert "Pipeline Simple" in names

    def test_lista_estructura_items(self, client_auth, pipeline_simple):
        items = client_auth.get("/api/pipelines/").json()
        item = items[0]
        for key in ("pipeline_id", "pipeline", "description", "config_json", "hidden", "last_run"):
            assert key in item


# ─────────────────────────────────────────────────────────────────────────
# GET /api/pipelines/{id}/config
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetPipelineConfig:
    def test_sin_auth_401(self, client, pipeline_simple):
        assert client.get(f"/api/pipelines/{pipeline_simple.pipeline_id}/config").status_code == 401

    def test_config_inexistente_devuelve_skeleton_vacio(self, client_auth):
        """Comportamiento peculiar: si el pipeline NO existe, devuelve un
        skeleton vacío (NO 404). Documenta contrato actual."""
        r = client_auth.get("/api/pipelines/99999/config")
        assert r.status_code == 200
        body = r.json()
        assert "pipeline_metadata" in body
        assert body["pipeline_metadata"]["pipeline_id"] == 99999
        assert body["pipeline_metadata"]["name"] == ""
        assert body["pipeline"] == []

    def test_config_otra_org_devuelve_skeleton(self, client_auth, pipeline_de_otra_org):
        _, p = pipeline_de_otra_org
        r = client_auth.get(f"/api/pipelines/{p.pipeline_id}/config")
        assert r.status_code == 200
        # No expone el name del pipeline ajeno
        assert r.json()["pipeline_metadata"]["name"] == ""

    def test_config_existente_sin_json(self, client_auth, pipeline_simple):
        r = client_auth.get(f"/api/pipelines/{pipeline_simple.pipeline_id}/config")
        assert r.status_code == 200
        body = r.json()
        assert body["pipeline_metadata"]["name"] == "Pipeline Simple"
        assert body["pipeline_metadata"]["description"] == "desc de Pipeline Simple"
        # config_json era "{}", entonces pipeline queda vacía
        assert body["pipeline"] == []

    def test_config_existente_con_json(self, client_auth, pipeline_con_config):
        r = client_auth.get(f"/api/pipelines/{pipeline_con_config.pipeline_id}/config")
        assert r.status_code == 200
        body = r.json()
        assert body["pipeline_metadata"]["name"] == "Pipeline Con Config"
        assert body["context"]["base_dir"] == "/tmp/run"
        assert len(body["pipeline"]) == 2
        assert body["pipeline"][0]["step"] == "DiscoverInputs"


# ─────────────────────────────────────────────────────────────────────────
# POST /api/pipelines/config  +  POST /api/pipelines/{id}/config
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestCreatePipelineConfig:
    def _payload(self, name="Nuevo Pipe"):
        return {
            "pipeline_metadata": {
                "name": name, "description": "creado en test",
                "input": "EXCEL", "output": "XLSX",
            },
            "context": {"base_dir": "."},
            "pipeline": [{"step": "DiscoverInputs", "params": {}}],
        }

    def test_sin_auth_401(self, client):
        r = client.post("/api/pipelines/config", json=self._payload())
        assert r.status_code == 401

    def test_crear_pipeline_basico(self, client_auth, db_session, org):
        from backend.models import Pipeline
        r = client_auth.post("/api/pipelines/config", json=self._payload("Nuevo"))
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        new_id = body["new_id"]
        # Verifica que existe en BD con la org del user
        p = db_session.get(Pipeline, new_id)
        assert p is not None
        assert p.pipeline == "Nuevo"
        assert p.org_id == org.id

    def test_crear_nombre_duplicado_devuelve_error(self, client_auth, pipeline_simple):
        """Si ya existe un pipeline con ese name en la org → error en el body."""
        r = client_auth.post("/api/pipelines/config",
                             json=self._payload("Pipeline Simple"))
        assert r.status_code == 200
        body = r.json()
        assert "error" in body
        assert "Ya existe" in body["error"]

    def test_crear_nombre_duplicado_en_otra_org_si_permite(self, client_auth, pipeline_de_otra_org):
        """El check de duplicado es POR ORG: el name "Ajeno" existe en otra
        org, pero acá creamos uno con ese mismo name en MI org y funciona."""
        r = client_auth.post("/api/pipelines/config", json=self._payload("Ajeno"))
        assert r.status_code == 200
        assert r.json().get("status") == "success"


@pytest.mark.integration
class TestSavePipelineConfig:
    def _payload(self, name):
        return {
            "pipeline_metadata": {"name": name, "description": "actualizado"},
            "context": {"base_dir": "."},
            "pipeline": [],
        }

    def test_save_existente_actualiza_name_y_desc(self, client_auth, pipeline_simple, db_session):
        from backend.models import Pipeline
        r = client_auth.post(f"/api/pipelines/{pipeline_simple.pipeline_id}/config",
                             json=self._payload("Renombrado"))
        assert r.status_code == 200
        assert r.json()["status"] == "success"
        db_session.expire_all()
        p = db_session.get(Pipeline, pipeline_simple.pipeline_id)
        assert p.pipeline == "Renombrado"
        assert p.description == "actualizado"

    def test_save_id_inexistente_cae_a_create(self, client_auth, db_session, org):
        """Si el pipeline_id no existe (ni en mi org ni en otra), el endpoint
        crea uno nuevo en lugar de error."""
        from backend.models import Pipeline
        r = client_auth.post("/api/pipelines/99999/config",
                             json=self._payload("Llegó como nuevo"))
        assert r.status_code == 200
        new_id = r.json()["new_id"]
        p = db_session.get(Pipeline, new_id)
        assert p.org_id == org.id

    def test_save_pipeline_otra_org_cae_a_create_en_mi_org(self, client_auth, pipeline_de_otra_org, db_session):
        """Multi-tenancy: si paso el id de un pipeline AJENO, el endpoint
        no lo modifica — crea uno nuevo en mi org. Hay protección
        cross-org incluso si el comportamiento es algo confuso."""
        from backend.models import Pipeline
        _, p_ajeno = pipeline_de_otra_org
        nombre_original_ajeno = p_ajeno.pipeline
        r = client_auth.post(f"/api/pipelines/{p_ajeno.pipeline_id}/config",
                             json=self._payload("Mio Nuevo"))
        assert r.status_code == 200
        # El pipeline ajeno NO fue tocado
        db_session.expire_all()
        p_ajeno_after = db_session.get(Pipeline, p_ajeno.pipeline_id)
        assert p_ajeno_after.pipeline == nombre_original_ajeno


# ─────────────────────────────────────────────────────────────────────────
# PATCH /api/pipelines/{id}/hidden
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestToggleHidden:
    def test_sin_auth_401(self, client, pipeline_simple):
        r = client.patch(f"/api/pipelines/{pipeline_simple.pipeline_id}/hidden",
                         json={"hidden": True})
        assert r.status_code == 401

    def test_inexistente_devuelve_error(self, client_auth):
        r = client_auth.patch("/api/pipelines/99999/hidden", json={"hidden": True})
        assert r.status_code == 200
        assert "error" in r.json()

    def test_otra_org_devuelve_error(self, client_auth, pipeline_de_otra_org):
        _, p = pipeline_de_otra_org
        r = client_auth.patch(f"/api/pipelines/{p.pipeline_id}/hidden",
                              json={"hidden": True})
        assert r.status_code == 200
        assert "error" in r.json()

    def test_toggle_true(self, client_auth, pipeline_simple, db_session):
        from backend.models import Pipeline
        r = client_auth.patch(f"/api/pipelines/{pipeline_simple.pipeline_id}/hidden",
                              json={"hidden": True})
        assert r.status_code == 200
        assert r.json()["hidden"] is True
        db_session.expire_all()
        p = db_session.get(Pipeline, pipeline_simple.pipeline_id)
        assert p.hidden is True

    def test_toggle_false(self, client_auth, db_session, org):
        # Empezamos con hidden=True y bajamos a False
        p = _make_pipeline(db_session, org, name="Hidden", hidden=True)
        r = client_auth.patch(f"/api/pipelines/{p.pipeline_id}/hidden",
                              json={"hidden": False})
        assert r.status_code == 200
        assert r.json()["hidden"] is False


# ─────────────────────────────────────────────────────────────────────────
# DELETE /api/pipelines/{id}
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestDeletePipeline:
    def test_sin_auth_401(self, client, pipeline_simple):
        assert client.delete(f"/api/pipelines/{pipeline_simple.pipeline_id}").status_code == 401

    def test_inexistente_devuelve_error(self, client_auth):
        r = client_auth.delete("/api/pipelines/99999")
        assert r.status_code == 200
        assert "error" in r.json()

    def test_otra_org_devuelve_error(self, client_auth, pipeline_de_otra_org):
        _, p = pipeline_de_otra_org
        r = client_auth.delete(f"/api/pipelines/{p.pipeline_id}")
        assert r.status_code == 200
        assert "error" in r.json()

    def test_delete_success(self, client_auth, pipeline_simple, db_session):
        from backend.models import Pipeline
        pid = pipeline_simple.pipeline_id
        r = client_auth.delete(f"/api/pipelines/{pid}")
        assert r.status_code == 200
        # No tiene "error" key
        assert "error" not in r.json()
        db_session.expire_all()
        assert db_session.get(Pipeline, pid) is None
