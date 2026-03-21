/**
 * evolution.jsx — Gráficos de evolución temporal
 *
 * Componentes:
 *   TrendLine — Tendencia de una métrica por grupo a lo largo del tiempo
 */

import React from 'react';
import PlotlyWrapper from './PlotlyWrapper';
import { avg, CATEGORY_COLORS } from './constants';

// ── TrendLine ─────────────────────────────────────────────────────────────────
/**
 * Props:
 *   records       Array<Object>
 *   groups        string[]         grupos a graficar como líneas (ej. cursos)
 *   groupField    string           campo de grupo (ej. "_curso")
 *   valueField    string           campo numérico a agregar (ej. "_rend")
 *   periodField   string           campo de periodo (ej. "_evaluacion_num")
 *   periodLabels  Object           mapa periodo → etiqueta para el eje X
 *   valueLabel    string           etiqueta del valor
 *   formatValue   (v) => string
 *   colors        string[]
 *   height        number
 */
export function TrendLine({
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
    const xLabels = periods.map(getLabel);

    const traces = groupList.map((g, i) => {
        const yValues = periods.map(p => {
            const subset = records.filter(r => r[groupField] === g && r[periodField] === p);
            return subset.length ? avg(subset, valueField) : null;
        });

        return {
            type: 'scatter',
            mode: 'lines+markers+text',
            name: String(g),
            x: xLabels,
            y: yValues,
            line: { color: colors[i % colors.length], width: 2.5 },
            marker: { color: colors[i % colors.length], size: 8 },
            text: yValues.map(v => v != null ? fmt(v) : ''),
            textposition: 'top center',
            textfont: { size: 11 },
            connectgaps: true,
            hovertemplate: `<b>${g}</b><br>%{x}<br>${valueLabel}: %{text}<extra></extra>`,
        };
    });

    const hasLongLabels = xLabels.some(l => l.length > 6);

    return (
        <PlotlyWrapper
            data={traces}
            layout={{
                legend: { orientation: 'h', y: -0.25 },
                margin: { t: 24, r: 16, b: hasLongLabels ? 70 : 50, l: 48 },
                xaxis: { tickangle: hasLongLabels ? -30 : 0 },
            }}
            height={height || 280}
        />
    );
}
