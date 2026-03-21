import { useState, useEffect } from 'react';
import { ChartColumn, RefreshCcw, Play } from 'lucide-react';
import toast from 'react-hot-toast';
import Plot from 'react-plotly.js';
import { API_BASE_URL } from '../constants';

const KPI_COLORS = {
    indigo: 'bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 border-indigo-100 dark:border-indigo-900',
    emerald: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border-emerald-100 dark:border-emerald-900',
    rose: 'bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 border-rose-100 dark:border-rose-900',
    amber: 'bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 border-amber-100 dark:border-amber-900',
};

export default function Results() {
    const [indicators, setIndicators] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingDashboard, setLoadingDashboard] = useState(false);
    const [selectedIndicator, setSelectedIndicator] = useState('');
    const [selectedFilters, setSelectedFilters] = useState({});
    const [filterDefs, setFilterDefs] = useState([]);
    const [dashboard, setDashboard] = useState(null);

    // ── Carga inicial ──
    useEffect(() => { fetchIndicators(); }, []);

    const fetchIndicators = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE_URL}/resultspy/indicators`);
            const data = res.ok ? await res.json() : [];
            setIndicators(Array.isArray(data) ? data : []);
        } catch (err) {
            toast.error('Error al cargar indicadores: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    // ── Al seleccionar indicador, cargar filtros ──
    useEffect(() => {
        if (!selectedIndicator) {
            setFilterDefs([]);
            setSelectedFilters({});
            setDashboard(null);
            return;
        }
        const load = async () => {
            try {
                const res = await fetch(`${API_BASE_URL}/resultspy/indicator/${selectedIndicator}/filters`);
                const data = res.ok ? await res.json() : { filters: [] };
                setFilterDefs(data.filters || []);
                setSelectedFilters({});
                setDashboard(null);
            } catch (err) {
                toast.error(err.message);
            }
        };
        load();
    }, [selectedIndicator]);

    // ── Generar dashboard ──
    const handleGenerate = async () => {
        if (!selectedIndicator) return toast.error('Selecciona un indicador');
        setLoadingDashboard(true);
        setDashboard(null);
        try {
            const filtersParam = Object.keys(selectedFilters).length > 0
                ? `?filters=${encodeURIComponent(JSON.stringify(selectedFilters))}`
                : '';
            const res = await fetch(`${API_BASE_URL}/resultspy/indicator/${selectedIndicator}/dashboard${filtersParam}`);
            if (!res.ok) throw new Error('Error al generar dashboard');
            const data = await res.json();
            setDashboard(data);
            if (!data.charts?.length && !data.kpis?.length) {
                toast('No se encontraron datos con los filtros seleccionados', { icon: 'ℹ️' });
            }
        } catch (err) {
            toast.error(err.message);
        } finally {
            setLoadingDashboard(false);
        }
    };

    // ── Parsear plotly_json para <Plot> ──
    const parsePlotly = (jsonStr) => {
        try {
            const parsed = JSON.parse(jsonStr);
            return { data: parsed.data || [], layout: parsed.layout || {} };
        } catch {
            return null;
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div className="space-y-1">
                    <h1 className="text-4xl font-black text-slate-800 dark:text-white tracking-tight flex items-center gap-3">
                        <div className="w-10 h-10 bg-violet-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-violet-100 dark:shadow-violet-900/20">
                            <ChartColumn size={22} />
                        </div>
                        Resultados
                    </h1>
                    <p className="text-slate-400 dark:text-slate-500 text-sm font-medium">
                        Dashboards de indicadores. Los gráficos son interactivos.
                    </p>
                </div>
                <button onClick={fetchIndicators} className="p-3 text-slate-400 hover:text-violet-600 hover:bg-violet-50 dark:hover:bg-slate-800 rounded-xl transition-all">
                    <RefreshCcw size={20} className={loading ? 'animate-spin' : ''} />
                </button>
            </div>

            {/* Panel de selectores */}
            <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-6">
                <div className="flex flex-wrap items-end gap-4">
                    <div className="flex-1 min-w-50">
                        <label className="block text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2">Indicador</label>
                        <select
                            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
                            value={selectedIndicator}
                            onChange={e => setSelectedIndicator(e.target.value)}
                            disabled={loading}
                        >
                            <option value="">Seleccionar indicador...</option>
                            {indicators.map(ind => (
                                <option key={ind.id_indicator} value={ind.id_indicator}>{ind.name}</option>
                            ))}
                        </select>
                    </div>

                    {filterDefs.map(dim => (
                        <div key={dim.id} className="flex-1 min-w-40">
                            <label className="block text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2">{dim.name}</label>
                            <select
                                className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
                                value={selectedFilters[dim.id] || ''}
                                onChange={e => {
                                    const val = e.target.value;
                                    setSelectedFilters(prev => {
                                        const next = { ...prev };
                                        if (val) next[dim.id] = val;
                                        else delete next[dim.id];
                                        return next;
                                    });
                                }}
                            >
                                <option value="">Todos</option>
                                {dim.values.map(v => <option key={v} value={v}>{v}</option>)}
                            </select>
                        </div>
                    ))}

                    <div>
                        <button
                            onClick={handleGenerate}
                            disabled={!selectedIndicator || loadingDashboard}
                            className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white px-6 py-2.5 rounded-2xl font-bold text-sm shadow-xl shadow-violet-100 dark:shadow-violet-900/20 transition-all active:scale-95 disabled:cursor-not-allowed"
                        >
                            {loadingDashboard
                                ? <RefreshCcw size={16} className="animate-spin" />
                                : <Play size={16} strokeWidth={3} />
                            }
                            Generar Dashboard
                        </button>
                    </div>
                </div>
            </div>

            {/* Dashboard */}
            {dashboard && (
                <div className="space-y-6">
                    {/* KPIs */}
                    {dashboard.kpis?.length > 0 && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {dashboard.kpis.map((kpi, i) => (
                                <div key={i} className={`rounded-2xl border p-5 ${KPI_COLORS[kpi.color] || KPI_COLORS.indigo}`}>
                                    <p className="text-[11px] font-bold uppercase tracking-widest opacity-60 mb-1">{kpi.label}</p>
                                    <p className="text-2xl font-black">{kpi.value}</p>
                                    <p className="text-xs opacity-50 mt-1">{kpi.sub}</p>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Charts grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {dashboard.charts?.map((chart, i) => {
                            // Tabla
                            if (chart.table_data) {
                                const cols = chart.table_data.length > 0 ? Object.keys(chart.table_data[0]) : [];
                                return (
                                    <div key={chart.id || i} className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-6">
                                        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">{chart.title}</h3>
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-sm">
                                                <thead>
                                                    <tr className="border-b border-slate-200 dark:border-slate-700">
                                                        {cols.map(c => (
                                                            <th key={c} className="text-left py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-400">{c}</th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {chart.table_data.map((row, ri) => (
                                                        <tr key={ri} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                                            {cols.map(c => (
                                                                <td key={c} className="py-2 px-3 text-slate-600 dark:text-slate-300 font-medium">{row[c]}</td>
                                                            ))}
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                );
                            }

                            // Plotly chart
                            const plotData = chart.plotly_json ? parsePlotly(chart.plotly_json) : null;
                            if (!plotData) return null;

                            const isWide = ['niveles_por_curso_y_mes', 'tabla_resumen', 'tendencia_temporal'].includes(chart.id);

                            return (
                                <div key={chart.id || i} className={`${isWide ? 'lg:col-span-2' : ''} bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-6`}>
                                    <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">{chart.title}</h3>
                                    <Plot
                                        data={plotData.data}
                                        layout={{
                                            ...plotData.layout,
                                            dragmode: false,
                                            autosize: true,
                                            paper_bgcolor: 'transparent',
                                            plot_bgcolor: 'transparent',
                                            font: { family: 'Inter, system-ui, sans-serif', color: '#64748b' },
                                        }}
                                        config={{
                                            responsive: true,
                                            displayModeBar: false,
                                            staticPlot: false,
                                            scrollZoom: false,
                                        }}
                                        useResizeHandler
                                        style={{ width: '100%', height: plotData.layout?.height || 320 }}
                                    />
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Empty state */}
            {!dashboard && !loadingDashboard && (
                <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-16 text-center">
                    <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-2xl flex items-center justify-center mx-auto mb-4">
                        <ChartColumn size={32} className="text-slate-300 dark:text-slate-600" />
                    </div>
                    <h3 className="text-lg font-bold text-slate-600 dark:text-slate-300 mb-2">Selecciona un indicador</h3>
                    <p className="text-slate-400 text-sm max-w-md mx-auto">
                        Elige un indicador y presiona "Generar Dashboard".
                    </p>
                </div>
            )}

            {loadingDashboard && (
                <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-16 text-center">
                    <RefreshCcw size={32} className="animate-spin text-violet-500 mx-auto mb-4" />
                    <p className="text-slate-500 font-semibold">Generando dashboard con Plotly...</p>
                </div>
            )}
        </div>
    );
}
