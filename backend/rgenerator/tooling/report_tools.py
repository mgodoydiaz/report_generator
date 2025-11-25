import itertools
import pandas as pd


def crear_tabla_estadistica_por_pregunta(
    df_preguntas,
    parametros,
    columnas_alternativas=["A", "B", "C", "D", "E"],
    columnas_data=["Pregunta", "Correcta", "Distractor"],
):
    """Crea una tabla de estadística por pregunta del establecimiento en general (se ignora el curso, se agrupa por pregunta)"""
    # Se filtra el dataframe por los parámetros dados
    for key, value in parametros.items():
        if key in df_preguntas.columns:
            df_preguntas = df_preguntas[df_preguntas[key] == value]

    # Agrupar por Pregunta, se suman las columnas A,B,C,D,E para el resto de columnas no se resume.
    resumen = (
        df_preguntas.groupby("Pregunta")[columnas_alternativas].sum().reset_index()
    )
    # Luego de cada columna se agrega el porcentaje respecto al total de respuestas, por ejemplo A, %A
    for col in columnas_alternativas:
        valor = resumen[col] / resumen[columnas_alternativas].sum(axis=1)
        resumen[f"%{col}"] = valor.apply(lambda x: f"{x:.0%}")

    # Se ordenan las columnas
    resumen = resumen[
        ["Pregunta"]
        + list(
            itertools.chain.from_iterable(
                (col, f"%{col}") for col in columnas_alternativas
            )
        )
    ]

    # Se agregan las columnas de Correcta, Distractor, Habilidad, Eje temático. Son valores unicos por pregunta, se toma el primer valor.
    resumen = pd.merge(
        resumen,
        df_preguntas[columnas_data].drop_duplicates(subset=["Pregunta"]),
        on="Pregunta",
        how="left",
    )

    # Se ordena por Pregunta
    resumen = resumen.sort_values(by="Pregunta").reset_index(drop=True)

    return resumen


def df_a_latex_loop(df):
    # Columnas
    cols = df.columns.tolist()
    ncols = len(cols)
    # Se determinan los índices de columnas que son numéricas o porcentajes
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    percent_cols = [col for col in cols if col.endswith("%")]

    # Se determinan los índices de columnas que son numéricas o porcentajes
    numeric_cols = df.apply(
        lambda x: pd.to_numeric(x, errors="coerce").notnull().all()
    ).to_list()
    # Se buscan columnas que los valores del dataframe son porcentajes
    percent_cols = df.apply(lambda x: x.astype(str).str.endswith("%")).any().tolist()
    # Se crea una lista de booleanos combinando ambas condiciones con or
    is_numeric = [n or p for n, p in zip(numeric_cols, percent_cols)]

    # Encabezado LaTeX
    latex = "\\begin{table}[H]\n"
    latex += "\\centering\n"

    # Si la columna es numérica, se alinea a la derecha
    latex += "\\begin{tabular}{|"
    for col in range(ncols):
        if is_numeric[col]:
            latex += "r|"
        else:
            latex += "l|"
    latex += "}\n"
    latex += "\\hline\n"

    # Títulos en negrita y alineados a la izquierda
    headers = []
    for col in range(ncols):
        c = cols[col]
        if is_numeric[col]:
            if col == 0:
                headers.append(f"\\multicolumn{{1}}{{|l|}}{{\\textbf{{{c}}}}}")
            else:
                headers.append(f"\\multicolumn{{1}}{{r|}}{{\\textbf{{{c}}}}}")
        else:
            if col == 0:
                headers.append(f"\\multicolumn{{1}}{{|l|}}{{\\textbf{{{c}}}}}")
            else:
                headers.append(f"\\multicolumn{{1}}{{l|}}{{\\textbf{{{c}}}}}")
    headers = " & ".join(headers) + " \\\\ \\hline\n"
    latex += headers.replace("%", "\\%")

    # Filas, si is_percente se hace un replace para que el % no afecte en LaTeX
    for _, row in df.iterrows():
        fila = " & ".join(str(v) for v in row.values) + " \\\\ \\hline\n"
        latex += fila.replace("%", "\\%")

    # Cierre
    latex += "\\end{tabular}\n"

    latex += "\\end{table}\n"

    return latex


