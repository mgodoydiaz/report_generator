import { useState, useEffect, useRef, useMemo } from 'react';
import { ChartColumn, Download, RefreshCcw } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import { useAuth } from '../context/AuthContext';
import { processDataForDashboard, computeDashboardKPIs } from '../tooling/dataProcessing';
import { DashboardRenderer } from '../tooling/dashboardRenderer';
import GenerateReportModal from '../components/GenerateReportModal';
import GenerateReportV2Modal from '../components/GenerateReportV2Modal';
import MultiSelectFilters from '../components/MultiSelectFilters';

export default function Results() {
    const { fetchAuth } = useAuth();
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
    const [indicatorDerivedCols, setIndicatorDerivedCols] = useState([]);
    const [cursoActivo, setCursoActivo] = useState(null);
    const [subpruebaActiva, setSubpruebaActiva] = useState(null);

    // ── Estado: modal de generación de PDF ──
    const [showReportModal, setShowReportModal] = useState(false);
    const [showReportV2Modal, setShowReportV2Modal] = useState(false);
    const [reportV2Context, setReportV2Context] = useState(null); // {tipoV2, indicatorId, filtros}

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
            const indRes = await fetchAuth(`${API_BASE_URL}/indicators`);
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
            setIndicatorDerivedCols([]);
            setDashboardData(null);
            setCursoActivo(null);
            setSubpruebaActiva(null);
            return;
        }

        const loadIndicatorDims = async () => {
            try {
                // Fetch en paralelo: datos del indicador + indicador fresco (layout actualizado del servidor)
                const [dataRes, indRes] = await Promise.all([
                    fetchAuth(`${API_BASE_URL}/results/indicator/${selectedIndicator}/data`),
                    fetchAuth(`${API_BASE_URL}/indicators`),
                ]);
                if (!dataRes.ok) throw new Error("Error al cargar dimensiones del indicador");
                const result = await dataRes.json();
                setIndicatorDims(result.dimensions || {});
                setFilterDimensionIds(result.filter_dimensions || []);
                setSelectedFilters({});
                setCursoActivo(null);
                setSubpruebaActiva(null);

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
                setIndicatorDerivedCols(indObj?.derived_columns || []);

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
            const res = await fetchAuth(`${API_BASE_URL}/results/indicator/${indicatorId}/data${filtersParam}`);
            if (!res.ok) throw new Error("Error al generar dashboard");

            // Descartar respuesta si el indicador cambió mientras esperábamos
            if (currentIndicatorRef.current !== indicatorId) return;

            const result = await res.json();
            const processed = processDataForDashboard(result);
            setDashboardData(processed);
            // Refresca dimensiones para soportar cascading filters: el
            // backend devuelve los `values` por dimensión recomputados
            // aplicando los filtros actuales excepto el de la propia
            // dimensión. Esto hace que los dropdowns solo muestren
            // valores consistentes con las selecciones previas.
            if (result.dimensions) setIndicatorDims(result.dimensions);
            setCursoActivo(null);
            setSubpruebaActiva(null);
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

    // ── Helper: filtros normalizados a arrays ──
    // Desde B9 selectedFilters tiene shape {dimId: string[]}. Ese helper
    // permite recibir formato viejo (single string) sin romper.
    const normalizeFilters = (raw) => {
        const out = {};
        Object.entries(raw || {}).forEach(([k, v]) => {
            if (v == null || v === '') return;
            if (Array.isArray(v)) {
                if (v.length) out[k] = v;
            } else {
                out[k] = [String(v)];
            }
        });
        return out;
    };

    const hasActiveFilters = Object.keys(selectedFilters).some((k) => (selectedFilters[k] || []).length > 0);

    // Filtros para configured_table / configured_chart: el endpoint
    // /api/tables/{id}/data y /api/charts/{id}/data esperan dimensiones
    // por NOMBRE (ej "Curso") no por id, y aceptan list-of-values para
    // filtros multi-valor. Se aplica el unwrap a single-value cuando
    // hay un solo elemento para no forzar array innecesariamente.
    const dashboardFilters = useMemo(() => {
        const out = {};
        Object.entries(selectedFilters || {}).forEach(([dimId, vals]) => {
            const dimName = indicatorDims[dimId]?.name;
            if (!dimName) return;
            const arr = Array.isArray(vals) ? vals.filter(v => v != null && v !== '') : [];
            if (!arr.length) return;
            out[dimName] = arr.length === 1 ? arr[0] : arr;
        });
        return out;
    }, [selectedFilters, indicatorDims]);

    // ── Indicador actualmente seleccionado + disponibilidad de informe PDF ──
    const currentIndicator = useMemo(() => {
        if (!selectedIndicator) return null;
        return indicators.find(i => String(i.id_indicator) === String(selectedIndicator)) || null;
    }, [indicators, selectedIndicator]);

    const pdfLayout = currentIndicator?.pdf_layout;
    const pdfEngine = (pdfLayout && typeof pdfLayout === 'object' ? pdfLayout.engine : null) || 'weasyprint';
    const pdfConfigured = !!(
        pdfLayout && typeof pdfLayout === 'object' &&
        // Para WeasyPrint, el layout debe tener sections configuradas.
        // Para otros engines (ej. pdl_idel en Fase B), basta con declarar el engine.
        (pdfEngine !== 'weasyprint' || (Array.isArray(pdfLayout.sections) && pdfLayout.sections.length > 0))
    );

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
            <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-6 space-y-4">
                {/* Selector de indicador */}
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

                    {/* Botón generar informe PDF */}
                    {selectedIndicator && (
                        <div className="flex items-end gap-2">
                            <button
                                onClick={() => setShowReportModal(true)}
                                disabled={!pdfConfigured || loadingDashboard}
                                title={
                                    !pdfConfigured
                                        ? 'Configura el informe PDF en el Editor de Layout → pestaña Informe PDF'
                                        : 'Abrir el modal de generación de informe (motor v1)'
                                }
                                className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 disabled:cursor-not-allowed shadow-sm transition-all"
                            >
                                <Download size={14} />
                                Generar Reporte
                            </button>
                            {/* Botón motor v2 (paridad LaTeX). Detecta tipo por el nombre del indicador.
                                Solo se muestra para indicators DIA / SIMCE — el motor v2 todavía no
                                soporta IDEL/CV/FL. */}
                            {(() => {
                                const ind = indicatorsRef.current.find(i => String(i.id_indicator) === String(selectedIndicator));
                                const nombre = (ind?.name || '').toLowerCase();
                                const tipoV2 = nombre.includes('simce') ? 'simce'
                                    : nombre.includes('dia') ? 'dia'
                                    : null;
                                if (!tipoV2) return null;
                                // Mapear filtros UI (multi-valor) → nombres DB.
                                // Para motor v2: si una dimensión tiene 1 solo valor lo
                                // pasa como string (compatible con el código viejo);
                                // si tiene >1 valor lo pasa como array (backend lo maneja).
                                // Pero para los temporales el motor REQUIERE 1 solo punto.
                                const params = {};
                                Object.entries(selectedFilters || {}).forEach(([dimId, vals]) => {
                                    const dimName = indicatorDims[dimId]?.name;
                                    const arr = Array.isArray(vals) ? vals : (vals ? [vals] : []);
                                    if (!dimName || arr.length === 0) return;
                                    params[dimName] = arr.length === 1 ? arr[0] : arr;
                                });
                                // El motor v2 requiere al menos UN filtro temporal por tipo.
                                const filtrosTemporales = tipoV2 === 'simce'
                                    ? ['Mes', 'N Prueba', 'Numero_Prueba']
                                    : ['Hito', 'Año'];
                                const tieneFiltroTemporal = filtrosTemporales.some(k => k in params);
                                // Si el filtro temporal tiene >1 valor, motor v2 no puede
                                // (sería un comparativo, no soportado todavía).
                                const temporalMulti = filtrosTemporales.some(k => Array.isArray(params[k]) && params[k].length > 1);
                                const disabled = loadingDashboard || !tieneFiltroTemporal || temporalMulti;
                                const titleMsg = temporalMulti
                                    ? `El motor v2 requiere UN solo punto temporal. Selecciona un único valor en ${filtrosTemporales.slice(0, 2).join(' o ')}.`
                                    : !tieneFiltroTemporal
                                        ? `Aplica un filtro de ${filtrosTemporales.slice(0, 2).join(' o ')} antes de generar el informe v2 (un punto en el tiempo)`
                                        : `Generar informe ${tipoV2.toUpperCase()} con motor v2 (paridad LaTeX)`;
                                return (
                                    <button
                                        onClick={() => {
                                            // Abrir modal v2 con contexto actual.
                                            // El modal arma overrides de branding y llama el endpoint.
                                            setReportV2Context({
                                                tipoV2,
                                                indicatorId: parseInt(selectedIndicator, 10),
                                                filtros: params,
                                            });
                                            setShowReportV2Modal(true);
                                        }}
                                        disabled={disabled}
                                        title={titleMsg}
                                        className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold text-indigo-700 bg-white border-2 border-indigo-600 hover:bg-indigo-50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white shadow-sm transition-all"
                                    >
                                        <Download size={14} />
                                        Generar v2 ({tipoV2.toUpperCase()})
                                    </button>
                                );
                            })()}
                        </div>
                    )}

                    {/* Spinner de actualización reactiva */}
                    {loadingDashboard && selectedIndicator && (
                        <div className="flex items-end pb-2.5">
                            <RefreshCcw size={16} className="animate-spin text-indigo-400" />
                        </div>
                    )}
                </div>

                {/* Filtros multi-valor (B9) — toolbar Linear/Notion style */}
                {selectedIndicator && sortedDimKeys.length > 0 && (
                    <div className="border-t border-slate-100 dark:border-slate-800 pt-4">
                        <div className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                            Filtros
                        </div>
                        <MultiSelectFilters
                            dimensions={indicatorDims}
                            sortedDimIds={sortedDimKeys}
                            value={selectedFilters}
                            onChange={setSelectedFilters}
                        />
                    </div>
                )}
            </div>

            {/* ── Dashboard ── */}
            {dashboardData && dashboardComputed && (
                <DashboardRenderer
                    layout={indicatorLayout}
                    computed={dashboardComputed}
                    datosCurso={datosCurso}
                    cursoActivo={cursoActivo}
                    setCursoActivo={setCursoActivo}
                    subpruebaActiva={subpruebaActiva}
                    setSubpruebaActiva={setSubpruebaActiva}
                    derivedColumns={indicatorDerivedCols}
                    dashboardFilters={dashboardFilters}
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

            {/* Modal de generación de informe PDF */}
            <GenerateReportModal
                open={showReportModal}
                onClose={() => setShowReportModal(false)}
                indicator={currentIndicator}
                indicatorDims={indicatorDims}
                initialFilters={selectedFilters}
                sortedDimKeys={sortedDimKeys}
                onSaved={fetchInitialData}
            />
            {reportV2Context && (
                <GenerateReportV2Modal
                    open={showReportV2Modal}
                    onClose={() => setShowReportV2Modal(false)}
                    tipoV2={reportV2Context.tipoV2}
                    indicatorId={reportV2Context.indicatorId}
                    filtros={reportV2Context.filtros}
                />
            )}
        </div>
    );
}
