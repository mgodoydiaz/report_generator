"""Router /api/charts — CRUD de gráficos configurables (B8).

Cada gráfico vive como un Spec con type='Gráficos' y una entrada en
charts_list[0]. Patrón análogo a B7 (/api/tables sobre Spec.tables_list).

Endpoints:
    GET    /api/charts/                 lista resumen
    POST   /api/charts/                 crear
    GET    /api/charts/{id}             leer detalle
    PUT    /api/charts/{id}             actualizar
    DELETE /api/charts/{id}             borrar
    POST   /api/charts/{id}/duplicate   clonar
    GET    /api/charts/{id}/data        preview con dataset agregado
    POST   /api/charts/preview          preview con config en body (sin persistir)
    GET    /api/charts/types            metadata de los tipos disponibles
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
from backend.models import Spec, User
from backend.schemas_chart import (
    CHART_TYPE_META,
    ChartConfig,
    ChartCreate,
    ChartSummary,
    ChartUpdate,
)
# Reutilizamos el helper de carga de tabla — la lógica de cargar
# metric_data + filters es idéntica.
from backend.routers.tables import _load_metric_to_df

router = APIRouter(prefix="/api/charts", tags=["charts"])


SPEC_TYPE = "Gráficos"


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


def _parse_charts_list(spec: Spec) -> List[Dict[str, Any]]:
    try:
        return json.loads(spec.charts_list or "[]")
    except Exception:
        return []


def _spec_to_summary(spec: Spec) -> ChartSummary:
    meta = _parse_meta(spec)
    charts = _parse_charts_list(spec)
    cfg = charts[0] if charts else {}
    ds = cfg.get("data_source") or {}
    return ChartSummary(
        id_spec=spec.id_spec,
        name=spec.name,
        description=meta.get("description", ""),
        is_draft=meta.get("is_draft", True),
        chart_type=cfg.get("chart_type"),
        metric_id=ds.get("metric_id"),
        updated_at=meta.get("updated_at", ""),
    )


def _spec_to_full(spec: Spec) -> Dict[str, Any]:
    meta = _parse_meta(spec)
    charts = _parse_charts_list(spec)
    return {
        "id_spec": spec.id_spec,
        "name": spec.name,
        "description": meta.get("description", ""),
        "is_draft": meta.get("is_draft", True),
        "updated_at": meta.get("updated_at", ""),
        "config": charts[0] if charts else None,
    }


def _get_spec_or_404(db: Session, chart_id: int, org_id: int) -> Spec:
    spec = db.query(Spec).filter(
        Spec.id_spec == chart_id,
        Spec.org_id == org_id,
        Spec.type == SPEC_TYPE,
    ).first()
    if not spec:
        raise HTTPException(status_code=404, detail=f"Gráfico {chart_id} no encontrado")
    return spec


# ─────────────────────────────────────────────────────────────────────────
# Construcción del dataset según chart_type
# ─────────────────────────────────────────────────────────────────────────


def _build_dataset(df: pd.DataFrame, cfg: ChartConfig) -> Dict[str, Any]:
    """Aplica groupby + agg según el chart_type y devuelve un dataset
    serializado JSON-friendly que el frontend pueda consumir directo.

    Estructura del dataset según tipo:
        bar/box/line:
            {x: [...], y: [...]}
        grouped_bar/heatmap:
            {x: [...], series: [{name, y: [...]}, ...]}
        stacked_bar:
            {x: [...], stacks: [{name, y: [...]}, ...]}
        pie:
            {labels: [...], values: [...]}
        histogram:
            {values: [...]}
        radar:
            {axes: [...], series: [{name, values: [...]}, ...]}
        gauge:
            {value: float}
    """
    m = cfg.mapping
    agg = m.aggregation
    ct = cfg.chart_type

    if df.empty:
        return {"empty": True}

    if ct == "bar":
        if not m.x_field or not m.y_field:
            raise ValueError("bar requiere x_field y y_field")
        if m.x_field not in df.columns or m.y_field not in df.columns:
            return {"empty": True}
        g = df.groupby(m.x_field, as_index=False)[m.y_field].agg(agg)
        return {"x": g[m.x_field].astype(str).tolist(), "y": g[m.y_field].tolist()}

    if ct == "grouped_bar":
        if not (m.x_field and m.y_field and m.group_field):
            raise ValueError("grouped_bar requiere x_field, y_field y group_field")
        if any(c not in df.columns for c in [m.x_field, m.y_field, m.group_field]):
            return {"empty": True}
        g = df.groupby([m.x_field, m.group_field], as_index=False)[m.y_field].agg(agg)
        x_vals = g[m.x_field].astype(str).unique().tolist()
        series = []
        for name in g[m.group_field].astype(str).unique():
            sub = g[g[m.group_field].astype(str) == name].set_index(m.x_field)[m.y_field]
            y_vals = [sub.get(x, None) for x in x_vals]
            series.append({"name": str(name), "y": y_vals})
        return {"x": x_vals, "series": series}

    if ct == "stacked_bar":
        if not (m.x_field and m.stack_field):
            raise ValueError("stacked_bar requiere x_field y stack_field")
        if any(c not in df.columns for c in [m.x_field, m.stack_field]):
            return {"empty": True}
        # Stacked = count por (x, stack)
        g = df.groupby([m.x_field, m.stack_field], as_index=False).size()
        g = g.rename(columns={"size": "_n"})
        x_vals = g[m.x_field].astype(str).unique().tolist()
        order = cfg.aesthetics.stack_order or g[m.stack_field].astype(str).unique().tolist()
        stacks = []
        for name in order:
            sub = g[g[m.stack_field].astype(str) == str(name)].set_index(m.x_field)["_n"]
            y_vals = [int(sub.get(x, 0)) for x in x_vals]
            stacks.append({"name": str(name), "y": y_vals})
        return {"x": x_vals, "stacks": stacks}

    if ct == "box":
        if not (m.x_field and m.y_field):
            raise ValueError("box requiere x_field y y_field")
        if any(c not in df.columns for c in [m.x_field, m.y_field]):
            return {"empty": True}
        # Box necesita los valores crudos por categoría
        out = {"x": [], "y_arrays": []}
        for cat, sub in df.groupby(m.x_field):
            out["x"].append(str(cat))
            out["y_arrays"].append(sub[m.y_field].dropna().tolist())
        return out

    if ct == "line":
        if not (m.x_field and m.y_field):
            raise ValueError("line requiere x_field y y_field")
        if m.group_field:
            if any(c not in df.columns for c in [m.x_field, m.y_field, m.group_field]):
                return {"empty": True}
            g = df.groupby([m.x_field, m.group_field], as_index=False)[m.y_field].agg(agg)
            x_vals = sorted(g[m.x_field].astype(str).unique().tolist())
            series = []
            for name in g[m.group_field].astype(str).unique():
                sub = g[g[m.group_field].astype(str) == name].set_index(m.x_field)[m.y_field]
                series.append({"name": str(name), "y": [sub.get(x, None) for x in x_vals]})
            return {"x": x_vals, "series": series}
        else:
            if any(c not in df.columns for c in [m.x_field, m.y_field]):
                return {"empty": True}
            g = df.groupby(m.x_field, as_index=False)[m.y_field].agg(agg)
            return {"x": g[m.x_field].astype(str).tolist(), "y": g[m.y_field].tolist()}

    if ct == "pie":
        cat = m.category_field or m.x_field
        if not cat or cat not in df.columns:
            raise ValueError("pie requiere category_field")
        if m.y_field and m.y_field in df.columns:
            g = df.groupby(cat, as_index=False)[m.y_field].agg(agg)
            return {"labels": g[cat].astype(str).tolist(), "values": g[m.y_field].tolist()}
        # Solo count
        g = df.groupby(cat, as_index=False).size()
        return {"labels": g[cat].astype(str).tolist(), "values": g["size"].tolist()}

    if ct == "histogram":
        if not m.y_field or m.y_field not in df.columns:
            return {"empty": True}
        return {"values": df[m.y_field].dropna().tolist()}

    if ct == "heatmap":
        if not (m.x_field and m.group_field and m.y_field):
            raise ValueError("heatmap requiere x_field, group_field, y_field")
        if any(c not in df.columns for c in [m.x_field, m.group_field, m.y_field]):
            return {"empty": True}
        pivot = df.pivot_table(
            index=m.group_field, columns=m.x_field, values=m.y_field, aggfunc=agg
        )
        return {
            "x": [str(c) for c in pivot.columns.tolist()],
            "y": [str(r) for r in pivot.index.tolist()],
            "z": pivot.fillna(None).values.tolist() if hasattr(pivot, "values") else [],
        }

    if ct == "radar":
        if not (m.axis_field and m.y_field):
            raise ValueError("radar requiere axis_field y y_field")
        if any(c not in df.columns for c in [m.axis_field, m.y_field]):
            return {"empty": True}
        if m.group_field and m.group_field in df.columns:
            g = df.groupby([m.group_field, m.axis_field], as_index=False)[m.y_field].agg(agg)
            axes = sorted(g[m.axis_field].astype(str).unique().tolist())
            series = []
            for name in g[m.group_field].astype(str).unique():
                sub = g[g[m.group_field].astype(str) == name].set_index(m.axis_field)[m.y_field]
                series.append({"name": str(name), "values": [sub.get(a, None) for a in axes]})
            return {"axes": axes, "series": series}
        else:
            g = df.groupby(m.axis_field, as_index=False)[m.y_field].agg(agg)
            return {
                "axes": g[m.axis_field].astype(str).tolist(),
                "series": [{"name": "Total", "values": g[m.y_field].tolist()}],
            }

    if ct == "gauge":
        if not m.y_field or m.y_field not in df.columns:
            return {"empty": True}
        series = pd.to_numeric(df[m.y_field], errors="coerce").dropna()
        if series.empty:
            return {"empty": True}
        agg_map = {"mean": series.mean, "sum": series.sum, "min": series.min,
                   "max": series.max, "count": lambda: float(series.count())}
        fn = agg_map.get(agg, series.mean)
        return {"value": float(fn())}

    raise ValueError(f"chart_type no soportado: {ct}")


def _render_chart_data(
    db: Session, org_id: int, cfg: ChartConfig,
    extra_filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base_filters = dict(cfg.data_source.filters)
    if extra_filters:
        base_filters.update(extra_filters)
    df = _load_metric_to_df(db, org_id, cfg.data_source.metric_id, base_filters)
    dataset = _build_dataset(df, cfg)
    return {
        "chart_type": cfg.chart_type,
        "mapping": cfg.mapping.model_dump(),
        "aesthetics": cfg.aesthetics.model_dump(),
        "dataset": dataset,
        "n_rows": len(df),
    }


# ─────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────


@router.get("/types")
async def list_chart_types(user: User = Depends(get_current_user)):
    """Devuelve la metadata de los tipos de gráfico disponibles. El
    frontend la usa para popular el selector y mostrar la lista de
    fields requeridos por tipo. Requiere autenticación (todos los
    endpoints autenticados, aunque no use org_id)."""
    return CHART_TYPE_META


@router.get("/", response_model=List[ChartSummary])
async def list_charts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    specs = db.query(Spec).filter(
        Spec.org_id == user.org_id, Spec.type == SPEC_TYPE
    ).order_by(Spec.id_spec.desc()).all()
    return [_spec_to_summary(s) for s in specs]


@router.post("/")
async def create_chart(
    payload: ChartCreate,
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
        charts_list=json.dumps([payload.config.model_dump()], ensure_ascii=False),
        tables_list="[]",
        org_id=user.org_id,
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return {"status": "success", "id_spec": spec.id_spec}


@router.get("/{chart_id}")
async def get_chart(
    chart_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, chart_id, user.org_id)
    return _spec_to_full(spec)


@router.put("/{chart_id}")
async def update_chart(
    chart_id: int,
    payload: ChartUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, chart_id, user.org_id)
    meta = _parse_meta(spec)
    if payload.name is not None:
        spec.name = payload.name
    if payload.description is not None:
        meta["description"] = payload.description
    if payload.is_draft is not None:
        meta["is_draft"] = payload.is_draft
    if payload.config is not None:
        spec.charts_list = json.dumps([payload.config.model_dump()], ensure_ascii=False)
    meta["updated_at"] = _now_str()
    spec.metadata_ = json.dumps(meta, ensure_ascii=False)
    db.commit()
    db.refresh(spec)
    return {"status": "success", "id_spec": spec.id_spec}


@router.delete("/{chart_id}")
async def delete_chart(
    chart_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, chart_id, user.org_id)
    db.delete(spec)
    db.commit()
    return {"status": "success", "message": f"Gráfico {chart_id} eliminado"}


@router.post("/{chart_id}/duplicate")
async def duplicate_chart(
    chart_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, chart_id, user.org_id)
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


@router.get("/{chart_id}/data")
async def get_chart_data(
    chart_id: int,
    extra_filters: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, chart_id, user.org_id)
    charts = _parse_charts_list(spec)
    if not charts:
        raise HTTPException(status_code=400, detail="Gráfico sin configuración")
    try:
        cfg = ChartConfig(**charts[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Config inválida: {e}")
    extra: Optional[Dict[str, Any]] = None
    if extra_filters:
        try:
            extra = json.loads(extra_filters)
        except Exception:
            extra = None
    try:
        return _render_chart_data(db, user.org_id, cfg, extra)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ChartPreviewRequest(BaseModel):
    config: ChartConfig
    extra_filters: Optional[Dict[str, Any]] = None


@router.post("/preview")
async def preview_chart_config(
    payload: ChartPreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Igual que /{id}/data pero recibe la config en body (no requiere
    persistencia). Para el editor live."""
    try:
        return _render_chart_data(db, user.org_id, payload.config, payload.extra_filters)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
