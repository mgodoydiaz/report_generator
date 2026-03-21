# Plan: Migración de Recharts a Plotly.js con charts generalizados

## Context

Los gráficos actuales del dashboard (`frontend/src/tooling/charts/`) están hechos con Recharts y usan nombres de dominio académico (`curso`, `logro`, `alumno`). El software se va a usar en contextos no académicos, así que necesitamos:
1. Migrar los gráficos a Plotly.js (que ya está instalado y renderiza en el browser)
2. Generalizar los props — sin términos de dominio
3. Organizar por **función analítica**, no un archivo por gráfico

## Estructura de archivos nuevos

```
frontend/src/tooling/plotly-charts/
├── README.md               — Documentación de clasificaciones y API de props
├── constants.js             — Paletas de colores, helpers de formato (portados de charts/constants.js)
├── PlotlyWrapper.jsx        — Componente <Plot> wrapper con defaults (sin modebar, dragmode:false, dark mode, responsive)
├── comparison.jsx           — BarByGroup, HorizontalBarByDimension, GroupedBarByPeriod
├── distribution.jsx         — BoxPlotByGroup, PieComposition, StackedCountByGroup, StackedCountByGroupAndPeriod
├── evolution.jsx            — TrendLine
├── radar.jsx                — RadarProfile
├── tables.jsx               — SummaryTable, DetailListTable, DetailListWithProgress
└── index.js                 — Re-exporta todo
```

**Total: 9 archivos nuevos** (6 módulos de charts/tables + constants + wrapper + index + README)

## Mapeo de componentes viejos → nuevos

| Viejo (Recharts) | Nuevo (Plotly) | Módulo | Función analítica |
|---|---|---|---|
| GraficoLogroPorCurso | BarByGroup | comparison | Promedio de métrica por grupo |
| GraficoHabilidades | HorizontalBarByDimension | comparison | Promedio por dimensión secundaria |
| GraficoPromedioAgrupadoPorDimension | GroupedBarByPeriod | comparison | Promedio por grupo × periodo |
| GraficoBoxplotPorCurso | BoxPlotByGroup | distribution | Distribución estadística por grupo |
| GraficoDistribucionNiveles | PieComposition | distribution | Composición de categorías (donut) |
| GraficoNivelesPorCurso | StackedCountByGroup | distribution | Conteo de categorías por grupo |
| GraficoNivelesPorCursoYMes | StackedCountByGroupAndPeriod | distribution | Conteo de categorías por grupo × periodo |
| GraficoTendenciaTemporal | TrendLine | evolution | Tendencia temporal por grupo |
| GraficoRadarHabilidades | RadarProfile | radar | Perfil multi-eje por grupo |
| TablaResumenCursos | SummaryTable | tables | Tabla de resumen con agregaciones |
| TablaAlumnos | DetailListTable | tables | Tabla de detalle con badges |
| TablaPreguntas | DetailListWithProgress | tables | Tabla de detalle con barra de progreso |

## Props genéricos (sin términos de dominio)

### Universales (todos los charts)
- `records: Array<Object>` — filas de datos
- `groups: string[]` — valores únicos del grupo principal
- `groupField: string` — nombre del campo de agrupación en records (ej: `"_curso"`)
- `colors: string[]` — paleta de colores para grupos
- `formatValue: (v) => string` — formateador del valor principal
- `height?: number` — altura en px

### Comparison
- `valueField: string` — campo numérico a agregar
- `valueLabel: string` — etiqueta del eje de valor
- `dimensionField?: string` — para HorizontalBar: campo de la dimensión secundaria
- `periodField?: string` — para GroupedBar: campo de periodo temporal
- `periodLabels?: Object` — mapa periodo → etiqueta display

### Distribution
- `valueField: string` — para BoxPlot: campo numérico
- `categoryField: string` — campo con la categoría (ej: `"_logro"`)
- `categoryLevels: string[]` — niveles ordenados
- `categoryColors: Object` — mapa nivel → color
- `periodField? / periodLabels?` — para StackedCountByGroupAndPeriod

### Evolution
- `valueField`, `periodField`, `periodLabels`

### Radar
- `valueField`, `axisField: string` — campo cuyos valores únicos son ejes del radar

