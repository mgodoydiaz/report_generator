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
    pct, CURSO_COLORS,
    KPICard, MetricToggle,
    GraficoLogroPorCurso, GraficoBoxplotPorCurso,
    GraficoNivelesPorCurso, GraficoHabilidades,
    GraficoDistribucionNiveles,
    GraficoNivelesPorCursoYMes, GraficoPromedioAgrupadoPorDimension,
    GraficoTendenciaTemporal, GraficoRadarHabilidades,
    TablaAlumnos, TablaPreguntas, TablaResumenCursos,
} from './charts';

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
};

// Props estándar que cada componente acepta (subset de dashboardComputed)
function buildComponentProps(componentId, ctx) {
    const { computed, datosCurso, onCursoClick, cursoActivo, metricLogro, setMetricLogro, metricBoxplot, setMetricBoxplot } = ctx;
    const base = {
        data: computed.estudiantes,
        cursos: computed.cursos,
        roleLabels: computed.roleLabels,
        activeRoles: computed.activeRoles,
        achievement_levels: computed.achievement_levels,
        onCursoClick,
        cursoActivo,
    };

    switch (componentId) {
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
            return { data: datosCurso.preguntas, roleLabels: computed.roleLabels };
        case 'GraficoNivelesPorCursoYMes':
            return { data: computed.estudiantes, cursos: computed.cursos, achievement_levels: computed.achievement_levels };
        case 'GraficoPromedioAgrupadoPorDimension':
            return { data: computed.estudiantes, cursos: computed.cursos, roleLabels: computed.roleLabels };
        case 'GraficoTendenciaTemporal':
            return { data: computed.estudiantes, cursos: computed.cursos, roleLabels: computed.roleLabels };
        case 'GraficoRadarHabilidades':
            return { data: datosCurso.preguntas, cursos: computed.cursos, roleLabels: computed.roleLabels };
        case 'TablaResumenCursos':
            return base;
        case 'TablaAlumnos':
            return { data: datosCurso.estudiantes, roleLabels: computed.roleLabels, activeRoles: computed.activeRoles };
        case 'TablaPreguntas':
            return { data: datosCurso.preguntas, roleLabels: computed.roleLabels };
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
                    <KPICard label={computed.roleLabels?.logro_1 || 'Logro promedio'} value={computed.logroPromedio ? pct(computed.logroPromedio) : '—'} sub="rendimiento general" icon={Target} color="emerald" />
                )}
                {activeRoles?.logro_2 && (
                    <KPICard label={computed.roleLabels?.logro_2 || 'Puntaje promedio'} value={computed.simcePromedio ? Math.round(computed.simcePromedio) : '—'} sub="puntaje estimado" icon={BarChart3} color="rose" />
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

    const props = buildComponentProps(item.component, ctx);
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
