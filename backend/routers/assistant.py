"""Asistente de configuración de indicadores.

POST /api/assistant/chat — chat con contexto del indicador (opcional).
El proveedor LLM es intercambiable (backend/llm_provider.py): modo mock por
defecto, Claude al configurar LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.llm_provider import LLMProviderError, get_provider
from backend.logging_config import get_logger
from backend.models import Indicator, IndicatorMetric, Metric, User

logger = get_logger(__name__)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

MAX_MESSAGES = 40
MAX_MESSAGE_CHARS = 8000

SYSTEM_BASE = """Eres el asistente de configuración de Report Generator, un SaaS de \
informes académicos para fundaciones educacionales chilenas. Ayudas a administradores \
a programar indicadores y sus configuraciones. Respondes SIEMPRE en español, conciso \
y con ejemplos JSON concretos listos para pegar.

Campos configurables de un Indicator:
- achievement_levels: array JSON ordenado peor→mejor con los niveles de logro.
- dashboard_layout: JSON {tabs: [{title, components: [{type: "configured_chart"|"configured_table", chart_id|table_id}]}]}. \
Los charts se crean en /charts y las tablas en /tables; los colores de niveles se \
heredan por aesthetics.color_overrides.
- filter_dimensions: array de ids de dimensiones filtrables (el dashboard las muestra \
en cascada, multi-valor).
- temporal_config: JSON que declara las dimensiones temporales (Mes, Hito, Año, Versión).
- derived_columns: array de campos calculados con kinds agg | slope | delta \
(entity_field puede ser compuesto, value_type/time_type pueden ser ordinal con sus levels).
- column_roles / role_labels / role_formats: mapeo de columnas a roles de despliegue.
- pdf_layout / pdf_layout_historico: layouts de informe PDF del motor v1.

Si el usuario pide algo destructivo o fuera de la configuración de indicadores, \
oriéntalo a la sección correcta de la app en vez de inventar. No inventes ids de \
charts/tablas/dimensiones que no estén en el contexto."""


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)
    indicator_id: Optional[int] = None


def _parse(value, default):
    if isinstance(value, str) and value:
        try:
            return json.loads(value)
        except Exception:
            return default
    return value if value is not None else default


def _contexto_indicator(db: Session, indicator_id: int, org_id: int) -> str:
    """Resume la configuración actual del indicador para el system prompt."""
    ind = (
        db.query(Indicator)
        .filter(Indicator.id_indicator == indicator_id, Indicator.org_id == org_id)
        .first()
    )
    if not ind:
        raise HTTPException(404, "Indicador no encontrado")

    metric_ids = [
        l.id_metric
        for l in db.query(IndicatorMetric)
        .filter(IndicatorMetric.id_indicator == ind.id_indicator)
        .all()
    ]
    metrics = (
        db.query(Metric)
        .filter(Metric.id_metric.in_(metric_ids), Metric.org_id == org_id)
        .all()
        if metric_ids
        else []
    )

    contexto = {
        "nombre": ind.name,
        "tipo": ind.type,
        "descripcion": ind.description or "",
        "achievement_levels": _parse(ind.achievement_levels, []),
        "filter_dimensions": _parse(ind.filter_dimensions, []),
        "temporal_config": _parse(ind.temporal_config, {}),
        "derived_columns": _parse(ind.derived_columns, []),
        "dashboard_layout": _parse(ind.dashboard_layout, {}),
        "metrics_asociadas": [{"id": m.id_metric, "nombre": m.name} for m in metrics],
    }
    return (
        "\n\nCONTEXTO — configuración actual del indicador sobre el que el usuario "
        "está trabajando:\n" + json.dumps(contexto, ensure_ascii=False, indent=1)
    )


@router.post("/chat")
def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    system = SYSTEM_BASE
    if body.indicator_id is not None:
        system += _contexto_indicator(db, body.indicator_id, user.org_id)

    try:
        provider = get_provider()
        reply = provider.chat(system, [m.model_dump() for m in body.messages])
    except LLMProviderError as e:
        raise HTTPException(e.status_code, e.detail)
    except Exception:
        logger.error("Error no controlado en el asistente", exc_info=True)
        raise HTTPException(500, "Error interno del asistente")

    return {"reply": reply, "provider": provider.name}


@router.get("/status")
def status(user: User = Depends(get_current_user)):
    """Estado del asistente: qué proveedor está activo (para la UI)."""
    try:
        provider = get_provider()
        return {"available": True, "provider": provider.name}
    except LLMProviderError as e:
        return {"available": False, "provider": None, "detail": e.detail}
