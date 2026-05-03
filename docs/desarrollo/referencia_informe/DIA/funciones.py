import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

import itertools
import os

from funciones import *

def df_a_latex_loop(df):
    # Columnas
    cols = df.columns.tolist()
    ncols = len(cols)
    # Se determinan los índices de columnas que son numéricas o porcentajes
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    percent_cols = [col for col in cols if col.endswith('%')]
    
    # Se determinan los índices de columnas que son numéricas o porcentajes
    numeric_cols = df.apply(lambda x: pd.to_numeric(x, errors='coerce').notnull().all()).to_list()
    # Se buscan columnas que los valores del dataframe son porcentajes
    percent_cols = df.apply(lambda x: x.astype(str).str.endswith('%')).any().tolist()
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
    latex += headers

    # Filas, si is_percente se hace un replace para que el % no afecte en LaTeX
    for _, row in df.iterrows():
        fila = " & ".join(str(v) for v in row.values) + " \\\\ \\hline\n"
        latex += fila.replace('%', '\\%')

    # Cierre
    latex += "\\end{tabular}\n"
    
    latex += "\\end{table}\n"

    return latex

def img_to_latex(path, options=''):
    latex = "\\begin{figure}[H]\n"
    latex += "    \\centering\n"
    if options:
        latex += f"    \\includegraphics[{options}]{{{path}}}\n"
    else:
        latex += f"    \\includegraphics[width=\\textwidth]{{{path}}}\n"
    latex += "\\end{figure}\n"
    return latex

def resumen_por_curso(df_estudiantes):
    # Agrupa por curso y calcula el resumen
    resumen_por_curso = df_estudiantes.groupby("Curso")
    # Se agregan las columnas de porcentaje de logro por curso, Mínimo, Promedio, Máximo
    resumen_por_curso = resumen_por_curso.agg(
        Alumnos=('Logro', 'size'),
        Promedio=('Logro', 'mean'),
        Minimo=('Logro', 'min'),
        Maximo=('Logro', 'max')
    ).reset_index()

# Se formatea los valores como % sin decimales
    for col in ["Promedio", "Minimo", "Maximo"]:
        resumen_por_curso[col] = resumen_por_curso[col].apply(lambda x: f"{x:.0%}")

    # Se ordena curso alfanuméricamente
    resumen_por_curso = resumen_por_curso.sort_index()
    return resumen_por_curso

