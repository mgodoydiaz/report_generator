import React, { useState, useEffect } from 'react';
import {
    X, FileText, Settings, Layers, PlusCircle, Trash, Trash2, Plus, LayoutTemplate
} from 'lucide-react';
import { SPEC_TYPES, ETL_PARAMETER_OPTIONS } from '../constants';

const SECTION_TYPES = ["tabla", "imagen", "texto"]; // Expanded types just in case

const FIXED_VARIABLES = [
    "leftimage", "rightimage", "centerheaderone", "centerheadertwo",
    "centerheaderthree", "leftfooter", "rightfooter", "documenttitle",
    "schoolname", "theauthor"
];

const NewSpecDrawer = ({ isOpen, onClose, initialData = null, title = "Nueva Especificación", onSave }) => {
    const [formData, setFormData] = useState({
        name: "",
        description: "",
        type: "Reporte",
        variables: FIXED_VARIABLES.map(key => ({ key, value: "" })),
        sections: [],
        etlParams: []
    });
    const [specId, setSpecId] = useState(null);

    // Estado para el select de "Nuevo Parámetro"
    const [selectedEtlParam, setSelectedEtlParam] = useState("");

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
                    sections: initialData.secciones_fijas || [],
                    etlParams: initialData.etlParams || []
                });
                setSpecId(initialData.id);
            } else {
                // Reset for new template
                setFormData({
                    name: "",
                    description: "",
                    type: "Reporte",
                    variables: FIXED_VARIABLES.map(key => ({ key, value: "" })),
                    sections: [],
                    etlParams: []
                });
                setSpecId(null);
            }
            setSelectedEtlParam("");
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

    // --- Handlers for ETL Params ---
    const addEtlParam = (paramId) => {
        if (!paramId) return;

        const paramConfig = ETL_PARAMETER_OPTIONS.find(p => p.id === paramId);
        if (!paramConfig) return;

        // Estructura incial según tipo
        let initialValue = "";
        if (paramConfig.type === 'list_text') initialValue = [];
        if (paramConfig.type === 'list_pair') initialValue = [];

        setFormData(prev => ({
            ...prev,
            etlParams: [...prev.etlParams, {
                id: paramId,
                type: paramConfig.type,
                label: paramConfig.label,
                value: initialValue,
                config: paramConfig
            }]
        }));
        setSelectedEtlParam(""); // Reset select
    };

    const removeEtlParam = (index) => {
        const newParams = formData.etlParams.filter((_, i) => i !== index);
        setFormData({ ...formData, etlParams: newParams });
    };

    const updateEtlParamValue = (index, newValue) => {
        const newParams = [...formData.etlParams];
        newParams[index].value = newValue;
        setFormData({ ...formData, etlParams: newParams });
    };

    // Helpers para actualizar listas dentro de ETL Params
    const addListItem = (paramIndex, itemValue) => {
        const newParams = [...formData.etlParams];
        if (Array.isArray(newParams[paramIndex].value)) {
            newParams[paramIndex].value.push(itemValue);
        }
        setFormData({ ...formData, etlParams: newParams });
    };

    const removeListItem = (paramIndex, itemIndex) => {
        const newParams = [...formData.etlParams];
        if (Array.isArray(newParams[paramIndex].value)) {
            newParams[paramIndex].value = newParams[paramIndex].value.filter((_, i) => i !== itemIndex);
        }
        setFormData({ ...formData, etlParams: newParams });
    };

    const updateListItem = (paramIndex, itemIndex, field, val) => {
        const newParams = [...formData.etlParams];
        if (Array.isArray(newParams[paramIndex].value)) {
            // Si es texto simple (list_text), field es null y val es el string
            // Si es par (list_pair), field es clave del objeto
            if (field === null) {
                newParams[paramIndex].value[itemIndex] = val;
            } else {
                newParams[paramIndex].value[itemIndex] = { ...newParams[paramIndex].value[itemIndex], [field]: val };
            }
        }
        setFormData({ ...formData, etlParams: newParams });
    };


    const handleSave = () => {
        const variablesObj = {};
        formData.variables.forEach(v => {
            if (v.key.trim()) variablesObj[v.key] = v.value;
        });

        const result = {
            name: formData.name,
            description: formData.description,
            type: formData.type,
            variables_documento: variablesObj,
            secciones_fijas: formData.sections,
            secciones_dinamicas: [],
            etlParams: formData.etlParams // Guardamos la config ETL cruda o procesada según necesites
        };

        if (onSave) onSave(result);
    };

    // Filtrar opciones ya seleccionadas
    const availableEtlOptions = ETL_PARAMETER_OPTIONS.filter(opt =>
        !formData.etlParams.some(p => p.id === opt.id)
    );

    return (
        <div className="fixed inset-0 z-50 overflow-hidden font-sans text-left">
            <div
                className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />

            <div className="absolute inset-y-0 right-0 max-w-xl w-full bg-white dark:bg-slate-900 shadow-2xl flex flex-col transition-transform duration-300 ease-in-out transform translate-x-0">
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-white dark:bg-slate-900 sticky top-0 z-10">
                    <div>
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white">{title}</h2>
                        <p className="text-xs text-slate-500 dark:text-slate-400">Configura la estructura básica.</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-full transition-colors">
                        <X size={20} className="text-slate-500 dark:text-slate-400" />
                    </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-6 space-y-8">

                    {/* Metadata */}
                    <section className="space-y-4">
                        <h3 className="text-sm font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider flex items-center gap-2">
                            <FileText size={16} /> Información General
                        </h3>
                        <div className="grid gap-4">
                            <div>
                                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Nombre Especificación</label>
                                <div className="relative">
                                    <input
                                        type="text"
                                        className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none pr-16"
                                        placeholder="Ej: Informe Ejecutivo Mensual"
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    />
                                    {specId && (
                                        <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-mono text-slate-400 bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded pointer-events-none">
                                            #{specId}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Tipo</label>
                                <select
                                    className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                                    value={formData.type}
                                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                                >
                                    {SPEC_TYPES.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Descripción</label>
                                <textarea
                                    rows="2"
                                    className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none resize-none"
                                    placeholder="Descripción breve..."
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                />
                            </div>
                        </div>
                    </section>

                    {/* VISTA: ETL Archivo */}
                    {formData.type === 'ETL Archivo' && (
                        <section className="space-y-6">
                            <h3 className="text-sm font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider flex items-center gap-2">
                                <Settings size={16} /> Parámetros ETL
                            </h3>

                            {/* Selector para añadir parámetros */}
                            <div className="flex gap-2 items-center">
                                <select
                                    className="flex-1 px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
                                    value={selectedEtlParam}
                                    onChange={(e) => {
                                        setSelectedEtlParam(e.target.value);
                                        addEtlParam(e.target.value);
                                    }}
                                >
                                    <option value="">+ Nuevo Parámetro</option>
                                    {availableEtlOptions.map(opt => (
                                        <option key={opt.id} value={opt.id}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>

                            {/* Lista de parámetros configurados */}
                            <div className="space-y-4">
                                {formData.etlParams.map((param, index) => {
                                    // Helper para obtener columnas seleccionadas (para rename_columns)
                                    let selectedColumns = [];
                                    if (param.id === 'rename_columns') {
                                        const sel = formData.etlParams.find(p => p.id === 'select_columns');
                                        if (sel && Array.isArray(sel.value)) selectedColumns = sel.value;
                                    }

                                    return (
                                        <div key={param.id} className="p-4 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50 dark:bg-slate-800 relative group">
                                            <button
                                                onClick={() => removeEtlParam(index)}
                                                className="absolute top-2 right-2 text-slate-400 hover:text-red-500 dark:hover:text-red-400"
                                            >
                                                <X size={16} />
                                            </button>

                                            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 uppercase mb-2">
                                                {param.label}
                                            </label>

                                            {/* TIPO TEXTO SIMPLE */}
                                            {param.type === 'text' && (
                                                <input
                                                    type="text"
                                                    className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                                                    value={param.value}
                                                    onChange={(e) => updateEtlParamValue(index, e.target.value)}
                                                    placeholder={`Ingrese valor para ${param.label}`}
                                                />
                                            )}

                                            {/* TIPO LISTA DE TEXTO (Select Columns) */}
                                            {param.type === 'list_text' && (
                                                <div className="space-y-2">
                                                    {/* Textarea para carga masiva */}
                                                    <div className="flex gap-2">
                                                        <input
                                                            id={`input-${param.id}`}
                                                            type="text"
                                                            placeholder="Columna individual o separadas por coma"
                                                            className="flex-1 px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-xs bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                                                            onKeyDown={(e) => {
                                                                if (e.key === 'Enter') {
                                                                    e.preventDefault();
                                                                    const val = e.target.value;
                                                                    if (val.trim()) {
                                                                        val.split(',').forEach(v => {
                                                                            if (v.trim()) addListItem(index, v.trim());
                                                                        });
                                                                        e.target.value = "";
                                                                    }
                                                                }
                                                            }}
                                                        />
                                                        <button
                                                            onClick={() => {
                                                                const input = document.getElementById(`input-${param.id}`);
                                                                if (input && input.value.trim()) {
                                                                    input.value.split(',').forEach(v => {
                                                                        if (v.trim()) addListItem(index, v.trim());
                                                                    });
                                                                    input.value = "";
                                                                }
                                                            }}
                                                            className="px-3 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-lg text-xs font-bold hover:bg-indigo-100 dark:hover:bg-indigo-900/50 border border-indigo-100 dark:border-indigo-800"
                                                        >
                                                            Confirmar
                                                        </button>
                                                    </div>
                                                    {/* Lista actual */}
                                                    <div className="flex flex-wrap gap-2 mt-2">
                                                        {param.value.map((item, i) => (
                                                            <span key={i} className="inline-flex items-center px-2 py-1 rounded bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-xs text-slate-700 dark:text-slate-200 gap-1">
                                                                {item}
                                                                <button onClick={() => removeListItem(index, i)} className="text-slate-400 hover:text-red-500"><X size={12} /></button>
                                                            </span>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* TIPO LISTA DE PARES (Rename / Enrich) */}
                                            {param.type === 'list_pair' && (
                                                <div className="space-y-2">
                                                    <div className="grid grid-cols-2 gap-2 mb-2">
                                                        <span className="text-[10px] font-bold text-slate-400">{param.config.fields[0]}</span>
                                                        <span className="text-[10px] font-bold text-slate-400">
                                                            {param.id === 'enrich_data' ? "Valor / Pregunta" : param.config.fields[1]}
                                                        </span>
                                                    </div>

                                                    {param.value.map((item, i) => (
                                                        <div key={i} className="flex gap-2 items-center">
                                                            {/* Si es rename_columns y hay columnas seleccionadas, mostramos un select */}
                                                            {param.id === 'rename_columns' && selectedColumns.length > 0 ? (
                                                                <select
                                                                    className="flex-1 px-2 py-1 border border-slate-200 dark:border-slate-700 rounded text-xs bg-white dark:bg-slate-900 text-slate-900 dark:text-white w-full"
                                                                    value={item.key || ""}
                                                                    onChange={(e) => updateListItem(index, i, 'key', e.target.value)}
                                                                >
                                                                    <option value="">Seleccionar Columna...</option>
                                                                    {selectedColumns.map((col, cIdx) => (
                                                                        <option key={cIdx} value={col}>{col}</option>
                                                                    ))}
                                                                </select>
                                                            ) : (
                                                                <input
                                                                    type="text"
                                                                    className="flex-1 px-2 py-1 border border-slate-200 dark:border-slate-700 rounded text-xs bg-white dark:bg-slate-900 text-slate-900 dark:text-white w-full"
                                                                    value={item.key || ""}
                                                                    onChange={(e) => updateListItem(index, i, 'key', e.target.value)}
                                                                    placeholder={param.config.fields[0]}
                                                                />
                                                            )}

                                                            <input
                                                                type="text"
                                                                className="flex-1 px-2 py-1 border border-slate-200 dark:border-slate-700 rounded text-xs bg-white dark:bg-slate-900 text-slate-900 dark:text-white w-full"
                                                                value={item.val || ""}
                                                                onChange={(e) => updateListItem(index, i, 'val', e.target.value)}
                                                                placeholder={param.id === 'enrich_data' && item.user_input ? "Ej: Ingrese el curso..." : param.config.fields[1]}
                                                            />

                                                            {/* Checkbox para User Input en Enrich Data */}
                                                            {param.id === 'enrich_data' && (
                                                                <label className="flex items-center gap-1 cursor-pointer select-none" title="Solicitar al usuario al ejecutar">
                                                                    <input
                                                                        type="checkbox"
                                                                        className="accent-indigo-600 w-4 h-4"
                                                                        checked={item.user_input || false}
                                                                        onChange={(e) => updateListItem(index, i, 'user_input', e.target.checked)}
                                                                    />
                                                                    <span className="text-[9px] font-bold text-slate-400 bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded uppercase">User</span>
                                                                </label>
                                                            )}

                                                            <button onClick={() => removeListItem(index, i)} className="text-slate-400 hover:text-red-500 shrink-0"><X size={14} /></button>
                                                        </div>
                                                    ))}

                                                    <button
                                                        onClick={() => addListItem(index, { key: "", val: "" })}
                                                        className="text-xs text-indigo-600 dark:text-indigo-400 font-bold flex items-center gap-1 mt-2"
                                                    >
                                                        <Plus size={14} /> Agregar Fila
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                                {formData.etlParams.length === 0 && (
                                    <div className="text-center p-6 border-2 border-dashed border-slate-100 dark:border-slate-800 rounded-xl">
                                        <p className="text-xs text-slate-400">Sin parámetros configurados.</p>
                                    </div>
                                )}
                            </div>
                        </section>
                    )}

                    {/* VISTA: Reporte (Original) */}
                    {formData.type === 'Reporte' && (
                        <>
                            {/* Document Variables */}
                            <section className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider flex items-center gap-2">
                                        <Settings size={16} /> Variables del Documento
                                    </h3>
                                </div>
                                <div className="space-y-3 bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-100 dark:border-slate-800">
                                    {formData.variables.map((v, index) => (
                                        <div key={index} className="flex items-center gap-3">
                                            <div className="w-1/3">
                                                <label className="text-[10px] font-bold text-slate-500 uppercase font-mono">{v.key}</label>
                                            </div>
                                            <div className="flex-1">
                                                <input
                                                    type="text"
                                                    placeholder="Valor..."
                                                    className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-xs bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:bg-white dark:focus:bg-slate-800 outline-none focus:ring-1 focus:ring-indigo-500 shadow-sm transition-all"
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
                                    <h3 className="text-sm font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider flex items-center gap-2">
                                        <LayoutTemplate size={16} /> Secciones Fijas
                                    </h3>
                                    <button
                                        onClick={addSection}
                                        className="text-xs flex items-center gap-1 text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-bold"
                                    >
                                        <Plus size={14} /> Añadir Sección
                                    </button>
                                </div>
                                <div className="space-y-4">
                                    {formData.sections.map((section, index) => (
                                        <div key={index} className="p-4 border border-slate-200 dark:border-slate-700 rounded-xl space-y-3 bg-white dark:bg-slate-800 relative group shadow-sm">
                                            <div className="flex items-center justify-between">
                                                <span className="text-[10px] font-bold bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 px-2 py-0.5 rounded-full uppercase">Sección {index + 1}</span>
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
                                                            className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-medium bg-white dark:bg-slate-900 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
                                                            value={section.titulo}
                                                            onChange={(e) => updateSection(index, 'titulo', e.target.value)}
                                                        />
                                                    </div>
                                                    <div>
                                                        <select
                                                            className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm bg-white dark:bg-slate-900 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
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
                                                    className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-mono text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-900 outline-none focus:ring-2 focus:ring-indigo-500"
                                                    value={section.contenido}
                                                    onChange={(e) => updateSection(index, 'contenido', e.target.value)}
                                                />
                                                <input
                                                    type="text"
                                                    placeholder="Opciones extra (ej: width=0.9\textwidth)"
                                                    className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-xs text-slate-400 dark:text-slate-500 bg-white dark:bg-slate-900 outline-none focus:ring-2 focus:ring-indigo-500"
                                                    value={section.options || ""}
                                                    onChange={(e) => updateSection(index, 'options', e.target.value)}
                                                />
                                            </div>
                                        </div>
                                    ))}
                                    {formData.sections.length === 0 && (
                                        <div className="text-center p-8 border-2 border-dashed border-slate-100 dark:border-slate-800 rounded-xl">
                                            <p className="text-xs text-slate-400">No hay secciones definidas.</p>
                                        </div>
                                    )}
                                </div>
                            </section>
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 flex items-center gap-3 mt-auto">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2.5 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-xl font-medium hover:bg-white dark:hover:bg-slate-800 transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        className="flex-1 px-4 py-2.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 shadow-md shadow-indigo-100 transition-all active:scale-95"
                        onClick={handleSave}
                    >
                        Guardar Especificación
                    </button>
                </div>
            </div>
        </div>
    );
};

export default NewSpecDrawer;
