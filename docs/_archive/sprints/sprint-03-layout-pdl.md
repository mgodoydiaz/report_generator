# Sprint 3 — Nuevo layout PDL

**Objetivo:** publicar el JSON de layout v2 para el indicador `id=3` que usa los componentes del Sprint 2.

**Duración estimada:** 1-2h (usuario ejecuta con asistencia).

**Precondición:** Sprint 1 + Sprint 2 completos. Todos los componentes nuevos registrados y funcionales.

**Ejecutor:** Miguel, vía [LayoutEditorModal.jsx](../frontend/src/components/LayoutEditorModal.jsx) o `PATCH /api/indicators/3/layout` con el JSON de abajo.

---

## Estructura del nuevo layout

### Tab 1 — Panorama general

Todos los items de este tab incluyen `"filter": { "_evaluacion_num": "latest" }` para mostrar solo el estado actual.

| Slot | Componente | Props destacadas |
|---|---|---|
| Row 1 col 1 | `TrendKPI` | `label: "Total estudiantes"`, `valueField: "_rut"`, `aggregation: "unique_count"` |
| Row 1 col 2 | `TrendKPI` | `label: "% Crítico+Alto"`, `valueField: "_is_concerning"`, `aggregation: "mean_percent"`, `invertColors: true`, `previousValue` del período anterior |
| Row 1 col 3 | `TrendKPI` | `label: "Curso más crítico"`, muestra nombre del curso con mayor `%_is_concerning` |
| Row 1 col 4 | `TrendKPI` | `label: "Subprueba más crítica"`, muestra nombre de habilidad con mayor `%_is_concerning` |
| Row 2 full | `StackedCountByGroup` | Niveles por curso. `groupField: "_curso"`, `levelField: "_worst_level_label"`, `dataSource: "estudiantes"` |
| Row 3 col 1 | `HeatmapMatrix` | N Crítico+Alto por curso × subprueba. `xField: "_habilidad"`, `yField: "_curso"`, `valueField: "_is_concerning"`, `agg: "count_true"` |
| Row 3 col 2 | `HeatmapMatrix` | % Crítico+Alto. Mismo pero `agg: "mean_percent"` |

### Tab 2 — Detalle por curso

| Slot | Componente | Props destacadas |
|---|---|---|
| Row 1 | `course_selector` | setea `cursoActivo` |
| Row 2 | Fila de 6 `TrendKPI` (1 por subprueba) | `filter: { _habilidad: <subprueba> }`, `label: <subprueba>`, `valueField: "_is_concerning"`, `aggregation: "mean_percent"`, `invertColors: true`, `sparklineData: trend` |
| Row 3 full | `StackedCountByGroup` | Niveles por subprueba del curso activo. `dataSource: "cursoEstudiantes"`, `groupField: "_habilidad"` |
| Row 4 col 1 | `StudentRiskList` | `dataSource: "cursoEstudiantes"`, `topN: 10` |
| Row 4 col 2 | `PivotTable` con semáforo | `dataSource: "cursoEstudiantes"`, rows=`_nombre`, cols=`_habilidad`, value=`_logro`, `semaphoreField: "_logro"` |

### Tab 3 — Por subprueba (sin cambios)

Mantiene layout actual. Funciona bien.

### Tab 4 — Síntesis + trayectoria

| Slot | Componente | Props destacadas |
|---|---|---|
| Row 1 col 1 | `ImprovementRateByGroup` | Por curso. `groupField: "_curso"`, `entityField: "_rut"`, `levelField: "_worst_level_label"` |
| Row 1 col 2 | `ImprovementRateByGroup` | Por subprueba. `groupField: "_habilidad"` |
| Row 2 full | `TransitionMatrix` (Sankey) | `timeField: "_evaluacion_num"`, `entityField: "_rut"`, `levelField: "_worst_level_label"` |
| Row 3 col 1 | `HeatmapMatrix` | Δ % Crítico+Alto entre v1 y vN por curso × subprueba |
| Row 3 col 2 | `PivotTable` con semáforo | Niveles por estudiante × subprueba, todos los cursos |

---

## JSON de layout base (plantilla)

Este JSON se aplica vía `PATCH /api/indicators/3/layout` o se pega en el editor JSON de `LayoutEditorModal`.

> ⚠️ Los IDs concretos de componentes y props finales dependen de lo que el registry (Sprint 2) exponga. Usar este como esqueleto.

