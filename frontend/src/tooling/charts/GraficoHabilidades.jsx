import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer,
} from 'recharts';
import { pct, avg } from './constants';

export default function GraficoHabilidades({ data }) {
    if (!data.length) return <p className="text-slate-400 text-sm">Sin datos de habilidades</p>;
    const habilidades = [...new Set(data.map(r => r._habilidad).filter(Boolean))];
    const chartData = habilidades.map(h => ({
        habilidad: h.charAt(0).toUpperCase() + h.slice(1).toLowerCase(),
        logro: avg(data.filter(r => r._habilidad === h), "_logro_pregunta"),
    }));
    return (
        <ResponsiveContainer width="100%" height={Math.max(200, habilidades.length * 40)}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 30, bottom: 0, left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                <XAxis type="number" tickFormatter={v => `${Math.round(v * 100)}%`} domain={[0, 1]} tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="habilidad" tick={{ fontSize: 12, fontWeight: 600 }} width={80} />
                <Tooltip formatter={(v) => pct(v)} />
                <Bar dataKey="logro" fill="#4361ee" radius={[0, 6, 6, 0]}
                    label={{ position: "right", formatter: pct, fontSize: 12, fontWeight: 700 }} />
            </BarChart>
        </ResponsiveContainer>
    );
}
