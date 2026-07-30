import json
from datetime import date, datetime
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
    # Período declarativo: cuando viene, el backend resuelve los filtros
    # temporales contra los datos reales y IGNORA `tipo` (usa el tipo_layout
    # que corresponda al período). Ver rgenerator/reports/periodos.py.
    #   {"tipo": "ultima_prueba" | "semestral" | "anual" | "personalizado",
    #    "fecha_inicio": "YYYY-MM", "fecha_fin": "YYYY-MM",
    #    "filtros": {"Curso": ["1 A"]}}
    periodo: Optional[Dict[str, Any]] = None


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


# ─────────────────────────────────────────────────────────────────────────
# Catálogo de informes (report-options)
# ─────────────────────────────────────────────────────────────────────────

# Las 4 cards de período. `layout` indica qué pdf_layout necesitan:
#   "evaluacion" → pdf_layout.sections
#   "historico"  → pdf_layout_historico.sections
#   "cualquiera" → basta con uno de los dos
_CARDS_PERIODO = (
    {
        "id": "periodo_ultima_prueba",
        "tipo": "ultima_prueba",
        "label": "Informe última prueba",
        "layout": "evaluacion",
        "descripcion_base": "Última evaluación registrada",
        "descripcion_generica": "PDF de la evaluación más reciente registrada.",
    },
    {
        "id": "periodo_semestral",
        "tipo": "semestral",
        "label": "Informe semestral",
        "layout": "historico",
        "descripcion_base": "Evolución del",
        "descripcion_generica": "PDF con la evolución del semestre en curso.",
    },
    {
        "id": "periodo_anual",
        "tipo": "anual",
        "label": "Informe Anual",
        "layout": "historico",
        "descripcion_base": "Evolución del año",
        "descripcion_generica": "PDF con la evolución del año en curso.",
    },
    {
        "id": "periodo_personalizado",
        "tipo": "personalizado",
        "label": "Informe Personalizado",
        "layout": "cualquiera",
        "requiere_configuracion": True,
        "descripcion_generica": (
            "Elige el rango de fechas y los filtros del informe antes de generarlo."
        ),
    },
)

_MOTIVO_SIN_LAYOUT = {
    "evaluacion": (
        "Este informe aún no está configurado — pide a tu administrador que "
        "agregue secciones en Editor de Layout → Informe PDF → por evaluación."
    ),
    "historico": (
        "Este informe aún no está configurado — pide a tu administrador que "
        "agregue secciones en Editor de Layout → Informe PDF → histórico."
    ),
    "cualquiera": (
        "Este informe aún no está configurado — pide a tu administrador que "
        "agregue secciones en Editor de Layout → Informe PDF."
    ),
}

_MOTIVO_SIN_DATOS = "Sin datos cargados para este indicador."


def _cargar_dataframes_best_effort(db: Session, indicator_id: int, org_id: int):
    """(dataframes, error) — nunca levanta. `error` es el motivo legible."""
    try:
        from backend.rgenerator.reports.data import cargar_dataframes_indicator
        dfs = cargar_dataframes_indicator(
            db, indicator_id=indicator_id, org_id=org_id, filtros={}
        )
    except Exception:
        logger.info(
            "report-options: no se pudieron cargar datos del indicador %s",
            indicator_id, exc_info=True,
        )
        return {}, _MOTIVO_SIN_DATOS
    if not dfs:
        return {}, _MOTIVO_SIN_DATOS
    return dfs, None


def _dimensiones_del_indicador(db: Session, indicator_id: int, org_id: int) -> list:
    """Dimensiones asociadas a las metrics del indicador (ORM, filtradas por org)."""
    from backend.models import Dimension, MetricDimension

    metric_ids = [
        lnk.id_metric for lnk in db.query(IndicatorMetric).filter(
            IndicatorMetric.id_indicator == indicator_id
        ).all()
    ]
    if not metric_ids:
        return []
    metric_ids = [
        m.id_metric for m in db.query(Metric).filter(
            Metric.id_metric.in_(metric_ids), Metric.org_id == org_id
        ).all()
    ]
    if not metric_ids:
        return []
    dim_ids = {
        lnk.id_dimension for lnk in db.query(MetricDimension).filter(
            MetricDimension.id_metric.in_(metric_ids)
        ).all()
    }
    if not dim_ids:
        return []
    return db.query(Dimension).filter(
        Dimension.id_dimension.in_(dim_ids), Dimension.org_id == org_id
    ).all()


