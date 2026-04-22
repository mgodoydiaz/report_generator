// ── Definición de campos configurables por tipo de gráfico ───────────────────

// Presets de props visuales reutilizables para charts.
// Los valores se materializan en el JSON del item cuando el usuario los edita
// en LayoutEditorModal. Si el componente no recibe la prop, el chart usa su default.
const VISUAL_PROPS_COMMON = [
    { name: 'labelX',     type: 'text',    label: 'Etiqueta eje X',            help: 'Override del nombre del eje X' },
    { name: 'labelY',     type: 'text',    label: 'Etiqueta eje Y',            help: 'Override del nombre del eje Y' },
    { name: 'showLegend', type: 'boolean', label: 'Mostrar leyenda',            default: true },
    { name: 'showValues', type: 'boolean', label: 'Mostrar valores en barras',  default: false },
];

const TITLE_PROP = { name: 'title', type: 'text', label: 'Título del bloque', help: 'Se muestra arriba del componente' };

const DATA_SOURCE_PROP = {
    name: 'dataSource',
    type: 'select',
    label: 'Fuente de datos',
    help: 'estudiantes (dataset global) o cursoEstudiantes (filtrado por course_selector)',
    options: [
        { value: 'estudiantes',      label: 'Estudiantes (global)' },
        { value: 'cursoEstudiantes', label: 'Curso activo (requiere course_selector)' },
    ],
    default: 'estudiantes',
};

