"""Carga de DataFrames desde la DB del proyecto.

Reemplaza el `pd.read_excel("...")` del flujo LaTeX por consultas SQL al
modelo `metric_data`. Devuelve DataFrames con columnas en el formato que
los esquemas (simce/dia) declaran ("Curso", "Logro", "Eje Temático", ...).

Estrategia:
    1) Iterar `IndicatorMetric` para conocer las metrics asociadas.
    2) Para cada metric, cargar su `MetricData` y construir 1 row por record:
       - value field(s): parseado de `value` JSON (con `meta_json.fields` para
         multi-valor).
       - dimension fields: parseados de `dimensions_json` y resueltos vía
         `Dimension.name`.
    3) Renombrar columnas `_logro` → "Logro", aplicando overrides para
       tildes y mayúsculas (ej `_eje_tematico` → "Eje Temático").
    4) Detectar el rol de cada metric por su nombre ("estudiantes" /
       "preguntas") y devolver dict `{rol: DataFrame}`.

Si una metric no matchea un rol conocido, queda como `metric_<id>`.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from backend.models import (
    Dimension,
    Indicator,
    IndicatorMetric,
    Metric,
    MetricData,
    MetricDimension,
)


# ─────────────────────────────────────────────────────────────────────────
# Conversión de nombres DB → nombres canónicos del LaTeX
# ─────────────────────────────────────────────────────────────────────────

def _to_field_name(name: str) -> str:
    """Normaliza un nombre de columna a `_field_key`.

    Replica `report_steps._to_field_name` para mantener compatibilidad con
    `column_roles` del Indicator. 'Eje Temático' → '_eje_tematico'.
    """
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9_]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return f"_{s}"


# Overrides explícitos para columnas que requieren mayúsculas o tildes que
# Title Case no recupera. Si una columna nueva falta, agregar acá.
_COLUMN_NAME_OVERRIDES = {
    "_eje_tematico": "Eje Temático",
    "_nivel_de_logro": "NIVEL DE LOGRO",
    "_nivel_logro": "Nivel Logro",
    "_n_pregunta": "N° Pregunta",
    "_numero_de_lista": "N° Lista",
    "_numero_pregunta": "N° Pregunta",
    "_nombre_del_estudiante": "Estudiante",
    "_nombre": "Nombre",
    "_anio": "Año",
    "_ano": "Año",
    "_año": "Año",
}


def _humanize_column(field_key: str) -> str:
    """`_eje_tematico` → 'Eje Temático' (vía override) o 'Eje Tematico' (Title)."""
    if field_key in _COLUMN_NAME_OVERRIDES:
        return _COLUMN_NAME_OVERRIDES[field_key]
    if field_key.startswith("_"):
        field_key = field_key[1:]
    return field_key.replace("_", " ").title()


# ─────────────────────────────────────────────────────────────────────────
# Detección de rol de la metric (estudiantes / preguntas / otro)
# ─────────────────────────────────────────────────────────────────────────

def _role_from_metric_name(name: str) -> str:
    """'Resultados DIA por estudiante' → 'estudiantes'; 'por Pregunta' → 'preguntas'.

    Para IDEL/PDL/Woodcock/Cálculo Veloz/Fluidez Lectora donde la única
    metric reúne todo (1 fila por aplicación al estudiante), se devuelve
    "estudiantes" como rol unificado.
    """
    n = (name or "").lower()
    if "pregunta" in n:
        return "preguntas"
    if any(k in n for k in ("estudiante", "alumno", "idel", "pdl", "woodcock",
                            "fluidez", "velocidad", "calculo", "cálculo")):
        return "estudiantes"
    return "otros"


# ─────────────────────────────────────────────────────────────────────────
# Carga de records desde MetricData (por metric individual)
# ─────────────────────────────────────────────────────────────────────────

def _records_for_metric(
    db: Session,
    metric: Metric,
    org_id: int,
    filtros: dict[str, Any] | None = None,
) -> list[dict]:
    """Construye lista de records para UNA metric, aplicando filtros opcionales.

    Args:
        db: sesión SQLAlchemy.
        metric: Metric ORM instance.
        org_id: para multi-tenancy.
        filtros: dict {nombre_columna_humano: valor} aplicado AL FINAL,
            después de construir cada record (ej {"Asignatura": "LENGUAJE"}).

    Returns:
        Lista de dicts con keys `_field_name` (todavía con prefijo `_` —
        el renombrado a humano se hace en el caller con `pd.DataFrame.rename`).
    """
    # 1) Meta del value (puede tener múltiples fields)
    meta_fields = []
    try:
        mj = json.loads(metric.meta_json) if isinstance(metric.meta_json, str) else (metric.meta_json or {})
        meta_fields = mj.get("fields", [])
    except Exception:
        meta_fields = []

    # 2) Dimensiones de la metric
    dim_links = db.query(MetricDimension).filter(MetricDimension.id_metric == metric.id_metric).all()
    dim_ids = [lnk.id_dimension for lnk in dim_links]
    dims_by_id: dict[int, Dimension] = {}
    if dim_ids:
        dims = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all()
        dims_by_id = {d.id_dimension: d for d in dims}

    # 3) MetricData filtrado por org
    data_rows = db.query(MetricData).filter(
        MetricData.id_metric == metric.id_metric,
        MetricData.org_id == org_id,
    ).all()

    records: list[dict] = []
    for row in data_rows:
        try:
            dims_json = json.loads(row.dimensions_json) if isinstance(row.dimensions_json, str) else (row.dimensions_json or {})
        except Exception:
            dims_json = {}

        rec: dict[str, Any] = {}

        # Value fields
        raw_val = row.value
        if meta_fields:
            try:
                parsed = json.loads(raw_val) if isinstance(raw_val, str) else raw_val
                if isinstance(parsed, dict):
                    for f in meta_fields:
                        fname = _to_field_name(f["name"])
                        rec[fname] = parsed.get(f["name"])
                else:
                    key = _to_field_name(meta_fields[0]["name"]) if meta_fields else _to_field_name(metric.name)
                    rec[key] = parsed
            except Exception:
                key = _to_field_name(metric.name)
                rec[key] = raw_val
        else:
            key = _to_field_name(metric.name)
            try:
                rec[key] = float(raw_val) if raw_val is not None else None
            except (ValueError, TypeError):
                rec[key] = raw_val

        # Dimension fields (key = nombre de la dimensión, no su id)
        for did in dim_ids:
            dim = dims_by_id.get(did)
            if dim:
                dkey = _to_field_name(dim.name)
                rec[dkey] = dims_json.get(str(did))

        records.append(rec)

    # 4) Filtros (después de armar records — operan sobre los nombres humanos)
    if filtros:
        # Convertir filtros a sus _field_name equivalentes
        filtros_field = {_to_field_name(k): v for k, v in filtros.items()}
        records = [
            r for r in records
            if all(str(r.get(fk, "")) == str(fv) for fk, fv in filtros_field.items())
        ]

    return records


# ─────────────────────────────────────────────────────────────────────────
# Punto de entrada principal
# ─────────────────────────────────────────────────────────────────────────

def cargar_dataframes_indicator(
    db: Session,
    indicator_id: int,
    org_id: int,
    filtros: dict[str, Any] | None = None,
) -> dict[str, pd.DataFrame]:
    """Carga DataFrames listos para charts.py / tables.py para un Indicator.

    Args:
        db: sesión SQLAlchemy.
        indicator_id: ID del Indicator.
        org_id: ID de la organización.
        filtros: dict opcional {nombre_columna_humano: valor} aplicado a
            ambos DFs antes de devolverlos. Ejemplos:
                {"Asignatura": "LENGUAJE"}        # SIMCE solo lenguaje
                {"Año": 2025, "Hito": "CIERRE"}   # DIA hito específico

    Returns:
        Dict con keys:
          - "estudiantes": DataFrame de la metric de estudiantes (o
            primera metric con ese rol).
          - "preguntas": DataFrame de la metric de preguntas (si existe).
          - "metric_<id>": DataFrames de metrics que no caen en los
            roles conocidos.

        Las columnas tienen nombres canónicos del LaTeX ("Curso", "Logro",
        "Eje Temático", "NIVEL DE LOGRO", etc.).

    Raises:
        ValueError: si el Indicator no existe o no tiene metrics asociadas.
    """
    indicator = (
        db.query(Indicator)
        .filter(Indicator.id_indicator == indicator_id, Indicator.org_id == org_id)
        .first()
    )
    if not indicator:
        raise ValueError(f"Indicator {indicator_id} no existe en org {org_id}")

    metric_links = db.query(IndicatorMetric).filter(
        IndicatorMetric.id_indicator == indicator_id
    ).all()
    if not metric_links:
        raise ValueError(f"Indicator {indicator_id} no tiene metrics asociadas")

    result: dict[str, pd.DataFrame] = {}
    for link in metric_links:
        metric = db.query(Metric).filter(Metric.id_metric == link.id_metric).first()
        if not metric:
            continue

        records = _records_for_metric(db, metric, org_id, filtros)
        if not records:
            continue

        df = pd.DataFrame(records)
        # Renombrar columnas: _campo → "Campo" (con override para tildes)
        df.columns = [_humanize_column(c) for c in df.columns]

        role = _role_from_metric_name(metric.name)
        if role == "otros":
            role = f"metric_{metric.id_metric}"

        # Si dos metrics caen en el mismo rol (improbable pero posible),
        # la segunda lleva sufijo numérico para no pisar.
        key = role
        n = 2
        while key in result:
            key = f"{role}_{n}"
            n += 1
        result[key] = df

    return result
