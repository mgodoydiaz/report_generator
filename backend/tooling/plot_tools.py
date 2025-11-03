import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
from matplotlib.ticker import PercentFormatter
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

import pandas as pd
import numpy as np


def grafico_barras_promedio_por(
    df_estudiantes,
    columna_valor,
    agrupar_por="Curso",
    titulo="Logro Promedio por Curso",
    ylabel="Logro (%)",
    nombre_grafico="aux_files/logro_promedio_por_curso.png",
):
    """Teniendo un dataframe de estudiantes, se crea un gráfico de barras del promedio de la columna_valor agrupado por agrupar_por."""

    # Agrupar por curso y calcular promedio
    resumen = (
        df_estudiantes.groupby(agrupar_por)
        .agg(Promedio=(columna_valor, "mean"))
        .reset_index()
    )

    # Crear gráfico
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(
        resumen[agrupar_por],
        resumen["Promedio"],
        color=plt.cm.Set2.colors,
        edgecolor="black",
        linewidth=1.2,
        zorder=3,
    )

    # Eje Y en porcentaje
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))

    ax.set_title(titulo)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(agrupar_por)
    ax.tick_params(axis="x", rotation=0)

    # Etiquetas arriba de cada barra
    for bar, val in zip(bars, resumen["Promedio"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{val:.0%}",
            ha="center",
            va="bottom",
        )

    # Grilla más debil que los bordes
    ax.grid(axis="y", linestyle="--", linewidth=0.9, zorder=0)

    plt.tight_layout()
    plt.savefig(nombre_grafico)
    plt.close()

    return None


def boxplot_valor_por_curso(
    df_estudiantes: pd.DataFrame,
    columna_valor: str,
    agrupar_por: str = "Curso",
    titulo_grafico: str = "Distribución de Rendimiento por Curso",
    ylabel="",
    ylims=None,
    formato="number",  # "number" o "percent"
    nombre_grafico: str = "aux_files/distribucion_rendimiento_por_curso.png",
):
    # ---- Datos
    cursos = sorted(df_estudiantes[agrupar_por].unique(), key=lambda x: str(x))
    data = [
        df_estudiantes.loc[df_estudiantes[agrupar_por] == c, columna_valor]
        .dropna()
        .values
        for c in cursos
    ]

    # ---- Colores por curso
    cmap = plt.cm.tab10
    colors = {c: cmap(i % 10) for i, c in enumerate(cursos)}

    # ---- Figura
    fig, ax = plt.subplots(figsize=(6, 4))

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
        capprops=dict(color="black"),
    )
    # Colorear cada box con alpha
    for patch, curso in zip(bp["boxes"], cursos):
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


def valor_promedio_agrupado_por(
    df_preguntas,
    columna_valor,
    agrupar_principal_por="Curso",
    agrupar_secundario_por="",
    orden_grupo_secundario="Numero_Prueba",  # Si no se quiere ordenar, dejar como ""
    titulo_grafico="",
    titulo_leyenda="",
    y_lims=None,
    formato="number",  # number o percent
    nombre_grafico="aux_files/logro_promedio_por_X.png",
):
    # Agrupamos por Curso y Eje Temático
    resumen = (
        df_preguntas.groupby([agrupar_principal_por, agrupar_secundario_por])
        .agg(Promedio=(columna_valor, "mean"))
        .reset_index()
    )

    grupo_primario = resumen[agrupar_principal_por].unique()
    grupo_secundario = resumen[agrupar_secundario_por].unique()
    x = np.arange(len(grupo_primario))
    width = 0.18

    # Se ordena el grupo secundario si se indicó una columna de orden
    if orden_grupo_secundario in df_preguntas.columns and orden_grupo_secundario != "":
        orden = df_preguntas[
            [agrupar_secundario_por, orden_grupo_secundario]
        ].drop_duplicates()
        orden = orden.sort_values(by=orden_grupo_secundario)
        grupo_secundario = orden[agrupar_secundario_por].tolist()

    # Se usa la paleta de colores
    colores = plt.cm.Set2.colors
    colores = {eje: colores[i] for i, eje in enumerate(grupo_secundario)}

    fig, ax = plt.subplots(figsize=(12, 6))

    # Se agregan barras con etiquetas
    for i, eje in enumerate(grupo_secundario):
        valores = resumen[resumen[agrupar_secundario_por] == eje]["Promedio"].values
        bars = ax.bar(
            x + i * width - (width * len(grupo_secundario) / 2),
            valores,
            width,
            label=eje,
            color=colores.get(eje, None),
            zorder=2,
            edgecolor="gray",
            linewidth=0.8,
        )

        # Etiquetas arriba, con un fondo blanco transparente para mejor visibilidad
        for bar, val in zip(bars, valores):
            format_str = "{val:.0%}" if formato == "percent" else "{val:.0f}"
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                format_str.format(val=val),
                ha="center",
                va="bottom",
                fontsize=8,
                zorder=3,
                bbox=dict(facecolor="white", edgecolor="none", pad=1, alpha=0.7),
            )

    # Se agrega grilla
    plt.grid(axis="y", linestyle="--", linewidth=0.9, zorder=0)

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


