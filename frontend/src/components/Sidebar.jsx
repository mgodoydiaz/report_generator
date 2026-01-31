import { NavLink } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import {
  House,        // Home
  Activity,     // Activity
  Play,         // Execution
  BookSearch,   // Values
  ChartColumn,  // Results
  Settings,     // Settings
  Layers,       // Dimensions
  Box,          // Metrics
  Notebook,     // Templates
  Workflow,     // Pipelines
  CircleHelp,   // Help
  Sun,          // Light mode
  Moon          // Dark mode
} from "lucide-react";

export default function Sidebar() {
  const { isDarkMode, toggleTheme } = useTheme();

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-2.5 rounded-lg font-medium transition-all ${isActive
      ? "bg-indigo-600 text-white shadow-lg shadow-indigo-200 dark:shadow-indigo-900/20"
      : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-indigo-600 dark:hover:text-indigo-400"
    }`;

  const sectionHeaderClass = "px-4 pt-6 pb-2 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center gap-2";

  return (
    <aside className="w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col h-screen sticky top-0 shrink-0 transition-colors duration-300" aria-label="Menu principal">
      <div className="p-6">
        <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
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
        <NavLink to="/values" className={linkClass}>
          <BookSearch size={18} />
          Valores
        </NavLink>
        <NavLink to="/results" className={linkClass}>
          <ChartColumn size={18} />
          Resultados
        </NavLink>

        {/* SECCIÓN CONFIGURACIÓN */}
        <div className={sectionHeaderClass}>
          <Settings size={12} className="text-amber-500" />
          Configuración
        </div>
        <NavLink to="/dimensions" className={linkClass}>
          <Layers size={18} />
          Dimensiones
        </NavLink>
        <NavLink to="/metrics" className={linkClass}>
          <Box size={18} />
          Métricas
        </NavLink>
        <NavLink to="/templates" className={linkClass}>
          <Notebook size={18} />
          Plantillas
        </NavLink>
        <NavLink to="/pipelines" className={linkClass}>
          <Workflow size={18} />
          Procesos
        </NavLink>
      </nav>

      <div className="p-4 mt-auto border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 overflow-hidden">
        <NavLink to="/help" className={`${linkClass({ isActive: false })} flex-1`}>
          <CircleHelp size={18} />
          Ayuda
        </NavLink>

        {/* Dark Mode Switch */}
        <button
          onClick={toggleTheme}
          className="relative w-11 h-6 shrink-0 rounded-full bg-slate-200 dark:bg-slate-700 transition-colors duration-300 focus:outline-none group/switch"
          title={isDarkMode ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
        >
          <div className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow-sm flex items-center justify-center transition-transform duration-300 ${isDarkMode ? 'translate-x-5' : 'translate-x-0'}`}>
            {isDarkMode ? <Moon size={10} className="text-indigo-600" /> : <Sun size={10} className="text-amber-500" />}
          </div>
        </button>
      </div>
    </aside>
  );
}
