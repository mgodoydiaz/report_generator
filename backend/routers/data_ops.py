"""Router /api/data-ops — operaciones masivas sobre metric_data (B10).

Endpoints:
    POST /api/data-ops/replace       buscar/reemplazar valores en una columna
    POST /api/data-ops/recalculate   re-aplicar un mapeo a una columna
                                     (lee source_column, escribe target_column)
    POST /api/data-ops/distinct      lista valores únicos de una columna
                                     (helper para el editor)

Todos los endpoints aceptan `dry_run` (default true) que devuelve qué
cambiaría sin aplicar. Una vez confirmado, el cliente vuelve a llamar
con dry_run=false.

Resolución de columna: si el nombre coincide con un field del meta_json
de la métrica, opera sobre value. Si coincide con una dimensión
registrada, opera sobre dimensions_json. Si está en ambas, prioriza
field.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Dimension, Metric, MetricData, MetricDimension, Spec, User
from backend.routers.mappings import apply_mapping
from backend.schemas_mapping import MappingConfig

router = APIRouter(prefix="/api/data-ops", tags=["data-ops"])


# Cantidad máxima de filas-cambio a devolver en el preview.
SAMPLE_LIMIT = 25


# ─────────────────────────────────────────────────────────────────────────
# Helpers compartidos
# ─────────────────────────────────────────────────────────────────────────


def _parse_value(value: Any, data_type: str) -> Any:
    """Parsea el campo .value de MetricData a su forma estructurada
    (dict si data_type=object, valor crudo si simple)."""
    if data_type == "object":
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return {}
        return {}
    return value


def _parse_dims(dims: Any) -> Dict[str, Any]:
    if isinstance(dims, dict):
        return dims
    if isinstance(dims, str):
        try:
            return json.loads(dims)
        except Exception:
            return {}
    return {}


def _get_metric_or_404(db: Session, metric_id: int, org_id: int) -> Metric:
    m = db.query(Metric).filter(
        Metric.id_metric == metric_id, Metric.org_id == org_id
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail=f"Métrica {metric_id} no encontrada")
    return m


def _get_meta_fields(metric: Metric) -> List[Dict[str, Any]]:
    try:
        meta = json.loads(metric.meta_json or "{}") if isinstance(metric.meta_json, str) else (metric.meta_json or {})
    except Exception:
        meta = {}
    return meta.get("fields", []) or []


def _resolve_column(db: Session, metric: Metric, column_name: str) -> Dict[str, Any]:
    """Resuelve column_name a 'field' o 'dimension'. Devuelve:
        {"kind": "field"|"dimension", "id_dimension": int|None, "type": str}
    """
    fields = _get_meta_fields(metric)
    for f in fields:
        if f.get("name") == column_name:
            return {"kind": "field", "id_dimension": None, "type": f.get("type", "str")}

    # Buscar entre las dimensiones de la métrica
    links = db.query(MetricDimension).filter(
        MetricDimension.id_metric == metric.id_metric
    ).all()
    dim_ids = [lnk.id_dimension for lnk in links]
    if dim_ids:
        dims = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all()
        for d in dims:
            if d.name == column_name:
                return {"kind": "dimension", "id_dimension": d.id_dimension, "type": d.data_type}

    raise HTTPException(
        status_code=400,
        detail=f"Columna '{column_name}' no es ni field ni dimension de la métrica {metric.id_metric}",
    )


def _read_cell(record: MetricData, metric: Metric, col_info: Dict[str, Any], column_name: str) -> Any:
    """Lee el valor actual de una celda (field o dimension)."""
    if col_info["kind"] == "field":
        val_obj = _parse_value(record.value, metric.data_type)
        return val_obj.get(column_name)
    else:
        dims = _parse_dims(record.dimensions_json)
        return dims.get(str(col_info["id_dimension"]))


def _write_cell(record: MetricData, metric: Metric, col_info: Dict[str, Any], column_name: str, new_value: Any):
    """Escribe el valor en la celda y reserializa el JSON correspondiente."""
    if col_info["kind"] == "field":
        val_obj = _parse_value(record.value, metric.data_type)
        val_obj[column_name] = new_value
        record.value = json.dumps(val_obj, ensure_ascii=False)
    else:
        dims = _parse_dims(record.dimensions_json)
        dims[str(col_info["id_dimension"])] = (
            None if new_value is None else str(new_value)
        )
        record.dimensions_json = json.dumps(dims, ensure_ascii=False)


def _coerce_to_field_type(value: Any, field_type: str) -> Any:
    """Castea un valor al tipo declarado del field."""
    if value is None or value == "":
        return None
    try:
        if field_type == "int":
            return int(float(value))
        if field_type == "float":
            return float(value)
        if field_type == "bool":
            if isinstance(value, str):
                return value.strip().lower() in ("true", "1", "yes", "sí", "si")
            return bool(value)
    except (TypeError, ValueError):
        return value
    return str(value) if not isinstance(value, str) else value


# ─────────────────────────────────────────────────────────────────────────
# Endpoint: distinct (helper para popular el dropdown del editor)
# ─────────────────────────────────────────────────────────────────────────


class DistinctRequest(BaseModel):
    metric_id: int
    column_name: str
    limit: int = 200


@router.post("/distinct")
async def distinct_values(
    payload: DistinctRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    metric = _get_metric_or_404(db, payload.metric_id, user.org_id)
    col_info = _resolve_column(db, metric, payload.column_name)
    rows = db.query(MetricData).filter(MetricData.id_metric == metric.id_metric).all()
    seen: Dict[str, int] = {}
    for r in rows:
        v = _read_cell(r, metric, col_info, payload.column_name)
        key = "" if v is None else str(v)
        seen[key] = seen.get(key, 0) + 1
    items = sorted(seen.items(), key=lambda kv: -kv[1])[: payload.limit]
    return {
        "kind": col_info["kind"],
        "n_total_rows": len(rows),
        "n_distinct": len(seen),
        "values": [{"value": k, "count": v} for k, v in items],
    }


# ─────────────────────────────────────────────────────────────────────────
# Endpoint: replace (find & replace estilo Excel)
# ─────────────────────────────────────────────────────────────────────────


class ReplaceRequest(BaseModel):
    metric_id: int
    column_name: str
    find: str
    replace: str
    match_type: Literal["exact", "contains", "regex"] = "exact"
    case_sensitive: bool = False
    dry_run: bool = True


@router.post("/replace")
async def replace_values(
    payload: ReplaceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    metric = _get_metric_or_404(db, payload.metric_id, user.org_id)
    col_info = _resolve_column(db, metric, payload.column_name)

    rows = db.query(MetricData).filter(MetricData.id_metric == metric.id_metric).all()

    # Compile regex / preparar match
    flags = 0 if payload.case_sensitive else re.IGNORECASE
    rx = None
    if payload.match_type == "regex":
        try:
            rx = re.compile(payload.find, flags)
        except re.error as e:
            raise HTTPException(400, f"Regex inválida: {e}")

    def _matches(v: Any) -> bool:
        if v is None:
            return False
        s = str(v)
        if payload.match_type == "exact":
            if payload.case_sensitive:
                return s == payload.find
            return s.lower() == payload.find.lower()
        if payload.match_type == "contains":
            if payload.case_sensitive:
                return payload.find in s
            return payload.find.lower() in s.lower()
        # regex
        return bool(rx.search(s))

    def _new_value(old: Any) -> Any:
        if old is None:
            return None
        s = str(old)
        if payload.match_type == "exact":
            return payload.replace
        if payload.match_type == "contains":
            if payload.case_sensitive:
                return s.replace(payload.find, payload.replace)
            # case-insensitive replace
            return re.sub(re.escape(payload.find), payload.replace, s, flags=flags)
        return rx.sub(payload.replace, s)

    sample = []
    n_matched = 0
    n_would_change = 0
    for r in rows:
        old = _read_cell(r, metric, col_info, payload.column_name)
        if not _matches(old):
            continue
        n_matched += 1
        new = _new_value(old)
        if str(new) == str(old):
            continue
        n_would_change += 1
        if len(sample) < SAMPLE_LIMIT:
            sample.append({
                "id_data": r.id_data,
                "before": str(old),
                "after": str(new),
            })
        if not payload.dry_run:
            # Cast al tipo del field si aplica
            cast_val = new
            if col_info["kind"] == "field":
                cast_val = _coerce_to_field_type(new, col_info["type"])
            _write_cell(r, metric, col_info, payload.column_name, cast_val)

    if not payload.dry_run:
        db.commit()

    return {
        "n_total_rows": len(rows),
        "n_matched": n_matched,
        "n_would_change": n_would_change,
        "sample_changes": sample,
        "applied": not payload.dry_run,
    }


# ─────────────────────────────────────────────────────────────────────────
# Endpoint: recalculate (aplicar mapeo a una columna source → target)
# ─────────────────────────────────────────────────────────────────────────


class RecalculateRequest(BaseModel):
    metric_id: int
    source_column: str       # columna de entrada (puede ser field o dim)
    target_column: str       # columna de salida (debe ser field)
    mapping_id: int          # id del Spec type='Mapeo'
    dry_run: bool = True


def _load_mapping_config(db: Session, org_id: int, mapping_id: int) -> MappingConfig:
    spec = db.query(Spec).filter(
        Spec.id_spec == mapping_id,
        Spec.org_id == org_id,
        Spec.type == "Mapeo",
    ).first()
    if not spec:
        raise HTTPException(404, f"Mapeo {mapping_id} no encontrado")
    raw = spec.metadata_
    meta = json.loads(raw) if isinstance(raw, str) else (raw or {})
    cfg_raw = meta.get("mapping_config")
    if not cfg_raw:
        raise HTTPException(400, f"Mapeo {mapping_id} sin config")
    return MappingConfig(**cfg_raw)


@router.post("/recalculate")
async def recalculate_column(
    payload: RecalculateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    metric = _get_metric_or_404(db, payload.metric_id, user.org_id)
    src_info = _resolve_column(db, metric, payload.source_column)

    # target debe ser field; si no existe, se acepta crearlo on-the-fly
    fields = _get_meta_fields(metric)
    field_names = {f.get("name") for f in fields}
    if payload.target_column not in field_names:
        # Create-on-write: el field no existe en meta_json, se agrega al
        # value de cada row pero no al schema declarado. El usuario puede
        # luego registrarlo en metric.meta_json desde /metrics si quiere
        # exponerlo en otros editores. Aquí solo emitimos warning.
        pass

    target_info = {"kind": "field", "id_dimension": None,
                   "type": next((f.get("type", "str") for f in fields if f.get("name") == payload.target_column), "str")}

    cfg = _load_mapping_config(db, user.org_id, payload.mapping_id)
    rows = db.query(MetricData).filter(MetricData.id_metric == metric.id_metric).all()

    sample = []
    n_processed = 0
    n_changed = 0
    n_default = 0
    for r in rows:
        n_processed += 1
        src_val = _read_cell(r, metric, src_info, payload.source_column)
        result = apply_mapping(cfg, src_val)
        new_label = result.label
        if not result.matched and new_label is not None:
            n_default += 1
        old_target = _read_cell(r, metric, target_info, payload.target_column)
        if str(old_target) == str(new_label):
            continue
        n_changed += 1
        if len(sample) < SAMPLE_LIMIT:
            sample.append({
                "id_data": r.id_data,
                "source": str(src_val),
                "before": str(old_target) if old_target is not None else "",
                "after": str(new_label) if new_label is not None else "",
                "matched": result.matched,
            })
        if not payload.dry_run:
            _write_cell(r, metric, target_info, payload.target_column, new_label)

    if not payload.dry_run:
        db.commit()

    return {
        "n_total_rows": len(rows),
        "n_processed": n_processed,
        "n_changed": n_changed,
        "n_default_used": n_default,
        "sample_changes": sample,
        "applied": not payload.dry_run,
        "mapping": {
            "id": payload.mapping_id,
            "kind": cfg.kind,
        },
    }
