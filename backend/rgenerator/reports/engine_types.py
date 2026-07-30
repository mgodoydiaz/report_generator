"""Resolución del `engine_type` de un indicador.

Fuente ÚNICA de la regla "campo explícito > heurística por nombre", usada
tanto por `GET /api/indicators/{id}/report-options` como por
`POST /api/reports/custom/{nombre}` para decidir qué informes
especializados aplican a un indicador.

La heurística por nombre es retrocompatibilidad pura: antes de existir la
columna `Indicator.report_engine_type`, el frontend adivinaba el tipo desde
el nombre del indicador. Se mantiene para no romper indicadores viejos, pero
la fuente de verdad es el campo.
"""
from __future__ import annotations

from typing import Optional


def inferir_engine_type(nombre: str) -> Optional[str]:
    """Adivina el engine_type desde el nombre del indicador. None si no matchea."""
    n = (nombre or "").lower()
    if "panguipulli" in n:
        return "simce_panguipulli"
    if "simce" in n:
        return "simce"
    if "dia" in n:
        return "dia"
    if "idel" in n or "pdl" in n:
        return "pdl_idel"
    return None


def resolver_engine_type(indicator) -> tuple[Optional[str], Optional[str]]:
    """(engine_type, origen) para un `Indicator`.

    Returns:
        Tupla `(engine_type, origen)` donde origen es "campo" si vino de
        `report_engine_type`, "inferido" si salió del nombre, y None si no
        se pudo determinar (indicador genérico).
    """
    explicito = getattr(indicator, "report_engine_type", None) or None
    if explicito:
        return explicito, "campo"
    inferido = inferir_engine_type(getattr(indicator, "name", "") or "")
    return (inferido, "inferido") if inferido else (None, None)
