"""Tests del step RunDIAPDFExtraction.

Cobertura:
- Helpers puros: `_get_correct_percent`, `_es_tabla_preguntas`.
- Detección de sección con PDFs sintéticos (formatos Cierre/Matemática
  con encabezados no numerados o abreviados — ver fix de sept-2026).
- Registro en STEP_MAPPING.
- Helpers con PDF real (skip si no hay PDFs DIA disponibles localmente).
- Step completo con PDF real (skip si no hay).

Los tests con PDF real se saltean automáticamente cuando se corre en CI
o en una máquina sin acceso a los PDFs del cliente.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from backend.rgenerator.core.pdf_steps import (
    RunDIAPDFExtraction,
    _detectar_paginas_tabla_preguntas,
    _es_tabla_preguntas,
    _extraer_establecimiento_y_curso,
    _get_correct_percent,
)


# Path donde Miguel guarda PDFs reales del cliente. Los tests con PDF real
# corren si esa carpeta existe; si no, se saltean.
_DIA_REAL_DIR = Path(
    r"C:\Users\magod\Documents\Proyectos\Informes PHP\Evaluaciones 2026\DIA"
    r"\Lectura Diagnóstico Panguipulli Media"
)


def _real_pdf_disponible() -> Path | None:
    if not _DIA_REAL_DIR.exists():
        return None
    pdfs = sorted(
        f for f in _DIA_REAL_DIR.iterdir()
        if f.name.startswith("RBD") and f.suffix.lower() == ".pdf"
    )
    return pdfs[0] if pdfs else None


def _fitz_disponible() -> bool:
    try:
        import fitz  # noqa: F401
        return True
    except ImportError:
        return False


def _camelot_disponible() -> bool:
    try:
        import camelot.io  # noqa: F401
        return True
    except ImportError:
        return False


needs_real_pdf_fitz = pytest.mark.skipif(
    _real_pdf_disponible() is None or not _fitz_disponible(),
    reason="Falta PDF DIA real o fitz/PyMuPDF no instalado",
)

needs_real_pdf_camelot = pytest.mark.skipif(
    _real_pdf_disponible() is None or not _fitz_disponible() or not _camelot_disponible(),
    reason="Falta PDF DIA real o fitz/camelot no instalados",
)


# ─────────────────────────────────────────────────────────────────────────
# Helpers puros (no requieren PDF)
# ─────────────────────────────────────────────────────────────────────────


class TestGetCorrectPercent:
    def test_caso_basico(self):
        cell = "A: 34.62%\nB: 7.69%\nC: 11.54%\nD: 46.15%\nN: 0.00%"
        assert _get_correct_percent(cell, "D") == pytest.approx(46.15)
        assert _get_correct_percent(cell, "A") == pytest.approx(34.62)

    def test_no_encontrada_devuelve_cero(self):
        cell = "A: 100.00%\nN: 0.00%"
        assert _get_correct_percent(cell, "Z") == 0.0

    def test_celda_vacia(self):
        assert _get_correct_percent("", "A") == 0.0


# ─────────────────────────────────────────────────────────────────────────
# _es_tabla_preguntas — regresión del bug "Matemática Diagnóstico nunca
# carga" (sept-2026): camelot funde el encabezado de la columna N° de
# pregunta con el de la columna N° OA en las tablas de Matemática, y el
# texto resultante queda abreviado "N° \npreg." en vez de "N° \npregunta"
# (que sí trae Lectura). El patrón viejo solo aceptaba la forma completa.
# ─────────────────────────────────────────────────────────────────────────


class TestEsTablaPreguntas:
    def test_header_lectura_forma_completa(self):
        df = pd.DataFrame(
            [
                ["N° \npregunta", "N° OA\n(1º básico)", "Tipo de texto", "Eje", "Indicador", "% respuestas"],
                ["1", "2", "Narración", "Interpretar", "Infieren", "A: 10%"],
            ]
        )
        assert _es_tabla_preguntas(df) is True

    def test_header_matematica_abreviado_preg(self):
        """Antes del fix, esta tabla (formato real de Matemática) NO se
        reconocía como la tabla de preguntas y el step fallaba con
        'camelot no encontró ninguna tabla...' en el 100% de los PDF de
        Matemática."""
        df = pd.DataFrame(
            [
                [
                    "N° \nN° \nNivel \nEje temático\npreg.\nOA\nOA", "", "", "",
                    "Habilidad", "Indicador de \nevaluación",
                    "N° OA basales \n% respuestas\n3° básico", "",
                ],
                ["1", "2", "3", "Números", "Contar", "Cuenta hasta 10", "1", "A: 10%"],
            ]
        )
        assert _es_tabla_preguntas(df) is True

    def test_header_sin_columna_pregunta_no_matchea(self):
        df = pd.DataFrame(
            [
                ["Nivel", "Logro", "Curso", "", "", "% respuestas"],
                ["1", "2", "3", "4", "5", "6"],
            ]
        )
        assert _es_tabla_preguntas(df) is False

    def test_shape_invalida_no_matchea(self):
        df = pd.DataFrame([["N° \npregunta", "% respuestas"]])
        assert _es_tabla_preguntas(df) is False

    def test_header_sin_respuestas_no_matchea(self):
        df = pd.DataFrame(
            [
                ["N° \npregunta", "N° OA", "Tipo", "Eje", "Habilidad", "Indicador"],
                ["1", "2", "3", "4", "5", "6"],
            ]
        )
        assert _es_tabla_preguntas(df) is False


# ─────────────────────────────────────────────────────────────────────────
# _detectar_paginas_tabla_preguntas — regresión del bug "hito Cierre
# nunca carga" (sept-2026): los informes de Cierre no siempre numeran la
# sección "N. Resultados por pregunta" como Diagnóstico/Intermedio.
# Se usan PDF sintéticos (fitz.open() en blanco, sin datos reales) para
# no depender de archivos del cliente.
# ─────────────────────────────────────────────────────────────────────────


def _crear_pdf_sintetico(tmp_path, paginas: list[str]) -> str:
    """Crea un PDF mínimo con una página de texto por entrada de `paginas`."""
    import fitz

    doc = fitz.open()
    for texto in paginas:
        page = doc.new_page()
        page.insert_text((50, 50), texto, fontsize=10)
    out = tmp_path / "sintetico.pdf"
    doc.save(str(out))
    doc.close()
    return str(out)


needs_fitz = pytest.mark.skipif(
    not _fitz_disponible(), reason="fitz/PyMuPDF no instalado"
)


@needs_fitz
class TestDetectarPaginasSintetico:
    def test_formato_numerado_diagnostico(self, tmp_path):
        """Formato clásico Diagnóstico/Intermedio: sección numerada."""
        paginas = [
            "1\nEn este informe encontrará:\n1. Resultados del curso\n2. Resultados por pregunta",
            "2\nResultados del curso",
            "3\n3. Resultados por pregunta\nN° \npregunta\n...",
            "4\n...continúa tabla...",
            "5\n4. Resultados por estudiante\n...",
        ]
        pdf = _crear_pdf_sintetico(tmp_path, paginas)
        rango = _detectar_paginas_tabla_preguntas(pdf)
        assert rango == "3-4"

    def test_formato_cierre_matematica_sin_numero(self, tmp_path):
        """Cierre Matemática: encabezado 'Resultados por pregunta' SIN el
        número de sección delante (antes del fix no matcheaba nada)."""
        paginas = [
            "1\nEvaluación de Cierre",
            "2\nGráfico eje temático",
            "3\nResultados por pregunta\nLa Tabla 1 muestra...\nN° \npreg.\n...",
            "4\n...continúa tabla...",
            "5\nResultados por estudiante\n...",
        ]
        pdf = _crear_pdf_sintetico(tmp_path, paginas)
        rango = _detectar_paginas_tabla_preguntas(pdf)
        assert rango == "3-4"

    def test_formato_cierre_lectura_solo_titulo_tabla(self, tmp_path):
        """Cierre Lectura (1° básico): no hay encabezado de sección
        dedicado, solo el título de la tabla ('Tabla N. Resultados del
        curso en cada pregunta...'). Además el cuerpo del informe la
        menciona antes, a mitad de oración ('consulte la Tabla 1...'):
        esa mención NO debe disparar el inicio (por eso el ancla exige
        salto de línea justo antes de 'Tabla')."""
        paginas = [
            "1\nEvaluación de Cierre",
            "2\nPara profundizar consulte la Tabla 1. Resultados del curso en cada pregunta de Comprensión lectora más adelante.",
            "3\nTabla 1. Resultados del curso en cada pregunta de Comprensión lectora\nN° \npregunta\n...",
            "4\n...continúa tabla...",
            "5\n2. Resultados por estudiante\n...",
        ]
        pdf = _crear_pdf_sintetico(tmp_path, paginas)
        rango = _detectar_paginas_tabla_preguntas(pdf)
        assert rango == "3-4"

    def test_sin_seccion_lanza_valueerror(self, tmp_path):
        paginas = ["1\nPortada", "2\nSin la sección que buscamos"]
        pdf = _crear_pdf_sintetico(tmp_path, paginas)
        with pytest.raises(ValueError, match="Resultados por pregunta"):
            _detectar_paginas_tabla_preguntas(pdf)


# ─────────────────────────────────────────────────────────────────────────
# Step registrado en STEP_MAPPING (sigue siendo válido tras port)
# ─────────────────────────────────────────────────────────────────────────


def test_step_registrado_en_pipeline_mapping():
    from backend.rgenerator.tooling.pipeline_tools import STEP_MAPPING
    assert "RunDIAPDFExtraction" in STEP_MAPPING


def test_se_puede_instanciar_sin_args_para_carga_dinamica():
    """El runner instancia con `**params`; debe aceptar kwargs vacíos."""
    step = RunDIAPDFExtraction()
    assert step.name == "RunDIAPDFExtraction"


def test_input_key_no_resolvable_lanza():
    from types import SimpleNamespace
    ctx = SimpleNamespace(
        inputs={}, artifacts={}, params={},
        last_artifact_key=None, last_step=None,
    )
    step = RunDIAPDFExtraction()
    with pytest.raises(ValueError, match="input_key"):
        step.run(ctx)


def test_sin_pdfs_devuelve_df_vacio_no_lanza(tmp_path):
    """Si el input_key no tiene PDFs, el step pasa y produce df vacío."""
    from types import SimpleNamespace
    ctx = SimpleNamespace(
        inputs={"preguntas_pdf": []},
        artifacts={},
        params={},
        last_artifact_key=None,
        last_step=None,
    )
    step = RunDIAPDFExtraction(input_key="preguntas_pdf")
    step.run(ctx)
    assert "df_preguntas_preguntas_pdf" in ctx.artifacts
    assert ctx.artifacts["df_preguntas_preguntas_pdf"].empty


# ─────────────────────────────────────────────────────────────────────────
# Helpers con PDF real (skip si no hay)
# ─────────────────────────────────────────────────────────────────────────


@needs_real_pdf_fitz
class TestPdfRealHelpers:
    @pytest.fixture
    def pdf_path(self):
        return str(_real_pdf_disponible())

    def test_detectar_paginas_devuelve_rango_valido(self, pdf_path):
        rango = _detectar_paginas_tabla_preguntas(pdf_path)
        assert "-" in rango
        start, end = map(int, rango.split("-"))
        assert 1 <= start <= end

    def test_extraer_establecimiento_y_curso(self, pdf_path):
        est, curso, mapa = _extraer_establecimiento_y_curso(pdf_path)
        # Establecimiento y curso no deben ser None ni vacíos
        assert est and est.strip()
        assert curso and curso.strip()
        # El mapa debe tener las 7 etiquetas esperadas
        assert "Establecimiento:" in mapa
        assert "Curso:" in mapa


# ─────────────────────────────────────────────────────────────────────────
# Step completo con PDF real (smoke test pesado)
# ─────────────────────────────────────────────────────────────────────────


@needs_real_pdf_camelot
def test_run_completo_con_pdf_real():
    """Smoke test: corre el step contra un PDF real DIA y verifica
    estructura del output. Pesado (camelot + análisis de píxeles), por
    eso marcado @slow. Skipea si no hay PDF disponible.
    """
    from types import SimpleNamespace

    pdf = _real_pdf_disponible()
    ctx = SimpleNamespace(
        inputs={"pdfs": [str(pdf)]},
        artifacts={},
        params={},
        last_artifact_key=None,
        last_step=None,
    )
    step = RunDIAPDFExtraction(input_key="pdfs")
    step.run(ctx)

    df = ctx.artifacts[step.output_key]
    assert not df.empty, "El step debe producir filas"
    assert list(df.columns) == [
        "N Pregunta", "Eje Temático", "Habilidad",
        "Indicador", "% respuestas", "Logro",
        "Establecimiento", "Curso",
    ]
    # Logro debe estar en [0, 1]
    logros = pd.to_numeric(df["Logro"], errors="coerce").dropna()
    assert (logros >= 0).all() and (logros <= 1).all()
