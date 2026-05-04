/**
 * microcopy.js — helpers determinísticos (sin IA) para texto interpretativo
 * debajo de cada chart. Cada fn recibe los records procesados y devuelve un
 * string corto en español. Retorna null si no hay datos suficientes.
 */

function pct(n) {
    if (n == null || Number.isNaN(n)) return '—';
    return `${Math.round(n * 100)}%`;
}

// Niveles "críticos" históricamente hardcodeados (SIMCE/DIA usan estos nombres
// canónicos). Para indicadores con niveles distintos (FL: MUY BAJA/BAJA/MEDIA/
// ALTA, IDEL: niveles propios), si se pasa `achievementLevels` resolvemos el
// set crítico dinámicamente como los 1-2 peores niveles del array (el orden
// del array en el indicator es de peor → mejor por convención).
const FALLBACK_CRITICAL = new Set(['Crítico', 'Critico', 'Alto Riesgo']);

function resolveCriticalSet(achievementLevels) {
    if (!Array.isArray(achievementLevels) || achievementLevels.length === 0) {
        return { set: FALLBACK_CRITICAL, label: 'Crítico+Alto' };
    }
    const names = achievementLevels
        .map(l => typeof l === 'string' ? l : (l?.name || ''))
        .filter(Boolean);
    if (!names.length) return { set: FALLBACK_CRITICAL, label: 'Crítico+Alto' };
    // Tomar los peores: si "No Aplica" está al final, usarlo NO como crítico.
    // Tomar los primeros 1-2 niveles (los del array vienen de peor a mejor).
    // Si hay 5+ niveles, tomar 2; si hay 3-4, tomar 2; si 2, tomar 1.
    const totalReal = names.filter(n => n.toLowerCase() !== 'no aplica').length;
    const k = totalReal >= 4 ? 2 : 1;
    const critical = names.slice(0, k);
    return { set: new Set(critical), label: critical.join('+') };
}

// ── StackedCountByGroup ──────────────────────────────────────────────────────
// Señala el grupo con más y menos estudiantes en los niveles peores del indicador.
export function microcopyStackedLevels(records, opts = {}) {
    const { groupField = '_curso', levelField = '_logro' } = opts;
    if (!Array.isArray(records) || records.length === 0) return null;
    const { set: CRITICAL, label: critLabel } = resolveCriticalSet(
        opts.achievement_levels || opts.achievementLevels  // soportar ambos nombres
    );
    const byGroup = new Map();
    for (const r of records) {
        const g = r[groupField];
        if (!g) continue;
        if (!byGroup.has(g)) byGroup.set(g, { n: 0, crit: 0 });
        const b = byGroup.get(g);
        b.n += 1;
        if (CRITICAL.has(r[levelField])) b.crit += 1;
    }
    if (byGroup.size < 2) return null;
    const rows = [...byGroup.entries()].map(([g, b]) => ({ g, n: b.n, pct: b.n ? b.crit / b.n : 0, crit: b.crit }));
    rows.sort((a, b) => b.pct - a.pct);
    const top = rows[0];
    const bottom = rows[rows.length - 1];
    return `Grupo con mayor concentración en ${critLabel}: ${top.g} — ${top.crit} estudiantes (${pct(top.pct)}). Más saludable: ${bottom.g} (${pct(bottom.pct)}).`;
}

// ── HeatmapMatrix ────────────────────────────────────────────────────────────
export function microcopyHeatmap(records, opts = {}) {
    const { xField, yField, valueField = '_is_concerning' } = opts;
    if (!Array.isArray(records) || records.length === 0 || !xField || !yField) return null;
    const { label: critLabel } = resolveCriticalSet(
        opts.achievement_levels || opts.achievementLevels
    );
    const buckets = new Map();
    for (const r of records) {
        const x = r[xField], y = r[yField];
        if (x == null || y == null) continue;
        const k = `${y}||${x}`;
        if (!buckets.has(k)) buckets.set(k, { x, y, n: 0, truthy: 0 });
        const b = buckets.get(k);
        b.n += 1;
        if (r[valueField]) b.truthy += 1;
    }
    if (buckets.size === 0) return null;
    const rows = [...buckets.values()].map(b => ({ ...b, pct: b.n ? b.truthy / b.n : 0 }));
    rows.sort((a, b) => b.pct - a.pct);
    const worst = rows[0];
    return `Combinación más crítica: ${worst.y} × ${worst.x} — ${pct(worst.pct)} en ${critLabel} (${worst.truthy} estudiantes).`;
}

