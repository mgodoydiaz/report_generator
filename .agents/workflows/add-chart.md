---
description: Crear un nuevo gráfico o tabla para el sistema de dashboards
---
# `/add-chart` — Agregar un nuevo gráfico o tabla al sistema de dashboards

> **Autonomía de Claude:**
> - **Opción A** (catálogo existente): Claude puede ejecutarlo autónomamente via API — sin editar código ni hacer build del frontend.
> - **Opción B/C** (componente nuevo): requiere editar archivos JSX y hacer `npm run build`. Solo con intervención humana en el entorno de desarrollo.

Guía paso a paso para crear un nuevo componente de visualización (gráfico o tabla) y dejarlo disponible en el Editor de Layout.

## Contexto

Existen **dos sistemas de gráficos** en paralelo:

| Sistema | Directorio | Librería | Cuándo usar |
|---|---|---|---|
| **Plotly (nuevo)** | `frontend/src/tooling/plotly-charts/` | `react-plotly.js` | Para gráficos nuevos — interactivos, dark mode, responsive |
| **Recharts (legacy)** | `frontend/src/tooling/charts/` | `recharts` | Solo para mantener componentes existentes |

**Usar siempre Plotly para componentes nuevos.** Los componentes Recharts se mantienen por compatibilidad con layouts guardados en la base de datos.

---

## Campos disponibles en los datos

Los datos los produce `processDataForDashboard()` y los pasa el `DashboardRenderer`. Cada fila tiene estos campos internos:

| Campo | Descripción | Rol que lo activa |
|-------|-------------|-------------------|
| `_rend` | Valor numérico principal (0-1 si es porcentaje) | `logro_1` |
| `_simce` | Valor numérico secundario | `logro_2` |
| `_logro` | Nivel textual (ej. "Adecuado") | `nivel_de_logro` |
| `_habilidad` | Dimensión analítica primaria | `habilidad` |
| `_habilidad_2` | Dimensión analítica secundaria | `habilidad_2` |
| `_logro_pregunta` | Valor numérico por ítem (0-1) | calculado desde `logro_1` |
| `_correcta` | Respuesta correcta del ítem | campo literal |
| `_pregunta` | Identificador del ítem | dimensión `pregunta` |
| `_nombre` | Nombre del registro individual | dimensión `nombre/estudiante` |
| `_curso` | Grupo principal | dimensión `curso` |
| `_evaluacion_num` | Número ordinal de la evaluación temporal | `evaluacion_num` / calculado |
| `_temporal_label` | Etiqueta legible del periodo (ej. "2024 / AGO") | temporal_config |

---

## Opción A — Usar un componente Plotly existente en un layout

Si el gráfico que necesitas ya existe en `plotly-charts/`, solo agrégalo al JSON del layout del indicador. No hay que escribir código.

### Componentes disponibles

**Comparación** (módulo `comparison.jsx`):

| Componente | Qué muestra |
|---|---|
| `BarByGroup` | Promedio de una métrica por grupo (eje X = grupos) |
| `HorizontalBarByDimension` | Promedio por dimensión analítica (ej. habilidad) — barras horizontales |
| `GroupedBarByPeriod` | Promedio por grupo × periodo — barras agrupadas |

**Distribución** (módulo `distribution.jsx`):

| Componente | Qué muestra |
|---|---|
| `BoxPlotByGroup` | Box-whisker por grupo — usa `type: "box"` nativo de Plotly |
| `PieComposition` | Donut chart de composición de categorías |
| `StackedCountByGroup` | Barras apiladas de conteo de categorías por grupo |
| `StackedCountByGroupAndPeriod` | Barras apiladas con separadores por grupo × periodo |

**Evolución** (módulo `evolution.jsx`):

| Componente | Qué muestra |
|---|---|
| `TrendLine` | Líneas de tendencia temporal, una por grupo |

**Radar** (módulo `radar.jsx`):

| Componente | Qué muestra |
|---|---|
| `RadarProfile` | Perfil multi-eje (scatterpolar), uno por grupo o promedio global |

**Tablas** (módulo `tables.jsx`):

| Componente | Qué muestra |
|---|---|
| `SummaryTable` | Tabla de resumen con agrupaciones, conteos y niveles |
| `DetailListTable` | Lista de items individuales con badge de categoría |
| `DetailListWithProgress` | Lista de items con barra de progreso (ej. preguntas) |

