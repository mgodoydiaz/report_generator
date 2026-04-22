"""
Informe PDL IDEL-Woodcock — sólo datos, respetando escalas por subprueba.

Principios de diseño:
  - Tamaño Carta (8.5" x 11"), header y footer consistentes en toda página.
  - Ancho de contenido fijo; todos los gráficos y tablas se alinean a la misma grilla.
  - Cada subprueba tiene escala propia; NO se mezclan puntajes entre subpruebas.
  - No se inventa un "nivel global" del estudiante. Se analiza por subprueba.

Estructura por curso:
  A. Distribución de niveles por evaluación + tabla de promedios/medianas por subprueba.
  B. Small multiples de boxplots (un panel por subprueba, escala propia).
  C. Matrices de transición v1→vN — una por subprueba (small multiples 2x3).
  D. Listado de estudiantes en riesgo persistente, por subprueba.
  E. Roster: nivel por subprueba × evaluación.

Más el panorama global al inicio y la síntesis comparativa al final.

Uso:
    python scripts/report_pdl_idel.py --establecimiento Panguipulli --anio 2025 --versiones 1,2,3
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

# ── Configuración del dominio ────────────────────────────────────────────────
# NOTA: las side effects (DATABASE_URL, dotenv, creación de OUTPUT_DIR) se
# difieren a funciones específicas para que este módulo sea importable desde
# el backend (ver backend/rgenerator/tooling/report_pdl_idel_tools.py) sin
# crashear ante ausencia de DATABASE_URL ni tocar el filesystem en import.

DEFAULT_METRIC_ID = 8

OUTPUT_DIR = Path("data/output")


def _get_database_url() -> str:
    """Lee DATABASE_URL, cargando .env sólo al invocarse (no en import)."""
    from dotenv import load_dotenv
    load_dotenv()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL no configurada. Este script CLI requiere la variable "
            "de entorno para cargar datos de la base."
        )
    return url

ACHIEVEMENT_LEVELS = ["Crítico", "Alto Riesgo", "Cierto Riesgo", "Bajo Riesgo"]
LEVEL_SHORT = {
    "Crítico": "Crít.",
    "Alto Riesgo": "Alto",
    "Cierto Riesgo": "Cierto",
    "Bajo Riesgo": "Bajo",
}
LEVEL_CODE = {
    "Crítico": "C",
    "Alto Riesgo": "A",
    "Cierto Riesgo": "R",
    "Bajo Riesgo": "B",
}
LEVEL_COLORS = {
    "Crítico":       "#dc2626",
    "Alto Riesgo":   "#f59e0b",
    "Cierto Riesgo": "#84cc16",
    "Bajo Riesgo":   "#16a34a",
}
LEVEL_VALUE = {"Crítico": 1, "Alto Riesgo": 2, "Cierto Riesgo": 3, "Bajo Riesgo": 4}
RISK_LEVELS = {"Crítico", "Alto Riesgo"}

# Colores direccionales para transiciones (verde mejoró / gris mantuvo / rojo empeoró)
DIR_COLORS = {
    "up":   {"bg": "#dcfce7", "fg": "#166534"},   # verde claro
    "same": {"bg": "#f1f5f9", "fg": "#475569"},   # gris claro
    "down": {"bg": "#fee2e2", "fg": "#991b1b"},   # rojo claro
}

CURSOS_ORDER = ["1° BÁSICO", "2° BÁSICO", "3° BÁSICO", "4° BÁSICO", "5° BÁSICO", "6° BÁSICO"]
SUBPRUEBAS_ORDER = ["CT", "FLO", "FNL", "FSF", "ILP", "VSD"]
SUBPRUEBAS_LABEL = {
    "CT":  "Conciencia de texto",
    "FLO": "Fluidez lectora",
    "FNL": "Segmentación fonémica",
    "FSF": "Fluidez síl./fon.",
    "ILP": "Identificación letras/palabras",
    "VSD": "Vocabulario sobre dibujo",
}

# ── Layout (hoja Carta) ──────────────────────────────────────────────────────

PAGE_W_IN = 8.5
PAGE_H_IN = 11.0

CONTENT_L = 0.10
CONTENT_R = 0.90
CONTENT_W = CONTENT_R - CONTENT_L

HEADER_TEXT_Y   = 0.960
HEADER_RULE_Y   = 0.935
SECTION_TITLE_Y = 0.905
CONTENT_TOP_Y   = 0.865
CONTENT_BOTTOM_Y = 0.075
FOOTER_RULE_Y    = 0.055
FOOTER_TEXT_Y    = 0.035

TITLE_INFORME = "Informe PDL IDEL-Woodcock"
INSTITUCION = "Fundación PHP"

COLOR_TITLE   = "#0f172a"
COLOR_TEXT    = "#334155"
COLOR_MUTED   = "#64748b"
COLOR_SOFT    = "#94a3b8"
COLOR_RULE    = "#cbd5e1"
COLOR_HEADCELL_BG = "#eef2ff"
COLOR_HEADCELL_FG = "#3730a3"
COLOR_HEADCELL_EDGE = "#c7d2fe"
COLOR_ROW_ALT = "#f8fafc"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titleweight": "bold",
    "axes.titlesize": 10.5,
    "axes.labelsize": 9,
    "figure.titlesize": 13,
    "figure.titleweight": "bold",
})


# ── Carga de datos ───────────────────────────────────────────────────────────

def load_data(metric_id: int = DEFAULT_METRIC_ID,
              establecimiento: str | None = None,
              anio: int | None = None,
              versiones: list[int] | None = None,
              cursos: list[str] | None = None) -> pd.DataFrame:
    import psycopg2
    sql = """
        SELECT id_data, value::text AS value, dimensions_json::text AS dims
        FROM metric_data
        WHERE id_metric = %s
    """
    conn = psycopg2.connect(_get_database_url())
    try:
        df = pd.read_sql(sql, conn, params=(metric_id,))
    finally:
        conn.close()

    df["value"] = df["value"].map(json.loads)
    df["dims"] = df["dims"].map(json.loads)

    df["puntaje"] = df["value"].map(lambda v: v.get("Puntaje"))
    df["nivel"] = df["value"].map(lambda v: v.get("Nivel de Riesgo"))
    df["establecimiento"] = df["dims"].map(lambda d: d.get("3"))
    df["año"] = df["dims"].map(lambda d: int(d["4"]) if d.get("4") else None)
    df["curso"] = df["dims"].map(lambda d: d.get("5"))
    df["rut"] = df["dims"].map(lambda d: d.get("6"))
    df["nombre"] = df["dims"].map(lambda d: d.get("7"))
    df["subprueba"] = df["dims"].map(lambda d: (d.get("19") or "").upper())
    df["version"] = df["dims"].map(lambda d: int(d["20"]) if d.get("20") else None)
    df["eval_id"] = df["año"].astype(str) + "/v" + df["version"].astype(str)
    df["puntaje"] = pd.to_numeric(df["puntaje"], errors="coerce")

    # Identificador del estudiante: usamos nombre (rut viene nulo en varios registros).
    df["estudiante"] = df["nombre"]

    df = df.dropna(subset=["puntaje", "curso", "nivel", "estudiante"])
    df = df[df["subprueba"].isin(SUBPRUEBAS_ORDER)]

    if establecimiento:
        df = df[df["establecimiento"] == establecimiento]
    if anio is not None:
        df = df[df["año"] == anio]
    if versiones:
        df = df[df["version"].isin(versiones)]
    if cursos:
        df = df[df["curso"].isin(cursos)]

    return df


# ── Helpers de cálculo ───────────────────────────────────────────────────────

def eval_ids_sorted(df: pd.DataFrame) -> list[str]:
    return sorted(df["eval_id"].dropna().unique())


def subprueba_nivel_por_est(sub_df: pd.DataFrame, eval_id: str) -> pd.Series:
    """Para una subprueba específica y una evaluación, devuelve nivel por estudiante
    (un único nivel, dado que cada estudiante tiene a lo más un registro por
    subprueba × evaluación).
    """
    return (sub_df[sub_df["eval_id"] == eval_id]
            .groupby("estudiante")["nivel"].first())


def compute_subprueba_transitions(sub_df: pd.DataFrame, first: str, latest: str
                                  ) -> tuple[pd.DataFrame, int, int, int]:
    """Matriz 4x4 de transiciones para UNA subprueba entre first y latest, y
    conteos (mejoraron, empeoraron, mantuvieron)."""
    by_first = subprueba_nivel_por_est(sub_df, first)
    by_latest = subprueba_nivel_por_est(sub_df, latest)
    both = pd.concat([by_first.rename("f"), by_latest.rename("l")], axis=1).dropna()

    matrix = pd.DataFrame(0, index=ACHIEVEMENT_LEVELS, columns=ACHIEVEMENT_LEVELS, dtype=int)
    for _, r in both.iterrows():
        f, l = r["f"], r["l"]
        if f in matrix.index and l in matrix.columns:
            matrix.loc[f, l] += 1

    # Mejorar: l > f en LEVEL_VALUE (niveles de menor a mayor severidad invertido)
    imp = wor = same = 0
    for _, r in both.iterrows():
        vf = LEVEL_VALUE.get(r["f"], 0)
        vl = LEVEL_VALUE.get(r["l"], 0)
        if vl > vf:
            imp += 1
        elif vl < vf:
            wor += 1
        else:
            same += 1
    return matrix, imp, wor, same


def course_aggregate_transitions(df: pd.DataFrame, first: str, latest: str
                                 ) -> tuple[int, int, int]:
    """Agrega transiciones sumando a través de todas las subpruebas del curso.
    Útil para un panorama general del curso."""
    total_imp = total_wor = total_same = 0
    for sub in SUBPRUEBAS_ORDER:
        sdf = df[df["subprueba"] == sub]
        if sdf.empty:
            continue
        _, imp, wor, same = compute_subprueba_transitions(sdf, first, latest)
        total_imp += imp; total_wor += wor; total_same += same
    return total_imp, total_wor, total_same


# ── Header / Footer / Título de sección ─────────────────────────────────────

class PageCounter:
    def __init__(self):
        self.n = 0

    def next(self) -> int:
        self.n += 1
        return self.n


def new_page(ctx_right: str, page_counter: PageCounter) -> tuple[plt.Figure, int]:
    fig = plt.figure(figsize=(PAGE_W_IN, PAGE_H_IN))
    n = page_counter.next()

    fig.text(CONTENT_L, HEADER_TEXT_Y, TITLE_INFORME,
             ha="left", va="center", fontsize=9.5, fontweight="bold", color=COLOR_TITLE)
    fig.text(CONTENT_R, HEADER_TEXT_Y, ctx_right,
             ha="right", va="center", fontsize=9, color=COLOR_MUTED)

    fig.add_artist(Line2D([CONTENT_L, CONTENT_R],
                          [HEADER_RULE_Y, HEADER_RULE_Y],
                          transform=fig.transFigure, figure=fig,
                          color=COLOR_RULE, linewidth=0.7))
    fig.add_artist(Line2D([CONTENT_L, CONTENT_R],
                          [FOOTER_RULE_Y, FOOTER_RULE_Y],
                          transform=fig.transFigure, figure=fig,
                          color=COLOR_RULE, linewidth=0.7))
    fig.text(CONTENT_L, FOOTER_TEXT_Y, INSTITUCION,
             ha="left", va="center", fontsize=8, color=COLOR_SOFT)
    fig.text(CONTENT_R, FOOTER_TEXT_Y, f"Página {n}",
             ha="right", va="center", fontsize=8, color=COLOR_SOFT)
    return fig, n


def section_heading(fig: plt.Figure, title: str) -> None:
    fig.text(0.5, SECTION_TITLE_Y, title,
             ha="center", va="center", fontsize=14, fontweight="bold", color=COLOR_TITLE)


def block_title(fig: plt.Figure, x: float, y: float, title: str) -> None:
    fig.text(x, y, title, ha="left", va="bottom",
             fontsize=10.5, fontweight="bold", color=COLOR_TEXT)


# ── Tablas ───────────────────────────────────────────────────────────────────

def render_table(ax,
                 df_cells: pd.DataFrame,
                 col_widths: list[float] | None = None,
                 fontsize: float = 8,
                 level_tint_cols: Iterable[str] = (),
                 movement_cols: Iterable[str] = (),
                 row_height: float = 1.45) -> None:
    ax.axis("off")
    cell_text = df_cells.values.tolist()
    col_labels = list(df_cells.columns)
    if col_widths is None:
        col_widths = [1 / len(col_labels)] * len(col_labels)

    tbl = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        cellLoc="center",
        colLoc="center",
        loc="upper center",
        colWidths=col_widths,
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(fontsize)
    tbl.scale(1, row_height)

    n_rows = len(cell_text)
    n_cols = len(col_labels)

    for j in range(n_cols):
        c = tbl[0, j]
        c.set_facecolor(COLOR_HEADCELL_BG)
        c.set_text_props(color=COLOR_HEADCELL_FG, fontweight="bold", fontsize=fontsize)
        c.set_edgecolor(COLOR_HEADCELL_EDGE)

    inv_short = {v: k for k, v in LEVEL_SHORT.items()}
    inv_code = {v: k for k, v in LEVEL_CODE.items()}

    for i in range(n_rows):
        for j in range(n_cols):
            c = tbl[i + 1, j]
            c.set_edgecolor("#e2e8f0")
            c.set_facecolor(COLOR_ROW_ALT if i % 2 == 1 else "white")
            c.set_text_props(fontsize=fontsize)

            col_name = col_labels[j]
            if col_name in level_tint_cols:
                text = cell_text[i][j]
                lvl = inv_short.get(text) or inv_code.get(text) or (text if text in LEVEL_COLORS else None)
                if lvl and lvl in LEVEL_COLORS:
                    c.set_facecolor(LEVEL_COLORS[lvl] + "33")
            if col_name in movement_cols:
                t = cell_text[i][j]
                if "↑" in t:
                    c.set_text_props(color="#16a34a", fontweight="bold", fontsize=fontsize)
                elif "↓" in t:
                    c.set_text_props(color="#dc2626", fontweight="bold", fontsize=fontsize)


# ── Página: Panorama global ──────────────────────────────────────────────────

def render_panorama(pdf, df: pd.DataFrame, page_counter: PageCounter) -> None:
    evals = eval_ids_sorted(df)
    latest = evals[-1]
    est_str = ", ".join(sorted(df["establecimiento"].dropna().unique())) or "—"
    ctx_right = f"{est_str} · {evals[0]} → {latest}"
    fig, _ = new_page(ctx_right, page_counter)
    section_heading(fig, "Panorama global")

    # — Mapa de riesgo curso × subprueba
    block_title(fig, CONTENT_L, 0.845,
                f"Mapa de riesgo — % estudiantes en Crítico o Alto Riesgo ({latest})")
    ax1 = fig.add_axes([CONTENT_L, 0.55, CONTENT_W, 0.27])

    latest_df = df[df["eval_id"] == latest]
    risk = (latest_df.assign(is_risk=latest_df["nivel"].isin(RISK_LEVELS))
                    .groupby(["curso", "subprueba"])["is_risk"].mean()
                    .unstack()
                    .reindex(index=CURSOS_ORDER, columns=SUBPRUEBAS_ORDER)) * 100

    im = ax1.imshow(risk.values, aspect="auto", cmap="YlOrRd", vmin=0, vmax=100)
    ax1.set_xticks(range(len(SUBPRUEBAS_ORDER))); ax1.set_xticklabels(SUBPRUEBAS_ORDER)
    ax1.set_yticks(range(len(CURSOS_ORDER)));    ax1.set_yticklabels(CURSOS_ORDER)
    ax1.tick_params(length=0)
    for i in range(risk.shape[0]):
        for j in range(risk.shape[1]):
            v = risk.iloc[i, j]
            if not np.isnan(v):
                ax1.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8.5,
                         color="white" if v > 55 else "#1f2937", fontweight="bold")
    cbar = fig.colorbar(im, ax=ax1, fraction=0.022, pad=0.015)
    cbar.ax.tick_params(labelsize=7)

    # — Tabla de cobertura
    block_title(fig, CONTENT_L, 0.49, "Cobertura de estudiantes por curso")
    ax2 = fig.add_axes([CONTENT_L, 0.18, CONTENT_W, 0.26])
    rows = []
    for curso in CURSOS_ORDER:
        cdf = df[df["curso"] == curso]
        if cdf.empty:
            continue
        evals_per_student = cdf.groupby("estudiante")["eval_id"].nunique()
        n_unique = len(evals_per_student)
        n1 = int((evals_per_student == 1).sum())
        n2 = int((evals_per_student == 2).sum())
        n3 = int((evals_per_student == 3).sum())
        rows.append([curso, n_unique, n1, n2, n3])
    cov_df = pd.DataFrame(rows, columns=["Curso", "Únicos",
                                         "En 1 eval.", "En 2 evals.", "En 3 evals."])
    render_table(ax2, cov_df, col_widths=[0.32, 0.14, 0.18, 0.18, 0.18], fontsize=9)

    pdf.savefig(fig); plt.close(fig)


# ── Curso — Página A: distribución de niveles + tabla prom/med ──────────────

def render_course_page_a(pdf, course_df: pd.DataFrame, curso: str,
                         page_counter: PageCounter) -> None:
    evals = eval_ids_sorted(course_df)
    est_str = ", ".join(sorted(course_df["establecimiento"].dropna().unique())) or ""
    fig, _ = new_page(f"{curso} · {est_str}", page_counter)
    section_heading(fig, curso)

    # — Distribución de niveles por evaluación
    block_title(fig, CONTENT_L, 0.845, "Distribución de niveles por evaluación")

    # Banner de leyenda
    legend_handles = [Patch(color=LEVEL_COLORS[lvl], label=lvl) for lvl in ACHIEVEMENT_LEVELS]
    fig.legend(handles=legend_handles, loc="center", bbox_to_anchor=(0.5, 0.815),
               ncol=4, fontsize=8.5, frameon=False, handlelength=1.2, columnspacing=2.0)

    ax_dist = fig.add_axes([CONTENT_L, 0.55, CONTENT_W, 0.24])
    counts = (course_df.groupby(["eval_id", "nivel"]).size().unstack(fill_value=0)
              .reindex(columns=ACHIEVEMENT_LEVELS, fill_value=0)
              .reindex(index=evals, fill_value=0))
    pct = counts.div(counts.sum(axis=1), axis=0).fillna(0) * 100
    bottom = np.zeros(len(pct))
    for level in ACHIEVEMENT_LEVELS:
        ax_dist.bar(pct.index, pct[level], bottom=bottom,
                    color=LEVEL_COLORS[level], edgecolor="white", linewidth=0.5)
        for i, (v, b) in enumerate(zip(pct[level], bottom)):
            if v >= 4:
                ax_dist.text(i, b + v / 2, f"{v:.0f}%", ha="center", va="center",
                             fontsize=8,
                             color="white" if level in ("Crítico", "Bajo Riesgo") else "#1f2937",
                             fontweight="bold")
        bottom += pct[level].values
    ax_dist.set_ylabel("% registros")
    ax_dist.set_ylim(0, 100)

    # — Tabla promedios/medianas por subprueba × evaluación
    block_title(fig, CONTENT_L, 0.48, "Promedios y medianas por subprueba")
    ax_tbl = fig.add_axes([CONTENT_L, 0.10, CONTENT_W, 0.36])

    tbl_rows = []
    for sub in SUBPRUEBAS_ORDER:
        sdf = course_df[course_df["subprueba"] == sub]
        if sdf.empty:
            continue
        row = [sub, SUBPRUEBAS_LABEL.get(sub, sub)]
        for e in evals:
            e_vals = sdf[sdf["eval_id"] == e]["puntaje"]
            if e_vals.empty:
                row.extend(["—", "—"])
            else:
                row.append(f"{e_vals.mean():.1f}")
                row.append(f"{e_vals.median():.1f}")
        tbl_rows.append(row)
    cols = ["Sub.", "Descripción"]
    for e in evals:
        cols.append(f"{e}\nProm.")
        cols.append(f"{e}\nMed.")
    if tbl_rows:
        n_eval_cols = 2 * len(evals)
        col_widths = [0.09, 0.35] + [0.56 / n_eval_cols] * n_eval_cols
        tbl_df = pd.DataFrame(tbl_rows, columns=cols)
        render_table(ax_tbl, tbl_df, col_widths=col_widths, fontsize=9, row_height=1.7)

    pdf.savefig(fig); plt.close(fig)


# ── Curso — Página B: small multiples boxplot ───────────────────────────────

def render_course_page_b(pdf, course_df: pd.DataFrame, curso: str,
                         page_counter: PageCounter) -> None:
    evals = eval_ids_sorted(course_df)
    est_str = ", ".join(sorted(course_df["establecimiento"].dropna().unique())) or ""
    fig, _ = new_page(f"{curso} · {est_str}", page_counter)
    section_heading(fig, curso)

    block_title(fig, CONTENT_L, 0.845,
                "Distribución de puntajes por subprueba y evaluación")

    rows_grid = 3
    cols_grid = 2
    grid_top = 0.80
    grid_bottom = 0.10
    grid_h = grid_top - grid_bottom
    row_gap = 0.050
    col_gap = 0.09

    panel_h = (grid_h - (rows_grid - 1) * row_gap) / rows_grid
    panel_w = (CONTENT_W - (cols_grid - 1) * col_gap) / cols_grid

    for idx, sub in enumerate(SUBPRUEBAS_ORDER):
        r = idx // cols_grid
        c = idx % cols_grid
        x = CONTENT_L + c * (panel_w + col_gap)
        y = grid_top - panel_h - r * (panel_h + row_gap)
        ax = fig.add_axes([x, y, panel_w, panel_h])

        sdf = course_df[course_df["subprueba"] == sub]
        if sdf.empty:
            ax.axis("off")
            ax.text(0.5, 0.5, f"{sub} — sin datos", ha="center", va="center",
                    fontsize=9, color=COLOR_MUTED)
            continue

        data = []
        labels = []
        for e in evals:
            vals = sdf[sdf["eval_id"] == e]["puntaje"].values
            if len(vals) > 0:
                data.append(vals)
                labels.append(e)

        bp = ax.boxplot(data, tick_labels=labels, patch_artist=True, widths=0.6,
                        showfliers=True,
                        flierprops=dict(marker="o", markersize=3, markerfacecolor=COLOR_SOFT,
                                        markeredgecolor="none"))
        for patch in bp["boxes"]:
            patch.set_facecolor("#6366f1"); patch.set_alpha(0.55); patch.set_edgecolor("#4338ca")
        for med in bp["medians"]:
            med.set_color("#0f172a"); med.set_linewidth(1.2)
        for whisker in bp["whiskers"]:
            whisker.set_color("#475569"); whisker.set_linewidth(0.9)
        for cap in bp["caps"]:
            cap.set_color("#475569"); cap.set_linewidth(0.9)

        means = [np.mean(d) for d in data]
        ax.plot(range(1, len(means) + 1), means, marker="D", linestyle="-",
                color="#dc2626", markersize=4, linewidth=1.0)

        ax.text(0.02, 1.04, f"{sub} — {SUBPRUEBAS_LABEL.get(sub, sub)}",
                transform=ax.transAxes, ha="left", va="bottom",
                fontsize=9.5, fontweight="bold", color=COLOR_TEXT)
        ax.set_ylabel("Puntaje", fontsize=8)
        ax.tick_params(axis="both", labelsize=8)
        ax.grid(True, axis="y", alpha=0.3)

    pdf.savefig(fig); plt.close(fig)


# ── Curso — Página C: matrices de transición por subprueba ──────────────────

def _render_transition_matrix_subprueba(ax, matrix: pd.DataFrame, total: int,
                                        sub_code: str, sub_label: str,
                                        first: str, latest: str,
                                        show_xlabel: bool = True,
                                        show_ylabel: bool = True) -> None:
    """Matriz 4x4 con colores direccionales (verde mejoró / gris mantuvo / rojo empeoró)."""
    ax.set_xlim(-0.5, 3.5); ax.set_ylim(3.5, -0.5)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks(range(4))
    ax.set_xticklabels([LEVEL_SHORT[l] for l in ACHIEVEMENT_LEVELS], fontsize=7)
    ax.set_yticks(range(4))
    ax.set_yticklabels([LEVEL_SHORT[l] for l in ACHIEVEMENT_LEVELS], fontsize=7)
    ax.tick_params(length=0)

    # Filas = nivel en first, columnas = nivel en latest.
    # Columnas están ordenadas [Crít, Alto, Cierto, Bajo] de izquierda a derecha
    # (de peor a mejor). Entonces j > i ⇒ destino a la derecha ⇒ MEJORÓ.
    for i in range(4):
        for j in range(4):
            v = int(matrix.iloc[i, j]) if not matrix.empty else 0
            if j > i:
                scheme = DIR_COLORS["up"]
            elif j < i:
                scheme = DIR_COLORS["down"]
            else:
                scheme = DIR_COLORS["same"]
            ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1,
                                   facecolor=scheme["bg"], edgecolor="white", linewidth=1.2))
            if v > 0:
                ax.text(j, i, str(v), ha="center", va="center",
                        fontsize=9, fontweight="bold", color=scheme["fg"])

    ax.add_patch(Rectangle((-0.5, -0.5), 4, 4, fill=False,
                           edgecolor=COLOR_SOFT, linewidth=0.8))

    # Título en una sola línea (evita colisión con N= a la derecha)
    ax.text(0.0, 1.10, f"{sub_code} — {sub_label}  ·  N={total}",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=8.5, fontweight="bold", color=COLOR_TEXT)

    if show_xlabel:
        ax.set_xlabel(f"Nivel en {latest}", fontsize=7.5, labelpad=2)
    else:
        ax.set_xlabel("")
    if show_ylabel:
        ax.set_ylabel(f"Nivel en {first}", fontsize=7.5, labelpad=2)
    else:
        ax.set_ylabel("")
    for spine in ax.spines.values():
        spine.set_visible(False)


def render_course_page_transitions(pdf, course_df: pd.DataFrame, curso: str,
                                   page_counter: PageCounter) -> None:
    evals = eval_ids_sorted(course_df)
    first, latest = evals[0], evals[-1]
    est_str = ", ".join(sorted(course_df["establecimiento"].dropna().unique())) or ""
    fig, _ = new_page(f"{curso} · {est_str}", page_counter)
    section_heading(fig, curso)

    block_title(fig, CONTENT_L, 0.855,
                f"Matrices de transición por subprueba ({first} → {latest})")

    # Leyenda direccional
    legend_patches = [
        Patch(facecolor=DIR_COLORS["up"]["bg"],   edgecolor="#64748b", label="Mejoró"),
        Patch(facecolor=DIR_COLORS["same"]["bg"], edgecolor="#64748b", label="Se mantuvo"),
        Patch(facecolor=DIR_COLORS["down"]["bg"], edgecolor="#64748b", label="Empeoró"),
    ]
    fig.legend(handles=legend_patches, loc="center", bbox_to_anchor=(0.5, 0.825),
               ncol=3, fontsize=9, frameon=False, handlelength=1.3, columnspacing=2.5)

    rows_grid = 3
    cols_grid = 2
    grid_top = 0.785
    grid_bottom = 0.09
    grid_h = grid_top - grid_bottom
    row_gap = 0.09
    col_gap = 0.14

    panel_h = (grid_h - (rows_grid - 1) * row_gap) / rows_grid
    panel_w = (CONTENT_W - (cols_grid - 1) * col_gap) / cols_grid

    for idx, sub in enumerate(SUBPRUEBAS_ORDER):
        r = idx // cols_grid
        c = idx % cols_grid
        x = CONTENT_L + c * (panel_w + col_gap)
        y = grid_top - panel_h - r * (panel_h + row_gap)
        ax = fig.add_axes([x, y, panel_w, panel_h])

        sdf = course_df[course_df["subprueba"] == sub]
        if sdf.empty:
            ax.axis("off")
            ax.text(0.5, 0.5, f"{sub} — sin datos", ha="center", va="center",
                    fontsize=9, color=COLOR_MUTED)
            continue

        matrix, _, _, _ = compute_subprueba_transitions(sdf, first, latest)
        total = int(matrix.values.sum())
        # Sólo mostrar xlabel en la última fila y ylabel en la primera columna
        _render_transition_matrix_subprueba(ax, matrix, total, sub,
                                            SUBPRUEBAS_LABEL.get(sub, sub),
                                            first, latest,
                                            show_xlabel=(r == rows_grid - 1),
                                            show_ylabel=(c == 0))

    pdf.savefig(fig); plt.close(fig)


# ── Curso — Página D: riesgo persistente ────────────────────────────────────

def render_course_page_persistent(pdf, course_df: pd.DataFrame, curso: str,
                                  page_counter: PageCounter) -> None:
    evals = eval_ids_sorted(course_df)
    first, latest = evals[0], evals[-1]
    est_str = ", ".join(sorted(course_df["establecimiento"].dropna().unique())) or ""

    # Construir listado por (estudiante, subprueba) donde ambos niveles son de riesgo
    rows: list[list[str]] = []
    for sub in SUBPRUEBAS_ORDER:
        sdf = course_df[course_df["subprueba"] == sub]
        if sdf.empty:
            continue
        by_first = subprueba_nivel_por_est(sdf, first)
        by_latest = subprueba_nivel_por_est(sdf, latest)
        both = pd.concat([by_first.rename("f"), by_latest.rename("l")], axis=1).dropna()
        persistent = both[(both["f"].isin(RISK_LEVELS)) & (both["l"].isin(RISK_LEVELS))]
        for est, r in persistent.iterrows():
            rows.append([
                est if len(est) <= 34 else est[:32] + "…",
                sub,
                LEVEL_SHORT.get(r["f"], r["f"]),
                LEVEL_SHORT.get(r["l"], r["l"]),
            ])

    # Ordenar por estudiante (alfabético) y luego por subprueba
    rows.sort(key=lambda row: (row[0], SUBPRUEBAS_ORDER.index(row[1])))

    # Paginación
    PER_PAGE = 48
    total_rows = len(rows)
    if total_rows == 0:
        fig, _ = new_page(f"{curso} · {est_str}", page_counter)
        section_heading(fig, curso)
        block_title(fig, CONTENT_L, 0.855, "Estudiantes en riesgo persistente")
        fig.text(0.5, 0.5, "Sin estudiantes en riesgo persistente en este curso.",
                 ha="center", va="center", fontsize=12, color=COLOR_MUTED)
        pdf.savefig(fig); plt.close(fig)
        return

    cols_tbl = ["Estudiante", "Subprueba", f"Nivel\n{first}", f"Nivel\n{latest}"]
    for offset in range(0, total_rows, PER_PAGE):
        chunk = rows[offset:offset + PER_PAGE]
        fig, _ = new_page(f"{curso} · {est_str}", page_counter)
        section_heading(fig, curso)
        block_title(fig, CONTENT_L, 0.855,
                    f"Estudiantes en riesgo persistente ({offset + 1}–{offset + len(chunk)} de {total_rows})")
        ax = fig.add_axes([CONTENT_L, CONTENT_BOTTOM_Y + 0.01, CONTENT_W, 0.78])
        tbl_df = pd.DataFrame(chunk, columns=cols_tbl)
        render_table(ax, tbl_df,
                     col_widths=[0.45, 0.15, 0.20, 0.20],
                     fontsize=8.5,
                     level_tint_cols=[f"Nivel\n{first}", f"Nivel\n{latest}"],
                     row_height=1.4)
        pdf.savefig(fig); plt.close(fig)


# ── Curso — Página E: roster (nivel por subprueba × evaluación) ─────────────

def render_course_roster(pdf, course_df: pd.DataFrame, curso: str,
                         page_counter: PageCounter) -> None:
    evals = eval_ids_sorted(course_df)
    est_str = ", ".join(sorted(course_df["establecimiento"].dropna().unique())) or ""

    # Diccionario: (estudiante, subprueba, eval_id) -> nivel
    keyed = course_df.set_index(["estudiante", "subprueba", "eval_id"])["nivel"].to_dict()

    estudiantes = sorted(course_df["estudiante"].unique())

    rows_all = []
    level_cols: list[str] = []
    for est in estudiantes:
        row = [est if len(est) <= 30 else est[:28] + "…"]
        for sub in SUBPRUEBAS_ORDER:
            for e in evals:
                lv = keyed.get((est, sub, e))
                row.append(LEVEL_CODE.get(lv, "—") if lv else "—")
        rows_all.append(row)

    cols = ["Estudiante"]
    for sub in SUBPRUEBAS_ORDER:
        for e in evals:
            v_label = e.split("/")[-1]  # "v1", "v2", "v3"
            col = f"{sub}\n{v_label}"
            cols.append(col)
            level_cols.append(col)

    # Paginación
    PER_PAGE = 34
    total = len(rows_all)
    for offset in range(0, total, PER_PAGE):
        chunk = rows_all[offset:offset + PER_PAGE]
        fig, _ = new_page(f"{curso} · {est_str}", page_counter)
        section_heading(fig, curso)
        block_title(fig, CONTENT_L, 0.860,
                    f"Roster — nivel por subprueba y evaluación ({offset + 1}–{offset + len(chunk)} de {total})")

        # Leyenda de códigos en una línea por debajo del título
        legend_parts = [f"{code}={lv}" for lv, code in LEVEL_CODE.items()]
        fig.text(CONTENT_L, 0.840,
                 "Códigos:  " + "   ·   ".join(legend_parts),
                 ha="left", va="top", fontsize=8, color=COLOR_MUTED)

        # Axes: dejar espacio debajo del título y la leyenda de códigos
        ax = fig.add_axes([CONTENT_L, CONTENT_BOTTOM_Y + 0.01, CONTENT_W, 0.72])
        n_eval_cols = len(SUBPRUEBAS_ORDER) * len(evals)
        name_w = 0.24
        col_widths = [name_w] + [(1 - name_w) / n_eval_cols] * n_eval_cols
        tbl_df = pd.DataFrame(chunk, columns=cols)
        render_table(ax, tbl_df, col_widths=col_widths, fontsize=7,
                     level_tint_cols=level_cols, row_height=1.4)
        pdf.savefig(fig); plt.close(fig)


# ── Página: Síntesis comparativa ────────────────────────────────────────────

def render_closing(pdf, df: pd.DataFrame, page_counter: PageCounter) -> None:
    evals = eval_ids_sorted(df)
    first, latest = evals[0], evals[-1]
    est_str = ", ".join(sorted(df["establecimiento"].dropna().unique())) or "—"
    fig, _ = new_page(f"{est_str} · {first} → {latest}", page_counter)
    section_heading(fig, "Síntesis comparativa")

    # Tasa de mejora por curso (agregando subpruebas — cada pareja estudiante×subprueba cuenta)
    block_title(fig, CONTENT_L, 0.845,
                f"Tasa de mejora por curso ({first} → {latest})")

    # Banner de leyenda horizontal
    legend_patches = [
        Patch(color="#16a34a", label="Mejoró"),
        Patch(color="#94a3b8", label="Se mantuvo"),
        Patch(color="#dc2626", label="Empeoró"),
    ]
    fig.legend(handles=legend_patches, loc="center", bbox_to_anchor=(0.5, 0.815),
               ncol=3, fontsize=8.5, frameon=False, handlelength=1.3, columnspacing=2.5)

    ax1 = fig.add_axes([CONTENT_L, 0.52, CONTENT_W, 0.26])

    imp_v, same_v, wor_v, labels = [], [], [], []
    for c in CURSOS_ORDER:
        cdf = df[df["curso"] == c]
        if cdf.empty:
            continue
        imp, wor, same = course_aggregate_transitions(cdf, first, latest)
        total = imp + wor + same
        labels.append(c)
        if total == 0:
            imp_v.append(0); same_v.append(0); wor_v.append(0)
        else:
            imp_v.append(imp / total * 100)
            same_v.append(same / total * 100)
            wor_v.append(wor / total * 100)

    imp_v = np.array(imp_v); same_v = np.array(same_v); wor_v = np.array(wor_v)
    ax1.bar(labels, imp_v, color="#16a34a", label="Mejoró", edgecolor="white", linewidth=0.5)
    ax1.bar(labels, same_v, bottom=imp_v, color="#94a3b8", label="Se mantuvo",
            edgecolor="white", linewidth=0.5)
    ax1.bar(labels, wor_v, bottom=imp_v + same_v, color="#dc2626", label="Empeoró",
            edgecolor="white", linewidth=0.5)
    for i, (imp, s, w) in enumerate(zip(imp_v, same_v, wor_v)):
        if imp >= 4:
            ax1.text(i, imp / 2, f"{imp:.0f}%", ha="center", va="center",
                     color="white", fontsize=8.5, fontweight="bold")
        if s >= 4:
            ax1.text(i, imp + s / 2, f"{s:.0f}%", ha="center", va="center",
                     color="white", fontsize=8.5, fontweight="bold")
        if w >= 4:
            ax1.text(i, imp + s + w / 2, f"{w:.0f}%", ha="center", va="center",
                     color="white", fontsize=8.5, fontweight="bold")
    ax1.set_ylabel("% estudiante×subprueba")
    ax1.set_ylim(0, 100)

    # Evolución del promedio por subprueba
    block_title(fig, CONTENT_L, 0.475,
                f"Evolución del promedio por subprueba ({first} → {latest})")
    ax2 = fig.add_axes([CONTENT_L, 0.10, CONTENT_W, 0.35])

    rows = []
    for sub in SUBPRUEBAS_ORDER:
        m1 = df[(df["eval_id"] == first) & (df["subprueba"] == sub)]["puntaje"].mean()
        mN = df[(df["eval_id"] == latest) & (df["subprueba"] == sub)]["puntaje"].mean()
        d = mN - m1 if not (np.isnan(m1) or np.isnan(mN)) else np.nan
        rows.append([
            sub,
            SUBPRUEBAS_LABEL.get(sub, sub),
            "—" if np.isnan(m1) else f"{m1:.1f}",
            "—" if np.isnan(mN) else f"{mN:.1f}",
            "—" if np.isnan(d)  else f"{d:+.1f}",
            "↑" if (not np.isnan(d) and d > 0) else ("↓" if (not np.isnan(d) and d < 0) else "="),
        ])
    tbl_df = pd.DataFrame(rows, columns=["Sub.", "Descripción",
                                         f"Prom.\n{first}", f"Prom.\n{latest}", "Δ", "Tend."])
    render_table(ax2, tbl_df, col_widths=[0.10, 0.40, 0.15, 0.15, 0.10, 0.10],
                 fontsize=9, movement_cols=["Tend."], row_height=1.7)

    pdf.savefig(fig); plt.close(fig)


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Genera el informe PDL IDEL-Woodcock en PDF.")
    p.add_argument("--metric-id", type=int, default=DEFAULT_METRIC_ID)
    p.add_argument("--establecimiento", type=str, default=None)
    p.add_argument("--anio", "--año", dest="anio", type=int, default=None)
    p.add_argument("--versiones", type=str, default=None)
    p.add_argument("--cursos", type=str, default=None)
    p.add_argument("--out", type=Path, default=None)
    return p.parse_args(argv)


def build_output_path(args: argparse.Namespace) -> Path:
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        return args.out
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    parts = ["informe_pdl_idel"]
    if args.establecimiento:
        parts.append(args.establecimiento.lower().replace(" ", "_"))
    if args.anio:
        parts.append(str(args.anio))
    parts.append(datetime.now().strftime("%Y-%m-%d"))
    return OUTPUT_DIR / (f"{'_'.join(parts)}.pdf")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    versiones = [int(v.strip()) for v in args.versiones.split(",")] if args.versiones else None
    cursos = [c.strip() for c in args.cursos.split(",")] if args.cursos else None

    print(f"Cargando datos de metric_id={args.metric_id}…")
    df = load_data(
        metric_id=args.metric_id,
        establecimiento=args.establecimiento,
        anio=args.anio,
        versiones=versiones,
        cursos=cursos,
    )
    if df.empty:
        sys.exit("No hay filas que cumplan los filtros solicitados.")

    n_students = df["estudiante"].nunique()
    evals = eval_ids_sorted(df)
    print(f"  → {len(df)} filas, {n_students} estudiantes únicos, {len(evals)} evaluaciones: {evals}")

    out_path = build_output_path(args)
    print(f"Generando PDF: {out_path}")
    with PdfPages(out_path) as pdf:
        pc = render_all_pages(pdf, df)

    print(f"OK — PDF generado en {out_path} ({pc.n} páginas)")


def render_all_pages(pdf: "PdfPages", df: pd.DataFrame) -> PageCounter:
    """Orquestador de renderizado: panorama + páginas por curso + cierre.

    Función pública reutilizable desde el CLI y desde el backend (Fase B).
    Recibe un PdfPages ya abierto y escribe todas las páginas en él.
    Retorna el PageCounter final (útil para saber total de páginas).
    """
    pc = PageCounter()
    render_panorama(pdf, df, pc)
    for curso in CURSOS_ORDER:
        cdf = df[df["curso"] == curso]
        if cdf.empty:
            continue
        render_course_page_a(pdf, cdf, curso, pc)
        render_course_page_b(pdf, cdf, curso, pc)
        render_course_page_transitions(pdf, cdf, curso, pc)
        render_course_page_persistent(pdf, cdf, curso, pc)
        render_course_roster(pdf, cdf, curso, pc)
    render_closing(pdf, df, pc)
    return pc


if __name__ == "__main__":
    main()
