"""Filtrado compartido de dimensiones para dashboards e informes.

Fuente de verdad ÚNICA de la semántica de filtros {id_dimension: valor}:
el dashboard (/api/results) manda listas multi-valor; los llamados
programáticos pueden mandar escalares. Cualquier motor de informes debe
filtrar con `matches` para que el PDF/Word refleje exactamente lo que el
usuario ve en pantalla (QA maestro P0-1, hallazgo informes H1).
"""
from __future__ import annotations


def matches(actual, expected) -> bool:
    """True si `actual` satisface el filtro `expected`.

    - `expected` escalar → igualdad como string.
    - `expected` lista/tupla/set → pertenencia (IN) como strings.
    - lista vacía → sin restricción (True).
    """
    if isinstance(expected, (list, tuple, set)):
        allowed = {str(v) for v in expected}
        if not allowed:
            return True
        return str(actual) in allowed
    return str(actual) == str(expected)
