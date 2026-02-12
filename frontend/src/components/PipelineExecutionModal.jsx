import React, { useState, useEffect, useRef } from 'react';
import { X, Play, CheckCircle2, AlertCircle, RefreshCcw, Loader2, FastForward, Square, StepForward, FileText } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import StepRenderer from './pipeline-steps/StepRenderer';
import '../assets/pipeline-execution.css';

/**
 * Modal para la ejecución paso a paso de un pipeline con visualización avanzada.
 */
const PipelineExecutionModal = ({ isOpen, onClose, pipelineId, pipelineName }) => {
    const [status, setStatus] = useState('idle'); // idle, loading, executing, waiting_input, success, error
    const [steps, setSteps] = useState([]);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);
    const [error, setError] = useState(null);
    const [userFiles, setUserFiles] = useState({}); // { input_key: File[] }
    const [executionResult, setExecutionResult] = useState(null);
    const [executionMode, setExecutionMode] = useState('normal'); // normal | fast

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
        if (pipelineId) {
            fetch(`${API_BASE_URL}/pipelines/${pipelineId}/reset`, { method: 'POST' }).catch(console.error);
        }
    };

    const fetchSteps = async () => {
        setStatus('loading');
        try {
            const response = await fetch(`${API_BASE_URL}/pipelines/${pipelineId}/config`);
            const data = await response.json();
            if (data.error) throw new Error(data.error);

            const pipelineSteps = data.pipeline || [];
            setSteps(pipelineSteps);
            setStatus('idle');

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
        // 1. Si el paso actual es RequestUserFiles y hay archivos seleccionados, subirlos primero
        const currentStep = steps[currentStepIndex];
        if (currentStep && currentStep.step === 'RequestUserFiles') {
            const specs = currentStep.params.file_specs || [];
            const hasFiles = Object.values(userFiles).some(files => files && files.length > 0);

            if (hasFiles) {
                // Validar que no falten archivos obligatorios
                const missing = specs.filter(spec =>
                    !spec.optional && (!userFiles[spec.id] || userFiles[spec.id].length === 0)
                );

                if (missing.length > 0) {
                    toast.error(`Faltan archivos: ${missing.map(m => m.label || m.id).join(', ')}`);
                    return;
                }

                // Subir archivos
                try {
                    const uploadPromises = Object.entries(userFiles).map(([id, files]) => {
                        if (files.length === 0) return Promise.resolve();
                        const formData = new FormData();
                        formData.append('input_key', id);
                        files.forEach(file => formData.append('files', file));
                        return fetch(`${API_BASE_URL}/pipelines/${pipelineId}/upload`, {
                            method: 'POST',
                            body: formData
                        }).then(res => res.json());
                    });

                    await Promise.all(uploadPromises);
                } catch (e) {
                    setError("Error subiendo archivos: " + e.message);
                    setStatus('error');
                    return;
                }
            } else if (status !== 'waiting_input') {
                // No hay archivos seleccionados y no estamos en waiting_input:
                // dejar que el backend lance WaitingForInputException para mostrar la UI
            }
        }

        setStatus('executing');

        // Recordar el modo para poder retomar después de un waiting_input
        const effectiveMode = status === 'waiting_input' ? executionMode : mode;
        setExecutionMode(effectiveMode);

        try {
            let result;
            let finalState = false;

            if (effectiveMode === 'fast') {
                // Modo rápido
                const progressInterval = setInterval(() => {
                    setCurrentStepIndex(prev => (prev < steps.length - 1 ? prev + 1 : prev));
                }, 400);

                const response = await fetch(`${API_BASE_URL}/pipelines/${pipelineId}/run`, { method: 'POST' });
                result = await response.json();
                clearInterval(progressInterval);

                // Si el pipeline se detuvo porque necesita input del usuario
                if (result.status === 'waiting_input') {
                    setStatus('waiting_input');
                    if (result.step_index !== undefined) {
                        setCurrentStepIndex(result.step_index);
                    }
                    if (result.message) toast(result.message, { icon: '👋' });
                    return;
                }

                finalState = true;
            } else {
                // Modo paso a paso
                const response = await fetch(`${API_BASE_URL}/pipelines/${pipelineId}/step`, { method: 'POST' });
                result = await response.json();

                // Caso especial: Backend pide input
                if (result.status === 'waiting_input') {
                    setStatus('waiting_input');
                    // Asegurarnos de que el índice visual coincida
                    if (result.step_index !== undefined) {
                        setCurrentStepIndex(result.step_index);
                    }
                    if (result.message) toast(result.message, { icon: '👋' });
                    return; // Terminamos aquí por ahora
                }

                // Si acabamos de resolver un RequestUserFiles (post-upload),
                // ejecutar automáticamente el siguiente paso para no requerir doble clic
                if (result.status === 'success' && !result.finished && result.step_name === 'RequestUserFiles') {
                    if (result.next_index !== undefined) {
                        setCurrentStepIndex(result.next_index);
                    }
                    const nextResponse = await fetch(`${API_BASE_URL}/pipelines/${pipelineId}/step`, { method: 'POST' });
                    result = await nextResponse.json();
                }

                if (result.status === 'success') {
                    if (result.next_index !== undefined) {
                        setCurrentStepIndex(result.next_index);
                    }
                    finalState = result.finished;
                }
            }

            if (result.status === 'success') {
                if (finalState) {
                    setCurrentStepIndex(steps.length); // Visualmente completo
                    setExecutionResult(result);
                    setStatus('success');
                    toast.success("¡Pipeline completado con éxito!");
                } else {
                    setStatus('idle');
                }
            } else {
                throw new Error(result.message || result.error || "Error desconocido");
            }
        } catch (err) {
            setError(err.message);
            setStatus('error');
        }
    };

    if (!isOpen) return null;

    const totalSteps = steps.length;
    const displayIndex = status === 'success' ? totalSteps - 1 : Math.min(currentStepIndex, totalSteps - 1);
    const progressPercent = totalSteps > 1 ? (displayIndex / (totalSteps - 1)) * 100 : 0;
    const currentStepData = steps[displayIndex];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={onClose} />
            <div id="pipeline-popup" className="bg-white w-full max-w-4xl h-[600px] rounded-2xl shadow-2xl overflow-hidden flex flex-col md:flex-row relative z-10 transition-all duration-300">

                {/* Sidebar: Visualizador de Pasos */}
                <div className="bg-slate-50 w-full md:w-64 border-r border-slate-200 flex flex-col items-center py-6 shrink-0">
                    <h2 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Progreso</h2>
                    <div ref={stepsViewportRef} id="steps-viewport" className="relative flex-1 w-full overflow-y-auto pipeline-scrollbar pipeline-steps-viewport px-6">
                        <div className="relative flex flex-col items-center min-h-full py-4">
                            {totalSteps > 1 && (
                                <div className="pipeline-step-line" style={{ background: `linear-gradient(to bottom, #4f46e5 ${progressPercent}%, #e2e8f0 ${progressPercent}%)` }}></div>
                            )}
                            <div className="flex flex-col gap-12 items-center w-full z-10">
                                {steps.map((step, index) => {
                                    const isCompleted = index < currentStepIndex;
                                    const isCurrent = index === currentStepIndex && status !== 'success';
                                    const isWaiting = status === 'waiting_input' && index === currentStepIndex;
                                    const isError = status === 'error' && index === currentStepIndex;

                                    return (
                                        <div key={index} ref={isCurrent || isWaiting ? activeStepRef : null}
                                            className={`step-circle w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-500 shrink-0 border-2 
                                                ${isError ? 'bg-red-500 text-white border-red-500 shadow-md' :
                                                    isCompleted ? 'bg-indigo-600 text-white border-indigo-600 shadow-md' :
                                                        isWaiting ? 'bg-amber-400 text-white border-amber-400 ring-4 ring-amber-100 scale-110' :
                                                            isCurrent ? 'bg-slate-900 text-white border-slate-900 ring-4 ring-indigo-100 scale-110' :
                                                                'bg-white text-slate-400 border-slate-200'}`}
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
                    <div className="mt-4 text-center border-t border-slate-200 pt-4 w-full px-4">
                        <p className="text-xl font-semibold text-slate-800">{Math.round(progressPercent)}%</p>
                        <p className="text-[10px] text-slate-500 uppercase font-bold">Paso {Math.min(displayIndex + 1, totalSteps)} de {totalSteps}</p>
                    </div>
                </div>

                {/* Main Content */}
                <div className="flex-1 p-8 flex flex-col bg-white overflow-y-auto">
                    <div className="mb-6 border-b border-slate-100 pb-4">
                        <h1 className="text-xs font-bold text-indigo-500 uppercase tracking-tight mb-1">Ejecución de Proceso</h1>
                        <h2 className="text-2xl font-light text-slate-800">{pipelineName}</h2>
                    </div>

                    <div className="flex-1">
                        {status === 'loading' && (
                            <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-400">
                                <Loader2 size={32} className="animate-spin text-indigo-500" />
                                <p className="text-sm font-medium">Cargando definición...</p>
                            </div>
                        )}

                        {/* Renderizado Modular del Paso Actual */}
                        {(status === 'idle' || status === 'executing' || status === 'waiting_input') && currentStepData && (
                            <StepRenderer
                                stepData={currentStepData}
                                status={status}
                                userFiles={userFiles}
                                onFileChange={handleFileChange}
                            />
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
                                <AlertCircle size={48} className="text-red-500 mx-auto" />
                                <div>
                                    <h3 className="text-lg font-bold text-red-800">Error en la Ejecución</h3>
                                    <p className="text-sm text-red-600 mt-1">{error}</p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Footer Buttons */}
                    <div className="flex items-center justify-between gap-3 border-t border-slate-100 pt-6 mt-6">
                        <button onClick={onClose} className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all">
                            <Square size={16} fill="currentColor" className="opacity-80" />
                            <span>{status === 'success' ? 'Cerrar' : 'Cancelar'}</span>
                        </button>

                        <div className="flex gap-2">
                            {(status === 'idle' || status === 'waiting_input') && (
                                <>
                                    <button onClick={() => startExecution('normal')} disabled={status === 'executing'}
                                        className="flex items-center gap-2 px-5 py-2.5 bg-slate-100 text-slate-700 rounded-xl text-sm font-bold hover:bg-slate-200 transition-all active:scale-95 disabled:opacity-50">
                                        <StepForward size={18} />
                                        <span>{status === 'waiting_input' ? 'Continuar' : 'Siguiente'}</span>
                                    </button>
                                    <button onClick={() => startExecution('fast')} disabled={status === 'executing'}
                                        className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200 active:scale-95 disabled:opacity-50">
                                        <span>Ejecutar Todo</span>
                                        <FastForward size={18} fill="currentColor" />
                                    </button>
                                </>
                            )}

                            {status === 'error' && (
                                <button onClick={() => startExecution('normal')} className="px-6 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-all active:scale-95 flex items-center gap-2">
                                    <RefreshCcw size={16} /> Reintentar
                                </button>
                            )}

                            {status === 'success' && (
                                <button onClick={onClose} className="px-6 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800 transition-all shadow-lg active:scale-95">
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
