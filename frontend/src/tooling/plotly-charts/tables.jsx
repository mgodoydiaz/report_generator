/**
 * tables.jsx — Tablas de datos (HTML/Tailwind, no Plotly)
 *
 * Componentes:
 *   SummaryTable         — Tabla de resumen con agregaciones por grupo
 *   DetailListTable      — Tabla de detalle de items con badges
 *   DetailListWithProgress — Tabla de detalle con barra de progreso
 */

import React from 'react';
import { avg, formatValue, CATEGORY_COLORS, levelColors } from './constants';

// ── Helpers internos ──────────────────────────────────────────────────────────

function Th({ children }) {
    return (
        <th className="p-3 font-bold text-slate-400 text-[11px] uppercase tracking-widest text-left">
            {children}
        </th>
    );
}

function Td({ children, className = '' }) {
    return <td className={`p-3 ${className}`}>{children}</td>;
}

// ── SummaryTable ──────────────────────────────────────────────────────────────
/**
 * Reemplaza TablaResumenCursos. Props genéricos:
 *
 *   records           Array<Object>
 *   groups            string[]          grupos (filas)
 *   groupField        string            campo de grupo (ej. "_curso")
 *   groupColors       string[]          colores por grupo
 *   valueField        string            campo de valor principal (ej. "_rend")
 *   valueLabel        string            etiqueta del valor
 *   formatValue       (v) => string
 *   valueField2       string?           campo de valor secundario (ej. "_simce")
 *   valueLabel2       string?
 *   formatValue2      (v) => string
 *   categoryField     string?           campo de categorías para conteo (ej. "_logro")
 *   categoryLevels    string[]          niveles ordenados
 *   onGroupClick      (group) => void   callback al hacer click en una fila
 *   activeGroup       string            grupo actualmente activo
 */