// ── ImprovementRateByGroup ───────────────────────────────────────────────────
export function microcopyImprovement(records, { groupField = '_curso', entityField = '_rut', levelField = '_logro', timeField = '_evaluacion_num', achievementLevels = [] } = {}) {
    if (!Array.isArray(records) || records.length === 0) return null;
    const order = new Map();
    achievementLevels.forEach((l, i) => {
        const name = typeof l === 'string' ? l : l?.name;
        const ord = typeof l === 'string' ? i + 1 : (l?.order ?? i + 1);
        if (name) order.set(name, ord);
    });
    if (order.size === 0) return null;

    const byEntity = new Map();
    for (const r of records) {
        const key = `${r[groupField] ?? ''}||${r[entityField] ?? ''}`;
        if (!r[entityField]) continue;
        if (!byEntity.has(key)) byEntity.set(key, []);
        byEntity.get(key).push(r);
    }
    let improved = 0, complete = 0;
    const byGroup = new Map();
    for (const [, rs] of byEntity) {
        const ordered = rs.filter(r => r[timeField] != null).sort((a, b) => Number(a[timeField]) - Number(b[timeField]));
        if (ordered.length < 2) continue;
        const first = order.get(ordered[0][levelField]);
        const last  = order.get(ordered[ordered.length - 1][levelField]);
        if (first == null || last == null) continue;
        complete += 1;
        const g = ordered[0][groupField] ?? '—';
        if (!byGroup.has(g)) byGroup.set(g, { n: 0, imp: 0 });
        byGroup.get(g).n += 1;
        if (last > first) { improved += 1; byGroup.get(g).imp += 1; }
    }
    if (complete === 0) return null;
    const overallPct = improved / complete;
    let best = null;
    for (const [g, b] of byGroup) {
        const p = b.n ? b.imp / b.n : 0;
        if (!best || p > best.pct) best = { g, pct: p, imp: b.imp, n: b.n };
    }
    return `${pct(overallPct)} de los estudiantes con trayectoria completa mejoró de nivel. Grupo líder: ${best.g} con ${pct(best.pct)}.`;
}

// ── TransitionMatrix (Sankey) ────────────────────────────────────────────────
export function microcopyTransition(records, { entityField = '_rut', levelField = '_worst_level_label', timeField = '_evaluacion_num' } = {}) {
    if (!Array.isArray(records) || records.length === 0) return null;
    const byEntity = new Map();
    for (const r of records) {
        if (!r[entityField]) continue;
        if (!byEntity.has(r[entityField])) byEntity.set(r[entityField], []);
        byEntity.get(r[entityField]).push(r);
    }
    let first = null, last = null;
    for (const rs of byEntity.values()) {
        for (const r of rs) {
            const t = Number(r[timeField]);
            if (Number.isNaN(t)) continue;
            if (first == null || t < first) first = t;
            if (last == null  || t > last)  last  = t;
        }
    }
    if (first == null || last == null || first === last) return null;

    const CRITICAL = 'Crítico';
    let inCritStart = 0, exitedCrit = 0;
    for (const rs of byEntity.values()) {
        const rsFirst = rs.find(r => Number(r[timeField]) === first);
        const rsLast  = rs.find(r => Number(r[timeField]) === last);
        if (!rsFirst || !rsLast) continue;
        if (rsFirst[levelField] === CRITICAL) {
            inCritStart += 1;
            if (rsLast[levelField] !== CRITICAL) exitedCrit += 1;
        }
    }
    if (inCritStart === 0) return null;
    return `De los ${inCritStart} estudiantes en Crítico al inicio, ${exitedCrit} salieron del nivel al final del período.`;
}

// Router: dado un componentId, devuelve la función correspondiente (o null).
export function microcopyFor(componentId) {
    switch (componentId) {
        case 'StackedCountByGroup':
        case 'StackedCountByGroupAndPeriod':
            return microcopyStackedLevels;
        case 'HeatmapMatrix':
            return microcopyHeatmap;
        case 'ImprovementRateByGroup':
            return microcopyImprovement;
        case 'TransitionMatrix':
            return microcopyTransition;
        default:
            return null;
    }
}
