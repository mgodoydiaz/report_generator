// fieldUtils.js — Helpers compartidos para derivar campos disponibles en los configuradores

export function toFieldName(col) {
    return '_' + col.trim().toLowerCase()
        .replace(/\s+/g, '_')
        .replace(/[^a-z0-9_]/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_+|_+$/g, '');
}

/**
 * Deriva la lista plana de campos disponibles a partir de las métricas e indicador.
 * Retorna Array<{ field, label, kind: 'valor'|'dimensión'|'derivado', type, metric }>
 */
export function buildAvailableFields(allMetrics, allDimensions, derivedColumns) {
    const seen = new Set();
    const fields = [];
    const dimMap = Object.fromEntries((allDimensions || []).map(d => [d.id_dimension, d]));

    for (const m of (allMetrics || [])) {
        const mFields = m.meta_json?.fields;
        if (Array.isArray(mFields) && mFields.length > 0) {
            for (const f of mFields) {
                const key = toFieldName(f.name);
                if (!seen.has(key)) {
                    seen.add(key);
                    fields.push({ field: key, label: f.name, kind: 'valor', type: f.type, metric: m.name });
                }
            }
        } else {
            const key = toFieldName(m.name);
            if (!seen.has(key)) {
                seen.add(key);
                fields.push({ field: key, label: m.name, kind: 'valor', type: m.data_type, metric: m.name });
            }
        }
        for (const did of (m.dimension_ids || [])) {
            const dim = dimMap[did];
            if (dim) {
                const key = toFieldName(dim.name);
                if (!seen.has(key)) {
                    seen.add(key);
                    fields.push({ field: key, label: dim.name, kind: 'dimensión', type: dim.data_type, metric: m.name });
                }
            }
        }
    }
    for (const dc of (derivedColumns || [])) {
        if (!dc.name) continue;
        const key = dc.name.startsWith('_') ? dc.name : `_${dc.name}`;
        if (!seen.has(key)) {
            seen.add(key);
            fields.push({ field: key, label: dc.label || dc.name, kind: 'derivado', type: 'float', metric: 'derivado' });
        }
    }

    return fields;
}
