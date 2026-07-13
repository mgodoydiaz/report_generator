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

---

## Estado de implementación — PARTE B1 (consumidores backend + migración)

Hecho sobre el motor ya probado (PARTE A). Todo lo de W2-B1 usa el mismo
`pivot(df, spec)` → una sola fuente de verdad.

### Consumidores cableados

1. **Dashboard web** — `backend/routers/tables.py`.
   Una `TableConfig` gana el campo opcional `pivot: PivotSpec`
   (`backend/schemas_table.py`). Si está definido:
   - `GET /api/tables/{id}/data` y `POST /api/tables/preview` devuelven el
     `PivotResult` en vez de la respuesta tabular clásica. **Forma exacta**:
     ```json
     {
       "mode": "pivot",
       "pivot": { /* PivotResult.model_dump(mode="json") */ },
       "n_rows": 120
     }
     ```
     Cuando `pivot` es `None` la respuesta tabular clásica
     (`{columns, rows, total_rows, limit, offset}`) queda intacta — sin
     regresión para las tablas existentes.
   - El `data_source` (metric_id + filters + derived_fields_override) se usa
     igual para cargar el df; el `PivotSpec` opera sobre ese df ya cargado.
     Las `columns`/`behavior` clásicas se ignoran en modo pivote.

2. **Informe PDF v2** — `backend/rgenerator/reports/`.
   - `tables.py`: nueva fn `tabla_pivote(df, spec, filtro=None, **params)`
     registrada en `TABLE_REGISTRY`. Envuelve
     `pivot_to_dataframe(pivot(df, spec))`. `filtro={campo: valor}`
     pre-filtra el df (para pivotes por curso/categoría).
   - `runtime.py`: nuevo tipo de sección `"pivot"` (azúcar sobre
     `tabla_pivote`): la sección declara `spec` (un PivotSpec) y opcional
     `filtro`. También funciona la vía `{"tipo": "table", "fn":
     "tabla_pivote", "params": {"spec": {...}}}`.
   - **Multi-pivote**: varias secciones `pivot`. **Pivote por curso**: usar
     las secciones dinámicas (`iterar_por`) + `filtro={"Curso": "{curso}"}`
     — la interpolación `{curso}` del runtime concreta el valor por iteración.

3. **Export Excel** — `GET /api/tables/{id}/export-pivot`
   (`backend/routers/tables.py`). Corre el motor sobre el df de la tabla
   (modo pivote) y devuelve un `.xlsx` (openpyxl) con **valores crudos** y
   `number_format` derivado del `format` del spec (`.1%`→`0.0%`,
   `.2f`→`0.00`, count→`0`). Auth JWT + multi-tenant por `org_id` (404
   cross-org). 400 si la tabla no está en modo pivote.

### Contrato para la PARTE B2 (frontend)

- **Cómo el usuario declara un pivote**: en el editor de tablas, setear el
  campo `pivot` de la `TableConfig` con un `PivotSpec`
  (`rows`, `cols`, `values:[{field, agg, label, format}]`, `totals`,
  `order`, `fill_value`, `total_label`). Si `pivot` está presente la tabla
  es un pivote; si es `null` es tabular clásica.
- **Endpoint a consumir**: `GET /api/tables/{id}/data` (o `POST
  /api/tables/preview` con la config en el body). Respuesta con
  `{"mode": "pivot", "pivot": <PivotResult>, "n_rows"}`.
- **Forma del `PivotResult`** (ver `pivot_engine.py`): `row_fields`,
  `col_fields`, `columns:[{keys, field, agg, label, is_total}]`,
  `rows:[{keys, cells:[{value, display}], is_total}]`, `meta`. `cells[i]`
  está alineada posicionalmente con `columns[i]`. `value` = número crudo (o
  `null`); `display` = string ya formateado.
- **Descarga Excel**: `GET /api/tables/{id}/export-pivot`.

### Migración del pivote existente

- **`_table_section` PivotTable (PDF v1)** — `report_steps.py`: MIGRADO.
  Ahora delega la agregación en `pivot_engine` vía el helper
  `_pivot_table_via_engine`, conservando byte-a-byte el formato de salida
  histórico (`{columns, rows}`, orden lexicográfico, 2 decimales, conteo
  entero, "—"). Regresión fijada con snapshot en
  `tests/steps/test_pivot_migration.py`.

