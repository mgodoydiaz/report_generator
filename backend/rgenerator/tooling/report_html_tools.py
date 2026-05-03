"""Helpers para generar HTML con paridad visual a `formato_informe.tex` (LaTeX).

Replican la lógica de `df_a_latex_loop` y `img_to_latex` de `report_tools.py`
pero produciendo HTML+CSS para WeasyPrint en vez de LaTeX.

Convención de estilo: las clases CSS están definidas en
`backend/rgenerator/templates/report_latex_paridad.html`. Este módulo solo
emite el HTML; el styling vive en el template.
"""

from pathlib import Path
from typing import List, Dict, Optional
import base64
import pandas as pd


def _is_numeric_column(series: pd.Series) -> bool:
    """Determina si una columna debe alinearse a la derecha (números o porcentajes)."""
    if pd.api.types.is_numeric_dtype(series):
        return True
    s = series.astype(str)
    if s.str.endswith('%').any():
        return True
    try:
        pd.to_numeric(s, errors='raise')
        return True
    except (ValueError, TypeError):
        return False


def df_to_html_table(df: pd.DataFrame, css_class: str = "report-table") -> str:
    """
    Convierte un DataFrame a tabla HTML con estilo `formato_informe.tex`.

    Mismo contrato que `df_a_latex_loop`:
        - Bordes en todas las celdas
        - Encabezado en negrita
        - Columnas numéricas alineadas a la derecha
        - Columnas de texto alineadas a la izquierda
        - La primera columna SIEMPRE alineada a la izquierda (es el "label")
    """
    cols = df.columns.tolist()
    if not cols:
        return f'<table class="{css_class}"></table>'

    align = []
    for i, c in enumerate(cols):
        if i == 0:
            align.append('left')
        else:
            align.append('right' if _is_numeric_column(df[c]) else 'left')

    parts = [f'<table class="{css_class}">']
    parts.append('<thead><tr>')
    for c, a in zip(cols, align):
        parts.append(f'<th class="al-{a}">{_html_escape(str(c))}</th>')
    parts.append('</tr></thead>')

    parts.append('<tbody>')
    for _, row in df.iterrows():
        parts.append('<tr>')
        for c, a in zip(cols, align):
            v = row[c]
            v_str = '' if pd.isna(v) else str(v)
            parts.append(f'<td class="al-{a}">{_html_escape(v_str)}</td>')
        parts.append('</tr>')
    parts.append('</tbody></table>')

    return ''.join(parts)


def img_to_html(path: Path, css_class: str = "report-figure", options: str = "") -> str:
    """
    Genera <figure> con imagen embebida en base64 (necesario para WeasyPrint
    cuando los assets están fuera del directorio del template).

    `options` permite control inline opcional al estilo LaTeX:
        - "height=0.4textheight" → height: 40vh (aprox)
        - "width=0.9textwidth"   → width: 90%
    Si no se especifica, usa width: 100% (default tipo \\textwidth de LaTeX).
    """
    path = Path(path)
    if not path.exists():
        return f'<figure class="{css_class}"><div class="missing">[Imagen no encontrada: {path.name}]</div></figure>'

    suffix = path.suffix.lower().lstrip('.')
    mime = {
        'png': 'image/png',
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'svg': 'image/svg+xml',
        'gif': 'image/gif',
        'webp': 'image/webp',
    }.get(suffix, 'application/octet-stream')

    b64 = base64.b64encode(path.read_bytes()).decode('ascii')
    src = f'data:{mime};base64,{b64}'

    style = _options_to_css(options) if options else 'width: 100%;'
    return (
        f'<figure class="{css_class}">'
        f'<img src="{src}" style="{style}" alt="{path.stem}"/>'
        f'</figure>'
    )


def _options_to_css(options: str) -> str:
    """Traduce opciones tipo LaTeX a CSS inline. Best-effort.

    Si solo se especifica `height=...` (sin width), igual se inyecta
    `max-width: 100%` para que la imagen nunca desborde el ancho de la
    página — equivalente a lo que LaTeX consigue cuando las imágenes
    están dentro de un `\\linewidth` aunque `\\includegraphics` no lo fuerce.
    """
    out = []
    has_width = False
    opts = options.replace('\\', '').replace(' ', '')
    parts = opts.split(',')
    for p in parts:
        if not p:
            continue
        if p.startswith('width='):
            has_width = True
            val = p[len('width='):]
            if 'textwidth' in val:
                pct = val.replace('textwidth', '')
                try:
                    pct_num = float(pct or '1.0')
                    out.append(f'width: {int(pct_num * 100)}%;')
                except ValueError:
                    out.append('width: 100%;')
            else:
                out.append(f'width: {val};')
        elif p.startswith('height='):
            val = p[len('height='):]
            if 'textheight' in val:
                pct = val.replace('textheight', '')
                try:
                    pct_num = float(pct or '1.0')
                    out.append(f'max-height: {int(pct_num * 100)}vh;')
                except ValueError:
                    out.append('max-height: 50vh;')
            else:
                out.append(f'height: {val};')
    if not has_width:
        out.append('max-width: 100%;')
    if not out:
        out.append('width: 100%;')
    return ' '.join(out)


def _html_escape(s: str) -> str:
    """Escape mínimo para HTML."""
    return (
        s.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
    )


def encode_image_b64(path: Path) -> Optional[Dict[str, str]]:
    """Lee una imagen del disco y devuelve {b64, mime} o None si no existe."""
    path = Path(path)
    if not path.exists():
        return None
    suffix = path.suffix.lower().lstrip('.')
    mime = {
        'png': 'image/png',
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'svg': 'image/svg+xml',
    }.get(suffix, 'application/octet-stream')
    return {
        'b64': base64.b64encode(path.read_bytes()).decode('ascii'),
        'mime': mime,
    }


def render_section(seccion: dict, aux_dir: Path, base_dir: Optional[Path] = None) -> dict:
    """
    Convierte una sección del esquema (LaTeX-style) en un dict listo para Jinja.

    seccion = { titulo, tipo: 'tabla'|'imagen', contenido, options? }

    Devuelve dict con:
        - titulo: str
        - tipo: 'tabla' | 'imagen'
        - html: str (la tabla o el <figure> ya renderizado)
    """
    titulo = seccion.get('titulo', '')
    tipo = seccion.get('tipo')
    contenido = seccion.get('contenido', '')

    content_path = Path(contenido)
    if not content_path.is_absolute():
        if (aux_dir / contenido).exists():
            content_path = aux_dir / contenido
        elif base_dir and (base_dir / contenido).exists():
            content_path = base_dir / contenido
        else:
            content_path = aux_dir / Path(contenido).name

    if tipo == 'tabla':
        try:
            df = pd.read_excel(content_path)
            html = df_to_html_table(df)
        except Exception as e:
            html = f'<p class="error">[Error leyendo tabla {content_path.name}: {e}]</p>'
    elif tipo == 'imagen':
        html = img_to_html(content_path, options=seccion.get('options', ''))
    else:
        html = f'<p class="error">[Tipo de sección desconocido: {tipo}]</p>'

    return {'titulo': titulo, 'tipo': tipo, 'html': html}
