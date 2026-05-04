import React, { useState, useEffect } from 'react';
import { AlertCircle, PenLine, CheckCircle2 } from 'lucide-react';

/**
 * Componente para el paso EnrichWithUserInput.
 * Soporta dos modos según `inputDetails.type`:
 *   - "enrich_per_file": tabla archivos × campos (un valor por archivo).
 *   - "enrich_once":     formulario único (un valor por campo, válido para todo el run).
 *
 * Props:
 *   inputDetails:
 *     { type: "enrich_per_file", files: string[], fields: [{key, label}] }
 *     { type: "enrich_once",  fields: [{key, label, default?, options?}] }
 *   onSubmit: (data, type) => void
 *     - per_file: data = { [filename]: { [key]: value } }
 *     - once:     data = { [key]: value }
 *   status: string
 */
const EnrichWithUserInput = ({ inputDetails, onSubmit, status }) => {
    const type = inputDetails?.type || 'enrich_per_file';
    const fields = inputDetails?.fields || [];
    const files = inputDetails?.files || [];

    if (!fields.length) {
        return (
            <div className="text-slate-400 text-sm text-center p-8">
                No se requieren datos adicionales.
            </div>
        );
    }

    if (type === 'enrich_once') {
        return <EnrichOnceForm fields={fields} onSubmit={(data) => onSubmit(data, 'enrich_once')} />;
    }

    return <EnrichPerFileTable files={files} fields={fields} onSubmit={(data) => onSubmit(data, 'enrich_per_file')} />;
};

// ─── Formulario único (mode="once") ────────────────────────────────────────

const EnrichOnceForm = ({ fields, onSubmit }) => {
    const [values, setValues] = useState({});

    useEffect(() => {
        const initial = {};
        fields.forEach(f => {
            initial[f.key] = f.default ?? '';
        });
        setValues(initial);
    }, [fields]);

    const update = (key, val) => setValues(prev => ({ ...prev, [key]: val }));

    const allFilled = fields.every(f => String(values[f.key] ?? '').trim());

    return (
        <div className="space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-amber-50 border border-amber-100 p-4 rounded-xl flex gap-3 text-amber-700">
                <PenLine size={20} className="shrink-0 mt-0.5" />
                <div className="text-sm">
                    <p className="font-bold">Datos del Run</p>
                    <p>Ingresa los valores que aplican a todos los archivos de esta ejecución.</p>
                </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm p-5 space-y-4">
                {fields.map(field => (
                    <div key={field.key} className="space-y-1.5">
                        <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider">
                            {field.label || field.key}
                        </label>
                        {Array.isArray(field.options) && field.options.length > 0 ? (
                            <select
                                value={values[field.key] ?? ''}
                                onChange={(e) => update(field.key, e.target.value)}
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white text-slate-800
                                           focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400"
                            >
                                <option value="">— Seleccioná —</option>
                                {field.options.map(opt => (
                                    <option key={opt} value={opt}>{opt}</option>
                                ))}
                            </select>
                        ) : (
                            <input
                                type="text"
                                value={values[field.key] ?? ''}
                                onChange={(e) => update(field.key, e.target.value)}
                                placeholder={field.label || field.key}
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white text-slate-800
                                           focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400
                                           placeholder:text-slate-300"
                            />
                        )}
                    </div>
                ))}
            </div>

            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-slate-400">
                    {allFilled ? (
                        <>
                            <CheckCircle2 size={14} className="text-green-500" />
                            <span className="text-green-600 font-bold">Listo para continuar</span>
                        </>
                    ) : (
                        <>
                            <AlertCircle size={14} />
                            <span>Completa todos los campos</span>
                        </>
                    )}
                </div>
                <button
                    onClick={() => allFilled && onSubmit(values)}
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

// ─── Tabla por archivo (mode="per_file") ────────────────────────────────────

const EnrichPerFileTable = ({ files, fields, onSubmit }) => {
    const [values, setValues] = useState({});

    useEffect(() => {
        const initial = {};
        files.forEach(fname => {
            initial[fname] = {};
            fields.forEach(field => { initial[fname][field.key] = ''; });
        });
        setValues(initial);
    }, [files, fields]);

    const updateValue = (filename, fieldKey, val) => {
        setValues(prev => ({
            ...prev,
            [filename]: { ...prev[filename], [fieldKey]: val }
        }));
    };

    const allFilled = files.every(fname =>
        fields.every(field => values[fname]?.[field.key]?.trim())
    );

    if (!files.length) {
        return <div className="text-slate-400 text-sm text-center p-8">No hay archivos para enriquecer.</div>;
    }

    return (
        <div className="space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-amber-50 border border-amber-100 p-4 rounded-xl flex gap-3 text-amber-700">
                <PenLine size={20} className="shrink-0 mt-0.5" />
                <div className="text-sm">
                    <p className="font-bold">Datos Requeridos por Archivo</p>
                    <p>Ingresa los valores correspondientes para cada archivo antes de continuar.</p>
                </div>
            </div>

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
                    onClick={() => allFilled && onSubmit(values)}
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
