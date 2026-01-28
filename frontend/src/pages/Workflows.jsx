import React, { useState, useMemo } from 'react';
import { Settings, Play, Trash2, Plus, Clock, Zap, Search, ArrowUpDown, ChevronUp, ChevronDown } from 'lucide-react';

const workflowsData = [
  {
    id: 1,
    nombre: "Pipeline SIMCE Matematicas",
    descripcion: "Generación automática de reportes PDF y consolidado Excel...",
    salida: "PDF / XLSX",
    ultimaEjecucion: "08 Ene 2026"
  },
  {
    id: 2,
    nombre: "Exportador DIA Lenguaje",
    descripcion: "ETL Data Lake para análisis de comprensión lectora.",
    salida: "CSV / Parquet",
    ultimaEjecucion: "20 Dic 2025"
  },
  {
    id: 3,
    nombre: "Workflow Calculo Veloz",
    descripcion: "Cálculo de métricas de velocidad para dashboard.",
    salida: "JSON / API",
    ultimaEjecucion: "14 Ene 2026"
  },
  {
    id: 4,
    nombre: "Procesador Fluidez Lectora",
    descripcion: "Audio-to-Text y métricas de palabras por minuto.",
    salida: "PDF / CSV",
    ultimaEjecucion: "10 Ene 2026"
  }
];

const parseSpanishDate = (dateStr) => {
  const months = {
    'Ene': 0, 'Feb': 1, 'Mar': 2, 'Abr': 3, 'May': 4, 'Jun': 5,
    'Jul': 6, 'Ago': 7, 'Sep': 8, 'Oct': 9, 'Nov': 10, 'Dic': 11
  };
  const parts = dateStr.split(' ');
  if (parts.length !== 3) return new Date(0);
  const [day, monthStr, year] = parts;
  return new Date(year, months[monthStr], day);
};

export default function Workflows() {
  const [busqueda, setBusqueda] = useState("");
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const sortedAndFilteredWorkflows = useMemo(() => {
    let items = [...workflowsData].filter(wf =>
      wf.nombre.toLowerCase().includes(busqueda.toLowerCase()) ||
      wf.descripcion.toLowerCase().includes(busqueda.toLowerCase())
    );

    if (sortConfig.key !== null) {
      items.sort((a, b) => {
        let aValue = a[sortConfig.key];
        let bValue = b[sortConfig.key];

        if (sortConfig.key === 'ultimaEjecucion') {
          aValue = parseSpanishDate(aValue);
          bValue = parseSpanishDate(bValue);
        }

        if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return items;
  }, [busqueda, sortConfig]);

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
        <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl font-bold transition-all shadow-md shadow-indigo-100 flex items-center gap-2">
          <Plus size={20} strokeWidth={3} />
          Nuevo Pipeline
        </button>
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

      {/* Table Card */}
      <div className="bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-100">
                <th
                  className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors"
                  onClick={() => handleSort('nombre')}
                >
                  <div className="flex items-center gap-2">
                    Workflow <SortIcon columnKey="nombre" />
                  </div>
                </th>
                <th
                  className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors"
                  onClick={() => handleSort('descripcion')}
                >
                  <div className="flex items-center gap-2">
                    Descripción <SortIcon columnKey="descripcion" />
                  </div>
                </th>
                <th
                  className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors"
                  onClick={() => handleSort('salida')}
                >
                  <div className="flex items-center gap-2">
                    Output <SortIcon columnKey="salida" />
                  </div>
                </th>
                <th
                  className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest cursor-pointer hover:text-indigo-600 transition-colors"
                  onClick={() => handleSort('ultimaEjecucion')}
                >
                  <div className="flex items-center gap-2">
                    Última Ejecución <SortIcon columnKey="ultimaEjecucion" />
                  </div>
                </th>
                <th className="p-5 font-bold text-slate-400 text-[11px] uppercase tracking-widest text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {sortedAndFilteredWorkflows.length > 0 ? (
                sortedAndFilteredWorkflows.map((wf) => (
                  <tr key={wf.id} className="hover:bg-slate-50/80 transition-colors group">
                    <td className="p-5">
                      <div className="font-bold text-slate-700">{wf.nombre}</div>
                    </td>
                    <td className="p-5 text-slate-500 text-sm">
                      {wf.descripcion}
                    </td>
                    <td className="p-5">
                      <span className="bg-slate-100 text-slate-500 text-[10px] font-bold px-2 py-1 rounded uppercase tracking-tighter">
                        {wf.salida}
                      </span>
                    </td>
                    <td className="p-5 text-slate-500 text-sm font-medium">
                      {wf.ultimaEjecucion}
                    </td>
                    <td className="p-5 text-right">
                      <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button className="p-2 text-indigo-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all" title="Ejecutar ahora">
                          <Play size={18} fill="currentColor" />
                        </button>
                        <button className="p-2 text-slate-300 hover:text-slate-500 hover:bg-slate-100 rounded-xl transition-all" title="Configurar">
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
    </div>
  );
}