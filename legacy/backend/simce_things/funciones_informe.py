"""Funciones auxiliares para el procesamiento de datos."""
import itertools
import pandas as pd
import numpy as np
import matplotlib.transforms as mtransforms

N_prueba = {"abril": 1, "junio": 2, "agosto": 3, "octubre": 4, "noviembre": 5}

def crear_tabla_estadistica_por_pregunta(
        df_preguntas,
        parametros,
        columnas_alternativas = ["A", "B", "C", "D", "E"],
        columnas_data = ["Pregunta", "Correcta", "Distractor"],
        ):
    """Crea una tabla de estadística por pregunta del establecimiento en general (se ignora el curso, se agrupa por pregunta)"""
    # Se filtra el dataframe por los parámetros dados
    for key, value in parametros.items():
        if key in df_preguntas.columns:
            df_preguntas = df_preguntas[df_preguntas[key] == value]

    # Agrupar por Pregunta, se suman las columnas A,B,C,D,E para el resto de columnas no se resume.
    resumen = df_preguntas.groupby("Pregunta")[columnas_alternativas].sum().reset_index()
    # Luego de cada columna se agrega el porcentaje respecto al total de respuestas, por ejemplo A, %A
    for col in columnas_alternativas:
        valor = resumen[col]/resumen[columnas_alternativas].sum(axis=1)
        resumen[f"%{col}"] = valor.apply(lambda x: f"{x:.0%}")
    
    # Se ordenan las columnas
    resumen = resumen[["Pregunta"] + list(itertools.chain.from_iterable(
        (col, f"%{col}") for col in columnas_alternativas
    ))]

    # Se agregan las columnas de Correcta, Distractor, Habilidad, Eje temático. Son valores unicos por pregunta, se toma el primer valor.
    resumen = pd.merge(resumen, df_preguntas[columnas_data].drop_duplicates(subset=["Pregunta"]), on="Pregunta", how="left")

    # Se ordena por Pregunta
    resumen = resumen.sort_values(by="Pregunta").reset_index(drop=True)

    return resumen

def extraer_datos(nombre_archivo):
    """Teniendo un archivo excel en el formato ASIGNATURA_MES_estudiantes.xlsx, se retorna una tupla con la asignatura en 
    mayusculas, el mes en mayusculas, y un numero asociado al numero de prueba por mes"""
    partes = nombre_archivo.split('_')
    asignatura = partes[0].upper()
    mes = partes[1].upper()
    numero_prueba = N_prueba.get(partes[1].lower(), None)
    return asignatura, mes, numero_prueba

def agregar_columnas_dataframe(df, datos):
    """Agrega columnas de asignatura, mes y numero de prueba a un DataFrame dado."""
    asignatura, mes, numero_prueba = datos
    df['Asignatura'] = asignatura
    df['Mes'] = mes
    df['Numero_Prueba'] = numero_prueba
    return df

def limpiar_columnas(df):
    """Teniendo las columnas Rend y Curso se modifian tal que:
    1) Rend quede como un número entre 0 y 1. A veces está en porcentaje o en número de 0 a 100.
    2) Curso se elimine la parte de '° medio ' y quede solo el número y la letra sin espacios.
    3) Si los  nombres de columnas tienen B, M, O se reemplazan por Buenas, Malas, Omitidas respectivamente."""
    # Renombrar columnas B, M, O
    df = df.rename(columns={'B': 'Buenas', 'M': 'Malas', 'O': 'Omitidas'})
    # Se elimina columna de Avance si existe    
    if 'Avance' in df.columns:
        df = df.drop(columns=['Avance'])
    # Se renombra la columna de Rut a RUT
    if 'RUT' not in df.columns and 'Rut' in df.columns:
        df = df.rename(columns={'Rut': 'RUT'})
    # Se elimina la columna Logro II si existe
    if 'Logro II' in df.columns:
        df = df.drop(columns=['Logro II'])
    # Limpiar columna Rend
    def limpiar_rend(valor):
        if isinstance(valor, str) and valor.endswith('%'):
            return float(valor.strip('%')) / 100
        elif isinstance(valor, (int, float)) and valor > 1:
            return valor / 100
        elif isinstance(valor, (int, float)):
            return valor
        else:
            return None
    if "Rend" in df.columns:
        df['Rend'] = df['Rend'].apply(limpiar_rend)

    # Limpiar columna Curso
    def limpiar_curso(curso):
        if isinstance(curso, str):
            curso = curso.replace('° medio ', '').strip()
            return curso
        return curso
    if "Curso" in df.columns:
        df['Curso'] = df['Curso'].apply(limpiar_curso)

    return df

