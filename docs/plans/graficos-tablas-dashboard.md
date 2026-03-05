# Plan: Sistema de Gráficos, Tablas, Reportes y Dashboard

## Contexto

El proyecto genera reportes académicos (SIMCE) a través de pipelines ETL. Actualmente los schemas de gráficos y tablas existen como **archivos JSON sueltos** en `data/database/reports_templates/` sin estar integrados en el flujo de specs ni pipelines. La página `Results.jsx` es un stub. El objetivo es:

1. Formalizar el esquema de configuración de gráficos y tablas dentro de los specs
2. Mejorar `GenerateGraphics`/`GenerateTables` para producir metadata consumible por el frontend
3. Crear endpoints backend para servir resultados de pipeline runs
4. Implementar la página Results como dashboard de visualización

---

## Problema actual

- `charts_simce_lenguaje.json` y `tables_simce_lenguaje.json` no están referenciados desde ningún spec ni pipeline
- `get_spec_config` en `routers/specs.py:42-50` solo retorna 4 claves fijas (`variables_documento`, `secciones_fijas`, `secciones_dinamicas`, `etlParams`) — descarta cualquier otra clave como `charts_schema`
- `save_spec_config_logic` en `routers/specs.py:73-78` tiene el mismo problema al persistir
- `Results.jsx` es un placeholder `<UnderConstruction />`
- No hay endpoints para listar runs ni servir archivos generados

---

## Fase 1: Integrar schemas en specs (backend)

### 1.1 Ampliar persistencia de config_json en specs

**Archivo:** `backend/routers/specs.py`

**`get_spec_config` (línea 42-50):** Agregar al retorno:
```python
"charts_schema": config.get("charts_schema", []),
"tables_schema": config.get("tables_schema", []),
"report_schema": config.get("report_schema", {}),
```

**`save_spec_config_logic` (línea 73-78):** Agregar al `json_data`:
```python
"charts_schema": config.get("charts_schema", []),
"tables_schema": config.get("tables_schema", []),
"report_schema": config.get("report_schema", {}),
```

### 1.2 Formato propuesto para charts_schema

Extensión del formato actual, **backward-compatible** (campos nuevos son opcionales):

```json
[
  {
    "id": "rendimiento_promedio",
    "title": "Rendimiento Promedio por Curso",
    "category": "resumen",
    "type": "grafico_barras_promedio_por",
    "input_key": "df_enriched_estudiantes",
    "output_filename": "rendimiento_promedio_por_curso.png",
    "params": {
      "columna_valor": "Rendimiento",
      "agrupar_por": "Curso",
      "titulo": "Rendimiento Promedio por Curso",
      "ylabel": "Rendimiento (%)"
    }
  }
]
```

Campos nuevos opcionales:
- `id` — identificador corto para referencia entre secciones y dashboard
- `title` — título legible para el dashboard (distinto del `params.titulo` que va en el eje)
- `category` — agrupación en el dashboard (ej: `"resumen"`, `"evolucion"`, `"detalle_curso"`)

### 1.3 Formato propuesto para tables_schema

```json
[
  {
    "id": "resumen_logro",
    "title": "Resumen de Logro por Curso",
    "category": "resumen",
    "type": "resumen_estadistico_basico",
    "input_key": "df_enriched_estudiantes",
    "output_filename": "resumen_logro_por_curso.xlsx",
    "iterate_by": null,
    "params": { "columna": "Rendimiento", "formato": "percent", "agrupar_por": "Curso" }
  },
  {
    "id": "logro_por_alumno",
    "title": "Logro por Alumno",
    "category": "detalle_curso",
    "type": "tabla_logro_por_alumno",
    "input_key": "df_enriched_estudiantes",
    "output_filename": "logro_por_alumno_{val}.xlsx",
    "iterate_by": "Curso",
    "params": { "parametros": {}, "sort_by": "Rend" }
  }
]
```

### 1.4 Estructura completa de config_json de un spec

```json
{
  "etlParams": [...],
  "charts_schema": [...],
  "tables_schema": [...],
  "report_schema": {
    "variables_documento": {...},
    "secciones_fijas": [...],
    "secciones_dinamicas": [...]
  }
}
```

> `variables_documento`, `secciones_fijas` y `secciones_dinamicas` se mueven bajo `report_schema`.
> `LoadConfigFromSpec` ya copia claves desconocidas a `ctx.params` (líneas 248-253 de `init_steps.py`),
> así que `charts_schema`, `tables_schema` y `report_schema` llegan solos sin cambiar el step.

