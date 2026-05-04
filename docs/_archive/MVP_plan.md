# Plan MVP — Gráficos + Builder de tablas + Generador de PDF

## Context

La fundación tiene operativo el pipeline de ETL y guardado de métricas en PostgreSQL, pero el stack de visualización y generación de informes está incompleto:

- **Biblioteca de gráficos** tiene 14 tipos Plotly (barras, boxplot, pie, radar, tendencia, etc.) pero le faltan tipos que la fundación pide para PDL y otras evaluaciones (heatmap, histograma, gauge).
- **Tablas** hoy requieren configuración manual (JSON + componente JSX). No hay builder visual; el usuario no puede crear una tabla desde la UI.
- **Generación de PDF** usa LaTeX/xelatex, que no está instalado en el Docker actual y pesa ~1 GB. ROADMAP#6 ya lo tiene marcado como deuda técnica. No hay UI para configurar qué va al informe — todo es JSON en `reports_templates/`.

Además, la métrica `Resultados IDEL` (id 8) debe renombrarse a `Resultados PDL` porque es el nombre interno correcto que usa la fundación.

El MVP va hasta producción (`main`), por lo que cada cambio debe respetar el flujo `dev → devtest → main`, incluir migración Alembic cuando toque el schema, y tests básicos.

**Fuera de scope (fase 2):** Dashboard preset de PDL, step de código Python aprobado, lectura de múltiples fuentes externas (API/CSV/DB).

---

## Milestones

### M0 — Rename IDEL → PDL ✅ COMPLETADO

**Objetivo:** Cambiar el nombre de la métrica id 8 de `Resultados IDEL` a `Resultados PDL`.

**Cambios:**
- `UPDATE metrics SET name = 'Resultados PDL' WHERE id_metric = 8;` en la DB dev/staging/prod.
- Buscar referencias literales a "IDEL" en `backend/` y `frontend/` — probablemente ninguna hardcodeada, pero confirmar con Grep.

**Estado:** Aplicado en dev DB. Pendiente aplicar en staging/prod en M4.

**Verificación:** `GET /api/metrics/` devuelve el nuevo nombre; el Dashboard lo lista.

---

### M1 — Ampliar biblioteca de gráficos: Heatmap, Histograma, Gauge ✅ COMPLETADO

**Objetivo:** Agregar 3 tipos de gráfico Plotly al catálogo, disponibles desde `AddComponentModal`.

**Archivos entregados:**
- `frontend/src/tooling/plotly-charts/distribution.jsx` — `Histogram` agregado.
- `frontend/src/tooling/plotly-charts/heatmap.jsx` (nuevo) — `HeatmapMatrix`.
- `frontend/src/tooling/plotly-charts/gauge.jsx` (nuevo) — `GaugeIndicator` con umbrales verde/amarillo/rojo.
- `componentDefs.js` — grupo nuevo `matrix` para heatmap; entradas para los 3 componentes.
- `dashboardRenderer.jsx` — `COMPONENT_MAP`, `PLOTLY_REQUIRED_FIELDS`, `AUTO_TITLES`, `buildComponentProps`.

**Verificación pendiente (QA_manual.md › M1):** probar en UI con datos de PDL.

---

### M2 — Builder visual de tablas (incremental en 3 fases)

**Objetivo:** UI para crear tablas sin tocar código. Se entrega incrementalmente: primero pivote (cubre 80%), luego plana, luego fórmulas.

#### M2.1 — Tabla pivote ✅ COMPLETADO

Usuario arrastra campos a 3 zonas: **Filas / Columnas / Valores** (con agregación por campo).

**Archivos entregados:**
- `frontend/src/tooling/plotly-charts/pivotTable.jsx` — `PivotTable` con cross-tabulation JS puro.
- `frontend/src/components/add-component/PivotTableConfig.jsx` — UI con DnD HTML5 nativo, 3 drop zones, selector de agregación por valor.
- `frontend/src/components/add-component/fieldUtils.js` (nuevo) — helper `buildAvailableFields` compartido.
- `componentDefs.js`, `StepConfig.jsx`, `dashboardRenderer.jsx` actualizados.

**Verificación pendiente (QA_manual.md › M2.1).**

#### M2.2 — Tabla plana con filtros interactivos ✅ COMPLETADO

Usuario elige columnas, campos de filtro (dropdowns en runtime) y orden por defecto.