export const CHART_COMPONENTS = [
    // ── Gráficos simples ──
    {
        id: 'BarByGroup',
        label: 'Barras por Grupo',
        type: 'chart',
        group: 'simple',
        requiresSingleMetricContext: true,
        axisConfig: [
            { key: 'valueField',  label: 'Eje Y — Valor a graficar',   optionType: 'value' },
            { key: 'groupField',  label: 'Eje X — Agrupación',         optionType: 'group' },
        ],
        configurableProps: [
            TITLE_PROP,
            ...VISUAL_PROPS_COMMON,
        ],
    },
    {
        id: 'BoxPlotByGroup',
        label: 'Boxplot por Grupo',
        type: 'chart',
        group: 'simple',
        requiresSingleMetricContext: true,
        axisConfig: [
            { key: 'valueField',  label: 'Eje Y — Valor a distribuir', optionType: 'value' },
            { key: 'groupField',  label: 'Eje X — Agrupación',         optionType: 'group' },
        ],
        configurableProps: [
            TITLE_PROP,
            { name: 'labelX', type: 'text', label: 'Etiqueta eje X' },
            { name: 'labelY', type: 'text', label: 'Etiqueta eje Y' },
            { name: 'showLegend', type: 'boolean', label: 'Mostrar leyenda', default: true },
        ],
    },
    {
        id: 'PieComposition',
        label: 'Composición (Torta)',
        type: 'chart',
        group: 'simple',
        axisConfig: [
            { key: 'categoryField', label: 'Campo de categoría', optionType: 'category' },
        ],
        configurableProps: [
            TITLE_PROP,
            { name: 'showLegend', type: 'boolean', label: 'Mostrar leyenda', default: true },
        ],
    },
    {
        id: 'StackedCountByGroup',
        label: 'Conteo Apilado por Grupo',
        type: 'chart',
        group: 'simple',
        axisConfig: [
            { key: 'groupField',    label: 'Eje X — Agrupación',    optionType: 'group'    },
            { key: 'categoryField', label: 'Categoría (colores)',   optionType: 'category' },
        ],
        configurableProps: [
            TITLE_PROP,
            DATA_SOURCE_PROP,
            ...VISUAL_PROPS_COMMON,
        ],
    },
    {
        id: 'HorizontalBarByDimension',
        label: 'Barras Horizontales por Dimensión',
        type: 'chart',
        group: 'simple',
        axisConfig: [
            { key: 'dimensionField', label: 'Campo de dimensión (etiquetas)', optionType: 'dimension' },
            { key: 'valueField',     label: 'Campo de valor',                 optionType: 'value'     },
        ],
    },

    // ── Gráficos de doble eje X ──
    {
        id: 'DoubleGroupedBar',
        label: 'Barras Doblemente Agrupadas',
        type: 'chart',
        group: 'double_x',
        axisConfig: [
            { key: 'groupField',    label: 'Eje X — Agrupación principal',                  optionType: 'group'    },
            { key: 'subGroupField', label: 'Sub-agrupación (barras dentro de cada grupo)',   optionType: 'any'      },
            { key: 'valueField',    label: 'Eje Y — Valor',                                  optionType: 'value'    },
        ],
    },
    {
        id: 'StackedCountByGroupAndPeriod',
        label: 'Conteo Apilado por Grupo y Período',
        type: 'chart',
        group: 'double_x',
        axisConfig: [
            { key: 'groupField',    label: 'Eje X — Agrupación principal', optionType: 'group'    },
            { key: 'periodField',   label: 'Eje X — Período (subgrupo)',   optionType: 'period'   },
            { key: 'categoryField', label: 'Categoría (colores)',          optionType: 'category' },
        ],
    },

    // ── Distribución / KPI ──
    {
        id: 'Histogram',
        label: 'Histograma',
        type: 'chart',
        group: 'simple',
        axisConfig: [
            { key: 'valueField', label: 'Eje X — Valor a distribuir', optionType: 'value' },
            { key: 'groupField', label: 'Agrupación (opcional, superpone series)', optionType: 'group' },
        ],
    },
    {
        id: 'HeatmapMatrix',
        label: 'Mapa de Calor (Matriz)',
        type: 'chart',
        group: 'matrix',
        axisConfig: [
            { key: 'xField',     label: 'Eje X — Dimensión',  optionType: 'any'   },
            { key: 'yField',     label: 'Eje Y — Dimensión',  optionType: 'any'   },
            { key: 'valueField', label: 'Valor (intensidad)', optionType: 'value' },
        ],
        configurableProps: [
            TITLE_PROP,
            DATA_SOURCE_PROP,
            {
                name: 'agg',
                type: 'select',
                label: 'Agregación',
                options: [
                    { value: 'avg',           label: 'Promedio' },
                    { value: 'sum',           label: 'Suma' },
                    { value: 'count',         label: 'Conteo' },
                    { value: 'count_true',    label: 'Conteo de verdaderos (boolean)' },
                    { value: 'mean_percent',  label: 'Porcentaje (media de booleanos)' },
                    { value: 'delta_mean_percent', label: 'Δ % entre primer y último período' },
                ],
                default: 'avg',
            },
            {
                name: 'colorscale',
                type: 'select',
                label: 'Escala de color',
                options: [
                    { value: 'YlOrRd',   label: 'Amarillo→Rojo' },
                    { value: 'Viridis',  label: 'Viridis' },
                    { value: 'Blues',    label: 'Azules' },
                    { value: 'RdYlGn',   label: 'Rojo→Verde' },
                ],
                default: 'YlOrRd',
            },
            { name: 'reverseColorscale', type: 'boolean', label: 'Invertir colorscale', default: false },
            { name: 'showValues', type: 'boolean', label: 'Mostrar valores en celdas', default: true },
        ],
    },
    {
        id: 'GaugeIndicator',
        label: 'Medidor (Gauge KPI)',
        type: 'chart',
        group: 'special',
        axisConfig: [
            { key: 'valueField', label: 'Campo numérico a promediar', optionType: 'value' },
        ],
    },

    // ── Gráficos especiales ──
    {
        id: 'RadarProfile',
        label: 'Perfil Radar',
        type: 'chart',
        group: 'special',
        axisConfig: [
            { key: 'axisField',   label: 'Ejes del radar (dimensión)', optionType: 'dimension' },
            { key: 'valueField',  label: 'Valor en cada eje',          optionType: 'value'     },
            { key: 'groupField',  label: 'Agrupación (series)',        optionType: 'group'     },
        ],
        configurableProps: [
            TITLE_PROP,
            { name: 'showLegend', type: 'boolean', label: 'Mostrar leyenda', default: true },
        ],
    },

    // ── Gráficos temporales ──
    {
        id: 'TrendLine',
        label: 'Tendencia Temporal',
        type: 'chart',
        group: 'temporal',
        requiresSingleMetricContext: true,
        axisConfig: [
            { key: 'groupField',  label: 'Series (agrupación)',  optionType: 'group'  },
            { key: 'periodField', label: 'Eje X — Período',      optionType: 'period' },
            { key: 'valueField',  label: 'Eje Y — Valor',        optionType: 'value'  },
        ],
        configurableProps: [
            TITLE_PROP,
            ...VISUAL_PROPS_COMMON,
        ],
    },
    {
        id: 'ImprovementRateByGroup',
        label: 'Tasa de Mejora por Grupo',
        type: 'chart',
        group: 'temporal',
        axisConfig: [
            { key: 'groupField',  label: 'Eje X — Agrupación',            optionType: 'group'  },
            { key: 'timeField',   label: 'Campo temporal (ordinal)',      optionType: 'period' },
            { key: 'entityField', label: 'Campo de entidad (ej. _rut)',   optionType: 'any'    },
            { key: 'levelField',  label: 'Campo de nivel (categórico)',   optionType: 'category' },
        ],
        configurableProps: [
            TITLE_PROP,
            ...VISUAL_PROPS_COMMON,
        ],
    },
    {
        id: 'TrendKPI',
        label: 'KPI con Tendencia',
        type: 'chart',
        group: 'special',
        axisConfig: [
            { key: 'valueField',   label: 'Campo de valor',              optionType: 'any'   },
            { key: 'aggregation',  label: 'Agregación',                  optionType: 'any'   },
        ],
        configurableProps: [
            { name: 'label', type: 'text', label: 'Etiqueta de la tarjeta', help: 'Ej. "% Crítico+Alto"' },
            DATA_SOURCE_PROP,
            {
                name: 'aggregation',
                type: 'select',
                label: 'Agregación',
                options: [
                    { value: 'unique_count',  label: 'Conteo único del campo (ej. _rut)' },
                    { value: 'mean_percent',  label: 'Porcentaje (media de booleanos)' },
                    { value: 'avg',           label: 'Promedio' },
                    { value: 'top_group',     label: 'Mostrar el grupo más crítico' },
                ],
                default: 'mean_percent',
            },
            { name: 'invertColors', type: 'boolean', label: 'Invertir colores (menor es mejor)', default: false, help: 'Útil cuando menor % es positivo' },
        ],
    },
    {
        id: 'TransitionMatrix',
        label: 'Matriz de Transición (Sankey)',
        type: 'chart',
        group: 'temporal',
        axisConfig: [
            { key: 'timeField',   label: 'Campo temporal',              optionType: 'period'   },
            { key: 'entityField', label: 'Campo de entidad (ej. _rut)', optionType: 'any'      },
            { key: 'levelField',  label: 'Campo de nivel',              optionType: 'category' },
        ],
        configurableProps: [
            TITLE_PROP,
            DATA_SOURCE_PROP,
        ],
    },
];