def alumnos_por_nivel_cualitativo(
    df_estudiantes,
    columna_nivel="Logro",
    agrupar_por="Curso",
    lista_niveles=["Adecuado", "Elemental", "Insuficiente"],
    titulo_grafico="",
    titulo_leyenda="",
    ylabel="",
    nombre_grafico="aux_files/alumnos_por_nivel.png",
):
    # Agrupamos por Curso y Nivel de Logro → cantidad de alumnos
    resumen = (
        df_estudiantes.groupby([agrupar_por, columna_nivel])
        .size()
        .reset_index(name="Cantidad")
    )

    # Pivot para stacked bar
    pivot = resumen.pivot(
        index=agrupar_por, columns=columna_nivel, values="Cantidad"
    ).fillna(0)

    # Ordenar cursos
    cursos = pivot.index.tolist()

    # Paleta
    colores = {
        lista_niveles[0]: "#1f9e89",  # verde-agua
        lista_niveles[1]: "#f1a340",  # amarillo
        lista_niveles[2]: "#e64b35",  # rojo
    }

    fig, ax = plt.subplots(figsize=(10, 6))

    bottom = None
    for nivel in lista_niveles[::-1]:  # Se grafica de abajo hacia arriba
        vals = pivot[nivel] if nivel in pivot.columns else [0] * len(cursos)
        bars = ax.bar(
            cursos, vals, label=nivel, color=colores[nivel], bottom=bottom, zorder=2
        )
        bottom = vals if bottom is None else bottom + vals

        # Etiquetas centradas y en negrita
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{int(val)}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white",
                    zorder=3,
                    fontweight="bold",
                )

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


def alumnos_por_nivel_curso_y_mes(
    df_estudiantes,
    columna_nivel="Logro",
    columna_curso="Curso",
    columna_mes="Mes",
    lista_niveles=("Insuficiente", "Elemental", "Adecuado"),
    lista_paleta=["#C2A47A", "#2196F3", "#5FA59E"],
    orden_cursos=["2A", "2B", "2C", "2D"],
    orden_meses=["ABRIL", "JUNIO", "AGOSTO", "OCTUBRE", "NOVIEMBRE"],
    titulo_grafico="Comparación de Alumnos por Nivel de Logro, Curso y Mes",
    titulo_leyenda="Nivel de Logro",
    ylabel="Cantidad",
    nombre_grafico="aux_files/alumnos_por_nivel_curso_mes.png",
    rot_x=90,  # rotación de etiquetas de mes
    mostrar_totales=True,
):
    # ---- 1) Agregación ----
    resumen = (
        df_estudiantes.groupby([columna_curso, columna_mes, columna_nivel])
        .size()
        .reset_index(name="Cantidad")
    )

    # Ordenar cursos y meses si se proveen
    if orden_cursos is None:
        orden_cursos = df_estudiantes[columna_curso].dropna().unique().tolist()
    if orden_meses is None:
        # Orden natural de aparición
        orden_meses = df_estudiantes[columna_mes].dropna().unique().tolist()

    # Asegurar categorías ordenadas (evita columnas desordenadas)
    resumen[columna_curso] = pd.Categorical(
        resumen[columna_curso], categories=orden_cursos, ordered=True
    )
    resumen[columna_mes] = pd.Categorical(
        resumen[columna_mes], categories=orden_meses, ordered=True
    )
    resumen[columna_nivel] = pd.Categorical(
        resumen[columna_nivel], categories=list(lista_niveles), ordered=True
    )

    # Pivot multi-índice (Curso, Mes) x Nivel → Cantidad
    pivot = resumen.pivot_table(
        index=[columna_curso, columna_mes],
        columns=columna_nivel,
        values="Cantidad",
        aggfunc="sum",
        fill_value=0,
    ).reindex(
        pd.MultiIndex.from_product(
            [orden_cursos, orden_meses], names=[columna_curso, columna_mes]
        ),
        fill_value=0,
    )

    # ---- 2) Eje X como pares (Curso|Mes) ----
    x_labels = [m for (_, m) in pivot.index]
    x_positions = np.arange(len(pivot))

    # ---- 3) Colores por nivel
    # Insuficiente (arena/ocre), Elemental (azul), Adecuado (verde)
    paleta = {
        "Insuficiente": "#C2A47A",
        "Elemental": "#2196F3",
        "Adecuado": "#5FA59E",
    }
    # Respaldo por si los niveles vienen en otro orden/nombres
    colores = {n: paleta.get(n, "#888888") for n in lista_niveles}

    # ---- 4) Plot ----
    fig, ax = plt.subplots(figsize=(12, 7))
    bottom = np.zeros(len(pivot), dtype=float)

    for nivel in lista_niveles:
        vals = pivot[nivel].values if nivel in pivot.columns else np.zeros(len(pivot))
        bars = ax.bar(
            x_positions,
            vals,
            label=nivel,
            color=colores[nivel],
            bottom=bottom,
            zorder=2,
        )

        # Etiquetas internas
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{int(val)}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white",
                    fontweight="bold",
                    zorder=3,
                )
        bottom += vals

    # Totales encima de cada barra
    if mostrar_totales:
        for x, total in zip(x_positions, bottom):
            if total > 0:
                ax.text(
                    x,
                    total + 0.6,
                    f"{int(total)}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    color="#444444",
                    fontweight="bold",
                )

    # ---- 5) Separadores y rótulos de curso bajo cada bloque ----
    # Calcula los cortes cada N_meses barras
    n_meses = len(orden_meses)
    course_centers = []
    for i, curso in enumerate(orden_cursos):
        start = i * n_meses
        end = start + n_meses
        # línea discontinua al inicio de cada bloque (excepto el primero)
        if i > 0:
            ax.axvline(
                start - 0.5, ls=(0, (3, 3)), color="#666666", lw=1, alpha=0.7, zorder=1
            )
        # posición central para el rótulo del curso
        course_centers.append((start + end - 1) / 2.0)

    # Última línea discontinua al final del último bloque (opcional/estético)
    ax.axvline(
        len(x_positions) - 0.5,
        ls=(0, (3, 3)),
        color="#666666",
        lw=1,
        alpha=0.7,
        zorder=1,
    )

    # ——— rótulos de cursos usando mezcla de transforms (x en datos, y en ejes)
    xt = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)

    curso_offset = -0.20  # más negativo = más abajo (prueba -0.10 a -0.20)
    for center, curso in zip(course_centers, orden_cursos):
        ax.text(
            center,
            curso_offset,
            curso,
            transform=xt,
            ha="center",
            va="top",
            fontsize=11,
            fontweight="bold",
            clip_on=False,
        )

    # ---- 6) Ejes, grilla, leyenda ----
    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels, rotation=rot_x, ha="right")
    ax.set_title(titulo_grafico, pad=14, fontsize=14, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", linestyle="--", alpha=0.5, zorder=0)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    # Leyenda arriba, parecida a tu ejemplo
    leg = ax.legend(
        title=titulo_leyenda,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.12),
        ncol=len(lista_niveles),
        frameon=False,
    )
    if leg and leg.get_title():
        leg.get_title().set_fontweight("bold")

    plt.subplots_adjust(bottom=0.20)

    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300, bbox_inches="tight")
    plt.close()

    return pivot.reset_index()  # opcional: devuelve la tabla base usada para el gráfico


