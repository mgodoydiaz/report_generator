import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Cell,
} from 'recharts';
import { CURSO_COLORS } from './constants';

export default function GraficoBoxplotPorCurso({ data, cursos, metric }) {
    const isSimce = metric === "simce";
    const key = isSimce ? "_simce" : "_rend";

    const boxData = cursos.map((c, i) => {
        const vals = data.filter(r => r._curso === c).map(r => r[key]).filter(v => v != null).sort((a, b) => a - b);
        if (!vals.length) return { curso: c, min: 0, q1: 0, median: 0, q3: 0, max: 0, base: 0, boxLower: 0, boxUpper: 0, color: CURSO_COLORS[i % CURSO_COLORS.length] };
        const q = (arr, p) => { const idx = (arr.length - 1) * p; const lo = Math.floor(idx); const hi = Math.ceil(idx); return arr[lo] + (arr[hi] - arr[lo]) * (idx - lo); };
        const q1 = q(vals, 0.25);
        const q3 = q(vals, 0.75);
        const median = q(vals, 0.5);
        const iqr = q3 - q1;
        const lowerFence = Math.max(vals[0], q1 - 1.5 * iqr);
        const upperFence = Math.min(vals[vals.length - 1], q3 + 1.5 * iqr);
        return {
            curso: c, min: lowerFence, q1, median, q3, max: upperFence,
            base: q1, boxLower: median - q1, boxUpper: q3 - median,
            color: CURSO_COLORS[i % CURSO_COLORS.length],
        };
    });

    const fmt = isSimce ? (v => Math.round(v)) : (v => `${Math.round(v * 100)}%`);

    const TopBarWithWhiskers = (props) => {
        const { x, y, width, height, payload } = props;
        if (!payload || !width || !height) return null;

        const { min, q1, median, q3, max, color } = payload;
        const dataRange = q3 - median;

        if (!dataRange || height <= 0) {
            return <rect x={x} y={y} width={width} height={Math.max(height, 2)} fill={color} opacity={0.85} rx={3} />;
        }

        const pxPerUnit = height / dataRange;
        const xCenter = x + width / 2;
        const capW = width * 0.5;
        const yMaxPx = y - (max - q3) * pxPerUnit;
        const yQ1Px = (y + height) + (median - q1) * pxPerUnit;
        const yMinPx = (y + height) + (median - min) * pxPerUnit;

        return (
            <g>
                <rect x={x} y={y} width={width} height={height} fill={color} opacity={0.85} rx={3} />
                <line x1={xCenter} x2={xCenter} y1={y} y2={yMaxPx} stroke={color} strokeWidth={2} />
                <line x1={xCenter - capW / 2} x2={xCenter + capW / 2} y1={yMaxPx} y2={yMaxPx} stroke={color} strokeWidth={2.5} />
                <line x1={xCenter} x2={xCenter} y1={yQ1Px} y2={yMinPx} stroke={color} strokeWidth={2} />
                <line x1={xCenter - capW / 2} x2={xCenter + capW / 2} y1={yMinPx} y2={yMinPx} stroke={color} strokeWidth={2.5} />
                <line x1={x + 2} x2={x + width - 2} y1={y + height} y2={y + height} stroke="white" strokeWidth={2.5} />
            </g>
        );
    };

    return (
        <ResponsiveContainer width="100%" height={260}>
            <BarChart data={boxData} margin={{ top: 20, right: 16, bottom: 0, left: 0 }} barCategoryGap="30%">
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="curso" tick={{ fontWeight: 700, fontSize: 13 }} />
                <YAxis tickFormatter={fmt} allowDataOverflow={true} domain={(() => {
                    if (!isSimce) return [0, 1];
                    const valid = boxData.filter(d => d.max > 0);
                    if (!valid.length) return [0, 350];
                    const allMin = Math.min(...valid.map(d => d.min));
                    const allMax = Math.max(...valid.map(d => d.max));
                    const pad = (allMax - allMin) * 0.1 || 10;
                    return [Math.floor((allMin - pad) / 10) * 10, Math.ceil((allMax + pad) / 10) * 10];
                })()} tick={{ fontSize: 12 }} />
                <Tooltip
                    content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const d = payload[0].payload;
                        return (
                            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-3 shadow-lg text-xs">
                                <div className="font-bold text-slate-700 dark:text-white mb-1">{d.curso}</div>
                                <div className="text-slate-500">Máx: {fmt(d.max)}</div>
                                <div className="text-slate-500">Q3: {fmt(d.q3)}</div>
                                <div className="text-slate-500 font-bold">Mediana: {fmt(d.median)}</div>
                                <div className="text-slate-500">Q1: {fmt(d.q1)}</div>
                                <div className="text-slate-500">Mín: {fmt(d.min)}</div>
                            </div>
                        );
                    }}
                />
                <Bar dataKey="base" stackId="box" fill="transparent" />
                <Bar dataKey="boxLower" stackId="box">
                    {boxData.map((entry, i) => (
                        <Cell key={`q1-${i}`} fill={entry.color} opacity={0.5} />
                    ))}
                </Bar>
                <Bar dataKey="boxUpper" stackId="box" shape={TopBarWithWhiskers} />
            </BarChart>
        </ResponsiveContainer>
    );
}
