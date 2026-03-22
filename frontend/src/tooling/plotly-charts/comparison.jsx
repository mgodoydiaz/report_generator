/**
 * comparison.jsx — Gráficos de comparación
 *
 * Componentes:
 *   BarByGroup              — Promedio de una métrica por grupo (ej. logro por curso)
 *   HorizontalBarByDimension — Promedio por dimensión secundaria (ej. habilidad)
 *   DoubleGroupedBar        — Barras doblemente agrupadas (grupo × subgrupo)
 */

import React from 'react';
import PlotlyWrapper from './PlotlyWrapper';
import { avg, formatValue, formatRange, CATEGORY_COLORS } from './constants';

/** Construye props de eje Y desde un formatStr (para eje numérico/porcentaje). */
function yAxisProps(formatStr) {
    const [yMin, yMax] = formatRange(formatStr);
    const isPct = formatStr?.split('.')[0] === '%';
    return {
        range: [yMin, yMax ?? null],
        tickformat: isPct ? '.0%' : undefined,
        ticksuffix: (!isPct && formatStr?.split('.')[0] === '#') ? '' : undefined,
    };
}

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
    formatStr,
    colors = CATEGORY_COLORS,
    height,
    labelX,
    labelY,
    showLegend,
    showValues,
}) {
    const groupList = groups.length
        ? groups
        : [...new Set(records.map(r => r[groupField]).filter(Boolean))].sort();

    const values = groupList.map(g =>
        avg(records.filter(r => r[groupField] === g), valueField)
    );

    const displayValues = showValues !== false;
    const trace = {
        type: 'bar',
        x: groupList,
        y: values,
        marker: { color: groupList.map((_, i) => colors[i % colors.length]) },
        text: values.map(v => fmt(v)),
        textposition: displayValues ? 'outside' : 'none',
        textfont: { size: 12, color: '#334155' },
        hovertemplate: `<b>%{x}</b><br>${valueLabel}: %{text}<extra></extra>`,
    };

    const maxVal = Math.max(...values.filter(v => !isNaN(v)), 0);
    const yax = yAxisProps(formatStr);
    if (!yax.range[1]) yax.range[1] = maxVal * 1.15 || 1;
    if (labelY) yax.title = { text: labelY, font: { size: 11 } };

    return (
        <PlotlyWrapper
            data={[trace]}
            layout={{
                showlegend: showLegend ?? false,
                yaxis: yax,
                xaxis: labelX ? { title: { text: labelX, font: { size: 11 } } } : {},
                margin: { t: 24, r: 16, b: labelX ? 56 : 40, l: 48 },
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
    formatStr,
    color = CATEGORY_COLORS[0],
    height,
    labelX,
    labelY,
    showLegend,
    showValues,
}) {
    const dims = [...new Set(records.map(r => r[dimensionField]).filter(Boolean))];
    if (!dims.length) return <p className="text-slate-400 text-sm p-4">Sin datos</p>;

    const values = dims.map(d =>
        avg(records.filter(r => r[dimensionField] === d), valueField)
    );

    const displayValues = showValues !== false;
    const trace = {
        type: 'bar',
        orientation: 'h',
        y: dims,
        x: values,
        marker: { color },
        text: values.map(v => fmt(v)),
        textposition: displayValues ? 'outside' : 'none',
        textfont: { size: 12 },
        hovertemplate: `<b>%{y}</b><br>${valueLabel}: %{text}<extra></extra>`,
    };

    const dynamicHeight = Math.max(200, dims.length * 44 + 60);
    const isPct = formatStr?.split('.')[0] === '%';

    return (
        <PlotlyWrapper
            data={[trace]}
            layout={{
                showlegend: showLegend ?? false,
                margin: { t: 16, r: 60, b: labelX ? 56 : 40, l: 100 },
                xaxis: {
                    range: [0, isPct ? 1.1 : null],
                    tickformat: isPct ? '.0%' : undefined,
                    ...(labelX ? { title: { text: labelX, font: { size: 11 } } } : {}),
                },
                yaxis: {
                    automargin: true,
                    ...(labelY ? { title: { text: labelY, font: { size: 11 } } } : {}),
                },
            }}
            height={height || dynamicHeight}
        />
    );
}

// ── DoubleGroupedBar ─────────────────────────────────────────────────────────
/**
 * Barras doblemente agrupadas.
 *
 * Eje X: valores únicos de `groupField` (ej. cursos: "II A", "II B", …)
 * Barras dentro de cada grupo: valores únicos de `subGroupField` (ej. meses, evaluaciones)
 * Eje Y: promedio de `valueField` para cada combinación grupo × subgrupo
 * Leyenda: cada `subGroup` recibe un color.
 *
 * Props:
 *   records         Array<Object>
 *   groupField      string          campo de agrupación principal — eje X (ej. "_curso")
 *   subGroupField   string          campo de sub-agrupación — barras dentro de cada grupo (ej. "_mes")
 *   valueField      string          campo numérico a agregar (ej. "_rend")
 *   subGroupLabels  Object          mapa subGroup → etiqueta display (ej. {1: "Ev. 1"})
 *   valueLabel      string
 *   formatValue     (v) => string
 *   formatStr       string
 *   colors          string[]
 *   height          number
 *   labelX          string
 *   labelY          string
 *   showLegend      boolean
 *   showValues      boolean
 */
export function DoubleGroupedBar({
    records = [],
    groupField = '_curso',
    subGroupField = '_evaluacion_num',
    valueField = '_rend',
    subGroupLabels = {},
    valueLabel = 'Valor',
    formatValue: fmt = (v) => String(v),
    formatStr,
    colors = CATEGORY_COLORS,
    height,
    labelX,
    labelY,
    showLegend,
    showValues,
}) {
    const groupList = [...new Set(records.map(r => r[groupField]).filter(Boolean))].sort();
    const subGroups = [...new Set(records.map(r => r[subGroupField]).filter(v => v != null))].sort((a, b) => {
        // Intentar orden numérico, fallback a string
        const na = Number(a), nb = Number(b);
        if (!isNaN(na) && !isNaN(nb)) return na - nb;
        return String(a).localeCompare(String(b));
    });

    if (!groupList.length || !subGroups.length) return <p className="text-slate-400 text-sm p-4">Sin datos</p>;

    const getSubLabel = (sg) => subGroupLabels[sg] ?? String(sg);
    const displayValues = showValues !== false;

    // Una trace por subGroup (cada subGroup = un color en la leyenda)
    const traces = subGroups.map((sg, i) => ({
        type: 'bar',
        name: getSubLabel(sg),
        x: groupList.map(String),
        y: groupList.map(g => avg(records.filter(r => r[groupField] === g && r[subGroupField] === sg), valueField)),
        marker: { color: colors[i % colors.length] },
        text: groupList.map(g => fmt(avg(records.filter(r => r[groupField] === g && r[subGroupField] === sg), valueField))),
        textposition: displayValues ? 'outside' : 'none',
        textfont: { size: 11 },
        hovertemplate: `<b>%{x}</b><br>${getSubLabel(sg)}<br>${valueLabel}: %{text}<extra></extra>`,
    }));

    const yax = yAxisProps(formatStr);
    if (labelY) yax.title = { text: labelY, font: { size: 11 } };

    return (
        <PlotlyWrapper
            data={traces}
            layout={{
                barmode: 'group',
                showlegend: showLegend ?? true,
                yaxis: yax,
                xaxis: labelX ? { title: { text: labelX, font: { size: 11 } } } : {},
                legend: { orientation: 'h', y: -0.2 },
                margin: { t: 24, r: 16, b: labelX ? 76 : 60, l: 48 },
            }}
            height={height || 280}
        />
    );
}

// Backward compat alias
export const GroupedBarByPeriod = DoubleGroupedBar;
