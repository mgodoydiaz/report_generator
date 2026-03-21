/**
 * dashboardRenderer.jsx
 *
 * Renderiza un dashboard a partir de un dashboard_layout (leído del indicador).
 * Si el indicador no tiene layout configurado, muestra un placeholder vacío.
 *
 * Los gráficos Plotly usan campos explícitos (valueField, groupField, etc.) configurados
 * en el Editor de Layout. Si algún campo requerido falta, se muestra un error en pantalla
 * y un toast de aviso.
 */

import React, { useState, useEffect, useRef } from 'react';
import { Users, Target, Award, BarChart3, AlertTriangle, LayoutGrid } from 'lucide-react';
import toast from 'react-hot-toast';
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

// ── Preset SIMCE — disponible en el Editor de Layout como opción de carga ────
// No se usa como fallback automático. Exportado para que LayoutEditorModal lo ofrezca.

export const SIMCE_PRESET_LAYOUT = {
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

// ── Mapa nombre → componente React ────────────────────────────────────────────

const COMPONENT_MAP = {
    GraficoLogroPorCurso, GraficoBoxplotPorCurso, GraficoNivelesPorCurso,
    GraficoHabilidades, GraficoDistribucionNiveles, GraficoNivelesPorCursoYMes,
    GraficoPromedioAgrupadoPorDimension, GraficoTendenciaTemporal, GraficoRadarHabilidades,
    TablaResumenCursos, TablaAlumnos, TablaPreguntas,
    BarByGroup, HorizontalBarByDimension, GroupedBarByPeriod,
    BoxPlotByGroup, PieComposition, StackedCountByGroup, StackedCountByGroupAndPeriod,
    TrendLine, RadarProfile, SummaryTable, DetailListTable, DetailListWithProgress,
};

// ── Campos requeridos por componente Plotly ───────────────────────────────────
// Los componentes legacy no tienen validación de campos.

const PLOTLY_REQUIRED_FIELDS = {
    BarByGroup:                   ['groupField', 'valueField'],
    BoxPlotByGroup:               ['groupField', 'valueField'],
    PieComposition:               ['categoryField'],
    StackedCountByGroup:          ['groupField', 'categoryField'],
    HorizontalBarByDimension:     ['dimensionField', 'valueField'],
    GroupedBarByPeriod:           ['groupField', 'periodField', 'valueField'],
    StackedCountByGroupAndPeriod: ['groupField', 'periodField', 'categoryField'],
    TrendLine:                    ['groupField', 'periodField', 'valueField'],
    RadarProfile:                 ['groupField', 'axisField', 'valueField'],
    DetailListWithProgress:       ['dimensionField', 'progressField'],
    SummaryTable:                 [],
    DetailListTable:              [],
};

function getMissingFields(componentId, item) {
    const required = PLOTLY_REQUIRED_FIELDS[componentId];
    if (!required) return [];
    // valueField puede ser string o array — ambos son válidos
    return required.filter(f => {
        const v = item[f];
        return !v || (Array.isArray(v) && v.length === 0);
    });
}

// Dado un item, devuelve el valueField activo (string).
// Si valueField es array, necesita el índice activo para resolver cuál usar.
function resolveValueField(item, activeIdx) {
    if (Array.isArray(item.valueField)) return item.valueField[activeIdx] ?? item.valueField[0];
    return item.valueField;
}

// ── Mapa campo interno → rol (para derivar formatStr/label desde roleFormats/roleLabels) ──

const FIELD_TO_ROLE = {
    '_rend':     'logro_1',
    '_simce':    'logro_2',
    '_logro':    'nivel_de_logro',
    '_habilidad':'habilidad',
};

// Formato por defecto por campo — cuando roleFormats no tiene el rol configurado
const FIELD_DEFAULT_FORMAT = {
    '_rend':     '%.0',   // porcentaje sin decimales
    '_simce':    '#.0',   // número entero
    '_logro':    'T',     // texto
    '_habilidad':'T',     // texto
};

// Label por defecto por campo
const FIELD_DEFAULT_LABEL = {
    '_rend':     'Logro',
    '_simce':    'Puntaje',
    '_logro':    'Nivel',
    '_habilidad':'Habilidad',
};

/**
 * Dada la instancia `item` y los `roleFormats` del indicador,
 * devuelve el formatStr que corresponde al valueField activo.
 * Prioridad: item.formatStr > roleFormats del rol > default por campo
 */
function deriveFormatStr(activeValueField, itemFormatStr, roleFormats) {
    if (itemFormatStr) return itemFormatStr;
    const role = FIELD_TO_ROLE[activeValueField];
    if (role && roleFormats?.[role]) return roleFormats[role];
    return FIELD_DEFAULT_FORMAT[activeValueField] ?? '%.0';
}

/**
 * Devuelve la etiqueta del valueField activo.
 * Prioridad: item.valueLabel > roleLabels del rol > default por campo
 */
function deriveValueLabel(activeValueField, itemValueLabel, roleLabels) {
    if (itemValueLabel) return itemValueLabel;
    const role = FIELD_TO_ROLE[activeValueField];
    if (role && roleLabels?.[role]) return roleLabels[role];
    return FIELD_DEFAULT_LABEL[activeValueField] ?? activeValueField;
}

// ── Props por componente ──────────────────────────────────────────────────────

function buildComponentProps(componentId, ctx, item, activeValueIdx = 0) {
    const {
        computed, datosCurso, onCursoClick, cursoActivo,
        metricLogro, setMetricLogro, metricBoxplot, setMetricBoxplot,
    } = ctx;

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

    // Resolver valueField activo (puede ser array con toggle)
    const activeValueField = resolveValueField(item, activeValueIdx);

    // Derivar formatStr y label desde roleFormats/roleLabels o defaults por campo
    const resolvedFormatStr = deriveFormatStr(activeValueField, item.formatStr, computed.roleFormats);
    const resolvedValueLabel = deriveValueLabel(activeValueField, item.valueLabel, computed.roleLabels);

    const fmtFn = (v) => formatValue(v, resolvedFormatStr);

    const temporalLabels = (() => {
        const map = {};
        if (computed.temporalConfig) {
            computed.estudiantes.forEach(e => {
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
            return { data: datosCurso.preguntas, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, dimension: item.dimension || 'habilidad' };
        case 'GraficoNivelesPorCursoYMes':
            return { data: computed.estudiantes, cursos: computed.cursos, achievement_levels: computed.achievement_levels, temporalConfig: computed.temporalConfig };
        case 'GraficoPromedioAgrupadoPorDimension':
            return { data: computed.estudiantes, cursos: computed.cursos, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, temporalConfig: computed.temporalConfig };
        case 'GraficoTendenciaTemporal':
            return { data: computed.estudiantes, cursos: computed.cursos, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, temporalConfig: computed.temporalConfig };
        case 'GraficoRadarHabilidades':
            return { data: datosCurso.preguntas, cursos: computed.cursos, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, dimension: item.dimension || 'habilidad' };
        case 'TablaResumenCursos':
            return base;
        case 'TablaAlumnos':
            return { data: datosCurso.estudiantes, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, activeRoles: computed.activeRoles };
        case 'TablaPreguntas':
            return { data: datosCurso.preguntas, roleLabels: computed.roleLabels };

        // ── Plotly — campos explícitos, sin fallbacks ──
        case 'BarByGroup':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField,
                valueField: activeValueField,
                valueLabel: resolvedValueLabel,
                formatValue: fmtFn,
                formatStr: resolvedFormatStr,
                colors: CURSO_COLORS,
            };
        case 'BoxPlotByGroup':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField,
                valueField: activeValueField,
                formatValue: fmtFn,
                formatStr: resolvedFormatStr,
                colors: CURSO_COLORS,
            };
        case 'PieComposition':
            return {
                records: computed.estudiantes,
                categoryField: item.categoryField,
                categoryLevels: computed.achievement_levels || [],
            };
        case 'StackedCountByGroup':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField,
                categoryField: item.categoryField,
                categoryLevels: computed.achievement_levels || [],
            };
        case 'StackedCountByGroupAndPeriod':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField,
                categoryField: item.categoryField,
                categoryLevels: computed.achievement_levels || [],
                periodField: item.periodField,
                periodLabels: temporalLabels,
            };
        case 'HorizontalBarByDimension':
            return {
                records: datosCurso.preguntas,
                dimensionField: item.dimensionField,
                valueField: activeValueField,
                valueLabel: resolvedValueLabel,
                formatValue: fmtFn,
                formatStr: resolvedFormatStr,
            };
        case 'GroupedBarByPeriod':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField,
                valueField: activeValueField,
                periodField: item.periodField,
                periodLabels: temporalLabels,
                valueLabel: resolvedValueLabel,
                formatValue: fmtFn,
                formatStr: resolvedFormatStr,
                colors: CURSO_COLORS,
            };
        case 'TrendLine':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField,
                valueField: activeValueField,
                periodField: item.periodField,
                periodLabels: temporalLabels,
                valueLabel: resolvedValueLabel,
                formatValue: fmtFn,
                formatStr: resolvedFormatStr,
                colors: CURSO_COLORS,
            };
        case 'RadarProfile':
            return {
                records: datosCurso.preguntas,
                groups: computed.cursos,
                groupField: item.groupField,
                axisField: item.axisField,
                valueField: activeValueField,
                formatValue: fmtFn,
                colors: CURSO_COLORS,
            };
        case 'SummaryTable':
            return {
                records: computed.estudiantes,
                groups: computed.cursos,
                groupField: item.groupField || '_curso',
                groupColors: CURSO_COLORS,
                valueField: item.valueField || null,
                valueLabel: item.valueLabel || null,
                formatValue: fmtFn,
                categoryField: item.categoryField || null,
                categoryLevels: computed.achievement_levels || [],
                onGroupClick: onCursoClick,
                activeGroup: cursoActivo,
            };
        case 'DetailListTable':
            return {
                records: datosCurso.estudiantes,
                labelField: item.labelField || '_nombre',
                valueField: item.valueField || null,
                formatValue: fmtFn,
                badgeField: item.badgeField || null,
            };
        case 'DetailListWithProgress':
            return {
                records: datosCurso.preguntas,
                labelField: item.labelField || '_pregunta',
                dimensionField: item.dimensionField,
                progressField: item.progressField,
                progressLabel: item.progressLabel || item.progressField,
                extraField: item.extraField || null,
                extraLabel: item.extraLabel || null,
            };

        default:
            return base;
    }
}

