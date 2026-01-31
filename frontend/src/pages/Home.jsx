import { House } from 'lucide-react';

export default function Home() {
  return (
    <div className="max-w-4xl animate-in fade-in duration-700">
      <section id="home" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-12 rounded-3xl shadow-sm relative overflow-hidden group transition-colors">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-indigo-50 dark:bg-indigo-900/20 rounded-full blur-3xl opacity-50 group-hover:opacity-80 transition-opacity"></div>
        <div className="relative flex flex-col md:flex-row items-center gap-8 text-center md:text-left">
          <div className="text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/50 w-24 h-24 flex items-center justify-center rounded-3xl shadow-inner" aria-hidden="true">
            <House size={48} />
          </div>
          <div>
            <h1 className="text-4xl font-extrabold text-slate-800 dark:text-white tracking-tight mb-4 flex items-center gap-3">
              Generador de Reportes Académicos
            </h1>
            <p className="text-lg text-slate-500 dark:text-slate-400 font-medium leading-relaxed">
              Bienvenido al sistema de gestión. Utiliza el menú lateral para navegar entre las secciones de workflows, resultados y configuración.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