def _columna_de_dimension(nombre_dimension: str) -> str:
    """Nombre de columna que `data.py` genera para una dimensión ('Año', 'Curso')."""
    from backend.rgenerator.reports.data import _humanize_column, _to_field_name
    return _humanize_column(_to_field_name(nombre_dimension))


def _dimensiones_filtrables(db: Session, indicator_id: int, org_id: int,
                            dataframes: dict) -> list[dict]:
    """Dimensiones del indicador con sus valores únicos reales.

    Los valores salen de los DataFrames cargados (reflejan lo que hay en
    `metric_data`); si la dimensión no aparece como columna, se cae al
    catálogo `dimension_values`.
    """
    from backend.models import DimensionValue

    out: list[dict] = []
    for dim in _dimensiones_del_indicador(db, indicator_id, org_id):
        columna = _columna_de_dimension(dim.name)
        valores: list[str] = []
        for df in (dataframes or {}).values():
            if columna in getattr(df, "columns", []):
                crudos = df[columna].dropna().unique().tolist()
                valores.extend(str(v) for v in crudos if str(v) != "")
        if not valores:
            valores = [
                v.value for v in db.query(DimensionValue).filter(
                    DimensionValue.id_dimension == dim.id_dimension,
                    DimensionValue.is_active.is_(True),
                ).all()
            ]
        out.append({
            "id_dimension": dim.id_dimension,
            "name": dim.name,
            "values": sorted(set(valores), key=_orden_natural),
        })
    return out


def _orden_natural(valor: str):
    """Clave de orden alfanumérico natural ('1 A' < '2 A' < '10 A')."""
    import re
    partes = re.split(r"(\d+)", str(valor))
    return [int(p) if p.isdigit() else p.lower() for p in partes]


def _descripcion_card(card: dict, resultado) -> str:
    """Texto de la card con el período resuelto contra datos reales."""
    if resultado is None or not resultado.disponible or not resultado.descripcion:
        return card["descripcion_generica"]
    base = card.get("descripcion_base")
    if not base:
        return card["descripcion_generica"]
    if card["tipo"] == "ultima_prueba":
        return f"{base}: {resultado.descripcion}."
    return f"{base} {resultado.descripcion}."


