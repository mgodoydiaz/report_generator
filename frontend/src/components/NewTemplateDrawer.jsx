import React, { useState, useEffect } from 'react';
import {
    X, FileText, Settings, Layers, PlusCircle, Trash, Trash2, Plus, LayoutTemplate
} from 'lucide-react';

const TYPE_OPTIONS = ["Reporte", "Dashboard"];
const SECTION_TYPES = ["tabla", "imagen", "texto"]; // Expanded types just in case

const FIXED_VARIABLES = [
    "leftimage", "rightimage", "centerheaderone", "centerheadertwo",
    "centerheaderthree", "leftfooter", "rightfooter", "documenttitle",
    "schoolname", "theauthor"
];

const NewTemplateDrawer = ({ isOpen, onClose, initialData = null, title = "Nueva Plantilla", onSave }) => {
    const [formData, setFormData] = useState({
        name: "",
        description: "",
        type: "Reporte",
        variables: FIXED_VARIABLES.map(key => ({ key, value: "" })),
        sections: []
    });

    useEffect(() => {
        if (isOpen) {
            if (initialData) {
                // Parse initial data if editing
                const vars = initialData.variables_documento || {};
                const variablesArray = FIXED_VARIABLES.map(key => ({
                    key,
                    value: String(vars[key] || "")
                }));

                setFormData({
                    name: initialData.name || "",
                    description: initialData.description || "",
                    type: initialData.type || "Reporte",
                    variables: variablesArray,
                    sections: initialData.secciones_fijas || []
                });
            } else {
                // Reset for new template
                setFormData({
                    name: "",
                    description: "",
                    type: "Reporte",
                    variables: FIXED_VARIABLES.map(key => ({ key, value: "" })),
                    sections: []
                });
            }
        }
    }, [isOpen, initialData]);

    if (!isOpen) return null;

    // --- Handlers for Variables ---
    const updateVariable = (index, value) => {
        const newVars = [...formData.variables];
        newVars[index].value = value;
        setFormData({ ...formData, variables: newVars });
    };

    // --- Handlers for Sections ---
    const addSection = () => {
        setFormData({
            ...formData,
            sections: [...formData.sections, { titulo: "", tipo: "tabla", contenido: "", options: "" }]
        });
    };

    const removeSection = (index) => {
        const newSections = formData.sections.filter((_, i) => i !== index);
        setFormData({ ...formData, sections: newSections });
    };

    const updateSection = (index, field, value) => {
        const newSections = [...formData.sections];
        newSections[index][field] = value;
        setFormData({ ...formData, sections: newSections });
    };

    const handleSave = () => {
        const variablesObj = {};
        formData.variables.forEach(v => {
            if (v.key.trim()) variablesObj[v.key] = v.value;
        });

        // Filter out empty sections or validate? For now just pass them through
        const result = {
            name: formData.name,
            description: formData.description,
            type: formData.type,
            variables_documento: variablesObj,
            secciones_fijas: formData.sections,
            secciones_dinamicas: [] // Empty as requested
        };

        if (onSave) onSave(result);
    };

    return (
        <div className="fixed inset-0 z-50 overflow-hidden font-sans text-left">
            <div
                className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />

            <div className="absolute inset-y-0 right-0 max-w-xl w-full bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out transform translate-x-0">
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-white sticky top-0 z-10">
                    <div>
                        <h2 className="text-lg font-bold text-slate-900">{title}</h2>
                        <p className="text-xs text-slate-500">Configura la estructura básica del informe.</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-50 rounded-full transition-colors">
                        <X size={20} className="text-slate-500" />
                    </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-6 space-y-8">

                    {/* Metadata */}
                    <section className="space-y-4">
                        <h3 className="text-sm font-semibold text-indigo-600 uppercase tracking-wider flex items-center gap-2">
                            <FileText size={16} /> Información General
                        </h3>
                        <div className="grid gap-4">
                            <div>
                                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Nombre Plantilla</label>
                                <input
                                    type="text"
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                                    placeholder="Ej: Informe Ejecutivo Mensual"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Tipo</label>
                                <select
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none bg-white"
                                    value={formData.type}
                                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                                >
                                    {TYPE_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Descripción</label>
                                <textarea
                                    rows="2"
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none resize-none"
                                    placeholder="Descripción breve..."
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                />
                            </div>
                        </div>
                    </section>

                    {formData.type === 'Reporte' && (
                        <>
                            {/* Document Variables */}
                            <section className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-semibold text-indigo-600 uppercase tracking-wider flex items-center gap-2">
                                        <Settings size={16} /> Variables del Documento
                                    </h3>
                                </div>
                                <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-100">
                                    {formData.variables.map((v, index) => (
                                        <div key={index} className="flex items-center gap-3">
                                            <div className="w-1/3">
                                                <label className="text-[10px] font-bold text-slate-500 uppercase font-mono">{v.key}</label>
                                            </div>
                                            <div className="flex-1">
                                                <input
                                                    type="text"
                                                    placeholder="Valor..."
                                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:bg-white outline-none focus:ring-1 focus:ring-indigo-500 shadow-sm transition-all"
                                                    value={v.value}
                                                    onChange={(e) => updateVariable(index, e.target.value)}
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            {/* Fixed Sections */}
                            <section className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-semibold text-indigo-600 uppercase tracking-wider flex items-center gap-2">
                                        <LayoutTemplate size={16} /> Secciones Fijas
                                    </h3>
                                    <button
                                        onClick={addSection}
                                        className="text-xs flex items-center gap-1 text-indigo-600 hover:text-indigo-700 font-bold"
                                    >
                                        <Plus size={14} /> Añadir Sección
                                    </button>
                                </div>
                                <div className="space-y-4">
                                    {formData.sections.map((section, index) => (
                                        <div key={index} className="p-4 border border-slate-200 rounded-xl space-y-3 bg-white relative group shadow-sm">
                                            <div className="flex items-center justify-between">
                                                <span className="text-[10px] font-bold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full uppercase">Sección {index + 1}</span>
                                                <button
                                                    onClick={() => removeSection(index)}
                                                    className="text-slate-300 hover:text-red-500 transition-colors"
                                                >
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                            <div className="grid gap-3">
                                                <div className="grid grid-cols-3 gap-3">
                                                    <div className="col-span-2">
                                                        <input
                                                            type="text"
                                                            placeholder="Título de la Sección"
                                                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm font-medium outline-none focus:ring-2 focus:ring-indigo-500"
                                                            value={section.titulo}
                                                            onChange={(e) => updateSection(index, 'titulo', e.target.value)}
                                                        />
                                                    </div>
                                                    <div>
                                                        <select
                                                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white outline-none focus:ring-2 focus:ring-indigo-500"
                                                            value={section.tipo}
                                                            onChange={(e) => updateSection(index, 'tipo', e.target.value)}
                                                        >
                                                            {SECTION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                                                        </select>
                                                    </div>
                                                </div>
                                                <input
                                                    type="text"
                                                    placeholder="Ruta del Contenido (ej: aux_files/grafico.png)"
                                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs font-mono text-slate-600 outline-none focus:ring-2 focus:ring-indigo-500"
                                                    value={section.contenido}
                                                    onChange={(e) => updateSection(index, 'contenido', e.target.value)}
                                                />
                                                <input
                                                    type="text"
                                                    placeholder="Opciones extra (ej: width=0.9\textwidth)"
                                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs text-slate-400 outline-none focus:ring-2 focus:ring-indigo-500"
                                                    value={section.options || ""}
                                                    onChange={(e) => updateSection(index, 'options', e.target.value)}
                                                />
                                            </div>
                                        </div>
                                    ))}
                                    {formData.sections.length === 0 && (
                                        <div className="text-center p-8 border-2 border-dashed border-slate-100 rounded-xl">
                                            <p className="text-xs text-slate-400">No hay secciones definidas.</p>
                                        </div>
                                    )}
                                </div>
                            </section>
                        </>
                    )}
                </div>

                {/* Footer */}
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
                        Guardar Plantilla
                    </button>
                </div>
            </div>
        </div>
    );
};

export default NewTemplateDrawer;