export const CHART_GROUPS = [
    { key: 'simple',   label: 'Gráficos simples'          },
    { key: 'double_x', label: 'Gráficos de doble eje X'   },
    { key: 'matrix',   label: 'Matrices / Calor'          },
    { key: 'special',  label: 'Gráficos especiales'       },
    { key: 'temporal', label: 'Gráficos temporales'       },
];

export const TABLE_COMPONENTS = [
    {
        id: 'PivotTable',
        label: 'Tabla Pivote',
        type: 'table',
        axisConfig: [
            { key: 'pivotConfig', label: 'Configurar filas, columnas y valores', optionType: 'pivot' },
        ],
        configurableProps: [
            TITLE_PROP,
            DATA_SOURCE_PROP,
            {
                name: 'semaphoreField',
                type: 'text',
                label: 'Campo para semáforo',
                help: 'Si el valor coincide con un achievement_level, colorea la celda con su color (ej. "_logro", "_worst_level_label")',
            },
            {
                name: 'semaphoreMode',
                type: 'select',
                label: 'Modo de semáforo',
                options: [
                    { value: 'cell', label: 'Por celda' },
                    { value: 'row',  label: 'Por fila (peor nivel)' },
                ],
                default: 'cell',
            },
        ],
    },
    { id: 'SummaryTable',           label: 'Resumen por Grupo',  type: 'table', axisConfig: [] },
    {
        id: 'FilterableTable',
        label: 'Lista con Filtros',
        type: 'table',
        axisConfig: [
            { key: 'flatTableConfig', label: 'Configurar columnas y filtros', optionType: 'flatTable' },
        ],
    },
    { id: 'DetailListTable',        label: 'Lista de Items',     type: 'table', axisConfig: [] },
    { id: 'DetailListWithProgress', label: 'Lista con Progreso', type: 'table', axisConfig: [
        { key: 'dimensionField', label: 'Campo de dimensión (etiqueta agrupadora)', optionType: 'dimension' },
        { key: 'progressField',  label: 'Campo de progreso (barra)',                optionType: 'value'     },
    ]},
    { id: 'TablaResumenCursos', label: 'Tabla Resumen Cursos',     type: 'table', axisConfig: [], legacy: true },
    { id: 'TablaAlumnos',       label: 'Tabla Alumnos (legacy)',   type: 'table', axisConfig: [], legacy: true },
    { id: 'TablaPreguntas',     label: 'Tabla Preguntas (legacy)', type: 'table', axisConfig: [], legacy: true },
    {
        id: 'StudentRiskList',
        label: 'Lista de Alumnos en Riesgo',
        type: 'table',
        axisConfig: [],
        configurableProps: [
            TITLE_PROP,
            DATA_SOURCE_PROP,
            { name: 'topN', type: 'number', label: 'Top N alumnos', default: 10, min: 1, max: 100 },
        ],
    },
];

