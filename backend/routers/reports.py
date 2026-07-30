"""Endpoint del motor PDF v2 (`backend/rgenerator/reports/`).

Expone POST /api/reports/{tipo} que recibe filtros + indicator_id y
devuelve el PDF binario. Independiente del motor viejo `RenderPDFReport`
del Indicator (que sigue funcionando vía /api/results y el botón
"Generar Reporte" del frontend).

El frontend puede llamar este endpoint desde un botón nuevo "Generar
Reporte v2" o equivalente, pasando el indicator_id + dict de filtros.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.http_utils import content_disposition
from backend.logging_config import get_logger
from backend.models import User
from backend.rgenerator.reports.data import cargar_dataframes_indicator
from backend.rgenerator.reports.dispatch_v2 import (
    DatosInsuficientes,
    TipoNoSoportado,
    generar_pdf_v2,
)


logger = get_logger(__name__)

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
def listar_tipos(user: User = Depends(get_current_user)):
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
def listar_charts(user: User = Depends(get_current_user)):
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
def listar_tablas(user: User = Depends(get_current_user)):
    """Lista las funciones de tabla disponibles + sus metadatos."""
    from backend.rgenerator.reports.tables import TABLE_REGISTRY
    return {
        nombre: {k: v for k, v in spec.items() if k != "fn"}
        for nombre, spec in TABLE_REGISTRY.items()
    }


# ─────────────────────────────────────────────────────────────────────────
# Informes Word (docxtpl) — registro por nombre de archivo
# ─────────────────────────────────────────────────────────────────────────

class WordReportRequest(BaseModel):
    """Request body para POST /api/reports/word/{nombre}."""
    indicator_id: int
    filtros: dict[str, Any] | None = None
    params: dict[str, Any] | None = None  # llegan a construir_contexto del informe


@router.get("/word/informes")
def listar_informes_word(user: User = Depends(get_current_user)):
    """Informes Word registrados (un módulo Python por informe).

    El campo `nombre` es el identificador para POST /api/reports/word/{nombre}.
    """
    from backend.rgenerator.reports import word as word_reports
    return word_reports.listar_informes()


@router.get("/word/informes/{nombre}/placeholders")
def placeholders_informe_word(nombre: str, user: User = Depends(get_current_user)):
    """Códigos {{valor}} que la plantilla Word del informe espera."""
    from backend.rgenerator.reports import word as word_reports
    try:
        modulo = word_reports.obtener_modulo(nombre)
        return {"nombre": nombre, "placeholders": word_reports.listar_placeholders(modulo)}
    except KeyError as e:
        raise HTTPException(404, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/word/{nombre}")
def generar_informe_word(
    nombre: str,
    body: WordReportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Genera el informe Word `nombre` con datos del Indicator.

    El nombre asocia directamente al archivo
    `backend/rgenerator/reports/word/informes/<nombre>.py` y su plantilla
    `templates/<nombre>.docx`. Devuelve el .docx binario.
    """
    from backend.rgenerator.reports import word as word_reports

    try:
        modulo = word_reports.obtener_modulo(nombre)
    except KeyError as e:
        raise HTTPException(404, str(e))

    try:
        dataframes = cargar_dataframes_indicator(
            db,
            indicator_id=body.indicator_id,
            org_id=user.org_id,
            filtros=body.filtros or {},
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        logger.error("Error cargando datos para informe Word", exc_info=True)
        raise HTTPException(500, "Error cargando datos del informe")

    try:
        docx_bytes = word_reports.render_informe(modulo, dataframes, body.params)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception:
        logger.error("Error generando informe Word", exc_info=True)
        raise HTTPException(500, "Error generando el informe Word")

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": content_disposition(f"informe_{nombre}.docx")},
    )


# ─────────────────────────────────────────────────────────────────────────
# Informes custom (hardcodeados en Python) — registro auto-descubierto
# ─────────────────────────────────────────────────────────────────────────

class CustomReportRequest(BaseModel):
    """Request body para POST /api/reports/custom/{nombre}."""
    indicator_id: int
    filtros: dict[str, Any] | None = None
    params: dict[str, Any] | None = None      # libres, los define cada informe
    overrides: dict[str, Any] | None = None   # ej {"branding": {"left_footer": "..."}}


