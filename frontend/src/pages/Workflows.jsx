import React, { useState, useMemo } from 'react';
import { Settings, Play, Trash2, Plus, Clock, Zap, Search, ArrowUpDown, ChevronUp, ChevronDown } from 'lucide-react';

const workflowsData = [
  {
    id: 1,
    nombre: "Pipeline SIMCE Matematicas",
    descripcion: "Generación automática de reportes PDF y consolidado Excel para resultados nacionales.",
    salida: "PDF / XLSX",
    ultimaEjecucion: "08 Ene 2026"
  },
  {
    id: 2,
    nombre: "Exportador DIA Lenguaje",
    descripcion: "Limpieza de datos y carga en el data lake para análisis de comprensión lectora.",
    salida: "CSV / Parquet",
    ultimaEjecucion: "20 Dic 2025"
  },
  {
    id: 3,
    nombre: "Workflow Calculo Veloz",
    descripcion: "Cálculo de métricas de velocidad y exportación a dashboard de visualización.",
    salida: "JSON / API",
    ultimaEjecucion: "14 Ene 2026"
  },
  {
    id: 4,
    nombre: "Procesador Fluidez Lectora",
    descripcion: "Transformación de audios a métricas de palabras por minuto y reportes individuales.",
    salida: "PDF / CSV",
    ultimaEjecucion: "10 Ene 2026"
  }
];

// Helper para parsear fechas en formato "DD Mes YYYY" con meses en español
const parseSpanishDate = (dateStr) => {
  const months = {
    'Ene': 0, 'Feb': 1, 'Mar': 2, 'Abr': 3, 'May': 4, 'Jun': 5,
    'Jul': 6, 'Ago': 7, 'Sep': 8, 'Oct': 9, 'Nov': 10, 'Dic': 11
  };
  const [day, monthStr, year] = dateStr.split(' ');
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

        // Lógica específica para fechas
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
    if (sortConfig.key !== columnKey) return <ArrowUpDown size={14} className="text-slate-300" />;
    return sortConfig.direction === 'asc' ? 
      <ChevronUp size={14} className="text-blue-600" /> : 
      <ChevronDown size={14} className="text-blue-600" />;
  };

  return (
    <div className="p-6 bg-slate-50 min-h-screen font-sans text-slate-900">
      {/* Cabecera */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="text-blue-600" size={28} />
            Workflows de Datos
          </h1>
          <p className="text-slate-500">
            Configura y administra los pipelines de salida para los archivos de evaluaciones.
          </p>
        </div>
        <button className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold transition-all shadow-sm">
          <Plus size={20} />
          Nuevo Workflow
        </button>
      </div>

      {/* Buscador */}
      <div className="relative mb-6 max-w-md">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-slate-400" />
        </div>
        <input
          type="text"
          placeholder="Buscar workflow..."
          className="block w-full pl-10 pr-3 py-2 border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all shadow-sm text-sm"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
        />
      </div>

      {/* Tabla de Workflows */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th 
                  className="p-4 font-semibold text-slate-700 text-sm cursor-pointer hover:bg-slate-100 transition-colors"
                  onClick={() => handleSort('nombre')}
                >
                  <div className="flex items-center gap-2">
                    Workflow / Pipeline <SortIcon columnKey="nombre" />
                  </div>
                </th>
                <th 
                  className="p-4 font-semibold text-slate-700 text-sm cursor-pointer hover:bg-slate-100 transition-colors"
                  onClick={() => handleSort('descripcion')}
                >
                  <div className="flex items-center gap-2">
                    Descripción del Proceso <SortIcon columnKey="descripcion" />
                  </div>
                </th>
                <th 
                  className="p-4 font-semibold text-slate-700 text-sm cursor-pointer hover:bg-slate-100 transition-colors"
                  onClick={() => handleSort('salida')}
                >
                  <div className="flex items-center gap-2">
                    Salida <SortIcon columnKey="salida" />
                  </div>
                </th>
                <th 
                  className="p-4 font-semibold text-slate-700 text-sm cursor-pointer hover:bg-slate-100 transition-colors"
                  onClick={() => handleSort('ultimaEjecucion')}
                >
                  <div className="flex items-center gap-2">
                    Última Ejecución <SortIcon columnKey="ultimaEjecucion" />
                  </div>
                </th>
                <th className="p-4 font-semibold text-slate-700 text-sm text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sortedAndFilteredWorkflows.length > 0 ? (
                sortedAndFilteredWorkflows.map((wf) => (
                  <tr key={wf.id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-4">
                      <div className="font-bold text-slate-900">{wf.nombre}</div>
                    </td>
                    <td className="p-4 text-slate-600 text-sm max-w-xs md:max-w-md">
                      {wf.descripcion}
                    </td>
                    <td className="p-4">
                      <div className="text-slate-700 font-medium">{wf.salida}</div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-1.5 text-slate-500 text-sm">
                        <Clock size={16} />
                        {wf.ultimaEjecucion}
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      <div className="inline-flex gap-2">
                        <button className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all" title="Ejecutar ahora">
                          <Play size={18} fill="currentColor" />
                        </button>
                        <button className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-all" title="Configurar">
                          <Settings size={18} />
                        </button>
                        <button className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all" title="Eliminar">
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="p-8 text-center text-slate-400 italic">
                    No se encontraron workflows.
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