**Archivos entregados:**
- `frontend/src/tooling/plotly-charts/tables.jsx` — nuevo componente `FilterableTable` con barra de filtros, sort clickable por encabezado, contador de filas.
- `frontend/src/components/add-component/FlatTableConfig.jsx` (nuevo) — UI de configuración (columnas, filtros, sort).
- `componentDefs.js`, `StepConfig.jsx`, `dashboardRenderer.jsx` actualizados.

**Verificación pendiente (QA_manual.md › M2.2).**

#### M2.3 — Campos derivados globales en el indicador

**Decisión de diseño:** los campos calculados se definen a nivel de indicador (no dentro de cada tabla),  
para que cualquier componente del dashboard —gráficos, tablas, KPIs— los consuma como si fueran campos reales.

**Flujo de usuario:**
1. En el editor del indicador → nueva tab/sección **"Campos derivados"**.
2. El usuario define filas `nombre = expresión`, ej. `rendimiento_pct = correctas / total * 100`.
3. Al cargar el dashboard, el frontend aplica las expresiones sobre cada registro antes de pasarlos a `DashboardRenderer`.
4. Los campos derivados aparecen disponibles en `AddComponentModal` igual que cualquier campo de métrica.

**Schema DB — consolidar con M3.1:**  
Agregar `derived_columns` (Text/JSON) al modelo `Indicator` en la **misma migración Alembic** que `pdf_layout`, para no hacer dos migraciones separadas.

```json
// Ejemplo de derived_columns guardado en el indicador
[
  { "name": "rendimiento_pct", "label": "Rendimiento %", "expression": "correctas / total * 100" },
  { "name": "brecha",          "label": "Brecha",        "expression": "logro_1 - logro_2" }
]
```

**Archivos a crear/modificar:**

| Archivo | Cambio |
|---|---|
| `backend/models.py` | Agregar `derived_columns = Column(Text, default='[]')` a `Indicator` |
| `backend/schemas/indicators.py` | Incluir `derived_columns` en schemas Pydantic |
| `backend/routers/indicators.py` | `GET` y `PATCH` ya exponen todos los campos del modelo — sin cambio extra si el schema se actualiza |
| `alembic/versions/` | Una sola migración que añade `derived_columns` **y** `pdf_layout` (ver M3.1) |
| `frontend/src/tooling/formulaEvaluator.js` **(nuevo)** | Evaluador seguro de expresiones: soporta `+ - * / ( )`, nombres de campo, sin `eval()`. Implementar con parser recursivo o `mathjs` (verificar si ya está en deps) |
| `frontend/src/tooling/dashboardRenderer.jsx` | Aplicar `derived_columns` sobre `computed.estudiantes` antes de pasarlo a componentes |
| `frontend/src/components/LayoutEditorModal.jsx` | Nueva tab **"Campos derivados"** con lista editable de `nombre / expresión` |

**Evaluador de fórmulas — restricciones de seguridad:**
- Campos permitidos: solo nombres que existen en el record (`/^[a-z_][a-z0-9_]*$/`)
- Operadores: `+ - * / ( )`
- Funciones: `round()`, `abs()`, `min()`, `max()` (whitelist explícita)
- Sin `eval()` — usar parser recursivo propio o `mathjs` con scope controlado
- División por cero → `null` (no crash)

**Integración con `AddComponentModal`:**  
En `buildAvailableFields` de `fieldUtils.js`, incluir los `derived_columns` del indicador junto a los campos de métrica. El usuario los ve en la paleta de campos de `PivotTableConfig` y `FlatTableConfig` sin distinción.

**Verificación M2:**
- Definir campo derivado `rendimiento_pct = correctas / total * 100` en el editor del indicador.
- Crear `FilterableTable` con `rendimiento_pct` como columna visible.
- Crear `PivotTable` con `rendimiento_pct` en zona Valores, agregación `avg`.
- Crear `BarByGroup` con `rendimiento_pct` como `valueField`.
- División por cero → celda muestra `—` sin crashear.
- Expresión inválida (nombre de campo inexistente) → celda muestra `—` sin crashear.

---

### M3 — Generador de PDF configurable

**Objetivo:** UI (extensión de `LayoutEditorModal`) para definir qué gráficos/tablas de un Indicator van al informe PDF, en qué orden. Backend que genera el PDF con tecnología nueva.

