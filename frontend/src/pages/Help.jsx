import React, { useState } from 'react';
import { CircleHelp, BarChart3, Table2, ChevronDown, ChevronRight } from 'lucide-react';
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

// ── Datos de muestra ─────────────────────────────────────────────────────────

const CURSOS = ['4°A', '4°B', '4°C'];
const NIVELES = ['Insuficiente', 'Elemental', 'Adecuado'];
const HABILIDADES = ['Comprensión', 'Argumentación', 'Síntesis', 'Evaluación'];

const ESTUDIANTES = [
    // Evaluación 1
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
    // Evaluación 2
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
    { _pregunta: 1,  _habilidad: 'Comprensión',  _logro_pregunta: 0.78, _correcta: 'A' },
    { _pregunta: 2,  _habilidad: 'Comprensión',  _logro_pregunta: 0.62, _correcta: 'C' },
    { _pregunta: 3,  _habilidad: 'Comprensión',  _logro_pregunta: 0.50, _correcta: 'B' },
    { _pregunta: 4,  _habilidad: 'Argumentación', _logro_pregunta: 0.45, _correcta: 'D' },
    { _pregunta: 5,  _habilidad: 'Argumentación', _logro_pregunta: 0.33, _correcta: 'A' },
    { _pregunta: 6,  _habilidad: 'Síntesis',      _logro_pregunta: 0.85, _correcta: 'B' },
    { _pregunta: 7,  _habilidad: 'Síntesis',      _logro_pregunta: 0.70, _correcta: 'C' },
    { _pregunta: 8,  _habilidad: 'Evaluación',    _logro_pregunta: 0.55, _correcta: 'A' },
    { _pregunta: 9,  _habilidad: 'Evaluación',    _logro_pregunta: 0.40, _correcta: 'D' },
    { _pregunta: 10, _habilidad: 'Evaluación',    _logro_pregunta: 0.28, _correcta: 'B' },
];

const ROLE_LABELS = { logro_1: 'Rendimiento %', logro_2: 'Puntaje SIMCE' };
const ACTIVE_ROLES_BASIC = { logro_1: true, nivel_de_logro: true };

// ── Componente de sección colapsable ─────────────────────────────────────────

