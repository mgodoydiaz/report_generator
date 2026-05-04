import { useState } from "react";
import Step1Gallery from "./Step1Gallery";
import Step2Config from "./Step2Config";
import Step3Preview from "./Step3Preview";
import ModalSidebar from "./ModalSidebar";

export default function AddComponentModal({ onClose, onConfirm }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedComp, setSelectedComp] = useState(null);
  const [configAnswers, setConfigAnswers] = useState({});
  const [configStepIdx, setConfigStepIdx] = useState(0);

  const handleSelectComp = (comp) => {
    setSelectedComp(comp);
    setConfigAnswers({});
    setConfigStepIdx(0);
  };

  const handleSelectOpt = (stepIdx, optIdx) => {
    setConfigAnswers((prev) => ({ ...prev, [stepIdx]: optIdx }));
  };

  const getConfig = () => {
    const id = selectedComp?.id;
    return CONFIGS[id] ?? CONFIGS.default;
  };

  const handleNext = () => {
    if (currentStep === 1 && selectedComp) {
      setCurrentStep(2);
      setConfigStepIdx(0);
    } else if (currentStep === 2) {
      const cfg = getConfig();
      if (configStepIdx < cfg.steps.length - 1) {
        setConfigStepIdx((i) => i + 1);
      } else {
        setCurrentStep(3);
      }
    } else if (currentStep === 3) {
      onConfirm?.({ selectedComp, configAnswers });
    }
  };

  const handleBack = () => {
    if (currentStep === 2) {
      if (configStepIdx > 0) setConfigStepIdx((i) => i - 1);
      else setCurrentStep(1);
    } else if (currentStep === 3) {
      setCurrentStep(2);
    }
  };

  const cfg = getConfig();
  const isLastConfigStep = configStepIdx === cfg.steps.length - 1;
  const nextDisabled =
    currentStep === 1
      ? !selectedComp
      : currentStep === 2
      ? configAnswers[configStepIdx] === undefined
      : false;

  const nextLabel =
    currentStep === 1
      ? "Siguiente"
      : currentStep === 2
      ? isLastConfigStep
        ? "Ver previa"
        : "Siguiente"
      : "Confirmar y agregar";

  const nextStyle =
    currentStep === 3
      ? "bg-emerald-600 hover:bg-emerald-700 text-white"
      : "bg-indigo-600 hover:bg-indigo-700 text-white";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700/60 w-full max-w-[820px] max-h-[90vh] flex overflow-hidden shadow-2xl shadow-slate-900/20">
        <ModalSidebar
          currentStep={currentStep}
          selectedComp={selectedComp}
          onStepClick={(s) => {
            if (s === 1) setCurrentStep(1);
            if (s === 2 && selectedComp) { setCurrentStep(2); setConfigStepIdx(0); }
            if (s === 3 && selectedComp && Object.keys(configAnswers).length > 0) setCurrentStep(3);
          }}
        />

        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <div className="px-6 pt-5 pb-4 border-b border-slate-100 dark:border-slate-800 flex-shrink-0">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {currentStep === 1
                    ? "Elige un componente"
                    : currentStep === 2
                    ? `Configura: ${selectedComp?.name}`
                    : "Vista previa"}
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  {currentStep === 1
                    ? "Selecciona el tipo de visualización para el dashboard"
                    : currentStep === 2
                    ? `Paso ${configStepIdx + 1} de ${cfg.steps.length} — define los parámetros`
                    : "Revisa la configuración antes de agregar"}
                </p>
              </div>
              <button
                onClick={onClose}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-5">
            {currentStep === 1 && (
              <Step1Gallery
                selectedComp={selectedComp}
                onSelect={handleSelectComp}
              />
            )}
            {currentStep === 2 && (
              <Step2Config
                comp={selectedComp}
                config={cfg}
                stepIdx={configStepIdx}
                answers={configAnswers}
                onSelect={handleSelectOpt}
              />
            )}
            {currentStep === 3 && (
              <Step3Preview
                comp={selectedComp}
                config={cfg}
                answers={configAnswers}
              />
            )}
          </div>

          <div className="px-5 py-3.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between flex-shrink-0 bg-slate-50/60 dark:bg-slate-900/60">
            <button
              onClick={handleBack}
              className={`text-xs font-medium px-3.5 py-2 rounded-xl border transition-all ${
                currentStep === 1
                  ? "invisible"
                  : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-white dark:hover:bg-slate-800"
              }`}
            >
              ← Atrás
            </button>
            <div className="flex items-center gap-2">
              <button
                onClick={onClose}
                className="text-xs font-medium px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-white dark:hover:bg-slate-800 transition-all"
              >
                Cancelar
              </button>
              <button
                onClick={handleNext}
                disabled={nextDisabled}
                className={`text-xs font-semibold px-4 py-2 rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed ${nextStyle}`}
              >
                {nextLabel} →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export const CONFIGS = {
  bar: {
    steps: [
      {
        title: "Eje Y — Valor a graficar",
        hint: "Métrica principal del gráfico",
        opts: [
          { name: "Logro 1", code: "_rend" },
          { name: "Logro 2", code: "_simce" },
          { name: "Puntaje promedio", code: "_prom" },
          { name: "% Adecuado+", code: "_pct_adeq" },
        ],
      },
      {
        title: "Eje X — Agrupación",
        hint: "Cómo agrupar los datos en el eje horizontal",
        opts: [
          { name: "Grupo-curso", code: "grupo" },
          { name: "Docente", code: "docente" },
          { name: "Establecimiento", code: "establecimiento" },
        ],
      },
    ],
  },
  trend: {
    steps: [
      {
        title: "Métrica a graficar",
        hint: "Valor del eje Y a lo largo del tiempo",
        opts: [
          { name: "Promedio general", code: "_prom" },
          { name: "% Nivel Adecuado", code: "_pct_adeq" },
          { name: "Logro 1", code: "_rend" },
        ],
      },
      {
        title: "Período",
        hint: "Unidad temporal del eje X",
        opts: [
          { name: "Año escolar", code: "anio" },
          { name: "Semestre", code: "semestre" },
          { name: "Mes", code: "mes" },
        ],
      },
      {
        title: "Desagregación",
        hint: "Trazar una línea por cada...",
        opts: [
          { name: "Establecimiento", code: "establecimiento" },
          { name: "Grupo-curso", code: "grupo" },
          { name: "Sin desagregación", code: "_none" },
        ],
      },
    ],
  },
  default: {
    steps: [
      {
        title: "Métrica principal",
        hint: "Selecciona el campo a visualizar",
        opts: [
          { name: "Logro 1", code: "_rend" },
          { name: "Logro 2", code: "_simce" },
          { name: "Puntaje promedio", code: "_prom" },
          { name: "% Adecuado+", code: "_pct_adeq" },
        ],
      },
    ],
  },
};
