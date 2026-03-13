import React from 'react';

export default function MetricToggle({ value, onChange, roleLabels={} }) {
    return (
        <div className="inline-flex bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5">
            <button
                className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${value === "logro" ? "bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-sm" : "text-slate-400 hover:text-slate-600"}`}
                onClick={() => onChange("logro")}
            >
                {roleLabels.logro_1 || "Logro"}
            </button>
            <button
                className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${value === "simce" ? "bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-sm" : "text-slate-400 hover:text-slate-600"}`}
                onClick={() => onChange("simce")}
            >
                {roleLabels.logro_2 || "Val. secundario"}
            </button>
        </div>
    );
}
