# Ejemplos de `pdf_layout` por tipo de informe

Catálogo de configuraciones JSON para el campo `Indicator.pdf_layout` que el motor `RenderPDFReport` (WeasyPrint) renderiza. Cubre los 4 informes principales del proyecto en sus dos modos: **por evaluación** (un punto temporal) e **histórico** (evolución).

Estos ejemplos asumen los componentes nuevos agregados en el sprint del 2026-05-01 a `_chart_to_png_b64` y `_table_section`:

- `BarByGroup` (chart, simple o multi-value)
- `StackedCountByGroup` / `DistribucionNiveles` (chart)
- `GroupedBarByPeriod` (chart)
- `Histogram` (chart)
- `GaugeIndicator` (chart KPI)
- `SummaryTable` / `TablaResumenCursos` (tabla)

> **Nota**: los nombres de campos (`xField`, `valueField`, `groupField`, etc.) usan **roles canónicos** del indicator (ej: `_logro_1`, `_nivel_de_logro`) que `_resolve_field` traduce a la columna real (ej: `_cantidad` para FL, `_nota` para CV). Esto permite que el mismo layout funcione para distintos indicators si los roles están bien configurados.

---

## 1 — SIMCE Lenguaje 2° Medio · POR EVALUACIÓN

**Caso**: informe del ensayo SIMCE N° 5 (Octubre 2025) para el curso 2° Medio.
**Filtros aplicados al generar**: `N Prueba = 5` (o `Mes = OCTUBRE`).

```json
{
  "sections": [
    {"type": "cover", "title": "Informe Ensayo SIMCE N° 5 — Lenguaje 2° Medio",
     "subtitle": "Liceo Técnico Profesional People Help People Pullinque · Octubre 2025"},

    {"type": "table", "heading": "Cuadro Resumen Logro por Curso",
     "item": {"component": "SummaryTable",
              "valueField": "_rend",
              "groupField": "_curso",
              "format": "percent",
              "showCounts": true}},

    {"type": "table", "heading": "Resumen Puntaje SIMCE por Curso",
     "item": {"component": "SummaryTable",
              "valueField": "_simce",
              "groupField": "_curso",
              "format": "number"}},

    {"type": "chart", "heading": "Rendimiento Promedio por Curso",
     "item": {"component": "BarByGroup",
              "valueField": "_rend",
              "groupField": "_curso",
              "showValues": true,
              "format": "percent",
              "labelY": "Rendimiento (%)"}},

    {"type": "chart", "heading": "Cantidad de Alumnos por Nivel de Logro",
     "item": {"component": "StackedCountByGroup",
              "groupField": "_curso",
              "levelField": "_nivel_de_logro",
              "labelY": "Cantidad de alumnos"}},

    {"type": "chart", "heading": "Logro Promedio por Habilidad",
     "item": {"component": "BarByGroup",
              "valueField": "_logro",
              "groupField": "_curso",
              "showLegend": true,
              "format": "percent"}},

    {"type": "page_break"},

    {"type": "table", "heading": "Logro por Alumno (top 30 por curso)",
     "item": {"component": "PivotTable",
              "pivotConfig": {
                "rows": ["_nombre"],
                "cols": [],
                "values": [
                  {"field": "_rend", "aggregation": "avg", "label": "Logro"},
                  {"field": "_simce", "aggregation": "avg", "label": "SIMCE"},
                  {"field": "_nivel_de_logro", "aggregation": "first", "label": "Nivel"}
                ]
              }}}
  ]
}
```

---

## 2 — SIMCE Lenguaje 2° Medio · HISTÓRICO

**Caso**: evolución del rendimiento desde Abril a Noviembre 2025, todos los cursos.
**Filtros aplicados**: ninguno temporal (o `Año = 2025`).

