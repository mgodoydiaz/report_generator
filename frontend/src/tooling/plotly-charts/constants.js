// ── Paleta de niveles de logro ──

const DEFAULT_LEVEL_PALETTE_DATA = [
    // PDL / IDEL-Woodcock
    { name: 'Crítico',       order: 1, color: '#dc2626' },
    { name: 'Critico',       order: 1, color: '#dc2626' },
    { name: 'Alto Riesgo',   order: 2, color: '#ea580c' },
    { name: 'Cierto Riesgo', order: 3, color: '#eab308' },
    { name: 'Bajo Riesgo',   order: 4, color: '#16a34a' },
    // SIMCE
    { name: 'Insuficiente',  order: 1, color: '#e76f51' },
    { name: 'Elemental',     order: 2, color: '#e9c46a' },
    { name: 'Adecuado',      order: 3, color: '#2a9d8f' },
    // DIA — Diagnóstico Integral de Aprendizajes
    { name: 'Inicial',       order: 1, color: '#e76f51' },
    { name: 'Intermedio',    order: 2, color: '#e9c46a' },
    { name: 'Avanzado',      order: 3, color: '#2a9d8f' },
    // Cálculo Veloz / Fluidez — 5 niveles ascendentes (mayúsculas como vienen en DB)
    { name: 'INICIAL',       order: 1, color: '#dc2626' },
    { name: 'BÁSICO',        order: 2, color: '#ea580c' },
    { name: 'INTERMEDIO',    order: 3, color: '#eab308' },
    { name: 'AVANZADO',      order: 4, color: '#65a30d' },
    { name: 'EXPERTO',       order: 5, color: '#16a34a' },
];

/**
 * Construye una paleta a partir de achievement_levels del indicador.
 * Soporta: [{name, color, order}], string[], undefined/[].
 * Retorna: { orderedNames, colorByName, ordByName }
 */
export function getLevelPalette(achievementLevels) {
    const defaults = {
        orderedNames: ['Crítico', 'Alto Riesgo', 'Cierto Riesgo', 'Bajo Riesgo'],
        colorByName: Object.fromEntries(DEFAULT_LEVEL_PALETTE_DATA.map(l => [l.name, l.color])),
        ordByName:   Object.fromEntries(DEFAULT_LEVEL_PALETTE_DATA.map(l => [l.name, l.order])),
    };
    if (!achievementLevels?.length) return defaults;

    if (typeof achievementLevels[0] === 'object' && achievementLevels[0]?.name) {
        const sorted = [...achievementLevels].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
        const colorByName = {};
        const ordByName   = {};
        for (const l of sorted) {
            colorByName[l.name] = l.color ?? defaults.colorByName[l.name] ?? '#94a3b8';
            ordByName[l.name]   = l.order;
        }
        return { orderedNames: sorted.map(l => l.name), colorByName, ordByName };
    }

    if (typeof achievementLevels[0] === 'string') {
        const colorByName = {};
        const ordByName   = {};
        achievementLevels.forEach((name, i) => {
            colorByName[name] = defaults.colorByName[name] ?? '#94a3b8';
            ordByName[name]   = i + 1;
        });
        return { orderedNames: achievementLevels, colorByName, ordByName };
    }

    return defaults;
}

// ── Paletas de colores ──

export const CATEGORY_COLORS = [
    "#4361ee", "#7209b7", "#f72585", "#4cc9f0",
    "#06d6a0", "#ffd166", "#118ab2", "#073b4c",
];

// Legacy alias
export const CURSO_COLORS = CATEGORY_COLORS;

export const LOGRO_COLORS = {
    Adecuado: "#2a9d8f",
    Elemental: "#e9c46a",
    Insuficiente: "#e76f51",
};

// ── Helpers ──

export const avg = (arr, key) =>
    arr.length ? arr.reduce((s, r) => s + r[key], 0) / arr.length : 0;