# Se toma el archivo simce_2025_estudiantes.xlsx, y se filtra sólo por las filas correspondientes a Numero_Prueba = 4, la asignatura correspondiente y el curso correspondiente.

def calcular_avance_promedio(df_estudiantes, estudiante, asignatura, numero_prueba=4):
    df_estudiante = df_estudiantes[(df_estudiantes['RUT'] == estudiante) & (df_estudiantes['Asignatura'] == asignatura) & (df_estudiantes['Numero_Prueba'] <= numero_prueba)]
    # Se guarda en dos listas el numero de prueba y el logro obtenido
    n_pruebas, rends = [], []
    for _, row in df_estudiante.iterrows():
        n_pruebas.append(row['Numero_Prueba'])
        rends.append(row['Rend'])
    # Se calcula una regresion lineal entre n_pruebas (X) y logros (Y)
    if len(n_pruebas) > 1:
        coef = np.polyfit(n_pruebas, rends, 1)
        pendiente = coef[0]
        return pendiente
    return 0

def crear_tabla(df_estudiantes, parametros):
    asignatura = parametros['Asignatura']
    curso = parametros.get('Curso', 'todos')
    numero_prueba = parametros.get('Numero_Prueba', 4)

    df_filtrado = df_estudiantes[
        (df_estudiantes['Numero_Prueba'] <= numero_prueba) &
        (df_estudiantes['Asignatura'] == asignatura) 
    ].copy()
    # Si curso dice 'todos', no se filtra por curso
    if curso != 'todos':
        df_filtrado = df_filtrado[df_filtrado['Curso'] == curso].copy()
    df_filtrado['Avance_Promedio'] = 0.0
    # Se agrega la columna Avance_Promedio que se calcula con la funcion anterior
    for _, row in df_filtrado.iterrows():
        df_filtrado.at[row.name, 'Avance_Promedio'] = calcular_avance_promedio(df_estudiantes, row['RUT'], row['Asignatura'], numero_prueba)
    return df_filtrado

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

import itertools
import os

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
    latex += headers.replace('%', '\\%')

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

def resumen_estadistico_basico(df_estudiantes, columna, formato = "percent", agrupar_por = "Curso", **parametros):
    """Teniendo un dataset, se crea un resumen con cuenta de alumnos, promedio, minimo y maximo de la columna indicada.
    Se formatean los valores por percent o number."""
    # Se filtra el dataframe por los parámetros dados
    for key, value in parametros.items():
        if key in df_estudiantes.columns:
            df_estudiantes = df_estudiantes[df_estudiantes[key] == value]

    # Agrupa por curso y calcula el resumen
    resumen_por_curso = df_estudiantes.groupby(agrupar_por)
    #print(resumen_por_curso)
    # Se agregan las columnas de porcentaje de logro por curso, Mínimo, Promedio, Máximo
    resumen_por_curso = resumen_por_curso.agg(
        Alumnos=(columna, 'size'),
        Promedio=(columna, 'mean'),
        Minimo=(columna, 'min'),
        Maximo=(columna, 'max')
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

#DEPRECATED
###################################
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

def grafico_barras_promedio_por(df_estudiantes, columna_valor, agrupar_por = "Curso", titulo = "Logro Promedio por Curso", ylabel = "Logro (%)", nombre_grafico="aux_files/logro_promedio_por_curso.png"):
    """Teniendo un dataframe de estudiantes, se crea un gráfico de barras del promedio de la columna_valor agrupado por agrupar_por."""
    
    # Agrupar por curso y calcular promedio
    resumen = df_estudiantes.groupby(agrupar_por).agg(
        Promedio=(columna_valor, "mean")
    ).reset_index()

    # Crear gráfico
    fig, ax = plt.subplots(figsize=(8,4))
    bars = ax.bar(resumen[agrupar_por], resumen["Promedio"], color=plt.cm.Set2.colors, edgecolor="black", linewidth=1.2, zorder=3)

    # Eje Y en porcentaje
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))

    ax.set_title(titulo)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(agrupar_por)
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

