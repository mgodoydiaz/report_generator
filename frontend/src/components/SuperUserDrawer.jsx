import { useState, useEffect } from "react";
import { X, ShieldCheck } from "lucide-react";
import { API_BASE_URL } from "../constants";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";

const ROLES = [
  { value: "admin", label: "Admin — Gestión completa de la org" },
  { value: "editor", label: "Editor — Crear y editar" },
  { value: "viewer", label: "Viewer — Solo lectura" },
];

export default function SuperUserDrawer({ isOpen, onClose, onSave, initialData, orgId, orgs = [] }) {
  const { fetchAuth, user: me } = useAuth();
  const isEditing = !!initialData?.id;

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("editor");
  const [selectedOrgId, setSelectedOrgId] = useState(orgId || "");
  const [isActive, setIsActive] = useState(true);
  const [isSuperadmin, setIsSuperadmin] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      if (initialData) {
        setName(initialData.name || "");
        setEmail(initialData.email || "");
        setPassword("");
        setRole(initialData.role || "editor");
        setSelectedOrgId(initialData.org_id || orgId || "");
        setIsActive(initialData.is_active ?? true);
        setIsSuperadmin(initialData.is_superadmin || false);
      } else {
        setName(""); setEmail(""); setPassword("");
        setRole("editor");
        setSelectedOrgId(orgId || "");
        setIsActive(true);
        setIsSuperadmin(false);
      }
    }
  }, [isOpen, initialData, orgId]);

  const handleSave = async () => {
    if (!email.trim()) { toast.error("El email es obligatorio"); return; }
    if (!isEditing && !password.trim()) { toast.error("La contraseña es obligatoria al crear"); return; }

    setSaving(true);
    try {
      let url, method, body;

      if (isEditing) {
        url = `${API_BASE_URL}/superadmin/users/${initialData.id}`;
        method = "PUT";
        body = { name, email, role, org_id: Number(selectedOrgId), is_active: isActive, is_superadmin: isSuperadmin };
        if (password.trim()) body.password = password;
      } else {
        url = `${API_BASE_URL}/superadmin/organizations/${selectedOrgId}/users`;
        method = "POST";
        body = { name, email, password, role, is_active: isActive, is_superadmin: isSuperadmin };
      }

      const res = await fetchAuth(url, { method, body: JSON.stringify(body) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Error al guardar");

      toast.success(isEditing ? "Usuario actualizado" : "Usuario creado");
      onSave && onSave(data);
      onClose();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  const isSelf = initialData?.id === me?.id;

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-white dark:bg-slate-900 shadow-2xl z-50 overflow-y-auto border-l border-slate-200 dark:border-slate-800 animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-lg font-bold text-slate-800 dark:text-white">
            {isEditing ? "Editar Usuario" : "Nuevo Usuario"}
          </h2>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500">
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <div className="p-5 space-y-5">
          {/* Nombre */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Nombre</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Nombre del usuario"
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-violet-500 outline-none transition"
            />
          </div>

          {/* Email */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Email *</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="correo@ejemplo.com"
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-violet-500 outline-none transition"
            />
          </div>

          {/* Contraseña */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              Contraseña {isEditing ? "(dejar vacío para no cambiar)" : "*"}
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={isEditing ? "Nueva contraseña (opcional)" : "Mínimo 6 caracteres"}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-violet-500 outline-none transition"
            />
          </div>

          {/* Organización */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Organización *</label>
            <select
              value={selectedOrgId}
              onChange={e => setSelectedOrgId(e.target.value)}
              disabled={!!orgId && !isEditing}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white focus:ring-2 focus:ring-violet-500 outline-none transition disabled:opacity-60"
            >
              <option value="">Selecciona organización</option>
              {orgs.map(o => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
            </select>
          </div>

          {/* Rol */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Rol en la organización</label>
            <select
              value={role}
              onChange={e => setRole(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white focus:ring-2 focus:ring-violet-500 outline-none transition"
            >
              {ROLES.map(r => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </div>

          {/* Estado activo */}
          {isEditing && !isSelf && (
            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <div>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Usuario activo</p>
                <p className="text-xs text-slate-400">Los usuarios inactivos no pueden iniciar sesión</p>
              </div>
              <button
                type="button"
                onClick={() => setIsActive(v => !v)}
                className={`relative w-11 h-6 rounded-full transition-colors duration-300 ${isActive ? "bg-emerald-500" : "bg-slate-300 dark:bg-slate-600"}`}
              >
                <div className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow-sm transition-transform duration-300 ${isActive ? "translate-x-5" : "translate-x-0"}`} />
              </button>
            </div>
          )}

          {/* Superadmin */}
          <div className={`flex items-center justify-between p-4 rounded-xl border ${
            isSuperadmin
              ? "bg-violet-50 dark:bg-violet-900/20 border-violet-200 dark:border-violet-800"
              : "bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700"
          }`}>
            <div className="flex items-start gap-3">
              <ShieldCheck size={20} className={isSuperadmin ? "text-violet-600 mt-0.5" : "text-slate-400 mt-0.5"} />
              <div>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Superadministrador</p>
                <p className="text-xs text-slate-400">Acceso al panel de gestión global de orgs y usuarios</p>
              </div>
            </div>
            <button
              type="button"
              disabled={isSelf}
              onClick={() => !isSelf && setIsSuperadmin(v => !v)}
              className={`relative w-11 h-6 rounded-full transition-colors duration-300 disabled:opacity-50 ${isSuperadmin ? "bg-violet-600" : "bg-slate-300 dark:bg-slate-600"}`}
            >
              <div className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow-sm transition-transform duration-300 ${isSuperadmin ? "translate-x-5" : "translate-x-0"}`} />
            </button>
          </div>
          {isSelf && (
            <p className="text-xs text-slate-400 -mt-3 px-1">No puedes modificar tu propio acceso de superadmin.</p>
          )}
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
