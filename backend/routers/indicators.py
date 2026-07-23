import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Any, List, Optional, Dict
from sqlalchemy.orm import Session, selectinload

from backend.database import get_db
from backend.auth import get_current_user
from backend.logging_config import get_logger
from backend.models import User, Indicator, IndicatorMetric, Metric

logger = get_logger(__name__)

router = APIRouter(prefix="/api/indicators", tags=["indicators"])


def _validate_metric_ids(db: Session, metric_ids: List[int], org_id: int) -> None:
    """Verifica que todos los metric_ids existen y pertenecen a la org del usuario.

    Sin esta validación, un editor podría enlazar su indicador a métricas de otra
    organización (FKs cross-org) y verlas vía /api/results y /api/reports.
    """
    if not metric_ids:
        return
    unique_ids = set(metric_ids)
    valid = db.query(Metric.id_metric).filter(
        Metric.id_metric.in_(unique_ids),
        Metric.org_id == org_id,
    ).count()
    if valid != len(unique_ids):
        raise HTTPException(
            status_code=400,
            detail="Una o más métricas no existen o no pertenecen a tu organización.",
        )


# --- Models ---
class IndicatorBase(BaseModel):
    name: str
    description: Optional[str] = ""
    type: str = "Evaluación"
    column_roles: Optional[Dict[str, Any]] = None
    role_labels: Optional[Dict[str, str]] = None
    role_formats: Optional[Dict[str, str]] = None
    filter_dimensions: Optional[List[int]] = None
    temporal_config: Optional[Dict[str, Any]] = None
    achievement_levels: Optional[List[Any]] = None
    dashboard_layout: Optional[Dict[str, Any]] = None
    derived_columns: Optional[List[Dict[str, Any]]] = None
    pdf_layout: Optional[Dict[str, Any]] = None
    pdf_layout_historico: Optional[Dict[str, Any]] = None
    report_engine_type: Optional[str] = None  # simce | simce_panguipulli | dia | pdl_idel | None


class IndicatorCreate(IndicatorBase):
    metric_ids: List[int] = []


class IndicatorUpdate(IndicatorBase):
    metric_ids: Optional[List[int]] = None


class ExportPDFRequest(BaseModel):
    """Body opcional para POST /{id}/export-pdf."""
    filters: Optional[Dict[str, Any]] = None
    engine: Optional[str] = None                    # override del motor (default: pdf_layout.engine)
    branding_override: Optional[Dict[str, Any]] = None  # overrides ad‑hoc de branding
    save_as_default: bool = False                   # si True, persiste branding en pdf_layout
    tipo: Optional[str] = "evaluacion"              # "evaluacion" | "historico" — qué layout usar


# Motores de informe disponibles — expuesto al frontend para poblar el modal
REPORT_ENGINES = [
    {
        "id": "weasyprint",
        "label": "Layout del indicador",
        "description": "Genera el PDF a partir del pdf_layout configurado en el Editor de Layout.",
        "requires_sections": True,
        "available": True,
    },
    {
        "id": "pdl_idel",
        "label": "Informe PDL IDEL-Woodcock",
        "description": "Informe especializado multi-curso con matrices de transición (hardcodeado).",
        "requires_sections": False,
        "available": True,
    },
]


def _parse_json_field(value, default):
    """Safely parse a JSON text field returning default on failure."""
    if isinstance(value, str) and value:
        try:
            return json.loads(value)
        except Exception:
            return default
    if value is None:
        return default
    if isinstance(value, type(default)):
        return value
    return default


def _indicator_to_dict(ind: Indicator) -> dict:
    metric_ids = [lnk.id_metric for lnk in ind.metric_links]
    return {
        "id_indicator": ind.id_indicator,
        "name": ind.name,
        "description": ind.description or "",
        "type": ind.type or "Evaluación",
        "column_roles": _parse_json_field(ind.column_roles, {}),
        "role_labels": _parse_json_field(ind.role_labels, {}),
        "role_formats": _parse_json_field(ind.role_formats, {}),
        "filter_dimensions": _parse_json_field(ind.filter_dimensions, []),
        "temporal_config": _parse_json_field(ind.temporal_config, {}),
        "achievement_levels": _parse_json_field(ind.achievement_levels, []),
        "dashboard_layout": _parse_json_field(ind.dashboard_layout, {}),
        "derived_columns": _parse_json_field(ind.derived_columns, []),
        "pdf_layout": _parse_json_field(ind.pdf_layout, {}),
        "pdf_layout_historico": _parse_json_field(ind.pdf_layout_historico, {}),
        "report_engine_type": ind.report_engine_type,
        "updated_at": ind.updated_at.strftime("%Y-%m-%d %H:%M:%S") if ind.updated_at else "",
        "metric_ids": metric_ids,
    }


