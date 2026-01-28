import { Download, Database, Users, TrendingUp, Award, Calendar } from 'lucide-react';

const kpis = [
  { icon: <Users size={20} />, label: "Estudiantes evaluados", value: "684", color: "bg-blue-50 text-blue-600" },
  { icon: <TrendingUp size={20} />, label: "Promedio global", value: "272 pts", color: "bg-emerald-50 text-emerald-600" },
  { icon: <Award size={20} />, label: "Mejor curso", value: "2C", color: "bg-amber-50 text-amber-600" },
];

const rows = [
  { curso: "2A", simce: "268 pts", logro: "72%", nivel: "Medio", variacion: "+3.1%", positive: true },
  { curso: "2B", simce: "274 pts", logro: "75%", nivel: "Medio", variacion: "+2.4%", positive: true },
  { curso: "2C", simce: "281 pts", logro: "79%", nivel: "Alto", variacion: "+4.0%", positive: true },
  { curso: "2D", simce: "265 pts", logro: "69%", nivel: "Medio", variacion: "-1.2%", positive: false },
];

const charts = [
  { src: "/data/output/rendimiento_promedio_por_curso.png", caption: "Rendimiento promedio por curso" },
  { src: "/data/output/distribucion_puntaje_simce_por_curso.png", caption: "Distribución de puntajes" },
];

export default function Resultados() {
  return (
    <div className="max-w-6xl mx-auto space-y-10">
      {/* Header section */}
      <section className="bg-indigo-900 text-white p-10 rounded-[2.5rem] shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500 rounded-full blur-3xl opacity-20 -mr-20 -mt-20"></div>
        <div className="relative z-10 flex flex-col lg:flex-row justify-between gap-10">
          <div className="max-w-xl">
            <span className="bg-white/10 text-indigo-100 text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-widest">Reporte General 2025</span>
            <h1 className="text-4xl font-extrabold mt-4 mb-4 tracking-tight">Resultados Trabajados</h1>
            <p className="text-indigo-100/70 font-medium leading-relaxed mb-8">
              Vista consolidada de indicadores académicos clave con comparativas anuales y gráficos de rendimiento por curso.
            </p>
            <div className="flex flex-wrap gap-4">
              <button className="bg-white text-indigo-900 px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:bg-indigo-50 transition-all shadow-lg">
                <Download size={20} /> Descargar PDF
              </button>
              <button className="bg-indigo-800 text-white border border-indigo-700 px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:bg-indigo-700 transition-all">
                <Database size={20} /> Datos Base
              </button>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-4 shrink-0 lg:w-64">
            {kpis.map((kpi) => (
              <div key={kpi.label} className="bg-white/5 backdrop-blur-md border border-white/10 p-5 rounded-2xl">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-xl ${kpi.color}`}>
                    {kpi.icon}
                  </div>
                  <div>
                    <p className="text-[10px] uppercase font-bold text-indigo-200/50 tracking-wider leading-none mb-1">{kpi.label}</p>
                    <p className="text-xl font-black text-white">{kpi.value}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Table Section */}
      <section className="bg-white border border-slate-200 rounded-[2.5rem] overflow-hidden shadow-sm">
        <div className="p-8 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-extrabold text-slate-800 tracking-tight">Promedios por Curso</h2>
            <p className="text-slate-500 text-sm font-medium mt-1">Indicadores de logro y puntaje SIMCE por sección.</p>
          </div>
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-4 py-2 rounded-xl text-xs font-bold text-slate-500">
            <Calendar size={14} className="text-indigo-600" /> Actualizado: 13 Oct 2025
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-slate-50/50">
                <th className="px-8 py-5 text-[11px] font-bold text-slate-400 uppercase tracking-widest">Curso</th>
                <th className="px-8 py-5 text-[11px] font-bold text-slate-400 uppercase tracking-widest">Promedio SIMCE</th>
                <th className="px-8 py-5 text-[11px] font-bold text-slate-400 uppercase tracking-widest">Logro</th>
                <th className="px-8 py-5 text-[11px] font-bold text-slate-400 uppercase tracking-widest">Nivel</th>
                <th className="px-8 py-5 text-[11px] font-bold text-slate-400 uppercase tracking-widest text-right">Variación</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 text-slate-700">
              {rows.map((row) => (
                <tr key={row.curso} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-8 py-5 font-black text-slate-900">{row.curso}</td>
                  <td className="px-8 py-5 font-medium">{row.simce}</td>
                  <td className="px-8 py-5 font-medium">{row.logro}</td>
                  <td className="px-8 py-5">
                    <span className={`px-3 py-1 rounded-full text-[10px] font-bold ${row.nivel === 'Alto' ? 'bg-indigo-50 text-indigo-600' : 'bg-slate-100 text-slate-500'}`}>
                      {row.nivel}
                    </span>
                  </td>
                  <td className={`px-8 py-5 text-right font-bold ${row.positive ? 'text-emerald-500' : 'text-rose-500'}`}>
                    {row.variacion}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
