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
    apply_lookup_dict,
    apply_lookup_range,
    apply_normalize_name,
    apply_row_mean_dynamic,
    apply_row_threshold,
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

class TestEntityCompuesto:
    """Soporte de entity_field como lista de columnas (groupby compuesto).

    Útil cuando no hay un id único de estudiante (ej DIA: usa Curso+Nombre
    en lugar de Rut).
    """
    @pytest.fixture
    def df_dia_sin_rut(self):
        rows = []
        # Mismo Nombre en distintos cursos: deberían tratarse como entidades
        # diferentes con la combinación (Curso, Nombre).
        for curso in ("I A", "II B"):
            for hito_idx, hito in enumerate(("DIAGNOSTICO", "INTERMEDIO", "CIERRE"), start=1):
                rows.append({
                    "Curso": curso,
                    "Nombre": "Juan Pérez",
                    "Hito": hito,
                    "Logro": 0.30 + (hito_idx * 0.10) + (0.05 if curso == "II B" else 0),
                })
        return pd.DataFrame(rows)

    def test_agg_compuesto(self, df_dia_sin_rut):
        out = apply_agg(df_dia_sin_rut, {
            "name": "Promedio",
            "value_field": "Logro",
            "entity_field": ["Curso", "Nombre"],
            "agg": "mean",
        })
        # I A:  0.40, 0.50, 0.60 → 0.50
        # II B: 0.45, 0.55, 0.65 → 0.55
        ia = out[out["Curso"] == "I A"]["Promedio"].iloc[0]
        iib = out[out["Curso"] == "II B"]["Promedio"].iloc[0]
        assert ia == pytest.approx(0.50)
        assert iib == pytest.approx(0.55)

    def test_slope_compuesto_con_time_ordinal(self, df_dia_sin_rut):
        out = apply_slope(df_dia_sin_rut, {
            "name": "Avance",
            "value_field": "Logro",
            "entity_field": ["Curso", "Nombre"],
            "time_field": "Hito",
            "time_type": "ordinal",
            "time_ordinal_levels": ["DIAGNOSTICO", "INTERMEDIO", "CIERRE"],
        })
        # Pendiente perfecta = 0.10
        ia_cierre = out[(out["Curso"] == "I A") & (out["Hito"] == "CIERRE")]["Avance"].iloc[0]
        assert ia_cierre == pytest.approx(0.10, abs=1e-9)

    def test_reaplicacion_no_genera_sufijos(self, df_dia_sin_rut):
        """Re-ejecutar agg/delta con entity compuesto sobre un df que ya
        tiene la columna calculada NO debe agregar sufijos _x/_y."""
        config = {
            "kind": "agg",
            "name": "Promedio",
            "value_field": "Logro",
            "entity_field": ["Curso", "Nombre"],
            "agg": "mean",
        }
        out_1 = apply_agg(df_dia_sin_rut, config)
        out_2 = apply_agg(out_1, config)
        # La columna debe seguir siendo "Promedio" tras la re-aplicación.
        assert "Promedio" in out_2.columns
        assert "Promedio_x" not in out_2.columns
        assert "Promedio_y" not in out_2.columns

    def test_delta_compuesto(self, df_dia_sin_rut):
        out = apply_delta(df_dia_sin_rut, {
            "name": "Mejora",
            "value_field": "Logro",
            "entity_field": ["Curso", "Nombre"],
            "time_field": "Hito",
            "time_type": "ordinal",
            "time_ordinal_levels": ["DIAGNOSTICO", "INTERMEDIO", "CIERRE"],
        })
        # I A: 0.60 - 0.40 = 0.20
        ia = out[out["Curso"] == "I A"]["Mejora"].iloc[0]
        assert ia == pytest.approx(0.20, abs=1e-9)


