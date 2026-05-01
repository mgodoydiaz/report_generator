"""Tests unitarios para `rgenerator.tooling.report_html_tools`.

Cubre los helpers que producen HTML para `RenderHtmlReport` con paridad
visual a `formato_informe.tex`. No requieren WeasyPrint instalado.
"""

import base64
from pathlib import Path

import pandas as pd
import pytest

from rgenerator.tooling.report_html_tools import (
    _html_escape,
    _is_numeric_column,
    _options_to_css,
    df_to_html_table,
    encode_image_b64,
    img_to_html,
    render_section,
)


# ───────────────────────────── _is_numeric_column ─────────────────────────────


class TestIsNumericColumn:
    def test_int_series(self):
        assert _is_numeric_column(pd.Series([1, 2, 3])) is True

    def test_float_series(self):
        assert _is_numeric_column(pd.Series([1.5, 2.7, 3.14])) is True

    def test_percent_strings(self):
        assert _is_numeric_column(pd.Series(["50%", "75%", "100%"])) is True

    def test_numeric_strings(self):
        assert _is_numeric_column(pd.Series(["10", "20", "30"])) is True

    def test_text_strings(self):
        assert _is_numeric_column(pd.Series(["hola", "mundo", "foo"])) is False

    def test_mixed_text_and_numbers(self):
        # Si NO todos son convertibles a número, no es numérica
        assert _is_numeric_column(pd.Series(["1", "dos", "3"])) is False


# ─────────────────────────────── _options_to_css ──────────────────────────────


class TestOptionsToCss:
    def test_empty_returns_full_width(self):
        # Sin opciones: max-width: 100% (defensivo) — ambos width y max-width
        # son aceptables siempre que la imagen no desborde el ancho.
        out = _options_to_css("")
        assert "100%" in out

    def test_width_textwidth_full(self):
        assert _options_to_css("width=textwidth") == "width: 100%;"

    def test_width_textwidth_with_factor(self):
        assert _options_to_css("width=0.9textwidth") == "width: 90%;"

    def test_width_in_cm(self):
        out = _options_to_css("width=5cm")
        assert "width: 5cm;" in out

    def test_height_textheight_adds_max_width(self):
        # Solo height → debe agregar max-width: 100% para no desbordar
        out = _options_to_css("height=0.4textheight")
        assert "max-height: 40vh;" in out
        assert "max-width: 100%;" in out

    def test_height_in_cm_adds_max_width(self):
        out = _options_to_css("height=10cm")
        assert "height: 10cm;" in out
        assert "max-width: 100%;" in out

    def test_width_present_no_max_width(self):
        # Si hay width explícito, NO se agrega max-width
        out = _options_to_css("width=8cm,height=5cm")
        assert "max-width" not in out

    def test_strips_backslashes(self):
        # LaTeX-style \textwidth debe ser equivalente a textwidth
        assert _options_to_css(r"width=0.9\textwidth") == "width: 90%;"


# ───────────────────────────────── _html_escape ────────────────────────────────


class TestHtmlEscape:
    def test_ampersand(self):
        assert _html_escape("Tom & Jerry") == "Tom &amp; Jerry"

    def test_lt_gt(self):
        assert _html_escape("<script>") == "&lt;script&gt;"

    def test_quotes(self):
        assert _html_escape("\"Hola\" 'mundo'") == "&quot;Hola&quot; &#39;mundo&#39;"

    def test_ampersand_first(self):
        # El & debe escaparse PRIMERO para no doble-escapar
        assert _html_escape("&lt;") == "&amp;lt;"


# ──────────────────────────────── df_to_html_table ─────────────────────────────


class TestDfToHtmlTable:
    def test_empty_df_returns_empty_table(self):
        out = df_to_html_table(pd.DataFrame())
        assert out == '<table class="report-table"></table>'

    def test_first_col_left_aligned(self):
        df = pd.DataFrame({"Curso": ["2A", "2B"], "Promedio": [80, 75]})
        out = df_to_html_table(df)
        # Primera columna SIEMPRE al-left (es el "label")
        assert '<th class="al-left">Curso</th>' in out
        # Segunda numérica → al-right
        assert '<th class="al-right">Promedio</th>' in out

    def test_text_column_left_aligned(self):
        df = pd.DataFrame({"Curso": ["2A", "2B"], "Nivel": ["Adecuado", "Elemental"]})
        out = df_to_html_table(df)
        # Ambas son texto → ambas al-left
        assert out.count('class="al-left"') >= 4  # 2 headers + 2 datos por columna

    def test_html_escape_in_cells(self):
        df = pd.DataFrame({"Texto": ["<script>alert('x')</script>"]})
        out = df_to_html_table(df)
        assert "&lt;script&gt;" in out
        assert "<script>" not in out

    def test_nan_renders_empty(self):
        df = pd.DataFrame({"X": [1.0, None, 3.0]})
        out = df_to_html_table(df)
        # Hay 3 filas, ninguna debe contener "nan"
        assert "nan" not in out.lower()

    def test_custom_css_class(self):
        df = pd.DataFrame({"X": [1]})
        out = df_to_html_table(df, css_class="my-table")
        assert 'class="my-table"' in out

    def test_structure_thead_tbody(self):
        df = pd.DataFrame({"X": [1, 2]})
        out = df_to_html_table(df)
        assert "<thead>" in out
        assert "<tbody>" in out
        assert out.index("<thead>") < out.index("<tbody>")


