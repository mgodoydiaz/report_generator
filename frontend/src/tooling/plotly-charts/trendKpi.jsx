/**
 * trendKpi.jsx — KPI card con delta y sparkline opcional
 *
 * Componente:
 *   TrendKPI — Tarjeta de métrica única con variación respecto a periodo anterior.
 */

import React, { useMemo } from 'react';

// ── Cómputo del valor ─────────────────────────────────────────────────────────

function computeValue(records, aggregation, valueField, groupField, scoreField) {
    if (!records || records.length === 0) return null;

    switch (aggregation) {
        case 'unique_count': {
            const vals = new Set(records.map(r => r[valueField]).filter(v => v != null));
            return vals.size;
        }
        case 'count':
            return records.length;
        case 'mean_percent': {
            const vals = records.map(r => r[valueField]).filter(v => v != null);
            if (!vals.length) return null;
            const trueCount = vals.filter(v => v === true || v === 1 || v === '1').length;
            return trueCount / vals.length;
        }
        case 'top_group': {
            const gf = groupField || '_curso';
            const sf = scoreField || valueField;
            const byGroup = {};
            for (const r of records) {
                const g = r[gf];
                const v = r[sf];
                if (g == null) continue;
                if (!byGroup[g]) byGroup[g] = { sum: 0, count: 0 };
                if (v === true || v === 1 || v === '1') byGroup[g].sum += 1;
                byGroup[g].count += 1;
            }
            let bestGroup = null, bestScore = -1;
            for (const [g, { sum, count }] of Object.entries(byGroup)) {
                const score = count > 0 ? sum / count : 0;
                if (score > bestScore) { bestScore = score; bestGroup = g; }
            }
            return bestGroup != null ? { group: bestGroup, score: bestScore } : null;
        }
        case 'avg':
        case 'mean': {
            const vals = records.map(r => r[valueField]).filter(v => v != null && !isNaN(Number(v)));
            if (!vals.length) return null;
            return vals.reduce((s, v) => s + Number(v), 0) / vals.length;
        }
        default:
            return null;
    }
}

function formatValue(value, aggregation) {
    if (value == null) return '—';
    if (typeof value === 'object' && value.group != null) return value.group;
    if (aggregation === 'mean_percent') return `${Math.round(value * 100)}%`;
    if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(1);
    return String(value);
}

// ── Sparkline SVG ─────────────────────────────────────────────────────────────

function Sparkline({ data, invertColors, width = 80, height = 20 }) {
    if (!data || data.length < 2) return null;
    const nums = data.map(Number).filter(v => !isNaN(v));
    if (nums.length < 2) return null;

    const min = Math.min(...nums);
    const max = Math.max(...nums);
    const range = max - min || 1;

    const points = nums.map((v, i) => {
        const x = (i / (nums.length - 1)) * width;
        const y = height - ((v - min) / range) * (height - 2) - 1;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');

    const trend = nums[nums.length - 1] > nums[0];
    const color = invertColors
        ? (trend ? '#dc2626' : '#16a34a')
        : (trend ? '#16a34a' : '#dc2626');

    return (
        <svg width={width} height={height} className="opacity-60 shrink-0">
            <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );
}

// ── Badge de delta ────────────────────────────────────────────────────────────

function DeltaBadge({ current, previous, invertColors, aggregation }) {
    if (current == null || previous == null) return null;
    if (typeof current === 'object' || typeof previous === 'object') return null;

    const scale = aggregation === 'mean_percent' ? 100 : 1;
    const delta = (current - previous) * scale;
    if (!isFinite(delta)) return null;

    const isImprovement = invertColors ? delta < 0 : delta > 0;
    const color = delta === 0
        ? 'text-slate-400'
        : isImprovement ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400';
    const prefix = delta > 0 ? '+' : '';
    const suffix = aggregation === 'mean_percent' ? ' pp' : '';

    return (
        <span className={`text-xs font-semibold tabular-nums ${color}`}>
            {prefix}{Math.round(delta)}{suffix}
        </span>
    );
}

// ── Componente principal ──────────────────────────────────────────────────────

/**
 * Props:
 *   records          Array<Object>   registros filtrados (ya con applyItemFilter)
 *   label            string
 *   valueField       string          campo a agregar
 *   aggregation      'unique_count'|'count'|'mean_percent'|'top_group'|'avg'
 *   groupField       string          para aggregation='top_group'
 *   scoreField       string          para aggregation='top_group' (qué campo medir)
 *   invertColors     bool            true si menor es mejor (ej. % en riesgo)
 *   sparklineData    number[]        serie temporal para sparkline mini
 *   previousRecords  Array<Object>   registros del periodo anterior (para Δ)
 *   previousValue    number          valor previo literal (alternativo a previousRecords)
 */
export function TrendKPI({
    records = [],
    label = '',
    valueField,
    aggregation = 'mean_percent',
    groupField,
    scoreField,
    invertColors = false,
    sparklineData,
    previousRecords,
    previousValue,
}) {
    const value = useMemo(
        () => computeValue(records, aggregation, valueField, groupField, scoreField),
        [records, aggregation, valueField, groupField, scoreField]
    );

    const prevValue = useMemo(() => {
        if (previousValue != null) return previousValue;
        if (!previousRecords) return null;
        return computeValue(previousRecords, aggregation, valueField, groupField, scoreField);
    }, [previousRecords, previousValue, aggregation, valueField, groupField, scoreField]);

    const display = formatValue(value, aggregation);
    const subValue = typeof value === 'object' && value?.score != null
        ? `${Math.round(value.score * 100)}% con riesgo`
        : null;

    return (
        <div className="flex flex-col gap-1 p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 h-full min-h-[100px]">
            <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400 truncate">{label}</span>
            <div className="flex items-end gap-2 flex-1">
                <span className="text-3xl font-black text-slate-800 dark:text-white leading-none">{display}</span>
                {sparklineData && <Sparkline data={sparklineData} invertColors={invertColors} />}
            </div>
            {subValue && <span className="text-xs text-slate-500 dark:text-slate-400">{subValue}</span>}
            {prevValue != null && (
                <DeltaBadge
                    current={typeof value === 'object' ? value?.score : value}
                    previous={typeof prevValue === 'object' ? prevValue?.score : prevValue}
                    invertColors={invertColors}
                    aggregation={aggregation}
                />
            )}
        </div>
    );
}
