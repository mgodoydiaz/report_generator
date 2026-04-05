import { useState, useEffect } from "react";
import { X } from "lucide-react";
import { API_BASE_URL } from "../constants";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";

export default function OrgDrawer({ isOpen, onClose, onSave, initialData }) {
  const { fetchAuth } = useAuth();
  const isEditing = !!initialData?.id;

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);

  // Auto-genera el slug a partir del nombre
  const slugify = (text) =>
    text.toLowerCase()
      .replace(/[áàä]/g, "a").replace(/[éèë]/g, "e")
      .replace(/[íìï]/g, "i").replace(/[óòö]/g, "o")
      .replace(/[úùü]/g, "u").replace(/ñ/g, "n")
      .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  useEffect(() => {
    if (isOpen) {
      if (initialData) {
        setName(initialData.name || "");
        setSlug(initialData.slug || "");
        setDescription(initialData.description || "");
        setIsActive(initialData.is_active ?? true);
      } else {
        setName(""); setSlug(""); setDescription(""); setIsActive(true);
      }
    }
  }, [isOpen, initialData]);

  const handleNameChange = (val) => {
    setName(val);
    if (!isEditing) setSlug(slugify(val));
  };

  const handleSave = async () => {
    if (!name.trim()) { toast.error("El nombre es obligatorio"); return; }
    if (!slug.trim()) { toast.error("El slug es obligatorio"); return; }

    setSaving(true);
    try {
      const url = isEditing
        ? `${API_BASE_URL}/superadmin/organizations/${initialData.id}`
        : `${API_BASE_URL}/superadmin/organizations`;

      const res = await fetchAuth(url, {
        method: isEditing ? "PUT" : "POST",
        body: JSON.stringify({ name, slug, description, is_active: isActive }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Error al guardar");

      toast.success(isEditing ? "Organización actualizada" : "Organización creada");
      onSave && onSave(data);
      onClose();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-white dark:bg-slate-900 shadow-2xl z-50 overflow-y-auto border-l border-slate-200 dark:border-slate-800 animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-lg font-bold text-slate-800 dark:text-white">
            {isEditing ? "Editar Organización" : "Nueva Organización"}
          </h2>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500">
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <div className="p-5 space-y-5">
          {/* Nombre */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Nombre *</label>
            <input
              type="text"
              value={name}
              onChange={e => handleNameChange(e.target.value)}
              placeholder="Fundación PHP"
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-violet-500 outline-none transition"
            />
          </div>

          {/* Slug */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Slug *</label>
            <input
              type="text"
              value={slug}
              onChange={e => setSlug(e.target.value)}
              placeholder="fundacion-php"
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-violet-500 outline-none font-mono transition"
            />
            <p className="text-xs text-slate-400">Identificador único. Solo letras minúsculas, números y guiones.</p>
          </div>

          {/* Descripción */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Descripción</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Descripción breve de la organización..."
              rows={3}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-violet-500 outline-none resize-none transition"
            />
          </div>

          {/* Estado */}
          <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Estado activo</p>
              <p className="text-xs text-slate-400">Los usuarios de orgs inactivas no pueden ingresar</p>
            </div>
            <button
              type="button"
              onClick={() => setIsActive(v => !v)}
              className={`relative w-11 h-6 rounded-full transition-colors duration-300 ${isActive ? "bg-violet-600" : "bg-slate-300 dark:bg-slate-600"}`}
            >
              <div className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow-sm transition-transform duration-300 ${isActive ? "translate-x-5" : "translate-x-0"}`} />
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-slate-200 dark:border-slate-800 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition font-medium"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 px-4 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-700 text-white font-medium transition disabled:opacity-60"
          >
            {saving ? "Guardando..." : isEditing ? "Actualizar" : "Crear"}
          </button>
        </div>
      </div>
    </>
  );
}