export function SummaryTable({
    records = [],
    groups = [],
    groupField = '_curso',
    groupColors = CATEGORY_COLORS,
    valueField = '_rend',
    valueLabel = 'Promedio',
    formatValue: fmt = (v) => String(v),
    valueField2 = null,
    valueLabel2 = null,
    formatValue2 = (v) => String(v),
    categoryField = '_logro',
    categoryLevels = [],
    onGroupClick,
    activeGroup,
}) {
    const groupList = groups.length
        ? groups
        : [...new Set(records.map(r => r[groupField]).filter(Boolean))].sort();

    const levels = categoryLevels.length
        ? categoryLevels
        : [...new Set(records.map(r => r[categoryField]).filter(Boolean))];

    const autoLevelColors = levelColors(levels);

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
                <thead>
                    <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        <Th>Grupo</Th>
                        <Th>Items</Th>
                        <Th>{valueLabel}</Th>
                        {valueField2 && valueLabel2 && <Th>{valueLabel2}</Th>}
                        <Th>Mín</Th>
                        <Th>Máx</Th>
                        {levels.map(l => <Th key={l}>{l}</Th>)}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                    {groupList.map((g, i) => {
                        const rows = records.filter(r => r[groupField] === g);
                        if (!rows.length) return null;
                        const vals = rows.map(r => r[valueField]).filter(v => v != null);
                        const vals2 = valueField2 ? rows.map(r => r[valueField2]).filter(v => v != null) : [];
                        return (
                            <tr
                                key={g}
                                className={`transition-colors ${onGroupClick ? 'cursor-pointer' : ''} ${activeGroup === g ? 'bg-indigo-50/80 dark:bg-indigo-900/20' : 'hover:bg-slate-50/80 dark:hover:bg-slate-800/80'}`}
                                onClick={() => onGroupClick?.(g)}
                            >
                                <Td className="font-extrabold" >
                                    <span style={{ color: groupColors[i % groupColors.length] }}>{g}</span>
                                </Td>
                                <Td className="text-slate-600 dark:text-slate-300">{rows.length}</Td>
                                <Td className="font-bold text-slate-800 dark:text-white">
                                    {vals.length ? fmt(avg(rows, valueField)) : '—'}
                                </Td>
                                {valueField2 && valueLabel2 && (
                                    <Td className="text-slate-600 dark:text-slate-300">
                                        {vals2.length ? formatValue2(avg(rows, valueField2)) : '—'}
                                    </Td>
                                )}
                                <Td className="text-rose-600">
                                    {vals.length ? fmt(Math.min(...vals)) : '—'}
                                </Td>
                                <Td className="text-emerald-600">
                                    {vals.length ? fmt(Math.max(...vals)) : '—'}
                                </Td>
                                {levels.map((level, li) => {
                                    const count = rows.filter(r => r[categoryField] === level).length;
                                    return (
                                        <Td key={level}>
                                            <span className="font-bold" style={{ color: autoLevelColors[li] }}>{count}</span>
                                            <span className="text-slate-400 text-xs ml-1">({rows.length ? Math.round(count / rows.length * 100) : 0}%)</span>
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

// ── DetailListTable ───────────────────────────────────────────────────────────
/**
 * Reemplaza TablaAlumnos. Tabla de items individuales con badge de categoría.
 *
 *   records         Array<Object>
 *   columns         Array<{field, label, format?, className?}>  definición de columnas
 *   labelField      string    campo para la etiqueta de la fila (ej. "_nombre")
 *   valueField      string    campo de valor principal para ordenar (ej. "_rend")
 *   formatValue     (v) => string
 *   badgeField      string?   campo para mostrar como badge (ej. "_logro")
 *   badgeColors     Object?   mapa badge → clase Tailwind
 *   emptyMessage    string
 */
export function DetailListTable({
    records = [],
    columns = [],
    labelField = '_nombre',
    valueField = '_rend',
    formatValue: fmt = (v) => String(v),
    badgeField = '_logro',
    badgeColors = {
        Adecuado: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400',
        Elemental: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400',
        Insuficiente: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-900/20 dark:text-rose-400',
    },
    emptyMessage = 'Sin datos',
}) {
    const sorted = [...records].sort((a, b) => (b[valueField] || 0) - (a[valueField] || 0));
    if (!sorted.length) return <p className="text-slate-400 text-sm p-4">{emptyMessage}</p>;

    // Default columns if not provided
    const cols = columns.length ? columns : [
        { field: labelField, label: 'Nombre' },
        { field: valueField, label: 'Valor', format: fmt },
        ...(badgeField ? [{ field: badgeField, label: 'Nivel', badge: true }] : []),
    ];

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
                <thead>
                    <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        <Th>#</Th>
                        {cols.map(c => <Th key={c.field}>{c.label}</Th>)}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                    {sorted.map((row, i) => (
                        <tr key={i} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/80 transition-colors">
                            <Td className="text-slate-400 font-semibold">{i + 1}</Td>
                            {cols.map(col => {
                                const val = row[col.field];
                                if (col.badge) {
                                    const cls = badgeColors[val] || 'bg-slate-50 text-slate-500 border-slate-200';
                                    return (
                                        <Td key={col.field}>
                                            {val ? (
                                                <span className={`px-2.5 py-0.5 rounded-lg text-[11px] font-bold border ${cls}`}>{val}</span>
                                            ) : '—'}
                                        </Td>
                                    );
                                }
                                const display = col.format ? col.format(val) : (val ?? '—');
                                return <Td key={col.field} className={col.className || 'text-slate-700 dark:text-slate-200'}>{display}</Td>;
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

// ── DetailListWithProgress ────────────────────────────────────────────────────
/**
 * Reemplaza TablaPreguntas. Tabla de items con barra de progreso.
 *
 *   records           Array<Object>
 *   labelField        string    campo para la etiqueta de la fila (ej. "_pregunta")
 *   dimensionField    string    campo de dimensión secundaria a mostrar (ej. "_habilidad")
 *   progressField     string    campo de progreso 0-1 (ej. "_logro_pregunta")
 *   progressLabel     string    etiqueta de la columna de progreso
 *   progressThresholds [number, number]  [umbral_ok, umbral_warn] (ej. [0.6, 0.45])
 *   extraField        string?   campo extra a mostrar (ej. "_correcta")
 *   extraLabel        string?
 *   formatProgress    (v) => string
 *   sortField         string    campo para ordenar desc
 *   emptyMessage      string
 */
export function DetailListWithProgress({
    records = [],
    labelField = '_pregunta',
    dimensionField = '_habilidad',
    progressField = '_logro_pregunta',
    progressLabel = 'Logro',
    progressThresholds = [0.6, 0.45],
    extraField = null,
    extraLabel = null,
    formatProgress = (v) => `${Math.round((v || 0) * 100)}%`,
    sortField = null,
    emptyMessage = 'Sin datos',
}) {
    const sorted = [...records].sort((a, b) => (b[sortField || progressField] || 0) - (a[sortField || progressField] || 0));
    if (!sorted.length) return <p className="text-slate-400 text-sm p-4">{emptyMessage}</p>;

    const [okThreshold, warnThreshold] = progressThresholds;

    const progressColor = (v) => {
        if ((v || 0) >= okThreshold) return '#2a9d8f';
        if ((v || 0) >= warnThreshold) return '#e9c46a';
        return '#e76f51';
    };

    const headers = ['N°', 'Dimensión', progressLabel];
    if (extraField && extraLabel) headers.push(extraLabel);

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
                <thead>
                    <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        {headers.map(h => <Th key={h}>{h}</Th>)}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                    {sorted.map((row, i) => {
                        const progVal = row[progressField] || 0;
                        const dimVal = row[dimensionField];
                        return (
                            <tr key={i} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/80 transition-colors">
                                <Td className="text-slate-400 font-semibold">{row[labelField] || i + 1}</Td>
                                <Td className="font-semibold text-slate-700 dark:text-slate-200">
                                    {dimVal ? dimVal.charAt(0).toUpperCase() + dimVal.slice(1).toLowerCase() : '—'}
                                </Td>
                                <Td>
                                    <div className="flex items-center gap-2">
                                        <div className="flex-1 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                            <div
                                                className="h-full rounded-full transition-all"
                                                style={{
                                                    width: `${progVal * 100}%`,
                                                    background: progressColor(progVal),
                                                }}
                                            />
                                        </div>
                                        <span className="font-bold text-slate-700 dark:text-slate-200 w-10 text-right">
                                            {formatProgress(progVal)}
                                        </span>
                                    </div>
                                </Td>
                                {extraField && extraLabel && (
                                    <Td className="font-bold text-indigo-600 dark:text-indigo-400 uppercase">
                                        {row[extraField] || '—'}
                                    </Td>
                                )}
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
