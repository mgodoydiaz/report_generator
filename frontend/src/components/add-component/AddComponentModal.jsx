import React, { useState, useEffect } from 'react';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import StepGallery from './StepGallery';
import StepConfig from './StepConfig';
import StepPreview from './StepPreview';
import { ALL_COMPONENTS } from './componentDefs';
import { API_BASE_URL } from '../../constants';

const STEP_TITLES = {
    1: { title: 'Elige un componente',      sub: 'Selecciona el tipo de visualización para el dashboard' },
    2: { title: 'Configura los parámetros', sub: 'Define los campos de datos que usará este componente' },
    3: { title: 'Vista previa',             sub: 'Revisa el componente antes de agregarlo al dashboard' },
};

const VISUAL_KEYS = ['title', 'legendField', 'labelY', 'labelX', 'showLegend', 'showValues'];

// Extract axis selections vs visual options from a saved item
function splitItemFields(item, compMeta) {
    const axisKeys = new Set((compMeta?.axisConfig || []).map(a => a.key));
    const axis = {};
    const visual = {};
    for (const [k, v] of Object.entries(item || {})) {
        if (['type', 'component', 'requires'].includes(k)) continue;
        if (VISUAL_KEYS.includes(k)) visual[k] = v;
        else if (axisKeys.has(k)) axis[k] = v;
    }
    return { axis, visual };
}

