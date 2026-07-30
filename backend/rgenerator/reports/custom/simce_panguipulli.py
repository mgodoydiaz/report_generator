"""Informe SIMCE Panguipulli — wrapper del motor v2.

Variante del SIMCE que usa la metric "por Habilidad" en lugar de "por
Pregunta". La lógica vive en `reports/dispatch_v2.py`.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..dispatch_v2 import generar_pdf_v2

LABEL = "Informe de evaluación SIMCE Panguipulli (formato oficial)"
DESCRIPCION = (
    "PDF con el formato oficial del ensayo SIMCE Panguipulli (resultados "
    "por habilidad). Requiere filtrar a un solo punto temporal."
)
FORMATO = "pdf"
ENGINE_TYPES = ["simce_panguipulli"]
REQUIERE_FILTRO_TEMPORAL = ["Mes", "N Prueba", "Numero_Prueba"]
REQUIERE_ASIGNATURA = True
FILENAME = "informe_simce_panguipulli.pdf"


def generar(
    db: Session,
    *,
    indicator_id: int,
    org_id: int,
    filtros: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> bytes:
    """Bytes del PDF SIMCE Panguipulli."""
    return generar_pdf_v2(
        db,
        tipo="simce_panguipulli",
        indicator_id=indicator_id,
        org_id=org_id,
        filtros=filtros,
        overrides=overrides,
    )