// ── Visibilidad por roles ─────────────────────────────────────────────────────

function itemIsVisible(item, activeRoles) {
    if (!item.requires || item.requires.length === 0) return true;
    return item.requires.every(role => activeRoles?.[role]);
}

// ── Títulos automáticos ───────────────────────────────────────────────────────

const AUTO_TITLES = {
    GraficoLogroPorCurso: 'Logro Promedio por Curso',
    GraficoBoxplotPorCurso: 'Distribución por Curso',
    GraficoNivelesPorCurso: 'Alumnos por Nivel de Logro',
    GraficoHabilidades: 'Logro por Habilidad',
    GraficoDistribucionNiveles: 'Distribución de Niveles de Logro',
    GraficoNivelesPorCursoYMes: 'Niveles por Curso y Evaluación',
    GraficoPromedioAgrupadoPorDimension: 'Logro Promedio por Curso y Evaluación',
    GraficoTendenciaTemporal: 'Tendencia Temporal por Curso',
    GraficoRadarHabilidades: 'Radar de Habilidades',
    TablaResumenCursos: 'Resumen por Curso',
    TablaAlumnos: 'Logro por Estudiante',
    TablaPreguntas: 'Logro por Pregunta',
    BarByGroup: 'Promedio por Grupo',
    BoxPlotByGroup: 'Distribución por Grupo',
    PieComposition: 'Composición por Nivel',
    StackedCountByGroup: 'Conteo por Grupo y Nivel',
    StackedCountByGroupAndPeriod: 'Niveles por Grupo y Evaluación',
    HorizontalBarByDimension: 'Promedio por Dimensión',
    GroupedBarByPeriod: 'Promedio por Grupo y Evaluación',
    TrendLine: 'Tendencia Temporal',
    RadarProfile: 'Perfil de Dimensiones',
    SummaryTable: 'Resumen por Grupo',
    DetailListTable: 'Detalle de Items',
    DetailListWithProgress: 'Detalle con Progreso',
};

