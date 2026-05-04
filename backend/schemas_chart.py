"""Pydantic schemas para gráficos configurables (B8).

Cada gráfico se persiste como un Spec con type='Gráficos'. El campo
`charts_list` del Spec contiene un array con UN único ChartConfig
(1 spec = 1 gráfico). Mismo patrón que B7 (TableConfig vs Spec.tables_list).

10 tipos soportados en v1 (mapean a componentes Plotly del frontend):
    bar, grouped_bar, stacked_bar, box, line, pie, histogram, heatmap,
    radar, gauge.

El backend prepara un dataset agregado (groupby + agg) y devuelve
{config, dataset}. El frontend lo grafica con `<ChartRenderer>` que
mapea cada `chart_type` a su componente React Plotly.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────
# Tipos de chart soportados (v1)
# ─────────────────────────────────────────────────────────────────────────


ChartType = Literal[
    "bar",          # Barras simples por categoría — promedio de Y por X
    "grouped_bar",  # Barras agrupadas — Y por X × group
    "stacked_bar",  # Barras apiladas — count por (X, categoría)
    "box",          # Boxplot — distribución de Y por X
    "line",         # Línea — Y por X (típicamente temporal)
    "pie",          # Torta — composición de una categoría
    "histogram",    # Histograma — distribución univariada de Y
    "heatmap",      # Matriz de calor — Y por (X, group)
    "radar",        # Radar — perfil multi-eje
    "gauge",        # Medidor KPI — un valor único
]


CHART_TYPE_META: Dict[str, Dict[str, Any]] = {
    "bar": {
        "display_name": "Barras",
        "description": "Barras simples del promedio (o suma/count) de Y agrupado por X.",
        "required_fields": ["x_field", "y_field"],
        "optional_fields": ["aggregation"],
        "plotly_component": "BarByGroup",
    },
    "grouped_bar": {
        "display_name": "Barras agrupadas",
        "description": "Barras agrupadas: eje X + serie por categoría secundaria.",
        "required_fields": ["x_field", "y_field", "group_field"],
        "optional_fields": ["aggregation"],
        "plotly_component": "GroupedBarByPeriod",
    },
    "stacked_bar": {
        "display_name": "Barras apiladas",
        "description": "Barras apiladas: count por (X, categoría). Típico semáforo de niveles.",
        "required_fields": ["x_field", "stack_field"],
        "optional_fields": ["stack_order", "color_palette"],
        "plotly_component": "StackedCountByGroup",
    },
    "box": {
        "display_name": "Boxplot",
        "description": "Distribución (caja-bigote) de Y por X.",
        "required_fields": ["x_field", "y_field"],
        "optional_fields": [],
        "plotly_component": "BoxPlotByGroup",
    },
    "line": {
        "display_name": "Línea",
        "description": "Línea de Y por X. Soporta múltiples series via group_field.",
        "required_fields": ["x_field", "y_field"],
        "optional_fields": ["group_field", "aggregation"],
        "plotly_component": "TrendLine",
    },
    "pie": {
        "display_name": "Torta",
        "description": "Composición proporcional de una dimensión (count o suma de Y).",
        "required_fields": ["category_field"],
        "optional_fields": ["y_field", "aggregation"],
        "plotly_component": "PieComposition",
    },
    "histogram": {
        "display_name": "Histograma",
        "description": "Distribución univariada de Y.",
        "required_fields": ["y_field"],
        "optional_fields": ["bins", "group_field"],
        "plotly_component": "Histogram",
    },
    "heatmap": {
        "display_name": "Matriz de calor",
        "description": "Matriz Y por (X, group). Valor de Y = intensidad de color.",
        "required_fields": ["x_field", "group_field", "y_field"],
        "optional_fields": ["aggregation", "color_palette"],
        "plotly_component": "HeatmapMatrix",
    },
    "radar": {
        "display_name": "Radar",
        "description": "Perfil multi-eje. Cada axis_field es un eje, cada serie un grupo.",
        "required_fields": ["axis_field", "y_field"],
        "optional_fields": ["group_field"],
        "plotly_component": "RadarProfile",
    },
    "gauge": {
        "display_name": "Medidor KPI",
        "description": "Un valor único (típicamente promedio del Y) con escala de color.",
        "required_fields": ["y_field"],
        "optional_fields": ["aggregation", "min_value", "max_value", "thresholds"],
        "plotly_component": "GaugeIndicator",
    },
}


# ─────────────────────────────────────────────────────────────────────────
# Sub-schemas
# ─────────────────────────────────────────────────────────────────────────


class ChartDataSource(BaseModel):
    """De dónde salen los datos: una métrica + filtros + (opcional) overrides."""
    metric_id: int
    filters: Dict[str, Any] = Field(default_factory=dict)
    derived_fields_override: List[Dict[str, Any]] = Field(default_factory=list)


class ChartMapping(BaseModel):
    """Mapeo de campos del df a roles del gráfico.

    Cuál usar depende del `chart_type`:
        - bar/grouped_bar/box/line: x_field + y_field (+ group_field si aplica)
        - stacked_bar: x_field + stack_field
        - pie: category_field (+ y_field si suma valores en lugar de contar)
        - histogram: y_field
        - heatmap: x_field + group_field + y_field
        - radar: axis_field + y_field (+ group_field para múltiples series)
        - gauge: y_field
    """
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    group_field: Optional[str] = None
    stack_field: Optional[str] = None
    category_field: Optional[str] = None  # alias para pie
    axis_field: Optional[str] = None       # para radar: la dimensión que define los ejes
    aggregation: Literal["mean", "sum", "min", "max", "count", "nunique"] = "mean"


class ChartAesthetics(BaseModel):
    """Configuración visual del gráfico."""
    titulo: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    y_format: Literal["number", "percent", "int"] = "number"
    y_lims: Optional[List[float]] = None  # [min, max]
    color_palette: Optional[str] = None    # ej "tab10", "Set2", "semaforo", "viridis"
    show_legend: bool = True
    legend_title: Optional[str] = None
    # Para stacked_bar, lista ordenada de los valores del stack_field para
    # asignar paleta consistente (ej ["Avanzado", "Intermedio", "Inicial"]).
    stack_order: Optional[List[str]] = None
    # Para histogram
    bins: int = 10
    # Para gauge
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    thresholds: Optional[List[Dict[str, Any]]] = None  # [{value, color}]


# ─────────────────────────────────────────────────────────────────────────
# ChartConfig (lo que vive en Spec.charts_list[0])
# ─────────────────────────────────────────────────────────────────────────


class ChartConfig(BaseModel):
    """Configuración completa de un gráfico."""
    version: int = 1
    chart_type: ChartType
    data_source: ChartDataSource
    mapping: ChartMapping = Field(default_factory=ChartMapping)
    aesthetics: ChartAesthetics = Field(default_factory=ChartAesthetics)


# ─────────────────────────────────────────────────────────────────────────
# Payloads de API
# ─────────────────────────────────────────────────────────────────────────


class ChartCreate(BaseModel):
    name: str
    description: str = ""
    is_draft: bool = True
    config: ChartConfig


class ChartUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_draft: Optional[bool] = None
    config: Optional[ChartConfig] = None


class ChartSummary(BaseModel):
    """Forma "card" para listar gráficos en el sidebar del editor."""
    id_spec: int
    name: str
    description: str
    is_draft: bool
    chart_type: Optional[str]
    metric_id: Optional[int]
    updated_at: str
