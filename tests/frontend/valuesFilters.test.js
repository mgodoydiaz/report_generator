/**
 * Tests de valuesFilters — helpers puros de los filtros de /values.
 *
 * Correr:
 *   cd frontend && npm run test:frontend -- valuesFilters
 */

import { describe, it, expect } from 'vitest';
import {
    FILTROS_VACIOS,
    normalizarFiltros,
    hayFiltroActivo,
    contarFiltros,
    construirParamsDatos,
    facetsADimensiones,
    ordenarDimIds,
    debeResetearFiltros,
    textoContador,
} from '../../frontend/src/tooling/valuesFilters.js';

describe('normalizarFiltros', () => {
    it('descarta dimensiones sin valores', () => {
        expect(normalizarFiltros({ 4: [], 9: ['MARZO'] })).toEqual({ 9: ['MARZO'] });
    });

    it('tolera null/undefined', () => {
        expect(normalizarFiltros(null)).toEqual({});
        expect(normalizarFiltros(undefined)).toEqual({});
    });

    it('castea claves y valores a string', () => {
        expect(normalizarFiltros({ 4: [2026] })).toEqual({ 4: ['2026'] });
    });
});

describe('hayFiltroActivo / contarFiltros', () => {
    it('sin filtros ni búsqueda es falso', () => {
        expect(hayFiltroActivo(FILTROS_VACIOS, '')).toBe(false);
        expect(hayFiltroActivo({ 4: [] }, '   ')).toBe(false);
    });

    it('detecta filtro por dimensión', () => {
        expect(hayFiltroActivo({ 4: ['2026'] }, '')).toBe(true);
    });

    it('detecta búsqueda libre', () => {
        expect(hayFiltroActivo({}, 'noviembre')).toBe(true);
    });

    it('cuenta todos los valores seleccionados', () => {
        expect(contarFiltros({ 4: ['2025', '2026'], 9: ['MARZO'] })).toBe(3);
        expect(contarFiltros({})).toBe(0);
    });
});

describe('construirParamsDatos', () => {
    const parse = (qs) => Object.fromEntries(new URLSearchParams(qs));

    it('sin filtros manda solo la paginación (retrocompat)', () => {
        const qs = construirParamsDatos({ page: 2, pageSize: 50 });
        expect(qs).toBe('page=2&page_size=50');
        expect(parse(qs).filters).toBeUndefined();
        expect(parse(qs).q).toBeUndefined();
    });

    it('incluye include_audit solo cuando está activo', () => {
        expect(parse(construirParamsDatos({ includeAudit: true })).include_audit).toBe('true');
        expect(parse(construirParamsDatos({ includeAudit: false })).include_audit).toBeUndefined();
    });

    it('serializa filters como JSON', () => {
        const qs = construirParamsDatos({ filtros: { 4: ['2026'] } });
        expect(JSON.parse(parse(qs).filters)).toEqual({ 4: ['2026'] });
    });

    it('multi-dimensión y multi-valor', () => {
        const qs = construirParamsDatos({ filtros: { 4: ['2025', '2026'], 9: ['MARZO'] } });
        expect(JSON.parse(parse(qs).filters)).toEqual({ 4: ['2025', '2026'], 9: ['MARZO'] });
    });

    it('omite dimensiones vacías', () => {
        const qs = construirParamsDatos({ filtros: { 4: [], 9: ['MARZO'] } });
        expect(JSON.parse(parse(qs).filters)).toEqual({ 9: ['MARZO'] });
    });

    it('si todas las dimensiones están vacías no manda filters', () => {
        expect(parse(construirParamsDatos({ filtros: { 4: [] } })).filters).toBeUndefined();
    });

    it('manda q recortado y omite el vacío', () => {
        expect(parse(construirParamsDatos({ q: '  NOVIEMBRE ' })).q).toBe('NOVIEMBRE');
        expect(parse(construirParamsDatos({ q: '   ' })).q).toBeUndefined();
    });

    it('combina filters + q + auditoría', () => {
        const p = parse(construirParamsDatos({
            page: 3, pageSize: 25, includeAudit: true,
            filtros: { 4: ['2026'] }, q: 'marzo',
        }));
        expect(p.page).toBe('3');
        expect(p.page_size).toBe('25');
        expect(p.include_audit).toBe('true');
        expect(JSON.parse(p.filters)).toEqual({ 4: ['2026'] });
        expect(p.q).toBe('marzo');
    });

    it('los valores con caracteres especiales viajan escapados', () => {
        const qs = construirParamsDatos({ filtros: { 4: ['1° A & B'] } });
        expect(qs).not.toContain('&B');
        expect(JSON.parse(parse(qs).filters)).toEqual({ 4: ['1° A & B'] });
    });
});

