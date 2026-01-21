const rows = [
  {
    nombre: "SIMCE Matematicas",
    descripcion: "Ensayo nacional para medicion de habilidades logico-matematicas.",
    modificado: "08 Ene 2026",
  },
  {
    nombre: "SIMCE Lenguaje",
    descripcion: "Evaluacion de comprension lectora y vocabulario contextual.",
    modificado: "08 Ene 2026",
  },
  {
    nombre: "DIA Matematicas",
    descripcion: "Diagnostico Integral de Aprendizajes - Eje Numeros y Geometria.",
    modificado: "20 Dic 2025",
  },
  {
    nombre: "DIA Lenguaje",
    descripcion: "Diagnostico Integral de Aprendizajes - Eje Lectura.",
    modificado: "20 Dic 2025",
  },
  {
    nombre: "Calculo Veloz",
    descripcion: "Medicion de velocidad y precision en operaciones basicas.",
    modificado: "14 Ene 2026",
  },
  {
    nombre: "Fluidez Lectora",
    descripcion: "Evaluacion de palabras por minuto y calidad lectora.",
    modificado: "10 Ene 2026",
  },
];

export default function Evaluaciones() {
  return (
    <div className="page-evaluaciones">
      <div className="d-flex justify-content-between align-items-center mb-5">
        <div>
          <h1 className="h2 fw-bold page-title">Evaluaciones Configuradas</h1>
          <p className="text-muted mb-0">
            Administra los tipos de pruebas disponibles.
          </p>
        </div>
        <button className="btn btn-primary d-flex align-items-center gap-2 fw-bold btn-app-primary">
          <i className="bi bi-plus-lg"></i>
          <span className="d-none d-sm-inline">Agregar Evaluacion</span>
        </button>
      </div>

      <div className="table-responsive">
        <table className="table align-middle">
          <thead>
            <tr>
              <th scope="col">Evaluacion</th>
              <th scope="col">Descripcion</th>
              <th scope="col">Modificado</th>
              <th scope="col" className="text-end">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.nombre}>
                <td className="fw-semibold">{row.nombre}</td>
                <td className="text-secondary">{row.descripcion}</td>
                <td className="text-muted">{row.modificado}</td>
                <td className="text-end">
                  <div className="d-inline-flex gap-2">
                    <button className="btn btn-light btn-icon" title="Editar">
                      <i className="bi bi-pencil-fill"></i>
                    </button>
                    <button className="btn btn-light btn-icon" title="Duplicar">
                      <i className="bi bi-copy"></i>
                    </button>
                    <button
                      className="btn btn-danger btn-icon text-white btn-danger-accent"
                      title="Eliminar"
                    >
                      <i className="bi bi-trash-fill"></i>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
