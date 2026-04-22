/**
 * Tests de processDataForDashboard (S4.5 · Sprint 4).
 *
 * Requiere vitest. Para correr:
 *   cd frontend && npm install --save-dev vitest
 *   npm run test:frontend
 *
 * Cubre los invariantes del Sprint 1:
 *   - Detección de dimensión RUT y filtrado de records sin RUT.
 *   - Deduplicación por (_rut, _habilidad, _evaluacion_num).
 *   - Derivadas: _worst_level_ord, _worst_level_label, _trajectory, _n_evaluations.
 *   - Respeto del achievement_levels como fuente de orden para peor-nivel.
 */

import { describe, it, expect } from 'vitest';
import { processDataForDashboard } from '../../frontend/src/tooling/dataProcessing.js';

// ── Helpers ──────────────────────────────────────────────────────────────────

const DIMS = {
    1: { id: 1, name: 'RUT' },
    2: { id: 2, name: 'Curso' },
    3: { id: 3, name: 'Habilidad' },
    4: { id: 4, name: 'Nombre' },
};

const COLUMN_ROLES = {
    logro_1:        [{ metric_id: 100, column: 'Porcentaje_Logro' }],
    nivel_de_logro: [{ metric_id: 100, column: 'Nivel' }],
    habilidad:      [{ metric_id: 100, column: 'Habilidad' }],
    evaluacion_num: [{ metric_id: 100, column: 'Eval' }],
};

const ACHIEVEMENT_LEVELS = [
    { name: 'Crítico',      color: '#dc2626', order: 1 },
    { name: 'Alto Riesgo',  color: '#f97316', order: 2 },
    { name: 'Cierto Riesgo', color: '#eab308', order: 3 },
    { name: 'Bajo Riesgo',  color: '#16a34a', order: 4 },
];

function mkResult(metricData) {
    return {
        dimensions: DIMS,
        column_roles: COLUMN_ROLES,
        role_labels: {},
        role_formats: {},
        achievement_levels: ACHIEVEMENT_LEVELS,
        metrics: [{
            id: 100,
            name: 'Rendimiento',
            data: metricData,
        }],
    };
}

function row({ rut, curso, habilidad, nombre, evalNum, nivel, pctLogro }) {
    return {
        dimensions_json: {
            1: rut ?? null,
            2: curso,
            3: habilidad,
            4: nombre,
        },
        value: {
            _porcentaje_logro: pctLogro,
            _nivel: nivel,
            _habilidad: habilidad,
            _eval: evalNum,
        },
    };
}

// ── Fixtures ─────────────────────────────────────────────────────────────────

describe('processDataForDashboard — RUT handling', () => {
    it('descarta records sin RUT cuando la dimensión RUT está configurada', () => {
        const data = [
            row({ rut: '11111111-1', curso: '1°', habilidad: 'CT', nombre: 'Ana',  evalNum: 1, nivel: 'Crítico',    pctLogro: 0.2 }),
            row({ rut: null,          curso: '1°', habilidad: 'CT', nombre: 'NoRut', evalNum: 1, nivel: 'Bajo Riesgo', pctLogro: 0.8 }),
        ];
        const out = processDataForDashboard(mkResult(data));
        expect(out.estudiantes.length).toBe(1);
        expect(out.estudiantes[0]._rut).toBe('111111111');
    });

    it('normaliza RUT a uppercase sin puntos ni guiones', () => {
        const data = [
            row({ rut: '11.222.333-k', curso: '1°', habilidad: 'CT', nombre: 'X', evalNum: 1, nivel: 'Crítico', pctLogro: 0.1 }),
        ];
        const out = processDataForDashboard(mkResult(data));
        expect(out.estudiantes[0]._rut).toBe('11222333K');
    });
});

describe('processDataForDashboard — deduplicación', () => {
    it('colapsa duplicados por (rut, habilidad, eval_num)', () => {
        const data = [
            row({ rut: '1-1', curso: '1°', habilidad: 'CT', nombre: 'A', evalNum: 1, nivel: 'Crítico', pctLogro: 0.2 }),
            row({ rut: '1-1', curso: '1°', habilidad: 'CT', nombre: 'A', evalNum: 1, nivel: 'Crítico', pctLogro: 0.3 }),
        ];
        const out = processDataForDashboard(mkResult(data));
        expect(out.estudiantes.length).toBe(1);
    });
});

describe('processDataForDashboard — derived columns', () => {
    it('peor nivel: Crítico en FLO gana sobre Bajo Riesgo en CT', () => {
        const data = [
            row({ rut: '2-2', curso: '1°', habilidad: 'CT',  nombre: 'B', evalNum: 1, nivel: 'Bajo Riesgo', pctLogro: 0.9 }),
            row({ rut: '2-2', curso: '1°', habilidad: 'FLO', nombre: 'B', evalNum: 1, nivel: 'Crítico',    pctLogro: 0.1 }),
        ];
        const out = processDataForDashboard(mkResult(data));
        const any = out.estudiantes.find(e => e._rut === '22');
        expect(any._worst_level_label).toBe('Crítico');
        expect(any._worst_subprueba).toBe('FLO');
        expect(any._is_urgent).toBe(true);
        expect(any._is_concerning).toBe(true);
    });

    it('trayectoria incompleta con 1 sola evaluación', () => {
        const data = [
            row({ rut: '3-3', curso: '1°', habilidad: 'CT', nombre: 'C', evalNum: 1, nivel: 'Crítico', pctLogro: 0.1 }),
        ];
        const out = processDataForDashboard(mkResult(data));
        const any = out.estudiantes.find(e => e._rut === '33');
        expect(any._trajectory).toBe('incomplete');
        expect(any._n_evaluations).toBe(1);
    });

    it('trayectoria improving cuando peor-nivel pasa de Crítico (1) a Bajo Riesgo (4)', () => {
        const data = [
            row({ rut: '4-4', curso: '1°', habilidad: 'CT', nombre: 'D', evalNum: 1, nivel: 'Crítico',    pctLogro: 0.1 }),
            row({ rut: '4-4', curso: '1°', habilidad: 'CT', nombre: 'D', evalNum: 2, nivel: 'Bajo Riesgo', pctLogro: 0.9 }),
        ];
        const out = processDataForDashboard(mkResult(data));
        const any = out.estudiantes.find(e => e._rut === '44');
        expect(any._n_evaluations).toBe(2);
        expect(any._trajectory).toBe('improving');
    });
});
