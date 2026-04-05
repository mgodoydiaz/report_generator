import { useState, useEffect, useMemo } from "react";
import { Users as UsersIcon, Plus, Search, Pencil, UserX, UserCheck, RefreshCw } from "lucide-react";
import { API_BASE_URL } from "../constants";
import { useAuth } from "../context/AuthContext";
import NewUserDrawer from "../components/NewUserDrawer";
import toast from "react-hot-toast";

const ROLE_BADGES = {
  admin:  "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300",
  editor: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  viewer: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

export default function Users() {
  const { fetchAuth, user: currentUser } = useAuth();
  const isAdmin = currentUser?.role === "admin";

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busqueda, setBusqueda] = useState("");
  const [sortConfig, setSortConfig] = useState({ key: "name", direction: "asc" });

  // Drawer
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await fetchAuth(`${API_BASE_URL}/users`);
      if (!res.ok) throw new Error("Error al cargar usuarios");
      const data = await res.json();
      setUsers(data);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // Sort & filter
  const sortedUsers = useMemo(() => {
    let filtered = users.filter(
      (u) =>
        (u.name || "").toLowerCase().includes(busqueda.toLowerCase()) ||
        u.email.toLowerCase().includes(busqueda.toLowerCase())
    );
    if (sortConfig.key) {
      filtered.sort((a, b) => {
        const aVal = (a[sortConfig.key] || "").toString().toLowerCase();
        const bVal = (b[sortConfig.key] || "").toString().toLowerCase();
        return sortConfig.direction === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      });
    }
    return filtered;
  }, [users, busqueda, sortConfig]);

  const handleSort = (key) => {
    setSortConfig((prev) =>
      prev.key === key
        ? { key, direction: prev.direction === "asc" ? "desc" : "asc" }
        : { key, direction: "asc" }
    );
  };

  const handleToggleActive = async (user) => {
    if (!isAdmin) return;
    if (user.id === currentUser.id) {
      toast.error("No puedes desactivar tu propia cuenta");
      return;
    }
    try {
      const res = await fetchAuth(`${API_BASE_URL}/users/${user.id}`, {
        method: "PUT",
        body: JSON.stringify({ is_active: !user.is_active }),
      });
      if (!res.ok) throw new Error("Error al actualizar");
      toast.success(user.is_active ? "Usuario desactivado" : "Usuario activado");
      fetchUsers();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const SortIcon = ({ col }) => {
    if (sortConfig.key !== col) return null;
    return <span className="ml-1">{sortConfig.direction === "asc" ? "↑" : "↓"}</span>;
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-indigo-100 dark:bg-indigo-900/40 rounded-2xl">
            <UsersIcon className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h1 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight">
              Usuarios
            </h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
              Administra los usuarios de tu organización
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchUsers}
            className="p-3 rounded-2xl border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition"
            title="Refrescar"
          >
            <RefreshCw size={18} />
          </button>
          {isAdmin && (
            <button
              onClick={() => { setEditingUser(null); setIsDrawerOpen(true); }}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-3 rounded-2xl font-semibold shadow-md hover:shadow-lg active:scale-95 transition"
            >
              <Plus size={18} /> Nuevo usuario
            </button>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
        <input
          type="text"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Buscar por nombre o email..."
          className="w-full pl-11 pr-4 py-3 rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 outline-none transition"
        />
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-6 h-6 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : sortedUsers.length === 0 ? (
          <div className="text-center py-16 text-slate-400 dark:text-slate-600">
            {busqueda ? "Sin resultados para la búsqueda" : "No hay usuarios registrados"}
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                {[
                  { key: "name", label: "Nombre" },
                  { key: "email", label: "Email" },
                  { key: "role", label: "Rol" },
                  { key: "is_active", label: "Estado" },
                ].map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="text-left px-5 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:text-indigo-600 select-none"
                  >
                    {col.label}
                    <SortIcon col={col.key} />
                  </th>
                ))}
                <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedUsers.map((u) => (
                <tr
                  key={u.id}
                  className="border-b border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition"
                >
                  <td className="px-5 py-3.5 text-sm font-medium text-slate-800 dark:text-white">
                    {u.name || "—"}
                  </td>
                  <td className="px-5 py-3.5 text-sm text-slate-600 dark:text-slate-300">
                    {u.email}
                  </td>
                  <td className="px-5 py-3.5">
                    <span
                      className={`inline-block px-2.5 py-1 rounded-lg text-xs font-semibold ${
                        ROLE_BADGES[u.role] || ROLE_BADGES.viewer
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span
                      className={`inline-block px-2.5 py-1 rounded-lg text-xs font-semibold ${
                        u.is_active
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                          : "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300"
                      }`}
                    >
                      {u.is_active ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    {isAdmin && (
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => { setEditingUser(u); setIsDrawerOpen(true); }}
                          className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-indigo-600 transition"
                          title="Editar"
                        >
                          <Pencil size={16} />
                        </button>
                        {u.id !== currentUser.id && (
                          <button
                            onClick={() => handleToggleActive(u)}
                            className={`p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition ${
                              u.is_active
                                ? "text-slate-500 hover:text-rose-600"
                                : "text-slate-500 hover:text-emerald-600"
                            }`}
                            title={u.is_active ? "Desactivar" : "Activar"}
                          >
                            {u.is_active ? <UserX size={16} /> : <UserCheck size={16} />}
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Drawer */}
      <NewUserDrawer
        isOpen={isDrawerOpen}
        onClose={() => { setIsDrawerOpen(false); setEditingUser(null); }}
        onSave={() => fetchUsers()}
        initialData={editingUser}
      />
    </div>
  );
}
