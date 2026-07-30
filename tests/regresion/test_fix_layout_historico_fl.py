"""Contrato de `scripts/fix_layout_historico_fl.py`.

El script repara el alias `_evaluacion` (que no es rol conocido) por
`_evaluacion_num` en los layouts PDF de Fluidez Lectora. Se corre también en
producción, así que interesa que sea idempotente, que no toque strings
parecidos y que reconozca el indicador sin depender del id.
"""
from __future__ import annotations

import pytest

from scripts.fix_layout_historico_fl import (
    ALIAS_CORRECTO,
    ALIAS_ROTO,
    corregir_layout,
    es_fluidez_lectora,
)

pytestmark = pytest.mark.unit


LAYOUT_ROTO = {
    "engine": "weasyprint",
    "mode": "historico",
    "sections": [
        {"type": "chart", "heading": "Evolución PPM Promedio por Curso y Evaluación",
         "item": {"component": "GroupedBarByPeriod", "valueField": "_logro_1",
                  "groupField": "_curso", "periodField": "_evaluacion"}},
        {"type": "chart", "heading": "Evolución de Categoría por Evaluación",
         "item": {"component": "StackedCountByGroup", "groupField": "_evaluacion",
                  "levelField": "_nivel_de_logro"}},
    ],
}


class _IndicadorFake:
    def __init__(self, name="", report_engine_type=None):
        self.name = name
        self.report_engine_type = report_engine_type


class TestCorregirLayout:
    def test_reemplaza_las_dos_ocurrencias(self):
        corregido, n = corregir_layout(LAYOUT_ROTO)
        assert n == 2
        assert corregido["sections"][0]["item"]["periodField"] == ALIAS_CORRECTO
        assert corregido["sections"][1]["item"]["groupField"] == ALIAS_CORRECTO

    def test_no_muta_el_layout_original(self):
        corregir_layout(LAYOUT_ROTO)
        assert LAYOUT_ROTO["sections"][0]["item"]["periodField"] == ALIAS_ROTO

    def test_es_idempotente(self):
        corregido, _ = corregir_layout(LAYOUT_ROTO)
        otra_vez, n = corregir_layout(corregido)
        assert n == 0
        assert otra_vez == corregido

    def test_no_toca_alias_que_solo_contienen_la_subcadena(self):
        layout = {"item": {"periodField": "_evaluacion_num",
                           "heading": "Evolución por _evaluacion y curso"}}
        corregido, n = corregir_layout(layout)
        assert n == 0
        assert corregido == layout

    def test_conserva_el_resto_del_layout(self):
        corregido, _ = corregir_layout(LAYOUT_ROTO)
        assert corregido["engine"] == "weasyprint"
        assert corregido["sections"][0]["item"]["groupField"] == "_curso"
        assert len(corregido["sections"]) == 2


class TestEsFluidezLectora:
    @pytest.mark.parametrize("nombre", [
        "Fluidez Lectora", "fluidez lectora", "FLUIDEZ LECTORA",
        "Fluidez Lectora Demo",
    ])
    def test_reconoce_por_nombre(self, nombre):
        assert es_fluidez_lectora(_IndicadorFake(name=nombre))

    def test_reconoce_por_engine(self):
        assert es_fluidez_lectora(
            _IndicadorFake(name="PPM 2026", report_engine_type="fluidez_lectora"))

    @pytest.mark.parametrize("nombre", ["SIMCE", "DIA", "IDEL", "Cálculo Veloz"])
    def test_ignora_los_demas_indicadores(self, nombre):
        assert not es_fluidez_lectora(_IndicadorFake(name=nombre))

    def test_tolera_engine_none(self):
        assert not es_fluidez_lectora(_IndicadorFake(name="SIMCE", report_engine_type=None))
