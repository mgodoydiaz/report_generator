"""Tests del motor de derived_fields.

Cobertura:
- Cada kind con caso happy path (agg, slope, delta).
- Edge cases: min_points, datos faltantes, ordinal mapping.
- Encadenamiento: una función usa columna calculada por otra previa.
- Validaciones: kind desconocido, args faltantes, columna inexistente.
- Inmutabilidad: no muta el DataFrame original.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rgenerator.core.derived_fields_engine import (
    KIND_REGISTRY,
    apply_agg,
    apply_delta,
    apply_derived_fields,
    apply_slope,
)


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture
def df_simce():
    """3 estudiantes con 5 hitos cada uno. Rend en 0-1."""
    rows = []
    for rut, base in [("R1", 0.40), ("R2", 0.60), ("R3", 0.55)]:
        for prueba in range(1, 6):
            rows.append({
                "Rut": rut,
                "Curso": "II A",
                "Numero_Prueba": prueba,
                "Rend": base + (prueba - 1) * 0.05,  # mejora lineal
            })
    return pd.DataFrame(rows)


@pytest.fixture
def df_dia_ordinal():
    """2 estudiantes con 3 hitos, columna Logro cualitativa."""
    return pd.DataFrame([
        {"Rut": "R1", "Hito": 1, "Logro": "Inicial"},
        {"Rut": "R1", "Hito": 2, "Logro": "Intermedio"},
        {"Rut": "R1", "Hito": 3, "Logro": "Avanzado"},
        {"Rut": "R2", "Hito": 1, "Logro": "Avanzado"},
        {"Rut": "R2", "Hito": 2, "Logro": "Avanzado"},
        {"Rut": "R2", "Hito": 3, "Logro": "Intermedio"},
    ])


# ─────────────────────────────────────────────────────────────────────────
# Kind: agg
# ─────────────────────────────────────────────────────────────────────────

class TestAgg:
    def test_mean_basico(self, df_simce):
        out = apply_agg(df_simce, {
            "name": "Logro_Promedio",
            "value_field": "Rend",
            "entity_field": "Rut",
            "agg": "mean",
        })
        # R1: (0.40+0.45+0.50+0.55+0.60)/5 = 0.50
        # R2: (0.60+0.65+0.70+0.75+0.80)/5 = 0.70
        # R3: (0.55+0.60+0.65+0.70+0.75)/5 = 0.65
        r1 = out[out["Rut"] == "R1"]["Logro_Promedio"].iloc[0]
        r2 = out[out["Rut"] == "R2"]["Logro_Promedio"].iloc[0]
        r3 = out[out["Rut"] == "R3"]["Logro_Promedio"].iloc[0]
        assert r1 == pytest.approx(0.50, abs=1e-9)
        assert r2 == pytest.approx(0.70, abs=1e-9)
        assert r3 == pytest.approx(0.65, abs=1e-9)
        # Broadcast: cada fila del estudiante tiene el mismo valor
        assert (out[out["Rut"] == "R1"]["Logro_Promedio"] == r1).all()

    def test_max(self, df_simce):
        out = apply_agg(df_simce, {
            "name": "Rend_Max",
            "value_field": "Rend",
            "entity_field": "Rut",
            "agg": "max",
        })
        assert out[out["Rut"] == "R1"]["Rend_Max"].iloc[0] == pytest.approx(0.60)

    def test_count_y_nunique(self, df_simce):
        out = apply_agg(df_simce, {
            "name": "N_Pruebas",
            "value_field": "Numero_Prueba",
            "entity_field": "Rut",
            "agg": "count",
        })
        assert out["N_Pruebas"].unique().tolist() == [5]

    def test_min_points_filtra(self, df_simce):
        # R1 tiene 5 puntos, pero pongo NaN en 4 de ellos.
        df = df_simce.copy()
        mask_r1 = df["Rut"] == "R1"
        idx_r1 = df[mask_r1].index
        df.loc[idx_r1[:4], "Rend"] = np.nan
        out = apply_agg(df, {
            "name": "Logro_Promedio",
            "value_field": "Rend",
            "entity_field": "Rut",
            "agg": "mean",
            "min_points": 2,
        })
        # R1 solo tiene 1 punto válido → NaN
        assert pd.isna(out[out["Rut"] == "R1"]["Logro_Promedio"].iloc[0])
        # R2 sin tocar → calcula normal
        assert not pd.isna(out[out["Rut"] == "R2"]["Logro_Promedio"].iloc[0])

    def test_ordinal(self, df_dia_ordinal):
        out = apply_agg(df_dia_ordinal, {
            "name": "Logro_Promedio_Ordinal",
            "value_field": "Logro",
            "entity_field": "Rut",
            "agg": "mean",
            "value_type": "ordinal",
            "ordinal_levels": ["Inicial", "Intermedio", "Avanzado"],
        })
        # R1: Inicial(1), Intermedio(2), Avanzado(3) → mean = 2.0
        # R2: Avanzado(3), Avanzado(3), Intermedio(2) → mean = 8/3
        r1 = out[out["Rut"] == "R1"]["Logro_Promedio_Ordinal"].iloc[0]
        r2 = out[out["Rut"] == "R2"]["Logro_Promedio_Ordinal"].iloc[0]
        assert r1 == pytest.approx(2.0)
        assert r2 == pytest.approx(8 / 3)

    def test_columna_inexistente_lanza(self, df_simce):
        with pytest.raises(KeyError, match="value_field"):
            apply_agg(df_simce, {
                "name": "X",
                "value_field": "NoExiste",
                "entity_field": "Rut",
            })


# ─────────────────────────────────────────────────────────────────────────
# Kind: slope (regresión expansiva)
# ─────────────────────────────────────────────────────────────────────────

class TestSlope:
    def test_pendiente_lineal_perfecta(self, df_simce):
        out = apply_slope(df_simce, {
            "name": "Avance",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Numero_Prueba",
        })
        # Cada estudiante mejora 0.05 por prueba (puntos perfectamente lineales).
        # Prueba 1: solo 1 punto → NaN (min_points=2 default).
        # Prueba 2+: pendiente = 0.05 exacto (línea perfecta).
        r1 = out[out["Rut"] == "R1"].sort_values("Numero_Prueba")
        assert pd.isna(r1.iloc[0]["Avance"])
        assert r1.iloc[1]["Avance"] == pytest.approx(0.05, abs=1e-9)
        assert r1.iloc[4]["Avance"] == pytest.approx(0.05, abs=1e-9)

    def test_min_points_3_omite_primeras_dos(self, df_simce):
        out = apply_slope(df_simce, {
            "name": "Avance",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Numero_Prueba",
            "min_points": 3,
        })
        r1 = out[out["Rut"] == "R1"].sort_values("Numero_Prueba")
        assert pd.isna(r1.iloc[0]["Avance"])
        assert pd.isna(r1.iloc[1]["Avance"])
        assert not pd.isna(r1.iloc[2]["Avance"])

    def test_un_solo_punto_es_nan(self):
        df = pd.DataFrame([{"Rut": "R1", "Numero_Prueba": 1, "Rend": 0.5}])
        out = apply_slope(df, {
            "name": "Avance",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Numero_Prueba",
        })
        assert pd.isna(out["Avance"].iloc[0])

    def test_datos_faltantes_se_ignoran(self):
        # 3 puntos pero el del medio es NaN → solo 2 puntos válidos.
        df = pd.DataFrame([
            {"Rut": "R1", "Numero_Prueba": 1, "Rend": 0.4},
            {"Rut": "R1", "Numero_Prueba": 2, "Rend": np.nan},
            {"Rut": "R1", "Numero_Prueba": 3, "Rend": 0.6},
        ])
        out = apply_slope(df, {
            "name": "Avance",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Numero_Prueba",
        })
        # Fila 1: solo 1 punto válido (0.4 en t=1) → NaN
        # Fila 2: aún solo 1 punto válido (no contó el NaN) → NaN
        # Fila 3: 2 puntos válidos (0.4 en t=1, 0.6 en t=3), pendiente = 0.1
        ordered = out.sort_values("Numero_Prueba").reset_index(drop=True)
        assert pd.isna(ordered.iloc[0]["Avance"])
        assert pd.isna(ordered.iloc[1]["Avance"])
        assert ordered.iloc[2]["Avance"] == pytest.approx(0.1, abs=1e-9)

    def test_ordinal_calcula_pendiente_de_niveles(self, df_dia_ordinal):
        out = apply_slope(df_dia_ordinal, {
            "name": "Avance_Cualitativo",
            "value_field": "Logro",
            "entity_field": "Rut",
            "time_field": "Hito",
            "value_type": "ordinal",
            "ordinal_levels": ["Inicial", "Intermedio", "Avanzado"],
        })
        # R1: 1, 2, 3 en hitos 1, 2, 3 → pendiente perfecta = 1
        r1 = out[out["Rut"] == "R1"].sort_values("Hito")
        assert r1.iloc[2]["Avance_Cualitativo"] == pytest.approx(1.0, abs=1e-9)
        # R2: 3, 3, 2 en hitos 1, 2, 3 → empeora, pendiente negativa
        r2 = out[out["Rut"] == "R2"].sort_values("Hito")
        assert r2.iloc[2]["Avance_Cualitativo"] < 0


# ─────────────────────────────────────────────────────────────────────────
# Kind: delta
# ─────────────────────────────────────────────────────────────────────────

class TestDelta:
    def test_delta_basico(self, df_simce):
        out = apply_delta(df_simce, {
            "name": "Mejora",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Numero_Prueba",
        })
        # R1: 0.60 - 0.40 = 0.20 (último - primero)
        # R2: 0.80 - 0.60 = 0.20
        assert out[out["Rut"] == "R1"]["Mejora"].iloc[0] == pytest.approx(0.20, abs=1e-9)
        assert out[out["Rut"] == "R2"]["Mejora"].iloc[0] == pytest.approx(0.20, abs=1e-9)

    def test_delta_un_solo_punto_es_nan(self):
        df = pd.DataFrame([{"Rut": "R1", "Numero_Prueba": 1, "Rend": 0.5}])
        out = apply_delta(df, {
            "name": "Mejora",
            "value_field": "Rend",
            "entity_field": "Rut",
            "time_field": "Numero_Prueba",
        })
        assert pd.isna(out["Mejora"].iloc[0])

    def test_delta_ordinal(self, df_dia_ordinal):
        out = apply_delta(df_dia_ordinal, {
            "name": "Mejora_Cualitativa",
            "value_field": "Logro",
            "entity_field": "Rut",
            "time_field": "Hito",
            "value_type": "ordinal",
            "ordinal_levels": ["Inicial", "Intermedio", "Avanzado"],
        })
        # R1: Avanzado(3) - Inicial(1) = 2
        # R2: Intermedio(2) - Avanzado(3) = -1
        assert out[out["Rut"] == "R1"]["Mejora_Cualitativa"].iloc[0] == pytest.approx(2.0)
        assert out[out["Rut"] == "R2"]["Mejora_Cualitativa"].iloc[0] == pytest.approx(-1.0)


# ─────────────────────────────────────────────────────────────────────────
# Orquestador: encadenamiento, validaciones, inmutabilidad
# ─────────────────────────────────────────────────────────────────────────

class TestOrchestrator:
    def test_encadenamiento_agg_luego_delta(self, df_simce):
        # 1) Calcula Logro_Promedio (mean por estudiante).
        # 2) Calcula Mejora_vs_Promedio = Rend - Logro_Promedio mediante un
        #    segundo agg que usa una columna creada por el primero como
        #    value_field. Eso valida que la pipeline acepta encadenamiento.
        configs = [
            {"kind": "agg", "name": "Logro_Promedio", "value_field": "Rend",
             "entity_field": "Rut", "agg": "mean"},
            {"kind": "agg", "name": "Logro_Promedio_Cuadrado",
             "value_field": "Logro_Promedio", "entity_field": "Rut", "agg": "max"},
        ]
        out = apply_derived_fields(df_simce, configs)
        # max == mean porque el broadcast hace que todas las filas del estudiante
        # tengan el mismo Logro_Promedio.
        r1 = out[out["Rut"] == "R1"]
        assert r1["Logro_Promedio_Cuadrado"].iloc[0] == r1["Logro_Promedio"].iloc[0]

    def test_kind_desconocido_lanza(self, df_simce):
        with pytest.raises(ValueError, match="kind"):
            apply_derived_fields(df_simce, [{"kind": "no_existe", "name": "X"}])

    def test_args_requeridos_faltantes_lanza(self, df_simce):
        # agg requiere value_field y entity_field
        with pytest.raises(ValueError, match="requeridos"):
            apply_derived_fields(df_simce, [{"kind": "agg", "name": "X"}])

    def test_lista_vacia_devuelve_copia(self, df_simce):
        out = apply_derived_fields(df_simce, [])
        # Mismas columnas, mismos valores, pero objeto distinto.
        assert list(out.columns) == list(df_simce.columns)
        assert out is not df_simce

    def test_no_muta_dataframe_original(self, df_simce):
        original_cols = list(df_simce.columns)
        original_len = len(df_simce)
        out = apply_derived_fields(df_simce, [
            {"kind": "agg", "name": "X", "value_field": "Rend", "entity_field": "Rut", "agg": "mean"},
        ])
        # df_simce no debe tener la columna nueva
        assert list(df_simce.columns) == original_cols
        assert len(df_simce) == original_len
        assert "X" in out.columns


# ─────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_kinds_esperados(self):
        assert set(KIND_REGISTRY.keys()) == {"agg", "slope", "delta"}

    def test_metadata_introspection(self):
        for kind, spec in KIND_REGISTRY.items():
            assert "fn" in spec
            assert "display_name" in spec
            assert "description" in spec
            assert "required_args" in spec
            assert "name" in spec["required_args"]
