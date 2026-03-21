export default function Step2Config({ comp, config, stepIdx, answers, onSelect }) {
  const step = config.steps[stepIdx];
  const total = config.steps.length;

  return (
    <div className="space-y-5">
      {total > 1 && (
        <div className="flex items-center gap-1.5">
          {config.steps.map((s, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-all ${
                i < stepIdx
                  ? "bg-indigo-500"
                  : i === stepIdx
                  ? "bg-indigo-500"
                  : "bg-slate-200 dark:bg-slate-700"
              }`}
            />
          ))}
          <span className="text-[11px] text-slate-400 dark:text-slate-500 ml-2 whitespace-nowrap">
            {stepIdx + 1} / {total}
          </span>
        </div>
      )}

      <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-700/50 px-4 py-3 flex items-center gap-2.5">
        <div className="w-6 h-6 rounded-md bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center flex-shrink-0">
          <span style={{ fontSize: 13 }}>{comp?.icon}</span>
        </div>
        <div>
          <p className="text-xs font-medium text-slate-700 dark:text-slate-300">{comp?.name}</p>
          <p className="text-[11px] text-slate-400 dark:text-slate-500">{comp?.desc}</p>
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 mb-0.5">{step.title}</p>
        <p className="text-[11px] text-slate-400 dark:text-slate-500 mb-3">{step.hint}</p>

        <div className="space-y-1.5">
          {step.opts.map((opt, i) => {
            const isSelected = answers[stepIdx] === i;
            return (
              <button
                key={i}
                onClick={() => onSelect(stepIdx, i)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl border text-left transition-all ${
                  isSelected
                    ? "border-indigo-400 dark:border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20"
                    : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 hover:border-slate-300 dark:hover:border-slate-600"
                }`}
              >
                <div
                  className={`w-4 h-4 min-w-[16px] rounded-full border-2 flex items-center justify-center transition-all ${
                    isSelected
                      ? "border-indigo-600 bg-indigo-600"
                      : "border-slate-300 dark:border-slate-600"
                  }`}
                >
                  {isSelected && (
                    <div className="w-1.5 h-1.5 rounded-full bg-white" />
                  )}
                </div>
                <span
                  className={`text-xs font-medium flex-1 ${
                    isSelected
                      ? "text-indigo-700 dark:text-indigo-300"
                      : "text-slate-700 dark:text-slate-300"
                  }`}
                >
                  {opt.name}
                </span>
                <code
                  className={`text-[11px] font-mono px-1.5 py-0.5 rounded-md transition-colors ${
                    isSelected
                      ? "bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400"
                      : "bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400"
                  }`}
                >
                  {opt.code}
                </code>
              </button>
            );
          })}
        </div>
      </div>

      {Object.keys(answers).length > 0 && (
        <div className="border-t border-slate-100 dark:border-slate-800 pt-4">
          <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">
            Seleccionado hasta ahora
          </p>
          <div className="flex flex-wrap gap-1.5">
            {config.steps.slice(0, stepIdx + 1).map((s, i) => {
              const ans = answers[i];
              if (ans === undefined) return null;
              const opt = s.opts[ans];
              return (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 text-[11px] bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-800/40 px-2 py-1 rounded-lg"
                >
                  <span className="text-indigo-400 dark:text-indigo-600">{s.title.split("—")[0].trim()}</span>
                  <span className="font-medium">{opt.name}</span>
                  <code className="font-mono opacity-70">{opt.code}</code>
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
