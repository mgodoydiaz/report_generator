import React, { useState, useEffect, useMemo } from 'react';
import { Play, Search, RefreshCcw, Rocket, Activity, CheckCircle2, Clock, ArrowRight } from 'lucide-react';
import PipelineExecutionModal from '../components/PipelineExecutionModal';
import { API_BASE_URL, getFormatStyle } from '../constants';

export default function Execution() {
    const [pipelines, setPipelines] = useState([]);
    const [loading, setLoading] = useState(true);
    const [busqueda, setBusqueda] = useState("");
    const [isExecutionModalOpen, setIsExecutionModalOpen] = useState(false);
    const [activePipeline, setActivePipeline] = useState(null);

    useEffect(() => {
        fetchPipelines();
    }, []);

    const fetchPipelines = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/workflows`);
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            setPipelines(data);
        } catch (err) {
            console.error("Error loading pipelines:", err);
        } finally {
            setLoading(false);
        }
    };

    const handleRunPipeline = (pipeline) => {
        setActivePipeline(pipeline);
        setIsExecutionModalOpen(true);
    };

    const filteredPipelines = useMemo(() => {
        return pipelines.filter(p =>
            (p.pipeline?.toLowerCase() || "").includes(busqueda.toLowerCase()) ||
            (p.description?.toLowerCase() || "").includes(busqueda.toLowerCase())
        );
    }, [pipelines, busqueda]);

    return (
        <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-500">
            {/* Header Profesional */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-4xl font-black text-slate-800 tracking-tight flex items-center gap-3">
                        <div className="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-indigo-100 ring-4 ring-indigo-50">
                            <Rocket size={28} />
                        </div>
                        Centro de Ejecución
                    </h1>
                    <p className="text-slate-500 mt-2 text-lg font-medium">
                        Selecciona un proceso para transformar datos y generar reportes.
                    </p>
                </div>
                <button
                    onClick={fetchPipelines}
                    className="flex items-center gap-2 px-4 py-2 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all font-bold text-sm"
                >
                    <RefreshCcw size={18} className={loading ? "animate-spin" : ""} />
                    Actualizar Lista
                </button>
            </div>

            {/* Barra de Búsqueda Estilizada */}
            <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                    <Search className="h-6 w-6 text-slate-400 group-focus-within:text-indigo-500 transition-colors" />
                </div>
                <input
                    type="text"
                    placeholder="Buscar proceso por nombre o descripción..."
                    className="block w-full pl-14 pr-6 py-5 border-none rounded-3xl bg-white shadow-xl shadow-slate-100/50 focus:ring-4 focus:ring-indigo-100 transition-all text-slate-700 text-lg placeholder:text-slate-400 font-medium"
                    value={busqueda}
                    onChange={(e) => setBusqueda(e.target.value)}
                />
            </div>

            {/* Grid de Pipelines */}
            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="h-48 bg-white rounded-3xl animate-pulse border border-slate-100" />
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {filteredPipelines.map((p) => (
                        <div
                            key={p.id_evaluation}
                            className="group bg-white rounded-3xl border border-slate-100 p-6 shadow-sm hover:shadow-2xl hover:shadow-indigo-100 hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between"
                        >
                            <div className="space-y-4">
                                <div className="flex items-start justify-between">
                                    <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors duration-300">
                                        <Activity size={24} />
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className={`px-2 py-0.5 rounded-lg border text-[10px] font-medium uppercase tracking-widest ${getFormatStyle(p.input)}`}>
                                            {p.input || "EXCEL"}
                                        </span>
                                        <ArrowRight size={12} className="text-slate-300" />
                                        <span className={`px-2 py-0.5 rounded-lg border text-[10px] font-medium uppercase tracking-widest ${getFormatStyle(p.output)}`}>
                                            {p.output}
                                        </span>
                                    </div>
                                </div>

                                <div>
                                    <h3 className="text-xl font-extrabold text-slate-800 line-clamp-1">{p.pipeline}</h3>
                                    <p className="text-slate-500 text-sm mt-1 line-clamp-2 min-h-10 font-medium">
                                        {p.description || "Sin descripción disponible."}
                                    </p>
                                </div>

                                <div className="flex items-center gap-4 text-[11px] text-slate-400 font-bold uppercase tracking-tighter">
                                    <div className="flex items-center gap-1">
                                        <Clock size={12} />
                                        {p.last_run ? p.last_run : "Sin ejecuciones"}
                                    </div>
                                    {p.last_run && (
                                        <div className="flex items-center gap-1 text-emerald-500">
                                            <CheckCircle2 size={12} />
                                            Listo
                                        </div>
                                    )}
                                </div>
                            </div>

                            <button
                                onClick={() => handleRunPipeline(p)}
                                className="mt-6 w-full bg-slate-50 group-hover:bg-indigo-600 text-slate-600 group-hover:text-white py-4 rounded-2xl font-black transition-all duration-300 flex items-center justify-center gap-3 shadow-inner group-hover:shadow-lg group-hover:shadow-indigo-200 overflow-hidden relative"
                            >
                                <Play size={20} fill="currentColor" />
                                <span>Ejecutar Proceso</span>
                                <div className="absolute inset-0 bg-white/20 translate-y-full group-active:translate-y-0 transition-transform duration-100" />
                            </button>
                        </div>
                    ))}

                    {filteredPipelines.length === 0 && (
                        <div className="col-span-full py-20 bg-slate-50/50 rounded-3xl border-2 border-dashed border-slate-200 flex flex-col items-center justify-center text-slate-400">
                            <Search size={48} className="mb-4 opacity-20" />
                            <p className="text-lg font-bold">No se encontraron procesos</p>
                            <p className="text-sm">Prueba con otros términos de búsqueda</p>
                        </div>
                    )}
                </div>
            )}

            {/* Modal de Ejecución Reutilizado */}
            <PipelineExecutionModal
                isOpen={isExecutionModalOpen}
                onClose={() => {
                    setIsExecutionModalOpen(false);
                    fetchPipelines();
                }}
                pipelineId={activePipeline?.id_evaluation}
                pipelineName={activePipeline?.pipeline}
            />
        </div>
    );
}