#### M3.0 — Elegir tecnología de PDF (entregable de diseño)

**Spike técnico:** Crear un doc `docs/desarrollo/pdf-tech-comparison.md` con ejemplo funcional de cada opción (mismo informe dummy de 1 página con título, gráfico Plotly como PNG, tabla) en:

| Tech | Pros | Contras |
|---|---|---|
| **WeasyPrint** | HTML/CSS reutilizable del frontend, pip install, sin binarios | Imágenes Plotly requieren export a PNG server-side. Soporte parcial de flexbox/grid. |
| **Typst** | Binario único ~30MB, sintaxis amigable, tipografía de 1ra clase | Curva de aprendizaje (lenguaje nuevo). Requiere instalar ejecutable en Docker. |
| **ReportLab** | Python puro, control total | Código muy verboso, no reutiliza nada del stack web. |

**Decisión sugerida por mí:** WeasyPrint, por coherencia con el stack HTML/CSS del frontend. Confirmar tras ver ejemplos.

#### M3.1 — Schema en la DB (migración conjunta con M2.3)

Agregar **dos columnas** al modelo `Indicator` en `backend/models.py` en **una sola migración Alembic**:

```python
derived_columns = Column(Text, default='[]')   # M2.3 — campos calculados
pdf_layout      = Column(Text, default='{}')   # M3    — layout del informe PDF
```

**Alembic migration:**
```bash
alembic revision --autogenerate -m "add derived_columns and pdf_layout to indicators"
alembic upgrade head
```

Verificar que los schemas Pydantic en `backend/schemas/indicators.py` expongan ambos campos en `GET` y `PATCH`.

- Migrar en dev → test en devtest → aplicar en prod con ventana planificada.

#### M3.2 — UI en LayoutEditorModal

Agregar tab "Informe PDF" dentro de `LayoutEditorModal.jsx`, con:
- Lista ordenable (DnD) de secciones: portada, índice, gráfico, tabla, salto de página, texto.
- Para gráfico/tabla: dropdown que muestra los items ya presentes en `dashboard_layout` (reutiliza lo configurado) + opción de agregar uno nuevo vía `AddComponentModal`.
- Para portada/texto: input de título + contenido markdown.
- Preview button (M3 extra): llama al backend y descarga PDF.

**Archivo a modificar:** `frontend/src/components/LayoutEditorModal.jsx` (agregar `Tabs` y estado `pdfLayout`).

#### M3.3 — Backend: nuevo step `RenderPDFReport`

**Archivo nuevo:** `backend/rgenerator/core/report_steps.py` — agregar clase `RenderPDFReport(Step)` que:
1. Lee `indicator.pdf_layout` (desde `ctx.db`).
2. Para cada sección de tipo gráfico: hace una request interna al mismo backend para obtener datos → genera PNG con Plotly server-side (usar `plotly` + `kaleido`; ya están en requirements? verificar).
3. Para cada sección de tipo tabla: genera HTML.
4. Ensambla un HTML/CSS template con Jinja2 → pasa a WeasyPrint → produce PDF.
5. Guarda en `ctx.outputs_dir/informe.pdf`.

**Template HTML:** `backend/rgenerator/templates/report_base.html` **(nuevo)** con CSS compartido desde el frontend (copiar los tokens de color/tipografía a un `report.css`).

**Registro del step:**
- `backend/rgenerator/tooling/pipeline_tools.py` → agregar a `STEP_MAPPING`.
- `backend/rgenerator/core/pipeline_steps.py` → re-exportar.
- `frontend/src/constants.js` → `STEP_OPTIONS` + `STEP_TRANSLATIONS` + `STEP_DEFAULT_PARAMS`.

#### M3.4 — Endpoint directo para descarga

Alternativa al pipeline: endpoint `POST /api/indicators/{id}/export-pdf` que ejecuta el mismo flujo sin necesidad de un pipeline completo. Útil para el botón "Preview" de la UI.

**Archivo a modificar:** `backend/routers/indicators.py` — nuevo endpoint que construye un mini-pipeline con solo `RenderPDFReport` o llama la lógica directamente.

#### M3.5 — Docker + dependencias

- Agregar `weasyprint` a `requirements.txt`.
- Agregar a `Dockerfile` las dependencias del sistema de WeasyPrint (`libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz0b`).
- Agregar `kaleido` a `requirements.txt` si no está (para exportar Plotly a PNG server-side).

