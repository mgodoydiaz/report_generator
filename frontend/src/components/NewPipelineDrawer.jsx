import React, { useState } from 'react';
import {
    X, Database, Settings, Code, PlusCircle, Trash, Trash2, Plus
} from 'lucide-react';

// Opciones para el selector de pasos del pipeline
const STEP_OPTIONS = [
    "InitRun",
    "LoadConfig",
    "DiscoverInputs",
    "RunExcelETL",
    "EnrichWithContext",
    "ExportConsolidatedExcel"
];

/**
 * Componente NewPipelineDrawer
 * @param {boolean} isOpen - Controla la visibilidad del panel
 * @param {function} onClose - Función para cerrar el panel
 */
const NewPipelineDrawer = ({ isOpen, onClose }) => {
    const [formData, setFormData] = useState({
        name: "",
        description: "",
        output: "",
        context: [
            { key: "base_dir", value: "./backend/tests" }
        ],
        pipeline: [{ step: "", params: "" }]
    });

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

    return (
        <div className="fixed inset-0 z-50 overflow-hidden font-sans">
            {/* Overlay con desenfoque */}
            <div
                className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />

            {/* Panel Principal */}
            <div className="absolute inset-y-0 right-0 max-w-xl w-full bg-white shadow-2xl flex flex-col">
                {/* Cabecera del Menú */}
                <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                    <div>
                        <h2 className="text-lg font-bold text-slate-900">Configurar Nuevo Pipeline</h2>
                        <p className="text-xs text-slate-500">Define los parámetros técnicos del proceso.</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full transition-colors">
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
                            <input
                                type="text"
                                placeholder="Nombre del Workflow"
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            />
                            <textarea
                                rows="2"
                                placeholder="Descripción breve..."
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none resize-none"
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            />
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
                                <Code size={16} /> Pasos del Pipeline
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
                                        <span className="text-[10px] font-bold bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full uppercase">Paso {index + 1}</span>
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
                                            rows="2"
                                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs font-mono outline-none focus:ring-2 focus:ring-indigo-500"
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
                <div className="p-6 border-t border-slate-100 bg-slate-50/50 flex items-center gap-3">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2.5 border border-slate-200 text-slate-600 rounded-xl font-medium hover:bg-slate-100 transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        className="flex-1 px-4 py-2.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 shadow-md shadow-indigo-100 transition-all active:scale-95"
                        onClick={() => console.log("Datos del Pipeline:", formData)}
                    >
                        Guardar Pipeline
                    </button>
                </div>
            </div>
        </div>
    );
};

export default NewPipelineDrawer;