- **`pivot_matrix` chart_type (`charts.py _build_dataset`)** — **NO
  migrado (TODO justificado)**. `pivot_matrix` no es un pivote numérico:
  cada celda es un **valor categórico** ("primer" `Nivel de Riesgo` por
  combinación) que luego se colorea según `achievement_levels`. El motor
  W2 produce **agregaciones numéricas** (`PivotCell.value: Optional[float]`)
  y no puede representar celdas string sin cambiar su firma/tests (fuera de
  alcance por instrucción). Es un "roster matrix", concepto distinto al
  pivote de este workstream. Se deja como está, con este TODO citando el
  diseño; migrarlo requeriría extender el contrato del motor con un modo
  categórico/`first` — evaluar en un workstream aparte.

### Tests

- `tests/routers/test_pivot_endpoints.py` — integración de los 3
  consumidores (dashboard PivotResult, Excel .xlsx válido, PDF v2 bytes sin
  `{{`), paridad de números entre los tres, y multi-tenant (404 cross-org).
- `tests/steps/test_pivot_migration.py` — regresión del PivotTable v1
  (snapshot pre-migración).
- Suite completa: **703 passed, 3 skipped** (`pytest -q -m "not slow"`),
  cero regresiones sobre la base de 685.

---

## Estado de implementación — PARTE B2 (frontend)

Hecho sobre el contrato de la PARTE B1 (arriba). `npm run build` pasa limpio.

### Render — `frontend/src/tooling/plotly-charts/pivotTable.jsx`

El archivo ahora exporta **dos** componentes:

- **`PivotResultTable({ pivotResult })`** — NUEVO. Render puro de un
  `PivotResult` calculado por el backend, sin agregación en JS. Encabezado
  en 1 o 2 filas: una fila de "nivel" (agrupa columnas que comparten el
  mismo `keys.join(' · ')`, con `colSpan`, solo si `col_fields.length>0`) y
  una fila de "métrica" (`col.label`, siempre presente — desambigua cuando
  hay 2+ `values` bajo el mismo nivel). Columnas/filas con `is_total` se
  estilan en negrita + fondo `slate-100`. Celdas con `value:null` y
  `display:""` se muestran como "—" en gris tenue. Es lo que usa
  `TableRenderer` cuando la respuesta trae `mode:"pivot"`.