# Tipos que sirve el motor v2 (paridad LaTeX) — espejo de routers/reports.py
_V2_TIPOS = ("simce", "simce_panguipulli", "dia")
_V2_FILTROS_TEMPORALES = {
    "simce": ["Mes", "N Prueba", "Numero_Prueba"],
    "simce_panguipulli": ["Mes", "N Prueba", "Numero_Prueba"],
    "dia": ["Hito", "Año"],
}


def _inferir_engine_type(nombre: str) -> Optional[str]:
    """Fallback por nombre mientras el indicador no tenga report_engine_type.

    Misma heurística que usaba el frontend (Results.jsx) — se mantiene solo
    para retrocompatibilidad; la fuente de verdad es el campo explícito.
    """
    n = (nombre or "").lower()
    if "panguipulli" in n:
        return "simce_panguipulli"
    if "simce" in n:
        return "simce"
    if "dia" in n:
        return "dia"
    if "idel" in n or "pdl" in n:
        return "pdl_idel"
    return None


@router.get("/{indicator_id}/report-options")
def report_options(
    indicator_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Catálogo de informes disponibles para el indicador.

    Fuente única para el selector de "Generar informe" del frontend: cada
    opción dice formato, motor, si está disponible (y por qué no), y cómo
    invocarla. Los tipos especializados salen de `report_engine_type`
    (con fallback a heurística por nombre si el campo está vacío).
    """
    record = db.query(Indicator).filter(
        Indicator.id_indicator == indicator_id,
        Indicator.org_id == user.org_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Indicador no encontrado")

    engine_type = record.report_engine_type or None
    origen = "campo" if engine_type else None
    if not engine_type:
        engine_type = _inferir_engine_type(record.name)
        origen = "inferido" if engine_type else None

    layout_eval = _parse_json_field(record.pdf_layout, {})
    layout_hist = _parse_json_field(record.pdf_layout_historico, {})
    opciones = []

    tiene_eval = bool(layout_eval.get("sections"))
    opciones.append({
        "id": "pdf_evaluacion",
        "label": "Informe PDF — por evaluación",
        "descripcion": "PDF con el diseño configurado en el Editor de Layout, para un punto en el tiempo.",
        "formato": "pdf",
        "motor": "weasyprint",
        "disponible": tiene_eval,
        "motivo_no_disponible": None if tiene_eval else (
            "Este informe aún no está configurado — pide a tu administrador que "
            "agregue secciones en Editor de Layout → Informe PDF → por evaluación."
        ),
        "invocacion": {
            "endpoint": f"/api/indicators/{indicator_id}/export-pdf",
            "params": {"tipo": "evaluacion", "engine": "weasyprint"},
        },
    })

    tiene_hist = bool(layout_hist.get("sections"))
    opciones.append({
        "id": "pdf_historico",
        "label": "Informe PDF — histórico",
        "descripcion": "PDF con la evolución entre evaluaciones (diseño del Editor de Layout).",
        "formato": "pdf",
        "motor": "weasyprint",
        "disponible": tiene_hist,
        "motivo_no_disponible": None if tiene_hist else (
            "Este informe aún no está configurado — pide a tu administrador que "
            "agregue secciones en Editor de Layout → Informe PDF → histórico."
        ),
        "invocacion": {
            "endpoint": f"/api/indicators/{indicator_id}/export-pdf",
            "params": {"tipo": "historico", "engine": "weasyprint"},
        },
    })

    if engine_type == "pdl_idel":
        opciones.append({
            "id": "pdl_idel",
            "label": "Informe PDL IDEL-Woodcock",
            "descripcion": "Informe especializado multi-curso con matrices de transición.",
            "formato": "pdf",
            "motor": "pdl_idel",
            "disponible": True,
            "motivo_no_disponible": None,
            "invocacion": {
                "endpoint": f"/api/indicators/{indicator_id}/export-pdf",
                "params": {"engine": "pdl_idel"},
            },
        })

    if engine_type in _V2_TIPOS:
        opciones.append({
            "id": f"v2_{engine_type}",
            "label": f"Informe de evaluación {engine_type.replace('_', ' ').upper()} (formato oficial)",
            "descripcion": "PDF con el formato oficial de la evaluación. Requiere filtrar a un solo punto temporal.",
            "formato": "pdf",
            "motor": "v2",
            "tipo_v2": engine_type,
            "requiere_filtro_temporal": _V2_FILTROS_TEMPORALES[engine_type],
            "disponible": True,
            "motivo_no_disponible": None,
            "invocacion": {
                "endpoint": f"/api/reports/{engine_type}",
                "params": {"indicator_id": indicator_id},
            },
        })

    try:
        from backend.rgenerator.reports import word as word_reports
        for inf in word_reports.listar_informes():
            disponible = bool(inf.get("plantilla_existe"))
            opciones.append({
                "id": f"word_{inf['nombre']}",
                "label": f"Word — {inf.get('label') or inf['nombre']}",
                "descripcion": inf.get("descripcion") or "Documento Word editable generado desde plantilla.",
                "formato": "word",
                "motor": "docxtpl",
                "disponible": disponible,
                "motivo_no_disponible": None if disponible else "Falta la plantilla .docx en el servidor.",
                "invocacion": {
                    "endpoint": f"/api/reports/word/{inf['nombre']}",
                    "params": {"indicator_id": indicator_id},
                },
            })
    except Exception:
        logger.error("No se pudieron listar informes Word para report-options", exc_info=True)

    return {
        "indicator_id": indicator_id,
        "engine_type": engine_type,
        "engine_type_origen": origen,
        "opciones": opciones,
    }


# --- Endpoints ---

@router.get("/export-pdf/engines")
def list_report_engines(
    user: User = Depends(get_current_user),
):
    """Lista los motores de informe PDF disponibles (para poblar el modal de generación)."""
    return REPORT_ENGINES


@router.get("/")
def get_indicators(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # selectinload evita N+1: en vez de 1 query por indicador para leer
        # metric_links (lazy load dentro de _indicator_to_dict), trae todos
        # los links en una segunda query con WHERE id_indicator IN (...).
        indicators = (
            db.query(Indicator)
            .options(selectinload(Indicator.metric_links))
            .filter(Indicator.org_id == user.org_id)
            .all()
        )
        return [_indicator_to_dict(i) for i in indicators]
    except Exception as e:
        logger.error("Error interno no controlado en router de indicators", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/")
def create_indicator(
    indicator: IndicatorCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        new_ind = Indicator(
            name=indicator.name,
            description=indicator.description or "",
            type=indicator.type,
            column_roles=json.dumps(indicator.column_roles or {}, ensure_ascii=False),
            role_labels=json.dumps(indicator.role_labels or {}, ensure_ascii=False),
            role_formats=json.dumps(indicator.role_formats or {}, ensure_ascii=False),
            filter_dimensions=json.dumps(indicator.filter_dimensions or [], ensure_ascii=False),
            temporal_config=json.dumps(indicator.temporal_config or {}, ensure_ascii=False),
            achievement_levels=json.dumps(indicator.achievement_levels or [], ensure_ascii=False),
            dashboard_layout=json.dumps(indicator.dashboard_layout or {}, ensure_ascii=False),
            derived_columns=json.dumps(indicator.derived_columns or [], ensure_ascii=False),
            pdf_layout=json.dumps(indicator.pdf_layout or {}, ensure_ascii=False),
            pdf_layout_historico=json.dumps(indicator.pdf_layout_historico or {}, ensure_ascii=False),
            report_engine_type=indicator.report_engine_type,
            updated_at=datetime.utcnow(),
            org_id=user.org_id,
        )
        _validate_metric_ids(db, indicator.metric_ids, user.org_id)

        db.add(new_ind)
        db.flush()  # get id_indicator

        for mid in indicator.metric_ids:
            db.add(IndicatorMetric(id_indicator=new_ind.id_indicator, id_metric=mid))

        db.commit()
        db.refresh(new_ind)

        return {"status": "success", "data": _indicator_to_dict(new_ind)}
    except HTTPException:
        # Re-raise HTTPException intactas (ej 400 de _validate_metric_ids)
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error interno no controlado en router de indicators", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.put("/{indicator_id}")
def update_indicator(
    indicator_id: int,
    indicator: IndicatorUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        record = db.query(Indicator).filter(
            Indicator.id_indicator == indicator_id,
            Indicator.org_id == user.org_id,
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="Indicador no encontrado")

        record.name = indicator.name
        if indicator.description is not None:
            record.description = indicator.description
        record.type = indicator.type
        if indicator.column_roles is not None:
            record.column_roles = json.dumps(indicator.column_roles, ensure_ascii=False)
        if indicator.role_labels is not None:
            record.role_labels = json.dumps(indicator.role_labels, ensure_ascii=False)
        if indicator.role_formats is not None:
            record.role_formats = json.dumps(indicator.role_formats, ensure_ascii=False)
        if indicator.filter_dimensions is not None:
            record.filter_dimensions = json.dumps(indicator.filter_dimensions, ensure_ascii=False)
        if indicator.temporal_config is not None:
            record.temporal_config = json.dumps(indicator.temporal_config, ensure_ascii=False)
        if indicator.achievement_levels is not None:
            record.achievement_levels = json.dumps(indicator.achievement_levels, ensure_ascii=False)
        if indicator.dashboard_layout is not None:
            record.dashboard_layout = json.dumps(indicator.dashboard_layout, ensure_ascii=False)
        if indicator.derived_columns is not None:
            record.derived_columns = json.dumps(indicator.derived_columns, ensure_ascii=False)
        if indicator.pdf_layout is not None:
            record.pdf_layout = json.dumps(indicator.pdf_layout, ensure_ascii=False)
        if indicator.pdf_layout_historico is not None:
            record.pdf_layout_historico = json.dumps(indicator.pdf_layout_historico, ensure_ascii=False)
        if indicator.report_engine_type is not None:
            # "" explícito limpia el campo (vuelve a genérico)
            record.report_engine_type = indicator.report_engine_type or None
        record.updated_at = datetime.utcnow()

        if indicator.metric_ids is not None:
            _validate_metric_ids(db, indicator.metric_ids, user.org_id)
            # Delete previous relations
            db.query(IndicatorMetric).filter(
                IndicatorMetric.id_indicator == indicator_id
            ).delete(synchronize_session=False)
            # Insert new
            for mid in indicator.metric_ids:
                db.add(IndicatorMetric(id_indicator=indicator_id, id_metric=mid))

        db.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error interno no controlado en router de indicators", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


class LayoutUpsert(BaseModel):
    dashboard_layout: Optional[Dict[str, Any]] = None
    pdf_layout: Optional[Dict[str, Any]] = None
    pdf_layout_historico: Optional[Dict[str, Any]] = None


@router.post("/{indicator_id}/layout")
def upsert_layout(
    indicator_id: int,
    body: LayoutUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Actualiza dashboard_layout, pdf_layout y/o pdf_layout_historico de un
    indicador en una sola request. Solo actualiza los campos que se pasan
    (los omitidos no se tocan)."""
    record = db.query(Indicator).filter(
        Indicator.id_indicator == indicator_id,
        Indicator.org_id == user.org_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Indicador no encontrado")

    try:
        from datetime import datetime
        if body.dashboard_layout is not None:
            record.dashboard_layout = json.dumps(body.dashboard_layout, ensure_ascii=False)
        if body.pdf_layout is not None:
            record.pdf_layout = json.dumps(body.pdf_layout, ensure_ascii=False)
        if body.pdf_layout_historico is not None:
            record.pdf_layout_historico = json.dumps(body.pdf_layout_historico, ensure_ascii=False)
        record.updated_at = datetime.utcnow()
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        logger.error("Error interno no controlado en router de indicators", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/{indicator_id}/export-pdf")
def export_pdf(
    indicator_id: int,
    body: Optional[ExportPDFRequest] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Genera y descarga el informe PDF del indicador.

    Dispatcher por motor (clave pdf_layout.engine):
      - "weasyprint" (default): usa build_pdf_bytes con las secciones configuradas.
      - "pdl_idel": reservado para el informe PDL IDEL-Woodcock (Fase B).

    Body opcional: { "filters": { "<id_dimension>": "<valor>", ... } }
    Los filtros se propagan a los MetricData antes de renderizar, de modo que
    el PDF refleje la misma vista que el usuario tiene en la página Results.
    """
    try:
        record = db.query(Indicator).filter(
            Indicator.id_indicator == indicator_id,
            Indicator.org_id == user.org_id,
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="Indicador no encontrado")

        # Tipo de informe (default "evaluacion" para retrocompat)
        tipo = (body.tipo if body else "evaluacion") or "evaluacion"
        if tipo not in ("evaluacion", "historico"):
            raise HTTPException(
                status_code=422,
                detail=f"tipo='{tipo}' inválido. Usa 'evaluacion' o 'historico'."
            )

        # Resolver el layout según el tipo
        if tipo == "historico":
            pdf_layout = _parse_json_field(record.pdf_layout_historico, {})
        else:
            pdf_layout = _parse_json_field(record.pdf_layout, {})

        filters = body.filters if body else None
        branding_override = body.branding_override if body else None
        save_as_default = bool(body.save_as_default) if body else False
        engine_override = body.engine if body else None

        # Precedencia del engine: override del modal > pdf_layout.engine > default weasyprint
        engine = (engine_override or pdf_layout.get("engine") or "weasyprint").lower()

        # Validar que el engine esté disponible
        engine_meta = next((e for e in REPORT_ENGINES if e["id"] == engine), None)
        if not engine_meta or not engine_meta.get("available"):
            valid = [e["id"] for e in REPORT_ENGINES if e.get("available")]
            raise HTTPException(
                status_code=422,
                detail=f"Motor de informe '{engine}' no disponible. "
                       f"Valores válidos: {', '.join(valid)}."
            )

        # Persistir branding como default del indicador (opt‑in vía checkbox del modal).
        # Se persiste en el campo correspondiente al tipo activo (evaluacion o historico).
        if save_as_default and branding_override:
            try:
                merged = dict(pdf_layout)
                merged['branding'] = {**(pdf_layout.get('branding') or {}), **branding_override}
                target_field = "pdf_layout_historico" if tipo == "historico" else "pdf_layout"
                setattr(record, target_field, json.dumps(merged, ensure_ascii=False))
                record.updated_at = datetime.utcnow()
                db.commit()
                # Refrescar pdf_layout local para que el render vea lo guardado
                pdf_layout = merged
                branding_override = None
            except Exception:
                db.rollback()
                raise

        if engine == "weasyprint":
            if not pdf_layout.get("sections"):
                modo_label = "histórico" if tipo == "historico" else "por evaluación"
                raise HTTPException(
                    status_code=422,
                    detail=f"El indicador no tiene secciones configuradas para el informe "
                           f"{modo_label}. Agrega secciones en el Editor de Layout → "
                           f"pestaña Informe PDF → {modo_label}."
                )
            from backend.rgenerator.core.report_steps import build_pdf_bytes
            pdf_bytes = build_pdf_bytes(
                record, db, user.org_id,
                filters=filters,
                branding_override=branding_override,
                pdf_layout_override=pdf_layout,
            )
        elif engine == "pdl_idel":
            from backend.rgenerator.tooling.report_pdl_idel_tools import build_pdl_idel_pdf_bytes
            try:
                pdf_bytes = build_pdl_idel_pdf_bytes(
                    record, db, user.org_id, filters=filters,
                )
            except ValueError as e:
                # Sin datos tras aplicar filtros — feedback accionable al usuario.
                raise HTTPException(status_code=422, detail=str(e))
        else:
            raise HTTPException(
                status_code=501,
                detail=f"Motor '{engine}' aún no implementado."
            )

        safe_name = record.name.replace(" ", "_").replace("/", "-")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="informe_{safe_name}.pdf"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error interno no controlado en router de indicators", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.delete("/{indicator_id}")
def delete_indicator(
    indicator_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        record = db.query(Indicator).filter(
            Indicator.id_indicator == indicator_id,
            Indicator.org_id == user.org_id,
        ).first()
        if not record:
            # 404 también si pertenece a otra org (no revelar existencia).
            raise HTTPException(status_code=404, detail="Indicador no encontrado")
        db.delete(record)  # cascade deletes IndicatorMetric links
        db.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error interno no controlado en router de indicators", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
