"""Excepciones compartidas por los motores de informes.

Viven en un módulo propio (y no en `dispatch_v2.py`) porque las levantan
capas distintas del stack:

    - `reports/dispatch_v2.py`      (motor v2, informes oficiales)
    - `reports/runtime.py`         (orquestador de secciones v2)
    - `reports/{tipo}/crear_informe.py`
    - `core/report_steps.py`       (motor v1 weasyprint por layout)

y todas ellas deben producir el MISMO error de dominio para que los
routers lo traduzcan a un HTTP consistente:

    TipoNoSoportado                 → 404
    DatosInsuficientes / ValueError → 400
    cualquier otra                  → 500

`dispatch_v2` re-exporta ambas clases para no romper los imports
históricos (`from ...dispatch_v2 import DatosInsuficientes`).
"""
from __future__ import annotations


class TipoNoSoportado(LookupError):
    """El tipo de informe pedido no existe en el motor → 404."""


class DatosInsuficientes(ValueError):
    """No hay datos/filtros suficientes para construir el informe → 400.

    Se usa tanto para "falta un filtro temporal" como para "los filtros
    seleccionados dejaron el dataset sin filas". El mensaje SIEMPRE debe
    ser accionable para el usuario final: qué filtro sobra o falta.
    """


def mensaje_sin_datos(descripcion_filtros: str = "") -> str:
    """Mensaje accionable estándar para un dataset vacío tras filtrar.

    Args:
        descripcion_filtros: filtros aplicados en texto legible
            ("Hito: INTERMEDIO · Año: 2026"). Vacío si no hubo filtros.

    Returns:
        Texto para el `detail` del 400.

    Ejemplo:
        >>> mensaje_sin_datos("Hito: INTERMEDIO · Año: 2026")
        'Los filtros seleccionados no tienen datos: Hito: INTERMEDIO · Año: 2026. Revisa la combinación (ese cruce puede no existir en los datos cargados) y vuelve a intentar.'
    """
    if descripcion_filtros:
        return (
            f"Los filtros seleccionados no tienen datos: {descripcion_filtros}. "
            "Revisa la combinación (ese cruce puede no existir en los datos "
            "cargados) y vuelve a intentar."
        )
    return (
        "El indicador no tiene datos cargados para generar este informe. "
        "Carga datos en sus métricas y vuelve a intentar."
    )
