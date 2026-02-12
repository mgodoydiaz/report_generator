import React, { useState, useEffect } from 'react';
import { X, Save, Box, Type, Hash, Variable, Plus, Trash2, CheckSquare, Square, Calendar, Clock } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';

export default function NewMetricDrawer({ isOpen, onClose, title, initialData, onSave }) {
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        data_type: 'float',
        dimension_ids: [],
        meta_json: { fields: [] } // Estructura para tipo objeto: { fields: [{name: 'campo', type: 'str'}] }
    });

    const [availableDimensions, setAvailableDimensions] = useState([]);
    const [loading, setLoading] = useState(false);

    // Estado para el constructor de objetos
    const [newFieldName, setNewFieldName] = useState('');
    const [newFieldType, setNewFieldType] = useState('str');

    useEffect(() => {
        fetchDimensions();
    }, []);

    useEffect(() => {
        if (initialData) {
            setFormData({
                name: initialData.name,
                description: initialData.description || '',
                data_type: initialData.data_type || 'float',
                dimension_ids: initialData.dimension_ids || [],
                meta_json: initialData.meta_json || { fields: [] }
            });
        } else {
            setFormData({
                name: '',
                description: '',
                data_type: 'float',
                dimension_ids: [],
                meta_json: { fields: [] }
            });
        }
    }, [initialData, isOpen]);

    const fetchDimensions = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/dimensions`);
            const data = await res.json();
            if (!data.error) setAvailableDimensions(data);
        } catch (error) {
            console.error("Error loading dimensions:", error);
        }
    };

    const handleToggleDimension = (dimId) => {
        setFormData(prev => {
            const current = prev.dimension_ids;
            if (current.includes(dimId)) {
                return { ...prev, dimension_ids: current.filter(id => id !== dimId) };
            } else {
                return { ...prev, dimension_ids: [...current, dimId] };
            }
        });
    };

    const handleAddField = () => {
        if (!newFieldName.trim()) return;

        setFormData(prev => ({
            ...prev,
            meta_json: {
                ...prev.meta_json,
                fields: [...(prev.meta_json.fields || []), { name: newFieldName, type: newFieldType }]
            }
        }));
        setNewFieldName('');
    };

    const handleDeleteField = (idx) => {
        setFormData(prev => {
            const newFields = [...(prev.meta_json.fields || [])];
            newFields.splice(idx, 1);
            return {
                ...prev,
                meta_json: { ...prev.meta_json, fields: newFields }
            };
        });
    };

    const handleSave = async () => {
        if (!formData.name.trim()) {
            toast.error("El nombre es obligatorio");
            return;
        }

        // Validación básica para objetos
        if (formData.data_type === 'object' && (!formData.meta_json.fields || formData.meta_json.fields.length === 0)) {
            toast.error("Debes definir al menos un campo para el tipo Objeto");
            return;
        }

        setLoading(true);
        try {
            const isEditing = !!initialData?.id_metric;
            const url = isEditing
                ? `${API_BASE_URL}/metrics/${initialData.id_metric}`
                : `${API_BASE_URL}/metrics`;

            const method = isEditing ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const result = await response.json();
            if (result.error) throw new Error(result.error);

            toast.success(isEditing ? "Métrica actualizada" : "Métrica creada");
            onSave(result.data);
            onClose();
        } catch (error) {
            toast.error(error.message);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <>
            <div className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-40 transition-opacity" onClick={onClose} />
            <div className="fixed inset-y-0 right-0 w-full max-w-2xl bg-white dark:bg-slate-900 shadow-2xl transform transition-transform z-50 overflow-y-auto">
                <div className="p-6 space-y-8">
                    {/* Header */}
                    <div className="flex items-center justify-between sticky top-0 bg-white dark:bg-slate-900 z-10 pb-4 border-b border-slate-100 dark:border-slate-800">
                        <div>
                            <h2 className="text-2xl font-black text-slate-800 dark:text-white">{title}</h2>
                            <p className="text-slate-400 dark:text-slate-500 text-sm">Define qué medirás y cómo se estructuran los datos</p>
                        </div>
                        <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors text-slate-400">
                            <X size={24} />
                        </button>
                    </div>

                    <div className="space-y-6">
                        {/* Basic Info */}
                        <div className="space-y-4">
                            <div className="flex items-end gap-2">
                                <div className="flex-1">
                                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Nombre de la Métrica</label>
                                    <input
                                        type="text"
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                        placeholder="Ej: Matrícula Total, Venta Neta"
                                        className="w-full px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-bold text-slate-700 dark:text-slate-200"
                                    />
                                </div>
                                {initialData?.id_metric && (
                                    <div className="shrink-0">
                                        <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2 text-center">ID</label>
                                        <span className="flex items-center justify-center px-3 h-[46px] rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm font-mono font-bold text-slate-400 select-all" title="ID de la métrica (no editable)">
                                            #{initialData.id_metric}
                                        </span>
                                    </div>
                                )}
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Descripción</label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    placeholder="Contexto sobre esta métrica..."
                                    className="w-full px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-indigo-500 outline-none transition-all h-20 resize-none"
                                />
                            </div>
                        </div>

                        {/* Data Type */}
                        <div>
                            <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">Tipo de Valor</label>
                            <div className="grid grid-cols-4 gap-2">
                                {[
                                    { id: 'float', label: 'Decimal', icon: Hash },
                                    { id: 'int', label: 'Entero', icon: Hash },
                                    { id: 'str', label: 'Texto', icon: Type },
                                    { id: 'date', label: 'Fecha', icon: Calendar },
                                    { id: 'datetime', label: 'Fecha+Hora', icon: Clock },
                                    { id: 'object', label: 'Objeto', icon: Box }
                                ].map(type => (
                                    <button
                                        key={type.id}
                                        onClick={() => setFormData({ ...formData, data_type: type.id })}
                                        className={`flex flex-col items-center justify-center p-3 rounded-xl border-2 transition-all ${formData.data_type === type.id
                                            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400'
                                            : 'border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 text-slate-400'
                                            }`}
                                    >
                                        <type.icon size={20} className="mb-2" />
                                        <span className="text-xs font-bold">{type.label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Object Builder (Conditional) */}
                        {formData.data_type === 'object' && (
                            <div className="bg-slate-50 dark:bg-slate-800/50 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 space-y-4 animate-in fade-in slide-in-from-top-2">
                                <div className="flex items-center justify-between">
                                    <h3 className="font-bold text-slate-700 dark:text-slate-200 text-sm flex items-center gap-2">
                                        <Box size={16} className="text-indigo-500" />
                                        Estructura del Objeto
                                    </h3>
                                </div>

                                <div className="flex gap-2 items-end">
                                    <div className="flex-1">
                                        <label className="text-[10px] uppercase font-bold text-slate-400 mb-1 block">Nombre Campo</label>
                                        <input
                                            type="text"
                                            value={newFieldName}
                                            onChange={(e) => setNewFieldName(e.target.value)}
                                            placeholder="ej: moneda"
                                            className="w-full px-3 py-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                                            onKeyDown={(e) => e.key === 'Enter' && handleAddField()}
                                        />
                                    </div>
                                    <div className="w-1/3">
                                        <label className="text-[10px] uppercase font-bold text-slate-400 mb-1 block">Tipo</label>
                                        <select
                                            value={newFieldType}
                                            onChange={(e) => setNewFieldType(e.target.value)}
                                            className="w-full px-3 py-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                                        >
                                            <option value="str">Texto</option>
                                            <option value="int">Entero</option>
                                            <option value="float">Decimal</option>
                                            <option value="bool">Booleano</option>
                                        </select>
                                    </div>
                                    <button
                                        onClick={handleAddField}
                                        className="p-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors"
                                    >
                                        <Plus size={18} />
                                    </button>
                                </div>

                                <div className="space-y-2">
                                    {(!formData.meta_json?.fields || formData.meta_json.fields.length === 0) && (
                                        <p className="text-xs text-center text-slate-400 py-2">Agrega campos para definir la estructura.</p>
                                    )}
                                    {formData.meta_json?.fields?.map((field, idx) => (
                                        <div key={idx} className="flex items-center justify-between bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                                            <div className="flex items-center gap-3">
                                                <div className="bg-slate-100 dark:bg-slate-700 p-1.5 rounded-md">
                                                    <Variable size={14} className="text-slate-500" />
                                                </div>
                                                <div className="flex flex-col">
                                                    <span className="font-bold text-sm text-slate-700 dark:text-slate-200">{field.name}</span>
                                                    <span className="text-[10px] text-slate-400 uppercase">{field.type}</span>
                                                </div>
                                            </div>
                                            <button onClick={() => handleDeleteField(idx)} className="text-slate-400 hover:text-red-500 transition-colors">
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Dimensions Selector */}
                        <div>
                            <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">Dimensiones Asociadas</label>
                            <div className="bg-slate-50 dark:bg-slate-900/50 rounded-2xl p-4 border border-slate-200 dark:border-slate-800 max-h-60 overflow-y-auto custom-scrollbar">
                                {availableDimensions.length === 0 ? (
                                    <p className="text-sm text-slate-400 text-center py-4">No hay dimensiones configuradas.</p>
                                ) : (
                                    <div className="grid grid-cols-1 gap-2">
                                        {availableDimensions.map(dim => {
                                            const isSelected = formData.dimension_ids.includes(dim.id_dimension);
                                            return (
                                                <div
                                                    key={dim.id_dimension}
                                                    onClick={() => handleToggleDimension(dim.id_dimension)}
                                                    className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all border ${isSelected
                                                        ? 'bg-white dark:bg-slate-800 border-indigo-500 shadow-sm'
                                                        : 'border-transparent hover:bg-slate-100 dark:hover:bg-slate-800'
                                                        }`}
                                                >
                                                    <div className={`transition-colors ${isSelected ? 'text-indigo-600' : 'text-slate-300'}`}>
                                                        {isSelected ? <CheckSquare size={20} /> : <Square size={20} />}
                                                    </div>
                                                    <div>
                                                        <p className={`font-bold text-sm ${isSelected ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-600 dark:text-slate-400'}`}>
                                                            {dim.name}
                                                        </p>
                                                        {dim.description && (
                                                            <p className="text-xs text-slate-400 line-clamp-1">{dim.description}</p>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                            <p className="text-xs text-slate-400 mt-2 px-1">
                                Selecciona qué dimensiones definen esta métrica (ej: si mides ventas, selecciona "Sede" y "Mes").
                            </p>
                        </div>

                        {/* Footer Buttons */}
                        <div className="pt-6 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-3">
                            <button
                                onClick={onClose}
                                className="px-6 py-3 font-bold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={loading}
                                className="flex items-center gap-2 px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg shadow-indigo-200 dark:shadow-indigo-900/30 transition-all active:scale-95 disabled:opacity-70 disabled:active:scale-100"
                            >
                                {loading ? 'Guardando...' : <><Save size={18} /> Guardar Métrica</>}
                            </button>
                        </div>

                    </div>
                </div>
            </div>
        </>
    );
}
