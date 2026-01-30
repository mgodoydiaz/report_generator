import React, { useState, useEffect } from 'react';
import {
    X, Database, Settings, Code, PlusCircle, Trash, Trash2, Plus, ChevronUp, ChevronDown
} from 'lucide-react';

// Opciones para el selector de pasos del pipeline
const STEP_OPTIONS = [
    "InitRun",
    "LoadConfig",
    "DiscoverInputs",
    "RequestUserFiles",
    "RunExcelETL",
    "EnrichWithContext",
    "ExportConsolidatedExcel",
    "GenerateGraphics",
    "GenerateTables",
    "RenderReport",
    "GenerateDocxReport",
    "DeleteTempFiles"
];

// Opciones para Entrada y Salida
const FORMAT_OPTIONS = ["EXCEL", "PDF", "DOC", "IMG"];

/**
 * Componente NewPipelineDrawer
 * @param {boolean} isOpen - Controla la visibilidad del panel
 * @param {function} onClose - Función para cerrar el panel
 * @param {object} initialData - Datos iniciales para editar (opcional)
 * @param {string} title - Título del panel
 * @param {function} onSave - Función para procesar los datos al guardar
 */
const NewPipelineDrawer = ({ isOpen, onClose, initialData = null, title = "Configurar Nuevo Proceso", onSave }) => {
    const [formData, setFormData] = useState({
        name: "",
        description: "",
        input: "EXCEL",
        output: "XLSX",
        context: [
            { key: "base_dir", value: "./backend/tests" }
        ],
        pipeline: [{ step: "", params: "" }]
    });

    // Cargar datos iniciales al abrir o cambiar initialData
    useEffect(() => {
        if (isOpen) {
            if (initialData) {
                // Transformar contexto de objeto a array de pairs
                const contextArray = Object.entries(initialData.context || {}).map(([key, value]) => ({
                    key,
                    value: String(value)
                }));

                // Transformar pipeline para pasar params a string JSON
                const pipelineArray = (initialData.pipeline || []).map(s => ({
                    step: s.step || "",
                    params: s.params ? JSON.stringify(s.params, null, 2) : ""
                }));

                setFormData({
                    name: initialData.workflow_metadata?.name || "",
                    description: initialData.workflow_metadata?.description || "",
                    input: initialData.workflow_metadata?.input || "EXCEL",
                    output: initialData.workflow_metadata?.output || "XLSX",
                    context: contextArray.length > 0 ? contextArray : [{ key: "base_dir", value: "./backend/tests" }],
                    pipeline: pipelineArray.length > 0 ? pipelineArray : [{ step: "", params: "" }]
                });
            } else {
                // Reset format for new pipeline
                setFormData({
                    name: "",
                    description: "",
                    input: "EXCEL",
                    output: "XLSX",
                    context: [{ key: "base_dir", value: "./backend/tests" }],
                    pipeline: [{ step: "", params: "" }]
                });
            }
        }
    }, [isOpen, initialData]);

    if (!isOpen) return null;

    // --- Handlers para Contexto ---
    const addContextParam = () => {
        setFormData({
            ...formData,
            context: [...formData.context, { key: "", value: "" }]
        });
    };

    const removeContextParam = (index) => {
        const newContext = formData.context.filter((_, i) => i !== index);
        setFormData({ ...formData, context: newContext });
    };

    const updateContextParam = (index, field, value) => {
        const newContext = [...formData.context];
        newContext[index][field] = value;
        setFormData({ ...formData, context: newContext });
    };

    // --- Handlers para Pipeline ---
    const addStep = () => {
        setFormData({
            ...formData,
            pipeline: [...formData.pipeline, { step: "", params: "" }]
        });
    };

    const removeStep = (index) => {
        const newPipeline = formData.pipeline.filter((_, i) => i !== index);
        setFormData({ ...formData, pipeline: newPipeline });
    };

    const updateStep = (index, field, value) => {
        const newPipeline = [...formData.pipeline];
        newPipeline[index][field] = value;
        setFormData({ ...formData, pipeline: newPipeline });
    };

    const moveStep = (index, direction) => {
        if (direction === 'up' && index === 0) return;
        if (direction === 'down' && index === formData.pipeline.length - 1) return;

        const newPipeline = [...formData.pipeline];
        const targetIndex = direction === 'up' ? index - 1 : index + 1;
        [newPipeline[index], newPipeline[targetIndex]] = [newPipeline[targetIndex], newPipeline[index]];

        setFormData({ ...formData, pipeline: newPipeline });
    };

    const handleSave = () => {
        // Re-transformar datos al formato JSON del archivo
        const contextObj = {};
        formData.context.forEach(c => {
            if (c.key.trim()) {
                contextObj[c.key] = c.value;
            }
        });

        const pipelineArray = formData.pipeline.map(s => {
            let parsedParams = {};
            try {
                if (s.params.trim()) {
                    parsedParams = JSON.parse(s.params);
                }
            } catch (e) {
                console.error("Error parsing JSON params for step", s.step, e);
                // Si no es JSON válido, lo enviamos como string o lo dejamos vacío?
                // Mejor alertar al usuario si no es válido
                alert(`Error en el JSON del paso "${s.step}": Parámetros inválidos.`);
                throw e; // Detener el guardado
            }
            return {
                step: s.step,
                params: parsedParams
            };
        });

        const finalConfig = {
            workflow_metadata: {
                name: formData.name,
                description: formData.description,
                input: formData.input,
                output: formData.output
            },
            context: contextObj,
            pipeline: pipelineArray
        };

        if (onSave) {
            onSave(finalConfig);
        }
    };

    return (
        <div className="fixed inset-0 z-50 overflow-hidden font-sans text-left">
            {/* Overlay con desenfoque */}
            <div
                className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />

            {/* Panel Principal */}
            <div className="absolute inset-y-0 right-0 max-w-xl w-full bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out transform translate-x-0">
                {/* Cabecera del Menú */}
                <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-white sticky top-0 z-10">
                    <div>
                        <h2 className="text-lg font-bold text-slate-900">{title}</h2>
                        <p className="text-xs text-slate-500">Define los parámetros técnicos del proceso.</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-50 rounded-full transition-colors">
                        <X size={20} className="text-slate-500" />
                    </button>
                </div>

                {/* Cuerpo del Formulario */}
                <div className="flex-1 overflow-y-auto p-6 space-y-8">

                    {/* Metadata Section */}
                    <section className="space-y-4">
                        <h3 className="text-sm font-semibold text-indigo-600 uppercase tracking-wider flex items-center gap-2">
                            <Database size={16} /> Metadata
                        </h3>
                        <div className="grid gap-4">
                            <div className="grid grid-cols-4 gap-3">
                                <div className="col-span-2">
                                    <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Nombre Proceso</label>
                                    <input
                                        type="text"
                                        placeholder="Nombre del Proceso"
                                        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Entrada</label>
                                    <select
                                        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none bg-white appearance-none"
                                        value={formData.input}
                                        onChange={(e) => setFormData({ ...formData, input: e.target.value })}
                                    >
                                        {FORMAT_OPTIONS.map(opt => (
                                            <option key={opt} value={opt}>{opt}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Salida</label>
                                    <select
                                        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none bg-white appearance-none"
                                        value={formData.output}
                                        onChange={(e) => setFormData({ ...formData, output: e.target.value })}
                                    >
                                        {FORMAT_OPTIONS.map(opt => (
                                            <option key={opt} value={opt}>{opt}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Descripción</label>
                                <textarea
                                    rows="2"
                                    placeholder="Descripción breve..."
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none resize-none"
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                />
                            </div>
                        </div>
                    </section>

                    {/* Contexto Dinámico Section */}
                    <section className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-indigo-600 uppercase tracking-wider flex items-center gap-2">
                                <Settings size={16} /> Contexto del Entorno
                            </h3>
                            <button
                                onClick={addContextParam}
                                className="text-xs flex items-center gap-1 text-indigo-600 hover:text-indigo-700 font-bold"
                            >
                                <PlusCircle size={14} /> Añadir parámetro
                            </button>
                        </div>

                        <div className="space-y-3">
                            {formData.context.map((ctx, index) => (
                                <div key={index} className="flex items-center gap-2 group">
                                    <input
                                        type="text"
                                        placeholder="Key (ej: base_dir)"
                                        className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-xs font-mono bg-slate-50 focus:bg-white outline-none focus:ring-1 focus:ring-indigo-500"
                                        value={ctx.key}
                                        onChange={(e) => updateContextParam(index, 'key', e.target.value)}
                                    />
                                    <input
                                        type="text"
                                        placeholder="Value"
                                        className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-xs font-mono bg-slate-50 focus:bg-white outline-none focus:ring-1 focus:ring-indigo-500"
                                        value={ctx.value}
                                        onChange={(e) => updateContextParam(index, 'value', e.target.value)}
                                    />
                                    <button
                                        onClick={() => removeContextParam(index)}
                                        className="p-2 text-slate-300 hover:text-red-500 transition-colors"
                                    >
                                        <Trash size={16} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Pipeline Steps Section */}
                    <section className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-indigo-600 uppercase tracking-wider flex items-center gap-2">
                                <Code size={16} /> Pasos del Proceso
                            </h3>
                            <button
                                onClick={addStep}
                                className="text-xs flex items-center gap-1 text-indigo-600 hover:text-indigo-700 font-bold"
                            >
                                <Plus size={14} /> Añadir Paso
                            </button>
                        </div>

                        <div className="space-y-4">
                            {formData.pipeline.map((step, index) => (
                                <div key={index} className="p-4 border border-slate-200 rounded-xl space-y-3 bg-slate-50/30 relative group">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] font-bold bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full uppercase">Paso {index + 1}</span>
                                            <div className="flex items-center border border-slate-200 rounded-lg overflow-hidden bg-white">
                                                <button
                                                    onClick={() => moveStep(index, 'up')}
                                                    disabled={index === 0}
                                                    className={`p-1 hover:bg-slate-50 transition-colors ${index === 0 ? 'text-slate-200 cursor-not-allowed' : 'text-slate-400 hover:text-indigo-600'}`}
                                                    title="Mover arriba"
                                                >
                                                    <ChevronUp size={14} />
                                                </button>
                                                <div className="w-px h-3 bg-slate-100" />
                                                <button
                                                    onClick={() => moveStep(index, 'down')}
                                                    disabled={index === formData.pipeline.length - 1}
                                                    className={`p-1 hover:bg-slate-50 transition-colors ${index === formData.pipeline.length - 1 ? 'text-slate-200 cursor-not-allowed' : 'text-slate-400 hover:text-indigo-600'}`}
                                                    title="Mover abajo"
                                                >
                                                    <ChevronDown size={14} />
                                                </button>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => removeStep(index)}
                                            className="text-slate-300 hover:text-red-500 transition-colors"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                    <div className="grid gap-3">
                                        <select
                                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm outline-none bg-white focus:ring-2 focus:ring-indigo-500 appearance-none"
                                            value={step.step}
                                            onChange={(e) => updateStep(index, 'step', e.target.value)}
                                        >
                                            <option value="" disabled>Selecciona un paso...</option>
                                            {STEP_OPTIONS.map(opt => (
                                                <option key={opt} value={opt}>{opt}</option>
                                            ))}
                                        </select>

                                        <textarea
                                            placeholder='Parámetros (JSON o Texto)'
                                            rows="4"
                                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs font-mono outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                                            value={step.params}
                                            onChange={(e) => updateStep(index, 'params', e.target.value)}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>

                {/* Acciones del Footer */}
                <div className="p-6 border-t border-slate-100 bg-slate-50/50 flex items-center gap-3 mt-auto">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2.5 border border-slate-200 text-slate-600 rounded-xl font-medium hover:bg-white transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        className="flex-1 px-4 py-2.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 shadow-md shadow-indigo-100 transition-all active:scale-95"
                        onClick={handleSave}
                    >
                        Guardar Proceso
                    </button>
                </div>
            </div>
        </div>
    );
};

export default NewPipelineDrawer;
