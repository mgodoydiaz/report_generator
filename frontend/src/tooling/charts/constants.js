// ── Paletas de colores ──

export const LOGRO_COLORS = {
    Adecuado: "#2a9d8f",
    Elemental: "#e9c46a",
    Insuficiente: "#e76f51",
};

export const CURSO_COLORS = [
    "#4361ee", "#7209b7", "#f72585", "#4cc9f0",
    "#06d6a0", "#ffd166", "#118ab2", "#073b4c",
];

// ── Helpers ──

export const pct = (v) => `${Math.round(v * 100)}%`;
export const avg = (arr, key) =>
    arr.length ? arr.reduce((s, r) => s + r[key], 0) / arr.length : 0;

/**
 * Convierte un string a Title Case respetando el formato canónico que ya
 * tienen los datos en BD. Equivalente a Python `str.title()`:
 *   - "INTERPRETAR" → "Interpretar"
 *   - "interpretar"  → "Interpretar"
 *   - "Interpretar Y Relacionar" → "Interpretar Y Relacionar"
 *   - "interpretar y relacionar" → "Interpretar Y Relacionar"
 *
 * Reemplaza el patrón legacy `s.charAt(0).toUpperCase() + s.slice(1).toLowerCase()`
 * que sólo capitalizaba la primera letra y forzaba lowercase en el resto,
 * lo cual destruía el title case que ya viene normalizado desde el backend.
 *
 * Para valores vacíos o null devuelve "—".
 */
export const titleCase = (s) => {
    if (s == null) return "—";
    const str = String(s).trim();
    if (!str) return "—";
    return str.replace(/\w\S*/g, (w) =>
        w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()
    );
};

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
 * Retorna el dominio del eje Y de recharts según el string de formato.
 *   '%' → datos en rango 0-1 → [0, 1]
 *   '#' o 'T' o sin formato → [0, 'auto']
 */
export const formatDomain = (formatStr) => {
    if (!formatStr) return [0, 1];
    const F = formatStr.split('.')[0];
    return F === '%' ? [0, 1] : [0, 'auto'];
};
