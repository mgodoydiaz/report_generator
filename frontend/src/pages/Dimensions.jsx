import React, { useState, useMemo, useEffect } from 'react';
import { Layers, Plus, Search, ArrowUpDown, ChevronUp, ChevronDown, RefreshCcw, Trash2, Settings, ShieldCheck, List, Type, Hash } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import NewDimensionDrawer from '../components/NewDimensionDrawer';

export default function Dimensions() {
    const [dimensions, setDimensions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [busqueda, setBusqueda] = useState("");
    const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [editingDimension, setEditingDimension] = useState(null);
    const [drawerTitle, setDrawerTitle] = useState("Nueva Dimensión");

    useEffect(() => {
        fetchDimensions();
    }, []);

    const fetchDimensions = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/dimensions`);
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            setDimensions(data);
        } catch (err) {
            toast.error("Error al cargar dimensiones: " + err.message);
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

    const handleNewDimension = () => {
        setEditingDimension(null);
        setDrawerTitle("Nueva Dimensión");
        setIsDrawerOpen(true);
    };

    const handleEditDimension = (dim) => {
        setEditingDimension(dim);
        setDrawerTitle("Editar Dimensión");
        setIsDrawerOpen(true);
    };

    const handleDeleteDimension = async (id, name) => {
        if (!confirm(`¿Estás seguro de eliminar la dimensión "${name}"? Se borrarán todos sus valores asociados.`)) return;

        try {
            const res = await fetch(`${API_BASE_URL}/dimensions/${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            toast.success("Dimensión eliminada");
            fetchDimensions();
        } catch (err) {
            toast.error(err.message);
        }
    };

    const handleSaveCallback = () => {
        fetchDimensions();
    };

    const sortedAndFilteredData = useMemo(() => {
        let items = dimensions.filter(d =>
            d.name.toLowerCase().includes(busqueda.toLowerCase()) ||
            d.description.toLowerCase().includes(busqueda.toLowerCase())
        );

        if (sortConfig.key) {
            items.sort((a, b) => {
                if (a[sortConfig.key] < b[sortConfig.key]) return sortConfig.direction === 'asc' ? -1 : 1;
                if (a[sortConfig.key] > b[sortConfig.key]) return sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }
        return items;
    }, [dimensions, busqueda, sortConfig]);

    const SortIcon = ({ columnKey }) => {
        if (sortConfig.key !== columnKey) return <ArrowUpDown size={14} className="text-slate-300 dark:text-slate-600" />;
        return sortConfig.direction === 'asc'
            ? <ChevronUp size={14} className="text-indigo-600 dark:text-indigo-400" />
            : <ChevronDown size={14} className="text-indigo-600 dark:text-indigo-400" />;
    };

    return (
        <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div className="space-y-1">
                    <h1 className="text-4xl font-black text-slate-800 dark:text-white tracking-tight flex items-center gap-3">
                        <div className="w-10 h-10 bg-emerald-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-emerald-100 dark:shadow-emerald-900/20">
                            <Layers size={22} />
                        </div>
                        Dimensiones
                    </h1>
                    <p className="text-slate-400 dark:text-slate-500 text-sm font-medium">
                        Define las variables categóricas (ej: Sedes, Carreras) y sus valores permitidos.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={fetchDimensions} className="p-3 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-xl transition-all">
                        <RefreshCcw size={20} className={loading ? "animate-spin" : ""} />
                    </button>
                    <button onClick={handleNewDimension} className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-3 rounded-2xl font-bold text-sm shadow-xl shadow-emerald-100 transition-all active:scale-95">
                        <Plus size={18} strokeWidth={3} />
                        Nueva Dimensión
                    </button>
                </div>
            </div>

            {/* Search */}
            <div className="flex items-center gap-3 bg-slate-100/50 dark:bg-slate-900/50 p-2 rounded-2xl border border-slate-200/50 dark:border-slate-800/50">
                <div className="relative flex-1">
                    <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
                    <input
                        type="text"
                        placeholder="Buscar dimensión..."
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
                                <th onClick={() => handleSort('name')} className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-emerald-600 transition-colors">
                                    <div className="flex items-center gap-2">Nombre <SortIcon columnKey="name" /></div>
                                </th>
                                <th onClick={() => handleSort('description')} className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-emerald-600 transition-colors">
                                    <div className="flex items-center gap-2">Descripción <SortIcon columnKey="description" /></div>
                                </th>
                                <th onClick={() => handleSort('data_type')} className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-emerald-600 transition-colors">
                                    <div className="flex items-center gap-2">Tipo <SortIcon columnKey="data_type" /></div>
                                </th>
                                <th onClick={() => handleSort('validation_mode')} className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-emerald-600 transition-colors">
                                    <div className="flex items-center gap-2">Validación <SortIcon columnKey="validation_mode" /></div>
                                </th>
                                <th className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest text-right">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {loading ? (
                                <tr><td colSpan="5" className="p-12 text-center text-slate-400">Cargando...</td></tr>
                            ) : sortedAndFilteredData.length > 0 ? (
                                sortedAndFilteredData.map((d) => (
                                    <tr key={d.id_dimension} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/80 transition-colors group">
                                        <td className="p-5 font-bold text-slate-700 dark:text-slate-200">{d.name}</td>
                                        <td className="p-5 text-slate-500 text-sm">{d.description}</td>
                                        <td className="p-5">
                                            <span className={`flex items-center gap-1 w-fit px-2 py-1 rounded-md text-[10px] font-bold border ${d.data_type === 'str' ? 'bg-indigo-50 text-indigo-600 border-indigo-100' : 'bg-amber-50 text-amber-600 border-amber-100'}`}>
                                                {d.data_type === 'str' ? <Type size={12} /> : <Hash size={12} />}
                                                {d.data_type === 'str' ? 'TEXTO' : 'NUMÉRICO'}
                                            </span>
                                        </td>
                                        <td className="p-5">
                                            <span className={`flex items-center gap-1 w-fit px-2 py-1 rounded-md text-[10px] font-bold border ${d.validation_mode === 'list' ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 'bg-slate-50 text-slate-500 border-slate-100'}`}>
                                                {d.validation_mode === 'list' ? <List size={12} /> : <ShieldCheck size={12} />}
                                                {d.validation_mode === 'list' ? 'LISTA CERRADA' : 'LIBRE'}
                                            </span>
                                        </td>
                                        <td className="p-5 text-right flex justify-end gap-1">
                                            <button onClick={() => handleEditDimension(d)} className="p-2 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-xl transition-all" title="Editar">
                                                <Settings size={18} />
                                            </button>
                                            <button onClick={() => handleDeleteDimension(d.id_dimension, d.name)} className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all" title="Eliminar">
                                                <Trash2 size={18} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr><td colSpan="5" className="p-12 text-center text-slate-400">No hay dimensiones registradas.</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <NewDimensionDrawer
                isOpen={isDrawerOpen}
                onClose={() => setIsDrawerOpen(false)}
                title={drawerTitle}
                initialData={editingDimension}
                onSave={handleSaveCallback}
            />
        </div>
    );
}