### 1.5 Crear spec de prueba

Migrar el contenido de:
- `data/database/reports_templates/charts_simce_lenguaje.json`
- `data/database/reports_templates/tables_simce_lenguaje.json`
- `data/database/reports_templates/esquema_informe_lenguaje.json`

...a un nuevo spec (id=4) con la estructura completa en `config_json`.

---

## Fase 2: Manifests en GenerateGraphics / GenerateTables

**Archivo:** `backend/rgenerator/etl/core/report_steps.py`

### 2.1 GenerateGraphics — generar charts_manifest

Al final de `GenerateGraphics.run()`, después de la línea 110:

```python
manifest = []
for chart_def in schema:
    manifest.append({
        "id": chart_def.get("id", chart_def.get("output_filename")),
        "title": chart_def.get("title", chart_def.get("params", {}).get("titulo", "")),
        "category": chart_def.get("category", ""),
        "filename": chart_def.get("output_filename"),
        "generated": chart_def["output_filename"] in generated_charts
    })

ctx.artifacts["charts_manifest"] = manifest

import json
with open(aux_dir / "charts_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
```

### 2.2 GenerateTables — generar tables_manifest

Análogo, después de la línea 238. Guarda `tables_manifest.json` en `aux_dir` y `ctx.artifacts["tables_manifest"]`.

---

## Fase 3: Endpoints de resultados (backend)

**Crear:** `backend/routers/results.py` (nuevo router separado de `pipelines.py`)

### 3.1 Listar runs de un pipeline

```
GET /api/pipelines/{pipeline_id}/runs
→ [{ "run_id": "20260305_143022", "has_charts": true, "has_tables": true, "has_report": true }]
```

Lee `data/pipeline_runs/runs/{pipeline_id}/`, lista subdirectorios, verifica existencia de manifests.

### 3.2 Obtener manifest de un run

```
GET /api/pipelines/{pipeline_id}/runs/{run_id}/manifest
→ { "charts": [...], "tables": [...], "outputs": {...} }
```

Lee `charts_manifest.json` y `tables_manifest.json` del `aux_files/` del run. Lista `outputs/` para reportes.

### 3.3 Servir archivos del run

```
GET /api/pipelines/{pipeline_id}/runs/{run_id}/files/{filename}
→ FileResponse (PNG, XLSX, PDF)
```

Sirve desde `data/pipeline_runs/runs/{pipeline_id}/{run_id}/aux_files/{filename}`.
Para outputs (PDF/DOCX), buscar también en `outputs/{filename}`.

### 3.4 Montar router en api.py

```python
from routers import results
app.include_router(results.router)
```

---

## Fase 4: Frontend Results.jsx

**Archivo:** `frontend/src/pages/Results.jsx`

### 4.1 Estructura de navegación (3 niveles)

1. **Lista de pipelines** con runs — grid de tarjetas (patrón de `Execution.jsx`)
2. **Lista de runs** de un pipeline — ordenados por fecha desc
3. **Dashboard de un run** — secciones de gráficos, tablas y reportes

### 4.2 Componentes nuevos

| Componente | Responsabilidad |
|---|---|
| `Results.jsx` | Página principal, lista pipelines con runs |
| `components/RunResultsView.jsx` | Dashboard de un run: secciones por categoría |
| `components/ChartCard.jsx` | Tarjeta con `<img>` del PNG, título, categoría |
| `components/TableCard.jsx` | Tarjeta con preview y botón de descarga Excel |

### 4.3 Patrón de carga

```
Results monta
  → fetch /api/pipelines (lista todos)
  → fetch /api/pipelines/{id}/runs (para cada uno, si tiene runs)

Click en pipeline → mostrar lista de runs

Click en run
  → fetch /api/pipelines/{id}/runs/{run_id}/manifest

Render gráficos
  → <img src="/api/pipelines/{id}/runs/{run_id}/files/{filename}">

Descargar tabla
  → <a href="/api/pipelines/{id}/runs/{run_id}/files/{filename}">
```

---

## Fase 5: Pipeline de dashboard completo

### 5.1 Pipeline JSON de ejemplo

