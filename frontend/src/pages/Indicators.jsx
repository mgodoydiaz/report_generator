import React, { useState, useMemo, useEffect } from 'react';
import { Microscope, Plus, Search, ArrowUpDown, ChevronUp, ChevronDown, RefreshCcw, Trash2, Settings, ClipboardCheck, BookOpen, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import NewIndicatorDrawer from '../components/NewIndicatorDrawer';

export default function Indicators() {
    const [indicators, setIndicators] = useState([]);
    const [metricsMap, setMetricsMap] = useState({});
    const [loading, setLoading] = useState(true);
    const [busqueda, setBusqueda] = useState("");
    const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [editingIndicator, setEditingIndicator] = useState(null);
    const [drawerTitle, setDrawerTitle] = useState("Nuevo Indicador");

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [indicatorsRes, metricsRes] = await Promise.all([
                fetch(`${API_BASE_URL}/indicators`).catch(() => ({ ok: false, status: 404 })),
                fetch(`${API_BASE_URL}/metrics`).catch(() => ({ ok: false, status: 404 }))
            ]);

            // Handling the case where indicators endpoint is not ready
            let indicatorsData = [];
            if (indicatorsRes.ok) {
                indicatorsData = await indicatorsRes.json();
                if (indicatorsData.error) throw new Error(indicatorsData.error);
            }

            let metricsData = [];
            if (metricsRes.ok) {
                metricsData = await metricsRes.json();
                if (metricsData.error) throw new Error(metricsData.error);
            }

            setIndicators(indicatorsData);

            const mMap = {};
            metricsData.forEach(m => mMap[m.id_metric] = m.name);
            setMetricsMap(mMap);

        } catch (err) {
            toast.error("Error al cargar datos: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const handleNewIndicator = () => {
        setEditingIndicator(null);
        setDrawerTitle("Nuevo Indicador");
        setIsDrawerOpen(true);
    };

    const handleEditIndicator = (indicator) => {
        setEditingIndicator(indicator);
        setDrawerTitle("Editar Indicador");
        setIsDrawerOpen(true);
    };

    const handleDeleteIndicator = async (id, name) => {
        if (!confirm(`¿Estás seguro de eliminar el indicador "${name}"?`)) return;

        try {
            const res = await fetch(`${API_BASE_URL}/indicators/${id}`, { method: 'DELETE' });
            if (!res.ok) {
                // If endpoint doesn't exist yet, we mock deletion
                setIndicators(prev => prev.filter(i => i.id_indicator !== id));
                toast.success("Indicador eliminado (Mocked)");
                return;
            }
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            toast.success("Indicador eliminado");
            fetchData();
        } catch (err) {
            toast.error(err.message);
        }
    };

    const handleSaveCallback = (savedData) => {
        // Optimistic UI update or fetch data again
        setIndicators(prev => {
            const exists = prev.find(i => i.id_indicator === savedData.id_indicator);
            if (exists) {
                return prev.map(i => i.id_indicator === savedData.id_indicator ? savedData : i);
            } else {
                return [...prev, savedData];
            }
        });
        // We can also call fetchData() but given it might be a mocked API right now, optimistic approach is safer.
    };

    const sortedAndFilteredData = useMemo(() => {
        let items = indicators.filter(i =>
            i.name?.toLowerCase().includes(busqueda.toLowerCase()) ||
            i.description?.toLowerCase().includes(busqueda.toLowerCase())
        );

        if (sortConfig.key) {
            items.sort((a, b) => {
                if (a[sortConfig.key] < b[sortConfig.key]) return sortConfig.direction === 'asc' ? -1 : 1;
                if (a[sortConfig.key] > b[sortConfig.key]) return sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }
        return items;
    }, [indicators, busqueda, sortConfig]);

    const SortIcon = ({ columnKey }) => {
        if (sortConfig.key !== columnKey) return <ArrowUpDown size={14} className="text-slate-300 dark:text-slate-600" />;
        return sortConfig.direction === 'asc'
            ? <ChevronUp size={14} className="text-indigo-600 dark:text-indigo-400" />
            : <ChevronDown size={14} className="text-indigo-600 dark:text-indigo-400" />;
    };

    const getTypeIcon = (type) => {
        switch (type) {
            case 'Evaluación': return <ClipboardCheck size={12} />;
            case 'Estudio': return <BookOpen size={12} />;
            case 'Alerta': return <AlertTriangle size={12} />;
            default: return <Microscope size={12} />;
        }
    };

    const getTypeStyles = (type) => {
        switch (type) {
            case 'Evaluación': return 'bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800';
            case 'Estudio': return 'bg-indigo-50 text-indigo-600 border-indigo-100 dark:bg-indigo-900/20 dark:text-indigo-400 dark:border-indigo-800';
            case 'Alerta': return 'bg-rose-50 text-rose-600 border-rose-100 dark:bg-rose-900/20 dark:text-rose-400 dark:border-rose-800';
            default: return 'bg-slate-50 text-slate-600 border-slate-100 dark:bg-slate-900/20 dark:text-slate-400 dark:border-slate-800';
        }
    };

    return (
        <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div className="space-y-1">
                    <h1 className="text-4xl font-black text-slate-800 dark:text-white tracking-tight flex items-center gap-3">
                        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-100 dark:shadow-indigo-900/20">
                            <Microscope size={22} />
                        </div>
                        Indicadores
                    </h1>
                    <p className="text-slate-400 dark:text-slate-500 text-sm font-medium">
                        Administra y consolida los indicadores con sus respectivas métricas.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={fetchData} className="p-3 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all">
                        <RefreshCcw size={20} className={loading ? "animate-spin" : ""} />
                    </button>
                    <button onClick={handleNewIndicator} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-3 rounded-2xl font-bold text-sm shadow-xl shadow-indigo-100 transition-all active:scale-95">
                        <Plus size={18} strokeWidth={3} />
                        Crear Indicador
                    </button>
                </div>
            </div>

            {/* Search */}
            <div className="flex items-center gap-3 bg-slate-100/50 dark:bg-slate-900/50 p-2 rounded-2xl border border-slate-200/50 dark:border-slate-800/50">
                <div className="relative flex-1">
                    <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
                    <input
                        type="text"
                        placeholder="Buscar indicador..."
                        className="w-full bg-transparent border-none py-3 pl-12 pr-4 focus:ring-0 text-sm text-slate-600 dark:text-slate-300 placeholder:text-slate-400 font-medium"
                        value={busqueda}
                        onChange={(e) => setBusqueda(e.target.value)}
                    />
                </div>
            </div>

            {/* Table */}
            <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden text-left font-sans">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                                <th onClick={() => handleSort('name')} className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors">
                                    <div className="flex items-center gap-2">Nombre <SortIcon columnKey="name" /></div>
                                </th>
                                <th onClick={() => handleSort('description')} className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors">
                                    <div className="flex items-center gap-2">Descripción <SortIcon columnKey="description" /></div>
                                </th>
                                <th onClick={() => handleSort('type')} className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors">
                                    <div className="flex items-center gap-2">Tipo <SortIcon columnKey="type" /></div>
                                </th>
                                <th className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest">Métricas Asociadas</th>
                                <th className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest text-right">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                            {loading ? (
                                <tr><td colSpan="5" className="p-12 text-center text-slate-400">Cargando...</td></tr>
                            ) : sortedAndFilteredData.length > 0 ? (
                                sortedAndFilteredData.map((indicator) => (
                                    <tr key={indicator.id_indicator} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/80 transition-colors group">
                                        <td className="p-5 font-bold text-slate-700 dark:text-slate-200">{indicator.name}</td>
                                        <td className="p-5 text-slate-500 text-sm max-w-xs truncate">{indicator.description}</td>
                                        <td className="p-5">
                                            <span className={`flex items-center gap-1 w-fit px-2 py-1 rounded-md text-[10px] uppercase font-bold border ${getTypeStyles(indicator.type)}`}>
                                                {getTypeIcon(indicator.type)}
                                                {indicator.type}
                                            </span>
                                        </td>
                                        <td className="p-5">
                                            <div className="flex flex-wrap gap-1">
                                                {indicator.metric_ids && indicator.metric_ids.length > 0 ? (
                                                    indicator.metric_ids.map(metricId => (
                                                        <span key={metricId} className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-[10px] font-medium border border-slate-200 dark:border-slate-700 flex items-center gap-1">
                                                            <Microscope size={10} />
                                                            {metricsMap[metricId] || `Metric #${metricId}`}
                                                        </span>
                                                    ))
                                                ) : (
                                                    <span className="text-slate-300 text-xs italic">Sin métricas</span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="p-5 text-right flex justify-end gap-1">
                                            <button onClick={() => handleEditIndicator(indicator)} className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-slate-800 rounded-xl transition-all" title="Editar">
                                                <Settings size={18} />
                                            </button>
                                            <button onClick={() => handleDeleteIndicator(indicator.id_indicator, indicator.name)} className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-slate-800 rounded-xl transition-all" title="Eliminar">
                                                <Trash2 size={18} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr><td colSpan="5" className="p-12 text-center text-slate-400">No hay indicadores registrados.</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <NewIndicatorDrawer
                isOpen={isDrawerOpen}
                onClose={() => setIsDrawerOpen(false)}
                title={drawerTitle}
                initialData={editingIndicator}
                onSave={handleSaveCallback}
            />
        </div>
    );
}
