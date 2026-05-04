"""auditing.py — helpers para registrar metadatos de carga en metric_data.

Cualquier código que inserte filas en `metric_data` debe pasar por
`make_metric_data` para que el registro quede auditado uniformemente.

Campos:
  - created_by_user_id: id del User que disparó la inserción (None si pipeline cron / legacy).
  - created_via: enum string indicando cómo entró el dato.
  - created_from_ip: IP de origen (opcional, captura desde Request si está disponible).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, Union

from fastapi import Request

from backend.models import MetricData


# Valores válidos para `created_via`. Validamos en el helper para que un
# typo no quede silencioso.
ALLOWED_VIA = frozenset({
    "pipeline",        # ejecución de pipeline disparada por usuario logueado
    "pipeline_cron",   # ejecución scheduled / sin usuario asociado
    "import_csv",      # bulk import desde Excel/CSV (POST /metrics/{id}/import)
    "manual_single",   # alta individual desde UI (POST /metrics/{id}/data)
    "api_direct",      # carga programática vía API (futuro: integración externa)
})


def make_metric_data(
    *,
    metric_id: int,
    value: Optional[str],
    dimensions: Union[dict, str],
    org_id: int,
    user_id: Optional[int],
    via: str,
    ip: Optional[str] = None,
) -> MetricData:
    """Construye una instancia de MetricData con auditoría poblada.

    `value` debe ser ya un string (json-serializado si era dict).
    `dimensions` puede ser dict (se serializa) o string (se asume json válido).
    """
    if via not in ALLOWED_VIA:
        raise ValueError(f"created_via inválido: {via!r}. Esperado uno de {sorted(ALLOWED_VIA)}")

    if isinstance(dimensions, dict):
        dimensions_json = json.dumps(dimensions, ensure_ascii=False)
    else:
        dimensions_json = dimensions or "{}"

    return MetricData(
        id_metric=metric_id,
        value=value,
        dimensions_json=dimensions_json,
        created_at=datetime.utcnow(),
        org_id=org_id,
        created_by_user_id=user_id,
        created_via=via,
        created_from_ip=ip,
    )


def client_ip(request: Optional[Request]) -> Optional[str]:
    """Extrae la IP del cliente desde el Request de FastAPI.

    Considera `X-Forwarded-For` para casos detrás de proxy (Railway, Render).
    Devuelve None si no hay request (ej. inserción desde script).
    """
    if request is None:
        return None
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        # X-Forwarded-For puede traer "client, proxy1, proxy2". El primero es el cliente.
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None
