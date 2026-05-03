"""Constructor del informe DIA.

Versión adaptada de docs/desarrollo/referencia_informe/DIA/crear_informe.py.
Diferencias respecto al original LaTeX:

- Recibe DataFrames como parámetro (no `pd.read_excel`).
- No genera variables.tex ni compila xelatex; llama runtime.construir_pdf
  con `dia/esquema.json`.
- El comparativo "Diagnóstico vs Intermedio" todavía no está incluido
  (TODO próximo iter — requiere 2 dfs).

Equivalente LaTeX: docs/desarrollo/referencia_informe/DIA/crear_informe.py.
"""
from __future__ import annotations

import pandas as pd

from .. import runtime


def construir(
    df_estudiantes: pd.DataFrame,
    df_preguntas: pd.DataFrame,
    overrides: dict | None = None,
) -> bytes:
    """Construye el PDF DIA para 1 hito.

    Args:
        df_estudiantes: DataFrame de estudiantes (1 fila por alumno).
            Columnas esperadas: Curso, Logro, NIVEL DE LOGRO,
            Número de Lista, Nombre del Estudiante, Nivel.
        df_preguntas: DataFrame de preguntas (1 fila por respuesta).
            Columnas esperadas: Curso, N° Pregunta, Eje Temático,
            Habilidad, Logro, Nivel de Logro.
        overrides: opcional, dict para sobreescribir esquema (ej branding).

    Returns:
        Bytes del PDF generado.
    """
    dataframes = {
        "estudiantes": df_estudiantes,
        "preguntas": df_preguntas,
    }
    return runtime.construir_pdf("dia", dataframes, overrides=overrides)