class TestRowMeanDynamic:
    """Mean horizontal sobre columnas dinámicas (caso DIA)."""

    @pytest.fixture
    def df_dia_xls(self):
        """Replica el shape del XLS DIA: 4 columnas de metadata + N de puntaje."""
        return pd.DataFrame([
            {"Numero Lista": 1, "Nombre del Estudiante": "Juan",
             "Establecimiento": "PHP", "Curso": "1A",
             "Pregunta 1": 100, "Pregunta 2": 80, "Pregunta 3": 60},
            {"Numero Lista": 2, "Nombre del Estudiante": "María",
             "Establecimiento": "PHP", "Curso": "1A",
             "Pregunta 1": 50, "Pregunta 2": 50, "Pregunta 3": 50},
        ])

    def test_exclude_columns_basico(self, df_dia_xls):
        out = apply_row_mean_dynamic(df_dia_xls, {
            "name": "Logro",
            "exclude_columns": ["Numero Lista", "Nombre del Estudiante",
                                "Establecimiento", "Curso"],
            "scale": 0.01,
        })
        # Juan: (100 + 80 + 60) / 3 = 80, * 0.01 = 0.80
        # María: 50, * 0.01 = 0.50
        assert out.loc[0, "Logro"] == pytest.approx(0.80)
        assert out.loc[1, "Logro"] == pytest.approx(0.50)

    def test_include_columns_explicito(self, df_dia_xls):
        out = apply_row_mean_dynamic(df_dia_xls, {
            "name": "Promedio_2_Preguntas",
            "include_columns": ["Pregunta 1", "Pregunta 2"],
        })
        assert out.loc[0, "Promedio_2_Preguntas"] == pytest.approx(90.0)
        assert out.loc[1, "Promedio_2_Preguntas"] == pytest.approx(50.0)

    def test_replace_decimal_comma(self):
        df = pd.DataFrame([
            {"Curso": "1A", "P1": "75,5", "P2": "80,0"},
            {"Curso": "1A", "P1": "60,2", "P2": "70,8"},
        ])
        out = apply_row_mean_dynamic(df, {
            "name": "Logro",
            "exclude_columns": ["Curso"],
            "scale": 0.01,
            "replace_decimal_comma": True,
        })
        # (75.5 + 80.0)/2 = 77.75, * 0.01 = 0.7775
        assert out.loc[0, "Logro"] == pytest.approx(0.7775)
        assert out.loc[1, "Logro"] == pytest.approx(0.6550)

    def test_min_columns_filtra(self):
        df = pd.DataFrame([
            {"Curso": "1A", "P1": 80, "P2": 70, "P3": 60},
            {"Curso": "1A", "P1": 90, "P2": np.nan, "P3": np.nan},
        ])
        out = apply_row_mean_dynamic(df, {
            "name": "Promedio",
            "exclude_columns": ["Curso"],
            "min_columns": 2,
        })
        assert out.loc[0, "Promedio"] == pytest.approx(70.0)
        assert pd.isna(out.loc[1, "Promedio"])

    def test_include_y_exclude_juntos_lanza(self, df_dia_xls):
        with pytest.raises(ValueError, match="ambos"):
            apply_row_mean_dynamic(df_dia_xls, {
                "name": "X",
                "include_columns": ["Pregunta 1"],
                "exclude_columns": ["Curso"],
            })

    def test_include_columns_inexistentes_lanza(self, df_dia_xls):
        with pytest.raises(KeyError, match="inexistentes"):
            apply_row_mean_dynamic(df_dia_xls, {
                "name": "X",
                "include_columns": ["NoExiste"],
            })

    def test_no_muta_original(self, df_dia_xls):
        cols_originales = list(df_dia_xls.columns)
        apply_row_mean_dynamic(df_dia_xls, {
            "name": "Logro",
            "exclude_columns": ["Curso"],
        })
        assert list(df_dia_xls.columns) == cols_originales


