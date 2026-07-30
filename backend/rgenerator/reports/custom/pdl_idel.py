"""Informe PDL IDEL-Woodcock — wrapper del generador matplotlib.

Delega en `backend/rgenerator/tooling/report_pdl_idel_tools.py`, el mismo
código que sirve `POST /api/indicators/{id}/export-pdf` con
`engine="pdl_idel"`. Este wrapper solo lo publica en el registro custom.

Los filtros de este informe llegan como `{id_dimension: valor}` (los mismos
que manda el dashboard), no por nombre de columna: el adapter los traduce
internamente con `_translate_filters`.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

LABEL = "Informe PDL IDEL-Woodcock"
DESCRIPCION = (
    "Informe especializado multi-curso con matrices de transición entre "
    "niveles de riesgo (formato fijo, no configurable desde la UI)."
)
FORMATO = "pdf"
ENGINE_TYPES = ["pdl_idel"]
REQUIERE_FILTRO_TEMPORAL: list[str] = []
# IDEL es una sola asignatura (lectura): no hay nada que elegir.
REQUIERE_ASIGNATURA = False
FILENAME = "informe_pdl_idel.pdf"


def generar(
    db: Session,
    *,
    indicator_id: int,
    org_id: int,
    filtros: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> bytes:
    """Bytes del PDF PDL IDEL-Woodcock.

    Raises:
        ValueError: si el indicador no existe en la org o si no hay datos
            tras aplicar los filtros.
    """
    from backend.models import Indicator
    from backend.rgenerator.tooling.report_pdl_idel_tools import build_pdl_idel_pdf_bytes

    indicator = (
        db.query(Indicator)
        .filter(Indicator.id_indicator == indicator_id, Indicator.org_id == org_id)
        .first()
    )
    if not indicator:
        raise ValueError(f"Indicator {indicator_id} no existe en org {org_id}")

    return build_pdl_idel_pdf_bytes(indicator, db, org_id, filters=filtros)