def img_to_latex(path, options=""):
    latex = "\\begin{figure}[H]\n"
    latex += "    \\centering\n"
    if options:
        latex += f"    \\includegraphics[{options}]{{{path}}}\n"
    else:
        latex += f"    \\includegraphics[width=\\textwidth]{{{path}}}\n"
    latex += "\\end{figure}\n"
    return latex


def resumen_estadistico_basico(
    df_estudiantes, columna, formato="percent", agrupar_por="Curso", **parametros
):
    """Teniendo un dataset, se crea un resumen con cuenta de alumnos, promedio, minimo y maximo de la columna indicada.
    Se formatean los valores por percent o number."""
    # Se filtra el dataframe por los parámetros dados
    for key, value in parametros.items():
        if key in df_estudiantes.columns:
            df_estudiantes = df_estudiantes[df_estudiantes[key] == value]

    # Agrupa por curso y calcula el resumen
    resumen_por_curso = df_estudiantes.groupby(agrupar_por)
    # print(resumen_por_curso)
    # Se agregan las columnas de porcentaje de logro por curso, Mínimo, Promedio, Máximo
    resumen_por_curso = resumen_por_curso.agg(
        Alumnos=(columna, "size"),
        Promedio=(columna, "mean"),
        Minimo=(columna, "min"),
        Maximo=(columna, "max"),
    ).reset_index()

    # Se formatea los valores según el formato indicado
    for col in ["Promedio", "Minimo", "Maximo"]:
        if formato == "percent":
            resumen_por_curso[col] = resumen_por_curso[col].apply(lambda x: f"{x:.0%}")
        else:
            resumen_por_curso[col] = resumen_por_curso[col].apply(lambda x: f"{x:.0f}")

    # Se ordena curso alfanuméricamente por curso
    resumen_por_curso = resumen_por_curso.sort_values(by=agrupar_por)
    return resumen_por_curso


def tabla_logro_por_alumno(
    df_estudiantes,
    parametros,
    sort_by="Rend",
    formatos={"Rend": "percent", "SIMCE": "number", "Avance_Promedio": "percent"},
    columnas=["Nombre", "Rend", "SIMCE", "Logro", "Avance_Promedio"],
    columnas_renombrar={
        "Nombre": "Estudiante",
        "Rend": "Logro",
        "SIMCE": "SIMCE",
        "Logro": "Nivel",
        "Avance_Promedio": "Avance",
    },
):

    # Se filtra por los parámetros dados
    for key, value in parametros.items():
        if key in df_estudiantes.columns:
            df_estudiantes = df_estudiantes[df_estudiantes[key] == value]
    # Seleccionar columnas necesarias
    df = df_estudiantes[columnas].copy()

    # Ordenar por sort_by
    df = df.sort_values(by=sort_by, ascending=False)
    df = df.reset_index(drop=True)

    # Formatear columnas según formatos
    for col, fmt in formatos.items():
        if col in df.columns:
            if fmt == "percent":
                df[col] = df[col].apply(lambda x: f"{x:.0%}")
            elif fmt == "number":
                df[col] = df[col].apply(lambda x: f"{x:.0f}")

    # Renombrar columnas
    df = df.rename(columns=columnas_renombrar)

    return df


def tabla_logro_por_pregunta(
    df_preguntas,
    valor_agrupacion,
    agrupar_por="Curso",
    sort_by="Logro",
    formatos={"Logro": "percent"},
    columnas=["Pregunta", "Habilidad", "Logro"],
    columnas_renombrar={
        "Pregunta": "N° Pregunta",
        "Habilidad": "Habilidad",
        "Logro": "Logro",
        "Eje Temático": "Eje Temático",
    },
):

    # Filtrar por curso y seleccionar columnas necesarias
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