### Tables
- `columns: Array<{field, label, format?, sortable?}>` — definición de columnas
- `onRowClick?: Function`, `highlightField?`, `highlightValue?`
- `progressField?`, `progressThresholds?` — para DetailListWithProgress

## Traducción dominio → genérico en buildComponentProps

La función `buildComponentProps` en `dashboardRenderer.jsx` es el **único punto de traducción**. Ejemplo:

```js
case 'BarByGroup':
case 'GraficoLogroPorCurso':  // alias backward-compat
    return {
        records: computed.estudiantes,
        groups: computed.cursos,
        groupField: '_curso',
        valueField: isSimce ? '_simce' : '_rend',
        valueLabel: isSimce ? roleLabels.logro_2 : roleLabels.logro_1,
        formatValue: (v) => formatValue(v, isSimce ? roleFormats.logro_2 : roleFormats.logro_1),
        colors: CURSO_COLORS,
    };
```

`dataProcessing.js` **NO se modifica** — sigue produciendo `_rend`, `_curso`, etc. La traducción ocurre solo en el renderer.

## Compatibilidad con layouts guardados

Los layouts de indicadores en la DB tienen nombres viejos (`"GraficoLogroPorCurso"`). Se mantiene compatibilidad con **aliases** en COMPONENT_MAP:

```js
const COMPONENT_MAP = {
    BarByGroup, /* ... */
    // Aliases
    GraficoLogroPorCurso: BarByGroup,
    GraficoBoxplotPorCurso: BoxPlotByGroup,
    // ... etc
};
```

## Archivos existentes a modificar

| Archivo | Cambio |
|---|---|
| `frontend/src/tooling/dashboardRenderer.jsx` | Imports de plotly-charts, COMPONENT_MAP actualizado con aliases, buildComponentProps con casos genéricos, AUTO_TITLES actualizado |
| `frontend/src/components/LayoutEditorModal.jsx` | CHART_COMPONENTS y TABLE_COMPONENTS con nuevos IDs y labels en inglés, DIMENSION_PICKER_IDS actualizado |

**NO se modifican**: `dataProcessing.js`, `Results.jsx`, `charts/` (quedan intactos como legacy)

## Mejoras respecto a Recharts

- **BoxPlot**: De ~60 líneas de SVG manual → `type: "box"` nativo (~15 líneas)
- **NivelesPorCursoYMes**: De `<Customized>` con acceso a xAxisMap → `layout.shapes` para separadores
- **Tooltips**: Plotly los maneja automáticamente, sin renderizar componentes custom
- **Interactividad**: Zoom, hover info gratuitos

## PlotlyWrapper.jsx

Wrapper compartido que aplica:
- `displayModeBar: false`, `dragmode: false`, `scrollZoom: false`
- Fondos transparentes
- Fuente Inter
- Detección dark mode via `document.documentElement.classList.contains('dark')`
- `useResizeHandler`, `responsive: true`

## Secuencia de implementación

1. `plotly-charts/constants.js` — portar paletas y formatters
2. `plotly-charts/PlotlyWrapper.jsx` — wrapper compartido
3. `plotly-charts/comparison.jsx` — 3 charts de comparación
4. `plotly-charts/distribution.jsx` — 4 charts de distribución
5. `plotly-charts/evolution.jsx` — TrendLine
6. `plotly-charts/radar.jsx` — RadarProfile
7. `plotly-charts/tables.jsx` — 3 tablas (HTML/Tailwind, no Plotly)
8. `plotly-charts/index.js` — re-exports
9. `plotly-charts/README.md` — documentación
10. Actualizar `dashboardRenderer.jsx`
11. Actualizar `LayoutEditorModal.jsx`

## Verificación

1. Levantar backend + frontend (`run_software.bat`)
2. Ir a `/results`, seleccionar un indicador SIMCE y generar dashboard
3. Verificar que todos los gráficos renderizan correctamente con Plotly
4. Verificar hover/tooltips interactivos
5. Verificar dark mode
6. Ir al editor de layout de un indicador y verificar que el catálogo muestra los nuevos componentes
7. Verificar que layouts guardados con nombres viejos siguen funcionando (aliases)