### Agregar al layout JSON del indicador

En el campo `dashboard_layout` del indicador (editable desde el Editor de Layout o directo en la base de datos), agregar un item en la fila correspondiente:

```json
{
  "type": "chart",
  "component": "BarByGroup",
  "requires": ["logro_1"]
}
```

**Props configurables desde el layout** (todos opcionales — si no se pasan, se usan defaults inteligentes):

```json
{
  "type": "chart",
  "component": "BarByGroup",
  "requires": ["logro_1"],
  "groupField": "_curso",
  "valueField": "_rend",
  "valueLabel": "Rendimiento"
}
```

| Prop de layout | Efecto |
|---|---|
| `groupField` | Campo de agrupación (default `_curso`) |
| `valueField` | Campo de valor (default `_rend` o `_simce` según toggle) |
| `valueLabel` | Etiqueta del valor en tooltip |
| `formatStr` | Override del formato (ej. `"%.1"` para porcentaje con 1 decimal) |
| `categoryField` | Campo de categorías para componentes de distribución (default `_logro`) |
| `periodField` | Campo de periodo temporal (default `_evaluacion_num`) |
| `dimensionField` | Campo de dimensión para HorizontalBarByDimension o RadarProfile (default `_habilidad`) |
| `axisField` | Alias de `dimensionField` para RadarProfile |
| `labelField` | Campo de etiqueta para tablas de detalle (default `_nombre` o `_pregunta`) |
| `progressField` | Campo de progreso para DetailListWithProgress (default `_logro_pregunta`) |
| `extraField` / `extraLabel` | Columna extra en DetailListWithProgress (default `_correcta` / `"Correcta"`) |
| `filter` | Filtro item-level sobre los records antes de renderizar (ver abajo) |

### Filtro item-level (`filter`)

Cualquier item del layout puede filtrar los records que recibe el componente sin afectar otras tabs ni otros items de la misma tab. Útil para, por ejemplo, mostrar la *última evaluación* en la pestaña de resumen, o restringir a un curso específico.

```jsx
// Igualdad literal
{ "component": "BarByGroup", "filter": { "_curso": "3° BÁSICO" } }

// "In" — cualquiera de la lista
{ "component": "BarByGroup", "filter": { "_curso": ["3° BÁSICO", "4° BÁSICO"] } }

// Tokens especiales para campos numéricos: "max" | "min" | "latest"
// (latest es alias de max)
{ "component": "StackedCountByGroup", "filter": { "_evaluacion_num": "max" } }

// Combinable: último evaluación Y un curso específico
{ "component": "BarByGroup", "filter": { "_evaluacion_num": "max", "_curso": "3° BÁSICO" } }
```

Reglas:

- El filtro afecta los tres arrays de records: `computed.estudiantes`, `datosCurso.estudiantes` y `datosCurso.preguntas`.
- Los agregados pre-computados (total alumnos, logroPromedio, cursos) **no** se recalculan — los KPIs siguen mostrando el dataset completo.
- `max`/`min` se calculan sobre el dataset completo del item antes de filtrar, no por grupo.
- La comparación es por coerción (`==`), así que `"2"` y `2` se consideran iguales.

---

## Opción B — Crear un componente Plotly nuevo

Cuando ningún componente existente cubre el caso de uso, crear uno nuevo en `plotly-charts/`.

### 1. Crear el componente

Agregarlo al módulo temático que corresponda (`comparison.jsx`, `distribution.jsx`, etc.) o crear un archivo nuevo si es una función analítica diferente.

**Props genéricos** (sin términos de dominio — el mapeo dominio→genérico ocurre solo en `buildComponentProps`):

