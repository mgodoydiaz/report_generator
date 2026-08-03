# Mapa de capas de layout de informes

**Fecha**: 2026-08-03 · **Rama**: `dev` · Levantado con agentes para responder: *"¿dónde se configura el layout de cada informe?"*

## 0. Resumen en una frase

Hoy conviven **9+ capas** que deciden cómo se ve un informe, repartidas en 3 lugares distintos (columnas de `indicators`, JSON en disco, Python hardcodeado), y **ninguna cubre los 4 motores**. El contrato del motor único ya designó ganador — el módulo Python en `reports/custom/` — pero solo 1 de 6 indicadores está migrado.

---

## 1. Tabla maestra

| # | Capa | Qué controla exactamente | Dónde vive | Quién la escribe | Quién la lee | Motores |
|---|---|---|---|---|---|---|
| **C1** | `indicators.dashboard_layout` | Tabs, filas, nº de columnas y bloques del dashboard web. Nada del PDF. | `backend/models.py:222` · JSON `{tabs:[{id,label,rows:[{cols,items:[…]}]}]}` | `LayoutEditorModal.jsx:1027-1031` (modo Dashboard) → `PUT /indicators/{id}`; también `POST /indicators/{id}/layout`; seeders `scripts/_oneshot/dashboards_v2/*.py`; y `scripts/apply_pdl_layout_v2.py:186` (SQL crudo) | `frontend/src/tooling/dashboardRenderer.jsx:1191` | **dashboard** únicamente |
| **C2** | `indicators.pdf_layout` | Secciones del PDF "por evaluación": orden, tipo (`cover`/`chart`/`table`/`text`/`page_break`), `heading`, `item.component` + campos. Además `title`, `subtitle`, `mode`, **`engine`** y `branding` (logos por asset id, `center_header`, `left_footer`, `show_page_number`). | `backend/models.py:224` · ejemplos en `docs/desarrollo/pdf_layout_examples.md` | `LayoutEditorModal.jsx:871-995` (modo Informe PDF → "Por evaluación"); `scripts/_seed_validation_layouts.py:331`; **efecto lateral**: `indicators.py:1075-1086` cuando `save_as_default=true` | `report_steps.build_pdf_bytes` (`report_steps.py:1534`) | **v1** |
| **C3** | `indicators.pdf_layout_historico` | Idéntico a C2 pero para el informe histórico. | `backend/models.py:225` | igual que C2, sub-pestaña "Histórico" | `indicators.py:1050` | **v1** |
| **C4** | `indicators.report_engine_type` | **No define layout**: elige *qué motor* lo define. Resuelto por `engine_types.resolver_engine_type` con fallback heurístico por nombre. | `backend/models.py:226` | `NewIndicatorDrawer.jsx` | `indicators.py:420` (report-options), `indicators.py:909` | **enrutador de todos** |
| **C5** | `indicators.achievement_levels` | Nombres, **colores** y orden de los niveles de logro | `backend/models.py:221` | `NewIndicatorDrawer.jsx:412-447` | v1: `report_steps.py:655→799-826`. Único: `custom/simce.py:404`. Dashboard: `plotly-charts/constants.js:31`. **IDEL: NO la lee** | v1 · único · dashboard |
| **C6** | `Spec.charts_list` / `tables_list` | Config completa de un gráfico/tabla del catálogo: `data_source`, `mapping`, **`aesthetics`** (`color_overrides`, paletas, límites, orden) | `backend/models.py:102-103`; schema `backend/schemas_chart.py:177-231` | `pages/Charts.jsx` tab Estética; seeders `dashboards_v2/helpers.py:207-276` | Dashboard (`routers/charts.py:152-441` + `ChartRenderer.jsx`). **Ningún motor PDF la lee** | **dashboard** únicamente |
| **C7** | Esquemas en disco `reports/{simce,simce_panguipulli,dia}/esquema.json` | `title`, `subtitle`, `branding` (logos por *filename* en `reports/assets/`), `derived_fields`, secciones fijas/dinámicas | ese path | A mano en el repo | `runtime.construir_pdf` para `modo=None`; **solo `branding`** para el motor único (`custom/simce.py:186-191`) | **único** (y v2 "formato oficial") |
| **C8** | Secciones construidas **en Python** por el módulo custom | Todo el cuerpo del informe por modo: qué secciones, orden, `fn`/`params`, auto-omisiones, notas | `reports/custom/simce.py:404-880`; helpers en `custom/_secciones.py` | A mano en el repo | `runtime.construir_pdf(..., esquema=…)` (N5, `runtime.py:244-266`) | **único** |
| **C9** | `backend/schemas/esquema_informe*.json` (4 archivos) | Formato **legacy LaTeX**: variables de documento + secciones cuyo `contenido` apunta a `aux_files/*.xlsx\|*.png` | `backend/schemas/` | A mano | Step `RenderHtmlReport` — **capa huérfana**: sigue en `STEP_MAPPING` pero los steps que producían sus `aux_files` se removieron en B6b | **v1-pipeline (muerto)** |
| **C10** | Plantillas Word docxtpl | Estructura del .docx | `reports/word/templates/resumen_indicador.docx` (única) | Se edita en Word | `word/engine.py:197-213` | **Word** |
| **C11** | CSS embebido en templates HTML | Página, márgenes, tipografía, header/footer | v1: `templates/report_base.html:14-38` (carta, `3.5/2.5/2/2.5cm`, Segoe UI **11pt**). Único: `reports/templates/informe_base.html:14-37` (`3.5/2/2/2cm`, Segoe UI **10pt**, tablas 8/7/6pt) | A mano | WeasyPrint | v1 · único |
| **C12** | Estilo matplotlib de los PNG | Fuente, DPI, paletas de los gráficos dentro del PDF | v1: `report_steps.py:47-73`. v2/único: `reports/charts.py:11-20` y `:671-675` (`PALETAS_SEMAFORO`) | A mano | `_chart_to_png_b64` / `CHART_REGISTRY` | v1 · único |
| **C13** | Layout IDEL hardcodeado en matplotlib | Página completa: geometría, colores, órdenes, etiquetas, 6 funciones de página | `scripts/report_pdl_idel.py:65-150` + renders | A mano | `tooling/report_pdl_idel_tools.py:210` | **motor IDEL** |
| **C14** | Paletas y tipografía del frontend | Colores de series y de nivel por defecto, fuente de gráficos | `plotly-charts/constants.js:3-77`; **duplicados** en `tooling/charts/constants.js:9-12` y `ChartRenderer.jsx:18-27` (valores distintos); `PlotlyWrapper.jsx:4` (Inter, **no cargada** → system-ui) | A mano | dashboardRenderer / ChartRenderer | **dashboard** |
| **C15** | Branding transversal | Regla dura: pie izquierdo = nombre org; última línea del encabezado = período | `reports/branding.py:43-273` | Código | v1, único e IDEL | v1 · único · IDEL |