def valor_promedio_agrupado_por(
    df_preguntas,
    columna_valor,
    agrupar_principal_por="Curso",
    agrupar_secundario_por="",
    orden_grupo_secundario="Numero_Prueba",  # Si no se quiere ordenar, dejar como ""
    titulo_grafico="",
    titulo_leyenda="",
    y_lims=None,
    formato="number",  # number o percent
    nombre_grafico="aux_files/logro_promedio_por_X.png",
):
    # Agrupamos por Curso y Eje Temático
    resumen = (
        df_preguntas.groupby([agrupar_principal_por, agrupar_secundario_por])
        .agg(Promedio=(columna_valor, "mean"))
        .reset_index()
    )

    grupo_primario = resumen[agrupar_principal_por].unique()
    grupo_secundario = resumen[agrupar_secundario_por].unique()
    x = np.arange(len(grupo_primario))
    width = 0.18

    # Se ordena el grupo secundario si se indicó una columna de orden
    if orden_grupo_secundario in df_preguntas.columns and orden_grupo_secundario != "":
        orden = df_preguntas[
            [agrupar_secundario_por, orden_grupo_secundario]
        ].drop_duplicates()
        orden = orden.sort_values(by=orden_grupo_secundario)
        grupo_secundario = orden[agrupar_secundario_por].tolist()

    # Se usa la paleta de colores
    colores = plt.cm.Set2.colors
    colores = {eje: colores[i] for i, eje in enumerate(grupo_secundario)}

    fig, ax = plt.subplots(figsize=(12, 6))

    # Se agregan barras con etiquetas
    for i, eje in enumerate(grupo_secundario):
        valores = resumen[resumen[agrupar_secundario_por] == eje]["Promedio"].values
        bars = ax.bar(
            x + i * width - (width * len(grupo_secundario) / 2),
            valores,
            width,
            label=eje,
            color=colores.get(eje, None),
            zorder=2,
            edgecolor="gray",
            linewidth=0.8,
        )

        # Etiquetas arriba, con un fondo blanco transparente para mejor visibilidad
        for bar, val in zip(bars, valores):
            format_str = "{val:.0%}" if formato == "percent" else "{val:.0f}"
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                format_str.format(val=val),
                ha="center",
                va="bottom",
                fontsize=8,
                zorder=3,
                bbox=dict(facecolor="white", edgecolor="none", pad=1, alpha=0.7),
            )

    # Se agrega grilla
    plt.grid(axis="y", linestyle="--", linewidth=0.9, zorder=0)

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
