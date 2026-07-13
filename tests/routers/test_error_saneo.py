"""Tests de saneo de errores 500 (W0.6 — data exposure).

Un error interno no controlado NO debe filtrar el mensaje de la excepción
(ni stack trace ni detalles) en el body de la respuesta. Se fuerza el fallo
con monkeypatch sobre un helper interno y se verifica que el cliente reciba
solo un mensaje genérico.
"""
from __future__ import annotations

import pytest

from tests.factories import make_metric

SECRETO = "FUGA_INTERNA_password=hunter2_/etc/passwd"


@pytest.mark.integration
def test_metrics_500_no_filtra_detalle_interno(client_auth, db_session, org, monkeypatch):
    """GET /api/metrics/ que revienta internamente → 500 genérico, sin str(e)."""
    from backend.routers import metrics as metrics_mod

    make_metric(db_session, org, name="M para forzar error")

    def _boom(*_a, **_k):
        raise RuntimeError(SECRETO)

    monkeypatch.setattr(metrics_mod, "_metric_to_dict", _boom)

    res = client_auth.get("/api/metrics/")
    assert res.status_code == 500
    body = res.text
    assert SECRETO not in body
    assert res.json()["detail"] == "Error interno del servidor"


@pytest.mark.integration
def test_pipelines_500_no_filtra_detalle_interno(client_auth, db_session, org, monkeypatch):
    """GET /api/pipelines/ conserva la FORMA {"error": ...} pero sin str(e)."""
    from backend.models import Pipeline
    from backend.routers import pipelines as pipelines_mod

    p = Pipeline(pipeline="P", description="", config_json="{}", org_id=org.id)
    db_session.add(p)
    db_session.commit()

    def _boom(*_a, **_k):
        raise RuntimeError(SECRETO)

    monkeypatch.setattr(pipelines_mod, "_pipeline_to_dict", _boom)

    res = client_auth.get("/api/pipelines/")
    assert res.status_code == 500
    assert SECRETO not in res.text
    assert res.json()["error"] == "Error interno del servidor"
