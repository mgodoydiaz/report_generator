/**
 * dashboardRenderer.jsx
 *
 * Renderiza un dashboard a partir de un `dashboard_layout` (leído del indicador).
 * Si el indicador no tiene layout configurado, usa DEFAULT_LAYOUT como fallback.
 *
 * Estructura del layout:
 * {
 *   tabs: [
 *     {
 *       id: string,
 *       label: string,
 *       rows: [
 *         {
 *           cols: 1 | 2 | 3 | 4,
 *           items: [
 *             { type: 'kpis' }
 *             { type: 'course_selector' }
 *             { type: 'table', component: 'TablaResumenCursos' }
 *             { type: 'chart', component: 'GraficoLogroPorCurso', requires: ['logro_1'] }
 *           ]
 *         }
 *       ]
 *     }
 *   ]
 * }
 */

import React, { useState } from 'react';
import { Users, Target, Award, BarChart3 } from 'lucide-react';
import {
    pct, formatValue, CURSO_COLORS,
    KPICard, MetricToggle,
    GraficoLogroPorCurso, GraficoBoxplotPorCurso,
    GraficoNivelesPorCurso, GraficoHabilidades,
    GraficoDistribucionNiveles,
    GraficoNivelesPorCursoYMes, GraficoPromedioAgrupadoPorDimension,
    GraficoTendenciaTemporal, GraficoRadarHabilidades,
    TablaAlumnos, TablaPreguntas, TablaResumenCursos,
} from './charts';
import {
    BarByGroup, HorizontalBarByDimension, GroupedBarByPeriod,
    BoxPlotByGroup, PieComposition, StackedCountByGroup, StackedCountByGroupAndPeriod,
    TrendLine,
    RadarProfile,
    SummaryTable, DetailListTable, DetailListWithProgress,
} from './plotly-charts';

// ── Layout por defecto (SIMCE) — usado como fallback ─────────────────────────

export const DEFAULT_LAYOUT = {
    tabs: [
        {
            id: 'general',
            label: 'Vista General',
            rows: [
                { cols: 4, items: [{ type: 'kpis' }] },
                { cols: 1, items: [{ type: 'table', component: 'TablaResumenCursos' }] },
                { cols: 2, items: [
                    { type: 'chart', component: 'GraficoLogroPorCurso',   requires: ['logro_1'] },
                    { type: 'chart', component: 'GraficoBoxplotPorCurso', requires: ['logro_1'] },
                ]},
                { cols: 2, items: [
                    { type: 'chart', component: 'GraficoDistribucionNiveles', requires: ['nivel_de_logro'] },
                    { type: 'chart', component: 'GraficoNivelesPorCurso',     requires: ['nivel_de_logro'] },
                ]},
            ],
        },
        {
            id: 'curso',
            label: 'Detalle Curso',
            rows: [
                { cols: 1, items: [{ type: 'course_selector' }] },
                { cols: 1, items: [{ type: 'chart', component: 'GraficoHabilidades', requires: ['habilidad'] }] },
                { cols: 1, items: [{ type: 'table', component: 'TablaAlumnos' }] },
                { cols: 1, items: [{ type: 'table', component: 'TablaPreguntas' }] },
            ],
        },
    ],
};

// ── Mapa de nombre → componente React ────────────────────────────────────────

const COMPONENT_MAP = {
    // ── Recharts legacy (mantener para layouts guardados) ──
    GraficoLogroPorCurso,
    GraficoBoxplotPorCurso,
    GraficoNivelesPorCurso,
    GraficoHabilidades,
    GraficoDistribucionNiveles,
    GraficoNivelesPorCursoYMes,
    GraficoPromedioAgrupadoPorDimension,
    GraficoTendenciaTemporal,
    GraficoRadarHabilidades,
    TablaResumenCursos,
    TablaAlumnos,
    TablaPreguntas,

    // ── Plotly — nuevos nombres genéricos ──
    BarByGroup,
    HorizontalBarByDimension,
    GroupedBarByPeriod,
    BoxPlotByGroup,
    PieComposition,
    StackedCountByGroup,
    StackedCountByGroupAndPeriod,
    TrendLine,
    RadarProfile,
    SummaryTable,
    DetailListTable,
    DetailListWithProgress,
};

