"""Biblioteca de tablas (DataFrames preparados para incrustar en HTML).

Cada función toma DataFrame(s) + parámetros y retorna un DataFrame ya
formateado (porcentajes, columnas renombradas, ordenado). El renderizado a
HTML lo hace `helpers.df_a_html_table`.

Las funciones son **copia textual** de SIMCE/funciones.py — solo se añaden
docstrings y un TABLE_REGISTRY al final.
"""
from __future__ import annotations

import itertools

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────
# Resumen estadístico (Alumnos / Promedio / Mín / Máx)
# ─────────────────────────────────────────────────────────────────────────

def resumen_estadistico_basico(
    df_estudiantes: pd.DataFrame,
    columna: str,
    formato: str = "percent",
    agrupar_por: str = "Curso",
    **parametros,
):
    """Resumen: Alumnos, Promedio, Mínimo, Máximo de `columna` por `agrupar_por`.

    Display name: Resumen estadístico básico
    Genera tabla con conteo + 3 estadísticas formateadas según `formato`.

    Args:
        df_estudiantes: DataFrame de entrada.
        columna: columna numérica a resumir (ej "Rend", "SIMCE", "Logro").
        formato: "percent" (multiplica por 100 y agrega %) o "number"
            (entero sin decimales).
        agrupar_por: columna categórica (default "Curso").
        **parametros: filtros adicionales aplicados antes de agrupar
            (ej Asignatura="LENGUAJE").

    Returns:
        DataFrame con columnas [agrupar_por, Alumnos, Promedio, Minimo, Maximo].

    Equivalente LaTeX: SIMCE.resumen_estadistico_basico,
        DIA.resumen_por_curso.
    """
    # Filtros adicionales por kwargs
    for key, value in parametros.items():
        if key in df_estudiantes.columns:
            df_estudiantes = df_estudiantes[df_estudiantes[key] == value]

    resumen = df_estudiantes.groupby(agrupar_por).agg(
        Alumnos=(columna, "size"),
        Promedio=(columna, "mean"),
        Minimo=(columna, "min"),
        Maximo=(columna, "max"),
    ).reset_index()

    # Formato
    for col in ["Promedio", "Minimo", "Maximo"]:
        if formato == "percent":
            resumen[col] = resumen[col].apply(lambda x: f"{x:.0%}")
        else:
            resumen[col] = resumen[col].apply(lambda x: f"{x:.0f}")

    resumen = resumen.sort_values(by=agrupar_por)
    return resumen


# ─────────────────────────────────────────────────────────────────────────
# Tabla logro por alumno (1 fila por estudiante)
# ─────────────────────────────────────────────────────────────────────────

def tabla_logro_por_alumno(
    df_estudiantes: pd.DataFrame,
    parametros: dict,
    sort_by: str = "Rend",
    formatos: dict | None = None,
    columnas: list | None = None,
    columnas_renombrar: dict | None = None,
):
    """Tabla detalle: 1 fila por estudiante con sus métricas.

    Display name: Logro por alumno
    Filtra el df por los `parametros` que matcheen columnas, ordena por
    `sort_by`, formatea las columnas según `formatos`, y renombra al final.

    Args:
        df_estudiantes: DataFrame.
        parametros: dict de filtros (ej {"Curso": "I A", "Asignatura": "LENGUAJE"}).
            Solo se aplican los keys que existan como columna en el df.
        sort_by: columna por la que ordenar (descendente).
        formatos: dict {columna: "percent"|"number"}. Default
            {"Rend": "percent", "SIMCE": "number", "Avance_Promedio": "percent"}.
        columnas: lista de columnas a incluir. Default
            ["Nombre", "Rend", "SIMCE", "Logro", "Avance_Promedio"].
        columnas_renombrar: dict {original: nuevo}. Default convierte a
            {Nombre: Estudiante, Rend: Logro, Logro: Nivel, ...}.

    Returns:
        DataFrame listo para df_a_html_table.

    Equivalente LaTeX: SIMCE.tabla_logro_por_alumno,
        DIA.tabla_logro_por_alumno (con columnas distintas).
    """
    # Defaults
    if formatos is None:
        formatos = {"Rend": "percent", "SIMCE": "number", "Avance_Promedio": "percent"}
    if columnas is None:
        columnas = ["Nombre", "Rend", "SIMCE", "Logro", "Avance_Promedio"]
    if columnas_renombrar is None:
        columnas_renombrar = {
            "Nombre": "Estudiante",
            "Rend": "Logro",
            "SIMCE": "SIMCE",
            "Logro": "Nivel",
            "Avance_Promedio": "Avance",
        }

    # Filtrar
    for key, value in parametros.items():
        if key in df_estudiantes.columns:
            df_estudiantes = df_estudiantes[df_estudiantes[key] == value]

    df = df_estudiantes[columnas].copy()
    df = df.sort_values(by=sort_by, ascending=False)
    df = df.reset_index(drop=True)

    # Formato por columna
    for col, fmt in formatos.items():
        if col in df.columns:
            if fmt == "percent":
                df[col] = df[col].apply(lambda x: f"{x:.0%}")
            elif fmt == "number":
                df[col] = df[col].apply(lambda x: f"{x:.0f}")

    df = df.rename(columns=columnas_renombrar)
    return df


