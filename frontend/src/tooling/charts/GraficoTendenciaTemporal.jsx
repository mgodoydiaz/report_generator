import React from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, Dot,
} from 'recharts';
import { CURSO_COLORS, pct, avg } from './constants';

export default function GraficoTendenciaTemporal({ data, cursos, roleLabels = {}, metric = 'logro' }) {
    const isSimce = metric === 'simce';
    const valueKey = isSimce ? '_simce' : '_rend';

    const cursoList = cursos.length ? cursos : [...new Set(data.map(r => r._curso).filter(Boolean))];

    // Collect all evaluation numbers present
    const allEvals = [...new Set(data.map(r => r._evaluacion_num).filter(v => v != null))].sort((a, b) => a - b);
    const evalList = allEvals.length ? allEvals : [1];

    // Build one entry per evaluation number; each curso is a dataKey
    const chartData = evalList.map(ev => {
        const entry = { ev };
        cursoList.forEach(curso => {
            const subset = data.filter(r => r._curso === curso && r._evaluacion_num === ev);
            entry[curso] = subset.length ? avg(subset, valueKey) : null;
        });
        return entry;
    });

    const yDomain = isSimce ? [0, 'auto'] : [0, 1];
    const yFormatter = isSimce ? (v => Math.round(v)) : pct;
    const metricLabel = isSimce ? (roleLabels.logro_2 || 'Puntaje') : (roleLabels.logro_1 || 'Logro');

    return (
        <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ top: 10, right: 24, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                    dataKey="ev"
                    label={{ value: 'Evaluación', position: 'insideBottomRight', offset: -8, fontSize: 11 }}
                    tick={{ fontSize: 12 }}
                />
                <YAxis tickFormatter={yFormatter} domain={yDomain} tick={{ fontSize: 12 }} />
                <Tooltip
                    formatter={(value, name) => [
                        isSimce ? Math.round(value) : pct(value),
                        name,
                    ]}
                    labelFormatter={(label) => `Evaluación ${label}`}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 13 }} />
                {cursoList.map((curso, i) => (
                    <Line
                        key={curso}
                        type="monotone"
                        dataKey={curso}
                        name={curso}
                        stroke={CURSO_COLORS[i % CURSO_COLORS.length]}
                        strokeWidth={2.5}
                        dot={<Dot r={5} />}
                        activeDot={{ r: 7 }}
                        connectNulls
                    />
                ))}
            </LineChart>
        </ResponsiveContainer>
    );
}
