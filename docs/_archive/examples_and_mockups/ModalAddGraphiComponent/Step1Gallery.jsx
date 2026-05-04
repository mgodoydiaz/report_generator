export const COMPONENTS = [
  {
    cat: "Especiales",
    items: [
      { id: "kpi", name: "Tarjetas KPI", desc: "Métricas clave en cards", icon: "📊", iconColor: "amber" },
      { id: "selector", name: "Selector de Curso", desc: "Filtro de curso activo", icon: "🎛️", iconColor: "indigo" },
    ],
  },
  {
    cat: "Tablas",
    items: [
      { id: "tbl-resumen", name: "Resumen por Grupo", desc: "Tabla agregada por grupo", icon: "📋", iconColor: "indigo" },
      { id: "tbl-lista", name: "Lista de Ítems", desc: "Listado detallado de registros", icon: "📄", iconColor: "indigo" },
      { id: "tbl-progreso", name: "Lista con Progreso", desc: "Ítems con barra de avance", icon: "📈", iconColor: "emerald" },
    ],
  },
  {
    cat: "Gráficos simples",
    items: [
      { id: "bar", name: "Barras por Grupo", desc: "Comparación entre grupos", icon: "📊", iconColor: "emerald" },
      { id: "box", name: "Boxplot", desc: "Distribución estadística", icon: "📦", iconColor: "emerald" },
      { id: "pie", name: "Torta", desc: "Proporción por categoría", icon: "🥧", iconColor: "emerald" },
      { id: "hbar", name: "Barras Horizontales", desc: "Ranking en horizontal", icon: "📉", iconColor: "emerald" },
      { id: "stack", name: "Conteo Apilado", desc: "Composición por grupos", icon: "🗂️", iconColor: "emerald" },
    ],
  },
  {
    cat: "Gráficos doble eje X",
    items: [
      { id: "grp-period", name: "Barras Agrupadas por Período", desc: "Comparación temporal agrupada", icon: "📅", iconColor: "emerald" },
      { id: "stack-period", name: "Conteo Apilado por Período", desc: "Evolución de composición", icon: "🗃️", iconColor: "emerald" },
    ],
  },
  {
    cat: "Gráficos especiales",
    items: [
      { id: "radar", name: "Perfil Radar", desc: "Comparación multidimensional", icon: "🕸️", iconColor: "indigo" },
    ],
  },
  {
    cat: "Gráficos temporales",
    items: [
      { id: "trend", name: "Tendencia Temporal", desc: "Serie de tiempo con líneas", icon: "📈", iconColor: "emerald" },
    ],
  },
];

const iconBg = {
  amber: "bg-amber-50 dark:bg-amber-900/20",
  emerald: "bg-emerald-50 dark:bg-emerald-900/20",
  indigo: "bg-indigo-50 dark:bg-indigo-900/20",
};

export default function Step1Gallery({ selectedComp, onSelect }) {
  return (
    <div className="space-y-4">
      {COMPONENTS.map((cat) => (
        <div key={cat.cat}>
          <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">
            {cat.cat}
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {cat.items.map((item) => {
              const isSelected = selectedComp?.id === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelect(item)}
                  className={`flex flex-col items-start gap-2 p-3 rounded-xl border text-left transition-all ${
                    isSelected
                      ? "border-indigo-400 dark:border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 ring-2 ring-indigo-200 dark:ring-indigo-800/50"
                      : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50/50 dark:hover:bg-indigo-900/10"
                  }`}
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-base ${iconBg[item.iconColor]}`}>
                    <span style={{ fontSize: 15 }}>{item.icon}</span>
                  </div>
                  <div>
                    <p
                      className={`text-xs font-medium leading-tight ${
                        isSelected
                          ? "text-indigo-700 dark:text-indigo-300"
                          : "text-slate-800 dark:text-slate-200"
                      }`}
                    >
                      {item.name}
                    </p>
                    <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5 leading-tight">
                      {item.desc}
                    </p>
                  </div>
                  {isSelected && (
                    <div className="ml-auto self-start mt-0.5">
                      <div className="w-4 h-4 rounded-full bg-indigo-600 flex items-center justify-center">
                        <svg width="9" height="9" viewBox="0 0 9 9" fill="none">
                          <path d="M1.5 4.5L3.5 6.5L7.5 2.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </div>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
