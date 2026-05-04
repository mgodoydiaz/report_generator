"""Router /api/tables — CRUD de tablas configurables (B7).

Cada tabla vive como un Spec con type='Tablas'. El campo `tables_list`
del Spec contiene un array con UN único TableConfig (1 spec = 1 tabla).
Esto mantiene la simetría con specs de Reportes/Gráficos.

Endpoints:
    GET    /api/tables/                 lista resumen (sidebar)
    POST   /api/tables/                 crear
    GET    /api/tables/{id}             leer detalle (config completa)
    PUT    /api/tables/{id}             actualizar
    DELETE /api/tables/{id}             borrar
    POST   /api/tables/{id}/duplicate   clonar
    GET    /api/tables/{id}/data        preview con datos reales formateados
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Indicator, Metric, MetricData, MetricDimension, Dimension, Spec, User
from backend.schemas_table import TableConfig, TableCreate, TableSummary, TableUpdate

router = APIRouter(prefix="/api/tables", tags=["tables"])


SPEC_TYPE = "Tablas"


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _now_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _parse_meta(spec: Spec) -> Dict[str, Any]:
    try:
        return json.loads(spec.metadata_ or "{}")
    except Exception:
        return {}


def _parse_tables_list(spec: Spec) -> List[Dict[str, Any]]:
    try:
        return json.loads(spec.tables_list or "[]")
    except Exception:
        return []


def _spec_to_summary(spec: Spec) -> TableSummary:
    meta = _parse_meta(spec)
    tables = _parse_tables_list(spec)
    cfg = tables[0] if tables else {}
    cols = cfg.get("columns") or []
    ds = cfg.get("data_source") or {}
    return TableSummary(
        id_spec=spec.id_spec,
        name=spec.name,
        description=meta.get("description", ""),
        is_draft=meta.get("is_draft", True),
        metric_id=ds.get("metric_id"),
        n_columns=len(cols),
        updated_at=meta.get("updated_at", ""),
    )


def _spec_to_full(spec: Spec) -> Dict[str, Any]:
    meta = _parse_meta(spec)
    tables = _parse_tables_list(spec)
    return {
        "id_spec": spec.id_spec,
        "name": spec.name,
        "description": meta.get("description", ""),
        "is_draft": meta.get("is_draft", True),
        "updated_at": meta.get("updated_at", ""),
        "config": tables[0] if tables else None,
    }


def _get_spec_or_404(db: Session, table_id: int, org_id: int) -> Spec:
    spec = db.query(Spec).filter(
        Spec.id_spec == table_id,
        Spec.org_id == org_id,
        Spec.type == SPEC_TYPE,
    ).first()
    if not spec:
        raise HTTPException(status_code=404, detail=f"Tabla {table_id} no encontrada")
    return spec


# ─────────────────────────────────────────────────────────────────────────
# Carga de datos (compartido con LoadMetricToDF, aplicado al preview)
# ─────────────────────────────────────────────────────────────────────────


def _load_metric_to_df(db: Session, org_id: int, metric_id: int,
                       filters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Carga metric_data + dimensiones a DataFrame plano, aplicando filtros
    por igualdad simple sobre nombres de dimensiones.

    Es una versión inline de la lógica que vive en
    `rgenerator/core/metric_steps.py:LoadMetricToDF` — replicada acá
    para que el endpoint /data no dependa de instanciar steps.
    """
    metric = db.query(Metric).filter(
        Metric.id_metric == metric_id,
        Metric.org_id == org_id,
    ).first()
    if not metric:
        raise HTTPException(status_code=404, detail=f"Métrica {metric_id} no encontrada")

    dim_links = db.query(MetricDimension).filter(MetricDimension.id_metric == metric_id).all()
    dim_ids = [lnk.id_dimension for lnk in dim_links]
    dims = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all() if dim_ids else []
    dims_map = {d.id_dimension: d.name for d in dims}

    rows = db.query(MetricData).filter(MetricData.id_metric == metric_id).all()

    flat: List[Dict[str, Any]] = []
    for r in rows:
        item: Dict[str, Any] = {}
        # Dimensiones
        try:
            dims_json = json.loads(r.dimensions_json) if isinstance(r.dimensions_json, str) else (r.dimensions_json or {})
        except Exception:
            dims_json = {}
        for dim_id, name in dims_map.items():
            item[name] = dims_json.get(str(dim_id))
        # Valor (object → expandido a fields, simple → 1 columna)
        meta = json.loads(metric.meta_json or "{}") if isinstance(metric.meta_json, str) else (metric.meta_json or {})
        val = r.value
        if metric.data_type == "object":
            try:
                val_obj = json.loads(val) if isinstance(val, str) else val
            except Exception:
                val_obj = {}
            for f in meta.get("fields", []):
                fname = f["name"]
                item[fname] = val_obj.get(fname)
        else:
            try:
                if metric.data_type == "int":
                    item[metric.name] = int(val)
                elif metric.data_type == "float":
                    item[metric.name] = float(val)
                else:
                    item[metric.name] = val
            except Exception:
                item[metric.name] = val
        flat.append(item)

    df = pd.DataFrame(flat)

    # Filtros por igualdad
    if filters:
        for col, val in filters.items():
            if col in df.columns:
                df = df[df[col].astype(str) == str(val)]

    return df


