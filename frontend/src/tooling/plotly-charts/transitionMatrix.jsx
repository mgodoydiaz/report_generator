/**
 * transitionMatrix.jsx — Matriz de transición entre niveles (Sankey)
 *
 * Componente:
 *   TransitionMatrix — Diagrama Sankey mostrando cuántos estudiantes cambiaron
 *                      de nivel entre la primera y última evaluación.
 */

import React, { useMemo } from 'react';
import PlotlyWrapper from './PlotlyWrapper';
import { getLevelPalette } from './constants';

function modalOf(counts) {
    if (!counts || !Object.keys(counts).length) return null;
    let best = null, bestCount = 0;
    for (const [k, c] of Object.entries(counts)) {
        if (c > bestCount) { best = k; bestCount = c; }
    }
    return best;
}

/**
 * Props:
 *   records           Array<Object>
 *   timeField         string (default '_evaluacion_num')
 *   entityField       string (default '_rut')
 *   levelField        string (default '_worst_level_label')
 *   achievement_levels
 *   height            number
 */
export function TransitionMatrix({
    records = [],
    timeField = '_evaluacion_num',
    entityField = '_rut',
    levelField = '_worst_level_label',
    achievement_levels = [],
    height,
}) {
    const palette = getLevelPalette(achievement_levels);

    const { traces, error } = useMemo(() => {
        // 1. Obtener primer y último periodo
        const periods = [...new Set(records.map(r => r[timeField]).filter(v => v != null))]
            .map(Number).filter(v => !isNaN(v)).sort((a, b) => a - b);

        if (periods.length < 2) {
            return { traces: null, error: 'Se necesitan al menos 2 evaluaciones para construir el Sankey.' };
        }

        const first = periods[0];
        const last  = periods[periods.length - 1];

        // 2. Nivel modal por entidad en cada extremo
        const firstCounts = {};  // entity → { level: count }
        const lastCounts  = {};

        for (const r of records) {
            const e = r[entityField];
            const t = Number(r[timeField]);
            const lv = r[levelField];
            if (e == null || !lv) continue;

            if (t === first) {
                if (!firstCounts[e]) firstCounts[e] = {};
                firstCounts[e][lv] = (firstCounts[e][lv] || 0) + 1;
            } else if (t === last) {
                if (!lastCounts[e]) lastCounts[e] = {};
                lastCounts[e][lv] = (lastCounts[e][lv] || 0) + 1;
            }
        }

        // 3. Contar transiciones from → to
        const transitions = {};
        for (const e of Object.keys(firstCounts)) {
            if (!lastCounts[e]) continue;
            const from = modalOf(firstCounts[e]);
            const to   = modalOf(lastCounts[e]);
            if (!from || !to) continue;
            const key = `${from}\u2192${to}`;
            transitions[key] = (transitions[key] || 0) + 1;
        }

        if (!Object.keys(transitions).length) {
            return { traces: null, error: 'Sin estudiantes con datos en ambas evaluaciones.' };
        }

        // 4. Construir nodos Sankey: from-side + to-side
        const levels = palette.orderedNames;
        const nodeLabels = [
            ...levels.map(l => `${l} (eval. ${first})`),
            ...levels.map(l => `${l} (eval. ${last})`),
        ];
        const nodeColors = [
            ...levels.map(l => (palette.colorByName[l] || '#94a3b8') + 'cc'),
            ...levels.map(l => (palette.colorByName[l] || '#94a3b8') + 'cc'),
        ];

        const fromIdx = Object.fromEntries(levels.map((l, i) => [l, i]));
        const toIdx   = Object.fromEntries(levels.map((l, i) => [l, i + levels.length]));

        const sources = [], targets = [], values = [], linkColors = [];
        for (const [key, count] of Object.entries(transitions)) {
            const [from, to] = key.split('\u2192');
            const fi = fromIdx[from];
            const ti = toIdx[to];
            if (fi == null || ti == null) continue;
            sources.push(fi);
            targets.push(ti);
            values.push(count);
            linkColors.push((palette.colorByName[to] || '#94a3b8') + '66');
        }

        const trace = {
            type: 'sankey',
            orientation: 'h',
            node: {
                pad: 15,
                thickness: 20,
                line: { color: 'rgba(0,0,0,0.1)', width: 0.5 },
                label: nodeLabels,
                color: nodeColors,
            },
            link: {
                source: sources,
                target: targets,
                value:  values,
                color:  linkColors,
                hovertemplate: '%{value} estudiante(s)<extra></extra>',
            },
        };

        return { traces: [trace], error: null };
    }, [records, timeField, entityField, levelField, palette]);

    if (error) {
        return <p className="text-slate-400 text-sm p-4 text-center">{error}</p>;
    }
    if (!traces) return null;

    return (
        <PlotlyWrapper
            data={traces}
            layout={{
                margin: { t: 10, r: 10, b: 10, l: 10 },
                font: { size: 11 },
            }}
            height={height || 360}
        />
    );
}
