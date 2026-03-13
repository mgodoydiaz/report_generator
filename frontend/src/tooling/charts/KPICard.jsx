import React from 'react';

const colorMap = {
    indigo: "bg-indigo-50 text-indigo-600 border-indigo-100 dark:bg-indigo-900/20 dark:text-indigo-400 dark:border-indigo-800",
    emerald: "bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800",
    rose: "bg-rose-50 text-rose-600 border-rose-100 dark:bg-rose-900/20 dark:text-rose-400 dark:border-rose-800",
    amber: "bg-amber-50 text-amber-600 border-amber-100 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800",
};

export default function KPICard({ label, value, sub, icon: Icon, color = "indigo" }) {
    return (
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 shadow-sm flex-1 min-w-40">
            <div className="flex items-center gap-3 mb-3">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${colorMap[color] || colorMap.indigo}`}>
                    {Icon && <Icon size={18} />}
                </div>
                <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">{label}</span>
            </div>
            <div className="text-2xl font-black text-slate-800 dark:text-white">{value}</div>
            {sub && <div className="text-xs text-slate-400 dark:text-slate-500 mt-1">{sub}</div>}
        </div>
    );
}