```json
{
  "sections": [
    {"type": "cover", "title": "Evolución SIMCE Lenguaje 2° Medio · 2025",
     "subtitle": "5 ensayos: Abril, Junio, Agosto, Octubre, Noviembre"},

    {"type": "chart", "heading": "Evolución del Rendimiento Promedio por Curso y Mes",
     "item": {"component": "GroupedBarByPeriod",
              "valueField": "_rend",
              "groupField": "_curso",
              "periodField": "_mes",
              "format": "percent",
              "labelY": "Rendimiento (%)"}},

    {"type": "chart", "heading": "Evolución del SIMCE Promedio por Curso y Mes",
     "item": {"component": "GroupedBarByPeriod",
              "valueField": "_simce",
              "groupField": "_curso",
              "periodField": "_mes",
              "format": "number",
              "labelY": "SIMCE"}},

    {"type": "chart", "heading": "Evolución de Alumnos por Nivel de Logro",
     "item": {"component": "StackedCountByGroup",
              "groupField": "_mes",
              "levelField": "_nivel_de_logro",
              "labelY": "Cantidad de alumnos (todos los cursos)"}},

    {"type": "table", "heading": "Resumen Histórico por Curso (todas las pruebas)",
     "item": {"component": "PivotTable",
              "pivotConfig": {
                "rows": ["_curso"],
                "cols": ["_mes"],
                "values": [
                  {"field": "_rend", "aggregation": "avg", "label": "Logro"}
                ]
              }}}
  ]
}
```

---

## 3 — DIA Diagnóstico Matemáticas Nivel Medio · POR EVALUACIÓN

**Caso**: DIA Diagnóstico Abril 2026, todos los cursos del nivel medio.
**Filtros**: `Asignatura = MATEMÁTICAS`, `N Prueba = Diagnóstico` (o `Mes = ABRIL`, `Año = 2026`).

```json
{
  "sections": [
    {"type": "cover", "title": "Informe DIA Diagnóstico — Matemáticas Nivel Medio",
     "subtitle": "Liceo Técnico Profesional PHP Panguipulli · Abril 2026"},

    {"type": "table", "heading": "Cuadro Resumen Logro por Curso",
     "item": {"component": "SummaryTable",
              "valueField": "_rend",
              "groupField": "_curso",
              "format": "percent"}},

    {"type": "chart", "heading": "Logro Promedio por Nivel",
     "item": {"component": "BarByGroup",
              "valueField": "_rend",
              "groupField": "_nivel",
              "format": "percent",
              "showValues": true}},

    {"type": "chart", "heading": "Logro Promedio por Curso",
     "item": {"component": "BarByGroup",
              "valueField": "_rend",
              "groupField": "_curso",
              "format": "percent",
              "showValues": true}},

    {"type": "chart", "heading": "Cantidad de Alumnos por Nivel de Logro y Curso",
     "item": {"component": "StackedCountByGroup",
              "groupField": "_curso",
              "levelField": "_nivel_de_logro",
              "labelY": "Cantidad de alumnos"}},

    {"type": "chart", "heading": "Logro Promedio por Eje Temático",
     "item": {"component": "BarByGroup",
              "valueField": "_logro",
              "groupField": "_eje_tematico",
              "format": "percent"}},

    {"type": "chart", "heading": "Logro Promedio por Habilidad",
     "item": {"component": "BarByGroup",
              "valueField": "_logro",
              "groupField": "_habilidad",
              "format": "percent"}}
  ]
}
```

---

## 4 — Fluidez Lectora · POR EVALUACIÓN

**Caso**: medición FL puntual de Agosto 2026.
**Filtros**: `Mes = AGOSTO`, `Año = 2026` (o `Evaluación = ESPECÍFICA`).

