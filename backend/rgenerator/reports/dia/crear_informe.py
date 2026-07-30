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

import json
from pathlib import Path

import pandas as pd

from .. import runtime
from ..branding import (
    aplicar_center_header,
    formatear_filtros,
    formatear_valor_filtro,
    valor_unico,
)
from ...core.derived_fields_engine import apply_derived_fields


def _filtrar_temporal(df: pd.DataFrame, columna: str, valor) -> pd.DataFrame:
    """Filtra `df` a un valor (o lista de valores) de una columna temporal.

    Los filtros del dashboard llegan como lista multi-valor; los llamados
    programáticos pueden pasar un escalar. None, lista vacía o columna
    inexistente → sin filtro.
    """
    if valor is None or columna not in df.columns:
        return df
    if isinstance(valor, (list, tuple, set)):
        valores = [str(v) for v in valor]
        if not valores:
            return df
    else:
        valores = [str(valor)]
    return df[df[columna].astype(str).isin(valores)].copy()


def construir(
    df_estudiantes: pd.DataFrame,
    df_preguntas: pd.DataFrame,
    hito: str | None = None,
    anio: str | None = None,
    overrides: dict | None = None,
) -> bytes:
    """Construye el PDF DIA para 1 hito.

    Args:
        df_estudiantes: DataFrame de estudiantes con todas las pruebas del año
            (DIAGNOSTICO/INTERMEDIO/CIERRE). Necesario para que las
            derived_fields tipo slope/delta vean el histórico completo.
        df_preguntas: DataFrame de preguntas (1 fila por respuesta).
        hito: hito a filtrar para mostrar el informe. Si None, no filtra.
            Las derived_fields se calculan ANTES del filtro.
        anio: año a filtrar (columna "Año"). Si None, no filtra. Acepta
            escalar o lista, igual que hito.
        overrides: opcional, dict para sobreescribir esquema (ej branding).

    Returns:
        Bytes del PDF generado.
    """
    # Aplicar derived_fields del esquema sobre el df full (antes de filtrar
    # por hito). Las derived_fields slope/delta necesitan ver todas las
    # pruebas del año para calcular correctamente.
    esquema_path = Path(__file__).parent / "esquema.json"
    esquema: dict = {}
    if esquema_path.exists():
        with open(esquema_path, encoding="utf-8") as f:
            esquema = json.load(f)
        for entry in (esquema.get("derived_fields") or []):
            target = entry.get("df_input")
            configs = entry.get("configs") or []
            if not configs:
                continue
            if target == "estudiantes":
                df_estudiantes = apply_derived_fields(df_estudiantes, configs)
            elif target == "preguntas":
                df_preguntas = apply_derived_fields(df_preguntas, configs)

    # Filtrar a un solo punto temporal si viene especificado (hito y/o año).
    df_estudiantes = _filtrar_temporal(df_estudiantes, "Hito", hito)
    df_preguntas = _filtrar_temporal(df_preguntas, "Hito", hito)
    df_estudiantes = _filtrar_temporal(df_estudiantes, "Año", anio)
    df_preguntas = _filtrar_temporal(df_preguntas, "Año", anio)

    dataframes = {
        "estudiantes": df_estudiantes,
        "preguntas": df_preguntas,
    }

    # Encabezado central con hito/año/asignatura REALES. El esquema traía
    # "Informe DIA Diagnóstico / Asignatura Nivel Medio / Mes Año" fijo, que
    # contradecía el contenido del informe (QA 2026-07-30, P0-10 y P0-11).
    # La asignatura solo se nombra si el informe cubre una sola: el DIA
    # mezcla Lenguaje y Matemática en el mismo agregado (P1-15).
    asignatura = valor_unico(df_estudiantes, "Asignatura")
    nivel = valor_unico(df_estudiantes, "Nivel")
    linea_materia = " ".join(x for x in (asignatura, nivel) if x)
    linea_periodo = " ".join(
        x for x in (formatear_valor_filtro(hito), formatear_valor_filtro(anio)) if x
    )
    overrides = aplicar_center_header(
        overrides,
        base=(esquema.get("branding") or {}).get("center_header"),
        lineas=[linea_materia, linea_periodo],
    )

    filtros_desc = formatear_filtros({"Hito": hito, "Año": anio})

    return runtime.construir_pdf(
        "dia",
        dataframes,
        overrides=overrides,
        df_principal="estudiantes",
        filtros_desc=filtros_desc,
    )
