import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
    X, FileText, FileType, Loader2, Download, SlidersHorizontal,
    CalendarClock, CalendarDays, CalendarRange, CalendarCog, BookOpen,
} from 'lucide-react';
import { API_BASE_URL } from '../constants';
import { useAuth } from '../context/AuthContext';
import MultiSelectFilters from './MultiSelectFilters';

/**
 * Selector unificado de tipo de informe.
 *
 * Consulta GET /api/indicators/{id}/report-options. La respuesta trae los
 * informes agrupados en `grupos`:
 *   - `grupos.periodo`      → informes del período (última prueba, semestral,
 *                             anual, personalizado). Motor weasyprint; el
 *                             layout lo decide el backend a partir de `periodo`.
 *   - `grupos.especializados` → informes con motor propio (registry `custom`,
 *                             Word/docxtpl, v2, …).
 *
 * Compatibilidad: si la respuesta NO trae `grupos` (backend anterior), se
 * renderiza la lista plana `opciones` igual que antes.
 *
 * Dos acciones por card:
 *   - Clic principal → onSelect(op, 'quick', extras): descarga directa con la
 *     configuración guardada (encabezados del último uso o defaults).
 *   - Botón "Personalizar" → onSelect(op, 'custom', extras): abre el modal
 *     para editar encabezados / nombre de archivo antes de descargar.
 *
 * `extras.periodo` viaja hacia Results:
 *   - cards de período   → `op.periodo` tal cual
 *   - "Informe Personalizado" → {tipo:'personalizado', fecha_inicio?, fecha_fin?, filtros?}
 *     armado en el panel inline (filtros por NOMBRE de dimensión).
 *
 * ── Asignatura obligatoria ─────────────────────────────────────────────
 * Una card puede declarar:
 *     "asignatura": {requerida: true, dimension: "Asignatura",
 *                    valores: ["LECTURA", "MATEMATICA"]}
 * El backend exige que esa dimensión quede fijada a EXACTAMENTE 1 valor en
 * los filtros efectivos (responde 400 en caso contrario). Aquí:
 *   - Si los filtros del dashboard (`initialFilters`) ya la fijan a 1 valor,
 *     se hereda y se muestra como chip informativo ("Asignatura: LECTURA")
 *     con opción de cambiarla.
 *   - Si hay 0 o ≥2 valores, la card muestra un selector obligatorio y las
 *     acciones de descarga quedan deshabilitadas hasta que haya selección.
 * La selección es única por modal (mismo indicador → misma dimensión) y viaja
 * en `extras.periodo.filtros[dimension] = [valor]` (cards de período) o en
 * `extras.filtrosExtra = {dimension: valor}` (cards sin período).
 *
 * Fallback: cards sin `asignatura` → cero cambios de UI ni de payload.
 */

// ─────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────

function iconFor(op) {
    if (op?.requiere_configuracion) return CalendarCog;
    const tipo = op?.periodo?.tipo;
    if (tipo === 'ultima_prueba') return CalendarClock;
    if (tipo === 'semestral') return CalendarRange;
    if (tipo === 'anual') return CalendarDays;
    if (tipo === 'personalizado') return CalendarCog;
    return op?.formato === 'word' ? FileType : FileText;
}

/** Normaliza {nombre: valor|valores} → {nombre: [valores]} descartando vacíos. */
function normalizeFiltrosPorNombre(raw, allowedNames = null) {
    const out = {};
    Object.entries(raw || {}).forEach(([name, v]) => {
        if (allowedNames && allowedNames.length && !allowedNames.includes(name)) return;
        const arr = (Array.isArray(v) ? v : [v])
            .filter((x) => x !== null && x !== undefined && x !== '')
            .map(String);
        if (arr.length) out[name] = arr;
    });
    return out;
}

/** Devuelve el spec de asignatura de una card sólo si es exigible. */
function specAsignatura(op) {
    const spec = op?.asignatura;
    if (!spec || typeof spec !== 'object') return null;
    if (!spec.requerida) return null;
    if (!spec.dimension) return null;
    return spec;
}

// ─────────────────────────────────────────────────────────────────────────
// Card de opción de informe
// ─────────────────────────────────────────────────────────────────────────

