/**
 * pivotTable.jsx — Tabla pivote configurable
 *
 * Componente:
 *   PivotTable — Tabla de cross-tabulation con agregación JS pura
 *
 * pivotConfig = {
 *   rows:   string[]                          campos de fila (ej. ["_curso"])
 *   cols:   string[]                          campos de columna (ej. ["_asignatura"])
 *   value:  string                            campo único (modo valor-crudo)
 *   values: [{ field, aggregation, label }]   valores agregados (modo clásico)
 * }
 *
 * Si se recibe `value` (string), cada celda muestra el valor crudo del único
 * record que coincida con (row, col). Si hay múltiples se toma el modo (más
 * frecuente) y se respeta la prioridad dada por `semaphoreField` si aplica.
 *
 * Semáforo:
 *   semaphoreField — cuando el valor de la celda coincide con un nivel en
 *                    achievement_levels, se colorea con su `color`.
 *   semaphoreMode  — 'cell' (default) o 'row' (peor nivel de la fila).
 */

import React, { useMemo } from 'react';
import { formatValue as fmtVal } from './constants';

const AGG = {
    avg:   (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null,
    sum:   (arr) => arr.length ? arr.reduce((a, b) => a + b, 0)              : null,
    count: (arr) => arr.length,
    min:   (arr) => arr.length ? Math.min(...arr)                            : null,
    max:   (arr) => arr.length ? Math.max(...arr)                            : null,
};

function rowKey(record, fields) {
    return fields.map(f => record[f] ?? '—').join('\x00');
}

function mode(arr) {
    if (!arr.length) return null;
    const counts = new Map();
    for (const v of arr) counts.set(v, (counts.get(v) || 0) + 1);
    let best = null, bestN = -1;
    for (const [k, n] of counts) { if (n > bestN) { best = k; bestN = n; } }
    return best;
}

function buildPivot(records, rows, cols, values, singleValueField) {
    const rowKeySet   = new Map();
    const colKeySet   = new Map();
    const cellBuckets = new Map();      // clásico: arrays numéricos
    const cellRaw     = new Map();      // modo valor-crudo: arrays de strings/values

    for (const r of records) {
        const rk = rowKey(r, rows);
        if (!rowKeySet.has(rk)) rowKeySet.set(rk, rows.map(f => r[f] ?? '—'));

        const ck = cols.length ? rowKey(r, cols) : '__total__';
        if (!colKeySet.has(ck)) {
            colKeySet.set(ck, cols.length ? cols.map(f => r[f] ?? '—').join(' / ') : 'Total');
        }

        // Modo valor-crudo: recolecta todo, después toma el modo.
        if (singleValueField) {
            const bk = `${rk}\x01${ck}`;
            const val = r[singleValueField];
            if (val != null && val !== '') {
                if (!cellRaw.has(bk)) cellRaw.set(bk, []);
                cellRaw.get(bk).push(val);
            }
        }

        // Modo agregado clásico
        values.forEach((v, vi) => {
            const bk = `${rk}\x01${ck}\x01${vi}`;
            const val = r[v.field];
            if (val != null && !isNaN(Number(val))) {
                if (!cellBuckets.has(bk)) cellBuckets.set(bk, []);
                cellBuckets.get(bk).push(Number(val));
            }
        });
    }

    const rowEntries = [...rowKeySet.entries()];
    const colEntries = [...colKeySet.entries()];

    return { rowEntries, colEntries, cellBuckets, cellRaw };
}

function formatCell(val, aggregation, formatStr) {
    if (val == null) return '—';
    if (aggregation === 'count') return String(Math.round(val));
    return fmtVal(val, formatStr || '#.1');
}

// ── Th / Td helpers ───────────────────────────────────────────────────────────

function Th({ children, className = '' }) {
    return (
        <th className={`px-3 py-2 text-[11px] font-bold text-slate-400 uppercase tracking-widest text-left whitespace-nowrap ${className}`}>
            {children}
        </th>
    );
}

function Td({ children, className = '' }) {
    return (
        <td className={`px-3 py-2 text-xs text-slate-700 dark:text-slate-300 border-t border-slate-100 dark:border-slate-800 ${className}`}>
            {children}
        </td>
    );
}

// Construye un mapa nombre→{color, order} desde achievement_levels.
function buildLevelMap(achievementLevels) {
    const map = new Map();
    if (!Array.isArray(achievementLevels)) return map;
    achievementLevels.forEach((al, i) => {
        if (typeof al === 'string') {
            map.set(al, { color: null, order: i + 1 });
        } else if (al && al.name) {
            map.set(al.name, { color: al.color || null, order: al.order ?? (i + 1) });
        }
    });
    return map;
}

// Elige texto legible (blanco/negro) según luminancia del fondo.
function textOn(bg) {
    if (!bg) return null;
    const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(bg.replace('#', ''));
    if (!m) return null;
    const [r, g, b] = [m[1], m[2], m[3]].map(h => parseInt(h, 16));
    const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return lum < 0.6 ? '#ffffff' : '#0f172a';
}

// ── PivotTable ────────────────────────────────────────────────────────────────

export function PivotTable({
    records = [],
    pivotConfig,
    formatStr,
    semaphoreField,          // si está seteado y el valor de la celda está en levelMap → colorea
    semaphoreMode = 'cell',  // 'cell' | 'row' (peor nivel de la fila)
    achievement_levels = [],
}) {
    const config = pivotConfig || {};
    const rows   = config.rows   || [];
    const cols   = config.cols   || [];
    const singleValueField = typeof config.value === 'string' ? config.value : null;
    const values = Array.isArray(config.values) ? config.values : [];

    const { rowEntries, colEntries, cellBuckets, cellRaw } = useMemo(
        () => buildPivot(records, rows, cols, values, singleValueField),
        [records, rows, cols, values, singleValueField]
    );

    const levelMap = useMemo(() => buildLevelMap(achievement_levels), [achievement_levels]);

    const isRawMode = !!singleValueField;

    if (!rows.length || (!isRawMode && !values.length)) {
        return (
            <div className="flex items-center justify-center py-10 text-slate-400 text-sm">
                Configura al menos una fila y un valor.
            </div>
        );
    }

    if (!rowEntries.length) {
        return <p className="text-slate-400 text-sm p-4">Sin datos</p>;
    }

    const hasMultipleCols = colEntries.length > 1;
    const hasMultipleValues = values.length > 1;

    // Pre-cálculo del peor nivel por fila (modo 'row')
    const worstByRow = new Map();
    if (isRawMode && semaphoreField && semaphoreMode === 'row') {
        for (const [rk] of rowEntries) {
            let worst = null;
            for (const [ck] of colEntries) {
                const bucket = cellRaw.get(`${rk}\x01${ck}`) || [];
                for (const v of bucket) {
                    const info = levelMap.get(v);
                    if (info && (worst == null || info.order < worst.order)) {
                        worst = { name: v, ...info };
                    }
                }
            }
            if (worst) worstByRow.set(rk, worst);
        }
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full min-w-max text-left">
                <thead>
                    {hasMultipleCols && hasMultipleValues && (
                        <tr>
                            {rows.map((_, ri) => <th key={ri} />)}
                            {colEntries.map(([ck, cLabel]) => (
                                <Th key={ck} className="text-center bg-slate-50 dark:bg-slate-800/50" colSpan={values.length}>
                                    {cLabel}
                                </Th>
                            ))}
                        </tr>
                    )}
                    <tr className="bg-white dark:bg-slate-900">
                        {rows.map((f, ri) => (
                            <Th key={ri}>{f.replace(/^_/, '').replace(/_/g, ' ')}</Th>
                        ))}
                        {isRawMode
                            ? colEntries.map(([ck, cLabel]) => (
                                <Th key={ck} className="text-center">{cLabel}</Th>
                            ))
                            : colEntries.map(([ck, cLabel]) =>
                                values.map((v, vi) => (
                                    <Th key={`${ck}-${vi}`} className="text-right">
                                        {hasMultipleCols && !hasMultipleValues ? cLabel : (hasMultipleValues ? v.label : cLabel + (values.length > 1 ? ` · ${v.label}` : ''))}
                                    </Th>
                                ))
                            )
                        }
                    </tr>
                </thead>
                <tbody>
                    {rowEntries.map(([rk, rowLabels], ri) => {
                        const worst = worstByRow.get(rk);
                        const rowStyle = (isRawMode && semaphoreMode === 'row' && worst?.color)
                            ? { background: worst.color, color: textOn(worst.color) }
                            : null;
                        return (
                            <tr key={rk} className={rowStyle ? '' : (ri % 2 === 0 ? '' : 'bg-slate-50/50 dark:bg-slate-800/20')} style={rowStyle || undefined}>
                                {rowLabels.map((label, li) => (
                                    <Td key={li} className="font-medium text-slate-800 dark:text-slate-200">{label}</Td>
                                ))}
                                {isRawMode
                                    ? colEntries.map(([ck]) => {
                                        const bucket = cellRaw.get(`${rk}\x01${ck}`) || [];
                                        const cellVal = bucket.length ? mode(bucket) : null;
                                        const info = semaphoreField && semaphoreMode === 'cell' && cellVal != null
                                            ? levelMap.get(cellVal)
                                            : null;
                                        const cellStyle = info?.color
                                            ? { background: info.color, color: textOn(info.color), fontWeight: 600 }
                                            : null;
                                        return (
                                            <Td
                                                key={ck}
                                                className="text-center"
                                                style={cellStyle || undefined}
                                                title={info ? `Nivel: ${cellVal} (orden ${info.order})` : undefined}
                                            >
                                                {cellVal ?? '—'}
                                            </Td>
                                        );
                                    })
                                    : colEntries.map(([ck]) =>
                                        values.map((v, vi) => {
                                            const bk = `${rk}\x01${ck}\x01${vi}`;
                                            const bucket = cellBuckets.get(bk) || [];
                                            const aggFn = AGG[v.aggregation] || AGG.avg;
                                            const result = bucket.length ? aggFn(bucket) : null;
                                            return (
                                                <Td key={`${ck}-${vi}`} className="text-right tabular-nums">
                                                    {formatCell(result, v.aggregation, v.formatStr || formatStr)}
                                                </Td>
                                            );
                                        })
                                    )
                                }
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
