import React, { useState } from 'react';
import { ChevronRight, ExternalLink, X } from 'lucide-react';
import { getFieldOptions } from './componentDefs';
import PivotTableConfig from './PivotTableConfig';
import FlatTableConfig from './FlatTableConfig';

// ── Helper: convierte nombre de columna al fieldName normalizado ─────────────

function toFieldName(col) {
    return '_' + col.trim().toLowerCase()
        .replace(/\s+/g, '_')
        .replace(/[^a-z0-9_]/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_+|_+$/g, '');
}

// ── Picker de campo externo ───────────────────────────────────────────────────
// Dos fases: elegir métrica → elegir columna (valores o dimensiones).

function ExternalFieldPicker({ allMetrics, allDimensions, onPick, onCancel }) {
    const [phase, setPhase] = useState('metric'); // 'metric' | 'column'
    const [selectedMetric, setSelectedMetric] = useState(null);

    // Derivar columnas disponibles de la métrica seleccionada
    function getColumns(metric) {
        const cols = [];
        // Campos de valor
        const fields = metric.meta_json?.fields;
        if (Array.isArray(fields) && fields.length > 0) {
            fields.forEach(f => cols.push({ value: toFieldName(f.name), label: f.name, kind: 'valor', type: f.type }));
        } else {
            // Métrica simple: el nombre de la métrica es el campo de valor
            cols.push({ value: toFieldName(metric.name), label: metric.name, kind: 'valor', type: metric.data_type });
        }
        // Dimensiones asociadas
        const dimMap = Object.fromEntries((allDimensions || []).map(d => [d.id_dimension, d]));
        (metric.dimension_ids || []).forEach(did => {
            const dim = dimMap[did];
            if (dim) cols.push({ value: toFieldName(dim.name), label: dim.name, kind: 'dimensión', type: dim.data_type });
        });
        return cols;
    }

    if (phase === 'metric') {
        return (
            <div className="mt-3 border border-indigo-200 dark:border-indigo-800/50 rounded-xl overflow-hidden">
                <div className="flex items-center justify-between px-3.5 py-2 bg-indigo-50 dark:bg-indigo-900/20 border-b border-indigo-100 dark:border-indigo-800/40">
                    <span className="text-[11px] font-semibold text-indigo-700 dark:text-indigo-400 uppercase tracking-wider">Elegir métrica</span>
                    <button onClick={onCancel} className="text-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-300 p-0.5 rounded">
                        <X size={13} />
                    </button>
                </div>
                <div className="max-h-48 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800">
                    {allMetrics.length === 0 && (
                        <p className="px-3.5 py-3 text-xs text-slate-400 dark:text-slate-500">No hay métricas disponibles.</p>
                    )}
                    {allMetrics.map(m => (
                        <button
                            key={m.id_metric}
                            onClick={() => { setSelectedMetric(m); setPhase('column'); }}
                            className="w-full flex items-center justify-between px-3.5 py-2.5 text-left hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors"
                        >
                            <div>
                                <span className="text-xs font-medium text-slate-800 dark:text-slate-200">{m.name}</span>
                                {m.description && <span className="ml-2 text-[11px] text-slate-400">{m.description}</span>}
                            </div>
                            <ChevronRight size={13} className="text-slate-400 shrink-0" />
                        </button>
                    ))}
                </div>
            </div>
        );
    }

    // phase === 'column'
    const columns = getColumns(selectedMetric);
    return (
        <div className="mt-3 border border-indigo-200 dark:border-indigo-800/50 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-3.5 py-2 bg-indigo-50 dark:bg-indigo-900/20 border-b border-indigo-100 dark:border-indigo-800/40">
                <div className="flex items-center gap-1.5">
                    <button onClick={() => setPhase('metric')} className="text-[11px] text-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-300">Métricas</button>
                    <ChevronRight size={11} className="text-indigo-300" />
                    <span className="text-[11px] font-semibold text-indigo-700 dark:text-indigo-400 truncate max-w-32">{selectedMetric.name}</span>
                </div>
                <button onClick={onCancel} className="text-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-300 p-0.5 rounded">
                    <X size={13} />
                </button>
            </div>
            <div className="max-h-48 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800">
                {columns.length === 0 && (
                    <p className="px-3.5 py-3 text-xs text-slate-400 dark:text-slate-500">No hay columnas disponibles.</p>
                )}
                {columns.map(col => (
                    <button
                        key={col.value}
                        onClick={() => onPick(col.value, col.label, selectedMetric.name)}
                        className="w-full flex items-center justify-between px-3.5 py-2.5 text-left hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors"
                    >
                        <div className="flex items-center gap-2 min-w-0">
                            <span className={`shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide ${
                                col.kind === 'valor'
                                    ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400'
                                    : 'bg-violet-50 dark:bg-violet-900/20 text-violet-600 dark:text-violet-400'
                            }`}>{col.kind}</span>
                            <span className="text-xs font-medium text-slate-800 dark:text-slate-200 truncate">{col.label}</span>
                        </div>
                        <code className="text-[11px] font-mono text-slate-400 dark:text-slate-500 shrink-0 ml-2">{col.value}</code>
                    </button>
                ))}
            </div>
        </div>
    );
}

