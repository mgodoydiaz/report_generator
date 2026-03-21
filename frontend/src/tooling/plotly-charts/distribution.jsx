/**
 * distribution.jsx — Gráficos de distribución
 *
 * Componentes:
 *   BoxPlotByGroup            — Distribución estadística por grupo
 *   PieComposition            — Composición de categorías (donut)
 *   StackedCountByGroup       — Conteo de categorías por grupo
 *   StackedCountByGroupAndPeriod — Conteo por grupo × periodo
 */

import React from 'react';
import PlotlyWrapper from './PlotlyWrapper';
import { CATEGORY_COLORS, LOGRO_COLORS, levelColors } from './constants';

// ── BoxPlotByGroup ────────────────────────────────────────────────────────────
/**
 * Props:
 *   records     Array<Object>
 *   groups      string[]
 *   groupField  string    campo de agrupación (ej. "_curso")
 *   valueField  string    campo numérico (ej. "_rend")
 *   formatValue (v) => string
 *   colors      string[]
 *   height      number
 */
export function BoxPlotByGroup({
    records = [],
    groups = [],
    groupField = '_curso',
    valueField = '_rend',
    formatValue: fmt = (v) => String(v),
    colors = CATEGORY_COLORS,
    height,
}) {
    const groupList = groups.length
        ? groups
        : [...new Set(records.map(r => r[groupField]).filter(Boolean))].sort();

    const traces = groupList.map((g, i) => ({
        type: 'box',
        name: String(g),
        y: records.filter(r => r[groupField] === g).map(r => r[valueField]).filter(v => v != null),
        marker: { color: colors[i % colors.length] },
        boxmean: false,
        hovertemplate: `<b>${g}</b><br>Q3: %{q3}<br>Mediana: %{median}<br>Q1: %{q1}<extra></extra>`,
    }));

    if (!traces.length) return <p className="text-slate-400 text-sm p-4">Sin datos</p>;

    return (
        <PlotlyWrapper
            data={traces}
            layout={{
                showlegend: false,
                margin: { t: 16, r: 16, b: 40, l: 48 },
            }}
            height={height || 280}
        />
    );
}

// ── PieComposition ────────────────────────────────────────────────────────────
/**
 * Props:
 *   records         Array<Object>
 *   categoryField   string    campo con la categoría (ej. "_logro")
 *   categoryLevels  string[]  niveles ordenados (ej. ["Insuficiente","Elemental","Adecuado"])
 *   categoryColors  Object    mapa nivel → color (usa LOGRO_COLORS si no se pasa)
 *   height          number
 */
export function PieComposition({
    records = [],
    categoryField = '_logro',
    categoryLevels = [],
    categoryColors = null,
    height,
}) {
    const levels = categoryLevels.length
        ? categoryLevels
        : [...new Set(records.map(r => r[categoryField]).filter(Boolean))];

    const autoColors = levelColors(levels);
    const getColor = (level, i) => {
        if (categoryColors?.[level]) return categoryColors[level];
        return autoColors[i] ?? CATEGORY_COLORS[i % CATEGORY_COLORS.length];
    };

    const values = levels.map(l => records.filter(r => r[categoryField] === l).length);
    const filteredLevels = levels.filter((_, i) => values[i] > 0);
    const filteredValues = values.filter(v => v > 0);

    if (!filteredValues.length) return <p className="text-slate-400 text-sm p-4">Sin datos</p>;

    const trace = {
        type: 'pie',
        labels: filteredLevels,
        values: filteredValues,
        marker: { colors: filteredLevels.map((l, i) => getColor(l, levels.indexOf(l))) },
        hole: 0.45,
        textinfo: 'label+percent',
        hovertemplate: '<b>%{label}</b><br>%{value} alumnos (%{percent})<extra></extra>',
    };

    return (
        <PlotlyWrapper
            data={[trace]}
            layout={{
                showlegend: false,
                margin: { t: 16, r: 16, b: 16, l: 16 },
            }}
            height={height || 260}
        />
    );
}

// ── StackedCountByGroup ───────────────────────────────────────────────────────
/**
 * Props:
 *   records         Array<Object>
 *   groups          string[]
 *   groupField      string    campo de agrupación (ej. "_curso")
 *   categoryField   string    campo de categoría (ej. "_logro")
 *   categoryLevels  string[]  niveles ordenados
 *   categoryColors  Object    mapa nivel → color
 *   height          number
 */
