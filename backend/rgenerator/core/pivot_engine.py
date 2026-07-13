"""Motor de pivotes puro (W2-A).

Una única función `pivot(df, spec)` server-side, declarativa, que reemplaza
las implementaciones fragmentadas de pivote (dashboard `pivot_matrix`,
`PivotTable` del PDF v1, groupbys ad-hoc). Función **pura**: sin DB, sin IO,
sin FastAPI — solo pandas. Los consumidores (PARTE B: dashboard/PDF/Excel)
cargan el DataFrame con la capa de métricas y consumen el `PivotResult`.

Ver el contrato en `docs/planes/w2_motor_pivotes.md` y el spec en
`backend/schemas_pivot.py`.

──────────────────────────────────────────────────────────────────────────
Representación de `PivotResult`
──────────────────────────────────────────────────────────────────────────

`PivotResult` es un modelo Pydantic (serializable directo a JSON con
`.model_dump(mode="json")`). Forma::

    {
      "row_fields": ["Curso"],
      "col_fields": ["Mes"],
      "columns": [
        {"keys": ["Marzo"], "field": "Logro", "agg": "mean",
         "label": "Logro prom.", "is_total": false},
        {"keys": ["Abril"], "field": "Logro", ...},
        {"keys": ["Total"], "field": "Logro", ..., "is_total": true}
      ],
      "rows": [
        {"keys": ["II A"],
         "cells": [{"value": 0.85, "display": "85.0%"}, ...],
         "is_total": false},
        {"keys": ["Total"], "cells": [...], "is_total": true}
      ],
      "meta": {"n_source_rows": 120,
               "has_totals": {"rows": true, "cols": true},
               "aggs": [{"field": "Logro", "agg": "mean",
                         "label": "Logro prom.", "format": ".1%"}],
               "total_label": "Total"}
    }

- `columns[i]` describe la i-ésima columna de datos. `cells[i]` de cada fila
  está alineada posicionalmente con `columns[i]`.
- Layout de columnas: **combinación de columna (outer) × métrica (inner)**,
  al estilo Excel. Con 0 campos de columna hay una columna por métrica. Las
  columnas "Total" (si `totals.cols` y hay campos de columna) van al final,
  una por métrica, con `is_total=True` y `keys=[total_label]`.
- Cada celda: `value` = número crudo (float) o None si falta/NaN; `display`
  = string ya formateado según el `format` de la métrica.
- Filas y columnas se emiten **solo para las combinaciones presentes** en los
  datos (no se genera el producto cartesiano de niveles). Con cols
  multinivel, una combinación de niveles que no aparece en el df no produce
  columna. Dentro de una fila, una celda de una combinación presente pero sin
  datos para esa fila sí aparece (value None / 0% según la agg).

──────────────────────────────────────────────────────────────────────────
Semántica de totales (fuente típica de bugs — leer)
──────────────────────────────────────────────────────────────────────────

El total usa la MISMA agregación sobre el conjunto completo, **no** la suma
(ni el promedio) de las celdas ya agregadas. Ejemplos:

- Total de un `mean` = promedio de TODOS los registros de esa fila/columna,
  NO el promedio de los promedios de las celdas.
- Total de un `sum` = suma de todos los registros (coincide con la suma de
  celdas para `sum`, pero se recalcula igual).
- Total de un `median`/`std`/`min`/`max` = el estadístico sobre el conjunto
  completo.
- El total de totales (esquina) = la agregación sobre TODO el DataFrame.

Para los `pct_*` los totales son coherentes por construcción (ver abajo).

──────────────────────────────────────────────────────────────────────────
Semántica de porcentajes (`pct_row`, `pct_col`, `pct_total`)
──────────────────────────────────────────────────────────────────────────

Base = **conteo de registros no nulos** del `field` en cada grupo (la
distribución de frecuencias clásica de una tabla de contingencia; es lo que
la fundación llama "% de estudiantes en cada nivel"). El valor es una
fracción 0..1 (usar format ".1%" para mostrarlo como %).

- `pct_row`: conteo de la celda / conteo total de su FILA. Las celdas de
  cuerpo de una fila suman 100%. La columna "Total" de una fila = 100%.
- `pct_col`: conteo de la celda / conteo total de su COLUMNA. Las celdas de
  cuerpo de una columna suman 100%. La fila "Total" de una columna = 100%.
- `pct_total`: conteo de la celda / conteo global. Toda la matriz de cuerpo
  suma 100%.
- La esquina (Total×Total) de cualquier `pct_*` es 100%.
- **División por cero** (fila/columna/total con conteo 0) → 0.0 (0%), nunca
  NaN. Una combinación sin registros → 0.0 (0%). `fill_value` NO aplica a
  los `pct_*` (las celdas faltantes ya son 0%).

──────────────────────────────────────────────────────────────────────────
NaN, división por cero y columnas no numéricas
──────────────────────────────────────────────────────────────────────────

- **Filas con NaN en una dimensión de agrupación** (rows/cols) se descartan
  del pivote (pero `meta.n_source_rows` reporta el largo original del df).
- **NaN en el campo de valor**: se excluye del cálculo (semántica pandas:
  mean/sum/etc ignoran NaN; count/nunique cuentan no nulos).
- **Celda de cuerpo sin datos** (agg no porcentual): `value=None`,
  `display=""` — salvo que `spec.fill_value` esté definido (número → esa
  celda vale ese número; string → display = ese texto, value None).
- **Columna no numérica con agg numérica** (`mean/sum/median/std`): se
  coerciona con `pd.to_numeric(errors="coerce")`; los valores no parseables
  quedan NaN y se excluyen. `min`/`max`/`count`/`nunique` y los `pct_*` no
  coercionan (operan sobre el tipo nativo).
- `std` es la desviación estándar MUESTRAL (ddof=1, default de pandas); con
  un solo dato da NaN.

──────────────────────────────────────────────────────────────────────────
Firma pública
──────────────────────────────────────────────────────────────────────────

    def pivot(df: pd.DataFrame, spec: PivotSpec | dict) -> PivotResult
    def pivot_to_dataframe(result: PivotResult) -> pd.DataFrame
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from pydantic import BaseModel, Field

from backend.schemas_pivot import PCT_AGGS, PivotSpec


# ─────────────────────────────────────────────────────────────────────────
# Modelos de salida (PivotResult)
# ─────────────────────────────────────────────────────────────────────────


class PivotCell(BaseModel):
    """Una celda: valor crudo + string ya formateado."""

    value: Optional[float] = None
    display: str = ""


class PivotColumn(BaseModel):
    """Encabezado de una columna de datos.

    - `keys`: valores de los campos de columna (niveles). Vacío si no hay
      campos de columna. Para la columna "Total": `[total_label]`.
    - `field`/`agg`/`label`: la métrica que representa esta columna.
    - `is_total`: True si es la columna de totales de fila.
    """

    keys: List[str] = Field(default_factory=list)
    field: str
    agg: str
    label: str
    is_total: bool = False


class PivotRow(BaseModel):
    """Una fila del resultado.

    - `keys`: valores de los campos de fila (niveles). Para la fila "Total":
      `[total_label]`.
    - `cells`: alineadas posicionalmente con `PivotResult.columns`.
    - `is_total`: True si es la fila de totales de columna.
    """

    keys: List[str] = Field(default_factory=list)
    cells: List[PivotCell] = Field(default_factory=list)
    is_total: bool = False


class PivotMeta(BaseModel):
    n_source_rows: int
    has_totals: Dict[str, bool]
    aggs: List[Dict[str, Any]]
    total_label: str = "Total"


class PivotResult(BaseModel):
    """Resultado del pivote. Serializable a JSON (`model_dump(mode="json")`)."""

    row_fields: List[str] = Field(default_factory=list)
    col_fields: List[str] = Field(default_factory=list)
    columns: List[PivotColumn] = Field(default_factory=list)
    rows: List[PivotRow] = Field(default_factory=list)
    meta: PivotMeta


# ─────────────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────────────

_NUMERIC_COERCE_AGGS = ("mean", "sum", "median", "std")


def _coerce_spec(spec: PivotSpec | dict) -> PivotSpec:
    """Normaliza el spec a un PivotSpec, tolerando dict o instancias de otro
    módulo (por el doble empaquetado rgenerator / backend.rgenerator)."""
    if isinstance(spec, PivotSpec):
        return spec
    if isinstance(spec, dict):
        return PivotSpec(**spec)
    # Instancia PivotSpec-like de otro import path.
    if hasattr(spec, "model_dump"):
        return PivotSpec(**spec.model_dump())
    raise TypeError(f"spec debe ser PivotSpec o dict, no {type(spec)!r}")


def _natkey(v: Any) -> Tuple[int, float, str]:
    """Clave de orden natural homogénea (evita comparar tipos mixtos).

    Orden: números primero (por valor), luego texto (alfabético), luego
    NaN/None al final.
    """
    if v is None:
        return (2, 0.0, "")
    if isinstance(v, float) and math.isnan(v):
        return (2, 0.0, "")
    if isinstance(v, bool):
        return (0, float(v), "")
    if isinstance(v, (int, float)):
        return (0, float(v), "")
    return (1, 0.0, str(v))


def _ordered_keys(df: pd.DataFrame, fields: List[str], order: Dict[str, List[str]]) -> List[tuple]:
    """Combinaciones únicas de `fields` presentes en el df, ordenadas.

    Respeta `order[campo]` (valores listados primero, en ese orden; el resto
    después en orden natural). Campos sin entrada en `order` usan orden
    natural. Devuelve lista de tuplas (una por combinación). Sin campos →
    `[()]` (una única "columna vacía").
    """
    if not fields:
        return [()]
    present = df[fields].drop_duplicates()
    combos = [tuple(row) for row in present.itertuples(index=False, name=None)]

    order_index = {f: {val: i for i, val in enumerate(order[f])} for f in fields if f in order}

    def keyfn(combo: tuple) -> list:
        parts = []
        for f, val in zip(fields, combo):
            oi = order_index.get(f)
            if oi is not None:
                if val in oi:
                    parts.append((0, oi[val], 0, 0.0, ""))
                else:
                    nk = _natkey(val)
                    parts.append((1, 0, nk[0], nk[1], nk[2]))
            else:
                nk = _natkey(val)
                parts.append((0, 0, nk[0], nk[1], nk[2]))
        return parts

    combos.sort(key=keyfn)
    return combos


def _keystr(v: Any) -> str:
    """Renderiza un valor de key como string legible (int limpio, sin ``.0``)."""
    if v is None:
        return ""
    if isinstance(v, float):
        if math.isnan(v):
            return ""
        if v.is_integer():
            return str(int(v))
    return str(v)


def _coerce_series(s: pd.Series, agg: str) -> pd.Series:
    if agg in _NUMERIC_COERCE_AGGS:
        return pd.to_numeric(s, errors="coerce")
    return s


def _agg_map(df: pd.DataFrame, group_fields: List[str], field: str, agg: str) -> Dict[tuple, Any]:
    """`{tupla_de_keys: valor_agregado}` para `agg` de `field` agrupando por
    `group_fields`."""
    tmp = pd.DataFrame({f: df[f].to_numpy() for f in group_fields})
    tmp["__v"] = _coerce_series(df[field], agg).to_numpy()
    grouped = tmp.groupby(group_fields, dropna=True, observed=True)["__v"].agg(agg)
    out: Dict[tuple, Any] = {}
    single = len(group_fields) == 1
    for k, val in grouped.items():
        out[(k,) if single else tuple(k)] = val
    return out


def _count_map(df: pd.DataFrame, group_fields: List[str], field: str) -> Dict[tuple, int]:
    """`{tupla_de_keys: conteo_no_nulos_de_field}` agrupando por `group_fields`."""
    tmp = pd.DataFrame({f: df[f].to_numpy() for f in group_fields})
    tmp["__v"] = df[field].to_numpy()
    grouped = tmp.groupby(group_fields, dropna=True, observed=True)["__v"].count()
    out: Dict[tuple, int] = {}
    single = len(group_fields) == 1
    for k, val in grouped.items():
        out[(k,) if single else tuple(k)] = int(val)
    return out


def _scalar_agg(s: pd.Series, agg: str) -> Any:
    return getattr(_coerce_series(s, agg), agg)()


def _is_nan(v: Any) -> bool:
    return isinstance(v, float) and math.isnan(v)


def _format_display(value: Any, fmt: Optional[str], agg: str) -> str:
    """Formatea `value` (número crudo) a string según `fmt` (Python format-spec)."""
    if value is None or _is_nan(value):
        return ""
    if not fmt:
        if agg in PCT_AGGS:
            fmt = ".1%"
        elif agg in ("count", "nunique"):
            try:
                return str(int(round(float(value))))
            except (ValueError, TypeError):
                return str(value)
        else:
            fv = float(value)
            if fv.is_integer():
                return str(int(fv))
            return f"{fv:g}"
    try:
        return format(float(value), fmt)
    except (ValueError, TypeError):
        return str(value)


def _make_cell(raw: Any, fmt: Optional[str], agg: str, fill_value: Any) -> PivotCell:
    """Construye una celda a partir del valor crudo, aplicando `fill_value` si
    falta (solo aggs no porcentuales)."""
    value: Optional[float]
    if raw is None or _is_nan(raw):
        if fill_value is None:
            return PivotCell(value=None, display="")
        try:
            fv = float(fill_value)
            return PivotCell(value=fv, display=_format_display(fv, fmt, agg))
        except (ValueError, TypeError):
            return PivotCell(value=None, display=str(fill_value))
    value = float(raw)
    return PivotCell(value=value, display=_format_display(value, fmt, agg))


# ─────────────────────────────────────────────────────────────────────────
# Cálculo por métrica
# ─────────────────────────────────────────────────────────────────────────


class _MetricCalc:
    """Precomputa y sirve los valores (cuerpo, total-columna, total-fila,
    esquina) de una métrica, ocultando la diferencia entre agg normal y pct."""

    def __init__(self, df: pd.DataFrame, rows: List[str], cols: List[str], field: str, agg: str,
                 want_col_total: bool, want_row_total: bool):
        self.field = field
        self.agg = agg
        self.is_pct = agg in PCT_AGGS

        if self.is_pct:
            self.k_body = _count_map(df, rows + cols, field)
            self.k_row = _count_map(df, rows, field)  # conteo por fila (todas las cols)
            self.k_grand = int(df[field].count())
            if cols:
                self.k_col = _count_map(df, cols, field)  # conteo por columna (todas las filas)
            else:
                self.k_col = {(): self.k_grand}
        else:
            self.body = _agg_map(df, rows + cols, field, agg)
            self.col_total = _agg_map(df, rows, field, agg) if want_col_total else {}
            if want_row_total:
                self.row_total = _agg_map(df, cols, field, agg) if cols else {(): _scalar_agg(df[field], agg)}
            else:
                self.row_total = {}
            self.corner = _scalar_agg(df[field], agg) if (want_col_total and want_row_total) else None

    @staticmethod
    def _ratio(num: float, den: float) -> float:
        return (num / den) if den else 0.0

    def body_value(self, r: tuple, c: tuple) -> Any:
        if not self.is_pct:
            return self.body.get(r + c)
        num = self.k_body.get(r + c, 0)
        if self.agg == "pct_row":
            den = self.k_row.get(r, 0)
        elif self.agg == "pct_col":
            den = self.k_col.get(c, 0)
        else:  # pct_total
            den = self.k_grand
        return self._ratio(num, den)

    def col_total_value(self, r: tuple) -> Any:
        """Columna Total (agrega todas las columnas para la fila r)."""
        if not self.is_pct:
            return self.col_total.get(r)
        row_n = self.k_row.get(r, 0)
        if self.agg == "pct_row":
            return 1.0 if row_n else 0.0
        # pct_col / pct_total: la fila completa sobre el gran total.
        return self._ratio(row_n, self.k_grand)

    def row_total_value(self, c: tuple) -> Any:
        """Fila Total (agrega todas las filas para la columna c)."""
        if not self.is_pct:
            return self.row_total.get(c)
        col_n = self.k_col.get(c, 0)
        if self.agg == "pct_col":
            return 1.0 if col_n else 0.0
        # pct_row / pct_total: la columna completa sobre el gran total.
        return self._ratio(col_n, self.k_grand)

    def corner_value(self) -> Any:
        """Esquina Total×Total."""
        if not self.is_pct:
            return self.corner
        return 1.0 if self.k_grand else 0.0


# ─────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────


def pivot(df: pd.DataFrame, spec: PivotSpec | dict) -> PivotResult:
    """Calcula un pivote declarativo sobre `df`.

    Args:
        df: DataFrame de origen (ya cargado; el motor no toca DB/IO).
        spec: `PivotSpec` o dict con la misma forma.

    Returns:
        `PivotResult` serializable a JSON.

    Raises:
        ValueError: si algún campo de `rows`/`cols`/`values` no existe en
            `df` (mensaje con los campos faltantes y las columnas disponibles).
    """
    spec = _coerce_spec(spec)
    rows = list(spec.rows)
    cols = list(spec.cols)
    values = spec.values
    total_label = spec.total_label

    # Validación de campos.
    needed = rows + cols + [v.field for v in values]
    missing = [f for f in needed if f not in df.columns]
    if missing:
        raise ValueError(
            f"Campos inexistentes en el DataFrame: {sorted(set(missing))}. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    n_source_rows = int(len(df))
    do_col_total = spec.totals.cols and len(cols) > 0
    do_row_total = spec.totals.rows

    meta = PivotMeta(
        n_source_rows=n_source_rows,
        has_totals={"rows": do_row_total, "cols": do_col_total},
        aggs=[{"field": v.field, "agg": v.agg, "label": v.display_label(), "format": v.format} for v in values],
        total_label=total_label,
    )

    # DataFrame vacío → resultado vacío pero válido.
    if n_source_rows == 0:
        return PivotResult(row_fields=rows, col_fields=cols, columns=[], rows=[], meta=meta)

    # Descartar filas con NaN en dimensiones de agrupación (coherencia de keys
    # y totales). n_source_rows ya quedó con el largo original.
    group_dims = rows + cols
    dfg = df.dropna(subset=group_dims) if group_dims else df

    row_keys = _ordered_keys(dfg, rows, spec.order)
    col_keys = _ordered_keys(dfg, cols, spec.order)  # [()] si no hay cols

    calcs = [
        _MetricCalc(dfg, rows, cols, v.field, v.agg, do_col_total, do_row_total)
        for v in values
    ]

    # ── Columnas: (combinación de columna) × (métrica), + columnas Total ──
    columns: List[PivotColumn] = []
    # col_plan: lista de (tipo, metric_idx, col_key) alineada con `columns`.
    col_plan: List[Tuple[str, int, Optional[tuple]]] = []
    for c in col_keys:
        for i, v in enumerate(values):
            columns.append(PivotColumn(
                keys=[_keystr(x) for x in c],
                field=v.field, agg=v.agg, label=v.display_label(), is_total=False,
            ))
            col_plan.append(("body", i, c))
    if do_col_total:
        for i, v in enumerate(values):
            columns.append(PivotColumn(
                keys=[total_label],
                field=v.field, agg=v.agg, label=v.display_label(), is_total=True,
            ))
            col_plan.append(("coltotal", i, None))

    # ── Filas de datos ──
    out_rows: List[PivotRow] = []
    for r in row_keys:
        cells: List[PivotCell] = []
        for kind, i, c in col_plan:
            v = values[i]
            if kind == "body":
                raw = calcs[i].body_value(r, c)
                fill = None if v.is_pct() else spec.fill_value
                cells.append(_make_cell(raw, v.format, v.agg, fill))
            else:  # coltotal
                raw = calcs[i].col_total_value(r)
                cells.append(_make_cell(raw, v.format, v.agg, None))
        out_rows.append(PivotRow(keys=[_keystr(x) for x in r], cells=cells, is_total=False))

    # ── Fila Total ──
    if do_row_total:
        cells = []
        for kind, i, c in col_plan:
            v = values[i]
            if kind == "body":
                raw = calcs[i].row_total_value(c)
            else:  # esquina Total×Total
                raw = calcs[i].corner_value()
            cells.append(_make_cell(raw, v.format, v.agg, None))
        out_rows.append(PivotRow(keys=[total_label], cells=cells, is_total=True))

    return PivotResult(row_fields=rows, col_fields=cols, columns=columns, rows=out_rows, meta=meta)


def pivot_to_dataframe(result: PivotResult) -> pd.DataFrame:
    """Convierte un `PivotResult` a un DataFrame plano para Word/PDF.

    - Columnas iniciales = los campos de fila (`row_fields`); sus valores son
      `row.keys` (la fila Total lleva el `total_label`).
    - Una columna por cada `PivotColumn`, con el **display** (string ya
      formateado — es lo que Word/PDF renderizan). El número crudo sigue en
      `result.rows[i].cells[j].value` si se necesita.
    - Encabezado de cada columna de datos = niveles de columna + etiqueta de
      métrica (según haga falta para desambiguar). Las columnas/filas Total
      quedan presentes con el `total_label`.

    Consistente con `PivotResult`: mismos valores (displays) en el mismo
    orden.
    """
    total_label = result.meta.total_label
    n_values = len(result.meta.aggs)
    multi_value = n_values > 1
    has_col_fields = len(result.col_fields) > 0

    # Encabezados de las columnas de datos.
    data_headers: List[str] = []
    for col in result.columns:
        level = " · ".join(col.keys) if col.keys else ""
        if has_col_fields or col.is_total:
            # Hay niveles de columna (o es Total): mostrar nivel + métrica si
            # hay varias métricas.
            header = f"{level} · {col.label}" if (multi_value and level) else (level or col.label)
        else:
            # Sin campos de columna: una columna por métrica.
            header = col.label
        data_headers.append(header)

    # Desambiguar headers repetidos.
    seen: Dict[str, int] = {}
    unique_headers: List[str] = []
    for h in data_headers:
        if h in seen:
            seen[h] += 1
            unique_headers.append(f"{h} ({seen[h]})")
        else:
            seen[h] = 0
            unique_headers.append(h)

    row_field_names = list(result.row_fields)
    records: List[Dict[str, Any]] = []
    for row in result.rows:
        rec: Dict[str, Any] = {}
        for idx, fname in enumerate(row_field_names):
            if row.is_total:
                rec[fname] = total_label if idx == 0 else ""
            else:
                rec[fname] = row.keys[idx] if idx < len(row.keys) else ""
        for header, cell in zip(unique_headers, row.cells):
            rec[header] = cell.display
        records.append(rec)

    columns_order = row_field_names + unique_headers
    df = pd.DataFrame.from_records(records, columns=columns_order) if records else pd.DataFrame(columns=columns_order)
    return df


__all__ = [
    "pivot",
    "pivot_to_dataframe",
    "PivotResult",
    "PivotColumn",
    "PivotRow",
    "PivotCell",
    "PivotMeta",
]