// ── Qué opciones visuales aplican por tipo de componente ─────────────────────
// Se mostrará solo si aplica al tipo seleccionado.

const VISUAL_OPTIONS_BY_TYPE = {
    chart: ['title', 'legendField', 'labelY', 'labelX', 'showLegend', 'showValues'],
    table: ['title'],
    kpis:  [],
    course_selector: [],
};

// Opciones específicas por componente que NO tienen labelX
const NO_LABEL_X = ['PieComposition', 'RadarProfile', 'BoxPlotByGroup'];
const NO_LABEL_Y = ['PieComposition', 'RadarProfile'];
const NO_SHOW_VALUES = ['BoxPlotByGroup', 'RadarProfile', 'PieComposition', 'TrendLine'];
// Componentes que soportan elegir columna de leyenda (tienen múltiples ejes de agrupación)
const HAS_LEGEND_FIELD = ['DoubleGroupedBar'];

function getVisualFields(comp) {
    const type = comp?.type;
    const id   = comp?.id;
    const base = VISUAL_OPTIONS_BY_TYPE[type] || [];
    return base.filter(f => {
        if (f === 'labelX'      && NO_LABEL_X.includes(id))       return false;
        if (f === 'labelY'      && NO_LABEL_Y.includes(id))       return false;
        if (f === 'showValues'  && NO_SHOW_VALUES.includes(id))   return false;
        if (f === 'legendField' && !HAS_LEGEND_FIELD.includes(id)) return false;
        return true;
    });
}

const VISUAL_FIELD_META = {
    title:       { label: 'Título del gráfico',     type: 'text',   placeholder: 'Ej: Logro por Curso' },
    legendField: { label: 'Columna de leyenda',      type: 'select', description: 'Elige qué campo define los colores de la leyenda' },
    labelY:      { label: 'Etiqueta eje Y',          type: 'text',   placeholder: 'Ej: % Logro' },
    labelX:      { label: 'Etiqueta eje X',          type: 'text',   placeholder: 'Ej: Curso' },
    showLegend:  { label: 'Mostrar leyenda',         type: 'toggle', default: true },
    showValues:  { label: 'Mostrar valores',         type: 'toggle', default: false },
};

// ── Formulario visual ─────────────────────────────────────────────────────────

