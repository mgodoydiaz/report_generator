import React, { useState, useEffect } from 'react';
import { X, Play, CheckCircle2, AlertCircle, RefreshCcw, Loader2, Upload, FileText } from 'lucide-react';

const WorkflowExecutionModal = ({ isOpen, onClose, workflowId, workflowName }) => {
    const [status, setStatus] = useState('idle'); // idle, loading, requesting_files, executing, success, error
    const [steps, setSteps] = useState([]);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);
    const [error, setError] = useState(null);
    const [userFiles, setUserFiles] = useState({}); // { input_key: File[] }
    const [executionResult, setExecutionResult] = useState(null);

    // Cargar pasos del pipeline al abrir
    useEffect(() => {
        if (isOpen && workflowId) {
            fetchSteps();
        } else {
            resetState();
        }
    }, [isOpen, workflowId]);

    const resetState = () => {
        setStatus('idle');
        setSteps([]);
        setCurrentStepIndex(0);
        setError(null);
        setUserFiles({});
        setExecutionResult(null);
    };

    const fetchSteps = async () => {
        setStatus('loading');
        try {
            const response = await fetch(`http://localhost:8000/api/workflows/${workflowId}/config`);
            const data = await response.json();
            if (data.error) throw new Error(data.error);

            const pipelineSteps = data.pipeline || [];
            setSteps(pipelineSteps);

            // Si el primer paso es RequestUserFiles, ir a ese estado
            if (pipelineSteps?.[0]?.step === 'RequestUserFiles') {
                setStatus('requesting_files');
            } else {
                // Iniciar ejecución directamente
                startExecution(pipelineSteps);
            }
        } catch (err) {
            setError(err.message);
            setStatus('error');
        }
    };

    const handleFileChange = (id, files) => {
        setUserFiles(prev => ({
            ...prev,
            [id]: Array.from(files)
        }));
    };

    const startExecution = async (overrideSteps = null) => {
        const activeSteps = overrideSteps || steps;
        // Validar archivos requeridos
        const requestStep = activeSteps.find(s => s.step === 'RequestUserFiles');
        if (requestStep) {
            const missing = requestStep.params.file_specs.filter(spec => !userFiles[spec.id] || userFiles[spec.id].length === 0);
            if (missing.length > 0) {
                alert(`Por favor sube los archivos requeridos: ${missing.map(m => m.label).join(', ')}`);
                return;
            }
        }

        setStatus('executing');
        setCurrentStepIndex(0);

        try {
            // 1. Subir archivos si existen
            const uploadPromises = Object.entries(userFiles).map(([id, files]) => {
                if (files.length === 0) return Promise.resolve();

                const formData = new FormData();
                formData.append('input_key', id);
                files.forEach(file => formData.append('files', file));

                return fetch(`http://localhost:8000/api/workflows/${workflowId}/upload`, {
                    method: 'POST',
                    body: formData
                }).then(res => res.json());
            });

            await Promise.all(uploadPromises);

            // 2. Iniciar ejecución
            // Simulamos el avance de la barra mientras el backend trabaja
            // Nota: El backend es síncrono por ahora, así que la barra saltará al final
            // o podemos hacer un intervalo visual mientras esperamos la respuesta real.
            const progressInterval = setInterval(() => {
                setCurrentStepIndex(prev => {
                    if (prev < steps.length - 1) return prev + 1;
                    return prev;
                });
            }, 800);

            const response = await fetch(`http://localhost:8000/api/workflows/${workflowId}/run`, {
                method: 'POST'
            });
            const result = await response.json();

            clearInterval(progressInterval);

            if (result.status === 'success') {
                setCurrentStepIndex(steps.length);
                setExecutionResult(result);
                setStatus('success');
            } else {
                throw new Error(result.message || result.error);
            }
        } catch (err) {
            setError(err.message);
            setStatus('error');
        }
    };

    if (!isOpen) return null;

    const progress = steps.length > 0 ? (currentStepIndex / steps.length) * 100 : 0;
    const currentStepName = steps[currentStepIndex]?.step || "Finalizando...";

    return (
        <div className="fixed inset-0 z-60 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={onClose} />

            <div className="bg-white rounded-3xl shadow-2xl w-full max-w-lg relative overflow-hidden flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-white sticky top-0">
                    <div>
                        <h2 className="text-lg font-bold text-slate-900">Ejecución: {workflowName}</h2>
                        <p className="text-xs text-slate-500">ID: {workflowId}</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-50 rounded-full transition-colors">
                        <X size={20} className="text-slate-500" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-8 flex-1 overflow-y-auto">
                    {status === 'loading' && (
                        <div className="flex flex-col items-center justify-center py-12 gap-4">
                            <Loader2 size={40} className="text-indigo-600 animate-spin" />
                            <p className="text-slate-600 font-medium">Cargando definición del pipeline...</p>
                        </div>
                    )}

                    {status === 'requesting_files' && (
                        <div className="space-y-6">
                            <div className="bg-amber-50 border border-amber-100 p-4 rounded-2xl flex gap-3 text-amber-700">
                                <AlertCircle size={20} className="shrink-0" />
                                <div className="text-sm">
                                    <p className="font-bold">Archivos Requeridos</p>
                                    <p>Este workflow necesita que proporciones los siguientes datos antes de comenzar.</p>
                                </div>
                            </div>

                            <div className="space-y-4">
                                {steps.find(s => s.step === 'RequestUserFiles')?.params.file_specs.map(spec => (
                                    <div key={spec.id} className="space-y-2">
                                        <label className="text-xs font-bold text-slate-500 uppercase flex items-center justify-between">
                                            {spec.label}
                                            {userFiles[spec.id] && <span className="text-green-600 flex items-center gap-1"><CheckCircle2 size={12} /> Listo</span>}
                                        </label>
                                        <div className="relative group">
                                            <input
                                                type="file"
                                                multiple={spec.multiple}
                                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                                                onChange={(e) => handleFileChange(spec.id, e.target.files)}
                                            />
                                            <div className={`p-4 border-2 border-dashed rounded-2xl flex flex-col items-center justify-center gap-2 transition-all ${userFiles[spec.id] ? 'bg-indigo-50 border-indigo-200' : 'bg-slate-50 border-slate-200 group-hover:bg-white group-hover:border-indigo-300'}`}>
                                                <Upload size={24} className={userFiles[spec.id] ? 'text-indigo-500' : 'text-slate-400'} />
                                                <p className="text-sm text-slate-600 font-medium">
                                                    {userFiles[spec.id]
                                                        ? `${userFiles[spec.id].length} archivo(s) seleccionado(s)`
                                                        : 'Haz clic o arrastra el archivo aquí'}
                                                </p>
                                                {spec.description && <p className="text-[10px] text-slate-400">{spec.description}</p>}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <button
                                onClick={startExecution}
                                className="w-full bg-indigo-600 text-white py-3 rounded-2xl font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100 flex items-center justify-center gap-2"
                            >
                                <Play size={20} fill="currentColor" />
                                Iniciar Ejecución
                            </button>
                        </div>
                    )}

                    {(status === 'executing' || status === 'idle') && (
                        <div className="space-y-8 py-4">
                            <div className="flex flex-col items-center gap-6">
                                <div className="relative">
                                    <div className="w-24 h-24 rounded-full border-4 border-slate-100 flex items-center justify-center">
                                        <RefreshCcw size={40} className="text-indigo-600 animate-spin" />
                                    </div>
                                    <div className="absolute -bottom-1 -right-1 bg-white p-1 rounded-full border border-slate-100">
                                        <div className="w-6 h-6 bg-indigo-600 rounded-full flex items-center justify-center text-white text-[10px] font-bold">
                                            {currentStepIndex + 1}
                                        </div>
                                    </div>
                                </div>
                                <div className="text-center">
                                    <h3 className="text-xl font-bold text-slate-800">{currentStepName}</h3>
                                    <p className="text-slate-500 text-sm mt-1">Procesando paso {currentStepIndex + 1} de {steps.length}</p>
                                </div>
                            </div>

                            {/* Progress Bar */}
                            <div className="space-y-2">
                                <div className="flex justify-between text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                    <span>Progreso</span>
                                    <span>{Math.round(progress)}%</span>
                                </div>
                                <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-indigo-600 transition-all duration-500 ease-out shadow-[0_0_10px_rgba(79,70,229,0.4)]"
                                        style={{ width: `${progress}%` }}
                                    />
                                </div>
                            </div>

                            {status === 'idle' && (
                                <button
                                    onClick={startExecution}
                                    className="w-full bg-indigo-600 text-white py-3 rounded-2xl font-bold hover:bg-indigo-700 transition-all"
                                >
                                    Confirmar y Ejecutar
                                </button>
                            )}
                        </div>
                    )}

                    {status === 'success' && (
                        <div className="flex flex-col items-center justify-center py-6 gap-6 text-center">
                            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center text-green-600">
                                <CheckCircle2 size={48} />
                            </div>
                            <div className="space-y-2">
                                <h3 className="text-2xl font-extrabold text-slate-800">¡Completado!</h3>
                                <div className="flex flex-col gap-1">
                                    <p className="text-slate-500 text-sm">El pipeline se ejecutó con éxito.</p>
                                    <div className="flex items-center justify-center gap-4 mt-2">
                                        <div className="bg-indigo-50 px-3 py-1 rounded-full text-indigo-700 text-[10px] font-bold uppercase tracking-wider border border-indigo-100">
                                            Pasos: {steps.length}
                                        </div>
                                        <div className="bg-green-50 px-3 py-1 rounded-full text-green-700 text-[10px] font-bold uppercase tracking-wider border border-green-100">
                                            Artefactos: {executionResult?.artifacts?.length || 0}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="bg-slate-50 w-full p-4 rounded-2xl border border-slate-100 text-left">
                                <p className="text-[10px] font-bold text-slate-400 uppercase mb-2">Resultados</p>
                                <div className="space-y-2">
                                    {executionResult?.artifacts?.map(art => (
                                        <div key={art} className="flex items-center gap-2 text-sm text-slate-700 font-medium bg-white p-2 rounded-lg border border-slate-100 shadow-sm">
                                            <FileText size={14} className="text-indigo-500" />
                                            {art}
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <button
                                onClick={onClose}
                                className="w-full bg-slate-800 text-white py-3 rounded-2xl font-bold hover:bg-slate-900 transition-all"
                            >
                                Cerrar Ventana
                            </button>
                        </div>
                    )}

                    {status === 'error' && (
                        <div className="flex flex-col items-center justify-center py-6 gap-6 text-center">
                            <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center text-red-600">
                                <AlertCircle size={48} />
                            </div>
                            <div className="space-y-2 text-red-700">
                                <h3 className="text-2xl font-extrabold">Ocurrió un Error</h3>
                                <p className="text-sm font-medium">{error}</p>
                            </div>
                            <div className="flex gap-3 w-full">
                                <button
                                    onClick={fetchSteps}
                                    className="flex-1 bg-white border border-slate-200 text-slate-600 py-3 rounded-2xl font-bold hover:bg-slate-50 transition-all"
                                >
                                    Reintentar
                                </button>
                                <button
                                    onClick={onClose}
                                    className="flex-1 bg-slate-800 text-white py-3 rounded-2xl font-bold hover:bg-slate-900 transition-all"
                                >
                                    Cerrar
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default WorkflowExecutionModal;
