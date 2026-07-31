"""Tests de la PARTE B del workstream W1 — endpoints de ingesta por API
externa (`backend/routers/ingest.py`).

Cubre:
  - Auth de ingesta (401/403/200) reusando la dependency de la PARTE A.
  - Tenancy dura: una key de Org A no puede tocar métricas/pipelines de Org B.
  - Validación de records (tipos, dimensiones desconocidas, dry_run).
  - Idempotencia vía header `Idempotency-Key`.
  - Auditoría: filas insertadas quedan con `created_via="api_direct"`.
  - Schema endpoint.
  - Trigger de pipelines: happy path, cross-org 404, needs_review.
"""
from __future__ import annotations

import json

import pytest

from backend.api_keys import generar_api_key, serializar_scopes
from tests.factories import make_dimension, make_metric, make_metric_data, make_org


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

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


def _headers(secreto: str, idempotency_key: str | None = None) -> dict:
    h = {"X-API-Key": secreto}
    if idempotency_key:
        h["Idempotency-Key"] = idempotency_key
    return h


@pytest.fixture
def write_key(db_session, org):
    """API key de `org` con scope ingest:write."""
    _, secreto = _crear_api_key_row(db_session, org, scopes=["ingest:write"], name="write")
    return secreto


@pytest.fixture
def read_key(db_session, org):
    """API key de `org` con scope metrics:read (sin ingest:write)."""
    _, secreto = _crear_api_key_row(db_session, org, scopes=["metrics:read"], name="read")
    return secreto


@pytest.fixture
def simple_metric(db_session, org):
    """Métrica simple (data_type=float) con una dimensión 'Curso'."""
    dim = make_dimension(db_session, org, name="Curso", data_type="str")
    return make_metric(db_session, org, name="Asistencia", data_type="float", dimensions=[dim])


@pytest.fixture
def object_metric(db_session, org):
    """Métrica compuesta (data_type=object) con dos fields tipados."""
    dim = make_dimension(db_session, org, name="Curso", data_type="str")
    return make_metric(
        db_session,
        org,
        name="Resultados",
        data_type="object",
        fields=[{"name": "puntaje", "type": "int"}, {"name": "aprobado", "type": "bool"}],
        dimensions=[dim],
    )


# ─────────────────────────────────────────────────────────────────────────
# Auth de ingesta
# ─────────────────────────────────────────────────────────────────────────

class TestAuthIngesta:
    def test_sin_key_401(self, client, simple_metric):
        resp = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json={"records": []},
        )
        assert resp.status_code == 401

    def test_key_revocada_401(self, client, db_session, org, simple_metric):
        _, secreto = _crear_api_key_row(db_session, org, scopes=["ingest:write"], revoked=True)
        resp = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json={"records": []},
            headers=_headers(secreto),
        )
        assert resp.status_code == 401

    def test_key_expirada_401(self, client, db_session, org, simple_metric):
        from datetime import datetime, timedelta

        _, secreto = _crear_api_key_row(
            db_session, org, scopes=["ingest:write"],
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        resp = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json={"records": []},
            headers=_headers(secreto),
        )
        assert resp.status_code == 401

    def test_scope_faltante_403(self, client, read_key, simple_metric):
        resp = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json={"records": []},
            headers=_headers(read_key),
        )
        assert resp.status_code == 403

    def test_key_con_ingest_write_200(self, client, write_key, simple_metric):
        resp = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json={"records": [{"value": 1.5, "dimensions": {}}]},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text


# ─────────────────────────────────────────────────────────────────────────
# Tenancy dura
# ─────────────────────────────────────────────────────────────────────────

