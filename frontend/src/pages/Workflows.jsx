import React, { useState, useMemo, useEffect } from 'react';
import { Settings, Play, Trash2, Plus, Clock, Zap, Search, ArrowUpDown, ChevronUp, ChevronDown, RefreshCcw } from 'lucide-react';
import NewPipelineDrawer from '../components/NewPipelineDrawer';

export default function Workflows() {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busqueda, setBusqueda] = useState("");
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [executingId, setExecutingId] = useState(null);
  const [error, setError] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [editingWorkflowId, setEditingWorkflowId] = useState(null);
  const [drawerTitle, setDrawerTitle] = useState("Configurar Nuevo Pipeline");
  const [drawerData, setDrawerData] = useState(null);

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const fetchWorkflows = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/workflows');
      if (!response.ok) throw new Error('Error al conectar con el servidor');
      const data = await response.json();
      if (data.error) throw new Error(data.error);
      setWorkflows(data);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("No se pudo cargar la base de datos de evaluaciones.");
    } finally {
      setLoading(false);
    }
  };

  const handleEditWorkflow = async (workflowId) => {
    setEditingWorkflowId(workflowId);
    setDrawerTitle("Configurar Pipeline");
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/workflows/${workflowId}/config`);
      const data = await response.json();
      if (data.error) throw new Error(data.error);

      setDrawerData(data);
      setIsDrawerOpen(true);
    } catch (err) {
      console.error(err);
      alert("No se pudo cargar la configuración del pipeline.");
    } finally {
      setLoading(false);
    }
  };

  const handleSavePipeline = async (config) => {
    const isNew = !editingWorkflowId;
    const url = isNew
      ? `http://localhost:8000/api/workflows/config`
      : `http://localhost:8000/api/workflows/${editingWorkflowId}/config`;

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
        fetchWorkflows(); // Recargar para ver el nuevo item
      } else {
        throw new Error(data.error || "Error al guardar");
      }
    } catch (err) {
      console.error(err);
      alert("Error al guardar la configuración: " + err.message);
    }
  };

  const handleOpenNewPipeline = () => {
    setEditingWorkflowId(null);
    setDrawerTitle("Configurar Nuevo Pipeline");
    setDrawerData(null);
    setIsDrawerOpen(true);
  };

  const handleRunWorkflow = async (id) => {
    setExecutingId(id);
    try {
      const response = await fetch(`http://localhost:8000/api/workflows/${id}/run`, {
        method: 'POST',
      });
      const data = await response.json();

      if (data.status === 'success') {
        alert(`Pipeline ejecutado exitosamente:\n${data.message}`);
        fetchWorkflows(); // Recargar para ver la nueva fecha
      } else {
        throw new Error(data.message || data.error);
      }
    } catch (err) {
      console.error(err);
      alert(`Error al ejecutar el pipeline: ${err.message}`);
    } finally {
      setExecutingId(null);
    }
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const sortedAndFilteredWorkflows = useMemo(() => {
    let items = [...workflows].filter(wf =>
      (wf.evaluation?.toLowerCase() || "").includes(busqueda.toLowerCase()) ||
      (wf.description?.toLowerCase() || "").includes(busqueda.toLowerCase())
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
  }, [workflows, busqueda, sortConfig]);

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
              <Zap size={24} fill="white" />
            </div>
            Workflows de Datos
          </h1>
          <p className="text-slate-500 mt-2 text-sm font-medium">
            Administración de pipelines de evaluación.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={fetchWorkflows}
            className="bg-white hover:bg-slate-50 text-slate-600 p-2.5 rounded-xl border border-slate-200 transition-all shadow-sm"
            title="Refrescar datos"
          >
            <RefreshCcw size={20} className={loading ? "animate-spin" : ""} />
          </button>
          <button
            onClick={handleOpenNewPipeline}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl font-bold transition-all shadow-md shadow-indigo-100 flex items-center gap-2"
          >
            <Plus size={20} strokeWidth={3} />
            Nuevo Pipeline
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
                  onClick={() => handleSort('evaluation')}
                >
                  <div className="flex items-center gap-2">
                    Workflow <SortIcon columnKey="evaluation" />
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
                  onClick={() => handleSort('output')}
                >
                  <div className="flex items-center gap-2">
                    Output <SortIcon columnKey="output" />
                  </div>
                </th>
                <th
                  className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors"
                  onClick={() => handleSort('last_run')}
                >
                  <div className="flex items-center gap-2">
                    Última Ejecución <SortIcon columnKey="last_run" />
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
              ) : sortedAndFilteredWorkflows.length > 0 ? (
                sortedAndFilteredWorkflows.map((wf) => (
                  <tr key={wf.id_evaluation} className="hover:bg-slate-50/80 transition-colors group">
                    <td className="p-5">
                      <div className="font-bold text-slate-700">{wf.evaluation}</div>
                    </td>
                    <td className="p-5 text-slate-500 text-sm">
                      {wf.description}
                    </td>
                    <td className="p-5">
                      <span className="bg-slate-100 text-slate-500 text-[10px] font-bold px-2 py-1 rounded uppercase tracking-tighter">
                        {wf.output}
                      </span>
                    </td>
                    <td className="p-5 text-slate-500 text-sm font-medium">
                      {wf.last_run}
                    </td>
                    <td className="p-5 text-right flex justify-end gap-1">
                      <div className="flex justify-end gap-1 opacity-100 lg:opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => handleRunWorkflow(wf.id_evaluation)}
                          disabled={executingId !== null}
                          className={`p-2 rounded-xl transition-all ${executingId === wf.id_evaluation ? "text-indigo-600 bg-indigo-50" : "text-indigo-400 hover:text-indigo-600 hover:bg-indigo-50"}`}
                          title="Ejecutar ahora"
                        >
                          {executingId === wf.id_evaluation ?
                            <RefreshCcw size={18} className="animate-spin" /> :
                            <Play size={18} fill="currentColor" />
                          }
                        </button>
                        <button
                          onClick={() => handleEditWorkflow(wf.id_evaluation)}
                          className="p-2 text-slate-300 hover:text-slate-500 hover:bg-slate-100 rounded-xl transition-all"
                          title="Configurar"
                        >
                          <Settings size={18} />
                        </button>
                        <button className="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all" title="Eliminar">
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="p-12 text-center text-slate-400 italic">
                    No se encontraron workflows con ese criterio.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      {/* Drawer */}
      <NewPipelineDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        initialData={drawerData}
        title={drawerTitle}
        onSave={handleSavePipeline}
      />
    </div>
  );
}