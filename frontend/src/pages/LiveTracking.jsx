import { useState } from 'react';
import {
    Sparkles, Newspaper, GraduationCap, UserCog, BookOpen,
    ArrowRight, MessageCircle, Construction, Check
} from 'lucide-react';

// ════════════════════════════════════════════════════════════════════════════
//   "Próximos módulos" — landing comercial
//   Placeholder. Sin lógica activa. Cada card vende un módulo del roadmap
//   con tono producto: tagline, propuesta de valor y features concretos.
//   El detalle técnico se conversa por separado.
// ════════════════════════════════════════════════════════════════════════════

const MODULOS = [
    {
        id: 'noticias',
        nombre: 'Módulo Noticias',
        tagline: 'Tu newsroom escolar — las historias detrás de los números.',
        icono: Newspaper,
        color: 'indigo',
        resumen: 'Cada vez que subes una evaluación, el sistema te cuenta qué cambió. En frases que entiende cualquiera.',
        descripcion:
            'Pensado para que UTP reciba un brief semanal de 5 frases y sepa, sin abrir Excel, ' +
            'qué cursos subieron, cuáles requieren atención y qué brechas se cerraron. Convierte los datos ' +
            'en un relato que se puede leer en el café de la mañana.',
        features: [
            'Titulares automáticos por curso después de cada lectura',
            'Detección de alertas tempranas sin que nadie tenga que mirar',
            'Resumen ejecutivo semanal listo para WhatsApp o correo',
        ],
        estado: 'En diseño',
    },
    {
        id: 'estudiantes',
        nombre: 'Módulo Estudiantes',
        tagline: 'Cada estudiante, una historia completa. En un solo lugar.',
        icono: GraduationCap,
        color: 'violet',
        resumen: 'La trayectoria de cada estudiante a través de todas las evaluaciones, sin tener que cruzar planillas.',
        descripcion:
            'Pasa del "promedio del curso" a la mirada individual. Encuentra rápido a quien necesita apoyo, ' +
            'celebra a quien remontó, y llega preparado a la reunión con apoderados con la ficha impresa ' +
            'y los datos correctos.',
        features: [
            'Ficha 360° por estudiante con línea de tiempo de evaluaciones',
            'Comparativo individual vs. promedio de curso por subprueba',
            'Detección automática de estudiantes en riesgo',
            'Exportable a PDF para reunión con apoderado',
        ],
        estado: 'En diseño',
    },
    {
        id: 'profesor',
        nombre: 'Panel Profesor',
        tagline: 'Cada profesor, su propio dashboard. Sin distracciones.',
        icono: UserCog,
        color: 'emerald',
        resumen: 'Una vista pensada para el docente — solo su curso, los KPIs que le sirven, las acciones de la próxima clase.',
        descripcion:
            'El profesor entra y ve únicamente lo suyo: su curso, su asignatura, sus estudiantes priorizados. ' +
            'Recibe sugerencias concretas sobre dónde poner el foco la próxima semana y puede planificar ' +
            'basado en datos sin tener que aprender a usar un BI.',
        features: [
            'Acceso restringido por curso/asignatura',
            'Vista simplificada: 3 KPIs + tabla de estudiantes priorizados',
            'Recomendaciones de foco por subprueba y por semana',
            'Sin jerga técnica — diseñado para uso diario en sala',
        ],
        estado: 'En diseño',
    },
    {
        id: 'cobertura',
        nombre: 'Seguimiento Cobertura Curricular',
        tagline: 'Tu mapa curricular en tiempo real — lo que enseñas vs. lo que rinde.',
        icono: BookOpen,
        color: 'amber',
        resumen: 'Cruza el avance real del plan anual con los resultados de evaluaciones para descubrir dónde están los gaps.',
        descripcion:
            'Por primera vez podrás responder con datos: "¿Los OAs que vimos esta unidad realmente se aprendieron?". ' +
            'Visualiza el avance contra el plan MINEDUC, detecta contenidos pendientes y conecta cobertura con ' +
            'resultados para tomar decisiones pedagógicas con evidencia.',
        features: [
            'Catálogo de OAs MINEDUC por nivel y asignatura',
            'Registro periódico de avance con un par de clicks',
            'Alertas de OAs sin cubrir cerca del cierre de unidad',
            'Cruce cobertura × resultados para medir efectividad real',
            'Reporte UTP exportable a fin de mes',
        ],
        estado: 'En diseño',
    },
];

