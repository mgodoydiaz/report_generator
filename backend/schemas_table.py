"""Pydantic schemas para tablas configurables (B7).

Una "tabla" se persiste como un Spec con type='Tablas'. El campo
`tables_list` del Spec contiene un array con UN único TableConfig
(1 spec = 1 tabla). Esto mantiene la simetría con cómo se manejan
charts en otros Specs y simplifica el CRUD.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────
# Color scales
# ─────────────────────────────────────────────────────────────────────────


class ColorScaleLinkedIndicator(BaseModel):
    """Toma los colores de los achievement_levels de un Indicator.

    Bidireccional: si el indicador cambia sus levels, las tablas
    vinculadas se actualizan automáticamente al consultarse.
    """
    kind: Literal["linked_indicator"]
    indicator_id: int
    # Columna del DataFrame que contiene la categoría/nivel del valor
    # (ej "Nivel Logro" → "Inicial"|"Intermedio"|"Avanzado"). Se usa
    # para hacer match con achievement_levels[i].name del indicador.
    level_field: str


class ColorScaleDiverging(BaseModel):
    """Escala divergente típica rojo→amarillo→verde para valores numéricos."""
    kind: Literal["diverging"]
    min_color: str = "#ef4444"
    neutral_color: str = "#fef3c7"
    max_color: str = "#22c55e"
    midpoint: float = 0.0
    domain_min: Optional[float] = None
    domain_max: Optional[float] = None


class ColorScaleSequential(BaseModel):
    """Escala secuencial (de claro a oscuro)."""
    kind: Literal["sequential"]
    base_color: str = "#3b82f6"
    domain_min: Optional[float] = None
    domain_max: Optional[float] = None


ColorScale = ColorScaleLinkedIndicator | ColorScaleDiverging | ColorScaleSequential


# ─────────────────────────────────────────────────────────────────────────
# Columnas
# ─────────────────────────────────────────────────────────────────────────


class TableColumn(BaseModel):
    """Configuración de una columna de la tabla."""
    key: str = Field(..., description="Nombre de la columna en metric_data")
    header: str = Field(..., description="Texto visible en el header")
    format: Literal["text", "int", "float", "percent", "date"] = "text"
    decimals: int = 1
    # Aggregación cuando hay grouping. None = no agrega (toma el primer
    # valor o pasa raw si la columna es de la dimensión de agrupación).
    agg: Optional[Literal["mean", "sum", "min", "max", "count", "nunique", "first"]] = None
    color_scale: Optional[ColorScale] = None
    width: Optional[int] = None
    # Si True, columna fija a la izquierda (no scrollea horizontalmente).
    pinned: bool = False
    # Si True, esta columna NO aparece en la tabla pero queda disponible
    # para sorting/filtering/agg.
    hidden: bool = False


# ─────────────────────────────────────────────────────────────────────────
# Data source
# ─────────────────────────────────────────────────────────────────────────


class TableDataSource(BaseModel):
    """De dónde salen los datos: una métrica + filtros + (opcional)
    overrides de derived_fields aplicados al df cargado."""
    metric_id: int
    filters: Dict[str, Any] = Field(default_factory=dict)
    derived_fields_override: List[Dict[str, Any]] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────
# Behavior
# ─────────────────────────────────────────────────────────────────────────


class TableGrouping(BaseModel):
    by: str
    # Aggregations para columnas que NO sean la de groupby (las columnas
    # mismas pueden definir su .agg para distintos modos por columna).
    drop_ungrouped: bool = False


class TableSort(BaseModel):
    column: str
    dir: Literal["asc", "desc"] = "asc"


class TablePagination(BaseModel):
    enabled: bool = True
    page_size: int = 50


class TableExport(BaseModel):
    csv: bool = True
    xlsx: bool = True


class TableBehavior(BaseModel):
    grouping: Optional[TableGrouping] = None
    sorting: List[TableSort] = Field(default_factory=list)
    pagination: TablePagination = Field(default_factory=TablePagination)
    export: TableExport = Field(default_factory=TableExport)
    search: bool = True


# ─────────────────────────────────────────────────────────────────────────
# TableConfig (lo que vive en Spec.tables_list[0])
# ─────────────────────────────────────────────────────────────────────────


class TableConfig(BaseModel):
    """Configuración completa de una tabla."""
    version: int = 1
    data_source: TableDataSource
    columns: List[TableColumn] = Field(default_factory=list)
    behavior: TableBehavior = Field(default_factory=TableBehavior)


# ─────────────────────────────────────────────────────────────────────────
# Payloads de API (lo que recibe POST /api/tables)
# ─────────────────────────────────────────────────────────────────────────


class TableCreate(BaseModel):
    name: str
    description: str = ""
    is_draft: bool = True
    config: TableConfig


class TableUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_draft: Optional[bool] = None
    config: Optional[TableConfig] = None


class TableSummary(BaseModel):
    """Forma "card" para listar tablas en el sidebar del editor."""
    id_spec: int
    name: str
    description: str
    is_draft: bool
    metric_id: Optional[int]
    n_columns: int
    updated_at: str