**Cosas que NO existen** (dato, no fallo): editor separado de `pdf_layout` (es un modo del mismo `LayoutEditorModal`); migraciones Alembic que siembren layouts; seeders de `dashboards_v2/` que escriban `pdf_layout` o `achievement_levels` (solo los leen); `pdf_layout` en vocabulario v2 (`configured_chart` está filtrado para PDF en `LayoutEditorModal.jsx:636-648`); `MODOS` en `dia.py`, `pdl_idel.py`, `simce_panguipulli.py` (solo `custom/simce.py:70`).

---

## 2. Cadena de decisiones — SIMCE (motor único)

```
GET /indicators/{id}/report-options       indicators.py:371
  resolver_engine_type → "simce"                          [C4]
  _modulo_motor_unico → custom/simce.py · modos()=4       [C8]
  ⇒ el requisito de pdf_layout NO se evalúa (indicators.py:478-481)
POST /indicators/{id}/export-pdf {periodo:{tipo}}
  _resolver_periodo_a_filtros (periodos.py)
  branding_override center_header                          [C15]
  custom/simce.py:generar(modo)
    _niveles_y_colores(achievement_levels)                 [C5]
    secciones por modo, en Python                          [C8]
    branding base ← simce/esquema.json                     [C7]
    aplicar_pie_organizacion                               [C15]
    runtime.construir_pdf(esquema en memoria)              (N5)
      CHART_REGISTRY (matplotlib)                          [C12]
      Jinja2 → informe_base.html                           [C11]
      WeasyPrint → bytes
```
**`pdf_layout` no participa en ningún punto.**

## 3. Cadena de decisiones — IDEL (v1 / pdl_idel)

```
report-options: engine "pdl_idel" pero modos()=[] ⇒ camino clásico
  exige pdf_layout.sections / pdf_layout_historico         [C2/C3]
export-pdf:
  engine = body.engine > pdf_layout.engine > "weasyprint"  (indicators.py:1063)
  save_as_default ⇒ REESCRIBE pdf_layout.branding          (indicators.py:1075-1086)
  (a) weasyprint → build_pdf_bytes: branding por asset id, secciones
      matplotlib, colores achievement_levels>fallback, report_base.html
  (b) pdl_idel → build_pdl_idel_pdf_bytes: TODO hardcodeado [C13]
      ⇒ ignora pdf_layout, achievement_levels y los templates
```
Cuál rama corre depende de un valor **persistido en la DB** (`pdf_layout.engine`), casi invisible en la UI.

---

## 4. Duplicaciones y conflictos