class TestRowThreshold:
    """Etiqueta por umbral (caso DIA: Nivel de Logro)."""

    def test_basico_dia_niveles(self):
        df = pd.DataFrame({"Logro": [0.20, 0.40, 0.50, 0.60, 0.80]})
        out = apply_row_threshold(df, {
            "name": "Nivel",
            "value_field": "Logro",
            "thresholds": [
                {"max": 0.4, "label": "Inicial"},
                {"max": 0.6, "label": "Intermedio"},
                {"max": None, "label": "Avanzado"},
            ],
        })
        assert out["Nivel"].tolist() == [
            "Inicial", "Inicial", "Intermedio", "Intermedio", "Avanzado",
        ]

    def test_default_para_nan(self):
        df = pd.DataFrame({"Logro": [0.5, np.nan, 0.9]})
        out = apply_row_threshold(df, {
            "name": "Nivel",
            "value_field": "Logro",
            "default": "Sin Datos",
            "thresholds": [
                {"max": 0.6, "label": "Bajo"},
                {"max": None, "label": "Alto"},
            ],
        })
        assert out.loc[0, "Nivel"] == "Bajo"
        assert out.loc[1, "Nivel"] == "Sin Datos"
        assert out.loc[2, "Nivel"] == "Alto"

    def test_sin_catchall_valores_sobre_ultimo_max_son_nan_o_default(self):
        df = pd.DataFrame({"Logro": [0.5, 0.99]})
        out = apply_row_threshold(df, {
            "name": "Nivel",
            "value_field": "Logro",
            "default": "Fuera",
            "thresholds": [
                {"max": 0.6, "label": "Bajo"},
                {"max": 0.8, "label": "Medio"},
            ],
        })
        assert out.loc[0, "Nivel"] == "Bajo"
        assert out.loc[1, "Nivel"] == "Fuera"

    def test_thresholds_vacios_lanza(self):
        df = pd.DataFrame({"Logro": [0.5]})
        with pytest.raises(ValueError, match="thresholds"):
            apply_row_threshold(df, {
                "name": "X", "value_field": "Logro", "thresholds": [],
            })

    def test_value_field_inexistente_lanza(self):
        df = pd.DataFrame({"Otra": [0.5]})
        with pytest.raises(KeyError, match="value_field"):
            apply_row_threshold(df, {
                "name": "X", "value_field": "Logro",
                "thresholds": [{"max": None, "label": "X"}],
            })

    def test_string_numerico_se_castea(self):
        df = pd.DataFrame({"Logro": ["0.30", "0.70"]})
        out = apply_row_threshold(df, {
            "name": "Nivel",
            "value_field": "Logro",
            "thresholds": [
                {"max": 0.5, "label": "Bajo"},
                {"max": None, "label": "Alto"},
            ],
        })
        assert out["Nivel"].tolist() == ["Bajo", "Alto"]


class TestNormalizeName:
    """Resolver bug DIA de nombres invertidos entre hitos."""

    def test_orden_de_palabras_no_importa(self):
        df = pd.DataFrame([
            {"Hito": "DIAGNOSTICO", "Nombre": "MARIANO JAZIEL ALARCÓN FLORES"},
            {"Hito": "INTERMEDIO", "Nombre": "ALARCÓN FLORES MARIANO JAZIEL"},
        ])
        out = apply_normalize_name(df, {
            "name": "Nombre_Norm",
            "value_field": "Nombre",
        })
        # Ambos deben colapsar a la misma clave (orden alfabético, sin tildes)
        assert out.loc[0, "Nombre_Norm"] == out.loc[1, "Nombre_Norm"]
        assert out.loc[0, "Nombre_Norm"] == "ALARCON FLORES JAZIEL MARIANO"

    def test_strip_accents_default_true(self):
        df = pd.DataFrame({"Nombre": ["José Pérez Núñez"]})
        out = apply_normalize_name(df, {"name": "N", "value_field": "Nombre"})
        # Sin tildes, ordenado alfabéticamente, en mayúsculas
        assert out.loc[0, "N"] == "JOSE NUNEZ PEREZ"

    def test_case_lower(self):
        df = pd.DataFrame({"Nombre": ["Juan PÉREZ"]})
        out = apply_normalize_name(df, {
            "name": "N", "value_field": "Nombre", "case": "lower",
        })
        assert out.loc[0, "N"] == "juan perez"

    def test_case_preserve(self):
        df = pd.DataFrame({"Nombre": ["Pérez Juan"]})
        out = apply_normalize_name(df, {
            "name": "N", "value_field": "Nombre",
            "case": "preserve", "strip_accents": False,
        })
        # Orden alfabético case-insensitive pero preserva mayúsculas originales
        assert out.loc[0, "N"] == "Juan Pérez"

    def test_nan_y_vacios(self):
        df = pd.DataFrame({"Nombre": [None, "", "  ", "Juan Pérez"]})
        out = apply_normalize_name(df, {"name": "N", "value_field": "Nombre"})
        # pandas convierte None a NaN en columnas mixtas; lo importante es
        # que no rompa y que los valores válidos sí se normalicen.
        assert pd.isna(out.loc[0, "N"])
        assert out.loc[1, "N"] == ""
        assert out.loc[2, "N"] == ""
        assert out.loc[3, "N"] == "JUAN PEREZ"

    def test_value_field_inexistente_lanza(self):
        df = pd.DataFrame({"Otra": ["x"]})
        with pytest.raises(KeyError, match="value_field"):
            apply_normalize_name(df, {"name": "N", "value_field": "Nombre"})

    def test_uso_realista_join_entre_hitos(self):
        """Caso de uso real: normalize_name + agg con entity_field compuesto
        permite calcular delta entre hitos cuando los nombres venían
        invertidos."""
        df = pd.DataFrame([
            {"Curso": "I A", "Hito": "DIAG", "Nombre": "MARIANO ALARCON",  "Logro": 0.40},
            {"Curso": "I A", "Hito": "INTER", "Nombre": "ALARCON MARIANO", "Logro": 0.60},
        ])
        configs = [
            {"kind": "normalize_name", "name": "Nombre_Norm",
             "value_field": "Nombre"},
            {"kind": "delta", "name": "Mejora",
             "value_field": "Logro",
             "entity_field": ["Curso", "Nombre_Norm"],
             "time_field": "Hito",
             "time_type": "ordinal",
             "time_ordinal_levels": ["DIAG", "INTER"]},
        ]
        out = apply_derived_fields(df, configs)
        # Ambas filas deben tener Mejora = 0.20 (= 0.60 - 0.40), porque al
        # normalizar caen en la misma entidad. Sin normalize_name esto da NaN.
        assert out["Mejora"].iloc[0] == pytest.approx(0.20)
        assert out["Mejora"].iloc[1] == pytest.approx(0.20)


