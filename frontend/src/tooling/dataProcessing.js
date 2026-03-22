import { avg } from './charts/constants';

/**
 * Convierte un nombre de columna al nombre de campo normalizado con prefijo _.
 * Ej: "Porcentaje_Logro" → "_porcentaje_logro"
 */
function toFieldName(col) {
    return '_' + col.trim().toLowerCase()
        .replace(/\s+/g, '_')
        .replace(/[^a-z0-9_]/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_+|_+$/g, '');
}

// Aliases fijos legacy — mantenidos para backward compat con charts legacy
const ROLE_ALIASES = {
    logro_1:        '_rend',
    logro_2:        '_simce',
    nivel_de_logro: '_logro',
    habilidad:      '_habilidad',
    habilidad_2:    '_habilidad_2',
    evaluacion_num: '_evaluacion_num',
};

/**
 * Construye un mapa de role → {metric_id → column} para búsqueda rápida.
 * column_roles format: { "logro_1": [{ metric_id: 1, column: "Rend" }], ... }
 */
function buildRoleMap(columnRoles) {
    const roleMap = {};
    for (const [role, entries] of Object.entries(columnRoles || {})) {
        if (!Array.isArray(entries)) continue;
        roleMap[role] = {};
        for (const e of entries) {
            // First-wins: si ya hay una columna para este metric_id, no sobreescribir.
            if (e.metric_id && e.column && !(e.metric_id in roleMap[role])) {
                roleMap[role][e.metric_id] = e.column;
            }
        }
    }
    return roleMap;
}

/**
 * Dado un entry, un roleMap, y el metric_id actual, extrae el valor de una columna
 * desde los fields del value (object) o desde las dimensiones.
 */
function resolveRoleValue(role, metricId, roleMap, val, djson, dimsMap) {
    const columnName = roleMap[role]?.[metricId];
    if (!columnName) return undefined;

    // Buscar en fields del value (object metrics)
    if (typeof val === 'object' && val !== null && columnName in val) {
        return val[columnName];
    }

    // Buscar en dimensiones por nombre
    for (const [dimId, dimVal] of Object.entries(djson)) {
        const dimDef = dimsMap[dimId];
        if (dimDef && dimDef.name === columnName) {
            return dimVal;
        }
    }

    return undefined;
}

/**
 * Ordena etiquetas temporales según los niveles del temporal_config.
 * Soporta sort_mode: "numeric", "custom" (con order[]), o alfabético.
 */
function sortTemporalLabels(labels, temporalConfig) {
    const levels = temporalConfig.levels;
    return [...labels].sort((a, b) => {
        const aParts = a.split(' / ');
        const bParts = b.split(' / ');
        for (let i = 0; i < levels.length; i++) {
            const level = levels[i];
            const aVal = aParts[i] ?? '';
            const bVal = bParts[i] ?? '';
            let cmp = 0;
            if (level.sort_mode === 'numeric') {
                cmp = (parseFloat(aVal) || 0) - (parseFloat(bVal) || 0);
            } else if (level.sort_mode === 'custom' && level.order?.length) {
                const aI = level.order.indexOf(aVal);
                const bI = level.order.indexOf(bVal);
                cmp = (aI === -1 ? Infinity : aI) - (bI === -1 ? Infinity : bI);
            } else {
                cmp = aVal.localeCompare(bVal);
            }
            if (cmp !== 0) return cmp;
        }
        return 0;
    });
}

/**
 * Construye la etiqueta temporal de una fila concatenando las dimensiones del temporal_config.
 * Ej. temporal_config con niveles [Año, Mes] + djson {4:"2024", 9:"AGOSTO"} → "2024 / AGOSTO"
 * Si solo hay un nivel, retorna el valor directamente sin separador.
 */
function buildTemporalLabel(djson, dimsMap, temporalConfig) {
    if (!temporalConfig?.levels?.length) return undefined;
    const parts = [];
    for (const level of temporalConfig.levels) {
        // Buscar la dimensión cuyo nombre coincida con el label del nivel
        const dimId = Object.keys(dimsMap).find(k =>
            dimsMap[k].name.toLowerCase() === level.label.toLowerCase()
        );
        if (dimId && djson[dimId] != null) {
            parts.push(String(djson[dimId]));
        }
    }
    return parts.length ? parts.join(' / ') : undefined;
}

/**
 * Procesa los datos crudos del backend al formato que consume el dashboard.
 * Usa column_roles del indicador para mapear campos explícitamente.
 *
 * @param {Object} result - { metrics, dimensions, data, column_roles, temporal_config } del endpoint /results/indicator/:id/data
 * @returns {{ estudiantes: Array, preguntas: Array, cursos: string[], dimsMap: Object, activeRoles: Object }}
 */