def logro_promedio_por_nivel(df_estudiantes, nombre_grafico="aux_files/logro_promedio_por_nivel.png"):
    # Agrupar por nivel y calcular promedio
    resumen = df_estudiantes.groupby("Nivel").agg(
        Promedio=("Logro", "mean")
    ).reset_index()
    
    # Crear gráfico
    fig, ax = plt.subplots(figsize=(5.95,4)) 
    plt.grid(axis='y')
    bars = ax.bar(resumen["Nivel"], resumen["Promedio"], color=plt.cm.Set2.colors, zorder=3, edgecolor="black", linewidth=1.2)
    
    ax.set_ylim(0, 1)  # como porcentaje (0 a 100%)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))  # Formato de porcentaje
    ax.set_ylabel("Logro (%)")
    ax.set_title("Logro Promedio por Nivel")

    # Etiquetas arriba de cada barra
    for bar, val in zip(bars, resumen["Promedio"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{val:.0%}", ha="center", va="bottom")

    plt.tight_layout()
    plt.savefig(nombre_grafico)
    plt.close()
    
    return resumen

def logro_promedio_por_curso(df_estudiantes, nombre_grafico="aux_files/logro_promedio_por_curso.png"):
    # Agrupar por curso y calcular promedio
    resumen = df_estudiantes.groupby("Curso").agg(
        Promedio=("Logro", "mean")
    ).reset_index()

    # Se formatea el curso dando I A (TPI-710) -> I A
    resumen["Curso"] = resumen["Curso"].apply(lambda x: x.split(" (")[0])
    
    # Crear gráfico
    fig, ax = plt.subplots(figsize=(8,4))
    bars = ax.bar(resumen["Curso"], resumen["Promedio"], color=plt.cm.Set2.colors, edgecolor="black", linewidth=1.2, zorder=3)

    # Eje Y en porcentaje
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))

    ax.set_title("Logro Promedio por Curso")
    ax.set_ylabel("Logro (%)")
    ax.set_xlabel("Curso")
    ax.tick_params(axis="x", rotation=45)

    # Etiquetas arriba de cada barra
    for bar, val in zip(bars, resumen["Promedio"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{val:.0%}", ha="center", va="bottom")
    
    # Grilla más debil que los bordes
    ax.grid(axis='y', linestyle="--", linewidth=0.9, zorder=0)

    plt.tight_layout()
    plt.savefig(nombre_grafico)
    plt.close()

    return None

def boxplot_logro_por_curso(
    df_estudiantes: pd.DataFrame,
    nombre_grafico: str = "aux_files/distribucion_rendimiento_por_curso.png"
):
    # ---- Datos
    cursos = sorted(df_estudiantes["Curso"].unique(), key=lambda x: str(x))
    data = [df_estudiantes.loc[df_estudiantes["Curso"] == c, "Logro"].dropna().values for c in cursos]
    # Se formatea el curso dando I A (TPI-710) -> I A
    cursos = [c.split(" (")[0] for c in cursos]

    # ---- Colores por curso
    cmap = plt.cm.tab10
    colors = {c: cmap(i % 10) for i, c in enumerate(cursos)}

    # ---- Figura
    fig, ax = plt.subplots(figsize=(6,4))

    # Boxplot sin relleno
    bp = ax.boxplot(
        data,
        positions=np.arange(len(cursos)),
        widths=0.6,
        patch_artist=True,
        showfliers=True,
        medianprops=dict(color="black", linewidth=2),
        boxprops=dict(facecolor="none", edgecolor="black", linewidth=1.5),
        whiskerprops=dict(color="black"),
        capprops=dict(color="black")
    )
    # Colorear cada box con alpha
    for patch, curso in zip(bp['boxes'], cursos):
        patch.set_facecolor(colors[curso])
        patch.set_alpha(0.6)
    
    # Ejes y formato
    ax.set_title("Distribución de Rendimiento por Curso")
    ax.set_xlabel("Curso")
    ax.set_ylabel("Rendimiento (%)")
    ax.set_xticks(np.arange(len(cursos)))
    ax.set_xticklabels(cursos, rotation=0)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))

    # Grilla más debil que los bordes
    plt.grid(axis="y", linestyle="--", alpha=0.6, linewidth=0.7, zorder=0)

    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300)
    plt.close()
    return None

def boxplot_logro_por_curso(
    df_estudiantes: pd.DataFrame,
    nombre_grafico: str = "aux_files/distribucion_rendimiento_por_curso.png"
):
    # ---- Datos
    cursos = sorted(df_estudiantes["Curso"].unique(), key=lambda x: str(x))
    data = [df_estudiantes.loc[df_estudiantes["Curso"] == c, "Logro"].dropna().values for c in cursos]
    # Se formatea el curso dando I A (TPI-710) -> I A
    cursos = [c.split(" (")[0] for c in cursos]

    # ---- Colores por curso
    cmap = plt.cm.tab10
    colors = {c: cmap(i % 10) for i, c in enumerate(cursos)}

    # ---- Figura
    fig, ax = plt.subplots(figsize=(6,4))

    # Boxplot sin relleno
    bp = ax.boxplot(
        data,
        positions=np.arange(len(cursos)),
        widths=0.6,
        patch_artist=True,
        showfliers=True,
        medianprops=dict(color="black", linewidth=2),
        boxprops=dict(facecolor="none", edgecolor="black", linewidth=1.5),
        whiskerprops=dict(color="black"),
        capprops=dict(color="black")
    )
    # Colorear cada box con alpha
    for patch, curso in zip(bp['boxes'], cursos):
        patch.set_facecolor(colors[curso])
        patch.set_alpha(0.6)
    
    # Ejes y formato
    ax.set_title("Distribución de Rendimiento por Curso")
    ax.set_xlabel("Curso")
    ax.set_ylabel("Rendimiento (%)")
    ax.set_xticks(np.arange(len(cursos)))
    ax.set_xticklabels(cursos, rotation=0)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))

    # Grilla más debil que los bordes
    plt.grid(axis="y", linestyle="--", alpha=0.6, linewidth=0.7, zorder=0)

    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300)
    plt.close()
    return None

