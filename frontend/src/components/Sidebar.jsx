import { NavLink } from "react-router-dom";
import {
  House,
  Workflow,
  Notebook,
  ChartColumn,
  Search,
  BookSearch,
  CircleHelp,
  Settings,
  Play,
  Activity,
  Layers,
  Box
} from "lucide-react";

export default function Sidebar() {
  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-2.5 rounded-lg font-medium transition-all ${isActive
      ? "bg-indigo-600 text-white shadow-lg shadow-indigo-200"
      : "text-slate-600 hover:bg-slate-100 hover:text-indigo-600"
    }`;

  const staticLinkClass = "flex items-center gap-3 px-4 py-2.5 rounded-lg font-medium text-slate-600 hover:bg-slate-100 hover:text-indigo-600 transition-all";

  const sectionHeaderClass = "px-4 pt-6 pb-2 text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2";

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col h-screen sticky top-0 shrink-0" aria-label="Menu principal">
      <div className="p-6">
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white text-xs">
            <Activity size={18} strokeWidth={3} />
          </div>
          Menu
        </h1>
      </div>
      <nav className="flex-1 px-4 space-y-1 overflow-y-auto pb-8 text-left">
        <NavLink to="/" className={linkClass}>
          <House size={18} />
          Inicio
        </NavLink>

        {/* SECCIÓN OPERACIONES */}
        <div className={sectionHeaderClass}>
          <Activity size={12} className="text-indigo-500" />
          Operaciones
        </div>
        <NavLink to="/execution" className={linkClass}>
          <Play size={18} />
          Ejecución
        </NavLink>
        <NavLink to="/valores" className={linkClass}>
          <BookSearch size={18} />
          Valores
        </NavLink>
        <NavLink to="/resultados" className={linkClass}>
          <ChartColumn size={18} />
          Resultados
        </NavLink>

        {/* SECCIÓN CONFIGURACIÓN */}
        <div className={sectionHeaderClass}>
          <Settings size={12} className="text-amber-500" />
          Configuración
        </div>
        <NavLink to="/dimensiones" className={linkClass}>
          <Layers size={18} />
          Dimensiones
        </NavLink>
        <NavLink to="/metricas" className={linkClass}>
          <Box size={18} />
          Métricas
        </NavLink>
        <NavLink to="/templates" className={linkClass}>
          <Notebook size={18} />
          Plantillas
        </NavLink>
        <NavLink to="/workflows" className={linkClass}>
          <Workflow size={18} />
          Workflows
        </NavLink>
      </nav>

      <div className="p-4 mt-auto border-t border-slate-100 space-y-1 text-left">
        <NavLink to="/ayuda" className={linkClass}>
          <CircleHelp size={18} />
          Ayuda
        </NavLink>
      </div>
    </aside>
  );
}
