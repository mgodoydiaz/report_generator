"""Endpoint del motor PDF v2 (`backend/rgenerator/reports/`).

Expone POST /api/reports/{tipo} que recibe filtros + indicator_id y
devuelve el PDF binario. Independiente del motor viejo `RenderPDFReport`
del Indicator (que sigue funcionando vía /api/results y el botón
"Generar Reporte" del frontend).

El frontend puede llamar este endpoint desde un botón nuevo "Generar
Reporte v2" o equivalente, pasando el indicator_id + dict de filtros.
"""
from __future__ import annotations

import traceback
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import User
from backend.rgenerator.reports import runtime
from backend.rgenerator.reports.data import cargar_dataframes_indicator
from backend.rgenerator.reports.dia import crear_informe as dia_informe
from backend.rgenerator.reports.simce import crear_informe as simce_informe


router = APIRouter(prefix="/api/reports", tags=["reports-v2"])


class ReportRequest(BaseModel):
    """Request body para POST /api/reports/{tipo}."""
    indicator_id: int
    filtros: dict[str, Any] | None = None
    overrides: dict[str, Any] | None = None  # ej {"branding": {"center_header": [...]}}


# ─────────────────────────────────────────────────────────────────────────
# Listing de tipos disponibles (introspección desde frontend)
# ─────────────────────────────────────────────────────────────────────────

@router.get("/tipos")
async def listar_tipos(user: User = Depends(get_current_user)):
    """Tipos de informe que el motor v2 puede generar.

    Cada tipo tiene un esquema declarativo en
    `backend/rgenerator/reports/<tipo>/esquema.json`.
    """
    return [
        {"tipo": "simce", "label": "Informe SIMCE", "params_esperados": ["asignatura", "numero_prueba"]},
        {"tipo": "dia", "label": "Informe DIA", "params_esperados": ["asignatura", "hito"]},
    ]


@router.get("/charts")
async def listar_charts(user: User = Depends(get_current_user)):
    """Lista las funciones de gráfico disponibles + sus metadatos.

    Útil para que el frontend ofrezca selector "agregar gráfico" en un
    futuro editor visual.
    """
    from backend.rgenerator.reports.charts import CHART_REGISTRY
    return {
        nombre: {k: v for k, v in spec.items() if k != "fn"}
        for nombre, spec in CHART_REGISTRY.items()
    }


@router.get("/tablas")
async def listar_tablas(user: User = Depends(get_current_user)):
    """Lista las funciones de tabla disponibles + sus metadatos."""
    from backend.rgenerator.reports.tables import TABLE_REGISTRY
    return {
        nombre: {k: v for k, v in spec.items() if k != "fn"}
        for nombre, spec in TABLE_REGISTRY.items()
    }


# ─────────────────────────────────────────────────────────────────────────
# Generación de PDF
# ─────────────────────────────────────────────────────────────────────────

@router.post("/{tipo}")
async def generar_reporte(
    tipo: str,
    body: ReportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Genera el PDF para `tipo` (simce | dia) con datos del Indicator.

    Args:
        tipo: identificador del informe — coincide con el subdirectorio
            que tiene el esquema.json.
        body: { indicator_id, filtros?, overrides? }.

    Returns:
        application/pdf con el binario.

    Raises:
        404 si el tipo no existe.
        400 si el indicator no se encuentra o no tiene metrics.
        500 si la generación falla.
    """
    if tipo not in ("simce", "dia"):
        raise HTTPException(404, f"Tipo '{tipo}' no soportado. Disponibles: simce, dia")

    try:
        dataframes = cargar_dataframes_indicator(
            db,
            indicator_id=body.indicator_id,
            org_id=user.org_id,
            filtros=body.filtros,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Error cargando datos: {type(e).__name__}: {e}")

    try:
        if tipo == "simce":
            # SIMCE necesita asignatura + numero_prueba. Los toma de filtros
            # si vienen, sino usa defaults razonables.
            asignatura = (body.filtros or {}).get("Asignatura", "LENGUAJE")
            numero_prueba = int((body.filtros or {}).get("Numero_Prueba", 5))
            df_estudiantes = dataframes.get("estudiantes", None)
            df_preguntas = dataframes.get("preguntas", None)
            if df_estudiantes is None or df_preguntas is None:
                raise HTTPException(
                    400,
                    "El indicator debe tener metrics 'estudiantes' y 'preguntas' asociadas",
                )
            pdf_bytes = simce_informe.construir(
                df_estudiantes,
                df_preguntas,
                asignatura=asignatura,
                numero_prueba=numero_prueba,
                overrides=body.overrides,
            )
        else:  # dia
            df_estudiantes = dataframes.get("estudiantes", None)
            df_preguntas = dataframes.get("preguntas", None)
            if df_estudiantes is None or df_preguntas is None:
                raise HTTPException(
                    400,
                    "El indicator DIA debe tener metrics 'estudiantes' y 'preguntas' asociadas",
                )
            pdf_bytes = dia_informe.construir(
                df_estudiantes,
                df_preguntas,
                overrides=body.overrides,
            )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Error generando PDF: {type(e).__name__}: {e}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="informe_{tipo}.pdf"'},
    )
