import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, Cell,
} from 'recharts';
import { CURSO_COLORS, avg, formatValue, formatDomain } from './constants';

export default function GraficoPromedioAgrupadoPorDimension({ data, cursos, roleLabels = {}, roleFormats = {}, metric = 'logro', temporalConfig = null }) {
    const isSimce = metric === 'simce';
    const fmtStr = isSimce ? roleFormats.logro_2 : roleFormats.logro_1;
    const fmt = (v) => formatValue(v, fmtStr);
    const valueKey = isSimce ? '_simce' : '_rend';
    const useTemporalLabel = temporalConfig?.levels?.length > 1;

    // Collect all evaluation numbers present in data, sorted numerically
    const allEvals = [...new Set(data.map(r => r._evaluacion_num).filter(v => v != null))].sort((a, b) => a - b);
    const evalList = allEvals.length ? allEvals : [1];

    // Mapa evaluacion_num → etiqueta temporal (ej. "2024 / AGOSTO")
    const evalLabelMap = {};
    if (useTemporalLabel) {
        for (const ev of evalList) {
            const row = data.find(r => r._evaluacion_num === ev && r._temporal_label);
            evalLabelMap[ev] = row?._temporal_label ?? String(ev);
        }
    }

    const evLabel = (ev) => useTemporalLabel ? (evalLabelMap[ev] ?? String(ev)) : `Ev. ${ev}`;

    // Build one entry per curso; each eval is a separate dataKey
    const chartData = (cursos.length ? cursos : [...new Set(data.map(r => r._curso).filter(Boolean))]).map((curso, ci) => {
        const entry = { curso, color: CURSO_COLORS[ci % CURSO_COLORS.length] };
        evalList.forEach(ev => {
            const subset = data.filter(r => r._curso === curso && r._evaluacion_num === ev);
            entry[`ev_${ev}`] = subset.length ? avg(subset, valueKey) : null;
        });
        return entry;
    });

    const yDomain = isSimce ? [0, 'auto'] : formatDomain(fmtStr);
    const yFormatter = fmt;
    const metricLabel = isSimce ? (roleLabels.logro_2 || 'Puntaje') : (roleLabels.logro_1 || 'Logro');

    return (
        <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="curso" tick={{ fontWeight: 700, fontSize: 13 }} />
                <YAxis tickFormatter={yFormatter} domain={yDomain} tick={{ fontSize: 12 }} />
                <Tooltip
                    formatter={(value, name) => {
                        const ev = name.replace('ev_', '');
                        return [fmt(value), `${metricLabel} — ${evLabel(ev)}`];
                    }}
                />
                <Legend
                    formatter={(value) => evLabel(value.replace('ev_', ''))}
                    iconType="circle"
                    wrapperStyle={{ fontSize: 13 }}
                />
                {evalList.map((ev, ei) => (
                    <Bar
                        key={ev}
                        dataKey={`ev_${ev}`}
                        name={`ev_${ev}`}
                        radius={[4, 4, 0, 0]}
                        label={{ position: 'top', formatter: yFormatter, fontSize: 11, fontWeight: 700 }}
                    >
                        {chartData.map((entry, ci) => (
                            <Cell
                                key={`${entry.curso}-${ev}`}
                                fill={entry.color}
                                fillOpacity={1 - (ei * 0.22)}
                            />
                        ))}
                    </Bar>
                ))}
            </BarChart>
        </ResponsiveContainer>
    );
}
