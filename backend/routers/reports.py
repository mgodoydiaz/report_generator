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
from backend.rgenerator.reports.simce_panguipulli import crear_informe as simce_panguipulli_informe


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
        {"tipo": "simce_panguipulli", "label": "Informe SIMCE Panguipulli", "params_esperados": ["asignatura", "numero_prueba"]},
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
    if tipo not in ("simce", "simce_panguipulli", "dia"):
        raise HTTPException(404, f"Tipo '{tipo}' no soportado. Disponibles: simce, simce_panguipulli, dia")

    # Validación: el motor v2 está pensado para UNA evaluación. Sin filtro
    # temporal mezclaría datos de múltiples meses/hitos y los gráficos
    # quedarían sucios. Exigimos al menos uno de los filtros temporales
    # conocidos por tipo.
    filtros_aplicados = body.filtros or {}
    filtros_temporales = {
        "simce": ["Mes", "N Prueba", "Numero_Prueba"],
        "simce_panguipulli": ["Mes", "N Prueba", "Numero_Prueba"],
        "dia": ["Hito", "Año"],
    }
    requeridos = filtros_temporales.get(tipo, [])
    if not any(k in filtros_aplicados for k in requeridos):
        raise HTTPException(
            400,
            f"El motor v2 requiere al menos un filtro temporal para mantener "
            f"un solo punto en el tiempo. Para '{tipo}', aplicar uno de: "
            f"{', '.join(requeridos)}.",
        )

    # Separar filtros temporales (van a crear_informe como param) de los
    # estructurales (van al loader). Esto permite que las derived_fields
    # tipo slope/delta vean todo el histórico antes de filtrar a una prueba.
    temporales_set = set(requeridos)
    filtros_estructurales = {k: v for k, v in filtros_aplicados.items() if k not in temporales_set}
    filtros_temporales_dict = {k: v for k, v in filtros_aplicados.items() if k in temporales_set}

    try:
        dataframes = cargar_dataframes_indicator(
            db,
            indicator_id=body.indicator_id,
            org_id=user.org_id,
            filtros=filtros_estructurales,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Error cargando datos: {type(e).__name__}: {e}")

    try:
        if tipo == "simce":
            # SIMCE necesita asignatura + numero_prueba (o el Mes específico).
            # crear_informe.construir aplica el filtro temporal después de
            # ejecutar las derived_fields, para que slope/delta vean todas
            # las pruebas del histórico.
            asignatura = filtros_estructurales.get("Asignatura", "LENGUAJE")
            mes = filtros_temporales_dict.get("Mes")
            n_prueba_raw = filtros_temporales_dict.get("N Prueba") or filtros_temporales_dict.get("Numero_Prueba", 5)
            try:
                numero_prueba = int(n_prueba_raw)
            except (TypeError, ValueError):
                numero_prueba = 5
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
                mes=mes,
                overrides=body.overrides,
            )
        elif tipo == "simce_panguipulli":
            # Variante Panguipulli: usa df_estudiantes (metric 24) + df_habilidad
            # (metric 26) en lugar de df_preguntas. data.py asigna a metric 26 el
            # rol "otros" → key "metric_26"; el detector aquí intenta varias
            # claves conocidas para localizarlo.
            asignatura = filtros_estructurales.get("Asignatura", "LENGUAJE")
            mes = filtros_temporales_dict.get("Mes")
            n_prueba_raw = filtros_temporales_dict.get("N Prueba") or filtros_temporales_dict.get("Numero_Prueba", 4)
            try:
                numero_prueba = int(n_prueba_raw)
            except (TypeError, ValueError):
                numero_prueba = 4
            df_estudiantes = dataframes.get("estudiantes", None)
            # Buscar el DataFrame de habilidad por las keys posibles que asigna
            # `cargar_dataframes_indicator` (rol detectado por nombre). No uso
            # `or` porque pandas no permite evaluar la verdad de un DataFrame.
            df_habilidad = dataframes.get("habilidad")
            if df_habilidad is None:
                df_habilidad = dataframes.get("metric_26")
            if df_habilidad is None:
                df_habilidad = next(
                    (v for k, v in dataframes.items() if k.startswith("metric_")),
                    None,
                )
            if df_estudiantes is None or df_habilidad is None:
                raise HTTPException(
                    400,
                    "El indicator SIMCE Panguipulli debe tener metrics 'por Estudiante' "
                    "y 'por Habilidad' asociadas",
                )
            pdf_bytes = simce_panguipulli_informe.construir(
                df_estudiantes,
                df_habilidad,
                asignatura=asignatura,
                numero_prueba=numero_prueba,
                mes=mes,
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
            hito = filtros_temporales_dict.get("Hito")
            pdf_bytes = dia_informe.construir(
                df_estudiantes,
                df_preguntas,
                hito=hito,
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