# ─────────────────────────────────────────────────────────────────────────
# Tabla logro por pregunta (1 fila por pregunta)
# ─────────────────────────────────────────────────────────────────────────

def tabla_logro_por_pregunta(
    df_preguntas: pd.DataFrame,
    valor_agrupacion,
    agrupar_por: str = "Curso",
    sort_by: str = "Logro",
    formatos: dict | None = None,
    columnas: list | None = None,
    columnas_renombrar: dict | None = None,
):
    """Tabla detalle: 1 fila por pregunta filtrado a un curso.

    Display name: Logro por pregunta
    Filtra el df de preguntas a un valor específico de `agrupar_por`
    (típicamente "I A", "II B", ...), ordena, formatea y renombra.

    Args:
        df_preguntas: DataFrame con info por pregunta.
        valor_agrupacion: valor por el que filtrar (ej "I A").
        agrupar_por: columna para el filtro (ej "Curso").
        sort_by: columna para ordenar (default "Logro" descendente).
        formatos: dict {columna: "percent"|"number"}. Default
            {"Logro": "percent"}.
        columnas: lista de columnas a incluir. Default
            ["Pregunta", "Habilidad", "Logro"].
        columnas_renombrar: dict de renombre.

    Returns:
        DataFrame listo para df_a_html_table.

    Equivalente LaTeX: SIMCE.tabla_logro_por_pregunta,
        DIA.tabla_logro_por_pregunta.
    """
    if formatos is None:
        formatos = {"Logro": "percent"}
    if columnas is None:
        columnas = ["Pregunta", "Habilidad", "Logro"]
    if columnas_renombrar is None:
        columnas_renombrar = {
            "Pregunta": "N° Pregunta",
            "Habilidad": "Habilidad",
            "Logro": "Logro",
            "Eje Temático": "Eje Temático",
        }

    df = df_preguntas[df_preguntas[agrupar_por] == valor_agrupacion][columnas].copy()
    df = df.sort_values(by=sort_by, ascending=False)
    df = df.reset_index(drop=True)

    for col, fmt in formatos.items():
        if col in df.columns:
            if fmt == "percent":
                df[col] = df[col].apply(lambda x: f"{x:.0%}")
            elif fmt == "number":
                df[col] = df[col].apply(lambda x: f"{x:.0f}")

    df = df.rename(columns=columnas_renombrar)
    return df


# ─────────────────────────────────────────────────────────────────────────
# Tabla estadística por pregunta (A/B/C/D/E con porcentajes) — SIMCE-only
# ─────────────────────────────────────────────────────────────────────────

def crear_tabla_estadistica_por_pregunta(
    df_preguntas: pd.DataFrame,
    parametros: dict,
    columnas_alternativas: list = ("A", "B", "C", "D", "E"),
    columnas_data: list = ("Pregunta", "Correcta", "Distractor"),
):
    """Tabla SIMCE: por pregunta, conteo y % de cada alternativa A-E.

    Display name: Estadística por pregunta (alternativas A-E)
    Útil sólo para SIMCE (que tiene columnas A,B,C,D,E con conteos por
    alternativa). Agrupa por pregunta sumando alternativas y agrega columnas
    %A, %B, ... %E.

    Args:
        df_preguntas: DataFrame con columnas A,B,C,D,E + Pregunta.
        parametros: dict de filtros (Asignatura, Numero_Prueba).
        columnas_alternativas: tupla de alternativas (default A-E).
        columnas_data: columnas adicionales que se mantienen (Correcta,
            Distractor, Habilidad, Eje Temático).

    Returns:
        DataFrame con columnas [Pregunta, A, %A, B, %B, ..., Correcta,
        Distractor, ...].

    Equivalente LaTeX: SIMCE.crear_tabla_estadistica_por_pregunta.
    """
    # Filtros
    for key, value in parametros.items():
        if key in df_preguntas.columns:
            df_preguntas = df_preguntas[df_preguntas[key] == value]

    columnas_alternativas = list(columnas_alternativas)
    columnas_data = list(columnas_data)

    # Agrupa por Pregunta sumando A,B,C,D,E
    resumen = df_preguntas.groupby("Pregunta")[columnas_alternativas].sum().reset_index()

    # %A, %B, ...
    for col in columnas_alternativas:
        valor = resumen[col] / resumen[columnas_alternativas].sum(axis=1)
        resumen[f"%{col}"] = valor.apply(lambda x: f"{x:.0%}")

    # Reordenar: Pregunta, A, %A, B, %B, ...
    resumen = resumen[
        ["Pregunta"] + list(itertools.chain.from_iterable((col, f"%{col}") for col in columnas_alternativas))
    ]

    # Mergear columnas data (valores únicos por pregunta)
    resumen = pd.merge(
        resumen,
        df_preguntas[columnas_data].drop_duplicates(subset=["Pregunta"]),
        on="Pregunta",
        how="left",
    )

    resumen = resumen.sort_values(by="Pregunta").reset_index(drop=True)
    return resumen


