import React from 'react';
import { pct } from './constants';

export default function TablaPreguntas({ data, roleLabels={} }) {
    const l1 = roleLabels.logro_1 || "Logro %";
    const preguntas = [...data].sort((a, b) => (b._logro_pregunta || 0) - (a._logro_pregunta || 0));
    if (!preguntas.length) return <p className="text-slate-400 text-sm p-4">Sin datos de preguntas</p>;

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
                <thead>
                    <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        {["N°", "Habilidad", l1, "Correcta"].map(h => (
                            <th key={h} className="p-3 font-bold text-slate-400 text-[11px] uppercase tracking-widest">{h}</th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                    {preguntas.map((p, i) => (
                        <tr key={i} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/80 transition-colors">
                            <td className="p-3 text-slate-400 font-semibold">{p._pregunta || i + 1}</td>
                            <td className="p-3 font-semibold text-slate-700 dark:text-slate-200">
                                {p._habilidad ? p._habilidad.charAt(0).toUpperCase() + p._habilidad.slice(1).toLowerCase() : "—"}
                            </td>
                            <td className="p-3">
                                <div className="flex items-center gap-2">
                                    <div className="flex-1 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                        <div className="h-full rounded-full transition-all"
                                            style={{
                                                width: `${(p._logro_pregunta || 0) * 100}%`,
                                                background: (p._logro_pregunta || 0) >= 0.6 ? "#2a9d8f" : (p._logro_pregunta || 0) >= 0.45 ? "#e9c46a" : "#e76f51"
                                            }} />
                                    </div>
                                    <span className="font-bold text-slate-700 dark:text-slate-200 w-10">{pct(p._logro_pregunta || 0)}</span>
                                </div>
                            </td>
                            <td className="p-3 font-bold text-indigo-600 dark:text-indigo-400 uppercase">{p._correcta || "—"}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
