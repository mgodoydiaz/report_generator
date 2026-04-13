import React from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, Dot,
} from 'recharts';
import { CURSO_COLORS, avg, formatValue, formatDomain } from './constants';

export default function GraficoTendenciaTemporal({ data, cursos, roleLabels = {}, roleFormats = {}, metric = 'logro', temporalConfig = null }) {
    const isSimce = metric === 'simce';
    const fmtStr = isSimce ? roleFormats.logro_2 : roleFormats.logro_1;
    const fmt = (v) => formatValue(v, fmtStr);
    const valueKey = isSimce ? '_simce' : '_rend';
    const useTemporalLabel = temporalConfig?.levels?.length > 1;

    const cursoList = cursos.length ? cursos : [...new Set(data.map(r => r._curso).filter(Boolean))];

    // Ordenar por _evaluacion_num; construir etiqueta temporal si hay config con 2+ niveles
    const allEvals = [...new Set(data.map(r => r._evaluacion_num).filter(v => v != null))].sort((a, b) => a - b);
    const evalList = allEvals.length ? allEvals : [1];

    // Mapa evaluacion_num → etiqueta (primera fila con ese num que tenga _temporal_label)
    const evalLabelMap = {};
    if (useTemporalLabel) {
        for (const ev of evalList) {
            const row = data.find(r => r._evaluacion_num === ev && r._temporal_label);
            evalLabelMap[ev] = row?._temporal_label ?? String(ev);
        }
    }

    // Build one entry per evaluation; each curso is a dataKey
    const chartData = evalList.map(ev => {
        const entry = {
            ev,
            label: useTemporalLabel ? (evalLabelMap[ev] ?? String(ev)) : String(ev),
        };
        cursoList.forEach(curso => {
            const subset = data.filter(r => r._curso === curso && r._evaluacion_num === ev);
            entry[curso] = subset.length ? avg(subset, valueKey) : null;
        });
        return entry;
    });

    const yDomain = isSimce ? [0, 'auto'] : formatDomain(fmtStr);
    const yFormatter = fmt;

    return (
        <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ top: 10, right: 24, bottom: useTemporalLabel ? 20 : 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                    dataKey="label"
                    tick={{ fontSize: 11 }}
                    angle={useTemporalLabel ? -25 : 0}
                    textAnchor={useTemporalLabel ? 'end' : 'middle'}
                    height={useTemporalLabel ? 52 : 24}
                    interval={0}
                />
                <YAxis tickFormatter={yFormatter} domain={yDomain} tick={{ fontSize: 12 }} />
                <Tooltip
                    formatter={(value, name) => [fmt(value), name]}
                    labelFormatter={(label) => label}
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
