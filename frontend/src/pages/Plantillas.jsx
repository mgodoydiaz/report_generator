import React, { useState, useMemo, useEffect } from 'react';
import { Settings, Trash2, Plus, Search, ArrowUpDown, ChevronUp, ChevronDown, RefreshCcw, FileText, Layout } from 'lucide-react';
import NewTemplateDrawer from '../components/NewTemplateDrawer';

export default function Plantillas() {
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);
    const [busqueda, setBusqueda] = useState("");
    const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
    const [error, setError] = useState(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [editingTemplateId, setEditingTemplateId] = useState(null);

    const [drawerData, setDrawerData] = useState(null);
    const [drawerTitle, setDrawerTitle] = useState("Nueva Plantilla");

    useEffect(() => {
        fetchTemplates();
    }, []);

    const fetchTemplates = async () => {
        setLoading(true);
        try {
            const response = await fetch('http://localhost:8000/api/templates');
            if (!response.ok) throw new Error('Error al conectar con el servidor');
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            setTemplates(data);
            setError(null);
        } catch (err) {
            console.error(err);
            setError("No se pudo cargar la base de datos de plantillas.");
        } finally {
            setLoading(false);
        }
    };

    const handleEditTemplate = async (templateId) => {
        setEditingTemplateId(templateId);
        setDrawerTitle("Editar Plantilla");
        setLoading(true);
        try {
            const response = await fetch(`http://localhost:8000/api/templates/${templateId}/config`);
            const data = await response.json();
            if (data.error) throw new Error(data.error);

            setDrawerData(data);
            setIsDrawerOpen(true);
        } catch (err) {
            console.error(err);
            alert("No se pudo cargar la configuración de la plantilla.");
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteTemplate = async (templateId) => {
        if (window.confirm("¿Estás seguro de que deseas eliminar esta plantilla?")) {
            // TODO: Implement delete logic
            console.log("Delete template", templateId);
        }
    }

    const handleOpenNewTemplate = () => {
        setEditingTemplateId(null);
        setDrawerTitle("Nueva Plantilla");
        setDrawerData(null);
        setIsDrawerOpen(true);
    };

    const handleSaveTemplate = async (config) => {
        const isNew = !editingTemplateId;
        const url = isNew
            ? `http://localhost:8000/api/templates/config`
            : `http://localhost:8000/api/templates/${editingTemplateId}/config`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            const data = await response.json();

            if (data.status === 'success') {
                alert(data.message);
                setIsDrawerOpen(false);
                fetchTemplates();
            } else {
                throw new Error(data.error || "Error al guardar");
            }
        } catch (err) {
            console.error(err);
            alert("Error al guardar la plantilla: " + err.message);
        }
    };

    const handleSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const sortedAndFilteredTemplates = useMemo(() => {
        let items = [...templates].filter(t =>
            (t.name?.toLowerCase() || "").includes(busqueda.toLowerCase()) ||
            (t.description?.toLowerCase() || "").includes(busqueda.toLowerCase())
        );

        if (sortConfig.key !== null) {
            items.sort((a, b) => {
                let aValue = a[sortConfig.key];
                let bValue = b[sortConfig.key];

                if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
                if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }
        return items;
    }, [templates, busqueda, sortConfig]);

    const SortIcon = ({ columnKey }) => {
        if (sortConfig.key !== columnKey) return <ArrowUpDown size={12} className="opacity-30" />;
        return sortConfig.direction === 'asc' ?
            <ChevronUp size={12} className="text-indigo-600" /> :
            <ChevronDown size={12} className="text-indigo-600" />;
    };

    return (
        <div className="max-w-6xl mx-auto">
            {/* Header */}
            <div className="flex items-start justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-3 tracking-tight">
                        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-100">
                            <FileText size={24} />
                        </div>
                        Plantillas
                    </h1>
                    <p className="text-slate-500 mt-2 text-sm font-medium">
                        Gestión de plantillas de informes y dashboards.
                    </p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={fetchTemplates}
                        className="bg-white hover:bg-slate-50 text-slate-600 p-2.5 rounded-xl border border-slate-200 transition-all shadow-sm"
                        title="Refrescar datos"
                    >
                        <RefreshCcw size={20} className={loading ? "animate-spin" : ""} />
                    </button>
                    <button
                        onClick={handleOpenNewTemplate}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl font-bold transition-all shadow-md shadow-indigo-100 flex items-center gap-2"
                    >
                        <Plus size={20} strokeWidth={3} />
                        Nueva Plantilla
                    </button>
                </div>
            </div>

            {/* Search */}
            <div className="relative mb-6">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Search className="h-5 w-5 text-slate-400" />
                </div>
                <input
                    type="text"
                    placeholder="Buscar por nombre o descripción..."
                    className="block w-full pl-12 pr-4 py-3.5 border border-slate-200 rounded-2xl bg-white focus:outline-none focus:ring-4 focus:ring-indigo-100 transition-all text-slate-600 placeholder:text-slate-400"
                    value={busqueda}
                    onChange={(e) => setBusqueda(e.target.value)}
                />
            </div>

            {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-100 text-red-600 rounded-2xl text-sm font-medium">
                    {error}
                </div>
            )}

            {/* Table Card */}
            <div className="bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden text-left">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-50/50 border-b border-slate-100">
                                <th
                                    className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors"
                                    onClick={() => handleSort('name')}
                                >
                                    <div className="flex items-center gap-2">
                                        Plantilla <SortIcon columnKey="name" />
                                    </div>
                                </th>
                                <th
                                    className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors"
                                    onClick={() => handleSort('description')}
                                >
                                    <div className="flex items-center gap-2">
                                        Descripción <SortIcon columnKey="description" />
                                    </div>
                                </th>
                                <th
                                    className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors"
                                    onClick={() => handleSort('type')}
                                >
                                    <div className="flex items-center gap-2">
                                        Tipo <SortIcon columnKey="type" />
                                    </div>
                                </th>
                                <th
                                    className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors"
                                    onClick={() => handleSort('updated_at')}
                                >
                                    <div className="flex items-center gap-2">
                                        Fecha Modificación <SortIcon columnKey="updated_at" />
                                    </div>
                                </th>
                                <th className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest text-right">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {loading ? (
                                <tr>
                                    <td colSpan="5" className="p-12 text-center text-slate-400">
                                        <div className="flex flex-col items-center gap-3">
                                            <RefreshCcw size={24} className="animate-spin text-indigo-500" />
                                            <p className="font-medium">Cargando datos...</p>
                                        </div>
                                    </td>
                                </tr>
                            ) : sortedAndFilteredTemplates.length > 0 ? (
                                sortedAndFilteredTemplates.map((template) => (
                                    <tr key={template.id_template} className="hover:bg-slate-50/80 transition-colors group">
                                        <td className="p-5">
                                            <div className="font-bold text-slate-700">{template.name}</div>
                                        </td>
                                        <td className="p-5 text-slate-500 text-sm">
                                            {template.description}
                                        </td>
                                        <td className="p-5">
                                            <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-tighter ${template.type === 'Dashboard'
                                                ? 'bg-purple-100 text-purple-600'
                                                : 'bg-blue-100 text-blue-600'
                                                }`}>
                                                {template.type}
                                            </span>
                                        </td>
                                        <td className="p-5 text-slate-500 text-sm font-medium">
                                            {template.updated_at}
                                        </td>
                                        <td className="p-5 text-right flex justify-end gap-1">
                                            <div className="flex justify-end gap-1 opacity-100 lg:opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    onClick={() => handleEditTemplate(template.id_template)}
                                                    className="p-2 text-slate-300 hover:text-slate-500 hover:bg-slate-100 rounded-xl transition-all"
                                                    title="Configurar"
                                                >
                                                    <Settings size={18} />
                                                </button>
                                                <button
                                                    onClick={() => handleDeleteTemplate(template.id_template)}
                                                    className="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
                                                    title="Eliminar"
                                                >
                                                    <Trash2 size={18} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan="5" className="p-12 text-center text-slate-400 italic">
                                        No se encontraron plantillas con ese criterio.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
            <NewTemplateDrawer
                isOpen={isDrawerOpen}
                onClose={() => setIsDrawerOpen(false)}
                initialData={drawerData}
                title={drawerTitle}
                onSave={handleSaveTemplate}
            />
        </div>
    );
}