export function processDataForDashboard(result) {
    const { metrics, dimensions: dims, data, column_roles: columnRoles, role_labels: roleLabels, role_formats: roleFormats, temporal_config: temporalConfig } = result;
    const dimsMap = dims || {};
    const roleMap = buildRoleMap(columnRoles);

    // Determinar qué roles están activos (tienen al menos una asignación)
    const activeRoles = {};
    for (const role of ["logro_1", "logro_2", "nivel_de_logro", "habilidad", "habilidad_2", "evaluacion_num"]) {
        activeRoles[role] = roleMap[role] && Object.keys(roleMap[role]).length > 0;
    }

    // Construir mapa role → fieldName canónico derivado del nombre real de la columna
    const roleFieldMap = {};
    for (const role of Object.keys(ROLE_ALIASES)) {
        const entries = columnRoles?.[role];
        if (Array.isArray(entries) && entries.length > 0 && entries[0].column) {
            roleFieldMap[role] = toFieldName(entries[0].column);
        } else {
            roleFieldMap[role] = ROLE_ALIASES[role];
        }
    }

    // Mapa inverso fieldName → role (cubre tanto el nombre canónico como el alias legacy)
    const fieldToRole = {};
    for (const [role, fieldName] of Object.entries(roleFieldMap)) {
        fieldToRole[fieldName] = role;
        const alias = ROLE_ALIASES[role];
        if (alias && alias !== fieldName) fieldToRole[alias] = role;
    }

    // Buscar dimensión de curso por nombre (siempre por convención, no es un role)
    const cursoDimId = Object.keys(dimsMap).find(k => dimsMap[k].name.toLowerCase().includes("curso"));
    const nombreDimId = Object.keys(dimsMap).find(k =>
        dimsMap[k].name.toLowerCase().includes("nombre") || dimsMap[k].name.toLowerCase().includes("estudiante")
    );
    const preguntaDimId = Object.keys(dimsMap).find(k => dimsMap[k].name.toLowerCase().includes("pregunta"));

    const estudiantes = [];
    const preguntas = [];

    for (const metric of metrics) {
        const mid = metric.id_metric;
        const metricData = data[mid] || [];
        const hasPregunta = preguntaDimId && metric.dimension_ids.includes(parseInt(preguntaDimId));

        // Determinar si esta métrica tiene rol de habilidad asignado
        const hasHabilidadRole = roleMap.habilidad?.[mid] || roleMap.habilidad_2?.[mid];

        for (const row of metricData) {
            const djson = row.dimensions_json || {};
            const val = row.value;
            const entry = {
                _curso: cursoDimId ? (djson[cursoDimId] || "") : "",
                _raw_dims: djson,
            };

            // Extraer nombre y pregunta de dimensiones
            if (nombreDimId) entry._nombre = djson[nombreDimId] || "";
            if (preguntaDimId) entry._pregunta = djson[preguntaDimId] || "";

            // ── Mapeo explícito por column_roles ──

            // logro_1
            const rend = resolveRoleValue("logro_1", mid, roleMap, val, djson, dimsMap);
            if (rend !== undefined) {
                const fn = roleFieldMap.logro_1;
                entry[fn] = parseFloat(rend) || 0;
                if (fn !== '_rend') entry._rend = entry[fn]; // backward compat
            }

            // logro_2
            const simce = resolveRoleValue("logro_2", mid, roleMap, val, djson, dimsMap);
            if (simce !== undefined) {
                const fn = roleFieldMap.logro_2;
                entry[fn] = parseFloat(simce) || 0;
                if (fn !== '_simce') entry._simce = entry[fn]; // backward compat
            }

            // nivel_de_logro
            const logro = resolveRoleValue("nivel_de_logro", mid, roleMap, val, djson, dimsMap);
            if (logro !== undefined) {
                const fn = roleFieldMap.nivel_de_logro;
                entry[fn] = logro;
                if (fn !== '_logro') entry._logro = logro; // backward compat
            }

            // habilidad (normalizado a capitalize)
            const hab = resolveRoleValue("habilidad", mid, roleMap, val, djson, dimsMap);
            if (hab !== undefined) {
                const fn = roleFieldMap.habilidad;
                const normalized = String(hab).charAt(0).toUpperCase() + String(hab).slice(1).toLowerCase();
                entry[fn] = normalized;
                if (fn !== '_habilidad') entry._habilidad = normalized; // backward compat
            }

            // habilidad_2 (normalizado a capitalize)
            const hab2 = resolveRoleValue("habilidad_2", mid, roleMap, val, djson, dimsMap);
            if (hab2 !== undefined) {
                const fn = roleFieldMap.habilidad_2;
                const normalized2 = String(hab2).charAt(0).toUpperCase() + String(hab2).slice(1).toLowerCase();
                entry[fn] = normalized2;
                if (fn !== '_habilidad_2') entry._habilidad_2 = normalized2; // backward compat
            }

            // evaluacion_num
            const evalNum = resolveRoleValue("evaluacion_num", mid, roleMap, val, djson, dimsMap);
            if (evalNum !== undefined) {
                const fn = roleFieldMap.evaluacion_num;
                entry[fn] = evalNum;
                if (fn !== '_evaluacion_num') entry._evaluacion_num = evalNum; // backward compat
            }

            // temporal_label → etiqueta concatenada desde temporal_config (ej. "2024 / AGOSTO")
            const tempLabel = buildTemporalLabel(djson, dimsMap, temporalConfig);
            if (tempLabel !== undefined) entry._temporal_label = tempLabel;

            // ── Bucketing logic ──
            const logroField = roleFieldMap.logro_1;
            if (hasPregunta) {
                if (entry[logroField] !== undefined) entry._logro_pregunta = entry[logroField];
                preguntas.push(entry);
            } else {
                estudiantes.push(entry);
                if (hasHabilidadRole) {
                    if (entry[logroField] !== undefined) entry._logro_pregunta = entry[logroField];
                    preguntas.push(entry);
                }
            }
        }
    }

    // Si hay temporal_config, reemplazar _evaluacion_num (y el campo canónico) por el índice ordinal
    // del _temporal_label ordenado según la config.
    if (temporalConfig?.levels?.length > 0) {
        const allEntries = [...estudiantes, ...preguntas];
        const uniqueLabels = [...new Set(allEntries.map(e => e._temporal_label).filter(Boolean))];
        const sortedLabels = sortTemporalLabels(uniqueLabels, temporalConfig);
        const labelToNum = Object.fromEntries(sortedLabels.map((lbl, i) => [lbl, i + 1]));
        const evalFn = roleFieldMap.evaluacion_num;
        for (const e of allEntries) {
            if (e._temporal_label) {
                e._evaluacion_num = labelToNum[e._temporal_label];
                if (evalFn !== '_evaluacion_num') e[evalFn] = e._evaluacion_num;
            }
        }
    }

    const cursos = [...new Set(estudiantes.map(e => e._curso).filter(Boolean))].sort();
    return {
        estudiantes,
        preguntas,
        cursos,
        dimsMap,
        activeRoles,
        roleLabels: roleLabels || {},
        roleFormats: roleFormats || {},
        achievement_levels: result.achievement_levels || [],
        temporalConfig: temporalConfig || null,
        roleFieldMap,
        fieldToRole,
    };
}