// ── Error de configuración ────────────────────────────────────────────────────

function MissingConfigError({ componentId, missingFields }) {
    const firedRef = useRef(false);
    useEffect(() => {
        if (!firedRef.current) {
            firedRef.current = true;
            toast.error(
                (AUTO_TITLES[componentId] || componentId) + ': faltan campos — ' + missingFields.join(', '),
                { id: 'missing-' + componentId + '-' + missingFields.join('-') }
            );
        }
    }, []);

    return (
        <div className="flex flex-col items-center justify-center gap-2 py-8 px-4 rounded-2xl border-2 border-dashed border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/10 text-center">
            <AlertTriangle size={24} className="text-amber-500" />
            <p className="text-sm font-bold text-amber-700 dark:text-amber-400">
                Configuración incompleta
            </p>
            <p className="text-xs text-amber-600 dark:text-amber-500">
                <span className="font-semibold">{AUTO_TITLES[componentId] || componentId}</span> requiere configurar:
            </p>
            <div className="flex flex-wrap gap-1 justify-center">
                {missingFields.map(f => (
                    <span key={f} className="px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 text-xs font-mono font-semibold">
                        {f}
                    </span>
                ))}
            </div>
            <p className="text-[11px] text-amber-500 dark:text-amber-600 mt-1">
                Edita el layout para configurar los ejes de este gráfico.
            </p>
        </div>
    );
}

