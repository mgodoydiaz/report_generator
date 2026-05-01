import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Any, List, Optional, Dict
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user
from backend.models import User, Indicator, IndicatorMetric

router = APIRouter(prefix="/api/indicators", tags=["indicators"])


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
        "updated_at": ind.updated_at.strftime("%Y-%m-%d %H:%M:%S") if ind.updated_at else "",
        "metric_ids": metric_ids,
    }


# --- Endpoints ---

@router.get("/export-pdf/engines")
async def list_report_engines(
    user: User = Depends(get_current_user),
):
    """Lista los motores de informe PDF disponibles (para poblar el modal de generación)."""
    return REPORT_ENGINES


@router.get("/")
async def get_indicators(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        indicators = db.query(Indicator).filter(Indicator.org_id == user.org_id).all()
        return [_indicator_to_dict(i) for i in indicators]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_indicator(
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
            updated_at=datetime.utcnow(),
            org_id=user.org_id,
        )
        db.add(new_ind)
        db.flush()  # get id_indicator

        for mid in indicator.metric_ids:
            db.add(IndicatorMetric(id_indicator=new_ind.id_indicator, id_metric=mid))

        db.commit()
        db.refresh(new_ind)

        return {"status": "success", "data": _indicator_to_dict(new_ind)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{indicator_id}")
async def update_indicator(
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
        record.updated_at = datetime.utcnow()

        if indicator.metric_ids is not None:
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
        raise HTTPException(status_code=500, detail=str(e))


class LayoutUpsert(BaseModel):
    dashboard_layout: Optional[Dict[str, Any]] = None
    pdf_layout: Optional[Dict[str, Any]] = None
    pdf_layout_historico: Optional[Dict[str, Any]] = None


@router.post("/{indicator_id}/layout")
async def upsert_layout(
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{indicator_id}/export-pdf")
async def export_pdf(
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
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{indicator_id}")
async def delete_indicator(
    indicator_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        record = db.query(Indicator).filter(
            Indicator.id_indicator == indicator_id,
            Indicator.org_id == user.org_id,
        ).first()
        if record:
            db.delete(record)  # cascade deletes IndicatorMetric links
            db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
