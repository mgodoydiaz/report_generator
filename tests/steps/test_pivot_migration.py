"""Regresión de la migración de pivotes existentes al motor W2.

`_table_section` PivotTable (PDF v1) ahora delega la agregación en
`pivot_engine` pero debe producir EXACTAMENTE el mismo `{columns, rows}` que
la implementación anterior (snapshot fijado pre-migración). Ver
docs/planes/w2_motor_pivotes.md.
"""
from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from backend.rgenerator.core.report_steps import _table_section  # noqa: E402


# Datos con casos borde: promedio de 2 obs, un valor no numérico ('NA'), y
# un None (deben excluirse del cálculo igual que la versión vieja).
_RECORDS = [
    {"Curso": "I A", "Mes": "Marzo", "Logro": 0.8, "Puntaje": 50},
    {"Curso": "I A", "Mes": "Marzo", "Logro": 0.6, "Puntaje": 40},
    {"Curso": "I A", "Mes": "Abril", "Logro": 0.9, "Puntaje": 60},
    {"Curso": "I B", "Mes": "Marzo", "Logro": 0.5, "Puntaje": 30},
    {"Curso": "I B", "Mes": "Abril", "Logro": 0.7, "Puntaje": None},
    {"Curso": "I B", "Mes": "Abril", "Logro": "NA", "Puntaje": 45},
]


@pytest.mark.unit
class TestPivotTableRegresion:
    def test_snapshot_cols_multi_value(self):
        """Snapshot capturado ANTES de migrar (avg + count, con columnas)."""
        item = {
            "component": "PivotTable",
            "pivotConfig": {
                "rows": ["Curso"], "cols": ["Mes"],
                "values": [
                    {"field": "Logro", "aggregation": "avg", "label": "Logro"},
                    {"field": "Puntaje", "aggregation": "count", "label": "N"},
                ],
            },
        }
        assert _table_section(item, _RECORDS) == {
            "columns": ["Curso", "Abril Logro", "Abril N", "Marzo Logro", "Marzo N"],
            "rows": [
                ["I A", "0.90", "1", "0.70", "2"],
                ["I B", "0.70", "1", "0.50", "1"],
            ],
        }

    def test_snapshot_sin_cols_sum(self):
        """Snapshot sin columnas, agg sum."""
        item = {
            "component": "PivotTable",
            "pivotConfig": {
                "rows": ["Curso"], "cols": [],
                "values": [{"field": "Logro", "aggregation": "sum", "label": "Suma"}],
            },
        }
        assert _table_section(item, _RECORDS) == {
            "columns": ["Curso", "Suma"],
            "rows": [["I A", "2.30"], ["I B", "1.20"]],
        }

    def test_min_max(self):
        item = {
            "component": "PivotTable",
            "pivotConfig": {
                "rows": ["Curso"], "cols": [],
                "values": [
                    {"field": "Logro", "aggregation": "min", "label": "Min"},
                    {"field": "Logro", "aggregation": "max", "label": "Max"},
                ],
            },
        }
        assert _table_section(item, _RECORDS) == {
            "columns": ["Curso", "Min", "Max"],
            "rows": [["I A", "0.60", "0.90"], ["I B", "0.50", "0.70"]],
        }

    def test_config_vacia_devuelve_vacio(self):
        item = {"component": "PivotTable", "pivotConfig": {"rows": [], "values": []}}
        assert _table_section(item, _RECORDS) == {"columns": [], "rows": []}

    def test_sin_registros(self):
        item = {
            "component": "PivotTable",
            "pivotConfig": {
                "rows": ["Curso"], "cols": ["Mes"],
                "values": [{"field": "Logro", "aggregation": "avg"}],
            },
        }
        assert _table_section(item, []) == {
            "columns": ["Curso"], "rows": [],
        }