- **D1 · Colores de nivel, 4 fuentes divergentes**: DB `achievement_levels` (#22c55e Bajo Riesgo) vs frontend default (`constants.js` #16a34a) vs IDEL hardcodeado (#f59e0b para Alto Riesgo, #84cc16 Cierto) vs fallback v1 (`report_steps.py:49-53`, otra paleta). + una 5ª tabla por cantidad en `charts.py:671`. El mismo IDEL se ve con tres verdes distintos según dónde se mire.
- **D2 · Paleta categórica del frontend ×3**: dos copias literales + `ChartRenderer.jsx` con valores distintos.
- **D3 · `aesthetics.color_overrides` vs `achievement_levels`**: `Charts.jsx:551` copia manual (queda stale); el PDF del motor único lee `achievement_levels` y nunca mira `aesthetics`.
- **D4 · Tipografía**: Segoe UI 11pt (v1) / 10pt (único) / 9pt (matplotlib v1) / DejaVu Sans (IDEL) / Inter-no-cargada (frontend).
- **D5 · Márgenes distintos** entre los dos WeasyPrint que dicen replicar el mismo `.tex`.
- **D6 · Logos, 2 mecanismos incompatibles**: v1 por `OrganizationAsset` id; motor único por filename en `reports/assets/`. Subir logo desde la UI no afecta al motor único.
- **D7 · Vocabulario de componentes duplicado**: mismos nombres (`BarByGroup`, …) renderizados por matplotlib (PDF) y plotly (dashboard) sin código compartido y con defaults distintos.
- **D8 · Dos escritores compiten por `dashboard_layout` de IDEL**: `apply_pdl_layout_v2.py` (TrendKPI) vs `dashboards_v2/idel.py` (configured_chart). Gana el último que corra.
- **D9 · `pdf_layout` se reescribe como efecto lateral** de generar un PDF con `save_as_default=true`.
- **D10 · C9 es capa muerta pero cargada**: `RenderHtmlReport` sigue en `STEP_MAPPING` y `constants.js` publica `RenderPDFReport`, pero sus insumos ya no se pueden producir.

---

## 5. Veredicto

**No existe hoy un punto único**, y depende del indicador:

| Indicador | Dónde se cambia hoy el layout del PDF |
|---|---|
| SIMCE | `custom/simce.py` + `simce/esquema.json` (branding) — su `pdf_layout` es letra muerta |
| DIA | `dia/esquema.json` (formato oficial) **y** `pdf_layout`/`historico` (cards de período) — dos sitios, dos resultados |
| Panguipulli | solo `simce_panguipulli/esquema.json`; `pdf_layout` vacío ⇒ 0/4 cards |
| IDEL | `scripts/report_pdl_idel.py` (1132 líneas) **o** `pdf_layout`, según `pdf_layout.engine` |
| CV · FL | solo `pdf_layout` desde la UI; sin módulo custom |

**El contrato del motor único ya designó la fuente de verdad** (`contrato_motor_unico.md:12,93,171,256`): **C8 (módulo Python)** para la estructura, **C5** para colores, **C15** para branding transversal; `pdf_layout` queda como escape hatch hasta la fase 5. El código lo cumple donde está migrado (despacho, N5, SIMCE completo) y no lo cumple en el resto (solo 1/6 módulos declara `MODOS`; el branding del motor único quedó a caballo en `esquema.json`; `pdf_layout.engine` sigue en la precedencia del camino normal).

### Qué migrar hacia C8 (alcance fase 4/5, en orden de valor/esfuerzo)

1. Declarar `MODOS` en `dia.py`, `simce_panguipulli.py`, `pdl_idel.py` (Panguipulli pasa de 0/4 a 4/4 sin tocar su `pdf_layout`).
2. Crear `custom/calculo_veloz.py` y `custom/fluidez_lectora.py` + setear `report_engine_type` en DB.
3. Un solo resolver de branding (lee `OrganizationAsset`, cae a `reports/assets/`) → cierra D6 y saca C7 del camino.
4. **Una sola tabla de colores de nivel**: que IDEL reciba `achievement_levels` (hoy la ignora) y el frontend elimine su default divergente → cierra D1. El mejor valor/esfuerzo de la lista.
5. CSS compartido (`@page`) entre los dos templates WeasyPrint → cierra D4/D5.
6. Retirar C9 completa (step, schemas, funciones LaTeX de `report_tools.py`).
7. Fase 5: `build_pdf_bytes` solo tras `body.engine` explícito; quitar `pdf_layout.engine` de la precedencia.

### ⚠️ Riesgo operativo inmediato

`db_seed.json` en la raíz del repo está **stale**: `report_engine_type=None`, `pdf_layout=null` y `achievement_levels` en formato pre-color. Un `db_seed.py import --clear` con ese archivo **destruiría C2, C3 y C5 de golpe**.
