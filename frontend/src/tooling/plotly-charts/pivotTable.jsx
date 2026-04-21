/**
 * pivotTable.jsx — Tabla pivote configurable
 *
 * Componente:
 *   PivotTable — Tabla de cross-tabulation con agregación JS pura
 *
 * pivotConfig = {
 *   rows:   string[]                          campos de fila (ej. ["_curso"])
 *   cols:   string[]                          campos de columna (ej. ["_asignatura"])
 *   values: [{ field, aggregation, label }]   valores a agregar
 * }
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

function buildPivot(records, rows, cols, values) {
    // Unique row combinations and col values
    const rowKeySet = new Map(); // rowKey → { label: [...], key: string }
    const colKeySet = new Map(); // colKey → label: string (only for single col field)
    const cellBuckets = new Map(); // `rowKey\x01colKey\x01valueIdx` → number[]

    for (const r of records) {
        const rk = rowKey(r, rows);
        if (!rowKeySet.has(rk)) {
            rowKeySet.set(rk, rows.map(f => r[f] ?? '—'));
        }
        const ck = cols.length ? rowKey(r, cols) : '__total__';
        if (!colKeySet.has(ck)) {
            colKeySet.set(ck, cols.length ? cols.map(f => r[f] ?? '—').join(' / ') : 'Total');
        }
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

    return { rowEntries, colEntries, cellBuckets };
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

// ── PivotTable ────────────────────────────────────────────────────────────────

export function PivotTable({
    records = [],
    pivotConfig,
    formatStr,
}) {
    const config = pivotConfig || {};
    const rows   = config.rows   || [];
    const cols   = config.cols   || [];
    const values = config.values || [];

    const { rowEntries, colEntries, cellBuckets } = useMemo(
        () => buildPivot(records, rows, cols, values),
        [records, rows, cols, values]
    );

    if (!rows.length || !values.length) {
        return (
            <div className="flex items-center justify-center py-10 text-slate-400 text-sm">
                Configura al menos una fila y un valor.
            </div>
        );
    }

    if (!rowEntries.length) {
        return <p className="text-slate-400 text-sm p-4">Sin datos</p>;
    }

    // Build header: row label columns + (col × value) combinations
    const hasMultipleCols = colEntries.length > 1;
    const hasMultipleValues = values.length > 1;

    return (
        <div className="overflow-x-auto">
            <table className="w-full min-w-max text-left">
                <thead>
                    {/* Top header: col names (if >1 col value and >1 value) */}
                    {hasMultipleCols && hasMultipleValues && (
                        <tr>
                            {/* empty cells for row label columns */}
                            {rows.map((_, ri) => <th key={ri} />)}
                            {colEntries.map(([ck, cLabel]) => (
                                <Th key={ck} className="text-center bg-slate-50 dark:bg-slate-800/50" colSpan={values.length}>
                                    {cLabel}
                                </Th>
                            ))}
                        </tr>
                    )}
                    {/* Main header row */}
                    <tr className="bg-white dark:bg-slate-900">
                        {rows.map((f, ri) => (
                            <Th key={ri}>{f.replace(/^_/, '').replace(/_/g, ' ')}</Th>
                        ))}
                        {colEntries.map(([ck, cLabel]) =>
                            values.map((v, vi) => (
                                <Th key={`${ck}-${vi}`} className="text-right">
                                    {hasMultipleCols && !hasMultipleValues ? cLabel : (hasMultipleValues ? v.label : cLabel + (values.length > 1 ? ` · ${v.label}` : ''))}
                                </Th>
                            ))
                        )}
                    </tr>
                </thead>
                <tbody>
                    {rowEntries.map(([rk, rowLabels], ri) => (
                        <tr key={rk} className={ri % 2 === 0 ? '' : 'bg-slate-50/50 dark:bg-slate-800/20'}>
                            {rowLabels.map((label, li) => (
                                <Td key={li} className="font-medium text-slate-800 dark:text-slate-200">{label}</Td>
                            ))}
                            {colEntries.map(([ck]) =>
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
                            )}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