// ── Item renderer ─────────────────────────────────────────────────────────────

// ── Toggle de valueField para componentes con múltiples valores ───────────────

function ValueFieldToggle({ fields, activeIdx, onChange, computed }) {
    // Intenta obtener una etiqueta legible para cada campo
    const labelFor = (field) => {
        const roleEntry = Object.entries(computed.roleLabels || {}).find(([, v]) => {
            // Mapeo inverso campo → label buscando en roleLabels via ROLE_TO_FIELD
            const FIELD_TO_ROLE = { '_rend': 'logro_1', '_simce': 'logro_2', '_habilidad': 'habilidad', '_habilidad_2': 'habilidad_2', '_logro': 'nivel_de_logro', '_evaluacion_num': 'evaluacion_num' };
            return FIELD_TO_ROLE[field] && computed.roleLabels?.[FIELD_TO_ROLE[field]];
        });
        const FIELD_TO_ROLE = { '_rend': 'logro_1', '_simce': 'logro_2', '_habilidad': 'habilidad', '_habilidad_2': 'habilidad_2', '_logro': 'nivel_de_logro', '_evaluacion_num': 'evaluacion_num' };
        return computed.roleLabels?.[FIELD_TO_ROLE[field]] || field;
    };

    return (
        <div className="flex gap-1 p-0.5 bg-slate-100 dark:bg-slate-800 rounded-lg">
            {fields.map((f, i) => (
                <button
                    key={f}
                    onClick={() => onChange(i)}
                    className={'px-2.5 py-1 rounded-md text-xs font-semibold transition-all ' + (i === activeIdx
                        ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
                        : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
                    )}
                >
                    {labelFor(f)}
                </button>
            ))}
        </div>
    );
}

function ItemRenderer({ item, ctx }) {
    const { computed, datosCurso, cursoActivo, setCursoActivo } = ctx;
    const { activeRoles } = computed;
    const [activeValueIdx, setActiveValueIdx] = useState(0);

    if (!itemIsVisible(item, activeRoles)) return null;

    if (item.type === 'kpis') {
        return (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KPICard label="Total alumnos" value={computed.totalAlumnos} sub="en los cursos evaluados" icon={Users} color="indigo" />
                {activeRoles?.logro_1 && (
                    <KPICard label={computed.roleLabels?.logro_1 || 'Logro promedio'} value={computed.logroPromedio != null ? formatValue(computed.logroPromedio, computed.roleFormats?.logro_1) : '\u2014'} sub="rendimiento general" icon={Target} color="emerald" />
                )}
                {activeRoles?.logro_2 && (
                    <KPICard label={computed.roleLabels?.logro_2 || 'Puntaje promedio'} value={computed.simcePromedio != null ? formatValue(computed.simcePromedio, computed.roleFormats?.logro_2) : '\u2014'} sub="puntaje estimado" icon={BarChart3} color="rose" />
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
                        className={'px-4 py-2 rounded-xl font-bold text-sm transition-all ' + (cursoActivo === c
                            ? 'text-white shadow-lg'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                        )}
                        style={cursoActivo === c ? { background: CURSO_COLORS[i % CURSO_COLORS.length] } : {}}
                    >
                        {c}
                    </button>
                ))}
            </div>
        );
    }

    const Comp = COMPONENT_MAP[item.component];
    if (!Comp) return null;

    const missingFields = getMissingFields(item.component, item);
    if (missingFields.length > 0) {
        return <MissingConfigError componentId={item.component} missingFields={missingFields} />;
    }

    const props = buildComponentProps(item.component, ctx, item, activeValueIdx);
    const title = AUTO_TITLES[item.component];

    if (item.component === 'TablaAlumnos' && datosCurso.estudiantes.length === 0) return null;
    if (item.component === 'TablaPreguntas' && datosCurso.preguntas.length === 0) return null;
    if (item.component === 'GraficoHabilidades' && (!activeRoles?.habilidad || datosCurso.preguntas.length === 0)) return null;

    const isTable = item.type === 'table';
    const hasLegacyToggle = props.toggle;
    const hasValueToggle = Array.isArray(item.valueField) && item.valueField.length > 1;

    return (
        <div>
            <div className="flex items-center justify-between mb-4">
                {title && <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">{title}</h3>}
                {hasLegacyToggle && props.toggle}
                {hasValueToggle && (
                    <ValueFieldToggle
                        fields={item.valueField}
                        activeIdx={activeValueIdx}
                        onChange={setActiveValueIdx}
                        computed={computed}
                    />
                )}
            </div>
            <div className={isTable ? 'bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm' : ''}>
                <Comp {...props} />
            </div>
        </div>
    );
}