/**
 * Calcula KPIs y datos derivados del dashboard.
 * Se adapta según qué roles están activos.
 */
export function computeDashboardKPIs(dashboardData) {
    if (!dashboardData) return null;
    const { estudiantes, preguntas, cursos, activeRoles, roleLabels, roleFormats, temporalConfig, roleFieldMap, fieldToRole } = dashboardData;

    // Contar alumnos únicos por nombre (si existe) para evitar duplicados en desgloses
    const studentNames = estudiantes.map(e => e._nombre).filter(Boolean);
    const totalAlumnos = studentNames.length > 0 ? new Set(studentNames).size : estudiantes.length;

    const rendField  = roleFieldMap?.logro_1        || '_rend';
    const simceField = roleFieldMap?.logro_2        || '_simce';
    const logroField = roleFieldMap?.nivel_de_logro || '_logro';

    const logroPromedio = activeRoles.logro_1 ? avg(estudiantes, rendField) : null;
    const simcePromedio = activeRoles.logro_2 ? avg(estudiantes, simceField) : null;

    let nivelPredominante = "—";
    if (activeRoles.nivel_de_logro) {
        const niveles = [...new Set(estudiantes.map(e => e[logroField]).filter(Boolean))];
        nivelPredominante = niveles.sort((a, b) =>
            estudiantes.filter(r => r[logroField] === b).length - estudiantes.filter(r => r[logroField] === a).length
        )[0] || "—";
    }

    return {
        totalAlumnos, logroPromedio, simcePromedio, nivelPredominante,
        cursos, estudiantes, preguntas, activeRoles, roleLabels,
        roleFormats: roleFormats || {},
        achievement_levels: dashboardData.achievement_levels || [],
        temporalConfig: temporalConfig || null,
        roleFieldMap: roleFieldMap || {},
        fieldToRole: fieldToRole || {},
    };
}
