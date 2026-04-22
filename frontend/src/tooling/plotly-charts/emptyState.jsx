import React from 'react';

/**
 * EmptyState — mensaje contextual cuando un chart no tiene datos.
 * Los componentes individuales llaman a `emptyReason(ctx)` para decidir cuál
 * mensaje mostrar; devuelve null si hay datos suficientes.
 */

export function emptyReason({ records, requiredPeriods = 0, activeFilters = false } = {}) {
    const n = Array.isArray(records) ? records.length : 0;
    if (n === 0) {
        if (activeFilters) return { key: 'filters', msg: 'Ningún registro coincide con los filtros actuales.' };
        return { key: 'nodata', msg: 'Sin datos para este componente.' };
    }
    if (requiredPeriods > 0) {
        const periods = new Set();
        for (const r of records) {
            if (r._evaluacion_num != null) periods.add(Number(r._evaluacion_num));
        }
        if (periods.size < requiredPeriods) {
            return { key: 'trajectory', msg: `Se requieren al menos ${requiredPeriods} evaluaciones para este análisis. Disponibles: ${periods.size}.` };
        }
    }
    return null;
}

export function EmptyState({ reason, onClearFilters }) {
    if (!reason) return null;
    return (
        <div className="flex flex-col items-center justify-center gap-2 py-8 px-4 rounded-xl border border-dashed border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400">{reason.msg}</p>
            {reason.key === 'filters' && onClearFilters && (
                <button
                    type="button"
                    onClick={onClearFilters}
                    className="mt-2 text-xs font-semibold text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 underline"
                >
                    Limpiar filtros
                </button>
            )}
        </div>
    );
}
