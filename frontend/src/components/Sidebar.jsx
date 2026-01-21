import { NavLink } from "react-router-dom";

const linkClass = ({ isActive }) =>
  isActive ? "nav-link active" : "nav-link";

export default function Sidebar() {
  return (
    <div
      className="offcanvas-lg offcanvas-start"
      tabIndex="-1"
      id="mainMenu"
      aria-labelledby="mainMenuLabel"
    >
      <div className="offcanvas-header">
        <h5 className="offcanvas-title" id="mainMenuLabel">
          Menu
        </h5>
        <button
          type="button"
          className="btn-close"
          data-bs-dismiss="offcanvas"
          aria-label="Cerrar"
        ></button>
      </div>
      <div className="offcanvas-body">
        <div className="nav flex-column nav-pills gap-2">
          <NavLink className={linkClass} to="/" data-bs-dismiss="offcanvas">
            Inicio
          </NavLink>
          <NavLink
            className={linkClass}
            to="/evaluaciones"
            data-bs-dismiss="offcanvas"
          >
            Evaluaciones
          </NavLink>
          <a className="nav-link" href="#" data-bs-dismiss="offcanvas">
            Plantillas
          </a>
          <NavLink
            className={linkClass}
            to="/resultados"
            data-bs-dismiss="offcanvas"
          >
            Resultados
          </NavLink>
          <a className="nav-link" href="#" data-bs-dismiss="offcanvas">
            Valores
          </a>
          <a className="nav-link" href="#" data-bs-dismiss="offcanvas">
            Analisis y alertas
          </a>
          <a className="nav-link" href="#" data-bs-dismiss="offcanvas">
            Ayuda
          </a>
          <a className="nav-link" href="#" data-bs-dismiss="offcanvas">
            Configuracion
          </a>
        </div>
      </div>
    </div>
  );
}