def logro_promedio_por_eje(df_preguntas, nombre_grafico="aux_files/logro_promedio_por_eje.png"):
    # Agrupamos por Curso y Eje Temático
    resumen = df_preguntas.groupby(["Curso", "Eje Temático"]).agg(
        Promedio=("Logro", "mean")
    ).reset_index()

    cursos = resumen["Curso"].unique()
    ejes = resumen["Eje Temático"].unique()
    x = np.arange(len(cursos))
    width = 0.18

    # Se formatea el curso dando I A (TPI-710) -> I A
    cursos = [c.split(" (")[0] for c in cursos]

    # Se usa la paleta de colores 
    colores = plt.cm.Set2.colors
    colores = {eje: colores[i] for i, eje in enumerate(ejes)}

    fig, ax = plt.subplots(figsize=(12,6))
    
    # Se agregan barras con etiquetas
    for i, eje in enumerate(ejes):
        valores = resumen[resumen["Eje Temático"] == eje]["Promedio"].values
        bars = ax.bar(x + i*width - (width*len(ejes)/2), valores,
                      width, label=eje, color=colores.get(eje, None), zorder=2, edgecolor="gray", linewidth=0.8)

        # Etiquetas arriba, con un fondo blanco transparente para mejor visibilidad
        for bar, val in zip(bars, valores):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f"{val:.0%}", ha="center", va="bottom", fontsize=8, zorder=3, bbox=dict(facecolor='white', edgecolor='none', pad=1, alpha=0.7))

    # Se agrega grilla
    plt.grid(axis='y', linestyle="--", linewidth=0.9, zorder=0)

    ax.set_xticks(x)
    ax.set_xticklabels(cursos, ha="right")
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_ylabel("Logro")
    ax.set_title("Logro Promedio por Eje Temático")

    ax.legend(title="Eje Temático")
    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300)
    plt.close()

    return None

def logro_promedio_por_habilidad(df_preguntas, nombre_grafico="aux_files/logro_promedio_por_habilidad.png"):
    # Agrupamos por Curso y Habilidad
    resumen = df_preguntas.groupby(["Curso", "Habilidad"]).agg(
        Promedio=("Logro", "mean")
    ).reset_index()

    cursos = resumen["Curso"].unique()
    habilidades = resumen["Habilidad"].unique()
    x = np.arange(len(cursos))
    width = 0.18

    # Se formatea el curso dando I A (TPI-710) -> I A
    cursos = [c.split(" (")[0] for c in cursos]

    # Se usa la paleta de colores 
    colores = plt.cm.Set2.colors
    colores = {habilidad: colores[i] for i, habilidad in enumerate(habilidades)}

    fig, ax = plt.subplots(figsize=(12,6))
    
    # Se agregan barras con etiquetas
    for i, habilidad in enumerate(habilidades):
        valores = resumen[resumen["Habilidad"] == habilidad]["Promedio"].values
        bars = ax.bar(x + i*width - (width*len(habilidades)/2), valores,
                      width, label=habilidad, color=colores.get(habilidad, None), zorder=2, edgecolor="gray", linewidth=0.8)

        # Etiquetas arriba, con un fondo blanco transparente para mejor visibilidad
        for bar, val in zip(bars, valores):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f"{val:.0%}", ha="center", va="bottom", fontsize=8, zorder=3, bbox=dict(facecolor='white', edgecolor='none', pad=1, alpha=0.7))

    # Se agrega grilla
    plt.grid(axis='y', linestyle="--", linewidth=0.9, zorder=0)

    ax.set_xticks(x)
    ax.set_xticklabels(cursos, ha="right")
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_ylabel("Logro")
    ax.set_title("Logro Promedio por Habilidad")

    ax.legend(title="Habilidad")
    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300)
    plt.close()

    return None

