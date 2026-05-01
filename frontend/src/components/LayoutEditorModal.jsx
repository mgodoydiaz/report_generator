import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, Save, Plus, Trash2, LayoutGrid, ChevronUp, ChevronDown, GripVertical, Settings2, FlaskConical, FileText, Download, BarChart2, Table2, Type, Minus, Image, Upload } from 'lucide-react';
import { validateExpression } from '../tooling/formulaEvaluator';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import { useAuth } from '../context/AuthContext';
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
        kpis:               'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-900/20 dark:border-amber-700 dark:text-amber-400',
        course_selector:    'bg-slate-50 border-slate-200 text-slate-600 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-400',
        subprueba_selector: 'bg-slate-50 border-slate-200 text-slate-600 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-400',
        table:              'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-900/20 dark:border-indigo-700 dark:text-indigo-400',
        chart:              'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/20 dark:border-emerald-700 dark:text-emerald-400',
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
                onDrop={(e) => { e.stopPropagation(); onDrop?.(e); }}
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
                    if (compMeta.type === 'kpis' || compMeta.type === 'course_selector' || compMeta.type === 'subprueba_selector') {
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

function RowEditor({ row, rowIndex, onUpdate, onDelete, onMoveUp, onMoveDown, isFirst, isLast, indicator, onItemDragStart, onItemDragEnd, onItemDrop }) {
    const [showAddModal, setShowAddModal] = useState(false);
    const [dragOverIdx, setDragOverIdx] = useState(null);        // hover sobre item → insertar antes
    const [dragOverRow, setDragOverRow] = useState(false);       // hover sobre el container de la fila → append

    const columnRoles = indicator?.column_roles || {};
    const roleLabels  = indicator?.role_labels  || {};

    const handleAddItem = (compMeta) => {
        commitAddItem(compMeta, {});
    };

    const commitAddItem = (compMeta, axisSelections) => {
        let newItem;
        if (compMeta.type === 'kpis' || compMeta.type === 'course_selector' || compMeta.type === 'subprueba_selector') {
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

    // Delegar el drag state al TabEditor (permite cross-row drops)
    const handleDragStart = (idx, e) => {
        // Firefox requiere setData para iniciar el drag
        try { e?.dataTransfer?.setData('text/plain', `${rowIndex}:${idx}`); } catch { /* ignore */ }
        if (e?.dataTransfer) e.dataTransfer.effectAllowed = 'move';
        onItemDragStart?.(rowIndex, idx);
    };

    const handleDragOver = (e, idx) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        setDragOverIdx(idx);
        setDragOverRow(false);
    };

    const handleDrop = (idx, e) => {
        e?.preventDefault?.();
        e?.stopPropagation?.();
        onItemDrop?.(rowIndex, idx);
        setDragOverIdx(null);
        setDragOverRow(false);
    };

    const handleDragEnd = () => {
        onItemDragEnd?.();
        setDragOverIdx(null);
        setDragOverRow(false);
    };

    // Drop sobre la fila (no sobre un item específico) → append al final
    const handleRowDragOver = (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        setDragOverRow(true);
    };

    const handleRowDragLeave = (e) => {
        // Sólo limpiar si el leave es del contenedor en sí, no de un hijo
        if (e.currentTarget === e.target) setDragOverRow(false);
    };

    const handleRowDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        onItemDrop?.(rowIndex, null); // null = append
        setDragOverIdx(null);
        setDragOverRow(false);
    };

    return (
        <div
            className={`border rounded-xl p-3 bg-slate-50/50 dark:bg-slate-800/30 space-y-2 transition-all ${
                dragOverRow
                    ? 'border-indigo-400 dark:border-indigo-500 ring-2 ring-indigo-200 dark:ring-indigo-900/40'
                    : 'border-slate-200 dark:border-slate-700'
            }`}
            onDragOver={handleRowDragOver}
            onDragLeave={handleRowDragLeave}
            onDrop={handleRowDrop}
        >
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
                        onDragStart={(e) => handleDragStart(idx, e)}
                        onDragOver={(e) => handleDragOver(e, idx)}
                        onDrop={(e) => handleDrop(idx, e)}
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
    // Drag & drop de items entre filas. El source guarda (rowIdx, itemIdx).
    // El drop resuelve tanto reorder interno como movimiento cross-row.
    const dragSrcRef = useRef(null);

    const handleItemDragStart = (rowIdx, itemIdx) => {
        dragSrcRef.current = { rowIdx, itemIdx };
    };

    const handleItemDragEnd = () => {
        dragSrcRef.current = null;
    };

    // insertBefore = null → append al final de la fila target
    const handleItemDrop = (targetRowIdx, insertBefore) => {
        const src = dragSrcRef.current;
        dragSrcRef.current = null;
        if (!src) return;

        const srcRow = tab.rows[src.rowIdx];
        if (!srcRow || src.itemIdx >= srcRow.items.length) return;

        // Clonar filas involucradas
        const rows = tab.rows.map((r, i) => (i === src.rowIdx || i === targetRowIdx) ? { ...r, items: [...r.items] } : r);
        const [moved] = rows[src.rowIdx].items.splice(src.itemIdx, 1);

        // Ajustar índice cuando el movimiento es dentro de la misma fila y
        // el target estaba después del source (el splice ya corrió los índices).
        let insertIdx = insertBefore == null ? rows[targetRowIdx].items.length : insertBefore;
        if (src.rowIdx === targetRowIdx && insertBefore != null && insertBefore > src.itemIdx) {
            insertIdx = insertBefore - 1;
        }

        rows[targetRowIdx].items.splice(insertIdx, 0, moved);
        onUpdate({ ...tab, rows });
    };

    const singleMetricWarnings = React.useMemo(() => {
        const warns = [];
        const hasSubpruebaSelector = (tab.rows || []).some(r => r.items.some(i => i.type === 'subprueba_selector'));
        for (const row of (tab.rows || [])) {
            for (const item of (row.items || [])) {
                const compId = item.component || item.type;
                const def = ALL_COMPONENTS.find(c => c.id === compId);
                if (!def?.requiresSingleMetricContext) continue;
                const filterHasHabilidad = item.filter && (
                    Object.prototype.hasOwnProperty.call(item.filter, '_habilidad') ||
                    Object.prototype.hasOwnProperty.call(item.filter, '_habilidad_2')
                );
                if (filterHasHabilidad || hasSubpruebaSelector) continue;
                warns.push(compId);
            }
        }
        return warns;
    }, [tab]);

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

            {singleMetricWarnings.length > 0 && (
                <div className="px-3 py-2 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-900/40 text-[11px] text-orange-700 dark:text-orange-300">
                    <span className="font-bold">Atención:</span> este tab contiene {singleMetricWarnings.length} gráfico{singleMetricWarnings.length === 1 ? '' : 's'} que mezclan escalas de distintas subpruebas ({[...new Set(singleMetricWarnings)].join(', ')}).
                    Agrega un <span className="font-mono">subprueba_selector</span> o un filtro <span className="font-mono">_habilidad</span> en los items.
                </div>
            )}

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
                        onItemDragStart={handleItemDragStart}
                        onItemDragEnd={handleItemDragEnd}
                        onItemDrop={handleItemDrop}
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

// ── Editor de campos derivados ────────────────────────────────────────────────

function DerivedColumnsEditor({ derivedColumns, onChange }) {
    const cols = derivedColumns || [];

    const add = () => onChange([...cols, { name: '', label: '', expression: '' }]);
    const remove = (i) => onChange(cols.filter((_, idx) => idx !== i));
    const update = (i, field, value) => {
        const next = cols.map((c, idx) => idx === i ? { ...c, [field]: value } : c);
        onChange(next);
    };

    return (
        <div className="space-y-4">
            <p className="text-xs text-slate-400 dark:text-slate-500">
                Define campos calculados a partir de los campos existentes. Estarán disponibles
                en todos los gráficos y tablas del dashboard como si fueran campos reales.
            </p>

            {cols.length === 0 && (
                <div className="text-center py-8 text-slate-400 text-xs border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-xl">
                    No hay campos derivados. Agrega uno para comenzar.
                </div>
            )}

            <div className="space-y-3">
                {cols.map((col, i) => {
                    const validation = col.expression ? validateExpression(col.expression) : null;
                    const hasError = validation && !validation.ok;
                    return (
                        <div key={i} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 p-3 space-y-2">
                            <div className="flex gap-2">
                                {/* Nombre interno */}
                                <div className="flex-1">
                                    <label className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">
                                        Nombre interno
                                    </label>
                                    <div className="flex items-center gap-1">
                                        <span className="text-xs text-slate-400 font-mono">_</span>
                                        <input
                                            type="text"
                                            value={col.name.replace(/^_/, '')}
                                            onChange={e => update(i, 'name', e.target.value.replace(/[^a-z0-9_]/gi, '_').toLowerCase())}
                                            placeholder="rendimiento_pct"
                                            className="flex-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                                        />
                                    </div>
                                </div>
                                {/* Etiqueta */}
                                <div className="flex-1">
                                    <label className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">
                                        Etiqueta
                                    </label>
                                    <input
                                        type="text"
                                        value={col.label}
                                        onChange={e => update(i, 'label', e.target.value)}
                                        placeholder="Rendimiento %"
                                        className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                                    />
                                </div>
                                <button
                                    onClick={() => remove(i)}
                                    className="mt-5 p-1.5 text-slate-300 dark:text-slate-600 hover:text-red-500 transition-colors"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                            {/* Expresión */}
                            <div>
                                <label className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">
                                    Expresión
                                </label>
                                <input
                                    type="text"
                                    value={col.expression}
                                    onChange={e => update(i, 'expression', e.target.value)}
                                    placeholder="correctas / total * 100"
                                    className={`w-full bg-white dark:bg-slate-800 border rounded-lg px-2.5 py-1.5 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-indigo-400 ${
                                        hasError
                                            ? 'border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-300'
                                            : 'border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200'
                                    }`}
                                />
                                {hasError && (
                                    <p className="text-[11px] text-rose-500 mt-1">{validation.error}</p>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            <button
                onClick={add}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-dashed border-slate-200 dark:border-slate-700 text-xs text-slate-400 hover:border-indigo-400 hover:text-indigo-500 transition-all w-full justify-center"
            >
                <Plus size={12} />
                Agregar campo derivado
            </button>

            <div className="rounded-xl bg-slate-100 dark:bg-slate-800/60 px-3 py-2.5 text-[11px] text-slate-500 dark:text-slate-400 space-y-0.5">
                <p className="font-semibold">Sintaxis</p>
                <p>Operadores: <code className="font-mono">+ − × ÷ ( )</code></p>
                <p>Campos: escribe el nombre sin <code className="font-mono">_</code> (ej. <code className="font-mono">correctas</code>)</p>
                <p>Funciones: <code className="font-mono">round(x)</code> · <code className="font-mono">abs(x)</code> · <code className="font-mono">min(x,y)</code> · <code className="font-mono">max(x,y)</code> · <code className="font-mono">sqrt(x)</code></p>
                <p>Igualdad: <code className="font-mono">eq(campo, "texto")</code> → 1 si coincide, 0 si no</p>
                <p>Ej. % Crítico+Alto: <code className="font-mono">eq(nivel_de_riesgo, "Crítico") + eq(nivel_de_riesgo, "Alto Riesgo")</code></p>
                <p>División por cero → muestra <code className="font-mono">—</code></p>
            </div>
        </div>
    );
}

// ── Editor de informe PDF ─────────────────────────────────────────────────────

function flattenDashboardItems(layout) {
    const items = [];
    for (const tab of (layout?.tabs || [])) {
        for (const row of (tab.rows || [])) {
            for (const item of (row.items || [])) {
                if (item.type === 'chart' || item.type === 'table') {
                    items.push({ ...item, _tabLabel: tab.label });
                }
            }
        }
    }
    return items;
}

const SECTION_ICONS = {
    cover:      <FileText size={13} className="text-indigo-400 shrink-0" />,
    chart:      <BarChart2 size={13} className="text-emerald-500 shrink-0" />,
    table:      <Table2 size={13} className="text-violet-500 shrink-0" />,
    text:       <Type size={13} className="text-amber-500 shrink-0" />,
    page_break: <Minus size={13} className="text-slate-400 shrink-0" />,
};

function PdfSectionCard({ sec, idx, total, onChange, onRemove, onMove, dashboardItems }) {
    return (
        <div className="border border-slate-200 dark:border-slate-700 rounded-xl p-3 bg-slate-50/50 dark:bg-slate-800/30 space-y-2">
            <div className="flex items-center gap-2">
                {SECTION_ICONS[sec.type]}
                <span className="text-xs font-bold text-slate-500 dark:text-slate-400 capitalize flex-1">
                    {sec.type === 'cover' ? 'Portada' :
                     sec.type === 'chart' ? 'Gráfico' :
                     sec.type === 'table' ? 'Tabla' :
                     sec.type === 'text'  ? 'Texto libre' : 'Salto de página'}
                </span>
                <button onClick={() => onMove(idx, -1)} disabled={idx === 0}
                    className="p-1 text-slate-300 hover:text-slate-500 disabled:opacity-30 transition-colors">
                    <ChevronUp size={13} />
                </button>
                <button onClick={() => onMove(idx, 1)} disabled={idx === total - 1}
                    className="p-1 text-slate-300 hover:text-slate-500 disabled:opacity-30 transition-colors">
                    <ChevronDown size={13} />
                </button>
                <button onClick={() => onRemove(idx)}
                    className="p-1 text-slate-300 hover:text-red-500 transition-colors">
                    <Trash2 size={13} />
                </button>
            </div>

            {sec.type === 'cover' && (
                <div className="space-y-1.5">
                    <input type="text" placeholder="Título" value={sec.title || ''}
                        onChange={e => onChange(idx, { ...sec, title: e.target.value })}
                        className="w-full text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
                    <input type="text" placeholder="Subtítulo" value={sec.subtitle || ''}
                        onChange={e => onChange(idx, { ...sec, subtitle: e.target.value })}
                        className="w-full text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
                </div>
            )}

            {(sec.type === 'chart' || sec.type === 'table') && (
                <div className="space-y-1.5">
                    <input type="text" placeholder="Título de sección" value={sec.heading || ''}
                        onChange={e => onChange(idx, { ...sec, heading: e.target.value })}
                        className="w-full text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
                    <select
                        value={dashboardItems.indexOf(sec.item) >= 0 ? dashboardItems.indexOf(sec.item) : ''}
                        onChange={e => {
                            const item = dashboardItems[parseInt(e.target.value)];
                            if (item) onChange(idx, { ...sec, item });
                        }}
                        className="w-full text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                    >
                        <option value="">— Selecciona componente del dashboard —</option>
                        {dashboardItems.map((it, i) => (
                            <option key={i} value={i}>
                                [{it._tabLabel}] {itemLabel(it)}
                            </option>
                        ))}
                    </select>
                    {sec.item && (
                        <p className="text-[10px] text-slate-400 font-mono px-1">
                            {sec.item.component || sec.item.type}
                        </p>
                    )}
                </div>
            )}

            {sec.type === 'text' && (
                <div className="space-y-1.5">
                    <input type="text" placeholder="Título de sección" value={sec.heading || ''}
                        onChange={e => onChange(idx, { ...sec, heading: e.target.value })}
                        className="w-full text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
                    <textarea placeholder="Contenido..." value={sec.body || ''}
                        rows={3}
                        onChange={e => onChange(idx, { ...sec, body: e.target.value })}
                        className="w-full text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-y" />
                </div>
            )}
        </div>
    );
}

// ── Branding Editor ───────────────────────────────────────────────────────────
// Exportado para ser reusado desde GenerateReportModal.

export function BrandingEditor({ branding = {}, onChange, orgId, fetchAuth }) {
    const [assets, setAssets] = useState([]);
    const [uploading, setUploading] = useState(false);
    const uploadRef = useRef(null);

    const fetchAssets = useCallback(async () => {
        if (!orgId) return;
        try {
            const res = await fetchAuth(`${API_BASE_URL}/organizations/${orgId}/assets?kind=logo`);
            if (res.ok) setAssets(await res.json());
        } catch { /* silent */ }
    }, [fetchAuth, orgId]);

    useEffect(() => { fetchAssets(); }, [fetchAssets]);

    const update = (patch) => onChange({ ...branding, ...patch });

    const handleUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);
        try {
            const fd = new FormData();
            fd.append('file', file);
            const res = await fetchAuth(
                `${API_BASE_URL}/organizations/${orgId}/assets?kind=logo&name=${encodeURIComponent(file.name)}`,
                { method: 'POST', body: fd }
            );
            if (!res.ok) throw new Error('Error al subir imagen');
            toast.success('Logo subido');
            await fetchAssets();
        } catch (err) {
            toast.error(err.message);
        } finally {
            setUploading(false);
            e.target.value = '';
        }
    };

    const AssetSelect = ({ label, value, onSelect }) => (
        <div className="flex-1 min-w-0">
            <label className="text-[10px] text-slate-500 dark:text-slate-400 font-medium mb-0.5 block">{label}</label>
            <select
                value={value || ''}
                onChange={e => onSelect(e.target.value ? Number(e.target.value) : null)}
                className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 px-2 py-1.5"
            >
                <option value="">— Sin logo —</option>
                {assets.map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                ))}
            </select>
        </div>
    );

    const centerHeader = branding.center_header || ['', '', ''];

    return (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 p-3 space-y-3">
            <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-600 dark:text-slate-300 flex items-center gap-1.5">
                    <Image size={12} /> Branding del informe
                </span>
                <div className="flex items-center gap-1.5">
                    <button
                        onClick={() => uploadRef.current?.click()}
                        disabled={uploading}
                        className="flex items-center gap-1 text-[10px] px-2 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 hover:bg-indigo-100 transition-colors border border-indigo-200 dark:border-indigo-800"
                    >
                        <Upload size={10} />
                        {uploading ? 'Subiendo…' : 'Subir logo'}
                    </button>
                    <input ref={uploadRef} type="file" accept="image/*" className="hidden" onChange={handleUpload} />
                </div>
            </div>

            {/* Logo selectors */}
            <div className="flex gap-2">
                <AssetSelect label="Logo izquierdo" value={branding.left_image_id}
                    onSelect={v => update({ left_image_id: v })} />
                <AssetSelect label="Logo derecho" value={branding.right_image_id}
                    onSelect={v => update({ right_image_id: v })} />
            </div>

            {/* Center header lines */}
            <div className="space-y-1">
                <label className="text-[10px] text-slate-500 dark:text-slate-400 font-medium block">Encabezado central (3 líneas)</label>
                {[0, 1, 2].map(i => (
                    <input
                        key={i}
                        type="text"
                        value={centerHeader[i] || ''}
                        placeholder={i === 0 ? 'Título principal' : i === 1 ? 'Subtítulo' : 'Fecha / descripción'}
                        onChange={e => {
                            const next = [...centerHeader];
                            next[i] = e.target.value;
                            update({ center_header: next });
                        }}
                        className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 px-2 py-1.5"
                    />
                ))}
            </div>

            {/* Footer */}
            <div className="flex gap-2 items-end">
                <div className="flex-1">
                    <label className="text-[10px] text-slate-500 dark:text-slate-400 font-medium mb-0.5 block">Pie izquierdo (autor)</label>
                    <input
                        type="text"
                        value={branding.left_footer || ''}
                        placeholder="Nombre del autor"
                        onChange={e => update({ left_footer: e.target.value })}
                        className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 px-2 py-1.5"
                    />
                </div>
                <label className="flex items-center gap-1.5 text-[10px] text-slate-600 dark:text-slate-300 pb-1.5 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={branding.show_page_number !== false}
                        onChange={e => update({ show_page_number: e.target.checked })}
                        className="rounded"
                    />
                    N° de página
                </label>
            </div>
        </div>
    );
}

// ── PDF Layout Editor ─────────────────────────────────────────────────────────

function PdfLayoutEditor({ pdfLayout, onChange, dashboardLayout, indicatorId, fetchAuth, orgId }) {
    const sections = pdfLayout?.sections || [];
    const branding = pdfLayout?.branding || {};
    const dashboardItems = flattenDashboardItems(dashboardLayout);
    const [downloading, setDownloading] = useState(false);

    const updateSections = (next) => onChange({ ...pdfLayout, sections: next });
    const updateBranding = (next) => onChange({ ...pdfLayout, branding: next });

    const addSection = (type) => {
        const base = { type };
        if (type === 'cover')      Object.assign(base, { title: '', subtitle: '' });
        if (type === 'text')       Object.assign(base, { heading: '', body: '' });
        if (type === 'chart')      Object.assign(base, { heading: '', item: null });
        if (type === 'table')      Object.assign(base, { heading: '', item: null });
        updateSections([...sections, base]);
    };

    const removeSection = (i) => updateSections(sections.filter((_, idx) => idx !== i));

    const moveSection = (i, dir) => {
        const next = [...sections];
        const target = i + dir;
        if (target < 0 || target >= next.length) return;
        [next[i], next[target]] = [next[target], next[i]];
        updateSections(next);
    };

    const updateSection = (i, sec) => updateSections(sections.map((s, idx) => idx === i ? sec : s));

    const handleDownload = async () => {
        setDownloading(true);
        try {
            const res = await fetchAuth(`${API_BASE_URL}/indicators/${indicatorId}/export-pdf`, { method: 'POST' });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'Error desconocido' }));
                throw new Error(err.detail || 'Error al generar PDF');
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `informe.pdf`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            toast.error(err.message);
        } finally {
            setDownloading(false);
        }
    };

    const ADD_OPTIONS = [
        { type: 'cover',      label: 'Portada',            icon: <FileText size={12} /> },
        { type: 'chart',      label: 'Gráfico del dashboard', icon: <BarChart2 size={12} /> },
        { type: 'table',      label: 'Tabla del dashboard',   icon: <Table2 size={12} /> },
        { type: 'text',       label: 'Texto libre',           icon: <Type size={12} /> },
        { type: 'page_break', label: 'Salto de página',       icon: <Minus size={12} /> },
    ];

    return (
        <div className="space-y-4">
            <p className="text-xs text-slate-400 dark:text-slate-500">
                Define las secciones del informe PDF. Los gráficos y tablas se toman del dashboard configurado.
            </p>

            <BrandingEditor
                branding={branding}
                onChange={updateBranding}
                orgId={orgId}
                fetchAuth={fetchAuth}
            />

            {sections.length === 0 && (
                <div className="text-center py-8 text-slate-400 text-xs border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-xl">
                    Sin secciones. Agrega una portada para comenzar.
                </div>
            )}

            <div className="space-y-2">
                {sections.map((sec, i) => (
                    <PdfSectionCard
                        key={i}
                        sec={sec}
                        idx={i}
                        total={sections.length}
                        onChange={updateSection}
                        onRemove={removeSection}
                        onMove={moveSection}
                        dashboardItems={dashboardItems}
                    />
                ))}
            </div>

            {/* Botones agregar */}
            <div className="flex flex-wrap gap-1.5">
                {ADD_OPTIONS.map(opt => (
                    <button
                        key={opt.type}
                        onClick={() => addSection(opt.type)}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-dashed border-slate-200 dark:border-slate-700 text-xs text-slate-500 hover:border-indigo-400 hover:text-indigo-600 transition-all"
                    >
                        {opt.icon}
                        {opt.label}
                    </button>
                ))}
            </div>

            {/* Botón descargar */}
            {sections.length > 0 && indicatorId && (
                <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                    <button
                        onClick={handleDownload}
                        disabled={downloading}
                        className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white text-xs font-bold shadow transition-all"
                    >
                        <Download size={13} />
                        {downloading ? 'Generando PDF...' : 'Descargar PDF de prueba'}
                    </button>
                    <p className="text-[10px] text-slate-400 mt-1">Guarda los cambios antes de descargar.</p>
                </div>
            )}
        </div>
    );
}

// ── Modal principal ───────────────────────────────────────────────────────────

export default function LayoutEditorModal({ isOpen, onClose, indicator, onSave }) {
    const { fetchAuth, user } = useAuth();
    const [layout, setLayout] = useState(SIMCE_PRESET_LAYOUT);
    const [activeTab, setActiveTab] = useState(0);
    const [saving, setSaving] = useState(false);
    const [mode, setMode] = useState('dashboard'); // 'dashboard' | 'derived' | 'pdf'
    const [derivedColumns, setDerivedColumns] = useState([]);
    const [pdfLayout, setPdfLayout] = useState({ sections: [] });
    const [pdfLayoutHistorico, setPdfLayoutHistorico] = useState({ sections: [] });
    const [pdfTipo, setPdfTipo] = useState('evaluacion'); // 'evaluacion' | 'historico'

    useEffect(() => {
        if (!isOpen) return;
        const existing = indicator?.dashboard_layout;
        if (existing && existing.tabs?.length > 0) {
            setLayout(cloneLayout(existing));
        } else {
            setLayout(cloneLayout(SIMCE_PRESET_LAYOUT));
        }
        setActiveTab(0);
        setMode('dashboard');
        setDerivedColumns(indicator?.derived_columns || []);
        setPdfLayout(indicator?.pdf_layout?.sections ? indicator.pdf_layout : { sections: [] });
        setPdfLayoutHistorico(indicator?.pdf_layout_historico?.sections ? indicator.pdf_layout_historico : { sections: [] });
        setPdfTipo('evaluacion');
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
            const res = await fetchAuth(`${API_BASE_URL}/indicators/${indicator.id_indicator}`, {
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
                    derived_columns: derivedColumns,
                    pdf_layout: pdfLayout,
                    pdf_layout_historico: pdfLayoutHistorico,
                }),
            });
            if (!res.ok) throw new Error('Error al guardar el layout');
            toast.success('Layout guardado');
            onSave?.({
                ...indicator,
                dashboard_layout: layout,
                derived_columns: derivedColumns,
                pdf_layout: pdfLayout,
                pdf_layout_historico: pdfLayoutHistorico,
            });
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

                {/* Mode switcher */}
                <div className="flex items-center gap-1 px-6 pt-3 pb-0 shrink-0">
                    <button
                        onClick={() => setMode('dashboard')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${mode === 'dashboard' ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
                    >
                        <LayoutGrid size={13} />
                        Dashboard
                    </button>
                    <button
                        onClick={() => setMode('derived')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${mode === 'derived' ? 'bg-violet-50 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
                    >
                        <FlaskConical size={13} />
                        Campos Derivados
                        {derivedColumns.length > 0 && (
                            <span className="ml-0.5 px-1.5 py-0.5 rounded-full bg-violet-100 dark:bg-violet-900/50 text-violet-600 dark:text-violet-400 text-[10px] font-bold">
                                {derivedColumns.length}
                            </span>
                        )}
                    </button>
                    <button
                        onClick={() => setMode('pdf')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${mode === 'pdf' ? 'bg-rose-50 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
                    >
                        <FileText size={13} />
                        Informe PDF
                        {((pdfLayout?.sections?.length || 0) + (pdfLayoutHistorico?.sections?.length || 0)) > 0 && (
                            <span className="ml-0.5 px-1.5 py-0.5 rounded-full bg-rose-100 dark:bg-rose-900/50 text-rose-600 dark:text-rose-400 text-[10px] font-bold">
                                {(pdfLayout?.sections?.length || 0) + (pdfLayoutHistorico?.sections?.length || 0)}
                            </span>
                        )}
                    </button>
                </div>

                {/* Sub-pestañas Por evaluación / Histórico (solo en mode='pdf') */}
                {mode === 'pdf' && (
                    <div className="flex items-center gap-1 px-6 pt-3 pb-0 shrink-0 border-b border-slate-100 dark:border-slate-800">
                        <button
                            onClick={() => setPdfTipo('evaluacion')}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-t-lg text-xs font-semibold transition-all border-b-2 ${pdfTipo === 'evaluacion'
                                ? 'text-rose-600 dark:text-rose-400 border-rose-500 bg-white dark:bg-slate-900'
                                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 border-transparent'
                            }`}
                        >
                            Por evaluación
                            {pdfLayout?.sections?.length > 0 && (
                                <span className="ml-0.5 px-1.5 py-0.5 rounded-full bg-rose-100 dark:bg-rose-900/50 text-rose-600 dark:text-rose-400 text-[10px] font-bold">
                                    {pdfLayout.sections.length}
                                </span>
                            )}
                        </button>
                        <button
                            onClick={() => setPdfTipo('historico')}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-t-lg text-xs font-semibold transition-all border-b-2 ${pdfTipo === 'historico'
                                ? 'text-rose-600 dark:text-rose-400 border-rose-500 bg-white dark:bg-slate-900'
                                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 border-transparent'
                            }`}
                        >
                            Histórico
                            {pdfLayoutHistorico?.sections?.length > 0 && (
                                <span className="ml-0.5 px-1.5 py-0.5 rounded-full bg-rose-100 dark:bg-rose-900/50 text-rose-600 dark:text-rose-400 text-[10px] font-bold">
                                    {pdfLayoutHistorico.sections.length}
                                </span>
                            )}
                        </button>
                    </div>
                )}

                {/* Tab bar (dashboard mode only) */}
                {mode === 'dashboard' && (
                    <div className="flex items-end gap-1 px-6 pt-3 border-b border-slate-100 dark:border-slate-800 shrink-0 overflow-x-auto">
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
                )}

                {/* Editor content */}
                <div className="flex-1 overflow-y-auto px-6 py-5">
                    {mode === 'dashboard' ? (
                        layout.tabs[activeTab] && (
                            <TabEditor
                                tab={layout.tabs[activeTab]}
                                tabIndex={activeTab}
                                indicator={indicator}
                                onUpdate={(t) => handleUpdateTab(activeTab, t)}
                                onDelete={() => handleDeleteTab(activeTab)}
                                isOnly={layout.tabs.length === 1}
                            />
                        )
                    ) : mode === 'derived' ? (
                        <DerivedColumnsEditor
                            derivedColumns={derivedColumns}
                            onChange={setDerivedColumns}
                        />
                    ) : (
                        <PdfLayoutEditor
                            key={pdfTipo /* fuerza re-mount al cambiar tipo, evita estado stale */}
                            pdfLayout={pdfTipo === 'historico' ? pdfLayoutHistorico : pdfLayout}
                            onChange={pdfTipo === 'historico' ? setPdfLayoutHistorico : setPdfLayout}
                            dashboardLayout={layout}
                            indicatorId={indicator?.id_indicator}
                            fetchAuth={fetchAuth}
                            orgId={user?.org_id}
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
