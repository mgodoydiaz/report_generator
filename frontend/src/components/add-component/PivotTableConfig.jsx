/**
 * PivotTableConfig.jsx — Configurador visual de tabla pivote
 *
 * UI con 3 zonas: Filas / Columnas / Valores
 * Drag and drop HTML5 nativo.
 * Llama a onConfirm({ rows, cols, values }) al confirmar.
 */

import React, { useState, useMemo } from 'react';
import { X, GripVertical } from 'lucide-react';
import { buildAvailableFields } from './fieldUtils';

// ── Constantes ────────────────────────────────────────────────────────────────

const AGGREGATIONS = [
    { value: 'avg',   label: 'Promedio' },
    { value: 'sum',   label: 'Suma'     },
    { value: 'count', label: 'Conteo'  },
    { value: 'min',   label: 'Mínimo'  },
    { value: 'max',   label: 'Máximo'  },
];

// ── Chip de campo (draggable) ─────────────────────────────────────────────────

function FieldChip({ field, label, kind, onRemove, isInZone = false }) {
    const kindStyle = kind === 'valor'
        ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'
        : 'bg-violet-50 dark:bg-violet-900/20 text-violet-700 dark:text-violet-400 border-violet-200 dark:border-violet-800';
    return (
        <div
            draggable
            onDragStart={(e) => { e.dataTransfer.setData('field', field); e.dataTransfer.setData('label', label); e.dataTransfer.setData('kind', kind); }}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium cursor-grab select-none ${kindStyle}`}
        >
            <GripVertical size={11} className="opacity-50 shrink-0" />
            <span className="truncate max-w-32">{label}</span>
            {isInZone && onRemove && (
                <button onClick={onRemove} className="ml-0.5 hover:opacity-70 transition-opacity shrink-0">
                    <X size={11} />
                </button>
            )}
        </div>
    );
}

// ── Zona de drop ──────────────────────────────────────────────────────────────

function DropZone({ label, description, items, onDrop, onRemove, zone, max, children }) {
    const [dragOver, setDragOver] = useState(false);
    const isDisabled = max && items.length >= max;

    return (
        <div>
            <div className="flex items-center gap-2 mb-2">
                <p className="text-xs font-bold text-slate-700 dark:text-slate-300">{label}</p>
                {max && <span className="text-[10px] text-slate-400">máx. {max}</span>}
            </div>
            {description && <p className="text-[11px] text-slate-400 dark:text-slate-500 mb-2">{description}</p>}
            <div
                onDragOver={(e) => { if (!isDisabled) { e.preventDefault(); setDragOver(true); } }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                    e.preventDefault();
                    setDragOver(false);
                    if (isDisabled) return;
                    const field = e.dataTransfer.getData('field');
                    const label = e.dataTransfer.getData('label');
                    const kind  = e.dataTransfer.getData('kind');
                    if (field) onDrop({ field, label, kind });
                }}
                className={`min-h-[52px] p-2.5 rounded-xl border-2 border-dashed transition-all flex flex-wrap gap-2 items-start ${
                    dragOver
                        ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/10'
                        : isDisabled
                            ? 'border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/30 cursor-not-allowed'
                            : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/30'
                }`}
            >
                {items.length === 0 && (
                    <span className="text-[11px] text-slate-300 dark:text-slate-600 self-center">
                        {isDisabled ? 'Límite alcanzado' : 'Arrastra campos aquí'}
                    </span>
                )}
                {children}
            </div>
        </div>
    );
}

// ── Value slot (con aggregation selector) ─────────────────────────────────────

function ValueSlot({ item, onRemove, onChangeAggregation }) {
    return (
        <div className="flex items-center gap-1.5 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg px-2 py-1.5">
            <GripVertical size={11} className="opacity-40 shrink-0 text-emerald-600 dark:text-emerald-400" />
            <span className="text-xs font-medium text-emerald-700 dark:text-emerald-400 truncate max-w-24">{item.label}</span>
            <select
                value={item.aggregation}
                onChange={(e) => onChangeAggregation(item.field, e.target.value)}
                onClick={(e) => e.stopPropagation()}
                className="text-[11px] bg-transparent border border-emerald-300 dark:border-emerald-700 rounded-md px-1 py-0.5 text-emerald-700 dark:text-emerald-400 focus:outline-none cursor-pointer"
            >
                {AGGREGATIONS.map(a => (
                    <option key={a.value} value={a.value}>{a.label}</option>
                ))}
            </select>
            <button onClick={onRemove} className="text-emerald-500 hover:text-emerald-700 dark:hover:text-emerald-300 transition-colors shrink-0">
                <X size={11} />
            </button>
        </div>
    );
}

// ── PivotTableConfig — componente principal ───────────────────────────────────

export default function PivotTableConfig({ allMetrics, allDimensions, derivedColumns, initial, onConfirm }) {
    const availableFields = useMemo(
        () => buildAvailableFields(allMetrics, allDimensions, derivedColumns),
        [allMetrics, allDimensions, derivedColumns]
    );

    const initConfig = initial || {};
    const [rows,   setRows  ] = useState(initConfig.rows   || []);
    const [cols,   setCols  ] = useState(initConfig.cols   || []);
    const [values, setValues] = useState(initConfig.values || []);

    const addToZone = (setter, existing, item, max) => {
        if (max && existing.length >= max) return;
        if (existing.some(e => e.field === item.field)) return;
        setter([...existing, item]);
    };

    const removeFromZone = (setter, existing, field) => {
        setter(existing.filter(e => e.field !== field));
    };

    const addValue = (item) => {
        if (values.some(v => v.field === item.field)) return;
        setValues([...values, { ...item, aggregation: item.kind === 'valor' ? 'avg' : 'count' }]);
    };

    const changeAgg = (field, aggregation) => {
        setValues(values.map(v => v.field === field ? { ...v, aggregation } : v));
    };

    const isValid = rows.length > 0 && values.length > 0;

    // Campos en uso (para marcarlos en la paleta)
    const inUse = new Set([...rows.map(f => f.field), ...cols.map(f => f.field), ...values.map(v => v.field)]);

    return (
        <div className="space-y-5">
            {/* Paleta de campos disponibles */}
            <div>
                <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">
                    Campos disponibles — arrastra a una zona
                </p>
                {availableFields.length === 0 ? (
                    <div className="rounded-xl border border-amber-200 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-900/10 px-4 py-3">
                        <p className="text-xs text-amber-700 dark:text-amber-400">
                            Configura <strong>column_roles</strong> en el indicador para que aparezcan campos aquí.
                        </p>
                    </div>
                ) : (
                    <div className="flex flex-wrap gap-2 p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-700/50">
                        {availableFields.map(f => (
                            <div key={f.field} className={inUse.has(f.field) ? 'opacity-30' : ''}>
                                <FieldChip field={f.field} label={f.label} kind={f.kind} />
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Zona Filas */}
            <DropZone
                label="Filas"
                description="Cada combinación única de estos campos crea una fila."
                items={rows}
                onDrop={(item) => addToZone(setRows, rows, item)}
                zone="rows"
            >
                {rows.map(f => (
                    <FieldChip
                        key={f.field}
                        field={f.field}
                        label={f.label}
                        kind={f.kind}
                        isInZone
                        onRemove={() => removeFromZone(setRows, rows, f.field)}
                    />
                ))}
            </DropZone>

            {/* Zona Columnas */}
            <DropZone
                label="Columnas"
                description="Pivote horizontal. Cada valor único de este campo crea una columna."
                items={cols}
                onDrop={(item) => addToZone(setCols, cols, item, 1)}
                zone="cols"
                max={1}
            >
                {cols.map(f => (
                    <FieldChip
                        key={f.field}
                        field={f.field}
                        label={f.label}
                        kind={f.kind}
                        isInZone
                        onRemove={() => removeFromZone(setCols, cols, f.field)}
                    />
                ))}
            </DropZone>

            {/* Zona Valores */}
            <DropZone
                label="Valores"
                description="Campos numéricos a agregar. Elige la función de agregación por campo."
                items={values}
                onDrop={addValue}
                zone="values"
            >
                {values.map(v => (
                    <ValueSlot
                        key={v.field}
                        item={v}
                        onRemove={() => removeFromZone(setValues, values, v.field)}
                        onChangeAggregation={changeAgg}
                    />
                ))}
            </DropZone>

            {/* Botón confirmar */}
            <button
                disabled={!isValid}
                onClick={() => onConfirm({ rows: rows.map(f => f.field), cols: cols.map(f => f.field), values })}
                className={`w-full py-2.5 rounded-xl text-sm font-bold transition-all ${
                    isValid
                        ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-600 cursor-not-allowed'
                }`}
            >
                {isValid ? 'Aplicar configuración' : 'Configura filas y valores para continuar'}
            </button>
        </div>
    );
}
