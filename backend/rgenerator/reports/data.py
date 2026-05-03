"""Carga de DataFrames desde la DB del proyecto.

Reemplaza el `pd.read_excel("...")` del flujo LaTeX por consultas SQL al
modelo `metric_data`. Devuelve DataFrames con las columnas EXACTAS que las
funciones de charts.py / tables.py esperan ("Curso", "Logro", "Nivel",
"Pregunta", "Eje Temático", "Habilidad", etc.).

Convenciones:

- Las columnas en la DB pueden tener nombres distintos según `column_roles`
  del Indicator. Esta capa traduce los roles a los nombres canónicos que
  espera el motor de informes.
- Filtros recibidos como dict (asignatura, año, hito, mes, ...) se aplican
  vía pandas después de la carga (más simple y barato para volúmenes < 100k).
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy.orm import Session

from backend.models import Indicator, Metric, MetricData


def cargar_dataframes_indicator(
    db: Session,
    indicator_id: int,
    org_id: int,
    filtros: dict | None = None,
) -> dict[str, pd.DataFrame]:
    """Carga las métricas asociadas a un Indicator y devuelve {role: DataFrame}.

    Por convención del proyecto, los Indicators de evaluación tienen 2
    métricas asociadas:
        - "estudiantes" → 1 fila por alumno (df_estudiantes)
        - "preguntas" → 1 fila por respuesta a pregunta (df_preguntas)

    Args:
        db: sesión SQLAlchemy.
        indicator_id: ID del Indicator.
        org_id: ID de la organización (multi-tenant).
        filtros: dict de filtros adicionales aplicados a TODOS los dfs
            antes de devolverlos (ej {"Asignatura": "LENGUAJE", "Año": 2025}).
            Solo se aplican los keys que existan como columna.

    Returns:
        Dict con keys "estudiantes" y "preguntas" (cuando ambas métricas
        existen) y valores DataFrames listos para charts.py / tables.py.

    Raises:
        ValueError: si el Indicator no existe o no tiene métricas asociadas.

    NOTA: implementación inicial. Revisar después si conviene streamear
    metric_data por chunks para volúmenes grandes (>100k filas).
    """
    indicator = (
        db.query(Indicator)
        .filter(Indicator.id_indicator == indicator_id, Indicator.org_id == org_id)
        .first()
    )
    if not indicator:
        raise ValueError(f"Indicator {indicator_id} no existe en org {org_id}")

    # TODO: implementar esta función iterando indicator.metrics o usando
    # IndicatorMetric (tabla pivot) para conocer qué métricas pertenecen
    # al indicator y con qué rol ("estudiantes" / "preguntas").
    raise NotImplementedError(
        "cargar_dataframes_indicator: pendiente de implementar la "
        "consulta a IndicatorMetric + MetricData. Por ahora el orquestador "
        "puede recibir DataFrames directos."
    )
