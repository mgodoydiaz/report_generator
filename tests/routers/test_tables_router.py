"""Tests del router /api/tables y sus helpers puros (B7).

Cubre:
- Validación del schema Pydantic (TableConfig, TableCreate, TableColumn,
  ColorScale variants).
- Helpers `_apply_format` y `_resolve_color_for_value`.

Los tests E2E del CRUD vs DB se hacen vía curl al container Docker
(ver `tests/routers/test_tables_router_e2e.sh` cuando se sumen).
"""
from __future__ import annotations

import pytest

# Tests requieren pydantic + sqlalchemy + fastapi (entorno backend). En la
# env Python 3.13 host esos no están — saltea limpio para que los tests
# del engine/etl se sigan corriendo localmente sin levantar el container.
pytest.importorskip("pydantic")
pytest.importorskip("sqlalchemy")
pytest.importorskip("fastapi")

from pydantic import ValidationError  # noqa: E402

from backend.schemas_table import (  # noqa: E402
    ColorScaleDiverging,
    ColorScaleLinkedIndicator,
    ColorScaleSequential,
    TableColumn,
    TableConfig,
    TableCreate,
    TableDataSource,
    TableUpdate,
)
from backend.routers.tables import _apply_format, _resolve_color_for_value  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────


class TestTableColumn:
    def test_minimal(self):
        c = TableColumn(key="Logro", header="Logro")
        assert c.format == "text"
        assert c.agg is None
        assert c.color_scale is None
        assert c.pinned is False
        assert c.hidden is False

    def test_format_invalido_lanza(self):
        with pytest.raises(ValidationError):
            TableColumn(key="x", header="X", format="weird")

    def test_agg_invalido_lanza(self):
        with pytest.raises(ValidationError):
            TableColumn(key="x", header="X", agg="weird")

    def test_color_scale_linked_indicator(self):
        c = TableColumn(key="Logro", header="Logro", color_scale={
            "kind": "linked_indicator", "indicator_id": 5, "level_field": "Nivel"
        })
        assert isinstance(c.color_scale, ColorScaleLinkedIndicator)
        assert c.color_scale.indicator_id == 5

    def test_color_scale_diverging_defaults(self):
        c = TableColumn(key="Avance", header="Avance", color_scale={"kind": "diverging"})
        assert isinstance(c.color_scale, ColorScaleDiverging)
        assert c.color_scale.midpoint == 0.0
        assert c.color_scale.min_color == "#ef4444"

    def test_color_scale_sequential(self):
        c = TableColumn(key="x", header="X", color_scale={
            "kind": "sequential", "base_color": "#000000"
        })
        assert isinstance(c.color_scale, ColorScaleSequential)


class TestTableConfig:
    def test_minimal_valid(self):
        cfg = TableConfig(data_source={"metric_id": 6})
        assert cfg.version == 1
        assert cfg.data_source.metric_id == 6
        assert cfg.columns == []
        assert cfg.behavior.pagination.page_size == 50

    def test_completo(self):
        cfg = TableConfig(
            data_source={"metric_id": 6, "filters": {"Año": 2026}},
            columns=[
                {"key": "Curso", "header": "Curso", "format": "text"},
                {
                    "key": "Logro", "header": "Logro", "format": "percent",
                    "agg": "mean",
                    "color_scale": {"kind": "linked_indicator",
                                    "indicator_id": 5, "level_field": "Nivel Logro"},
                },
            ],
            behavior={
                "grouping": {"by": "Curso"},
                "sorting": [{"column": "Logro", "dir": "desc"}],
                "pagination": {"page_size": 25},
                "search": False,
            },
        )
        assert len(cfg.columns) == 2
        assert cfg.behavior.grouping.by == "Curso"
        assert cfg.behavior.sorting[0].dir == "desc"
        assert cfg.behavior.pagination.page_size == 25
        assert cfg.behavior.search is False

    def test_metric_id_obligatorio(self):
        with pytest.raises(ValidationError):
            TableConfig(data_source={})

    def test_serializable(self):
        cfg = TableConfig(data_source={"metric_id": 6})
        d = cfg.model_dump()
        assert d["data_source"]["metric_id"] == 6
        # Roundtrip
        cfg2 = TableConfig(**d)
        assert cfg2.data_source.metric_id == 6


