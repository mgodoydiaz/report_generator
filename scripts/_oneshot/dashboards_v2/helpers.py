"""Helpers compartidos para el seed de dashboards v2.

Provee:
- Upsert idempotente de specs (Tablas | Gráficos) por (org_id, name, type).
- Construcción del JSON de dashboard_layout.
- Update del Indicator.dashboard_layout.

Idempotencia: el script se puede correr N veces; si un spec ya existe con el
mismo nombre, su config se reemplaza (UPSERT). El id_spec se mantiene cuando
es posible para no romper layouts referenciados por otros indicadores.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models import Indicator, Spec


# ─────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────

SPEC_TYPE_TABLE = "Tablas"
SPEC_TYPE_CHART = "Gráficos"


# Paletas estándar reusables. Coinciden con frontend/src/tooling/charts/constants.js
PALETTE_LOGRO = "semaforo"  # verde-amarillo-rojo según valor
PALETTE_CURSO = "tab10"
PALETTE_VIRIDIS = "viridis"


def now_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────────────────────────────────
# Color scales reusables (TableColumn.color_scale)
# ─────────────────────────────────────────────────────────────────────────


def color_scale_diverging_logro() -> Dict[str, Any]:
    """Escala rojo→amarillo→verde con punto medio en 0.5 (logro 50%)."""
    return {
        "kind": "diverging",
        "min_color": "#ef4444",
        "neutral_color": "#fef3c7",
        "max_color": "#22c55e",
        "midpoint": 0.5,
    }


def color_scale_linked(indicator_id: int, level_field: str = "Nivel Logro") -> Dict[str, Any]:
    """Vincula a achievement_levels del indicador (colores oficiales)."""
    return {
        "kind": "linked_indicator",
        "indicator_id": indicator_id,
        "level_field": level_field,
    }


def color_scale_sequential_blue() -> Dict[str, Any]:
    return {"kind": "sequential", "base_color": "#3b82f6"}


# ─────────────────────────────────────────────────────────────────────────
# Builders de TableConfig / ChartConfig
# ─────────────────────────────────────────────────────────────────────────


def table_config(
    metric_id: int,
    columns: List[Dict[str, Any]],
    grouping: Optional[Dict[str, Any]] = None,
    sorting: Optional[List[Dict[str, str]]] = None,
    page_size: int = 50,
    search: bool = True,
    filters: Optional[Dict[str, Any]] = None,
    derived_fields_override: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Arma un TableConfig (lo que va dentro de tables_list[0])."""
    behavior: Dict[str, Any] = {
        "pagination": {"enabled": True, "page_size": page_size},
        "export": {"csv": True, "xlsx": True},
        "search": search,
        "sorting": sorting or [],
    }
    if grouping:
        behavior["grouping"] = grouping
    return {
        "version": 1,
        "data_source": {
            "metric_id": metric_id,
            "filters": filters or {},
            "derived_fields_override": derived_fields_override or [],
        },
        "columns": columns,
        "behavior": behavior,
    }


def chart_config(
    chart_type: str,
    metric_id: int,
    *,
    titulo: str,
    x_field: Optional[str] = None,
    y_field: Optional[str] = None,
    group_field: Optional[str] = None,
    stack_field: Optional[str] = None,
    category_field: Optional[str] = None,
    axis_field: Optional[str] = None,
    aggregation: str = "mean",
    y_format: str = "number",
    y_lims: Optional[List[float]] = None,
    y_label: Optional[str] = None,
    x_label: Optional[str] = None,
    color_palette: Optional[str] = None,
    stack_order: Optional[List[str]] = None,
    bins: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    show_legend: bool = True,
    legend_title: Optional[str] = None,
) -> Dict[str, Any]:
    """Arma un ChartConfig (lo que va dentro de charts_list[0])."""
    return {
        "version": 1,
        "chart_type": chart_type,
        "data_source": {
            "metric_id": metric_id,
            "filters": filters or {},
            "derived_fields_override": [],
        },
        "mapping": {
            "x_field": x_field,
            "y_field": y_field,
            "group_field": group_field,
            "stack_field": stack_field,
            "category_field": category_field,
            "axis_field": axis_field,
            "aggregation": aggregation,
        },
        "aesthetics": {
            "titulo": titulo,
            "x_label": x_label,
            "y_label": y_label,
            "y_format": y_format,
            "y_lims": y_lims,
            "color_palette": color_palette,
            "show_legend": show_legend,
            "legend_title": legend_title,
            "stack_order": stack_order,
            "bins": bins,
        },
    }


# ─────────────────────────────────────────────────────────────────────────
# Upsert de specs
# ─────────────────────────────────────────────────────────────────────────


def upsert_table(
    db: Session,
    org_id: int,
    name: str,
    description: str,
    config: Dict[str, Any],
) -> int:
    """Inserta o actualiza un spec de tipo Tablas. Devuelve id_spec."""
    spec = (
        db.query(Spec)
        .filter(Spec.org_id == org_id, Spec.name == name, Spec.type == SPEC_TYPE_TABLE)
        .first()
    )
    meta = {"description": description, "is_draft": False, "updated_at": now_str()}
    payload_meta = json.dumps(meta, ensure_ascii=False)
    payload_tables = json.dumps([config], ensure_ascii=False)

    if spec is None:
        spec = Spec(
            name=name,
            type=SPEC_TYPE_TABLE,
            metadata_=payload_meta,
            charts_list="[]",
            tables_list=payload_tables,
            org_id=org_id,
        )
        db.add(spec)
        db.flush()
    else:
        spec.metadata_ = payload_meta
        spec.tables_list = payload_tables
        spec.charts_list = "[]"
        db.flush()
    return spec.id_spec


