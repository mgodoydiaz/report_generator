import React, { useState } from 'react';
import { Upload, CheckCircle2, AlertCircle, FileUp, X } from 'lucide-react';

const FileDropZone = ({ spec, files, onFileChange }) => {
    const [isDragging, setIsDragging] = useState(false);
    const currentFiles = files || [];
    const isReady = currentFiles.length > 0;

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

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
        }
    };

    const handleFiles = (newFilesList) => {
        const newFiles = Array.from(newFilesList);
        if (spec.multiple && currentFiles.length > 0) {
            const merged = [...currentFiles, ...newFiles];
            onFileChange(spec.id, merged);
        } else {
            onFileChange(spec.id, newFiles);
        }
    };

    const removeFile = (indexToRemove) => {
        const updatedFiles = currentFiles.filter((_, index) => index !== indexToRemove);
        onFileChange(spec.id, updatedFiles);
    };

    return (
        <div
            className="space-y-2"
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
        >
            <div className="flex justify-between items-center transition-all duration-300">
                <label className={`text-xs font-bold uppercase transition-colors ${isDragging ? 'text-indigo-600' : 'text-slate-600'}`}>
                    {spec.label || spec.id}
                </label>
                {isReady && <span className="text-xs font-bold text-green-600 flex items-center gap-1 animate-in zoom-in"><CheckCircle2 size={12} /> Listo</span>}
            </div>

            <div className="relative group">
                <input
                    type="file"
                    multiple={spec.multiple}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                    onChange={(e) => handleFiles(e.target.files)}
                    disabled={isDragging}
                />

                <div className={`
                    p-6 border-2 border-dashed rounded-xl flex flex-col items-center justify-center gap-3 transition-all duration-300 transform
                    ${isDragging
                        ? 'bg-indigo-100/50 border-indigo-500 scale-[1.02] shadow-xl shadow-indigo-100'
                        : isReady
                            ? 'bg-indigo-50 border-indigo-200'
                            : 'bg-slate-50 border-slate-200 group-hover:bg-white group-hover:border-indigo-300'
                    }
                `}>
                    <div className={`
                        p-3 rounded-full transition-all duration-300
                        ${isDragging ? 'bg-indigo-500 text-white scale-110 rotate-12' :
                            isReady ? 'bg-indigo-100/50 text-indigo-600' :
                                'bg-slate-100 group-hover:bg-indigo-50 text-slate-400 group-hover:text-indigo-400'}
                    `}>
                        {isDragging ? <FileUp size={28} /> : <Upload size={24} />}
                    </div>

                    <div className="text-center transition-all duration-300">
                        <p className={`text-sm font-bold ${isDragging ? 'text-indigo-600 text-lg' : 'text-slate-700'}`}>
                            {isDragging ? '¡Suelta los archivos aquí!' :
                                isReady ? `${currentFiles.length} archivo(s) seleccionado(s)` :
                                    'Haz clic o arrastra archivos aquí'}
                        </p>
                        <p className={`text-xs mt-1 transition-opacity ${isDragging ? 'opacity-0' : 'text-slate-400'}`}>
                            {spec.description || "Formatos soportados: Excel, CSV"}
                        </p>
                    </div>
                </div>
            </div>

            {isReady && !isDragging && (
                <div className="flex flex-wrap gap-2 mt-2 animate-in slide-in-from-top-2 fade-in">
                    {Array.from(currentFiles).map((file, idx) => (
                        <div key={idx} className="flex items-center gap-1 text-[10px] bg-slate-100 text-slate-600 pl-2 pr-1 py-1 rounded-md border border-slate-200 shadow-sm group">
                            <span className="truncate max-w-[150px]">{file.name}</span>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    removeFile(idx);
                                }}
                                className="ml-1 p-0.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                            >
                                <X size={12} />
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

const RequestUserFiles = ({ stepParams, files = {}, onFileChange }) => {
    const fileSpecs = stepParams?.file_specs || [];

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-amber-50 border border-amber-100 p-4 rounded-xl flex gap-3 text-amber-700">
                <AlertCircle size={20} className="shrink-0" />
                <div className="text-sm">
                    <p className="font-bold">Archivos Requeridos</p>
                    <p>Selecciona los archivos necesarios para continuar con el proceso.</p>
                </div>
            </div>
            <div className="grid gap-6">
                {fileSpecs.map(spec => (
                    <FileDropZone
                        key={spec.id}
                        spec={spec}
                        files={files[spec.id]}
                        onFileChange={onFileChange}
                    />
                ))}
            </div>
        </div>
    );
};

export default RequestUserFiles;