class TestLookupRange:
    """BUSCARV con tramos (rango verdadero Excel)."""

    def test_basico_3_tramos(self):
        df = pd.DataFrame({"Logro": [0.30, 0.50, 0.85]})
        out = apply_lookup_range(df, {
            "name": "Nivel",
            "value_field": "Logro",
            "ranges": [
                {"min": 0.0, "max": 0.4, "label": "Insuficiente"},
                {"min": 0.4, "max": 0.7, "label": "Adecuado"},
                {"min": 0.7, "max": 1.0, "label": "Avanzado"},
            ],
        })
        assert out["Nivel"].tolist() == ["Insuficiente", "Adecuado", "Avanzado"]

    def test_tramos_abiertos_min_y_max(self):
        df = pd.DataFrame({"x": [-100, 0.5, 1000]})
        out = apply_lookup_range(df, {
            "name": "label",
            "value_field": "x",
            "ranges": [
                {"min": None, "max": 0,    "label": "neg"},
                {"min": 0,    "max": 1,    "label": "med"},
                {"min": 1,    "max": None, "label": "pos"},
            ],
        })
        assert out["label"].tolist() == ["neg", "med", "pos"]

    def test_match_left_inclusive_default(self):
        # min <= v < max
        df = pd.DataFrame({"x": [0.4, 0.7]})  # bordes
        out = apply_lookup_range(df, {
            "name": "L",
            "value_field": "x",
            "ranges": [
                {"min": 0.0, "max": 0.4, "label": "A"},
                {"min": 0.4, "max": 0.7, "label": "B"},
                {"min": 0.7, "max": 1.0, "label": "C"},
            ],
        })
        # 0.4 cae en B (left_inclusive), 0.7 cae en C
        assert out["L"].tolist() == ["B", "C"]

    def test_match_both_inclusive(self):
        df = pd.DataFrame({"x": [0.4, 0.7]})
        out = apply_lookup_range(df, {
            "name": "L",
            "value_field": "x",
            "match": "both_inclusive",
            "ranges": [
                {"min": 0.0, "max": 0.4, "label": "A"},
                {"min": 0.4, "max": 0.7, "label": "B"},
            ],
        })
        # 0.4 cae en el primer rango que matchea (A), 0.7 cae en B
        assert out["L"].tolist() == ["A", "B"]

    def test_default_para_fuera_de_rango_y_nan(self):
        df = pd.DataFrame({"x": [0.5, np.nan, 99.0]})
        out = apply_lookup_range(df, {
            "name": "L",
            "value_field": "x",
            "default": "fuera",
            "ranges": [
                {"min": 0, "max": 1, "label": "in"},
            ],
        })
        assert out["L"].tolist() == ["in", "fuera", "fuera"]

    def test_ranges_vacios_lanza(self):
        df = pd.DataFrame({"x": [1]})
        with pytest.raises(ValueError, match="ranges"):
            apply_lookup_range(df, {
                "name": "L", "value_field": "x", "ranges": [],
            })

    def test_match_invalido_lanza(self):
        df = pd.DataFrame({"x": [1]})
        with pytest.raises(ValueError, match="match"):
            apply_lookup_range(df, {
                "name": "L", "value_field": "x", "match": "weird",
                "ranges": [{"min": 0, "max": 2, "label": "a"}],
            })

    def test_value_field_inexistente_lanza(self):
        df = pd.DataFrame({"otra": [1]})
        with pytest.raises(KeyError, match="value_field"):
            apply_lookup_range(df, {
                "name": "L", "value_field": "x",
                "ranges": [{"min": 0, "max": 1, "label": "a"}],
            })


