import React, { useEffect, useMemo, useState } from "react";

// 1) Helpers y constantes FUERA del componente
function downloadJSON(filename, dataObj) {
  const dataStr =
    "data:text/json;charset=utf-8," +
    encodeURIComponent(JSON.stringify(dataObj, null, 2));
  const dlAnchor = document.createElement("a");
  dlAnchor.setAttribute("href", dataStr);
  dlAnchor.setAttribute("download", filename);
  document.body.appendChild(dlAnchor);
  dlAnchor.click();
  dlAnchor.remove();
}

const DEFAULT_VARS_DOC = {
  leftimage: "img/logo_php.png",
  rightimage: "img/pullinque_php.png",
  centerheaderone: "Informe DIA Intermedio",
  centerheadertwo: "Lenguaje Nivel Medio",
  centerheaderthree: "Septiembre 2025",
  leftfooter: "Miguel Godoy Díaz",
  rightfooter: "\\thepage",
  documenttitle: "Informe DIA Intermedio - Lenguaje Nivel Medio",
  schoolname: "Liceo Técnico Profesional People Help People Pullinque",
  theauthor: "Miguel Godoy Díaz",
};

const defaultItem = () => ({
  id: crypto.randomUUID(),
  tipo: "imagen",
  nombre: "",
  ruta: "",
  ancho: "",
});

