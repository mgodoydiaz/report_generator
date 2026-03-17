import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, Cell,
} from 'recharts';
import { CURSO_COLORS, pct, avg } from './constants';

export default function GraficoPromedioAgrupadoPorDimension({ data, cursos, roleLabels = {}, metric = 'logro' }) {
    const isSimce = metric === 'simce';
    const valueKey = isSimce ? '_simce' : '_rend';

    // Collect all evaluation numbers present in data
    const allEvals = [...new Set(data.map(r => r._evaluacion_num).filter(v => v != null))].sort((a, b) => a - b);
    const evalList = allEvals.length ? allEvals : [1];

    // Build one entry per curso; each eval is a separate dataKey
    const chartData = (cursos.length ? cursos : [...new Set(data.map(r => r._curso).filter(Boolean))]).map((curso, ci) => {
        const entry = { curso, color: CURSO_COLORS[ci % CURSO_COLORS.length] };
        evalList.forEach(ev => {
            const subset = data.filter(r => r._curso === curso && r._evaluacion_num === ev);
            entry[`ev_${ev}`] = subset.length ? avg(subset, valueKey) : null;
        });
        return entry;
    });

    const yDomain = isSimce ? [0, 'auto'] : [0, 1];
    const yFormatter = isSimce ? (v => Math.round(v)) : pct;

    const metricLabel = isSimce
        ? (roleLabels.logro_2 || 'Puntaje')
        : (roleLabels.logro_1 || 'Logro');

    return (
        <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="curso" tick={{ fontWeight: 700, fontSize: 13 }} />
                <YAxis tickFormatter={yFormatter} domain={yDomain} tick={{ fontSize: 12 }} />
                <Tooltip
                    formatter={(value, name) => {
                        const evNum = name.replace('ev_', '');
                        return [isSimce ? Math.round(value) : pct(value), `${metricLabel} Ev.${evNum}`];
                    }}
                />
                <Legend
                    formatter={(value) => `Evaluación ${value.replace('ev_', '')}`}
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
                        {chartData.map((entry, ci) => {
                            const baseColor = entry.color;
                            // Vary lightness by evaluation index
                            const opacity = 1 - (ei * 0.22);
                            return (
                                <Cell
                                    key={`${entry.curso}-${ev}`}
                                    fill={baseColor}
                                    fillOpacity={opacity}
                                />
                            );
                        })}
                    </Bar>
                ))}
            </BarChart>
        </ResponsiveContainer>
    );
}
