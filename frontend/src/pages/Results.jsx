import { useState, useEffect, useRef, useMemo } from 'react';
import { ChartColumn, RefreshCcw, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import { processDataForDashboard, computeDashboardKPIs } from '../tooling/dataProcessing';
import { DashboardRenderer } from '../tooling/dashboardRenderer';

export default function Results() {
    // ── Estado: datos del backend ──
    const [indicators, setIndicators] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingDashboard, setLoadingDashboard] = useState(false);

    // ── Estado: selectores ──
    const [selectedIndicator, setSelectedIndicator] = useState("");
    const [selectedFilters, setSelectedFilters] = useState({});
    const [indicatorDims, setIndicatorDims] = useState({});
    const [filterDimensionIds, setFilterDimensionIds] = useState([]);

    // ── Estado: dashboard ──
    const [dashboardData, setDashboardData] = useState(null);
    const [indicatorLayout, setIndicatorLayout] = useState(null);
    const [cursoActivo, setCursoActivo] = useState(null);

    const debounceTimer = useRef(null);
    const currentIndicatorRef = useRef(null); // evita race conditions
    const indicatorsRef = useRef([]); // ref para acceder a indicators sin crear dependencias reactivas

    // ── Carga inicial ──
    useEffect(() => {
        fetchInitialData();
    }, []);

    const fetchInitialData = async () => {
        setLoading(true);
        try {
            const indRes = await fetch(`${API_BASE_URL}/indicators`);
            const indData = indRes.ok ? await indRes.json() : [];
            const arr = Array.isArray(indData) ? indData : [];
            setIndicators(arr);
            indicatorsRef.current = arr;
        } catch (err) {
            toast.error("Error al cargar datos iniciales: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    // ── Al seleccionar un indicador, cargar dimensiones y lanzar dashboard ──
    useEffect(() => {
        if (!selectedIndicator) {
            setIndicatorDims({});
            setSelectedFilters({});
            setFilterDimensionIds([]);
            setIndicatorLayout(null);
            setDashboardData(null);
            setCursoActivo(null);
            return;
        }

        const loadIndicatorDims = async () => {
            try {
                // Fetch en paralelo: datos del indicador + indicador fresco (layout actualizado del servidor)
                const [dataRes, indRes] = await Promise.all([
                    fetch(`${API_BASE_URL}/results/indicator/${selectedIndicator}/data`),
                    fetch(`${API_BASE_URL}/indicators`),
                ]);
                if (!dataRes.ok) throw new Error("Error al cargar dimensiones del indicador");
                const result = await dataRes.json();
                setIndicatorDims(result.dimensions || {});
                setFilterDimensionIds(result.filter_dimensions || []);
                setSelectedFilters({});
                setCursoActivo(null);

                // Usar los indicadores frescos del servidor para obtener el layout actualizado
                // SIN llamar a setIndicators (evita re-disparar este useEffect)
                const freshIndicators = indRes.ok ? await indRes.json() : indicatorsRef.current;
                if (Array.isArray(freshIndicators)) indicatorsRef.current = freshIndicators;
                const indObj = (Array.isArray(freshIndicators) ? freshIndicators : indicatorsRef.current)
                    .find(i => String(i.id_indicator) === String(selectedIndicator));
                const layout = indObj?.dashboard_layout;
                // DEBUG — quitar cuando se confirme que el layout llega correcto
                console.log('[Results] dashboard_layout recibido del servidor:', JSON.stringify(layout, null, 2));
                // layout válido = objeto con tabs. {} vacío o null → null
                setIndicatorLayout(layout?.tabs?.length ? layout : null);

                // Procesar datos inmediatamente (sin filtros aún)
                const processed = processDataForDashboard(result);
                setDashboardData(processed);
            } catch (err) {
                toast.error(err.message);
                setIndicatorDims({});
            }
        };

        loadIndicatorDims();
    }, [selectedIndicator]); // ← SIN indicators en dependencias para evitar loop infinito

    // ── Filtros reactivos con debounce (300ms) ──
    useEffect(() => {
        if (!selectedIndicator) return;

        // No relanzar en el primer render cuando selectedFilters está vacío
        // (la carga inicial ya se hizo sin filtros)
        clearTimeout(debounceTimer.current);
        debounceTimer.current = setTimeout(() => {
            fetchDashboard(selectedIndicator, selectedFilters);
        }, 300);

        return () => clearTimeout(debounceTimer.current);
    }, [selectedFilters]);

    const fetchDashboard = async (indicatorId, filters) => {
        if (!indicatorId) return;
        currentIndicatorRef.current = indicatorId;
        setLoadingDashboard(true);

        try {
            const filtersParam = Object.keys(filters).length > 0
                ? `?filters=${encodeURIComponent(JSON.stringify(filters))}`
                : "";
            const res = await fetch(`${API_BASE_URL}/results/indicator/${indicatorId}/data${filtersParam}`);
            if (!res.ok) throw new Error("Error al generar dashboard");

            // Descartar respuesta si el indicador cambió mientras esperábamos
            if (currentIndicatorRef.current !== indicatorId) return;

            const result = await res.json();
            const processed = processDataForDashboard(result);
            setDashboardData(processed);
            setCursoActivo(null);
            if (processed.estudiantes.length === 0 && processed.preguntas.length === 0) {
                toast("No se encontraron datos con los filtros seleccionados", { icon: "ℹ️" });
            }
        } catch (err) {
            if (currentIndicatorRef.current === indicatorId) {
                toast.error(err.message);
            }
        } finally {
            if (currentIndicatorRef.current === indicatorId) {
                setLoadingDashboard(false);
            }
        }
    };

    const handleClearFilters = () => {
        setSelectedFilters({});
    };

    const hasActiveFilters = Object.keys(selectedFilters).length > 0;

    // ── Datos computados del dashboard ──
    const dashboardComputed = useMemo(() => computeDashboardKPIs(dashboardData), [dashboardData]);

    // ── Datos del curso activo ──
    const datosCurso = useMemo(() => {
        if (!dashboardData || !cursoActivo) return { estudiantes: [], preguntas: [] };
        return {
            estudiantes: dashboardData.estudiantes.filter(r => r._curso === cursoActivo),
            preguntas: dashboardData.preguntas.filter(r => r._curso === cursoActivo),
        };
    }, [dashboardData, cursoActivo]);

    // ── Dimensiones de filtro ordenadas por prioridad ──
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

                    {/* Filtros de dimensión */}
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

                    {/* Botón limpiar filtros */}
                    {hasActiveFilters && (
                        <div className="flex items-end">
                            <button
                                onClick={handleClearFilters}
                                className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 transition-all"
                            >
                                <X size={14} />
                                Limpiar filtros
                            </button>
                        </div>
                    )}

                    {/* Spinner de actualización reactiva */}
                    {loadingDashboard && selectedIndicator && (
                        <div className="flex items-end pb-2.5">
                            <RefreshCcw size={16} className="animate-spin text-indigo-400" />
                        </div>
                    )}
                </div>
            </div>

            {/* ── Dashboard ── */}
            {dashboardData && dashboardComputed && (
                <DashboardRenderer
                    layout={indicatorLayout}
                    computed={dashboardComputed}
                    datosCurso={datosCurso}
                    cursoActivo={cursoActivo}
                    setCursoActivo={setCursoActivo}
                />
            )}

            {/* Estado vacío — no se ha seleccionado indicador */}
            {!selectedIndicator && !loading && (
                <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-16 text-center">
                    <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-2xl flex items-center justify-center mx-auto mb-4">
                        <ChartColumn size={32} className="text-slate-300 dark:text-slate-600" />
                    </div>
                    <h3 className="text-lg font-bold text-slate-600 dark:text-slate-300 mb-2">Selecciona un indicador</h3>
                    <p className="text-slate-400 text-sm max-w-md mx-auto">
                        Elige un indicador para visualizar su dashboard. Los filtros se actualizan automáticamente.
                    </p>
                </div>
            )}

            {/* Cargando dashboard por primera vez */}
            {loadingDashboard && !dashboardData && (
                <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-16 text-center">
                    <RefreshCcw size={32} className="animate-spin text-indigo-500 mx-auto mb-4" />
                    <p className="text-slate-500 font-semibold">Cargando dashboard...</p>
                </div>
            )}
        </div>
    );
}