```jsx
// frontend/src/tooling/plotly-charts/comparison.jsx (o el módulo que corresponda)
import React from 'react';
import PlotlyWrapper from './PlotlyWrapper';
import { avg, formatValue, CATEGORY_COLORS } from './constants';

/**
 * MiNuevoGrafico — descripción de qué muestra
 *
 * Props:
 *   records     Array<Object>   filas de datos
 *   groups      string[]        valores únicos del grupo principal
 *   groupField  string          campo de agrupación (ej. "_curso")
 *   valueField  string          campo numérico a agregar
 *   valueLabel  string          etiqueta del valor
 *   formatValue (v) => string   formateador
 *   colors      string[]        paleta de colores
 *   height      number
 */
export function MiNuevoGrafico({
    records = [],
    groups = [],
    groupField = '_curso',
    valueField = '_rend',
    valueLabel = 'Valor',
    formatValue: fmt = (v) => String(v),
    colors = CATEGORY_COLORS,
    height,
}) {
    // Transformar datos
    const groupList = groups.length
        ? groups
        : [...new Set(records.map(r => r[groupField]).filter(Boolean))].sort();

    const trace = {
        type: 'bar',
        x: groupList,
        y: groupList.map(g => avg(records.filter(r => r[groupField] === g), valueField)),
        marker: { color: groupList.map((_, i) => colors[i % colors.length]) },
        hovertemplate: `<b>%{x}</b><br>${valueLabel}: %{y}<extra></extra>`,
    };

    return (
        <PlotlyWrapper
            data={[trace]}
            layout={{ margin: { t: 24, r: 16, b: 40, l: 48 } }}
            height={height || 260}
        />
    );
}
```

**`PlotlyWrapper` aplica automáticamente**: sin modebar, sin drag, fondos transparentes, fuente Inter, responsive. Solo pasar `data` y `layout`.

### 2. Exportar desde `plotly-charts/index.js`

```js
export * from './mi-modulo'; // si se agregó a un módulo existente
// o si se creó un archivo nuevo:
export * from './nuevo-modulo';
```

### 3. Registrar en `dashboardRenderer.jsx`

**Tres lugares**:

```js
// 3a. Import al inicio del archivo:
import { /* ... existentes ..., */ MiNuevoGrafico } from './plotly-charts';

// 3b. En COMPONENT_MAP:
const COMPONENT_MAP = {
    // ... existentes ...
    MiNuevoGrafico,
};

// 3c. En buildComponentProps() — mapear campos de dominio → genéricos:
case 'MiNuevoGrafico':
    return {
        records: computed.estudiantes,   // o datosCurso.estudiantes / datosCurso.preguntas
        groups: computed.cursos,
        groupField: item.groupField ?? '_curso',
        valueField: item.valueField ?? '_rend',
        valueLabel: computed.roleLabels?.logro_1 || 'Promedio',
        formatValue: (v) => formatValue(v, computed.roleFormats?.logro_1),
        colors: CURSO_COLORS,
    };

// 3d. En AUTO_TITLES:
const AUTO_TITLES = {
    // ...
    MiNuevoGrafico: 'Título Visible en el Dashboard',
};
```

> **Regla de oro**: `buildComponentProps` es el **único punto de traducción** dominio→genérico. El componente no debe saber qué es `_rend` o `_simce`; recibe `valueField` como string.

---

## Opción C — Crear un componente Recharts (solo para casos especiales)

Solo si hay una razón técnica específica para no usar Plotly (no debería ocurrir para componentes nuevos). Seguir el mismo proceso que Opción B pero:

1. Crear en `frontend/src/tooling/charts/NombreDescriptivo.jsx`
2. Exportar desde `frontend/src/tooling/charts/index.js`
3. Registrar en `dashboardRenderer.jsx` igual que en Opción B

---

## Registrar en el Editor de Layout

El catálogo vive en `frontend/src/components/add-component/componentDefs.js`. Agregar una entrada en `CHART_COMPONENTS`, `TABLE_COMPONENTS` o `SPECIAL_COMPONENTS` según corresponda:

```js
const CHART_COMPONENTS = [
    // ... existentes ...
    {
        id: 'MiNuevoGrafico',
        label: 'Nombre legible para el editor de layout',
        type: 'chart',
        group: 'simple',                       // grupo en la galería (ver CHART_GROUPS)
        requires: ['logro_1'],                 // roles requeridos — controla visibilidad
        requiresSingleMetricContext: false,    // ver abajo
        axisConfig: [
            { key: 'valueField', label: 'Eje Y', optionType: 'value' },
            { key: 'groupField', label: 'Eje X', optionType: 'group' },
        ],
        configurableProps: [ /* ver abajo */ ],
    },
];
```

### `requires` — visibilidad por rol del indicador

Valores posibles: `logro_1`, `logro_2`, `nivel_de_logro`, `habilidad`, `habilidad_2`, `evaluacion_num`. Dejar `[]` si no depende de ningún rol. Cuando el rol no está activo en el indicador, el componente se oculta sin errores.

### `requiresSingleMetricContext` — charts sensibles a escala

