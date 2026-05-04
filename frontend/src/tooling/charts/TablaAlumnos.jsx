import React from 'react';
import NivelBadge from './NivelBadge';
import AvancePill from './AvancePill';
import { formatValue } from './constants';

export default function TablaAlumnos({ data, roleLabels={}, roleFormats={}, activeRoles={} }) {
    const l1 = roleLabels.logro_1 || "Logro";
    const l2 = roleLabels.logro_2 || "Val. secundario";
    const hasLogro2 = !!activeRoles.logro_2;
    const fmt1 = (v) => formatValue(v, roleFormats.logro_1);
    const fmt2 = (v) => formatValue(v, roleFormats.logro_2);

    // Detectar si hay datos de campos derivados — solo se muestran las columnas
    // si al menos una fila tiene el campo (evita columnas vacías).
    const hasPromedio = data.some(a => a._promedio_estudiante != null);
    const hasMejora = data.some(a => a._mejora != null);

    // Format del valor principal (logro_1) — determina cómo mostrar Avance/Mejora.
    // "%" multiplica por 100 (ej. SIMCE Rend 0-1 → "+6%").
    // "#" usa el valor crudo (ej. CV Puntaje 0-100 → "+5", FL PPM → "+15").
    // El primer carácter de roleFormats.logro_1 (ej. "%.1" o "#.0") indica el tipo.
    const fmtChar = (roleFormats.logro_1 || "%").charAt(0);
    const isPercent = fmtChar === '%' || fmtChar === '';

    const headers = ["#", "Estudiante", l1];
    if (hasLogro2) headers.push(l2);
    headers.push("Nivel");
    if (hasPromedio) headers.push("Promedio Año");
    headers.push("Avance");
    if (hasMejora) headers.push("Mejora");

    // Helper: formato del valor con signo (positivo → "+", negativo ya viene con "-").
    // Usa el mismo criterio que AvancePill: porcentaje o entero según el formato.
    const formatSigned = (v) => {
        const n = parseFloat(v);
        if (isNaN(n)) return "—";
        const display = isPercent ? Math.round(n * 100) + "%" : Math.round(n).toString();
        return (n > 0 ? "+" : "") + display;
    };

    const formatPromedio = (v) => {
        const n = parseFloat(v);
        if (isNaN(n)) return "—";
        return isPercent ? Math.round(n * 100) + "%" : Math.round(n).toString();
    };

    const alumnos = [...data].sort((a, b) => (b._rend || 0) - (a._rend || 0));
    if (!alumnos.length) return <p className="text-slate-400 text-sm p-4">Sin datos de estudiantes</p>;

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
                    {alumnos.map((a, i) => (
                        <tr key={i} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/80 transition-colors">
                            <td className="p-3 text-slate-400 font-semibold">{i + 1}</td>
                            <td className="p-3 font-semibold text-slate-700 dark:text-slate-200">{a._nombre || `Estudiante ${i + 1}`}</td>
                            <td className="p-3 font-bold text-slate-800 dark:text-white">{a._rend != null ? fmt1(a._rend) : "—"}</td>
                            {hasLogro2 && (
                                <td className="p-3 text-slate-600 dark:text-slate-300">{a._simce != null ? fmt2(a._simce) : "—"}</td>
                            )}
                            <td className="p-3">{a._logro ? <NivelBadge nivel={a._logro} /> : "—"}</td>
                            {hasPromedio && (
                                <td className="p-3 text-slate-600 dark:text-slate-300">{formatPromedio(a._promedio_estudiante)}</td>
                            )}
                            <td className="p-3">{a._avance != null ? <AvancePill val={a._avance} format={isPercent ? '%' : '#'} /> : "—"}</td>
                            {hasMejora && (
                                <td className="p-3 text-slate-600 dark:text-slate-300 font-mono text-xs">{formatSigned(a._mejora)}</td>
                            )}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