class TestTenancy:
    def test_org_a_no_carga_en_metrica_de_org_b(self, client, db_session, org):
        org_b = make_org(db_session)
        metric_b = make_metric(db_session, org_b, name="Ajena", data_type="float")
        _, secreto_a = _crear_api_key_row(db_session, org, scopes=["ingest:write"], name="a")

        resp = client.post(
            f"/api/ingest/metrics/{metric_b.id_metric}/data",
            json={"records": [{"value": 1.0, "dimensions": {}}]},
            headers=_headers(secreto_a),
        )
        assert resp.status_code == 404

    def test_org_a_no_ve_schema_de_org_b(self, client, db_session, org):
        org_b = make_org(db_session)
        metric_b = make_metric(db_session, org_b, name="Ajena", data_type="float")
        _, secreto_a = _crear_api_key_row(db_session, org, scopes=["metrics:read"], name="a")

        resp = client.get(
            f"/api/ingest/metrics/{metric_b.id_metric}/schema",
            headers=_headers(secreto_a),
        )
        assert resp.status_code == 404

    def test_org_id_sale_de_la_key_no_del_body(self, client, db_session, org, simple_metric, write_key):
        # No hay org_id en el body/URL más que metric_id — igual funciona
        # porque el org_id sale de la key. Verificamos que la fila insertada
        # quedó con el org_id de la key, no con ningún otro valor.
        resp = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json={"records": [{"value": 2.0, "dimensions": {}}]},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text

        from backend.models import MetricData
        rows = db_session.query(MetricData).filter(MetricData.id_metric == simple_metric.id_metric).all()
        assert len(rows) == 1
        assert rows[0].org_id == org.id


# ─────────────────────────────────────────────────────────────────────────
# Validación
# ─────────────────────────────────────────────────────────────────────────

class TestValidacion:
    def test_record_valido_se_inserta(self, client, db_session, write_key, simple_metric):
        resp = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json={"records": [{"value": 3.5, "dimensions": {"Curso": "4A"}}]},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["rows_ok"] == 1
        assert body["rows_failed"] == 0
        assert body["errors"] == []

        from backend.models import MetricData
        rows = db_session.query(MetricData).filter(MetricData.id_metric == simple_metric.id_metric).all()
        assert len(rows) == 1
        assert rows[0].value == "3.5"

    def test_tipo_invalido_va_a_rows_failed(self, client, write_key, simple_metric):
        resp = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json={"records": [{"value": "no-es-un-numero", "dimensions": {}}]},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["rows_ok"] == 0
        assert body["rows_failed"] == 1
        assert body["errors"][0]["index"] == 0
        assert "value" in body["errors"][0]["reason"] or "tipo" in body["errors"][0]["reason"]

    def test_dimension_desconocida_va_a_rows_failed(self, client, write_key, simple_metric):
        resp = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json={"records": [{"value": 1.0, "dimensions": {"NoExiste": "x"}}]},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["rows_ok"] == 0
        assert body["rows_failed"] == 1
        assert "dimensión desconocida" in body["errors"][0]["reason"]

    def test_batch_mixto_reporta_ambos(self, client, db_session, write_key, simple_metric):
        resp = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json={
                "records": [
                    {"value": 1.0, "dimensions": {}},
                    {"value": "invalido", "dimensions": {}},
                    {"value": 2.0, "dimensions": {}},
                ]
            },
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["rows_ok"] == 2
        assert body["rows_failed"] == 1
        assert body["errors"] == [{"index": 1, "reason": body["errors"][0]["reason"]}]

        from backend.models import MetricData
        count = db_session.query(MetricData).filter(MetricData.id_metric == simple_metric.id_metric).count()
        assert count == 2

    def test_dry_run_no_inserta(self, client, db_session, write_key, simple_metric):
        resp = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json={"records": [{"value": 9.0, "dimensions": {}}], "dry_run": True},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["dry_run"] is True
        assert body["rows_ok"] == 1

        from backend.models import MetricData
        count = db_session.query(MetricData).filter(MetricData.id_metric == simple_metric.id_metric).count()
        assert count == 0

    def test_object_metric_valida_fields(self, client, db_session, write_key, object_metric):
        resp = client.post(
            f"/api/ingest/metrics/{object_metric.id_metric}/data",
            json={
                "records": [
                    {"value": {"puntaje": 85, "aprobado": True}, "dimensions": {"Curso": "4A"}},
                    {"value": {"puntaje": "no-int", "aprobado": True}, "dimensions": {}},
                ]
            },
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["rows_ok"] == 1
        assert body["rows_failed"] == 1

        from backend.models import MetricData
        rows = db_session.query(MetricData).filter(MetricData.id_metric == object_metric.id_metric).all()
        assert len(rows) == 1
        val = json.loads(rows[0].value)
        assert val == {"puntaje": 85, "aprobado": True}


# ─────────────────────────────────────────────────────────────────────────
# Idempotencia
# ─────────────────────────────────────────────────────────────────────────

class TestIdempotencia:
    def test_misma_idempotency_key_una_sola_insercion(self, client, db_session, write_key, simple_metric):
        payload = {"records": [{"value": 5.0, "dimensions": {}}]}
        r1 = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json=payload,
            headers=_headers(write_key, idempotency_key="abc-123"),
        )
        r2 = client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json=payload,
            headers=_headers(write_key, idempotency_key="abc-123"),
        )
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text
        assert r1.json()["rows_ok"] == r2.json()["rows_ok"] == 1

        from backend.models import MetricData
        count = db_session.query(MetricData).filter(MetricData.id_metric == simple_metric.id_metric).count()
        assert count == 1

    def test_sin_idempotency_key_dos_inserciones(self, client, db_session, write_key, simple_metric):
        payload = {"records": [{"value": 5.0, "dimensions": {}}]}
        client.post(f"/api/ingest/metrics/{simple_metric.id_metric}/data", json=payload, headers=_headers(write_key))
        client.post(f"/api/ingest/metrics/{simple_metric.id_metric}/data", json=payload, headers=_headers(write_key))

        from backend.models import MetricData
        count = db_session.query(MetricData).filter(MetricData.id_metric == simple_metric.id_metric).count()
        assert count == 2

    def test_idempotency_key_queda_registrada_en_ingest_log(self, client, db_session, write_key, simple_metric):
        payload = {"records": [{"value": 5.0, "dimensions": {}}]}
        client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json=payload,
            headers=_headers(write_key, idempotency_key="xyz-999"),
        )

        from backend.models import IngestLog
        logs = db_session.query(IngestLog).filter(IngestLog.idempotency_key == "xyz-999").all()
        assert len(logs) == 1
        assert logs[0].status == "success"
        assert logs[0].rows_ok == 1


