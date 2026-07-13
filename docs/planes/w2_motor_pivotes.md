# W2 — Motor de pivotes (base del multi-pivote)

Rama: `feature/w2-motor-pivotes` (sobre `dev2`). Workstream W2 del
[Plan Maestro](./plan_maestro_arquitectura.md).

Decisiones del dueño (2026-07-12):
- **Agregaciones**: todas — promedio, conteo, porcentaje/distribución, suma,
  y estadísticos (mediana, min, max, desviación).
- **Totales**: fila y columna.
- **Consumidores**: los tres a la vez (dashboard web, informes PDF, export Excel).
- **Pivote existente**: construir el motor nuevo y **migrar ya** las
  implementaciones actuales para que todo use una sola fuente.

Objetivo: una única función pura de pivote server-side, declarativa, que
reemplace las implementaciones fragmentadas de hoy y sea la base del
"multi-pivote para informes".

## Fragmentación actual (lo que se unifica)

| Implementación | Ubicación | Rol |
|---|---|---|
| `pivot_matrix` chart_type | `backend/schemas_chart.py:78` + `charts.py _build_dataset` | pivote coloreado del dashboard (Roster IDEL) |
| `PivotTable` PDF v1 | `backend/rgenerator/core/report_steps.py:797` (`pivotConfig`) | tabla pivote en el informe PDF v1 |
| `PivotTable` Plotly | `frontend/src/tooling/plotly-charts/pivotTable.jsx` + `add-component/PivotTableConfig.jsx` | render web |
| groupbys ad-hoc | varias funciones de `reports/tables.py`, `analysis_tools.py` | tablas de resumen |

Enum de agregación existente a respetar/extender: `schemas_chart.py:174`
(`mean|sum|min|max|count|nunique`) — el motor lo amplía con `median`, `std`,
`pct` (porcentaje sobre total de fila/columna/global).

## Mapa de archivos (dónde vive cada cosa)

```
backend/rgenerator/core/
└── pivot_engine.py              NUEVO — pivot(df, spec) -> PivotResult (función pura)
backend/
├── schemas_pivot.py             NUEVO — PivotSpec (Pydantic): rows, cols, values, totals, order, format
├── routers/tables.py            + usa pivot_engine para configured_table tipo pivote
├── routers/reports.py|charts.py + endpoint export Excel del pivote
└── rgenerator/reports/
    ├── tables.py                + fn de tabla que envuelve pivot_engine (para PDF v2)
    └── runtime.py               + tipo de sección "pivot" (multi-pivote en informes)
backend/rgenerator/core/report_steps.py   MIGRA _table_section PivotTable → pivot_engine
frontend/src/tooling/plotly-charts/pivotTable.jsx   MIGRA a consumir el pivote ya calculado por el backend
tests/steps/test_pivot_engine.py          NUEVO — unit exhaustivo del motor
tests/routers/test_pivot_endpoints.py     NUEVO — integración de los 3 consumidores
docs/planes/w2_motor_pivotes.md           este archivo
```

Regla de localización: **todo lo de W2 lleva "pivot" en el nombre**.

## Contrato del motor

### `PivotSpec` (declarativo, JSON-serializable)
```json
{
  "rows": ["Curso"],                       // 1+ campos de agrupación en filas (multi-nivel)
  "cols": ["Mes"],                         // 0+ campos de agrupación en columnas
  "values": [                              // 1+ métricas a agregar (multi-value)
    {"field": "Logro", "agg": "mean", "label": "Logro prom.", "format": ".1%"}
  ],
  "totals": {"rows": true, "cols": true},  // fila Total y columna Total
  "order": {"Mes": ["Marzo","Abril","..."]}, // orden custom por campo (default: natural)
  "fill_value": null                        // valor para celdas sin datos
}
```

Agregaciones soportadas (`agg`): `mean`, `sum`, `count`, `nunique`, `min`,
`max`, `median`, `std`, `pct_row`, `pct_col`, `pct_total` (porcentaje de la
celda sobre el total de su fila / columna / global).

### `PivotResult` (lo que devuelve el motor)
```json
{
  "columns": [...],        // encabezados (con niveles si cols multi-nivel)
  "rows": [                // filas de datos, incluida la fila Total si aplica
    {"keys": ["II A"], "cells": [{"value": 0.85, "display": "85.0%"}, ...]}
  ],
  "meta": {"n_source_rows": 120, "aggs": [...], "has_totals": {...}}
}
```

