import { Link } from "react-router-dom";

export default function Sidebar() {
  return (
    <aside className="w-60 min-h-screen bg-neutral-900 text-neutral-100 p-4">
      <nav className="space-y-3">
        <Link
          to="/inicio"
          className="block rounded-lg px-3 py-2 hover:bg-neutral-800"
        >
          Inicio
        </Link>
        <Link
          to="/plantillas"
          className="block rounded-lg px-3 py-2 hover:bg-neutral-800"
        >
          Plantillas
        </Link>
        <Link
          to="/generar-informe"
          className="block rounded-lg px-3 py-2 hover:bg-neutral-800"
        >
          Generar Informe
        </Link>
      </nav>
    </aside>
  );
}
