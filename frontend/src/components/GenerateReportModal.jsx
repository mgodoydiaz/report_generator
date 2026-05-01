import React, { useState, useEffect, useMemo } from 'react';
import { X, Download, FileText, Filter, RefreshCcw, Save, Calendar, TrendingUp } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import { useAuth } from '../context/AuthContext';
import { BrandingEditor } from './LayoutEditorModal';

// Dimensiones consideradas "temporales" (se ocultan en modo histórico, donde
// se quiere ver evolución a través del tiempo). Coincidencia case-insensitive
// por substring sobre el `name` de la dimensión.
const TEMPORAL_DIM_NAMES = [
    'mes', 'n prueba', 'n evaluación', 'n evaluacion',
    'numero_prueba', 'numero prueba', 'numero evaluación',
    'evaluación', 'evaluacion', 'fecha',
];

function isTemporalDimension(dimName) {
    if (!dimName) return false;
    const n = String(dimName).toLowerCase();
    return TEMPORAL_DIM_NAMES.some(k => n.includes(k));
}

/**
 * Modal para generar el informe PDF desde la página Results.
 *
 * Expone:
 *   - **Tipo de informe**: toggle "Por evaluación" / "Histórico" — define qué
 *     `pdf_layout` del indicator se usa (`pdf_layout` vs `pdf_layout_historico`).
 *   - Filtros (pre‑cargados desde el dashboard y editables). En modo histórico
 *     las dimensiones temporales se deshabilitan automáticamente.
 *   - Motor del informe (lista de engines disponibles)
 *   - Branding (logos, encabezados, pie, n° de página) reutilizando BrandingEditor
 *   - Checkbox "Guardar branding como default" para persistir en el layout activo
 */