class TestLookupDict:
    """Mapping discreto valor → label, opcionalmente con extract previo."""

    def test_basico_sin_extract(self):
        df = pd.DataFrame({"Codigo": ["A", "B", "C", "Z"]})
        out = apply_lookup_dict(df, {
            "name": "Etiqueta",
            "value_field": "Codigo",
            "mapping": {"A": "Alfa", "B": "Beta", "C": "Gamma"},
            "default": "Otro",
        })
        assert out["Etiqueta"].tolist() == ["Alfa", "Beta", "Gamma", "Otro"]

    def test_extract_split_basico_dia_curso_nivel(self):
        """Caso real DIA: 'curso = 1 A' → split por ' ' idx 0 → '1' → 'Primeros'."""
        df = pd.DataFrame({"Curso": ["1 A", "2 B", "I A", "III C"]})
        out = apply_lookup_dict(df, {
            "name": "Nivel",
            "value_field": "Curso",
            "mapping": {
                "1": "Primeros", "2": "Segundos",
                "I": "Primeros Medios", "III": "Terceros Medios",
            },
            "extract": {"split": " ", "index": 0},
        })
        assert out["Nivel"].tolist() == [
            "Primeros", "Segundos", "Primeros Medios", "Terceros Medios",
        ]

    def test_extract_regex(self):
        df = pd.DataFrame({"x": ["1° básico A", "II° medio B"]})
        out = apply_lookup_dict(df, {
            "name": "L",
            "value_field": "x",
            "mapping": {"1": "Primeros", "II": "Segundos Medios"},
            "extract": {"regex": r"^[IVX]+|^\d+"},
        })
        assert out["L"].tolist() == ["Primeros", "Segundos Medios"]

    def test_case_insensitive(self):
        df = pd.DataFrame({"x": ["Abc", "DEF"]})
        out = apply_lookup_dict(df, {
            "name": "L",
            "value_field": "x",
            "mapping": {"abc": "uno", "def": "dos"},
            "case_insensitive": True,
        })
        assert out["L"].tolist() == ["uno", "dos"]

    def test_default_para_no_match_y_nan(self):
        df = pd.DataFrame({"x": ["A", "Z", None]})
        out = apply_lookup_dict(df, {
            "name": "L",
            "value_field": "x",
            "mapping": {"A": "uno"},
            "default": "x",
        })
        assert out["L"].tolist() == ["uno", "x", "x"]

    def test_mapping_vacio_lanza(self):
        df = pd.DataFrame({"x": ["A"]})
        with pytest.raises(ValueError, match="mapping"):
            apply_lookup_dict(df, {
                "name": "L", "value_field": "x", "mapping": {},
            })