```json
{
  "sections": [
    {"type": "cover", "title": "Informe Fluidez Lectora",
     "subtitle": "Establecimiento PHP Pullinque · Agosto 2026"},

    {"type": "chart", "heading": "Promedio PPM (Cantidad) por Curso",
     "item": {"component": "GaugeIndicator",
              "valueField": "_cantidad",
              "labelX": "Promedio PPM general"}},

    {"type": "table", "heading": "Resumen por Curso",
     "item": {"component": "SummaryTable",
              "valueField": "_cantidad",
              "groupField": "_curso",
              "format": "number",
              "showCounts": true,
              "countLabel": "Categoría"}},

    {"type": "chart", "heading": "Distribución de Categoría por Curso",
     "item": {"component": "DistribucionNiveles",
              "groupField": "_curso",
              "levelField": "_categoria",
              "labelY": "Cantidad de alumnos"}},

    {"type": "chart", "heading": "Distribución de Calidad Lectora por Curso",
     "item": {"component": "StackedCountByGroup",
              "groupField": "_curso",
              "levelField": "_calidad_lectora",
              "labelY": "Cantidad de alumnos"}},

    {"type": "chart", "heading": "Distribución de PPM (todos los alumnos)",
     "item": {"component": "Histogram",
              "valueField": "_cantidad",
              "nbins": 20,
              "labelX": "PPM"}}
  ]
}
```

---

## 5 — Fluidez Lectora · HISTÓRICO

**Caso**: evolución de fluidez a través de las 3-5 evaluaciones del año.
**Filtros**: `Año = 2026` (sin filtrar Mes ni Evaluación).

```json
{
  "sections": [
    {"type": "cover", "title": "Evolución Fluidez Lectora · 2026",
     "subtitle": "Comparación entre evaluaciones"},

    {"type": "chart", "heading": "Evolución PPM Promedio por Curso y Evaluación",
     "item": {"component": "GroupedBarByPeriod",
              "valueField": "_cantidad",
              "groupField": "_curso",
              "periodField": "_evaluacion",
              "labelY": "PPM"}},

    {"type": "chart", "heading": "Evolución de Categoría por Mes",
     "item": {"component": "StackedCountByGroup",
              "groupField": "_evaluacion",
              "levelField": "_categoria",
              "labelY": "Cantidad de alumnos"}},

    {"type": "table", "heading": "PPM Promedio por Curso × Evaluación",
     "item": {"component": "PivotTable",
              "pivotConfig": {
                "rows": ["_curso"],
                "cols": ["_evaluacion"],
                "values": [{"field": "_cantidad", "aggregation": "avg", "label": "PPM"}]
              }}}
  ]
}
```

---

## 6 — Cálculo Veloz · POR EVALUACIÓN

**Caso**: prueba CV de un mes específico (ej: Mayo 2026).
**Filtros**: `Mes = MAYO`, `Año = 2026`, `N Prueba = 1`.

```json
{
  "sections": [
    {"type": "cover", "title": "Informe Cálculo Veloz",
     "subtitle": "Establecimiento PHP Pullinque · Mayo 2026 — Prueba 1"},

    {"type": "table", "heading": "Resumen por Curso",
     "item": {"component": "SummaryTable",
              "valueField": "_puntaje",
              "groupField": "_curso",
              "format": "number"}},

    {"type": "chart", "heading": "Puntaje y Nota Promedio por Curso",
     "item": {"component": "BarByGroup",
              "valueField": ["_puntaje", "_nota"],
              "groupField": "_curso",
              "showLegend": true,
              "showValues": true}},

    {"type": "chart", "heading": "Distribución de Nivel por Curso",
     "item": {"component": "DistribucionNiveles",
              "groupField": "_curso",
              "levelField": "_nivel",
              "labelY": "Cantidad de alumnos"}},

    {"type": "chart", "heading": "Histograma de Puntajes",
     "item": {"component": "Histogram",
              "valueField": "_puntaje",
              "nbins": 15,
              "labelX": "Puntaje"}},

    {"type": "table", "heading": "Detalle por alumno (top puntajes)",
     "item": {"component": "PivotTable",
              "pivotConfig": {
                "rows": ["_nombre"],
                "cols": [],
                "values": [
                  {"field": "_puntaje", "aggregation": "avg", "label": "Puntaje"},
                  {"field": "_nota", "aggregation": "avg", "label": "Nota"},
                  {"field": "_nivel", "aggregation": "first", "label": "Nivel"}
                ]
              }}}
  ]
}
```