```json
{
  "workflow_metadata": { "name": "Dashboard SIMCE Lenguaje" },
  "context": { "evaluation": "simce_lenguaje" },
  "pipeline": [
    { "step": "InitRun", "params": { "evaluation": "simce_lenguaje" } },
    { "step": "LoadConfigFromSpec", "params": { "spec_id": 4 } },
    {
      "step": "LoadMetricToDF",
      "params": { "metric_id": 3, "output_key": "df_enriched_estudiantes", "filters": { "Año": "2025" } }
    },
    {
      "step": "LoadMetricToDF",
      "params": { "metric_id": 4, "output_key": "df_enriched_preguntas", "filters": { "Año": "2025" } }
    },
    { "step": "GenerateGraphics", "params": {} },
    { "step": "GenerateTables", "params": {} },
    {
      "step": "GenerateDocxReport",
      "params": { "template_name": "plantilla_simce.docx", "output_filename": "informe.docx" }
    }
  ]
}
```

### 5.2 Flujo de datos completo

```
LoadConfigFromSpec → ctx.params["charts_schema"], ctx.params["tables_schema"], ctx.params["report_schema"]
LoadMetricToDF     → ctx.artifacts["df_enriched_estudiantes"], ctx.artifacts["df_enriched_preguntas"]
GenerateGraphics   → PNGs en aux_dir + ctx.artifacts["charts_manifest"] + charts_manifest.json
GenerateTables     → XLSXs en aux_dir + ctx.artifacts["tables_manifest"] + tables_manifest.json
GenerateDocxReport → DOCX/PDF en outputs_dir
```

---

## Funciones reutilizables existentes

### plot_tools.py

| Función | Descripción |
|---|---|
| `grafico_barras_promedio_por` | Barras de promedio agrupado por columna |
| `boxplot_valor_por_curso` | Distribución (boxplot) por grupo |
| `valor_promedio_agrupado_por` | Barras agrupadas con doble nivel (principal + secundario) |
| `alumnos_por_nivel_cualitativo` | Barras apiladas por nivel cualitativo |
| `alumnos_por_nivel_curso_y_mes` | Evolución nivel × curso × mes |

### report_tools.py

| Función | Descripción |
|---|---|
| `resumen_estadistico_basico` | Tabla N/mean/min/max agrupada |
| `tabla_logro_por_alumno` | Tabla de logro por estudiante |
| `tabla_logro_por_pregunta` | Tabla de logro por pregunta |
| `crear_tabla_estadistica_por_pregunta` | Estadística de respuestas por pregunta (A/B/C/D/E) |
| `df_a_latex_loop` | Convierte DataFrame a código LaTeX |
| `img_to_latex` | Envuelve imagen en entorno figure LaTeX |

---

## Archivos a modificar (resumen)

| Archivo | Tipo | Cambio |
|---|---|---|
| `backend/routers/specs.py` | Modificar | Ampliar get/save para charts_schema, tables_schema, report_schema |
| `backend/rgenerator/etl/core/report_steps.py` | Modificar | Agregar generación de manifests JSON en GenerateGraphics y GenerateTables |
| `backend/routers/results.py` | **NUEVO** | Endpoints: listar runs, manifest, servir archivos |
| `backend/api.py` | Modificar | Montar router de results |
| `frontend/src/pages/Results.jsx` | Modificar | Reemplazar stub con dashboard |
| `frontend/src/components/RunResultsView.jsx` | **NUEVO** | Vista de resultados de un run |
| `frontend/src/components/ChartCard.jsx` | **NUEVO** | Tarjeta de gráfico |
| `frontend/src/components/TableCard.jsx` | **NUEVO** | Tarjeta de tabla |

---

## Orden de implementación recomendado

1. **Fase 1** (specs) → **Fase 2** (manifests) → **Fase 5** (pipeline de prueba) — valida backend end-to-end
2. **Fase 3** (endpoints) → **Fase 4** (frontend) — una vez que el backend sirve datos correctamente

Cada fase puede hacerse en un chat separado.

---

## Verificación

1. Crear spec 4 con `charts_schema` + `tables_schema` + `report_schema` embebidos
2. Ejecutar pipeline de dashboard desde la UI (página Execution)
3. Verificar que `aux_files/` contiene PNGs, XLSXs, `charts_manifest.json` y `tables_manifest.json`
4. `GET /api/pipelines/{id}/runs` retorna la lista de runs con flags `has_charts`, `has_tables`
5. `GET /api/pipelines/{id}/runs/{run_id}/manifest` retorna el manifest completo
6. `Results.jsx` muestra gráficos como imágenes y tablas con botón de descarga