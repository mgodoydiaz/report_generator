/**
 * transition.jsx — Gráficos de transición/evolución por entidad
 *
 * Componentes:
 *   ImprovementRateByGroup — % de entidades (ej. estudiantes) que mejoraron / se
 *                            mantuvieron / empeoraron su nivel entre dos momentos,
 *                            agrupado por un campo (curso, subprueba, etc.).
 */

import React from 'react';
import PlotlyWrapper from './PlotlyWrapper';
import { getLevelPalette } from './constants';

function modal(list) {
    if (!list.length) return null;
    const counts = {};
    for (const v of list) {
        if (v == null) continue;
        counts[v] = (counts[v] || 0) + 1;
    }
    let best = null;
    let bestCount = -1;
    for (const [k, c] of Object.entries(counts)) {
        if (c > bestCount) { best = k; bestCount = c; }
    }
    return best;
}

/**
 * Calcula tasa de transición por grupo entre el primer y último valor de timeField.
 *
 * Props:
 *   records      Array<Object>
 *   groups       string[]             orden opcional; si no se pasa se infiere
 *   groupField   string               campo de grupo (ej. "_curso")
 *   timeField    string               campo temporal ordinal (ej. "_evaluacion_num")
 *   entityField  string               campo de entidad (ej. "_rut")
 *   levelField   string               campo de nivel (ej. "_nivel_de_riesgo")
 *   levelOrder   Object<string,number> mapping nivel → valor ordinal
 *   height       number
 */
export function ImprovementRateByGroup({
    records = [],
    groups = [],
    groupField = '_curso',
    timeField = '_evaluacion_num',
    entityField = '_nombre',
    levelField = '_logro',
    levelOrder = null,
    achievement_levels = [],
    height,
    labelX,
    labelY,
    showLegend,
    showValues,
}) {
    const palette = getLevelPalette(achievement_levels);
    const resolvedLevelOrder = levelOrder ?? palette.ordByName;
    // 1. Resolver primer y último periodo
    const periods = [...new Set(records.map(r => r[timeField]).filter(v => v != null))]
        .map(Number)
        .filter(v => !Number.isNaN(v))
        .sort((a, b) => a - b);
    if (periods.length < 2) return <p className="text-slate-400 text-sm p-4">Se necesitan al menos 2 periodos para calcular transiciones.</p>;

    const first = periods[0];
    const last = periods[periods.length - 1];

    // 2. Agrupar records por entidad y periodo → nivel modal
    //    También guardar el grupo al que pertenece la entidad (último grupo visto).
    const entityLevelFirst = {};  // rut → nivel modal en "first"
    const entityLevelLast = {};
    const entityGroup = {};       // rut → valor de groupField

    const byEntityFirst = {}; // rut → [levels]
    const byEntityLast = {};

    for (const r of records) {
        const rawE = r[entityField];
        const g = r[groupField];
        if (rawE == null || g == null) continue;
        const e = `${rawE}||${g}`;
        entityGroup[e] = g;
        const t = Number(r[timeField]);
        if (t === first) {
            (byEntityFirst[e] ||= []).push(r[levelField]);
        } else if (t === last) {
            (byEntityLast[e] ||= []).push(r[levelField]);
        }
    }
    for (const e of Object.keys(byEntityFirst)) entityLevelFirst[e] = modal(byEntityFirst[e]);
    for (const e of Object.keys(byEntityLast))  entityLevelLast[e] = modal(byEntityLast[e]);

    // 3. Por cada entidad con datos en ambos periodos, clasificar transición
    const groupList = groups.length
        ? groups
        : [...new Set(records.map(r => r[groupField]).filter(Boolean))].sort();

    const counts = {};  // grupo → { mejoró, mantuvo, empeoró, total }
    for (const g of groupList) counts[g] = { mejoro: 0, mantuvo: 0, empeoro: 0, total: 0 };

    for (const e of Object.keys(entityLevelFirst)) {
        const lvF = entityLevelFirst[e];
        const lvL = entityLevelLast[e];
        if (lvF == null || lvL == null) continue;
        const vF = resolvedLevelOrder[lvF];
        const vL = resolvedLevelOrder[lvL];
        if (vF == null || vL == null) continue;
        const g = entityGroup[e];
        if (!counts[g]) continue;
        counts[g].total += 1;
        if (vL > vF)      counts[g].mejoro += 1;
        else if (vL < vF) counts[g].empeoro += 1;
        else              counts[g].mantuvo += 1;
    }

    const pct = (n, d) => d > 0 ? (n / d) * 100 : 0;

    const xGroups = groupList.filter(g => counts[g].total > 0);
    if (!xGroups.length) return <p className="text-slate-400 text-sm p-4">Sin datos para calcular transiciones.</p>;

    const pctMejoro = xGroups.map(g => pct(counts[g].mejoro, counts[g].total));
    const pctMantuvo = xGroups.map(g => pct(counts[g].mantuvo, counts[g].total));
    const pctEmpeoro = xGroups.map(g => pct(counts[g].empeoro, counts[g].total));

    const displayValues = showValues !== false;
    const txt = (arr) => arr.map(v => v >= 5 ? Math.round(v) + '%' : '');

    const mkTrace = (name, y, color) => ({
        type: 'bar',
        name,
        x: xGroups,
        y,
        marker: { color },
        text: displayValues ? txt(y) : undefined,
        textposition: 'inside',
        textfont: { color: '#fff', size: 12 },
        hovertemplate: `<b>%{x}</b><br>${name}: %{y:.1f}%<extra></extra>`,
    });

    // Colores: mejor nivel (último en orderedNames) y peor nivel (primero)
    const bestColor  = palette.colorByName[palette.orderedNames[palette.orderedNames.length - 1]] ?? '#16a34a';
    const worstColor = palette.colorByName[palette.orderedNames[0]] ?? '#dc2626';

    const traces = [
        mkTrace('Mejoró',     pctMejoro,  bestColor),
        mkTrace('Se mantuvo', pctMantuvo, '#94a3b8'),
        mkTrace('Empeoró',    pctEmpeoro, worstColor),
    ];

    return (
        <PlotlyWrapper
            data={traces}
            layout={{
                barmode: 'stack',
                showlegend: showLegend ?? true,
                legend: { orientation: 'h', y: -0.2 },
                yaxis: {
                    range: [0, 100],
                    tickformat: '.0f',
                    ticksuffix: '%',
                    ...(labelY ? { title: { text: labelY, font: { size: 11 } } } : {}),
                },
                xaxis: labelX ? { title: { text: labelX, font: { size: 11 } } } : {},
                margin: { t: 16, r: 16, b: 56, l: 56 },
            }}
            height={height || 280}
        />
    );
}
