// ── Definición de campos configurables por tipo de gráfico ───────────────────

export const CHART_COMPONENTS = [
    // ── Gráficos simples ──
    {
        id: 'BarByGroup',
        label: 'Barras por Grupo',
        type: 'chart',
        group: 'simple',
        axisConfig: [
            { key: 'valueField',  label: 'Eje Y — Valor a graficar',   optionType: 'value' },
            { key: 'groupField',  label: 'Eje X — Agrupación',         optionType: 'group' },
        ],
    },
    {
        id: 'BoxPlotByGroup',
        label: 'Boxplot por Grupo',
        type: 'chart',
        group: 'simple',
        axisConfig: [
            { key: 'valueField',  label: 'Eje Y — Valor a distribuir', optionType: 'value' },
            { key: 'groupField',  label: 'Eje X — Agrupación',         optionType: 'group' },
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
    },

    // ── Gráficos temporales ──
    {
        id: 'TrendLine',
        label: 'Tendencia Temporal',
        type: 'chart',
        group: 'temporal',
        axisConfig: [
            { key: 'groupField',  label: 'Series (agrupación)',  optionType: 'group'  },
            { key: 'periodField', label: 'Eje X — Período',      optionType: 'period' },
            { key: 'valueField',  label: 'Eje Y — Valor',        optionType: 'value'  },
        ],
    },
];

export const CHART_GROUPS = [
    { key: 'simple',   label: 'Gráficos simples'          },
    { key: 'double_x', label: 'Gráficos de doble eje X'   },
    { key: 'special',  label: 'Gráficos especiales'       },
    { key: 'temporal', label: 'Gráficos temporales'       },
];

export const TABLE_COMPONENTS = [
    { id: 'SummaryTable',           label: 'Resumen por Grupo',  type: 'table', axisConfig: [] },
    { id: 'DetailListTable',        label: 'Lista de Items',     type: 'table', axisConfig: [] },
    { id: 'DetailListWithProgress', label: 'Lista con Progreso', type: 'table', axisConfig: [
        { key: 'dimensionField', label: 'Campo de dimensión (etiqueta agrupadora)', optionType: 'dimension' },
        { key: 'progressField',  label: 'Campo de progreso (barra)',                optionType: 'value'     },
    ]},
    { id: 'TablaResumenCursos', label: 'Tabla Resumen Cursos',     type: 'table', axisConfig: [], legacy: true },
    { id: 'TablaAlumnos',       label: 'Tabla Alumnos (legacy)',   type: 'table', axisConfig: [], legacy: true },
    { id: 'TablaPreguntas',     label: 'Tabla Preguntas (legacy)', type: 'table', axisConfig: [], legacy: true },
];

export const SPECIAL_COMPONENTS = [
    { id: 'kpis',            label: 'Tarjetas KPI',      type: 'kpis',            axisConfig: [] },
    { id: 'course_selector', label: 'Selector de Curso', type: 'course_selector', axisConfig: [] },
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
