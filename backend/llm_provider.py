"""Proveedor LLM intercambiable para el asistente de indicadores.

Selección por env var `LLM_PROVIDER`:
  - "mock" (default): respuestas guiadas por reglas, sin costo ni red.
    Permite desarrollar y testear la UI/endpoint sin API key.
  - "anthropic": Claude vía Messages API. Requiere ANTHROPIC_API_KEY.
    Modelo configurable con ASSISTANT_LLM_MODEL (default claude-opus-4-8).

Contrato: `get_provider().chat(system, messages)` → str (respuesta del asistente).
`messages` es una lista [{"role": "user"|"assistant", "content": str}].
Errores del proveedor se levantan como LLMProviderError(status_code, detail)
para que el router los traduzca a HTTPException sin filtrar detalles internos.
"""
from __future__ import annotations

import os
from typing import Dict, List

from backend.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_ANTHROPIC_MODEL = "claude-opus-4-8"
MAX_TOKENS = 4096


class LLMProviderError(Exception):
    """Error de proveedor con status HTTP sugerido y mensaje apto para el usuario."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class MockProvider:
    """Proveedor sin LLM: respuestas por reglas para desarrollo y tests.

    No pretende ser inteligente — cubre las preguntas típicas sobre
    configuración de indicadores con ejemplos concretos, y deja claro
    que es el modo mock.
    """

    name = "mock"

    _RESPUESTAS = [
        (
            ("nivel", "niveles", "logro", "color", "achievement"),
            "Los niveles de logro se definen en `achievement_levels` como lista "
            "ordenada de peor a mejor. Ejemplo para IDEL:\n\n"
            '```json\n["Crítico", "Alto Riesgo", "Cierto Riesgo", "Bajo Riesgo"]\n```\n\n'
            "Los colores oficiales se asignan en los charts vía "
            "`aesthetics.color_overrides` (no via paleta) para mantener "
            "consistencia con la página de Indicadores.",
        ),
        (
            ("layout", "dashboard", "tab", "pestaña"),
            "El `dashboard_layout` es un JSON con tabs y componentes. Cada tab "
            "tiene `title` y `components`, y cada componente referencia un chart "
            "o tabla del catálogo:\n\n"
            '```json\n{"tabs": [{"title": "Resumen", "components": [\n'
            '  {"type": "configured_chart", "chart_id": 5},\n'
            '  {"type": "configured_table", "table_id": 2}\n]}]}\n```\n\n'
            "Los charts se administran en /charts y las tablas en /tables.",
        ),
        (
            ("filtro", "filtros", "dimension", "dimensión"),
            "Los filtros del dashboard se configuran en `filter_dimensions` como "
            "array de ids de dimensiones. El dashboard los muestra en cascada y "
            "soporta multi-valor. Las dimensiones temporales van además en "
            "`temporal_config` para que los informes respeten el punto en el tiempo.",
        ),
        (
            ("derivad", "slope", "delta", "agg", "calculad"),
            "Las columnas calculadas van en `derived_columns` con el engine de "
            "campos derivados: `agg` (groupby+agregación), `slope` (regresión "
            "expansiva) y `delta` (último menos primero). Ejemplo:\n\n"
            '```json\n[{"name": "Avance", "kind": "slope", "value_field": "Rendimiento",\n'
            '  "time_field": "Mes", "entity_field": ["Curso", "Nombre"]}]\n```',
        ),
    ]

    def chat(self, system: str, messages: List[Dict[str, str]]) -> str:
        ultimo = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
        ).lower()
        for claves, respuesta in self._RESPUESTAS:
            if any(c in ultimo for c in claves):
                return respuesta + "\n\n_(Asistente en modo demo — configura ANTHROPIC_API_KEY y LLM_PROVIDER=anthropic para respuestas completas.)_"
        return (
            "Puedo ayudarte a configurar este indicador: niveles de logro y "
            "colores, layout del dashboard (tabs, charts, tablas), filtros por "
            "dimensión y columnas calculadas (derived_columns). ¿Sobre cuál "
            "quieres avanzar?\n\n"
            "_(Asistente en modo demo — configura ANTHROPIC_API_KEY y "
            "LLM_PROVIDER=anthropic para respuestas completas.)_"
        )


class AnthropicProvider:
    """Claude vía Messages API (SDK oficial `anthropic`)."""

    name = "anthropic"

    def __init__(self):
        try:
            import anthropic  # noqa: F401
        except ImportError:
            raise LLMProviderError(
                503,
                "El proveedor Anthropic no está disponible: falta el paquete "
                "'anthropic' (pip install anthropic).",
            )
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMProviderError(
                503,
                "El proveedor Anthropic no está configurado: falta ANTHROPIC_API_KEY.",
            )
        self._anthropic = anthropic
        self._client = anthropic.Anthropic()
        self._model = os.environ.get("ASSISTANT_LLM_MODEL", DEFAULT_ANTHROPIC_MODEL)

    def chat(self, system: str, messages: List[Dict[str, str]]) -> str:
        a = self._anthropic
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=MAX_TOKENS,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                thinking={"type": "adaptive"},
                messages=messages,
            )
        except a.AuthenticationError:
            raise LLMProviderError(503, "API key de Anthropic inválida o revocada.")
        except a.RateLimitError:
            raise LLMProviderError(429, "Límite de uso del asistente alcanzado. Intenta en unos minutos.")
        except a.APIStatusError as e:
            logger.error(f"Error de la API de Anthropic ({e.status_code})", exc_info=True)
            raise LLMProviderError(502, "El asistente no está disponible en este momento.")
        except a.APIConnectionError:
            raise LLMProviderError(502, "No se pudo conectar con el servicio del asistente.")

        if response.stop_reason == "refusal":
            return "No puedo ayudar con esa solicitud. ¿Quieres que veamos otra parte de la configuración?"
        return "".join(b.text for b in response.content if b.type == "text")


def get_provider():
    """Instancia el proveedor según LLM_PROVIDER (default: mock)."""
    provider = os.environ.get("LLM_PROVIDER", "mock").strip().lower()
    if provider == "anthropic":
        return AnthropicProvider()
    if provider == "mock":
        return MockProvider()
    raise LLMProviderError(500, f"LLM_PROVIDER desconocido: '{provider}' (usar mock | anthropic).")