Poner `true` cuando el componente mezcla escalas si recibe registros de múltiples subpruebas (ej. `BarByGroup`, `BoxPlotByGroup`, `TrendLine` — el eje Y cambia de significado por subprueba y la comparación pierde sentido). El `LayoutEditorModal` muestra un warning si un tab usa uno de estos charts sin filtrar por `_habilidad` y sin `subprueba_selector`. En dev mode, `dashboardRenderer` también loggea el warning en consola.

### `configurableProps` — schema de propiedades editables desde UI (Sprint 4)

Declara los props que el usuario puede editar desde el formulario dinámico del `LayoutEditorModal`. Complementa `axisConfig` (que es solo para campos de datos):

```js
configurableProps: [
    { name: 'title', type: 'text', label: 'Título del bloque' },

    // Fuente de datos (estudiantes global vs curso activo)
    { name: 'dataSource', type: 'select', label: 'Fuente de datos',
      options: [
          { value: 'estudiantes',      label: 'Estudiantes (global)' },
          { value: 'cursoEstudiantes', label: 'Curso activo' },
      ],
      default: 'estudiantes',
    },

    { name: 'topN', type: 'number', label: 'Top N', default: 10, min: 1, max: 100 },
    { name: 'showLegend', type: 'boolean', label: 'Mostrar leyenda', default: true },
    { name: 'color', type: 'color', label: 'Color principal' },
],
```

**Tipos soportados:** `text`, `number`, `select`, `boolean`, `color`. El formulario los renderiza con inputs estándar y persiste el valor en el JSON del item del layout. Los props declarados en `configurableProps` tienen precedencia sobre los legacy (`VISUAL_OPTIONS_BY_TYPE` en `StepConfig.jsx`) — si el mismo nombre aparece en ambos, se usa el declarativo.

**Propiedades no declaradas:** los campos custom que no están en `axisConfig` ni en `configurableProps` se preservan al guardar (no se pierden). Esto permite seguir usando props avanzadas como `filter`, `pivotConfig`, `flatTableConfig` sin que el modal las descarte.

### Probar desde el Editor de Layout

1. Abrir un indicador → "Editar layout".
2. Agregar una fila, click "Agregar" → elegir el componente en la galería.
3. Paso 2: configurar ejes (si hay `axisConfig`). Al completarlos, aparece el formulario visual con todos los `configurableProps`.
4. Paso 3: vista previa.
5. Guardar → refrescar el dashboard.

**Fuente de verdad del catálogo:** `frontend/src/components/add-component/componentDefs.js`. El modal lee desde ahí; no hay listas duplicadas.

---

## Resumen de archivos a tocar

### Para usar un componente existente en un layout

| Acción | Dónde |
|---|---|
| Editar el `dashboard_layout` del indicador | Base de datos / Editor de Layout en UI |

### Para crear un componente Plotly nuevo

| # | Archivo | Qué agregar |
|---|---------|-------------|
| 1 | `frontend/src/tooling/plotly-charts/<modulo>.jsx` | Componente nuevo con props genéricos |
| 2 | `frontend/src/tooling/plotly-charts/index.js` | Export |
| 3 | `frontend/src/tooling/dashboardRenderer.jsx` | Import, `COMPONENT_MAP`, `buildComponentProps`, `AUTO_TITLES` |
| 4 | `frontend/src/components/LayoutEditorModal.jsx` | Entrada en `CHART_COMPONENTS` o `TABLE_COMPONENTS` |

---

## Notas importantes

- **`requires` controla visibilidad automática**: si el rol no está activo en el indicador, el componente se oculta sin errores.
- **Vista general vs. detalle por curso**: `computed.estudiantes` tiene todos los registros; `datosCurso.estudiantes` / `datosCurso.preguntas` tienen solo los del curso activo. Elegir el correcto según en qué tab se usará el componente.
- **Props de layout sobreescriben defaults**: el JSON del indicador puede pasar `valueField`, `groupField`, etc. para hacer el mismo componente configurable para distintos indicadores.
- **Dark mode**: `PlotlyWrapper` detecta `.dark` en el `<html>` y ajusta colores automáticamente. Las tablas HTML usan clases `dark:` de Tailwind.
- **Compatibilidad con layouts guardados**: los nombres Recharts (`GraficoLogroPorCurso`, etc.) siguen funcionando vía aliases en `COMPONENT_MAP`. No romper eso.