export default function AddComponentModal({ isOpen, onClose, onConfirm, indicator, initialItem }) {
    const isEditMode = !!initialItem;

    // Métricas y dimensiones del indicador (para el picker de campo externo)
    // Solo se cargan las métricas referenciadas en column_roles del indicador.
    const [indicatorMetrics, setIndicatorMetrics] = useState([]);
    const [allDimensions, setAllDimensions] = useState([]);
    useEffect(() => {
        if (!isOpen) return;
        // Extraer metric_ids únicos de column_roles del indicador
        const columnRoles = indicator?.column_roles || {};
        const metricIds = [...new Set(
            Object.values(columnRoles).flat().map(e => e.metric_id).filter(Boolean)
        )];
        Promise.all([
            fetch(`${API_BASE_URL}/metrics`).then(r => r.ok ? r.json() : []),
            fetch(`${API_BASE_URL}/dimensions`).then(r => r.ok ? r.json() : []),
        ]).then(([metrics, dims]) => {
            setIndicatorMetrics(metrics.filter(m => metricIds.includes(m.id_metric)));
            setAllDimensions(dims);
        }).catch(() => {});
    }, [isOpen]);

    // Derive initial comp from initialItem
    const getInitialComp = () => {
        if (!initialItem) return null;
        return ALL_COMPONENTS.find(c => c.id === (initialItem.component || initialItem.type)) || null;
    };

    const [step, setStep] = useState(() => isEditMode ? 2 : 1);
    const [selectedComp, setSelectedComp] = useState(getInitialComp);

    // Estado paso 2 — ejes
    const [axisSelections, setAxisSelections] = useState(() => {
        if (!initialItem) return {};
        const comp = ALL_COMPONENTS.find(c => c.id === (initialItem.component || initialItem.type));
        return splitItemFields(initialItem, comp).axis;
    });
    const [axisStepIdx, setAxisStepIdx] = useState(0);
    const [multiPicked, setMultiPicked] = useState([]);
    const [axisCompleted, setAxisCompleted] = useState(() => isEditMode);
    // Opciones visuales (título, etiquetas, leyenda)
    const [visualOptions, setVisualOptions] = useState(() => {
        if (!initialItem) return {};
        const comp = ALL_COMPONENTS.find(c => c.id === (initialItem.component || initialItem.type));
        return splitItemFields(initialItem, comp).visual;
    });

    // Reset when modal opens
    useEffect(() => {
        if (!isOpen) return;
        if (isEditMode) {
            const comp = ALL_COMPONENTS.find(c => c.id === (initialItem.component || initialItem.type));
            const { axis, visual } = splitItemFields(initialItem, comp);
            setSelectedComp(comp);
            setAxisSelections(axis);
            setVisualOptions(visual);
            setAxisCompleted(true);
            setStep(2);
        } else {
            setStep(1);
            setSelectedComp(null);
            setAxisSelections({});
            setAxisStepIdx(0);
            setMultiPicked([]);
            setAxisCompleted(false);
            setVisualOptions({});
        }
    }, [isOpen]);

    if (!isOpen) return null;

    const columnRoles = indicator?.column_roles || {};
    const roleLabels  = indicator?.role_labels  || {};

    const axisSteps = selectedComp?.axisConfig || [];
    const hasAxisConfig = axisSteps.length > 0;
    // Siempre 3 pasos: galería → config (si aplica, se omite si no hay ejes) → preview
    const totalSteps = 3;

    const currentAxisStep = axisSteps[axisStepIdx];
    const isLastAxisStep = axisStepIdx >= axisSteps.length - 1;

    // ── Habilitación del botón Siguiente ─────────────────────────────────────

    const canNext = (() => {
        if (step === 1) return !!selectedComp;
        if (step === 2) {
            if (axisCompleted) return true; // formulario visual: siempre puede avanzar
            if (!currentAxisStep) return true;
            const { optionType, key } = currentAxisStep;
            if (optionType === 'value') return multiPicked.length > 0;
            return !!axisSelections[key];
        }
        return true;
    })();

    // ── Avanzar sub-pasos de ejes ─────────────────────────────────────────────

    const commitAxisSubStep = () => {
        if (!currentAxisStep) {
            setAxisCompleted(true);
            return;
        }
        const { optionType, key } = currentAxisStep;
        const isMulti = optionType === 'value';
        const value = isMulti
            ? (multiPicked.length === 1 ? multiPicked[0] : multiPicked)
            : axisSelections[key];

        const nextSelections = { ...axisSelections, [key]: value };
        setAxisSelections(nextSelections);

        if (!isLastAxisStep) {
            setAxisStepIdx(i => i + 1);
            setMultiPicked([]);
        } else {
            // Último eje completado → mostrar formulario visual
            setAxisCompleted(true);
        }
    };

    // ── Navegación principal ──────────────────────────────────────────────────

    const handleNext = () => {
        if (step === 1) {
            if (hasAxisConfig) {
                setAxisStepIdx(0);
                setAxisSelections({});
                setMultiPicked([]);
                setAxisCompleted(false);
                setVisualOptions({});
                setStep(2);
            } else {
                setAxisCompleted(true);
                setVisualOptions({});
                setStep(2); // formulario visual sin ejes
            }
            return;
        }
        if (step === 2) {
            if (axisCompleted) {
                setStep(3);
            } else {
                commitAxisSubStep();
            }
            return;
        }
        if (step === 3) {
            onConfirm(selectedComp, { ...axisSelections, ...visualOptions });
            handleClose();
        }
    };

    const handleBack = () => {
        if (step === 2) {
            if (axisCompleted) {
                // Desde formulario visual: volver al último eje (o al paso 1 si no había ejes)
                setAxisCompleted(false);
                if (!hasAxisConfig && !isEditMode) setStep(1);
            } else if (axisStepIdx > 0) {
                setAxisStepIdx(i => i - 1);
                setMultiPicked([]);
            } else if (!isEditMode) {
                setStep(1);
            }
        } else if (step === 3) {
            setStep(2);
            setAxisCompleted(true); // volver al formulario visual
        }
    };

    const handleClose = () => {
        setStep(1);
        setSelectedComp(null);
        setAxisSelections({});
        setAxisStepIdx(0);
        setMultiPicked([]);
        setAxisCompleted(false);
        setVisualOptions({});
        onClose();
    };

    const handleSelectComp = (comp) => {
        setSelectedComp(comp);
        setAxisSelections({});
        setAxisStepIdx(0);
        setMultiPicked([]);
        setAxisCompleted(false);
        setVisualOptions({});
    };

    // ── Labels del footer ─────────────────────────────────────────────────────

    const isLastStep = step === 3;
    const nextLabel = isLastStep
        ? (isEditMode ? 'Guardar cambios' : 'Agregar al dashboard')
        : 'Siguiente';

    // En paso 2 con ejes completos, cambiar subtítulo del header
    const stepTitleOverride = (step === 2 && axisCompleted)
        ? { title: isEditMode ? 'Editar componente' : 'Opciones visuales', sub: 'Personaliza cómo se verá el componente (opcional)' }
        : null;
    const { title, sub } = stepTitleOverride || STEP_TITLES[step] || {};

    // Sub-paso visible en el header (solo en paso 2 con múltiples ejes)
    const showSubStep = step === 2 && axisSteps.length > 1;

    return (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700/60 w-full max-w-215 max-h-[90vh] flex flex-col overflow-hidden shadow-2xl shadow-slate-900/20">

                {/* Header */}
                <div className="px-6 pt-5 pb-4 border-b border-slate-100 dark:border-slate-800 shrink-0">
                    <div className="flex items-start justify-between">
                        <div>
                            <div className="flex items-center gap-2 mb-0.5">
                                <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest">
                                    Paso {step} / {totalSteps}
                                    {showSubStep && (
                                        <span className="ml-2 text-indigo-400">
                                            · campo {axisStepIdx + 1} de {axisSteps.length}
                                        </span>
                                    )}
                                </span>
                            </div>
                            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{sub}</p>
                        </div>
                        <button
                            onClick={handleClose}
                            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                        >
                            <X size={16} />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto px-6 py-5">
                    {step === 1 && (
                        <StepGallery selectedComp={selectedComp} onSelect={handleSelectComp} />
                    )}
                    {step === 2 && (
                        <StepConfig
                            comp={selectedComp}
                            columnRoles={columnRoles}
                            roleLabels={roleLabels}
                            axisStepIdx={axisStepIdx}
                            axisCompleted={axisCompleted}
                            selections={axisSelections}
                            onSelect={(key, value) => setAxisSelections(prev => ({ ...prev, [key]: value }))}
                            multiPicked={multiPicked}
                            onMultiToggle={(value) => setMultiPicked(prev =>
                                prev.includes(value) ? prev.filter(v => v !== value) : [...prev, value]
                            )}
                            visualOptions={visualOptions}
                            onVisualChange={(key, value) => setVisualOptions(prev => ({ ...prev, [key]: value }))}
                            allMetrics={indicatorMetrics}
                            allDimensions={allDimensions}
                            derivedColumns={indicator?.derived_columns || []}
                        />
                    )}
                    {step === 3 && (
                        <StepPreview
                            comp={selectedComp}
                            axisSelections={axisSelections}
                            indicator={indicator}
                        />
                    )}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between shrink-0 bg-slate-50/60 dark:bg-slate-900/60">
                    <button
                        onClick={handleBack}
                        className={`flex items-center gap-1 text-xs font-medium px-3.5 py-2 rounded-xl border transition-all
                            border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400
                            hover:bg-white dark:hover:bg-slate-800
                            ${step === 1 ? 'invisible' : ''}`}
                    >
                        <ChevronLeft size={13} />
                        Atrás
                    </button>

                    <div className="flex items-center gap-2">
                        {/* Dots de progreso */}
                        <div className="flex items-center gap-1.5 mr-3">
                            {Array.from({ length: totalSteps }, (_, i) => (
                                <div
                                    key={i}
                                    className={`rounded-full transition-all ${
                                        i + 1 === step
                                            ? 'w-4 h-1.5 bg-indigo-600'
                                            : i + 1 < step
                                            ? 'w-1.5 h-1.5 bg-indigo-400'
                                            : 'w-1.5 h-1.5 bg-slate-200 dark:bg-slate-700'
                                    }`}
                                />
                            ))}
                        </div>

                        <button
                            onClick={handleClose}
                            className="text-xs font-medium px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-white dark:hover:bg-slate-800 transition-all"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleNext}
                            disabled={!canNext}
                            className={`flex items-center gap-1 text-xs font-semibold px-4 py-2 rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed
                                ${isLastStep
                                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                                    : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                                }`}
                        >
                            {nextLabel}
                            {!isLastStep && <ChevronRight size={13} />}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
