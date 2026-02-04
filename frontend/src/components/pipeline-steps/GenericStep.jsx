import React from 'react';
import { STEP_TRANSLATIONS } from '../../constants';

const GenericStep = ({ stepData, status }) => {
    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-slate-50 p-6 rounded-2xl border border-slate-100 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-50 rounded-full blur-3xl -mr-16 -mt-16 opacity-50"></div>
                <h3 className="text-lg font-bold text-slate-800 mb-2">
                    {STEP_TRANSLATIONS[stepData.step] || stepData.step}
                </h3>
                <p className="text-slate-600 text-sm leading-relaxed">
                    {stepData.description || "Este paso se ejecutará automáticamente."}
                </p>
                <div className="mt-4 flex items-center gap-2 text-xs font-mono text-slate-400">
                    <div className={`w-2 h-2 rounded-full bg-indigo-500 ${status === 'executing' ? 'animate-pulse' : ''}`}></div>
                    {status === 'executing' ? "Procesando paso..." : "Listo para ejecutar"}
                </div>
            </div>
        </div>
    );
};

export default GenericStep;