# ───────────────────────────────── img_to_html ─────────────────────────────────


@pytest.fixture
def png_1x1(tmp_path):
    """PNG 1x1 válido generado con Pillow (evita hardcodear bytes frágiles)."""
    from PIL import Image
    p = tmp_path / "test.png"
    Image.new("RGB", (1, 1), color="white").save(p)
    return p


class TestImgToHtml:
    def test_missing_file_renders_placeholder(self, tmp_path):
        out = img_to_html(tmp_path / "no_existe.png")
        assert "no encontrada" in out
        assert "missing" in out

    def test_existing_png_returns_data_uri(self, png_1x1):
        out = img_to_html(png_1x1)
        assert "data:image/png;base64," in out
        assert "<figure" in out
        assert "<img" in out

    def test_default_width_full(self, png_1x1):
        out = img_to_html(png_1x1)
        assert "width: 100%" in out

    def test_options_propagate(self, png_1x1):
        out = img_to_html(png_1x1, options="width=0.9textwidth")
        assert "width: 90%" in out

    def test_jpeg_mime(self, tmp_path):
        p = tmp_path / "x.jpg"
        # JPEG mínimo (no es válido pero suficiente para test de mime)
        p.write_bytes(b"\xff\xd8\xff\xe0")
        out = img_to_html(p)
        assert "data:image/jpeg;base64," in out

    def test_custom_css_class(self, png_1x1):
        out = img_to_html(png_1x1, css_class="my-fig")
        assert 'class="my-fig"' in out


# ──────────────────────────── encode_image_b64 ────────────────────────────────


class TestEncodeImageB64:
    def test_missing_returns_none(self, tmp_path):
        assert encode_image_b64(tmp_path / "no.png") is None

    def test_existing_returns_dict(self, png_1x1):
        meta = encode_image_b64(png_1x1)
        assert meta is not None
        assert meta["mime"] == "image/png"
        # b64 decodificable y con bytes
        decoded = base64.b64decode(meta["b64"])
        assert len(decoded) > 0
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_jpeg_mime(self, tmp_path):
        p = tmp_path / "x.jpeg"
        p.write_bytes(b"\xff\xd8\xff\xe0")
        meta = encode_image_b64(p)
        assert meta["mime"] == "image/jpeg"

    def test_unknown_extension(self, tmp_path):
        p = tmp_path / "x.bin"
        p.write_bytes(b"raw")
        meta = encode_image_b64(p)
        assert meta["mime"] == "application/octet-stream"


# ───────────────────────────────── render_section ─────────────────────────────


class TestRenderSection:
    def test_unknown_type(self, tmp_path):
        out = render_section(
            {"titulo": "X", "tipo": "raro", "contenido": ""},
            aux_dir=tmp_path,
        )
        assert out["tipo"] == "raro"
        assert "desconocido" in out["html"]

    def test_imagen_missing(self, tmp_path):
        out = render_section(
            {"titulo": "Sin imagen", "tipo": "imagen", "contenido": "no.png"},
            aux_dir=tmp_path,
        )
        assert out["titulo"] == "Sin imagen"
        assert out["tipo"] == "imagen"
        assert "no encontrada" in out["html"]

    def test_imagen_resolves_in_aux_dir(self, tmp_path, png_1x1):
        # png_1x1 está en tmp_path; la sección referencia su nombre
        out = render_section(
            {"titulo": "T", "tipo": "imagen", "contenido": png_1x1.name},
            aux_dir=tmp_path,
        )
        assert "data:image/png;base64," in out["html"]

    def test_imagen_resolves_in_base_dir(self, tmp_path, png_1x1):
        # aux_dir vacío, base_dir contiene la imagen
        empty = tmp_path / "empty"
        empty.mkdir()
        out = render_section(
            {"titulo": "T", "tipo": "imagen", "contenido": png_1x1.name},
            aux_dir=empty,
            base_dir=tmp_path,
        )
        assert "data:image/png;base64," in out["html"]

    def test_imagen_options_propagate(self, tmp_path, png_1x1):
        out = render_section(
            {"titulo": "T", "tipo": "imagen", "contenido": png_1x1.name,
             "options": "width=0.5textwidth"},
            aux_dir=tmp_path,
        )
        assert "width: 50%" in out["html"]

    def test_tabla_xlsx_rendered(self, tmp_path):
        df = pd.DataFrame({"Curso": ["2A", "2B"], "Promedio": [80, 75]})
        xlsx = tmp_path / "t.xlsx"
        df.to_excel(xlsx, index=False)
        out = render_section(
            {"titulo": "Tabla", "tipo": "tabla", "contenido": "t.xlsx"},
            aux_dir=tmp_path,
        )
        assert out["tipo"] == "tabla"
        assert "<table" in out["html"]
        assert "Curso" in out["html"]
        assert "Promedio" in out["html"]

    def test_tabla_missing_file_returns_error(self, tmp_path):
        out = render_section(
            {"titulo": "X", "tipo": "tabla", "contenido": "no.xlsx"},
            aux_dir=tmp_path,
        )
        assert "Error leyendo" in out["html"]
