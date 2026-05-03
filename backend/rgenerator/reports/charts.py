"""Biblioteca de gráficos matplotlib.

Cada función toma un DataFrame (o varios) + parámetros y produce un PNG en
disco en `nombre_grafico` (path). Las funciones son **copia textual** de
docs/desarrollo/referencia_informe/SIMCE/funciones.py — el código matplotlib
no se reinterpreta. Solo se añaden docstrings y un CHART_REGISTRY al final
para que el frontend pueda listar funciones disponibles.

Convenciones (heredadas de SIMCE/funciones.py):

- DPI = 300 en todos los savefig.
- Paleta categórica: `plt.cm.Set2.colors` (8 pasteles).
- Paleta boxplot: `plt.cm.tab10` cicled.
- Paleta semáforo (niveles ordinales): {Adecuado/Avanzado=#1f9e89, Elemental/
  Intermedio=#f1a340, Insuficiente/Inicial=#e64b35}.
- Bordes: edgecolor='black', linewidth=1.2 (barras simples) o 'gray', 0.8
  (barras agrupadas).
- Grid Y: linestyle='--', linewidth=0.9, zorder=0.
- Eje Y percent: PercentFormatter(1.0), set_ylim(0, 1).
- Etiquetas valor: fontsize=8, bbox blanco semi-transparente.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # backend sin GUI; obligatorio en server
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
from matplotlib.ticker import PercentFormatter, MaxNLocator


# ─────────────────────────────────────────────────────────────────────────
# Gráficos de barras simples
# ─────────────────────────────────────────────────────────────────────────

def grafico_barras_promedio_por(
    df_estudiantes: pd.DataFrame,
    columna_valor: str,
    agrupar_por: str = "Curso",
    titulo: str = "Logro Promedio por Curso",
    ylabel: str = "Logro (%)",
    nombre_grafico: str = "aux_files/logro_promedio_por_curso.png",
):
    """Barras: promedio de `columna_valor` agrupado por `agrupar_por`.

    Display name: Promedio por categoría (barras simples)
    Genera 1 barra por valor único de `agrupar_por`. Eje Y en porcentaje
    (0-100%) con etiqueta sobre cada barra. Paleta Set2.

    Args:
        df_estudiantes: DataFrame con al menos las columnas `columna_valor`
            y `agrupar_por`.
        columna_valor: nombre de la columna numérica a promediar (ej "Rend",
            "Logro").
        agrupar_por: columna categórica que define el eje X (ej "Curso").
        titulo: título del gráfico.
        ylabel: etiqueta del eje Y.
        nombre_grafico: path donde guardar el PNG (DPI 300).

    Equivalente LaTeX: SIMCE.grafico_barras_promedio_por,
        DIA.logro_promedio_por_curso, DIA.logro_promedio_por_nivel.
    """
    # Agrupar por curso y calcular promedio
    resumen = df_estudiantes.groupby(agrupar_por).agg(
        Promedio=(columna_valor, "mean")
    ).reset_index()

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
    ax.tick_params(axis="x", rotation=45)

    # Etiquetas arriba de cada barra
    for bar, val in zip(bars, resumen["Promedio"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{val:.0%}",
            ha="center",
            va="bottom",
        )

    # Grilla más débil que los bordes
    ax.grid(axis="y", linestyle="--", linewidth=0.9, zorder=0)

    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300)
    plt.close()
    return None


# ─────────────────────────────────────────────────────────────────────────
# Gráficos de barras agrupadas (dos categorías cruzadas)
# ─────────────────────────────────────────────────────────────────────────

def valor_promedio_agrupado_por(
    df_preguntas: pd.DataFrame,
    columna_valor: str,
    agrupar_principal_por: str = "Curso",
    agrupar_secundario_por: str = "",
    orden_grupo_secundario: str = "Numero_Prueba",
    titulo_grafico: str = "",
    titulo_leyenda: str = "",
    y_lims: tuple | None = None,
    formato: str = "number",  # "number" o "percent"
    nombre_grafico: str = "aux_files/logro_promedio_por_X.png",
):
    """Barras agrupadas: promedio de `columna_valor` cruzado por dos categorías.

    Display name: Promedio agrupado por dos categorías
    Eje X = `agrupar_principal_por` (ej "Curso"), N barras por grupo según
    `agrupar_secundario_por` (ej "Eje Temático", "Habilidad", "Mes").

    Args:
        df_preguntas: DataFrame con las 3 columnas requeridas.
        columna_valor: columna numérica a promediar.
        agrupar_principal_por: columna del eje X.
        agrupar_secundario_por: columna que genera N series por X.
        orden_grupo_secundario: columna usada para ordenar las series
            (ej "Numero_Prueba" si las series son meses). Si vacía, orden
            por aparición.
        titulo_grafico, titulo_leyenda: texto.
        y_lims: tupla (min, max) del eje Y o None.
        formato: "percent" (eje 0-1, ticker %) o "number".
        nombre_grafico: path PNG.

    Equivalente LaTeX: SIMCE.valor_promedio_agrupado_por,
        DIA.logro_promedio_por_eje, DIA.logro_promedio_por_habilidad.
    """
    # Filtrar filas donde la categoría secundaria es null/vacía: si el dato
    # no está cargado (ej "Eje Temático" None en DIA por bug de seed), no
    # tiene sentido graficarlo como serie en blanco.
    df_local = df_preguntas[
        df_preguntas[agrupar_secundario_por].notna()
        & (df_preguntas[agrupar_secundario_por].astype(str).str.strip() != "")
    ].copy()

    # Si después del filtro no queda nada útil, devolvemos un placeholder
    # "Sin datos" en lugar de generar un gráfico vacío con eje -0.04 a 0.04.
    if df_local.empty or df_local[columna_valor].isna().all():
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.axis("off")
        ax.text(
            0.5, 0.5,
            f"Sin datos disponibles para «{agrupar_secundario_por}»",
            ha="center", va="center",
            fontsize=11, color="#666", style="italic",
            transform=ax.transAxes,
        )
        plt.savefig(nombre_grafico, dpi=300, bbox_inches="tight")
        plt.close()
        return None

    # Agrupamos por las dos categorías
    resumen = df_local.groupby([agrupar_principal_por, agrupar_secundario_por]).agg(
        Promedio=(columna_valor, "mean")
    ).reset_index()

    grupo_primario = resumen[agrupar_principal_por].unique()
    grupo_secundario = resumen[agrupar_secundario_por].unique()
    x = np.arange(len(grupo_primario))
    width = 0.18

    # Se ordena el grupo secundario si se indicó una columna de orden
    if orden_grupo_secundario in df_local.columns and orden_grupo_secundario != "":
        orden = df_local[[agrupar_secundario_por, orden_grupo_secundario]].drop_duplicates()
        orden = orden.sort_values(by=orden_grupo_secundario)
        grupo_secundario = orden[agrupar_secundario_por].tolist()

    # Paleta Set2
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

        # Etiquetas con bbox blanco semi-transparente
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

    # Grilla
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


# ─────────────────────────────────────────────────────────────────────────
# Boxplot
# ─────────────────────────────────────────────────────────────────────────

def boxplot_valor_por_curso(
    df_estudiantes: pd.DataFrame,
    columna_valor: str,
    agrupar_por: str = "Curso",
    titulo_grafico: str = "Distribución de Rendimiento por Curso",
    ylabel: str = "",
    ylims: tuple | None = None,
    formato: str = "number",  # "number" o "percent"
    nombre_grafico: str = "aux_files/distribucion_rendimiento_por_curso.png",
):
    """Boxplot: distribución de `columna_valor` agrupado por `agrupar_por`.

    Display name: Boxplot por categoría
    Cajas sin relleno con borde negro, mediana negra gruesa, paleta tab10
    cicled con alpha 0.6.

    Args:
        df_estudiantes: DataFrame.
        columna_valor: columna numérica a distribuir (ej "Rend", "SIMCE").
        agrupar_por: columna categórica del eje X.
        titulo_grafico, ylabel: texto.
        ylims: tupla (min, max) o None.
        formato: "percent" agrega PercentFormatter al eje Y.
        nombre_grafico: path PNG.

    Equivalente LaTeX: SIMCE.boxplot_valor_por_curso,
        DIA.boxplot_logro_por_curso.
    """
    # Datos
    cursos = sorted(df_estudiantes[agrupar_por].unique(), key=lambda x: str(x))
    data = [
        df_estudiantes.loc[df_estudiantes[agrupar_por] == c, columna_valor].dropna().values
        for c in cursos
    ]

    # Colores por curso (tab10 cicled)
    cmap = plt.cm.tab10
    colors = {c: cmap(i % 10) for i, c in enumerate(cursos)}

    fig, ax = plt.subplots(figsize=(6, 4))

    # Boxplot sin relleno (luego coloreamos)
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
    for patch, curso in zip(bp["boxes"], cursos):
        patch.set_facecolor(colors[curso])
        patch.set_alpha(0.6)

    # Ejes y formato
    ax.set_title(titulo_grafico)
    ax.set_xlabel(agrupar_por)
    ax.set_ylabel(ylabel)
    ax.set_xticks(np.arange(len(cursos)))
    # Rotación adaptativa: 0° si pocos grupos cortos; 45° si muchos o largos
    # (umbral conservador: rotamos cuando hay ≥6 grupos o algún label > 6 chars).
    label_largo = any(len(str(c)) > 6 for c in cursos)
    rot = 45 if (len(cursos) >= 6 or label_largo) else 0
    ax.set_xticklabels(cursos, rotation=rot, ha="right" if rot else "center")
    if ylims:
        ax.set_ylim(ylims)
    if formato == "percent":
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))

    # Grilla
    plt.grid(axis="y", linestyle="--", alpha=0.6, linewidth=0.7, zorder=0)

    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300)
    plt.close()
    return None


# ─────────────────────────────────────────────────────────────────────────
# Stacked: alumnos por nivel cualitativo (semáforo)
# ─────────────────────────────────────────────────────────────────────────

def alumnos_por_nivel_cualitativo(
    df_estudiantes: pd.DataFrame,
    columna_nivel: str = "Logro",
    agrupar_por: str = "Curso",
    lista_niveles: list = ("Adecuado", "Elemental", "Insuficiente"),
    lista_paleta: list | None = None,
    titulo_grafico: str = "",
    titulo_leyenda: str = "",
    ylabel: str = "",
    nombre_grafico: str = "aux_files/alumnos_por_nivel.png",
):
    """Stacked bars: cantidad de alumnos por nivel cualitativo y categoría.

    Display name: Cantidad por nivel (stacked semáforo)
    Paleta semáforo fija: nivel[0]=verde (#1f9e89), nivel[1]=naranja
    (#f1a340), nivel[2]=rojo (#e64b35). El orden de `lista_niveles` define
    el mapping (de mejor a peor: Adecuado, Elemental, Insuficiente para
    SIMCE; Avanzado, Intermedio, Inicial para DIA).

    Args:
        df_estudiantes: DataFrame.
        columna_nivel: columna cualitativa con los nombres de los niveles.
        agrupar_por: columna del eje X (ej "Curso").
        lista_niveles: tupla/lista de 3 niveles ordenados de mejor a peor.
        titulo_grafico, titulo_leyenda, ylabel: texto.
        nombre_grafico: path PNG.

    Equivalente LaTeX: SIMCE.alumnos_por_nivel_cualitativo,
        DIA.alumnos_por_nivel.
    """
    # Agrupamos por agrupar_por y nivel → cantidad
    resumen = df_estudiantes.groupby([agrupar_por, columna_nivel]).size().reset_index(name="Cantidad")

    # Pivot para stacked bar
    pivot = resumen.pivot(index=agrupar_por, columns=columna_nivel, values="Cantidad").fillna(0)

    cursos = pivot.index.tolist()

    # Paleta semáforo: si no la pasan, default por cantidad de niveles
    # (mejor → peor). Soporta 3, 4 o 5 niveles.
    if lista_paleta is None:
        defaults = {
            3: ["#1f9e89", "#f1a340", "#e64b35"],
            4: ["#1f9e89", "#f1ce63", "#f1a340", "#e64b35"],
            5: ["#1f9e89", "#a6d854", "#f1ce63", "#f1a340", "#e64b35"],
        }
        lista_paleta = defaults.get(len(lista_niveles), defaults[3])
    colores = {nivel: lista_paleta[i % len(lista_paleta)] for i, nivel in enumerate(lista_niveles)}

    fig, ax = plt.subplots(figsize=(10, 6))

    bottom = None
    # Se grafica de abajo hacia arriba: peor primero (rojo en base)
    for nivel in lista_niveles[::-1]:
        vals = pivot[nivel] if nivel in pivot.columns else [0] * len(cursos)
        bars = ax.bar(cursos, vals, label=nivel, color=colores[nivel], bottom=bottom, zorder=2)
        bottom = vals if bottom is None else bottom + vals

        # Etiquetas centradas blancas y bold
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

    # Grilla suave + Y entera
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="y", linestyle="--", alpha=0.6, zorder=0)

    ax.set_title(titulo_grafico)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(agrupar_por)

    # Leyenda fuera del plot a la derecha
    ax.legend(title=titulo_leyenda, loc="upper left", bbox_to_anchor=(1, 1))

    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300)
    plt.close()
    return None


# ─────────────────────────────────────────────────────────────────────────
# Stacked: evolución de niveles por curso × mes (con separadores entre cursos)
# ─────────────────────────────────────────────────────────────────────────

def alumnos_por_nivel_curso_y_mes(
    df_estudiantes: pd.DataFrame,
    columna_nivel: str = "Logro",
    columna_curso: str = "Curso",
    columna_mes: str = "Mes",
    lista_niveles: tuple = ("Insuficiente", "Elemental", "Adecuado"),
    lista_paleta: list | None = None,
    orden_cursos: list | None = None,
    orden_meses: list = ("ABRIL", "JUNIO", "AGOSTO", "OCTUBRE", "NOVIEMBRE"),
    titulo_grafico: str = "Comparación de Alumnos por Nivel de Logro, Curso y Mes",
    titulo_leyenda: str = "Nivel de Logro",
    ylabel: str = "Cantidad",
    nombre_grafico: str = "aux_files/alumnos_por_nivel_curso_mes.png",
    rot_x: int = 90,
    mostrar_totales: bool = True,
):
    """Stacked compuesto: evolución de niveles por curso × mes.

    Display name: Evolución de niveles por curso y período
    Eje X muestra cada combinación curso×mes; los cursos se separan con
    líneas discontinuas verticales y un rótulo bold debajo. Apto para SIMCE
    histórico (5 hitos del año).

    Args:
        df_estudiantes: DataFrame con columnas curso, mes, nivel.
        columna_nivel, columna_curso, columna_mes: nombres de columna.
        lista_niveles: 3 niveles ordenados de PEOR a MEJOR para que el peor
            quede en la base del stack.
        lista_paleta: lista de 3 colores hex (default azul SIMCE).
        orden_cursos: lista para fijar el orden del eje X.
        orden_meses: lista para fijar el orden de los meses.
        titulo_grafico, titulo_leyenda, ylabel: texto.
        rot_x: rotación de las etiquetas de mes.
        mostrar_totales: si True, suma encima de cada barra.

    Equivalente LaTeX: SIMCE.alumnos_por_nivel_curso_y_mes.
    """
    # 1) Agregación
    resumen = (
        df_estudiantes
        .groupby([columna_curso, columna_mes, columna_nivel])
        .size()
        .reset_index(name="Cantidad")
    )

    if orden_cursos is None:
        orden_cursos = df_estudiantes[columna_curso].dropna().unique().tolist()
    if orden_meses is None:
        orden_meses = df_estudiantes[columna_mes].dropna().unique().tolist()

    # Categorías ordenadas
    resumen[columna_curso] = pd.Categorical(resumen[columna_curso], categories=orden_cursos, ordered=True)
    resumen[columna_mes] = pd.Categorical(resumen[columna_mes], categories=orden_meses, ordered=True)
    resumen[columna_nivel] = pd.Categorical(resumen[columna_nivel], categories=list(lista_niveles), ordered=True)

    # Pivot (Curso, Mes) × Nivel
    pivot = (
        resumen
        .pivot_table(index=[columna_curso, columna_mes], columns=columna_nivel, values="Cantidad", aggfunc="sum", fill_value=0)
        .reindex(pd.MultiIndex.from_product([orden_cursos, orden_meses], names=[columna_curso, columna_mes]), fill_value=0)
    )

    # 2) Eje X
    x_labels = [m for (_, m) in pivot.index]
    x_positions = np.arange(len(pivot))

    # 3) Colores por nivel (fija — diseño SIMCE original)
    paleta = {
        "Insuficiente": "#C2A47A",
        "Elemental": "#2196F3",
        "Adecuado": "#5FA59E",
    }
    colores = {n: paleta.get(n, "#888888") for n in lista_niveles}

    # 4) Plot
    fig, ax = plt.subplots(figsize=(12, 7))
    bottom = np.zeros(len(pivot), dtype=float)

    for nivel in lista_niveles:
        vals = pivot[nivel].values if nivel in pivot.columns else np.zeros(len(pivot))
        bars = ax.bar(x_positions, vals, label=nivel, color=colores[nivel], bottom=bottom, zorder=2)

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

    # Totales encima
    if mostrar_totales:
        for x, total in zip(x_positions, bottom):
            if total > 0:
                ax.text(x, total + 0.6, f"{int(total)}", ha="center", va="bottom", fontsize=9, color="#444444", fontweight="bold")

    # 5) Separadores y rótulos de curso bajo cada bloque
    n_meses = len(orden_meses)
    course_centers = []
    for i, curso in enumerate(orden_cursos):
        start = i * n_meses
        end = start + n_meses
        if i > 0:
            ax.axvline(start - 0.5, ls=(0, (3, 3)), color="#666666", lw=1, alpha=0.7, zorder=1)
        course_centers.append((start + end - 1) / 2.0)

    ax.axvline(len(x_positions) - 0.5, ls=(0, (3, 3)), color="#666666", lw=1, alpha=0.7, zorder=1)

    # Rótulos de cursos con transform mezclado
    xt = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)
    curso_offset = -0.20
    for center, curso in zip(course_centers, orden_cursos):
        ax.text(center, curso_offset, curso, transform=xt, ha="center", va="top", fontsize=11, fontweight="bold", clip_on=False)

    # 6) Ejes, grilla, leyenda
    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels, rotation=rot_x, ha="right")
    ax.set_title(titulo_grafico, pad=14, fontsize=14, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", linestyle="--", alpha=0.5, zorder=0)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    leg = ax.legend(title=titulo_leyenda, loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=len(lista_niveles), frameon=False)
    if leg and leg.get_title():
        leg.get_title().set_fontweight("bold")

    plt.subplots_adjust(bottom=0.20)
    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300, bbox_inches="tight")
    plt.close()
    return pivot.reset_index()


# ─────────────────────────────────────────────────────────────────────────
# Comparativo entre 2 evaluaciones
# ─────────────────────────────────────────────────────────────────────────

def comparacion_logro_por_curso(
    df_comparacion: pd.DataFrame,
    columna_id: str = "Curso",
    columnas_evaluaciones: list = ("Diagnóstico", "Intermedio"),
    titulo_grafico: str = "Logro Promedio por Curso — Comparativo",
    titulo_leyenda: str = "Evaluación",
    nombre_grafico: str = "aux_files/comparacion_logro_por_curso.png",
):
    """Barras agrupadas: comparativo entre N evaluaciones por categoría.

    Display name: Comparativo entre evaluaciones
    Espera un DataFrame con una columna por evaluación (ej Diagnóstico,
    Intermedio) y `columna_id` como categoría (ej Curso). Genera N barras
    por curso.

    Args:
        df_comparacion: DataFrame en formato wide (1 columna por evaluación).
        columna_id: columna categórica del eje X.
        columnas_evaluaciones: lista de columnas a comparar.
        titulo_grafico, titulo_leyenda: texto.
        nombre_grafico: path PNG.

    Equivalente LaTeX: SIMCE.comparacion_logro_por_curso,
        DIA.comparacion_logro_por_curso.
    """
    resumen = df_comparacion.melt(
        id_vars=[columna_id],
        value_vars=list(columnas_evaluaciones),
        var_name="Evaluación",
        value_name="Logro",
    )
    cursos = resumen[columna_id].unique()
    evaluaciones = resumen["Evaluación"].unique()
    x = np.arange(len(cursos))
    width = 0.8 / max(1, len(evaluaciones))

    colores = plt.cm.Set2.colors
    colores = {evaluacion: colores[i] for i, evaluacion in enumerate(evaluaciones)}

    fig, ax = plt.subplots(figsize=(12, 6))
    for i, evaluacion in enumerate(evaluaciones):
        valores = resumen[resumen["Evaluación"] == evaluacion]["Logro"].values
        bars = ax.bar(
            x + i * width - (width * len(evaluaciones) / 2),
            valores,
            width,
            label=evaluacion,
            color=colores[evaluacion],
            zorder=2,
            edgecolor="gray",
            linewidth=0.8,
        )
        for bar, val in zip(bars, valores):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{val:.0%}",
                ha="center",
                va="bottom",
                fontsize=8,
                zorder=3,
                bbox=dict(facecolor="white", edgecolor="none", pad=1, alpha=0.7),
            )

    plt.grid(axis="y", linestyle="--", linewidth=0.9, zorder=0)

    ax.set_xticks(x)
    ax.set_xticklabels(cursos, ha="right")
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_ylabel("Logro")
    ax.set_title(titulo_grafico)

    ax.legend(title=titulo_leyenda, framealpha=0.6)
    plt.tight_layout()
    plt.savefig(nombre_grafico, dpi=300)
    plt.close()
    return None


# ─────────────────────────────────────────────────────────────────────────
# Registry para introspección desde el frontend
# ─────────────────────────────────────────────────────────────────────────

CHART_REGISTRY = {
    "grafico_barras_promedio_por": {
        "fn": grafico_barras_promedio_por,
        "display_name": "Promedio por categoría (barras simples)",
        "description": "Barras simples del promedio de una columna numérica agrupado por una categoría. Eje Y en porcentaje.",
        "required_params": ["columna_valor", "agrupar_por"],
        "optional_params": ["titulo", "ylabel"],
        "input_dataframes": ["df_estudiantes"],
    },
    "valor_promedio_agrupado_por": {
        "fn": valor_promedio_agrupado_por,
        "display_name": "Promedio agrupado por dos categorías",
        "description": "Barras agrupadas: eje X = categoría principal, N series = categoría secundaria (ej Curso × Habilidad).",
        "required_params": ["columna_valor", "agrupar_principal_por", "agrupar_secundario_por"],
        "optional_params": ["titulo_grafico", "titulo_leyenda", "y_lims", "formato", "orden_grupo_secundario"],
        "input_dataframes": ["df_preguntas", "df_estudiantes"],
    },
    "boxplot_valor_por_curso": {
        "fn": boxplot_valor_por_curso,
        "display_name": "Boxplot por categoría",
        "description": "Distribución (caja-bigote) de una columna numérica agrupada por categoría. Sin relleno, paleta tab10.",
        "required_params": ["columna_valor", "agrupar_por"],
        "optional_params": ["titulo_grafico", "ylabel", "ylims", "formato"],
        "input_dataframes": ["df_estudiantes"],
    },
    "alumnos_por_nivel_cualitativo": {
        "fn": alumnos_por_nivel_cualitativo,
        "display_name": "Cantidad por nivel (stacked semáforo)",
        "description": "Barras apiladas con paleta semáforo fija (verde/naranja/rojo). El orden de `lista_niveles` mapea los colores.",
        "required_params": ["columna_nivel", "agrupar_por", "lista_niveles"],
        "optional_params": ["titulo_grafico", "titulo_leyenda", "ylabel"],
        "input_dataframes": ["df_estudiantes"],
    },
    "alumnos_por_nivel_curso_y_mes": {
        "fn": alumnos_por_nivel_curso_y_mes,
        "display_name": "Evolución de niveles por curso y período",
        "description": "Stacked compuesto: cada barra es un (curso × mes), con separadores verticales y rótulo de curso debajo.",
        "required_params": ["columna_nivel", "columna_curso", "columna_mes", "lista_niveles"],
        "optional_params": ["orden_cursos", "orden_meses", "titulo_grafico", "ylabel", "mostrar_totales"],
        "input_dataframes": ["df_estudiantes"],
    },
    "comparacion_logro_por_curso": {
        "fn": comparacion_logro_por_curso,
        "display_name": "Comparativo entre evaluaciones",
        "description": "Barras agrupadas comparando 2+ evaluaciones (ej Diagnóstico vs Intermedio) por categoría.",
        "required_params": ["columna_id", "columnas_evaluaciones"],
        "optional_params": ["titulo_grafico", "titulo_leyenda"],
        "input_dataframes": ["df_comparacion"],
    },
}