def alumnos_por_nivel(df_estudiantes, nombre_grafico="aux_files/alumnos_por_nivel.png"):
    # Agrupamos por Curso y Nivel de Logro → cantidad de alumnos
    resumen = df_estudiantes.groupby(["Curso", "NIVEL DE LOGRO"]).size().reset_index(name="Cantidad")

    # Pivot para stacked bar
    pivot = resumen.pivot(index="Curso", columns="NIVEL DE LOGRO", values="Cantidad").fillna(0)

    # Ordenar cursos
    cursos = pivot.index.tolist()

    # Se formatean los cursos dando I A (TPI-710) -> I A
    cursos = [c.split(" (")[0] for c in cursos]

    # Paleta
    colores = {
        "Avanzado": "#1f9e89",   # verde-agua
        "Intermedio": "#f1a340", # amarillo
        "Inicial": "#e64b35"     # rojo
    }

    fig, ax = plt.subplots(figsize=(10,6))

    bottom = None
    for nivel in ["Inicial", "Intermedio", "Avanzado"]:
        vals = pivot[nivel] if nivel in pivot.columns else [0]*len(cursos)
        bars = ax.bar(cursos, vals, label=nivel, color=colores[nivel], bottom=bottom, zorder=2)
        bottom = vals if bottom is None else bottom + vals

        # Etiquetas centradas y en negrita
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_y() + bar.get_height()/2,
                        f"{int(val)}", ha="center", va="center", fontsize=9, color="white", zorder=3, fontweight='bold')

    # Grilla suave
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="y", linestyle="--", alpha=0.6, zorder=0)

    ax.set_title("Cantidad de Alumnos por Nivel de Logro y Curso")
    ax.set_ylabel("Cantidad")
    ax.set_xlabel("Curso")
    # Leyenda a la derecha fuera del gráfico
    ax.legend(title="Nivel de Logro", loc="upper left", bbox_to_anchor=(1, 1))

    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300)
    plt.close()

    return None

def tabla_logro_por_alumno(df_estudiantes, curso):

    # Se filtra por curso y se seleccionan columnas necesarias
    df = df_estudiantes[df_estudiantes["Curso"] == curso][["Número de Lista", "Nombre del Estudiante", "Logro", "NIVEL DE LOGRO"]].copy()
    df = df.sort_values(by="Logro", ascending=False)
    df = df.reset_index(drop=True)
    # Formatear el logro como porcentaje sin decimales
    df["Logro"] = (df["Logro"]*100).round(0).astype(int).astype(str) + " %"

    # Renombrar columnas
    df = df.rename(columns={
        "NIVEL DE LOGRO": "Nivel",
        "Número de Lista": "N° Lista",
        "Nombre del Estudiante": "Estudiante"
    })

    return df

def tabla_logro_por_pregunta(df_preguntas, curso):

    # Filtrar por curso y seleccionar columnas necesarias
    df = df_preguntas[df_preguntas["Curso"] == curso][["N° Pregunta", "Eje Temático", "Habilidad", "Logro", "Nivel de Logro"]].copy()
    df = df.sort_values(by="Logro", ascending=False)
    df = df.reset_index(drop=True)
    # Formatear el logro como porcentaje sin decimales
    df["Logro"] = (df["Logro"]*100).round(0).astype(int).astype(str) + " %"

    return df

def crear_df_comparacion(df_diagnostico, df_intermedio):
    


    
    
    df_diagnostico['Evaluación'] = 'Diagnóstico'
    df_intermedio['Evaluación'] = 'Intermedio'
    
    df_comparacion = pd.DataFrame({
        'Diagnóstico': df_diagnostico.groupby('CURSO')['Logro'].mean(),
        'Intermedio': df_intermedio.groupby('Curso')['Logro'].mean()
        }).reset_index()

    df_comparacion = df_comparacion.rename(columns={'index': 'Curso'})

    # Se ordena el DataFrame por Curso alfabéticamente
    df_comparacion = df_comparacion.sort_values(by='Curso')

    # Se formatea el curso con split en " (" y se toma la primera parte
    df_comparacion['Curso'] = df_comparacion['Curso'].apply(lambda x: x.split(" (")[0])

    return df_comparacion

