import React, { useState, useEffect } from 'react';
import { X, Save, Plus, Trash2, LayoutGrid, ChevronUp, ChevronDown, GripVertical } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import { DEFAULT_LAYOUT } from '../tooling/dashboardRenderer';

// ── Catálogo de componentes disponibles ──────────────────────────────────────

// Componentes que permiten elegir dimensión (habilidad vs habilidad_2) al agregar
const DIMENSION_PICKER_IDS = new Set(['GraficoHabilidades', 'GraficoRadarHabilidades']);

const DIMENSION_OPTIONS = [
    { value: 'habilidad',   label: 'Habilidad',             requires: 'habilidad' },
    { value: 'habilidad_2', label: 'Habilidad 2 / Eje Temático', requires: 'habilidad_2' },
];

const CHART_COMPONENTS = [
    { id: 'GraficoLogroPorCurso',       label: 'Logro Promedio por Curso',       type: 'chart',  requires: ['logro_1'] },
    { id: 'GraficoBoxplotPorCurso',     label: 'Distribución por Curso (Boxplot)', type: 'chart', requires: ['logro_1'] },
    { id: 'GraficoNivelesPorCurso',     label: 'Alumnos por Nivel por Curso',    type: 'chart',  requires: ['nivel_de_logro'] },
    { id: 'GraficoHabilidades',         label: 'Logro por Habilidad',            type: 'chart',  requires: ['habilidad'], dimensionPicker: true },
    { id: 'GraficoDistribucionNiveles', label: 'Distribución de Niveles (Pie)',  type: 'chart',  requires: ['nivel_de_logro'] },
    { id: 'GraficoNivelesPorCursoYMes',          label: 'Niveles por Curso y Evaluación',        type: 'chart', requires: ['nivel_de_logro', 'evaluacion_num'] },
    { id: 'GraficoPromedioAgrupadoPorDimension', label: 'Logro Promedio por Curso y Evaluación', type: 'chart', requires: ['logro_1', 'evaluacion_num'] },
    { id: 'GraficoTendenciaTemporal',            label: 'Tendencia Temporal por Curso',          type: 'chart', requires: ['logro_1', 'evaluacion_num'] },
    { id: 'GraficoRadarHabilidades',             label: 'Radar de Habilidades',                  type: 'chart', requires: ['habilidad'], dimensionPicker: true },
];

const TABLE_COMPONENTS = [
    { id: 'TablaResumenCursos', label: 'Resumen por Curso',   type: 'table', requires: [] },
    { id: 'TablaAlumnos',       label: 'Logro por Estudiante', type: 'table', requires: [] },
    { id: 'TablaPreguntas',     label: 'Logro por Pregunta',  type: 'table', requires: [] },
];

const SPECIAL_COMPONENTS = [
    { id: 'kpis',            label: 'Tarjetas KPI',       type: 'kpis',            requires: [] },
    { id: 'course_selector', label: 'Selector de Curso',  type: 'course_selector', requires: [] },
];

const ALL_COMPONENTS = [...SPECIAL_COMPONENTS, ...TABLE_COMPONENTS, ...CHART_COMPONENTS];

const COLS_OPTIONS = [1, 2, 3, 4];

