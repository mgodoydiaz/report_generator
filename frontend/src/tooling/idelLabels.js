/**
 * Etiquetas largas de subpruebas IDEL Woodcock.
 *
 * En la base de datos las subpruebas se guardan como siglas (CT, FLO, FNL,
 * FSF, ILP, VSD) — eso permite filtros, joins y comparaciones rápidas. Para
 * la UI, mostramos también el nombre legible solicitado por la fundación
 * (ver feedback del cliente 2026-05-06: "CT debería decir Comprensión de
 * Textos").
 *
 * Dos formatos:
 *   - long:  "Comprensión de Textos"
 *   - short: "CT · Comprensión de Textos"  (para selectores donde la sigla
 *            sigue siendo útil para identificar rápido)
 *
 * Si la sigla no está en el mapping (caso futuro o data inesperada),
 * `getSubpruebaLabel` devuelve el raw sin alterar, así no rompe charts ni
 * filtros que dependan del valor original.
 */

export const IDEL_SUBPRUEBA_LABELS = {
  CT:  'Comprensión de Textos',
  FLO: 'Fluidez Lectora',
  FNL: 'Segmentación Fonémica',
  FSF: 'Fluidez Silábica/Fonémica',
  ILP: 'Identificación de Letras y Palabras',
  VSD: 'Vocabulario sobre Dibujo',
};

/**
 * Devuelve la etiqueta legible para un valor de subprueba.
 * @param {string} raw - sigla cruda (ej "CT")
 * @param {'long'|'short_with_long'|'short'} mode
 * @returns {string}
 */
export function getSubpruebaLabel(raw, mode = 'long') {
  if (raw == null) return '';
  const long = IDEL_SUBPRUEBA_LABELS[raw];
  if (!long) return String(raw);
  if (mode === 'short') return raw;
  if (mode === 'short_with_long') return `${raw} · ${long}`;
  return long;
}

/**
 * Aplica getSubpruebaLabel a una lista, preservando orden y valores no
 * mapeados. Útil para transformar `dataset.x` antes de pasarlo a Plotly.
 */
export function mapSubpruebaLabels(values, mode = 'long') {
  if (!Array.isArray(values)) return values;
  return values.map((v) => getSubpruebaLabel(v, mode));
}
