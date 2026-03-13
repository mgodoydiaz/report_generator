import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer,
} from 'recharts';
import { LOGRO_COLORS } from './constants';

export default function GraficoNivelesPorCurso({ data, cursos, achievement_levels=[] }) {
    const levelsToUse = achievement_levels && achievement_levels.length > 0 
        ? achievement_levels 
        : ["Insuficiente", "Elemental", "Adecuado"];

    const resumen = cursos.map((c) => {
        const alumnos = data.filter(r => r._curso === c);
        const currentRes = { curso: c };
        levelsToUse.forEach(level => {
            currentRes[level] = alumnos.filter(r => r._logro === level).length;
        });
        return currentRes;
    });

    return (
        <ResponsiveContainer width="100%" height={240}>
            <BarChart data={resumen} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="curso" tick={{ fontWeight: 700, fontSize: 13 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 13 }} />
                {levelsToUse.map((level, i) => {
                    const hue = Math.round((i / Math.max(1, levelsToUse.length - 1)) * 120);
                    const fill = achievement_levels && achievement_levels.length > 0 
                                 ? `hsl(${hue}, 70%, 50%)` 
                                 : LOGRO_COLORS[level];

                    // Add top rounded corners only to the topmost section
                    const isTop = (i === levelsToUse.length - 1);
                    return (
                        <Bar 
                            key={level} 
                            dataKey={level} 
                            stackId="a" 
                            fill={fill} 
                            radius={isTop ? [4, 4, 0, 0] : [0, 0, 0, 0]} 
                        />
                    );
                })}
            </BarChart>
        </ResponsiveContainer>
    );
}
