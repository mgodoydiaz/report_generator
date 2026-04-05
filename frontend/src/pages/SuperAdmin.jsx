import { useState, useEffect, useMemo } from "react";
import {
  Building2, Users, Plus, Search, Pencil, Trash2,
  RefreshCw, UserPlus, ChevronRight, ChevronDown,
  ShieldCheck, ToggleLeft, ToggleRight,
} from "lucide-react";
import { API_BASE_URL } from "../constants";
import { useAuth } from "../context/AuthContext";
import OrgDrawer from "../components/OrgDrawer";
import SuperUserDrawer from "../components/SuperUserDrawer";
import toast from "react-hot-toast";

// ─── Role badge ──────────────────────────────────────────────────────────────
const ROLE_BADGES = {
  admin:  "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300",
  editor: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  viewer: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400",
};

// ─── Component ───────────────────────────────────────────────────────────────
export default function SuperAdmin() {
  const { fetchAuth, user: me } = useAuth();

  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Expandir filas para ver usuarios
  const [expanded, setExpanded] = useState({});
  const [orgUsers, setOrgUsers] = useState({}); // { orgId: [...users] }
  const [loadingUsers, setLoadingUsers] = useState({});

  // Drawers
  const [orgDrawer, setOrgDrawer] = useState({ open: false, data: null });
  const [userDrawer, setUserDrawer] = useState({ open: false, data: null, orgId: null });

  // ─── Fetch orgs ──────────────────────────────────────────────
  const fetchOrgs = async () => {
    setLoading(true);
    try {
      const res = await fetchAuth(`${API_BASE_URL}/superadmin/organizations`);
      if (!res.ok) throw new Error("Error al cargar organizaciones");
      setOrgs(await res.json());
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchOrgs(); }, []);

  // ─── Fetch users of an org ────────────────────────────────────
  const fetchOrgUsers = async (orgId) => {
    setLoadingUsers(prev => ({ ...prev, [orgId]: true }));
    try {
      const res = await fetchAuth(`${API_BASE_URL}/superadmin/organizations/${orgId}/users`);
      if (!res.ok) throw new Error("Error al cargar usuarios");
      setOrgUsers(prev => ({ ...prev, [orgId]: await res.json() }));
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoadingUsers(prev => ({ ...prev, [orgId]: false }));
    }
  };

  const toggleExpand = (orgId) => {
    const next = !expanded[orgId];
    setExpanded(prev => ({ ...prev, [orgId]: next }));
    if (next && !orgUsers[orgId]) {
      fetchOrgUsers(orgId);
    }
  };

  // ─── Delete org ───────────────────────────────────────────────
  const handleDeleteOrg = async (org) => {
    if (!confirm(`¿Eliminar la organización "${org.name}"? Esta acción es irreversible.`)) return;
    try {
      const res = await fetchAuth(`${API_BASE_URL}/superadmin/organizations/${org.id}`, { method: "DELETE" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Error al eliminar");
      toast.success("Organización eliminada");
      fetchOrgs();
    } catch (err) {
      toast.error(err.message);
    }
  };

  // ─── Toggle org active ────────────────────────────────────────
  const handleToggleOrg = async (org) => {
    try {
      const res = await fetchAuth(`${API_BASE_URL}/superadmin/organizations/${org.id}`, {
        method: "PUT",
        body: JSON.stringify({ is_active: !org.is_active }),
      });
      if (!res.ok) throw new Error("Error al actualizar");
      toast.success(org.is_active ? "Organización desactivada" : "Organización activada");
      fetchOrgs();
    } catch (err) {
      toast.error(err.message);
    }
  };

  // ─── Toggle user active ───────────────────────────────────────
  const handleToggleUser = async (user, orgId) => {
    if (user.id === me?.id) { toast.error("No puedes modificar tu propia cuenta aquí"); return; }
    try {
      const res = await fetchAuth(`${API_BASE_URL}/superadmin/users/${user.id}`, {
        method: "PUT",
        body: JSON.stringify({ is_active: !user.is_active }),
      });
      if (!res.ok) throw new Error("Error al actualizar usuario");
      toast.success(user.is_active ? "Usuario desactivado" : "Usuario activado");
      fetchOrgUsers(orgId);
    } catch (err) {
      toast.error(err.message);
    }
  };

  // ─── Filter orgs ─────────────────────────────────────────────
  const filteredOrgs = useMemo(() => {
    if (!search.trim()) return orgs;
    const q = search.toLowerCase();
    return orgs.filter(o =>
      o.name.toLowerCase().includes(q) ||
      o.slug.toLowerCase().includes(q)
    );
  }, [orgs, search]);

  // ─── Render ───────────────────────────────────────────────────
  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-500">

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-violet-100 dark:bg-violet-900/40 rounded-2xl">
            <ShieldCheck className="w-8 h-8 text-violet-600 dark:text-violet-400" />
          </div>
          <div>
            <h1 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight">
              Superadministrador
            </h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
              Gestiona organizaciones y usuarios globales
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchOrgs}
            className="p-3 rounded-2xl border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition"
            title="Refrescar"
          >
            <RefreshCw size={18} />
          </button>
          <button
            onClick={() => setOrgDrawer({ open: true, data: null })}
            className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700 text-white px-5 py-3 rounded-2xl font-semibold shadow-md hover:shadow-lg active:scale-95 transition"
          >
            <Plus size={18} /> Nueva organización
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Buscar por nombre o slug..."
          className="w-full pl-11 pr-4 py-3 rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-violet-500 outline-none transition"
        />
      </div>

      {/* Table de orgs */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-6 h-6 border-4 border-violet-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filteredOrgs.length === 0 ? (
          <div className="text-center py-16 text-slate-400 dark:text-slate-600">
            {search ? "Sin resultados" : "No hay organizaciones registradas"}
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider w-8" />
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Organización</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Slug</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Usuarios activos</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Estado</th>
                <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrgs.map(org => (
                <>
                  {/* Fila principal de la org */}
                  <tr
                    key={org.id}
                    className="border-b border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition"
                  >
                    {/* Expand button */}
                    <td className="pl-5 pr-1 py-3.5">
                      <button
                        onClick={() => toggleExpand(org.id)}
                        className="p-1 rounded-lg text-slate-400 hover:text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-900/20 transition"
                        title={expanded[org.id] ? "Contraer usuarios" : "Ver usuarios"}
                      >
                        {expanded[org.id]
                          ? <ChevronDown size={16} />
                          : <ChevronRight size={16} />
                        }
                      </button>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="font-medium text-sm text-slate-800 dark:text-white">{org.name}</div>
                      {org.description && (
                        <div className="text-xs text-slate-400 mt-0.5 truncate max-w-xs">{org.description}</div>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-sm text-slate-500 dark:text-slate-400 font-mono">
                      {org.slug}
                    </td>
                    <td className="px-5 py-3.5 text-sm text-slate-600 dark:text-slate-300">
                      <span className="inline-flex items-center gap-1.5">
                        <Users size={14} className="text-slate-400" />
                        {org.user_count}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-semibold ${
                        org.is_active
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                          : "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300"
                      }`}>
                        {org.is_active ? "Activa" : "Inactiva"}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {/* Agregar usuario */}
                        <button
                          onClick={() => setUserDrawer({ open: true, data: null, orgId: org.id })}
                          className="p-2 rounded-xl hover:bg-violet-50 dark:hover:bg-violet-900/20 text-slate-400 hover:text-violet-600 transition"
                          title="Agregar usuario"
                        >
                          <UserPlus size={16} />
                        </button>
                        {/* Editar org */}
                        <button
                          onClick={() => setOrgDrawer({ open: true, data: org })}
                          className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-indigo-600 transition"
                          title="Editar"
                        >
                          <Pencil size={16} />
                        </button>
                        {/* Toggle activo */}
                        <button
                          onClick={() => handleToggleOrg(org)}
                          className={`p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition ${
                            org.is_active ? "text-slate-400 hover:text-rose-600" : "text-slate-400 hover:text-emerald-600"
                          }`}
                          title={org.is_active ? "Desactivar" : "Activar"}
                        >
                          {org.is_active ? <ToggleRight size={16} /> : <ToggleLeft size={16} />}
                        </button>
                        {/* Eliminar */}
                        <button
                          onClick={() => handleDeleteOrg(org)}
                          className="p-2 rounded-xl hover:bg-rose-50 dark:hover:bg-rose-900/20 text-slate-400 hover:text-rose-600 transition"
                          title="Eliminar"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* Filas expandidas de usuarios */}
                  {expanded[org.id] && (
                    <tr key={`users-${org.id}`} className="bg-slate-50 dark:bg-slate-800/20">
                      <td colSpan={6} className="px-8 py-3">
                        {loadingUsers[org.id] ? (
                          <div className="flex items-center gap-2 text-sm text-slate-400 py-2">
                            <div className="w-4 h-4 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                            Cargando usuarios...
                          </div>
                        ) : !orgUsers[org.id] || orgUsers[org.id].length === 0 ? (
                          <p className="text-sm text-slate-400 py-2 italic">Sin usuarios en esta organización</p>
                        ) : (
                          <div className="space-y-1">
                            <div className="grid grid-cols-[2fr_2fr_1fr_1fr_auto] gap-3 text-xs font-semibold text-slate-400 uppercase tracking-wider pb-1 border-b border-slate-200 dark:border-slate-700">
                              <span>Nombre</span>
                              <span>Email</span>
                              <span>Rol</span>
                              <span>Estado</span>
                              <span className="text-right">Acciones</span>
                            </div>
                            {orgUsers[org.id].map(u => (
                              <div
                                key={u.id}
                                className="grid grid-cols-[2fr_2fr_1fr_1fr_auto] gap-3 items-center py-1.5 text-sm"
                              >
                                <span className="text-slate-700 dark:text-slate-300 font-medium flex items-center gap-1.5">
                                  {u.name || "—"}
                                  {u.is_superadmin && (
                                    <ShieldCheck size={13} className="text-violet-500" title="Superadmin" />
                                  )}
                                </span>
                                <span className="text-slate-500 dark:text-slate-400 truncate">{u.email}</span>
                                <span className={`inline-block px-2 py-0.5 rounded-md text-xs font-semibold ${ROLE_BADGES[u.role] || ROLE_BADGES.viewer}`}>
                                  {u.role}
                                </span>
                                <span className={`inline-block px-2 py-0.5 rounded-md text-xs font-semibold ${
                                  u.is_active
                                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                                    : "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300"
                                }`}>
                                  {u.is_active ? "Activo" : "Inactivo"}
                                </span>
                                <div className="flex justify-end gap-1">
                                  <button
                                    onClick={() => setUserDrawer({ open: true, data: u, orgId: org.id })}
                                    className="p-1.5 rounded-lg hover:bg-white dark:hover:bg-slate-800 text-slate-400 hover:text-indigo-600 transition"
                                    title="Editar"
                                  >
                                    <Pencil size={14} />
                                  </button>
                                  {u.id !== me?.id && (
                                    <button
                                      onClick={() => handleToggleUser(u, org.id)}
                                      className={`p-1.5 rounded-lg hover:bg-white dark:hover:bg-slate-800 transition ${
                                        u.is_active ? "text-slate-400 hover:text-rose-600" : "text-slate-400 hover:text-emerald-600"
                                      }`}
                                      title={u.is_active ? "Desactivar" : "Activar"}
                                    >
                                      {u.is_active ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                                    </button>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Drawers */}
      <OrgDrawer
        isOpen={orgDrawer.open}
        onClose={() => setOrgDrawer({ open: false, data: null })}
        initialData={orgDrawer.data}
        onSave={() => { fetchOrgs(); }}
      />
      <SuperUserDrawer
        isOpen={userDrawer.open}
        onClose={() => setUserDrawer({ open: false, data: null, orgId: null })}
        initialData={userDrawer.data}
        orgId={userDrawer.orgId}
        orgs={orgs}
        onSave={() => {
          if (userDrawer.orgId) fetchOrgUsers(userDrawer.orgId);
          fetchOrgs();
        }}
      />
    </div>
  );
}
