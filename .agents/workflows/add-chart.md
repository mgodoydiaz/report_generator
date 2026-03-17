---
description: Crear un nuevo gráfico o tabla para el sistema de dashboards
---
# `/add-chart` — Agregar un nuevo gráfico o tabla al sistema de dashboards

Guía paso a paso para crear un nuevo componente de visualización (gráfico o tabla) y dejarlo disponible en el Editor de Layout y en el Centro de Ayuda.

## Contexto

Los componentes de visualización viven en `frontend/src/tooling/charts/`. Son componentes React puros que reciben datos ya procesados por `processDataForDashboard()` vía el `DashboardRenderer`. Para agregar uno nuevo hay que tocas 4 puntos del sistema.

---

## Checklist de implementación

### 1. Crear el componente en `frontend/src/tooling/charts/`

Naming: `GraficoNombreDescriptivo.jsx` para gráficos, `TablaNombreDescriptivo.jsx` para tablas.

**Props estándar disponibles** (pasadas automáticamente por `DashboardRenderer` vía `buildComponentProps`):

| Prop | Tipo | Descripción |
|------|------|-------------|
| `data` | `Array` | `estudiantes` o `preguntas` según el componente |
| `cursos` | `string[]` | Lista de cursos únicos en el dataset |
| `roleLabels` | `Object` | Etiquetas personalizadas: `{ logro_1: "Rendimiento %", ... }` |
| `activeRoles` | `Object` | Roles activos: `{ logro_1: true, nivel_de_logro: false, ... }` |
| `achievement_levels` | `string[]` | Niveles de logro configurados en el indicador |
| `onCursoClick` | `Function` | Callback al hacer clic en un curso |
| `cursoActivo` | `string` | Curso seleccionado actualmente |

**Campos disponibles en cada fila de `data`:**

| Campo | Descripción | Rol que lo produce |
|-------|-------------|-------------------|
| `_rend` | Logro numérico 0-1 | `logro_1` |
| `_simce` | Puntaje secundario | `logro_2` |
| `_logro` | Nivel textual | `nivel_de_logro` |
| `_habilidad` | Habilidad evaluada | `habilidad` |
| `_habilidad_2` | Eje temático secundario | `habilidad_2` |
| `_logro_pregunta` | Logro por ítem (0-1) | calculado desde `logro_1` |
| `_correcta` | Respuesta correcta | campo literal del valor |
| `_pregunta` | N° de pregunta | dimensión `pregunta` |
| `_nombre` | Nombre del estudiante | dimensión `nombre/estudiante` |
| `_curso` | Curso del estudiante | dimensión `curso` |
| `_avance` | Δ respecto a evaluación anterior | calculado en ETL |

**Paletas de color disponibles** (importar desde `./constants`):

```js
import { LOGRO_COLORS, CURSO_COLORS, pct, avg } from './constants';

// LOGRO_COLORS: { Adecuado: "#2a9d8f", Elemental: "#e9c46a", Insuficiente: "#e76f51" }
// CURSO_COLORS: array de 8 colores para cursos
// pct(v): formatea 0.75 → "75%"
// avg(arr, key): promedio de arr[*][key]
```

**Plantilla de gráfico de barras:**

```jsx
// frontend/src/tooling/charts/GraficoNombreDescriptivo.jsx
import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Cell,
} from 'recharts';
import { CURSO_COLORS, pct, avg } from './constants';

export default function GraficoNombreDescriptivo({ data, cursos, roleLabels = {} }) {
    // Transformar data al formato que necesita el gráfico
    const chartData = cursos.map((c, i) => ({
        curso: c,
        valor: avg(data.filter(r => r._curso === c), '_rend'),
        color: CURSO_COLORS[i % CURSO_COLORS.length],
    }));

    return (
        <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="curso" tick={{ fontWeight: 700, fontSize: 13 }} />
                <YAxis tickFormatter={v => pct(v)} domain={[0, 1]} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v) => [pct(v), roleLabels.logro_1 || 'Logro']} />
                <Bar dataKey="valor" radius={[6, 6, 0, 0]}>
                    {chartData.map(entry => (
                        <Cell key={entry.curso} fill={entry.color} />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
}
```

**Plantilla de tabla:**

```jsx
// frontend/src/tooling/charts/TablaNombreDescriptivo.jsx
import React from 'react';
import { pct } from './constants';

export default function TablaNombreDescriptivo({ data, roleLabels = {} }) {
    if (!data.length) return <p className="text-slate-400 text-sm p-4">Sin datos</p>;

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
                <thead>
                    <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        {['Columna A', 'Columna B'].map(h => (
                            <th key={h} className="p-3 font-bold text-slate-400 text-[11px] uppercase tracking-widest">{h}</th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                    {data.map((row, i) => (
                        <tr key={i} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/80 transition-colors">
                            <td className="p-3 font-semibold text-slate-700 dark:text-slate-200">{row._nombre}</td>
                            <td className="p-3 font-bold text-slate-800 dark:text-white">{pct(row._rend)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
```

