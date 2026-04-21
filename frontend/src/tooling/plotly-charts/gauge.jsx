/**
 * gauge.jsx — Indicador tipo gauge (medidor KPI)
 *
 * Componente:
 *   GaugeIndicator — Medidor con rangos verde/amarillo/rojo configurables
 */

import React from 'react';
import PlotlyWrapper from './PlotlyWrapper';

/**
 * Props:
 *   records     Array<Object>
 *   valueField  string   campo numérico a agregar
 *   aggregation 'avg'|'sum'|'min'|'max'|'count'  (default 'avg')
 *   min         number   (default 0)
 *   max         number   (default 1 si formatStr='%' else 100)
 *   thresholds  { low: number, high: number }  límites entre rojo/amarillo/verde
 *                Valores en la misma unidad que el dato (ej. 0.6, 0.8 para %)
 *   formatStr   string   usado para derivar rango si no se pasa min/max
 *   formatValue (v)=>string
 *   height      number
 *   labelX (usado como título del gauge)
 */
export function GaugeIndicator({
    records = [],
    valueField,
    aggregation = 'avg',
    min,
    max,
    thresholds,
    formatStr,
    formatValue: fmt,
    height,
    labelX,
    showLegend: _showLegend,
}) {
    if (!valueField) {
        return <p className="text-slate-400 text-sm p-4">Configuración incompleta</p>;
    }

    const vals = records.map(r => r[valueField]).filter(v => v != null && !isNaN(v));
    if (!vals.length) return <p className="text-slate-400 text-sm p-4">Sin datos</p>;

    const value = (() => {
        if (aggregation === 'sum') return vals.reduce((a, b) => a + b, 0);
        if (aggregation === 'count') return vals.length;
        if (aggregation === 'min') return Math.min(...vals);
        if (aggregation === 'max') return Math.max(...vals);
        return vals.reduce((a, b) => a + b, 0) / vals.length;
    })();

    const isPct = formatStr?.split('.')[0] === '%';
    const axisMin = min ?? 0;
    const axisMax = max ?? (isPct ? 1 : 100);

    const tLow = thresholds?.low ?? (axisMin + (axisMax - axisMin) * 0.6);
    const tHigh = thresholds?.high ?? (axisMin + (axisMax - axisMin) * 0.8);

    const defaultFmt = (v) => {
        if (isPct) return `${(v * 100).toFixed(1)}%`;
        return Number(v).toFixed(2);
    };
    const formatFn = fmt || defaultFmt;

    const trace = {
        type: 'indicator',
        mode: 'gauge+number',
        value,
        number: {
            valueformat: isPct ? '.1%' : undefined,
            font: { size: 36 },
        },
        title: labelX ? { text: labelX, font: { size: 14 } } : undefined,
        gauge: {
            axis: {
                range: [axisMin, axisMax],
                tickformat: isPct ? '.0%' : undefined,
            },
            bar: { color: '#1e293b' },
            steps: [
                { range: [axisMin, tLow], color: '#fecaca' },
                { range: [tLow, tHigh], color: '#fde68a' },
                { range: [tHigh, axisMax], color: '#bbf7d0' },
            ],
            threshold: {
                line: { color: '#0f172a', width: 3 },
                thickness: 0.8,
                value,
            },
        },
    };

    // texto adicional debajo para valores formateados custom
    const showCustomFormat = fmt && !isPct;

    return (
        <div className="flex flex-col items-center">
            <PlotlyWrapper
                data={[trace]}
                layout={{ margin: { t: 24, r: 16, b: 16, l: 16 } }}
                height={height || 260}
            />
            {showCustomFormat && (
                <div className="text-xs text-slate-400 -mt-4">{formatFn(value)}</div>
            )}
        </div>
    );
}