`PivotResult` es serializable directo a: JSON para el dashboard, DataFrame
para Word (`tabla_desde_df`), HTML para el PDF v2 (`df_a_html_table`) y celdas
para `openpyxl` en el export Excel. Un solo cálculo, cuatro salidas.

### Firma
```python
def pivot(df: pd.DataFrame, spec: PivotSpec | dict) -> PivotResult: ...
def pivot_to_dataframe(result: PivotResult) -> pd.DataFrame: ...   # helper para Word/PDF
```

Implementación base sobre `pandas.pivot_table` + post-proceso para totales,
porcentajes, orden custom y formato. Función **pura** (sin DB, sin IO):
recibe el DataFrame ya cargado (los consumidores lo obtienen con la capa de
carga de métricas existente).

## Multi-pivote en informes

Una sección de informe declara una LISTA de `PivotSpec` (o un `PivotSpec`
iterado por un campo, ej. un pivote por curso). El `runtime.py` del motor PDF
v2 gana un tipo de sección `"pivot"` que consume `pivot_engine`; las secciones
dinámicas ya iteran por valor único, así que "un pivote por curso" sale casi
gratis. En Word, el módulo del informe pone `pivot_to_dataframe(pivot(...))`
en el contexto y usa `tabla_desde_df`.

## Plan de consumidores (los tres)

1. **Dashboard web**: `routers/tables.py` — cuando una `configured_table` es de
   tipo pivote, el backend devuelve el `PivotResult` ya calculado. El frontend
   `pivotTable.jsx` se simplifica a renderizar la matriz recibida (menos lógica
   en JS). Migrar `pivot_matrix`/`PivotTableConfig` al nuevo spec.
2. **Informe PDF**: `reports/tables.py` gana una fn registrada en `TABLE_REGISTRY`
   que envuelve el motor; el esquema declara `fn: "tabla_pivote"` con su
   `PivotSpec`. Migrar el viejo `_table_section` PivotTable de `report_steps.py`.
3. **Export Excel**: endpoint `GET` que corre el motor y escribe `.xlsx` con
   `openpyxl` (formato de celdas según `format` del spec). Descargable.

## Plan de pruebas de calidad

**Unit del motor** (`tests/steps/test_pivot_engine.py`) — el núcleo, TDD:
- Cada agregación con datos conocidos (mean/sum/count/median/std/min/max).
- Porcentajes: `pct_row` suma 100% por fila; `pct_col` por columna; `pct_total`
  global. Con celdas vacías y con NaN.
- Totales de fila y columna correctos y coherentes con las celdas.
- Multi-nivel en rows y cols; multi-value (2+ métricas en la misma tabla).
- Orden custom respetado; orden natural por defecto.
- Bordes: DataFrame vacío → resultado vacío sin crash; campo inexistente →
  error claro; una sola fila; valores no numéricos con agg numérica.
- `pivot_to_dataframe` reversible y consistente con `PivotResult`.

**Integración de consumidores** (`tests/routers/test_pivot_endpoints.py`):
- `configured_table` pivote devuelve el `PivotResult` esperado (dashboard).
- Export Excel produce un `.xlsx` válido con los valores correctos.
- PDF v2 con sección pivote genera bytes sin `{{` residual.
- Paridad: la MISMA `PivotSpec` da los mismos números en los tres consumidores
  (test de paridad — garantía de "una sola fuente").

**Regresión de migración**: los dashboards/informes que hoy usan
`pivot_matrix`/`PivotTable` siguen dando los mismos números tras migrar
(comparar contra un snapshot pre-migración).

**Manual** (gate): revisar un informe real con pivote (ej. Roster IDEL) y una
tabla del dashboard antes/después de la migración — mismos números, mismo look.

## Secuencia
1. **W2-A**: `pivot_engine.py` + `schemas_pivot.py` + unit exhaustivo. Nada más
   depende hasta que esto esté verde. (Opus — correctitud matemática crítica.)
2. **W2-B**: los tres consumidores + migración del pivote existente + tests de
   integración y paridad. (Sobre el motor ya probado.)
