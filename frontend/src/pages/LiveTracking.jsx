import { useEffect, useState, useRef } from 'react';
import {
    Radio, TrendingUp, TrendingDown, Sparkles, Lock, Calendar, Users,
    AlertTriangle, ArrowUpRight, Clock, Zap, ArrowRight
} from 'lucide-react';

// ════════════════════════════════════════════════════════════════════════════
//   "Seguimiento en vivo" — placeholder marketing
//   Diseño orientado a transmitir movimiento con elementos calmos:
//   - Hero rotativo (fade lento, una idea a la vez)
//   - Ticker continuo de eventos
//   - KPIs con count-up al montar
//   - Carrete de noticias con auto-avance + dots
//   - Card de próxima lectura con countdown vivo
//   Sin ruido visual: paleta sobria, animaciones lentas, una sola atención.
// ════════════════════════════════════════════════════════════════════════════

const HERO_FRASES = [
    { tag: 'II° A',  texto: 'pasó de alto riesgo a bajo riesgo', sub: '14 estudiantes salieron del cuartil crítico', tono: 'positivo' },
    { tag: '5° B',   texto: '+8 puntos en Lectura este hito',     sub: 'Mejora sostenida desde la lectura anterior', tono: 'positivo' },
    { tag: 'III° B', texto: 'redujo a la mitad la brecha de género', sub: 'En Matemáticas, diferencia M-F bajó de 12 a 6', tono: 'positivo' },
    { tag: '7° C',   texto: 'requiere atención en Resolución de problemas', sub: '3 estudiantes retrocedieron a insuficiente', tono: 'alerta' },
    { tag: '4° A',   texto: 'avanzó 1 nivel completo en DIA Lectura',  sub: '22 de 28 estudiantes lograron el nivel esperado', tono: 'positivo' },
];

const TICKER = [
    { curso: 'II° A',  msg: 'riesgo · Alto → Bajo', tono: 'up' },
    { curso: '5° B',   msg: 'Lectura · +8 pts',     tono: 'up' },
    { curso: '7° C',   msg: 'Matemáticas · 3 alertas', tono: 'down' },
    { curso: 'III° B', msg: 'Brecha género · −50%', tono: 'up' },
    { curso: '4° A',   msg: 'DIA · +1 nivel',       tono: 'up' },
    { curso: '6° A',   msg: 'IDEL · meta cumplida',  tono: 'up' },
    { curso: '1° B',   msg: 'Velocidad lectora · +12 ppm', tono: 'up' },
    { curso: 'II° C',  msg: 'asistencia evaluación · 96%', tono: 'up' },
];

const NOTICIAS = [
    { curso: 'II° A',  titulo: 'Pasó de alto riesgo a bajo riesgo', detalle: '14 estudiantes salieron del cuartil crítico tras la última lectura.', delta: '+14',  tono: 'positivo' },
    { curso: '5° B',   titulo: 'Mejora sostenida en Lectura',       detalle: '+8 puntos promedio respecto al hito anterior.',                       delta: '+8 pts', tono: 'positivo' },
    { curso: '7° C',   titulo: 'Caída en Resolución de problemas',  detalle: '3 estudiantes retrocedieron a nivel insuficiente.',                   delta: '−3',     tono: 'alerta' },
    { curso: 'III° B', titulo: 'Brecha de género se redujo a la mitad', detalle: 'Diferencia M-F bajó de 12 a 6 puntos en Matemáticas.',           delta: '−50%',   tono: 'positivo' },
    { curso: '4° A',   titulo: 'Avanzó un nivel completo en DIA',   detalle: '22 de 28 estudiantes alcanzaron el nivel esperado.',                 delta: '79%',    tono: 'positivo' },
];

