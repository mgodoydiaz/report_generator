/**
 * heatmap.jsx — Matriz de calor
 *
 * Componente:
 *   HeatmapMatrix — Cruce de dos dimensiones con intensidad por color
 */

import React from 'react';
import PlotlyWrapper from './PlotlyWrapper';
import { formatRange } from './constants';

/**
 * Props:
 *   records     Array<Object>
 *   xField      string   dimensión del eje X
 *   yField      string   dimensión del eje Y
 *   valueField  string   campo numérico agregado por promedio
 *   aggregation 'avg'|'sum'|'count'  (default 'avg')
 *   colorscale  string   Plotly colorscale (default 'Viridis')
 *   formatStr   string
 *   formatValue (v)=>string
 *   height      number
 *   labelX, labelY, showLegend
 *   showValues  bool (default true)
 */
function parseTickMap(raw) {
    if (!raw || typeof raw !== 'string') return {};
    const out = {};
    raw.split(/\r?\n/).forEach(line => {
        const m = line.match(/^\s*([^=]+?)\s*=\s*(.+?)\s*$/);
        if (m) out[m[1].toLowerCase()] = m[2];
    });
    return out;
}

function applyTickTransform(label, transform, tickMap) {
    const key = String(label).toLowerCase();
    if (tickMap[key] != null) return tickMap[key];
    const s = String(label);
    if (transform === 'upper') return s.toUpperCase();
    if (transform === 'lower') return s.toLowerCase();
    if (transform === 'title') return s.replace(/\w\S*/g, w => w[0].toUpperCase() + w.slice(1).toLowerCase());
    return s;
}

export function HeatmapMatrix({
    records = [],
    xField,
    yField,
    valueField,
    aggregation = 'avg',
    achievement_levels = [],
    colorscale = 'YlOrRd',
    reverseColorscale = false,
    xTickCase = 'none',
    yTickCase = 'none',
    xTickMap,
    yTickMap,
    formatStr,
    formatValue: fmt = (v) => (v == null ? '—' : Number(v).toFixed(2)),
    height,
    labelX,
    labelY,
    showLegend,
    showValues,
}) {
    if (!xField || !yField || !valueField) {
        return <p className="text-slate-400 text-sm p-4">Configuración incompleta</p>;
    }

    const xs = [...new Set(records.map(r => r[xField]).filter(v => v != null))].sort();
    const ys = [...new Set(records.map(r => r[yField]).filter(v => v != null))].sort();

    if (!xs.length || !ys.length) {
        return <p className="text-slate-400 text-sm p-4">Sin datos</p>;
    }

    const aggregate = (vals) => {
        if (aggregation === 'count_true') {
            return vals.filter(v => v === true || v === 1 || v === '1').length;
        }
        if (aggregation === 'mean_percent') {
            if (!vals.length) return null;
            const trueCount = vals.filter(v => v === true || v === 1 || v === '1').length;
            return trueCount / vals.length;
        }
        const clean = vals.filter(v => v != null && !isNaN(Number(v)));
        if (!clean.length) return null;
        if (aggregation === 'sum') return clean.reduce((a, b) => a + Number(b), 0);
        if (aggregation === 'count') return clean.length;
        if (aggregation === 'min') return Math.min(...clean.map(Number));
        if (aggregation === 'max') return Math.max(...clean.map(Number));
        return clean.reduce((a, b) => a + Number(b), 0) / clean.length;
    };

    const z = ys.map(y => xs.map(x => {
        const cell = records.filter(r => r[xField] === x && r[yField] === y).map(r => r[valueField]);
        return aggregate(cell);
    }));

    const text = z.map(row => row.map(v => (v == null ? '' : fmt(v))));

    const [zMin, zMax] = formatRange(formatStr);
    const display = showValues !== false;

    const xMap = parseTickMap(xTickMap);
    const yMap = parseTickMap(yTickMap);
    const xsDisplay = xs.map(v => applyTickTransform(v, xTickCase, xMap));
    const ysDisplay = ys.map(v => applyTickTransform(v, yTickCase, yMap));

    const trace = {
        type: 'heatmap',
        x: xsDisplay,
        y: ysDisplay,
        z,
        text,
        texttemplate: display ? '%{text}' : '',
        textfont: { size: 11 },
        colorscale,
        reversescale: !!reverseColorscale,
        zmin: zMin,
        zmax: zMax ?? undefined,
        hovertemplate: `<b>%{y} × %{x}</b><br>Valor: %{text}<extra></extra>`,
        showscale: showLegend ?? true,
    };

    const dynamicHeight = Math.max(240, 80 + ys.length * 32);

    return (
        <PlotlyWrapper
            data={[trace]}
            layout={{
                margin: { t: 16, r: 16, b: labelX ? 60 : 48, l: labelY ? 80 : 64 },
                xaxis: { tickangle: -30, ...(labelX ? { title: { text: labelX, font: { size: 11 } } } : {}) },
                yaxis: { automargin: true, ...(labelY ? { title: { text: labelY, font: { size: 11 } } } : {}) },
            }}
            height={height || dynamicHeight}
        />
    );
}
