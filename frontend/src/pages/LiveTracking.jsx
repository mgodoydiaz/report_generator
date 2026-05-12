import { useState } from 'react';
import {
    Sparkles, Newspaper, GraduationCap, UserCog, BookOpen,
    ArrowRight, MessageCircle, Construction
} from 'lucide-react';

// ════════════════════════════════════════════════════════════════════════════
//   "Próximos módulos" — landing exploratoria
//   Sin protagonismo: es un mapa de lo que viene, no un dashboard activo.
//   Cada módulo es una card con descripción breve, ideas iniciales y CTA
//   "Conversar" para ir definiendo el alcance con Miguel.
// ════════════════════════════════════════════════════════════════════════════

const MODULOS = [
    {
        id: 'noticias',
        nombre: 'Módulo Noticias',
        icono: Newspaper,
        color: 'indigo',
        resumen: 'Lo que cambió entre lecturas — explicado en una frase.',
        descripcion:
            'Lee las últimas evaluaciones cargadas y resume los movimientos relevantes por curso: ' +
            'pasos de nivel, brechas que se cierran, alertas que aparecen. Pensado para que un director ' +
            'lea 5 frases y entienda la semana.',
        ideas: [
            'Detectar deltas de riesgo por curso entre lecturas consecutivas',
            'Generar el texto narrativo desde reglas (no LLM por ahora)',
            'Permitir marcar noticias como vistas / archivadas',
        ],
        estado: 'Por definir',
    },
    {
        id: 'estudiantes',
        nombre: 'Módulo Estudiantes',
        icono: GraduationCap,
        color: 'violet',
        resumen: 'La trayectoria individual, sin tener que armarla a mano.',
        descripcion:
            'Ficha por estudiante con su historia de evaluaciones, niveles y banderas. ' +
            'Cuándo subió, cuándo cayó, qué subprueba lo arrastra. Permite buscar por nombre o RUT ' +
            'y comparar con el promedio de su curso.',
        ideas: [
            'Línea de tiempo de niveles alcanzados por evaluación',
            'Comparativo curso vs. estudiante en cada subprueba',
            'Exportar ficha PDF para reunión con apoderado',
        ],
        estado: 'Por definir',
    },
    {
        id: 'profesor',
        nombre: 'Panel Profesor',
        icono: UserCog,
        color: 'emerald',
        resumen: 'Vista del docente con solo su curso, sin ruido del resto.',
        descripcion:
            'Acceso restringido por curso/asignatura para que cada profesor vea únicamente ' +
            'su grupo, con los KPIs que le sirven para planificar la siguiente clase. ' +
            'Decisión clave: ¿cuentas individuales o link público por curso?',
        ideas: [
            'Rol "docente" con scoping por curso en la API',
            'Vista simplificada: 3-4 KPIs + tabla de estudiantes priorizados',
            'Recomendaciones de foco por subprueba',
        ],
        estado: 'Por definir',
    },
    {
        id: 'cobertura',
        nombre: 'Seguimiento Cobertura Curricular',
        icono: BookOpen,
        color: 'amber',
        resumen: 'Qué se cubrió, qué falta, contra el plan anual.',
        descripcion:
            'Registro de avance de contenidos por curso/asignatura cruzado con el plan ' +
            'anual del MINEDUC. Visualiza brechas entre lo planificado y lo enseñado, y conecta ' +
            'con los resultados de evaluaciones para inferir efectividad.',
        ideas: [
            'Catálogo de OAs por nivel (CL/MAT/CN/HCS)',
            'Carga periódica de cobertura (semanal/quincenal)',
            'Cruce cobertura × resultados para detectar gaps de aprendizaje',
        ],
        estado: 'Por definir',
    },
];

