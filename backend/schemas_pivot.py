"""Pydantic schemas para el motor de pivotes (W2).

Contrato declarativo, JSON-serializable, que describe UN pivote:
filas (agrupación multinivel), columnas (0+ niveles), una o más métricas
(`values`) con su agregación y formato, totales de fila/columna, orden
custom por campo y valor de relleno para celdas sin datos.

El motor puro vive en `backend/rgenerator/core/pivot_engine.py` y consume
estos modelos (o un dict con la misma forma). Ver el diseño en
`docs/planes/w2_motor_pivotes.md`.

Convención de nombres: todo lo de W2 lleva "pivot" en el nombre.

Agregaciones soportadas (`PivotValue.agg`):

- Numéricas: `mean`, `sum`, `min`, `max`, `median`, `std`.
- Conteo: `count` (no nulos del campo), `nunique` (distintos no nulos).
- Porcentaje/distribución (base = conteo de registros): `pct_row`,
  `pct_col`, `pct_total` — fracción (0..1) de la celda sobre el total de
  su fila / columna / global. Ver la doc del motor para la semántica exacta.

Amplía el enum de agregación existente de `schemas_chart.py`
(`mean|sum|min|max|count|nunique`) con `median`, `std` y los tres `pct_*`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# Todas las agregaciones que entiende el motor. El mismo Literal se usa para
# validar el spec y como fuente de verdad para introspección del frontend.
PivotAgg = Literal[
    "mean",
    "sum",
    "count",
    "nunique",
    "min",
    "max",
    "median",
    "std",
    "pct_row",
    "pct_col",
    "pct_total",
]

# Subconjunto de agregaciones que producen porcentajes/distribución.
PCT_AGGS = ("pct_row", "pct_col", "pct_total")


class PivotValue(BaseModel):
    """Una métrica a agregar dentro del pivote.

    - `field`: nombre de la columna del DataFrame de origen.
    - `agg`: agregación (ver `PivotAgg`).
    - `label`: etiqueta visible de la métrica (default: el nombre del campo).
    - `format`: format-spec de Python aplicado al `display` de cada celda
      (ej ".1%" → "85.0%", ".2f" → "3.14"). El `value` crudo (numérico)
      siempre se conserva sin formatear. Si es None, el motor elige un
      default razonable según la agregación (porcentaje → ".1%",
      count/nunique → entero, resto → general).
    """

    field: str
    agg: PivotAgg = "mean"
    label: Optional[str] = None
    format: Optional[str] = None

    @field_validator("field")
    @classmethod
    def _field_no_vacio(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("PivotValue.field no puede ser vacío")
        return v

    def display_label(self) -> str:
        """Etiqueta visible: `label` si está definido, si no el nombre del campo."""
        return self.label if self.label else self.field

    def is_pct(self) -> bool:
        return self.agg in PCT_AGGS


class PivotTotals(BaseModel):
    """Qué totales agregar al resultado.

    - `rows=True`: fila "Total" al final, agregando TODAS las filas.
    - `cols=True`: columna "Total" al final, agregando TODAS las columnas
      (solo se emite si el pivote tiene campos de columna).
    """

    rows: bool = True
    cols: bool = True


class PivotSpec(BaseModel):
    """Especificación declarativa de UN pivote (JSON-serializable).

    Ejemplo::

        {
          "rows": ["Curso"],
          "cols": ["Mes"],
          "values": [
            {"field": "Logro", "agg": "mean", "label": "Logro prom.", "format": ".1%"}
          ],
          "totals": {"rows": true, "cols": true},
          "order": {"Mes": ["Marzo", "Abril", "Mayo"]},
          "fill_value": null,
          "total_label": "Total"
        }
    """

    rows: List[str] = Field(..., min_length=1, description="1+ campos de agrupación en filas (multinivel)")
    cols: List[str] = Field(default_factory=list, description="0+ campos de agrupación en columnas (multinivel)")
    values: List[PivotValue] = Field(..., min_length=1, description="1+ métricas a agregar")
    totals: PivotTotals = Field(default_factory=PivotTotals)
    # Orden custom por campo: {campo: [valores en el orden deseado]}. Los
    # valores no listados van después, en orden natural. Campos sin entrada
    # usan orden natural (numérico antes que texto, alfanumérico).
    order: Dict[str, List[str]] = Field(default_factory=dict)
    # Valor con el que se rellenan las celdas de cuerpo sin datos (solo aggs
    # NO porcentuales). None = celda vacía (value None, display ""). Un número
    # participa como tal (ej 0). No aplica a los totales ni a los pct_*.
    fill_value: Optional[Any] = None
    # Etiqueta de la fila/columna de totales.
    total_label: str = "Total"

    @field_validator("rows", "cols")
    @classmethod
    def _campos_no_vacios(cls, v: List[str]) -> List[str]:
        for f in v:
            if not f or not str(f).strip():
                raise ValueError("Los nombres de campo en rows/cols no pueden ser vacíos")
        return v
