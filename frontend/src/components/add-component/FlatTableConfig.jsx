/**
 * FlatTableConfig.jsx — Configurador de tabla plana con filtros
 *
 * Permite al usuario elegir:
 *   - Columnas a mostrar
 *   - Campos con filtro interactivo en tiempo de vista
 *   - Orden por defecto
 *
 * Llama a onConfirm({ columns, filterFields, sortBy, sortDir })
 */

import React, { useState, useMemo } from 'react';
import { Check, ChevronUp, ChevronDown } from 'lucide-react';
import { buildAvailableFields } from './fieldUtils';

// ── Checkbox de campo ─────────────────────────────────────────────────────────

function FieldCheckbox({ field, label, kind, checked, onChange }) {
    const kindDot = kind === 'valor'
        ? 'bg-emerald-400'
        : 'bg-violet-400';
    return (
        <label className={`flex items-center gap-2.5 px-3 py-2 rounded-xl border cursor-pointer transition-all select-none ${
            checked
                ? 'border-indigo-300 dark:border-indigo-700 bg-indigo-50 dark:bg-indigo-900/20'
                : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 hover:border-slate-300 dark:hover:border-slate-600'
        }`}>
            <div className={`w-4 h-4 min-w-4 rounded border-2 flex items-center justify-center transition-all ${
                checked ? 'border-indigo-600 bg-indigo-600' : 'border-slate-300 dark:border-slate-600'
            }`}>
                {checked && <Check size={10} color="white" strokeWidth={3} />}
            </div>
            <input type="checkbox" className="sr-only" checked={checked} onChange={onChange} />
            <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${kindDot}`} />
            <span className={`text-xs font-medium flex-1 truncate ${checked ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-700 dark:text-slate-300'}`}>
                {label}
            </span>
            <code className="text-[10px] font-mono text-slate-400 dark:text-slate-500 shrink-0">{field}</code>
        </label>
    );
}

// ── FlatTableConfig ───────────────────────────────────────────────────────────

export default function FlatTableConfig({ allMetrics, allDimensions, derivedColumns, initial, onConfirm }) {
    const availableFields = useMemo(
        () => buildAvailableFields(allMetrics, allDimensions, derivedColumns),
        [allMetrics, allDimensions, derivedColumns]
    );

    const init = initial || {};

    // Columnas elegidas (array de field names, en orden)
    const [selectedCols, setSelectedCols] = useState(
        () => init.columns?.map(c => c.field) || availableFields.map(f => f.field)
    );
    // Campos con filtro interactivo
    const [filterFields, setFilterFields] = useState(init.filterFields || []);
    // Orden
    const [sortBy,  setSortBy ] = useState(init.sortBy  || '');
    const [sortDir, setSortDir] = useState(init.sortDir || 'asc');

    const toggleCol = (field) => {
        setSelectedCols(prev =>
            prev.includes(field) ? prev.filter(f => f !== field) : [...prev, field]
        );
    };

    const toggleFilter = (field) => {
        setFilterFields(prev =>
            prev.includes(field) ? prev.filter(f => f !== field) : [...prev, field]
        );
    };

    const isValid = selectedCols.length > 0;

    const handleConfirm = () => {
        const columns = selectedCols.map(f => {
            const meta = availableFields.find(a => a.field === f);
            return { field: f, label: meta?.label || f };
        });
        onConfirm({ columns, filterFields, sortBy, sortDir });
    };

    if (availableFields.length === 0) {
        return (
            <div className="rounded-xl border border-amber-200 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-900/10 px-4 py-3">
                <p className="text-xs text-amber-700 dark:text-amber-400">
                    Configura <strong>column_roles</strong> en el indicador para que aparezcan campos aquí.
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-5">

            {/* Columnas a mostrar */}
            <div>
                <p className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">Columnas a mostrar</p>
                <p className="text-[11px] text-slate-400 dark:text-slate-500 mb-2">
                    Selecciona y ordena los campos que aparecerán como columnas en la tabla.
                </p>
                <div className="space-y-1.5">
                    {availableFields.map(f => (
                        <FieldCheckbox
                            key={f.field}
                            field={f.field}
                            label={f.label}
                            kind={f.kind}
                            checked={selectedCols.includes(f.field)}
                            onChange={() => toggleCol(f.field)}
                        />
                    ))}
                </div>
            </div>

            {/* Filtros interactivos */}
            <div>
                <p className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">Filtros interactivos</p>
                <p className="text-[11px] text-slate-400 dark:text-slate-500 mb-2">
                    Los campos marcados mostrarán un desplegable de filtro encima de la tabla.
                </p>
                <div className="space-y-1.5">
                    {availableFields.filter(f => f.kind === 'dimensión').map(f => (
                        <label key={f.field} className={`flex items-center gap-2.5 px-3 py-2 rounded-xl border cursor-pointer transition-all select-none ${
                            filterFields.includes(f.field)
                                ? 'border-violet-300 dark:border-violet-700 bg-violet-50 dark:bg-violet-900/20'
                                : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 hover:border-slate-300 dark:hover:border-slate-600'
                        }`}>
                            <div className={`w-4 h-4 min-w-4 rounded border-2 flex items-center justify-center transition-all ${
                                filterFields.includes(f.field) ? 'border-violet-600 bg-violet-600' : 'border-slate-300 dark:border-slate-600'
                            }`}>
                                {filterFields.includes(f.field) && <Check size={10} color="white" strokeWidth={3} />}
                            </div>
                            <input type="checkbox" className="sr-only" checked={filterFields.includes(f.field)} onChange={() => toggleFilter(f.field)} />
                            <span className={`text-xs font-medium flex-1 ${filterFields.includes(f.field) ? 'text-violet-700 dark:text-violet-300' : 'text-slate-700 dark:text-slate-300'}`}>
                                {f.label}
                            </span>
                        </label>
                    ))}
                    {availableFields.filter(f => f.kind === 'dimensión').length === 0 && (
                        <p className="text-[11px] text-slate-400 px-1">No hay campos de dimensión disponibles.</p>
                    )}
                </div>
            </div>

            {/* Orden por defecto */}
            <div>
                <p className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">Orden por defecto</p>
                <div className="flex gap-2 items-center">
                    <select
                        value={sortBy}
                        onChange={e => setSortBy(e.target.value)}
                        className="flex-1 bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                    >
                        <option value="">Sin orden (original)</option>
                        {availableFields.map(f => (
                            <option key={f.field} value={f.field}>{f.label}</option>
                        ))}
                    </select>
                    <button
                        onClick={() => setSortDir(d => d === 'asc' ? 'desc' : 'asc')}
                        className="flex items-center gap-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 text-xs font-medium text-slate-600 dark:text-slate-300 hover:border-slate-300 transition-all"
                    >
                        {sortDir === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        {sortDir === 'asc' ? 'Asc' : 'Desc'}
                    </button>
                </div>
            </div>

            {/* Confirmar */}
            <button
                disabled={!isValid}
                onClick={handleConfirm}
                className={`w-full py-2.5 rounded-xl text-sm font-bold transition-all ${
                    isValid
                        ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed'
                }`}
            >
                {isValid ? 'Aplicar configuración' : 'Selecciona al menos una columna'}
            </button>
        </div>
    );
}