@router.get("/custom/informes")
def listar_informes_custom(user: User = Depends(get_current_user)):
    """Informes custom registrados (un módulo Python por informe).

    El campo `nombre` es el identificador para
    POST /api/reports/custom/{nombre}.
    """
    from backend.rgenerator.reports import custom as custom_reports
    return custom_reports.listar_informes()


@router.post("/custom/{nombre}")
def generar_informe_custom(
    nombre: str,
    body: CustomReportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Genera el informe custom `nombre` con datos del Indicator.

    El nombre asocia directamente al archivo
    `backend/rgenerator/reports/custom/<nombre>.py`. Devuelve el binario
    con el `FILENAME` que declare el módulo.

    Raises:
        404 si `nombre` no está registrado o el indicador no existe.
        400 si el informe no aplica al engine_type del indicador, o si el
            informe reporta datos/filtros insuficientes.
        500 en cualquier otro error de generación.
    """
    from backend.models import Indicator
    from backend.rgenerator.reports import custom as custom_reports
    from backend.rgenerator.reports.engine_types import resolver_engine_type

    try:
        modulo = custom_reports.obtener_modulo(nombre)
    except KeyError as e:
        raise HTTPException(404, str(e))

    record = db.query(Indicator).filter(
        Indicator.id_indicator == body.indicator_id,
        Indicator.org_id == user.org_id,
    ).first()
    if not record:
        raise HTTPException(404, "Indicador no encontrado")

    engine_type, _origen = resolver_engine_type(record)
    if not custom_reports.aplica_a(modulo, engine_type):
        permitidos = getattr(modulo, "ENGINE_TYPES", None) or []
        raise HTTPException(
            400,
            f"El informe '{nombre}' no aplica a este indicador "
            f"(tipo detectado: {engine_type or 'genérico'}). "
            f"Aplica a: {', '.join(permitidos) or '(ninguno)'}.",
        )

    meta = custom_reports.metadata(nombre, modulo)

    try:
        contenido = modulo.generar(
            db,
            indicator_id=body.indicator_id,
            org_id=user.org_id,
            filtros=body.filtros,
            params=body.params,
            overrides=body.overrides,
        )
    except TipoNoSoportado as e:
        raise HTTPException(404, str(e))
    except (DatosInsuficientes, ValueError) as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except HTTPException:
        raise
    except Exception:
        logger.error("Error generando informe custom '%s'", nombre, exc_info=True)
        raise HTTPException(500, "Error generando el informe")

    return Response(
        content=contenido,
        media_type=meta["mime"],
        headers={"Content-Disposition": content_disposition(meta["filename"])},
    )


# ─────────────────────────────────────────────────────────────────────────
# Generación de PDF (motor v2 — endpoint legacy por tipo)
# ─────────────────────────────────────────────────────────────────────────

@router.post("/{tipo}")
def generar_reporte(
    tipo: str,
    body: ReportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Genera el PDF para `tipo` (simce | simce_panguipulli | dia).

    Endpoint histórico: la lógica vive en
    `backend/rgenerator/reports/dispatch_v2.py`, compartida con los informes
    del registro `reports/custom/` (que es la vía nueva y preferida).

    Args:
        tipo: identificador del informe — coincide con el subdirectorio
            que tiene el esquema.json.
        body: { indicator_id, filtros?, overrides? }.

    Returns:
        application/pdf con el binario.

    Raises:
        404 si el tipo no existe.
        400 si falta el filtro temporal, o el indicator no se encuentra o
            no tiene las metrics requeridas.
        500 si la generación falla.
    """
    try:
        pdf_bytes = generar_pdf_v2(
            db,
            tipo=tipo,
            indicator_id=body.indicator_id,
            org_id=user.org_id,
            filtros=body.filtros,
            overrides=body.overrides,
        )
    except TipoNoSoportado as e:
        raise HTTPException(404, str(e))
    except (DatosInsuficientes, ValueError) as e:
        raise HTTPException(400, str(e))
    except Exception:
        logger.error("Error generando PDF de reporte", exc_info=True)
        raise HTTPException(500, "Error interno del servidor")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": content_disposition(f"informe_{tipo}.pdf", disposition="inline")},
    )