const KPIS = [
    { label: 'Estudiantes con mejora este mes', valor: 127,  sufijo: '',   sub: '+18% vs. mes anterior',         icono: TrendingUp,    color: 'emerald' },
    { label: 'Cursos en alerta',                 valor: 4,    sufijo: '',   sub: '2 menos que hace una semana',   icono: AlertTriangle, color: 'amber'   },
    { label: 'Estudiantes monitoreados',         valor: 1842, sufijo: '',   sub: '23 cursos · 4 evaluaciones',    icono: Users,         color: 'sky'     },
    { label: 'Lecturas procesadas',              valor: 38,   sufijo: '',   sub: 'últimos 30 días',               icono: Zap,           color: 'violet'  },
];

const PROXIMAS_LECTURAS = [
    { fecha: '12 may', evaluacion: 'DIA Matemáticas',    cobertura: '6 cursos · 312 estudiantes' },
    { fecha: '19 may', evaluacion: 'IDEL — cierre ciclo', cobertura: '2 cursos · 84 estudiantes'  },
    { fecha: '02 jun', evaluacion: 'SIMCE Lectura ensayo', cobertura: '4 cursos · 178 estudiantes' },
];

// ── Hooks utilitarios ──────────────────────────────────────────────────────

function useInterval(callback, delay) {
    const saved = useRef(callback);
    useEffect(() => { saved.current = callback; }, [callback]);
    useEffect(() => {
        if (delay == null) return;
        const id = setInterval(() => saved.current(), delay);
        return () => clearInterval(id);
    }, [delay]);
}

