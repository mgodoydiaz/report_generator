export default function Home() {
  return (
    <div className="max-w-4xl">
      <section id="home" className="bg-white border border-slate-200 p-12 rounded-[2rem] shadow-sm relative overflow-hidden group">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-indigo-50 rounded-full blur-3xl opacity-50 group-hover:opacity-80 transition-opacity"></div>
        <div className="relative flex flex-col md:flex-row items-center gap-8 text-center md:text-left">
          <div className="text-6xl bg-indigo-50 w-24 h-24 flex items-center justify-center rounded-3xl shadow-inner" aria-hidden="true">
            🏠
          </div>
          <div>
            <h1 className="text-4xl font-extrabold text-slate-800 tracking-tight mb-4">
              Generador de Reportes Académicos
            </h1>
            <p className="text-lg text-slate-500 font-medium leading-relaxed">
              Bienvenido al sistema de gestión. Utiliza el menú lateral para navegar entre las secciones de workflows, resultados y configuración.
            </p>
            <div className="mt-8 flex flex-wrap gap-4 justify-center md:justify-start">
              <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-2xl font-bold transition-all shadow-lg shadow-indigo-100">
                Comenzar ahora
              </button>
              <button className="bg-white border border-slate-200 hover:border-slate-300 text-slate-600 px-6 py-3 rounded-2xl font-bold transition-all">
                Ver documentación
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