def boxplot_valor_por_curso(
    df_estudiantes: pd.DataFrame,
    columna_valor: str,
    agrupar_por: str = "Curso",
    titulo_grafico: str = "Distribución de Rendimiento por Curso",
    ylabel = "",
    ylims = None,
    formato = "number",  # "number" o "percent"
    nombre_grafico: str = "aux_files/distribucion_rendimiento_por_curso.png"
):
    # ---- Datos
    cursos = sorted(df_estudiantes[agrupar_por].unique(), key=lambda x: str(x))
    data = [df_estudiantes.loc[df_estudiantes[agrupar_por] == c, columna_valor].dropna().values for c in cursos]
    
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
    ax.set_title(titulo_grafico)
    ax.set_xlabel(agrupar_por)
    ax.set_ylabel(ylabel)
    ax.set_xticks(np.arange(len(cursos)))
    ax.set_xticklabels(cursos, rotation=0)
    if ylims:
        ax.set_ylim(ylims)
    if formato == "percent":
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

    # Grilla más debil que los bordes
    plt.grid(axis="y", linestyle="--", alpha=0.6, linewidth=0.7, zorder=0)

    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300)
    plt.close()
    return None


def alumnos_por_nivel_curso_y_mes(
    df_estudiantes,
    columna_nivel="Logro",
    columna_curso="Curso",
    columna_mes="Mes",
    lista_niveles = ("Insuficiente","Elemental","Adecuado"),
    lista_paleta = ["#C2A47A", "#2196F3", "#5FA59E"],
    orden_cursos=["2A","2B","2C","2D"],
    orden_meses=["ABRIL","JUNIO","AGOSTO","OCTUBRE", "NOVIEMBRE"],
    titulo_grafico="Comparación de Alumnos por Nivel de Logro, Curso y Mes",
    titulo_leyenda="Nivel de Logro",
    ylabel="Cantidad",
    nombre_grafico="aux_files/alumnos_por_nivel_curso_mes.png",
    rot_x=90,                   # rotación de etiquetas de mes
    mostrar_totales=True,
):
    # ---- 1) Agregación ----
    resumen = (
        df_estudiantes
        .groupby([columna_curso, columna_mes, columna_nivel])
        .size().reset_index(name="Cantidad")
    )

    # Ordenar cursos y meses si se proveen
    if orden_cursos is None:
        orden_cursos = (
            df_estudiantes[columna_curso].dropna().unique().tolist()
        )
    if orden_meses is None:
        # Orden natural de aparición
        orden_meses = (
            df_estudiantes[columna_mes].dropna().unique().tolist()
        )

    # Asegurar categorías ordenadas (evita columnas desordenadas)
    resumen[columna_curso] = pd.Categorical(resumen[columna_curso],
                                            categories=orden_cursos, ordered=True)
    resumen[columna_mes]   = pd.Categorical(resumen[columna_mes],
                                            categories=orden_meses, ordered=True)
    resumen[columna_nivel] = pd.Categorical(resumen[columna_nivel],
                                            categories=list(lista_niveles), ordered=True)

    # Pivot multi-índice (Curso, Mes) x Nivel → Cantidad
    pivot = (
        resumen
        .pivot_table(index=[columna_curso, columna_mes],
                     columns=columna_nivel,
                     values="Cantidad",
                     aggfunc="sum", fill_value=0)
        .reindex(pd.MultiIndex.from_product([orden_cursos, orden_meses],
                                            names=[columna_curso, columna_mes]),
                 fill_value=0)
    )

    # ---- 2) Eje X como pares (Curso|Mes) ----
    x_labels = [m for (_, m) in pivot.index]
    x_positions = np.arange(len(pivot))

    # ---- 3) Colores por nivel 
    # Insuficiente (arena/ocre), Elemental (azul), Adecuado (verde)
    paleta = {
        "Insuficiente": "#C2A47A",
        "Elemental":    "#2196F3",
        "Adecuado":     "#5FA59E",
    }
    # Respaldo por si los niveles vienen en otro orden/nombres
    colores = {n: paleta.get(n, "#888888") for n in lista_niveles}

    # ---- 4) Plot ----
    fig, ax = plt.subplots(figsize=(12, 7))
    bottom = np.zeros(len(pivot), dtype=float)

    for nivel in lista_niveles:
        vals = pivot[nivel].values if nivel in pivot.columns else np.zeros(len(pivot))
        bars = ax.bar(x_positions, vals, label=nivel, color=colores[nivel], bottom=bottom, zorder=2)

        # Etiquetas internas
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width()/2,
                    bar.get_y() + bar.get_height()/2,
                    f"{int(val)}",
                    ha="center", va="center", fontsize=9, color="white",
                    fontweight="bold", zorder=3
                )
        bottom += vals

    # Totales encima de cada barra
    if mostrar_totales:
        for x, total in zip(x_positions, bottom):
            if total > 0:
                ax.text(x, total + 0.6, f"{int(total)}", ha="center", va="bottom",
                        fontsize=9, color="#444444", fontweight="bold")

    # ---- 5) Separadores y rótulos de curso bajo cada bloque ----
    # Calcula los cortes cada N_meses barras
    n_meses = len(orden_meses)
    course_centers = []
    for i, curso in enumerate(orden_cursos):
        start = i * n_meses
        end   = start + n_meses
        # línea discontinua al inicio de cada bloque (excepto el primero)
        if i > 0:
            ax.axvline(start - 0.5, ls=(0, (3, 3)), color="#666666", lw=1, alpha=0.7, zorder=1)
        # posición central para el rótulo del curso
        course_centers.append((start + end - 1) / 2.0)

    # Última línea discontinua al final del último bloque (opcional/estético)
    ax.axvline(len(x_positions) - 0.5, ls=(0, (3, 3)), color="#666666", lw=1, alpha=0.7, zorder=1)

    # ——— rótulos de cursos usando mezcla de transforms (x en datos, y en ejes)
    xt = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)

    curso_offset = -0.20  # más negativo = más abajo (prueba -0.10 a -0.20)
    for center, curso in zip(course_centers, orden_cursos):
        ax.text(center, curso_offset, curso,
                transform=xt, ha="center", va="top",
                fontsize=11, fontweight="bold", clip_on=False)

    # ---- 6) Ejes, grilla, leyenda ----
    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels, rotation=rot_x, ha="right")
    ax.set_title(titulo_grafico, pad=14, fontsize=14, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", linestyle="--", alpha=0.5, zorder=0)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    # Leyenda arriba, parecida a tu ejemplo
    leg = ax.legend(title=titulo_leyenda, loc="upper center", bbox_to_anchor=(0.5, 1.12),
                    ncol=len(lista_niveles), frameon=False)
    if leg and leg.get_title():
        leg.get_title().set_fontweight('bold')

    plt.subplots_adjust(bottom=0.20)  

    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300, bbox_inches="tight")
    plt.close()

    return pivot.reset_index()  # opcional: devuelve la tabla base usada para el gráfico