**Verificación M3:**
- Crear Indicator de PDL con layout de dashboard.
- En LayoutEditor → tab PDF: configurar portada + 2 gráficos + 1 tabla.
- Click "Descargar PDF" → recibe informe.pdf con layout correcto.
- Deploy en staging → probar con datos reales de la fundación.

---

### M4 — Deploy a producción

**Secuencia estándar del proyecto:**
1. Todo merge-able a `dev` tras tests verdes.
2. Cherry-pick o merge `dev → devtest`. Probar en Render staging con datos copiados.
3. Merge `devtest → main` con ventana de mantenimiento. Aplicar migraciones Alembic.
4. Smoke test: login admin, ver dashboard, descargar PDF.

---

## Archivos críticos (mapa rápido)

| Área | Archivo |
|---|---|
| Modelo Indicator | `backend/models.py` |
| Step base / context | `backend/rgenerator/core/step.py`, `context.py` |
| Steps existentes | `backend/rgenerator/core/report_steps.py`, `metric_steps.py` |
| Registro de steps | `backend/rgenerator/tooling/pipeline_tools.py` (STEP_MAPPING) |
| API indicators/results | `backend/routers/indicators.py`, `results.py` |
| Componentes gráficos Plotly | `frontend/src/tooling/plotly-charts/*.jsx` |
| Catálogo de componentes | `frontend/src/components/add-component/componentDefs.js` |
| Editor de dashboard | `frontend/src/components/LayoutEditorModal.jsx` |
| Modal crear componente | `frontend/src/components/add-component/AddComponentModal.jsx` |
| Renderer dashboard | `frontend/src/tooling/dashboardRenderer.jsx` |
| Config frontend steps | `frontend/src/constants.js` |
| Workflows docs | `.agents/workflows/add-step.md`, `add-chart.md` |
| Migraciones DB | `alembic/versions/` |

---

## Verificación end-to-end del MVP completo

1. **Login** como admin en dev Docker (`docker compose -f docker-compose.dev.yml up`).
2. **Métrica**: confirmar `Resultados PDL` en `/metrics`.
3. **Gráficos nuevos**: crear un Indicator de prueba → agregar componentes Heatmap, Histograma, Gauge con una métrica existente → verificar renderizado.
4. **Tabla pivote**: en el mismo Indicator, agregar PivotTable con Curso en filas, Asignatura en columnas, avg(Logro) en valores.
5. **Tabla plana con filtro**: agregar DetailListTable filtrado por Curso=2°A.
6. **Tabla con fórmula**: agregar columna calculada `Rendimiento %` = `correctas/total*100`.
7. **PDF**: en LayoutEditor → tab PDF: armar informe con portada + 2 gráficos + 1 tabla. Descargar → abrir PDF → validar que se ve ordenado y con datos correctos.
8. **Deploy devtest**: `git push devtest`, Render redeploy, probar el mismo flujo con credenciales de prueba.
9. **Deploy prod**: `git merge main`, aplicar Alembic, smoke test.

---

## Estado actual y orden de ejecución

```
M0  ✅ Completado
M1  ✅ Completado
M2.1 ✅ Completado
M2.2 ✅ Completado
M2.3 ← EN CURSO
 └─ M3.1 (migración conjunta derived_columns + pdf_layout · ~2 horas)
     └─ M3.0 (spike tech PDF · ~1 día) — en paralelo con M2.3 si se puede
         └─ M3.2 (tab PDF en LayoutEditorModal · ~2 días)
             └─ M3.2b (tab Campos Derivados en LayoutEditorModal · ~1 día)
                 └─ M3.3 (step RenderPDFReport · ~2 días)
                     └─ M3.4 (endpoint export-pdf · ~1 día)
                         └─ M3.5 (docker deps · ~medio día)
                             └─ M4 (deploy · ~1 día)
```

**Notas:**
- M2.3 y M3.1 se implementan juntos porque comparten la migración Alembic.
- M3.0 (elección de tecnología PDF) debe resolverse antes de empezar M3.3.
- M3.2 y M3.2b pueden ir en el mismo PR ya que tocan el mismo archivo (`LayoutEditorModal.jsx`).

Total restante estimado: **2-3 semanas**, con posibilidad de entregar M0–M2 a `dev` como release parcial.
