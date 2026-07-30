import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { ChartColumn, Download, RefreshCcw } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import { useAuth } from '../context/AuthContext';
import { processDataForDashboard, computeDashboardKPIs } from '../tooling/dataProcessing';
import { DashboardRenderer } from '../tooling/dashboardRenderer';
import GenerateReportModal from '../components/GenerateReportModal';
import ReportSelectorModal from '../components/ReportSelectorModal';
import GenerateReportV2Modal, { brandingGuardadoToOverrides } from '../components/GenerateReportV2Modal';
import GenerateWordReportModal from '../components/GenerateWordReportModal';
import MultiSelectFilters from '../components/MultiSelectFilters';

export default function Results() {
    const { fetchAuth, user } = useAuth();
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
    const [showReportSelector, setShowReportSelector] = useState(false); // selector unificado (Fase 1)
    const [showReportModal, setShowReportModal] = useState(false);
    const [reportV1Context, setReportV1Context] = useState(null); // {tipo, engine} preselección del selector
    const [showReportV2Modal, setShowReportV2Modal] = useState(false);
    const [reportV2Context, setReportV2Context] = useState(null); // {tipoV2, indicatorId, filtros}
    const [showWordModal, setShowWordModal] = useState(false);
    const [wordContext, setWordContext] = useState(null); // {indicatorId, filtros}

    const debounceTimer = useRef(null);
    const currentIndicatorRef = useRef(null); // evita race conditions
    const indicatorsRef = useRef([]); // ref para acceder a indicators sin crear dependencias reactivas
    // Evita el doble-fetch al cambiar de indicador: loadIndicatorDims ya
    // cargó la data sin filtros, y luego reseteamos selectedFilters a {} —
    // ese reset NO debe disparar otra llamada idéntica vía useEffect[selectedFilters].
    const skipNextFilterFetch = useRef(false);

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
                skipNextFilterFetch.current = true;
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

        // Si el reset de filtros vino de cambiar de indicador, loadIndicatorDims
        // ya cargó la data sin filtros — no relanzar la misma request.
        if (skipNextFilterFetch.current) {
            skipNextFilterFetch.current = false;
            return;
        }

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

    // ── Despacho del selector unificado de informes (Fase 1) ──
    // Mapea filtros UI {dimId: [vals]} → {nombre_humano: val|[vals]} (contrato v2/Word)
    const mapFiltersToNames = useCallback(() => {
        const params = {};
        Object.entries(selectedFilters || {}).forEach(([dimId, vals]) => {
            const dimName = indicatorDims[dimId]?.name;
            const arr = Array.isArray(vals) ? vals : (vals ? [vals] : []);
            if (!dimName || arr.length === 0) return;
            params[dimName] = arr.length === 1 ? arr[0] : arr;
        });
        return params;
    }, [selectedFilters, indicatorDims]);

    // Referencia estable para prefillear el panel del informe personalizado
    // (el selector la usa como `initialFilters`; si cambiara en cada render
    // dispararía re-seteos innecesarios dentro del modal).
    const filtrosPorNombre = useMemo(() => mapFiltersToNames(), [mapFiltersToNames]);

    // Descarga un Response como archivo, respetando Content-Disposition.
    const descargarRespuesta = async (resp, fallbackName) => {
        const blob = await resp.blob();
        const disposition = resp.headers.get('Content-Disposition') || '';
        const match = disposition.match(/filename="?([^";]+)"?/);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = match ? match[1] : fallbackName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    };

    // Nombre de archivo por defecto según el tipo de período solicitado.
    const NOMBRE_POR_PERIODO = {
        ultima_prueba: 'informe_ultima_prueba.pdf',
        semestral: 'informe_semestral.pdf',
        anual: 'informe_anual.pdf',
        personalizado: 'informe_personalizado.pdf',
    };

    // Descarga directa (modo 'quick') sin pasar por el modal de la opción:
    // usa la configuración guardada (branding del último uso o defaults).
    // `periodo` (opcional) proviene de las cards de "Informes del período":
    // cuando viaja en el body, el backend resuelve el layout por sí solo.
    const descargaRapida = async (op, periodo = null) => {
        const tid = toast.loading('Generando informe…');
        try {
            let resp;
            let fallbackName = 'informe.pdf';
            if (op.motor === 'v2') {
                // Branding: último usado para este tipo (mismo storage que el modal v2)
                let overrides;
                try {
                    const saved = JSON.parse(localStorage.getItem(`report_v2_branding_${op.tipo_v2}`) || 'null');
                    overrides = brandingGuardadoToOverrides(saved, user?.org_name);
                } catch { /* sin branding guardado: usa defaults del esquema */ }
                resp = await fetchAuth(`${API_BASE_URL}/reports/${op.tipo_v2}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        indicator_id: parseInt(selectedIndicator, 10),
                        filtros: mapFiltersToNames(),
                        ...(overrides ? { overrides } : {}),
                    }),
                });
                fallbackName = `informe_${op.tipo_v2}.pdf`;
            } else if (periodo) {
                // Informes del período — motor único (weasyprint). `tipo` va como
                // placeholder por retrocompatibilidad del contrato: el backend lo
                // ignora cuando `periodo` está presente.
                resp = await fetchAuth(`${API_BASE_URL}/indicators/${selectedIndicator}/export-pdf`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        filters: selectedFilters,
                        tipo: 'evaluacion',
                        engine: 'weasyprint',
                        periodo,
                    }),
                });
                fallbackName = NOMBRE_POR_PERIODO[periodo.tipo] || 'informe.pdf';
            } else if (op.motor === 'custom') {
                // Registry de informes especializados con motor propio.
                const nombreCustom = op.nombre || String(op.id || '').replace(/^custom_/, '');
                resp = await fetchAuth(`${API_BASE_URL}/reports/custom/${nombreCustom}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        indicator_id: parseInt(selectedIndicator, 10),
                        filtros: mapFiltersToNames(),
                    }),
                });
                fallbackName = `informe_${nombreCustom}.${op.formato === 'word' ? 'docx' : 'pdf'}`;
            } else if (op.motor === 'weasyprint' || op.motor === 'pdl_idel') {
                resp = await fetchAuth(`${API_BASE_URL}/indicators/${selectedIndicator}/export-pdf`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        filters: selectedFilters,
                        tipo: op.invocacion?.params?.tipo || 'evaluacion',
                        engine: op.motor === 'pdl_idel' ? 'pdl_idel' : 'weasyprint',
                    }),
                });
                fallbackName = 'informe.pdf';
            } else if (op.motor === 'docxtpl') {
                const nombreInforme = op.id.replace(/^word_/, '');
                resp = await fetchAuth(`${API_BASE_URL}/reports/word/${nombreInforme}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        indicator_id: parseInt(selectedIndicator, 10),
                        filtros: mapFiltersToNames(),
                    }),
                });
                fallbackName = `${nombreInforme}.docx`;
            }
            if (!resp) {
                throw new Error(`Tipo de informe no soportado por esta interfaz (motor: ${op.motor || 'desconocido'})`);
            }
            if (!resp.ok) {
                let detail = 'Error generando el informe';
                try { detail = (await resp.json()).detail || detail; } catch { /* binario o vacío */ }
                throw new Error(detail);
            }
            await descargarRespuesta(resp, fallbackName);
            toast.success('Informe descargado', { id: tid });
        } catch (err) {
            toast.error(err.message || 'No se pudo generar el informe', { id: tid });
        }
    };

    // Valida que los filtros del dashboard acoten UN solo punto temporal.
    // Aplica a los motores que lo declaran (`requiere_filtro_temporal`).
    // Devuelve true si se puede continuar.
    const validarFiltroTemporal = (op) => {
        const temporales = op.requiere_filtro_temporal || [];
        if (temporales.length === 0) return true;
        const params = mapFiltersToNames();
        const tiene = temporales.some(k => k in params);
        const multi = temporales.some(k => Array.isArray(params[k]) && params[k].length > 1);
        if (!tiene) {
            toast.error(`Aplica un filtro de ${temporales.slice(0, 2).join(' o ')} en el dashboard antes de generar este informe (un punto en el tiempo).`);
            return false;
        }
        if (multi) {
            toast.error(`Este informe requiere UN solo punto temporal. Selecciona un único valor en ${temporales.slice(0, 2).join(' o ')}.`);
            return false;
        }
        return true;
    };

    const handleReportOptionSelect = (op, mode = 'custom', extras = {}) => {
        // Período solicitado: viene del selector (cards de período / panel
        // personalizado) o del propio catálogo de la opción.
        const periodo = extras?.periodo || op?.periodo || null;

        // Validación temporal — motores que declaran dimensiones temporales
        if (op.motor === 'v2' || op.motor === 'custom') {
            if (!validarFiltroTemporal(op)) return;
        }

        if (mode === 'quick') {
            setShowReportSelector(false);
            descargaRapida(op, periodo);
            return;
        }

        // Modo 'custom': abrir el modal específico para personalizar
        // Informes del período → modal V1 con el `periodo` ya resuelto.
        if (periodo) {
            setReportV1Context({
                tipo: 'evaluacion',
                engine: 'weasyprint',
                periodo,
                periodoLabel: op.label,
            });
            setShowReportSelector(false);
            setShowReportModal(true);
            return;
        }
        if (op.motor === 'weasyprint' || op.motor === 'pdl_idel') {
            setReportV1Context({
                tipo: op.invocacion?.params?.tipo || 'evaluacion',
                engine: op.motor === 'pdl_idel' ? 'pdl_idel' : 'weasyprint',
            });
            setShowReportSelector(false);
            setShowReportModal(true);
            return;
        }
        if (op.motor === 'v2') {
            setReportV2Context({
                tipoV2: op.tipo_v2,
                indicatorId: parseInt(selectedIndicator, 10),
                filtros: mapFiltersToNames(),
            });
            setShowReportSelector(false);
            setShowReportV2Modal(true);
            return;
        }
        if (op.motor === 'docxtpl') {
            setWordContext({
                indicatorId: parseInt(selectedIndicator, 10),
                filtros: mapFiltersToNames(),
            });
            setShowReportSelector(false);
            setShowWordModal(true);
            return;
        }
        // Motores del registry `custom`: no tienen modal de encabezados propio,
        // así que "personalizar" degrada a descarga directa con los filtros
        // activos del dashboard.
        if (op.motor === 'custom') {
            setShowReportSelector(false);
            descargaRapida(op, null);
        }
    };

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

                    {/* Botón único "Generar informe" — selector unificado (Fase 1).
                        El catálogo de informes disponibles viene de
                        GET /api/indicators/{id}/report-options; el selector
                        despacha al modal específico según la opción elegida. */}
                    {selectedIndicator && (
                        <div className="flex items-end gap-2">
                            <button
                                onClick={() => setShowReportSelector(true)}
                                disabled={loadingDashboard}
                                title="Elegir y generar un informe de este indicador"
                                className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 disabled:cursor-not-allowed shadow-sm transition-all"
                            >
                                <Download size={14} />
                                Generar informe
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

            {/* Selector unificado de tipo de informe (Fase 1) */}
            <ReportSelectorModal
                open={showReportSelector}
                onClose={() => setShowReportSelector(false)}
                indicatorId={selectedIndicator ? parseInt(selectedIndicator, 10) : null}
                onSelect={handleReportOptionSelect}
                initialFilters={filtrosPorNombre}
            />

            {/* Modal de generación de informe PDF */}
            <GenerateReportModal
                open={showReportModal}
                onClose={() => setShowReportModal(false)}
                indicator={currentIndicator}
                indicatorDims={indicatorDims}
                initialFilters={selectedFilters}
                sortedDimKeys={sortedDimKeys}
                onSaved={fetchInitialData}
                initialTipo={reportV1Context?.tipo}
                initialEngine={reportV1Context?.engine}
                initialPeriodo={reportV1Context?.periodo}
                periodoLabel={reportV1Context?.periodoLabel}
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
            {wordContext && (
                <GenerateWordReportModal
                    open={showWordModal}
                    onClose={() => setShowWordModal(false)}
                    indicatorId={wordContext.indicatorId}
                    filtros={wordContext.filtros}
                />
            )}
        </div>
    );
}