const COLOR_MAP = {
    indigo:  { bg: 'bg-indigo-50 dark:bg-indigo-950/40',   text: 'text-indigo-700 dark:text-indigo-300',   border: 'border-indigo-200 dark:border-indigo-900',   hover: 'hover:border-indigo-300 dark:hover:border-indigo-700',   chip: 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300',   accent: 'text-indigo-500 dark:text-indigo-400' },
    violet:  { bg: 'bg-violet-50 dark:bg-violet-950/40',   text: 'text-violet-700 dark:text-violet-300',   border: 'border-violet-200 dark:border-violet-900',   hover: 'hover:border-violet-300 dark:hover:border-violet-700',   chip: 'bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300',   accent: 'text-violet-500 dark:text-violet-400' },
    emerald: { bg: 'bg-emerald-50 dark:bg-emerald-950/40', text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-200 dark:border-emerald-900', hover: 'hover:border-emerald-300 dark:hover:border-emerald-700', chip: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300', accent: 'text-emerald-500 dark:text-emerald-400' },
    amber:   { bg: 'bg-amber-50 dark:bg-amber-950/40',     text: 'text-amber-700 dark:text-amber-300',     border: 'border-amber-200 dark:border-amber-900',     hover: 'hover:border-amber-300 dark:hover:border-amber-700',     chip: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300',     accent: 'text-amber-500 dark:text-amber-400' },
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
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${c.bg} ${c.text}`}>
                    <Icono size={22} />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">{modulo.nombre}</h3>
                        <span className={`text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded ${c.chip}`}>
                            {modulo.estado}
                        </span>
                    </div>
                    <p className={`text-sm font-medium ${c.accent} mb-1.5`}>{modulo.tagline}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{modulo.resumen}</p>
                </div>
                <ArrowRight
                    size={16}
                    className={`text-slate-300 dark:text-slate-600 shrink-0 mt-2 transition-transform duration-300 ${expanded ? 'rotate-90' : ''}`}
                />
            </button>

            {expanded && (
                <div className="px-5 pb-5 pl-[5.25rem] animate-in fade-in slide-in-from-top-1 duration-300">
                    <div className="border-t border-slate-100 dark:border-slate-800 pt-4 mb-4">
                        <div className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">La propuesta</div>
                        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{modulo.descripcion}</p>
                    </div>
                    <div>
                        <div className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Qué incluirá</div>
                        <ul className="space-y-2">
                            {modulo.features.map((feat, i) => (
                                <li key={i} className="flex items-start gap-2.5 text-sm text-slate-600 dark:text-slate-300">
                                    <span className={`mt-0.5 w-4 h-4 rounded-full flex items-center justify-center shrink-0 ${c.bg}`}>
                                        <Check size={10} className={c.text} />
                                    </span>
                                    {feat}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <button className="mt-5 inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
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
                    Lo que viene en el roadmap. Hacé click en cada uno para ver la propuesta.
                </p>
            </div>

            {/* Nota de contexto */}
            <div className="flex items-start gap-3 px-4 py-3 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl">
                <Construction size={16} className="text-slate-400 shrink-0 mt-0.5" />
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                    Vista previa de funcionalidades en desarrollo. Las descripciones son la dirección de producto;
                    el alcance final se afina en conversación.
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
                    ¿Falta algún módulo? Lo agregamos al roadmap.
                </p>
            </div>
        </div>
    );
}