# ─────────────────────────────────────────────────────────────────────────
# Comparativo entre evaluaciones (utility para charts.comparacion_*)
# ─────────────────────────────────────────────────────────────────────────

def crear_df_comparacion(
    df_diagnostico: pd.DataFrame,
    df_intermedio: pd.DataFrame,
    columna_id_diagnostico: str = "CURSO",
    columna_id_intermedio: str = "Curso",
    columna_valor: str = "Logro",
):
    """Une 2 evaluaciones en formato wide para `comparacion_logro_por_curso`.

    Display name: Comparador entre 2 evaluaciones
    Devuelve un DataFrame con 1 fila por curso y 2 columnas
    (Diagnóstico, Intermedio) con el promedio de `columna_valor`.

    Args:
        df_diagnostico, df_intermedio: DataFrames de las 2 evaluaciones.
        columna_id_*: columnas de identificación en cada df (a veces
            difieren por mayúsculas/minúsculas).
        columna_valor: columna numérica a promediar.

    Returns:
        DataFrame [Curso, Diagnóstico, Intermedio].

    Equivalente LaTeX: SIMCE.crear_df_comparacion, DIA.crear_df_comparacion.
    """
    df_comparacion = pd.DataFrame({
        "Diagnóstico": df_diagnostico.groupby(columna_id_diagnostico)[columna_valor].mean(),
        "Intermedio": df_intermedio.groupby(columna_id_intermedio)[columna_valor].mean(),
    }).reset_index()

    df_comparacion = df_comparacion.rename(columns={"index": "Curso"})
    df_comparacion = df_comparacion.sort_values(by="Curso")
    df_comparacion["Curso"] = df_comparacion["Curso"].apply(lambda x: x.split(" (")[0] if isinstance(x, str) else x)
    return df_comparacion


# ─────────────────────────────────────────────────────────────────────────
# Registry para introspección desde el frontend
# ─────────────────────────────────────────────────────────────────────────

TABLE_REGISTRY = {
    "resumen_estadistico_basico": {
        "fn": resumen_estadistico_basico,
        "display_name": "Resumen estadístico básico",
        "description": "Tabla con Alumnos, Promedio, Mínimo y Máximo de una columna numérica agrupado por categoría.",
        "required_params": ["columna", "agrupar_por"],
        "optional_params": ["formato"],
        "input_dataframes": ["df_estudiantes"],
    },
    "tabla_logro_por_alumno": {
        "fn": tabla_logro_por_alumno,
        "display_name": "Logro por alumno",
        "description": "Detalle 1 fila por estudiante con sus métricas (Rend, SIMCE, Logro, Avance...). Ordenable y formateable.",
        "required_params": ["parametros"],
        "optional_params": ["sort_by", "formatos", "columnas", "columnas_renombrar"],
        "input_dataframes": ["df_estudiantes"],
    },
    "tabla_logro_por_pregunta": {
        "fn": tabla_logro_por_pregunta,
        "display_name": "Logro por pregunta",
        "description": "Detalle 1 fila por pregunta filtrado a un curso. Útil para análisis de ítems.",
        "required_params": ["valor_agrupacion", "agrupar_por"],
        "optional_params": ["sort_by", "formatos", "columnas", "columnas_renombrar"],
        "input_dataframes": ["df_preguntas"],
    },
    "crear_tabla_estadistica_por_pregunta": {
        "fn": crear_tabla_estadistica_por_pregunta,
        "display_name": "Estadística por pregunta (alternativas A-E)",
        "description": "SIMCE-only: conteo y % de respuestas por alternativa por pregunta del establecimiento.",
        "required_params": ["parametros"],
        "optional_params": ["columnas_alternativas", "columnas_data"],
        "input_dataframes": ["df_preguntas"],
    },
}
