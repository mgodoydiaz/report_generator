---
description: Crear un nuevo gráfico o tabla para el sistema de dashboards
---
# `/add-chart` — Agregar un nuevo gráfico o tabla al sistema de dashboards

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

**`frontend/src/components/LayoutEditorModal.jsx`** — agregar al catálogo para que el usuario lo vea al editar un layout:

```js
const CHART_COMPONENTS = [
    // ... existentes ...
    {
        id: 'MiNuevoGrafico',
        label: 'Nombre legible para el editor de layout',
        type: 'chart',
        requires: ['logro_1'],   // roles requeridos — controla visibilidad
    },
];
// Para tablas usar TABLE_COMPONENTS
```

Valores posibles de `requires`: `logro_1`, `logro_2`, `nivel_de_logro`, `habilidad`, `habilidad_2`, `evaluacion_num`. Dejar `[]` si no depende de ningún rol.

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
