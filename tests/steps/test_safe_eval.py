"""Tests del evaluador seguro que reemplaza a eval() en etl_tools.

Dos frentes:
1. Compatibilidad: TODAS las expresiones reales de los configs existentes
   (FL/CV, ejemplos de docstrings) deben seguir funcionando igual.
2. Seguridad: los vectores clásicos de escape de eval deben ser rechazados.
"""
from __future__ import annotations

import pandas as pd
import pytest

from backend.rgenerator.tooling.safe_eval import ExpresionInvalida, evaluar_expresion
from backend.rgenerator.tooling.etl_tools import modificar_valores_columna


@pytest.fixture
def row():
    return pd.Series({
        "Fecha": pd.Timestamp("2026-03-15"),
        "Curso": "5 BASICO A",
        "Nombre": "Ana",
        "Puntaje": 72,
    })


@pytest.mark.unit
class TestCompatibilidadConfigsReales:
    """Expresiones copiadas de scripts/_create_fl_cv_specs_pipelines.py y docstrings."""

    def test_fstring_mes_de_fecha(self, row):
        assert evaluar_expresion('f"{row[\'Fecha\'].month:02d}"', {"row": row}) == "03"

    def test_hasattr_sobre_timestamp(self, row):
        assert evaluar_expresion("hasattr(row['Fecha'], 'month')", {"row": row}) is True

    def test_slicing_de_string(self, row):
        assert evaluar_expresion("str(row['Fecha'])[5:7]", {"row": row}) == "03"

    def test_split_join_de_curso(self, row):
        out = evaluar_expresion("' '.join(str(row['Curso']).split(' ')[:-1])", {"row": row})
        assert out == "5 BASICO"

    def test_in_sobre_index_y_get(self, row):
        out = evaluar_expresion("'Apellido' in row.index and row.get('Apellido')", {"row": row})
        assert out is False

    def test_round_aritmetica(self, row):
        out = evaluar_expresion("round(0.075 * row['Puntaje'] - 0.5, 2)", {"row": row})
        assert out == 4.9

    def test_comparacion_umbral(self, row):
        assert evaluar_expresion("row['Puntaje'] <= 72", {"row": row}) is True

    def test_condicion_con_x_escalar(self):
        assert evaluar_expresion("x > 1", {"x": 85}) is True
        assert evaluar_expresion("x / 100", {"x": 85}) == 0.85

    def test_re_shim_search(self, row):
        out = evaluar_expresion(
            "re.search(r'(\\d+)', str(row['Curso'])).group(1)", {"row": row}
        )
        assert out == "5"

    def test_re_shim_sub(self):
        out = evaluar_expresion("re.sub(r'\\s+', '_', x)", {"x": "II  A"})
        assert out == "II_A"


@pytest.mark.unit
class TestSandbox:
    """Vectores de escape que ANTES pasaban por eval() y ahora se rechazan."""

    @pytest.mark.parametrize("expr", [
        "__import__('os').system('id')",
        "open('/etc/passwd').read()",
        "().__class__.__bases__[0].__subclasses__()",
        "x.__class__",
        "exec('print(1)')",
        "eval('1+1')",
        "globals()",
    ])
    def test_vectores_bloqueados(self, expr):
        with pytest.raises(ExpresionInvalida):
            evaluar_expresion(expr, {"x": 1})

    def test_sintaxis_invalida_da_error_claro(self):
        with pytest.raises(ExpresionInvalida, match="Sintaxis|inválida"):
            evaluar_expresion("x +* 2", {"x": 1})


@pytest.mark.unit
class TestModificarValoresColumnaMath:
    """La operación math del step ModifyColumnValues usa el evaluador."""

    def test_math_escalar_normaliza_porcentaje(self):
        df = pd.DataFrame({"Logro": [85.0, 0.9]})
        out = modificar_valores_columna(df, [{
            "columna": "Logro",
            "operacion": "math",
            "valores": [
                {"condicion": "x > 1", "expresion": "x / 100"},
                {"condicion": "*", "expresion": "x"},
            ],
        }])
        assert list(out["Logro"]) == [0.85, 0.9]

    def test_math_por_fila_con_fstring(self):
        df = pd.DataFrame({"Fecha": [pd.Timestamp("2026-04-01")], "Mes": [None]})
        out = modificar_valores_columna(df, [{
            "columna": "Mes",
            "operacion": "math",
            "usa_fila": True,
            "valores": [
                {"condicion": "hasattr(row['Fecha'], 'month')",
                 "expresion": "f\"{row['Fecha'].month:02d}\""},
                {"condicion": "*", "expresion": "str(row['Fecha'])[5:7]"},
            ],
        }])
        assert list(out["Mes"]) == ["04"]

    def test_math_config_malicioso_lanza_error(self):
        df = pd.DataFrame({"X": [1]})
        with pytest.raises(ExpresionInvalida):
            modificar_valores_columna(df, [{
                "columna": "X",
                "operacion": "math",
                "valores": [{"condicion": "*",
                             "expresion": "__import__('os').getcwd()"}],
            }])
