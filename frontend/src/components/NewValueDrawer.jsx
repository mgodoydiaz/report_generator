import React, { useState, useEffect } from 'react';
import { X, Save, Layers, Hash } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';

export default function NewValueDrawer({ isOpen, onClose, metric, dimensionsMap, onSave, initialData = null }) {
    // dimensionsValues: { [dimId]: value } -> Value can be ID (for List validation) or Text (for Free validation)
    const [dimensionInputs, setDimensionInputs] = useState({});

    // valueInput: el valor real de la métrica. Si es objeto, será un objeto; si no, string/number.
    const [valueInput, setValueInput] = useState("");

    // Cache para valores de listas desplegables: { [dimId]: [ {id_value, value, ...} ] }
    const [listOptions, setListOptions] = useState({});
    const [loadingLists, setLoadingLists] = useState(false);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (isOpen && metric) {
            // Cargar opciones
            fetchListOptions(metric.dimension_ids);

            if (initialData) {
                // Modo Edición
                let dims = initialData.dimensions_json;
                if (typeof dims === 'string') {
                    try { dims = JSON.parse(dims); } catch { }
                }
                setDimensionInputs(dims || {});

                let val = initialData.value;
                if (metric.data_type === 'object' && typeof val === 'string') {
                    try { val = JSON.parse(val); } catch { }
                }
                setValueInput(val);
            } else {
                // Reset forms
                setDimensionInputs({});
                setValueInput(metric.data_type === 'object' ? {} : "");
            }
        }
    }, [isOpen, metric, initialData]);

    const fetchListOptions = async (dimIds) => {
        setLoadingLists(true);
        const optionsMap = {};

        try {
            const promises = dimIds.map(async (dimId) => {
                const dimDef = dimensionsMap[dimId];
                if (dimDef && dimDef.validation_mode === 'list') {
                    const res = await fetch(`${API_BASE_URL}/dimensions/${dimId}/values`);
                    const data = await res.json();
                    if (!data.error) {
                        optionsMap[dimId] = data;
                    }
                }
            });

            await Promise.all(promises);
            setListOptions(optionsMap);
        } catch (err) {
            console.error(err);
        } finally {
            setLoadingLists(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            // Validaciones
            // 1. Verificar que todas las dimensiones tengan valor
            const missingDims = metric?.dimension_ids.filter(id => !dimensionInputs[id] || dimensionInputs[id] === "");
            if (missingDims?.length > 0) {
                // Obtener nombres de las faltantes
                const names = missingDims.map(id => dimensionsMap[id]?.name || id).join(", ");
                throw new Error(`Falta seleccionar: ${names}`);
            }

            // 2. Verificar valor principal
            if (metric.data_type === 'object') {
                // TODO: Validar campos requeridos del objeto?
            } else {
                if (!valueInput && valueInput !== 0) throw new Error("Debes ingresar un valor");
            }

            // Preparar Payload
            // Convertimos values de dimensiones a un mapa simple {dimId: "Valor"}
            // OJO: Si la dimensión es LIST, ¿guardamos el ID del valor o el Texto?
            // Para simplicidad de lectura visual en las tablas (sin joins complejos), 
            // guardemos el TEXTO del valor seleccionado.
            // PERO, si guardamos el texto, perdemos la referencia si cambia el nombre del valor.
            // Lo IDEAL es guardar el ID si es Lista, y Texto si es Libre.
            // El backend/tabla actual recibe STRING en el JSON. Guardaremos el Texto valor por ahora para prototipo rápido.

            const dimsJson = {};
            metric.dimension_ids.forEach(id => {
                dimsJson[id] = dimensionInputs[id];
            });

            // Valor principal
            let finalValue = valueInput;
            if (metric.data_type === 'int') finalValue = parseInt(valueInput);
            if (metric.data_type === 'float') finalValue = parseFloat(valueInput);
            if (metric.data_type === 'object') finalValue = JSON.stringify(valueInput); // El backend espera string JSON o JSONB. El router lo recibe como 'any'. 
            // NOTA: El router backend definimos `value: Any`. Si mandamos objeto, Axios/Fetch lo manda como JSON.
            // Si el backend lo mete a la DB (Excel), debe ser serializable. 

            const body = {
                value: finalValue,
                dimensions_json: dimsJson
            };

            const url = initialData
                ? `${API_BASE_URL}/metrics/data/${initialData.id_data}`
                : `${API_BASE_URL}/metrics/${metric.id_metric}/data`;

            const method = initialData ? 'PUT' : 'POST';

            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            const result = await res.json();
            if (result.error) throw new Error(result.error);

            toast.success(initialData ? "Valor actualizado" : "Valor registrado");
            onSave();
            onClose();

        } catch (error) {
            toast.error(error.message);
        } finally {
            setSaving(false);
        }
    };

    const renderDimensionInput = (dimId) => {
        const dimDef = dimensionsMap[dimId];
        if (!dimDef) return null;

        const val = dimensionInputs[dimId] || "";

        if (dimDef.validation_mode === 'list') {
            const options = listOptions[dimId] || [];
            return (
                <div key={dimId}>
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1.5">{dimDef.name}</label>
                    <div className="relative">
                        <select
                            value={val}
                            onChange={(e) => setDimensionInputs({ ...dimensionInputs, [dimId]: e.target.value })}
                            className="w-full px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 appearance-none font-medium text-slate-700 dark:text-slate-200"
                        >
                            <option value="">Selecciona una opción...</option>
                            {options.map(opt => (
                                <option key={opt.id_value} value={opt.value}>
                                    {opt.value}
                                </option>
                            ))}
                        </select>
                        {/* Custom Arrow */}
                        <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6" /></svg>
                        </div>
                    </div>
                </div>
            );
        } else {
            return (
                <div key={dimId}>
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1.5">{dimDef.name}</label>
                    <input
                        type="text"
                        value={val}
                        onChange={(e) => setDimensionInputs({ ...dimensionInputs, [dimId]: e.target.value })}
                        placeholder={`Ingresa ${dimDef.name.toLowerCase()}...`}
                        className="w-full px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 font-medium text-slate-700 dark:text-slate-200"
                    />
                </div>
            );
        }
    };

    if (!isOpen || !metric) return null;

    return (
        <>
            <div className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-40 transition-opacity" onClick={onClose} />
            <div className="fixed inset-y-0 right-0 w-full max-w-lg bg-white dark:bg-slate-900 shadow-2xl transform transition-transform z-50 overflow-y-auto">
                <div className="p-6 space-y-8 h-full flex flex-col">

                    {/* Header */}
                    <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
                        <div>
                            <h2 className="text-xl font-black text-slate-800 dark:text-white">{initialData ? "Editar Valor" : "Registrar Valor"}</h2>
                            <p className="text-slate-400 dark:text-slate-500 text-sm font-medium">{metric.name}</p>
                        </div>
                        <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors text-slate-400">
                            <X size={24} />
                        </button>
                    </div>

                    <div className="flex-1 space-y-8">

                        {/* Dimensiones Inputs */}
                        <div className="space-y-4">
                            <h3 className="flex items-center gap-2 font-bold text-slate-800 dark:text-white text-sm">
                                <Layers size={16} className="text-indigo-500" />
                                Contexto (Dimensiones)
                            </h3>
                            <div className="grid gap-4 bg-white dark:bg-slate-900 p-1">
                                {metric.dimension_ids?.length > 0 ? (
                                    metric.dimension_ids.map(dimId => renderDimensionInput(dimId))
                                ) : (
                                    <p className="text-slate-400 text-sm italic">Esta métrica no tiene dimensiones asociadas.</p>
                                )}
                            </div>
                        </div>

                        <hr className="border-slate-100 dark:border-slate-800" />

                        {/* Valor Input */}
                        <div className="space-y-4">
                            <h3 className="flex items-center gap-2 font-bold text-slate-800 dark:text-white text-sm">
                                <Hash size={16} className="text-emerald-500" />
                                Valor a Registrar
                            </h3>

                            {metric.data_type === 'object' ? (
                                <div className="space-y-3 bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                                    {(metric.meta_json?.fields || []).map((field, idx) => (
                                        <div key={idx}>
                                            <label className="block text-xs font-bold text-slate-500 uppercase mb-1.5">{field.name}</label>
                                            <input
                                                type={field.type === 'int' || field.type === 'float' ? 'number' : 'text'}
                                                value={valueInput?.[field.name] || ''}
                                                onChange={(e) => setValueInput({ ...valueInput, [field.name]: e.target.value })}
                                                className="w-full px-3 py-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 outline-none focus:ring-2 focus:ring-emerald-500"
                                            />
                                        </div>
                                    ))}
                                    {(!metric.meta_json?.fields || metric.meta_json.fields.length === 0) && (
                                        <p className="text-xs text-red-400">La estructura del objeto no está definida. Edita la métrica primero.</p>
                                    )}
                                </div>
                            ) : (
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1.5">Valor ({metric.data_type})</label>
                                    <input
                                        type={
                                            metric.data_type === 'int' || metric.data_type === 'float' ? 'number' :
                                                metric.data_type === 'date' ? 'date' :
                                                    metric.data_type === 'datetime' ? 'datetime-local' :
                                                        'text'
                                        }
                                        step={metric.data_type === 'float' ? '0.01' : '1'}
                                        value={valueInput}
                                        onChange={(e) => setValueInput(e.target.value)}
                                        placeholder="Ingresa el valor..."
                                        className="w-full px-4 py-4 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 outline-none focus:ring-2 focus:ring-emerald-500 font-bold text-lg text-slate-700 dark:text-slate-200"
                                        autoFocus
                                    />
                                </div>
                            )}
                        </div>

                    </div>

                    {/* Footer */}
                    <div className="pt-4 flex justify-end gap-3 sticky bottom-0 bg-white dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800">
                        <button
                            onClick={onClose}
                            className="px-6 py-3 font-bold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={saving || loadingLists}
                            className="flex items-center gap-2 px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg shadow-indigo-200 dark:shadow-indigo-900/30 transition-all active:scale-95 disabled:opacity-70 disabled:active:scale-100"
                        >
                            {saving ? 'Guardando...' : <><Save size={18} /> {initialData ? "Actualizar" : "Guardar Registro"}</>}
                        </button>
                    </div>

                </div>
            </div>
        </>
    );
}