export const SPECIAL_COMPONENTS = [
    { id: 'kpis',               label: 'Tarjetas KPI',         type: 'kpis',               axisConfig: [] },
    { id: 'course_selector',    label: 'Selector de Curso',    type: 'course_selector',    axisConfig: [] },
    { id: 'subprueba_selector', label: 'Selector de Subprueba', type: 'subprueba_selector', axisConfig: [] },
];

export const ALL_COMPONENTS = [...SPECIAL_COMPONENTS, ...TABLE_COMPONENTS, ...CHART_COMPONENTS];

// ── Resolución de opciones según roles del indicador ─────────────────────────

/**
 * Convierte el primer entry de un rol en columnRoles al nombre de campo normalizado.
 * Retorna null si no hay column disponible.
 */
function roleToFieldName(role, columnRoles) {
    const entries = columnRoles?.[role];
    if (Array.isArray(entries) && entries.length > 0 && entries[0].column) {
        const col = entries[0].column;
        return '_' + col.trim().toLowerCase()
            .replace(/\s+/g, '_')
            .replace(/[^a-z0-9_]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_+|_+$/g, '');
    }
    return null;
}

export function getFieldOptions(optionType, columnRoles, roleLabels) {
    const rl = roleLabels || {};

    switch (optionType) {
        case 'value':
            return [
                columnRoles?.logro_1   && { value: roleToFieldName('logro_1', columnRoles)   || '_rend',  label: rl.logro_1  || 'Logro 1' },
                columnRoles?.logro_2   && { value: roleToFieldName('logro_2', columnRoles)   || '_simce', label: rl.logro_2  || 'Logro 2' },
            ].filter(Boolean);

        case 'group':
            return [
                { value: '_curso', label: 'Curso' },
            ];

        case 'category':
            return [
                columnRoles?.nivel_de_logro && { value: roleToFieldName('nivel_de_logro', columnRoles) || '_logro', label: rl.nivel_de_logro || 'Nivel de Logro' },
            ].filter(Boolean);

        case 'period':
            return [
                columnRoles?.evaluacion_num && { value: roleToFieldName('evaluacion_num', columnRoles) || '_evaluacion_num', label: rl.evaluacion_num || 'N° Evaluación' },
            ].filter(Boolean);

        case 'dimension':
            return [
                columnRoles?.habilidad   && { value: roleToFieldName('habilidad', columnRoles)   || '_habilidad',   label: rl.habilidad   || 'Habilidad'   },
                columnRoles?.habilidad_2 && { value: roleToFieldName('habilidad_2', columnRoles) || '_habilidad_2', label: rl.habilidad_2 || 'Habilidad 2' },
            ].filter(Boolean);

        case 'any': {
            // Todas las opciones disponibles de todos los tipos (para campos genéricos)
            const all = [
                { value: '_curso', label: 'Curso' },
                columnRoles?.logro_1        && { value: roleToFieldName('logro_1', columnRoles)        || '_rend',           label: rl.logro_1        || 'Logro 1' },
                columnRoles?.logro_2        && { value: roleToFieldName('logro_2', columnRoles)        || '_simce',          label: rl.logro_2        || 'Logro 2' },
                columnRoles?.nivel_de_logro && { value: roleToFieldName('nivel_de_logro', columnRoles) || '_logro',          label: rl.nivel_de_logro || 'Nivel de Logro' },
                columnRoles?.evaluacion_num && { value: roleToFieldName('evaluacion_num', columnRoles) || '_evaluacion_num', label: rl.evaluacion_num || 'N° Evaluación' },
                columnRoles?.habilidad      && { value: roleToFieldName('habilidad', columnRoles)      || '_habilidad',      label: rl.habilidad      || 'Habilidad' },
                columnRoles?.habilidad_2    && { value: roleToFieldName('habilidad_2', columnRoles)    || '_habilidad_2',    label: rl.habilidad_2    || 'Habilidad 2' },
            ];
            return all.filter(Boolean);
        }

        default:
            return [];
    }
}
