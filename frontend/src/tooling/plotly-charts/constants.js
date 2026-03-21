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