/**
 * Formatea un valor numérico según un string de formato "F.X".
 *   F = '%'  → multiplica por 100, toFixed(X), agrega '%'   ej. "45.3%"
 *   F = '#'  → número decimal,  toFixed(X)                  ej. "220" / "3.14"
 *   F = 'T'  → texto, devuelve el valor como string          ej. "0.87"
 * Sin formato (undefined/null) → comportamiento legacy: pct (porcentaje redondeado)
 */
export const formatValue = (value, formatStr) => {
    if (value == null || value === '') return '—';
    if (!formatStr) return `${Math.round(value * 100)}%`;

    const dotIdx = formatStr.indexOf('.');
    const F = dotIdx >= 0 ? formatStr.slice(0, dotIdx) : formatStr;
    const X = dotIdx >= 0 ? parseInt(formatStr.slice(dotIdx + 1), 10) : 0;
    const decimals = isNaN(X) ? 0 : X;

    if (F === 'T') return String(value);
    if (F === '#') return Number(value).toFixed(decimals);
    if (F === '%') return `${Number(value * 100).toFixed(decimals)}%`;

    return `${Math.round(value * 100)}%`;
};

/**
 * Retorna el rango del eje Y según el string de formato.
 *   '%' → datos en rango 0-1 → [0, 1]
 *   '#' o 'T' o sin formato → [0, null] (auto)
 */
export const formatRange = (formatStr) => {
    if (!formatStr) return [0, 1];
    const F = formatStr.split('.')[0];
    return F === '%' ? [0, 1] : [0, null];
};

/**
 * Genera colores HSL distribuidos uniformemente para N niveles.
 * Verde → Amarillo → Rojo (hue 120 → 0)
 */
export const levelColors = (levels) =>
    levels.map((_, i) => {
        const hue = Math.round((i / Math.max(1, levels.length - 1)) * 120);
        return `hsl(${hue}, 70%, 50%)`;
    });

/**
 * Convierte un string a Title Case respetando el formato canónico que ya
 * tienen los datos en BD. Equivalente a Python `str.title()`:
 *   - "INTERPRETAR" → "Interpretar"
 *   - "interpretar y relacionar" → "Interpretar Y Relacionar"
 *
 * Reemplaza el patrón legacy `s.charAt(0).toUpperCase() + s.slice(1).toLowerCase()`
 * que sólo capitalizaba la primera letra y forzaba el resto en lowercase,
 * destruyendo el title case que ya viene normalizado desde el backend.
 */
export const titleCase = (s) => {
    if (s == null) return "—";
    const str = String(s).trim();
    if (!str) return "—";
    return str.replace(/\w\S*/g, (w) =>
        w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()
    );
};

// ── A11y (S5.3) ──────────────────────────────────────────────────────────────
// Emojis prefijo por nivel para reforzar la identidad visual sin depender
// exclusivamente del color (usuarios daltónicos y stakeholders). Se aplica
// a las etiquetas de leyenda y a los ticks de ejes categóricos.
export const LEVEL_EMOJI = {
    'Crítico':       '🔴',
    'Critico':       '🔴',
    'Alto Riesgo':   '🟠',
    'Cierto Riesgo': '🟡',
    'Bajo Riesgo':   '🟢',
    'Insuficiente':  '🔴',
    'Elemental':     '🟡',
    'Adecuado':      '🟢',
    // DIA
    'Inicial':       '🔴',
    'Intermedio':    '🟡',
    'Avanzado':      '🟢',
    // Cálculo Veloz
    'INICIAL':       '🔴',
    'BÁSICO':        '🟠',
    'INTERMEDIO':    '🟡',
    'AVANZADO':      '🟢',
    'EXPERTO':       '🟢',
};

export function levelLabelWithEmoji(name) {
    if (!name) return name;
    const e = LEVEL_EMOJI[name];
    return e ? `${e} ${name}` : name;
}

// Patrones Plotly para diferenciar series apiladas sin color (daltonismo).
// Índice = posición del nivel en la paleta ordenada.
export const LEVEL_PATTERN_SHAPES = ['', '/', '\\\\', 'x', '.'];
