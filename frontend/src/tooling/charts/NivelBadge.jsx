import React from 'react';

const styles = {
    Adecuado: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800",
    Elemental: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800",
    Insuficiente: "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-900/20 dark:text-rose-400 dark:border-rose-800",
};

export default function NivelBadge({ nivel }) {
    return (
        <span className={`px-2.5 py-0.5 rounded-lg text-[11px] font-bold border ${styles[nivel] || 'bg-slate-50 text-slate-500 border-slate-200'}`}>
            {nivel}
        </span>
    );
}