// 2) ÚNICO export default del archivo
export default function GenerarInforme() {
  // Estado y efectos que antes estaban en InformeFormPrototype
  const [varsDoc, setVarsDoc] = useState(DEFAULT_VARS_DOC);
  const [items, setItems] = useState([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("informe_form_state");
      if (raw) {
        const parsed = JSON.parse(raw);
        setVarsDoc(parsed.varsDoc ?? DEFAULT_VARS_DOC);
        setItems(parsed.items ?? []);
      }
    } catch (_) {}
  }, []);

  useEffect(() => {
    const state = { varsDoc, items };
    localStorage.setItem("informe_form_state", JSON.stringify(state));
  }, [varsDoc, items]);

  const esquemaPreview = useMemo(() => {
    return {
      variables_documento: varsDoc,
      secciones_fijas: items.map(({ id, ...rest }) => rest),
    };
  }, [varsDoc, items]);

  const handleAddItem = () => setItems((prev) => [...prev, defaultItem()]);
  const handleRemoveItem = (id) => setItems((prev) => prev.filter((x) => x.id !== id));
  const handleItemChange = (id, field, value) => {
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, [field]: value } : it)));
  };
  const readyToDownload = (varsDoc.documenttitle || "").trim().length > 0;

  // 3) AQUÍ pega tu JSX de la UI (lo largo), SIN funciones/const adentro
  return (
    <>
      {
          <div className="min-h-screen w-full bg-neutral-950 text-neutral-100">
            <div className="max-w-5xl mx-auto px-4 py-8">
              <header className="mb-8">
                <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">
                  Prototipo · Formulario de Informe
                </h1>
                <p className="text-sm md:text-base text-neutral-400 mt-1">
                  Define la información del documento y agrega secciones fijas
                  (imagen/tabla). Luego puedes descargar un
                  <code className="mx-1 px-1 bg-neutral-800 rounded">
                    esquema_informe.json
                  </code>{" "}
                  listo para tu pipeline.
                </p>
              </header>
      
              {/* Información del documento */}
              <section className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-5 mb-6">
                <h2 className="text-lg font-medium mb-4">Información del documento</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-neutral-400">
                      Título del documento (documenttitle)
                    </label>
                    <input
                      value={varsDoc.documenttitle}
                      onChange={(e) =>
                        setVarsDoc((prev) => ({ ...prev, documenttitle: e.target.value }))
                      }
                      placeholder="Informe DIA Intermedio - Lenguaje Nivel Medio"
                      className="rounded-xl border border-neutral-700 bg-neutral-900 px-3 py-2 w-full"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-neutral-400">
                      Establecimiento (schoolname)
                    </label>
                    <input
                      value={varsDoc.schoolname}
                      onChange={(e) =>
                        setVarsDoc((prev) => ({ ...prev, schoolname: e.target.value }))
                      }
                      placeholder="Liceo Técnico Profesional People Help People Pullinque"
                      className="rounded-xl border border-neutral-700 bg-neutral-900 px-3 py-2 w-full"
                    />
                  </div>
                </div>
                {/* Aquí siguen los demás campos (encabezados, logos, pie, autor)… */}
              </section>
      
              {/* Secciones fijas */}
              <section className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-5 mb-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-medium">Secciones fijas</h2>
                  <button
                    onClick={handleAddItem}
                    className="rounded-xl bg-white text-neutral-900 px-3 py-2 text-sm font-medium hover:opacity-90 active:opacity-80"
                  >
                    + Agregar sección
                  </button>
                </div>
                {items.length === 0 && (
                  <p className="text-sm text-neutral-500">
                    Aún no has agregado secciones. Usa el botón “Agregar sección”.
                  </p>
                )}
                <div className="grid gap-4">
                  {items.map((it, idx) => (
                    <div
                      key={it.id}
                      className="rounded-2xl border border-neutral-800 bg-neutral-900 p-4"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-semibold text-neutral-300">
                          Sección #{idx + 1}
                        </h3>
                        <button
                          onClick={() => handleRemoveItem(it.id)}
                          className="text-xs rounded-lg border border-red-500/40 text-red-300 px-2 py-1 hover:bg-red-500/10"
                        >
                          Eliminar
                        </button>
                      </div>
                      <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3">
                        <div>
                          <label className="text-xs text-neutral-400">Tipo</label>
                          <select
                            value={it.tipo}
                            onChange={(e) =>
                              handleItemChange(it.id, "tipo", e.target.value)
                            }
                            className="rounded-xl border border-neutral-700 bg-neutral-900 px-3 py-2 w-full"
                          >
                            <option value="imagen">Imagen</option>
                            <option value="tabla">Tabla</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-xs text-neutral-400">Nombre</label>
                          <input
                            value={it.nombre}
                            onChange={(e) =>
                              handleItemChange(it.id, "nombre", e.target.value)
                            }
                            placeholder="Ej: Logro promedio por curso"
                            className="rounded-xl border border-neutral-700 bg-neutral-900 px-3 py-2 w-full"
                          />
                        </div>
                        <div className="md:col-span-2">
                          <label className="text-xs text-neutral-400">
                            Ruta de archivo (aux_files/…)
                          </label>
                          <input
                            value={it.ruta}
                            onChange={(e) =>
                              handleItemChange(it.id, "ruta", e.target.value)
                            }
                            placeholder="aux_files/figuras/logro_promedio_por_curso.png"
                            className="rounded-xl border border-neutral-700 bg-neutral-900 px-3 py-2 w-full"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
      
              {/* Vista previa */}
              <section className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-medium">Vista previa del esquema</h2>
                  <button
                    onClick={() => downloadJSON("esquema_informe.json", esquemaPreview)}
                    disabled={!readyToDownload}
                    className={
                      "rounded-xl px-3 py-2 text-sm font-medium " +
                      (readyToDownload
                        ? "bg-white text-neutral-900 hover:opacity-90 active:opacity-80"
                        : "bg-neutral-800 text-neutral-500 cursor-not-allowed")
                    }
                  >
                    Descargar JSON
                  </button>
                </div>
                {!readyToDownload && (
                  <p className="text-xs text-amber-300 mb-2">
                    Para habilitar la descarga, completa el título del informe.
                  </p>
                )}
                <pre className="text-xs md:text-sm bg-neutral-950 border border-neutral-800 rounded-xl p-4 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(esquemaPreview, null, 2)}
                </pre>
              </section>
            </div>
          </div>
      }
    </>
  );
}
      