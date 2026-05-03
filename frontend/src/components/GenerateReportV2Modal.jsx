import React, { useState, useEffect } from 'react';
import { X, Download } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import { useAuth } from '../context/AuthContext';

/**
 * Modal compacto para generar el informe PDF v2 (motor paridad LaTeX).
 *
 * Permite editar antes de descargar:
 *   - Las 3 líneas del header centrado (título, asignatura/curso, periodo)
 *   - El pie izquierdo (autor)
 *   - El nombre del archivo descargado
 *
 * Persiste el último branding usado por tipo en localStorage para que
 * volver a generar el mismo informe sea 1 click. No toca el esquema en
 * el repo — sólo se manda como `overrides` en el body del POST.
 */
export default function GenerateReportV2Modal({
    open,
    onClose,
    tipoV2,             // 'simce' | 'dia'
    indicatorId,
    filtros,            // dict {nombre_dim_humano: valor}
}) {
    const { fetchAuth } = useAuth();

    const [headerLine1, setHeaderLine1] = useState('');
    const [headerLine2, setHeaderLine2] = useState('');
    const [headerLine3, setHeaderLine3] = useState('');
    const [autor, setAutor] = useState('');
    const [filename, setFilename] = useState('');
    const [generating, setGenerating] = useState(false);

    const storageKey = `report_v2_branding_${tipoV2}`;

    // Defaults sensatos por tipo (si no hay nada en localStorage)
    const defaultsByTipo = {
        simce: {
            line1: 'Informe Ensayo SIMCE',
            line2: 'Lenguaje 2° Medio',
            line3: 'Mes Año',
            autor: 'Miguel Godoy Díaz',
        },
        dia: {
            line1: 'Informe DIA Diagnóstico',
            line2: 'Asignatura Nivel Medio',
            line3: 'Mes Año',
            autor: 'Miguel Godoy Díaz',
        },
    };

    // Al abrir el modal, cargar valores: localStorage > defaults
    useEffect(() => {
        if (!open) return;
        const saved = localStorage.getItem(storageKey);
        const defaults = defaultsByTipo[tipoV2] || defaultsByTipo.dia;
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                setHeaderLine1(parsed.line1 ?? defaults.line1);
                setHeaderLine2(parsed.line2 ?? defaults.line2);
                setHeaderLine3(parsed.line3 ?? defaults.line3);
                setAutor(parsed.autor ?? defaults.autor);
            } catch {
                setHeaderLine1(defaults.line1);
                setHeaderLine2(defaults.line2);
                setHeaderLine3(defaults.line3);
                setAutor(defaults.autor);
            }
        } else {
            setHeaderLine1(defaults.line1);
            setHeaderLine2(defaults.line2);
            setHeaderLine3(defaults.line3);
            setAutor(defaults.autor);
        }
        setFilename(`informe_${tipoV2}.pdf`);
    }, [open, tipoV2]);

    if (!open) return null;

    const handleGenerar = async () => {
        // Persistir branding para próxima vez
        localStorage.setItem(storageKey, JSON.stringify({
            line1: headerLine1,
            line2: headerLine2,
            line3: headerLine3,
            autor,
        }));

        const overrides = {
            branding: {
                center_header: [headerLine1, headerLine2, headerLine3].filter(Boolean),
                left_footer: autor,
            },
        };

        setGenerating(true);
        const tid = toast.loading('Generando informe v2…');
        try {
            const res = await fetchAuth(`${API_BASE_URL}/reports/${tipoV2}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    indicator_id: indicatorId,
                    filtros,
                    overrides,
                }),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename || `informe_${tipoV2}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            toast.success('Informe v2 descargado', { id: tid });
            onClose();
        } catch (e) {
            toast.error('Error v2: ' + e.message, { id: tid });
        } finally {
            setGenerating(false);
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
            onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        >
            <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
                    <div>
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                            Generar Informe v2 ({tipoV2.toUpperCase()})
                        </h2>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                            Personaliza los textos del header antes de descargar el PDF
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
                        aria-label="Cerrar"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Body */}
                <div className="px-6 py-5 space-y-4">
                    <div>
                        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1.5">
                            Encabezado central (3 líneas)
                        </label>
                        <div className="space-y-2">
                            <input
                                type="text"
                                value={headerLine1}
                                onChange={(e) => setHeaderLine1(e.target.value)}
                                placeholder="Línea 1 — título del informe"
                                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            />
                            <input
                                type="text"
                                value={headerLine2}
                                onChange={(e) => setHeaderLine2(e.target.value)}
                                placeholder="Línea 2 — asignatura · nivel · curso"
                                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            />
                            <input
                                type="text"
                                value={headerLine3}
                                onChange={(e) => setHeaderLine3(e.target.value)}
                                placeholder="Línea 3 — mes año"
                                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1.5">
                            Pie izquierdo (autor)
                        </label>
                        <input
                            type="text"
                            value={autor}
                            onChange={(e) => setAutor(e.target.value)}
                            placeholder="Nombre del autor o entidad"
                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1.5">
                            Nombre del archivo descargado
                        </label>
                        <input
                            type="text"
                            value={filename}
                            onChange={(e) => setFilename(e.target.value)}
                            placeholder={`informe_${tipoV2}.pdf`}
                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                    </div>

                    <div className="text-[11px] text-slate-500 dark:text-slate-400 italic">
                        Se recordará para la próxima vez que generes un informe {tipoV2.toUpperCase()}.
                    </div>
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-2 px-6 py-4 bg-slate-50 dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800">
                    <button
                        onClick={onClose}
                        disabled={generating}
                        className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 disabled:opacity-50"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleGenerar}
                        disabled={generating || !headerLine1.trim()}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 disabled:cursor-not-allowed shadow-sm"
                    >
                        <Download size={14} />
                        {generating ? 'Generando…' : 'Descargar PDF'}
                    </button>
                </div>
            </div>
        </div>
    );
}
