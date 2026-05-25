"""Smoke test del boot de FastAPI.

Motivado por el incidente 2026-05-19: el backend se cayó en Railway y el
panel siguió marcando "Active" porque Railway no tiene healthcheck activo
configurado. Si el proceso muriera al import (por ejemplo, un error en un
router recién agregado, un símbolo eliminado, o un schema malformado),
queremos detectarlo en CI antes que en producción.

Este test no reemplaza un healthcheck en Railway — son capas complementarias:
- Este test: la app importa y monta sin errores.
- Railway healthcheck: el contenedor vivo responde HTTP 200.

Si este test pasa pero prod sigue cayendo, el problema es runtime (memoria,
DB, deadlock), no boot.
"""
from __future__ import annotations

import pytest


@pytest.mark.unit
class TestAppImport:
    """La app se construye limpia desde un import en frío."""

    def test_app_se_importa_sin_errores(self):
        """Detectaría: ImportError de cualquier router, Pydantic schema roto,
        symbol faltante, sintaxis."""
        from backend.api import app
        assert app is not None

    def test_app_es_instancia_fastapi(self):
        from fastapi import FastAPI
        from backend.api import app
        assert isinstance(app, FastAPI)


@pytest.mark.integration
class TestAppRoutas:
    """Las rutas críticas están registradas tras el boot."""

    def test_root_responde_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_openapi_schema_se_genera(self, client):
        """Si algún router tiene un schema Pydantic inválido o un Depends
        roto, /openapi.json devuelve 500. Este test atrapa eso temprano."""
        r = client.get("/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert "paths" in data
        assert len(data["paths"]) > 0

    @pytest.mark.parametrize("prefix", [
        "/api/auth",
        "/api/users",
        "/api/charts",
        "/api/tables",
        "/api/indicators",
        "/api/results",
        "/api/metrics",
        "/api/dimensions",
        "/api/pipelines",
        "/api/reports",
        "/api/mappings",
        "/api/data-ops",
        "/api/organizations",
        "/api/specs",
        "/api/superadmin",
    ])
    def test_router_prefix_registrado_en_openapi(self, client, prefix):
        """Verifica vía /openapi.json que cada router crítico está montado.

        Detectaría: alguien olvidó `app.include_router(...)` para un router,
        o un router falló al importar y no llegó a registrarse.

        Usamos /openapi.json en lugar de hacer GET al prefix porque varios
        routers no tienen endpoint en la raíz (ej: /api/results/ no existe,
        solo /api/results/indicator/{id}/data).
        """
        schema = client.get("/openapi.json").json()
        paths = list(schema.get("paths", {}).keys())
        assert any(p.startswith(prefix) for p in paths), (
            f"Ningún path del router '{prefix}' está registrado en OpenAPI"
        )
