"""Motor de renderizado de informes Word (docxtpl).

Toma un informe registrado (módulo en `informes/` + plantilla .docx en
`templates/`) y produce bytes .docx listos para descargar.

Contrato del módulo de informe (`informes/<nombre>.py`):
    - `construir_contexto(dataframes, params) -> dict`  (obligatorio)
    - `PLANTILLA: str`   nombre del .docx en templates/ (default `<nombre>.docx`)
    - `LABEL: str`       nombre legible para el frontend (default = nombre)
    - `DESCRIPCION: str` texto de ayuda (opcional)
    - `PARAMS_ESPERADOS: list[str]` documentación de params (opcional)

El contexto que devuelve `construir_contexto` es un dict Jinja2 normal.
Dos tipos especiales se post-procesan antes de renderizar:
    - `Grafico(fn=..., df=..., params=...)` → se ejecuta la función del
      CHART_REGISTRY del motor v2, se guarda un PNG temporal y se inserta
      como InlineImage en el Word.
    - `Imagen(path=...)` → PNG/JPG ya existente insertado como InlineImage.

La plantilla Word usa sintaxis Jinja2 estándar de docxtpl:
    {{ titulo }}                          → valor simple
    {%tr for fila in resumen %} ... {%tr endfor %}  → filas de tabla
    {{ grafico_logro }}                   → clave cuyo valor es Grafico/Imagen
"""
from __future__ import annotations

import io
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

TEMPLATES_DIR = Path(__file__).parent / "templates"


# ─────────────────────────────────────────────────────────────────────────
# Tipos especiales que un informe puede poner en su contexto
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class Grafico:
    """Marca un gráfico del CHART_REGISTRY para insertar en el Word.

    Args:
        fn: nombre de la función en `reports.charts.CHART_REGISTRY`
            (ej "grafico_barras_promedio_por").
        df: DataFrame de entrada para la función.
        params: kwargs extra para la función (sin `nombre_grafico`,
            que lo maneja el engine).
        width_mm: ancho de la imagen dentro del Word.
    """
    fn: str
    df: pd.DataFrame
    params: dict = field(default_factory=dict)
    width_mm: int = 160


@dataclass
class Imagen:
    """Imagen ya existente en disco para insertar como InlineImage."""
    path: str | Path
    width_mm: int = 160


# ─────────────────────────────────────────────────────────────────────────
# Helpers para construir contextos
# ─────────────────────────────────────────────────────────────────────────

def tabla_desde_df(
    df: pd.DataFrame,
    columnas: list[str] | None = None,
    formatos: dict[str, str] | None = None,
) -> list[dict]:
    """Convierte un DataFrame en lista de dicts para loops `{%tr for %}`.

    Args:
        df: DataFrame de entrada.
        columnas: subset y orden de columnas a incluir (default: todas).
        formatos: dict {columna: format_spec} aplicado con `format()`,
            ej {"Promedio": ".1%"} → "85.3%".

    Returns:
        Lista de dicts, un dict por fila, con las claves normalizadas
        para Jinja (espacios → `_`, minúsculas, sin tildes básicas).
    """
    if columnas:
        df = df[[c for c in columnas if c in df.columns]]
    formatos = formatos or {}

    def _key(col: str) -> str:
        s = str(col).strip().lower()
        for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                     ("ú", "u"), ("ñ", "n"), ("°", ""), (" ", "_")):
            s = s.replace(a, b)
        return s

    filas = []
    for _, row in df.iterrows():
        fila = {}
        for col in df.columns:
            val = row[col]
            if col in formatos and pd.notna(val):
                try:
                    val = format(val, formatos[col])
                except (ValueError, TypeError):
                    val = str(val)
            elif pd.isna(val):
                val = ""
            fila[_key(col)] = val
        filas.append(fila)
    return filas


# ─────────────────────────────────────────────────────────────────────────
# Render
# ─────────────────────────────────────────────────────────────────────────