def comparacion_logro_por_curso(df_comparacion, nombre_grafico="aux_files/comparacion_logro_por_curso.png"):
    # Agrupamos por Curso y Evaluación
    resumen = df_comparacion.melt(id_vars=["Curso"], value_vars=["Diagnóstico", "Intermedio"],
                                  var_name="Evaluación", value_name="Logro")
    cursos = resumen["Curso"].unique()
    evaluaciones = resumen["Evaluación"].unique()
    x = np.arange(len(cursos))
    width = 0.8 / max(1, len(evaluaciones))  # Ancho de las barras

    # Se usa la paleta de colores
    colores = plt.cm.Set2.colors
    colores = {evaluacion: colores[i] for i, evaluacion in enumerate(evaluaciones)}

    fig, ax = plt.subplots(figsize=(12,6))
    for i, evaluacion in enumerate(evaluaciones):
        valores = resumen[resumen["Evaluación"] == evaluacion]["Logro"].values
        bars = ax.bar(x + i*width - (width*len(evaluaciones)/2), valores, width,
                      label=evaluacion, color=colores[evaluacion], zorder=2, edgecolor="gray", linewidth=0.8)
        for bar, val in zip(bars, valores):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.01,
                    f"{val:.0%}", ha="center", va="bottom", fontsize=8, zorder=3,
                    bbox=dict(facecolor='white', edgecolor='none', pad=1, alpha=0.7))
            
    # Se agrega grilla
    plt.grid(axis='y', linestyle="--", linewidth=0.9, zorder=0)

    ax.set_xticks(x)
    ax.set_xticklabels(cursos, ha="right")
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_ylabel("Logro")
    ax.set_title("Logro Promedio por Eje Temático")

    ax.legend(title="Eje Temático", framealpha=0.6)
    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300)
    plt.close()

    return None

# Lista de aprox 700 elementos con combinaciones de letras del alfabeto

alfabeto = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
# Se crea una lista con las letras del alfabeto en mayúscula, ['A', 'B', 'C', ..., 'Z', 'AA', 'AB', ...]
indice_alfabetico = []
for i in range(1, 3):  # Hasta 2 letras (puede ajustarse según necesidad)
    for combo in itertools.product(alfabeto, repeat=i):
        indice_alfabetico.append(''.join(combo))

formato_informe_generico = r""" 
\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[spanish]{babel}
\usepackage[letterpaper,headheight=61pt, bottom=2cm, top=3.5cm, left=2.5cm,right=2.5cm]{geometry}
\usepackage{fancyhdr} %para encabezado y pie de página
\usepackage{tikz} %para imágenes en el encabezado
\usepackage{graphicx} %para imágenes
\usepackage{caption} %para comentarios en tablas e imágenes
\usepackage{multirow} % para las tablas
\usepackage{float} %usar [H]
\usepackage{setspace} %interlineado
\usepackage{fontspec} %para definir fuentes


\input{variables.tex} % archivo con variables

\setmainfont{Segoe UI}[
    BoldFont = Segoe UI Bold,
    ItalicFont = Segoe UI Italic
]
\setlength{\parskip}{5pt}

\pagestyle{fancy}

\lhead{\pgfimage[height=2.0cm]{\leftimage}}
\rhead{\pgfimage[height=2.0cm]{\rightimage}}

\chead{
	\centerheaderone\\
	\centerheadertwo\\
	\centerheaderthree\\
}

\lfoot{\leftfooter}
\cfoot{}
\rfoot{\rightfooter}

\renewcommand{\headrulewidth}{0.4pt}% Default \headrulewidth is 0.4pt
\renewcommand{\footrulewidth}{0.4pt}% Default \footrulewidth is 0pt

\renewcommand{\figurename}{Figura}
\renewcommand{\tablename}{Tabla}

\begin{document}

\thispagestyle{fancy}
\spacing{1.1}

% Se agrega el título
\begin{center}
    \huge{\documenttitle}\\
    \vspace{0.5cm}
    \Large{\schoolname}\\
    \vspace{0.5cm}
\end{center}
"""