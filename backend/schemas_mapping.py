"""Pydantic schemas para tablas de mapeo (B10).

Una "tabla de mapeo" persiste como Spec con type='Mapeo'. El campo
`metadata_` del Spec contiene un MappingConfig serializado.

Tipos soportados:
- range: tabla de tramos {min, max, label}. Pensado para Cantidad → Categoría.
- discrete: dict {valor: label}. Pensado para Curso → Nivel.

Una vez guardado, los pipelines y tablas/gráficos pueden referenciar
el mapeo por id en lugar de inline. El backend resuelve el mapping_id
antes de aplicarlo via lookup_range/lookup_dict.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class MappingRange(BaseModel):
    """Un tramo de un mapeo por rangos."""
    min: Optional[float] = None  # None = abierto (sin límite inferior)
    max: Optional[float] = None  # None = abierto (sin límite superior)
    label: str


class MappingExtract(BaseModel):
    """Pre-procesamiento opcional del valor antes de buscar (para discrete)."""
    split: Optional[str] = None
    index: int = 0
    regex: Optional[str] = None


class MappingConfig(BaseModel):
    """Configuración completa de un mapeo."""
    version: int = 1
    kind: Literal["range", "discrete"]

    # Range: tramos ordenados ASC
    ranges: List[MappingRange] = Field(default_factory=list)
    match: Literal["left_inclusive", "right_inclusive", "both_inclusive"] = "left_inclusive"

    # Discrete: dict + opciones
    mapping: Dict[str, str] = Field(default_factory=dict)
    extract: Optional[MappingExtract] = None
    case_insensitive: bool = False

    # Default para valores no clasificables (NaN, fuera de rango, sin match)
    default: Optional[str] = None

    # Metadata semántica para validación al referenciarlo desde un pipeline:
    # - input_field_type: el value_field debe ser de este tipo en el df
    # - input_domain: rango esperado (informativo, no validado strictamente)
    input_field_type: Literal["numeric", "string", "any"] = "numeric"
    input_domain: Optional[str] = None  # ej "0-100", "0-1", informativo


class MappingCreate(BaseModel):
    name: str
    description: str = ""
    is_draft: bool = True
    config: MappingConfig


class MappingUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_draft: Optional[bool] = None
    config: Optional[MappingConfig] = None


class MappingSummary(BaseModel):
    """Forma 'card' para listar mapeos en el sidebar."""
    id_spec: int
    name: str
    description: str
    is_draft: bool
    kind: Optional[str]
    n_entries: int                # cuántos tramos (range) o claves (discrete)
    input_field_type: Optional[str]
    updated_at: str


class MappingPreviewRequest(BaseModel):
    """Body de POST /api/mappings/preview — testea un mapeo con valores."""
    config: MappingConfig
    values: List[Any]              # lista de valores a clasificar


class MappingPreviewResult(BaseModel):
    value: Any
    raw_value: Any                  # post-extract (si discrete con extract)
    label: Optional[str]
    matched: bool
