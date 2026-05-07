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

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Users, Target, Award, BarChart3, AlertTriangle, LayoutGrid, Download } from 'lucide-react';
import toast from 'react-hot-toast';
import { applyDerivedColumns } from './formulaEvaluator';
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
    BarByGroup, HorizontalBarByDimension, GroupedBarByPeriod, DoubleGroupedBar,
    BoxPlotByGroup, PieComposition, StackedCountByGroup, StackedCountByGroupAndPeriod,
    TrendLine,
    RadarProfile,
    Histogram, HeatmapMatrix, GaugeIndicator,
    PivotTable,
    FilterableTable,
    SummaryTable, DetailListTable, DetailListWithProgress,
    ImprovementRateByGroup,
    TrendKPI,
    StudentRiskList,
    TransitionMatrix,
} from './plotly-charts';
import { microcopyFor } from './plotly-charts/microcopy';
import { EmptyState, emptyReason } from './plotly-charts/emptyState';
import { TableRenderer } from '../components/tables';
import { ChartRenderer } from '../components/charts';

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
                // Vista equivalente a las páginas por curso del informe PDF:
                // ~6 gráficos + tablas que muestran los datos del curso seleccionado.
                { cols: 2, items: [
                    { type: 'chart', component: 'GraficoLogroPorCurso',     requires: ['logro_1'], filter: 'cursoActivo' },
                    { type: 'chart', component: 'GraficoDistribucionNiveles', requires: ['nivel_de_logro'], filter: 'cursoActivo' },
                ]},
                { cols: 2, items: [
                    { type: 'chart', component: 'GraficoHabilidades',        requires: ['habilidad'] },
                    { type: 'chart', component: 'GraficoBoxplotPorCurso',    requires: ['logro_1'], filter: 'cursoActivo' },
                ]},
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
    BarByGroup, HorizontalBarByDimension, GroupedBarByPeriod, DoubleGroupedBar,
    BoxPlotByGroup, PieComposition, StackedCountByGroup, StackedCountByGroupAndPeriod,
    TrendLine, RadarProfile,
    Histogram, HeatmapMatrix, GaugeIndicator,
    PivotTable,
    FilterableTable,
    SummaryTable, DetailListTable, DetailListWithProgress,
    ImprovementRateByGroup,
    TrendKPI,
    StudentRiskList,
    TransitionMatrix,
};

// ── Campos requeridos por componente Plotly ───────────────────────────────────
// Los componentes legacy no tienen validación de campos.