def valor_promedio_agrupado_por(
        df_preguntas, 
        columna_valor, 
        agrupar_principal_por = "Curso", 
        agrupar_secundario_por = "",
        orden_grupo_secundario = "Numero_Prueba", # Si no se quiere ordenar, dejar como ""
        titulo_grafico = "", 
        titulo_leyenda = "",
        y_lims = None,
        formato = "number", # number o percent
        nombre_grafico="aux_files/logro_promedio_por_X.png"):
    # Agrupamos por Curso y Eje Temático
    resumen = df_preguntas.groupby([agrupar_principal_por, agrupar_secundario_por]).agg(
        Promedio=(columna_valor, "mean")
    ).reset_index()

    grupo_primario = resumen[agrupar_principal_por].unique()
    grupo_secundario = resumen[agrupar_secundario_por].unique()
    x = np.arange(len(grupo_primario))
    width = 0.18

    # Se ordena el grupo secundario si se indicó una columna de orden
    if orden_grupo_secundario in df_preguntas.columns and orden_grupo_secundario != "":
        orden = df_preguntas[[agrupar_secundario_por, orden_grupo_secundario]].drop_duplicates()
        orden = orden.sort_values(by=orden_grupo_secundario)
        grupo_secundario = orden[agrupar_secundario_por].tolist()

    # Se usa la paleta de colores 
    colores = plt.cm.Set2.colors
    colores = {eje: colores[i] for i, eje in enumerate(grupo_secundario)}

    fig, ax = plt.subplots(figsize=(12,6))
    
    # Se agregan barras con etiquetas
    for i, eje in enumerate(grupo_secundario):
        valores = resumen[resumen[agrupar_secundario_por] == eje]["Promedio"].values
        bars = ax.bar(x + i*width - (width*len(grupo_secundario)/2), valores,
                      width, label=eje, color=colores.get(eje, None), zorder=2, edgecolor="gray", linewidth=0.8)

        # Etiquetas arriba, con un fondo blanco transparente para mejor visibilidad
        for bar, val in zip(bars, valores):
            format_str = "{val:.0%}" if formato == "percent" else "{val:.0f}"
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    format_str.format(val=val), ha="center", va="bottom", fontsize=8, zorder=3, bbox=dict(facecolor='white', edgecolor='none', pad=1, alpha=0.7))

    # Se agrega grilla
    plt.grid(axis='y', linestyle="--", linewidth=0.9, zorder=0)

    ax.set_xticks(x)
    ax.set_xticklabels(grupo_primario, ha="right")
    if y_lims is not None:
        ax.set_ylim(y_lims)
    if formato == "percent":
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))
        ax.set_ylabel(f"{columna_valor} (%)")
    else:
        ax.set_ylabel(f"{columna_valor}")
    ax.set_ylabel(columna_valor)
    ax.set_title(titulo_grafico)

    ax.legend(title=titulo_leyenda)
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

