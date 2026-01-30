import { NavLink } from "react-router-dom";
import {
  Menu,
  House,
  Workflow,
  Notebook,
  ChartColumn,
  Database,
  FileWarning,
  CircleHelp,
  Settings
} from "lucide-react";

export default function Sidebar() {
  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-2.5 rounded-lg font-medium transition-all ${isActive
      ? "bg-indigo-600 text-white shadow-lg shadow-indigo-200"
      : "text-slate-600 hover:bg-slate-100 hover:text-indigo-600"
    }`;

  const staticLinkClass = "flex items-center gap-3 px-4 py-2.5 rounded-lg font-medium text-slate-600 hover:bg-slate-100 hover:text-indigo-600 transition-all";

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col h-screen sticky top-0 shrink-0" aria-label="Menu principal">
      <div className="p-6">
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white text-xs">
            <Menu size={18} strokeWidth={3} />
          </div>
          Menu
        </h1>
      </div>
      <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
        <NavLink to="/" className={linkClass}>
          <House size={18} />
          Inicio
        </NavLink>
        <NavLink to="/workflows" className={linkClass}>
          <Workflow size={18} />
          Workflows
        </NavLink>
        <NavLink to="/templates" className={linkClass}>
          <Notebook size={18} />
          Plantillas
        </NavLink>
        <NavLink to="/resultados" className={linkClass}>
          <ChartColumn size={18} />
          Resultados
        </NavLink>
        <a href="#" className={staticLinkClass}>
          <Database size={18} />
          Valores
        </a>
        <a href="#" className={staticLinkClass}>
          <FileWarning size={18} />
          Analisis y alertas
        </a>
      </nav>
      <div className="p-4 mt-auto border-t border-slate-100 space-y-1">
        <a href="#" className={staticLinkClass}>
          <CircleHelp size={18} />
          Ayuda
        </a>
        <a href="#" className={staticLinkClass}>
          <Settings size={18} />
          Configuracion
        </a>
      </div>
    </aside>
  );
}
