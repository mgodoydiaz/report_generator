import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer,
} from 'recharts';
import { LOGRO_COLORS } from './constants';

export default function GraficoNivelesPorCurso({ data, cursos }) {
    const resumen = cursos.map((c) => {
        const alumnos = data.filter(r => r._curso === c);
        return {
            curso: c,
            Adecuado: alumnos.filter(r => r._logro === "Adecuado").length,
            Elemental: alumnos.filter(r => r._logro === "Elemental").length,
            Insuficiente: alumnos.filter(r => r._logro === "Insuficiente").length,
        };
    });
    return (
        <ResponsiveContainer width="100%" height={240}>
            <BarChart data={resumen} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="curso" tick={{ fontWeight: 700, fontSize: 13 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 13 }} />
                {["Insuficiente", "Elemental", "Adecuado"].map(n => (
                    <Bar key={n} dataKey={n} stackId="a" fill={LOGRO_COLORS[n]} radius={n === "Adecuado" ? [4, 4, 0, 0] : [0, 0, 0, 0]} />
                ))}
            </BarChart>
        </ResponsiveContainer>
    );
}