def alumnos_por_nivel_cualitativo(df_estudiantes, columna_nivel = "Logro", agrupar_por = "Curso", lista_niveles = ["Adecuado", "Elemental", "Insuficiente"], titulo_grafico = "", titulo_leyenda = "", ylabel = "", nombre_grafico="aux_files/alumnos_por_nivel.png"):
    # Agrupamos por Curso y Nivel de Logro → cantidad de alumnos
    resumen = df_estudiantes.groupby([agrupar_por, columna_nivel]).size().reset_index(name="Cantidad")

    # Pivot para stacked bar
    pivot = resumen.pivot(index=agrupar_por, columns=columna_nivel, values="Cantidad").fillna(0)

    # Ordenar cursos
    cursos = pivot.index.tolist()

    # Paleta
    colores = {
        lista_niveles[0]: "#1f9e89",   # verde-agua
        lista_niveles[1]: "#f1a340", # amarillo
        lista_niveles[2]: "#e64b35"     # rojo
    }

    fig, ax = plt.subplots(figsize=(10,6))

    bottom = None
    for nivel in lista_niveles[::-1]: # Se grafica de abajo hacia arriba
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

    ax.set_title(titulo_grafico)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(agrupar_por)
    
    # Leyenda a la derecha fuera del gráfico
    ax.legend(title=titulo_leyenda, loc="upper left", bbox_to_anchor=(1, 1))

    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300)
    plt.close()

    return None

def tabla_logro_por_alumno(
        df_estudiantes, 
        parametros,
        sort_by = "Rend",
        formatos = {"Rend": "percent", "SIMCE": "number", "Avance_Promedio": "percent"},
        columnas = ["Nombre", "Rend", "SIMCE", "Logro", "Avance_Promedio"],
        columnas_renombrar = {"Nombre": "Estudiante", "Rend": "Logro", "SIMCE": "SIMCE", "Logro": "Nivel", "Avance_Promedio": "Avance"}
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
        agrupar_por = "Curso",
        sort_by = "Logro",
        formatos = {"Logro": "percent"},
        columnas = ["Pregunta", "Habilidad", "Logro"],
        columnas_renombrar = {"Pregunta": "N° Pregunta", "Habilidad": "Habilidad", "Logro": "Logro", "Eje Temático": "Eje Temático"}
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
\documentclass[10pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[spanish]{babel}
\usepackage[letterpaper,headheight=61pt, bottom=2cm, top=3.5cm, left=2cm,right=2cm]{geometry}
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