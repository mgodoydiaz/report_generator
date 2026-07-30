"""PLANTILLA — copiar este archivo para crear un informe custom nuevo.

Empieza con `_`, por lo tanto el registro lo IGNORA: no aparece en la UI ni
se puede invocar. Para publicar un informe nuevo:

    1. cp _ejemplo.py mi_informe.py
    2. Ajustar LABEL / DESCRIPCION / ENGINE_TYPES / FILENAME.
    3. Implementar `generar(...)` devolviendo bytes.
    4. Listo — aparece solo en GET /api/indicators/{id}/report-options
       (grupo "especializados") y se invoca con
       POST /api/reports/custom/mi_informe.

Ver README.md de esta carpeta para el detalle del contrato.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

# ── Metadata (la lee el registro; LABEL y DESCRIPCION son obligatorias) ──

LABEL = "Informe de ejemplo"
DESCRIPCION = "Plantilla de referencia para crear un informe custom nuevo."

# "pdf" | "word" — determina el Content-Type y la extensión por defecto.
FORMATO = "pdf"

# Engine types del indicador a los que aplica este informe.
#   ["simce"]  → solo indicadores con report_engine_type == "simce"
#   None       → aplica a TODOS los indicadores
ENGINE_TYPES: list[str] | None = None

# Dimensiones temporales que el informe necesita para no mezclar
# aplicaciones. El frontend usa esta lista para exigir el filtro antes de
# habilitar el botón. Lista vacía = el informe se arregla solo.
REQUIERE_FILTRO_TEMPORAL: list[str] = []

# True si el informe cubre UNA sola asignatura. Cuando los datos del
# indicador traen ≥2 asignaturas distintas, report-options publica el campo
# `asignatura` en la card (para que la UI muestre el selector) y el informe
# no se puede generar sin fijarla: mezclar asignaturas hace que cada alumno
# se cuente una vez por prueba rendida. Ver `reports/asignatura.py`.
REQUIERE_ASIGNATURA = False

# Nombre del archivo descargado. Opcional: default `informe_<nombre>.pdf`.
FILENAME = "informe_ejemplo.pdf"


def generar(
    db: Session,
    *,
    indicator_id: int,
    org_id: int,
    filtros: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> bytes:
    """Construye el informe y devuelve sus bytes.

    Args:
        db: sesión SQLAlchemy — SIEMPRE filtrar por `org_id` en las queries.
        indicator_id: indicador desde el que se pidió el informe.
        org_id: organización del usuario autenticado (multi-tenancy).
        filtros: {nombre_columna: valor | [valores]} elegidos en la UI —
            incluye la asignatura cuando `REQUIERE_ASIGNATURA` es True.
        params: parámetros libres del informe (los define cada informe).
        overrides: overrides de esquema/branding. El pie izquierdo se
            rellena con el nombre de la organización si no viene definido
            (ver `dispatch_v2.aplicar_pie_organizacion`).

    Returns:
        Bytes del archivo (PDF o DOCX según FORMATO).

    Raises:
        ValueError: cuando faltan datos o filtros → el endpoint devuelve 400
            con el mensaje tal cual, así que escribirlo pensando en el
            usuario final.
    """
    # Patrón habitual: cargar los DataFrames del indicador y delegar en un
    # constructor del motor v2.
    #
    #   from ..data import cargar_dataframes_indicator
    #   from ..dispatch_v2 import aplicar_pie_organizacion
    #   from .. import runtime
    #
    #   dataframes = cargar_dataframes_indicator(
    #       db, indicator_id=indicator_id, org_id=org_id, filtros=filtros or {}
    #   )
    #   overrides = aplicar_pie_organizacion(db, org_id, overrides)
    #   return runtime.construir_pdf("mi_tipo", dataframes, overrides=overrides)
    raise NotImplementedError("Implementar generar() antes de renombrar sin '_'")
