/**
 * pivotTable.jsx — Tabla pivote
 *
 * Dos componentes:
 *
 *   PivotResultTable — render puro de un `PivotResult` calculado por el
 *     backend (motor W2, `backend/rgenerator/core/pivot_engine.py`). Es el
 *     componente que usa `TableRenderer` cuando `GET /api/tables/{id}/data`
 *     responde `{mode: "pivot", pivot: <PivotResult>}`. Sin agregación en
 *     JS — solo pinta `columns`/`rows` tal como llegan.
 *
 *     PivotResult = {
 *       row_fields: string[], col_fields: string[],
 *       columns: [{ keys, field, agg, label, is_total }],
 *       rows:    [{ keys, cells: [{ value, display }], is_total }],
 *       meta: {...},
 *     }
 *     `cells[i]` está alineada posicionalmente con `columns[i]`.
 *
 *   PivotTable — componente LEGACY que se mantiene sin cambios para el modo
 *     "raw"/categórico (un único campo `pivotConfig.value` + `semaphoreField`,
 *     ej. el Roster IDEL armado por `scripts/apply_pdl_layout_v2.py`). Este
 *     modo pinta el valor categórico más frecuente por celda y lo colorea
 *     según `achievement_levels` — el motor W2 no lo puede representar
 *     (solo produce agregaciones numéricas, `PivotCell.value: float | null`),
 *     igual que el `pivot_matrix` chart_type del backend (ver
 *     docs/planes/w2_motor_pivotes.md, sección "Migración del pivote
 *     existente"). El modo agregado clásico (`pivotConfig.values` con
 *     aggregation por campo, calculado en JS) SE RETIRÓ de este componente:
 *     era la implementación fragmentada que el motor W2 unifica. Si un item
 *     de dashboard legacy todavía declara ese modo, se muestra un aviso
 *     dirigiendo a crear una Tabla Pivote nueva (página Tablas).
 */

import React, { useMemo } from 'react';

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

// ─────────────────────────────────────────────────────────────────────────
// PivotResultTable — render puro del PivotResult del backend (motor W2)
// ─────────────────────────────────────────────────────────────────────────

/**
 * Fila de agrupación (nivel de columna) — una celda por combinación
 * consecutiva de `col.keys` (join con " · " para col_fields multinivel),
 * con `colSpan` = cantidad de columnas de métrica que comparten ese nivel.
 * Solo tiene sentido cuando `col_fields.length >= 1`. Las columnas Total
 * (`is_total`, `keys=[total_label]`) forman su propio grupo — no participan
 * del multinivel de `col_fields` (el motor las emite con un único key).
 */
function buildLevelGroups(columns) {
    const groups = [];
    let i = 0;
    while (i < columns.length) {
        const col = columns[i];
        const levelKey = col.keys.join('\x00');
        let span = 1;
        while (
            i + span < columns.length &&
            columns[i + span].keys.join('\x00') === levelKey &&
            columns[i + span].is_total === col.is_total
        ) {
            span++;
        }
        groups.push({
            key: `${i}`,
            label: col.keys.length ? col.keys.join(' · ') : col.label,
            span,
            isTotal: col.is_total,
        });
        i += span;
    }
    return groups;
}