// ── Row renderer ──────────────────────────────────────────────────────────────

const GRID_COLS = { 1: 'grid-cols-1', 2: 'grid-cols-1 lg:grid-cols-2', 3: 'grid-cols-1 lg:grid-cols-3', 4: 'grid-cols-2 md:grid-cols-4' };

function RowRenderer({ row, ctx }) {
    const visibleItems = row.items.filter(item => itemIsVisible(item, ctx.computed.activeRoles));
    if (visibleItems.length === 0) return null;

    const cols = Math.min(row.cols || 1, visibleItems.length);
    const gridClass = GRID_COLS[cols] || 'grid-cols-1';

    return (
        <div className={'grid ' + gridClass + ' gap-8'}>
            {visibleItems.map((item, idx) => (
                <ItemRenderer key={idx} item={item} ctx={ctx} />
            ))}
        </div>
    );
}

// ── DashboardRenderer ─────────────────────────────────────────────────────────

// ── Placeholder para indicadores sin layout configurado ───────────────────────

function EmptyLayoutPlaceholder() {
    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-16 text-center shadow-sm">
            <div className="w-14 h-14 bg-indigo-50 dark:bg-indigo-900/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <LayoutGrid size={28} className="text-indigo-400" />
            </div>
            <h3 className="text-base font-bold text-slate-700 dark:text-slate-200 mb-2">
                Este indicador no tiene layout configurado
            </h3>
            <p className="text-sm text-slate-400 max-w-sm mx-auto">
                Ve a la página de <span className="font-semibold text-indigo-500">Indicadores</span>, abre el Editor de Layout y diseña el dashboard para este indicador.
            </p>
        </div>
    );
}

export function DashboardRenderer({ layout, computed, datosCurso, cursoActivo, setCursoActivo, onCursoClick }) {
    const [activeTab, setActiveTab] = useState(0);
    const [metricLogro, setMetricLogro] = useState('logro');
    const [metricBoxplot, setMetricBoxplot] = useState('logro');

    // Si no hay layout configurado, mostrar placeholder — sin fallback SIMCE
    if (!layout?.tabs?.length) return <EmptyLayoutPlaceholder />;

    const resolvedLayout = layout;

    const ctx = {
        computed, datosCurso, cursoActivo, setCursoActivo, onCursoClick,
        metricLogro, setMetricLogro, metricBoxplot, setMetricBoxplot,
    };

    const tabStyle = (active) =>
        'px-5 py-2.5 rounded-t-xl font-bold text-sm border-b-2 transition-all cursor-pointer ' + (active
            ? 'text-indigo-600 border-indigo-600 bg-white dark:bg-slate-900 dark:text-indigo-400 dark:border-indigo-400'
            : 'text-slate-400 border-transparent hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300'
        );

    const handleCursoClick = (curso) => {
        setCursoActivo(curso);
        const courseTabIdx = resolvedLayout.tabs.findIndex(tab =>
            tab.rows.some(row => row.items.some(item => item.type === 'course_selector'))
        );
        if (courseTabIdx >= 0) setActiveTab(courseTabIdx);
        onCursoClick?.(curso);
    };

    const ctxWithCursoClick = { ...ctx, onCursoClick: handleCursoClick };

    return (
        <div>
            <div className="flex gap-1 border-b border-slate-200 dark:border-slate-800">
                {resolvedLayout.tabs.map((tab, idx) => (
                    <button key={tab.id || idx} className={tabStyle(activeTab === idx)} onClick={() => setActiveTab(idx)}>
                        {tab.id === 'curso' && cursoActivo ? 'Detalle Curso ' + cursoActivo : tab.label}
                    </button>
                ))}
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-b-3xl rounded-tr-3xl border border-t-0 border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                {resolvedLayout.tabs[activeTab] && (
                    <div className="space-y-8">
                        {resolvedLayout.tabs[activeTab].rows.map((row, rowIdx) => (
                            <RowRenderer key={rowIdx} row={row} ctx={ctxWithCursoClick} />
                        ))}
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