```json
{
  "tabs": [
    {
      "id": "panorama",
      "label": "Panorama",
      "items": [
        { "type": "TrendKPI", "label": "Total estudiantes", "valueField": "_rut", "aggregation": "unique_count", "filter": { "_evaluacion_num": "latest" } },
        { "type": "TrendKPI", "label": "% Crítico+Alto", "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": true, "filter": { "_evaluacion_num": "latest" } },
        { "type": "TrendKPI", "label": "Curso más crítico", "aggregation": "top_group", "groupField": "_curso", "scoreField": "_is_concerning", "filter": { "_evaluacion_num": "latest" } },
        { "type": "TrendKPI", "label": "Subprueba más crítica", "aggregation": "top_group", "groupField": "_habilidad", "scoreField": "_is_concerning", "filter": { "_evaluacion_num": "latest" } },
        { "type": "StackedCountByGroup", "groupField": "_curso", "levelField": "_worst_level_label", "dataSource": "estudiantes", "filter": { "_evaluacion_num": "latest" } },
        { "type": "HeatmapMatrix", "label": "N Crítico+Alto", "xField": "_habilidad", "yField": "_curso", "valueField": "_is_concerning", "agg": "count_true", "filter": { "_evaluacion_num": "latest" } },
        { "type": "HeatmapMatrix", "label": "% Crítico+Alto", "xField": "_habilidad", "yField": "_curso", "valueField": "_is_concerning", "agg": "mean_percent", "filter": { "_evaluacion_num": "latest" } }
      ]
    },
    {
      "id": "por-curso",
      "label": "Por Curso",
      "items": [
        { "type": "course_selector" },
        { "type": "TrendKPI", "label": "CT", "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": true, "dataSource": "cursoEstudiantes", "filter": { "_habilidad": "CT" } },
        { "type": "TrendKPI", "label": "FLO", "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": true, "dataSource": "cursoEstudiantes", "filter": { "_habilidad": "FLO" } },
        { "type": "TrendKPI", "label": "FNL", "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": true, "dataSource": "cursoEstudiantes", "filter": { "_habilidad": "FNL" } },
        { "type": "TrendKPI", "label": "FSF", "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": true, "dataSource": "cursoEstudiantes", "filter": { "_habilidad": "FSF" } },
        { "type": "TrendKPI", "label": "ILP", "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": true, "dataSource": "cursoEstudiantes", "filter": { "_habilidad": "ILP" } },
        { "type": "TrendKPI", "label": "VSD", "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": true, "dataSource": "cursoEstudiantes", "filter": { "_habilidad": "VSD" } },
        { "type": "StackedCountByGroup", "groupField": "_habilidad", "levelField": "_logro", "dataSource": "cursoEstudiantes" },
        { "type": "StudentRiskList", "dataSource": "cursoEstudiantes", "topN": 10 },
        { "type": "PivotTable", "dataSource": "cursoEstudiantes", "pivotConfig": { "rows": ["_nombre"], "cols": ["_habilidad"], "value": "_logro" }, "semaphoreField": "_logro" }
      ]
    },
    {
      "id": "por-subprueba",
      "label": "Por Subprueba",
      "items": [
        { "type": "subprueba_selector" }
      ]
    },
    {
      "id": "sintesis",
      "label": "Síntesis",
      "items": [
        { "type": "ImprovementRateByGroup", "groupField": "_curso", "entityField": "_rut", "levelField": "_worst_level_label", "timeField": "_evaluacion_num" },
        { "type": "ImprovementRateByGroup", "groupField": "_habilidad", "entityField": "_rut", "levelField": "_logro", "timeField": "_evaluacion_num" },
        { "type": "TransitionMatrix", "timeField": "_evaluacion_num", "entityField": "_rut", "levelField": "_worst_level_label" },
        { "type": "HeatmapMatrix", "label": "Δ % Crítico+Alto (vN − v1)", "xField": "_habilidad", "yField": "_curso", "valueField": "_is_concerning", "agg": "delta_mean_percent" },
        { "type": "PivotTable", "pivotConfig": { "rows": ["_curso", "_nombre"], "cols": ["_habilidad"], "value": "_worst_level_label" }, "semaphoreField": "_worst_level_label" }
      ]
    }
  ]
}
```

---

## Pasos de ejecución

1. Abrir la app en local (`npm run dev`)
2. Ir a Results → indicador 3 (IDEL)
3. Click en "Editar layout" → abre `LayoutEditorModal`
4. Pegar JSON de arriba en el editor JSON y guardar, **o** usar los wizards del editor para construirlo ítem por ítem (mejor para usar `configurableProps` del Sprint 4 si ya estuviera activo)
5. Refrescar dashboard → verificar cada tab
6. Si falla algún item, inspeccionar consola: probablemente falta registrar el componente en [componentDefs.js](../frontend/src/components/add-component/componentDefs.js) o en [dashboardRenderer.jsx](../frontend/src/tooling/dashboardRenderer.jsx)

---

## Verificación

- Tab 1: 4 KPIs con Δ, stacked bar por curso, 2 heatmaps 6×6
- Tab 2: selector → 6 KPIs por subprueba del curso activo + stacked + lista riesgo + pivot
- Tab 3: selector → se mantiene funcional
- Tab 4: 2 barras de mejora + Sankey + heatmap Δ + pivot consolidado
- Cambiar de tab limpia filtros
- `71% mejoró 1° básico` visible en Tab 4 (regresión v1)

---

## Commit sugerido

```
feat(dashboard/pdl): layout v2 del indicador 3 con worst-level y Sankey

- Tab 1 Panorama: TrendKPI con Δ + stacked + 2 heatmaps solo latest
- Tab 2 Por Curso: 6 KPIs por subprueba + stacked + StudentRiskList + PivotTable semáforo
- Tab 4 Síntesis: ImprovementRate + TransitionMatrix Sankey + heatmap Δ + pivot consolidado
- Tab 3: sin cambios

Ref: sprints/sprint-03-layout-pdl.md
```