export function PivotResultTable({ pivotResult, className = '' }) {
    const result = pivotResult || {};
    const rowFields = result.row_fields || [];
    const colFields = result.col_fields || [];
    const columns = result.columns || [];
    const rows = result.rows || [];

    const hasColFields = colFields.length > 0;

    const levelGroups = useMemo(
        () => (hasColFields ? buildLevelGroups(columns) : []),
        [columns, hasColFields]
    );

    if (!rowFields.length && !columns.length) {
        return (
            <div className="flex items-center justify-center py-10 text-slate-400 text-sm">
                Configura al menos una fila y un valor en el pivote.
            </div>
        );
    }

    if (!rows.length) {
        return <p className="text-slate-400 dark:text-slate-500 text-sm p-4">Sin datos</p>;
    }

    // Fila de nivel (Marzo / Abril / … · Total) — solo si hay col_fields;
    // agrupa columnas que comparten el mismo valor de columna con colSpan.
    // Fila de métrica (Logro prom. / Asistencia …) — siempre presente: es la
    // única fila de encabezado cuando no hay col_fields, y desambigua la
    // métrica de cada columna cuando sí los hay (multi-value o no).
    const showLevelRow = hasColFields;

    return (
        <div className={`overflow-x-auto ${className}`}>
            <table className="w-full min-w-max text-left">
                <thead>
                    {showLevelRow && (
                        <tr>
                            {rowFields.map((_, ri) => <th key={ri} />)}
                            {!rowFields.length && <th />}
                            {levelGroups.map((g) => (
                                <Th
                                    key={g.key}
                                    className={`text-center ${g.isTotal ? 'bg-slate-100 dark:bg-slate-800/70 text-slate-600 dark:text-slate-300' : 'bg-slate-50 dark:bg-slate-800/50'}`}
                                    colSpan={g.span}
                                >
                                    {g.label}
                                </Th>
                            ))}
                        </tr>
                    )}
                    <tr className="bg-white dark:bg-slate-900">
                        {rowFields.map((f, ri) => (
                            <Th key={ri}>{f.replace(/^_/, '').replace(/_/g, ' ')}</Th>
                        ))}
                        {!rowFields.length && <Th></Th>}
                        {columns.map((col, ci) => (
                            <Th
                                key={ci}
                                className={`text-right ${col.is_total ? 'bg-slate-100 dark:bg-slate-800/70 text-slate-600 dark:text-slate-300' : ''}`}
                            >
                                {col.label}
                            </Th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row, ri) => {
                        const rowCls = row.is_total
                            ? 'bg-slate-50 dark:bg-slate-800/40 font-bold'
                            : (ri % 2 === 0 ? '' : 'bg-slate-50/50 dark:bg-slate-800/20');
                        return (
                            <tr key={ri} className={rowCls}>
                                {row.keys.map((label, li) => (
                                    <Td
                                        key={li}
                                        className={row.is_total ? 'font-bold text-slate-800 dark:text-slate-100' : 'font-medium text-slate-800 dark:text-slate-200'}
                                    >
                                        {label}
                                    </Td>
                                ))}
                                {!row.keys.length && <Td>—</Td>}
                                {row.cells.map((cell, ci) => {
                                    const col = columns[ci];
                                    const isTotalCol = col?.is_total;
                                    const empty = cell.display === '' && cell.value == null;
                                    return (
                                        <Td
                                            key={ci}
                                            className={`text-right tabular-nums ${row.is_total || isTotalCol ? 'font-bold' : ''} ${empty ? 'text-slate-300 dark:text-slate-600' : ''}`}
                                        >
                                            {empty ? '—' : cell.display}
                                        </Td>
                                    );
                                })}
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────
// PivotTable — LEGACY, modo raw/categórico (Roster IDEL). No migrado: el
// motor W2 solo produce agregaciones numéricas (ver docstring del archivo).
// ─────────────────────────────────────────────────────────────────────────

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

function buildRawPivot(records, rows, cols, singleValueField) {
    const rowKeySet = new Map();
    const colKeySet = new Map();
    const cellRaw = new Map();

    for (const r of records) {
        const rk = rowKey(r, rows);
        if (!rowKeySet.has(rk)) rowKeySet.set(rk, rows.map(f => r[f] ?? '—'));

        const ck = cols.length ? rowKey(r, cols) : '__total__';
        if (!colKeySet.has(ck)) {
            colKeySet.set(ck, cols.length ? cols.map(f => r[f] ?? '—').join(' / ') : 'Total');
        }

        const bk = `${rk}\x01${ck}`;
        const val = r[singleValueField];
        if (val != null && val !== '') {
            if (!cellRaw.has(bk)) cellRaw.set(bk, []);
            cellRaw.get(bk).push(val);
        }
    }

    return { rowEntries: [...rowKeySet.entries()], colEntries: [...colKeySet.entries()], cellRaw };
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

export function PivotTable({
    records = [],
    pivotConfig,
    formatStr,
    semaphoreField,          // si está seteado y el valor de la celda está en levelMap → colorea
    semaphoreMode = 'cell',  // 'cell' | 'row' (peor nivel de la fila)
    achievement_levels = [],
}) {
    const config = pivotConfig || {};
    const rows = config.rows || [];
    const cols = config.cols || [];
    const singleValueField = typeof config.value === 'string' ? config.value : null;
    const legacyAggregatedValues = Array.isArray(config.values) ? config.values : [];

    const { rowEntries, colEntries, cellRaw } = useMemo(
        () => (singleValueField ? buildRawPivot(records, rows, cols, singleValueField) : { rowEntries: [], colEntries: [], cellRaw: new Map() }),
        [records, rows, cols, singleValueField]
    );

    const levelMap = useMemo(() => buildLevelMap(achievement_levels), [achievement_levels]);

    // Modo agregado clásico (values[] + aggregation en JS) — RETIRADO. Este
    // componente ya no calcula agregaciones en el cliente; use una Tabla
    // Pivote (página Tablas → PivotSpec) que el backend calcula con el
    // motor W2 y renderiza `PivotResultTable`.
    if (!singleValueField && legacyAggregatedValues.length > 0) {
        return (
            <div className="flex flex-col items-center justify-center gap-1 py-10 text-slate-400 text-sm text-center px-4">
                <span>Este modo de Tabla Pivote (agregación por campo) se migró al nuevo motor de pivotes.</span>
                <span>Crea una <strong>Tabla Pivote</strong> nueva desde la página <strong>Tablas</strong> con el mismo resultado (y export a Excel).</span>
            </div>
        );
    }

    if (!rows.length || !singleValueField) {
        return (
            <div className="flex items-center justify-center py-10 text-slate-400 text-sm">
                Configura al menos una fila y un valor.
            </div>
        );
    }

    if (!rowEntries.length) {
        return <p className="text-slate-400 text-sm p-4">Sin datos</p>;
    }

    // Pre-cálculo del peor nivel por fila (modo 'row')
    const worstByRow = new Map();
    if (semaphoreField && semaphoreMode === 'row') {
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
                    <tr className="bg-white dark:bg-slate-900">
                        {rows.map((f, ri) => (
                            <Th key={ri}>{f.replace(/^_/, '').replace(/_/g, ' ')}</Th>
                        ))}
                        {colEntries.map(([ck, cLabel]) => (
                            <Th key={ck} className="text-center">{cLabel}</Th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {rowEntries.map(([rk, rowLabels], ri) => {
                        const worst = worstByRow.get(rk);
                        const rowStyle = (semaphoreMode === 'row' && worst?.color)
                            ? { background: worst.color, color: textOn(worst.color) }
                            : null;
                        return (
                            <tr key={rk} className={rowStyle ? '' : (ri % 2 === 0 ? '' : 'bg-slate-50/50 dark:bg-slate-800/20')} style={rowStyle || undefined}>
                                {rowLabels.map((label, li) => (
                                    <Td key={li} className="font-medium text-slate-800 dark:text-slate-200">{label}</Td>
                                ))}
                                {colEntries.map(([ck]) => {
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
                                })}
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
