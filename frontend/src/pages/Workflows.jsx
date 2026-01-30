import React, { useState, useMemo, useEffect } from 'react';
import { Settings, Play, Trash2, Plus, Clock, Workflow, Search, ArrowUpDown, ChevronUp, ChevronDown, RefreshCcw, Copy, ArrowRight } from 'lucide-react';
import NewPipelineDrawer from '../components/NewPipelineDrawer';
import WorkflowExecutionModal from '../components/WorkflowExecutionModal';
import { API_BASE_URL, getFormatStyle } from '../constants';

export default function Workflows() {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busqueda, setBusqueda] = useState("");
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [executingId, setExecutingId] = useState(null);
  const [error, setError] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [editingWorkflowId, setEditingWorkflowId] = useState(null);
  const [drawerTitle, setDrawerTitle] = useState("Configurar Nuevo Proceso");
  const [editingData, setEditingData] = useState(null);
  const [isExecutionModalOpen, setIsExecutionModalOpen] = useState(false);
  const [activeWorkflow, setActiveWorkflow] = useState(null);

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const fetchWorkflows = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/workflows`);
      const data = await response.json();
      if (data.error) throw new Error(data.error);
      setWorkflows(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRunWorkflow = (workflow) => {
    setActiveWorkflow(workflow);
    setIsExecutionModalOpen(true);
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const handleEditWorkflow = async (id) => {
    setEditingWorkflowId(id);
    setDrawerTitle("Editar Proceso");
    try {
      const response = await fetch(`${API_BASE_URL}/workflows/${id}/config`);
      const configData = await response.json();
      if (configData.error) throw new Error(configData.error);
      setEditingData(configData);
      setIsDrawerOpen(true);
    } catch (err) {
      alert("Error al cargar configuración: " + err.message);
    }
  };

  const handleDuplicateWorkflow = async (id) => {
    try {
      const response = await fetch(`${API_BASE_URL}/workflows/${id}/config`);
      const configData = await response.json();
      if (configData.error) throw new Error(configData.error);

      const newConfig = {
        ...configData,
        workflow_metadata: {
          ...configData.workflow_metadata,
          name: `${configData.workflow_metadata.name} (Copia)`
        }
      };

      const saveResponse = await fetch(`${API_BASE_URL}/workflows/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      });
      const result = await saveResponse.json();
      if (result.error) throw new Error(result.error);

      fetchWorkflows();
    } catch (err) {
      alert("Error al duplicar: " + err.message);
    }
  };

  const handleNewWorkflow = () => {
    setEditingWorkflowId(null);
    setEditingData(null);
    setDrawerTitle("Configurar Nuevo Proceso");
    setIsDrawerOpen(true);
  };

  const handleSaveWorkflow = async (config) => {
    try {
      const url = editingWorkflowId
        ? `${API_BASE_URL}/workflows/${editingWorkflowId}/config`
        : `${API_BASE_URL}/workflows/config`;

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });

      const result = await response.json();
      if (result.error) throw new Error(result.error);

      setIsDrawerOpen(false);
      fetchWorkflows();
    } catch (err) {
      alert("Error al guardar: " + err.message);
    }
  };

  const handleDeleteWorkflow = async (id, name) => {
    if (!confirm(`¿Estás seguro de que deseas eliminar el proceso "${name}"? Esta acción no se puede deshacer.`)) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/workflows/${id}`, {
        method: 'DELETE'
      });
      const result = await response.json();
      if (result.error) throw new Error(result.error);

      fetchWorkflows();
    } catch (err) {
      alert("Error al eliminar: " + err.message);
    }
  };

  const sortedAndFilteredWorkflows = useMemo(() => {
    let items = workflows.filter(wf =>
      wf.evaluation.toLowerCase().includes(busqueda.toLowerCase()) ||
      wf.description.toLowerCase().includes(busqueda.toLowerCase())
    );

    if (sortConfig.key) {
      items.sort((a, b) => {
        if (a[sortConfig.key] < b[sortConfig.key]) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (a[sortConfig.key] > b[sortConfig.key]) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }
    return items;
  }, [workflows, busqueda, sortConfig]);

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <ArrowUpDown size={12} className="text-slate-300" />;
    return sortConfig.direction === 'asc' ? <ChevronUp size={12} className="text-indigo-600" /> : <ChevronDown size={12} className="text-indigo-600" />;
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
      {/* Header section con Título Principal y Stats rápidos */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-4xl font-black text-slate-800 tracking-tight flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-100">
              <Workflow size={22} />
            </div>
            Gestión de Procesos
          </h1>
          <p className="text-slate-400 text-sm font-medium">
            Administra los flujos de trabajo, automatizaciones y scripts de procesamiento.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchWorkflows}
            className="p-3 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all"
            title="Recargar"
          >
            <RefreshCcw size={20} className={loading ? "animate-spin" : ""} />
          </button>
          <button
            onClick={handleNewWorkflow}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-3 rounded-2xl font-bold text-sm shadow-xl shadow-indigo-100 transition-all active:scale-95"
          >
            <Plus size={18} strokeWidth={3} />
            Nuevo Proceso
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex items-center gap-3 bg-slate-100/50 p-2 rounded-2xl border border-slate-200/50">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar por proceso, descripción o tag..."
            className="w-full bg-transparent border-none py-3 pl-12 pr-4 focus:ring-0 text-sm text-slate-600 placeholder:text-slate-400 font-medium"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </div>
        <div className="h-6 w-px bg-slate-300 mx-2"></div>
        <div className="px-4 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
          {sortedAndFilteredWorkflows.length} Procesos
        </div>
      </div>

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
                    Proceso <SortIcon columnKey="evaluation" />
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
                    Transformación <SortIcon columnKey="output" />
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
                sortedAndFilteredWorkflows.map((workflow) => (
                  <tr key={workflow.id_evaluation} className="hover:bg-slate-50/80 transition-colors group">
                    <td className="p-5">
                      <div className="font-bold text-slate-700">
                        {workflow.evaluation}
                      </div>
                    </td>
                    <td className="p-5 text-slate-500 text-sm">
                      {workflow.description}
                    </td>
                    <td className="p-5">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-medium tracking-tight border ${getFormatStyle(workflow.input)}`}>
                          {workflow.input || "EXCEL"}
                        </span>
                        <ArrowRight size={12} className="text-slate-300" />
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-medium tracking-tight border ${getFormatStyle(workflow.output)}`}>
                          {workflow.output}
                        </span>
                      </div>
                    </td>
                    <td className="p-5 text-slate-500 text-sm font-medium">
                      {workflow.last_run || "Nunca"}
                    </td>
                    <td className="p-5 text-right flex justify-end gap-1">
                      <div className="flex justify-end gap-1 opacity-100 lg:opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => handleRunWorkflow(workflow)}
                          disabled={executingId === workflow.id_evaluation}
                          className={`p-2 rounded-xl transition-all ${executingId === workflow.id_evaluation
                            ? 'bg-slate-100 text-slate-400'
                            : 'text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50'
                            }`}
                          title="Ejecutar"
                        >
                          <Play size={18} fill={executingId === workflow.id_evaluation ? "none" : "currentColor"} className={executingId === workflow.id_evaluation ? "animate-spin" : ""} />
                        </button>
                        <button
                          onClick={() => handleDuplicateWorkflow(workflow.id_evaluation)}
                          className="p-2 text-slate-300 hover:text-indigo-500 hover:bg-indigo-50 rounded-xl transition-all"
                          title="Duplicar"
                        >
                          <Copy size={18} />
                        </button>
                        <button
                          onClick={() => handleEditWorkflow(workflow.id_evaluation)}
                          className="p-2 text-slate-300 hover:text-slate-500 hover:bg-slate-100 rounded-xl transition-all"
                          title="Configurar"
                        >
                          <Settings size={18} />
                        </button>
                        <button
                          onClick={() => handleDeleteWorkflow(workflow.id_evaluation, workflow.evaluation)}
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
                  <td colSpan="5" className="p-12 text-center text-slate-400">
                    <p className="font-medium">No se encontraron procesos.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Drawer para configuración de pipeline */}
      <NewPipelineDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={drawerTitle}
        initialData={editingData}
        onSave={handleSaveWorkflow}
      />

      {/* Modal de Ejecución Reutilizado */}
      <WorkflowExecutionModal
        isOpen={isExecutionModalOpen}
        onClose={() => {
          setIsExecutionModalOpen(false);
          fetchWorkflows();
        }}
        workflowId={activeWorkflow?.id_evaluation}
        workflowName={activeWorkflow?.evaluation}
      />
    </div>
  );
}