import React, { useState, useEffect, useMemo } from 'react';
import {
    ChartColumn, RefreshCcw, Search, ChevronDown, ChevronUp, Play,
    TrendingUp, TrendingDown, Minus, Users, Target, Award, BarChart3
} from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, Cell, LineChart, Line, PieChart, Pie
} from 'recharts';

// ── Paletas ──
const LOGRO_COLORS = {
    Adecuado: "#2a9d8f",
    Elemental: "#e9c46a",
    Insuficiente: "#e76f51",
};
const CURSO_COLORS = ["#4361ee", "#7209b7", "#f72585", "#4cc9f0", "#06d6a0", "#ffd166", "#118ab2", "#073b4c"];

// ── Helpers ──
const pct = (v) => `${Math.round(v * 100)}%`;
const avg = (arr, key) => arr.length ? arr.reduce((s, r) => s + r[key], 0) / arr.length : 0;

// ── Sub-componentes ──

function KPICard({ label, value, sub, icon: Icon, color = "indigo" }) {
    const colorMap = {
        indigo: "bg-indigo-50 text-indigo-600 border-indigo-100 dark:bg-indigo-900/20 dark:text-indigo-400 dark:border-indigo-800",
        emerald: "bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800",
        rose: "bg-rose-50 text-rose-600 border-rose-100 dark:bg-rose-900/20 dark:text-rose-400 dark:border-rose-800",
        amber: "bg-amber-50 text-amber-600 border-amber-100 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800",
    };
    return (
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 shadow-sm flex-1 min-w-40">
            <div className="flex items-center gap-3 mb-3">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${colorMap[color] || colorMap.indigo}`}>
                    {Icon && <Icon size={18} />}
                </div>
                <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">{label}</span>
            </div>
            <div className="text-2xl font-black text-slate-800 dark:text-white">{value}</div>
            {sub && <div className="text-xs text-slate-400 dark:text-slate-500 mt-1">{sub}</div>}
        </div>
    );
}

function NivelBadge({ nivel }) {
    const styles = {
        Adecuado: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800",
        Elemental: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800",
        Insuficiente: "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-900/20 dark:text-rose-400 dark:border-rose-800",
    };
    return (
        <span className={`px-2.5 py-0.5 rounded-lg text-[11px] font-bold border ${styles[nivel] || 'bg-slate-50 text-slate-500 border-slate-200'}`}>
            {nivel}
        </span>
    );
}

function AvancePill({ val }) {
    const n = parseFloat(val);
    if (isNaN(n)) return <span className="text-slate-300">—</span>;
    const color = n > 0 ? "text-emerald-600" : n < 0 ? "text-rose-600" : "text-slate-400";
    const Icon = n > 0 ? TrendingUp : n < 0 ? TrendingDown : Minus;
    return (
        <span className={`flex items-center gap-1 font-bold text-sm ${color}`}>
            <Icon size={14} />
            {n !== 0 ? pct(Math.abs(n)) : ""}
        </span>
    );
}

// ── Gráficos ──

function GraficoLogroPorCurso({ data, cursos, onCursoClick, cursoActivo }) {
    const resumen = cursos.map((c, i) => ({
        curso: c,
        logro: avg(data.filter(r => r._curso === c), "_rend"),
        color: CURSO_COLORS[i % CURSO_COLORS.length],
    }));
    return (
        <ResponsiveContainer width="100%" height={240}>
            <BarChart data={resumen} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}
                onClick={(d) => d?.activePayload && onCursoClick(d.activePayload[0].payload.curso)}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="curso" tick={{ fontWeight: 700, fontSize: 13 }} />
                <YAxis tickFormatter={v => `${Math.round(v * 100)}%`} domain={[0, 1]} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v) => pct(v)} />
                <Bar dataKey="logro" radius={[6, 6, 0, 0]} label={{ position: "top", formatter: pct, fontSize: 12, fontWeight: 700 }}>
                    {resumen.map((entry) => (
                        <Cell key={entry.curso}
                            fill={entry.curso === cursoActivo ? "#f72585" : entry.color}
                            opacity={cursoActivo && entry.curso !== cursoActivo ? 0.4 : 1}
                            cursor="pointer"
                        />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
}

function GraficoNivelesPorCurso({ data, cursos }) {
    const resumen = cursos.map((c) => {
        const alumnos = data.filter(r => r._curso === c);
        return {
            curso: c,
            Adecuado: alumnos.filter(r => r._logro === "Adecuado").length,
            Elemental: alumnos.filter(r => r._logro === "Elemental").length,
            Insuficiente: alumnos.filter(r => r._logro === "Insuficiente").length,
        };
    });
    return (
        <ResponsiveContainer width="100%" height={240}>
            <BarChart data={resumen} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="curso" tick={{ fontWeight: 700, fontSize: 13 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 13 }} />
                {["Insuficiente", "Elemental", "Adecuado"].map(n => (
                    <Bar key={n} dataKey={n} stackId="a" fill={LOGRO_COLORS[n]} radius={n === "Adecuado" ? [4, 4, 0, 0] : [0, 0, 0, 0]} />
                ))}
            </BarChart>
        </ResponsiveContainer>
    );
}

function GraficoHabilidades({ data }) {
    if (!data.length) return <p className="text-slate-400 text-sm">Sin datos de habilidades</p>;
    const habilidades = [...new Set(data.map(r => r._habilidad).filter(Boolean))];
    const chartData = habilidades.map(h => ({
        habilidad: h.charAt(0).toUpperCase() + h.slice(1).toLowerCase(),
        logro: avg(data.filter(r => r._habilidad === h), "_logro_pregunta"),
    }));
    return (
        <ResponsiveContainer width="100%" height={Math.max(200, habilidades.length * 40)}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 30, bottom: 0, left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                <XAxis type="number" tickFormatter={v => `${Math.round(v * 100)}%`} domain={[0, 1]} tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="habilidad" tick={{ fontSize: 12, fontWeight: 600 }} width={80} />
                <Tooltip formatter={(v) => pct(v)} />
                <Bar dataKey="logro" fill="#4361ee" radius={[0, 6, 6, 0]}
                    label={{ position: "right", formatter: pct, fontSize: 12, fontWeight: 700 }} />
            </BarChart>
        </ResponsiveContainer>
    );
}

function GraficoDistribucionNiveles({ data }) {
    const conteo = [
        { name: "Adecuado", value: data.filter(r => r._logro === "Adecuado").length, fill: LOGRO_COLORS.Adecuado },
        { name: "Elemental", value: data.filter(r => r._logro === "Elemental").length, fill: LOGRO_COLORS.Elemental },
        { name: "Insuficiente", value: data.filter(r => r._logro === "Insuficiente").length, fill: LOGRO_COLORS.Insuficiente },
    ].filter(d => d.value > 0);

    if (!conteo.length) return null;

    return (
        <ResponsiveContainer width="100%" height={240}>
            <PieChart>
                <Pie data={conteo} dataKey="value" nameKey="name" cx="50%" cy="50%"
                    outerRadius={90} innerRadius={50} paddingAngle={3} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {conteo.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                </Pie>
                <Tooltip />
            </PieChart>
        </ResponsiveContainer>
    );
}

// ── Tablas ──

function TablaAlumnos({ data }) {
    const alumnos = [...data].sort((a, b) => (b._rend || 0) - (a._rend || 0));
    if (!alumnos.length) return <p className="text-slate-400 text-sm p-4">Sin datos de estudiantes</p>;

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
                <thead>
                    <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        {["#", "Estudiante", "Logro %", "SIMCE", "Nivel", "Avance"].map(h => (
                            <th key={h} className="p-3 font-bold text-slate-400 text-[11px] uppercase tracking-widest">{h}</th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                    {alumnos.map((a, i) => (
                        <tr key={i} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/80 transition-colors">
                            <td className="p-3 text-slate-400 font-semibold">{i + 1}</td>
                            <td className="p-3 font-semibold text-slate-700 dark:text-slate-200">{a._nombre || `Estudiante ${i + 1}`}</td>
                            <td className="p-3 font-bold text-slate-800 dark:text-white">{a._rend != null ? pct(a._rend) : "—"}</td>
                            <td className="p-3 text-slate-600 dark:text-slate-300">{a._simce != null ? Math.round(a._simce) : "—"}</td>
                            <td className="p-3">{a._logro ? <NivelBadge nivel={a._logro} /> : "—"}</td>
                            <td className="p-3">{a._avance != null ? <AvancePill val={a._avance} /> : "—"}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function TablaPreguntas({ data }) {
    const preguntas = [...data].sort((a, b) => (b._logro_pregunta || 0) - (a._logro_pregunta || 0));
    if (!preguntas.length) return <p className="text-slate-400 text-sm p-4">Sin datos de preguntas</p>;

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
                <thead>
                    <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        {["N\u00b0", "Habilidad", "Logro %", "Correcta"].map(h => (
                            <th key={h} className="p-3 font-bold text-slate-400 text-[11px] uppercase tracking-widest">{h}</th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                    {preguntas.map((p, i) => (
                        <tr key={i} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/80 transition-colors">
                            <td className="p-3 text-slate-400 font-semibold">{p._pregunta || i + 1}</td>
                            <td className="p-3 font-semibold text-slate-700 dark:text-slate-200">
                                {p._habilidad ? p._habilidad.charAt(0).toUpperCase() + p._habilidad.slice(1).toLowerCase() : "—"}
                            </td>
                            <td className="p-3">
                                <div className="flex items-center gap-2">
                                    <div className="flex-1 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                        <div className="h-full rounded-full transition-all"
                                            style={{
                                                width: `${(p._logro_pregunta || 0) * 100}%`,
                                                background: (p._logro_pregunta || 0) >= 0.6 ? "#2a9d8f" : (p._logro_pregunta || 0) >= 0.45 ? "#e9c46a" : "#e76f51"
                                            }} />
                                    </div>
                                    <span className="font-bold text-slate-700 dark:text-slate-200 w-10">{pct(p._logro_pregunta || 0)}</span>
                                </div>
                            </td>
                            <td className="p-3 font-bold text-indigo-600 dark:text-indigo-400 uppercase">{p._correcta || "—"}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function TablaResumenCursos({ data, cursos, onCursoClick, cursoActivo }) {
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
                <thead>
                    <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        {["Curso", "Alumnos", "Promedio %", "SIMCE prom", "Mín", "Máx", "Adecuado", "Elemental", "Insuficiente"].map(h => (
                            <th key={h} className="p-3 font-bold text-slate-400 text-[11px] uppercase tracking-widest">{h}</th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                    {cursos.map((c, i) => {
                        const d = data.filter(r => r._curso === c);
                        if (!d.length) return null;
                        const rends = d.map(r => r._rend).filter(v => v != null);
                        return (
                            <tr key={c} className={`cursor-pointer transition-colors ${cursoActivo === c ? 'bg-indigo-50/80 dark:bg-indigo-900/20' : 'hover:bg-slate-50/80 dark:hover:bg-slate-800/80'}`}
                                onClick={() => onCursoClick(c)}>
                                <td className="p-3 font-extrabold" style={{ color: CURSO_COLORS[i % CURSO_COLORS.length] }}>{c}</td>
                                <td className="p-3 text-slate-600 dark:text-slate-300">{d.length}</td>
                                <td className="p-3 font-bold text-slate-800 dark:text-white">{rends.length ? pct(avg(d, "_rend")) : "—"}</td>
                                <td className="p-3 text-slate-600 dark:text-slate-300">{rends.length ? Math.round(avg(d, "_simce")) : "—"}</td>
                                <td className="p-3 text-rose-600">{rends.length ? pct(Math.min(...rends)) : "—"}</td>
                                <td className="p-3 text-emerald-600">{rends.length ? pct(Math.max(...rends)) : "—"}</td>
                                <td className="p-3"><span className="text-emerald-600 font-bold">{d.filter(r => r._logro === "Adecuado").length}</span></td>
                                <td className="p-3"><span className="text-amber-600 font-bold">{d.filter(r => r._logro === "Elemental").length}</span></td>
                                <td className="p-3"><span className="text-rose-600 font-bold">{d.filter(r => r._logro === "Insuficiente").length}</span></td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}


// ══════════════════════════════════════════════════════════════════════════════
// ██  COMPONENTE PRINCIPAL
// ══════════════════════════════════════════════════════════════════════════════

export default function Results() {
    // ── Estado: datos del backend ──
    const [indicators, setIndicators] = useState([]);
    const [dimensions, setDimensions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingDashboard, setLoadingDashboard] = useState(false);

    // ── Estado: selectores ──
    const [selectedIndicator, setSelectedIndicator] = useState("");
    const [selectedFilters, setSelectedFilters] = useState({});
    // Dimensiones dinámicas que el indicador requiere
    const [indicatorDims, setIndicatorDims] = useState({});
    // Métricas del indicador seleccionado
    const [indicatorMetrics, setIndicatorMetrics] = useState([]);

    // ── Estado: dashboard ──
    const [dashboardData, setDashboardData] = useState(null);
    const [tab, setTab] = useState("general");
    const [cursoActivo, setCursoActivo] = useState(null);

    // ── Carga inicial ──
    useEffect(() => {
        fetchInitialData();
    }, []);

    const fetchInitialData = async () => {
        setLoading(true);
        try {
            const [indRes, dimRes] = await Promise.all([
                fetch(`${API_BASE_URL}/indicators`),
                fetch(`${API_BASE_URL}/dimensions`),
            ]);
            const indData = indRes.ok ? await indRes.json() : [];
            const dimData = dimRes.ok ? await dimRes.json() : [];

            setIndicators(Array.isArray(indData) ? indData : []);
            setDimensions(Array.isArray(dimData) ? dimData : []);
        } catch (err) {
            toast.error("Error al cargar datos iniciales: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    // ── Al seleccionar un indicador, cargar sus dimensiones disponibles ──
    useEffect(() => {
        if (!selectedIndicator) {
            setIndicatorDims({});
            setIndicatorMetrics([]);
            setSelectedFilters({});
            return;
        }

        const loadIndicatorDims = async () => {
            try {
                // Obtener datos sin filtros para saber qué dimensiones y valores están disponibles
                const res = await fetch(`${API_BASE_URL}/results/indicator/${selectedIndicator}/data`);
                if (!res.ok) throw new Error("Error al cargar dimensiones del indicador");
                const result = await res.json();

                setIndicatorDims(result.dimensions || {});
                setIndicatorMetrics(result.metrics || []);
                setSelectedFilters({});
                setDashboardData(null);
                setCursoActivo(null);
                setTab("general");
            } catch (err) {
                toast.error(err.message);
                setIndicatorDims({});
            }
        };
        loadIndicatorDims();
    }, [selectedIndicator]);

    // ── Generar Dashboard ──
    const handleGenerateDashboard = async () => {
        if (!selectedIndicator) {
            toast.error("Selecciona un indicador");
            return;
        }

        setLoadingDashboard(true);
        setDashboardData(null);
        setCursoActivo(null);
        setTab("general");

        try {
            const filtersParam = Object.keys(selectedFilters).length > 0
                ? `?filters=${encodeURIComponent(JSON.stringify(selectedFilters))}`
                : "";
            const res = await fetch(`${API_BASE_URL}/results/indicator/${selectedIndicator}/data${filtersParam}`);
            if (!res.ok) throw new Error("Error al generar dashboard");
            const result = await res.json();

            // Procesar datos para el dashboard
            const processed = processDataForDashboard(result);
            setDashboardData(processed);

            if (processed.estudiantes.length === 0 && processed.preguntas.length === 0) {
                toast("No se encontraron datos con los filtros seleccionados", { icon: "ℹ️" });
            }
        } catch (err) {
            toast.error(err.message);
        } finally {
            setLoadingDashboard(false);
        }
    };

    // ── Procesar datos del backend al formato del dashboard ──
    const processDataForDashboard = (result) => {
        const { metrics, dimensions: dims, data } = result;
        const dimsMap = dims || {};

        // Buscar la dimensión "Curso" por nombre
        const cursoDimId = Object.keys(dimsMap).find(k => dimsMap[k].name.toLowerCase().includes("curso"));
        const nombreDimId = Object.keys(dimsMap).find(k =>
            dimsMap[k].name.toLowerCase().includes("nombre") || dimsMap[k].name.toLowerCase().includes("estudiante")
        );
        const habilidadDimId = Object.keys(dimsMap).find(k => dimsMap[k].name.toLowerCase().includes("habilidad"));
        const preguntaDimId = Object.keys(dimsMap).find(k => dimsMap[k].name.toLowerCase().includes("pregunta"));

        const estudiantes = [];
        const preguntas = [];

        // Procesar cada métrica
        for (const metric of metrics) {
            const mid = metric.id_metric;
            const metricData = data[mid] || [];
            const isObject = metric.data_type === 'object';
            const fields = isObject ? (metric.meta_json?.fields || []) : [];

            // Detectar si es métrica de estudiantes o de preguntas
            const hasPregunta = preguntaDimId && metric.dimension_ids.includes(parseInt(preguntaDimId));
            const hasHabilidad = habilidadDimId && metric.dimension_ids.includes(parseInt(habilidadDimId));

            for (const row of metricData) {
                const djson = row.dimensions_json || {};
                const val = row.value;

                const entry = {
                    _curso: cursoDimId ? (djson[cursoDimId] || "") : "",
                    _raw_dims: djson,
                };

                // Extraer valor
                if (isObject && typeof val === 'object' && val !== null) {
                    for (const f of fields) {
                        const fval = val[f.name];
                        entry[`_${f.name.toLowerCase()}`] = fval;
                    }
                } else if (!isObject) {
                    entry._value = val;
                }

                // Mapear campos conocidos
                if (nombreDimId) entry._nombre = djson[nombreDimId] || "";
                if (habilidadDimId) entry._habilidad = djson[habilidadDimId] || "";
                if (preguntaDimId) entry._pregunta = djson[preguntaDimId] || "";

                // Campos que podrían venir en value (object) o como dimensiones
                // Intentar mapear campos comunes del mockup
                if (entry._rend === undefined && entry._rendimiento !== undefined) entry._rend = entry._rendimiento;
                if (entry._rend === undefined && entry._logro_porcentaje !== undefined) entry._rend = entry._logro_porcentaje;
                if (entry._rend === undefined && entry._value !== undefined) {
                    const v = parseFloat(entry._value);
                    if (!isNaN(v) && v >= 0 && v <= 1) entry._rend = v;
                }

                // Normalizar logro
                if (!entry._logro && entry._nivel) entry._logro = entry._nivel;
                if (!entry._logro && entry._nivel_logro) entry._logro = entry._nivel_logro;
                if (!entry._logro && entry._nivel_de_logro) entry._logro = entry._nivel_de_logro;

                // Normalizar numéricos
                if (entry._rend != null) entry._rend = parseFloat(entry._rend) || 0;
                if (entry._simce != null) entry._simce = parseFloat(entry._simce) || 0;
                if (entry._avance != null) entry._avance = parseFloat(entry._avance) || 0;
                if (entry._logro_pregunta != null) entry._logro_pregunta = parseFloat(entry._logro_pregunta) || 0;
                if (entry._logro != null && typeof entry._logro === 'number') {
                    // Si logro es numérico, podría ser el logro_pregunta
                    entry._logro_pregunta = entry._logro;
                    entry._logro = undefined;
                }

                if (hasPregunta || hasHabilidad) {
                    // Datos de preguntas
                    if (entry._logro_pregunta === undefined && entry._logro === undefined) {
                        if (entry._rend !== undefined) {
                            entry._logro_pregunta = entry._rend;
                        } else {
                            // Intentar extraer de _value
                            const v = parseFloat(entry._value);
                            if (!isNaN(v)) entry._logro_pregunta = v <= 1 ? v : v / 100;
                        }
                    }
                    preguntas.push(entry);
                } else {
                    estudiantes.push(entry);
                }
            }
        }

        // Obtener cursos únicos
        const cursos = [...new Set(estudiantes.map(e => e._curso).filter(Boolean))].sort();

        return { estudiantes, preguntas, cursos, dimsMap };
    };

    // ── Datos computados del dashboard ──
    const dashboardComputed = useMemo(() => {
        if (!dashboardData) return null;
        const { estudiantes, preguntas, cursos } = dashboardData;

        const totalAlumnos = estudiantes.length;
        const logroPromedio = avg(estudiantes, "_rend");
        const simcePromedio = avg(estudiantes, "_simce");

        // Nivel predominante
        const niveles = ["Adecuado", "Elemental", "Insuficiente"];
        const nivelPredominante = niveles.sort((a, b) =>
            estudiantes.filter(r => r._logro === b).length - estudiantes.filter(r => r._logro === a).length
        )[0] || "—";

        return { totalAlumnos, logroPromedio, simcePromedio, nivelPredominante, cursos, estudiantes, preguntas };
    }, [dashboardData]);

    // ── Filtros del curso activo ──
    const datosCurso = useMemo(() => {
        if (!dashboardData || !cursoActivo) return { estudiantes: [], preguntas: [] };
        return {
            estudiantes: dashboardData.estudiantes.filter(r => r._curso === cursoActivo),
            preguntas: dashboardData.preguntas.filter(r => r._curso === cursoActivo),
        };
    }, [dashboardData, cursoActivo]);

    const handleCursoClick = (c) => {
        setCursoActivo(c);
        setTab("curso");
    };

    // ── Dimensiones ordenadas por nombre conocido ──
    const sortedDimKeys = useMemo(() => {
        const priority = ["indicador", "año", "asignatura", "ensayo", "mes", "prueba"];
        return Object.keys(indicatorDims).sort((a, b) => {
            const nameA = (indicatorDims[a]?.name || "").toLowerCase();
            const nameB = (indicatorDims[b]?.name || "").toLowerCase();
            const idxA = priority.findIndex(p => nameA.includes(p));
            const idxB = priority.findIndex(p => nameB.includes(p));
            if (idxA !== -1 && idxB !== -1) return idxA - idxB;
            if (idxA !== -1) return -1;
            if (idxB !== -1) return 1;
            return nameA.localeCompare(nameB);
        });
    }, [indicatorDims]);

    // ── Tabs ──
    const tabStyle = (active) =>
        `px-5 py-2.5 rounded-t-xl font-bold text-sm border-b-2 transition-all cursor-pointer ${active
            ? 'text-indigo-600 border-indigo-600 bg-white dark:bg-slate-900 dark:text-indigo-400 dark:border-indigo-400'
            : 'text-slate-400 border-transparent hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300'
        }`;

    // ══════════════════════════════════════════════════════════════════════════
    // ██  RENDER
    // ══════════════════════════════════════════════════════════════════════════

    return (
        <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
            {/* ── Header ── */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div className="space-y-1">
                    <h1 className="text-4xl font-black text-slate-800 dark:text-white tracking-tight flex items-center gap-3">
                        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-100 dark:shadow-indigo-900/20">
                            <ChartColumn size={22} />
                        </div>
                        Resultados
                    </h1>
                    <p className="text-slate-400 dark:text-slate-500 text-sm font-medium">
                        Visualiza el dashboard de resultados por indicador.
                    </p>
                </div>
                <button onClick={fetchInitialData} className="p-3 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-slate-800 rounded-xl transition-all">
                    <RefreshCcw size={20} className={loading ? "animate-spin" : ""} />
                </button>
            </div>

            {/* ── Panel de selectores ── */}
            <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-6">
                <div className="flex flex-wrap items-end gap-4">
                    {/* Selector de indicador */}
                    <div className="flex-1 min-w-50">
                        <label className="block text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2">Indicador</label>
                        <select
                            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                            value={selectedIndicator}
                            onChange={(e) => setSelectedIndicator(e.target.value)}
                            disabled={loading}
                        >
                            <option value="">Seleccionar indicador...</option>
                            {indicators.map(ind => (
                                <option key={ind.id_indicator} value={ind.id_indicator}>{ind.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Selectores de dimensiones dinámicas */}
                    {sortedDimKeys.map(dimId => {
                        const dim = indicatorDims[dimId];
                        if (!dim || !dim.values || dim.values.length === 0) return null;
                        // Excluir dimensiones que son datos internos o a nivel de detalle (curso, pregunta, rut)
                        const nameLower = dim.name.toLowerCase();
                        const excluded = ["nombre", "estudiante", "habilidad", "curso", "pregunta", "rut"];
                        if (excluded.some(ex => nameLower.includes(ex))) return null;

                        return (
                            <div key={dimId} className="flex-1 min-w-40">
                                <label className="block text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2">{dim.name}</label>
                                <select
                                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                                    value={selectedFilters[dimId] || ""}
                                    onChange={(e) => {
                                        const val = e.target.value;
                                        setSelectedFilters(prev => {
                                            const next = { ...prev };
                                            if (val) next[dimId] = val;
                                            else delete next[dimId];
                                            return next;
                                        });
                                    }}
                                >
                                    <option value="">Todos</option>
                                    {dim.values.map(v => (
                                        <option key={v} value={v}>{v}</option>
                                    ))}
                                </select>
                            </div>
                        );
                    })}

                    {/* Botón generar */}
                    <div>
                        <button
                            onClick={handleGenerateDashboard}
                            disabled={!selectedIndicator || loadingDashboard}
                            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white px-6 py-2.5 rounded-2xl font-bold text-sm shadow-xl shadow-indigo-100 dark:shadow-indigo-900/20 transition-all active:scale-95 disabled:cursor-not-allowed"
                        >
                            {loadingDashboard ? (
                                <RefreshCcw size={16} className="animate-spin" />
                            ) : (
                                <Play size={16} strokeWidth={3} />
                            )}
                            Generar Dashboard
                        </button>
                    </div>
                </div>
            </div>

            {/* ── Dashboard ── */}
            {dashboardData && dashboardComputed && (
                <>
                    {/* KPIs */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <KPICard label="Total alumnos" value={dashboardComputed.totalAlumnos} sub="en los cursos evaluados" icon={Users} color="indigo" />
                        <KPICard label="Logro promedio" value={dashboardComputed.logroPromedio ? pct(dashboardComputed.logroPromedio) : "—"} sub="rendimiento general" icon={Target} color="emerald" />
                        <KPICard label="SIMCE promedio" value={dashboardComputed.simcePromedio ? Math.round(dashboardComputed.simcePromedio) : "—"} sub="puntaje estimado" icon={BarChart3} color="rose" />
                        <KPICard label="Nivel predominante" value={dashboardComputed.nivelPredominante} sub="más frecuente" icon={Award} color="amber" />
                    </div>

                    {/* Tabs */}
                    <div>
                        <div className="flex gap-1 border-b border-slate-200 dark:border-slate-800">
                            <button className={tabStyle(tab === "general")} onClick={() => setTab("general")}>Vista General</button>
                            <button className={tabStyle(tab === "curso")} onClick={() => setTab("curso")} disabled={!cursoActivo}>
                                {cursoActivo ? `Detalle Curso ${cursoActivo}` : "Detalle Curso"}
                            </button>
                        </div>

                        <div className="bg-white dark:bg-slate-900 rounded-b-3xl rounded-tr-3xl border border-t-0 border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                            {/* TAB: GENERAL */}
                            {tab === "general" && (
                                <div className="space-y-8">
                                    {dashboardComputed.cursos.length > 0 && (
                                        <p className="text-slate-400 text-sm">
                                            Haz click en una barra para ver el detalle del curso.
                                        </p>
                                    )}

                                    {/* Gráficos principales */}
                                    {dashboardComputed.cursos.length > 0 && (
                                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                            <div>
                                                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Logro Promedio por Curso</h3>
                                                <GraficoLogroPorCurso
                                                    data={dashboardComputed.estudiantes}
                                                    cursos={dashboardComputed.cursos}
                                                    onCursoClick={handleCursoClick}
                                                    cursoActivo={cursoActivo}
                                                />
                                            </div>
                                            <div>
                                                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Alumnos por Nivel de Logro</h3>
                                                <GraficoNivelesPorCurso data={dashboardComputed.estudiantes} cursos={dashboardComputed.cursos} />
                                            </div>
                                        </div>
                                    )}

                                    {/* Distribución de niveles (pie) */}
                                    {dashboardComputed.estudiantes.some(e => e._logro) && (
                                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                            <div>
                                                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Distribución de Niveles de Logro</h3>
                                                <GraficoDistribucionNiveles data={dashboardComputed.estudiantes} />
                                            </div>
                                        </div>
                                    )}

                                    {/* Tabla resumen */}
                                    {dashboardComputed.cursos.length > 0 && (
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Resumen por Curso</h3>
                                            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
                                                <TablaResumenCursos
                                                    data={dashboardComputed.estudiantes}
                                                    cursos={dashboardComputed.cursos}
                                                    onCursoClick={handleCursoClick}
                                                    cursoActivo={cursoActivo}
                                                />
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* TAB: DETALLE CURSO */}
                            {tab === "curso" && cursoActivo && (
                                <div className="space-y-8">
                                    {/* Selector de curso */}
                                    <div className="flex gap-2 flex-wrap">
                                        {dashboardComputed.cursos.map((c, i) => (
                                            <button key={c} onClick={() => setCursoActivo(c)}
                                                className={`px-4 py-2 rounded-xl font-bold text-sm transition-all ${cursoActivo === c
                                                    ? 'text-white shadow-lg'
                                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                                                    }`}
                                                style={cursoActivo === c ? { background: CURSO_COLORS[i % CURSO_COLORS.length] } : {}}
                                            >
                                                {c}
                                            </button>
                                        ))}
                                    </div>

                                    {/* Gráficos */}
                                    {datosCurso.preguntas.length > 0 && (
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Logro por Habilidad</h3>
                                            <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm">
                                                <GraficoHabilidades data={datosCurso.preguntas} />
                                            </div>
                                        </div>
                                    )}

                                    {/* Tabla alumnos */}
                                    {datosCurso.estudiantes.length > 0 && (
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Logro por Estudiante</h3>
                                            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
                                                <TablaAlumnos data={datosCurso.estudiantes} />
                                            </div>
                                        </div>
                                    )}

                                    {/* Tabla preguntas */}
                                    {datosCurso.preguntas.length > 0 && (
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Logro por Pregunta</h3>
                                            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
                                                <TablaPreguntas data={datosCurso.preguntas} />
                                            </div>
                                        </div>
                                    )}

                                    {datosCurso.estudiantes.length === 0 && datosCurso.preguntas.length === 0 && (
                                        <div className="text-center py-16 text-slate-400">
                                            No hay datos para el curso {cursoActivo} con los filtros seleccionados.
                                        </div>
                                    )}
                                </div>
                            )}

                            {tab === "curso" && !cursoActivo && (
                                <div className="text-center py-16 text-slate-400">
                                    Selecciona un curso desde la vista general para ver el detalle.
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}

            {/* Estado vacío */}
            {!dashboardData && !loadingDashboard && (
                <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-16 text-center">
                    <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-2xl flex items-center justify-center mx-auto mb-4">
                        <ChartColumn size={32} className="text-slate-300 dark:text-slate-600" />
                    </div>
                    <h3 className="text-lg font-bold text-slate-600 dark:text-slate-300 mb-2">Selecciona un indicador</h3>
                    <p className="text-slate-400 text-sm max-w-md mx-auto">
                        Elige un indicador y los filtros deseados, luego presiona "Generar Dashboard" para visualizar los resultados.
                    </p>
                </div>
            )}

            {loadingDashboard && (
                <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-16 text-center">
                    <RefreshCcw size={32} className="animate-spin text-indigo-500 mx-auto mb-4" />
                    <p className="text-slate-500 font-semibold">Generando dashboard...</p>
                </div>
            )}
        </div>
    );
}
