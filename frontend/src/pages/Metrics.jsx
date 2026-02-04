import React, { useState, useMemo, useEffect } from 'react';
import { Box, Plus, Search, ArrowUpDown, ChevronUp, ChevronDown, RefreshCcw, Trash2, Settings, Hash, Type, Layers } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import NewMetricDrawer from '../components/NewMetricDrawer';

export default function Metrics() {
    const [metrics, setMetrics] = useState([]);
    const [dimensionsMap, setDimensionsMap] = useState({});
    const [loading, setLoading] = useState(true);
    const [busqueda, setBusqueda] = useState("");
    const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [editingMetric, setEditingMetric] = useState(null);
    const [drawerTitle, setDrawerTitle] = useState("Nueva Métrica");

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            // Cargar Métricas y Dimensiones en paralelo para mapear nombres
            const [metricsRes, dimsRes] = await Promise.all([
                fetch(`${API_BASE_URL}/metrics`),
                fetch(`${API_BASE_URL}/dimensions`)
            ]);

            const metricsData = await metricsRes.json();
            const dimsData = await dimsRes.json();

            if (metricsData.error) throw new Error(metricsData.error);
            setMetrics(metricsData);

            // Crear mapa de dimensiones {id: nombre}
            const dMap = {};
            if (!dimsData.error) {
                dimsData.forEach(d => dMap[d.id_dimension] = d.name);
            }
            setDimensionsMap(dMap);

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

    const handleNewMetric = () => {
        setEditingMetric(null);
        setDrawerTitle("Nueva Métrica");
        setIsDrawerOpen(true);
    };

    const handleEditMetric = (metric) => {
        setEditingMetric(metric);
        setDrawerTitle("Editar Métrica");
        setIsDrawerOpen(true);
    };

    const handleDeleteMetric = async (id, name) => {
        if (!confirm(`¿Estás seguro de eliminar la métrica "${name}"? Se borrarán todos los datos históricos asociados.`)) return;

        try {
            const res = await fetch(`${API_BASE_URL}/metrics/${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            toast.success("Métrica eliminada");
            fetchData();
        } catch (err) {
            toast.error(err.message);
        }
    };

    const handleSaveCallback = () => {
        fetchData();
    };

    const sortedAndFilteredData = useMemo(() => {
        let items = metrics.filter(m =>
            m.name.toLowerCase().includes(busqueda.toLowerCase()) ||
            m.description.toLowerCase().includes(busqueda.toLowerCase())
        );

        if (sortConfig.key) {
            items.sort((a, b) => {
                if (a[sortConfig.key] < b[sortConfig.key]) return sortConfig.direction === 'asc' ? -1 : 1;
                if (a[sortConfig.key] > b[sortConfig.key]) return sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }
        return items;
    }, [metrics, busqueda, sortConfig]);

    const SortIcon = ({ columnKey }) => {
        if (sortConfig.key !== columnKey) return <ArrowUpDown size={14} className="text-slate-300 dark:text-slate-600" />;
        return sortConfig.direction === 'asc'
            ? <ChevronUp size={14} className="text-indigo-600 dark:text-indigo-400" />
            : <ChevronDown size={14} className="text-indigo-600 dark:text-indigo-400" />;
    };

    const getDataTypeIcon = (type) => {
        switch (type) {
            case 'int': return <Hash size={12} />;
            case 'float': return <Hash size={12} />;
            case 'str': return <Type size={12} />;
            case 'object': return <Box size={12} />;
            default: return <Hash size={12} />;
        }
    };

    const getDataTypeLabel = (type) => {
        switch (type) {
            case 'int': return 'ENTERO';
            case 'float': return 'DECIMAL';
            case 'str': return 'TEXTO';
            case 'object': return 'OBJETO';
            default: return 'NUMÉRICO';
        }
    };

    return (
        <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div className="space-y-1">
                    <h1 className="text-4xl font-black text-slate-800 dark:text-white tracking-tight flex items-center gap-3">
                        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-100 dark:shadow-indigo-900/20">
                            <Box size={22} />
                        </div>
                        Métricas
                    </h1>
                    <p className="text-slate-400 dark:text-slate-500 text-sm font-medium">
                        Administra los indicadores y variables que mides en tus reportes.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={fetchData} className="p-3 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all">
                        <RefreshCcw size={20} className={loading ? "animate-spin" : ""} />
                    </button>
                    <button onClick={handleNewMetric} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-3 rounded-2xl font-bold text-sm shadow-xl shadow-indigo-100 transition-all active:scale-95">
                        <Plus size={18} strokeWidth={3} />
                        Nueva Métrica
                    </button>
                </div>
            </div>

            {/* Search */}
            <div className="flex items-center gap-3 bg-slate-100/50 dark:bg-slate-900/50 p-2 rounded-2xl border border-slate-200/50 dark:border-slate-800/50">
                <div className="relative flex-1">
                    <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
                    <input
                        type="text"
                        placeholder="Buscar métrica..."
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
                                <th onClick={() => handleSort('data_type')} className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors">
                                    <div className="flex items-center gap-2">Tipo <SortIcon columnKey="data_type" /></div>
                                </th>
                                <th className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest">Dimensiones</th>
                                <th className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest text-right">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {loading ? (
                                <tr><td colSpan="5" className="p-12 text-center text-slate-400">Cargando...</td></tr>
                            ) : sortedAndFilteredData.length > 0 ? (
                                sortedAndFilteredData.map((m) => (
                                    <tr key={m.id_metric} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/80 transition-colors group">
                                        <td className="p-5 font-bold text-slate-700 dark:text-slate-200">{m.name}</td>
                                        <td className="p-5 text-slate-500 text-sm max-w-xs truncate">{m.description}</td>
                                        <td className="p-5">
                                            <span className={`flex items-center gap-1 w-fit px-2 py-1 rounded-md text-[10px] font-bold border 
                                                ${m.data_type === 'object' ? 'bg-purple-50 text-purple-600 border-purple-100' :
                                                    m.data_type === 'str' ? 'bg-amber-50 text-amber-600 border-amber-100' :
                                                        'bg-indigo-50 text-indigo-600 border-indigo-100'}`}>
                                                {getDataTypeIcon(m.data_type)}
                                                {getDataTypeLabel(m.data_type)}
                                            </span>
                                        </td>
                                        <td className="p-5">
                                            <div className="flex flex-wrap gap-1">
                                                {m.dimension_ids && m.dimension_ids.length > 0 ? (
                                                    m.dimension_ids.map(dimId => (
                                                        <span key={dimId} className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-[10px] font-medium border border-slate-200 dark:border-slate-700 flex items-center gap-1">
                                                            <Layers size={10} />
                                                            {dimensionsMap[dimId] || dimId}
                                                        </span>
                                                    ))
                                                ) : (
                                                    <span className="text-slate-300 text-xs italic">Sin dimensiones</span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="p-5 text-right flex justify-end gap-1">
                                            <button onClick={() => handleEditMetric(m)} className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all" title="Editar">
                                                <Settings size={18} />
                                            </button>
                                            <button onClick={() => handleDeleteMetric(m.id_metric, m.name)} className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all" title="Eliminar">
                                                <Trash2 size={18} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr><td colSpan="5" className="p-12 text-center text-slate-400">No hay métricas registradas.</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <NewMetricDrawer
                isOpen={isDrawerOpen}
                onClose={() => setIsDrawerOpen(false)}
                title={drawerTitle}
                initialData={editingMetric}
                onSave={handleSaveCallback}
            />
        </div>
    );
}
