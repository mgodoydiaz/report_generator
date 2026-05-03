"""Steps de extracción de datos desde PDFs.

Hoy contiene solo el stub de `RunDIAPDFExtraction`. La implementación
real requiere portar literal las funciones del script artesanal del
cliente (`script_consolidar_DIA.py`) — camelot para tablas, fitz para
texto y análisis de píxeles para detección de respuestas en negrita.
Esas funciones fueron depuradas durante meses contra el formato exacto
de los PDFs de Agencia DIA y no se deben reescribir desde cero.

Ver `docs/desarrollo/script_dia_artesanal_referencia.md` para el plan
detallado de migración.
"""
from __future__ import annotations

from typing import Optional

from .step import Step


class RunDIAPDFExtraction(Step):
    """Extrae el cuadro 'Resultados por pregunta' de los PDFs Agencia DIA.

    **Estado: stub no implementado.** Llamar a `run()` lanza
    `NotImplementedError`. El step queda registrado en `STEP_MAPPING`
    para reservar el nombre y permitir que pipelines de referencia lo
    incluyan, pero no debe usarse en pipelines productivos hasta que
    esté completo.

    Implementación pendiente — debe portar del script artesanal:
        - `detectar_paginas_tabla_preguntas(pdf)` → rango "start-end"
        - `extraer_establecimiento_y_curso(pdf)` → (str, str, dict)
        - `extract_bold_alternatives(pdf, df, ...)` → lista de winners
        - `region_darkness(page, bbox, zoom)` → float
        - `get_correct_percent(cell_text, alt_correcta)` → float

    Parámetros futuros esperados:
        input_key: clave en ctx.inputs con los PDFs por curso.
        output_key: clave del DataFrame resultante (1 fila por pregunta).
        metadata_cells_overrides: opcional para sobre-escribir el
            establecimiento/curso si vienen mal en el PDF.
    """

    def __init__(
        self,
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
    ):
        super().__init__(
            name="RunDIAPDFExtraction",
            requires=[input_key] if input_key else [],
            produces=[output_key] if output_key else [],
        )
        self.input_key = input_key
        self.output_key = output_key

    def run(self, ctx):
        raise NotImplementedError(
            "RunDIAPDFExtraction aún no está implementado. "
            "Ver docs/desarrollo/script_dia_artesanal_referencia.md y "
            "ROADMAP B6b para el plan de migración. Se requiere portar "
            "literal las funciones camelot+fitz del script artesanal del "
            "cliente — no reescribir desde cero."
        )