export default function GenerateReportModal({
    open,
    onClose,
    indicator,           // full indicator object (incluye pdf_layout, pdf_layout_historico, id_indicator, name)
    indicatorDims,       // {id_dimension_str: {id, name, values: []}}
    initialFilters,      // {id_dimension_str: valor}
    sortedDimKeys,       // orden preferido de dimensiones
    onSaved,             // callback opcional, invocado si se persiste pdf_layout
}) {
    const { fetchAuth, user } = useAuth();
    const orgId = user?.org_id;

    const [engines, setEngines] = useState([]);
    const [selectedEngine, setSelectedEngine] = useState('weasyprint');
    const [tipo, setTipo] = useState('evaluacion'); // 'evaluacion' | 'historico'
    const [filters, setFilters] = useState({});
    const [branding, setBranding] = useState({});
    const [saveAsDefault, setSaveAsDefault] = useState(false);
    const [generating, setGenerating] = useState(false);

    // Layout activo según el tipo seleccionado
    const activeLayout = useMemo(() => {
        if (!indicator) return {};
        const lay = tipo === 'historico'
            ? (indicator.pdf_layout_historico && typeof indicator.pdf_layout_historico === 'object'
                ? indicator.pdf_layout_historico : {})
            : (indicator.pdf_layout && typeof indicator.pdf_layout === 'object'
                ? indicator.pdf_layout : {});
        return lay || {};
    }, [indicator, tipo]);

    const layoutHasSections = useMemo(() => {
        const secs = activeLayout?.sections;
        return Array.isArray(secs) && secs.length > 0;
    }, [activeLayout]);

    // Reset al abrir
    useEffect(() => {
        if (!open || !indicator) return;
        setFilters({ ...(initialFilters || {}) });
        setSaveAsDefault(false);
        setTipo('evaluacion');
    }, [open, indicator, initialFilters]);

    // Refresh branding y engine cuando cambia el tipo (cada layout puede tener
    // su propio branding configurado)
    useEffect(() => {
        if (!open || !indicator) return;
        setBranding({ ...(activeLayout.branding || {}) });
        setSelectedEngine((activeLayout.engine || 'weasyprint').toLowerCase());
    }, [open, indicator, tipo, activeLayout]);

    // Limpiar filtros temporales al cambiar a histórico (no aplican)
    useEffect(() => {
        if (tipo !== 'historico' || !indicatorDims) return;
        setFilters(prev => {
            const next = { ...prev };
            for (const dimId of Object.keys(prev)) {
                const dim = indicatorDims[dimId];
                if (dim && isTemporalDimension(dim.name)) delete next[dimId];
            }
            return next;
        });
    }, [tipo, indicatorDims]);

    // Cargar engines disponibles
    useEffect(() => {
        if (!open) return;
        let active = true;
        (async () => {
            try {
                const res = await fetchAuth(`${API_BASE_URL}/indicators/export-pdf/engines`);
                if (!res.ok) return;
                const data = await res.json();
                if (active && Array.isArray(data)) setEngines(data);
            } catch { /* silent */ }
        })();
        return () => { active = false; };
    }, [open, fetchAuth]);

    const dimKeys = useMemo(() => {
        if (Array.isArray(sortedDimKeys) && sortedDimKeys.length) return sortedDimKeys;
        return Object.keys(indicatorDims || {});
    }, [sortedDimKeys, indicatorDims]);

    const currentEngineMeta = useMemo(
        () => engines.find(e => e.id === selectedEngine),
        [engines, selectedEngine]
    );

    const setFilter = (dimId, value) => {
        setFilters(prev => {
            const next = { ...prev };
            if (value) next[dimId] = value;
            else delete next[dimId];
            return next;
        });
    };

    const clearFilters = () => setFilters({});
    const hasActiveFilters = Object.keys(filters).length > 0;

    const handleGenerate = async () => {
        if (!indicator || generating) return;
        setGenerating(true);
        try {
            const res = await fetchAuth(
                `${API_BASE_URL}/indicators/${indicator.id_indicator}/export-pdf`,
                {
                    method: 'POST',
                    body: JSON.stringify({
                        filters,
                        engine: selectedEngine,
                        branding_override: branding,
                        save_as_default: saveAsDefault,
                        tipo, // 'evaluacion' | 'historico'
                    }),
                }
            );
            if (!res.ok) {
                let detail = 'Error al generar el informe PDF';
                try {
                    const err = await res.json();
                    if (err?.detail) detail = err.detail;
                } catch { /* ignore */ }
                throw new Error(detail);
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const safeName = (indicator.name || 'informe')
                .replace(/\s+/g, '_')
                .replace(/\//g, '-');
            const tipoSuffix = tipo === 'historico' ? '_historico' : '';
            a.download = `informe_${safeName}${tipoSuffix}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            toast.success('Informe descargado');
            if (saveAsDefault && onSaved) onSaved();
            onClose();
        } catch (err) {
            toast.error(err.message);
        } finally {
            setGenerating(false);
        }
    };

    if (!open || !indicator) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
            <div className="w-full max-w-3xl max-h-[90vh] bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-sm">
                            <FileText size={18} />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-slate-800 dark:text-white leading-tight">
                                Generar informe PDF
                            </h2>
                            <p className="text-xs text-slate-400 dark:text-slate-500">
                                {indicator.name}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        disabled={generating}
                        className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">

                    {/* Tipo de informe — toggle segmentado */}
                    <section>
                        <label className="block text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-2">
                            Tipo de informe
                        </label>
                        <div className="flex bg-slate-100 dark:bg-slate-800 rounded-xl p-1">
                            <button
                                type="button"
                                onClick={() => setTipo('evaluacion')}
                                className={`flex-1 py-2 px-3 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-all ${
                                    tipo === 'evaluacion'
                                        ? 'bg-white dark:bg-slate-900 shadow-sm text-indigo-600 dark:text-indigo-400'
                                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                                }`}
                            >
                                <Calendar size={14} />
                                Por evaluación
                            </button>
                            <button
                                type="button"
                                onClick={() => setTipo('historico')}
                                className={`flex-1 py-2 px-3 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-all ${
                                    tipo === 'historico'
                                        ? 'bg-white dark:bg-slate-900 shadow-sm text-indigo-600 dark:text-indigo-400'
                                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                                }`}
                            >
                                <TrendingUp size={14} />
                                Histórico
                            </button>
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1.5">
                            {tipo === 'evaluacion'
                                ? 'Snapshot de un momento concreto. Filtra mes / N° prueba para acotarlo.'
                                : 'Comparación a lo largo del año. Las dimensiones temporales no se filtran (se ven todas en el gráfico).'}
                        </p>
                        {!layoutHasSections && (
                            <div className="mt-2 px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50">
                                <p className="text-[11px] text-amber-800 dark:text-amber-300">
                                    Este indicador no tiene secciones configuradas para el modo
                                    <strong> {tipo === 'historico' ? 'histórico' : 'por evaluación'}</strong>.
                                    Configúralas en el Editor de Layout antes de generar.
                                </p>
                            </div>
                        )}
                    </section>

                    {/* Motor del informe */}
                    <section>
                        <label className="block text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-2">
                            Motor del informe
                        </label>
                        <select
                            value={selectedEngine}
                            onChange={(e) => setSelectedEngine(e.target.value)}
                            className="w-full text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-200 px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                        >
                            {engines.length === 0 && (
                                <option value="weasyprint">Layout del indicador</option>
                            )}
                            {engines.map(e => (
                                <option
                                    key={e.id}
                                    value={e.id}
                                    disabled={!e.available}
                                >
                                    {e.label}{!e.available ? ' — próximamente' : ''}
                                </option>
                            ))}
                        </select>
                        {currentEngineMeta?.description && (
                            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1.5">
                                {currentEngineMeta.description}
                            </p>
                        )}
                    </section>

                    {/* Filtros */}
                    <section>
                        <div className="flex items-center justify-between mb-2">
                            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                                <Filter size={12} /> Filtros
                            </label>
                            {hasActiveFilters && (
                                <button
                                    onClick={clearFilters}
                                    className="text-[11px] font-semibold text-slate-500 hover:text-indigo-600"
                                >
                                    Limpiar
                                </button>
                            )}
                        </div>
                        {dimKeys.length === 0 ? (
                            <p className="text-xs text-slate-400 italic">
                                El indicador no tiene dimensiones filtrables.
                            </p>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {dimKeys.map(dimId => {
                                    const dim = indicatorDims?.[dimId];
                                    if (!dim) return null;
                                    const values = (dim.values || []).filter(v => {
                                        if (v === null || v === undefined) return false;
                                        const s = String(v).trim().toLowerCase();
                                        return s && s !== 'nan' && s !== 'nat' && s !== 'none' && s !== 'null';
                                    });
                                    if (values.length === 0) return null;
                                    const isTemporal = isTemporalDimension(dim.name);
                                    const disabledForHistorico = tipo === 'historico' && isTemporal;
                                    return (
                                        <div key={dimId} className={disabledForHistorico ? 'opacity-50' : ''}>
                                            <label className="block text-[10px] uppercase font-semibold text-slate-500 dark:text-slate-400 mb-1 flex items-center gap-1">
                                                {dim.name}
                                                {isTemporal && (
                                                    <Calendar size={10} className="text-slate-400" />
                                                )}
                                            </label>
                                            <select
                                                value={filters[dimId] || ''}
                                                onChange={(e) => setFilter(dimId, e.target.value)}
                                                disabled={disabledForHistorico}
                                                className="w-full text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-200 px-3 py-2 disabled:cursor-not-allowed"
                                            >
                                                <option value="">
                                                    {disabledForHistorico ? 'Todos (histórico)' : 'Todos'}
                                                </option>
                                                {!disabledForHistorico && values.map(v => (
                                                    <option key={v} value={v}>{v}</option>
                                                ))}
                                            </select>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </section>

                    {/* Branding (encabezados, logos, pie) */}
                    {selectedEngine === 'weasyprint' && (
                        <section>
                            <label className="block text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-2">
                                Encabezado y pie de página
                            </label>
                            <BrandingEditor
                                branding={branding}
                                onChange={setBranding}
                                orgId={orgId}
                                fetchAuth={fetchAuth}
                            />
                            <label className="flex items-center gap-2 mt-3 text-xs text-slate-600 dark:text-slate-300 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={saveAsDefault}
                                    onChange={(e) => setSaveAsDefault(e.target.checked)}
                                    className="rounded"
                                />
                                <Save size={12} className="text-slate-400" />
                                Guardar estos ajustes como default del layout {tipo === 'historico' ? 'histórico' : 'por evaluación'}
                            </label>
                        </section>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40">
                    <button
                        onClick={onClose}
                        disabled={generating}
                        className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 disabled:opacity-50"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleGenerate}
                        disabled={generating || !currentEngineMeta?.available || !layoutHasSections}
                        className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 disabled:cursor-not-allowed shadow-sm"
                    >
                        {generating ? (
                            <RefreshCcw size={14} className="animate-spin" />
                        ) : (
                            <Download size={14} />
                        )}
                        {generating ? 'Generando...' : 'Generar PDF'}
                    </button>
                </div>
            </div>
        </div>
    );
}
