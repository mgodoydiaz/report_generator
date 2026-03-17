import React from 'react';
import {
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
    Legend, Tooltip, ResponsiveContainer,
} from 'recharts';
import { CURSO_COLORS, avg, formatValue, formatDomain } from './constants';

export default function GraficoRadarHabilidades({ data, cursos, roleLabels = {}, roleFormats = {}, dimension = 'habilidad' }) {
    if (!data || !data.length) {
        return <p className="text-slate-400 text-sm">Sin datos de habilidades</p>;
    }

    const field = dimension === 'habilidad_2' ? '_habilidad_2' : '_habilidad';
    const habilidades = [...new Set(data.map(r => r[field]).filter(Boolean))];
    if (!habilidades.length) {
        return <p className="text-slate-400 text-sm">Sin datos para la dimensión seleccionada</p>;
    }

    const cursoList = cursos && cursos.length
        ? cursos
        : [...new Set(data.map(r => r._curso).filter(Boolean))];

    const showByCurso = cursoList.length > 1 && data.some(r => r._curso);

    // Build chart data: one entry per habilidad axis
    const chartData = habilidades.map(h => {
        const entry = {
            habilidad: h.charAt(0).toUpperCase() + h.slice(1).toLowerCase(),
        };
        if (showByCurso) {
            cursoList.forEach(curso => {
                const subset = data.filter(r => r[field] === h && r._curso === curso);
                entry[curso] = subset.length ? avg(subset, '_logro_pregunta') : 0;
            });
        } else {
            const subset = data.filter(r => r[field] === h);
            entry['Logro'] = subset.length ? avg(subset, '_logro_pregunta') : 0;
        }
        return entry;
    });

    const dataKeys = showByCurso ? cursoList : ['Logro'];
    const fmtStr = roleFormats.logro_1;
    const fmt = (v) => formatValue(v, fmtStr);

    return (
        <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={chartData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis
                    dataKey="habilidad"
                    tick={{ fontSize: 12, fontWeight: 600, fill: '#64748b' }}
                />
                <PolarRadiusAxis
                    angle={90}
                    domain={formatDomain(fmtStr)}
                    tickFormatter={fmt}
                    tick={{ fontSize: 10, fill: '#94a3b8' }}
                />
                <Tooltip formatter={(value, name) => [fmt(value), name]} />
                {dataKeys.length > 1 && (
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 13 }} />
                )}
                {dataKeys.map((key, i) => (
                    <Radar
                        key={key}
                        name={key}
                        dataKey={key}
                        stroke={CURSO_COLORS[i % CURSO_COLORS.length]}
                        fill={CURSO_COLORS[i % CURSO_COLORS.length]}
                        fillOpacity={0.3}
                        strokeWidth={2}
                    />
                ))}
            </RadarChart>
        </ResponsiveContainer>
    );
}