def _apply_format(value: Any, fmt: str, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if fmt == "int":
        try:
            return f"{int(value)}"
        except (ValueError, TypeError):
            return str(value)
    if fmt == "float":
        try:
            return f"{float(value):.{decimals}f}"
        except (ValueError, TypeError):
            return str(value)
    if fmt == "percent":
        try:
            return f"{float(value) * 100:.{decimals}f}%"
        except (ValueError, TypeError):
            return str(value)
    if fmt == "date":
        return str(value)
    return str(value)


def _resolve_color_for_value(value: Any, color_scale: Dict[str, Any],
                              row: Dict[str, Any], indicator_levels_cache: Dict[int, list]) -> Optional[str]:
    """Devuelve color hex para una celda según el color_scale."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    kind = color_scale.get("kind")
    if kind == "linked_indicator":
        ind_id = color_scale.get("indicator_id")
        level_field = color_scale.get("level_field")
        levels = indicator_levels_cache.get(ind_id, [])
        if not level_field or not levels:
            return None
        level_name = row.get(level_field)
        if not level_name:
            return None
        for lvl in levels:
            if str(lvl.get("name", "")).lower() == str(level_name).lower():
                return lvl.get("color")
    elif kind == "diverging":
        try:
            v = float(value)
        except (ValueError, TypeError):
            return None
        mp = float(color_scale.get("midpoint", 0))
        if v < mp:
            return color_scale.get("min_color")
        if v > mp:
            return color_scale.get("max_color")
        return color_scale.get("neutral_color")
    elif kind == "sequential":
        return color_scale.get("base_color")
    return None


def _load_indicator_levels(db: Session, org_id: int, indicator_ids: List[int]) -> Dict[int, list]:
    """Cache: {id_indicator: [{name, color, order}]}."""
    if not indicator_ids:
        return {}
    inds = db.query(Indicator).filter(
        Indicator.id_indicator.in_(indicator_ids),
        Indicator.org_id == org_id,
    ).all()
    out: Dict[int, list] = {}
    for ind in inds:
        try:
            levels = json.loads(ind.achievement_levels or "[]")
        except Exception:
            levels = []
        out[ind.id_indicator] = levels
    return out


# ─────────────────────────────────────────────────────────────────────────
# CRUD endpoints
# ─────────────────────────────────────────────────────────────────────────


@router.get("/", response_model=List[TableSummary])
async def list_tables(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    specs = db.query(Spec).filter(Spec.org_id == user.org_id, Spec.type == SPEC_TYPE).order_by(Spec.id_spec.desc()).all()
    return [_spec_to_summary(s) for s in specs]


@router.post("/")
async def create_table(
    payload: TableCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    meta = {
        "description": payload.description,
        "is_draft": payload.is_draft,
        "updated_at": _now_str(),
    }
    spec = Spec(
        name=payload.name,
        type=SPEC_TYPE,
        metadata_=json.dumps(meta, ensure_ascii=False),
        charts_list="[]",
        tables_list=json.dumps([payload.config.model_dump()], ensure_ascii=False),
        org_id=user.org_id,
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return {"status": "success", "id_spec": spec.id_spec}


@router.get("/{table_id}")
async def get_table(
    table_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, table_id, user.org_id)
    return _spec_to_full(spec)


@router.put("/{table_id}")
async def update_table(
    table_id: int,
    payload: TableUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, table_id, user.org_id)
    meta = _parse_meta(spec)
    if payload.name is not None:
        spec.name = payload.name
    if payload.description is not None:
        meta["description"] = payload.description
    if payload.is_draft is not None:
        meta["is_draft"] = payload.is_draft
    if payload.config is not None:
        spec.tables_list = json.dumps([payload.config.model_dump()], ensure_ascii=False)
    meta["updated_at"] = _now_str()
    spec.metadata_ = json.dumps(meta, ensure_ascii=False)
    db.commit()
    db.refresh(spec)
    return {"status": "success", "id_spec": spec.id_spec}


@router.delete("/{table_id}")
async def delete_table(
    table_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, table_id, user.org_id)
    db.delete(spec)
    db.commit()
    return {"status": "success", "message": f"Tabla {table_id} eliminada"}


@router.post("/{table_id}/duplicate")
async def duplicate_table(
    table_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, table_id, user.org_id)
    new = Spec(
        name=spec.name + " (Copia)",
        type=spec.type,
        metadata_=spec.metadata_,
        charts_list=spec.charts_list,
        tables_list=spec.tables_list,
        org_id=spec.org_id,
    )
    db.add(new)
    db.commit()
    db.refresh(new)
    return {"status": "success", "id_spec": new.id_spec}


# ─────────────────────────────────────────────────────────────────────────
# Preview de datos
# ─────────────────────────────────────────────────────────────────────────


def _render_table_data(
    db: Session, org_id: int, cfg: TableConfig,
    limit: int, offset: int, include_styles: bool,
    extra_filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Aplica el pipeline completo (filtros → grouping → sort → format → color)
    sobre una TableConfig y devuelve la respuesta estandar `{columns, rows, total_rows, limit, offset}`.

    Compartido por GET /{id}/data (config persistida) y POST /preview
    (config draft sin persistir, pensado para el editor live).
    """
    base_filters = dict(cfg.data_source.filters)
    if extra_filters:
        base_filters.update(extra_filters)

    df = _load_metric_to_df(db, org_id, cfg.data_source.metric_id, base_filters)

    # Grouping
    if cfg.behavior.grouping:
        gb = cfg.behavior.grouping.by
        if gb in df.columns:
            agg_map = {}
            for c in cfg.columns:
                if c.key == gb or c.key not in df.columns:
                    continue
                if c.agg:
                    agg_map[c.key] = c.agg
            if agg_map:
                df = df.groupby(gb, as_index=False).agg(agg_map)

    # Sort
    for s in cfg.behavior.sorting:
        if s.column in df.columns:
            df = df.sort_values(by=s.column, ascending=(s.dir == "asc"))

    total_rows = len(df)
    df_page = df.iloc[offset: offset + limit].copy()

    # Color scales — pre-cargar achievement_levels de indicadores referenciados
    indicator_ids = [
        c.color_scale.indicator_id for c in cfg.columns
        if c.color_scale and c.color_scale.kind == "linked_indicator"
    ]
    indicator_levels_cache = _load_indicator_levels(db, org_id, list(set(indicator_ids))) if indicator_ids else {}

    columns_meta = [
        {"key": c.key, "header": c.header, "format": c.format,
         "pinned": c.pinned, "width": c.width}
        for c in cfg.columns if not c.hidden
    ]

    rows_out = []
    for _, row in df_page.iterrows():
        row_obj: Dict[str, Any] = {}
        for c in cfg.columns:
            if c.hidden:
                continue
            raw = row.get(c.key) if c.key in df_page.columns else None
            cell: Dict[str, Any] = {
                "raw": None if (isinstance(raw, float) and pd.isna(raw)) else raw,
                "formatted": _apply_format(raw, c.format, c.decimals),
            }
            if include_styles and c.color_scale:
                color = _resolve_color_for_value(raw, c.color_scale.model_dump(), row.to_dict(), indicator_levels_cache)
                if color:
                    cell["color"] = color
            row_obj[c.key] = cell
        rows_out.append(row_obj)

    return {
        "columns": columns_meta,
        "rows": rows_out,
        "total_rows": total_rows,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{table_id}/data")
async def get_table_data(
    table_id: int,
    limit: int = Query(50, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    include_styles: bool = Query(True),
    extra_filters: Optional[str] = Query(None, description="JSON dict con filtros adicionales (encoded)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Devuelve datos formateados de una tabla persistida."""
    spec = _get_spec_or_404(db, table_id, user.org_id)
    tables = _parse_tables_list(spec)
    if not tables:
        raise HTTPException(status_code=400, detail="Tabla sin configuración")
    try:
        cfg = TableConfig(**tables[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Config inválida: {e}")

    extra: Optional[Dict[str, Any]] = None
    if extra_filters:
        try:
            extra = json.loads(extra_filters)
        except Exception:
            extra = None
    return _render_table_data(db, user.org_id, cfg, limit, offset, include_styles, extra)


class TablePreviewRequest(BaseModel):
    config: TableConfig
    limit: int = 50
    offset: int = 0
    include_styles: bool = True
    extra_filters: Optional[Dict[str, Any]] = None


@router.post("/preview")
async def preview_table_config(
    payload: "TablePreviewRequest",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Igual que /{id}/data pero recibe la config en body (no requiere
    que la tabla esté persistida). Pensado para el editor live."""
    return _render_table_data(
        db, user.org_id, payload.config,
        payload.limit, payload.offset, payload.include_styles,
        payload.extra_filters,
    )