// Props estándar que cada componente acepta (subset de dashboardComputed)
function buildComponentProps(componentId, ctx, item = {}) {
    const { computed, datosCurso, onCursoClick, cursoActivo, metricLogro, setMetricLogro, metricBoxplot, setMetricBoxplot } = ctx;
    const base = {
        data: computed.estudiantes,
        cursos: computed.cursos,
        roleLabels: computed.roleLabels,
        roleFormats: computed.roleFormats,
        activeRoles: computed.activeRoles,
        achievement_levels: computed.achievement_levels,
        onCursoClick,
        cursoActivo,
    };

    // ── Resolución de campos configurables desde el layout (item) ──
    // Los campos valueField, groupField, etc. pueden venir del JSON del indicador
    // para hacer los gráficos Plotly completamente configurables.
    const isSimce = metricLogro === 'simce';
    const resolvedValueField = item.valueField ?? (isSimce ? '_simce' : '_rend');
    const resolvedGroupField = item.groupField ?? '_curso';
    const resolvedValueLabel = item.valueLabel ?? (isSimce ? (computed.roleLabels?.logro_2 || 'Val. secundario') : (computed.roleLabels?.logro_1 || 'Promedio'));
    const resolvedFormatStr = item.formatStr ?? (isSimce ? computed.roleFormats?.logro_2 : computed.roleFormats?.logro_1);
    const fmtFn = (v) => formatValue(v, resolvedFormatStr);
    const temporalLabels = (() => {
        const map = {};
        if (computed.temporalConfig) {
            const allEntries = computed.estudiantes;
            allEntries.forEach(e => {
                if (e._evaluacion_num != null && e._temporal_label) {
                    map[e._evaluacion_num] = e._temporal_label;
                }
            });
        }
        return map;
    })();

    switch (componentId) {
        // ── Recharts legacy ──
        case 'GraficoLogroPorCurso':
            return {
                ...base,
                metric: computed.activeRoles?.logro_1 && computed.activeRoles?.logro_2
                    ? metricLogro
                    : (computed.activeRoles?.logro_1 ? 'logro' : 'simce'),
                toggle: computed.activeRoles?.logro_1 && computed.activeRoles?.logro_2
                    ? <MetricToggle value={metricLogro} onChange={setMetricLogro} roleLabels={computed.roleLabels} />
                    : null,
            };
        case 'GraficoBoxplotPorCurso':
            return {
                ...base,
                metric: computed.activeRoles?.logro_1 && computed.activeRoles?.logro_2
                    ? metricBoxplot
                    : (computed.activeRoles?.logro_1 ? 'logro' : 'simce'),
                toggle: computed.activeRoles?.logro_1 && computed.activeRoles?.logro_2
                    ? <MetricToggle value={metricBoxplot} onChange={setMetricBoxplot} roleLabels={computed.roleLabels} />
                    : null,
            };
        case 'GraficoNivelesPorCurso':
        case 'GraficoDistribucionNiveles':
            return base;
        case 'GraficoHabilidades':
            return { data: datosCurso.preguntas, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, dimension: item?.dimension || 'habilidad' };
        case 'GraficoNivelesPorCursoYMes':
            return { data: computed.estudiantes, cursos: computed.cursos, achievement_levels: computed.achievement_levels, temporalConfig: computed.temporalConfig };
        case 'GraficoPromedioAgrupadoPorDimension':
            return { data: computed.estudiantes, cursos: computed.cursos, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, temporalConfig: computed.temporalConfig };
        case 'GraficoTendenciaTemporal':
            return { data: computed.estudiantes, cursos: computed.cursos, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, temporalConfig: computed.temporalConfig };
        case 'GraficoRadarHabilidades':
            return { data: datosCurso.preguntas, cursos: computed.cursos, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, dimension: item?.dimension || 'habilidad' };
        case 'TablaResumenCursos':
            return base;
        case 'TablaAlumnos':
            return { data: datosCurso.estudiantes, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, activeRoles: computed.activeRoles };
        case 'TablaPreguntas':
            return { data: datosCurso.preguntas, roleLabels: computed.roleLabels };

        // ── Plotly — nuevos componentes genéricos ──
        case 'BarByGroup':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField ?? '_curso',
                valueField: resolvedValueField,
                valueLabel: resolvedValueLabel,
                formatValue: fmtFn,
                colors: CURSO_COLORS,
            };
        case 'BoxPlotByGroup':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField ?? '_curso',
                valueField: resolvedValueField,
                formatValue: fmtFn,
                colors: CURSO_COLORS,
            };
        case 'PieComposition':
            return {
                records: computed.estudiantes,
                categoryField: item.categoryField ?? '_logro',
                categoryLevels: computed.achievement_levels || [],
            };
        case 'StackedCountByGroup':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField ?? '_curso',
                categoryField: item.categoryField ?? '_logro',
                categoryLevels: computed.achievement_levels || [],
            };
        case 'StackedCountByGroupAndPeriod':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField ?? '_curso',
                categoryField: item.categoryField ?? '_logro',
                categoryLevels: computed.achievement_levels || [],
                periodField: item.periodField ?? '_evaluacion_num',
                periodLabels: temporalLabels,
            };
        case 'HorizontalBarByDimension':
            return {
                records: datosCurso.preguntas,
                dimensionField: item.dimensionField ?? '_habilidad',
                valueField: item.valueField ?? '_logro_pregunta',
                valueLabel: resolvedValueLabel,
                formatValue: fmtFn,
            };
        case 'GroupedBarByPeriod':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField ?? '_curso',
                valueField: resolvedValueField,
                periodField: item.periodField ?? '_evaluacion_num',
                periodLabels: temporalLabels,
                valueLabel: resolvedValueLabel,
                formatValue: fmtFn,
                colors: CURSO_COLORS,
            };
        case 'TrendLine':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField ?? '_curso',
                valueField: resolvedValueField,
                periodField: item.periodField ?? '_evaluacion_num',
                periodLabels: temporalLabels,
                valueLabel: resolvedValueLabel,
                formatValue: fmtFn,
                colors: CURSO_COLORS,
            };
        case 'RadarProfile':
            return {
                records: datosCurso.preguntas,
                groups: computed.cursos,
                groupField: item.groupField ?? '_curso',
                axisField: item.axisField ?? '_habilidad',
                valueField: item.valueField ?? '_logro_pregunta',
                formatValue: fmtFn,
                colors: CURSO_COLORS,
            };
        case 'SummaryTable':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField ?? '_curso',
                groupColors: CURSO_COLORS,
                valueField: item.valueField ?? '_rend',
                valueLabel: computed.roleLabels?.logro_1 || 'Promedio',
                formatValue: (v) => formatValue(v, computed.roleFormats?.logro_1),
                valueField2: computed.activeRoles?.logro_2 ? '_simce' : null,
                valueLabel2: computed.activeRoles?.logro_2 ? (computed.roleLabels?.logro_2 || 'Val. secundario') : null,
                formatValue2: (v) => formatValue(v, computed.roleFormats?.logro_2),
                categoryField: item.categoryField ?? '_logro',
                categoryLevels: computed.achievement_levels || [],
                onGroupClick: onCursoClick,
                activeGroup: cursoActivo,
            };
        case 'DetailListTable':
            return {
                records: datosCurso.estudiantes,
                labelField: item.labelField ?? '_nombre',
                valueField: item.valueField ?? '_rend',
                formatValue: (v) => formatValue(v, computed.roleFormats?.logro_1),
                badgeField: item.badgeField ?? '_logro',
            };
        case 'DetailListWithProgress':
            return {
                records: datosCurso.preguntas,
                labelField: item.labelField ?? '_pregunta',
                dimensionField: item.dimensionField ?? '_habilidad',
                progressField: item.progressField ?? '_logro_pregunta',
                progressLabel: computed.roleLabels?.logro_1 || 'Logro',
                extraField: item.extraField ?? '_correcta',
                extraLabel: item.extraLabel ?? 'Correcta',
            };

        default:
            return base;
    }
}

