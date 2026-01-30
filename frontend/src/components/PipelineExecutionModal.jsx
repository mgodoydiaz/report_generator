import React, { useState, useEffect, useRef } from 'react';
import { X, Play, CheckCircle2, AlertCircle, RefreshCcw, Loader2, Upload, FileText, FastForward, Square, StepForward } from 'lucide-react';
import { API_BASE_URL } from '../constants';
import '../assets/pipeline-execution.css';

/**
 * Modal para la ejecución paso a paso de un pipeline con visualización avanzada.
 */
const PipelineExecutionModal = ({ isOpen, onClose, pipelineId, pipelineName }) => {
    const [status, setStatus] = useState('idle'); // idle, loading, requesting_files, executing, success, error
    const [steps, setSteps] = useState([]);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);
    const [error, setError] = useState(null);
    const [userFiles, setUserFiles] = useState({}); // { input_key: File[] }
    const [executionResult, setExecutionResult] = useState(null);

    const stepsViewportRef = useRef(null);
    const activeStepRef = useRef(null);

    // Cargar pasos del pipeline al abrir
    useEffect(() => {
        if (isOpen && pipelineId) {
            fetchSteps();
        } else {
            resetState();
        }
    }, [isOpen, pipelineId]);

    // Auto-scroll al paso activo
    useEffect(() => {
        if (activeStepRef.current && stepsViewportRef.current) {
            activeStepRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, [currentStepIndex, status]);

    const resetState = () => {
        setStatus('idle');
        setSteps([]);
        setCurrentStepIndex(0);
        setError(null);
        setUserFiles({});
        setExecutionResult(null);
        // Resetear sesión en backend también?
        if (pipelineId) {
            fetch(`${API_BASE_URL}/workflows/${pipelineId}/reset`, { method: 'POST' }).catch(console.error);
        }
    };

    const fetchSteps = async () => {
        setStatus('loading');
        try {
            const response = await fetch(`${API_BASE_URL}/workflows/${pipelineId}/config`);
            const data = await response.json();
            if (data.error) throw new Error(data.error);

            const pipelineSteps = data.pipeline || [];
            setSteps(pipelineSteps);

            // Si el primer paso es RequestUserFiles, ir a ese estado
            if (pipelineSteps?.[0]?.step === 'RequestUserFiles') {
                setStatus('requesting_files');
            } else {
                setStatus('idle');
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

    const startExecution = async (mode = 'normal') => {
        // Validar archivos requeridos si estamos en ese paso
        const requestStep = steps.find(s => s.step === 'RequestUserFiles');
        if (requestStep && status === 'requesting_files') {
            const missing = requestStep.params.file_specs.filter(spec => !userFiles[spec.id] || userFiles[spec.id].length === 0);
            if (missing.length > 0) {
                alert(`Por favor sube los archivos requeridos: ${missing.map(m => m.label).join(', ')}`);
                return;
            }
        }

        setStatus('executing');
        // No reseteamos currentStepIndex a 0 aquí, porque podríamos estar reanudando

        try {
            // 1. Subir archivos si existen (solo si estamos al inicio o es la primera vez)
            // Para simplificar, subimos siempre que haya archivos y estemos en requesting_files
            if (status === 'requesting_files') {
                const uploadPromises = Object.entries(userFiles).map(([id, files]) => {
                    if (files.length === 0) return Promise.resolve();

                    const formData = new FormData();
                    formData.append('input_key', id);
                    files.forEach(file => formData.append('files', file));

                    return fetch(`${API_BASE_URL}/workflows/${pipelineId}/upload`, {
                        method: 'POST',
                        body: formData
                    }).then(res => res.json());
                });
                await Promise.all(uploadPromises);
            }

            // 2. Ejecutar según modo
            let result;
            let finalState = false;

            if (mode === 'fast') {
                // Modo rápido: Backend ejecuta todo lo restante
                // Simulamos progreso visual acelerado
                const progressInterval = setInterval(() => {
                    setCurrentStepIndex(prev => {
                        if (prev < steps.length - 1) return prev + 1;
                        return prev;
                    });
                }, 400);

                const response = await fetch(`${API_BASE_URL}/workflows/${pipelineId}/run`, {
                    method: 'POST'
                });
                result = await response.json();
                clearInterval(progressInterval);
                finalState = true;
            } else {
                // Modo paso a paso: Backend ejecuta solo el siguiente paso
                const response = await fetch(`${API_BASE_URL}/workflows/${pipelineId}/step`, {
                    method: 'POST'
                });
                result = await response.json();

                if (result.status === 'success') {
                    // Actualizar índice al siguiente paso indicado por el backend
                    if (result.next_index !== undefined) {
                        setCurrentStepIndex(result.next_index);
                    }
                    finalState = result.finished;
                }
            }

            if (result.status === 'success') {
                if (finalState) {
                    setCurrentStepIndex(steps.length); // Marcar todo como completo visualmente
                    setExecutionResult(result);
                    setStatus('success');
                } else {
                    // Si no ha terminado, volvemos a idle para esperar el siguiente click
                    setStatus('idle');
                }
            } else {
                throw new Error(result.message || result.error);
            }
        } catch (err) {
            setError(err.message);
            setStatus('error');
        }
    };

    if (!isOpen) return null;

    // Calculamos el porcentaje para la línea de fondo
    const totalSteps = steps.length;
    // Si estamos en success, visualmente lleno (steps.length - 1 para array index).
    // Si steps.length es N, indices son 0..N-1.
    // Si estamos en N (finished), mostramos lleno.
    const displayIndex = status === 'success' ? totalSteps - 1 : Math.min(currentStepIndex, totalSteps - 1);
    const progressPercent = totalSteps > 1 ? (displayIndex / (totalSteps - 1)) * 100 : 0;

    const currentStepData = steps[displayIndex];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={onClose} />

            {/* Popup Container */}
            <div id="pipeline-popup" className="bg-white w-full max-w-4xl h-[600px] rounded-2xl shadow-2xl overflow-hidden flex flex-col md:flex-row relative z-10 transition-all duration-300">

                {/* Sidebar: Visualizador de Pasos con Scroll */}
                <div className="bg-slate-50 w-full md:w-64 border-r border-slate-200 flex flex-col items-center py-6 shrink-0">
                    <h2 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Progreso</h2>

                    {/* Contenedor con Scroll */}
                    <div ref={stepsViewportRef} id="steps-viewport" className="relative flex-1 w-full overflow-y-auto pipeline-scrollbar pipeline-steps-viewport px-6">
                        <div className="relative flex flex-col items-center min-h-full py-4">
                            {/* Línea de conexión dinámica */}
                            {totalSteps > 1 && (
                                <div
                                    className="pipeline-step-line"
                                    style={{
                                        background: `linear-gradient(to bottom, #4f46e5 ${progressPercent}%, #e2e8f0 ${progressPercent}%)`
                                    }}
                                ></div>
                            )}

                            {/* Contenedor de Círculos */}
                            <div className="flex flex-col gap-12 items-center w-full z-10">
                                {steps.map((step, index) => {
                                    // Comprobación de estado del paso
                                    const isCompleted = index < currentStepIndex; // Pasos anteriores completados
                                    const isCurrent = index === currentStepIndex && status !== 'success'; // Paso actual activo
                                    const isError = status === 'error' && index === currentStepIndex;

                                    return (
                                        <div
                                            key={index}
                                            ref={isCurrent ? activeStepRef : null}
                                            className={`step-circle w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-500 shrink-0 border-2 
                                                ${isError ? 'bg-red-500 text-white border-red-500 shadow-md' :
                                                    isCompleted ? 'bg-indigo-600 text-white border-indigo-600 shadow-md' :
                                                        isCurrent ? 'bg-slate-900 text-white border-slate-900 ring-4 ring-indigo-100 scale-110' :
                                                            'bg-white text-slate-400 border-slate-200'
                                                }`}
                                        >
                                            {isCompleted ? <CheckCircle2 size={14} /> :
                                                isError ? <AlertCircle size={14} /> :
                                                    (index + 1)}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>

                    {/* Info de progreso fija abajo */}
                    <div className="mt-4 text-center border-t border-slate-200 pt-4 w-full px-4">
                        <p className="text-xl font-semibold text-slate-800">{Math.round(progressPercent)}%</p>
                        <p className="text-[10px] text-slate-500 uppercase font-bold">
                            Paso {Math.min(displayIndex + 1, totalSteps)} de {totalSteps}
                        </p>
                    </div>
                </div>

                {/* Main Content */}
                <div className="flex-1 p-8 flex flex-col bg-white overflow-y-auto">
                    <div className="mb-6 border-b border-slate-100 pb-4">
                        <h1 className="text-xs font-bold text-indigo-500 uppercase tracking-tight mb-1">Ejecución de Proceso</h1>
                        <h2 className="text-2xl font-light text-slate-800">{pipelineName}</h2>
                        <p className="text-xs text-slate-400 mt-1 font-mono">{pipelineId}</p>
                    </div>

                    <div className="flex-1">
                        {status === 'loading' && (
                            <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-400">
                                <Loader2 size={32} className="animate-spin text-indigo-500" />
                                <p className="text-sm font-medium">Cargando definición...</p>
                            </div>
                        )}

                        {status === 'requesting_files' && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <div className="bg-amber-50 border border-amber-100 p-4 rounded-xl flex gap-3 text-amber-700">
                                    <AlertCircle size={20} className="shrink-0" />
                                    <div className="text-sm">
                                        <p className="font-bold">Archivos Requeridos</p>
                                        <p>Selecciona los archivos necesarios para iniciar el proceso.</p>
                                    </div>
                                </div>
                                <div className="grid gap-4">
                                    {steps.find(s => s.step === 'RequestUserFiles')?.params.file_specs.map(spec => (
                                        <div key={spec.id} className="space-y-2">
                                            <div className="flex justify-between items-center">
                                                <label className="text-xs font-bold text-slate-600 uppercase">{spec.label}</label>
                                                {userFiles[spec.id] && <span className="text-xs font-bold text-green-600 flex items-center gap-1"><CheckCircle2 size={12} /> Listo</span>}
                                            </div>
                                            <div className="relative group">
                                                <input
                                                    type="file"
                                                    multiple={spec.multiple}
                                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                                                    onChange={(e) => handleFileChange(spec.id, e.target.files)}
                                                />
                                                <div className={`p-4 border-2 border-dashed rounded-xl flex flex-col items-center justify-center gap-2 transition-all ${userFiles[spec.id] ? 'bg-indigo-50 border-indigo-200' : 'bg-slate-50 border-slate-200 group-hover:bg-white group-hover:border-indigo-300'}`}>
                                                    <Upload size={20} className={userFiles[spec.id] ? 'text-indigo-500' : 'text-slate-400'} />
                                                    <span className="text-sm font-medium text-slate-600">
                                                        {userFiles[spec.id] ? `${userFiles[spec.id].length} archivo(s)` : 'Subir archivo'}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {(status === 'idle' || status === 'executing') && currentStepData && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <div className="bg-slate-50 p-6 rounded-2xl border border-slate-100 relative overflow-hidden">
                                    <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-50 rounded-full blur-3xl -mr-16 -mt-16 opacity-50"></div>
                                    <h3 className="text-lg font-bold text-slate-800 mb-2">{currentStepData.step}</h3>
                                    <p className="text-slate-600 text-sm leading-relaxed">
                                        {currentStepData.description || "Esperando confirmación para ejecutar este paso..."}
                                    </p>
                                    <div className="mt-4 flex items-center gap-2 text-xs font-mono text-slate-400">
                                        <div className={`w-2 h-2 rounded-full bg-indigo-500 ${status === 'executing' ? 'animate-pulse' : ''}`}></div>
                                        {status === 'executing' ? "Procesando paso..." : "Listo para continuar"}
                                    </div>
                                </div>
                            </div>
                        )}

                        {status === 'success' && (
                            <div className="flex flex-col items-center justify-center h-full text-center space-y-4 animate-in zoom-in duration-500">
                                <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-2">
                                    <CheckCircle2 size={32} />
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold text-slate-800">¡Proceso Completado!</h3>
                                    <p className="text-slate-500 text-sm">Todos los pasos han finalizado correctamente.</p>
                                </div>
                                <div className="w-full bg-slate-50 rounded-xl border border-slate-100 p-4 text-left mt-4">
                                    <p className="text-[10px] font-bold text-slate-400 uppercase mb-3">Artefactos Generados</p>
                                    <div className="space-y-2">
                                        {executionResult?.artifacts?.map((art, i) => (
                                            <div key={i} className="flex items-center gap-3 p-2 bg-white rounded-lg border border-slate-100 shadow-sm text-sm text-slate-700">
                                                <FileText size={16} className="text-indigo-500" />
                                                <span className="truncate">{art}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {status === 'error' && (
                            <div className="bg-red-50 border border-red-100 p-6 rounded-2xl text-center space-y-4 animate-in shake duration-300">
                                <div className="w-12 h-12 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto">
                                    <AlertCircle size={24} />
                                </div>
                                <div>
                                    <h3 className="text-lg font-bold text-red-800">Error en la Ejecución</h3>
                                    <p className="text-sm text-red-600 mt-1">{error}</p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Botones footer */}
                    <div className="flex items-center justify-between gap-3 border-t border-slate-100 pt-6 mt-6">
                        {/* Botón Cancelar */}
                        <button
                            onClick={onClose}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                            title="Cancelar ejecución"
                        >
                            <Square size={16} fill="currentColor" className="opacity-80" />
                            <span>{status === 'success' ? 'Cerrar' : 'Cancelar'}</span>
                        </button>

                        <div className="flex gap-2">
                            {(status === 'idle' || status === 'requesting_files') && (
                                <>
                                    {/* Siguiente (Paso a paso / Normal) */}
                                    <button
                                        onClick={() => startExecution('normal')}
                                        disabled={status === 'executing'}
                                        className="flex items-center gap-2 px-5 py-2.5 bg-slate-100 text-slate-700 rounded-xl text-sm font-bold hover:bg-slate-200 hover:text-slate-900 transition-all active:scale-95 disabled:opacity-50"
                                        title="Ejecutar siguiente paso"
                                    >
                                        <StepForward size={18} />
                                        <span>Siguiente</span>
                                    </button>

                                    {/* Avanzar Rápido (Fast Forward) */}
                                    <button
                                        onClick={() => startExecution('fast')}
                                        disabled={status === 'executing'}
                                        className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200 active:scale-95 disabled:opacity-50"
                                        title="Ejecutar todo el proceso automáticamente"
                                    >
                                        <span>Ejecutar Todo</span>
                                        <FastForward size={18} fill="currentColor" />
                                    </button>
                                </>
                            )}


                            {status === 'error' && (
                                <button
                                    onClick={() => startExecution(currentStepIndex > 0 ? 'normal' : 'fast')} // Reintentar
                                    className="px-6 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-all active:scale-95 flex items-center gap-2"
                                >
                                    <RefreshCcw size={16} /> Reintentar
                                </button>
                            )}

                            {status === 'success' && (
                                <button
                                    onClick={onClose}
                                    className="px-6 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800 transition-all shadow-lg active:scale-95"
                                >
                                    Finalizar
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PipelineExecutionModal;