const ROLES_LABELS = {
    logro_1:        'Logro 1',
    logro_2:        'Logro 2',
    nivel_de_logro: 'Nivel de Logro',
    habilidad:      'Habilidad',
    habilidad_2:    'Habilidad 2',
    evaluacion_num: 'N° Evaluación',
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function getComponentMeta(item) {
    return ALL_COMPONENTS.find(c => c.id === (item.component || item.type)) || null;
}

function itemLabel(item) {
    const meta = getComponentMeta(item);
    return meta ? meta.label : item.component || item.type;
}

function requiresLabel(requires) {
    if (!requires || requires.length === 0) return null;
    return requires.map(r => ROLES_LABELS[r] || r).join(', ');
}

function cloneLayout(layout) {
    return JSON.parse(JSON.stringify(layout));
}

// ── Sub-componentes ──────────────────────────────────────────────────────────

function ItemBadge({ item, onRemove }) {
    const meta = getComponentMeta(item);
    const typeColor = {
        kpis:            'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-900/20 dark:border-amber-700 dark:text-amber-400',
        course_selector: 'bg-slate-50 border-slate-200 text-slate-600 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-400',
        table:           'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-900/20 dark:border-indigo-700 dark:text-indigo-400',
        chart:           'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/20 dark:border-emerald-700 dark:text-emerald-400',
    }[meta?.type || item.type] || 'bg-slate-50 border-slate-200 text-slate-600';

    return (
        <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-semibold ${typeColor}`}>
            <GripVertical size={12} className="opacity-40" />
            <span>{itemLabel(item)}</span>
            {item.dimension && (
                <span className="opacity-70 font-normal italic">
                    {DIMENSION_OPTIONS.find(d => d.value === item.dimension)?.label ?? item.dimension}
                </span>
            )}
            {!item.dimension && meta?.requires?.length > 0 && (
                <span className="opacity-50 font-normal">({requiresLabel(meta.requires)})</span>
            )}
            <button onClick={onRemove} className="ml-1 opacity-50 hover:opacity-100 transition-opacity">
                <X size={12} />
            </button>
        </div>
    );
}

function RowEditor({ row, rowIndex, onUpdate, onDelete, onMoveUp, onMoveDown, isFirst, isLast }) {
    const [showAddItem, setShowAddItem] = useState(false);
    const [pendingComp, setPendingComp] = useState(null); // comp que espera elección de dimensión

    const handleAddItem = (compMeta) => {
        if (compMeta.dimensionPicker) {
            setPendingComp(compMeta);
            return;
        }
        commitAddItem(compMeta, null);
    };

    const commitAddItem = (compMeta, dimension) => {
        const newItem = compMeta.type === 'kpis' || compMeta.type === 'course_selector'
            ? { type: compMeta.type }
            : { type: compMeta.type, component: compMeta.id, requires: compMeta.requires };
        if (dimension) {
            newItem.dimension = dimension;
            // Ajustar requires según la dimensión elegida
            const dimOpt = DIMENSION_OPTIONS.find(d => d.value === dimension);
            if (dimOpt) newItem.requires = [dimOpt.requires];
        }
        onUpdate({ ...row, items: [...row.items, newItem] });
        setShowAddItem(false);
        setPendingComp(null);
    };

    const handleRemoveItem = (itemIdx) => {
        onUpdate({ ...row, items: row.items.filter((_, i) => i !== itemIdx) });
    };

    const handleColsChange = (cols) => {
        onUpdate({ ...row, cols: parseInt(cols) });
    };

    return (
        <div className="border border-slate-200 dark:border-slate-700 rounded-xl p-3 bg-slate-50/50 dark:bg-slate-800/30 space-y-2">
            {/* Row header */}
            <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 w-14">Fila {rowIndex + 1}</span>

                {/* Cols selector */}
                <div className="flex items-center gap-1">
                    <span className="text-[10px] text-slate-400">Cols:</span>
                    {COLS_OPTIONS.map(n => (
                        <button
                            key={n}
                            onClick={() => handleColsChange(n)}
                            className={`w-6 h-6 rounded text-xs font-bold transition-all ${row.cols === n
                                ? 'bg-indigo-600 text-white'
                                : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-indigo-50 dark:hover:bg-slate-600'
                            }`}
                        >
                            {n}
                        </button>
                    ))}
                </div>

                <div className="flex-1" />

                {/* Move up/down */}
                <button onClick={onMoveUp} disabled={isFirst} className="p-1 text-slate-300 dark:text-slate-600 hover:text-slate-500 disabled:opacity-30 transition-colors">
                    <ChevronUp size={14} />
                </button>
                <button onClick={onMoveDown} disabled={isLast} className="p-1 text-slate-300 dark:text-slate-600 hover:text-slate-500 disabled:opacity-30 transition-colors">
                    <ChevronDown size={14} />
                </button>
                <button onClick={onDelete} className="p-1 text-slate-300 dark:text-slate-600 hover:text-red-500 transition-colors">
                    <Trash2 size={14} />
                </button>
            </div>

            {/* Items */}
            <div className="flex flex-wrap gap-1.5 min-h-8">
                {row.items.map((item, idx) => (
                    <ItemBadge key={idx} item={item} onRemove={() => handleRemoveItem(idx)} />
                ))}

                {/* Add item button */}
                <div className="relative">
                    <button
                        onClick={() => setShowAddItem(v => !v)}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-dashed border-slate-300 dark:border-slate-600 text-xs text-slate-400 hover:border-indigo-400 hover:text-indigo-500 transition-all"
                    >
                        <Plus size={12} />
                        Agregar
                    </button>

                    {showAddItem && !pendingComp && (
                        <div className="absolute left-0 top-8 z-50 w-64 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                            {[
                                { label: 'Especiales', items: SPECIAL_COMPONENTS },
                                { label: 'Tablas', items: TABLE_COMPONENTS },
                                { label: 'Gráficos', items: CHART_COMPONENTS },
                            ].map(group => (
                                <div key={group.label}>
                                    <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-400 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-100 dark:border-slate-700">
                                        {group.label}
                                    </div>
                                    {group.items.map(comp => (
                                        <button
                                            key={comp.id}
                                            onClick={() => handleAddItem(comp)}
                                            className="w-full text-left px-3 py-2 text-xs hover:bg-indigo-50 dark:hover:bg-slate-700 transition-colors"
                                        >
                                            <span className="font-semibold text-slate-700 dark:text-slate-200">{comp.label}</span>
                                            {comp.requires?.length > 0 && (
                                                <span className="ml-1 text-slate-400">({requiresLabel(comp.requires)})</span>
                                            )}
                                        </button>
                                    ))}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Sub-menú de dimensión para GraficoHabilidades / GraficoRadarHabilidades */}
                    {showAddItem && pendingComp && (
                        <div className="absolute left-0 top-8 z-50 w-64 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                            <div className="px-3 py-2 bg-indigo-50 dark:bg-indigo-900/30 border-b border-indigo-100 dark:border-indigo-800 flex items-center gap-2">
                                <button onClick={() => setPendingComp(null)} className="text-indigo-400 hover:text-indigo-600 text-xs">←</button>
                                <span className="text-[10px] font-bold uppercase tracking-widest text-indigo-500">{pendingComp.label} — Dimensión</span>
                            </div>
                            {DIMENSION_OPTIONS.map(opt => (
                                <button
                                    key={opt.value}
                                    onClick={() => commitAddItem(pendingComp, opt.value)}
                                    className="w-full text-left px-3 py-2.5 text-xs hover:bg-indigo-50 dark:hover:bg-slate-700 transition-colors"
                                >
                                    <span className="font-semibold text-slate-700 dark:text-slate-200">{opt.label}</span>
                                    <span className="ml-1 text-slate-400">(rol: {opt.requires})</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function TabEditor({ tab, tabIndex, onUpdate, onDelete, isOnly }) {
    const handleAddRow = () => {
        onUpdate({ ...tab, rows: [...tab.rows, { cols: 1, items: [] }] });
    };

    const handleUpdateRow = (rowIdx, updatedRow) => {
        const rows = tab.rows.map((r, i) => i === rowIdx ? updatedRow : r);
        onUpdate({ ...tab, rows });
    };

    const handleDeleteRow = (rowIdx) => {
        onUpdate({ ...tab, rows: tab.rows.filter((_, i) => i !== rowIdx) });
    };

    const handleMoveRow = (rowIdx, dir) => {
        const rows = [...tab.rows];
        const target = rowIdx + dir;
        if (target < 0 || target >= rows.length) return;
        [rows[rowIdx], rows[target]] = [rows[target], rows[rowIdx]];
        onUpdate({ ...tab, rows });
    };

    return (
        <div className="space-y-3">
            {/* Tab label */}
            <div className="flex items-center gap-3">
                <div className="flex-1">
                    <label className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">Nombre del Tab</label>
                    <input
                        className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                        value={tab.label}
                        onChange={e => onUpdate({ ...tab, label: e.target.value })}
                    />
                </div>
                <button
                    onClick={onDelete}
                    disabled={isOnly}
                    title={isOnly ? 'Debe haber al menos un tab' : 'Eliminar tab'}
                    className="mt-5 p-2 text-slate-300 dark:text-slate-600 hover:text-red-500 disabled:opacity-30 transition-colors"
                >
                    <Trash2 size={16} />
                </button>
            </div>

            {/* Rows */}
            <div className="space-y-2 pl-2 border-l-2 border-slate-100 dark:border-slate-800">
                {tab.rows.map((row, rowIdx) => (
                    <RowEditor
                        key={rowIdx}
                        row={row}
                        rowIndex={rowIdx}
                        onUpdate={(r) => handleUpdateRow(rowIdx, r)}
                        onDelete={() => handleDeleteRow(rowIdx)}
                        onMoveUp={() => handleMoveRow(rowIdx, -1)}
                        onMoveDown={() => handleMoveRow(rowIdx, 1)}
                        isFirst={rowIdx === 0}
                        isLast={rowIdx === tab.rows.length - 1}
                    />
                ))}
                <button
                    onClick={handleAddRow}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-dashed border-slate-200 dark:border-slate-700 text-xs text-slate-400 hover:border-indigo-400 hover:text-indigo-500 transition-all w-full justify-center"
                >
                    <Plus size={12} />
                    Agregar fila
                </button>
            </div>
        </div>
    );
}

// ── Modal principal ──────────────────────────────────────────────────────────

export default function LayoutEditorModal({ isOpen, onClose, indicator, onSave }) {
    const [layout, setLayout] = useState(DEFAULT_LAYOUT);
    const [activeTab, setActiveTab] = useState(0);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (!isOpen) return;
        const existing = indicator?.dashboard_layout;
        if (existing && existing.tabs?.length > 0) {
            setLayout(cloneLayout(existing));
        } else {
            setLayout(cloneLayout(DEFAULT_LAYOUT));
        }
        setActiveTab(0);
    }, [isOpen, indicator]);

    const handleAddTab = () => {
        const newTab = {
            id: `tab_${Date.now()}`,
            label: 'Nuevo Tab',
            rows: [{ cols: 1, items: [] }],
        };
        setLayout(prev => ({ ...prev, tabs: [...prev.tabs, newTab] }));
        setActiveTab(layout.tabs.length);
    };

    const handleUpdateTab = (tabIdx, updatedTab) => {
        setLayout(prev => ({
            ...prev,
            tabs: prev.tabs.map((t, i) => i === tabIdx ? updatedTab : t),
        }));
    };

    const handleDeleteTab = (tabIdx) => {
        setLayout(prev => {
            const tabs = prev.tabs.filter((_, i) => i !== tabIdx);
            return { ...prev, tabs };
        });
        setActiveTab(t => Math.min(t, layout.tabs.length - 2));
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${API_BASE_URL}/indicators/${indicator.id_indicator}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: indicator.name,
                    description: indicator.description,
                    type: indicator.type,
                    column_roles: indicator.column_roles,
                    role_labels: indicator.role_labels,
                    filter_dimensions: indicator.filter_dimensions,
                    temporal_config: indicator.temporal_config,
                    achievement_levels: indicator.achievement_levels,
                    dashboard_layout: layout,
                }),
            });
            if (!res.ok) throw new Error('Error al guardar el layout');
            toast.success('Layout guardado');
            onSave?.({ ...indicator, dashboard_layout: layout });
            onClose();
        } catch (err) {
            toast.error(err.message);
        } finally {
            setSaving(false);
        }
    };

    if (!isOpen) return null;

    const tabStyle = (active) =>
        `px-4 py-2 rounded-t-lg font-bold text-xs border-b-2 transition-all cursor-pointer whitespace-nowrap ${active
            ? 'text-indigo-600 border-indigo-600 bg-white dark:bg-slate-900 dark:text-indigo-400 dark:border-indigo-400'
            : 'text-slate-400 border-transparent hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300'
        }`;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

            {/* Modal */}
            <div className="relative z-10 bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 w-full max-w-3xl max-h-[90vh] flex flex-col">

                {/* Header */}
                <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100 dark:border-slate-800 shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-indigo-600 rounded-xl flex items-center justify-center text-white">
                            <LayoutGrid size={16} />
                        </div>
                        <div>
                            <h2 className="text-base font-black text-slate-800 dark:text-white">Editor de Layout</h2>
                            <p className="text-xs text-slate-400">{indicator?.name}</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-all">
                        <X size={20} />
                    </button>
                </div>

                {/* Tab bar */}
                <div className="flex items-end gap-1 px-6 pt-4 border-b border-slate-100 dark:border-slate-800 shrink-0 overflow-x-auto">
                    {layout.tabs.map((tab, idx) => (
                        <button key={tab.id || idx} className={tabStyle(activeTab === idx)} onClick={() => setActiveTab(idx)}>
                            {tab.label || `Tab ${idx + 1}`}
                        </button>
                    ))}
                    <button
                        onClick={handleAddTab}
                        className="mb-0.5 px-3 py-1.5 rounded-lg border border-dashed border-slate-200 dark:border-slate-700 text-xs text-slate-400 hover:border-indigo-400 hover:text-indigo-500 transition-all flex items-center gap-1 whitespace-nowrap"
                    >
                        <Plus size={12} />
                        Tab
                    </button>
                </div>

                {/* Editor content */}
                <div className="flex-1 overflow-y-auto px-6 py-5">
                    {layout.tabs[activeTab] && (
                        <TabEditor
                            tab={layout.tabs[activeTab]}
                            tabIndex={activeTab}
                            onUpdate={(t) => handleUpdateTab(activeTab, t)}
                            onDelete={() => handleDeleteTab(activeTab)}
                            isOnly={layout.tabs.length === 1}
                        />
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 dark:border-slate-800 shrink-0">
                    <button
                        onClick={() => setLayout(cloneLayout(DEFAULT_LAYOUT))}
                        className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors underline underline-offset-2"
                    >
                        Restaurar layout SIMCE por defecto
                    </button>
                    <div className="flex gap-3">
                        <button onClick={onClose} className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all">
                            Cancelar
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white px-5 py-2 rounded-xl font-bold text-sm shadow-lg shadow-indigo-100 dark:shadow-indigo-900/20 transition-all active:scale-95"
                        >
                            <Save size={15} />
                            {saving ? 'Guardando...' : 'Guardar Layout'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
