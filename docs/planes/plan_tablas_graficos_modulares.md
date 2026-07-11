# Plan: tablas y gráficos modulares (Python + JavaScript)

Fecha: 2026-07-11 · Basado en el recorrido con agentes sobre la rama `dev`.

## Diagnóstico (estado actual)

Hoy existen **cinco vocabularios** distintos para "definir un gráfico" y
**hasta 4 copias** del mismo código matplotlib:

| Definición | Dónde vive | Quién la renderiza |
|---|---|---|
| `Indicator.pdf_layout` (component switch) | DB | `report_steps._chart_to_png_b64` (matplotlib, switch hardcodeado) |
| `reports/<tipo>/esquema.json` (fn + registry) | repo | `reports/runtime.py` + `CHART_REGISTRY` |
| `charts_simce_lenguaje.json` (LaTeX legacy) | data/database | `scripts/generate_report.py` (xelatex) |
| `Spec.charts_list` (ChartConfig) | DB | frontend Plotly vía `ChartRenderer` |
| Props ad-hoc de `dashboard_layout` | DB | `dashboardRenderer.buildComponentProps` (switch de 370 líneas) |

Duplicaciones de código concretas:
- `grafico_barras_promedio_por`, `boxplot_valor_por_curso`, etc. existen en
  `tooling/plot_tools.py`, `reports/charts.py` y `docs/.../funciones.py` (copias textuales).
- `resumen_estadistico_basico` y tablas en `tooling/report_tools.py` + `reports/tables.py`.
- DataFrame→tabla: `df_a_latex_loop` (LaTeX), `df_to_html_table` (HTML v1), `df_a_html_table` (v2).
- Los nombres de componente (`BarByGroup`, `StackedCountByGroup`, …) están
  duplicados entre `_chart_to_png_b64` (Python) y `dashboardRenderer.COMPONENT_MAP` (JS)
  — cambiar uno obliga a sincronizar el otro a mano.
- Paletas repetidas en `ChartRenderer.jsx`, `plotly-charts/constants.js` y `report_steps.py`.

**Convergencia natural**: el modelo *registry de funciones + params declarativos*
que ya comparten `reports/charts.py` (Python) y `Spec.charts_list` (ChartConfig).

## Objetivo

Una sola forma de declarar un gráfico/tabla (`ChartConfig`/`TableConfig`), con
dos renderers intercambiables: **matplotlib** (informes PDF/Word, Python) y
**Plotly** (dashboards web, JS). Agregar un gráfico nuevo = 1 función Python
+ 1 componente Plotly + 1 entrada de metadata compartida.

## Fases

### F0 — Consolidación Python (bajo riesgo, ~1 sesión)
1. Declarar `backend/rgenerator/reports/charts.py` y `tables.py` como **única
   fuente**. `tooling/plot_tools.py` y `tooling/report_tools.py` pasan a
   re-exportar desde ahí (con DeprecationWarning) y se eliminan cuando nada
   los importe.
2. Unificar `_to_field_name` (hoy en `report_steps.py:84` y `reports/data.py:45`)
   en un módulo `core/naming.py`.
3. Extraer paleta/colores a `reports/theme.py` (semáforo, Set2, niveles IDEL)
   y consumirla desde charts v1 y v2.
4. Borrar del árbol lo ya muerto: `scripts/generate_report.py` + LaTeX legacy
   (queda en historia git), `report_docx_tools.py` (reemplazado por `reports/word/`).

### F1 — ChartConfig como contrato único (~1-2 sesiones)
1. Escribir `reports/spec_adapter.py`: `ChartConfig → llamada a CHART_REGISTRY`
   (mapea `chart_type` + `mapping` + `aesthetics` a la función matplotlib y
   sus params). Con esto un mismo Spec de la página /charts se puede
   renderizar como PNG para PDF/Word.
2. Extender `CHART_TYPE_META` (schemas_chart.py) con el campo `matplotlib_fn`
   junto al existente `plotly_component` — la metadata queda EN UN SOLO LUGAR
   y ambos mundos la leen.
3. Endpoint `GET /api/charts/render/{spec_id}.png` (debug/preview server-side).

### F2 — Motor PDF v1 sobre el registry (~1 sesión)
1. Reemplazar el switch de `_chart_to_png_b64` (report_steps.py:290) por el
   adapter de F1: `pdf_layout` sigue funcionando pero delega en las funciones
   registradas, no en código duplicado.
2. Idem `_table_section` → `TABLE_REGISTRY`.
3. `report_steps.py` (1327 líneas) queda reducido a orquestación.

### F3 — Frontend modular (~1-2 sesiones)
1. Matar Recharts legacy: migrar `SIMCE_PRESET_LAYOUT` y `Help.jsx` a
   componentes Plotly, script de migración para `dashboard_layout` guardados
   que nombren `Grafico*`, borrar `tooling/charts/` y `recharts` de package.json.
2. Partir `dashboardRenderer.jsx` (1278 líneas): `componentMap.js`,
   `buildProps/<familia>.js`, `presets/simce.js`.
3. Cliente API único (`src/api/client.js`) envolviendo `fetchAuth` — elimina
   los helpers duplicados de Tables.jsx/Charts.jsx y los `fetch` crudos.
4. Paletas y `formatValue` en un solo módulo (`src/tooling/theme.js`).

### F4 — Contrato generado (opcional, cuando duela)
`GET /api/reports/charts` ya expone el registry; generar de ahí un JSON de
contrato que el frontend valide en build (nombres de componentes/params
sincronizados automáticamente entre Python y JS).

## Orden recomendado y criterio de éxito

F0 → F2 → F1 → F3 (F0 y F2 eliminan la deuda más peligrosa: dos motores
matplotlib divergentes). Éxito = agregar un gráfico nuevo tocando:
`reports/charts.py` (fn) + `CHART_TYPE_META` (metadata) + 1 componente
Plotly. Nada más.
