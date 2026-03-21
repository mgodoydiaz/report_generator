const STEPS = [
  { id: 1, label: "Selección", sub: "Tipo de componente" },
  { id: 2, label: "Configuración", sub: "Ejes y parámetros" },
  { id: 3, label: "Vista previa", sub: "Confirma y agrega" },
];

export default function ModalSidebar({ currentStep, selectedComp, onStepClick }) {
  return (
    <div className="w-[248px] min-w-[248px] bg-slate-50 dark:bg-slate-800/50 border-r border-slate-100 dark:border-slate-700/60 p-5 flex flex-col">
      <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-5">
        Nuevo componente
      </p>

      <div className="flex flex-col gap-0.5">
        {STEPS.map((step, i) => {
          const isDone = step.id < currentStep;
          const isActive = step.id === currentStep;
          const isPending = step.id > currentStep;

          return (
            <div key={step.id} className="relative">
              {i < STEPS.length - 1 && (
                <div
                  className={`absolute left-[13px] top-[34px] w-px h-[28px] transition-colors ${
                    isDone
                      ? "bg-indigo-400 dark:bg-indigo-500"
                      : "bg-slate-200 dark:bg-slate-700"
                  }`}
                />
              )}
              <button
                onClick={() => onStepClick(step.id)}
                disabled={isPending}
                className={`w-full flex items-start gap-3 px-2 py-2.5 rounded-xl text-left transition-all ${
                  isActive
                    ? "bg-white dark:bg-slate-800 shadow-sm shadow-slate-200/80 dark:shadow-slate-900/40"
                    : isPending
                    ? "opacity-50 cursor-not-allowed"
                    : "hover:bg-white/70 dark:hover:bg-slate-800/50 cursor-pointer"
                }`}
              >
                <div
                  className={`w-[26px] h-[26px] min-w-[26px] rounded-full flex items-center justify-center text-[11px] font-semibold transition-all z-10 ${
                    isDone
                      ? "bg-indigo-600 text-white"
                      : isActive
                      ? "bg-indigo-600 text-white ring-4 ring-indigo-100 dark:ring-indigo-900/50"
                      : "bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-slate-400 dark:text-slate-500"
                  }`}
                >
                  {isDone ? (
                    <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                      <path d="M2 5.5L4.5 8L9 3" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  ) : (
                    step.id
                  )}
                </div>
                <div className="pt-0.5 min-w-0">
                  <p
                    className={`text-xs font-medium leading-tight ${
                      isActive
                        ? "text-slate-900 dark:text-slate-100"
                        : isDone
                        ? "text-slate-700 dark:text-slate-300"
                        : "text-slate-400 dark:text-slate-500"
                    }`}
                  >
                    {step.label}
                  </p>
                  <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5 leading-tight">
                    {step.sub}
                  </p>
                </div>
              </button>
            </div>
          );
        })}
      </div>

      {selectedComp && (
        <div className="mt-auto pt-5 border-t border-slate-200 dark:border-slate-700/60">
          <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">
            Seleccionado
          </p>
          <div className="flex items-center gap-2 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800/40 rounded-xl px-3 py-2.5">
            <div
              className={`w-7 h-7 min-w-[28px] rounded-lg flex items-center justify-center text-sm ${
                selectedComp.iconColor === "amber"
                  ? "bg-amber-100 dark:bg-amber-900/30"
                  : selectedComp.iconColor === "emerald"
                  ? "bg-emerald-100 dark:bg-emerald-900/30"
                  : "bg-indigo-100 dark:bg-indigo-900/30"
              }`}
            >
              {selectedComp.icon}
            </div>
            <p className="text-xs font-medium text-indigo-700 dark:text-indigo-300 leading-tight">
              {selectedComp.name}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