def _materializar_especiales(doc, contexto: Any, aux_dir: Path) -> Any:
    """Convierte recursivamente Grafico/Imagen del contexto en InlineImage.

    Se llama después de tener el DocxTemplate (InlineImage lo requiere).
    """
    from docx.shared import Mm
    from docxtpl import InlineImage

    if isinstance(contexto, Grafico):
        from ..charts import CHART_REGISTRY
        spec = CHART_REGISTRY.get(contexto.fn)
        if not spec:
            raise KeyError(
                f"Grafico fn='{contexto.fn}' no existe en CHART_REGISTRY. "
                f"Disponibles: {sorted(CHART_REGISTRY)}"
            )
        png_path = aux_dir / f"chart_{contexto.fn}_{id(contexto)}.png"
        params = dict(contexto.params)
        params["nombre_grafico"] = str(png_path)
        spec["fn"](contexto.df, **params)
        return InlineImage(doc, str(png_path), width=Mm(contexto.width_mm))

    if isinstance(contexto, Imagen):
        p = Path(contexto.path)
        if not p.exists():
            raise FileNotFoundError(f"Imagen no encontrada: {p}")
        return InlineImage(doc, str(p), width=Mm(contexto.width_mm))

    if isinstance(contexto, dict):
        return {k: _materializar_especiales(doc, v, aux_dir) for k, v in contexto.items()}
    if isinstance(contexto, list):
        return [_materializar_especiales(doc, v, aux_dir) for v in contexto]
    return contexto


def resolver_plantilla(modulo) -> Path:
    """Path absoluto de la plantilla .docx de un módulo de informe."""
    nombre = getattr(modulo, "NOMBRE", modulo.__name__.rsplit(".", 1)[-1])
    plantilla = getattr(modulo, "PLANTILLA", f"{nombre}.docx")
    return TEMPLATES_DIR / plantilla


def listar_placeholders(modulo) -> list[str]:
    """Variables Jinja no declaradas que la plantilla espera ({{valor}}).

    Útil para que el frontend (o el autor del informe) sepa qué claves
    debe devolver `construir_contexto`.
    """
    from docxtpl import DocxTemplate

    path = resolver_plantilla(modulo)
    if not path.exists():
        raise FileNotFoundError(f"Plantilla no encontrada: {path}")
    doc = DocxTemplate(str(path))
    return sorted(doc.get_undeclared_template_variables())


def render_informe(
    modulo,
    dataframes: dict[str, pd.DataFrame],
    params: dict | None = None,
) -> bytes:
    """Renderiza un informe Word y devuelve los bytes .docx.

    Args:
        modulo: módulo de informe (obtenido del registry por nombre).
        dataframes: dict {rol: DataFrame} — normalmente el output de
            `cargar_dataframes_indicator`.
        params: parámetros del frontend (ej {"titulo": "...", "mes": "Mayo"}).

    Returns:
        Bytes del archivo .docx renderizado.

    Raises:
        FileNotFoundError: si la plantilla no existe.
        Exception: lo que lance `construir_contexto` del informe.
    """
    from docxtpl import DocxTemplate

    plantilla_path = resolver_plantilla(modulo)
    if not plantilla_path.exists():
        raise FileNotFoundError(
            f"Plantilla no encontrada: {plantilla_path}. "
            f"Crear con: python scripts/nuevo_informe_word.py <nombre>"
        )

    contexto = modulo.construir_contexto(dataframes, params or {})
    if not isinstance(contexto, dict):
        raise TypeError(
            f"construir_contexto de '{modulo.__name__}' debe devolver dict, "
            f"devolvió {type(contexto).__name__}"
        )

    doc = DocxTemplate(str(plantilla_path))
    with tempfile.TemporaryDirectory(prefix="word_report_") as tmp:
        contexto_final = _materializar_especiales(doc, contexto, Path(tmp))
        doc.render(contexto_final)
        buf = io.BytesIO()
        doc.save(buf)
    return buf.getvalue()
