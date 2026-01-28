import { NavLink } from "react-router-dom";

const linkClass = ({ isActive }) =>
  isActive ? "nav-link active" : "nav-link";

export default function Sidebar() {
  return (
    <aside className="sidebar" aria-label="Menu principal">
      <div className="sidebar-header">
        <h5 className="sidebar-title">Menu</h5>
      </div>
      <div className="nav flex-column nav-pills gap-2">
        <NavLink className={linkClass} to="/">
          Inicio
        </NavLink>
        <NavLink className={linkClass} to="/workflows">
          Workflows
        </NavLink>
        <a className="nav-link" href="#">
          Plantillas
        </a>
        <NavLink className={linkClass} to="/resultados">
          Resultados
        </NavLink>
        <a className="nav-link" href="#">
          Valores
        </a>
        <a className="nav-link" href="#">
          Analisis y alertas
        </a>
        <a className="nav-link" href="#">
          Ayuda
        </a>
        <a className="nav-link" href="#">
          Configuracion
        </a>
      </div>
    </aside>
  );
}