function VisualOptionsForm({ comp, axisSelections, visualOptions, onVisualChange }) {
    const fields = getVisualFields(comp);
    if (fields.length === 0) {
        return (
            <div className="text-center py-8 text-slate-400 text-xs">
                No hay opciones visuales para este componente.
            </div>
        );
    }

    // Resumen de ejes configurados
    const axisEntries = Object.entries(axisSelections);

    // Opciones para el selector de columna de leyenda: campos no-valor de los ejes configurados
    const legendOptions = (comp?.axisConfig || [])
        .filter(a => a.key !== 'valueField')
        .map(a => ({ value: axisSelections[a.key], label: a.label.split('—').pop().trim() }))
        .filter(o => o.value);

    return (
        <div className="space-y-5">
            {/* Resumen de ejes ya configurados */}
            {axisEntries.length > 0 && (
                <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-700/50 px-4 py-3">
                    <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">
                        Ejes configurados
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                        {axisEntries.map(([key, val]) => (
                            <span key={key} className="inline-flex items-center gap-1 text-[11px] bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-800/40 px-2 py-1 rounded-lg">
                                <span className="opacity-70">{key}</span>
                                <code className="font-mono">{Array.isArray(val) ? val.join(', ') : val}</code>
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Opciones visuales */}
            <div className="space-y-3">
                {fields.map(fieldKey => {
                    const meta = VISUAL_FIELD_META[fieldKey];
                    if (!meta) return null;
                    const value = visualOptions[fieldKey] ?? (meta.type === 'toggle' ? meta.default : '');

                    if (meta.type === 'text') {
                        return (
                            <div key={fieldKey}>
                                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                                    {meta.label}
                                    <span className="ml-1 text-[10px] text-slate-400 font-normal">(opcional)</span>
                                </label>
                                <input
                                    type="text"
                                    value={value}
                                    onChange={e => onVisualChange(fieldKey, e.target.value)}
                                    placeholder={meta.placeholder}
                                    className="w-full bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-700 dark:text-slate-200 placeholder-slate-300 dark:placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-all"
                                />
                            </div>
                        );
                    }

                    if (meta.type === 'select' && fieldKey === 'legendField') {
                        if (legendOptions.length < 2) return null; // solo mostrar si hay más de un campo candidato
                        const defaultLegendField = legendOptions[legendOptions.length - 1]?.value;
                        const selected = value || defaultLegendField;
                        return (
                            <div key={fieldKey}>
                                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                                    {meta.label}
                                </label>
                                <p className="text-[11px] text-slate-400 dark:text-slate-500 mb-2">{meta.description}</p>
                                <div className="space-y-1.5">
                                    {legendOptions.map(opt => {
                                        const isActive = selected === opt.value;
                                        return (
                                            <button
                                                key={opt.value}
                                                onClick={() => onVisualChange('legendField', opt.value)}
                                                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl border text-left transition-all ${
                                                    isActive
                                                        ? 'border-indigo-400 dark:border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                                                        : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 hover:border-slate-300 dark:hover:border-slate-600'
                                                }`}
                                            >
                                                <div className={`w-4 h-4 min-w-4 rounded-full border-2 flex items-center justify-center transition-all ${
                                                    isActive ? 'border-indigo-600 bg-indigo-600' : 'border-slate-300 dark:border-slate-600'
                                                }`}>
                                                    {isActive && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                                                </div>
                                                <span className={`text-xs font-medium flex-1 ${isActive ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-700 dark:text-slate-300'}`}>
                                                    {opt.label}
                                                </span>
                                                <code className={`text-[11px] font-mono px-1.5 py-0.5 rounded-md ${
                                                    isActive
                                                        ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400'
                                                        : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
                                                }`}>
                                                    {opt.value}
                                                </code>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>
                        );
                    }

                    if (meta.type === 'toggle') {
                        return (
                            <div key={fieldKey} className="flex items-center justify-between px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40">
                                <span className="text-xs font-medium text-slate-700 dark:text-slate-300">{meta.label}</span>
                                <button
                                    type="button"
                                    onClick={() => onVisualChange(fieldKey, !value)}
                                    className={`relative w-9 h-5 rounded-full transition-colors ${value ? 'bg-indigo-600' : 'bg-slate-200 dark:bg-slate-700'}`}
                                >
                                    <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${value ? 'translate-x-4' : 'translate-x-0.5'}`} />
                                </button>
                            </div>
                        );
                    }

                    return null;
                })}
            </div>
        </div>
    );
}

// ── Componente principal ──────────────────────────────────────────────────────

export default function StepConfig({ comp, columnRoles, roleLabels, axisStepIdx, axisCompleted, selections, onSelect, onMultiToggle, multiPicked, visualOptions, onVisualChange, allMetrics, allDimensions, derivedColumns }) {
    const steps = comp?.axisConfig || [];
    const [showExternalPicker, setShowExternalPicker] = useState(false);

    // Resetear picker al cambiar de sub-paso
    React.useEffect(() => { setShowExternalPicker(false); }, [axisStepIdx]);

    // Mostrar formulario visual si los ejes están completos
    if (axisCompleted) {
        return (
            <VisualOptionsForm
                comp={comp}
                axisSelections={selections}
                visualOptions={visualOptions}
                onVisualChange={onVisualChange}
            />
        );
    }

    const currentStep = steps[axisStepIdx];
    if (!currentStep) return null;

    // Tabla pivote: UI especial — reemplaza el flow estándar de ejes
    if (currentStep.optionType === 'pivot') {
        return (
            <PivotTableConfig
                allMetrics={allMetrics || []}
                allDimensions={allDimensions || []}
                derivedColumns={derivedColumns || []}
                initial={selections[currentStep.key]}
                onConfirm={(cfg) => onSelect(currentStep.key, cfg)}
            />
        );
    }

    // Tabla plana con filtros: UI especial
    if (currentStep.optionType === 'flatTable') {
        return (
            <FlatTableConfig
                allMetrics={allMetrics || []}
                allDimensions={allDimensions || []}
                derivedColumns={derivedColumns || []}
                initial={selections[currentStep.key]}
                onConfirm={(cfg) => onSelect(currentStep.key, cfg)}
            />
        );
    }

    const options = getFieldOptions(currentStep.optionType, columnRoles, roleLabels);
    const isMulti = currentStep.optionType === 'value' && options.length > 1;
    const total = steps.length;

    // Detectar si la selección actual es un campo externo (no está en las opciones del indicador)
    const currentValue = isMulti ? null : selections[currentStep.key];
    const isExternalValue = currentValue && !options.some(o => o.value === currentValue);

    return (
        <div className="space-y-5">
            {/* Barra de progreso de sub-pasos */}
            {total > 1 && (
                <div className="flex items-center gap-1.5">
                    {steps.map((_, i) => (
                        <div
                            key={i}
                            className={`h-1 flex-1 rounded-full transition-all ${
                                i <= axisStepIdx ? 'bg-indigo-500' : 'bg-slate-200 dark:bg-slate-700'
                            }`}
                        />
                    ))}
                    <span className="text-[11px] text-slate-400 dark:text-slate-500 ml-2 whitespace-nowrap">
                        {axisStepIdx + 1} / {total}
                    </span>
                </div>
            )}

            {/* Mini-card del componente seleccionado */}
            <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-700/50 px-4 py-3">
                <p className="text-xs font-medium text-slate-700 dark:text-slate-300">{comp?.label}</p>
                <p className="text-[11px] text-slate-400 dark:text-slate-500">{currentStep.label}</p>
            </div>

            {/* Pregunta actual */}
            <div>
                <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 mb-0.5">{currentStep.label}</p>

                {options.length === 0 ? (
                    <div className="mt-3 space-y-1.5">
                        <div className="rounded-xl border border-amber-200 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-900/10 px-4 py-3">
                            <p className="text-xs text-amber-700 dark:text-amber-400">
                                No hay roles configurados para este campo en el indicador.
                            </p>
                            {!showExternalPicker && !isExternalValue && (
                                <button
                                    onClick={() => setShowExternalPicker(true)}
                                    className="mt-2 flex items-center gap-1 text-[11px] font-medium text-amber-700 dark:text-amber-400 hover:text-amber-900 dark:hover:text-amber-200 transition-colors"
                                >
                                    <ExternalLink size={12} />
                                    Usar campo de otra métrica...
                                </button>
                            )}
                        </div>
                        {/* Campo externo ya seleccionado */}
                        {isExternalValue && !showExternalPicker && (
                            <button
                                onClick={() => setShowExternalPicker(true)}
                                className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl border text-left transition-all border-violet-400 dark:border-violet-500 bg-violet-50 dark:bg-violet-900/20"
                            >
                                <div className="w-4 h-4 min-w-4 rounded-full border-2 border-violet-600 bg-violet-600 flex items-center justify-center">
                                    <div className="w-1.5 h-1.5 rounded-full bg-white" />
                                </div>
                                <span className="text-xs font-medium flex-1 text-violet-700 dark:text-violet-300">Campo externo</span>
                                <code className="text-[11px] font-mono px-1.5 py-0.5 rounded-md bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400">
                                    {currentValue}
                                </code>
                            </button>
                        )}
                        {isExternalValue && !showExternalPicker && (
                            <button
                                onClick={() => setShowExternalPicker(true)}
                                className="w-full flex items-center gap-2 px-3.5 py-2 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:border-indigo-300 dark:hover:border-indigo-700 hover:text-indigo-600 dark:hover:text-indigo-400 transition-all text-xs"
                            >
                                <ExternalLink size={13} />
                                Cambiar campo externo...
                            </button>
                        )}
                    </div>
                ) : isMulti ? (
                    <div className="mt-3 space-y-2">
                        <p className="text-[11px] text-slate-400 dark:text-slate-500 mb-3">
                            Selecciona uno o más — se mostrará un toggle en el gráfico
                        </p>
                        {options.map(opt => (
                            <label
                                key={opt.value}
                                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl border cursor-pointer transition-all ${
                                    multiPicked.includes(opt.value)
                                        ? 'border-indigo-400 dark:border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                                        : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 hover:border-slate-300 dark:hover:border-slate-600'
                                }`}
                            >
                                <div className={`w-4 h-4 min-w-4 rounded border-2 flex items-center justify-center transition-all ${
                                    multiPicked.includes(opt.value)
                                        ? 'border-indigo-600 bg-indigo-600'
                                        : 'border-slate-300 dark:border-slate-600'
                                }`}>
                                    {multiPicked.includes(opt.value) && (
                                        <svg width="9" height="9" viewBox="0 0 9 9" fill="none">
                                            <path d="M1.5 4.5L3.5 6.5L7.5 2.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                        </svg>
                                    )}
                                </div>
                                <input type="checkbox" className="sr-only" checked={multiPicked.includes(opt.value)} onChange={() => onMultiToggle(opt.value)} />
                                <span className={`text-xs font-medium flex-1 ${multiPicked.includes(opt.value) ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-700 dark:text-slate-300'}`}>
                                    {opt.label}
                                </span>
                                <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mr-1">recomendado</span>
                                <code className={`text-[11px] font-mono px-1.5 py-0.5 rounded-md transition-colors ${
                                    multiPicked.includes(opt.value)
                                        ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400'
                                        : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
                                }`}>
                                    {opt.value}
                                </code>
                            </label>
                        ))}

                        {/* Campos externos ya seleccionados (no están en options del indicador) */}
                        {multiPicked.filter(v => !options.some(o => o.value === v)).map(extVal => (
                            <label
                                key={extVal}
                                className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl border cursor-pointer transition-all border-violet-400 dark:border-violet-500 bg-violet-50 dark:bg-violet-900/20"
                            >
                                <div className="w-4 h-4 min-w-4 rounded border-2 border-violet-600 bg-violet-600 flex items-center justify-center">
                                    <svg width="9" height="9" viewBox="0 0 9 9" fill="none">
                                        <path d="M1.5 4.5L3.5 6.5L7.5 2.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                    </svg>
                                </div>
                                <input type="checkbox" className="sr-only" checked onChange={() => onMultiToggle(extVal)} />
                                <span className="text-xs font-medium flex-1 text-violet-700 dark:text-violet-300">Campo externo</span>
                                <code className="text-[11px] font-mono px-1.5 py-0.5 rounded-md bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400">{extVal}</code>
                            </label>
                        ))}

                        {/* Botón para agregar campo externo como opción adicional al multi-select */}
                        {!showExternalPicker && (
                            <button
                                onClick={() => setShowExternalPicker(true)}
                                className="w-full flex items-center gap-2 px-3.5 py-2 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:border-indigo-300 dark:hover:border-indigo-700 hover:text-indigo-600 dark:hover:text-indigo-400 transition-all text-xs"
                            >
                                <ExternalLink size={13} />
                                Agregar campo de otra métrica...
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="mt-3 space-y-1.5">
                        {options.map(opt => {
                            const isSelected = selections[currentStep.key] === opt.value;
                            return (
                                <button
                                    key={opt.value}
                                    onClick={() => { onSelect(currentStep.key, opt.value); setShowExternalPicker(false); }}
                                    className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl border text-left transition-all ${
                                        isSelected
                                            ? 'border-indigo-400 dark:border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                                            : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 hover:border-slate-300 dark:hover:border-slate-600'
                                    }`}
                                >
                                    <div className={`w-4 h-4 min-w-4 rounded-full border-2 flex items-center justify-center transition-all ${
                                        isSelected ? 'border-indigo-600 bg-indigo-600' : 'border-slate-300 dark:border-slate-600'
                                    }`}>
                                        {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                                    </div>
                                    <span className={`text-xs font-medium flex-1 ${isSelected ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-700 dark:text-slate-300'}`}>
                                        {opt.label}
                                    </span>
                                    <span className="text-[10px] font-semibold text-slate-300 dark:text-slate-600 uppercase tracking-wide mr-1">recomendado</span>
                                    <code className={`text-[11px] font-mono px-1.5 py-0.5 rounded-md transition-colors ${
                                        isSelected
                                            ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400'
                                            : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
                                    }`}>
                                        {opt.value}
                                    </code>
                                </button>
                            );
                        })}

                        {/* Campo externo ya seleccionado */}
                        {isExternalValue && !showExternalPicker && (
                            <button
                                onClick={() => setShowExternalPicker(true)}
                                className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl border text-left transition-all border-violet-400 dark:border-violet-500 bg-violet-50 dark:bg-violet-900/20"
                            >
                                <div className="w-4 h-4 min-w-4 rounded-full border-2 border-violet-600 bg-violet-600 flex items-center justify-center">
                                    <div className="w-1.5 h-1.5 rounded-full bg-white" />
                                </div>
                                <span className="text-xs font-medium flex-1 text-violet-700 dark:text-violet-300">
                                    Campo externo
                                </span>
                                <code className="text-[11px] font-mono px-1.5 py-0.5 rounded-md bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400">
                                    {currentValue}
                                </code>
                            </button>
                        )}

                        {/* Botón para abrir picker */}
                        {!showExternalPicker && !isExternalValue && (
                            <button
                                onClick={() => setShowExternalPicker(true)}
                                className="w-full flex items-center gap-2 px-3.5 py-2 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:border-indigo-300 dark:hover:border-indigo-700 hover:text-indigo-600 dark:hover:text-indigo-400 transition-all text-xs"
                            >
                                <ExternalLink size={13} />
                                Usar campo de otra métrica...
                            </button>
                        )}
                    </div>
                )}

                {/* Picker de campo externo */}
                {showExternalPicker && (
                    <ExternalFieldPicker
                        allMetrics={allMetrics || []}
                        allDimensions={allDimensions || []}
                        onPick={(fieldName) => {
                            if (isMulti) {
                                if (!multiPicked.includes(fieldName)) onMultiToggle(fieldName);
                            } else {
                                onSelect(currentStep.key, fieldName);
                            }
                            setShowExternalPicker(false);
                        }}
                        onCancel={() => setShowExternalPicker(false)}
                    />
                )}
            </div>

            {/* Resumen de ejes ya seleccionados */}
            {Object.keys(selections).length > 0 && axisStepIdx > 0 && (
                <div className="border-t border-slate-100 dark:border-slate-800 pt-4">
                    <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">
                        Configurado hasta ahora
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                        {steps.slice(0, axisStepIdx).map(s => {
                            const val = selections[s.key];
                            if (!val) return null;
                            const displayVal = Array.isArray(val) ? val.join(', ') : val;
                            return (
                                <span key={s.key} className="inline-flex items-center gap-1 text-[11px] bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-800/40 px-2 py-1 rounded-lg">
                                    <span className="text-indigo-400 dark:text-indigo-600">{s.label.split('—')[0].trim()}</span>
                                    <code className="font-mono opacity-80">{displayVal}</code>
                                </span>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}
