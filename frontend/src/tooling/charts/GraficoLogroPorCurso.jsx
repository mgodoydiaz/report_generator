import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Cell,
} from 'recharts';
import { CURSO_COLORS, pct, avg } from './constants';

export default function GraficoLogroPorCurso({ data, cursos, metric, roleLabels={} }) {
    const isSimce = metric === "simce";
    const resumen = cursos.map((c, i) => ({
        curso: c,
        valor: isSimce
            ? avg(data.filter(r => r._curso === c), "_simce")
            : avg(data.filter(r => r._curso === c), "_rend"),
        color: CURSO_COLORS[i % CURSO_COLORS.length],
    }));

    const vals = resumen.map(r => r.valor).filter(v => v != null && !isNaN(v));
    const yDomain = isSimce
        ? [0, vals.length ? Math.ceil(Math.max(...vals) * 1.1 / 10) * 10 : 350]
        : [0, 1];

    return (
        <ResponsiveContainer width="100%" height={240}>
            <BarChart data={resumen} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="curso" tick={{ fontWeight: 700, fontSize: 13 }} />
                <YAxis
                    tickFormatter={isSimce ? (v => Math.round(v)) : (v => `${Math.round(v * 100)}%`)}
                    domain={yDomain}
                    tick={{ fontSize: 12 }}
                />
                <Tooltip formatter={(v) => [isSimce ? Math.round(v) : pct(v), isSimce ? (roleLabels.logro_2 || "Val. secundario") : (roleLabels.logro_1 || "Logro")]} />
                <Bar dataKey="valor" radius={[6, 6, 0, 0]}
                    label={{ position: "top", formatter: isSimce ? (v => Math.round(v)) : pct, fontSize: 12, fontWeight: 700 }}>
                    {resumen.map((entry) => (
                        <Cell key={entry.curso} fill={entry.color} />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
}
