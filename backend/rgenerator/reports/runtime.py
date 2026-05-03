"""Orquestador del motor PDF v2.

Recibe (esquema + dataframes + params) y produce bytes PDF. No conoce de
SIMCE/DIA específicos — lee el `esquema.json` del tipo solicitado y ejecuta
las funciones declaradas usando `CHART_REGISTRY` y `TABLE_REGISTRY`.

Flujo:
    1) Carga esquema.json del report_type.
    2) Crea aux_dir temporal para PNGs intermedios.
    3) Para cada sección fija:
        - chart → llama charts.fn(df, ..., nombre_grafico=aux_dir/X.png)
                  → embebe como <img src="data:base64,...">
        - table → llama tables.fn(df, ...) → DataFrame
                  → renderiza con helpers.df_a_html_table
    4) Para secciones_dinamicas (iteración por curso/categoría): idem pero
       repitiendo por cada valor único (TODO en próximo iter).
    5) Renderiza informe_base.html con Jinja2.
    6) WeasyPrint → bytes PDF.
    7) Limpia aux_dir.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from datetime import date
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML as WeasyprintHTML

from . import charts, tables
from .helpers import df_a_html_table, embed_png_b64

REPORTS_DIR = Path(__file__).parent
TEMPLATES_DIR = REPORTS_DIR / "templates"
ASSETS_DIR = REPORTS_DIR / "assets"


def _resolve_logo_path(name: str | None) -> str | None:
    """Resuelve un nombre de logo a path absoluto en assets/. None si no existe."""
    if not name:
        return None
    p = ASSETS_DIR / name
    return str(p) if p.exists() else None


def _ejecutar_seccion(
    seccion: dict,
    dataframes: dict[str, pd.DataFrame],
    aux_dir: Path,
) -> dict:
    """Ejecuta UNA sección del esquema y devuelve un dict listo para Jinja.

    Args:
        seccion: dict del esquema con keys `tipo`, `titulo`, `fn`,
            `df_input`, `params`.
        dataframes: dict {role: DataFrame} disponibles.
        aux_dir: Path donde guardar PNGs intermedios.

    Returns:
        Dict con `tipo` y datos renderizados:
            chart → {tipo: "chart", titulo, image_b64}
            table → {tipo: "table", titulo, html}
            heading → {tipo: "heading", titulo}  (puramente visual)
    """
    tipo = seccion.get("tipo")
    titulo = seccion.get("titulo", "")

    if tipo == "heading":
        return {"tipo": "heading", "titulo": titulo}

    if tipo == "page_break":
        return {"tipo": "page_break"}

    fn_name = seccion.get("fn")
    df_key = seccion.get("df_input")
    params = dict(seccion.get("params", {}))  # copia, no mutamos el esquema

    if df_key not in dataframes:
        return {"tipo": "error", "titulo": titulo, "msg": f"DataFrame '{df_key}' no disponible"}
    df = dataframes[df_key]

    if tipo == "chart":
        spec = charts.CHART_REGISTRY.get(fn_name)
        if not spec:
            return {"tipo": "error", "titulo": titulo, "msg": f"Chart '{fn_name}' no existe"}
        # Path PNG temporal
        png_path = aux_dir / f"{fn_name}_{abs(hash(json.dumps(params, sort_keys=True, default=str)))}.png"
        params["nombre_grafico"] = str(png_path)
        try:
            spec["fn"](df, **params)
        except Exception as e:  # pragma: no cover — defensivo, mostramos error in-place
            return {"tipo": "error", "titulo": titulo, "msg": f"{type(e).__name__}: {e}"}
        return {"tipo": "chart", "titulo": titulo, "image_b64": embed_png_b64(png_path)}

    if tipo == "table":
        spec = tables.TABLE_REGISTRY.get(fn_name)
        if not spec:
            return {"tipo": "error", "titulo": titulo, "msg": f"Table '{fn_name}' no existe"}
        try:
            df_out = spec["fn"](df, **params)
        except Exception as e:  # pragma: no cover
            return {"tipo": "error", "titulo": titulo, "msg": f"{type(e).__name__}: {e}"}
        return {"tipo": "table", "titulo": titulo, "html": df_a_html_table(df_out)}

    return {"tipo": "error", "titulo": titulo, "msg": f"Tipo desconocido: {tipo}"}


def construir_pdf(
    report_type: str,
    dataframes: dict[str, pd.DataFrame],
    overrides: dict | None = None,
) -> bytes:
    """Punto de entrada: genera bytes PDF para un tipo de informe.

    Args:
        report_type: "simce" | "dia" | etc. — coincide con el subdirectorio
            que contiene el esquema.json.
        dataframes: dict {role: DataFrame}, ej {"estudiantes": df1,
            "preguntas": df2}. Las keys deben coincidir con las que el
            esquema declare en `df_input`.
        overrides: dict opcional para sobreescribir partes del esquema en
            runtime (ej {"branding": {"center_header": ["...", "...", "..."]}}).
            Útil para que el endpoint reciba parámetros de UI.

    Returns:
        Bytes del PDF generado.

    Raises:
        FileNotFoundError: si no existe el esquema.json del tipo solicitado.
    """
    esquema_path = REPORTS_DIR / report_type / "esquema.json"
    if not esquema_path.exists():
        raise FileNotFoundError(f"No existe esquema para tipo '{report_type}': {esquema_path}")

    with open(esquema_path, "r", encoding="utf-8") as f:
        esquema = json.load(f)

    # Aplicar overrides (merge superficial, suficiente para esta versión)
    if overrides:
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(esquema.get(key), dict):
                esquema[key].update(value)
            else:
                esquema[key] = value

    # Resolver branding (logos a path absoluto + base64)
    branding = dict(esquema.get("branding", {}))
    for side in ("left_image", "right_image"):
        path = _resolve_logo_path(branding.get(side))
        if path:
            branding[f"{side}_b64"] = embed_png_b64(path)
        else:
            branding[f"{side}_b64"] = None

    # Ejecutar secciones dentro de un aux_dir temporal
    with tempfile.TemporaryDirectory(prefix=f"report_{report_type}_") as tmp_str:
        aux_dir = Path(tmp_str)

        rendered = []
        for sec in esquema.get("secciones_fijas", []):
            rendered.append(_ejecutar_seccion(sec, dataframes, aux_dir))

        # Renderizar HTML
        env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
        template = env.get_template("informe_base.html")
        html_str = template.render(
            title=esquema.get("title", "Informe"),
            subtitle=esquema.get("subtitle", ""),
            filters_label=esquema.get("filters_label", ""),
            secciones=rendered,
            branding=branding,
            report_date=date.today().strftime("%d/%m/%Y"),
        )

        # WeasyPrint
        return WeasyprintHTML(string=html_str, base_url=str(REPORTS_DIR)).write_pdf()
