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
