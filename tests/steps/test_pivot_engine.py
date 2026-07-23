"""Tests del motor de pivotes (W2-A).

Cobertura (correctitud matemática es lo crítico):
- Cada agregación con resultado calculado a mano (mean/sum/count/nunique/
  min/max/median/std).
- Semántica de totales: el total de un promedio = promedio del conjunto, NO
  promedio de promedios (test explícito).
- Porcentajes pct_row/pct_col/pct_total: suman lo que deben; división por
  cero; NaN en la fuente.
- Multinivel en rows y cols; multi-value.
- Orden custom y orden por defecto.
- Formato display sin perder el value crudo.
- Bordes: df vacío, campo inexistente, una sola fila, columna no numérica.
- pivot_to_dataframe consistente con el PivotResult.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from backend.schemas_pivot import PivotSpec, PivotValue
from backend.rgenerator.core.pivot_engine import (
    PivotCell,
    PivotResult,
    pivot,
    pivot_to_dataframe,
)


# ─────────────────────────────────────────────────────────────────────────
# Helpers de acceso al resultado
# ─────────────────────────────────────────────────────────────────────────

def cell_at(result: PivotResult, row_keys, col_keys, *, is_total_row=False, is_total_col=False):
    """Devuelve la PivotCell de la fila con `row_keys` y la columna con
    `col_keys` (listas). `is_total_*` selecciona la fila/columna Total."""
    # localizar columna
    col_idx = None
    for j, col in enumerate(result.columns):
        if col.is_total == is_total_col and list(col.keys) == list(col_keys):
            col_idx = j
            break
    assert col_idx is not None, f"columna no encontrada: keys={col_keys} total={is_total_col}"
    for row in result.rows:
        if row.is_total == is_total_row and list(row.keys) == list(row_keys):
            return row.cells[col_idx]
    raise AssertionError(f"fila no encontrada: keys={row_keys} total={is_total_row}")


def approx(x):
    return pytest.approx(x, rel=1e-9, abs=1e-12)


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture
def df_simple():
    """Curso × Mes con Logro numérico. Combinación (B, Abril) ausente."""
    return pd.DataFrame([
        {"Curso": "A", "Mes": "Marzo", "Logro": 0.8},
        {"Curso": "A", "Mes": "Marzo", "Logro": 0.9},
        {"Curso": "A", "Mes": "Abril", "Logro": 1.0},
        {"Curso": "B", "Mes": "Marzo", "Logro": 0.4},
        {"Curso": "B", "Mes": "Marzo", "Logro": 0.6},
    ])


@pytest.fixture
def df_niveles():
    """Curso × Nivel para tests de distribución/porcentaje (conteos)."""
    rows = []
    # Curso A: 3 Alto, 1 Bajo
    for _ in range(3):
        rows.append({"Curso": "A", "Nivel": "Alto", "Rut": f"a{len(rows)}"})
    rows.append({"Curso": "A", "Nivel": "Bajo", "Rut": f"a{len(rows)}"})
    # Curso B: 1 Alto, 1 Bajo
    rows.append({"Curso": "B", "Nivel": "Alto", "Rut": f"b{len(rows)}"})
    rows.append({"Curso": "B", "Nivel": "Bajo", "Rut": f"b{len(rows)}"})
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────
# Agregaciones básicas (valores calculados a mano)
# ─────────────────────────────────────────────────────────────────────────

def test_mean_por_grupo(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "mean"}],
                          "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], ["Marzo"]).value == approx(0.85)
    assert cell_at(r, ["A"], ["Abril"]).value == approx(1.0)
    assert cell_at(r, ["B"], ["Marzo"]).value == approx(0.5)
    # (B, Abril) ausente → None
    assert cell_at(r, ["B"], ["Abril"]).value is None


def test_sum(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "sum"}],
                          "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], ["Marzo"]).value == approx(1.7)
    assert cell_at(r, ["B"], ["Marzo"]).value == approx(1.0)


def test_count(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "count"}],
                          "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], ["Marzo"]).value == 2
    assert cell_at(r, ["A"], ["Abril"]).value == 1
    assert cell_at(r, ["B"], ["Marzo"]).value == 2


def test_nunique():
    df = pd.DataFrame([
        {"Curso": "A", "Prof": "x"},
        {"Curso": "A", "Prof": "x"},
        {"Curso": "A", "Prof": "y"},
        {"Curso": "B", "Prof": "z"},
    ])
    r = pivot(df, {"rows": ["Curso"], "values": [{"field": "Prof", "agg": "nunique"}],
                  "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], []).value == 2
    assert cell_at(r, ["B"], []).value == 1


def test_min_max(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"],
                          "values": [{"field": "Logro", "agg": "min"},
                                     {"field": "Logro", "agg": "max"}],
                          "totals": {"rows": False, "cols": False}})
    # sin cols → una columna por métrica (keys vacías); localizar por índice
    assert r.rows[0].keys == ["A"]
    assert r.rows[0].cells[0].value == approx(0.8)   # min A
    assert r.rows[0].cells[1].value == approx(1.0)   # max A
    assert r.rows[1].cells[0].value == approx(0.4)   # min B
    assert r.rows[1].cells[1].value == approx(0.6)   # max B


def test_median():
    df = pd.DataFrame([
        {"G": "A", "V": 1.0}, {"G": "A", "V": 3.0}, {"G": "A", "V": 100.0},
        {"G": "B", "V": 2.0}, {"G": "B", "V": 4.0},
    ])
    r = pivot(df, {"rows": ["G"], "values": [{"field": "V", "agg": "median"}],
                  "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], []).value == approx(3.0)
    assert cell_at(r, ["B"], []).value == approx(3.0)


def test_std_muestral():
    df = pd.DataFrame([
        {"G": "A", "V": 2.0}, {"G": "A", "V": 4.0}, {"G": "A", "V": 6.0},
    ])
    r = pivot(df, {"rows": ["G"], "values": [{"field": "V", "agg": "std"}],
                  "totals": {"rows": False, "cols": False}})
    # std muestral (ddof=1) de [2,4,6] = 2.0
    assert cell_at(r, ["A"], []).value == approx(2.0)


def test_std_un_solo_dato_es_nan():
    df = pd.DataFrame([{"G": "A", "V": 5.0}])
    r = pivot(df, {"rows": ["G"], "values": [{"field": "V", "agg": "std"}],
                  "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], []).value is None


# ─────────────────────────────────────────────────────────────────────────
# Semántica de totales (el punto crítico)
# ─────────────────────────────────────────────────────────────────────────

def test_total_de_promedio_no_es_promedio_de_promedios(df_simple):
    """El total de un mean es el mean del conjunto, NO el mean de las celdas.

    Curso A: Marzo mean=0.85, Abril mean=1.0. El promedio de promedios sería
    (0.85+1.0)/2 = 0.925. El correcto es mean(0.8,0.9,1.0) = 0.9.
    """
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "mean"}],
                          "totals": {"rows": True, "cols": True}})
    total_A = cell_at(r, ["A"], ["Total"], is_total_col=True)
    assert total_A.value == approx(0.9)
    assert total_A.value != approx(0.925)  # el bug clásico


def test_total_fila_es_agg_del_conjunto(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "mean"}],
                          "totals": {"rows": True, "cols": True}})
    # Fila Total, columna Marzo = mean de todos los Marzo (0.8,0.9,0.4,0.6)
    total_marzo = cell_at(r, ["Total"], ["Marzo"], is_total_row=True)
    assert total_marzo.value == approx((0.8 + 0.9 + 0.4 + 0.6) / 4)


def test_esquina_total_total(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "mean"}],
                          "totals": {"rows": True, "cols": True}})
    corner = cell_at(r, ["Total"], ["Total"], is_total_row=True, is_total_col=True)
    assert corner.value == approx((0.8 + 0.9 + 1.0 + 0.4 + 0.6) / 5)


def test_total_sum_coincide_con_suma_de_celdas(df_simple):
    """Para sum el total = suma total (coincide con suma de celdas)."""
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "sum"}],
                          "totals": {"rows": True, "cols": True}})
    total_A = cell_at(r, ["A"], ["Total"], is_total_col=True)
    assert total_A.value == approx(0.8 + 0.9 + 1.0)


def test_total_min_max_del_conjunto(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "max"}],
                          "totals": {"rows": True, "cols": True}})
    corner = cell_at(r, ["Total"], ["Total"], is_total_row=True, is_total_col=True)
    assert corner.value == approx(1.0)


def test_no_totales_no_agrega_filas_ni_columnas(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "mean"}],
                          "totals": {"rows": False, "cols": False}})
    assert all(not row.is_total for row in r.rows)
    assert all(not col.is_total for col in r.columns)
    assert r.meta.has_totals == {"rows": False, "cols": False}


def test_col_total_no_se_emite_sin_campos_de_columna(df_simple):
    """Con cols=[] no hay columna Total (sería redundante)."""
    r = pivot(df_simple, {"rows": ["Curso"],
                          "values": [{"field": "Logro", "agg": "mean"}],
                          "totals": {"rows": True, "cols": True}})
    assert all(not col.is_total for col in r.columns)
    assert r.meta.has_totals["cols"] is False
    # pero sí hay fila Total (mean global)
    total_row = [row for row in r.rows if row.is_total]
    assert len(total_row) == 1
    assert total_row[0].cells[0].value == approx((0.8 + 0.9 + 1.0 + 0.4 + 0.6) / 5)


# ─────────────────────────────────────────────────────────────────────────
# Porcentajes
# ─────────────────────────────────────────────────────────────────────────

def test_pct_row_suma_100_por_fila(df_niveles):
    r = pivot(df_niveles, {"rows": ["Curso"], "cols": ["Nivel"],
                           "values": [{"field": "Rut", "agg": "pct_row"}],
                           "totals": {"rows": True, "cols": True}})
    # Curso A: 3 Alto de 4 = 0.75, 1 Bajo de 4 = 0.25
    assert cell_at(r, ["A"], ["Alto"]).value == approx(0.75)
    assert cell_at(r, ["A"], ["Bajo"]).value == approx(0.25)
    # suma por fila = 1.0
    suma_A = cell_at(r, ["A"], ["Alto"]).value + cell_at(r, ["A"], ["Bajo"]).value
    assert suma_A == approx(1.0)
    # columna Total de la fila = 100%
    assert cell_at(r, ["A"], ["Total"], is_total_col=True).value == approx(1.0)


def test_pct_col_suma_100_por_columna(df_niveles):
    r = pivot(df_niveles, {"rows": ["Curso"], "cols": ["Nivel"],
                           "values": [{"field": "Rut", "agg": "pct_col"}],
                           "totals": {"rows": True, "cols": True}})
    # Columna Alto: A=3, B=1, total 4 → A=0.75, B=0.25
    assert cell_at(r, ["A"], ["Alto"]).value == approx(0.75)
    assert cell_at(r, ["B"], ["Alto"]).value == approx(0.25)
    suma_alto = cell_at(r, ["A"], ["Alto"]).value + cell_at(r, ["B"], ["Alto"]).value
    assert suma_alto == approx(1.0)
    # fila Total de la columna = 100%
    assert cell_at(r, ["Total"], ["Alto"], is_total_row=True).value == approx(1.0)


def test_pct_total_suma_100_global(df_niveles):
    r = pivot(df_niveles, {"rows": ["Curso"], "cols": ["Nivel"],
                           "values": [{"field": "Rut", "agg": "pct_total"}],
                           "totals": {"rows": True, "cols": True}})
    # 6 registros. (A,Alto)=3/6=0.5, (A,Bajo)=1/6, (B,Alto)=1/6, (B,Bajo)=1/6
    assert cell_at(r, ["A"], ["Alto"]).value == approx(0.5)
    assert cell_at(r, ["A"], ["Bajo"]).value == approx(1 / 6)
    total = sum(
        cell_at(r, [c], [n]).value
        for c in ["A", "B"] for n in ["Alto", "Bajo"]
    )
    assert total == approx(1.0)
    # esquina = 100%
    corner = cell_at(r, ["Total"], ["Total"], is_total_row=True, is_total_col=True)
    assert corner.value == approx(1.0)


def test_pct_total_columna_total_es_pct_de_la_fila(df_niveles):
    r = pivot(df_niveles, {"rows": ["Curso"], "cols": ["Nivel"],
                           "values": [{"field": "Rut", "agg": "pct_total"}],
                           "totals": {"rows": True, "cols": True}})
    # columna Total de A = 4/6
    assert cell_at(r, ["A"], ["Total"], is_total_col=True).value == approx(4 / 6)


def test_pct_celda_ausente_es_cero():
    """Combinación sin registros → 0% (no NaN)."""
    df = pd.DataFrame([
        {"Curso": "A", "Nivel": "Alto", "Rut": "1"},
        {"Curso": "A", "Nivel": "Alto", "Rut": "2"},
        {"Curso": "B", "Nivel": "Bajo", "Rut": "3"},
    ])
    r = pivot(df, {"rows": ["Curso"], "cols": ["Nivel"],
                  "values": [{"field": "Rut", "agg": "pct_row"}],
                  "totals": {"rows": False, "cols": False}})
    # (A, Bajo) ausente → 0.0
    assert cell_at(r, ["A"], ["Bajo"]).value == approx(0.0)
    assert cell_at(r, ["A"], ["Alto"]).value == approx(1.0)


def test_pct_division_por_cero_da_cero():
    """Si una columna tiene conteo 0 (todos NaN en el field), pct_col = 0."""
    df = pd.DataFrame([
        {"Curso": "A", "Nivel": "Alto", "Rut": "1"},
        {"Curso": "A", "Nivel": "Vacio", "Rut": None},
        {"Curso": "B", "Nivel": "Vacio", "Rut": None},
    ])
    r = pivot(df, {"rows": ["Curso"], "cols": ["Nivel"],
                  "values": [{"field": "Rut", "agg": "pct_col"}],
                  "totals": {"rows": False, "cols": False}})
    # columna "Vacio" tiene 0 no-nulos → todas las celdas 0.0
    assert cell_at(r, ["A"], ["Vacio"]).value == approx(0.0)
    assert cell_at(r, ["B"], ["Vacio"]).value == approx(0.0)
    # columna "Alto" A tiene 1 de 1 → 1.0
    assert cell_at(r, ["A"], ["Alto"]).value == approx(1.0)


def test_pct_display_por_defecto_es_porcentaje(df_niveles):
    """Sin format explícito, un pct_* se muestra como porcentaje (.1%)."""
    r = pivot(df_niveles, {"rows": ["Curso"], "cols": ["Nivel"],
                           "values": [{"field": "Rut", "agg": "pct_row"}],
                           "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], ["Alto"]).display == "75.0%"


# ─────────────────────────────────────────────────────────────────────────
# NaN en la fuente
# ─────────────────────────────────────────────────────────────────────────

def test_nan_en_valor_se_excluye_del_mean():
    df = pd.DataFrame([
        {"G": "A", "V": 1.0},
        {"G": "A", "V": np.nan},
        {"G": "A", "V": 3.0},
    ])
    r = pivot(df, {"rows": ["G"], "values": [{"field": "V", "agg": "mean"}],
                  "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], []).value == approx(2.0)  # (1+3)/2, NaN excluido


def test_nan_en_valor_count_cuenta_no_nulos():
    df = pd.DataFrame([
        {"G": "A", "V": 1.0}, {"G": "A", "V": np.nan}, {"G": "A", "V": 3.0},
    ])
    r = pivot(df, {"rows": ["G"], "values": [{"field": "V", "agg": "count"}],
                  "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], []).value == 2


def test_grupo_todo_nan_da_none():
    df = pd.DataFrame([
        {"G": "A", "V": np.nan}, {"G": "A", "V": np.nan},
        {"G": "B", "V": 5.0},
    ])
    r = pivot(df, {"rows": ["G"], "values": [{"field": "V", "agg": "mean"}],
                  "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], []).value is None


# ─────────────────────────────────────────────────────────────────────────
# Multinivel y multi-value
# ─────────────────────────────────────────────────────────────────────────

def test_rows_multinivel():
    df = pd.DataFrame([
        {"Colegio": "X", "Curso": "A", "V": 10.0},
        {"Colegio": "X", "Curso": "B", "V": 20.0},
        {"Colegio": "Y", "Curso": "A", "V": 30.0},
    ])
    r = pivot(df, {"rows": ["Colegio", "Curso"],
                  "values": [{"field": "V", "agg": "sum"}],
                  "totals": {"rows": False, "cols": False}})
    assert r.row_fields == ["Colegio", "Curso"]
    assert cell_at(r, ["X", "A"], []).value == approx(10.0)
    assert cell_at(r, ["X", "B"], []).value == approx(20.0)
    assert cell_at(r, ["Y", "A"], []).value == approx(30.0)


def test_cols_multinivel():
    df = pd.DataFrame([
        {"Curso": "A", "Anio": "2024", "Sem": "1", "V": 1.0},
        {"Curso": "A", "Anio": "2024", "Sem": "2", "V": 2.0},
        {"Curso": "A", "Anio": "2025", "Sem": "1", "V": 3.0},
    ])
    r = pivot(df, {"rows": ["Curso"], "cols": ["Anio", "Sem"],
                  "values": [{"field": "V", "agg": "sum"}],
                  "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], ["2024", "1"]).value == approx(1.0)
    assert cell_at(r, ["A"], ["2024", "2"]).value == approx(2.0)
    assert cell_at(r, ["A"], ["2025", "1"]).value == approx(3.0)
    # combinación de columnas ausente (2025, 2) NO se emite (present-only,
    # no producto cartesiano de niveles)
    assert ["2025", "2"] not in [c.keys for c in r.columns]
    assert [c.keys for c in r.columns] == [["2024", "1"], ["2024", "2"], ["2025", "1"]]


def test_multi_value_dos_metricas(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [
                              {"field": "Logro", "agg": "mean", "label": "Prom"},
                              {"field": "Logro", "agg": "count", "label": "N"},
                          ],
                          "totals": {"rows": False, "cols": False}})
    # layout: por cada col (Marzo, Abril) las 2 métricas
    labels = [(c.keys, c.label) for c in r.columns]
    assert (["Marzo"], "Prom") in labels
    assert (["Marzo"], "N") in labels
    # localizar por índice: primera columna Marzo/Prom
    col_marzo_prom = next(j for j, c in enumerate(r.columns) if c.keys == ["Marzo"] and c.label == "Prom")
    col_marzo_n = next(j for j, c in enumerate(r.columns) if c.keys == ["Marzo"] and c.label == "N")
    row_A = next(row for row in r.rows if row.keys == ["A"])
    assert row_A.cells[col_marzo_prom].value == approx(0.85)
    assert row_A.cells[col_marzo_n].value == 2


def test_multi_value_mezcla_mean_y_pct(df_niveles):
    """Una métrica mean y otra pct en la misma tabla, independientes."""
    df = df_niveles.copy()
    df["Puntaje"] = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    r = pivot(df, {"rows": ["Curso"], "cols": ["Nivel"],
                  "values": [
                      {"field": "Puntaje", "agg": "mean"},
                      {"field": "Rut", "agg": "pct_row"},
                  ],
                  "totals": {"rows": False, "cols": False}})
    col_alto_mean = next(j for j, c in enumerate(r.columns) if c.keys == ["Alto"] and c.agg == "mean")
    col_alto_pct = next(j for j, c in enumerate(r.columns) if c.keys == ["Alto"] and c.agg == "pct_row")
    row_A = next(row for row in r.rows if row.keys == ["A"])
    assert row_A.cells[col_alto_mean].value == approx((10 + 20 + 30) / 3)
    assert row_A.cells[col_alto_pct].value == approx(0.75)


# ─────────────────────────────────────────────────────────────────────────
# Orden
# ─────────────────────────────────────────────────────────────────────────

def test_orden_custom_respetado():
    df = pd.DataFrame([
        {"Mes": "Abril", "V": 1.0},
        {"Mes": "Marzo", "V": 2.0},
        {"Mes": "Mayo", "V": 3.0},
    ])
    r = pivot(df, {"rows": ["Mes"],
                  "values": [{"field": "V", "agg": "sum"}],
                  "order": {"Mes": ["Marzo", "Abril", "Mayo"]},
                  "totals": {"rows": False, "cols": False}})
    assert [row.keys[0] for row in r.rows] == ["Marzo", "Abril", "Mayo"]


def test_orden_custom_valores_no_listados_van_al_final():
    df = pd.DataFrame([
        {"Mes": "Junio", "V": 1.0},
        {"Mes": "Marzo", "V": 2.0},
        {"Mes": "Abril", "V": 3.0},
    ])
    r = pivot(df, {"rows": ["Mes"],
                  "values": [{"field": "V", "agg": "sum"}],
                  "order": {"Mes": ["Marzo", "Abril"]},
                  "totals": {"rows": False, "cols": False}})
    # Marzo, Abril primero (listados); Junio después (natural)
    assert [row.keys[0] for row in r.rows] == ["Marzo", "Abril", "Junio"]


def test_orden_por_defecto_natural_numerico():
    df = pd.DataFrame([
        {"N": 10, "V": 1.0}, {"N": 2, "V": 2.0}, {"N": 1, "V": 3.0},
    ])
    r = pivot(df, {"rows": ["N"], "values": [{"field": "V", "agg": "sum"}],
                  "totals": {"rows": False, "cols": False}})
    # orden numérico natural: 1, 2, 10 (no alfabético "1","10","2")
    assert [row.keys[0] for row in r.rows] == ["1", "2", "10"]


def test_orden_columnas_custom():
    df = pd.DataFrame([
        {"Curso": "A", "Mes": "Abril", "V": 1.0},
        {"Curso": "A", "Mes": "Marzo", "V": 2.0},
    ])
    r = pivot(df, {"rows": ["Curso"], "cols": ["Mes"],
                  "values": [{"field": "V", "agg": "sum"}],
                  "order": {"Mes": ["Marzo", "Abril"]},
                  "totals": {"rows": False, "cols": False}})
    assert [c.keys for c in r.columns] == [["Marzo"], ["Abril"]]


# ─────────────────────────────────────────────────────────────────────────
# Formato display
# ─────────────────────────────────────────────────────────────────────────

def test_format_percent_conserva_value_crudo(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "mean", "format": ".1%"}],
                          "totals": {"rows": False, "cols": False}})
    cell = cell_at(r, ["A"], ["Marzo"])
    assert cell.display == "85.0%"
    assert cell.value == approx(0.85)  # value sigue crudo


def test_format_float_2f():
    df = pd.DataFrame([{"G": "A", "V": 3.14159}, {"G": "A", "V": 3.14159}])
    r = pivot(df, {"rows": ["G"], "values": [{"field": "V", "agg": "mean", "format": ".2f"}],
                  "totals": {"rows": False, "cols": False}})
    cell = cell_at(r, ["A"], [])
    assert cell.display == "3.14"
    assert cell.value == approx(3.14159)


def test_format_count_por_defecto_entero(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "count"}],
                          "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], ["Marzo"]).display == "2"


def test_display_vacio_para_celda_ausente(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "mean", "format": ".1%"}],
                          "totals": {"rows": False, "cols": False}})
    cell = cell_at(r, ["B"], ["Abril"])
    assert cell.value is None
    assert cell.display == ""


def test_fill_value_numerico(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "mean", "format": ".1f"}],
                          "fill_value": 0,
                          "totals": {"rows": False, "cols": False}})
    cell = cell_at(r, ["B"], ["Abril"])
    assert cell.value == approx(0.0)
    assert cell.display == "0.0"


# ─────────────────────────────────────────────────────────────────────────
# Bordes / errores
# ─────────────────────────────────────────────────────────────────────────

def test_df_vacio_no_crashea():
    df = pd.DataFrame(columns=["Curso", "Mes", "Logro"])
    r = pivot(df, {"rows": ["Curso"], "cols": ["Mes"],
                  "values": [{"field": "Logro", "agg": "mean"}]})
    assert isinstance(r, PivotResult)
    assert r.rows == []
    assert r.columns == []
    assert r.meta.n_source_rows == 0


def test_campo_inexistente_error_claro():
    df = pd.DataFrame([{"Curso": "A", "Logro": 0.5}])
    with pytest.raises(ValueError) as exc:
        pivot(df, {"rows": ["NoExiste"], "values": [{"field": "Logro", "agg": "mean"}]})
    assert "NoExiste" in str(exc.value)
    assert "Columnas disponibles" in str(exc.value)


def test_campo_valor_inexistente_error():
    df = pd.DataFrame([{"Curso": "A", "Logro": 0.5}])
    with pytest.raises(ValueError) as exc:
        pivot(df, {"rows": ["Curso"], "values": [{"field": "Fantasma", "agg": "mean"}]})
    assert "Fantasma" in str(exc.value)


def test_una_sola_fila():
    df = pd.DataFrame([{"Curso": "A", "Mes": "Marzo", "Logro": 0.7}])
    r = pivot(df, {"rows": ["Curso"], "cols": ["Mes"],
                  "values": [{"field": "Logro", "agg": "mean"}],
                  "totals": {"rows": True, "cols": True}})
    assert cell_at(r, ["A"], ["Marzo"]).value == approx(0.7)
    # todos los totales = 0.7
    assert cell_at(r, ["A"], ["Total"], is_total_col=True).value == approx(0.7)
    assert cell_at(r, ["Total"], ["Marzo"], is_total_row=True).value == approx(0.7)
    corner = cell_at(r, ["Total"], ["Total"], is_total_row=True, is_total_col=True)
    assert corner.value == approx(0.7)


def test_columna_no_numerica_con_mean_coerciona():
    """mean sobre columna con texto: se coerciona; texto no parseable → NaN
    excluido."""
    df = pd.DataFrame([
        {"G": "A", "V": "10"},
        {"G": "A", "V": "20"},
        {"G": "A", "V": "abc"},  # no parseable → NaN
    ])
    r = pivot(df, {"rows": ["G"], "values": [{"field": "V", "agg": "mean"}],
                  "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], []).value == approx(15.0)  # (10+20)/2


def test_count_sobre_texto_funciona():
    df = pd.DataFrame([
        {"G": "A", "V": "x"}, {"G": "A", "V": "y"}, {"G": "B", "V": "z"},
    ])
    r = pivot(df, {"rows": ["G"], "values": [{"field": "V", "agg": "count"}],
                  "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], []).value == 2
    assert cell_at(r, ["B"], []).value == 1


def test_spec_sin_values_falla():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PivotSpec(rows=["Curso"], values=[])


def test_spec_sin_rows_falla():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PivotSpec(rows=[], values=[PivotValue(field="V", agg="mean")])


def test_acepta_pivotspec_instancia(df_simple):
    spec = PivotSpec(rows=["Curso"], values=[PivotValue(field="Logro", agg="mean")],
                     totals={"rows": False, "cols": False})
    r = pivot(df_simple, spec)
    assert cell_at(r, ["A"], []).value == approx((0.8 + 0.9 + 1.0) / 3)


def test_filas_con_nan_en_dimension_se_descartan():
    df = pd.DataFrame([
        {"Curso": "A", "Logro": 1.0},
        {"Curso": None, "Logro": 5.0},  # NaN en dimensión → descartada
        {"Curso": "A", "Logro": 3.0},
    ])
    r = pivot(df, {"rows": ["Curso"], "values": [{"field": "Logro", "agg": "mean"}],
                  "totals": {"rows": False, "cols": False}})
    assert cell_at(r, ["A"], []).value == approx(2.0)  # (1+3)/2, la NaN fuera
    assert [row.keys[0] for row in r.rows] == ["A"]


# ─────────────────────────────────────────────────────────────────────────
# pivot_to_dataframe
# ─────────────────────────────────────────────────────────────────────────

def test_pivot_to_dataframe_consistente(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "mean", "format": ".1%"}],
                          "order": {"Mes": ["Marzo", "Abril"]},
                          "totals": {"rows": True, "cols": True}})
    df_out = pivot_to_dataframe(r)
    # columna de campo de fila presente
    assert "Curso" in df_out.columns
    # encabezados de columnas de datos + Total
    assert "Marzo" in df_out.columns
    assert "Abril" in df_out.columns
    assert "Total" in df_out.columns
    # fila Total presente
    assert "Total" in df_out["Curso"].tolist()
    # los valores del df = displays del PivotResult
    fila_A = df_out[df_out["Curso"] == "A"].iloc[0]
    assert fila_A["Marzo"] == cell_at(r, ["A"], ["Marzo"]).display
    assert fila_A["Abril"] == cell_at(r, ["A"], ["Abril"]).display
    assert fila_A["Total"] == cell_at(r, ["A"], ["Total"], is_total_col=True).display


def test_pivot_to_dataframe_multinivel_rows():
    df = pd.DataFrame([
        {"Colegio": "X", "Curso": "A", "V": 10.0},
        {"Colegio": "X", "Curso": "B", "V": 20.0},
    ])
    r = pivot(df, {"rows": ["Colegio", "Curso"],
                  "values": [{"field": "V", "agg": "sum", "format": ".0f"}],
                  "totals": {"rows": False, "cols": False}})
    df_out = pivot_to_dataframe(r)
    assert list(df_out.columns[:2]) == ["Colegio", "Curso"]
    fila = df_out[(df_out["Colegio"] == "X") & (df_out["Curso"] == "A")].iloc[0]
    assert fila["V"] == "10"


def test_pivot_to_dataframe_df_vacio():
    df = pd.DataFrame(columns=["Curso", "Logro"])
    r = pivot(df, {"rows": ["Curso"], "values": [{"field": "Logro", "agg": "mean"}]})
    df_out = pivot_to_dataframe(r)
    assert "Curso" in df_out.columns
    assert len(df_out) == 0


# ─────────────────────────────────────────────────────────────────────────
# Serialización JSON
# ─────────────────────────────────────────────────────────────────────────

def test_resultado_serializa_a_json(df_simple):
    r = pivot(df_simple, {"rows": ["Curso"], "cols": ["Mes"],
                          "values": [{"field": "Logro", "agg": "mean", "format": ".1%"}],
                          "totals": {"rows": True, "cols": True}})
    data = r.model_dump(mode="json")
    assert set(data.keys()) >= {"row_fields", "col_fields", "columns", "rows", "meta"}
    assert isinstance(data["rows"][0]["cells"][0]["display"], str)
    import json
    json.dumps(data)  # no debe lanzar
