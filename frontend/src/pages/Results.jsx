import React, { useState, useEffect, useMemo } from 'react';
import {
    ChartColumn, RefreshCcw, Play, Users, Target, Award, BarChart3
} from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import { processDataForDashboard, computeDashboardKPIs } from '../tooling/dataProcessing';
import {
    pct, CURSO_COLORS,
    KPICard, MetricToggle,
    GraficoLogroPorCurso, GraficoBoxplotPorCurso,
    GraficoNivelesPorCurso, GraficoHabilidades,
    GraficoDistribucionNiveles,
    TablaAlumnos, TablaPreguntas, TablaResumenCursos,
} from '../tooling/charts';

export default function Results() {
    // ── Estado: datos del backend ──
    const [indicators, setIndicators] = useState([]);
    const [dimensions, setDimensions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingDashboard, setLoadingDashboard] = useState(false);

    // ── Estado: selectores ──
    const [selectedIndicator, setSelectedIndicator] = useState("");
    const [selectedFilters, setSelectedFilters] = useState({});
    const [indicatorDims, setIndicatorDims] = useState({});
    const [indicatorMetrics, setIndicatorMetrics] = useState([]);
    const [filterDimensionIds, setFilterDimensionIds] = useState([]);

    // ── Estado: dashboard ──
    const [dashboardData, setDashboardData] = useState(null);
    const [tab, setTab] = useState("general");
    const [cursoActivo, setCursoActivo] = useState(null);
    const [metricLogro, setMetricLogro] = useState("logro");   // "logro" = logro_1, "simce" = logro_2
    const [metricBoxplot, setMetricBoxplot] = useState("logro");

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
            setFilterDimensionIds([]);
            return;
        }
        const loadIndicatorDims = async () => {
            try {
                const res = await fetch(`${API_BASE_URL}/results/indicator/${selectedIndicator}/data`);
                if (!res.ok) throw new Error("Error al cargar dimensiones del indicador");
                const result = await res.json();
                setIndicatorDims(result.dimensions || {});
                setIndicatorMetrics(result.metrics || []);
                setFilterDimensionIds(result.filter_dimensions || []);
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

    // ── Datos computados del dashboard ──
    const dashboardComputed = useMemo(() => computeDashboardKPIs(dashboardData), [dashboardData]);

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

    // ── Dimensiones de filtro (solo las configuradas en el indicador) ──
    const sortedDimKeys = useMemo(() => {
        if (!filterDimensionIds || filterDimensionIds.length === 0) return [];
        const priority = ["indicador", "año", "asignatura", "ensayo", "mes", "prueba"];
        return filterDimensionIds
            .map(id => String(id))
            .filter(k => indicatorDims[k])
            .sort((a, b) => {
                const nameA = (indicatorDims[a]?.name || "").toLowerCase();
                const nameB = (indicatorDims[b]?.name || "").toLowerCase();
                const idxA = priority.findIndex(p => nameA.includes(p));
                const idxB = priority.findIndex(p => nameB.includes(p));
                if (idxA !== -1 && idxB !== -1) return idxA - idxB;
                if (idxA !== -1) return -1;
                if (idxB !== -1) return 1;
                return nameA.localeCompare(nameB);
            });
    }, [indicatorDims, filterDimensionIds]);

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

                    {sortedDimKeys.map(dimId => {
                        const dim = indicatorDims[dimId];
                        if (!dim || !dim.values || dim.values.length === 0) return null;
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
                    {/* Tabs */}
                    <div>
                        <div className="flex gap-1 border-b border-slate-200 dark:border-slate-800">
                            <button className={tabStyle(tab === "general")} onClick={() => setTab("general")}>Vista General</button>
                            <button className={tabStyle(tab === "curso")} onClick={() => setTab("curso")}>
                                {cursoActivo ? `Detalle Curso ${cursoActivo}` : "Detalle Curso"}
                            </button>
                        </div>

                        <div className="bg-white dark:bg-slate-900 rounded-b-3xl rounded-tr-3xl border border-t-0 border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                            {/* TAB: GENERAL */}
                            {tab === "general" && (
                                <div className="space-y-8">
                                    {/* KPIs */}
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                        <KPICard label="Total alumnos" value={dashboardComputed.totalAlumnos} sub="en los cursos evaluados" icon={Users} color="indigo" />
                                        {dashboardComputed.activeRoles?.logro_1 && (
                                            <KPICard label={dashboardComputed.roleLabels?.logro_1 || "Logro promedio"} value={dashboardComputed.logroPromedio ? pct(dashboardComputed.logroPromedio) : "—"} sub="rendimiento general" icon={Target} color="emerald" />
                                        )}
                                        {dashboardComputed.activeRoles?.logro_2 && (
                                            <KPICard label={dashboardComputed.roleLabels?.logro_2 || "Puntaje promedio"} value={dashboardComputed.simcePromedio ? Math.round(dashboardComputed.simcePromedio) : "—"} sub="puntaje estimado" icon={BarChart3} color="rose" />
                                        )}
                                        {dashboardComputed.activeRoles?.nivel_de_logro && (
                                            <KPICard label={dashboardComputed.roleLabels?.nivel_de_logro || "Nivel predominante"} value={dashboardComputed.nivelPredominante} sub="más frecuente" icon={Award} color="amber" />
                                        )}
                                    </div>

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
                                                    roleLabels={dashboardComputed.roleLabels}
                                                    activeRoles={dashboardComputed.activeRoles}
                                                    achievement_levels={dashboardComputed.achievement_levels}
                                                />
                                            </div>
                                        </div>
                                    )}

                                    {/* Gráficos en grid 2x2 */}
                                    {dashboardComputed.cursos.length > 0 && (
                                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                            {/* Logro Promedio por Curso — requiere logro_1 o logro_2 */}
                                            {(dashboardComputed.activeRoles?.logro_1 || dashboardComputed.activeRoles?.logro_2) && (
                                                <div>
                                                    <div className="flex items-center justify-between mb-4">
                                                        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">Logro Promedio por Curso</h3>
                                                        {dashboardComputed.activeRoles?.logro_1 && dashboardComputed.activeRoles?.logro_2 && (
                                                            <MetricToggle value={metricLogro} onChange={setMetricLogro} roleLabels={dashboardComputed.roleLabels} />
                                                        )}
                                                    </div>
                                                    <GraficoLogroPorCurso
                                                        data={dashboardComputed.estudiantes}
                                                        cursos={dashboardComputed.cursos}
                                                        metric={dashboardComputed.activeRoles?.logro_1 && dashboardComputed.activeRoles?.logro_2 ? metricLogro : (dashboardComputed.activeRoles?.logro_1 ? "logro" : "simce")}
                                                        roleLabels={dashboardComputed.roleLabels}
                                                    />
                                                </div>
                                            )}

                                            {/* Boxplot — requiere logro_1 o logro_2 */}
                                            {(dashboardComputed.activeRoles?.logro_1 || dashboardComputed.activeRoles?.logro_2) && (
                                                <div>
                                                    <div className="flex items-center justify-between mb-4">
                                                        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">Distribución por Curso</h3>
                                                        {dashboardComputed.activeRoles?.logro_1 && dashboardComputed.activeRoles?.logro_2 && (
                                                            <MetricToggle value={metricBoxplot} onChange={setMetricBoxplot} roleLabels={dashboardComputed.roleLabels} />
                                                        )}
                                                    </div>
                                                    <GraficoBoxplotPorCurso
                                                        data={dashboardComputed.estudiantes}
                                                        cursos={dashboardComputed.cursos}
                                                        metric={dashboardComputed.activeRoles?.logro_1 && dashboardComputed.activeRoles?.logro_2 ? metricBoxplot : (dashboardComputed.activeRoles?.logro_1 ? "logro" : "simce")}
                                                        roleLabels={dashboardComputed.roleLabels}
                                                    />
                                                </div>
                                            )}

                                            {/* Distribución de Niveles — requiere nivel_de_logro */}
                                            {dashboardComputed.activeRoles?.nivel_de_logro && dashboardComputed.estudiantes.some(e => e._logro) && (
                                                <div>
                                                    <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Distribución de Niveles de Logro</h3>
                                                    <GraficoDistribucionNiveles 
                                                        data={dashboardComputed.estudiantes} 
                                                        achievement_levels={dashboardComputed.achievement_levels} 
                                                    />
                                                </div>
                                            )}

                                            {/* Alumnos por Nivel — requiere nivel_de_logro */}
                                            {dashboardComputed.activeRoles?.nivel_de_logro && (
                                                <div>
                                                    <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Alumnos por Nivel de Logro</h3>
                                                    <GraficoNivelesPorCurso
                                                        data={dashboardComputed.estudiantes}
                                                        cursos={dashboardComputed.cursos}
                                                        achievement_levels={dashboardComputed.achievement_levels}
                                                    />
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* TAB: DETALLE CURSO */}
                            {tab === "curso" && cursoActivo && (
                                <div className="space-y-8">
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

                                    {dashboardComputed.activeRoles?.habilidad && datosCurso.preguntas.length > 0 && (
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Logro por Habilidad</h3>
                                            <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm">
                                                <GraficoHabilidades data={datosCurso.preguntas} roleLabels={dashboardComputed.roleLabels} />
                                            </div>
                                        </div>
                                    )}

                                    {datosCurso.estudiantes.length > 0 && (
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Logro por Estudiante</h3>
                                            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
                                                <TablaAlumnos data={datosCurso.estudiantes} roleLabels={dashboardComputed.roleLabels} activeRoles={dashboardComputed.activeRoles} />
                                            </div>
                                        </div>
                                    )}

                                    {datosCurso.preguntas.length > 0 && (
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Logro por Pregunta</h3>
                                            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
                                                <TablaPreguntas data={datosCurso.preguntas} roleLabels={dashboardComputed.roleLabels} />
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
                                    Selecciona un curso desde la tabla de resumen para ver el detalle.
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