---

## 7 — Cálculo Veloz · HISTÓRICO

**Caso**: comparación de Puntaje y Nota entre meses (Marzo, Mayo, Julio, Septiembre).
**Filtros**: `Año = 2026`.

```json
{
  "sections": [
    {"type": "cover", "title": "Evolución Cálculo Veloz · 2026",
     "subtitle": "Comparación entre pruebas mensuales"},

    {"type": "chart", "heading": "Evolución Puntaje Promedio por Curso y Mes",
     "item": {"component": "GroupedBarByPeriod",
              "valueField": "_puntaje",
              "groupField": "_curso",
              "periodField": "_mes",
              "labelY": "Puntaje"}},

    {"type": "chart", "heading": "Evolución Nota Promedio por Curso y Mes",
     "item": {"component": "GroupedBarByPeriod",
              "valueField": "_nota",
              "groupField": "_curso",
              "periodField": "_mes",
              "labelY": "Nota"}},

    {"type": "chart", "heading": "Distribución de Nivel a través del Año",
     "item": {"component": "StackedCountByGroup",
              "groupField": "_mes",
              "levelField": "_nivel",
              "labelY": "Cantidad de alumnos (todos los cursos)"}},

    {"type": "table", "heading": "Puntaje Promedio por Curso × Mes",
     "item": {"component": "PivotTable",
              "pivotConfig": {
                "rows": ["_curso"],
                "cols": ["_mes"],
                "values": [{"field": "_puntaje", "aggregation": "avg", "label": "Puntaje"}]
              }}}
  ]
}
```

---

## Cómo se elige cuál layout usar (3 caminos)

### Camino A — Un layout único + filtros del modal

`pdf_layout` mezcla componentes "por evaluación" + "históricos". Al generar, el usuario aplica filtro `Mes` para obtener vista puntual o lo deja vacío para histórico.

**Pro**: cero cambios de schema o código. **Con**: layouts híbridos no se ven óptimos en ningún caso (el `GroupedBarByPeriod` con un solo periodo queda vacío).

### Camino B — Dos layouts por indicator (recomendado para sprint dashboards post-lunes)

Migración Alembic agrega dos columnas:
- `Indicator.pdf_layout_evaluacion` (JSON)
- `Indicator.pdf_layout_historico` (JSON)

`GenerateReportModal.jsx` agrega un toggle:
```
Tipo de informe:  ⚪ Por evaluación   ⚪ Histórico
```

El backend `/api/indicators/{id}/export-pdf` recibe `layout_type=evaluacion|historico` y lee el layout correspondiente.

**Pro**: cada layout optimizado, UX clara. **Con**: requiere migración + cambios de UI + endpoint.

### Camino C — Dos indicators distintos (recomendado AHORA para entrega lunes)

En la UI de `/indicators`, crear dos registros por evaluación:
- "SIMCE Lenguaje 2° Medio — Por evaluación" (layout #1 de este doc)
- "SIMCE Lenguaje 2° Medio — Histórico" (layout #2 de este doc)

El usuario navega al indicator que le sirva y genera PDF normalmente.

**Pro**: cero cambios de código, funciona ya. **Con**: duplica configuración (si cambian los `column_roles` hay que actualizar dos veces).

---

## Próximos pasos

1. **Hoy/sábado**: cargar los 7 layouts arriba en BD (camino C) para los indicators existentes 2 (DIA), 4 (CV), 5 (FL), y crear los nuevos para SIMCE — usando el editor `LayoutEditorModal` o un script seed.
2. **Validar end-to-end**: generar los 7 PDFs vía `/results/{id}` → "Generar informe" → comparar con `docs/pdf_examples/`.
3. **Post-lunes**: implementar Camino B (migración Alembic + toggle en modal) — queda en backlog del sprint dashboards automáticos.