// Campos realmente requeridos (sin default posible).
// groupField, valueField, categoryField, dimensionField, axisField, periodField
// ya tienen defaults inteligentes en buildComponentProps — no se listan aquí.
const PLOTLY_REQUIRED_FIELDS = {
    BarByGroup:                   [],
    BoxPlotByGroup:               [],
    PieComposition:               [],
    StackedCountByGroup:          [],
    HorizontalBarByDimension:     [],
    GroupedBarByPeriod:           [],
    DoubleGroupedBar:             [],
    StackedCountByGroupAndPeriod: [],
    TrendLine:                    [],
    RadarProfile:                 [],
    Histogram:                    [],
    HeatmapMatrix:                ['xField', 'yField'],
    GaugeIndicator:               [],
    PivotTable:                   ['pivotConfig'],
    FilterableTable:              ['flatTableConfig'],
    DetailListWithProgress:       ['progressField'],
    SummaryTable:                 [],
    DetailListTable:              [],
    ImprovementRateByGroup:       [],
    TrendKPI:                     [],
    StudentRiskList:              [],
    TransitionMatrix:             [],
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

// ── Filtro item-level ─────────────────────────────────────────────────────────
// Permite que un item del layout filtre sus records antes de renderizar.
// Sintaxis de `filter` (objeto campo → target):
//   { _curso: "3° BÁSICO" }             — igualdad literal
//   { _curso: ["3° BÁSICO", "4°"] }     — "in" (cualquiera de la lista)
//   { _evaluacion_num: "max" | "min" }  — max/min del campo en el dataset
//   { _evaluacion_num: "latest" }       — alias de "max"
// Los records NO filtrados (null/undefined en el campo) quedan fuera.
// Nota: sólo afecta los records pasados al componente; no recalcula agregados
// pre-computados como `cursos`, `logroPromedio`, etc.
export function applyItemFilter(records, filter) {
    if (!filter || typeof filter !== 'object') return records;
    if (!Array.isArray(records) || records.length === 0) return records;

    // Resolver tokens especiales (max/min/latest) una sola vez
    const resolved = {};
    for (const [field, target] of Object.entries(filter)) {
        if (target === null || target === undefined) continue;
        if (target === 'max' || target === 'min' || target === 'latest') {
            const op = target === 'min' ? 'min' : 'max';
            let best = null;
            for (const r of records) {
                const v = r[field];
                if (v == null) continue;
                const n = Number(v);
                if (Number.isNaN(n)) continue;
                if (best === null) best = n;
                else if (op === 'max' && n > best) best = n;
                else if (op === 'min' && n < best) best = n;
            }
            if (best === null) return [];
            resolved[field] = best;
        } else {
            resolved[field] = target;
        }
    }

    return records.filter(r => {
        for (const [field, target] of Object.entries(resolved)) {
            const actual = r[field];
            if (Array.isArray(target)) {
                // Comparación por coerción (tolera string vs number)
                // eslint-disable-next-line eqeqeq
                if (!target.some(t => t == actual)) return false;
            } else {
                // eslint-disable-next-line eqeqeq
                if (actual != target) return false;
            }
        }
        return true;
    });
}

// ── Single-metric context check ──────────────────────────────────────────────
// Componentes que mezclan escalas si reciben registros de múltiples subpruebas
// (ej. BarByGroup, BoxPlotByGroup, TrendLine). Se considera "contexto único" si
// el item declara un filtro sobre _habilidad o hay un `subprueba_selector`
// activo en el mismo tab.
const SINGLE_METRIC_CHARTS = new Set(['BarByGroup', 'BoxPlotByGroup', 'TrendLine']);

export function needsSingleMetricWarning(componentId, item, tabContext = {}) {
    if (!SINGLE_METRIC_CHARTS.has(componentId)) return false;
    const { hasSubpruebaSelector = false, subpruebaActiva = null } = tabContext;
    const filterHasHabilidad = item?.filter && (
        Object.prototype.hasOwnProperty.call(item.filter, '_habilidad') ||
        Object.prototype.hasOwnProperty.call(item.filter, '_habilidad_2')
    );
    if (filterHasHabilidad) return false;
    if (hasSubpruebaSelector && subpruebaActiva) return false;
    if (hasSubpruebaSelector) return false; // hay selector → el usuario puede filtrar
    return true;
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
function deriveFormatStr(activeValueField, itemFormatStr, roleFormats, fieldToRole) {
    if (itemFormatStr) return itemFormatStr;
    const role = fieldToRole?.[activeValueField] || FIELD_TO_ROLE[activeValueField];
    if (role && roleFormats?.[role]) return roleFormats[role];
    return FIELD_DEFAULT_FORMAT[activeValueField] ?? '%.0';
}

/**
 * Devuelve la etiqueta del valueField activo.
 * Prioridad: item.valueLabel > roleLabels del rol > default por campo
 */
function deriveValueLabel(activeValueField, itemValueLabel, roleLabels, fieldToRole) {
    if (itemValueLabel) return itemValueLabel;
    const role = fieldToRole?.[activeValueField] || FIELD_TO_ROLE[activeValueField];
    if (role && roleLabels?.[role]) return roleLabels[role];
    return FIELD_DEFAULT_LABEL[activeValueField] ?? activeValueField;
}

// ── Props por componente ──────────────────────────────────────────────────────

function buildComponentProps(componentId, ctx, item, activeValueIdx = 0) {
    const {
        computed, datosCurso, onCursoClick, cursoActivo, subpruebaActiva,
        metricLogro, setMetricLogro, metricBoxplot, setMetricBoxplot,
    } = ctx;

    // Filtro item-level (no afecta agregados pre-computados)
    let filteredEstudiantes      = applyItemFilter(computed.estudiantes, item.filter);
    let filteredCursoEstudiantes = applyItemFilter(datosCurso.estudiantes, item.filter);
    const filteredCursoPreguntas = applyItemFilter(datosCurso.preguntas, item.filter);

    // Auto-filter por subprueba activa (si el selector está activo y el item no la sobrescribe)
    if (subpruebaActiva && !(item.filter && '_habilidad' in item.filter)) {
        filteredEstudiantes      = filteredEstudiantes.filter(r => r._habilidad === subpruebaActiva);
        filteredCursoEstudiantes = filteredCursoEstudiantes.filter(r => r._habilidad === subpruebaActiva);
    }

    const base = {
        data: filteredEstudiantes,
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

    // Para derivar formato y label usamos un fallback a '_rend' cuando el item
    // no tiene valueField configurado (el ?? real en cada case sigue siendo '_rend').
    const effectiveValueField = activeValueField ?? '_rend';

    // Derivar formatStr y label desde roleFormats/roleLabels o defaults por campo
    const resolvedFormatStr = deriveFormatStr(effectiveValueField, item.formatStr, computed.roleFormats, computed.fieldToRole);
    const resolvedValueLabel = deriveValueLabel(effectiveValueField, item.valueLabel, computed.roleLabels, computed.fieldToRole);

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
            return { data: filteredCursoPreguntas, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, dimension: item.dimension || 'habilidad' };
        case 'GraficoNivelesPorCursoYMes':
            return { data: filteredEstudiantes, cursos: computed.cursos, achievement_levels: computed.achievement_levels, temporalConfig: computed.temporalConfig };
        case 'GraficoPromedioAgrupadoPorDimension':
            return { data: filteredEstudiantes, cursos: computed.cursos, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, temporalConfig: computed.temporalConfig };
        case 'GraficoTendenciaTemporal':
            return { data: filteredEstudiantes, cursos: computed.cursos, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, temporalConfig: computed.temporalConfig };
        case 'GraficoRadarHabilidades':
            return { data: filteredCursoPreguntas, cursos: computed.cursos, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, dimension: item.dimension || 'habilidad' };
        case 'TablaResumenCursos':
            return base;
        case 'TablaAlumnos':
            return { data: filteredCursoEstudiantes, roleLabels: computed.roleLabels, roleFormats: computed.roleFormats, activeRoles: computed.activeRoles };
        case 'TablaPreguntas':
            return { data: filteredCursoPreguntas, roleLabels: computed.roleLabels };

        // ── Plotly — campos explícitos, sin fallbacks ──
        // Opciones visuales comunes (del item, configuradas en el modal)
        // eslint-disable-next-line no-case-declarations
        case 'BarByGroup': {
            const vp = { labelX: item.labelX, labelY: item.labelY, showLegend: item.showLegend, showValues: item.showValues };
            const bgf = item.groupField ?? '_curso';
            const bgroups = bgf === '_curso'
                ? computed.cursos
                : [...new Set(filteredEstudiantes.map(r => r[bgf]).filter(Boolean))].sort();
            return {
                records: filteredEstudiantes,
                groups: bgroups,
                groupField: bgf,
                valueField: activeValueField ?? '_rend',
                valueLabel: resolvedValueLabel,
                formatValue: fmtFn,
                formatStr: resolvedFormatStr,
                colors: CURSO_COLORS,
                ...vp,
            };
        }
        case 'BoxPlotByGroup': {
            const vp = { labelX: item.labelX, labelY: item.labelY, showLegend: item.showLegend };
            const bpgf = item.groupField ?? '_curso';
            const bpgroups = bpgf === '_curso'
                ? computed.cursos
                : [...new Set(filteredEstudiantes.map(r => r[bpgf]).filter(Boolean))].sort();
            return {
                records: filteredEstudiantes,
                groups: bpgroups,
                groupField: bpgf,
                valueField: activeValueField ?? '_rend',
                formatValue: fmtFn,
                formatStr: resolvedFormatStr,
                colors: CURSO_COLORS,
                ...vp,
            };
        }
        case 'PieComposition': {
            const vp = { showLegend: item.showLegend };
            const recs = item.dataSource === 'cursoEstudiantes' ? filteredCursoEstudiantes : filteredEstudiantes;
            const catField = item.categoryField ?? '_logro';
            // Mismo patrón que StackedCountByGroup: si la categoría no es el
            // nivel de logro principal, derivar los valores únicos del dataset.
            const catLevels = catField === '_logro'
                ? (computed.achievement_levels || []).map(al => typeof al === 'string' ? al : al.name).filter(Boolean)
                : [...new Set(recs.map(r => r[catField]).filter(Boolean))].sort();
            return {
                records: recs,
                categoryField: catField,
                categoryLevels: catLevels,
                achievement_levels: computed.achievement_levels || [],
                ...vp,
            };
        }
        case 'StackedCountByGroup': {
            const vp = { labelX: item.labelX, labelY: item.labelY, showLegend: item.showLegend, showValues: item.showValues };
            const gf = item.groupField ?? '_curso';
            const recs = item.dataSource === 'cursoEstudiantes' ? filteredCursoEstudiantes : filteredEstudiantes;
            const grps = gf === '_curso'
                ? computed.cursos
                : [...new Set(recs.map(r => r[gf]).filter(Boolean))].sort();
            const catField = item.categoryField ?? item.levelField ?? '_logro';
            // Si la categoría es _logro usa achievement_levels (orden semántico).
            // Si no (ej. _habilidad para Calidad Lectora), saca los valores únicos
            // del dataset y los ordena alfabéticamente.
            const catLevels = catField === '_logro'
                ? (computed.achievement_levels || []).map(al => typeof al === 'string' ? al : al.name).filter(Boolean)
                : [...new Set(recs.map(r => r[catField]).filter(Boolean))].sort();
            return {
                records: recs,
                groups: grps,
                groupField: gf,
                categoryField: catField,
                categoryLevels: catLevels,
                achievement_levels: computed.achievement_levels || [],
                ...vp,
            };
        }
        case 'StackedCountByGroupAndPeriod': {
            const vp = { labelX: item.labelX, labelY: item.labelY, showLegend: item.showLegend, showValues: item.showValues };
            const catField = item.categoryField ?? '_logro';
            const catLevels = catField === '_logro'
                ? (computed.achievement_levels || []).map(al => typeof al === 'string' ? al : al.name).filter(Boolean)
                : [...new Set(filteredEstudiantes.map(r => r[catField]).filter(Boolean))].sort();
            return {
                records: filteredEstudiantes,
                groups: computed.cursos,
                groupField: item.groupField ?? '_curso',
                categoryField: catField,
                categoryLevels: catLevels,
                achievement_levels: computed.achievement_levels || [],
                periodField: item.periodField ?? '_evaluacion_num',
                periodLabels: temporalLabels,
                ...vp,
            };
        }
        case 'HorizontalBarByDimension': {
            const vp = { labelX: item.labelX, labelY: item.labelY, showLegend: item.showLegend, showValues: item.showValues };
            // En tab general usar todos los registros; en tab curso usar solo ese curso
            const useAll = !datosCurso?.preguntas?.length;
            return {
                records: useAll ? filteredEstudiantes : filteredCursoPreguntas,
                dimensionField: item.dimensionField ?? '_habilidad',
                valueField: activeValueField ?? '_rend',
                valueLabel: resolvedValueLabel,
                formatValue: fmtFn,
                formatStr: resolvedFormatStr,
                ...vp,
            };
        }
        case 'DoubleGroupedBar':
        case 'GroupedBarByPeriod': {
            const vp = { labelX: item.labelX, labelY: item.labelY, showLegend: item.showLegend, showValues: item.showValues };
            const rawSubGroup = item.subGroupField || item.periodField || '_evaluacion_num';
            let effGroup = item.groupField ?? '_curso';
            let effSubGroup = rawSubGroup;
            if (item.legendField && item.legendField !== rawSubGroup) {
                effGroup = rawSubGroup;
                effSubGroup = item.groupField ?? '_curso';
            }
            return {
                records: filteredEstudiantes,
                groupField: effGroup,
                subGroupField: effSubGroup,
                valueField: activeValueField ?? '_rend',
                subGroupLabels: temporalLabels,
                valueLabel: resolvedValueLabel,
                formatValue: fmtFn,
                formatStr: resolvedFormatStr,
                colors: CURSO_COLORS,
                ...vp,
            };
        }
        case 'TrendLine': {
            const vp = { labelX: item.labelX, labelY: item.labelY, showLegend: item.showLegend, showValues: item.showValues };
            const tgf = item.groupField ?? '_curso';
            const tgroups = tgf === '_curso'
                ? computed.cursos
                : [...new Set(filteredEstudiantes.map(r => r[tgf]).filter(Boolean))].sort();
            return {
                records: filteredEstudiantes,
                groups: tgroups,
                groupField: tgf,
                valueField: activeValueField ?? '_rend',
                periodField: item.periodField ?? '_evaluacion_num',
                periodLabels: temporalLabels,
                valueLabel: resolvedValueLabel,
                formatValue: fmtFn,
                formatStr: resolvedFormatStr,
                colors: CURSO_COLORS,
                ...vp,
            };
        }
        case 'RadarProfile': {
            const vp = { showLegend: item.showLegend };
            const rgf = item.groupField ?? '_curso';
            const rgroups = rgf === '_curso'
                ? computed.cursos
                : [...new Set(filteredCursoPreguntas.map(r => r[rgf]).filter(Boolean))].sort();
            return {
                records: filteredCursoPreguntas,
                groups: rgroups,
                groupField: rgf,
                axisField: item.axisField ?? '_habilidad',
                valueField: activeValueField ?? '_rend',
                formatValue: fmtFn,
                colors: CURSO_COLORS,
                ...vp,
            };
        }
        case 'Histogram': {
            const vp = { labelX: item.labelX, labelY: item.labelY, showLegend: item.showLegend };
            return {
                records: item.dataSource === 'cursoEstudiantes' ? filteredCursoEstudiantes : filteredEstudiantes,
                valueField: activeValueField,
                groupField: item.groupField,
                groups: item.groupField ? computed.cursos : [],
                nbins: item.nbins,
                formatStr: resolvedFormatStr,
                colors: CURSO_COLORS,
                ...vp,
            };
        }
        case 'HeatmapMatrix': {
            const vp = { labelX: item.labelX, labelY: item.labelY, showLegend: item.showLegend, showValues: item.showValues };
            const hmRecs = item.dataSource === 'cursoEstudiantes' ? filteredCursoEstudiantes : filteredEstudiantes;
            const hmAgg = item.agg ?? item.aggregation ?? 'avg';
            const hmFmt = hmAgg === 'count_true'
                ? (v) => v == null ? '—' : String(Math.round(v))
                : hmAgg === 'mean_percent'
                    ? (v) => v == null ? '—' : `${Math.round(v * 100)}%`
                    : fmtFn;
            return {
                records: hmRecs,
                xField: item.xField,
                yField: item.yField,
                valueField: item.valueField ?? activeValueField,
                aggregation: hmAgg,
                achievement_levels: computed.achievement_levels || [],
                colorscale: item.colorscale || 'YlOrRd',
                reverseColorscale: !!item.reverseColorscale,
                xTickCase: item.xTickCase || 'none',
                yTickCase: item.yTickCase || 'none',
                xTickMap: item.xTickMap || '',
                yTickMap: item.yTickMap || '',
                formatStr: resolvedFormatStr,
                formatValue: hmFmt,
                ...vp,
            };
        }
        case 'GaugeIndicator': {
            return {
                records: filteredEstudiantes,
                valueField: activeValueField,
                aggregation: item.aggregation || 'avg',
                min: item.min,
                max: item.max,
                thresholds: item.thresholds,
                formatStr: resolvedFormatStr,
                formatValue: fmtFn,
                labelX: item.labelX || resolvedValueLabel,
            };
        }
        case 'PivotTable': {
            const pivotRecs = item.dataSource === 'cursoEstudiantes'
                ? filteredCursoEstudiantes
                : filteredEstudiantes;
            return {
                records: pivotRecs,
                pivotConfig: item.pivotConfig,
                formatStr: resolvedFormatStr,
                semaphoreField: item.semaphoreField,
                semaphoreMode: item.semaphoreMode || 'cell',
                achievement_levels: computed.achievement_levels || [],
            };
        }
        case 'FilterableTable':
            return {
                records: filteredEstudiantes,
                flatTableConfig: item.flatTableConfig || {},
                formatValue: fmtFn,
            };
        case 'SummaryTable':
            return {
                records: filteredEstudiantes,
                groups: computed.cursos,
                groupField: item.groupField ?? '_curso',
                groupColors: CURSO_COLORS,
                valueField: item.valueField ?? '_rend',
                valueLabel: item.valueLabel ?? resolvedValueLabel,
                formatValue: fmtFn,
                categoryField: item.categoryField || null,
                categoryLevels: computed.achievement_levels || [],
                onGroupClick: onCursoClick,
                activeGroup: cursoActivo,
            };
        case 'DetailListTable':
            return {
                records: filteredCursoEstudiantes,
                labelField: item.labelField || '_nombre',
                valueField: item.valueField || null,
                formatValue: fmtFn,
                badgeField: item.badgeField || null,
            };
        case 'DetailListWithProgress':
            return {
                records: filteredCursoPreguntas,
                labelField: item.labelField || '_pregunta',
                dimensionField: item.dimensionField,
                progressField: item.progressField,
                progressLabel: item.progressLabel || item.progressField,
                extraField: item.extraField || null,
                extraLabel: item.extraLabel || null,
            };
        case 'ImprovementRateByGroup': {
            const vp = { labelX: item.labelX, labelY: item.labelY, showLegend: item.showLegend, showValues: item.showValues };
            const groupField = item.groupField ?? '_curso';
            const groups = groupField === '_curso'
                ? computed.cursos
                : [...new Set(filteredEstudiantes.map(r => r[groupField]).filter(Boolean))].sort();
            return {
                records: filteredEstudiantes,
                groups,
                groupField,
                timeField: item.timeField ?? '_evaluacion_num',
                entityField: item.entityField ?? '_nombre',
                levelField: item.levelField ?? '_logro',
                achievement_levels: computed.achievement_levels || [],
                ...vp,
            };
        }

        case 'TrendKPI': {
            const recs = item.dataSource === 'cursoEstudiantes' ? filteredCursoEstudiantes : filteredEstudiantes;
            return {
                records: recs,
                label: item.label || '',
                valueField: item.valueField,
                aggregation: item.aggregation || 'mean_percent',
                groupField: item.groupField,
                scoreField: item.scoreField,
                invertColors: item.invertColors ?? false,
                sparklineData: item.sparklineData,
            };
        }
        case 'StudentRiskList': {
            const recs = item.dataSource === 'cursoEstudiantes' ? filteredCursoEstudiantes : filteredEstudiantes;
            return {
                records: recs,
                topN: item.topN || 10,
                achievement_levels: computed.achievement_levels || [],
            };
        }
        case 'TransitionMatrix': {
            const recs = item.dataSource === 'cursoEstudiantes' ? filteredCursoEstudiantes : filteredEstudiantes;
            return {
                records: recs,
                timeField: item.timeField ?? '_evaluacion_num',
                entityField: item.entityField ?? '_rut',
                levelField: item.levelField ?? '_worst_level_label',
                achievement_levels: computed.achievement_levels || [],
            };
        }

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
    GroupedBarByPeriod: 'Barras Doblemente Agrupadas',
    DoubleGroupedBar: 'Barras Doblemente Agrupadas',
    TrendLine: 'Tendencia Temporal',
    RadarProfile: 'Perfil de Dimensiones',
    Histogram: 'Histograma',
    HeatmapMatrix: 'Mapa de Calor',
    GaugeIndicator: 'Medidor',
    PivotTable: 'Tabla Pivote',
    FilterableTable: 'Lista con Filtros',
    SummaryTable: 'Resumen por Grupo',
    DetailListTable: 'Detalle de Items',
    DetailListWithProgress: 'Detalle con Progreso',
    TrendKPI: 'KPI con Tendencia',
    StudentRiskList: 'Alumnos en Riesgo',
    TransitionMatrix: 'Matriz de Transición',
};

// ── CSV export helper (S2.8) ─────────────────────────────────────────────────

function recordsToCsv(records) {
    if (!Array.isArray(records) || records.length === 0) return '';
    // Unión de claves (excluye dimensiones crudas por defecto)
    const keys = [];
    const seen = new Set();
    for (const r of records) {
        for (const k of Object.keys(r)) {
            if (k === '_raw_dims') continue;
            if (!seen.has(k)) { seen.add(k); keys.push(k); }
        }
    }
    const esc = (v) => {
        if (v == null) return '';
        const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
        return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const lines = [keys.join(',')];
    for (const r of records) lines.push(keys.map(k => esc(r[k])).join(','));
    return lines.join('\n');
}

function downloadCsv(records, filename) {
    const csv = recordsToCsv(records);
    if (!csv) return;
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

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

export function ItemRenderer({ item, ctx, tabContext }) {
    const { computed, datosCurso, cursoActivo, setCursoActivo, subpruebaActiva, setSubpruebaActiva } = ctx;
    const { activeRoles } = computed;
    const [activeValueIdx, setActiveValueIdx] = useState(0);
    const warnedRef = useRef(false);

    if (!itemIsVisible(item, activeRoles)) return null;

    // Dev-only: advertir cuando un chart sensible a escala mezcla subpruebas
    const componentIdForWarn = item.component || item.type;
    if (import.meta.env.DEV && !warnedRef.current && needsSingleMetricWarning(componentIdForWarn, item, { ...(tabContext || {}), subpruebaActiva })) {
        warnedRef.current = true;
        console.warn(
            '[dashboardRenderer] "' + componentIdForWarn + '" mezcla escalas de múltiples subpruebas. ' +
            'Agrega filter: { _habilidad: "<subprueba>" } o un subprueba_selector en el tab.'
        );
    }

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

    if (item.type === 'subprueba_selector') {
        const field = item.field || '_habilidad';
        const subpruebas = [...new Set(computed.estudiantes.map(e => e[field]).filter(Boolean))].sort();
        if (!subpruebas.length) return null;
        return (
            <div className="flex gap-2 flex-wrap items-center">
                <button
                    onClick={() => setSubpruebaActiva(null)}
                    className={'px-4 py-2 rounded-xl font-bold text-sm transition-all ' + (subpruebaActiva === null
                        ? 'bg-indigo-600 text-white shadow-lg'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                    )}
                >
                    Todas
                </button>
                {subpruebas.map((s, i) => (
                    <button
                        key={s}
                        onClick={() => setSubpruebaActiva(s)}
                        className={'px-4 py-2 rounded-xl font-bold text-sm transition-all ' + (subpruebaActiva === s
                            ? 'text-white shadow-lg'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                        )}
                        style={subpruebaActiva === s ? { background: CURSO_COLORS[i % CURSO_COLORS.length] } : {}}
                    >
                        {s}
                    </button>
                ))}
            </div>
        );
    }

    // Nota explicativa estática (texto). Útil para aclarar particularidades
    // del dataset (ej "5° y 6° BÁSICO no tienen evaluación v3 IDEL"), notas
    // de pie de gráfico, advertencias de muestra pequeña, etc.
    // Item shape: {type: 'note', text: '...', tone?: 'info'|'warn'|'tip', title?: '...'}
    if (item.type === 'note') {
        const tone = item.tone || 'info';
        const styles = {
            info: 'bg-slate-50 border-slate-200 text-slate-700',
            warn: 'bg-amber-50 border-amber-200 text-amber-800',
            tip: 'bg-blue-50 border-blue-200 text-blue-800',
        };
        const cls = styles[tone] || styles.info;
        return (
            <div className={`px-4 py-3 border rounded-lg text-sm ${cls}`}>
                {item.title && <div className="font-semibold mb-1">{item.title}</div>}
                <div className="leading-relaxed">{item.text}</div>
            </div>
        );
    }

    // Gráfico configurado (Spec type=Gráficos) — render directo con ChartRenderer.
    // Item shape: {type: 'configured_chart', spec_id: 9, title?, height?}
    if (item.type === 'configured_chart' && item.spec_id) {
        // Combina: filtros del indicador (Año, Asignatura, Hito, ...) +
        // filtros scoped del dashboard (curso, habilidad activos). Los
        // scoped pisan a los del indicador si hay colisión por nombre.
        const extra = { ...(ctx.dashboardFilters || {}) };
        // cursoActivo (course_selector) → filtro por nombre de dim "Curso".
        // Esa dim existe por convención en TODAS las métricas de evaluación
        // (SIMCE, DIA, IDEL, FL, CV) — ver dataProcessing.js.
        // subpruebaActiva (subprueba_selector) → en SIMCE/DIA/FL/CV la dim
        // se llama "Habilidad"; en IDEL se llama "Subprueba". Inyectamos
        // ambos: el backend ignora silenciosamente la dim que la métrica
        // no tenga (igualdad por nombre), así un único selector sirve para
        // todas las evaluaciones sin romper compatibilidad.
        if (cursoActivo) extra["Curso"] = cursoActivo;
        if (subpruebaActiva) {
            // Habilidad → SIMCE/DIA/FL/CV. Subprueba/Evaluación → IDEL.
            // El backend ignora filtros con keys que no son dims de la métrica.
            extra["Habilidad"] = subpruebaActiva;
            extra["Subprueba"] = subpruebaActiva;
            extra["Evaluación"] = subpruebaActiva;
        }
        return (
            <div>
                {item.title && (
                    <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
                        {item.title}
                    </h3>
                )}
                <ChartRenderer
                    chartId={item.spec_id}
                    extraFilters={Object.keys(extra).length ? extra : null}
                    height={item.height || 360}
                />
            </div>
        );
    }

    // Tabla configurada (Spec type=Tablas) — render directo con TableRenderer.
    // Item shape: {type: 'configured_table', spec_id: 9, title?, pageSize?}
    if (item.type === 'configured_table' && item.spec_id) {
        // Inyecta filtros del indicador + filtros scoped del dashboard
        // como extra_filters de la tabla. El backend valida si esas
        // dimensiones existen en la métrica subyacente.
        const extra = { ...(ctx.dashboardFilters || {}) };
        // Mismo razonamiento que en configured_chart: Habilidad (SIMCE/DIA/
        // FL/CV) y Subprueba (IDEL) coexisten; el backend descarta la que
        // no aplica a la métrica.
        if (cursoActivo) extra["Curso"] = cursoActivo;
        if (subpruebaActiva) {
            // Habilidad → SIMCE/DIA/FL/CV. Subprueba/Evaluación → IDEL.
            // El backend ignora filtros con keys que no son dims de la métrica.
            extra["Habilidad"] = subpruebaActiva;
            extra["Subprueba"] = subpruebaActiva;
            extra["Evaluación"] = subpruebaActiva;
        }
        return (
            <div>
                {item.title && (
                    <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
                        {item.title}
                    </h3>
                )}
                <TableRenderer
                    tableId={item.spec_id}
                    extraFilters={Object.keys(extra).length ? extra : null}
                    pageSize={item.pageSize || 50}
                />
            </div>
        );
    }

    // Formato nuevo: type = nombre del componente; formato viejo: component = nombre del componente
    const componentId = item.component || item.type;
    const Comp = COMPONENT_MAP[componentId];
    if (!Comp) return null;

    const missingFields = getMissingFields(componentId, item);
    if (missingFields.length > 0) {
        return <MissingConfigError componentId={componentId} missingFields={missingFields} />;
    }

    const props = buildComponentProps(componentId, ctx, item, activeValueIdx);
    const title = item.title || AUTO_TITLES[componentId];

    if (componentId === 'TablaAlumnos' && datosCurso.estudiantes.length === 0) return null;
    if (componentId === 'TablaPreguntas' && datosCurso.preguntas.length === 0) return null;
    if (componentId === 'GraficoHabilidades' && (!activeRoles?.habilidad || datosCurso.preguntas.length === 0)) return null;

    const isTable = item.type === 'table' || ['PivotTable', 'FilterableTable', 'SummaryTable', 'DetailListTable', 'DetailListWithProgress', 'StudentRiskList'].includes(componentId);
    const hasLegacyToggle = props.toggle;
    const hasValueToggle = Array.isArray(item.valueField) && item.valueField.length > 1;

    // S2.8 — habilitar export CSV si el componente recibe `records`
    const exportableRecords = Array.isArray(props.records) && props.records.length > 0 ? props.records : null;
    const handleExportCsv = () => {
        const base = (title || componentId).replace(/[^a-z0-9-]+/gi, '-').replace(/^-|-$/g, '').toLowerCase();
        const stamp = new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-');
        downloadCsv(exportableRecords, `${base || 'export'}_${stamp}.csv`);
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-4 gap-2">
                {title && <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">{title}</h3>}
                <div className="flex items-center gap-2 ml-auto">
                    {hasLegacyToggle && props.toggle}
                    {hasValueToggle && (
                        <ValueFieldToggle
                            fields={item.valueField}
                            activeIdx={activeValueIdx}
                            onChange={setActiveValueIdx}
                            computed={computed}
                        />
                    )}
                    {exportableRecords && (
                        <button
                            onClick={handleExportCsv}
                            title="Descargar CSV"
                            className="p-1.5 rounded-md text-slate-300 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors"
                        >
                            <Download size={14} />
                        </button>
                    )}
                </div>
            </div>
            <div className={isTable ? 'bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm' : ''}>
                {(() => {
                    // Empty-state contextual: sólo para componentes Plotly que reciben `records`.
                    // Los legacy/kpi/selector no pasan por aquí porque no tienen `records` en props.
                    if (!Array.isArray(props.records)) return <Comp {...props} />;
                    const hasFilter = !!(item.filter) || !!cursoActivo || !!subpruebaActiva;
                    const reason = emptyReason({ records: props.records, activeFilters: hasFilter });
                    if (reason) {
                        return (
                            <div className="p-4">
                                <EmptyState
                                    reason={reason}
                                    onClearFilters={hasFilter ? () => {
                                        setCursoActivo?.(null);
                                        setSubpruebaActiva?.(null);
                                    } : undefined}
                                />
                            </div>
                        );
                    }
                    return <Comp {...props} />;
                })()}
            </div>
            {(() => {
                if (item.hideMicrocopy) return null;
                const fn = microcopyFor(componentId);
                if (!fn) return null;
                try {
                    const txt = fn(props.records || [], {
                        groupField: props.groupField,
                        levelField: props.categoryField || props.levelField,
                        xField: props.xField,
                        yField: props.yField,
                        valueField: props.valueField,
                        entityField: props.entityField,
                        timeField: props.timeField,
                        achievementLevels: computed.achievement_levels || [],
                    });
                    if (!txt) return null;
                    return <p className="mt-3 text-sm italic text-slate-500 dark:text-slate-400">{txt}</p>;
                } catch { return null; }
            })()}
        </div>
    );
}

// ── Row renderer ──────────────────────────────────────────────────────────────

// Breakpoints más agresivos: colapsa a 1 col <1024px. Para 4 cols,
// en mobile <=768px queda 1 col (los KPIs arriba quedan legibles),
// hasta md=2, hasta lg=4.
const GRID_COLS = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-1 lg:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-4',
    6: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-6',
};

function RowRenderer({ row, ctx, tabContext }) {
    const visibleItems = row.items.filter(item => itemIsVisible(item, ctx.computed.activeRoles));
    if (visibleItems.length === 0) return null;

    const cols = Math.min(row.cols || 1, visibleItems.length);
    const gridClass = GRID_COLS[cols] || 'grid-cols-1';

    return (
        <div className={'grid ' + gridClass + ' gap-8'}>
            {visibleItems.map((item, idx) => (
                <ItemRenderer key={idx} item={item} ctx={ctx} tabContext={tabContext} />
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

export function DashboardRenderer({ layout, computed, datosCurso, cursoActivo, setCursoActivo, subpruebaActiva, setSubpruebaActiva, onCursoClick, derivedColumns, dashboardFilters }) {
    const [activeTab, setActiveTab] = useState(0);
    const [metricLogro, setMetricLogro] = useState('logro');
    const [metricBoxplot, setMetricBoxplot] = useState('logro');

    // S2.6: limpiar filtros scoped (curso / subprueba) al cambiar de tab.
    // Los filtros item-level (filter) son estáticos por item, no se tocan.
    useEffect(() => {
        setCursoActivo?.(null);
        setSubpruebaActiva?.(null);
    }, [activeTab]);

    // Aplicar columnas derivadas del indicador sobre los records
    const enrichedEstudiantes = useMemo(
        () => applyDerivedColumns(computed?.estudiantes || [], derivedColumns || []),
        [computed?.estudiantes, derivedColumns]
    );
    const enrichedComputed = useMemo(
        () => ({ ...computed, estudiantes: enrichedEstudiantes }),
        [computed, enrichedEstudiantes]
    );

    // Si no hay layout configurado, mostrar placeholder — sin fallback SIMCE
    if (!layout?.tabs?.length) return <EmptyLayoutPlaceholder />;

    const resolvedLayout = layout;

    const ctx = {
        computed: enrichedComputed, datosCurso, cursoActivo, setCursoActivo,
        subpruebaActiva, setSubpruebaActiva, onCursoClick,
        metricLogro, setMetricLogro, metricBoxplot, setMetricBoxplot,
        // Filtros del indicador (Año, Asignatura, Hito, etc.) propagados a
        // los items configured_table / configured_chart como extra_filters.
        // Llaves son nombres de dimensión, valores pueden ser str | str[].
        dashboardFilters: dashboardFilters || {},
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
                {resolvedLayout.tabs[activeTab] && (() => {
                    const tabContext = {
                        hasSubpruebaSelector: resolvedLayout.tabs[activeTab].rows.some(
                            r => r.items.some(i => i.type === 'subprueba_selector')
                        ),
                    };
                    return (
                    <div className="space-y-8">
                        {resolvedLayout.tabs[activeTab].rows.map((row, rowIdx) => (
                            <RowRenderer key={rowIdx} row={row} ctx={ctxWithCursoClick} tabContext={tabContext} />
                        ))}
                        {resolvedLayout.tabs[activeTab].rows.some(r => r.items.some(i => i.type === 'course_selector')) && !cursoActivo && (
                            <div className="text-center py-8 text-slate-400 text-sm">
                                Selecciona un curso desde la tabla de resumen para ver el detalle.
                            </div>
                        )}
                    </div>
                    );
                })()}
            </div>
        </div>
    );
}
