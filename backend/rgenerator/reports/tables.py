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

from ..core.pivot_engine import pivot, pivot_to_dataframe
from .helpers import (
    DECIMALES_AJUSTE_ANCHO,
    coalescer_nombre_estudiante,
    columnas_nombre_estudiante,
    contar_estudiantes,
    formatear_serie,
    ordenar_df_por,
    ordenar_valores_categoricos,
)


# ─────────────────────────────────────────────────────────────────────────
# Resumen estadístico (Alumnos / Promedio / Mín / Máx)
# ─────────────────────────────────────────────────────────────────────────

def resumen_estadistico_basico(
    df_estudiantes: pd.DataFrame,
    columna: str,
    formato: str = "percent",
    agrupar_por: str = "Curso",
    columna_identidad: str | None = None,
    **parametros,
):
    """Resumen: Alumnos, Promedio, Mínimo, Máximo de `columna` por `agrupar_por`.

    Display name: Resumen estadístico básico
    Genera tabla con conteo + 3 estadísticas formateadas según `formato`.

    `Alumnos` cuenta estudiantes DISTINTOS, no filas: con un df que trae
    varias filas por estudiante (asignatura, habilidad, subprueba) el conteo
    por filas salía inflado y contradecía el gráfico de la misma página
    (P0-12 del QA 2026-07-30). Con una fila por estudiante — el caso de
    Cálculo Veloz — el resultado es idéntico al anterior.

    Args:
        df_estudiantes: DataFrame de entrada.
        columna: columna numérica a resumir (ej "Rend", "SIMCE", "Logro").
        formato: "percent" (multiplica por 100 y agrega %) o "number"
            (entero sin decimales).
        agrupar_por: columna categórica (default "Curso").
        columna_identidad: columna que identifica al estudiante. Si no se
            pasa se autodetecta (RUT → Nombre_Norm → Nombre → Curso+N°
            Lista); sin ninguna se cuentan filas.
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
        Promedio=(columna, "mean"),
        Minimo=(columna, "min"),
        Maximo=(columna, "max"),
    ).reset_index()

    alumnos = contar_estudiantes(
        df_estudiantes, agrupar_por=agrupar_por, columna_identidad=columna_identidad,
    )
    resumen.insert(
        1, "Alumnos",
        resumen[agrupar_por].map(alumnos).fillna(0).astype(int),
    )

    # Formato — SIEMPRE después de decidir si hay valor, para no emitir
    # "nan%" cuando el grupo no tiene datos numéricos (P0-3 / P0-4).
    for col in ["Promedio", "Minimo", "Maximo"]:
        resumen[col] = formatear_serie(
            resumen[col], "percent" if formato == "percent" else "number"
        )

    # Orden del grupo: cronológico si es una dimensión temporal (P0-9),
    # natural en cualquier otro caso — "10 A" después de "9 A", no antes
    # (P0-A del QA 2026-07-30).
    orden = ordenar_valores_categoricos(resumen[agrupar_por].tolist(), agrupar_por)
    resumen = resumen.set_index(agrupar_por).reindex(orden).reset_index()
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

    # Coalesce de identidad: la carga DIA 2026 dejó `Nombre` nulo con
    # `Nombre_Norm` poblado (y la de 2025 al revés), así que la columna
    # Estudiante salía `nan` en 60 de 67 páginas. Es mitigación de
    # presentación — el problema de datos queda reportado (P0-3 del QA
    # 2026-07-30).
    for col_nombre in columnas_nombre_estudiante(df_estudiantes):
        if col_nombre in columnas:
            df_estudiantes = coalescer_nombre_estudiante(df_estudiantes, col_nombre)
            break

    df = df_estudiantes[columnas].copy()
    # Orden natural: para una columna numérica ("Rend") es el sort_values de
    # siempre; para una de texto evita el 1, 10, 11, … 2 (P0-A).
    df = ordenar_df_por(df, sort_by, ascending=False)
    df = df.reset_index(drop=True)

    # Formato por columna — se decide primero si hay valor, para que un
    # faltante salga como "—" y no como "nan%".
    for col, fmt in formatos.items():
        if col in df.columns:
            df[col] = formatear_serie(df[col], fmt)

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
    # Igual que en `tabla_logro_por_alumno`: ordenar por "Logro" (numérico)
    # no cambia, pero ordenar por "Pregunta" (texto) ya sale 1, 2, … 10.
    df = ordenar_df_por(df, sort_by, ascending=False)
    df = df.reset_index(drop=True)

    # Formato tras comprobar que haya valor: "—" en vez de "nan%".
    for col, fmt in formatos.items():
        if col in df.columns:
            df[col] = formatear_serie(df[col], fmt)

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

    # %A, %B, ... (una pregunta sin respuestas registradas da 0/0 → "—")
    for col in columnas_alternativas:
        valor = resumen[col] / resumen[columnas_alternativas].sum(axis=1)
        resumen[f"%{col}"] = formatear_serie(valor, "percent")

    # Los conteos A-E se formatean DESPUÉS de calcular los porcentajes.
    # Sin esto la métrica publica proporciones crudas y la celda sale con el
    # ruido binario completo ("0.5700000000000001", 18 caracteres): con 13
    # columnas eso empujaba D, E, Correcta y Distractor fuera del margen
    # derecho (QA 2026-07-30, P0-B).
    _formatear_alternativas(resumen, columnas_alternativas)

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

    # Orden numérico de las preguntas. La dimensión `Pregunta` llega como
    # texto desde metric_data, así que el sort_values de strings las dejaba
    # 1, 10, 11, … 2, 20 (QA 2026-07-30, P0-A).
    resumen = ordenar_df_por(resumen, "Pregunta").reset_index(drop=True)
    return resumen


def _formatear_alternativas(resumen: pd.DataFrame, columnas: list) -> None:
    """Formatea in-place los conteos por alternativa (A-E) de la tabla SIMCE.

    La métrica guarda conteos enteros en unas cargas y proporciones en
    otras. Se decide por el contenido real:

    - Todos los valores enteros → se imprimen como enteros ("62"), igual
      que el informe de referencia del dueño.
    - Hay decimales (proporciones) → `DECIMALES_AJUSTE_ANCHO` decimales
      ("0.57"), que es lo que corta el ruido de coma flotante.

    Toda la columna sale con el mismo formato: es un redondeo de
    presentación, los porcentajes %A-%E ya se calcularon con los valores
    completos antes de llegar acá.
    """
    numericas = [pd.to_numeric(resumen[col], errors="coerce") for col in columnas]
    if numericas:
        todos = pd.concat(numericas).dropna()
        enteros = bool(todos.empty or (todos % 1 == 0).all())
    else:
        enteros = True

    for col in columnas:
        if enteros:
            resumen[col] = formatear_serie(resumen[col], "number")
        else:
            resumen[col] = formatear_serie(
                resumen[col], "decimal", decimales=DECIMALES_AJUSTE_ANCHO
            )


# ─────────────────────────────────────────────────────────────────────────
# Tabla ya calculada (puente para módulos del motor único)
# ─────────────────────────────────────────────────────────────────────────

def tabla_desde_dataframe(
    df: pd.DataFrame,
    columnas: list | None = None,
    columnas_renombrar: dict | None = None,
):
    """Imprime tal cual un DataFrame que el llamador ya calculó.

    Display name: Tabla ya calculada
    El runtime solo sabe ejecutar funciones de `TABLE_REGISTRY`, así que un
    módulo que arma su tabla en Python (resumen comparado, riesgo
    persistente, comparativos de `crear_df_comparacion`…) necesita un `fn`
    de paso: calcula el DataFrame, lo publica como un `df_input` más y
    declara la sección con esta función. Es el puente que el contrato del
    motor único deja abierto en §6.1.

    Args:
        df: DataFrame ya formateado, listo para imprimir.
        columnas: subconjunto/orden de columnas a mostrar. Las que no
            existan se ignoran.
        columnas_renombrar: `{original: nuevo}` aplicado al final.

    Returns:
        DataFrame listo para `helpers.df_a_html_table`.
    """
    out = df
    if columnas:
        presentes = [c for c in columnas if c in out.columns]
        if presentes:
            out = out[presentes]
    if columnas_renombrar:
        out = out.rename(columns=columnas_renombrar)
    return out


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
# Tabla pivote (motor W2) — envuelve pivot_engine para el PDF v2
# ─────────────────────────────────────────────────────────────────────────

_PIVOT_SPEC_KEYS = ("rows", "cols", "values", "totals", "order", "fill_value", "total_label")


def tabla_pivote(
    df: pd.DataFrame,
    spec: dict | None = None,
    filtro: dict | None = None,
    **params,
):
    """Tabla pivote declarativa para informes, respaldada por el motor W2.

    Display name: Tabla pivote
    Envuelve `pivot_engine.pivot` + `pivot_to_dataframe`: recibe un
    `PivotSpec` (dict) y devuelve un DataFrame plano con el `display` ya
    formateado, listo para `helpers.df_a_html_table`. Fuente única de verdad
    para pivotes (dashboard / PDF / Excel comparten el mismo motor).

    Multi-pivote: se declaran varias secciones `pivot` (o `table` con
    `fn: tabla_pivote`) en el esquema. Un pivote iterado por curso sale de
    las secciones dinámicas del runtime (`iterar_por`) combinadas con
    `filtro={"Curso": "{curso}"}` — que pre-filtra el df antes de pivotar.

    Args:
        df: DataFrame de origen.
        spec: `PivotSpec` como dict (rows, cols, values, totals, order,
            fill_value, total_label). Si es None, se arma con los `params`
            sueltos que matcheen las keys del spec.
        filtro: dict opcional {campo: valor} para filtrar el df por igualdad
            (str) antes de pivotar. Útil para pivotes por curso/categoría en
            secciones dinámicas.
        **params: alternativa a `spec` — se aceptan rows/cols/values/... como
            kwargs sueltos.

    Returns:
        DataFrame plano (display formateado) listo para df_a_html_table.
    """
    if filtro:
        for k, v in filtro.items():
            if k in df.columns:
                df = df[df[k].astype(str) == str(v)]

    if spec is None:
        spec = {k: params[k] for k in _PIVOT_SPEC_KEYS if k in params}

    result = pivot(df, spec)
    return pivot_to_dataframe(result)


# ─────────────────────────────────────────────────────────────────────────
# Registry para introspección desde el frontend
# ─────────────────────────────────────────────────────────────────────────

TABLE_REGISTRY = {
    "tabla_pivote": {
        "fn": tabla_pivote,
        "display_name": "Tabla pivote",
        "description": "Pivote declarativo (rows × cols × values con agregaciones y totales) respaldado por el motor de pivotes W2. Acepta un PivotSpec y un filtro opcional por campo.",
        "required_params": ["spec"],
        "optional_params": ["filtro"],
        "input_dataframes": ["df"],
    },
    "resumen_estadistico_basico": {
        "fn": resumen_estadistico_basico,
        "display_name": "Resumen estadístico básico",
        "description": "Tabla con Alumnos, Promedio, Mínimo y Máximo de una columna numérica agrupado por categoría. Alumnos = estudiantes distintos.",
        "required_params": ["columna", "agrupar_por"],
        "optional_params": ["formato", "columna_identidad"],
        "input_dataframes": ["df_estudiantes"],
    },
    "tabla_desde_dataframe": {
        "fn": tabla_desde_dataframe,
        "display_name": "Tabla ya calculada",
        "description": "Imprime tal cual un DataFrame calculado por el llamador (módulos del motor único). Permite subconjunto de columnas y renombre.",
        "required_params": [],
        "optional_params": ["columnas", "columnas_renombrar"],
        "input_dataframes": ["df"],
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
