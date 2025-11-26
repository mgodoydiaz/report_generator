"""
Atajos para exponer utilidades del subpaquete tooling.
Permite importar funciones directamente desde `rgenerator.tooling`.
"""

from . import etl_tools, plot_tools, report_tools, constants  # noqa: F401
from .constants import formato_informe_generico, indice_alfabetico
from .etl_tools import (
    agregar_columnas_dataframe,
    limpiar_columnas,
    calcular_avance_promedio,
    crear_tabla,
)
from .plot_tools import (
    grafico_barras_promedio_por,
    boxplot_valor_por_curso,
    alumnos_por_nivel_cualitativo,
    alumnos_por_nivel_curso_y_mes,
    valor_promedio_agrupado_por,
)
from .report_tools import (
    crear_tabla_estadistica_por_pregunta,
    df_a_latex_loop,
    img_to_latex,
    resumen_estadistico_basico,
    tabla_logro_por_alumno,
    tabla_logro_por_pregunta,
)

__all__ = [
    # constantes
    "formato_informe_generico",
    "indice_alfabetico",
    # ETL
    "agregar_columnas_dataframe",
    "limpiar_columnas",
    "calcular_avance_promedio",
    "crear_tabla",
    # plotting
    "grafico_barras_promedio_por",
    "boxplot_valor_por_curso",
    "alumnos_por_nivel_cualitativo",
    "alumnos_por_nivel_curso_y_mes",
    "valor_promedio_agrupado_por",
    # reportes
    "crear_tabla_estadistica_por_pregunta",
    "df_a_latex_loop",
    "img_to_latex",
    "resumen_estadistico_basico",
    "tabla_logro_por_alumno",
    "tabla_logro_por_pregunta",
    # módulos completos (por compatibilidad)
    "etl_tools",
    "plot_tools",
    "report_tools",
    "constants",
]
