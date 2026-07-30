"""Informe DIA (Diagnóstico Integral de Aprendizajes) — wrapper del motor v2.

La lógica vive en `reports/dispatch_v2.py`, compartida con el endpoint
legacy `POST /api/reports/dia`.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..dispatch_v2 import generar_pdf_v2

LABEL = "Informe de evaluación DIA (formato oficial)"
DESCRIPCION = (
    "PDF con el formato oficial del DIA. Requiere filtrar a un solo hito "
    "(o año) para no mezclar aplicaciones."
)
FORMATO = "pdf"
ENGINE_TYPES = ["dia"]
REQUIERE_FILTRO_TEMPORAL = ["Hito", "Año"]
# Los datos DIA de la fundación traen LECTURA y MATEMATICA del mismo
# alumno: sin fijar la asignatura, todos los conteos se duplican.
REQUIERE_ASIGNATURA = True
FILENAME = "informe_dia.pdf"


def generar(
    db: Session,
    *,
    indicator_id: int,
    org_id: int,
    filtros: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> bytes:
    """Bytes del PDF DIA."""
    return generar_pdf_v2(
        db,
        tipo="dia",
        indicator_id=indicator_id,
        org_id=org_id,
        filtros=filtros,
        overrides=overrides,
    )
