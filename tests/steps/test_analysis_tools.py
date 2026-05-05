"""Tests de rgenerator.tooling.analysis_tools."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rgenerator.tooling.analysis_tools import (
    DIA_MILESTONES_ORDINAL,
    establishment_gap,
    item_discrimination,
    milestone_delta_per_group,
    milestone_slope_per_group,
    performance_quartiles,
    student_risk_flag,
)


# ─────────────────────────────────────────────────────────────────────────
# student_risk_flag
# ─────────────────────────────────────────────────────────────────────────


def test_risk_flag_threshold_simple():
    df = pd.DataFrame({"Logro": [0.3, 0.5, 0.2, 0.7, np.nan]})
    out = student_risk_flag(df)
    assert out.tolist() == [True, False, True, False, False]


def test_risk_flag_custom_threshold():
    df = pd.DataFrame({"Logro": [0.4, 0.5, 0.6]})
    out = student_risk_flag(df, threshold=0.5)
    assert out.tolist() == [True, False, False]


def test_risk_flag_with_negative_slope():
    df = pd.DataFrame({"Logro": [0.3, 0.3, 0.7], "slope": [-0.1, 0.1, -0.5]})
    out = student_risk_flag(
        df, require_negative_slope=True, slope_col="slope"
    )
    assert out.tolist() == [True, False, False]


def test_risk_flag_missing_column():
    with pytest.raises(KeyError):
        student_risk_flag(pd.DataFrame({"X": [1]}))


# ─────────────────────────────────────────────────────────────────────────
# milestone_slope_per_group
# ─────────────────────────────────────────────────────────────────────────


def test_slope_per_group_two_milestones():
    df = pd.DataFrame({
        "Curso": ["A", "A", "A"],
        "Hito": ["DIAGNOSTICO", "INTERMEDIO", "CIERRE"],
        "Logro": [0.4, 0.55, 0.7],
    })
    out = milestone_slope_per_group(df, ["Curso"], "Hito", "Logro")
    assert len(out) == 1
    row = out.iloc[0]
    assert row["Curso"] == "A"
    assert row["n_hitos"] == 3
    assert abs(row["slope"] - 0.15) < 1e-6
    assert row["score_inicial"] == 0.4
    assert row["score_final"] == 0.7


def test_slope_negative():
    df = pd.DataFrame({
        "Curso": ["B", "B"],
        "Hito": ["DIAGNOSTICO", "CIERRE"],
        "Logro": [0.7, 0.5],
    })
    out = milestone_slope_per_group(df, ["Curso"], "Hito", "Logro")
    assert out.iloc[0]["slope"] < 0


def test_slope_ignores_unknown_milestones():
    df = pd.DataFrame({
        "Curso": ["A", "A", "A"],
        "Hito": ["DIAGNOSTICO", "MID", "CIERRE"],
        "Logro": [0.4, 0.99, 0.6],
    })
    out = milestone_slope_per_group(df, ["Curso"], "Hito", "Logro")
    assert out.iloc[0]["n_hitos"] == 2
    assert abs(out.iloc[0]["slope"] - 0.1) < 1e-6


def test_slope_multi_group_keys():
    df = pd.DataFrame({
        "Establecimiento": ["E1", "E1", "E2", "E2"],
        "Curso": ["A", "A", "A", "A"],
        "Hito": ["DIAGNOSTICO", "CIERRE", "DIAGNOSTICO", "CIERRE"],
        "Logro": [0.5, 0.7, 0.6, 0.55],
    })
    out = milestone_slope_per_group(
        df, ["Establecimiento", "Curso"], "Hito", "Logro"
    )
    assert len(out) == 2
    e1 = out[out["Establecimiento"] == "E1"].iloc[0]
    e2 = out[out["Establecimiento"] == "E2"].iloc[0]
    assert e1["slope"] > 0
    assert e2["slope"] < 0


# ─────────────────────────────────────────────────────────────────────────
# milestone_delta_per_group
# ─────────────────────────────────────────────────────────────────────────


def test_delta_basic():
    df = pd.DataFrame({
        "Curso": ["A", "A", "B", "B"],
        "Hito": ["DIAGNOSTICO", "CIERRE", "DIAGNOSTICO", "CIERRE"],
        "Logro": [0.5, 0.7, 0.6, 0.55],
    })
    out = milestone_delta_per_group(df, ["Curso"], "Hito", "Logro")
    a = out[out["Curso"] == "A"].iloc[0]
    b = out[out["Curso"] == "B"].iloc[0]
    assert abs(a["delta"] - 0.2) < 1e-6
    assert abs(b["delta"] - (-0.05)) < 1e-6


def test_delta_missing_milestone_yields_nan():
    df = pd.DataFrame({
        "Curso": ["A", "A"],
        "Hito": ["DIAGNOSTICO", "INTERMEDIO"],
        "Logro": [0.5, 0.6],
    })
    out = milestone_delta_per_group(df, ["Curso"], "Hito", "Logro")
    assert out.iloc[0]["score_fin"] != out.iloc[0]["score_fin"]  # NaN


# ─────────────────────────────────────────────────────────────────────────
# establishment_gap
# ─────────────────────────────────────────────────────────────────────────


def test_gap_two_establishments():
    df = pd.DataFrame({
        "Establecimiento": ["A", "A", "B", "B"],
        "Curso": ["1°", "2°", "1°", "2°"],
        "Logro": [0.6, 0.7, 0.5, 0.8],
    })
    out = establishment_gap(df, "Logro")
    assert "A" in out.columns
    assert "B" in out.columns
    assert "gap" in out.columns
    primero = out[out["Curso"] == "1°"].iloc[0]
    assert abs(primero["gap"] - 0.1) < 1e-6


def test_gap_single_establishment_no_gap_col():
    df = pd.DataFrame({
        "Establecimiento": ["A", "A"],
        "Curso": ["1°", "2°"],
        "Logro": [0.6, 0.7],
    })
    out = establishment_gap(df, "Logro")
    assert "gap" not in out.columns


# ─────────────────────────────────────────────────────────────────────────
# item_discrimination
# ─────────────────────────────────────────────────────────────────────────


def test_item_discrimination_buena():
    # Caso ideal: buenos estudiantes aciertan, malos fallan -> alta discriminación
    df = pd.DataFrame({
        "estudiante": ["s1"] * 5 + ["s2"] * 5 + ["s3"] * 5,
        "item": ["P1", "P2", "P3", "P4", "P5"] * 3,
        "ok": [
            1, 1, 1, 1, 1,   # s1: aciertos altos
            1, 1, 0, 0, 0,   # s2: medio
            0, 0, 0, 0, 0,   # s3: aciertos bajos
        ],
    })
    out = item_discrimination(df, "estudiante", "item", "ok")
    p1 = out[out["item"] == "P1"].iloc[0]
    assert p1["dificultad"] == pytest.approx(2 / 3)
    assert p1["discriminacion"] is not None
    assert p1["discriminacion"] > 0.5


def test_item_discrimination_handles_constant_item():
    df = pd.DataFrame({
        "estudiante": ["s1", "s2", "s3"],
        "item": ["P1", "P1", "P1"],
        "ok": [1, 1, 1],
    })
    out = item_discrimination(df, "estudiante", "item", "ok")
    row = out.iloc[0]
    assert row["dificultad"] == 1.0
    assert row["discriminacion"] is None
    assert row["calidad"] == "revisar"


def test_item_discrimination_empty_df():
    df = pd.DataFrame({"estudiante": [], "item": [], "ok": []})
    out = item_discrimination(df, "estudiante", "item", "ok")
    assert out.empty


# ─────────────────────────────────────────────────────────────────────────
# performance_quartiles
# ─────────────────────────────────────────────────────────────────────────


def test_quartiles_basic():
    df = pd.DataFrame({
        "Curso": ["A"] * 5 + ["B"] * 5,
        "Logro": [0.1, 0.3, 0.5, 0.7, 0.9, 0.4, 0.5, 0.6, 0.7, 0.8],
    })
    out = performance_quartiles(df, "Curso", "Logro")
    a = out[out["Curso"] == "A"].iloc[0]
    assert a["n"] == 5
    assert a["mediana"] == 0.5
    assert a["IQR"] == pytest.approx(0.4)


# ─────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────


def test_dia_milestones_canonical():
    assert DIA_MILESTONES_ORDINAL == ("DIAGNOSTICO", "INTERMEDIO", "CIERRE")
