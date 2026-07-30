/**
 * valuesFilters — lógica pura de los filtros de la página /values.
 *
 * La tabla de valores usa paginación de servidor (hasta ~25k filas por
 * métrica), así que TODO el filtrado ocurre en el backend dentro de la
 * query paginada. Este módulo solo arma los query params y normaliza el
 * estado — sin React, sin fetch — para poder testearlo aparte.
 *
 * Contrato con `GET /api/metrics/{id}/data`:
 *   filters = JSON urlencoded {"<id_dimension>": ["valor", ...]}
 *   q       = texto libre (case-insensitive) sobre valor + dimensiones
 *
 * Contrato con `GET /api/metrics/{id}/data/facets`:
 *   {"<id_dimension>": {name: "Curso", values: ["1 A", ...]}}
 */

/** Estado inicial (y de reseteo) de los filtros por dimensión. */
export const FILTROS_VACIOS = {};

/**
 * Quita dimensiones sin valores seleccionados.
 * @param {Object<string, string[]>} filtros
 * @returns {Object<string, string[]>}
 */
export function normalizarFiltros(filtros) {
    const out = {};
    Object.entries(filtros || {}).forEach(([dimId, vals]) => {
        if (Array.isArray(vals) && vals.length > 0) {
            out[String(dimId)] = vals.map(String);
        }
    });
    return out;
}

/** ¿Hay algún filtro por dimensión o búsqueda activa? */
export function hayFiltroActivo(filtros, q) {
    return Object.keys(normalizarFiltros(filtros)).length > 0 || Boolean((q || '').trim());
}

/** Cantidad total de valores seleccionados (para el badge del botón). */
export function contarFiltros(filtros) {
    return Object.values(normalizarFiltros(filtros)).reduce((acc, vals) => acc + vals.length, 0);
}

/**
 * Arma el querystring de `GET /api/metrics/{id}/data`.
 *
 * Omite `filters` y `q` cuando no hay nada activo, para que la llamada sea
 * byte a byte la histórica (hay consumidores que dependen de eso).
 *
 * @returns {string} querystring SIN el '?' inicial
 */
export function construirParamsDatos({
    page = 1,
    pageSize = 50,
    includeAudit = false,
    filtros = FILTROS_VACIOS,
    q = '',
} = {}) {
    const params = new URLSearchParams();
    params.set('page', String(page));
    params.set('page_size', String(pageSize));
    if (includeAudit) params.set('include_audit', 'true');

    const limpios = normalizarFiltros(filtros);
    if (Object.keys(limpios).length > 0) params.set('filters', JSON.stringify(limpios));

    const texto = (q || '').trim();
    if (texto) params.set('q', texto);

    return params.toString();
}

/**
 * Normaliza la respuesta de facets al shape que espera MultiSelectFilters:
 * `{ [dimId]: { name, values } }`.
 */
export function facetsADimensiones(facets) {
    const out = {};
    Object.entries(facets || {}).forEach(([dimId, meta]) => {
        if (!meta) return;
        const values = Array.isArray(meta.values) ? meta.values.map(String) : [];
        out[String(dimId)] = { name: meta.name || `Dim_${dimId}`, values };
    });
    return out;
}

/**
 * Orden de los dropdowns: primero las dimensiones declaradas por la métrica
 * (en su orden), después cualquier otra presente solo en los datos.
 *
 * Necesario porque las claves de facets son numéricas y un objeto JS las
 * reordena de forma ascendente, perdiendo el orden que mandó el backend.
 */
export function ordenarDimIds(metric, facets) {
    const presentes = Object.keys(facets || {}).map(String);
    const declaradas = (metric?.dimension_ids || []).map(String).filter((d) => presentes.includes(d));
    const extras = presentes.filter((d) => !declaradas.includes(d)).sort();
    return [...declaradas, ...extras];
}

/**
 * ¿Hay que resetear los filtros al pasar de `metricAnterior` a `metricNueva`?
 * Los ids de dimensión no son comparables entre métricas distintas, así que
 * cualquier cambio de métrica limpia el estado.
 */
export function debeResetearFiltros(metricAnterior, metricNueva) {
    const a = metricAnterior?.id_metric ?? null;
    const b = metricNueva?.id_metric ?? null;
    return a !== b;
}

/** Texto del contador de registros del toolbar. */
export function textoContador({ total = 0, totalSinFiltro = null, rangeStart = 0, rangeEnd = 0, filtroActivo = false }) {
    if (total === 0) return filtroActivo ? '0 registros (filtrado)' : '0 registros';
    const base = `${rangeStart}–${rangeEnd} de ${total}`;
    if (filtroActivo && totalSinFiltro != null && totalSinFiltro !== total) {
        return `${base} (de ${totalSinFiltro} sin filtrar)`;
    }
    return base;
}
