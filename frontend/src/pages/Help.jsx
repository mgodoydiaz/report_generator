import React, { useState, useEffect, useRef } from 'react';
import { CircleHelp, BarChart3, Table2, Sparkles, ChevronRight, BookOpen } from 'lucide-react';
import {
    GraficoLogroPorCurso,
    GraficoBoxplotPorCurso,
    GraficoNivelesPorCurso,
    GraficoHabilidades,
    GraficoDistribucionNiveles,
    GraficoNivelesPorCursoYMes,
    GraficoPromedioAgrupadoPorDimension,
    GraficoTendenciaTemporal,
    GraficoRadarHabilidades,
    TablaAlumnos,
    TablaPreguntas,
    TablaResumenCursos,
} from '../tooling/charts';
import {
    BarByGroup,
    HorizontalBarByDimension,
    DoubleGroupedBar,
    BoxPlotByGroup,
    PieComposition,
    StackedCountByGroup,
    StackedCountByGroupAndPeriod,
    TrendLine,
    RadarProfile,
    SummaryTable,
    DetailListTable,
    DetailListWithProgress,
} from '../tooling/plotly-charts';

// ── Datos de muestra ──────────────────────────────────────────────────────────

const CURSOS = ['4°A', '4°B', '4°C'];
const NIVELES = ['Insuficiente', 'Elemental', 'Adecuado'];

const ESTUDIANTES = [
    { _nombre: 'Ana García',     _curso: '4°A', _rend: 0.82, _logro: 'Adecuado',     _avance:  0.08, _evaluacion_num: 1 },
    { _nombre: 'Luis Martínez',  _curso: '4°A', _rend: 0.54, _logro: 'Elemental',    _avance:  0.03, _evaluacion_num: 1 },
    { _nombre: 'Sofía Pérez',    _curso: '4°A', _rend: 0.38, _logro: 'Insuficiente', _avance: -0.06, _evaluacion_num: 1 },
    { _nombre: 'Mateo López',    _curso: '4°A', _rend: 0.71, _logro: 'Adecuado',     _avance:  0.12, _evaluacion_num: 1 },
    { _nombre: 'Valentina Ruiz', _curso: '4°B', _rend: 0.90, _logro: 'Adecuado',     _avance:  0.05, _evaluacion_num: 1 },
    { _nombre: 'Tomás Díaz',     _curso: '4°B', _rend: 0.47, _logro: 'Elemental',    _avance: -0.04, _evaluacion_num: 1 },
    { _nombre: 'Camila Torres',  _curso: '4°B', _rend: 0.33, _logro: 'Insuficiente', _avance: -0.11, _evaluacion_num: 1 },
    { _nombre: 'Ignacio Vargas', _curso: '4°B', _rend: 0.61, _logro: 'Elemental',    _avance:  0.09, _evaluacion_num: 1 },
    { _nombre: 'Isidora Rojas',  _curso: '4°C', _rend: 0.75, _logro: 'Adecuado',     _avance:  0.07, _evaluacion_num: 1 },
    { _nombre: 'Emilio Castro',  _curso: '4°C', _rend: 0.42, _logro: 'Elemental',    _avance:  0.00, _evaluacion_num: 1 },
    { _nombre: 'Martina Silva',  _curso: '4°C', _rend: 0.88, _logro: 'Adecuado',     _avance:  0.14, _evaluacion_num: 1 },
    { _nombre: 'Benjamín Mora',  _curso: '4°C', _rend: 0.29, _logro: 'Insuficiente', _avance: -0.08, _evaluacion_num: 1 },
    { _nombre: 'Ana García',     _curso: '4°A', _rend: 0.87, _logro: 'Adecuado',     _avance:  0.05, _evaluacion_num: 2 },
    { _nombre: 'Luis Martínez',  _curso: '4°A', _rend: 0.60, _logro: 'Elemental',    _avance:  0.06, _evaluacion_num: 2 },
    { _nombre: 'Sofía Pérez',    _curso: '4°A', _rend: 0.45, _logro: 'Elemental',    _avance:  0.07, _evaluacion_num: 2 },
    { _nombre: 'Mateo López',    _curso: '4°A', _rend: 0.78, _logro: 'Adecuado',     _avance:  0.07, _evaluacion_num: 2 },
    { _nombre: 'Valentina Ruiz', _curso: '4°B', _rend: 0.92, _logro: 'Adecuado',     _avance:  0.02, _evaluacion_num: 2 },
    { _nombre: 'Tomás Díaz',     _curso: '4°B', _rend: 0.52, _logro: 'Elemental',    _avance:  0.05, _evaluacion_num: 2 },
    { _nombre: 'Camila Torres',  _curso: '4°B', _rend: 0.40, _logro: 'Insuficiente', _avance:  0.07, _evaluacion_num: 2 },
    { _nombre: 'Ignacio Vargas', _curso: '4°B', _rend: 0.68, _logro: 'Adecuado',     _avance:  0.07, _evaluacion_num: 2 },
    { _nombre: 'Isidora Rojas',  _curso: '4°C', _rend: 0.80, _logro: 'Adecuado',     _avance:  0.05, _evaluacion_num: 2 },
    { _nombre: 'Emilio Castro',  _curso: '4°C', _rend: 0.50, _logro: 'Elemental',    _avance:  0.08, _evaluacion_num: 2 },
    { _nombre: 'Martina Silva',  _curso: '4°C', _rend: 0.91, _logro: 'Adecuado',     _avance:  0.03, _evaluacion_num: 2 },
    { _nombre: 'Benjamín Mora',  _curso: '4°C', _rend: 0.35, _logro: 'Insuficiente', _avance:  0.06, _evaluacion_num: 2 },
];