---

### 2. Exportar desde `frontend/src/tooling/charts/index.js`

```js
export { default as GraficoNombreDescriptivo } from './GraficoNombreDescriptivo';
// o para tabla:
export { default as TablaNombreDescriptivo } from './TablaNombreDescriptivo';
```

---

### 3. Registrar en el renderer y en el editor de layout

**`frontend/src/tooling/dashboardRenderer.jsx`** — dos lugares:

```js
// 3a. En el COMPONENT_MAP (línea ~50):
import GraficoNombreDescriptivo from './charts/GraficoNombreDescriptivo';

const COMPONENT_MAP = {
    // ... componentes existentes ...
    GraficoNombreDescriptivo,
};

// 3b. En buildComponentProps(), agregar el caso si necesita props especiales:
case 'GraficoNombreDescriptivo':
    return { data: computed.estudiantes, cursos: computed.cursos, roleLabels: computed.roleLabels };
    // Si usa datosCurso (detalle por curso):
    // return { data: datosCurso.estudiantes, roleLabels: computed.roleLabels };

// 3c. En AUTO_TITLES (línea ~100), agregar el título que aparece encima del gráfico:
const AUTO_TITLES = {
    // ... otros ...
    GraficoNombreDescriptivo: 'Título Visible en el Dashboard',
};
```

**`frontend/src/components/LayoutEditorModal.jsx`** — agregar al catálogo de componentes:

```js
// En CHART_COMPONENTS (para gráficos) o TABLE_COMPONENTS (para tablas):
const CHART_COMPONENTS = [
    // ... existentes ...
    {
        id: 'GraficoNombreDescriptivo',
        label: 'Nombre legible para el editor',
        type: 'chart',
        requires: ['logro_1'],   // roles que debe tener el indicador para mostrarlo
    },
];
```

Los valores posibles de `requires`: `logro_1`, `logro_2`, `nivel_de_logro`, `habilidad`, `habilidad_2`, `evaluacion_num`. Dejar `[]` si el componente no depende de ningún rol específico.

---

### 4. Agregar ejemplo en el Centro de Ayuda

**`frontend/src/pages/Help.jsx`**

Agregar una `ComponentCard` dentro de la sección `<Section icon={BarChart3} title="Gráficos">` (o `title="Tablas"`):

```jsx
// Importar el componente al inicio del archivo:
import { /* ... existentes ..., */ GraficoNombreDescriptivo } from '../tooling/charts';

// Agregar datos de muestra representativos si los existentes no aplican:
const MIS_DATOS_EJEMPLO = [ /* ... */ ];

// Dentro de la sección correspondiente:
<ComponentCard
    title="GraficoNombreDescriptivo"
    description="Una línea que explica qué muestra este gráfico y cuándo usarlo."
    requires={['logro_1']}
>
    <GraficoNombreDescriptivo
        data={ESTUDIANTES}
        cursos={CURSOS}
        roleLabels={ROLE_LABELS}
    />
</ComponentCard>
```

---

## Resumen de archivos a tocar

| # | Archivo | Qué agregar |
|---|---------|-------------|
| 1 | `frontend/src/tooling/charts/GraficoXxx.jsx` | Componente nuevo |
| 2 | `frontend/src/tooling/charts/index.js` | Export del componente |
| 3 | `frontend/src/tooling/dashboardRenderer.jsx` | `COMPONENT_MAP`, `buildComponentProps`, `AUTO_TITLES` |
| 4 | `frontend/src/components/LayoutEditorModal.jsx` | Entrada en `CHART_COMPONENTS` o `TABLE_COMPONENTS` |
| 5 | `frontend/src/pages/Help.jsx` | `ComponentCard` con ejemplo visual |

---

## Notas importantes

- **`requires` controla visibilidad automática**: si el rol no está activo en los datos del indicador, el componente se oculta sin errores. Usarlo correctamente evita renders vacíos.
- **`buildComponentProps` determina qué datos recibe**: los componentes de vista general reciben `computed.estudiantes`; los de detalle por curso reciben `datosCurso.estudiantes` o `datosCurso.preguntas`. Elegir el correcto según el contexto del tab donde se usará.
- **Recharts es la librería de gráficos**: usar `ResponsiveContainer` para que sea responsivo. El ancho siempre es `"100%"`, solo ajustar el `height`.
- **Dark mode**: usar clases Tailwind `dark:` para colores de texto, fondo y bordes. Los gráficos de Recharts no heredan dark mode automáticamente — usar colores neutrales (`#f0f0f0` para grillas) que funcionen en ambos modos.
