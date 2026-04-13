import { useState } from "react";
import AddComponentModal from "./AddComponentModal";

export default function DashboardDemo() {
  const [open, setOpen] = useState(false);

  const handleConfirm = ({ selectedComp, configAnswers }) => {
    console.log("Componente confirmado:", selectedComp, configAnswers);
    setOpen(false);
  };

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950 flex items-center justify-center">
      <button
        onClick={() => setOpen(true)}
        className="text-sm font-medium px-4 py-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors"
      >
        + Agregar componente
      </button>

      {open && (
        <AddComponentModal
          onClose={() => setOpen(false)}
          onConfirm={handleConfirm}
        />
      )}
    </div>
  );
}