- **`PivotTable(...)`** — se mantiene el componente LEGACY intacto en su
  modo "raw"/categórico (`pivotConfig.value` + `semaphoreField`, usado por
  el Roster IDEL armado por `scripts/apply_pdl_layout_v2.py` vía el item de
  dashboard `type:"PivotTable"`). **No se migró** por la misma razón que
  `pivot_matrix`: el motor W2 solo produce `PivotCell.value: float|null`,
  no puede representar el valor categórico más frecuente por celda + su
  color de `achievement_levels`. El modo agregado clásico anterior
  (`pivotConfig.values` con `aggregation` calculado en JS) SÍ se retiró —
  era la implementación fragmentada que este workstream unifica — y ahora
  muestra un aviso ("este modo se migró... crea una Tabla Pivote nueva
  desde Tablas") en vez de calcular nada en el cliente.

### Fetch — `frontend/src/components/tables/TableRenderer.jsx`

Detecta `data.mode === "pivot"` en la respuesta de `GET /tables/{id}/data`
y `POST /tables/preview`; en ese caso guarda el `PivotResult` en estado y
renderiza `PivotResultTable` en vez de la tabla TanStack clásica (que sigue
intacta para `mode` tabular). Modo pivote y modo clásico son mutuamente
excluyentes en el mismo componente según lo que responda el backend — cero
cambios de contrato para los consumidores tabulares existentes.

### Editor — `frontend/src/components/add-component/PivotTableConfig.jsx`

Reescrito para construir un `PivotSpec` (no el `pivotConfig` viejo):
zonas de drag&drop Filas/Columnas (multinivel, sin límite) y Valores
(`field` + `agg` — select con las 11 agregaciones del backend, `mean` por
default — + `label` y `format` editables por valor), más dos checkboxes
para `totals.rows`/`totals.cols` (default `true`, igual que el backend).
`onConfirm` emite `{rows, cols, values:[{field,agg,label,format}], totals}`
listo para `TableConfig.pivot`. Props cambiaron de
`{allMetrics,allDimensions,derivedColumns}` a `{fields}` (catálogo plano
`{field,label,kind}`) para poder reusarse tanto desde el editor viejo
(`StepConfig.jsx`, que sigue armando `fields` con
`buildAvailableFields()`) como desde la página **Tablas** (`fields` desde
`metricColumns` de la métrica seleccionada).

Nueva pestaña **"Pivote"** en `frontend/src/pages/Tables.jsx` (junto a
Origen/Columnas/Comportamiento): botón "Activar modo Pivote" (no escribe
`config.pivot` hasta que el usuario arma un spec válido — evita disparar un
preview con `rows`/`values` vacíos, que el backend rechaza con 422) →
`PivotTableConfig` → al aplicar, guarda en `config.pivot`. Botón "Quitar
pivote" vuelve a tabla clásica. Tabs Columnas/Comportamiento muestran un
aviso cuando `config.pivot` está activo (esos campos se ignoran en modo
pivote, según el contrato de B1).

### Descarga Excel

Botón "Exportar Excel" en la toolbar de `TableRenderer` (solo visible en
modo pivote): pega a `GET /api/tables/{id}/export-pivot` con `fetchAuth`
del `AuthContext` (mismo patrón de descarga de blob que
`GenerateReportV2Modal.jsx`) y dispara la descarga del `.xlsx`. Deshabilitado
si no hay `tableId` (modo preview con `draftConfig` sin persistir — el
endpoint de export requiere una tabla guardada). En la página Tablas, el
panel de preview usa la tabla persistida (`tableId={selectedId}`) en vez
del draft cuando no hay cambios sin guardar, precisamente para habilitar el
botón de export durante el preview.

### Desvíos del contrato / cosas a revisar manualmente en la UI

1. **Sin test runner de frontend** — verificado solo con `npm run build`
   (pasa limpio) y lectura de código; no hubo smoke test en navegador con
   sesión autenticada (bloqueado por el clasificador de auto-mode al
   intentar generar credenciales locales de prueba). **Recomendado**:
   antes de dar por cerrado B2, abrir `/tables`, crear una tabla con
   `pivot` (rows multinivel + cols + 2 values + totales) y verificar
   visualmente el render (headers agrupados, fila/columna Total en negrita,
   celdas vacías) y la descarga de Excel.
2. **Header multinivel simplificado**: cuando `col_fields.length > 1`, en
   vez de una fila de encabezado POR nivel (ej. una fila "Mes", otra fila
   "Curso"), se muestra una única fila de "nivel" con los valores unidos
   por `" · "` (ej. "Marzo · IIA"). Se eligió así porque las columnas Total
   del motor llevan `keys:[total_label]` (un solo elemento) sin importar
   cuántos `col_fields` haya — un header verdaderamente por-nivel necesita
   `rowSpan` especial para la columna Total que se decidió no implementar
   por complejidad/riesgo. El resultado es correcto y legible, solo no es
   "N filas, una por nivel".
3. **Item legacy de dashboard `PivotTable` con `pivotConfig.values`**
   (modo agregado viejo, si existiera guardado en algún indicador) ahora
   renderiza un aviso en vez de una tabla — no se encontró ningún indicador
   con ese modo en `db_seed.json` (0 matches), pero no se pudo verificar
   contra la base Postgres de producción/staging real. Si aparece en algún
   dashboard tras el deploy, hay que recrearlo como Tabla Pivote nueva
   (página Tablas) y agregarla al layout como item `configured_table`.
4. **`componentDefs.js` no se tocó**: se dejó la entrada `PivotTable` en
   `TABLE_COMPONENTS` intacta para no romper la edición de items ya
   guardados (`AddComponentModal` busca el componente por id — si se
   borra, la edición de items existentes deja de encontrar el def). Solo
   se actualizó el call site en `StepConfig.jsx` para pasarle `fields` en
   vez de `allMetrics/allDimensions/derivedColumns` al nuevo
   `PivotTableConfig`.