const PREGUNTAS = [
    { _pregunta: 1,  _habilidad: 'Comprensión',   _logro_pregunta: 0.78, _correcta: 'A' },
    { _pregunta: 2,  _habilidad: 'Comprensión',   _logro_pregunta: 0.62, _correcta: 'C' },
    { _pregunta: 3,  _habilidad: 'Comprensión',   _logro_pregunta: 0.50, _correcta: 'B' },
    { _pregunta: 4,  _habilidad: 'Argumentación', _logro_pregunta: 0.45, _correcta: 'D' },
    { _pregunta: 5,  _habilidad: 'Argumentación', _logro_pregunta: 0.33, _correcta: 'A' },
    { _pregunta: 6,  _habilidad: 'Síntesis',       _logro_pregunta: 0.85, _correcta: 'B' },
    { _pregunta: 7,  _habilidad: 'Síntesis',       _logro_pregunta: 0.70, _correcta: 'C' },
    { _pregunta: 8,  _habilidad: 'Evaluación',     _logro_pregunta: 0.55, _correcta: 'A' },
    { _pregunta: 9,  _habilidad: 'Evaluación',     _logro_pregunta: 0.40, _correcta: 'D' },
    { _pregunta: 10, _habilidad: 'Evaluación',     _logro_pregunta: 0.28, _correcta: 'B' },
];

const ROLE_LABELS = { logro_1: 'Rendimiento %', logro_2: 'Puntaje SIMCE' };
const ACTIVE_ROLES_BASIC = { logro_1: true, nivel_de_logro: true };
const FMT_PCT = (v) => v != null ? (v * 100).toFixed(0) + '%' : '—';

// ── Índice de contenidos ───────────────────────────────────────────────────────

const TOC = [
    {
        group: 'Guías de uso',
        color: 'amber',
        icon: BookOpen,
        items: [
            { id: 'guide-pipeline',  label: 'Crear y ejecutar pipeline' },
            { id: 'guide-tables',    label: 'Configurar tablas' },
            { id: 'guide-charts',    label: 'Configurar gráficos' },
            { id: 'guide-functions', label: 'Funciones derivadas' },
        ],
    },
    {
        group: 'Gráficos Plotly',
        color: 'emerald',
        icon: BarChart3,
        items: [
            { id: 'BarByGroup',                   label: 'Barras por Grupo' },
            { id: 'HorizontalBarByDimension',     label: 'Barras Horizontales' },
            { id: 'DoubleGroupedBar',              label: 'Barras Doblemente Agrupadas' },
            { id: 'BoxPlotByGroup',               label: 'Boxplot por Grupo' },
            { id: 'PieComposition',               label: 'Composición (Torta)' },
            { id: 'StackedCountByGroup',          label: 'Conteo Apilado por Grupo' },
            { id: 'StackedCountByGroupAndPeriod', label: 'Conteo Apilado + Período' },
            { id: 'TrendLine',                    label: 'Tendencia Temporal' },
            { id: 'RadarProfile',                 label: 'Perfil Radar' },
        ],
    },
    {
        group: 'Tablas Plotly',
        color: 'indigo',
        icon: Table2,
        items: [
            { id: 'SummaryTable',            label: 'Resumen por Grupo' },
            { id: 'DetailListTable',         label: 'Lista de Items' },
            { id: 'DetailListWithProgress',  label: 'Lista con Progreso' },
        ],
    },
    {
        group: 'Gráficos Legacy',
        color: 'slate',
        icon: BarChart3,
        items: [
            { id: 'GraficoLogroPorCurso',              label: 'Logro por Curso' },
            { id: 'GraficoBoxplotPorCurso',            label: 'Boxplot por Curso' },
            { id: 'GraficoNivelesPorCurso',            label: 'Niveles por Curso' },
            { id: 'GraficoDistribucionNiveles',        label: 'Distribución Niveles' },
            { id: 'GraficoHabilidades',                label: 'Habilidades' },
            { id: 'GraficoNivelesPorCursoYMes',        label: 'Niveles por Curso y Mes' },
            { id: 'GraficoPromedioAgrupadoPorDimension', label: 'Promedio Agrupado' },
            { id: 'GraficoTendenciaTemporal',          label: 'Tendencia Temporal' },
            { id: 'GraficoRadarHabilidades',           label: 'Radar Habilidades' },
        ],
    },
    {
        group: 'Tablas Legacy',
        color: 'slate',
        icon: Table2,
        items: [
            { id: 'TablaResumenCursos', label: 'Resumen Cursos' },
            { id: 'TablaAlumnos',       label: 'Tabla Alumnos' },
            { id: 'TablaPreguntas',     label: 'Tabla Preguntas' },
        ],
    },
];

const COLOR_RING = {
    amber:   'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
    emerald: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300',
    indigo:  'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300',
    slate:   'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400',
};
const COLOR_DOT = {
    amber:   'bg-amber-500',
    emerald: 'bg-emerald-500',
    indigo:  'bg-indigo-500',
    slate:   'bg-slate-400',
};

// ── Pill de parámetro ─────────────────────────────────────────────────────────

