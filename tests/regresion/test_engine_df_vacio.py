"""Regresión: apply_delta y apply_slope sobre DataFrame vacío.

Bug visto en producción 2026-05-19: cuando un filtro previo dejaba el df
con 0 filas, `apply_delta` construía `pd.DataFrame([])` (sin columnas) y
hacía `df.merge(deltas_df, on=entity_keys)` → pandas lanzaba
`KeyError: 'Rut'` (la primera entity_key). Error confuso que ocultaba la
causa real (df vacío).

Fix en commit a498648: si delta_records está vacío, asignar df[name] =
NaN sin merge. Idéntico para slope.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.rgenerator.core.derived_fields_engine import (
    apply_delta,
    apply_slope,
    apply_derived_fields,
)


@pytest.mark.unit
class TestApplyDeltaDfVacio:
    def test_delta_df_vacio_devuelve_columna_nan(self):
        """df sin filas pero con columnas correctas no debe romper."""
        df = pd.DataFrame({"Rut": [], "Rend": [], "Mes": []})
        out = apply_delta(df, {
            "name": "Mejora",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Mes",
            "time_type": "ordinal",
            "time_ordinal_levels": ["ABRIL", "JUNIO"],
        })
        assert "Mejora" in out.columns
        assert len(out) == 0

    def test_delta_df_con_filas_pero_sin_min_points(self):
        """1 fila por entidad → delta NaN (min_points=2), no error."""
        df = pd.DataFrame({
            "Rut": ["A", "B"],
            "Rend": [0.5, 0.6],
            "Mes": ["ABRIL", "JUNIO"],
        })
        out = apply_delta(df, {
            "name": "Mejora",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Mes",
            "time_type": "ordinal",
            "time_ordinal_levels": ["ABRIL", "JUNIO"],
        })
        # Cada entidad tiene 1 punto → NaN
        assert out["Mejora"].isna().all()

    def test_delta_normal_funciona(self):
        """Sanity: con datos válidos sí calcula delta."""
        df = pd.DataFrame({
            "Rut": ["A", "A", "B", "B"],
            "Rend": [0.4, 0.7, 0.5, 0.6],
            "Mes": ["ABRIL", "JUNIO", "ABRIL", "JUNIO"],
        })
        out = apply_delta(df, {
            "name": "Mejora",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Mes",
            "time_type": "ordinal",
            "time_ordinal_levels": ["ABRIL", "JUNIO"],
        })
        # Entidad A: 0.7 - 0.4 = 0.3; B: 0.6 - 0.5 = 0.1
        rows_a = out[out["Rut"] == "A"]["Mejora"].unique()
        assert len(rows_a) == 1
        assert rows_a[0] == pytest.approx(0.3)


@pytest.mark.unit
class TestApplySlopeDfVacio:
    def test_slope_df_vacio_devuelve_columna_nan(self):
        df = pd.DataFrame({"Rut": [], "Rend": [], "Mes": []})
        out = apply_slope(df, {
            "name": "Avance",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Mes",
            "time_type": "ordinal",
            "time_ordinal_levels": ["ABRIL", "JUNIO"],
        })
        assert "Avance" in out.columns
        assert len(out) == 0

    def test_slope_normal_funciona(self):
        df = pd.DataFrame({
            "Rut": ["A", "A", "A"],
            "Rend": [0.3, 0.5, 0.7],
            "Mes": ["ABRIL", "JUNIO", "AGOSTO"],
        })
        out = apply_slope(df, {
            "name": "Avance",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Mes",
            "time_type": "ordinal",
            "time_ordinal_levels": ["ABRIL", "JUNIO", "AGOSTO"],
        })
        # Última fila tiene la slope completa (3 puntos): mejora 0.2 por hito
        assert not out["Avance"].isna().all()


@pytest.mark.unit
def test_apply_derived_fields_simce_config_completo_sobre_df_vacio():
    """Reproduce exactamente el escenario del bug en producción:
    el esquema de SIMCE corre agg + slope + delta sobre Rend con
    entity_field=Rut, y al llegar con df vacío no debe romper."""
    df = pd.DataFrame({"Rut": [], "Rend": [], "Mes": []})
    configs = [
        {
            "kind": "agg",
            "name": "Logro_Promedio_Estudiante",
            "value_field": "Rend",
            "entity_field": "Rut",
            "agg": "mean",
            "min_points": 1,
        },
        {
            "kind": "slope",
            "name": "Avance",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Mes",
            "time_type": "ordinal",
            "time_ordinal_levels": ["ABRIL", "JUNIO", "AGOSTO", "OCTUBRE", "OCTUBRE 2"],
            "min_points": 2,
        },
        {
            "kind": "delta",
            "name": "Mejora_vs_Inicio",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Mes",
            "time_type": "ordinal",
            "time_ordinal_levels": ["ABRIL", "JUNIO", "AGOSTO", "OCTUBRE", "OCTUBRE 2"],
            "min_points": 2,
        },
    ]
    # Antes del fix esto lanzaba KeyError: 'Rut'. Ahora debe pasar limpio.
    out = apply_derived_fields(df, configs)
    assert "Logro_Promedio_Estudiante" in out.columns
    assert "Avance" in out.columns
    assert "Mejora_vs_Inicio" in out.columns
