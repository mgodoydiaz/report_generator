import React from 'react';
import {
    PieChart, Pie, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { LOGRO_COLORS } from './constants';

export default function GraficoDistribucionNiveles({ data }) {
    const conteo = [
        { name: "Adecuado", value: data.filter(r => r._logro === "Adecuado").length, fill: LOGRO_COLORS.Adecuado },
        { name: "Elemental", value: data.filter(r => r._logro === "Elemental").length, fill: LOGRO_COLORS.Elemental },
        { name: "Insuficiente", value: data.filter(r => r._logro === "Insuficiente").length, fill: LOGRO_COLORS.Insuficiente },
    ].filter(d => d.value > 0);

    if (!conteo.length) return null;

    return (
        <ResponsiveContainer width="100%" height={240}>
            <PieChart>
                <Pie data={conteo} dataKey="value" nameKey="name" cx="50%" cy="50%"
                    outerRadius={90} innerRadius={50} paddingAngle={3} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {conteo.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                </Pie>
                <Tooltip />
            </PieChart>
        </ResponsiveContainer>
    );
}
