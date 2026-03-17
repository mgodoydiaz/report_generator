import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Cell,
} from 'recharts';
import { CURSO_COLORS, avg, formatValue, formatDomain } from './constants';

export default function GraficoLogroPorCurso({ data, cursos, metric, roleLabels={}, roleFormats={} }) {
    const isSimce = metric === "simce";
    const fmtStr = isSimce ? roleFormats.logro_2 : roleFormats.logro_1;
    const fmt = (v) => formatValue(v, fmtStr);
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
        : formatDomain(fmtStr);

    return (
        <ResponsiveContainer width="100%" height={240}>
            <BarChart data={resumen} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="curso" tick={{ fontWeight: 700, fontSize: 13 }} />
                <YAxis
                    tickFormatter={fmt}
                    domain={yDomain}
                    tick={{ fontSize: 12 }}
                />
                <Tooltip formatter={(v) => [fmt(v), isSimce ? (roleLabels.logro_2 || "Val. secundario") : (roleLabels.logro_1 || "Logro")]} />
                <Bar dataKey="valor" radius={[6, 6, 0, 0]}
                    label={{ position: "top", formatter: fmt, fontSize: 12, fontWeight: 700 }}>
                    {resumen.map((entry) => (
                        <Cell key={entry.curso} fill={entry.color} />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
}