class TestTemporalValueAt:
    """Kind temporal_value_at: extrae el valor de value_field en la primera
    o última observación temporal por entity, broadcast al grupo.
    """
    def _df(self):
        return pd.DataFrame({
            "Nombre": ["ana", "ana", "ana", "beto", "beto", "cris"],
            "Sub": ["CT", "CT", "CT", "CT", "CT", "CT"],
            "Versión": ["v2", "v3", "v1", "v1", "v3", "v2"],
            "Nivel": ["Crítico", "Bajo", "Crítico", "Alto", "Cierto", "Alto"],
        })

    def test_first_y_last_categorical(self):
        df = apply_derived_fields(self._df(), [
            {"kind": "temporal_value_at", "name": "nivel_v1", "value_field": "Nivel",
             "entity_field": ["Nombre", "Sub"], "time_field": "Versión",
             "when": "first", "time_type": "ordinal", "time_ordinal_levels": ["v1","v2","v3"]},
            {"kind": "temporal_value_at", "name": "nivel_final", "value_field": "Nivel",
             "entity_field": ["Nombre", "Sub"], "time_field": "Versión",
             "when": "last", "time_type": "ordinal", "time_ordinal_levels": ["v1","v2","v3"]},
        ])
        # ana CT: v1=Crítico, v3=Bajo
        ana = df[df["Nombre"] == "ana"].iloc[0]
        assert ana["nivel_v1"] == "Crítico"
        assert ana["nivel_final"] == "Bajo"
        # beto CT: v1=Alto, v3=Cierto
        beto = df[df["Nombre"] == "beto"].iloc[0]
        assert beto["nivel_v1"] == "Alto"
        assert beto["nivel_final"] == "Cierto"
        # cris CT: solo v2 → ambos = Alto
        cris = df[df["Nombre"] == "cris"].iloc[0]
        assert cris["nivel_v1"] == "Alto"
        assert cris["nivel_final"] == "Alto"

    def test_min_points_filtra(self):
        # cris solo tiene 1 versión; con min_points=2 debe ser NaN
        df = apply_derived_fields(self._df(), [
            {"kind": "temporal_value_at", "name": "nivel_v1", "value_field": "Nivel",
             "entity_field": ["Nombre", "Sub"], "time_field": "Versión",
             "when": "first", "time_type": "ordinal", "time_ordinal_levels": ["v1","v2","v3"],
             "min_points": 2},
        ])
        ana = df[df["Nombre"] == "ana"].iloc[0]
        assert ana["nivel_v1"] == "Crítico"
        cris = df[df["Nombre"] == "cris"].iloc[0]
        assert pd.isna(cris["nivel_v1"])

    def test_when_invalido_explota(self):
        with pytest.raises(ValueError, match="when"):
            apply_derived_fields(self._df(), [
                {"kind": "temporal_value_at", "name": "x", "value_field": "Nivel",
                 "entity_field": ["Nombre"], "time_field": "Versión",
                 "when": "middle", "time_type": "ordinal",
                 "time_ordinal_levels": ["v1","v2","v3"]},
            ])

    def test_value_field_inexistente_explota(self):
        with pytest.raises(KeyError, match="NoExiste"):
            apply_derived_fields(self._df(), [
                {"kind": "temporal_value_at", "name": "x", "value_field": "NoExiste",
                 "entity_field": ["Nombre"], "time_field": "Versión",
                 "time_type": "ordinal", "time_ordinal_levels": ["v1","v2","v3"]},
            ])


class TestRegistry:
    def test_kinds_esperados(self):
        assert set(KIND_REGISTRY.keys()) == {
            "agg", "slope", "delta",
            "row_mean_dynamic", "row_threshold", "normalize_name",
            "lookup_range", "lookup_dict", "piecewise_linear",
            "temporal_value_at",
        }

    def test_metadata_introspection_first_check(self):
        """Sentinel para detectar si el iter del registry pasa los kinds."""
        for kind, spec in KIND_REGISTRY.items():
            assert callable(spec["fn"])

    def test_metadata_introspection(self):
        for kind, spec in KIND_REGISTRY.items():
            assert "fn" in spec
            assert "display_name" in spec
            assert "description" in spec
            assert "required_args" in spec
            assert "name" in spec["required_args"]
