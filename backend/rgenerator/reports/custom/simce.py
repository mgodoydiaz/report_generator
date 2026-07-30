"""Informe SIMCE (formato oficial) — wrapper del motor v2.

Toda la lógica vive en `reports/dispatch_v2.py`, compartida con el endpoint
legacy `POST /api/reports/simce`. Este módulo solo declara la metadata que
el selector del frontend necesita.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..dispatch_v2 import generar_pdf_v2

LABEL = "Informe de evaluación SIMCE (formato oficial)"
DESCRIPCION = (
    "PDF con el formato oficial del ensayo SIMCE. Requiere filtrar a un "
    "solo punto temporal (Mes o N° de prueba)."
)
FORMATO = "pdf"
ENGINE_TYPES = ["simce"]
REQUIERE_FILTRO_TEMPORAL = ["Mes", "N Prueba", "Numero_Prueba"]
FILENAME = "informe_simce.pdf"


def generar(
    db: Session,
    *,
    indicator_id: int,
    org_id: int,
    filtros: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> bytes:
    """Bytes del PDF SIMCE. Ver `dispatch_v2.generar_pdf_v2` para el detalle."""
    return generar_pdf_v2(
        db,
        tipo="simce",
        indicator_id=indicator_id,
        org_id=org_id,
        filtros=filtros,
        overrides=overrides,
    )
