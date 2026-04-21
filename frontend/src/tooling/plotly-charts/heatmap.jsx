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
export function HeatmapMatrix({
    records = [],
    xField,
    yField,
    valueField,
    aggregation = 'avg',
    colorscale = 'Viridis',
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
        const clean = vals.filter(v => v != null && !isNaN(v));
        if (!clean.length) return null;
        if (aggregation === 'sum') return clean.reduce((a, b) => a + b, 0);
        if (aggregation === 'count') return clean.length;
        if (aggregation === 'min') return Math.min(...clean);
        if (aggregation === 'max') return Math.max(...clean);
        return clean.reduce((a, b) => a + b, 0) / clean.length;
    };

    const z = ys.map(y => xs.map(x => {
        const cell = records.filter(r => r[xField] === x && r[yField] === y).map(r => r[valueField]);
        return aggregate(cell);
    }));

    const text = z.map(row => row.map(v => (v == null ? '' : fmt(v))));

    const [zMin, zMax] = formatRange(formatStr);
    const display = showValues !== false;

    const trace = {
        type: 'heatmap',
        x: xs.map(String),
        y: ys.map(String),
        z,
        text,
        texttemplate: display ? '%{text}' : '',
        textfont: { size: 11 },
        colorscale,
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
