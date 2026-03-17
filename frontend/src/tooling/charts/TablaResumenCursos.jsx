import React from 'react';
import { CURSO_COLORS, avg, formatValue } from './constants';

export default function TablaResumenCursos({ data, cursos, onCursoClick, cursoActivo, roleLabels={}, roleFormats={}, activeRoles={}, achievement_levels=[] }) {
    const l1 = roleLabels.logro_1 || "Promedio";
    const l2 = roleLabels.logro_2 || "Val. secundario";
    const hasLogro2 = !!activeRoles.logro_2;
    const fmt1 = (v) => formatValue(v, roleFormats.logro_1);
    const fmt2 = (v) => formatValue(v, roleFormats.logro_2);

    const levelsToUse = achievement_levels && achievement_levels.length > 0 
        ? achievement_levels 
        : ["Insuficiente", "Elemental", "Adecuado"];

    const headers = ["Curso", "Alumnos", l1];
    if (hasLogro2) headers.push(l2);
    headers.push(hasLogro2 ? `Mín (${l1} / ${l2})` : `Mín (${l1})`);
    headers.push(hasLogro2 ? `Máx (${l1} / ${l2})` : `Máx (${l1})`);
    
    // Add dynamic level headers
    levelsToUse.forEach(level => headers.push(level));

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
                <thead>
                    <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        {headers.map(h => (
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
                        return (
                            <tr key={c} className={`cursor-pointer transition-colors ${cursoActivo === c ? 'bg-indigo-50/80 dark:bg-indigo-900/20' : 'hover:bg-slate-50/80 dark:hover:bg-slate-800/80'}`}
                                onClick={() => onCursoClick(c)}>
                                <td className="p-3 font-extrabold" style={{ color: CURSO_COLORS[i % CURSO_COLORS.length] }}>{c}</td>
                                <td className="p-3 text-slate-600 dark:text-slate-300">{d.length}</td>
                                <td className="p-3 font-bold text-slate-800 dark:text-white">{rends.length ? fmt1(avg(d, "_rend")) : "—"}</td>
                                {hasLogro2 && (
                                    <td className="p-3 text-slate-600 dark:text-slate-300">{simces.length ? fmt2(avg(d, "_simce")) : "—"}</td>
                                )}
                                <td className="p-3 text-rose-600">
                                    {rends.length ? (hasLogro2 ? `${fmt1(Math.min(...rends))} / ${simces.length ? fmt2(Math.min(...simces)) : "—"}` : fmt1(Math.min(...rends))) : "—"}
                                </td>
                                <td className="p-3 text-emerald-600">
                                    {rends.length ? (hasLogro2 ? `${fmt1(Math.max(...rends))} / ${simces.length ? fmt2(Math.max(...simces)) : "—"}` : fmt1(Math.max(...rends))) : "—"}
                                </td>
                                {levelsToUse.map((level, li) => {
                                    const count = d.filter(r => r._logro === level).length;
                                    const hue = Math.round((li / Math.max(1, levelsToUse.length - 1)) * 120);
                                    return (
                                        <td key={level} className="p-3">
                                            <span className="font-bold" style={{ color: `hsl(${hue}, 70%, 50%)` }}>{count}</span> 
                                            <span className="text-slate-400 text-xs ml-1">({total ? Math.round(count / total * 100) : 0}%)</span>
                                        </td>
                                    );
                                })}
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
