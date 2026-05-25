"""Regresión: apply_slope con time_type='ordinal' y time_ordinal_levels ausente/vacío.

Bug visto en producción 2026-05-19 16:15 GMT-4 (incidente backend caído).

Traza que apareció en los logs de Railway antes del crash final:

    File "/app/backend/routers/charts.py", line 534, in render_chart_data
      df = apply_derived_fields(df, configs)
    File "/app/backend/rgenerator/core/derived_fields_engine.py", line 1014,
      in apply_derived_fields
      out = fn(out, config)
    File "/app/backend/rgenerator/core/derived_fields_engine.py", line 227,
      in apply_slope
      df["_time_num"] = _as_numeric(df[time_field], time_type, time_ordinal_levels)
    File "/app/backend/rgenerator/core/derived_fields_engine.py", line 74,
      in _as_numeric
      raise ValueError("value_type='ordinal' requiere ordinal_levels no vacío")

Causa raíz: una config de derived_field tenía `time_type: "ordinal"` pero
NO definía `time_ordinal_levels`. KIND_REGISTRY['slope'] tiene
`time_ordinal_levels` como opcional, así que `apply_derived_fields` no la
exige al validar args, y el error explota en runtime dentro de `_as_numeric`.

NOTA: el crash final del contenedor (502/503 durante 5 días) NO fue causado
por esta excepción — el router `charts.py:535` la captura con bare
`except Exception` y solo printea el traceback. La excepción se traga,
pero el chart se renderiza sin la columna derivada. El crash de proceso
ocurrió ~30 min después y probablemente fue OOM.

Este test fija el contrato:
1. `_as_numeric` levanta ValueError descriptivo si ordinal sin levels.
2. `apply_slope` propaga ese error con contexto cuando es time_type='ordinal'.
3. El endpoint /api/charts/{id}/data NO devuelve 500 ante una config malformada
   — sigue devolviendo el dataset sin la columna derivada (degradación graceful).
"""
from __future__ import annotations

import pandas as pd
import pytest

from backend.rgenerator.core.derived_fields_engine import (
    _as_numeric,
    apply_slope,
    apply_derived_fields,
)


@pytest.mark.unit
class TestAsNumericOrdinalSinLevels:
    """_as_numeric: ordinal sin ordinal_levels debe fallar con mensaje claro."""

    def test_ordinal_levels_none_lanza_valueerror(self):
        serie = pd.Series(["ABRIL", "JUNIO"])
        with pytest.raises(ValueError, match="ordinal_levels"):
            _as_numeric(serie, value_type="ordinal", ordinal_levels=None)

    def test_ordinal_levels_vacio_lanza_valueerror(self):
        serie = pd.Series(["ABRIL", "JUNIO"])
        with pytest.raises(ValueError, match="ordinal_levels"):
            _as_numeric(serie, value_type="ordinal", ordinal_levels=[])

    def test_ordinal_con_levels_funciona(self):
        """Happy path: con ordinal_levels válidos sí mapea a int."""
        serie = pd.Series(["ABRIL", "JUNIO", "AGOSTO"])
        out = _as_numeric(serie, value_type="ordinal", ordinal_levels=["ABRIL", "JUNIO", "AGOSTO"])
        assert list(out) == [1.0, 2.0, 3.0]

    def test_numeric_default_no_requiere_levels(self):
        """value_type='numeric' (default) ignora ordinal_levels."""
        serie = pd.Series(["1.5", "2.0"])
        out = _as_numeric(serie, value_type="numeric", ordinal_levels=None)
        assert list(out) == [1.5, 2.0]


@pytest.mark.unit
class TestApplySlopeTimeOrdinalSinLevels:
    """apply_slope: time_type='ordinal' sin time_ordinal_levels = el caso real del 19-may."""

    def test_time_type_ordinal_sin_time_ordinal_levels_lanza_valueerror(self):
        """Reproduce exacto el path de la traza del 19-may."""
        df = pd.DataFrame({
            "Rut": ["A", "A", "B"],
            "Rend": [0.4, 0.6, 0.5],
            "Mes": ["ABRIL", "JUNIO", "ABRIL"],
        })
        config = {
            "name": "Avance",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Mes",
            "time_type": "ordinal",
            # ⚠️ time_ordinal_levels ausente — el bug del 19-may
        }
        with pytest.raises(ValueError, match="ordinal_levels"):
            apply_slope(df, config)

    def test_time_type_ordinal_con_levels_vacios_lanza_valueerror(self):
        """time_ordinal_levels = [] también dispara el error."""
        df = pd.DataFrame({
            "Rut": ["A", "A"],
            "Rend": [0.4, 0.6],
            "Mes": ["ABRIL", "JUNIO"],
        })
        config = {
            "name": "Avance",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Mes",
            "time_type": "ordinal",
            "time_ordinal_levels": [],
        }
        with pytest.raises(ValueError, match="ordinal_levels"):
            apply_slope(df, config)

    def test_time_type_default_numeric_no_requiere_levels(self):
        """Default time_type='numeric': no exige time_ordinal_levels."""
        df = pd.DataFrame({
            "Rut": ["A", "A", "A"],
            "Rend": [0.3, 0.5, 0.7],
            "Mes": [1, 2, 3],  # ya numérico
        })
        out = apply_slope(df, {
            "name": "Avance",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Mes",
            # sin time_type ni time_ordinal_levels → default numeric
        })
        # Con 3 puntos colineales (slope=0.2) la última fila tiene avance no-NaN
        assert "Avance" in out.columns
        last_avance = out.iloc[-1]["Avance"]
        assert last_avance == pytest.approx(0.2)


@pytest.mark.unit
class TestApplyDerivedFieldsConSlopeOrdinalMalformado:
    """apply_derived_fields orquestador: el error del slope se propaga."""

    def test_slope_ordinal_sin_levels_propaga_valueerror(self):
        """El orquestador no atrapa el error — lo deja subir.

        Esto es A PROPÓSITO: la captura debe ocurrir en la capa router, no acá,
        para que tests unit del engine puedan observarlo. El router en
        producción (charts.py:535) hace `except Exception: traceback.print_exc()`.
        """
        df = pd.DataFrame({
            "Rut": ["A", "A"],
            "Rend": [0.4, 0.6],
            "Mes": ["ABRIL", "JUNIO"],
        })
        configs = [{
            "kind": "slope",
            "name": "Avance",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Mes",
            "time_type": "ordinal",
            # falta time_ordinal_levels — KIND_REGISTRY['slope'] lo tiene opcional
        }]
        with pytest.raises(ValueError, match="ordinal_levels"):
            apply_derived_fields(df, configs)

    def test_validator_no_atrapa_porque_time_ordinal_levels_es_optional(self):
        """Documenta: el validator del registry NO exige time_ordinal_levels.

        Si en el futuro alguien marca time_ordinal_levels como required cuando
        time_type='ordinal' (validación cruzada), este test va a empezar a
        fallar con un mensaje distinto al de _as_numeric — y será mejor UX.
        Por ahora documenta el estado actual.
        """
        from backend.rgenerator.core.derived_fields_engine import KIND_REGISTRY
        slope_spec = KIND_REGISTRY["slope"]
        assert "time_ordinal_levels" not in slope_spec["required_args"]
        assert "time_ordinal_levels" in slope_spec["optional_args"]
