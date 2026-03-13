import React from 'react';
import { CURSO_COLORS, pct, avg } from './constants';

export default function TablaResumenCursos({ data, cursos, onCursoClick, cursoActivo }) {
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
                <thead>
                    <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        {["Curso", "Alumnos", "Promedio %", "SIMCE prom", "Mín (% / SIMCE)", "Máx (% / SIMCE)", "Adecuado", "Elemental", "Insuficiente"].map(h => (
                            <th key={h} className="p-3 font-bold text-slate-400 text-[11px] uppercase tracking-widest">{h}</th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                    {cursos.map((c, i) => {
                        const d = data.filter(r => r._curso === c);
                        if (!d.length) return null;
                        const rends = d.map(r => r._rend).filter(v => v != null);
                        const simces = d.map(r => r._simce).filter(v => v != null);
                        const total = d.length;
                        const adeCount = d.filter(r => r._logro === "Adecuado").length;
                        const eleCount = d.filter(r => r._logro === "Elemental").length;
                        const insCount = d.filter(r => r._logro === "Insuficiente").length;
                        return (
                            <tr key={c} className={`cursor-pointer transition-colors ${cursoActivo === c ? 'bg-indigo-50/80 dark:bg-indigo-900/20' : 'hover:bg-slate-50/80 dark:hover:bg-slate-800/80'}`}
                                onClick={() => onCursoClick(c)}>
                                <td className="p-3 font-extrabold" style={{ color: CURSO_COLORS[i % CURSO_COLORS.length] }}>{c}</td>
                                <td className="p-3 text-slate-600 dark:text-slate-300">{d.length}</td>
                                <td className="p-3 font-bold text-slate-800 dark:text-white">{rends.length ? pct(avg(d, "_rend")) : "—"}</td>
                                <td className="p-3 text-slate-600 dark:text-slate-300">{simces.length ? Math.round(avg(d, "_simce")) : "—"}</td>
                                <td className="p-3 text-rose-600">
                                    {rends.length ? `${pct(Math.min(...rends))} / ${simces.length ? Math.round(Math.min(...simces)) : "—"}` : "—"}
                                </td>
                                <td className="p-3 text-emerald-600">
                                    {rends.length ? `${pct(Math.max(...rends))} / ${simces.length ? Math.round(Math.max(...simces)) : "—"}` : "—"}
                                </td>
                                <td className="p-3"><span className="text-emerald-600 font-bold">{adeCount}</span> <span className="text-slate-400 text-xs">({total ? Math.round(adeCount / total * 100) : 0}%)</span></td>
                                <td className="p-3"><span className="text-amber-600 font-bold">{eleCount}</span> <span className="text-slate-400 text-xs">({total ? Math.round(eleCount / total * 100) : 0}%)</span></td>
                                <td className="p-3"><span className="text-rose-600 font-bold">{insCount}</span> <span className="text-slate-400 text-xs">({total ? Math.round(insCount / total * 100) : 0}%)</span></td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