function Section({ icon: Icon, title, color, children }) {
    const [open, setOpen] = useState(true);
    const colors = {
        emerald: 'bg-emerald-600 shadow-emerald-100 dark:shadow-emerald-900/20',
        indigo:  'bg-indigo-600 shadow-indigo-100 dark:shadow-indigo-900/20',
    };
    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden">
            <button
                onClick={() => setOpen(v => !v)}
                className="w-full flex items-center gap-4 px-6 py-5 text-left hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors"
            >
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-white shadow-lg ${colors[color]}`}>
                    <Icon size={18} />
                </div>
                <h2 className="text-xl font-black text-slate-800 dark:text-white tracking-tight flex-1">{title}</h2>
                {open
                    ? <ChevronDown size={18} className="text-slate-400" />
                    : <ChevronRight size={18} className="text-slate-400" />
                }
            </button>
            {open && <div className="px-6 pb-8 space-y-10">{children}</div>}
        </div>
    );
}

// ── Tarjeta de componente ─────────────────────────────────────────────────────

function ComponentCard({ title, description, requires, children }) {
    return (
        <div>
            <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                    <h3 className="text-sm font-black text-slate-700 dark:text-slate-200 font-mono">{title}</h3>
                    {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
                </div>
                {requires?.length > 0 && (
                    <div className="flex gap-1 flex-wrap justify-end shrink-0">
                        {requires.map(r => (
                            <span key={r} className="px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-[10px] font-bold border border-indigo-100 dark:border-indigo-800">
                                {r}
                            </span>
                        ))}
                    </div>
                )}
            </div>
            <div className="bg-slate-50/60 dark:bg-slate-800/40 rounded-2xl p-4 border border-slate-100 dark:border-slate-800">
                {children}
            </div>
        </div>
    );
}

// ── Página principal ─────────────────────────────────────────────────────────

export default function Help() {
    return (
        <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-500">

            {/* Header */}
            <div className="space-y-1">
                <h1 className="text-4xl font-black text-slate-800 dark:text-white tracking-tight flex items-center gap-3">
                    <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-100 dark:shadow-indigo-900/20">
                        <CircleHelp size={22} />
                    </div>
                    Centro de Ayuda
                </h1>
                <p className="text-slate-400 dark:text-slate-500 text-sm font-medium">
                    Referencia visual de los componentes disponibles para configurar dashboards en el Editor de Layout.
                </p>
            </div>

            {/* ── Gráficos ── */}
            <Section icon={BarChart3} title="Gráficos" color="emerald">

                <ComponentCard
                    title="GraficoLogroPorCurso"
                    description="Barras verticales con el logro promedio por curso. Soporta toggle entre logro_1 (%) y logro_2 (puntaje)."
                    requires={['logro_1']}
                >
                    <GraficoLogroPorCurso
                        data={ESTUDIANTES}
                        cursos={CURSOS}
                        metric="logro"
                        roleLabels={ROLE_LABELS}
                    />
                </ComponentCard>

                <ComponentCard
                    title="GraficoBoxplotPorCurso"
                    description="Diagrama de caja y bigotes por curso. Muestra mínimo, Q1, mediana, Q3 y máximo para visualizar la distribución interna."
                    requires={['logro_1']}
                >
                    <GraficoBoxplotPorCurso
                        data={ESTUDIANTES}
                        cursos={CURSOS}
                        metric="logro"
                    />
                </ComponentCard>

                <ComponentCard
                    title="GraficoNivelesPorCurso"
                    description="Barras apiladas con la cantidad de alumnos por nivel de logro en cada curso."
                    requires={['nivel_de_logro']}
                >
                    <GraficoNivelesPorCurso
                        data={ESTUDIANTES}
                        cursos={CURSOS}
                        achievement_levels={NIVELES}
                    />
                </ComponentCard>

                <ComponentCard
                    title="GraficoDistribucionNiveles"
                    description="Gráfico de dona con la distribución general de todos los alumnos por nivel de logro."
                    requires={['nivel_de_logro']}
                >
                    <GraficoDistribucionNiveles
                        data={ESTUDIANTES}
                        achievement_levels={NIVELES}
                    />
                </ComponentCard>

                <ComponentCard
                    title="GraficoHabilidades"
                    description="Barras horizontales con el logro promedio por habilidad o eje temático. Se usa en la vista de detalle por curso."
                    requires={['habilidad']}
                >
                    <GraficoHabilidades
                        data={PREGUNTAS}
                        roleLabels={ROLE_LABELS}
                    />
                </ComponentCard>

                <ComponentCard
                    title="GraficoNivelesPorCursoYMes"
                    description="Barras apiladas por nivel de logro agrupadas por curso y número de evaluación. Permite comparar la evolución de niveles a lo largo del tiempo dentro de cada curso."
                    requires={['nivel_de_logro', 'evaluacion_num']}
                >
                    <GraficoNivelesPorCursoYMes
                        data={ESTUDIANTES}
                        cursos={CURSOS}
                        achievement_levels={NIVELES}
                    />
                </ComponentCard>

                <ComponentCard
                    title="GraficoPromedioAgrupadoPorDimension"
                    description="Barras agrupadas con el logro promedio por curso, una barra por número de evaluación. Permite comparar el rendimiento entre evaluaciones dentro de cada curso."
                    requires={['logro_1', 'evaluacion_num']}
                >
                    <GraficoPromedioAgrupadoPorDimension
                        data={ESTUDIANTES}
                        cursos={CURSOS}
                        roleLabels={ROLE_LABELS}
                        metric="logro"
                    />
                </ComponentCard>

                <ComponentCard
                    title="GraficoTendenciaTemporal"
                    description="Gráfico de líneas que muestra la evolución del logro promedio a lo largo de las evaluaciones, con una línea por curso."
                    requires={['logro_1', 'evaluacion_num']}
                >
                    <GraficoTendenciaTemporal
                        data={ESTUDIANTES}
                        cursos={CURSOS}
                        roleLabels={ROLE_LABELS}
                        metric="logro"
                    />
                </ComponentCard>

                <ComponentCard
                    title="GraficoRadarHabilidades"
                    description="Gráfico de radar (araña) con el logro promedio por habilidad. Muestra un polígono por curso cuando hay múltiples cursos en los datos."
                    requires={['habilidad']}
                >
                    <GraficoRadarHabilidades
                        data={PREGUNTAS}
                        cursos={[]}
                        roleLabels={ROLE_LABELS}
                    />
                </ComponentCard>

            </Section>

            {/* ── Tablas ── */}
            <Section icon={Table2} title="Tablas" color="indigo">

                <ComponentCard
                    title="TablaResumenCursos"
                    description="Resumen agregado por curso: total alumnos, logro promedio, mín/máx y conteo por nivel. Cada fila es clickeable para ir al detalle del curso."
                >
                    <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                        <TablaResumenCursos
                            data={ESTUDIANTES}
                            cursos={CURSOS}
                            onCursoClick={() => {}}
                            cursoActivo={null}
                            roleLabels={ROLE_LABELS}
                            activeRoles={ACTIVE_ROLES_BASIC}
                            achievement_levels={NIVELES}
                        />
                    </div>
                </ComponentCard>

                <ComponentCard
                    title="TablaAlumnos"
                    description="Listado de estudiantes de un curso ordenado por logro descendente, con nivel de logro y tendencia (avance) respecto a la evaluación anterior."
                >
                    <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                        <TablaAlumnos
                            data={ESTUDIANTES.slice(0, 6)}
                            roleLabels={ROLE_LABELS}
                            activeRoles={ACTIVE_ROLES_BASIC}
                        />
                    </div>
                </ComponentCard>

                <ComponentCard
                    title="TablaPreguntas"
                    description="Análisis ítem a ítem con la habilidad asociada, barra de logro con color por rango (verde ≥ 60%, amarillo ≥ 45%, rojo < 45%) y respuesta correcta."
                >
                    <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                        <TablaPreguntas
                            data={PREGUNTAS}
                            roleLabels={ROLE_LABELS}
                        />
                    </div>
                </ComponentCard>

            </Section>
        </div>
    );
}
