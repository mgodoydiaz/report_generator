const kpis = [
  { icon: "bi-people", label: "Estudiantes evaluados", value: "684" },
  { icon: "bi-graph-up", label: "Promedio global", value: "272 pts" },
  { icon: "bi-award", label: "Mejor curso", value: "2C" },
];

const rows = [
  {
    curso: "2A",
    simce: "268 pts",
    logro: "72%",
    nivel: "Medio",
    variacion: "+3.1%",
    tono: "text-success",
  },
  {
    curso: "2B",
    simce: "274 pts",
    logro: "75%",
    nivel: "Medio",
    variacion: "+2.4%",
    tono: "text-success",
  },
  {
    curso: "2C",
    simce: "281 pts",
    logro: "79%",
    nivel: "Alto",
    variacion: "+4.0%",
    tono: "text-success",
  },
  {
    curso: "2D",
    simce: "265 pts",
    logro: "69%",
    nivel: "Medio",
    variacion: "-1.2%",
    tono: "text-danger",
  },
];

const charts = [
  {
    src: "/data/output/rendimiento_promedio_por_curso.png",
    caption: "Rendimiento promedio por curso.",
  },
  {
    src: "/data/output/distribucion_puntaje_simce_por_curso.png",
    caption: "Distribucion de puntajes SIMCE por curso.",
  },
  {
    src: "/data/output/evolucion_simce_promedio_por_curso_y_mes.png",
    caption: "Evolucion SIMCE promedio por curso y mes.",
  },
  {
    src: "/data/output/evolucion_logro_promedio_por_curso_y_mes.png",
    caption: "Evolucion de logro promedio por curso y mes.",
  },
  {
    src: "/data/output/logro_promedio_por_eje.png",
    caption: "Logro promedio por eje.",
  },
  {
    src: "/data/output/logro_promedio_por_habilidad.png",
    caption: "Logro promedio por habilidad.",
  },
];

export default function Resultados() {
  return (
    <div className="page-resultados">
      <section className="hero-card results-hero p-4 p-lg-5 mb-5">
        <div className="results-hero-copy">
          <p className="eyebrow">Reporte general</p>
          <h1 className="display-6 fw-bold mb-3">Resultados trabajados 2025</h1>
          <p className="mb-4">
            Vista consolidada de resultados con promedios generales y graficos
            listos para presentacion.
          </p>
          <div className="d-flex flex-wrap gap-3">
            <button className="btn btn-app-primary">
              <i className="bi bi-download me-2"></i>Descargar resultados
            </button>
            <button className="btn btn-outline-secondary">Ver datos base</button>
          </div>
        </div>
        <div className="results-metrics">
          {kpis.map((kpi) => (
            <div className="kpi-card" key={kpi.label}>
              <div className="kpi-icon">
                <i className={`bi ${kpi.icon}`}></i>
              </div>
              <div>
                <p className="kpi-label">{kpi.label}</p>
                <p className="kpi-value">{kpi.value}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-5">
        <div className="d-flex justify-content-between align-items-end flex-wrap gap-3 mb-3">
          <div>
            <h2 className="h4 fw-bold mb-1">Promedios por curso</h2>
            <p className="text-muted mb-0">
              Sintesis general con indicadores de logro y puntaje SIMCE.
            </p>
          </div>
          <span className="badge bg-light text-dark border results-badge">
            Actualizado: 13 Oct 2025
          </span>
        </div>
        <div className="table-responsive">
          <table className="table align-middle results-table">
            <thead>
              <tr>
                <th scope="col">Curso</th>
                <th scope="col">Promedio SIMCE</th>
                <th scope="col">Logro promedio</th>
                <th scope="col">Nivel dominante</th>
                <th scope="col" className="text-end">
                  Variacion mensual
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.curso}>
                  <td className="fw-semibold">{row.curso}</td>
                  <td>{row.simce}</td>
                  <td>{row.logro}</td>
                  <td>{row.nivel}</td>
                  <td className={`text-end ${row.tono}`}>{row.variacion}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-4">
        <h2 className="h4 fw-bold mb-3">Graficos principales</h2>
        <div className="results-charts">
          {charts.map((chart) => (
            <figure className="chart-card" key={chart.src}>
              <img src={chart.src} alt={chart.caption} loading="lazy" />
              <figcaption>{chart.caption}</figcaption>
            </figure>
          ))}
        </div>
      </section>
    </div>
  );
}