# ─────────────────────────────────────────────────────────────────────────
# Auditoría
# ─────────────────────────────────────────────────────────────────────────

class TestAuditoria:
    def test_filas_quedan_con_created_via_api_direct(self, client, db_session, write_key, simple_metric):
        client.post(
            f"/api/ingest/metrics/{simple_metric.id_metric}/data",
            json={"records": [{"value": 1.0, "dimensions": {}}]},
            headers=_headers(write_key),
        )

        from backend.models import MetricData
        row = db_session.query(MetricData).filter(MetricData.id_metric == simple_metric.id_metric).first()
        assert row.created_via == "api_direct"
        assert row.created_by_user_id is None


# ─────────────────────────────────────────────────────────────────────────
# Pares X / X_Norm
#
# La red de seguridad "toda carga deja el nombre en AMBAS columnas" vivía
# solo en el camino de pipelines (`SaveToMetric`). La ingesta por API la
# aplica con el mismo helper compartido
# (`backend/rgenerator/core/pares_nombre.py`).
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture
def metric_con_par_nombre(db_session, org):
    """Métrica float con dimensiones Curso + Nombre + Nombre_Norm."""
    dims = {
        n: make_dimension(db_session, org, name=n)
        for n in ("Curso", "Nombre", "Nombre_Norm")
    }
    metric = make_metric(
        db_session, org, name="Logro", data_type="float",
        dimensions=list(dims.values()),
    )
    return metric, dims


@pytest.fixture
def metric_sin_par_nombre(db_session, org):
    """Métrica float con dimensión Nombre pero SIN su hermana normalizada."""
    dims = {n: make_dimension(db_session, org, name=n) for n in ("Curso", "Nombre")}
    metric = make_metric(
        db_session, org, name="Logro", data_type="float",
        dimensions=list(dims.values()),
    )
    return metric, dims


def _dims_guardadas(db, metric):
    from backend.models import MetricData
    db.expire_all()
    filas = (
        db.query(MetricData)
        .filter(MetricData.id_metric == metric.id_metric)
        .order_by(MetricData.id_data)
        .all()
    )
    return [json.loads(f.dimensions_json) for f in filas]


