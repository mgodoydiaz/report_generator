/**
 * studentRiskList.jsx — Lista de estudiantes ordenados por nivel de riesgo
 *
 * Componente:
 *   StudentRiskList — Top-N alumnos con peor nivel, con badge de nivel y trayectoria.
 */

import React, { useMemo } from 'react';
import { getLevelPalette } from './constants';

const TRAJECTORY_ICON = {
    improving:  '↗',
    stable:     '→',
    declining:  '↘',
    incomplete: '—',
};

const TRAJECTORY_COLOR = {
    improving:  'text-emerald-500',
    stable:     'text-slate-400',
    declining:  'text-red-500',
    incomplete: 'text-slate-300 dark:text-slate-600',
};

/**
 * Props:
 *   records          Array<Object>
 *   topN             number (default 10)
 *   riskField        string (default '_worst_level_ord') — ordinal: menor = peor
 *   trajectoryField  string (default '_trajectory')
 *   nameField        string (default '_nombre')
 *   rutField         string (default '_rut')
 *   levelLabelField  string (default '_worst_level_label')
 *   subpruebaField   string (default '_worst_subprueba')
 *   achievement_levels
 */
export function StudentRiskList({
    records = [],
    topN = 10,
    riskField = '_worst_level_ord',
    trajectoryField = '_trajectory',
    nameField = '_nombre',
    rutField = '_rut',
    levelLabelField = '_worst_level_label',
    subpruebaField = '_worst_subprueba',
    achievement_levels = [],
}) {
    const palette = getLevelPalette(achievement_levels);

    const sorted = useMemo(() => {
        // Dedup por RUT conservando peor nivel
        const byRut = {};
        for (const r of records) {
            const key = r[rutField] || r[nameField];
            if (key == null) continue;
            const ord = r[riskField];
            if (!byRut[key] || (ord != null && ord < byRut[key][riskField])) {
                byRut[key] = r;
            }
        }
        return Object.values(byRut)
            .filter(r => r[riskField] != null)
            .sort((a, b) => (a[riskField] ?? Infinity) - (b[riskField] ?? Infinity))
            .slice(0, topN);
    }, [records, topN, riskField, rutField, nameField]);

    if (!sorted.length) {
        return (
            <p className="text-slate-400 text-sm p-4 text-center">
                Sin estudiantes con datos de riesgo.
            </p>
        );
    }

    return (
        <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
            <table className="w-full text-sm">
                <thead>
                    <tr className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                        <th className="text-left px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400 w-8">#</th>
                        <th className="text-left px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">Estudiante</th>
                        <th className="text-left px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">Nivel</th>
                        <th className="text-left px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400 hidden sm:table-cell">Subprueba</th>
                        <th className="text-center px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400 w-10">Tray.</th>
                    </tr>
                </thead>
                <tbody>
                    {sorted.map((r, i) => {
                        const level = r[levelLabelField];
                        const color = palette.colorByName[level];
                        const traj = r[trajectoryField] || 'incomplete';
                        const name = r[nameField] || '—';
                        const rut = r[rutField];

                        return (
                            <tr
                                key={rut || i}
                                className="border-b border-slate-100 dark:border-slate-800 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                            >
                                <td className="px-3 py-2 text-slate-400 font-mono text-xs">{i + 1}</td>
                                <td className="px-3 py-2">
                                    <div className="font-semibold text-slate-700 dark:text-slate-200 truncate max-w-[150px]">{name}</div>
                                    {rut && <div className="text-[11px] text-slate-400 font-mono">{rut}</div>}
                                </td>
                                <td className="px-3 py-2">
                                    {level ? (
                                        <span
                                            className="px-2 py-0.5 rounded-md text-xs font-semibold text-white whitespace-nowrap"
                                            style={{ backgroundColor: color || '#94a3b8' }}
                                        >
                                            {level}
                                        </span>
                                    ) : '—'}
                                </td>
                                <td className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400 truncate max-w-[90px] hidden sm:table-cell">
                                    {r[subpruebaField] || '—'}
                                </td>
                                <td className={`px-3 py-2 text-center font-bold text-base ${TRAJECTORY_COLOR[traj] || TRAJECTORY_COLOR.incomplete}`}>
                                    {TRAJECTORY_ICON[traj] || '—'}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
