/**
 * PivotTableConfig.jsx — Configurador visual de un PivotSpec (motor W2)
 *
 * UI con 3 zonas: Filas / Columnas / Valores, drag and drop HTML5 nativo,
 * más toggles de totales. Construye el `PivotSpec` que consume el motor de
 * pivotes del backend (`backend/schemas_pivot.py` / `pivot_engine.py`):
 *
 *   { rows: string[], cols: string[],
 *     values: [{ field, agg, label, format }],
 *     totals: { rows: bool, cols: bool } }
 *
 * `onConfirm(spec)` se llama al aplicar — el caller lo guarda donde
 * corresponda (ej. `TableConfig.pivot` en la página Tablas).
 *
 * `fields`: Array<{ field, label, kind }> — catálogo de campos disponibles
 * (dimensiones + valores numéricos). `kind` solo se usa para el estilo del
 * chip ('valor' = verde, cualquier otro = violeta).
 */

import React, { useState } from 'react';
import { X, GripVertical } from 'lucide-react';

// ── Constantes ────────────────────────────────────────────────────────────────
// Debe reflejar `PivotAgg` en backend/schemas_pivot.py.

export const PIVOT_AGGREGATIONS = [
    { value: 'mean',      label: 'Promedio' },
    { value: 'sum',       label: 'Suma' },
    { value: 'count',     label: 'Conteo' },
    { value: 'nunique',   label: 'Conteo único' },
    { value: 'min',       label: 'Mínimo' },
    { value: 'max',       label: 'Máximo' },
    { value: 'median',    label: 'Mediana' },
    { value: 'std',       label: 'Desv. estándar' },
    { value: 'pct_row',   label: '% sobre fila' },
    { value: 'pct_col',   label: '% sobre columna' },
    { value: 'pct_total', label: '% sobre total' },
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

function DropZone({ label, description, items, onDrop, max, children }) {
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

// ── Value slot (agg + label + format) ──────────────────────────────────────────

function ValueSlot({ item, onRemove, onChange }) {
    return (
        <div className="flex flex-col gap-1.5 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg px-2.5 py-2 w-full sm:w-auto">
            <div className="flex items-center gap-1.5">
                <GripVertical size={11} className="opacity-40 shrink-0 text-emerald-600 dark:text-emerald-400" />
                <span className="text-xs font-medium text-emerald-700 dark:text-emerald-400 truncate max-w-24">{item.field}</span>
                <select
                    value={item.agg}
                    onChange={(e) => onChange({ agg: e.target.value })}
                    onClick={(e) => e.stopPropagation()}
                    className="text-[11px] bg-transparent border border-emerald-300 dark:border-emerald-700 rounded-md px-1 py-0.5 text-emerald-700 dark:text-emerald-400 focus:outline-none cursor-pointer"
                >
                    {PIVOT_AGGREGATIONS.map(a => (
                        <option key={a.value} value={a.value}>{a.label}</option>
                    ))}
                </select>
                <button onClick={onRemove} className="text-emerald-500 hover:text-emerald-700 dark:hover:text-emerald-300 transition-colors shrink-0 ml-auto">
                    <X size={11} />
                </button>
            </div>
            <div className="flex items-center gap-1.5">
                <input
                    type="text"
                    value={item.label ?? ''}
                    onChange={(e) => onChange({ label: e.target.value })}
                    placeholder="Etiqueta (opcional)"
                    className="flex-1 min-w-0 text-[11px] px-1.5 py-0.5 rounded border border-emerald-200 dark:border-emerald-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200"
                />
                <input
                    type="text"
                    value={item.format ?? ''}
                    onChange={(e) => onChange({ format: e.target.value })}
                    placeholder="Formato (.1%, .2f)"
                    title="Format-spec Python aplicado al display (ej: .1% → 85.0%, .2f → 3.14). Vacío = default según agregación."
                    className="w-28 shrink-0 text-[11px] px-1.5 py-0.5 rounded border border-emerald-200 dark:border-emerald-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200"
                />
            </div>
        </div>
    );
}

// ── PivotTableConfig — componente principal ───────────────────────────────────

export default function PivotTableConfig({ fields = [], initial, onConfirm }) {
    const availableFields = fields;

    const initSpec = initial || {};
    const initRowFields = (initSpec.rows || []).map((f) => fieldMeta(f, availableFields));
    const initColFields  = (initSpec.cols || []).map((f) => fieldMeta(f, availableFields));
    const initValues = (initSpec.values || []).map((v) => ({
        field: v.field,
        agg: v.agg || 'mean',
        label: v.label ?? '',
        format: v.format ?? '',
    }));

    const [rows,   setRows  ] = useState(initRowFields);
    const [cols,   setCols  ] = useState(initColFields);
    const [values, setValues] = useState(initValues);
    const [totalsRows, setTotalsRows] = useState(initSpec.totals?.rows ?? true);
    const [totalsCols, setTotalsCols] = useState(initSpec.totals?.cols ?? true);

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
        setValues([...values, { field: item.field, agg: 'mean', label: '', format: '' }]);
    };

    const updateValue = (field, patch) => {
        setValues(values.map(v => v.field === field ? { ...v, ...patch } : v));
    };

    const isValid = rows.length > 0 && values.length > 0;

    // Campos en uso (para marcarlos en la paleta)
    const inUse = new Set([...rows.map(f => f.field), ...cols.map(f => f.field), ...values.map(v => v.field)]);

    const handleConfirm = () => {
        const spec = {
            rows: rows.map(f => f.field),
            cols: cols.map(f => f.field),
            values: values.map(v => ({
                field: v.field,
                agg: v.agg,
                label: v.label?.trim() ? v.label.trim() : null,
                format: v.format?.trim() ? v.format.trim() : null,
            })),
            totals: { rows: totalsRows, cols: totalsCols },
        };
        onConfirm(spec);
    };

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
                            Selecciona una métrica con columnas para que aparezcan campos aquí.
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
                description="Cada combinación única de estos campos crea una fila. El orden importa (multinivel)."
                items={rows}
                onDrop={(item) => addToZone(setRows, rows, item)}
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
                description="Pivote horizontal. Cada combinación única de estos campos crea una columna (multinivel)."
                items={cols}
                onDrop={(item) => addToZone(setCols, cols, item)}
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
                description="Campos a agregar. Elige agregación, etiqueta y formato por campo."
                items={values}
                onDrop={addValue}
            >
                {values.map(v => (
                    <ValueSlot
                        key={v.field}
                        item={v}
                        onRemove={() => removeFromZone(setValues, values, v.field)}
                        onChange={(patch) => updateValue(v.field, patch)}
                    />
                ))}
            </DropZone>

            {/* Totales */}
            <div>
                <p className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Totales</p>
                <div className="flex items-center gap-4">
                    <label className="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={totalsRows}
                            onChange={(e) => setTotalsRows(e.target.checked)}
                            className="accent-indigo-600"
                        />
                        Fila Total
                    </label>
                    <label className="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={totalsCols}
                            onChange={(e) => setTotalsCols(e.target.checked)}
                            className="accent-indigo-600"
                        />
                        Columna Total
                        <span className="text-slate-400">(solo si hay columnas)</span>
                    </label>
                </div>
            </div>

            {/* Botón confirmar */}
            <button
                disabled={!isValid}
                onClick={handleConfirm}
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

// ── Helpers ──────────────────────────────────────────────────────────────────

function fieldMeta(fieldName, availableFields) {
    const found = availableFields.find(f => f.field === fieldName);
    return found || { field: fieldName, label: fieldName, kind: 'dimensión' };
}
