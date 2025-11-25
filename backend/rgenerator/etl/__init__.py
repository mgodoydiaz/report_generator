"""
ETL
Funciones para reconocer cursos, extraer valores desde PDFs/XLS y normalizar niveles de logro.
"""


from .consolidar_dia import (
    reconocer_cursos,
    region_darkness,
    extract_bold_alternatives,
    get_correct_percent,
    get_curso_establecimiento_from_pdf,
    reemplazar_nivel_logro,
    calcular_nivel_logro,
    obtener_nivel,
    extraer_establecimiento_y_curso,
)

__all__ = [
    "reconocer_cursos",
    "region_darkness",
    "extract_bold_alternatives",
    "get_correct_percent",
    "get_curso_establecimiento_from_pdf",
    "reemplazar_nivel_logro",
    "calcular_nivel_logro",
    "obtener_nivel",
    "extraer_establecimiento_y_curso",
]

# Versión del subpaquete (actualiza al hacer releases)
__version__ = "0.1.0"

# Logger del paquete (configúralo desde la app principal)
import logging
logger = logging.getLogger(__name__)