function Param({ name, type, required, description }) {
    return (
        <div className="flex items-start gap-2 py-1.5 border-b border-slate-100 dark:border-slate-800 last:border-0">
            <code className={`shrink-0 text-[11px] font-mono px-1.5 py-0.5 rounded-md font-semibold ${
                required
                    ? 'bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
            }`}>{name}</code>
            <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide shrink-0 mt-0.5">{type}</span>
            {description && <span className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight">{description}</span>}
        </div>
    );
}

// ── Tarjeta de guía ───────────────────────────────────────────────────────────

function GuideCard({ id, title, summary, steps = [], note }) {
    return (
        <div id={id} className="scroll-mt-6 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
            <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
                        Guía
                    </span>
                </div>
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">{title}</h3>
                {summary && <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">{summary}</p>}
            </div>

            {steps.length > 0 && (
                <div className="p-5">
                    <ol className="space-y-3 list-none">
                        {steps.map((step, i) => (
                            <li key={i} className="flex items-start gap-3">
                                <span className="shrink-0 w-6 h-6 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 flex items-center justify-center text-xs font-bold">
                                    {i + 1}
                                </span>
                                <div className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed pt-0.5">
                                    {step}
                                </div>
                            </li>
                        ))}
                    </ol>

                    {note && (
                        <div className="mt-4 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                            {note}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// ── Tarjeta de componente ─────────────────────────────────────────────────────

function ComponentCard({ id, badge, badgeColor = 'emerald', title, description, params = [], children }) {
    return (
        <div id={id} className="scroll-mt-6 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
            {/* Header */}
            <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-start justify-between gap-4">
                <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        {badge && (
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide ${COLOR_RING[badgeColor]}`}>
                                {badge}
                            </span>
                        )}
                    </div>
                    <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100 font-mono">{title}</h3>
                    {description && <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5 leading-relaxed">{description}</p>}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px]">
                {/* Ejemplo */}
                <div className="p-5 border-r border-slate-100 dark:border-slate-800">
                    <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3">Ejemplo</p>
                    <div className="bg-slate-50/60 dark:bg-slate-800/40 rounded-xl p-3 border border-slate-100 dark:border-slate-800">
                        {children}
                    </div>
                </div>

                {/* Parámetros */}
                {params.length > 0 && (
                    <div className="p-5">
                        <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3">Parámetros</p>
                        <div className="space-y-0">
                            {params.map(p => <Param key={p.name} {...p} />)}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

// ── Separador de sección ──────────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title, color, id }) {
    const bg = {
        amber:   'bg-amber-600 shadow-amber-100 dark:shadow-amber-900/20',
        emerald: 'bg-emerald-600 shadow-emerald-100 dark:shadow-emerald-900/20',
        indigo:  'bg-indigo-600 shadow-indigo-100 dark:shadow-indigo-900/20',
        slate:   'bg-slate-500 shadow-slate-100 dark:shadow-slate-900/20',
    };
    return (
        <div id={id} className="flex items-center gap-3 pt-2 scroll-mt-6">
            <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-white shadow-lg shrink-0 ${bg[color]}`}>
                <Icon size={16} />
            </div>
            <h2 className="text-lg font-black text-slate-800 dark:text-white tracking-tight">{title}</h2>
            <div className="flex-1 h-px bg-slate-200 dark:bg-slate-800" />
        </div>
    );
}

// ── TOC sidebar ───────────────────────────────────────────────────────────────

function TableOfContents({ activeId }) {
    const scrollTo = (id) => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    return (
        <nav className="sticky top-4 space-y-4">
            <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">Contenidos</p>
            {TOC.map(group => (
                <div key={group.group}>
                    <p className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-lg mb-1 ${COLOR_RING[group.color]}`}>
                        {group.group}
                    </p>
                    <ul className="space-y-0.5">
                        {group.items.map(item => {
                            const isActive = activeId === item.id;
                            return (
                                <li key={item.id}>
                                    <button
                                        onClick={() => scrollTo(item.id)}
                                        className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition-all text-xs ${
                                            isActive
                                                ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 font-semibold'
                                                : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60 hover:text-slate-700 dark:hover:text-slate-300'
                                        }`}
                                    >
                                        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isActive ? 'bg-indigo-500' : COLOR_DOT[group.color]}`} />
                                        {item.label}
                                    </button>
                                </li>
                            );
                        })}
                    </ul>
                </div>
            ))}
        </nav>
    );
}

// ── Hook: detectar sección visible ───────────────────────────────────────────

function useActiveSection() {
    const [activeId, setActiveId] = useState(null);
    useEffect(() => {
        const allIds = TOC.flatMap(g => g.items.map(i => i.id));
        const observer = new IntersectionObserver(
            (entries) => {
                const visible = entries.filter(e => e.isIntersecting);
                if (visible.length > 0) setActiveId(visible[0].target.id);
            },
            { rootMargin: '-10% 0px -80% 0px' }
        );
        allIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) observer.observe(el);
        });
        return () => observer.disconnect();
    }, []);
    return activeId;
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function Help() {
    const activeId = useActiveSection();

    return (
        <div className="animate-in fade-in duration-500">

            {/* Header */}
            <div className="mb-8 space-y-1">
                <h1 className="text-4xl font-black text-slate-800 dark:text-white tracking-tight flex items-center gap-3">
                    <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-100 dark:shadow-indigo-900/20">
                        <CircleHelp size={22} />
                    </div>
                    Centro de Ayuda
                </h1>
                <p className="text-slate-400 dark:text-slate-500 text-sm font-medium">
                    Referencia visual de componentes disponibles para configurar dashboards. Los gráficos Plotly son configurables desde el modal de agregar componente; los legacy usan campos fijos.
                </p>
            </div>

            {/* Layout: sidebar + contenido */}
            <div className="flex gap-8 items-start">

                {/* Sidebar TOC */}
                <div className="w-52 shrink-0 hidden lg:block">
                    <TableOfContents activeId={activeId} />
                </div>

                {/* Contenido principal */}
                <div className="flex-1 min-w-0 space-y-10">

                    {/* ═══════════════════════════════════════════════════════
                        GUÍAS DE USO
                    ════════════════════════════════════════════════════════ */}
                    <SectionHeader icon={BookOpen} title="Guías de uso" color="amber" id="section-guides" />

                    <div className="rounded-xl border border-amber-200 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-900/10 px-4 py-3 text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
                        Estas guías describen los flujos principales de la aplicación a alto nivel. Si necesitás más detalle, revisá la documentación técnica en <code className="font-mono bg-amber-100 dark:bg-amber-900/30 px-1 rounded">docs/</code> o pedile a tu administrador acceso al material extendido.
                    </div>

                    <GuideCard
                        id="guide-pipeline"
                        title="Crear y ejecutar un pipeline"
                        summary="Un pipeline es una secuencia ordenada de pasos (steps) que toma archivos de entrada (Excel, PDF), los procesa y guarda los resultados en una métrica."
                        steps={[
                            <>Diríjase a <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">/pipelines</code> y abra "Nuevo pipeline". Defina nombre, descripción y el tipo de input principal.</>,
                            <>Edite el JSON del pipeline en el modal. La estructura es <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">{`{ workflow_metadata, context, pipeline: [{ step, params }, ...] }`}</code>. Los pasos disponibles aparecen en el desplegable del editor.</>,
                            <>Pasos típicos: <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">InitRun</code> → <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">RequestUserFiles</code> → <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">RunExcelETL</code> → <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">SaveToMetric</code>.</>,
                            <>Al ejecutar, el modal de ejecución le pedirá los archivos cuando un step lo requiera (pausa interactiva). Súbalos y continúe.</>,
                            <>Al terminar, los datos quedan guardados en la métrica destino y son visibles en <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">/results</code>.</>,
                        ]}
                        note="Sugerencia: si un pipeline va a procesar varios archivos del mismo tipo (ej. EMN por mes), use varios bloques RequestUserFiles consecutivos — cada uno limpia solo su carpeta de inputs."
                    />

                    <GuideCard
                        id="guide-tables"
                        title="Configurar tablas (catálogo /tables)"
                        summary="El catálogo de tablas permite definir tablas reutilizables (resumen por curso, lista de estudiantes, análisis por pregunta) sin escribir JSON."
                        steps={[
                            <>Diríjase a <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">/tables</code> y elija "Nueva tabla" o duplique una existente del catálogo.</>,
                            <>Defina el grouping principal (curso, estudiante, pregunta) y las columnas a calcular: cantidad, promedio, mínimo, máximo, distribución por categoría.</>,
                            <>Si una columna requiere un cálculo derivado (ej. avance temporal), referencie el <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">derived_field</code> ya configurado en el indicador.</>,
                            <>Vincule la tabla al indicador correspondiente desde su layout. Aparece en <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">/results</code> y en los PDFs si el layout PDF la incluye.</>,
                        ]}
                        note="Multi-agg: una misma columna puede mostrar varias agregaciones a la vez (ej. promedio + delta vs. evaluación anterior)."
                    />

                    <GuideCard
                        id="guide-charts"
                        title="Configurar gráficos (catálogo /charts)"
                        summary="El catálogo de gráficos centraliza la configuración de visualizaciones disponibles para los dashboards y los PDFs."
                        steps={[
                            <>Diríjase a <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">/charts</code>. Verá los gráficos pre-armados (BarByGroup, BoxPlotByGroup, RadarProfile, etc.) y puede crear nuevos.</>,
                            <>Para crear uno nuevo, elija el componente del registry (la lista completa aparece más abajo en este Centro de Ayuda) y mapee los campos del data al gráfico (groupField, valueField, etc.).</>,
                            <>Si el gráfico necesita un campo derivado, primero configure el <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">derived_field</code> en el indicador para que esté disponible.</>,
                            <>Asígnelo a un dashboard desde el layout del indicador, o a una sección del PDF desde el layout PDF.</>,
                        ]}
                        note="Los gráficos legacy (Recharts) usan campos fijos como _rend, _logro, _habilidad. Los Plotly nuevos son completamente configurables — se recomiendan los Plotly cuando sea posible."
                    />

                    <GuideCard
                        id="guide-functions"
                        title="Funciones derivadas (/functions)"
                        summary="Las funciones derivadas transforman datos crudos en valores derivados: avance entre evaluaciones, mejora respecto al inicio, mapeos de niveles, etc."
                        steps={[
                            <>Diríjase a <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">/functions</code> para ver el catálogo de mapeos. Los kinds disponibles incluyen <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">piecewise_linear</code> y lookup tables.</>,
                            <>Para campos derivados a nivel de indicador (avance temporal, promedio por estudiante), abra el indicador y configure <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">derived_columns</code> con el kind apropiado: <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">agg</code> (groupby), <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">slope</code> (regresión lineal expansiva), <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">delta</code> (último menos primero).</>,
                            <>Defina el <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">entity_field</code> (qué identifica una unidad: RUT, Curso+Nombre, etc.) y el <code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">time_field</code> con su orden si es ordinal (ej. ABRIL → JUNIO → AGOSTO).</>,
                            <>Una vez configurado, el campo aparece automáticamente en dashboards (<code className="font-mono px-1 rounded bg-slate-100 dark:bg-slate-800">/results</code>) y PDFs.</>,
                        ]}
                        note="Importante: las funciones temporales (slope/delta) operan sobre el histórico completo del estudiante, ignorando los filtros temporales del dashboard. Esto es deseable para que el avance no cambie según el filtro."
                    />

                    {/* ═══════════════════════════════════════════════════════
                        GRÁFICOS PLOTLY
                    ════════════════════════════════════════════════════════ */}
                    <SectionHeader icon={BarChart3} title="Gráficos Plotly" color="emerald" id="section-plotly-charts" />

                    <ComponentCard
                        id="BarByGroup"
                        badge="Plotly"
                        badgeColor="emerald"
                        title="BarByGroup — Barras por Grupo"
                        description="Barras verticales con el promedio de una métrica por grupo (ej. logro promedio por curso). Cada barra recibe un color distinto."
                        params={[
                            { name: 'groupField',  type: 'string',   required: true,  description: 'Campo de agrupación del eje X (ej. _curso)' },
                            { name: 'valueField',  type: 'string',   required: true,  description: 'Campo numérico a promediar (ej. _rend)' },
                            { name: 'labelX',      type: 'string',   required: false, description: 'Etiqueta del eje X' },
                            { name: 'labelY',      type: 'string',   required: false, description: 'Etiqueta del eje Y' },
                            { name: 'showValues',  type: 'boolean',  required: false, description: 'Mostrar valores sobre las barras' },
                        ]}
                    >
                        <BarByGroup
                            records={ESTUDIANTES}
                            groups={CURSOS}
                            groupField="_curso"
                            valueField="_rend"
                            valueLabel="Rendimiento"
                            formatValue={FMT_PCT}
                            formatStr="%.0"
                            height={220}
                        />
                    </ComponentCard>

                    <ComponentCard
                        id="HorizontalBarByDimension"
                        badge="Plotly"
                        badgeColor="emerald"
                        title="HorizontalBarByDimension — Barras Horizontales por Dimensión"
                        description="Barras horizontales con el promedio por dimensión secundaria (ej. habilidad o eje temático). Útil para comparar muchas categorías."
                        params={[
                            { name: 'dimensionField', type: 'string',  required: true,  description: 'Campo cuyas categorías son el eje Y (ej. _habilidad)' },
                            { name: 'valueField',     type: 'string',  required: true,  description: 'Campo numérico a promediar' },
                            { name: 'labelX',         type: 'string',  required: false, description: 'Etiqueta del eje X' },
                            { name: 'showValues',     type: 'boolean', required: false, description: 'Mostrar valores al lado de las barras' },
                        ]}
                    >
                        <HorizontalBarByDimension
                            records={PREGUNTAS}
                            dimensionField="_habilidad"
                            valueField="_logro_pregunta"
                            valueLabel="Logro"
                            formatValue={FMT_PCT}
                            formatStr="%.0"
                            height={200}
                        />
                    </ComponentCard>

                    <ComponentCard
                        id="DoubleGroupedBar"
                        badge="Plotly"
                        badgeColor="emerald"
                        title="DoubleGroupedBar — Barras Doblemente Agrupadas"
                        description="Barras agrupadas donde el eje X es el grupo principal (ej. cursos) y dentro de cada grupo hay sub-barras por subgrupo (ej. evaluaciones). Cada subgrupo recibe un color en la leyenda."
                        params={[
                            { name: 'groupField',    type: 'string',  required: true,  description: 'Eje X — agrupación principal (ej. _curso)' },
                            { name: 'subGroupField', type: 'string',  required: true,  description: 'Sub-agrupación — barras dentro de cada grupo (ej. _evaluacion_num)' },
                            { name: 'valueField',    type: 'string',  required: true,  description: 'Campo numérico a promediar' },
                            { name: 'legendField',   type: 'string',  required: false, description: 'Override: elige cuál campo maneja la leyenda (swap automático de ejes)' },
                            { name: 'showLegend',    type: 'boolean', required: false, description: 'Mostrar leyenda de subgrupos' },
                        ]}
                    >
                        <DoubleGroupedBar
                            records={ESTUDIANTES}
                            groupField="_curso"
                            subGroupField="_evaluacion_num"
                            valueField="_rend"
                            valueLabel="Rendimiento"
                            subGroupLabels={{ 1: 'Ev. 1', 2: 'Ev. 2' }}
                            formatValue={FMT_PCT}
                            formatStr="%.0"
                            height={240}
                            showLegend={true}
                        />
                    </ComponentCard>

                    <ComponentCard
                        id="BoxPlotByGroup"
                        badge="Plotly"
                        badgeColor="emerald"
                        title="BoxPlotByGroup — Boxplot por Grupo"
                        description="Diagrama de caja y bigotes que muestra la distribución estadística (mín, Q1, mediana, Q3, máx) de una métrica por grupo."
                        params={[
                            { name: 'groupField', type: 'string', required: true, description: 'Campo de agrupación del eje X' },
                            { name: 'valueField', type: 'string', required: true, description: 'Campo numérico cuya distribución se grafica' },
                            { name: 'labelX',     type: 'string', required: false, description: 'Etiqueta del eje X' },
                            { name: 'labelY',     type: 'string', required: false, description: 'Etiqueta del eje Y' },
                        ]}
                    >
                        <BoxPlotByGroup
                            records={ESTUDIANTES}
                            groups={CURSOS}
                            groupField="_curso"
                            valueField="_rend"
                            formatValue={FMT_PCT}
                            formatStr="%.0"
                            height={220}
                        />
                    </ComponentCard>

                    <ComponentCard
                        id="PieComposition"
                        badge="Plotly"
                        badgeColor="emerald"
                        title="PieComposition — Composición (Torta)"
                        description="Gráfico de dona con la distribución de alumnos por nivel de logro u otra categoría. Muestra porcentajes y etiquetas en cada sector."
                        params={[
                            { name: 'categoryField',  type: 'string',   required: true,  description: 'Campo categórico (ej. _logro)' },
                            { name: 'categoryLevels', type: 'string[]', required: false, description: 'Orden de las categorías (controla colores)' },
                        ]}
                    >
                        <PieComposition
                            records={ESTUDIANTES}
                            categoryField="_logro"
                            categoryLevels={NIVELES}
                            height={220}
                        />
                    </ComponentCard>

                    <ComponentCard
                        id="StackedCountByGroup"
                        badge="Plotly"
                        badgeColor="emerald"
                        title="StackedCountByGroup — Conteo Apilado por Grupo"
                        description="Barras apiladas con el conteo de alumnos por nivel de logro dentro de cada grupo. Permite ver la composición interna por curso."
                        params={[
                            { name: 'groupField',     type: 'string',   required: true,  description: 'Campo de agrupación del eje X (ej. _curso)' },
                            { name: 'categoryField',  type: 'string',   required: true,  description: 'Campo de categoría para el apilado (ej. _logro)' },
                            { name: 'categoryLevels', type: 'string[]', required: false, description: 'Orden de los niveles (controla colores)' },
                            { name: 'showValues',     type: 'boolean',  required: false, description: 'Mostrar conteos dentro de las barras' },
                        ]}
                    >
                        <StackedCountByGroup
                            records={ESTUDIANTES}
                            groups={CURSOS}
                            groupField="_curso"
                            categoryField="_logro"
                            categoryLevels={NIVELES}
                            height={220}
                        />
                    </ComponentCard>

                    <ComponentCard
                        id="StackedCountByGroupAndPeriod"
                        badge="Plotly"
                        badgeColor="emerald"
                        title="StackedCountByGroupAndPeriod — Conteo Apilado por Grupo y Período"
                        description="Barras apiladas agrupadas por curso y número de evaluación. Muestra cómo cambia la distribución de niveles entre evaluaciones para cada curso."
                        params={[
                            { name: 'groupField',     type: 'string',   required: true,  description: 'Agrupación principal (ej. _curso)' },
                            { name: 'periodField',    type: 'string',   required: true,  description: 'Campo de período (ej. _evaluacion_num)' },
                            { name: 'categoryField',  type: 'string',   required: true,  description: 'Campo de categoría para el apilado (ej. _logro)' },
                            { name: 'categoryLevels', type: 'string[]', required: false, description: 'Orden de los niveles' },
                            { name: 'periodLabels',   type: 'object',   required: false, description: 'Mapa num → etiqueta (ej. {1: "Ev. 1"})' },
                        ]}
                    >
                        <StackedCountByGroupAndPeriod
                            records={ESTUDIANTES}
                            groups={CURSOS}
                            groupField="_curso"
                            periodField="_evaluacion_num"
                            categoryField="_logro"
                            categoryLevels={NIVELES}
                            periodLabels={{ 1: 'Ev. 1', 2: 'Ev. 2' }}
                            height={240}
                        />
                    </ComponentCard>

                    <ComponentCard
                        id="TrendLine"
                        badge="Plotly"
                        badgeColor="emerald"
                        title="TrendLine — Tendencia Temporal"
                        description="Gráfico de líneas que muestra la evolución de una métrica a lo largo de evaluaciones, con una línea por curso. Permite ver tendencias de mejora o retroceso."
                        params={[
                            { name: 'groupField',   type: 'string',  required: true,  description: 'Campo de agrupación — una línea por valor (ej. _curso)' },
                            { name: 'periodField',  type: 'string',  required: true,  description: 'Eje X — campo temporal (ej. _evaluacion_num)' },
                            { name: 'valueField',   type: 'string',  required: true,  description: 'Eje Y — métrica a graficar' },
                            { name: 'periodLabels', type: 'object',  required: false, description: 'Mapa de etiquetas para los períodos' },
                            { name: 'showValues',   type: 'boolean', required: false, description: 'Mostrar valores sobre los puntos' },
                        ]}
                    >
                        <TrendLine
                            records={ESTUDIANTES}
                            groups={CURSOS}
                            groupField="_curso"
                            periodField="_evaluacion_num"
                            valueField="_rend"
                            valueLabel="Rendimiento"
                            periodLabels={{ 1: 'Ev. 1', 2: 'Ev. 2' }}
                            formatValue={FMT_PCT}
                            formatStr="%.0"
                            height={220}
                            showLegend={true}
                        />
                    </ComponentCard>

                    <ComponentCard
                        id="RadarProfile"
                        badge="Plotly"
                        badgeColor="emerald"
                        title="RadarProfile — Perfil Radar"
                        description="Gráfico de radar (araña) con el promedio de una métrica por dimensión, con un polígono coloreado por grupo. Ideal para perfiles de habilidades."
                        params={[
                            { name: 'axisField',  type: 'string', required: true,  description: 'Campo cuyas categorías forman los ejes del radar (ej. _habilidad)' },
                            { name: 'valueField', type: 'string', required: true,  description: 'Valor en cada eje' },
                            { name: 'groupField', type: 'string', required: true,  description: 'Agrupación — un polígono por valor (ej. _curso)' },
                            { name: 'showLegend', type: 'boolean', required: false, description: 'Mostrar leyenda de grupos' },
                        ]}
                    >
                        <RadarProfile
                            records={PREGUNTAS}
                            groups={[]}
                            groupField="_curso"
                            axisField="_habilidad"
                            valueField="_logro_pregunta"
                            formatValue={FMT_PCT}
                            height={260}
                        />
                    </ComponentCard>

                    {/* ═══════════════════════════════════════════════════════
                        TABLAS PLOTLY
                    ════════════════════════════════════════════════════════ */}
                    <SectionHeader icon={Table2} title="Tablas Plotly" color="indigo" id="section-plotly-tables" />

                    <ComponentCard
                        id="SummaryTable"
                        badge="Tabla"
                        badgeColor="indigo"
                        title="SummaryTable — Resumen por Grupo"
                        description="Tabla de resumen con agregaciones por grupo: conteo, promedio, mín/máx y distribución por categoría. Las filas son clickeables para navegar al detalle."
                        params={[
                            { name: 'groupField',     type: 'string',   required: false, description: 'Campo de agrupación (default: _curso)' },
                            { name: 'valueField',     type: 'string',   required: false, description: 'Métrica numérica principal' },
                            { name: 'categoryField',  type: 'string',   required: false, description: 'Campo de categoría para distribución' },
                            { name: 'categoryLevels', type: 'string[]', required: false, description: 'Orden de las categorías' },
                        ]}
                    >
                        <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                            <SummaryTable
                                records={ESTUDIANTES}
                                groups={CURSOS}
                                groupField="_curso"
                                valueField="_rend"
                                formatValue={FMT_PCT}
                                categoryField="_logro"
                                categoryLevels={NIVELES}
                                onGroupClick={() => {}}
                            />
                        </div>
                    </ComponentCard>

                    <ComponentCard
                        id="DetailListTable"
                        badge="Tabla"
                        badgeColor="indigo"
                        title="DetailListTable — Lista de Items"
                        description="Lista de registros individuales ordenada por valor descendente, con un badge de categoría. Útil para mostrar el ranking de alumnos."
                        params={[
                            { name: 'labelField', type: 'string', required: false, description: 'Campo de etiqueta (default: _nombre)' },
                            { name: 'valueField', type: 'string', required: false, description: 'Campo numérico de ordenación' },
                            { name: 'badgeField', type: 'string', required: false, description: 'Campo de categoría para el badge' },
                        ]}
                    >
                        <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                            <DetailListTable
                                records={ESTUDIANTES.slice(0, 6)}
                                labelField="_nombre"
                                valueField="_rend"
                                formatValue={FMT_PCT}
                                badgeField="_logro"
                            />
                        </div>
                    </ComponentCard>

                    <ComponentCard
                        id="DetailListWithProgress"
                        badge="Tabla"
                        badgeColor="indigo"
                        title="DetailListWithProgress — Lista con Progreso"
                        description="Lista de ítems con barra de progreso coloreada por umbral (verde ≥ 60%, amarillo ≥ 45%, rojo < 45%). Ideal para análisis ítem a ítem."
                        params={[
                            { name: 'dimensionField', type: 'string', required: true,  description: 'Campo de dimensión agrupadora (ej. _habilidad)' },
                            { name: 'progressField',  type: 'string', required: true,  description: 'Campo numérico para la barra de progreso' },
                            { name: 'labelField',     type: 'string', required: false, description: 'Etiqueta de cada ítem (default: _pregunta)' },
                        ]}
                    >
                        <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                            <DetailListWithProgress
                                records={PREGUNTAS}
                                labelField="_pregunta"
                                dimensionField="_habilidad"
                                progressField="_logro_pregunta"
                                progressLabel="Logro"
                            />
                        </div>
                    </ComponentCard>

                    {/* ═══════════════════════════════════════════════════════
                        GRÁFICOS LEGACY
                    ════════════════════════════════════════════════════════ */}
                    <SectionHeader icon={BarChart3} title="Gráficos Legacy" color="slate" id="section-legacy-charts" />

                    <div className="rounded-xl border border-amber-200 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-900/10 px-4 py-3 text-xs text-amber-700 dark:text-amber-400">
                        Los componentes legacy usan campos fijos (<code className="font-mono bg-amber-100 dark:bg-amber-900/30 px-1 rounded">_rend</code>, <code className="font-mono bg-amber-100 dark:bg-amber-900/30 px-1 rounded">_logro</code>, <code className="font-mono bg-amber-100 dark:bg-amber-900/30 px-1 rounded">_habilidad</code>) y no requieren configurar ejes en el modal. Se recomienda migrar a los gráficos Plotly configurables.
                    </div>

                    <ComponentCard
                        id="GraficoLogroPorCurso"
                        badge="Legacy"
                        badgeColor="slate"
                        title="GraficoLogroPorCurso"
                        description="Barras verticales con el logro promedio por curso. Soporta toggle entre logro_1 (%) y logro_2 (puntaje). Requiere roles logro_1 y/o logro_2."
                        params={[
                            { name: 'data',        type: 'array',  required: true, description: 'Filas de estudiantes con _rend y _curso' },
                            { name: 'cursos',      type: 'array',  required: true, description: 'Lista de cursos únicos' },
                            { name: 'metric',      type: 'string', required: true, description: '"logro" o "simce"' },
                            { name: 'roleLabels',  type: 'object', required: false, description: 'Etiquetas personalizadas por rol' },
                        ]}
                    >
                        <GraficoLogroPorCurso data={ESTUDIANTES} cursos={CURSOS} metric="logro" roleLabels={ROLE_LABELS} />
                    </ComponentCard>

                    <ComponentCard
                        id="GraficoBoxplotPorCurso"
                        badge="Legacy"
                        badgeColor="slate"
                        title="GraficoBoxplotPorCurso"
                        description="Diagrama de caja y bigotes por curso. Muestra mínimo, Q1, mediana, Q3 y máximo para visualizar la dispersión interna de cada grupo."
                        params={[
                            { name: 'data',   type: 'array',  required: true, description: 'Filas de estudiantes con _rend y _curso' },
                            { name: 'cursos', type: 'array',  required: true, description: 'Lista de cursos únicos' },
                            { name: 'metric', type: 'string', required: true, description: '"logro" o "simce"' },
                        ]}
                    >
                        <GraficoBoxplotPorCurso data={ESTUDIANTES} cursos={CURSOS} metric="logro" />
                    </ComponentCard>

                    <ComponentCard
                        id="GraficoNivelesPorCurso"
                        badge="Legacy"
                        badgeColor="slate"
                        title="GraficoNivelesPorCurso"
                        description="Barras apiladas con la cantidad de alumnos por nivel de logro en cada curso. Los colores corresponden a Insuficiente / Elemental / Adecuado."
                        params={[
                            { name: 'data',               type: 'array',  required: true, description: 'Filas de estudiantes con _logro y _curso' },
                            { name: 'cursos',             type: 'array',  required: true, description: 'Lista de cursos únicos' },
                            { name: 'achievement_levels', type: 'array',  required: true, description: 'Lista de niveles (en orden de apilado)' },
                        ]}
                    >
                        <GraficoNivelesPorCurso data={ESTUDIANTES} cursos={CURSOS} achievement_levels={NIVELES} />
                    </ComponentCard>

                    <ComponentCard
                        id="GraficoDistribucionNiveles"
                        badge="Legacy"
                        badgeColor="slate"
                        title="GraficoDistribucionNiveles"
                        description="Gráfico de dona con la distribución general de todos los alumnos por nivel de logro, sin distinción de curso."
                        params={[
                            { name: 'data',               type: 'array', required: true, description: 'Filas de estudiantes con _logro' },
                            { name: 'achievement_levels', type: 'array', required: true, description: 'Lista de niveles' },
                        ]}
                    >
                        <GraficoDistribucionNiveles data={ESTUDIANTES} achievement_levels={NIVELES} />
                    </ComponentCard>

                    <ComponentCard
                        id="GraficoHabilidades"
                        badge="Legacy"
                        badgeColor="slate"
                        title="GraficoHabilidades"
                        description="Barras horizontales con el logro promedio por habilidad. Se nutre de los datos de preguntas del curso activo, no de estudiantes."
                        params={[
                            { name: 'data',       type: 'array',  required: true,  description: 'Filas de preguntas con _habilidad y _logro_pregunta' },
                            { name: 'roleLabels', type: 'object', required: false, description: 'Etiquetas personalizadas por rol' },
                        ]}
                    >
                        <GraficoHabilidades data={PREGUNTAS} roleLabels={ROLE_LABELS} />
                    </ComponentCard>

                    <ComponentCard
                        id="GraficoNivelesPorCursoYMes"
                        badge="Legacy"
                        badgeColor="slate"
                        title="GraficoNivelesPorCursoYMes"
                        description="Barras apiladas por nivel agrupadas por curso y número de evaluación. Permite comparar la evolución de niveles a lo largo del tiempo dentro de cada curso."
                        params={[
                            { name: 'data',               type: 'array', required: true, description: 'Estudiantes con _evaluacion_num, _logro y _curso' },
                            { name: 'cursos',             type: 'array', required: true, description: 'Lista de cursos únicos' },
                            { name: 'achievement_levels', type: 'array', required: true, description: 'Lista de niveles' },
                        ]}
                    >
                        <GraficoNivelesPorCursoYMes data={ESTUDIANTES} cursos={CURSOS} achievement_levels={NIVELES} />
                    </ComponentCard>

                    <ComponentCard
                        id="GraficoPromedioAgrupadoPorDimension"
                        badge="Legacy"
                        badgeColor="slate"
                        title="GraficoPromedioAgrupadoPorDimension"
                        description="Barras agrupadas con el logro promedio por curso, una barra por número de evaluación. Compara el rendimiento entre evaluaciones dentro de cada curso."
                        params={[
                            { name: 'data',       type: 'array',  required: true,  description: 'Estudiantes con _evaluacion_num, _rend y _curso' },
                            { name: 'cursos',     type: 'array',  required: true,  description: 'Lista de cursos únicos' },
                            { name: 'roleLabels', type: 'object', required: false, description: 'Etiquetas por rol' },
                            { name: 'metric',     type: 'string', required: true,  description: '"logro" o "simce"' },
                        ]}
                    >
                        <GraficoPromedioAgrupadoPorDimension data={ESTUDIANTES} cursos={CURSOS} roleLabels={ROLE_LABELS} metric="logro" />
                    </ComponentCard>

                    <ComponentCard
                        id="GraficoTendenciaTemporal"
                        badge="Legacy"
                        badgeColor="slate"
                        title="GraficoTendenciaTemporal"
                        description="Gráfico de líneas con la evolución del logro promedio por evaluación, una línea por curso. Muestra la trayectoria de cada grupo a lo largo del tiempo."
                        params={[
                            { name: 'data',       type: 'array',  required: true, description: 'Estudiantes con _evaluacion_num, _rend y _curso' },
                            { name: 'cursos',     type: 'array',  required: true, description: 'Lista de cursos' },
                            { name: 'roleLabels', type: 'object', required: false, description: 'Etiquetas por rol' },
                            { name: 'metric',     type: 'string', required: true, description: '"logro" o "simce"' },
                        ]}
                    >
                        <GraficoTendenciaTemporal data={ESTUDIANTES} cursos={CURSOS} roleLabels={ROLE_LABELS} metric="logro" />
                    </ComponentCard>

                    <ComponentCard
                        id="GraficoRadarHabilidades"
                        badge="Legacy"
                        badgeColor="slate"
                        title="GraficoRadarHabilidades"
                        description="Gráfico de radar (araña) con el logro promedio por habilidad. Con múltiples cursos, muestra un polígono por curso. Con un solo curso, muestra el polígono general."
                        params={[
                            { name: 'data',       type: 'array', required: true,  description: 'Preguntas con _habilidad y _logro_pregunta' },
                            { name: 'cursos',     type: 'array', required: false, description: 'Lista de cursos para mostrar múltiples polígonos' },
                            { name: 'roleLabels', type: 'object', required: false, description: 'Etiquetas por rol' },
                        ]}
                    >
                        <GraficoRadarHabilidades data={PREGUNTAS} cursos={[]} roleLabels={ROLE_LABELS} />
                    </ComponentCard>

                    {/* ═══════════════════════════════════════════════════════
                        TABLAS LEGACY
                    ════════════════════════════════════════════════════════ */}
                    <SectionHeader icon={Table2} title="Tablas Legacy" color="slate" id="section-legacy-tables" />

                    <ComponentCard
                        id="TablaResumenCursos"
                        badge="Legacy"
                        badgeColor="slate"
                        title="TablaResumenCursos"
                        description="Resumen agregado por curso: total de alumnos, logro promedio, mín/máx y distribución por nivel. Las filas son clickeables para ir al detalle del curso."
                        params={[
                            { name: 'data',               type: 'array',   required: true,  description: 'Estudiantes con _curso, _rend, _logro' },
                            { name: 'cursos',             type: 'array',   required: true,  description: 'Lista de cursos únicos' },
                            { name: 'achievement_levels', type: 'array',   required: false, description: 'Lista de niveles de logro' },
                            { name: 'onCursoClick',       type: 'function',required: false, description: 'Callback al hacer clic en una fila' },
                        ]}
                    >
                        <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                            <TablaResumenCursos data={ESTUDIANTES} cursos={CURSOS} onCursoClick={() => {}} cursoActivo={null} roleLabels={ROLE_LABELS} activeRoles={ACTIVE_ROLES_BASIC} achievement_levels={NIVELES} />
                        </div>
                    </ComponentCard>

                    <ComponentCard
                        id="TablaAlumnos"
                        badge="Legacy"
                        badgeColor="slate"
                        title="TablaAlumnos"
                        description="Listado de estudiantes del curso activo, ordenados por logro descendente, con nivel de logro y tendencia (avance) respecto a la evaluación anterior."
                        params={[
                            { name: 'data',        type: 'array',  required: true,  description: 'Estudiantes del curso activo con _nombre, _rend, _logro, _avance' },
                            { name: 'roleLabels',  type: 'object', required: false, description: 'Etiquetas por rol' },
                            { name: 'activeRoles', type: 'object', required: false, description: 'Roles activos (controla columnas visibles)' },
                        ]}
                    >
                        <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                            <TablaAlumnos data={ESTUDIANTES.slice(0, 6)} roleLabels={ROLE_LABELS} activeRoles={ACTIVE_ROLES_BASIC} />
                        </div>
                    </ComponentCard>

                    <ComponentCard
                        id="TablaPreguntas"
                        badge="Legacy"
                        badgeColor="slate"
                        title="TablaPreguntas"
                        description="Análisis ítem a ítem con habilidad asociada, barra de logro coloreada por rango (verde ≥ 60%, amarillo ≥ 45%, rojo < 45%) y respuesta correcta."
                        params={[
                            { name: 'data',       type: 'array',  required: true,  description: 'Preguntas con _pregunta, _habilidad, _logro_pregunta, _correcta' },
                            { name: 'roleLabels', type: 'object', required: false, description: 'Etiquetas por rol' },
                        ]}
                    >
                        <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                            <TablaPreguntas data={PREGUNTAS} roleLabels={ROLE_LABELS} />
                        </div>
                    </ComponentCard>

                    <div className="h-8" />
                </div>
            </div>
        </div>
    );
}
