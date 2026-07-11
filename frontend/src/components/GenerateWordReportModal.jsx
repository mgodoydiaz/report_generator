import React, { useState, useEffect } from 'react';
import { X, Download, FileText } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import { useAuth } from '../context/AuthContext';

/**
 * Modal para generar informes Word (docxtpl) registrados por nombre.
 *
 * Lista los informes disponibles desde GET /api/reports/word/informes
 * (cada uno es un módulo Python + plantilla .docx en el backend) y genera
 * vía POST /api/reports/word/{nombre}. El nombre del informe asocia
 * directamente al archivo — no hay mapeo intermedio.
 */
export default function GenerateWordReportModal({
    open,
    onClose,
    indicatorId,
    filtros,            // dict {nombre_dim_humano: valor|array}
}) {
    const { fetchAuth } = useAuth();

    const [informes, setInformes] = useState([]);
    const [loadingInformes, setLoadingInformes] = useState(false);
    const [nombreInforme, setNombreInforme] = useState('');
    const [titulo, setTitulo] = useState('');
    const [subtitulo, setSubtitulo] = useState('');
    const [generating, setGenerating] = useState(false);

    // Cargar informes disponibles al abrir
    useEffect(() => {
        if (!open) return;
        setLoadingInformes(true);
        fetchAuth(`${API_BASE_URL}/reports/word/informes`)
            .then((res) => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.json();
            })
            .then((data) => {
                setInformes(data);
                if (data.length && !data.some((i) => i.nombre === nombreInforme)) {
                    setNombreInforme(data[0].nombre);
                }
            })
            .catch((e) => toast.error('Error listando informes Word: ' + e.message))
            .finally(() => setLoadingInformes(false));
    }, [open]);

    if (!open) return null;

    const informeActual = informes.find((i) => i.nombre === nombreInforme);

    const handleGenerar = async () => {
        setGenerating(true);
        const tid = toast.loading('Generando informe Word…');
        try {
            const params = {};
            if (titulo.trim()) params.titulo = titulo.trim();
            if (subtitulo.trim()) params.subtitulo = subtitulo.trim();

            const res = await fetchAuth(`${API_BASE_URL}/reports/word/${nombreInforme}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    indicator_id: indicatorId,
                    filtros,
                    params,
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
            a.download = `informe_${nombreInforme}.docx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            toast.success('Informe Word descargado', { id: tid });
            onClose();
        } catch (e) {
            toast.error('Error Word: ' + e.message, { id: tid });
        } finally {
            setGenerating(false);
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
            onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        >
            <div
                role="dialog"
                aria-modal="true"
                aria-label="Generar informe Word"
                className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden"
            >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
                    <div className="flex items-center gap-2">
                        <FileText size={18} className="text-indigo-600" />
                        <div>
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                                Generar Informe Word
                            </h2>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                Plantilla .docx editable con códigos {'{{valor}}'}
                            </p>
                        </div>
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
                            Informe
                        </label>
                        <select
                            value={nombreInforme}
                            onChange={(e) => setNombreInforme(e.target.value)}
                            disabled={loadingInformes || !informes.length}
                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        >
                            {!informes.length && <option value="">{loadingInformes ? 'Cargando…' : 'Sin informes registrados'}</option>}
                            {informes.map((i) => (
                                <option key={i.nombre} value={i.nombre}>
                                    {i.label} ({i.nombre})
                                </option>
                            ))}
                        </select>
                        {informeActual?.descripcion && (
                            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1.5">
                                {informeActual.descripcion}
                            </p>
                        )}
                        {informeActual && !informeActual.plantilla_existe && (
                            <p className="text-[11px] text-amber-600 mt-1.5">
                                ⚠ La plantilla {informeActual.plantilla} no existe en el servidor.
                            </p>
                        )}
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1.5">
                            Título (opcional)
                        </label>
                        <input
                            type="text"
                            value={titulo}
                            onChange={(e) => setTitulo(e.target.value)}
                            placeholder="Título que reemplaza el código del informe"
                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1.5">
                            Subtítulo (opcional)
                        </label>
                        <input
                            type="text"
                            value={subtitulo}
                            onChange={(e) => setSubtitulo(e.target.value)}
                            placeholder="Ej: Establecimiento · Curso · Periodo"
                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                    </div>

                    <div className="text-[11px] text-slate-500 dark:text-slate-400 italic">
                        Se aplican los filtros activos del dashboard. El archivo descargado
                        es un .docx editable en Word.
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
                        disabled={generating || !nombreInforme || !informeActual?.plantilla_existe}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 disabled:cursor-not-allowed shadow-sm"
                    >
                        <Download size={14} />
                        {generating ? 'Generando…' : 'Descargar Word'}
                    </button>
                </div>
            </div>
        </div>
    );
}
