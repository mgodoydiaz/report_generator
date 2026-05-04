import { useState, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BoxPlot, ComposedChart, Scatter, ResponsiveContainer, Cell,
  LineChart, Line, ReferenceLine
} from "recharts";

// ─── DATOS DE EJEMPLO (extraídos de los Excel reales) ────────────────────────
const ESTUDIANTES = [
  { curso: "2A", nombre: "Alumno 1",  rend: 0.72, simce: 298, logro: "Adecuado",    avance: 0.05,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2A", nombre: "Alumno 2",  rend: 0.59, simce: 271, logro: "Elemental",   avance: -0.02, mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2A", nombre: "Alumno 3",  rend: 0.38, simce: 232, logro: "Insuficiente",avance: 0.03,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2A", nombre: "Alumno 4",  rend: 0.80, simce: 311, logro: "Adecuado",    avance: 0.08,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2A", nombre: "Alumno 5",  rend: 0.65, simce: 284, logro: "Elemental",   avance: 0.01,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2A", nombre: "Alumno 6",  rend: 0.55, simce: 264, logro: "Elemental",   avance: -0.04, mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2B", nombre: "Alumno 7",  rend: 0.49, simce: 252, logro: "Insuficiente",avance: 0.06,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2B", nombre: "Alumno 8",  rend: 0.61, simce: 277, logro: "Elemental",   avance: 0.02,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2B", nombre: "Alumno 9",  rend: 0.70, simce: 294, logro: "Adecuado",    avance: 0.10,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2B", nombre: "Alumno 10", rend: 0.42, simce: 241, logro: "Insuficiente",avance: -0.01, mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2B", nombre: "Alumno 11", rend: 0.53, simce: 262, logro: "Elemental",   avance: 0.03,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2C", nombre: "Alumno 12", rend: 0.41, simce: 237, logro: "Insuficiente",avance: 0.00,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2C", nombre: "Alumno 13", rend: 0.64, simce: 287, logro: "Elemental",   avance: 0.04,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2C", nombre: "Alumno 14", rend: 0.75, simce: 302, logro: "Adecuado",    avance: 0.07,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2C", nombre: "Alumno 15", rend: 0.50, simce: 257, logro: "Elemental",   avance: -0.03, mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2D", nombre: "Alumno 16", rend: 0.68, simce: 290, logro: "Adecuado",    avance: 0.09,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2D", nombre: "Alumno 17", rend: 0.44, simce: 245, logro: "Insuficiente",avance: 0.02,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2D", nombre: "Alumno 18", rend: 0.57, simce: 269, logro: "Elemental",   avance: -0.01, mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2D", nombre: "Alumno 19", rend: 0.83, simce: 317, logro: "Adecuado",    avance: 0.05,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
  { curso: "2D", nombre: "Alumno 20", rend: 0.62, simce: 280, logro: "Elemental",   avance: 0.03,  mes: "Noviembre", prueba: 5, asignatura: "Lenguaje" },
];

const PREGUNTAS = [
  { pregunta: 1,  curso: "2A", habilidad: "SINTETIZAR",  logro: 0.67, correcta: "b" },
  { pregunta: 2,  curso: "2A", habilidad: "LOCALIZAR",   logro: 0.83, correcta: "a" },
  { pregunta: 3,  curso: "2A", habilidad: "INFERIR",     logro: 0.50, correcta: "c" },
  { pregunta: 4,  curso: "2A", habilidad: "EVALUAR",     logro: 0.33, correcta: "d" },
  { pregunta: 5,  curso: "2A", habilidad: "INTERPRETAR", logro: 0.72, correcta: "a" },
  { pregunta: 1,  curso: "2B", habilidad: "SINTETIZAR",  logro: 0.55, correcta: "b" },
  { pregunta: 2,  curso: "2B", habilidad: "LOCALIZAR",   logro: 0.75, correcta: "a" },
  { pregunta: 3,  curso: "2B", habilidad: "INFERIR",     logro: 0.45, correcta: "c" },
  { pregunta: 4,  curso: "2B", habilidad: "EVALUAR",     logro: 0.60, correcta: "d" },
  { pregunta: 5,  curso: "2B", habilidad: "INTERPRETAR", logro: 0.40, correcta: "a" },
  { pregunta: 1,  curso: "2C", habilidad: "SINTETIZAR",  logro: 0.48, correcta: "b" },
  { pregunta: 2,  curso: "2C", habilidad: "LOCALIZAR",   logro: 0.70, correcta: "a" },
  { pregunta: 3,  curso: "2C", habilidad: "INFERIR",     logro: 0.55, correcta: "c" },
  { pregunta: 4,  curso: "2C", habilidad: "EVALUAR",     logro: 0.42, correcta: "d" },
  { pregunta: 5,  curso: "2C", habilidad: "INTERPRETAR", logro: 0.65, correcta: "a" },
  { pregunta: 1,  curso: "2D", habilidad: "SINTETIZAR",  logro: 0.62, correcta: "b" },
  { pregunta: 2,  curso: "2D", habilidad: "LOCALIZAR",   logro: 0.78, correcta: "a" },
  { pregunta: 3,  curso: "2D", habilidad: "INFERIR",     logro: 0.53, correcta: "c" },
  { pregunta: 4,  curso: "2D", habilidad: "EVALUAR",     logro: 0.38, correcta: "d" },
  { pregunta: 5,  curso: "2D", habilidad: "INTERPRETAR", logro: 0.70, correcta: "a" },
];

const EVOLUCION = [
  { mes: "Abril",     "2A": 52, "2B": 48, "2C": 50, "2D": 55 },
  { mes: "Junio",     "2A": 55, "2B": 51, "2C": 53, "2D": 57 },
  { mes: "Agosto",    "2A": 58, "2B": 50, "2C": 54, "2D": 60 },
  { mes: "Octubre",   "2A": 60, "2B": 51, "2C": 54, "2D": 54 },
  { mes: "Noviembre", "2A": 62, "2B": 53, "2C": 56, "2D": 62 },
];

// ─── PALETAS ─────────────────────────────────────────────────────────────────
const LOGRO_COLORS = {
  Adecuado:    "#2a9d8f",
  Elemental:   "#e9c46a",
  Insuficiente:"#e76f51",
};
const CURSO_COLORS = ["#4361ee","#7209b7","#f72585","#4cc9f0"];
const CURSOS = ["2A","2B","2C","2D"];

// ─── HELPERS ─────────────────────────────────────────────────────────────────
const pct = (v) => `${Math.round(v * 100)}%`;
const avg = (arr, key) => arr.length ? arr.reduce((s, r) => s + r[key], 0) / arr.length : 0;

function KPICard({ label, value, sub, color = "#4361ee" }) {
  return (
    <div style={{
      background: "#fff", borderRadius: 12, padding: "18px 22px",
      boxShadow: "0 2px 12px #0001", borderLeft: `4px solid ${color}`,
      minWidth: 160, flex: 1,
    }}>
      <div style={{ fontSize: 12, color: "#888", fontWeight: 600, letterSpacing: 1, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 800, color: "#1a1a2e", marginTop: 4 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: "#aaa", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function NivelBadge({ nivel }) {
  const bg = { Adecuado: "#d1f0ec", Elemental: "#fdf3d0", Insuficiente: "#fce4dc" };
  const fg = { Adecuado: "#1a6b61", Elemental: "#7a6200", Insuficiente: "#9b3522" };
  return (
    <span style={{
      background: bg[nivel] || "#eee", color: fg[nivel] || "#555",
      borderRadius: 6, padding: "2px 10px", fontSize: 12, fontWeight: 700,
    }}>{nivel}</span>
  );
}

function AvancePill({ val }) {
  const n = parseFloat(val);
  const color = n > 0 ? "#2a9d8f" : n < 0 ? "#e76f51" : "#aaa";
  const sign = n > 0 ? "▲" : n < 0 ? "▼" : "—";
  return (
    <span style={{ color, fontWeight: 700, fontSize: 13 }}>
      {sign} {n !== 0 ? pct(Math.abs(n)) : ""}
    </span>
  );
}

// ─── GRÁFICO BARRAS APILADAS NIVELES ─────────────────────────────────────────
function GraficoNivelesPorCurso({ data }) {
  const resumen = CURSOS.map((c) => {
    const alumnos = data.filter(r => r.curso === c);
    return {
      curso: c,
      Adecuado:    alumnos.filter(r => r.logro === "Adecuado").length,
      Elemental:   alumnos.filter(r => r.logro === "Elemental").length,
      Insuficiente:alumnos.filter(r => r.logro === "Insuficiente").length,
    };
  });
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={resumen} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
        <XAxis dataKey="curso" tick={{ fontWeight: 700, fontSize: 13 }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 13 }} />
        {["Insuficiente","Elemental","Adecuado"].map(n => (
          <Bar key={n} dataKey={n} stackId="a" fill={LOGRO_COLORS[n]} radius={n === "Adecuado" ? [4,4,0,0] : [0,0,0,0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── GRÁFICO LOGRO PROMEDIO POR CURSO ────────────────────────────────────────
function GraficoLogroPorCurso({ data, onCursoClick, cursoActivo }) {
  const resumen = CURSOS.map((c, i) => ({
    curso: c,
    logro: avg(data.filter(r => r.curso === c), "rend"),
    color: CURSO_COLORS[i],
  }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={resumen} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}
        onClick={(d) => d?.activePayload && onCursoClick(d.activePayload[0].payload.curso)}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
        <XAxis dataKey="curso" tick={{ fontWeight: 700, fontSize: 13 }} />
        <YAxis tickFormatter={v => `${Math.round(v*100)}%`} domain={[0,1]} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v) => pct(v)} />
        <Bar dataKey="logro" radius={[6,6,0,0]} label={{ position: "top", formatter: pct, fontSize: 12, fontWeight: 700 }}>
          {resumen.map((entry) => (
            <Cell key={entry.curso}
              fill={entry.curso === cursoActivo ? "#f72585" : entry.color}
              opacity={cursoActivo && entry.curso !== cursoActivo ? 0.4 : 1}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── GRÁFICO HABILIDADES POR CURSO ───────────────────────────────────────────
function GraficoHabilidades({ curso }) {
  const habilidades = [...new Set(PREGUNTAS.map(r => r.habilidad))];
  const data = habilidades.map(h => ({
    habilidad: h.charAt(0) + h.slice(1).toLowerCase(),
    logro: avg(PREGUNTAS.filter(r => r.curso === curso && r.habilidad === h), "logro"),
  }));
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 30, bottom: 0, left: 80 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
        <XAxis type="number" tickFormatter={v => `${Math.round(v*100)}%`} domain={[0,1]} tick={{ fontSize: 12 }} />
        <YAxis type="category" dataKey="habilidad" tick={{ fontSize: 12, fontWeight: 600 }} width={80} />
        <Tooltip formatter={(v) => pct(v)} />
        <Bar dataKey="logro" fill="#4361ee" radius={[0,6,6,0]}
          label={{ position: "right", formatter: pct, fontSize: 12, fontWeight: 700 }} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── EVOLUCIÓN TEMPORAL ───────────────────────────────────────────────────────
function GraficoEvolucion() {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={EVOLUCION} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="mes" tick={{ fontSize: 12 }} />
        <YAxis domain={[40, 75]} tickFormatter={v => `${v}%`} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v) => `${v}%`} />
        <Legend />
        {CURSOS.map((c, i) => (
          <Line key={c} type="monotone" dataKey={c} stroke={CURSO_COLORS[i]}
            strokeWidth={2.5} dot={{ r: 5 }} activeDot={{ r: 7 }} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

// ─── TABLA ALUMNOS ────────────────────────────────────────────────────────────
function TablaAlumnos({ curso }) {
  const alumnos = ESTUDIANTES.filter(r => r.curso === curso)
    .sort((a, b) => b.rend - a.rend);
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ background: "#f7f8fc", borderBottom: "2px solid #e8eaf0" }}>
            {["#","Estudiante","Logro %","SIMCE","Nivel","Avance"].map(h => (
              <th key={h} style={{ padding: "10px 14px", textAlign: "left", color: "#555", fontWeight: 700, fontSize: 12, letterSpacing: 0.5 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {alumnos.map((a, i) => (
            <tr key={a.nombre} style={{ borderBottom: "1px solid #f0f0f0", background: i % 2 === 0 ? "#fff" : "#fafbff" }}>
              <td style={{ padding: "9px 14px", color: "#bbb", fontWeight: 600 }}>{i + 1}</td>
              <td style={{ padding: "9px 14px", fontWeight: 600 }}>{a.nombre}</td>
              <td style={{ padding: "9px 14px", fontWeight: 700, color: "#1a1a2e" }}>{pct(a.rend)}</td>
              <td style={{ padding: "9px 14px" }}>{a.simce}</td>
              <td style={{ padding: "9px 14px" }}><NivelBadge nivel={a.logro} /></td>
              <td style={{ padding: "9px 14px" }}><AvancePill val={a.avance} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── TABLA PREGUNTAS ──────────────────────────────────────────────────────────
function TablaPreguntas({ curso }) {
  const preguntas = PREGUNTAS.filter(r => r.curso === curso).sort((a, b) => b.logro - a.logro);
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ background: "#f7f8fc", borderBottom: "2px solid #e8eaf0" }}>
            {["N°","Habilidad","Logro %","Correcta"].map(h => (
              <th key={h} style={{ padding: "10px 14px", textAlign: "left", color: "#555", fontWeight: 700, fontSize: 12 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {preguntas.map((p, i) => (
            <tr key={p.pregunta} style={{ borderBottom: "1px solid #f0f0f0", background: i % 2 === 0 ? "#fff" : "#fafbff" }}>
              <td style={{ padding: "9px 14px", color: "#bbb", fontWeight: 600 }}>{p.pregunta}</td>
              <td style={{ padding: "9px 14px", fontWeight: 600 }}>{p.habilidad.charAt(0)+p.habilidad.slice(1).toLowerCase()}</td>
              <td style={{ padding: "9px 14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ flex: 1, height: 6, background: "#eee", borderRadius: 3 }}>
                    <div style={{ width: `${p.logro*100}%`, height: "100%", background: p.logro >= 0.6 ? "#2a9d8f" : p.logro >= 0.45 ? "#e9c46a" : "#e76f51", borderRadius: 3 }} />
                  </div>
                  <span style={{ fontWeight: 700, width: 38 }}>{pct(p.logro)}</span>
                </div>
              </td>
              <td style={{ padding: "9px 14px", fontWeight: 700, textTransform: "uppercase", color: "#4361ee" }}>{p.correcta}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── COMPONENTE PRINCIPAL ─────────────────────────────────────────────────────
export default function ResultadosDashboard() {
  const [asignatura, setAsignatura] = useState("Lenguaje");
  const [prueba,     setPrueba]     = useState("5");
  const [mes,        setMes]        = useState("Noviembre");
  const [año,        setAño]        = useState("2025");
  const [cursoActivo, setCursoActivo] = useState(null);
  const [tab, setTab] = useState("general"); // "general" | "curso" | "evolucion"

  const datosFiltrados = useMemo(() =>
    ESTUDIANTES.filter(r =>
      r.asignatura === asignatura &&
      String(r.prueba) === prueba &&
      r.mes === mes
    ), [asignatura, prueba, mes]);

  const totalAlumnos = datosFiltrados.length;
  const logroPromedio = avg(datosFiltrados, "rend");
  const simcePromedio = avg(datosFiltrados, "simce");

  const handleCursoClick = (c) => {
    setCursoActivo(c);
    setTab("curso");
  };

  const selectorStyle = {
    padding: "7px 14px", borderRadius: 8, border: "1.5px solid #e0e3ef",
    fontSize: 13, fontWeight: 600, background: "#fff", color: "#1a1a2e",
    cursor: "pointer", outline: "none",
  };
  const tabStyle = (active) => ({
    padding: "9px 22px", borderRadius: "8px 8px 0 0", cursor: "pointer",
    fontWeight: 700, fontSize: 13, border: "none", outline: "none",
    background: active ? "#fff" : "transparent",
    color: active ? "#4361ee" : "#888",
    borderBottom: active ? "3px solid #4361ee" : "3px solid transparent",
    transition: "all 0.15s",
  });

  return (
    <div style={{ fontFamily: "'DM Sans', 'Segoe UI', sans-serif", background: "#f4f6fb", minHeight: "100vh", padding: 0 }}>

      {/* ── TOPBAR ── */}
      <div style={{ background: "#1a1a2e", padding: "14px 32px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <span style={{ color: "#fff", fontWeight: 800, fontSize: 18, letterSpacing: -0.5 }}>PHP Pullinque</span>
          <span style={{ color: "#4cc9f0", marginLeft: 10, fontSize: 13, fontWeight: 500 }}>Resultados Académicos</span>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <select style={selectorStyle} value={asignatura} onChange={e => setAsignatura(e.target.value)}>
            <option>Lenguaje</option>
            <option>Matemática</option>
          </select>
          <select style={selectorStyle} value={año} onChange={e => setAño(e.target.value)}>
            <option>2025</option>
            <option>2026</option>
          </select>
          <select style={selectorStyle} value={prueba} onChange={e => setPrueba(e.target.value)}>
            {["1","2","3","4","5"].map(p => <option key={p}>Ensayo N°{p}</option>)}
          </select>
          <select style={selectorStyle} value={mes} onChange={e => setMes(e.target.value)}>
            {["Abril","Junio","Agosto","Octubre","Noviembre"].map(m => <option key={m}>{m}</option>)}
          </select>
        </div>
      </div>

      <div style={{ padding: "0 32px 32px" }}>

        {/* ── KPIs ── */}
        <div style={{ display: "flex", gap: 16, margin: "24px 0 20px" }}>
          <KPICard label="Total alumnos" value={totalAlumnos} sub="en los 4 cursos" color="#4361ee" />
          <KPICard label="Logro promedio" value={pct(logroPromedio)} sub="rendimiento general" color="#2a9d8f" />
          <KPICard label="SIMCE promedio" value={Math.round(simcePromedio)} sub="puntaje estimado" color="#f72585" />
          <KPICard
            label="Nivel predominante"
            value={["Adecuado","Elemental","Insuficiente"].sort((a,b) =>
              datosFiltrados.filter(r=>r.logro===b).length - datosFiltrados.filter(r=>r.logro===a).length
            )[0]}
            sub="más frecuente"
            color="#e9c46a"
          />
        </div>

        {/* ── TABS ── */}
        <div style={{ display: "flex", gap: 4, borderBottom: "1px solid #e0e3ef", marginBottom: 0 }}>
          <button style={tabStyle(tab === "general")}  onClick={() => setTab("general")}>Vista General</button>
          <button style={tabStyle(tab === "curso")}    onClick={() => setTab("curso")}
            disabled={!cursoActivo}>
            {cursoActivo ? `Detalle Curso ${cursoActivo}` : "Detalle Curso"}
          </button>
          <button style={tabStyle(tab === "evolucion")} onClick={() => setTab("evolucion")}>Evolución Temporal</button>
        </div>

        {/* ── CONTENIDO TABS ── */}
        <div style={{ background: "#fff", borderRadius: "0 12px 12px 12px", padding: 28, boxShadow: "0 2px 16px #0001" }}>

          {/* TAB: GENERAL */}
          {tab === "general" && (
            <div>
              <p style={{ color: "#888", fontSize: 13, marginTop: 0, marginBottom: 24 }}>
                Haz click en una barra para ver el detalle del curso.
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28 }}>
                <div>
                  <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#555", fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>
                    Logro Promedio por Curso
                  </h3>
                  <GraficoLogroPorCurso data={datosFiltrados} onCursoClick={handleCursoClick} cursoActivo={cursoActivo} />
                </div>
                <div>
                  <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#555", fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>
                    Alumnos por Nivel de Logro
                  </h3>
                  <GraficoNivelesPorCurso data={datosFiltrados} />
                </div>
              </div>

              {/* Mini tabla resumen */}
              <div style={{ marginTop: 28 }}>
                <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#555", fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>
                  Resumen por Curso
                </h3>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "#f7f8fc" }}>
                      {["Curso","Alumnos","Promedio %","SIMCE prom","Mín","Máx","Adecuado","Elemental","Insuficiente"].map(h => (
                        <th key={h} style={{ padding: "10px 14px", textAlign: "left", color: "#555", fontWeight: 700, fontSize: 12, borderBottom: "2px solid #e8eaf0" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {CURSOS.map((c, i) => {
                      const d = datosFiltrados.filter(r => r.curso === c);
                      return (
                        <tr key={c} style={{ borderBottom: "1px solid #f0f0f0", cursor: "pointer", background: cursoActivo === c ? "#f0f3ff" : i%2===0?"#fff":"#fafbff" }}
                          onClick={() => handleCursoClick(c)}>
                          <td style={{ padding: "9px 14px", fontWeight: 800, color: CURSO_COLORS[i] }}>{c}</td>
                          <td style={{ padding: "9px 14px" }}>{d.length}</td>
                          <td style={{ padding: "9px 14px", fontWeight: 700 }}>{pct(avg(d,"rend"))}</td>
                          <td style={{ padding: "9px 14px" }}>{Math.round(avg(d,"simce"))}</td>
                          <td style={{ padding: "9px 14px", color:"#e76f51" }}>{pct(Math.min(...d.map(r=>r.rend)))}</td>
                          <td style={{ padding: "9px 14px", color:"#2a9d8f" }}>{pct(Math.max(...d.map(r=>r.rend)))}</td>
                          <td style={{ padding: "9px 14px" }}><span style={{ color:"#2a9d8f", fontWeight:700 }}>{d.filter(r=>r.logro==="Adecuado").length}</span></td>
                          <td style={{ padding: "9px 14px" }}><span style={{ color:"#c8860a", fontWeight:700 }}>{d.filter(r=>r.logro==="Elemental").length}</span></td>
                          <td style={{ padding: "9px 14px" }}><span style={{ color:"#e76f51", fontWeight:700 }}>{d.filter(r=>r.logro==="Insuficiente").length}</span></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB: DETALLE CURSO */}
          {tab === "curso" && cursoActivo && (
            <div>
              {/* Selector de curso */}
              <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
                {CURSOS.map((c, i) => (
                  <button key={c} onClick={() => setCursoActivo(c)} style={{
                    padding: "7px 18px", borderRadius: 8, border: "none", cursor: "pointer", fontWeight: 700,
                    background: cursoActivo === c ? CURSO_COLORS[i] : "#f0f0f0",
                    color: cursoActivo === c ? "#fff" : "#555",
                    fontSize: 14, transition: "all 0.15s",
                  }}>{c}</button>
                ))}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28, marginBottom: 28 }}>
                <div>
                  <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#555", fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>
                    Logro por Habilidad
                  </h3>
                  <GraficoHabilidades curso={cursoActivo} />
                </div>
                <div>
                  <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#555", fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>
                    Logro por Pregunta
                  </h3>
                  <TablaPreguntas curso={cursoActivo} />
                </div>
              </div>

              <div>
                <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#555", fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>
                  Resultados por Estudiante
                </h3>
                <TablaAlumnos curso={cursoActivo} />
              </div>
            </div>
          )}

          {tab === "curso" && !cursoActivo && (
            <div style={{ textAlign: "center", padding: 60, color: "#aaa" }}>
              Selecciona un curso desde la vista general para ver el detalle.
            </div>
          )}

          {/* TAB: EVOLUCIÓN */}
          {tab === "evolucion" && (
            <div>
              <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#555", fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>
                Evolución Logro Promedio por Curso y Mes (%)
              </h3>
              <GraficoEvolucion />
              <p style={{ color: "#aaa", fontSize: 12, marginTop: 16 }}>
                Datos de ensayos Lenguaje 2025. Los meses sin evaluación se interpolan en el gráfico.
              </p>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
