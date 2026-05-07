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
        # Si aesthetics.x_order está definido, lo usamos para ordenar las
        # categorías (ej meses cronológicos, cursos chilenos). Solo se
        # mantienen las x que existen en el dataset; valores en x_order
        # ausentes se omiten silenciosamente.
        if cfg.aesthetics and cfg.aesthetics.x_order:
            existing = set(g[m.x_field].astype(str))
            ordered_x = [x for x in cfg.aesthetics.x_order if x in existing]
            extras = [x for x in g[m.x_field].astype(str) if x not in cfg.aesthetics.x_order]
            ordered_x = ordered_x + extras
            g_idx = g.set_index(m.x_field)
            return {
                "x": [str(x) for x in ordered_x],
                "y": [g_idx.loc[x, m.y_field] for x in ordered_x],
            }
        return {"x": g[m.x_field].astype(str).tolist(), "y": g[m.y_field].tolist()}

    if ct == "grouped_bar":
        if not (m.x_field and m.y_field and m.group_field):
            raise ValueError("grouped_bar requiere x_field, y_field y group_field")
        if any(c not in df.columns for c in [m.x_field, m.y_field, m.group_field]):
            return {"empty": True}
        g = df.groupby([m.x_field, m.group_field], as_index=False)[m.y_field].agg(agg)
        x_vals = g[m.x_field].astype(str).unique().tolist()
        # `stack_order` también define el orden de las series en grouped_bar
        # (útil para meses cronológicos, hitos ordinales, etc.). Si no se
        # define, se usa el orden de aparición en el dataset (típicamente
        # alfabético post-groupby).
        series_order = (
            cfg.aesthetics.stack_order
            or g[m.group_field].astype(str).unique().tolist()
        )
        series = []
        for name in series_order:
            sub = g[g[m.group_field].astype(str) == str(name)].set_index(m.x_field)[m.y_field]
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
        x_vals = (
            cfg.aesthetics.x_order
            or g[m.x_field].astype(str).unique().tolist()
        )
        order = cfg.aesthetics.stack_order or g[m.stack_field].astype(str).unique().tolist()
        stacks = []
        for name in order:
            sub = g[g[m.stack_field].astype(str) == str(name)].set_index(m.x_field)["_n"]
            y_vals = [int(sub.get(x, 0)) for x in x_vals]
            stacks.append({"name": str(name), "y": y_vals})
        return {"x": x_vals, "stacks": stacks}

    if ct == "stacked_grouped_bar":
        # Eje X de 2 niveles: outer = group_field (ej Curso), inner = x_field
        # (ej Mes), stacked = stack_field (ej Logro/Nivel). Devuelve x_outer
        # y x_inner como arrays paralelos del mismo largo (Plotly soporta
        # x: [outer, inner] como categorical multi-level).
        if not (m.x_field and m.group_field and m.stack_field):
            raise ValueError(
                "stacked_grouped_bar requiere x_field, group_field y stack_field"
            )
        if any(c not in df.columns for c in [m.x_field, m.group_field, m.stack_field]):
            return {"empty": True}
        cnt = (
            df.groupby([m.group_field, m.x_field, m.stack_field], as_index=False)
            .size()
            .rename(columns={"size": "_n"})
        )
        # Orders: group natural sort, x desde aesthetics.x_order si existe,
        # stack desde aesthetics.stack_order si existe.
        g_order = sorted(cnt[m.group_field].astype(str).unique().tolist())
        x_order = (
            cfg.aesthetics.x_order
            or sorted(cnt[m.x_field].astype(str).unique().tolist())
        )
        s_order = (
            cfg.aesthetics.stack_order
            or sorted(cnt[m.stack_field].astype(str).unique().tolist())
        )
        # Construir x_outer (group repetido) y x_inner (x_field por group)
        x_outer: list[str] = []
        x_inner: list[str] = []
        for g in g_order:
            for x in x_order:
                x_outer.append(str(g))
                x_inner.append(str(x))
        # Stack series — cada uno tiene array y paralelo a (x_outer, x_inner)
        stacks = []
        # Index por (group, x, stack) → _n para lookup rápido
        idx = {
            (str(r[m.group_field]), str(r[m.x_field]), str(r[m.stack_field])): int(r["_n"])
            for _, r in cnt.iterrows()
        }
        for s in s_order:
            ys = []
            for g in g_order:
                for x in x_order:
                    ys.append(idx.get((str(g), str(x), str(s)), 0))
            stacks.append({"name": str(s), "y": ys})
        return {"x_outer": x_outer, "x_inner": x_inner, "stacks": stacks}

    if ct == "box":
        if not (m.x_field and m.y_field):
            raise ValueError("box requiere x_field y y_field")
        if any(c not in df.columns for c in [m.x_field, m.y_field]):
            return {"empty": True}
        # Box necesita los valores crudos por categoría.
        groups = {}
        for cat, sub in df.groupby(m.x_field):
            groups[str(cat)] = sub[m.y_field].dropna().tolist()
        # Aplicar x_order si existe (ej cursos chilenos, meses cronológicos).
        if cfg.aesthetics and cfg.aesthetics.x_order:
            ordered = [str(x) for x in cfg.aesthetics.x_order if str(x) in groups]
            extras = [k for k in groups if k not in [str(x) for x in cfg.aesthetics.x_order]]
            ordered = ordered + extras
        else:
            ordered = list(groups.keys())
        return {
            "x": ordered,
            "y_arrays": [groups[k] for k in ordered],
        }

    if ct == "line":
        if not (m.x_field and m.y_field):
            raise ValueError("line requiere x_field y y_field")
        if m.group_field:
            if any(c not in df.columns for c in [m.x_field, m.y_field, m.group_field]):
                return {"empty": True}
            g = df.groupby([m.x_field, m.group_field], as_index=False)[m.y_field].agg(agg)
            # x_order tiene precedencia (cronológico). Default: orden
            # alfabético de aparición.
            existing_x = set(g[m.x_field].astype(str))
            if cfg.aesthetics.x_order:
                x_vals = [str(x) for x in cfg.aesthetics.x_order if str(x) in existing_x]
                extras = [x for x in g[m.x_field].astype(str).unique() if x not in [str(o) for o in cfg.aesthetics.x_order]]
                x_vals = x_vals + sorted(extras)
            else:
                x_vals = sorted(g[m.x_field].astype(str).unique().tolist())
            # stack_order también ordena las series (curso/establecimiento).
            existing_series = set(g[m.group_field].astype(str))
            if cfg.aesthetics.stack_order:
                series_order = [str(s) for s in cfg.aesthetics.stack_order if str(s) in existing_series]
                series_extras = [s for s in g[m.group_field].astype(str).unique() if s not in [str(o) for o in cfg.aesthetics.stack_order]]
                series_order = series_order + sorted(series_extras)
            else:
                series_order = g[m.group_field].astype(str).unique().tolist()
            series = []
            for name in series_order:
                sub = g[g[m.group_field].astype(str) == str(name)].set_index(m.x_field)[m.y_field]
                series.append({"name": str(name), "y": [sub.get(x, None) for x in x_vals]})
            return {"x": x_vals, "series": series}
        else:
            if any(c not in df.columns for c in [m.x_field, m.y_field]):
                return {"empty": True}
            g = df.groupby(m.x_field, as_index=False)[m.y_field].agg(agg)
            existing_x = set(g[m.x_field].astype(str))
            if cfg.aesthetics.x_order:
                x_vals = [str(x) for x in cfg.aesthetics.x_order if str(x) in existing_x]
                extras = [x for x in g[m.x_field].astype(str).unique() if x not in [str(o) for o in cfg.aesthetics.x_order]]
                x_vals = x_vals + extras
            else:
                x_vals = g[m.x_field].astype(str).tolist()
            sub = g.set_index(m.x_field)[m.y_field]
            return {"x": x_vals, "y": [sub.get(x, None) for x in x_vals]}

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
        # Reordenar filas/cols según x_order/stack_order si están definidos.
        # Convención: aesthetics.x_order ordena el x_field (cols); stack_order
        # ordena el group_field (rows). Esto es esencial para matrices de
        # transición y heatmaps con niveles ordinales (peor→mejor) — sin
        # esto, pandas usa orden alfabético que no tiene sentido semántico.
        x_order = cfg.aesthetics.x_order if cfg.aesthetics else None
        row_order = cfg.aesthetics.stack_order if cfg.aesthetics else None
        if row_order:
            ordered_rows = [r for r in row_order if r in pivot.index]
            extras = [r for r in pivot.index if r not in row_order]
            pivot = pivot.reindex(ordered_rows + extras)
        if x_order:
            ordered_cols = [c for c in x_order if c in pivot.columns]
            extras = [c for c in pivot.columns if c not in x_order]
            pivot = pivot.reindex(columns=ordered_cols + extras)
        # `pivot.fillna(None)` es un no-op en pandas (None != NaN). Para que
        # json.dumps acepte el resultado hay que reemplazar NaN por None
        # explícitamente con .where + .astype(object).
        z_values = (
            pivot.astype(object).where(pivot.notna(), None).values.tolist()
            if hasattr(pivot, "values") else []
        )
        return {
            "x": [str(c) for c in pivot.columns.tolist()],
            "y": [str(r) for r in pivot.index.tolist()],
            "z": z_values,
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

    if ct == "pivot_matrix":
        # Tabla pivote: rows × cols con valores categóricos en celdas.
        # Mapping:
        #   axis_field  → row_field (ej Nombre)
        #   group_field → col_outer (ej Subprueba) - OPCIONAL
        #   x_field     → col_inner (ej Versión)
        #   y_field     → cell value (ej Nivel de Riesgo)
        # Si hay agg, se usa para combinar duplicados; default = first.
        if not (m.axis_field and m.x_field and m.y_field):
            raise ValueError(
                "pivot_matrix requiere axis_field (rows), x_field (cols) y y_field (celda)"
            )
        if any(c not in df.columns for c in [m.axis_field, m.x_field, m.y_field]):
            return {"empty": True}
        use_outer = bool(m.group_field) and m.group_field in df.columns

        rows_order = sorted(df[m.axis_field].astype(str).unique().tolist())
        col_inner_order = (
            cfg.aesthetics.x_order
            or sorted(df[m.x_field].astype(str).unique().tolist())
        )

        # Aggregation: si hay duplicados por (row, col), tomar el primer
        # valor non-null. Si quisiéramos otro agg numérico, se podría
        # parametrizar — para celdas categóricas, "first" es lo natural.
        if use_outer:
            col_outer_order = (
                cfg.aesthetics.stack_order
                or sorted(df[m.group_field].astype(str).unique().tolist())
            )
            cells = []
            for r in rows_order:
                sub = df[df[m.axis_field].astype(str) == r]
                row_cells = []
                for outer in col_outer_order:
                    for inner in col_inner_order:
                        s = sub[
                            (sub[m.group_field].astype(str) == str(outer))
                            & (sub[m.x_field].astype(str) == str(inner))
                        ]
                        val = (
                            s[m.y_field].iloc[0]
                            if len(s) > 0 and pd.notna(s[m.y_field].iloc[0])
                            else None
                        )
                        row_cells.append(val)
                cells.append(row_cells)
            return {
                "rows": rows_order,
                "col_outer": col_outer_order,
                "col_inner": col_inner_order,
                "cells": cells,
            }
        else:
            cells = []
            for r in rows_order:
                sub = df[df[m.axis_field].astype(str) == r]
                row_cells = []
                for c in col_inner_order:
                    s = sub[sub[m.x_field].astype(str) == str(c)]
                    val = (
                        s[m.y_field].iloc[0]
                        if len(s) > 0 and pd.notna(s[m.y_field].iloc[0])
                        else None
                    )
                    row_cells.append(val)
                cells.append(row_cells)
            return {
                "rows": rows_order,
                "cols": col_inner_order,
                "cells": cells,
            }

    raise ValueError(f"chart_type no soportado: {ct}")


def _render_chart_data(
    db: Session, org_id: int, cfg: ChartConfig,
    extra_filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base_filters = dict(cfg.data_source.filters)
    if extra_filters:
        base_filters.update(extra_filters)

    # Derived columns: pueden venir del spec (override) o del indicador
    # vinculado a la metric. Se aplican PRE-filtro temporal — los kinds
    # slope/delta/agg necesitan ver todas las observaciones del estudiante.
    # Mismo patrón que tables.py para consistencia entre charts y tablas.
    derived_cfg_list = list(cfg.data_source.derived_fields_override or [])
    if not derived_cfg_list:
        from backend.models import IndicatorMetric, Indicator
        ind_links = db.query(IndicatorMetric).filter(
            IndicatorMetric.id_metric == cfg.data_source.metric_id
        ).all()
        for lnk in ind_links:
            ind = db.query(Indicator).filter(
                Indicator.id_indicator == lnk.id_indicator,
                Indicator.org_id == org_id,
            ).first()
            if not ind or not ind.derived_columns:
                continue
            try:
                ind_dc = json.loads(ind.derived_columns)
            except Exception:
                continue
            for entry in ind_dc:
                if entry.get("metric_id") == cfg.data_source.metric_id:
                    derived_cfg_list.append(entry)

    # Identifica dims temporales para excluirlas del filtro pre-cálculo
    from backend.models import Dimension
    temporal_dim_ids: set[str] = set()
    for entry in derived_cfg_list:
        for did in (entry.get("temporal_dim_ids") or []):
            temporal_dim_ids.add(str(did))
    temporal_dim_names: set[str] = set()
    if temporal_dim_ids:
        dims = db.query(Dimension).filter(
            Dimension.id_dimension.in_([int(x) for x in temporal_dim_ids])
        ).all()
        temporal_dim_names = {d.name for d in dims}

    pre_filters = {k: v for k, v in base_filters.items() if k not in temporal_dim_names}
    df = _load_metric_to_df(db, org_id, cfg.data_source.metric_id, pre_filters)

    if derived_cfg_list and not df.empty:
        try:
            from backend.rgenerator.core.derived_fields_engine import apply_derived_fields
            for entry in derived_cfg_list:
                configs = entry.get("configs") or []
                if configs:
                    df = apply_derived_fields(df, configs)
        except Exception:
            import traceback
            traceback.print_exc()

    # Filtros temporales POST cálculo
    post_temporal = {k: v for k, v in base_filters.items() if k in temporal_dim_names}
    if post_temporal:
        for col, val in post_temporal.items():
            if col not in df.columns:
                continue
            if isinstance(val, (list, tuple, set)):
                allowed = {str(v) for v in val}
                if not allowed:
                    continue
                df = df[df[col].astype(str).isin(allowed)]
            else:
                df = df[df[col].astype(str) == str(val)]

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