// ── Comprueba si un item debe mostrarse según sus requires ───────────────────

function itemIsVisible(item, activeRoles) {
    if (!item.requires || item.requires.length === 0) return true;
    return item.requires.every(role => activeRoles?.[role]);
}

// ── Títulos automáticos por componente ───────────────────────────────────────

const AUTO_TITLES = {
    // Recharts legacy
    GraficoLogroPorCurso:                 'Logro Promedio por Curso',
    GraficoBoxplotPorCurso:               'Distribución por Curso',
    GraficoNivelesPorCurso:               'Alumnos por Nivel de Logro',
    GraficoHabilidades:                   'Logro por Habilidad',
    GraficoDistribucionNiveles:           'Distribución de Niveles de Logro',
    GraficoNivelesPorCursoYMes:           'Niveles por Curso y Evaluación',
    GraficoPromedioAgrupadoPorDimension:  'Logro Promedio por Curso y Evaluación',
    GraficoTendenciaTemporal:             'Tendencia Temporal por Curso',
    GraficoRadarHabilidades:              'Radar de Habilidades',
    TablaResumenCursos:                   'Resumen por Curso',
    TablaAlumnos:                         'Logro por Estudiante',
    TablaPreguntas:                       'Logro por Pregunta',
    // Plotly new
    BarByGroup:                           'Promedio por Grupo',
    BoxPlotByGroup:                       'Distribución por Grupo',
    PieComposition:                       'Composición por Nivel',
    StackedCountByGroup:                  'Conteo por Grupo y Nivel',
    StackedCountByGroupAndPeriod:         'Niveles por Grupo y Evaluación',
    HorizontalBarByDimension:             'Promedio por Dimensión',
    GroupedBarByPeriod:                   'Promedio por Grupo y Evaluación',
    TrendLine:                            'Tendencia Temporal',
    RadarProfile:                         'Perfil de Dimensiones',
    SummaryTable:                         'Resumen por Grupo',
    DetailListTable:                      'Detalle de Items',
    DetailListWithProgress:               'Detalle con Progreso',
};