describe('facetsADimensiones', () => {
    it('convierte al shape de MultiSelectFilters', () => {
        const out = facetsADimensiones({
            4: { name: 'Año', values: ['2025', '2026'] },
            9: { name: 'Mes', values: ['MARZO'] },
        });
        expect(out).toEqual({
            4: { name: 'Año', values: ['2025', '2026'] },
            9: { name: 'Mes', values: ['MARZO'] },
        });
    });

    it('tolera respuesta vacía o inválida', () => {
        expect(facetsADimensiones(null)).toEqual({});
        expect(facetsADimensiones({ 4: null })).toEqual({});
        expect(facetsADimensiones({ 4: { name: 'Año' } })).toEqual({ 4: { name: 'Año', values: [] } });
    });
});

describe('ordenarDimIds', () => {
    const facets = {
        9: { name: 'Mes', values: ['MARZO'] },
        4: { name: 'Año', values: ['2026'] },
    };

    it('respeta el orden de dimension_ids de la métrica', () => {
        expect(ordenarDimIds({ dimension_ids: [4, 9] }, facets)).toEqual(['4', '9']);
        expect(ordenarDimIds({ dimension_ids: [9, 4] }, facets)).toEqual(['9', '4']);
    });

    it('agrega al final las dimensiones que solo están en los datos', () => {
        const conExtra = { ...facets, 12: { name: 'Curso', values: ['1 A'] } };
        expect(ordenarDimIds({ dimension_ids: [4, 9] }, conExtra)).toEqual(['4', '9', '12']);
    });

    it('ignora dimensiones declaradas sin datos', () => {
        expect(ordenarDimIds({ dimension_ids: [4, 9, 99] }, facets)).toEqual(['4', '9']);
    });

    it('sin métrica devuelve las claves de facets', () => {
        expect(ordenarDimIds(null, facets).sort()).toEqual(['4', '9']);
    });
});

describe('debeResetearFiltros', () => {
    it('resetea al cambiar de métrica', () => {
        expect(debeResetearFiltros({ id_metric: 1 }, { id_metric: 2 })).toBe(true);
    });

    it('no resetea si es la misma métrica', () => {
        expect(debeResetearFiltros({ id_metric: 4 }, { id_metric: 4 })).toBe(false);
    });

    it('resetea al pasar de ninguna métrica a una', () => {
        expect(debeResetearFiltros(null, { id_metric: 1 })).toBe(true);
        expect(debeResetearFiltros(null, null)).toBe(false);
    });
});

describe('textoContador', () => {
    it('sin registros', () => {
        expect(textoContador({ total: 0 })).toBe('0 registros');
        expect(textoContador({ total: 0, filtroActivo: true })).toBe('0 registros (filtrado)');
    });

    it('rango simple sin filtro', () => {
        expect(textoContador({ total: 120, rangeStart: 1, rangeEnd: 50 })).toBe('1–50 de 120');
    });

    it('muestra el total sin filtrar cuando hay filtro', () => {
        expect(textoContador({
            total: 3, totalSinFiltro: 120, rangeStart: 1, rangeEnd: 3, filtroActivo: true,
        })).toBe('1–3 de 3 (de 120 sin filtrar)');
    });

    it('no repite el total si el filtro no descarta nada', () => {
        expect(textoContador({
            total: 120, totalSinFiltro: 120, rangeStart: 1, rangeEnd: 50, filtroActivo: true,
        })).toBe('1–50 de 120');
    });
});
