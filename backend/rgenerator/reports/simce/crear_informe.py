"""Constructor del informe SIMCE.

Versión adaptada de docs/desarrollo/referencia_informe/SIMCE/crear_informe.py
con cambios MÍNIMOS:

- En lugar de leer Excels, recibe DataFrames ya cargados (`df_estudiantes`,
  `df_preguntas`).
- En lugar de escribir variables.tex y compilar xelatex, llama a
  runtime.construir_pdf con el esquema declarativo `simce/esquema.json`.
- Las funciones matplotlib que ANTES generaban PNGs en `aux_files/` ahora
  son llamadas POR EL RUNTIME (no por este archivo). Este archivo solo
  prepara los DataFrames filtrados que el runtime espera.

Flujo para SIMCE original (preservado):
    1) Filtrar df_estudiantes/df_preguntas por Asignatura + Numero_Prueba
       → df_estudiantes_prueba.
    2) Pasar dict {"estudiantes": df_full, "estudiantes_prueba":
       df_filtered, "preguntas": df_preguntas} al runtime.
    3) Runtime ejecuta el esquema, llama a charts/tables, compone PDF.

Equivalente LaTeX: docs/desarrollo/referencia_informe/SIMCE/crear_informe.py
(líneas 1-50 — el resto de ese archivo es boilerplate xelatex que ya no
aplica).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .. import runtime
from ...core.derived_fields_engine import apply_derived_fields


def construir(
    df_estudiantes: pd.DataFrame,
    df_preguntas: pd.DataFrame,
    asignatura: str,
    numero_prueba: int,
    mes: str | None = None,
    overrides: dict | None = None,
) -> bytes:
    """Construye el PDF SIMCE para una asignatura + número de prueba.

    Args:
        df_estudiantes: DataFrame completo de estudiantes (todos los meses).
        df_preguntas: DataFrame completo de preguntas.
        asignatura: ej "LENGUAJE", "MATEMÁTICA".
        numero_prueba: 1-5 (abril a noviembre).
        overrides: opcional, dict para sobreescribir partes del esquema en
            runtime (ej {"branding": {"center_header": ["...", ...]}}).

    Returns:
        Bytes del PDF generado.
    """
    # Filtrar igual que SIMCE/crear_informe.py. Soportar nombres alternos
    # de columnas (DB del proyecto usa "N Prueba" con espacio, no
    # "Numero_Prueba"). Si la columna del nº de prueba no existe o todos
    # sus valores son null, no filtra (usa todo el dataset).
    if "Asignatura" in df_estudiantes.columns:
        df_estudiantes = df_estudiantes[df_estudiantes["Asignatura"] == asignatura].copy()
    if "Asignatura" in df_preguntas.columns:
        df_preguntas = df_preguntas[df_preguntas["Asignatura"] == asignatura].copy()

    # Aplicar derived_fields ANTES del filtro a una sola prueba. slope/delta
    # necesitan ver todas las pruebas del estudiante para calcular. El df ya
    # está filtrado por asignatura. Una vez calculadas las columnas
    # derivadas, el filter por prueba las hereda automáticamente.
    esquema_path = Path(__file__).parent / "esquema.json"
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

    # Filtrar a una sola prueba: prioridad a Mes (string ej "OCTUBRE 2"),
    # fallback a Numero_Prueba/N Prueba (int 1-5). Si ninguno aplica,
    # se usa todo el dataset.
    def _filter_to_one_prueba(df: pd.DataFrame) -> pd.DataFrame:
        if mes and "Mes" in df.columns:
            return df[df["Mes"].astype(str) == str(mes)].copy()
        n_prueba_col = next(
            (c for c in ("N Prueba", "Numero_Prueba", "N_Prueba", "Nro Prueba") if c in df.columns),
            None,
        )
        if n_prueba_col and df[n_prueba_col].notna().any():
            return df[df[n_prueba_col] == numero_prueba].copy()
        return df.copy()

    df_estudiantes_prueba = _filter_to_one_prueba(df_estudiantes)
    df_preguntas_prueba = _filter_to_one_prueba(df_preguntas)

    dataframes = {
        "estudiantes": df_estudiantes,                # df completo (para evolución por mes)
        "estudiantes_prueba": df_estudiantes_prueba,  # df filtrado a 1 prueba
        "preguntas": df_preguntas,                    # df preguntas filtrado por asignatura
        "preguntas_prueba": df_preguntas_prueba,      # df preguntas filtrado a 1 prueba
    }

    return runtime.construir_pdf("simce", dataframes, overrides=overrides)