class TestParesNombreNormalizado:
    def test_solo_nombre_completa_la_normalizada(
        self, client, db_session, write_key, metric_con_par_nombre
    ):
        metric, dims = metric_con_par_nombre
        resp = client.post(
            f"/api/ingest/metrics/{metric.id_metric}/data",
            json={"records": [
                {"value": 0.5, "dimensions": {"Curso": "II A", "Nombre": "Pérez Juan"}},
                {"value": 0.7, "dimensions": {"Nombre": "Ana Soto"}},
            ]},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["rows_ok"] == 2

        id_nom = str(dims["Nombre"].id_dimension)
        id_norm = str(dims["Nombre_Norm"].id_dimension)
        guardadas = _dims_guardadas(db_session, metric)
        assert [d[id_nom] for d in guardadas] == ["Pérez Juan", "Ana Soto"]
        assert [d[id_norm] for d in guardadas] == ["JUAN PEREZ", "ANA SOTO"]

    def test_solo_normalizada_copia_el_nombre(
        self, client, db_session, write_key, metric_con_par_nombre
    ):
        metric, dims = metric_con_par_nombre
        resp = client.post(
            f"/api/ingest/metrics/{metric.id_metric}/data",
            json={"records": [{"value": 0.5, "dimensions": {"Nombre_Norm": "JUAN PEREZ"}}]},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text

        id_nom = str(dims["Nombre"].id_dimension)
        id_norm = str(dims["Nombre_Norm"].id_dimension)
        (guardada,) = _dims_guardadas(db_session, metric)
        assert guardada[id_norm] == "JUAN PEREZ"
        assert guardada[id_nom] == "JUAN PEREZ"

    def test_ambas_presentes_quedan_intactas(
        self, client, db_session, write_key, metric_con_par_nombre
    ):
        """Guard de no-sobrescritura: si vienen las dos, ninguna se toca."""
        metric, dims = metric_con_par_nombre
        resp = client.post(
            f"/api/ingest/metrics/{metric.id_metric}/data",
            json={"records": [{
                "value": 0.5,
                "dimensions": {"Nombre": "Pérez Juan", "Nombre_Norm": "valor raro"},
            }]},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text

        id_nom = str(dims["Nombre"].id_dimension)
        id_norm = str(dims["Nombre_Norm"].id_dimension)
        (guardada,) = _dims_guardadas(db_session, metric)
        assert guardada == {id_nom: "Pérez Juan", id_norm: "valor raro"}

    def test_sin_par_asociado_no_cambia_nada(
        self, client, db_session, write_key, metric_sin_par_nombre
    ):
        metric, dims = metric_sin_par_nombre
        resp = client.post(
            f"/api/ingest/metrics/{metric.id_metric}/data",
            json={"records": [{"value": 0.5, "dimensions": {"Nombre": "Pérez Juan"}}]},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text

        (guardada,) = _dims_guardadas(db_session, metric)
        assert guardada == {str(dims["Nombre"].id_dimension): "Pérez Juan"}

    def test_sin_nombre_no_inventa_columnas(
        self, client, db_session, write_key, metric_con_par_nombre
    ):
        metric, dims = metric_con_par_nombre
        resp = client.post(
            f"/api/ingest/metrics/{metric.id_metric}/data",
            json={"records": [{"value": 0.5, "dimensions": {"Curso": "II A"}}]},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text

        (guardada,) = _dims_guardadas(db_session, metric)
        assert guardada == {str(dims["Curso"].id_dimension): "II A"}

    def test_dry_run_no_inserta_nada(
        self, client, db_session, write_key, metric_con_par_nombre
    ):
        """El completado no altera la semántica de dry_run."""
        metric, _ = metric_con_par_nombre
        resp = client.post(
            f"/api/ingest/metrics/{metric.id_metric}/data",
            json={
                "records": [{"value": 0.5, "dimensions": {"Nombre": "Pérez Juan"}}],
                "dry_run": True,
            },
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["rows_ok"] == 1
        assert _dims_guardadas(db_session, metric) == []


# ─────────────────────────────────────────────────────────────────────────
# Schema endpoint
# ─────────────────────────────────────────────────────────────────────────

class TestSchema:
    def test_devuelve_fields_y_dimensiones(self, client, read_key, object_metric):
        resp = client.get(f"/api/ingest/metrics/{object_metric.id_metric}/schema", headers=_headers(read_key))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["data_type"] == "object"
        assert {"name": "puntaje", "type": "int"} in body["fields"]
        assert {"name": "aprobado", "type": "bool"} in body["fields"]
        assert {"name": "Curso", "type": "str"} in body["dimensions"]

    def test_metrica_simple_expone_field_implicito(self, client, read_key, simple_metric):
        resp = client.get(f"/api/ingest/metrics/{simple_metric.id_metric}/schema", headers=_headers(read_key))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["fields"] == [{"name": "Asistencia", "type": "float"}]

    def test_scope_faltante_403(self, client, write_key, simple_metric):
        # write_key solo tiene ingest:write, no metrics:read.
        resp = client.get(f"/api/ingest/metrics/{simple_metric.id_metric}/schema", headers=_headers(write_key))
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────
# Trigger de pipelines
# ─────────────────────────────────────────────────────────────────────────

def _make_pipeline(db, org, *, config: dict, name: str = "Pipeline API"):
    from backend.models import Pipeline

    p = Pipeline(
        pipeline=name,
        description="",
        config_json=json.dumps(config, ensure_ascii=False),
        org_id=org.id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


class TestTrigger:
    @pytest.fixture(autouse=True)
    def _uploads_dir_aislado(self, tmp_path, monkeypatch):
        """Redirige UPLOADS_DIR/PIPELINE_RUNS_DIR a un tmp_path — igual que
        test_w0_hardening.py para pipelines.py. Sin esto, el trigger intenta
        escribir en data/pipeline_runs/{uploads,runs} del repo real, que no
        es escribible en el entorno de test."""
        from backend.routers import ingest as mod
        monkeypatch.setattr(mod, "UPLOADS_DIR", tmp_path / "uploads")

        import backend.rgenerator.core.init_steps as init_steps_mod
        monkeypatch.setattr(init_steps_mod, "PIPELINE_RUNS_DIR", tmp_path / "runs_root")

    def test_happy_path_completa(self, client, db_session, org, write_key):
        # Config mínima que no requiere archivos para completar.
        config = {"pipeline": [{"step": "InitRun", "params": {"evaluation": "test"}}]}
        pipeline = _make_pipeline(db_session, org, config=config)

        resp = client.post(
            f"/api/ingest/pipelines/{pipeline.pipeline_id}/trigger",
            data={"input_key": "estudiantes"},
            files={"files": ("data.csv", b"a,b\n1,2\n", "text/csv")},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "completed"
        assert "job_id" in body

        from backend.models import IngestLog
        log = db_session.query(IngestLog).filter(IngestLog.id == body["job_id"]).first()
        assert log is not None
        assert log.status == "success"
        assert log.endpoint == f"pipelines/{pipeline.pipeline_id}/trigger"

    def test_cross_org_404(self, client, db_session, org, write_key):
        org_b = make_org(db_session)
        config = {"pipeline": [{"step": "InitRun", "params": {"evaluation": "test"}}]}
        pipeline_b = _make_pipeline(db_session, org_b, config=config)

        resp = client.post(
            f"/api/ingest/pipelines/{pipeline_b.pipeline_id}/trigger",
            data={"input_key": "estudiantes"},
            files={"files": ("data.csv", b"a,b\n1,2\n", "text/csv")},
            headers=_headers(write_key),
        )
        assert resp.status_code == 404

    def test_needs_review_cuando_faltan_archivos(self, client, db_session, org, write_key):
        config = {
            "pipeline": [
                {"step": "InitRun", "params": {"evaluation": "test"}},
                {
                    "step": "RequestUserFiles",
                    "params": {"file_specs": [{"id": "otros_datos", "label": "Otros datos"}]},
                },
            ]
        }
        pipeline = _make_pipeline(db_session, org, config=config)

        resp = client.post(
            f"/api/ingest/pipelines/{pipeline.pipeline_id}/trigger",
            data={"input_key": "estudiantes"},
            files={"files": ("data.csv", b"a,b\n1,2\n", "text/csv")},
            headers=_headers(write_key),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "needs_review"

    def test_sin_scope_403(self, client, db_session, org, read_key):
        config = {"pipeline": [{"step": "InitRun", "params": {"evaluation": "test"}}]}
        pipeline = _make_pipeline(db_session, org, config=config)

        resp = client.post(
            f"/api/ingest/pipelines/{pipeline.pipeline_id}/trigger",
            data={"input_key": "estudiantes"},
            files={"files": ("data.csv", b"a,b\n1,2\n", "text/csv")},
            headers=_headers(read_key),
        )
        assert resp.status_code == 403
