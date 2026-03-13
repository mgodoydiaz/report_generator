import React from 'react';
import {
    PieChart, Pie, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { LOGRO_COLORS } from './constants';

export default function GraficoDistribucionNiveles({ data, achievement_levels=[] }) {
    const levelsToUse = achievement_levels && achievement_levels.length > 0 
        ? achievement_levels 
        : ["Insuficiente", "Elemental", "Adecuado"];

    const conteo = levelsToUse.map((level, i) => {
        const hue = Math.round((i / Math.max(1, levelsToUse.length - 1)) * 120);
        return {
            name: level,
            value: data.filter(r => r._logro === level).length,
            fill: achievement_levels && achievement_levels.length > 0 ? `hsl(${hue}, 70%, 50%)` : LOGRO_COLORS[level]
        };
    }).filter(d => d.value > 0);

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
