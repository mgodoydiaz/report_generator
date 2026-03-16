import React, { useState, useCallback } from 'react';
import { X, UploadCloud, FileSpreadsheet, Settings, Trash2, Download } from 'lucide-react';

export default function ImportModal({ isOpen, onClose, onImport, onDownloadTemplate, metricName }) {
    const [mode, setMode] = useState('template'); // template, etl
    const [files, setFiles] = useState([]);
    const [isDragging, setIsDragging] = useState(false);
    const [uploading, setUploading] = useState(false);

    if (!isOpen) return null;

    const handleDragEnter = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        const droppedFiles = Array.from(e.dataTransfer.files);
        // Filtrar solo excels si queremos ser estrictos, o dejar pasar y validar en back
        const validFiles = droppedFiles.filter(f => f.name.endsWith('.xlsx') || f.name.endsWith('.xls') || f.name.endsWith('.csv'));
        setFiles(prev => [...prev, ...validFiles]);
    };

    const handleFileSelect = (e) => {
        if (e.target.files) {
            const selectedFiles = Array.from(e.target.files);
            setFiles(prev => [...prev, ...selectedFiles]);
        }
    };

    const removeFile = (index) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleImportClick = async () => {
        if (files.length === 0) return;
        setUploading(true);
        await onImport(files);
        setUploading(false);
        setFiles([]);
        onClose();
    };

    return (
        <>
            <div className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-40 transition-opacity" onClick={onClose} />
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-2xl border border-slate-100 dark:border-slate-800 animate-in zoom-in-95 duration-200 flex flex-col max-h-[90vh]">

                    {/* Header */}
                    <div className="flex items-center justify-between p-6 border-b border-slate-100 dark:border-slate-800">
                        <div>
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">Importar Datos</h3>
                            <p className="text-sm text-slate-400 font-medium">Métrica: <span className="text-indigo-500">{metricName}</span></p>
                        </div>
                        <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors text-slate-400">
                            <X size={20} />
                        </button>
                    </div>

                    {/* Tabs */}
                    <div className="flex px-6 pt-4 gap-4 border-b border-slate-100 dark:border-slate-800">
                        <button
                            onClick={() => setMode('template')}
                            className={`pb-3 text-sm font-bold border-b-2 transition-colors flex items-center gap-2 ${mode === 'template'
                                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                                    : 'border-transparent text-slate-400 hover:text-slate-600'
                                }`}
                        >
                            <FileSpreadsheet size={18} />
                            Archivo Plantilla
                        </button>
                        <button
                            disabled
                            className="pb-3 text-sm font-bold border-b-2 border-transparent text-slate-300 dark:text-slate-700 cursor-not-allowed flex items-center gap-2"
                        >
                            <Settings size={18} />
                            ETL Configurado
                            <span className="text-[10px] bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">Pronto</span>
                        </button>
                    </div>

                    {/* Content */}
                    <div className="p-6 space-y-6 overflow-y-auto flex-1 custom-scrollbar">

                        {/* Download Template Section */}
                        <div className="bg-indigo-50 dark:bg-indigo-900/10 p-4 rounded-xl border border-indigo-100 dark:border-indigo-900/30 flex items-center justify-between">
                            <div className="pr-4">
                                <h4 className="font-bold text-indigo-900 dark:text-indigo-300 text-sm">¿No tienes la plantilla?</h4>
                                <p className="text-xs text-indigo-700 dark:text-indigo-400 mt-1">Descarga el formato Excel exacto para esta métrica con sus columnas.</p>
                            </div>
                            <button
                                onClick={onDownloadTemplate}
                                className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 font-bold rounded-lg text-xs shadow-sm border border-indigo-200 dark:border-indigo-700 hover:shadow-md transition-all active:scale-95 whitespace-nowrap"
                            >
                                <Download size={14} /> Descargar Plantilla
                            </button>
                        </div>

                        {/* Dropzone */}
                        <div
                            className={`border-2 border-dashed rounded-2xl p-5 flex flex-col items-center justify-center transition-all bg-slate-50 dark:bg-slate-800/50 ${isDragging
                                    ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-900/20 scale-[0.99]'
                                    : 'border-slate-300 dark:border-slate-700'
                                }`}
                            onDragEnter={handleDragEnter}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                        >
                            <div className="bg-white dark:bg-slate-800 p-3 rounded-full shadow-sm mb-2">
                                <UploadCloud size={24} className="text-indigo-500" />
                            </div>
                            <h4 className="font-bold text-slate-700 dark:text-slate-200 text-base">Arrastra tus archivos aquí</h4>
                            <p className="text-slate-400 text-xs mt-1 mb-4 text-center max-w-xs">Excel (.xlsx, .xls) o CSV.</p>

                            <input
                                type="file"
                                multiple
                                accept=".xlsx, .xls, .csv"
                                onChange={handleFileSelect}
                                className="hidden"
                                id="fileInput"
                            />
                            <label
                                htmlFor="fileInput"
                                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl cursor-pointer shadow-md shadow-indigo-200 dark:shadow-indigo-900/30 transition-all active:scale-95 text-sm"
                            >
                                Seleccionar Archivos
                            </label>
                        </div>

                        {/* File List */}
                        {files.length > 0 && (
                            <div className="space-y-3">
                                <h5 className="text-xs font-bold text-slate-400 uppercase">Archivos listos ({files.length})</h5>
                                <div className="space-y-2">
                                    {files.map((file, idx) => (
                                        <div key={idx} className="flex items-center justify-between p-3 bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-xl shadow-sm animate-in slide-in-from-bottom-2 fade-in duration-300" style={{ animationDelay: `${idx * 50}ms` }}>
                                            <div className="flex items-center gap-3 overflow-hidden">
                                                <div className="bg-green-100 dark:bg-green-900/30 p-2 rounded-lg text-green-600 dark:text-green-400 shrink-0">
                                                    <FileSpreadsheet size={18} />
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="text-sm font-bold text-slate-700 dark:text-slate-200 truncate">{file.name}</p>
                                                    <p className="text-xs text-slate-400">{(file.size / 1024).toFixed(1)} KB</p>
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => removeFile(idx)}
                                                className="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                    </div>

                    {/* Footer */}
                    <div className="p-6 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-3 bg-slate-50/50 dark:bg-slate-800/50 rounded-b-2xl">
                        <button
                            onClick={onClose}
                            className="px-5 py-2.5 font-bold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition-colors text-sm"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleImportClick}
                            disabled={files.length === 0 || uploading}
                            className="flex items-center gap-2 px-8 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg shadow-indigo-200 dark:shadow-indigo-900/30 transition-all active:scale-95 text-sm disabled:opacity-70 disabled:active:scale-100 disabled:shadow-none"
                        >
                            {uploading ? (
                                <>Procesando...</>
                            ) : (
                                <>Importar {files.length > 0 && `(${files.length})`}</>
                            )}
                        </button>
                    </div>

                </div>
            </div>
        </>
    );
}
