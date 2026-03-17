import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer,
} from 'recharts';
import { avg, formatValue, formatDomain } from './constants';

export default function GraficoHabilidades({ data, roleLabels={}, roleFormats={}, dimension='habilidad' }) {
    if (!data.length) return <p className="text-slate-400 text-sm">Sin datos de habilidades</p>;
    const fmtStr = roleFormats.logro_1;
    const fmt = (v) => formatValue(v, fmtStr);
    const field = dimension === 'habilidad_2' ? '_habilidad_2' : '_habilidad';
    const habilidades = [...new Set(data.map(r => r[field]).filter(Boolean))];
    if (!habilidades.length) return <p className="text-slate-400 text-sm">Sin datos para la dimensión seleccionada</p>;
    const chartData = habilidades.map(h => ({
        habilidad: h.charAt(0).toUpperCase() + h.slice(1).toLowerCase(),
        logro: avg(data.filter(r => r[field] === h), "_logro_pregunta"),
    }));
    return (
        <ResponsiveContainer width="100%" height={Math.max(200, habilidades.length * 40)}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 30, bottom: 0, left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                <XAxis type="number" tickFormatter={fmt} domain={formatDomain(fmtStr)} tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="habilidad" tick={{ fontSize: 12, fontWeight: 600 }} width={80} />
                <Tooltip formatter={(v) => [fmt(v), roleLabels.logro_1 || "Logro"]} />
                <Bar dataKey="logro" fill="#4361ee" radius={[0, 6, 6, 0]}
                    label={{ position: "right", formatter: fmt, fontSize: 12, fontWeight: 700 }} />
            </BarChart>
        </ResponsiveContainer>
    );
}
