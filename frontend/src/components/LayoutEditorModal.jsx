import React, { useState, useEffect, useRef } from 'react';
import { X, Save, Plus, Trash2, LayoutGrid, ChevronUp, ChevronDown, GripVertical, Settings2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import { SIMCE_PRESET_LAYOUT } from '../tooling/dashboardRenderer';
import AddComponentModal from './add-component/AddComponentModal';
import { ALL_COMPONENTS, getFieldOptions } from './add-component/componentDefs';
export { CHART_COMPONENTS, CHART_GROUPS, TABLE_COMPONENTS, SPECIAL_COMPONENTS, ALL_COMPONENTS, getFieldOptions } from './add-component/componentDefs';

const COLS_OPTIONS = [1, 2, 3, 4];

// ── Helpers ──────────────────────────────────────────────────────────────────

function getComponentMeta(item) {
    return ALL_COMPONENTS.find(c => c.id === (item.component || item.type)) || null;
}

function itemLabel(item) {
    const meta = getComponentMeta(item);
    return meta ? meta.label : item.component || item.type;
}

function cloneLayout(layout) {
    return JSON.parse(JSON.stringify(layout));
}

// ── Context menu del badge ────────────────────────────────────────────────────

function ItemContextMenu({ item, position, onClose, onEdit, onRemove }) {
    const menuRef = useRef(null);

    useEffect(() => {
        const handler = (e) => {
            if (menuRef.current && !menuRef.current.contains(e.target)) onClose();
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [onClose]);

    const style = { position: 'fixed', top: position.y, left: position.x, zIndex: 9999 };

    return (
        <div
            ref={menuRef}
            style={style}
            className="w-52 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden py-1"
        >
            <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-700">
                <p className="text-[11px] font-bold text-slate-500 dark:text-slate-400 truncate">
                    {itemLabel(item)}
                </p>
            </div>

            <button
                onClick={() => { onEdit(); onClose(); }}
                className="w-full text-left px-3 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-indigo-50 dark:hover:bg-slate-700 flex items-center gap-2 transition-colors"
            >
                <Settings2 size={13} className="text-indigo-400" />
                Editar componente
            </button>

            <button
                onClick={() => { onRemove(); onClose(); }}
                className="w-full text-left px-3 py-2 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2 transition-colors"
            >
                <Trash2 size={13} />
                Eliminar
            </button>
        </div>
    );
}

// ── Badge de item en la fila ──────────────────────────────────────────────────

function ItemBadge({ item, onRemove, onUpdate, onDragStart, onDragOver, onDrop, onDragEnd, isDragOver, columnRoles, roleLabels, indicator }) {
    const meta = getComponentMeta(item);
    const [contextMenu, setContextMenu] = useState(null); // { x, y }
    const [editModalOpen, setEditModalOpen] = useState(false);

    const typeColor = {
        kpis:            'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-900/20 dark:border-amber-700 dark:text-amber-400',
        course_selector: 'bg-slate-50 border-slate-200 text-slate-600 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-400',
        table:           'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-900/20 dark:border-indigo-700 dark:text-indigo-400',
        chart:           'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/20 dark:border-emerald-700 dark:text-emerald-400',
    }[meta?.type || item.type] || 'bg-slate-50 border-slate-200 text-slate-600';

    const configFields = meta?.axisConfig?.map(a => item[a.key]).filter(Boolean) || [];

    const handleContextMenu = (e) => {
        e.preventDefault();
        setContextMenu({ x: e.clientX, y: e.clientY });
    };

    return (
        <>
            <div
                draggable
                onDragStart={onDragStart}
                onDragOver={onDragOver}
                onDrop={onDrop}
                onDragEnd={onDragEnd}
                onContextMenu={handleContextMenu}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-semibold transition-all ${typeColor} ${isDragOver ? 'ring-2 ring-indigo-400 ring-offset-1 scale-105' : ''}`}
            >
                <GripVertical size={12} className="opacity-40 cursor-grab active:cursor-grabbing shrink-0" />
                <span>{itemLabel(item)}</span>
                {configFields.length > 0 && (
                    <span className="opacity-60 font-normal font-mono text-[10px]">
                        [{configFields.join(', ')}]
                    </span>
                )}
                <button onClick={onRemove} className="ml-1 opacity-50 hover:opacity-100 transition-opacity">
                    <X size={12} />
                </button>
            </div>

            {contextMenu && (
                <ItemContextMenu
                    item={item}
                    position={contextMenu}
                    onClose={() => setContextMenu(null)}
                    onEdit={() => setEditModalOpen(true)}
                    onRemove={onRemove}
                />
            )}

            <AddComponentModal
                isOpen={editModalOpen}
                onClose={() => setEditModalOpen(false)}
                onConfirm={(compMeta, fields) => {
                    let updated;
                    if (compMeta.type === 'kpis' || compMeta.type === 'course_selector') {
                        updated = { type: compMeta.type };
                    } else {
                        updated = { type: compMeta.type, component: compMeta.id, ...fields };
                    }
                    onUpdate(updated);
                    // Modal closes itself via handleClose → onClose
                }}
                indicator={indicator}
                initialItem={item}
            />
        </>
    );
}

// ── Editor de fila ───────────────────────────────────────────────────────────

function RowEditor({ row, rowIndex, onUpdate, onDelete, onMoveUp, onMoveDown, isFirst, isLast, indicator }) {
    const [showAddModal, setShowAddModal] = useState(false);
    const [dragOverIdx, setDragOverIdx] = useState(null);
    const dragSrcIdx = useRef(null);

    const columnRoles = indicator?.column_roles || {};
    const roleLabels  = indicator?.role_labels  || {};

    const handleAddItem = (compMeta) => {
        commitAddItem(compMeta, {});
    };

    const commitAddItem = (compMeta, axisSelections) => {
        let newItem;
        if (compMeta.type === 'kpis' || compMeta.type === 'course_selector') {
            newItem = { type: compMeta.type };
        } else {
            newItem = {
                type: compMeta.type,
                component: compMeta.id,
                ...axisSelections,
            };
        }
        onUpdate({ ...row, items: [...row.items, newItem] });
        setShowAddModal(false);
    };

    const handleRemoveItem = (itemIdx) => {
        onUpdate({ ...row, items: row.items.filter((_, i) => i !== itemIdx) });
    };

    const handleUpdateItem = (itemIdx, updatedItem) => {
        onUpdate({ ...row, items: row.items.map((it, i) => i === itemIdx ? updatedItem : it) });
    };

    const handleColsChange = (cols) => {
        onUpdate({ ...row, cols: parseInt(cols) });
    };

    const handleDragStart = (idx) => {
        dragSrcIdx.current = idx;
    };

    const handleDragOver = (e, idx) => {
        e.preventDefault();
        setDragOverIdx(idx);
    };

    const handleDrop = (idx) => {
        const src = dragSrcIdx.current;
        if (src === null || src === idx) return;
        const items = [...row.items];
        const [moved] = items.splice(src, 1);
        items.splice(idx, 0, moved);
        onUpdate({ ...row, items });
        dragSrcIdx.current = null;
        setDragOverIdx(null);
    };

    const handleDragEnd = () => {
        dragSrcIdx.current = null;
        setDragOverIdx(null);
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
                    <ItemBadge
                        key={idx}
                        item={item}
                        onRemove={() => handleRemoveItem(idx)}
                        onUpdate={(updated) => handleUpdateItem(idx, updated)}
                        onDragStart={() => handleDragStart(idx)}
                        onDragOver={(e) => handleDragOver(e, idx)}
                        onDrop={() => handleDrop(idx)}
                        onDragEnd={handleDragEnd}
                        isDragOver={dragOverIdx === idx}
                        columnRoles={columnRoles}
                        roleLabels={roleLabels}
                        indicator={indicator}
                    />
                ))}

                {/* Add item button */}
                <button
                    onClick={() => setShowAddModal(true)}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-dashed border-slate-300 dark:border-slate-600 text-xs text-slate-400 hover:border-indigo-400 hover:text-indigo-500 transition-all"
                >
                    <Plus size={12} />
                    Agregar
                </button>

                <AddComponentModal
                    isOpen={showAddModal}
                    onClose={() => setShowAddModal(false)}
                    onConfirm={(compMeta, axisSelections) => commitAddItem(compMeta, axisSelections)}
                    indicator={indicator}
                />
            </div>
        </div>
    );
}

// ── Editor de tab ─────────────────────────────────────────────────────────────

function TabEditor({ tab, tabIndex, onUpdate, onDelete, isOnly, indicator }) {
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

            <div className="space-y-2 pl-2 border-l-2 border-slate-100 dark:border-slate-800">
                {tab.rows.map((row, rowIdx) => (
                    <RowEditor
                        key={rowIdx}
                        row={row}
                        rowIndex={rowIdx}
                        indicator={indicator}
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

// ── Modal principal ───────────────────────────────────────────────────────────

export default function LayoutEditorModal({ isOpen, onClose, indicator, onSave }) {
    const [layout, setLayout] = useState(SIMCE_PRESET_LAYOUT);
    const [activeTab, setActiveTab] = useState(0);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (!isOpen) return;
        const existing = indicator?.dashboard_layout;
        if (existing && existing.tabs?.length > 0) {
            setLayout(cloneLayout(existing));
        } else {
            setLayout(cloneLayout(SIMCE_PRESET_LAYOUT));
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
            <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

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
                            indicator={indicator}
                            onUpdate={(t) => handleUpdateTab(activeTab, t)}
                            onDelete={() => handleDeleteTab(activeTab)}
                            isOnly={layout.tabs.length === 1}
                        />
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 dark:border-slate-800 shrink-0">
                    <button
                        onClick={() => setLayout(cloneLayout(SIMCE_PRESET_LAYOUT))}
                        className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors underline underline-offset-2"
                    >
                        Cargar preset SIMCE
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
