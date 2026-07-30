"""`GroupedBarByPeriod` no debe salir en blanco por un periodField inexistente.

El layout histórico de Fluidez Lectora declaraba el eje temporal como
`"_evaluacion"`. Ese alias NO está en `_KNOWN_ROLES` (el rol se llama
`evaluacion_num`), así que `_resolve_field` lo devuelve tal cual, ningún record
trae la clave `_evaluacion`, el eje X queda sin categorías y el gráfico sale
COMPLETAMENTE en blanco — sin excepción ni advertencia (QA 2026-07-30).

La regla: si el `periodField` resuelto no está poblado en ningún record, se cae
a la primera columna del rol temporal que sí lo esté. Misma convención que el
fallback de `levelField` en `StackedCountByGroup`: mejor el eje del rol que un
gráfico vacío.
"""
from __future__ import annotations

import pytest

from backend.rgenerator.core.report_steps import (
    METRIC_ID_KEY,
    _chart_to_png_b64,
    _periodo_presente_en_records,
)


# `column_roles` real de Fluidez Lectora (org 1, id 5): el rol temporal declara
# N Prueba y Fecha; "Cantidad" ES el PPM.
COLUMN_ROLES_FL = {
    "logro_1": [{"metric_id": 10, "column": "Cantidad"}],
    "nivel_de_logro": [{"metric_id": 10, "column": "Categoria"}],
    "habilidad": [{"metric_id": 10, "column": "Calidad lectora"}],
    "evaluacion_num": [
        {"metric_id": 10, "column": "N Prueba"},
        {"metric_id": 10, "column": "Fecha"},
    ],
}


class _IndicadorFake:
    """Stub mínimo con los atributos que lee `_chart_to_png_b64`."""

    def __init__(self, column_roles, achievement_levels=None,
                 role_formats=None, temporal_config=None):
        self.column_roles = column_roles
        self.achievement_levels = achievement_levels or []
        self.role_formats = role_formats or {}
        self.temporal_config = temporal_config or {}


def _records_fl():
    """2 cursos × 2 ensayos, PPM conocido para verificar el promedio."""
    filas = [
        ("I A", "Ensayo 1", [100, 120]),
        ("I A", "Ensayo 2", [140, 160]),
        ("I B", "Ensayo 1", [200, 220]),
        ("I B", "Ensayo 2", [240, 260]),
    ]
    records = []
    for curso, ensayo, ppms in filas:
        for ppm in ppms:
            records.append({
                METRIC_ID_KEY: 10,
                "_curso": curso,
                "_n_prueba": ensayo,
                "_fecha": "2026-04-02 00:00:00",
                "_cantidad": ppm,
            })
    return records


@pytest.fixture
def barras_espiadas(monkeypatch):
    """Captura las llamadas a `Axes.bar`: [(label, [alturas])]."""
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from matplotlib.axes import Axes

    capturadas: list[tuple] = []
    original = Axes.bar

    def _bar_espia(self, x, height, *args, **kwargs):
        capturadas.append((kwargs.get("label"), list(height)))
        return original(self, x, height, *args, **kwargs)

    monkeypatch.setattr(Axes, "bar", _bar_espia)
    return capturadas


@pytest.mark.unit
class TestPeriodoPresenteEnRecords:
    def test_respeta_el_period_field_que_existe(self):
        assert _periodo_presente_en_records(
            "_n_prueba", _records_fl(), COLUMN_ROLES_FL) == "_n_prueba"

    def test_cae_a_la_primera_columna_del_rol_temporal(self):
        assert _periodo_presente_en_records(
            "_evaluacion", _records_fl(), COLUMN_ROLES_FL) == "_n_prueba"

    def test_salta_las_columnas_del_rol_que_no_estan_pobladas(self):
        # Sin `_n_prueba` en los datos, el rol sigue con "Fecha".
        records = [{k: v for k, v in r.items() if k != "_n_prueba"}
                   for r in _records_fl()]
        assert _periodo_presente_en_records(
            "_evaluacion", records, COLUMN_ROLES_FL) == "_fecha"

    def test_sin_rol_temporal_devuelve_el_campo_original(self):
        roles = {k: v for k, v in COLUMN_ROLES_FL.items() if k != "evaluacion_num"}
        assert _periodo_presente_en_records(
            "_evaluacion", _records_fl(), roles) == "_evaluacion"

    def test_sin_records_no_toca_nada(self):
        assert _periodo_presente_en_records(
            "_evaluacion", [], COLUMN_ROLES_FL) == "_evaluacion"


@pytest.mark.unit
class TestGroupedBarByPeriodConAliasRoto:
    def _indicador(self):
        return _IndicadorFake(column_roles=COLUMN_ROLES_FL)

    def test_alias_inexistente_ya_no_deja_el_grafico_vacio(self, barras_espiadas):
        item = {
            "component": "GroupedBarByPeriod",
            "valueField": "_logro_1",
            "groupField": "_curso",
            "periodField": "_evaluacion",  # el alias roto del layout histórico
        }
        b64 = _chart_to_png_b64(item, _records_fl(), indicator=self._indicador())
        assert b64

        por_curso = {label: vals for label, vals in barras_espiadas if label}
        assert set(por_curso) == {"I A", "I B"}
        # Dos períodos (Ensayo 1, Ensayo 2) con el promedio de PPM de cada uno.
        assert por_curso["I A"] == [110.0, 150.0]
        assert por_curso["I B"] == [210.0, 250.0]

    def test_el_alias_correcto_da_el_mismo_resultado(self, barras_espiadas):
        item = {
            "component": "GroupedBarByPeriod",
            "valueField": "_logro_1",
            "groupField": "_curso",
            "periodField": "_evaluacion_num",
        }
        _chart_to_png_b64(item, _records_fl(), indicator=self._indicador())
        por_curso = {label: vals for label, vals in barras_espiadas if label}
        assert por_curso["I A"] == [110.0, 150.0]
        assert por_curso["I B"] == [210.0, 250.0]

    def test_un_solo_periodo_dibuja_ese_periodo(self, barras_espiadas):
        """Con una sola evaluación cargada el gráfico muestra ese punto.

        Es el estado real de Fluidez Lectora en dev: solo "Ensayo 1".
        """
        records = [r for r in _records_fl() if r["_n_prueba"] == "Ensayo 1"]
        item = {
            "component": "GroupedBarByPeriod",
            "valueField": "_logro_1",
            "groupField": "_curso",
            "periodField": "_evaluacion",
        }
        _chart_to_png_b64(item, records, indicator=self._indicador())
        por_curso = {label: vals for label, vals in barras_espiadas if label}
        assert por_curso["I A"] == [110.0]
        assert por_curso["I B"] == [210.0]
