import React, { useState, useEffect } from 'react';
import { AlertCircle, PenLine, CheckCircle2 } from 'lucide-react';

/**
 * Componente para el paso EnrichWithUserInput.
 * Muestra una tabla donde el usuario ingresa valores por archivo para cada campo requerido.
 * 
 * Props:
 *   inputDetails: { type, files: string[], fields: [{key, label}] }
 *   onSubmit: (data: { [filename]: { [key]: value } }) => void
 *   status: string
 */
const EnrichWithUserInput = ({ inputDetails, onSubmit, status }) => {
    const files = inputDetails?.files || [];
    const fields = inputDetails?.fields || [];

    // Estado: { "archivo1.xlsx": { "Curso": "2A" }, ... }
    const [values, setValues] = useState({});

    // Inicializar estado vacío al recibir nuevos detalles
    useEffect(() => {
        if (files.length > 0 && fields.length > 0) {
            const initial = {};
            files.forEach(fname => {
                initial[fname] = {};
                fields.forEach(field => {
                    initial[fname][field.key] = '';
                });
            });
            setValues(initial);
        }
    }, [inputDetails]);

    const updateValue = (filename, fieldKey, val) => {
        setValues(prev => ({
            ...prev,
            [filename]: {
                ...prev[filename],
                [fieldKey]: val
            }
        }));
    };

    // Verificar si todos los campos están llenos
    const allFilled = files.every(fname =>
        fields.every(field => values[fname]?.[field.key]?.trim())
    );

    const handleSubmit = () => {
        if (!allFilled) return;
        onSubmit(values);
    };

    if (!files.length || !fields.length) {
        return (
            <div className="text-slate-400 text-sm text-center p-8">
                No se requieren datos adicionales.
            </div>
        );
    }

    return (
        <div className="space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Banner informativo */}
            <div className="bg-amber-50 border border-amber-100 p-4 rounded-xl flex gap-3 text-amber-700">
                <PenLine size={20} className="shrink-0 mt-0.5" />
                <div className="text-sm">
                    <p className="font-bold">Datos Requeridos por Archivo</p>
                    <p>Ingresa los valores correspondientes para cada archivo antes de continuar.</p>
                </div>
            </div>

            {/* Tabla de ingreso */}
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="bg-slate-50 border-b border-slate-200">
                            <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                Archivo
                            </th>
                            {fields.map(field => (
                                <th key={field.key} className="text-left px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                    {field.label}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {files.map((fname, idx) => (
                            <tr key={fname} className={`border-b border-slate-100 last:border-0 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'}`}>
                                <td className="px-4 py-3">
                                    <div className="flex items-center gap-2">
                                        <div className={`w-2 h-2 rounded-full shrink-0 transition-colors ${fields.every(f => values[fname]?.[f.key]?.trim())
                                                ? 'bg-green-500'
                                                : 'bg-slate-300'
                                            }`} />
                                        <span className="font-mono text-xs text-slate-700 truncate max-w-[200px]" title={fname}>
                                            {fname}
                                        </span>
                                    </div>
                                </td>
                                {fields.map(field => (
                                    <td key={field.key} className="px-4 py-2">
                                        <input
                                            type="text"
                                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs 
                                                       bg-white text-slate-800 
                                                       focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 
                                                       transition-all placeholder:text-slate-300"
                                            placeholder={field.label}
                                            value={values[fname]?.[field.key] || ''}
                                            onChange={(e) => updateValue(fname, field.key, e.target.value)}
                                        />
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Indicador de progreso */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-slate-400">
                    {allFilled ? (
                        <>
                            <CheckCircle2 size={14} className="text-green-500" />
                            <span className="text-green-600 font-bold">Todos los campos completos</span>
                        </>
                    ) : (
                        <>
                            <AlertCircle size={14} />
                            <span>Completa todos los campos para continuar</span>
                        </>
                    )}
                </div>
                <button
                    onClick={handleSubmit}
                    disabled={!allFilled}
                    className={`px-5 py-2 rounded-xl text-sm font-bold transition-all active:scale-95
                        ${allFilled
                            ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg shadow-indigo-200'
                            : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                        }`}
                >
                    Confirmar Datos
                </button>
            </div>
        </div>
    );
};

export default EnrichWithUserInput;
