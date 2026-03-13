import React from 'react';
import NivelBadge from './NivelBadge';
import AvancePill from './AvancePill';
import { pct } from './constants';

export default function TablaAlumnos({ data }) {
    const alumnos = [...data].sort((a, b) => (b._rend || 0) - (a._rend || 0));
    if (!alumnos.length) return <p className="text-slate-400 text-sm p-4">Sin datos de estudiantes</p>;

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
                <thead>
                    <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        {["#", "Estudiante", "Logro %", "SIMCE", "Nivel", "Avance"].map(h => (
                            <th key={h} className="p-3 font-bold text-slate-400 text-[11px] uppercase tracking-widest">{h}</th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                    {alumnos.map((a, i) => (
                        <tr key={i} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/80 transition-colors">
                            <td className="p-3 text-slate-400 font-semibold">{i + 1}</td>
                            <td className="p-3 font-semibold text-slate-700 dark:text-slate-200">{a._nombre || `Estudiante ${i + 1}`}</td>
                            <td className="p-3 font-bold text-slate-800 dark:text-white">{a._rend != null ? pct(a._rend) : "—"}</td>
                            <td className="p-3 text-slate-600 dark:text-slate-300">{a._simce != null ? Math.round(a._simce) : "—"}</td>
                            <td className="p-3">{a._logro ? <NivelBadge nivel={a._logro} /> : "—"}</td>
                            <td className="p-3">{a._avance != null ? <AvancePill val={a._avance} /> : "—"}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