class TestTableCreate:
    def test_create_valido(self):
        payload = TableCreate(
            name="Logro DIA Lectura",
            description="Tabla resumen por curso",
            config={"data_source": {"metric_id": 6}},
        )
        assert payload.is_draft is True
        assert payload.config.data_source.metric_id == 6

    def test_name_obligatorio(self):
        with pytest.raises(ValidationError):
            TableCreate(config={"data_source": {"metric_id": 6}})


class TestTableUpdate:
    def test_partial(self):
        upd = TableUpdate(name="Nuevo nombre")
        assert upd.name == "Nuevo nombre"
        assert upd.config is None
        assert upd.is_draft is None


# ─────────────────────────────────────────────────────────────────────────
# Helpers de formato
# ─────────────────────────────────────────────────────────────────────────


class TestApplyFormat:
    def test_text(self):
        assert _apply_format("hola", "text") == "hola"
        assert _apply_format(123, "text") == "123"

    def test_int(self):
        assert _apply_format(42, "int") == "42"
        assert _apply_format(42.7, "int") == "42"
        assert _apply_format("x", "int") == "x"

    def test_float_default_1_decimal(self):
        assert _apply_format(3.14159, "float") == "3.1"
        assert _apply_format(3.14159, "float", decimals=3) == "3.142"

    def test_percent(self):
        assert _apply_format(0.4567, "percent") == "45.7%"
        assert _apply_format(0.5, "percent", decimals=0) == "50%"

    def test_none_y_nan(self):
        import math
        assert _apply_format(None, "percent") == ""
        assert _apply_format(float("nan"), "float") == ""

    def test_date_passthrough(self):
        assert _apply_format("2026-05-04", "date") == "2026-05-04"


# ─────────────────────────────────────────────────────────────────────────
# Color scales
# ─────────────────────────────────────────────────────────────────────────


class TestResolveColor:
    def test_linked_indicator_match(self):
        scale = {"kind": "linked_indicator", "indicator_id": 5, "level_field": "Nivel Logro"}
        cache = {5: [
            {"name": "Inicial",     "color": "#ef4444"},
            {"name": "Intermedio",  "color": "#f59e0b"},
            {"name": "Avanzado",    "color": "#22c55e"},
        ]}
        row = {"Nivel Logro": "Intermedio"}
        assert _resolve_color_for_value(0.5, scale, row, cache) == "#f59e0b"

    def test_linked_indicator_case_insensitive(self):
        scale = {"kind": "linked_indicator", "indicator_id": 5, "level_field": "N"}
        cache = {5: [{"name": "AVANZADO", "color": "#0f0"}]}
        assert _resolve_color_for_value(1, scale, {"N": "avanzado"}, cache) == "#0f0"

    def test_linked_indicator_sin_match(self):
        scale = {"kind": "linked_indicator", "indicator_id": 5, "level_field": "N"}
        cache = {5: [{"name": "X", "color": "#fff"}]}
        assert _resolve_color_for_value(1, scale, {"N": "Z"}, cache) is None

    def test_diverging(self):
        scale = {
            "kind": "diverging", "min_color": "#f00",
            "neutral_color": "#fff", "max_color": "#0f0", "midpoint": 0,
        }
        assert _resolve_color_for_value(-0.1, scale, {}, {}) == "#f00"
        assert _resolve_color_for_value(0, scale, {}, {}) == "#fff"
        assert _resolve_color_for_value(0.1, scale, {}, {}) == "#0f0"

    def test_diverging_midpoint_no_cero(self):
        scale = {"kind": "diverging", "min_color": "#f00",
                 "neutral_color": "#fff", "max_color": "#0f0", "midpoint": 0.5}
        assert _resolve_color_for_value(0.4, scale, {}, {}) == "#f00"
        assert _resolve_color_for_value(0.6, scale, {}, {}) == "#0f0"

    def test_sequential(self):
        scale = {"kind": "sequential", "base_color": "#3b82f6"}
        assert _resolve_color_for_value(0.5, scale, {}, {}) == "#3b82f6"

    def test_nan_devuelve_none(self):
        scale = {"kind": "diverging", "min_color": "#f00",
                 "neutral_color": "#fff", "max_color": "#0f0", "midpoint": 0}
        assert _resolve_color_for_value(None, scale, {}, {}) is None
        assert _resolve_color_for_value(float("nan"), scale, {}, {}) is None