@router.get("/{indicator_id}/report-options")
def report_options(
    indicator_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Catálogo de informes disponibles para el indicador.

    Fuente única para el selector de "Generar informe" del frontend.
    Respuesta:

        grupos.periodo         4 cards de período (última prueba, semestral,
                               anual, personalizado) resueltas contra los
                               datos reales del indicador.
        grupos.especializados  informes hardcodeados del registro
                               `reports/custom/` aplicables al engine_type,
                               más los informes Word.
        dimensiones_filtrables dimensiones del indicador con sus valores.
        opciones               concatenación plana de ambos grupos (compat).

    El `engine_type` sale de `report_engine_type` (fallback a heurística por
    nombre solo para retrocompatibilidad).
    """
    from backend.rgenerator.reports.engine_types import resolver_engine_type
    from backend.rgenerator.reports.periodos import resolver_periodo_multi

    record = db.query(Indicator).filter(
        Indicator.id_indicator == indicator_id,
        Indicator.org_id == user.org_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Indicador no encontrado")

    engine_type, origen = resolver_engine_type(record)

    layout_eval = _parse_json_field(record.pdf_layout, {})
    layout_hist = _parse_json_field(record.pdf_layout_historico, {})
    tiene = {
        "evaluacion": bool(layout_eval.get("sections")),
        "historico": bool(layout_hist.get("sections")),
    }
    tiene["cualquiera"] = tiene["evaluacion"] or tiene["historico"]

    dataframes, error_datos = _cargar_dataframes_best_effort(
        db, indicator_id, user.org_id
    )
    hoy = date.today()

    # ── Grupo "periodo" ──
    grupo_periodo: list[dict] = []
    for card in _CARDS_PERIODO:
        periodo = {"tipo": card["tipo"]}
        requiere_config = bool(card.get("requiere_configuracion"))

        resultado = None
        if not requiere_config and not error_datos:
            try:
                resultado = resolver_periodo_multi(dataframes, periodo, hoy)
            except Exception:
                logger.error(
                    "report-options: falló resolver_periodo (%s) del indicador %s",
                    card["tipo"], indicator_id, exc_info=True,
                )
                resultado = None

        motivo = None
        if not tiene[card["layout"]]:
            motivo = _MOTIVO_SIN_LAYOUT[card["layout"]]
        elif requiere_config:
            motivo = None
        elif error_datos:
            motivo = error_datos
        elif resultado is None:
            motivo = _MOTIVO_SIN_DATOS
        elif not resultado.disponible:
            motivo = resultado.motivo

        opcion = {
            "id": card["id"],
            "label": card["label"],
            "descripcion": _descripcion_card(card, resultado),
            "formato": "pdf",
            "motor": "weasyprint",
            "periodo": periodo,
            "tipo_layout": (
                resultado.tipo_layout if resultado is not None
                else ("historico" if card["layout"] == "historico" else "evaluacion")
            ),
            "disponible": motivo is None,
            "motivo_no_disponible": motivo,
            "invocacion": {
                "endpoint": f"/api/indicators/{indicator_id}/export-pdf",
                "params": {"periodo": periodo},
            },
        }
        if requiere_config:
            opcion["requiere_configuracion"] = True
        grupo_periodo.append(opcion)

    # ── Grupo "especializados": registro custom + informes Word ──
    especializados: list[dict] = []
    try:
        from backend.rgenerator.reports import custom as custom_reports
        for inf in custom_reports.informes_para(engine_type):
            especializados.append({
                "id": f"custom_{inf['nombre']}",
                "label": inf["label"],
                "descripcion": inf["descripcion"],
                "formato": inf["formato"],
                "motor": "custom",
                "nombre": inf["nombre"],
                "requiere_filtro_temporal": inf["requiere_filtro_temporal"],
                "disponible": True,
                "motivo_no_disponible": None,
                "invocacion": {
                    "endpoint": f"/api/reports/custom/{inf['nombre']}",
                    "params": {"indicator_id": indicator_id},
                },
            })
    except Exception:
        logger.error("No se pudieron listar informes custom para report-options", exc_info=True)

    try:
        from backend.rgenerator.reports import word as word_reports
        for inf in word_reports.listar_informes():
            disponible = bool(inf.get("plantilla_existe"))
            especializados.append({
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

    try:
        dimensiones = _dimensiones_filtrables(db, indicator_id, user.org_id, dataframes)
    except Exception:
        logger.error("No se pudieron listar dimensiones filtrables", exc_info=True)
        dimensiones = []

    return {
        "indicator_id": indicator_id,
        "engine_type": engine_type,
        "engine_type_origen": origen,
        "grupos": {
            "periodo": grupo_periodo,
            "especializados": especializados,
        },
        "dimensiones_filtrables": dimensiones,
        # Compat: lista plana con todas las opciones (consumidores viejos).
        "opciones": grupo_periodo + especializados,
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


def _mapa_columna_a_dimension(db: Session, indicator_id: int, org_id: int) -> Dict[str, int]:
    """{nombre_de_columna: id_dimension} para las dimensiones del indicador.

    `data.py` nombra las columnas de los DataFrames a partir del nombre de la
    dimensión (`_humanize_column(_to_field_name(dim.name))`). Este mapa hace
    el camino inverso, necesario porque `export-pdf` filtra por
    `{id_dimension: valor}` mientras el resolver de períodos devuelve
    `{nombre_columna: valor}`.
    """
    mapa: Dict[str, int] = {}
    for dim in _dimensiones_del_indicador(db, indicator_id, org_id):
        mapa.setdefault(_columna_de_dimension(dim.name), dim.id_dimension)
        mapa.setdefault(dim.name, dim.id_dimension)
    return mapa


def _resolver_periodo_a_filtros(
    db: Session, record: Indicator, org_id: int, periodo: Dict[str, Any]
) -> tuple:
    """(tipo_layout, {id_dimension: valores}, descripcion) para el `periodo`.

    La `descripcion` es el texto resuelto contra los datos reales
    ("DIAGNOSTICO 2026", "1er semestre 2026 (enero–julio)") y se usa para
    la última línea del encabezado del PDF, que en el layout persistido
    queda stale (QA 2026-07-30, P0-10).

    Raises:
        HTTPException 400: si el período no es resoluble (sin datos, sin
            dimensión temporal, sin datos del año/semestre) o si alguna
            columna resuelta no corresponde a una dimensión del indicador.
    """
    from backend.rgenerator.reports.periodos import resolver_periodo_multi

    dataframes, error_datos = _cargar_dataframes_best_effort(
        db, record.id_indicator, org_id
    )
    if error_datos:
        raise HTTPException(status_code=400, detail=error_datos)

    resultado = resolver_periodo_multi(dataframes, periodo, date.today())
    if not resultado.disponible:
        raise HTTPException(
            status_code=400,
            detail=resultado.motivo or "No se pudo resolver el período solicitado.",
        )

    mapa = _mapa_columna_a_dimension(db, record.id_indicator, org_id)
    faltantes = [c for c in resultado.filtros if c not in mapa]
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se pudo traducir el período a dimensiones del indicador: "
                f"{', '.join(faltantes)}. Revisa que esas dimensiones estén "
                "asociadas a las métricas del indicador."
            ),
        )

    filtros = {str(mapa[col]): valor for col, valor in resultado.filtros.items()}
    return resultado.tipo_layout, filtros, resultado.descripcion


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

    Body opcional `periodo`: cuando viene, el backend resuelve el período
    contra los datos reales (ver `rgenerator/reports/periodos.py`), IGNORA
    `tipo` (usa el `tipo_layout` resuelto) y aplica los filtros resueltos
    ADEMÁS de los de `filters`.
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
        filters = dict(body.filters) if (body and body.filters) else {}

        # ── Período declarativo: manda sobre `tipo` y agrega filtros ──
        periodo = body.periodo if body else None
        descripcion_periodo = ""
        if periodo:
            resuelto_tipo, filtros_periodo, descripcion_periodo = _resolver_periodo_a_filtros(
                db, record, user.org_id, periodo
            )
            tipo = resuelto_tipo
            filters.update(filtros_periodo)

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

        filters = filters or None
        branding_override = body.branding_override if body else None
        # El branding lo pidió el usuario explícitamente: nadie lo pisa
        # después (ni el `center_header` derivado del período).
        branding_es_del_usuario = bool(branding_override)
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

        # ── Última línea del encabezado = período resuelto ──
        # El `center_header` del layout es configuración editable del usuario y
        # su última línea (la del período) queda stale al cambiar de prueba
        # (QA 2026-07-30, P0-10: "Octubre 2025" con datos de DIAGNOSTICO 2026).
        # Solo se pisa esa línea, y solo si el usuario no mandó branding propio.
        if descripcion_periodo and not branding_es_del_usuario:
            from backend.rgenerator.reports.branding import reemplazar_ultima_linea
            header_actual = (pdf_layout.get("branding") or {}).get("center_header")
            header_nuevo = reemplazar_ultima_linea(header_actual, descripcion_periodo)
            if header_nuevo:
                branding_override = {"center_header": header_nuevo}

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
            from backend.rgenerator.reports.errores import DatosInsuficientes
            try:
                pdf_bytes = build_pdf_bytes(
                    record, db, user.org_id,
                    filters=filters,
                    branding_override=branding_override,
                    pdf_layout_override=pdf_layout,
                )
            except DatosInsuficientes as e:
                # Combinación de filtros sin datos: 400 accionable en vez de
                # un PDF con gráficos en blanco (QA 2026-07-30, P0-1).
                raise HTTPException(status_code=400, detail=str(e))
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
