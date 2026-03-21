/**
 * comparison.jsx — Gráficos de comparación
 *
 * Componentes:
 *   BarByGroup              — Promedio de una métrica por grupo (ej. logro por curso)
 *   HorizontalBarByDimension — Promedio por dimensión secundaria (ej. habilidad)
 *   GroupedBarByPeriod      — Promedio por grupo × periodo temporal
 */

import React from 'react';
import PlotlyWrapper from './PlotlyWrapper';
import { avg, formatValue, formatRange, CATEGORY_COLORS } from './constants';

// ── BarByGroup ────────────────────────────────────────────────────────────────
/**
 * Props:
 *   records     Array<Object>   filas de datos
 *   groups      string[]        valores únicos del grupo principal (eje X)
 *   groupField  string          campo de agrupación en records (ej. "_curso")
 *   valueField  string          campo numérico a agregar (ej. "_rend")
 *   valueLabel  string          etiqueta del valor para el tooltip
 *   formatValue (v) => string   formateador del valor
 *   colors      string[]        paleta de colores por grupo
 *   height      number
 */
export function BarByGroup({
    records = [],
    groups = [],
    groupField = '_curso',
    valueField = '_rend',
    valueLabel = 'Valor',
    formatValue: fmt = (v) => String(v),
    colors = CATEGORY_COLORS,
    height,
}) {
    const groupList = groups.length
        ? groups
        : [...new Set(records.map(r => r[groupField]).filter(Boolean))].sort();

    const values = groupList.map(g =>
        avg(records.filter(r => r[groupField] === g), valueField)
    );

    const trace = {
        type: 'bar',
        x: groupList,
        y: values,
        marker: { color: groupList.map((_, i) => colors[i % colors.length]) },
        text: values.map(v => fmt(v)),
        textposition: 'outside',
        textfont: { size: 12, color: '#334155' },
        hovertemplate: `<b>%{x}</b><br>${valueLabel}: %{text}<extra></extra>`,
    };

    const [yMin, yMax] = formatRange(null);
    const maxVal = Math.max(...values.filter(v => !isNaN(v)), 0);

    return (
        <PlotlyWrapper
            data={[trace]}
            layout={{
                yaxis: { range: [0, (yMax ?? (maxVal * 1.15 || 1))] },
                margin: { t: 24, r: 16, b: 40, l: 48 },
            }}
            height={height || 260}
        />
    );
}

// ── HorizontalBarByDimension ─────────────────────────────────────────────────
/**
 * Props:
 *   records        Array<Object>
 *   dimensionField string    campo cuyas categorías son el eje Y (ej. "_habilidad")
 *   valueField     string    campo numérico a agregar (ej. "_logro_pregunta")
 *   valueLabel     string
 *   formatValue    (v) => string
 *   color          string    color único de las barras
 *   height         number
 */
export function HorizontalBarByDimension({
    records = [],
    dimensionField = '_habilidad',
    valueField = '_logro_pregunta',
    valueLabel = 'Valor',
    formatValue: fmt = (v) => String(v),
    color = CATEGORY_COLORS[0],
    height,
}) {
    const dims = [...new Set(records.map(r => r[dimensionField]).filter(Boolean))];
    if (!dims.length) return <p className="text-slate-400 text-sm p-4">Sin datos</p>;

    const values = dims.map(d =>
        avg(records.filter(r => r[dimensionField] === d), valueField)
    );

    const trace = {
        type: 'bar',
        orientation: 'h',
        y: dims,
        x: values,
        marker: { color },
        text: values.map(v => fmt(v)),
        textposition: 'outside',
        textfont: { size: 12 },
        hovertemplate: `<b>%{y}</b><br>${valueLabel}: %{text}<extra></extra>`,
    };

    const dynamicHeight = Math.max(200, dims.length * 44 + 60);

    return (
        <PlotlyWrapper
            data={[trace]}
            layout={{
                margin: { t: 16, r: 60, b: 40, l: 100 },
                xaxis: { range: [0, null] },
                yaxis: { automargin: true },
            }}
            height={height || dynamicHeight}
        />
    );
}

// ── GroupedBarByPeriod ────────────────────────────────────────────────────────
/**
 * Props:
 *   records       Array<Object>
 *   groups        string[]        grupos (ej. cursos) — cada grupo = una barra dentro del periodo
 *   groupField    string          campo de grupo (ej. "_curso")
 *   valueField    string          campo numérico a agregar
 *   periodField   string          campo de periodo (ej. "_evaluacion_num")
 *   periodLabels  Object          mapa periodo → etiqueta display (ej. {1: "Ev. 1"})
 *   valueLabel    string
 *   formatValue   (v) => string
 *   colors        string[]
 *   height        number
 */
export function GroupedBarByPeriod({
    records = [],
    groups = [],
    groupField = '_curso',
    valueField = '_rend',
    periodField = '_evaluacion_num',
    periodLabels = {},
    valueLabel = 'Valor',
    formatValue: fmt = (v) => String(v),
    colors = CATEGORY_COLORS,
    height,
}) {
    const groupList = groups.length
        ? groups
        : [...new Set(records.map(r => r[groupField]).filter(Boolean))].sort();

    const periods = [...new Set(records.map(r => r[periodField]).filter(v => v != null))].sort((a, b) => a - b);
    if (!periods.length) return <p className="text-slate-400 text-sm p-4">Sin datos</p>;

    const getLabel = (p) => periodLabels[p] ?? String(p);

    const traces = groupList.map((g, i) => ({
        type: 'bar',
        name: String(g),
        x: periods.map(getLabel),
        y: periods.map(p => avg(records.filter(r => r[groupField] === g && r[periodField] === p), valueField)),
        marker: { color: colors[i % colors.length] },
        text: periods.map(p => fmt(avg(records.filter(r => r[groupField] === g && r[periodField] === p), valueField))),
        textposition: 'outside',
        textfont: { size: 11 },
        hovertemplate: `<b>${g}</b><br>%{x}<br>${valueLabel}: %{text}<extra></extra>`,
    }));

    return (
        <PlotlyWrapper
            data={traces}
            layout={{
                barmode: 'group',
                legend: { orientation: 'h', y: -0.2 },
                margin: { t: 24, r: 16, b: 60, l: 48 },
            }}
            height={height || 280}
        />
    );
}
