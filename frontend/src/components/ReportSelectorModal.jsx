import React, { useState, useEffect } from 'react';
import { X, FileText, FileType, Loader2, ChevronRight } from 'lucide-react';
import { API_BASE_URL } from '../constants';
import { useAuth } from '../context/AuthContext';

/**
 * Selector unificado de tipo de informe (Fase 1 del motor único).
 * Consulta GET /api/indicators/{id}/report-options y muestra las opciones
 * disponibles; al elegir una, delega en el modal específico vía onSelect(opcion).
 */
export default function ReportSelectorModal({ open, onClose, indicatorId, onSelect }) {
    const { fetchAuth } = useAuth();
    const [options, setOptions] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!open || !indicatorId) return;
        setOptions(null);
        setError(null);
        (async () => {
            try {
                const resp = await fetchAuth(`${API_BASE_URL}/indicators/${indicatorId}/report-options`);
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.detail || 'No se pudieron cargar los informes disponibles');
                setOptions(data.opciones || []);
            } catch (err) {
                setError(err.message);
            }
        })();
    }, [open, indicatorId]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" onClick={onClose} />
            <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-3xl shadow-2xl p-6 max-h-[85vh] overflow-y-auto">
                <div className="flex items-center justify-between mb-5">
                    <h3 className="font-bold text-slate-800 dark:text-slate-100">Generar informe</h3>
                    <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-xl transition-all">
                        <X size={18} />
                    </button>
                </div>

                {error && (
                    <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">
                        {error}
                    </div>
                )}

                {!options && !error && (
                    <div className="flex justify-center py-10">
                        <Loader2 size={22} className="animate-spin text-indigo-400" />
                    </div>
                )}

                {options && (
                    <div className="space-y-2">
                        {options.map(op => (
                            <button
                                key={op.id}
                                disabled={!op.disponible}
                                onClick={() => onSelect(op)}
                                title={op.disponible ? op.descripcion : op.motivo_no_disponible}
                                className={`w-full flex items-center gap-4 p-4 rounded-2xl border-2 text-left transition-all ${
                                    op.disponible
                                        ? 'border-slate-100 dark:border-slate-800 hover:border-indigo-400 hover:bg-indigo-50/50 dark:hover:bg-slate-800 cursor-pointer'
                                        : 'border-slate-50 dark:border-slate-800/50 opacity-50 cursor-not-allowed'
                                }`}
                            >
                                <div className={`p-2.5 rounded-xl ${op.formato === 'word' ? 'bg-emerald-50 dark:bg-emerald-900/20' : 'bg-indigo-50 dark:bg-indigo-900/20'}`}>
                                    {op.formato === 'word'
                                        ? <FileType size={18} className="text-emerald-600 dark:text-emerald-400" />
                                        : <FileText size={18} className="text-indigo-600 dark:text-indigo-400" />}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-semibold text-sm text-slate-800 dark:text-slate-100">{op.label}</p>
                                    <p className="text-xs text-slate-400 mt-0.5">
                                        {op.disponible ? op.descripcion : op.motivo_no_disponible}
                                    </p>
                                </div>
                                {op.disponible && <ChevronRight size={16} className="text-slate-300 shrink-0" />}
                            </button>
                        ))}
                        {options.length === 0 && (
                            <p className="text-sm text-slate-400 text-center py-6">
                                Este indicador aún no tiene informes configurados.
                            </p>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