// Conteo animado al montar — easing suave, ~1.4s
function useCountUp(target, duration = 1400) {
    const [val, setVal] = useState(0);
    useEffect(() => {
        const start = performance.now();
        let raf;
        const tick = (now) => {
            const t = Math.min(1, (now - start) / duration);
            const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
            setVal(Math.round(target * eased));
            if (t < 1) raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(raf);
    }, [target, duration]);
    return val;
}

function formatNumber(n) {
    return new Intl.NumberFormat('es-CL').format(n);
}

// ── Componentes ────────────────────────────────────────────────────────────

function Hero() {
    const [idx, setIdx] = useState(0);
    useInterval(() => setIdx(i => (i + 1) % HERO_FRASES.length), 4500);
    const f = HERO_FRASES[idx];
    const isPos = f.tono === 'positivo';

    return (
        <div className="relative bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 overflow-hidden">
            {/* Gradiente animado de fondo */}
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-50 via-white to-violet-50 dark:from-indigo-950/40 dark:via-slate-900 dark:to-violet-950/40" />
            <div className="absolute -top-32 -right-32 w-96 h-96 bg-indigo-200/40 dark:bg-indigo-700/15 rounded-full blur-3xl animate-lt-drift" />
            <div className="absolute -bottom-32 -left-32 w-96 h-96 bg-violet-200/40 dark:bg-violet-700/15 rounded-full blur-3xl animate-lt-drift-rev" />

            <div className="relative px-8 py-10 md:py-12 min-h-[260px] flex flex-col justify-center">
                {/* Eyebrow vivo */}
                <div className="flex items-center gap-2 mb-5">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                    </span>
                    <span className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500 dark:text-slate-400">
                        Última lectura · hace 2 h
                    </span>
                </div>

                {/* Frase rotativa con crossfade */}
                <div key={idx} className="animate-lt-fadeup">
                    <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2 mb-3">
                        <span className={`inline-flex items-center gap-1.5 text-xs font-black uppercase tracking-widest px-3 py-1 rounded-full border ${
                            isPos
                                ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900'
                                : 'bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-900'
                        }`}>
                            {isPos ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                            {f.tag}
                        </span>
                    </div>
                    <h2 className="text-3xl md:text-5xl font-black text-slate-800 dark:text-white tracking-tight leading-[1.1] mb-3 max-w-3xl">
                        {f.texto}
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400 text-base md:text-lg max-w-2xl">
                        {f.sub}
                    </p>
                </div>

                {/* Indicadores de slide */}
                <div className="flex gap-1.5 mt-7">
                    {HERO_FRASES.map((_, i) => (
                        <button
                            key={i}
                            onClick={() => setIdx(i)}
                            aria-label={`Ir a noticia ${i + 1}`}
                            className={`h-1 rounded-full transition-all duration-500 ${
                                i === idx ? 'w-8 bg-indigo-600 dark:bg-indigo-400' : 'w-1.5 bg-slate-300 dark:bg-slate-700 hover:bg-slate-400'
                            }`}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}

function Ticker() {
    // duplicamos para loop seamless
    const items = [...TICKER, ...TICKER];
    return (
        <div className="relative bg-slate-900 dark:bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden group">
            <div className="absolute left-0 top-0 bottom-0 w-16 bg-gradient-to-r from-slate-900 dark:from-slate-950 to-transparent z-10 pointer-events-none" />
            <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-slate-900 dark:from-slate-950 to-transparent z-10 pointer-events-none" />
            <div className="absolute left-3 top-1/2 -translate-y-1/2 z-20 flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/30 px-2 py-1 rounded-md">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[9px] font-black uppercase tracking-widest text-emerald-300">Live</span>
            </div>
            <div className="flex animate-lt-marquee group-hover:[animation-play-state:paused] py-3 pl-24">
                {items.map((it, i) => {
                    const up = it.tono === 'up';
                    const Icono = up ? TrendingUp : TrendingDown;
                    return (
                        <div key={i} className="flex items-center gap-2 px-6 shrink-0 border-r border-slate-800/60">
                            <Icono size={14} className={up ? 'text-emerald-400' : 'text-amber-400'} />
                            <span className="text-[11px] font-black uppercase tracking-widest text-slate-400">{it.curso}</span>
                            <span className="text-sm font-medium text-slate-100">{it.msg}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function KpiCard({ label, valor, sufijo, sub, icono: Icono, color }) {
    const palette = {
        emerald: { ico: 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10', halo: 'from-emerald-500/0 via-emerald-500/40 to-emerald-500/0' },
        amber:   { ico: 'text-amber-600 dark:text-amber-400 bg-amber-500/10',       halo: 'from-amber-500/0 via-amber-500/40 to-amber-500/0' },
        sky:     { ico: 'text-sky-600 dark:text-sky-400 bg-sky-500/10',             halo: 'from-sky-500/0 via-sky-500/40 to-sky-500/0' },
        violet:  { ico: 'text-violet-600 dark:text-violet-400 bg-violet-500/10',    halo: 'from-violet-500/0 via-violet-500/40 to-violet-500/0' },
    }[color];
    const animado = useCountUp(valor);
    return (
        <div className="relative bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 overflow-hidden hover:border-slate-300 dark:hover:border-slate-700 transition-colors">
            {/* Línea superior con shimmer */}
            <div className={`absolute top-0 left-0 right-0 h-px bg-gradient-to-r ${palette.halo} animate-lt-shimmer`} />
            <div className="flex items-start justify-between mb-3">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">{label}</span>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${palette.ico}`}>
                    <Icono size={15} />
                </div>
            </div>
            <div className="text-3xl md:text-4xl font-black text-slate-800 dark:text-white tracking-tight tabular-nums">
                {formatNumber(animado)}{sufijo}
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-1.5">{sub}</div>
        </div>
    );
}

function Carrete() {
    const [idx, setIdx] = useState(0);
    const [paused, setPaused] = useState(false);
    useInterval(() => { if (!paused) setIdx(i => (i + 1) % NOTICIAS.length); }, 5000);

    // tres tarjetas visibles a la vez (en md+); en mobile, una
    const total = NOTICIAS.length;
    return (
        <div onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
            <div className="flex items-end justify-between mb-3">
                <div className="flex items-center gap-2">
                    <Sparkles size={16} className="text-indigo-500" />
                    <h2 className="text-sm font-black text-slate-700 dark:text-slate-200 uppercase tracking-widest">Noticias del día</h2>
                </div>
                <div className="flex gap-1.5">
                    {NOTICIAS.map((_, i) => (
                        <button
                            key={i}
                            onClick={() => setIdx(i)}
                            aria-label={`Ir a noticia ${i + 1}`}
                            className={`h-1.5 rounded-full transition-all duration-500 ${
                                i === idx ? 'w-6 bg-indigo-600 dark:bg-indigo-400' : 'w-1.5 bg-slate-300 dark:bg-slate-700'
                            }`}
                        />
                    ))}
                </div>
            </div>
            <div className="overflow-hidden">
                <div
                    className="flex gap-4 transition-transform duration-700 ease-[cubic-bezier(0.65,0,0.35,1)]"
                    style={{ transform: `translateX(calc(${-idx * 100}% / 3 - ${idx} * 1rem / 3))` }}
                >
                    {NOTICIAS.map((n, i) => {
                        const isPos = n.tono === 'positivo';
                        const Icono = isPos ? TrendingUp : TrendingDown;
                        const active = i === idx;
                        return (
                            <article
                                key={i}
                                className={`shrink-0 w-full md:w-[calc((100%-2rem)/3)] bg-white dark:bg-slate-900 rounded-2xl border p-5 transition-all duration-500 ${
                                    active
                                        ? 'border-indigo-200 dark:border-indigo-800 shadow-lg shadow-indigo-100/50 dark:shadow-indigo-950/20 scale-100'
                                        : 'border-slate-200 dark:border-slate-800 scale-[0.98] opacity-80'
                                }`}
                            >
                                <div className="flex items-start justify-between mb-3">
                                    <span className={`inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-widest px-2 py-1 rounded-md border ${
                                        isPos
                                            ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900'
                                            : 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-900'
                                    }`}>
                                        <Icono size={11} />
                                        {n.curso}
                                    </span>
                                    <span className={`text-xs font-black tabular-nums ${
                                        isPos ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'
                                    }`}>
                                        {n.delta}
                                    </span>
                                </div>
                                <h3 className="text-base font-bold text-slate-800 dark:text-slate-100 leading-snug mb-2">{n.titulo}</h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{n.detalle}</p>
                            </article>
                        );
                    })}
                </div>
            </div>
            <div className="text-[10px] text-slate-400 dark:text-slate-600 mt-3 flex items-center gap-1.5">
                <span className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-700" />
                avanza solo · pausa al pasar el cursor · {idx + 1} de {total}
            </div>
        </div>
    );
}

function ProximaLectura() {
    // countdown sintético hacia 12 may
    const [tick, setTick] = useState(0);
    useInterval(() => setTick(t => t + 1), 1000);
    const target = new Date('2026-05-12T08:00:00').getTime();
    const ms = Math.max(0, target - Date.now());
    const dd = Math.floor(ms / 86400000);
    const hh = Math.floor((ms % 86400000) / 3600000);
    const mm = Math.floor((ms % 3600000) / 60000);
    const ss = Math.floor((ms % 60000) / 1000);

    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Clock size={16} className="text-indigo-500" />
                    <h2 className="text-sm font-black text-slate-700 dark:text-slate-200 uppercase tracking-widest">Próximas lecturas</h2>
                </div>
                <div className="hidden md:flex items-baseline gap-1.5 text-xs font-medium text-slate-400">
                    <span>siguiente en</span>
                    <span className="tabular-nums font-black text-slate-700 dark:text-slate-200">
                        {dd}d {String(hh).padStart(2, '0')}:{String(mm).padStart(2, '0')}:{String(ss).padStart(2, '0')}
                    </span>
                </div>
            </div>
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {PROXIMAS_LECTURAS.map((l, i) => {
                    const [num, mes] = l.fecha.split(' ');
                    return (
                        <div key={i} className="px-6 py-4 flex items-center gap-4 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                            <div className={`w-14 h-14 rounded-xl flex flex-col items-center justify-center shrink-0 ${
                                i === 0
                                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200 dark:shadow-indigo-900/30'
                                    : 'bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300'
                            }`}>
                                <span className="text-[10px] font-bold uppercase tracking-widest opacity-70">{mes}</span>
                                <span className="text-lg font-black leading-none">{num}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                                    {l.evaluacion}
                                    {i === 0 && (
                                        <span className="inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-widest text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/40 px-1.5 py-0.5 rounded">
                                            <span className="w-1 h-1 rounded-full bg-indigo-500 animate-pulse" />
                                            próxima
                                        </span>
                                    )}
                                </h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{l.cobertura}</p>
                            </div>
                            <ArrowRight size={16} className="text-slate-300 dark:text-slate-600 shrink-0" />
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ── Página ─────────────────────────────────────────────────────────────────

export default function LiveTracking() {
    return (
        <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
            {/* Animaciones locales */}
            <style>{`
                @keyframes lt-marquee { from { transform: translateX(0); } to { transform: translateX(-50%); } }
                @keyframes lt-fadeup  { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                @keyframes lt-shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
                @keyframes lt-drift     { 0%,100% { transform: translate(0,0); } 50% { transform: translate(20px,-20px); } }
                @keyframes lt-drift-rev { 0%,100% { transform: translate(0,0); } 50% { transform: translate(-20px,20px); } }
                .animate-lt-marquee   { animation: lt-marquee 38s linear infinite; width: max-content; }
                .animate-lt-fadeup    { animation: lt-fadeup 700ms cubic-bezier(0.16,1,0.3,1) both; }
                .animate-lt-shimmer   { background-size: 200% 100%; animation: lt-shimmer 4s ease-in-out infinite; }
                .animate-lt-drift     { animation: lt-drift 14s ease-in-out infinite; }
                .animate-lt-drift-rev { animation: lt-drift-rev 16s ease-in-out infinite; }
                @media (prefers-reduced-motion: reduce) {
                    .animate-lt-marquee, .animate-lt-fadeup, .animate-lt-shimmer,
                    .animate-lt-drift, .animate-lt-drift-rev { animation: none !important; }
                }
            `}</style>

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div className="space-y-1">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-100 dark:shadow-indigo-900/30 relative">
                            <Radio size={22} />
                            <span className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full ring-2 ring-white dark:ring-slate-950 animate-pulse" />
                        </div>
                        <h1 className="text-4xl font-black text-slate-800 dark:text-white tracking-tight">Seguimiento en vivo</h1>
                        <span className="hidden md:inline-block text-[10px] font-black uppercase tracking-widest px-2 py-1 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 text-white">
                            Próximamente
                        </span>
                    </div>
                    <p className="text-slate-400 dark:text-slate-500 text-sm font-medium pl-13">
                        El pulso de tus datos. Cada lectura cuenta su historia.
                    </p>
                </div>
            </div>

            {/* Hero rotativo */}
            <Hero />

            {/* Ticker */}
            <Ticker />

            {/* KPIs */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {KPIS.map((k, i) => <KpiCard key={i} {...k} />)}
            </div>

            {/* Carrete de noticias */}
            <Carrete />

            {/* Próxima lectura */}
            <ProximaLectura />

            {/* CTA "Próximamente" — invitación silenciosa */}
            <div className="bg-gradient-to-br from-indigo-50 via-white to-violet-50 dark:from-indigo-950/30 dark:via-slate-900 dark:to-violet-950/30 rounded-3xl border border-indigo-100 dark:border-indigo-900/40 p-8 text-center relative overflow-hidden">
                <div className="absolute top-0 right-0 -mr-20 -mt-20 w-64 h-64 bg-indigo-200/40 dark:bg-indigo-700/10 rounded-full blur-3xl animate-lt-drift" />
                <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-64 h-64 bg-violet-200/40 dark:bg-violet-700/10 rounded-full blur-3xl animate-lt-drift-rev" />
                <div className="relative">
                    <div className="w-12 h-12 bg-white dark:bg-slate-900 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-sm border border-indigo-100 dark:border-indigo-900/40">
                        <Lock size={20} className="text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <h3 className="text-lg font-black text-slate-800 dark:text-white mb-2">Esto es solo una vista previa</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto leading-relaxed mb-5">
                        Pronto, cada vez que subas un informe, esta vista se actualizará sola con las historias detrás de los datos.
                    </p>
                    <button className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-indigo-700 dark:text-indigo-300 hover:gap-2 transition-all">
                        Quiero saber cuando esté listo
                        <ArrowUpRight size={14} />
                    </button>
                </div>
            </div>
        </div>
    );
}