export function StackedCountByGroup({
    records = [],
    groups = [],
    groupField = '_curso',
    categoryField = '_logro',
    categoryLevels = [],
    categoryColors = null,
    height,
}) {
    const groupList = groups.length
        ? groups
        : [...new Set(records.map(r => r[groupField]).filter(Boolean))].sort();

    const levels = categoryLevels.length
        ? categoryLevels
        : [...new Set(records.map(r => r[categoryField]).filter(Boolean))];

    const autoColors = levelColors(levels);
    const getColor = (level, i) => {
        if (categoryColors?.[level]) return categoryColors[level];
        return autoColors[i] ?? CATEGORY_COLORS[i % CATEGORY_COLORS.length];
    };

    const traces = levels.map((level, i) => ({
        type: 'bar',
        name: String(level),
        x: groupList,
        y: groupList.map(g => records.filter(r => r[groupField] === g && r[categoryField] === level).length),
        marker: { color: getColor(level, i) },
        hovertemplate: `<b>${level}</b><br>%{x}: %{y} alumnos<extra></extra>`,
        text: groupList.map(g => {
            const cnt = records.filter(r => r[groupField] === g && r[categoryField] === level).length;
            return cnt > 0 ? String(cnt) : '';
        }),
        textposition: 'inside',
        textfont: { color: '#fff', size: 11 },
    }));

    return (
        <PlotlyWrapper
            data={traces}
            layout={{
                barmode: 'stack',
                legend: { orientation: 'h', y: -0.2 },
                margin: { t: 16, r: 16, b: 60, l: 40 },
                yaxis: { title: null },
            }}
            height={height || 260}
        />
    );
}

// ── StackedCountByGroupAndPeriod ──────────────────────────────────────────────
/**
 * Props:
 *   records         Array<Object>
 *   groups          string[]
 *   groupField      string
 *   categoryField   string
 *   categoryLevels  string[]
 *   categoryColors  Object
 *   periodField     string    campo de periodo (ej. "_evaluacion_num")
 *   periodLabels    Object    mapa periodo → etiqueta
 *   height          number
 */
export function StackedCountByGroupAndPeriod({
    records = [],
    groups = [],
    groupField = '_curso',
    categoryField = '_logro',
    categoryLevels = [],
    categoryColors = null,
    periodField = '_evaluacion_num',
    periodLabels = {},
    height,
}) {
    const groupList = groups.length
        ? groups
        : [...new Set(records.map(r => r[groupField]).filter(Boolean))].sort();

    const periods = [...new Set(records.map(r => r[periodField]).filter(v => v != null))].sort((a, b) => a - b);

    const levels = categoryLevels.length
        ? categoryLevels
        : [...new Set(records.map(r => r[categoryField]).filter(Boolean))];

    const autoColors = levelColors(levels);
    const getColor = (level, i) => {
        if (categoryColors?.[level]) return categoryColors[level];
        return autoColors[i] ?? CATEGORY_COLORS[i % CATEGORY_COLORS.length];
    };

    const getLabel = (p) => periodLabels[p] ?? String(p);

    // X axis: one tick per (group × period), with separators between groups
    // Build pairs: [{group, period, xLabel}]
    const pairs = [];
    const groupStartIdx = {};
    groupList.forEach(g => {
        groupStartIdx[g] = pairs.length;
        const periodList = periods.length ? periods : [1];
        periodList.forEach(p => pairs.push({ group: g, period: p, xLabel: getLabel(p) }));
    });

    // Build traces per level
    const traces = levels.map((level, i) => ({
        type: 'bar',
        name: String(level),
        x: pairs.map((_, idx) => idx),
        y: pairs.map(({ group, period }) =>
            records.filter(r => r[groupField] === group && r[periodField] === period && r[categoryField] === level).length
        ),
        marker: { color: getColor(level, i) },
        text: pairs.map(({ group, period }) => {
            const cnt = records.filter(r => r[groupField] === group && r[periodField] === period && r[categoryField] === level).length;
            return cnt > 0 ? String(cnt) : '';
        }),
        textposition: 'inside',
        textfont: { color: '#fff', size: 10 },
        hovertemplate: `<b>${level}</b><br>Ev. %{x}<br>%{y} alumnos<extra></extra>`,
    }));

    // Separators between groups as layout shapes
    const shapes = Object.values(groupStartIdx).slice(1).map(startIdx => ({
        type: 'line',
        x0: startIdx - 0.5,
        x1: startIdx - 0.5,
        y0: 0,
        y1: 1,
        yref: 'paper',
        line: { color: '#1e293b', width: 2, dash: 'dot' },
    }));

    // Annotations for group labels
    const annotations = groupList.map(g => {
        const start = groupStartIdx[g];
        const nextG = groupList[groupList.indexOf(g) + 1];
        const end = nextG != null ? groupStartIdx[nextG] - 1 : pairs.length - 1;
        return {
            x: (start + end) / 2,
            y: -0.18,
            yref: 'paper',
            text: `<b>${g}</b>`,
            showarrow: false,
            font: { size: 12, color: '#334155' },
        };
    });

    const dynamicHeight = Math.max(280, 200 + pairs.length * 10);

    return (
        <PlotlyWrapper
            data={traces}
            layout={{
                barmode: 'stack',
                shapes,
                annotations,
                xaxis: {
                    tickmode: 'array',
                    tickvals: pairs.map((_, i) => i),
                    ticktext: pairs.map(p => p.xLabel),
                    tickangle: -35,
                    tickfont: { size: 11 },
                },
                legend: { orientation: 'h', y: -0.3 },
                margin: { t: 16, r: 16, b: 80, l: 40 },
            }}
            height={height || dynamicHeight}
        />
    );
}
