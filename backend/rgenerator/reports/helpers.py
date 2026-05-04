"""Utilidades comunes del motor PDF v2.

- df_a_html_table: equivalente HTML del df_a_latex_loop. Detecta columnas
  numéricas / porcentajes y alinea a derecha; texto a izquierda. Headers en
  bold. Bordes negros 0.5pt vía la clase CSS `report-table` del template.
- embed_png_b64: lee un PNG de disco y devuelve `data:image/png;base64,...`
  para embeberlo inline en el HTML (evita paths absolutos en WeasyPrint).
- format_curso_corto: "I A (TPI-510)" → "I A".
"""
from __future__ import annotations

import base64
from html import escape as html_escape
from pathlib import Path

import pandas as pd


def df_a_html_table(df: pd.DataFrame, css_class: str = "report-table") -> str:
    """Convierte DataFrame → HTML <table> con alineación smart.

    - Columnas numéricas o que terminen en % → texto alineado a derecha.
    - Otras columnas → alineado a izquierda.
    - Headers en bold (vía CSS de la clase `report-table`).
    - Sin zebra. Bordes negros 0.5pt.

    Args:
        df: DataFrame a renderizar.
        css_class: clase CSS de la tabla. Default "report-table" (definida
            en templates/informe_base.html).

    Returns:
        HTML string.

    Equivalente LaTeX: df_a_latex_loop (en SIMCE/DIA funciones.py).
    """
    cols = df.columns.tolist()

    # Detectar columnas numéricas / porcentajes (igual que df_a_latex_loop)
    numeric_cols_mask = df.apply(
        lambda x: pd.to_numeric(x, errors="coerce").notnull().all()
    ).to_list()
    percent_cols_mask = df.apply(
        lambda x: x.astype(str).str.endswith("%")
    ).any().tolist()
    is_numeric = [n or p for n, p in zip(numeric_cols_mask, percent_cols_mask)]

    # Render
    parts = [f'<table class="{css_class}">']

    # Header
    parts.append("<thead><tr>")
    for c, num in zip(cols, is_numeric):
        align_class = "al-right" if num else "al-left"
        parts.append(f'<th class="{align_class}">{html_escape(str(c))}</th>')
    parts.append("</tr></thead>")

    # Body
    parts.append("<tbody>")
    for _, row in df.iterrows():
        parts.append("<tr>")
        for val, num in zip(row.values, is_numeric):
            align_class = "al-right" if num else "al-left"
            parts.append(f'<td class="{align_class}">{html_escape(str(val))}</td>')
        parts.append("</tr>")
    parts.append("</tbody></table>")

    return "".join(parts)


def embed_png_b64(path: str | Path) -> str:
    """Lee un PNG de disco y devuelve data URI base64.

    Args:
        path: ruta al PNG.

    Returns:
        String "data:image/png;base64,iVBORw0KGgo..." apto para
        usar como `<img src="...">` en HTML.
    """
    p = Path(path)
    with open(p, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


def format_curso_corto(curso: str) -> str:
    """Limpia "I A (TPI-510)" → "I A". Útil para etiquetas de eje X.

    Args:
        curso: nombre completo del curso.

    Returns:
        Nombre sin texto entre paréntesis.
    """
    if not isinstance(curso, str):
        return str(curso)
    return curso.split(" (")[0]
