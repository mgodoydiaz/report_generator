import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, LabelList, Customized,
} from 'recharts';
import { LOGRO_COLORS } from './constants';


export default function GraficoNivelesPorCursoYMes({ data, cursos, achievement_levels = [] }) {
    const levelsToUse = achievement_levels?.length > 0
        ? achievement_levels
        : ['Insuficiente', 'Elemental', 'Adecuado'];

    // ── Construir datos: una entrada por (curso, evaluacion_num) ─────────────

    const cursoList = cursos?.length
        ? cursos
        : [...new Set(data.map(r => r._curso).filter(Boolean))];

    const pairs = [];
    const cursoStartIndices = {};  // curso → índice de inicio en pairs[]

    cursoList.forEach(curso => {
        const cursoDatos = data.filter(r => r._curso === curso);
        const evals = [...new Set(cursoDatos.map(r => r._evaluacion_num).filter(v => v != null))].sort((a, b) => a - b);
        const evalList = evals.length ? evals : [1];

        cursoStartIndices[curso] = pairs.length;

        evalList.forEach((ev, evIdx) => {
            const alumnos = cursoDatos.filter(r => r._evaluacion_num === ev);
            const entry = {
                _key: `${curso}__${ev}`,   // clave única para XAxis
                _ev: String(ev),
                _curso: curso,
            };
            levelsToUse.forEach(level => {
                entry[level] = alumnos.filter(r => r._logro === level).length;
            });
            pairs.push(entry);
        });
    });

    // ── Metadatos por índice de tick ─────────────────────────────────────────

    const groupTickMeta = {};
    cursoList.forEach(curso => {
        const start = cursoStartIndices[curso];
        const nextCurso = cursoList[cursoList.indexOf(curso) + 1];
        const end = nextCurso != null ? cursoStartIndices[nextCurso] - 1 : pairs.length - 1;
        const centerIdx = Math.round((start + end) / 2);
        for (let i = start; i <= end; i++) {
            groupTickMeta[i] = {
                curso,
                isCenter: i === centerIdx,
                isGroupStart: i === start && start !== 0,  // primer tick del grupo (excepto el primero)
            };
        }
    });

    // ── Color por nivel ──────────────────────────────────────────────────────

    function levelColor(level, i) {
        if (!achievement_levels?.length) return LOGRO_COLORS[level] ?? `hsl(${Math.round(i * 120)}, 65%, 52%)`;
        const hue = Math.round((i / Math.max(1, levelsToUse.length - 1)) * 120);
        return `hsl(${hue}, 65%, 52%)`;
    }

    // ── Tooltip personalizado ────────────────────────────────────────────────

    function CustomTooltip({ active, payload, label }) {
        if (!active || !payload?.length) return null;
        const entry = pairs.find(p => p._key === label);
        return (
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-3 shadow-lg text-sm">
                <p className="font-bold text-slate-700 dark:text-slate-200 mb-1">{entry?._curso} — Ev. {entry?._ev}</p>
                {payload.map(p => (
                    <p key={p.name} style={{ color: p.fill }} className="font-semibold">
                        {p.name}: {p.value}
                    </p>
                ))}
            </div>
        );
    }

    // ── Tick superior (número de evaluación, rotado) ─────────────────────────

    function EvTick({ x, y, payload }) {
        // payload.value es "_key" (ej. "4°A__1"), extraemos solo el número de evaluación
        const ev = payload.value?.split('__')[1] ?? payload.value;
        return (
            <g transform={`translate(${x},${y})`}>
                <text
                    x={0} y={0} dy={12}
                    textAnchor="end"
                    transform="rotate(-35)"
                    fontSize={11}
                    fontWeight={600}
                    fill="#64748b"
                >
                    {ev}
                </text>
            </g>
        );
    }

    // ── Tick inferior (nombre de curso, centrado en el grupo) ────────────────
    // Usamos un segundo XAxis con dataKey numérico para posicionarlo

    function GrupoTick({ x, y, index }) {
        const meta = groupTickMeta[index];
        if (!meta?.isCenter) return null;
        return (
            <text x={x} y={y + 16} textAnchor="middle" fontSize={12} fontWeight={700} fill="#334155">
                {meta.curso}
            </text>
        );
    }

    // ── Separadores SVG entre grupos (via Customized, que tiene acceso al xScale) ──

    function GroupSeparators({ xAxisMap, yAxisMap, offset }) {
        const xAxis = xAxisMap?.['ev'];
        if (!xAxis?.scale) return null;

        const { top, height: plotHeight } = offset;

        return (
            <g>
                {Object.values(cursoStartIndices).slice(1).map((startIdx, i) => {
                    const prevKey = pairs[startIdx - 1]?._key;
                    const currKey = pairs[startIdx]?._key;
                    if (!prevKey || !currKey) return null;

                    const xPrev = xAxis.scale(prevKey);
                    const xCurr = xAxis.scale(currKey);
                    // Midpoint entre las dos barras (en coordenadas del eje)
                    const bw = xAxis.scale.bandwidth?.() ?? 0;
                    const midX = (xPrev + bw + xCurr) / 2;

                    return (
                        <line
                            key={i}
                            x1={midX}
                            y1={top}
                            x2={midX}
                            y2={top + plotHeight}
                            stroke="#1e293b"
                            strokeDasharray="5 3"
                            strokeWidth={2}
                            strokeLinecap="round"
                        />
                    );
                })}
            </g>
        );
    }

    // Altura dinámica: más evaluaciones → más ancho necesario
    const height = Math.max(260, 180 + pairs.length * 12);

    return (
        <ResponsiveContainer width="100%" height={height}>
            <BarChart
                data={pairs}
                margin={{ top: 16, right: 16, bottom: 48, left: 0 }}
                barCategoryGap="20%"
            >
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />

                {/* Eje X superior: número de evaluación (dataKey único = _key) */}
                <XAxis
                    xAxisId="ev"
                    dataKey="_key"
                    tick={<EvTick />}
                    interval={0}
                    height={40}
                    axisLine={false}
                    tickLine={false}
                />

                {/* Eje X inferior: etiqueta de grupo (curso) */}
                <XAxis
                    xAxisId="grupo"
                    dataKey="_key"
                    tick={<GrupoTick />}
                    interval={0}
                    height={32}
                    axisLine={{ stroke: '#e2e8f0' }}
                    tickLine={false}
                    orientation="bottom"
                />

                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} width={32} />

                <Tooltip content={<CustomTooltip />} />

                <Legend
                    iconType="circle"
                    wrapperStyle={{ fontSize: 13, paddingTop: 4 }}
                />

                {/* Líneas separadoras entre grupos de curso */}
                <Customized component={GroupSeparators} />

                {levelsToUse.map((level, i) => {
                    const isTop = i === levelsToUse.length - 1;
                    return (
                        <Bar
                            key={level}
                            xAxisId="ev"
                            dataKey={level}
                            stackId="a"
                            fill={levelColor(level, i)}
                            radius={isTop ? [4, 4, 0, 0] : [0, 0, 0, 0]}
                        >
                            <LabelList
                                dataKey={level}
                                position="center"
                                style={{ fontSize: 10, fontWeight: 700, fill: '#fff' }}
                                formatter={v => (v > 0 ? v : '')}
                            />
                        </Bar>
                    );
                })}
            </BarChart>
        </ResponsiveContainer>
    );
}
