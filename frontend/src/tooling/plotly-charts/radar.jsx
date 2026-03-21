/**
 * radar.jsx — Gráfico de radar
 *
 * Componentes:
 *   RadarProfile — Perfil multi-eje por grupo
 */

import React from 'react';
import PlotlyWrapper from './PlotlyWrapper';
import { avg, formatValue, CATEGORY_COLORS } from './constants';

// ── RadarProfile ──────────────────────────────────────────────────────────────
/**
 * Props:
 *   records       Array<Object>
 *   groups        string[]         grupos (cada grupo = una traza en el radar)
 *   groupField    string           campo de grupo (ej. "_curso")
 *   axisField     string           campo cuyos valores únicos son los ejes del radar (ej. "_habilidad")
 *   valueField    string           campo numérico a agregar por eje (ej. "_logro_pregunta")
 *   formatValue   (v) => string
 *   colors        string[]
 *   height        number
 *
 * Nota: si groups tiene 0 o 1 elementos, dibuja una sola traza "Promedio".
 */
export function RadarProfile({
    records = [],
    groups = [],
    groupField = '_curso',
    axisField = '_habilidad',
    valueField = '_logro_pregunta',
    formatValue: fmt = (v) => String(v),
    colors = CATEGORY_COLORS,
    height,
}) {
    if (!records.length) return <p className="text-slate-400 text-sm p-4">Sin datos</p>;

    const axes = [...new Set(records.map(r => r[axisField]).filter(Boolean))];
    if (!axes.length) return <p className="text-slate-400 text-sm p-4">Sin ejes de dimensión</p>;

    const groupList = groups.length
        ? groups
        : [...new Set(records.map(r => r[groupField]).filter(Boolean))].sort();

    const showByGroup = groupList.length > 1 && records.some(r => r[groupField]);

    const buildTrace = (g, i) => {
        const subset = showByGroup ? records.filter(r => r[groupField] === g) : records;
        const r = axes.map(ax => avg(subset.filter(rec => rec[axisField] === ax), valueField));
        const color = colors[i % colors.length];

        return {
            type: 'scatterpolar',
            name: showByGroup ? String(g) : 'Promedio',
            r: [...r, r[0]], // cerrar el polígono
            theta: [...axes, axes[0]],
            fill: 'toself',
            fillcolor: color + '33', // 20% opacity
            line: { color, width: 2 },
            text: [...r, r[0]].map(v => fmt(v)),
            hovertemplate: `<b>%{theta}</b><br>${fmt('%{r}')}<extra></extra>`,
        };
    };

    const traces = showByGroup
        ? groupList.map((g, i) => buildTrace(g, i))
        : [buildTrace(null, 0)];

    return (
        <PlotlyWrapper
            data={traces}
            layout={{
                polar: {
                    radialaxis: {
                        visible: true,
                        range: [0, null],
                        tickfont: { size: 10 },
                        gridcolor: '#e2e8f0',
                    },
                    angularaxis: {
                        tickfont: { size: 12, color: '#64748b' },
                        gridcolor: '#e2e8f0',
                    },
                    bgcolor: 'transparent',
                },
                showlegend: traces.length > 1,
                legend: { orientation: 'h', y: -0.15 },
                margin: { t: 16, r: 40, b: 40, l: 40 },
            }}
            height={height || 320}
        />
    );
}