function ReportOptionCard({
    op,
    onMainClick,
    onCustomize,
    expanded = false,
    blocked = false,          // acciones deshabilitadas por requisito pendiente
    blockedTooltip = '',
    footer = null,            // bloque siempre visible bajo la fila (ej. asignatura)
    children,
}) {
    const Icon = iconFor(op);
    const disponible = op.disponible !== false;
    const bloqueado = disponible && blocked;
    const esWord = op.formato === 'word';

    return (
        <div
            className={`w-full rounded-2xl border-2 transition-all ${
                !disponible
                    ? 'border-slate-50 dark:border-slate-800/50 opacity-50'
                    : expanded
                        ? 'border-indigo-400 bg-indigo-50/40 dark:bg-slate-800/60'
                        : 'border-slate-100 dark:border-slate-800 hover:border-indigo-400 hover:bg-indigo-50/50 dark:hover:bg-slate-800'
            }`}
        >
            <div className="flex items-center gap-3 p-4">
                {/* Zona principal: descarga en un clic (o expande, en Personalizado) */}
                <button
                    type="button"
                    disabled={!disponible || (bloqueado && !op.requiere_configuracion)}
                    aria-expanded={op.requiere_configuracion ? expanded : undefined}
                    onClick={onMainClick}
                    title={
                        !disponible
                            ? (op.motivo_no_disponible || 'No disponible')
                            : bloqueado && !op.requiere_configuracion
                                ? (blockedTooltip || 'Falta completar un dato obligatorio')
                                : op.requiere_configuracion
                                    ? 'Configurar el período y los filtros del informe'
                                    : 'Descargar con la configuración guardada'
                    }
                    className={`flex-1 flex items-center gap-4 text-left min-w-0 ${
                        !disponible || (bloqueado && !op.requiere_configuracion)
                            ? 'cursor-not-allowed'
                            : 'cursor-pointer'
                    }`}
                >
                    <div className={`p-2.5 rounded-xl shrink-0 ${esWord ? 'bg-emerald-50 dark:bg-emerald-900/20' : 'bg-indigo-50 dark:bg-indigo-900/20'}`}>
                        <Icon size={18} className={esWord ? 'text-emerald-600 dark:text-emerald-400' : 'text-indigo-600 dark:text-indigo-400'} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="font-semibold text-sm text-slate-800 dark:text-slate-100">{op.label}</p>
                        <p className="text-xs text-slate-400 mt-0.5">
                            {disponible
                                ? (op.requiere_configuracion
                                    ? (op.descripcion || 'Elige el rango de fechas y los filtros del informe.')
                                    : op.descripcion)
                                : op.motivo_no_disponible}
                        </p>
                    </div>
                    {disponible && !op.requiere_configuracion && (
                        <Download size={16} className={`shrink-0 ${bloqueado ? 'text-slate-300 dark:text-slate-600' : 'text-indigo-400'}`} />
                    )}
                    {disponible && op.requiere_configuracion && (
                        <SlidersHorizontal size={16} className={`shrink-0 ${expanded ? 'text-indigo-600' : 'text-indigo-400'}`} />
                    )}
                </button>

                {/* Acción secundaria: editar encabezados / nombre de archivo */}
                {disponible && !op.requiere_configuracion && onCustomize && (
                    <button
                        type="button"
                        disabled={bloqueado}
                        onClick={onCustomize}
                        aria-label={`Personalizar ${op.label}`}
                        title={bloqueado
                            ? (blockedTooltip || 'Falta completar un dato obligatorio')
                            : 'Personalizar encabezados y nombre de archivo antes de descargar'}
                        className="p-2.5 rounded-xl text-slate-400 hover:text-indigo-600 hover:bg-indigo-100/60 dark:hover:bg-slate-700 disabled:text-slate-300 dark:disabled:text-slate-600 disabled:hover:bg-transparent disabled:cursor-not-allowed transition-all shrink-0"
                    >
                        <SlidersHorizontal size={16} />
                    </button>
                )}
            </div>

            {/* Requisitos siempre visibles (ej. selector de asignatura) */}
            {disponible && footer && (
                <div className="px-4 pb-4 -mt-1">{footer}</div>
            )}

            {/* Panel inline (Informe Personalizado) */}
            {expanded && children && (
                <div className="px-4 pb-4">{children}</div>
            )}
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────
// Modal
// ─────────────────────────────────────────────────────────────────────────

export default function ReportSelectorModal({
    open,
    onClose,
    indicatorId,
    onSelect,
    initialFilters,   // opcional: {nombre_dimension: valor|valores} — prefill del panel Personalizado
}) {
    const { fetchAuth } = useAuth();
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);

    // Panel inline del informe personalizado
    const [customOpen, setCustomOpen] = useState(false);
    const [customFilters, setCustomFilters] = useState({});   // {nombreDim: [vals]}
    const [fechaInicio, setFechaInicio] = useState('');
    const [fechaFin, setFechaFin] = useState('');

    // Asignatura obligatoria — selección única para todo el modal
    const [asignatura, setAsignatura] = useState(null);
    const [cambiandoAsignatura, setCambiandoAsignatura] = useState(false);

    // Ref para no meter `initialFilters` (objeto nuevo en cada render del padre)
    // en las dependencias de los efectos.
    const initialFiltersRef = useRef(initialFilters);
    initialFiltersRef.current = initialFilters;

    // ── Carga del catálogo ──
    useEffect(() => {
        if (!open || !indicatorId) return;
        setData(null);
        setError(null);
        setCustomOpen(false);
        setFechaInicio('');
        setFechaFin('');
        setAsignatura(null);
        setCambiandoAsignatura(false);
        let active = true;
        (async () => {
            try {
                const resp = await fetchAuth(`${API_BASE_URL}/indicators/${indicatorId}/report-options`);
                const payload = await resp.json();
                if (!resp.ok) throw new Error(payload?.detail || 'No se pudieron cargar los informes disponibles');
                if (active) setData(payload);
            } catch (err) {
                if (active) setError(err.message);
            }
        })();
        return () => { active = false; };
    }, [open, indicatorId]);

    // ── Cierre con Escape ──
    useEffect(() => {
        if (!open) return;
        const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [open, onClose]);

    // ── Dimensiones filtrables del informe personalizado ──
    // MultiSelectFilters usa keys opacas: aquí las keys son los NOMBRES de
    // dimensión, que es justo el formato que espera `periodo.filtros`.
    const dimsFiltrables = useMemo(() => {
        const arr = Array.isArray(data?.dimensiones_filtrables) ? data.dimensiones_filtrables : [];
        const dimensions = {};
        const order = [];
        arr.forEach((d) => {
            const name = d?.name;
            if (!name || dimensions[name]) return;
            dimensions[name] = {
                name,
                values: (Array.isArray(d.values) ? d.values : []).map(String),
            };
            order.push(name);
        });
        return { dimensions, order };
    }, [data]);

    // ── Prefill de filtros con los del dashboard ──
    // Sólo se conservan los nombres que el backend declara filtrables, para
    // no arrastrar filtros invisibles (sin dropdown) al payload.
    useEffect(() => {
        if (!open) return;
        if (!data || dimsFiltrables.order.length === 0) {
            setCustomFilters({});
            return;
        }
        setCustomFilters(normalizeFiltrosPorNombre(initialFiltersRef.current, dimsFiltrables.order));
    }, [open, data, dimsFiltrables]);

    const filtrosPersonalizados = useMemo(
        () => normalizeFiltrosPorNombre(customFilters),
        [customFilters]
    );

    // ── Asignatura obligatoria ──
    // Todas las cards que la exigen comparten dimensión (mismo indicador), así
    // que basta el primer spec encontrado para derivar el valor heredado y el
    // catálogo de valores.
    const asignaturaSpec = useMemo(() => {
        if (!data) return null;
        const listas = [
            Array.isArray(data?.grupos?.periodo) ? data.grupos.periodo : [],
            Array.isArray(data?.grupos?.especializados) ? data.grupos.especializados : [],
            Array.isArray(data?.opciones) ? data.opciones : [],
        ];
        for (const lista of listas) {
            for (const op of lista) {
                const spec = specAsignatura(op);
                if (spec) return spec;
            }
        }
        return null;
    }, [data]);

    // Valores ofrecibles: los del contrato; si el backend no los manda, se
    // recuperan del catálogo de dimensiones filtrables.
    const asignaturaValores = useMemo(() => {
        if (!asignaturaSpec) return [];
        const declarados = (Array.isArray(asignaturaSpec.valores) ? asignaturaSpec.valores : [])
            .filter((v) => v !== null && v !== undefined && v !== '')
            .map(String);
        if (declarados.length) return declarados;
        return dimsFiltrables.dimensions[asignaturaSpec.dimension]?.values || [];
    }, [asignaturaSpec, dimsFiltrables]);

    // Valor heredado del dashboard: sólo cuenta si acota a EXACTAMENTE 1 valor.
    const asignaturaHeredada = useMemo(() => {
        if (!open || !asignaturaSpec) return null;
        const vals = normalizeFiltrosPorNombre(initialFiltersRef.current)[asignaturaSpec.dimension];
        return Array.isArray(vals) && vals.length === 1 ? vals[0] : null;
    }, [open, asignaturaSpec]);

    // Prefill con el valor heredado.
    useEffect(() => {
        if (!open) return;
        setAsignatura(asignaturaHeredada || null);
        setCambiandoAsignatura(false);
    }, [open, asignaturaHeredada]);

    // El panel del informe personalizado manda: si fija la dimensión a 1 valor,
    // el selector se sincroniza con él.
    useEffect(() => {
        const dim = asignaturaSpec?.dimension;
        if (!dim) return;
        const vals = filtrosPersonalizados[dim];
        if (Array.isArray(vals) && vals.length === 1 && vals[0] !== asignatura) {
            setAsignatura(vals[0]);
            setCambiandoAsignatura(false);
        }
    }, [filtrosPersonalizados, asignaturaSpec, asignatura]);

    // Elegir asignatura: se refleja también en el panel personalizado cuando esa
    // dimensión es filtrable, para que ambos controles digan lo mismo.
    const elegirAsignatura = (valor) => {
        setAsignatura(valor);
        setCambiandoAsignatura(false);
        const dim = asignaturaSpec?.dimension;
        if (dim && dimsFiltrables.dimensions[dim]) {
            setCustomFilters((prev) => ({ ...prev, [dim]: [valor] }));
        }
    };

    // Una card está bloqueada si exige asignatura, no hay valor elegido y
    // tenemos valores que ofrecer. Sin catálogo de valores no bloqueamos: el
    // backend responderá 400 con un detalle accionable.
    const asignaturaPendiente = (op) =>
        !!specAsignatura(op) && !asignatura && asignaturaValores.length > 0;

    const rangoInvalido = !!(fechaInicio && fechaFin && fechaInicio > fechaFin);

    const buildPeriodoPersonalizado = () => ({
        tipo: 'personalizado',
        ...(fechaInicio ? { fecha_inicio: fechaInicio } : {}),
        ...(fechaFin ? { fecha_fin: fechaFin } : {}),
        ...(Object.keys(filtrosPersonalizados).length ? { filtros: filtrosPersonalizados } : {}),
    });

    // ── Despacho al padre ──
    const emit = (op, mode) => {
        const spec = specAsignatura(op);
        // Guardia: no emitir sin asignatura cuando la card la exige y hay
        // valores disponibles (los botones ya están deshabilitados en ese caso).
        if (spec && !asignatura && asignaturaValores.length > 0) return;

        const extras = {};
        let periodo = null;
        if (op?.requiere_configuracion) periodo = buildPeriodoPersonalizado();
        else if (op?.periodo) periodo = op.periodo;

        if (spec && asignatura) {
            const dim = spec.dimension;
            // Filtros extra por NOMBRE de dimensión: Results los fusiona sobre los
            // del dashboard. Van SIEMPRE para que la dimensión quede acotada a un
            // solo valor también en `filters`, y no sólo en `periodo.filtros`
            // (los filtros efectivos del backend son la unión de ambos).
            extras.filtrosExtra = { [dim]: asignatura };
            if (periodo) {
                // Cards de período: además viaja dentro de periodo.filtros.
                periodo = {
                    ...periodo,
                    filtros: { ...(periodo.filtros || {}), [dim]: [asignatura] },
                };
            }
        }

        if (periodo) extras.periodo = periodo;
        onSelect?.(op, mode, extras);
    };

    const handleMainClick = (op) => {
        if (op?.requiere_configuracion) {
            setCustomOpen((v) => !v);
            return;
        }
        emit(op, 'quick');
    };

    // Bloque de asignatura de una card: chip informativo o selector obligatorio.
    const renderAsignatura = (op) => {
        const spec = specAsignatura(op);
        if (!spec) return null;
        if (op.disponible === false) return null;

        const etiqueta = spec.dimension || 'Asignatura';
        const mostrarSelector = !asignatura || cambiandoAsignatura;

        if (!asignaturaValores.length) {
            return (
                <p className="text-[11px] text-amber-600 dark:text-amber-400">
                    Este informe requiere fijar <strong>{etiqueta}</strong> a un solo valor en los filtros del dashboard.
                </p>
            );
        }

        if (!mostrarSelector) {
            return (
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-100 dark:border-indigo-900/50 text-[11px] font-semibold text-indigo-700 dark:text-indigo-300">
                        <BookOpen size={11} />
                        {etiqueta}: {asignatura}
                    </span>
                    <button
                        type="button"
                        onClick={() => setCambiandoAsignatura(true)}
                        className="text-[11px] font-semibold text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400"
                    >
                        Cambiar
                    </button>
                </div>
            );
        }

        return (
            <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
                    {etiqueta} del informe <span className="text-rose-500">*</span>
                </p>
                <div className="flex flex-wrap gap-1.5">
                    {asignaturaValores.map((v) => (
                        <button
                            key={v}
                            type="button"
                            aria-pressed={asignatura === v}
                            onClick={() => elegirAsignatura(v)}
                            className={`px-3 py-1.5 rounded-xl text-[11px] font-semibold border transition-all ${
                                asignatura === v
                                    ? 'bg-indigo-600 border-indigo-600 text-white shadow-sm'
                                    : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-400'
                            }`}
                        >
                            {v}
                        </button>
                    ))}
                    {asignatura && cambiandoAsignatura && (
                        <button
                            type="button"
                            onClick={() => setCambiandoAsignatura(false)}
                            className="px-2 py-1.5 text-[11px] font-semibold text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                        >
                            Cancelar
                        </button>
                    )}
                </div>
                {!asignatura && (
                    <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-1.5">
                        Elige una asignatura para poder descargar este informe.
                    </p>
                )}
            </div>
        );
    };

    if (!open) return null;

    // ── Agrupación (con fallback a lista plana) ──
    const grupos = data && data.grupos && typeof data.grupos === 'object' ? data.grupos : null;
    const periodoOps = Array.isArray(grupos?.periodo) ? grupos.periodo : [];
    const especialOps = Array.isArray(grupos?.especializados) ? grupos.especializados : [];
    const usarGrupos = !!grupos && (periodoOps.length + especialOps.length) > 0;
    const flatOps = Array.isArray(data?.opciones) ? data.opciones : [];
    const totalOps = usarGrupos ? periodoOps.length + especialOps.length : flatOps.length;

    const renderCard = (op) => {
        const bloqueado = asignaturaPendiente(op);
        return (
        <ReportOptionCard
            key={op.id}
            op={op}
            expanded={!!op.requiere_configuracion && customOpen}
            blocked={bloqueado}
            blockedTooltip="Elige una asignatura"
            footer={renderAsignatura(op)}
            onMainClick={() => handleMainClick(op)}
            // Los motores del registry `custom` no tienen modal de encabezados
            // propio: esas cards sólo descargan.
            onCustomize={op.motor === 'custom' ? null : () => emit(op, 'custom')}
        >
            {op.requiere_configuracion && (
                <div className="pt-3 border-t border-indigo-100 dark:border-slate-700 space-y-4">
                    {/* Filtros por dimensión */}
                    <div>
                        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                            Filtros del informe
                        </p>
                        {dimsFiltrables.order.length > 0 ? (
                            <MultiSelectFilters
                                compact
                                dimensions={dimsFiltrables.dimensions}
                                sortedDimIds={dimsFiltrables.order}
                                value={customFilters}
                                onChange={setCustomFilters}
                            />
                        ) : (
                            <p className="text-xs text-slate-400 italic">
                                Este indicador no declara dimensiones filtrables.
                            </p>
                        )}
                    </div>

                    {/* Rango de fechas */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                                Rango de fechas (opcional)
                            </p>
                            {(fechaInicio || fechaFin) && (
                                <button
                                    type="button"
                                    onClick={() => { setFechaInicio(''); setFechaFin(''); }}
                                    className="text-[11px] font-semibold text-slate-500 hover:text-rose-600 inline-flex items-center gap-1"
                                >
                                    <X size={11} /> Limpiar
                                </button>
                            )}
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            <label className="block">
                                <span className="block text-[10px] uppercase font-semibold text-slate-500 dark:text-slate-400 mb-1">Desde</span>
                                <input
                                    type="month"
                                    value={fechaInicio}
                                    onChange={(e) => setFechaInicio(e.target.value)}
                                    className="w-full text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                />
                            </label>
                            <label className="block">
                                <span className="block text-[10px] uppercase font-semibold text-slate-500 dark:text-slate-400 mb-1">Hasta</span>
                                <input
                                    type="month"
                                    value={fechaFin}
                                    onChange={(e) => setFechaFin(e.target.value)}
                                    className="w-full text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                />
                            </label>
                        </div>
                        {rangoInvalido && (
                            <p className="text-[11px] text-rose-500 mt-1.5">
                                «Desde» debe ser anterior o igual a «Hasta».
                            </p>
                        )}
                        {!fechaInicio && !fechaFin && (
                            <p className="text-[11px] text-slate-400 mt-1.5">
                                Sin rango, el informe usa todo el período disponible según los filtros.
                            </p>
                        )}
                    </div>

                    {/* Acciones */}
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                        <button
                            type="button"
                            disabled={rangoInvalido || bloqueado}
                            title={bloqueado ? 'Elige una asignatura' : undefined}
                            onClick={() => emit(op, 'quick')}
                            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 disabled:cursor-not-allowed shadow-sm transition-all"
                        >
                            <Download size={14} />
                            Descargar
                        </button>
                        <button
                            type="button"
                            disabled={rangoInvalido || bloqueado}
                            title={bloqueado ? 'Elige una asignatura' : undefined}
                            onClick={() => emit(op, 'custom')}
                            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        >
                            <SlidersHorizontal size={14} />
                            Personalizar encabezados
                        </button>
                    </div>
                </div>
            )}
        </ReportOptionCard>
        );
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" onClick={onClose} />
            <div
                role="dialog"
                aria-modal="true"
                aria-label="Generar informe"
                className="relative w-full max-w-xl bg-white dark:bg-slate-900 rounded-3xl shadow-2xl p-6 max-h-[85vh] overflow-y-auto"
            >
                <div className="flex items-center justify-between mb-5">
                    <h3 className="font-bold text-slate-800 dark:text-slate-100">Generar informe</h3>
                    <button
                        onClick={onClose}
                        aria-label="Cerrar"
                        className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-xl transition-all"
                    >
                        <X size={18} />
                    </button>
                </div>

                {error && (
                    <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">
                        {error}
                    </div>
                )}

                {!data && !error && (
                    <div className="flex justify-center py-10">
                        <Loader2 size={22} className="animate-spin text-indigo-400" />
                    </div>
                )}

                {data && !error && (
                    <div className="space-y-6">
                        {usarGrupos ? (
                            <>
                                {periodoOps.length > 0 && (
                                    <section className="space-y-2">
                                        <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
                                            Informes del período
                                        </p>
                                        {periodoOps.map(renderCard)}
                                    </section>
                                )}
                                {especialOps.length > 0 && (
                                    <section className="space-y-2">
                                        <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
                                            Informes especializados
                                        </p>
                                        {especialOps.map(renderCard)}
                                    </section>
                                )}
                            </>
                        ) : (
                            <div className="space-y-2">
                                {flatOps.map(renderCard)}
                            </div>
                        )}

                        {totalOps === 0 && (
                            <p className="text-sm text-slate-400 text-center py-6">
                                Este indicador aún no tiene informes configurados.
                            </p>
                        )}
                        {totalOps > 0 && (
                            <p className="text-[11px] text-slate-400 text-center pt-1">
                                Un clic descarga el informe · <SlidersHorizontal size={11} className="inline -mt-0.5" /> para personalizar títulos y archivo
                            </p>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
