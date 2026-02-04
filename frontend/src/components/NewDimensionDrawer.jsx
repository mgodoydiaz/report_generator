import React, { useState, useEffect } from 'react';
import { X, Plus, Trash2, Save, Check, ShieldCheck, List, Type, Hash } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';

export default function NewDimensionDrawer({ isOpen, onClose, title, initialData, onSave }) {
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        data_type: 'str',
        validation_mode: 'list' // 'free' or 'list'
    });

    // Lista local de valores para edición visual. Se guardan solo al guardar la dimensión si es nueva,
    // o se gestionan via API si la dimensión ya existe.
    // Simplificación: Para esta versión, guardaremos la dimensión primero, y luego habilitaremos la edición de valores.
    const [values, setValues] = useState([]);
    const [newValue, setNewValue] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (initialData) {
            setFormData({
                name: initialData.name,
                description: initialData.description || '',
                data_type: initialData.data_type || 'str',
                validation_mode: initialData.validation_mode || 'free'
            });
            fetchValues(initialData.id_dimension);
        } else {
            setFormData({ name: '', description: '', data_type: 'str', validation_mode: 'free' });
            setValues([]);
        }
    }, [initialData, isOpen]);

    const fetchValues = async (dimId) => {
        if (!dimId) return;
        try {
            const res = await fetch(`${API_BASE_URL}/dimensions/${dimId}/values`);
            const data = await res.json();
            if (!data.error) setValues(data);
        } catch (error) {
            console.error(error);
        }
    };

    const handleSaveDimension = async () => {
        if (!formData.name.trim()) {
            toast.error("El nombre es obligatorio");
            return;
        }

        setLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/dimensions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            const result = await response.json();
            if (result.error) throw new Error(result.error);

            toast.success("Dimensión guardada");

            // Si es nueva y tiene validation_mode 'list', podríamos querer agregar los valores inmediatamente.
            // Para simplificar, cerramos y el usuario puede reabrir para editar valores si lo desea,
            // o mejor aún, si estamos 'creando', el ID recién se genera.
            // Una mejor UX sería: Guardar Dimensión -> Obtener ID -> Habilitar sección de valores.
            // Pero seguiremos el flujo simple de onSave parent.
            onSave(result.data);
            onClose();
        } catch (error) {
            toast.error(error.message);
        } finally {
            setLoading(false);
        }
    };

    // Gestión de VALORES (Solo habilitado si la dimensión ya existe, para tener un ID)
    const handleAddValue = async () => {
        if (!newValue.trim() || !initialData?.id_dimension) return;

        try {
            const res = await fetch(`${API_BASE_URL}/dimensions/${initialData.id_dimension}/values`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value: newValue, is_active: true })
            });
            const result = await res.json();
            if (result.status === 'success') {
                setValues([...values, result.data]);
                setNewValue('');
                toast.success("Valor agregado");
            }
        } catch (error) {
            toast.error("Error al agregar valor");
        }
    };

    const handleDeleteValue = async (valId) => {
        try {
            await fetch(`${API_BASE_URL}/dimensions/values/${valId}`, { method: 'DELETE' });
            setValues(values.filter(v => v.id_value !== valId));
            toast.success("Valor eliminado");
        } catch (error) {
            toast.error("Error al eliminar");
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
                            <p className="text-slate-400 dark:text-slate-500 text-sm">Define las propiedades de la dimensión de datos</p>
                        </div>
                        <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors text-slate-400">
                            <X size={24} />
                        </button>
                    </div>

                    <div className="space-y-6">
                        {/* Nombre y Descripción */}
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Nombre de la Dimensión</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    placeholder="Ej: Sede, Carrera, Jornada"
                                    className="w-full px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-bold text-slate-700 dark:text-slate-200"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Descripción (Opcional)</label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    placeholder="Describe para qué se usa esta dimensión..."
                                    className="w-full px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-indigo-500 outline-none transition-all h-24 resize-none"
                                />
                            </div>
                        </div>

                        {/* Configuración Técnica (Grid 2 columnas) */}
                        <div className="grid grid-cols-2 gap-6">
                            <div className="space-y-3">
                                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300">Tipo de Dato</label>
                                <div className="grid grid-cols-2 gap-2">
                                    <button
                                        onClick={() => setFormData({ ...formData, data_type: 'str' })}
                                        className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all ${formData.data_type === 'str'
                                            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400'
                                            : 'border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 text-slate-400'
                                            }`}
                                    >
                                        <Type size={24} className="mb-2" />
                                        <span className="text-xs font-bold">Texto</span>
                                    </button>
                                    <button
                                        onClick={() => setFormData({ ...formData, data_type: 'int' })}
                                        className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all ${formData.data_type === 'int'
                                            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400'
                                            : 'border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 text-slate-400'
                                            }`}
                                    >
                                        <Hash size={24} className="mb-2" />
                                        <span className="text-xs font-bold">Numérico</span>
                                    </button>
                                </div>
                            </div>

                            <div className="space-y-3">
                                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300">Modo de Validación</label>
                                <div className="grid grid-cols-2 gap-2">
                                    <button
                                        onClick={() => setFormData({ ...formData, validation_mode: 'free' })}
                                        className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all ${formData.validation_mode === 'free'
                                            ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400'
                                            : 'border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 text-slate-400'
                                            }`}
                                    >
                                        <ShieldCheck size={24} className="mb-2" />
                                        <span className="text-xs font-bold">Libre</span>
                                    </button>
                                    <button
                                        onClick={() => setFormData({ ...formData, validation_mode: 'list' })}
                                        className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all ${formData.validation_mode === 'list'
                                            ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400'
                                            : 'border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 text-slate-400'
                                            }`}
                                    >
                                        <List size={24} className="mb-2" />
                                        <span className="text-xs font-bold">Lista</span>
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Sección de Valores (Solo si es Validation Mode: List) */}
                        {formData.validation_mode === 'list' && (
                            <div className="bg-slate-50 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-100 dark:border-slate-800 space-y-4 animate-in fade-in slide-in-from-top-4">
                                <div className="flex items-center justify-between">
                                    <h3 className="font-bold text-slate-700 dark:text-slate-200 flex items-center gap-2">
                                        <List size={18} className="text-indigo-500" />
                                        Valores Permitidos
                                    </h3>
                                    <span className="text-xs font-medium text-slate-400 bg-white dark:bg-slate-800 px-2 py-1 rounded-md border border-slate-200 dark:border-slate-700">
                                        {values.length} activos
                                    </span>
                                </div>

                                {!initialData ? (
                                    <div className="text-center p-8 bg-white dark:bg-slate-800 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 text-slate-400 text-sm">
                                        Guarda la dimensión primero para agregar valores a la lista.
                                    </div>
                                ) : (
                                    <>
                                        <div className="flex gap-2">
                                            <input
                                                type="text"
                                                value={newValue}
                                                onChange={(e) => setNewValue(e.target.value)}
                                                onKeyDown={(e) => e.key === 'Enter' && handleAddValue()}
                                                placeholder="Agregar nuevo valor..."
                                                className="flex-1 px-4 py-2 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-indigo-500 outline-none"
                                            />
                                            <button
                                                onClick={handleAddValue}
                                                className="p-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors"
                                            >
                                                <Plus size={20} />
                                            </button>
                                        </div>

                                        <div className="max-h-60 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                                            {values.map((val) => (
                                                <div key={val.id_value} className="flex items-center justify-between p-3 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 group">
                                                    <span className="font-medium text-slate-600 dark:text-slate-300">{val.value}</span>
                                                    <button
                                                        onClick={() => handleDeleteValue(val.id_value)}
                                                        className="text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                </div>
                                            ))}
                                            {values.length === 0 && (
                                                <p className="text-center text-slate-400 text-xs py-4">No hay valores configurados aún.</p>
                                            )}
                                        </div>
                                    </>
                                )}
                            </div>
                        )}

                        {/* Footer Buttons */}
                        <div className="pt-6 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-3">
                            <button
                                onClick={onClose}
                                className="px-6 py-3 font-bold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={handleSaveDimension}
                                disabled={loading}
                                className="flex items-center gap-2 px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg shadow-indigo-200 dark:shadow-indigo-900/30 transition-all active:scale-95 disabled:opacity-70 disabled:active:scale-100"
                            >
                                {loading ? 'Guardando...' : <><Save size={18} /> Guardar Dimensión</>}
                            </button>
                        </div>

                    </div>
                </div>
            </div>
        </>
    );
}