def upsert_chart(
    db: Session,
    org_id: int,
    name: str,
    description: str,
    config: Dict[str, Any],
) -> int:
    """Inserta o actualiza un spec de tipo Gráficos. Devuelve id_spec."""
    spec = (
        db.query(Spec)
        .filter(Spec.org_id == org_id, Spec.name == name, Spec.type == SPEC_TYPE_CHART)
        .first()
    )
    meta = {"description": description, "is_draft": False, "updated_at": now_str()}
    payload_meta = json.dumps(meta, ensure_ascii=False)
    payload_charts = json.dumps([config], ensure_ascii=False)

    if spec is None:
        spec = Spec(
            name=name,
            type=SPEC_TYPE_CHART,
            metadata_=payload_meta,
            charts_list=payload_charts,
            tables_list="[]",
            org_id=org_id,
        )
        db.add(spec)
        db.flush()
    else:
        spec.metadata_ = payload_meta
        spec.charts_list = payload_charts
        spec.tables_list = "[]"
        db.flush()
    return spec.id_spec


# ─────────────────────────────────────────────────────────────────────────
# Builders de layout
# ─────────────────────────────────────────────────────────────────────────


def cfg_chart_item(spec_id: int, title: Optional[str] = None) -> Dict[str, Any]:
    item: Dict[str, Any] = {"type": "configured_chart", "spec_id": spec_id}
    if title:
        item["title"] = title
    return item


def cfg_table_item(spec_id: int, title: Optional[str] = None) -> Dict[str, Any]:
    item: Dict[str, Any] = {"type": "configured_table", "spec_id": spec_id}
    if title:
        item["title"] = title
    return item


def kpis_item() -> Dict[str, Any]:
    return {"type": "kpis"}


def course_selector_item() -> Dict[str, Any]:
    return {"type": "course_selector"}


def row(items: List[Dict[str, Any]], cols: Optional[int] = None) -> Dict[str, Any]:
    return {"cols": cols if cols is not None else len(items), "items": items}


def tab(tab_id: str, label: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"id": tab_id, "label": label, "rows": rows}


def update_indicator_layout(
    db: Session,
    org_id: int,
    indicator_name: str,
    layout: Dict[str, Any],
) -> int:
    """Actualiza el dashboard_layout de un indicador por nombre."""
    ind = (
        db.query(Indicator)
        .filter(Indicator.org_id == org_id, Indicator.name == indicator_name)
        .first()
    )
    if ind is None:
        raise ValueError(f"Indicator {indicator_name!r} no encontrado en org {org_id}")
    ind.dashboard_layout = json.dumps(layout, ensure_ascii=False)
    db.flush()
    return ind.id_indicator


# ─────────────────────────────────────────────────────────────────────────
# Columnas reusables
# ─────────────────────────────────────────────────────────────────────────


def col_text(key: str, header: str, **kwargs) -> Dict[str, Any]:
    return {"key": key, "header": header, "format": "text", **kwargs}


def col_int(key: str, header: str, **kwargs) -> Dict[str, Any]:
    return {"key": key, "header": header, "format": "int", **kwargs}


def col_float(key: str, header: str, decimals: int = 2, **kwargs) -> Dict[str, Any]:
    return {"key": key, "header": header, "format": "float", "decimals": decimals, **kwargs}


def col_percent(
    key: str,
    header: str,
    decimals: int = 1,
    color_logro: bool = True,
    **kwargs,
) -> Dict[str, Any]:
    out = {"key": key, "header": header, "format": "percent", "decimals": decimals, **kwargs}
    if color_logro and "color_scale" not in out:
        out["color_scale"] = color_scale_diverging_logro()
    return out


def col_agg(
    alias: str,
    source_key: str,
    header: str,
    agg: str,
    fmt: str = "percent",
    decimals: int = 1,
    color_scale: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Columna derivada de una columna del df con agregación distinta.

    Útil en tablas de resumen donde múltiples columnas (mean, min, max, std)
    derivan de un mismo campo del df.
    """
    out: Dict[str, Any] = {
        "key": alias,
        "source_key": source_key,
        "header": header,
        "format": fmt,
        "decimals": decimals,
        "agg": agg,
    }
    if color_scale is not None:
        out["color_scale"] = color_scale
    return out


__all__ = [
    "SPEC_TYPE_TABLE",
    "SPEC_TYPE_CHART",
    "PALETTE_LOGRO",
    "PALETTE_CURSO",
    "PALETTE_VIRIDIS",
    "color_scale_diverging_logro",
    "color_scale_linked",
    "color_scale_sequential_blue",
    "table_config",
    "chart_config",
    "upsert_table",
    "upsert_chart",
    "cfg_chart_item",
    "cfg_table_item",
    "kpis_item",
    "course_selector_item",
    "row",
    "tab",
    "update_indicator_layout",
    "col_text",
    "col_int",
    "col_float",
    "col_percent",
    "col_agg",
]