// ── Renderer de un ítem individual ───────────────────────────────────────────

function ItemRenderer({ item, ctx }) {
    const { computed, datosCurso, cursoActivo, setCursoActivo } = ctx;
    const { activeRoles } = computed;

    if (!itemIsVisible(item, activeRoles)) return null;

    // ── Especiales ──
    if (item.type === 'kpis') {
        return (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KPICard label="Total alumnos" value={computed.totalAlumnos} sub="en los cursos evaluados" icon={Users} color="indigo" />
                {activeRoles?.logro_1 && (
                    <KPICard label={computed.roleLabels?.logro_1 || 'Logro promedio'} value={computed.logroPromedio != null ? formatValue(computed.logroPromedio, computed.roleFormats?.logro_1) : '—'} sub="rendimiento general" icon={Target} color="emerald" />
                )}
                {activeRoles?.logro_2 && (
                    <KPICard label={computed.roleLabels?.logro_2 || 'Puntaje promedio'} value={computed.simcePromedio != null ? formatValue(computed.simcePromedio, computed.roleFormats?.logro_2) : '—'} sub="puntaje estimado" icon={BarChart3} color="rose" />
                )}
                {activeRoles?.nivel_de_logro && (
                    <KPICard label={computed.roleLabels?.nivel_de_logro || 'Nivel predominante'} value={computed.nivelPredominante} sub="más frecuente" icon={Award} color="amber" />
                )}
            </div>
        );
    }

    if (item.type === 'course_selector') {
        if (!computed.cursos.length) return null;
        return (
            <div className="flex gap-2 flex-wrap">
                {computed.cursos.map((c, i) => (
                    <button
                        key={c}
                        onClick={() => setCursoActivo(c)}
                        className={`px-4 py-2 rounded-xl font-bold text-sm transition-all ${cursoActivo === c
                            ? 'text-white shadow-lg'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                        }`}
                        style={cursoActivo === c ? { background: CURSO_COLORS[i % CURSO_COLORS.length] } : {}}
                    >
                        {c}
                    </button>
                ))}
            </div>
        );
    }

    // ── Tablas y gráficos ──
    const Comp = COMPONENT_MAP[item.component];
    if (!Comp) return null;

    const props = buildComponentProps(item.component, ctx, item);
    const title = AUTO_TITLES[item.component];

    // Ocultar tablas vacías
    if (item.component === 'TablaAlumnos' && datosCurso.estudiantes.length === 0) return null;
    if (item.component === 'TablaPreguntas' && datosCurso.preguntas.length === 0) return null;
    if (item.component === 'GraficoHabilidades' && (!activeRoles?.habilidad || datosCurso.preguntas.length === 0)) return null;

    const isTable = item.type === 'table';
    const hasToggle = props.toggle;

    return (
        <div>
            <div className="flex items-center justify-between mb-4">
                {title && <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">{title}</h3>}
                {hasToggle && props.toggle}
            </div>
            <div className={isTable ? 'bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm' : ''}>
                <Comp {...props} />
            </div>
        </div>
    );
}

// ── Renderer de una fila ─────────────────────────────────────────────────────

const GRID_COLS = { 1: 'grid-cols-1', 2: 'grid-cols-1 lg:grid-cols-2', 3: 'grid-cols-1 lg:grid-cols-3', 4: 'grid-cols-2 md:grid-cols-4' };

function RowRenderer({ row, ctx }) {
    const visibleItems = row.items.filter(item => itemIsVisible(item, ctx.computed.activeRoles));
    if (visibleItems.length === 0) return null;

    const cols = Math.min(row.cols || 1, visibleItems.length);
    const gridClass = GRID_COLS[cols] || 'grid-cols-1';

    return (
        <div className={`grid ${gridClass} gap-8`}>
            {visibleItems.map((item, idx) => (
                <ItemRenderer key={idx} item={item} ctx={ctx} />
            ))}
        </div>
    );
}

// ── Componente principal exportado ───────────────────────────────────────────

/**
 * @param {Object} layout       - dashboard_layout del indicador (o null → usa DEFAULT_LAYOUT)
 * @param {Object} computed     - resultado de computeDashboardKPIs()
 * @param {Object} datosCurso   - { estudiantes, preguntas } filtrados por cursoActivo
 * @param {string} cursoActivo
 * @param {Function} setCursoActivo
 * @param {Function} onCursoClick  - callback al hacer click en un curso (cambia tab)
 */
export function DashboardRenderer({ layout, computed, datosCurso, cursoActivo, setCursoActivo, onCursoClick }) {
    const [activeTab, setActiveTab] = useState(0);
    const [metricLogro, setMetricLogro] = useState('logro');
    const [metricBoxplot, setMetricBoxplot] = useState('logro');

    const resolvedLayout = (layout?.tabs?.length > 0) ? layout : DEFAULT_LAYOUT;

    const ctx = {
        computed,
        datosCurso,
        cursoActivo,
        setCursoActivo,
        onCursoClick,
        metricLogro, setMetricLogro,
        metricBoxplot, setMetricBoxplot,
    };

    const tabStyle = (active) =>
        `px-5 py-2.5 rounded-t-xl font-bold text-sm border-b-2 transition-all cursor-pointer ${active
            ? 'text-indigo-600 border-indigo-600 bg-white dark:bg-slate-900 dark:text-indigo-400 dark:border-indigo-400'
            : 'text-slate-400 border-transparent hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300'
        }`;

    // Sincronizar tab activo cuando cambia el cursoActivo desde TablaResumenCursos
    const handleCursoClick = (curso) => {
        setCursoActivo(curso);
        // Buscar el primer tab que contenga course_selector y saltar a él
        const courseTabIdx = resolvedLayout.tabs.findIndex(tab =>
            tab.rows.some(row => row.items.some(item => item.type === 'course_selector'))
        );
        if (courseTabIdx >= 0) setActiveTab(courseTabIdx);
        onCursoClick?.(curso);
    };

    const ctxWithCursoClick = { ...ctx, onCursoClick: handleCursoClick };

    return (
        <div>
            {/* Tab bar */}
            <div className="flex gap-1 border-b border-slate-200 dark:border-slate-800">
                {resolvedLayout.tabs.map((tab, idx) => (
                    <button key={tab.id || idx} className={tabStyle(activeTab === idx)} onClick={() => setActiveTab(idx)}>
                        {tab.id === 'curso' && cursoActivo ? `Detalle Curso ${cursoActivo}` : tab.label}
                    </button>
                ))}
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-b-3xl rounded-tr-3xl border border-t-0 border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                {resolvedLayout.tabs[activeTab] && (
                    <div className="space-y-8">
                        {resolvedLayout.tabs[activeTab].rows.map((row, rowIdx) => (
                            <RowRenderer key={rowIdx} row={row} ctx={ctxWithCursoClick} />
                        ))}

                        {/* Mensaje vacío para tabs de detalle curso sin curso seleccionado */}
                        {resolvedLayout.tabs[activeTab].rows.some(r => r.items.some(i => i.type === 'course_selector')) && !cursoActivo && (
                            <div className="text-center py-8 text-slate-400 text-sm">
                                Selecciona un curso desde la tabla de resumen para ver el detalle.
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
