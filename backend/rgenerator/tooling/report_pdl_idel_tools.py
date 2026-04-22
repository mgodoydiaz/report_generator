"""
Adapter backend para el informe PDL IDEL-Woodcock.

Reutiliza las funciones de renderizado de `scripts/report_pdl_idel.py` pero
reemplaza la capa de acceso a datos (antes psycopg2 directo) por SQLAlchemy +
filtrado multi-tenant por org_id, y escribe el PDF a BytesIO para servirlo
desde el endpoint.

NOTA: El script CLI sigue funcionando tal cual — comparte las funciones puras
con este módulo. Sólo la entrada (carga de datos) difiere.
"""
from __future__ import annotations

import io
import json
from typing import Optional, Dict, Any

import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from sqlalchemy.orm import Session

from backend.models import MetricData

# Reusamos funciones puras y constantes del script CLI (side-effect-free tras
# el refactor: scripts/__init__.py existe y el script ya no lee DATABASE_URL
# en import time).
from scripts.report_pdl_idel import (
    DEFAULT_METRIC_ID,
    SUBPRUEBAS_ORDER,
    render_all_pages,
)


# ── IDs de dimensión hardcodeados (específicos de la métrica IDEL-Woodcock) ──
# Mismos índices que usa el script CLI (ver load_data en scripts/report_pdl_idel.py).
# Si la metric se recrea con otros id_dimension, estos valores deben ajustarse.
DIM_ESTABLECIMIENTO = "3"
DIM_ANIO = "4"
DIM_CURSO = "5"
DIM_RUT = "6"
DIM_NOMBRE = "7"
DIM_SUBPRUEBA = "19"
DIM_VERSION = "20"


def _load_dataframe_from_orm(
    db: Session,
    metric_id: int,
    establecimiento: Optional[str] = None,
    anio: Optional[int] = None,
    versiones: Optional[list[int]] = None,
    cursos: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Carga los MetricData de la métrica IDEL-Woodcock vía SQLAlchemy y los
    proyecta a un DataFrame con las columnas esperadas por las funciones de
    renderizado del script (puntaje, nivel, establecimiento, año, curso,
    estudiante, subprueba, version, eval_id).

    Los filtros opcionales son iguales a los del CLI — el filtrado se hace
    en memoria porque la cantidad de filas es moderada (una sola metric).
    """
    rows = db.query(MetricData).filter(MetricData.id_metric == metric_id).all()
    if not rows:
        return pd.DataFrame()

    records = []
    for r in rows:
        try:
            value = json.loads(r.value) if isinstance(r.value, str) else (r.value or {})
        except Exception:
            value = {}
        try:
            dims = json.loads(r.dimensions_json) if isinstance(r.dimensions_json, str) else (r.dimensions_json or {})
        except Exception:
            dims = {}
        records.append({
            "id_data": r.id_data,
            "puntaje": value.get("Puntaje"),
            "nivel": value.get("Nivel de Riesgo"),
            "establecimiento": dims.get(DIM_ESTABLECIMIENTO),
            "año": int(dims[DIM_ANIO]) if dims.get(DIM_ANIO) else None,
            "curso": dims.get(DIM_CURSO),
            "rut": dims.get(DIM_RUT),
            "nombre": dims.get(DIM_NOMBRE),
            "subprueba": (dims.get(DIM_SUBPRUEBA) or "").upper(),
            "version": int(dims[DIM_VERSION]) if dims.get(DIM_VERSION) else None,
        })

    df = pd.DataFrame.from_records(records)
    if df.empty:
        return df

    df["eval_id"] = df["año"].astype("Int64").astype(str) + "/v" + df["version"].astype("Int64").astype(str)
    df["puntaje"] = pd.to_numeric(df["puntaje"], errors="coerce")
    df["estudiante"] = df["nombre"]

    df = df.dropna(subset=["puntaje", "curso", "nivel", "estudiante"])
    df = df[df["subprueba"].isin(SUBPRUEBAS_ORDER)]

    if establecimiento:
        df = df[df["establecimiento"] == establecimiento]
    if anio is not None:
        df = df[df["año"] == anio]
    if versiones:
        df = df[df["version"].isin(versiones)]
    if cursos:
        df = df[df["curso"].isin(cursos)]

    return df


def _translate_filters(filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convierte los filtros del modal ({id_dimension_str: valor}) a los kwargs
    que acepta _load_dataframe_from_orm. Se ignora cualquier filtro sobre
    dimensiones desconocidas para este informe.
    """
    if not filters:
        return {}
    kwargs: Dict[str, Any] = {}
    if filters.get(DIM_ESTABLECIMIENTO):
        kwargs["establecimiento"] = str(filters[DIM_ESTABLECIMIENTO])
    if filters.get(DIM_ANIO):
        try:
            kwargs["anio"] = int(filters[DIM_ANIO])
        except (TypeError, ValueError):
            pass
    if filters.get(DIM_CURSO):
        kwargs["cursos"] = [str(filters[DIM_CURSO])]
    if filters.get(DIM_VERSION):
        try:
            kwargs["versiones"] = [int(filters[DIM_VERSION])]
        except (TypeError, ValueError):
            pass
    return kwargs


def build_pdl_idel_pdf_bytes(
    indicator,
    db: Session,
    org_id: int,
    filters: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Genera el informe PDL IDEL-Woodcock como bytes, listo para servir desde
    un Response de FastAPI.

    El metric_id se toma de indicator.pdf_layout["metric_id"] si está definido;
    si no, cae al default del script (DEFAULT_METRIC_ID = 8).
    """
    # El dispatcher del endpoint ya validó que el indicator es de org_id.
    # Multi-tenancy: las filas de MetricData heredan el org_id de su Metric,
    # que a su vez ya está bajo el Indicator validado. Si se quisiera reforzar,
    # se podría hacer un join explícito — por ahora se confía en la validación
    # del endpoint caller.
    pdf_layout = indicator.pdf_layout
    if isinstance(pdf_layout, str):
        try:
            pdf_layout = json.loads(pdf_layout)
        except Exception:
            pdf_layout = {}

    metric_id = int((pdf_layout or {}).get("metric_id") or DEFAULT_METRIC_ID)
    load_kwargs = _translate_filters(filters)

    df = _load_dataframe_from_orm(db, metric_id=metric_id, **load_kwargs)
    if df.empty:
        raise ValueError(
            "No hay datos para generar el informe PDL IDEL-Woodcock con los "
            "filtros solicitados."
        )

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        render_all_pages(pdf, df)
    return buf.getvalue()
