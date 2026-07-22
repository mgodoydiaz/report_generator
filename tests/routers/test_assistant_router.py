"""Tests del router /api/assistant (asistente de configuración de indicadores).

El proveedor por defecto es mock (sin red), así que los tests corren sin
API key. Cubre: auth, respuesta del chat, contexto de indicador con
tenancy, selección de proveedor y endpoint de status.
"""
from __future__ import annotations

import pytest

from tests.factories import make_indicator, make_metric, make_org


@pytest.mark.integration
class TestAssistantChat:
    def test_requiere_auth(self, client):
        resp = client.post("/api/assistant/chat", json={"messages": [{"role": "user", "content": "hola"}]})
        assert resp.status_code in (401, 403)

    def test_chat_mock_responde(self, client_auth):
        resp = client_auth.post(
            "/api/assistant/chat",
            json={"messages": [{"role": "user", "content": "¿Cómo configuro los niveles de logro?"}]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider"] == "mock"
        assert "achievement_levels" in body["reply"]

    def test_chat_generico_ofrece_temas(self, client_auth):
        resp = client_auth.post(
            "/api/assistant/chat",
            json={"messages": [{"role": "user", "content": "hola"}]},
        )
        assert resp.status_code == 200
        assert "indicador" in resp.json()["reply"].lower()

    def test_contexto_indicator_propio(self, client_auth, db_session, org):
        metric = make_metric(db_session, org, name="Rendimiento IDEL")
        ind = make_indicator(db_session, org, name="IDEL", metrics=[metric])
        resp = client_auth.post(
            "/api/assistant/chat",
            json={
                "messages": [{"role": "user", "content": "¿qué layout me recomiendas?"}],
                "indicator_id": ind.id_indicator,
            },
        )
        assert resp.status_code == 200

    def test_contexto_indicator_cross_org_404(self, client_auth, db_session):
        otra = make_org(db_session, name="Org Ajena Assistant")
        ind_ajeno = make_indicator(db_session, otra, name="Ajeno")
        resp = client_auth.post(
            "/api/assistant/chat",
            json={
                "messages": [{"role": "user", "content": "hola"}],
                "indicator_id": ind_ajeno.id_indicator,
            },
        )
        assert resp.status_code == 404

    def test_provider_invalido_da_500_limpio(self, client_auth, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "gpt9000")
        resp = client_auth.post(
            "/api/assistant/chat",
            json={"messages": [{"role": "user", "content": "hola"}]},
        )
        assert resp.status_code == 500
        assert "LLM_PROVIDER" in resp.json()["detail"]

    def test_mensajes_vacios_400(self, client_auth):
        resp = client_auth.post("/api/assistant/chat", json={"messages": []})
        assert resp.status_code == 422


@pytest.mark.integration
class TestAssistantStatus:
    def test_status_mock_disponible(self, client_auth):
        resp = client_auth.get("/api/assistant/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is True
        assert body["provider"] == "mock"

    def test_status_anthropic_sin_key_no_disponible(self, client_auth, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        resp = client_auth.get("/api/assistant/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is False