const COLOR_MAP = {
    indigo:  { bg: 'bg-indigo-50 dark:bg-indigo-950/40',   text: 'text-indigo-700 dark:text-indigo-300',   border: 'border-indigo-200 dark:border-indigo-900',   hover: 'hover:border-indigo-300 dark:hover:border-indigo-700',   chip: 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300' },
    violet:  { bg: 'bg-violet-50 dark:bg-violet-950/40',   text: 'text-violet-700 dark:text-violet-300',   border: 'border-violet-200 dark:border-violet-900',   hover: 'hover:border-violet-300 dark:hover:border-violet-700',   chip: 'bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300' },
    emerald: { bg: 'bg-emerald-50 dark:bg-emerald-950/40', text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-200 dark:border-emerald-900', hover: 'hover:border-emerald-300 dark:hover:border-emerald-700', chip: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300' },
    amber:   { bg: 'bg-amber-50 dark:bg-amber-950/40',     text: 'text-amber-700 dark:text-amber-300',     border: 'border-amber-200 dark:border-amber-900',     hover: 'hover:border-amber-300 dark:hover:border-amber-700',     chip: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300' },
};

function ModuloCard({ modulo, expanded, onToggle }) {
    const Icono = modulo.icono;
    const c = COLOR_MAP[modulo.color];

    return (
        <div className={`bg-white dark:bg-slate-900 rounded-2xl border ${c.border} ${c.hover} transition-all overflow-hidden`}>
            <button
                onClick={onToggle}
                className="w-full text-left p-5 flex items-start gap-4"
            >
                <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${c.bg} ${c.text}`}>
                    <Icono size={20} />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">{modulo.nombre}</h3>
                        <span className={`text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded ${c.chip}`}>
                            {modulo.estado}
                        </span>
                    </div>
                    <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{modulo.resumen}</p>
                </div>
                <ArrowRight
                    size={16}
                    className={`text-slate-300 dark:text-slate-600 shrink-0 mt-2 transition-transform duration-300 ${expanded ? 'rotate-90' : ''}`}
                />
            </button>

            {expanded && (
                <div className="px-5 pb-5 pl-20 animate-in fade-in slide-in-from-top-1 duration-300">
                    <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed mb-4">{modulo.descripcion}</p>
                    <div>
                        <div className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Ideas iniciales</div>
                        <ul className="space-y-1.5">
                            {modulo.ideas.map((idea, i) => (
                                <li key={i} className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300">
                                    <span className={`mt-1.5 w-1 h-1 rounded-full shrink-0 ${c.text} bg-current opacity-60`} />
                                    {idea}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <button className="mt-4 inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                        <MessageCircle size={13} />
                        Conversar este módulo
                    </button>
                </div>
            )}
        </div>
    );
}

export default function LiveTracking() {
    const [openId, setOpenId] = useState(null);

    return (
        <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
            {/* Header sobrio */}
            <div className="space-y-1">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-slate-100 dark:bg-slate-800 rounded-xl flex items-center justify-center text-slate-500 dark:text-slate-400">
                        <Sparkles size={18} />
                    </div>
                    <h1 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight">Próximos módulos</h1>
                </div>
                <p className="text-slate-400 dark:text-slate-500 text-sm font-medium pl-12">
                    Borrador de lo que viene. Conversemos cada uno para ir armando el mapa.
                </p>
            </div>

            {/* Nota de contexto */}
            <div className="flex items-start gap-3 px-4 py-3 bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 rounded-xl">
                <Construction size={16} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                <p className="text-xs text-amber-800 dark:text-amber-200 leading-relaxed">
                    Esta sección es un espacio de exploración — todavía no hay nada implementado.
                    Sirve para discutir alcance y prioridades antes de codear.
                </p>
            </div>

            {/* Módulos */}
            <div className="space-y-3">
                {MODULOS.map(m => (
                    <ModuloCard
                        key={m.id}
                        modulo={m}
                        expanded={openId === m.id}
                        onToggle={() => setOpenId(openId === m.id ? null : m.id)}
                    />
                ))}
            </div>

            {/* Pie sobrio */}
            <div className="text-center pt-4">
                <p className="text-xs text-slate-400 dark:text-slate-600">
                    ¿Falta algún módulo en esta lista? Lo agregamos.
                </p>
            </div>
        </div>
    );
}
