import React, { useState } from 'react';
import { X, Download, FileSpreadsheet, FileText, FileCode } from 'lucide-react';

export default function ExportModal({ isOpen, onClose, onExport, defaultFileName = "export" }) {
    const [format, setFormat] = useState('excel'); // excel, csv, txt
    const [fileName, setFileName] = useState(defaultFileName);
    const [loading, setLoading] = useState(false);

    // Actualizar nombre al abrir el modal o cambiar la prop
    React.useEffect(() => {
        if (isOpen) {
            setFileName(defaultFileName);
        }
    }, [isOpen, defaultFileName]);

    if (!isOpen) return null;

    const handleExport = async () => {
        setLoading(true);
        // Simulamos un pequeño delay o esperamos a la promesa de exportación real
        await onExport(format, fileName);
        setLoading(false);
        onClose();
    };

    return (
        <>
            <div className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-40 transition-opacity" onClick={onClose} />
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-md border border-slate-100 dark:border-slate-800 animate-in zoom-in-95 duration-200">

                    {/* Header */}
                    <div className="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
                        <h3 className="text-lg font-black text-slate-800 dark:text-white">Exportar Datos</h3>
                        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
                            <X size={20} />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="p-6 space-y-6">

                        {/* 1. Format Selection */}
                        <div className="space-y-3">
                            <label className="text-xs font-bold text-slate-400 uppercase">Formato de Archivo</label>
                            <div className="grid grid-cols-3 gap-3">
                                <button
                                    onClick={() => setFormat('excel')}
                                    className={`flex flex-col items-center gap-2 p-3 rounded-xl border-2 transition-all ${format === 'excel'
                                        ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400'
                                        : 'border-slate-100 dark:border-slate-700 hover:border-slate-200 dark:hover:border-slate-600 text-slate-500'
                                        }`}
                                >
                                    <FileSpreadsheet size={24} />
                                    <span className="text-xs font-bold">Excel (.xlsx)</span>
                                </button>

                                <button
                                    onClick={() => setFormat('csv')}
                                    className={`flex flex-col items-center gap-2 p-3 rounded-xl border-2 transition-all ${format === 'csv'
                                        ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400'
                                        : 'border-slate-100 dark:border-slate-700 hover:border-slate-200 dark:hover:border-slate-600 text-slate-500'
                                        }`}
                                >
                                    <FileText size={24} />
                                    <span className="text-xs font-bold">CSV (;)</span>
                                </button>

                                <button
                                    onClick={() => setFormat('txt')}
                                    className={`flex flex-col items-center gap-2 p-3 rounded-xl border-2 transition-all ${format === 'txt'
                                        ? 'border-slate-500 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                                        : 'border-slate-100 dark:border-slate-700 hover:border-slate-200 dark:hover:border-slate-600 text-slate-500'
                                        }`}
                                >
                                    <FileCode size={24} />
                                    <span className="text-xs font-bold">TXT</span>
                                </button>
                            </div>
                        </div>

                        {/* 2. File Name */}
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-400 uppercase">Nombre del Archivo</label>
                            <div className="flex items-center bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 focus-within:ring-2 focus-within:ring-indigo-500 transition-all">
                                <input
                                    type="text"
                                    value={fileName}
                                    onChange={(e) => setFileName(e.target.value)}
                                    className="bg-transparent border-none outline-none w-full text-slate-700 dark:text-slate-200 font-medium placeholder:text-slate-400"
                                    placeholder="Nombre del archivo..."
                                />
                                <span className="text-slate-400 text-sm font-medium ml-2">
                                    .{format === 'excel' ? 'xlsx' : format === 'csv' ? 'csv' : 'txt'}
                                </span>
                            </div>
                        </div>

                    </div>

                    {/* Footer */}
                    <div className="p-5 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-3 bg-slate-50/50 dark:bg-slate-800/50 rounded-b-2xl">
                        <button
                            onClick={onClose}
                            className="px-5 py-2.5 font-bold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition-colors text-sm"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleExport}
                            disabled={loading}
                            className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg shadow-indigo-200 dark:shadow-indigo-900/30 transition-all active:scale-95 text-sm disabled:opacity-70 disabled:active:scale-100"
                        >
                            {loading ? 'Preparando...' : <><Download size={18} /> Descargar</>}
                        </button>
                    </div>

                </div>
            </div>
        </>
    );
}
