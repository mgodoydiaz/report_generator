"""
routers/ingest.py — Ingesta programática por API externa (W1 PARTE B).

Auth: API key (`X-API-Key`), NO JWT de usuario. Toda query filtra por
`ctx.org_id`, que sale SIEMPRE de la key autenticada (`ApiKeyContext`,
`backend/auth.py`), nunca de un parámetro del request — es la garantía de
tenancy dura del diseño (`docs/planes/w1_ingesta_api.md`).

Endpoints:
    POST /api/ingest/metrics/{metric_id}/data       scope ingest:write
    GET  /api/ingest/metrics/{metric_id}/schema     scope metrics:read
    POST /api/ingest/pipelines/{pipeline_id}/trigger scope ingest:write

Cada operación de escritura queda registrada en `IngestLog` (auditoría +
idempotencia vía header `Idempotency-Key`).
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auditing import client_ip, make_metric_data
from backend.auth import ApiKeyContext, require_scope
from backend.config import UPLOADS_DIR
from backend.database import get_db
from backend.logging_config import get_logger
from backend.models import Dimension, IngestLog, Metric, MetricDimension, Pipeline
from backend.rgenerator.core.pares_nombre import (
    completar_pares_nombre,
    pares_nombre_normalizado,
)
from backend.routers.pipelines import _INPUT_KEY_RE, MAX_UPLOAD_BYTES, _get_pipeline_config_from_db
from backend.routers.tables import invalidate_metric_df_cache
from backend.rgenerator.tooling.pipeline_tools import PipelineRunner

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


# ─────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────

class IngestRecord(BaseModel):
    value: Any = None
    dimensions: Dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    records: List[IngestRecord]
    dry_run: bool = False


class IngestRowError(BaseModel):
    index: int
    reason: str


class IngestResponse(BaseModel):
    rows_ok: int
    rows_failed: int
    errors: List[IngestRowError]
    dry_run: bool


# ─────────────────────────────────────────────────────────────────────────
# Helpers — resolución/validación de métrica (imitan metrics.py/data_ops.py)
# ─────────────────────────────────────────────────────────────────────────

def _get_metric_or_404(db: Session, metric_id: int, org_id: int) -> Metric:
    metric = db.query(Metric).filter(
        Metric.id_metric == metric_id,
        Metric.org_id == org_id,
    ).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Métrica no encontrada")
    return metric


def _get_pipeline_or_404(db: Session, pipeline_id: int, org_id: int) -> Pipeline:
    pipeline = db.query(Pipeline).filter(
        Pipeline.pipeline_id == pipeline_id,
        Pipeline.org_id == org_id,
    ).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline no encontrado")
    return pipeline


def _parse_meta_json(raw) -> dict:
    if isinstance(raw, str) and raw:
        try:
            return json.loads(raw)
        except Exception:
            return {}
    if isinstance(raw, dict):
        return raw
    return {}


def _expected_fields(metric: Metric) -> List[Dict[str, Any]]:
    """Fields esperados en `value`.

    Para métricas `data_type="object"` son los `meta_json.fields` (múltiples
    subcampos tipados). Para métricas simples (int/float/str/bool) hay un
    único campo implícito: el propio valor de la métrica.
    """
    if metric.data_type == "object":
        meta = _parse_meta_json(metric.meta_json)
        return meta.get("fields", []) or []
    return [{"name": metric.name, "type": metric.data_type}]


def _dim_name_to_id(db: Session, metric: Metric) -> Dict[str, int]:
    links = db.query(MetricDimension).filter(MetricDimension.id_metric == metric.id_metric).all()
    dim_ids = [lnk.id_dimension for lnk in links]
    if not dim_ids:
        return {}
    dims = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all()
    return {d.name: d.id_dimension for d in dims}


def _coerce_scalar(value: Any, type_: str) -> Tuple[bool, Any]:
    """Intenta coercionar `value` (ya deserializado de JSON) al `type_`
    esperado (int/float/str/bool). Devuelve (ok, valor_coercido)."""
    if value is None:
        return False, None

    if type_ == "int":
        if isinstance(value, bool):
            return False, None
        if isinstance(value, int):
            return True, value
        if isinstance(value, float) and value.is_integer():
            return True, int(value)
        if isinstance(value, str):
            try:
                return True, int(value.strip())
            except ValueError:
                return False, None
        return False, None

    if type_ == "float":
        if isinstance(value, bool):
            return False, None
        if isinstance(value, (int, float)):
            return True, float(value)
        if isinstance(value, str):
            try:
                return True, float(value.strip())
            except ValueError:
                return False, None
        return False, None

    if type_ == "bool":
        if isinstance(value, bool):
            return True, value
        if isinstance(value, int) and value in (0, 1):
            return True, bool(value)
        if isinstance(value, str):
            low = value.strip().lower()
            if low in ("true", "1", "si", "sí", "yes"):
                return True, True
            if low in ("false", "0", "no"):
                return True, False
        return False, None

    # "str" (default): cualquier escalar es representable como texto; los
    # compuestos (dict/list) no.
    if isinstance(value, (dict, list)):
        return False, None
    return True, str(value)


def _validate_record(
    metric: Metric,
    fields: List[Dict[str, Any]],
    dim_name_to_id: Dict[str, int],
    record: IngestRecord,
) -> Tuple[bool, Optional[str], Dict[str, str], Optional[str]]:
    """Valida un record contra los fields/dimensiones de la métrica.

    Devuelve (ok, value_final_serializado, dimensions_json, reason_si_falla).
    """
    dims_json: Dict[str, str] = {}
    for dim_name, dim_value in (record.dimensions or {}).items():
        dim_id = dim_name_to_id.get(dim_name)
        if dim_id is None:
            return False, None, {}, f"dimensión desconocida: '{dim_name}'"
        dims_json[str(dim_id)] = None if dim_value is None else str(dim_value)

    if metric.data_type == "object":
        if not isinstance(record.value, dict):
            return False, None, {}, "value debe ser un objeto para una métrica de tipo 'object'"
        field_names = {f.get("name") for f in fields}
        unknown = [k for k in record.value.keys() if k not in field_names]
        if unknown:
            return False, None, {}, f"campos desconocidos: {unknown}"
        val_obj: Dict[str, Any] = {}
        for f in fields:
            fname = f.get("name")
            ftype = f.get("type", "str")
            if fname not in record.value:
                continue
            ok, coerced = _coerce_scalar(record.value[fname], ftype)
            if not ok:
                return False, None, {}, f"campo '{fname}' inválido: se esperaba tipo {ftype}"
            val_obj[fname] = coerced
        final_value = json.dumps(val_obj, ensure_ascii=False)
    else:
        ftype = metric.data_type
        ok, coerced = _coerce_scalar(record.value, ftype)
        if not ok:
            return False, None, {}, f"value inválido: se esperaba tipo {ftype}"
        final_value = str(coerced)

    return True, final_value, dims_json, None


def _hash_response(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _log_to_response(prev: IngestLog) -> IngestResponse:
    """Reconstruye una respuesta equivalente a partir de un `IngestLog`
    previo, para reintentos idempotentes. El detalle por fila (`errors`) no
    se persiste — solo los conteos — así que en un replay viene vacío."""
    return IngestResponse(
        rows_ok=prev.rows_ok or 0,
        rows_failed=prev.rows_failed or 0,
        errors=[],
        dry_run=(prev.status == "dry_run"),
    )


# ─────────────────────────────────────────────────────────────────────────
# POST /api/ingest/metrics/{metric_id}/data
# ─────────────────────────────────────────────────────────────────────────

@router.post("/metrics/{metric_id}/data", response_model=IngestResponse)
def ingest_metric_data(
    metric_id: int,
    body: IngestRequest,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    ctx: ApiKeyContext = Depends(require_scope("ingest:write")),
):
    metric = _get_metric_or_404(db, metric_id, ctx.org_id)
    endpoint_name = f"metrics/{metric_id}/data"

    # Idempotencia: un `(org_id, idempotency_key)` ya visto devuelve el
    # resultado previo SIN re-insertar.
    if idempotency_key:
        prev = db.query(IngestLog).filter(
            IngestLog.org_id == ctx.org_id,
            IngestLog.idempotency_key == idempotency_key,
        ).first()
        if prev:
            return _log_to_response(prev)

    dim_name_to_id = _dim_name_to_id(db, metric)
    # Pares X/X_Norm de la métrica: si el integrador manda solo una de las
    # dos dimensiones del par, la otra se completa antes de insertar (misma
    # red de seguridad que `SaveToMetric` en pipelines y que el import de
    # /values). Ver `backend/rgenerator/core/pares_nombre.py`.
    pares_nombre = pares_nombre_normalizado(dim_name_to_id)
    fields = _expected_fields(metric)

    errors: List[dict] = []
    to_insert = []
    rows_ok = 0

    for idx, record in enumerate(body.records):
        ok, final_value, dims_json, reason = _validate_record(metric, fields, dim_name_to_id, record)
        if not ok:
            errors.append({"index": idx, "reason": reason})
            continue
        if pares_nombre:
            completar_pares_nombre(dims_json, pares_nombre)
        rows_ok += 1
        if not body.dry_run:
            to_insert.append(make_metric_data(
                metric_id=metric_id,
                value=final_value,
                dimensions=dims_json,
                org_id=ctx.org_id,
                user_id=None,
                via="api_direct",
                ip=client_ip(request),
            ))

    rows_failed = len(errors)

    if body.dry_run:
        log_status = "dry_run"
    elif rows_ok > 0 and rows_failed == 0:
        log_status = "success"
    elif rows_ok > 0:
        log_status = "success"  # éxito parcial: se insertaron filas válidas
    else:
        log_status = "error"

    response_body = {
        "rows_ok": rows_ok,
        "rows_failed": rows_failed,
        "errors": errors,
        "dry_run": body.dry_run,
    }

    if not body.dry_run and to_insert:
        db.add_all(to_insert)

    log_row = IngestLog(
        org_id=ctx.org_id,
        api_key_id=ctx.api_key_id,
        idempotency_key=idempotency_key,
        endpoint=endpoint_name,
        status=log_status,
        rows_ok=rows_ok,
        rows_failed=rows_failed,
        response_hash=_hash_response(response_body),
    )
    db.add(log_row)

    try:
        db.commit()
    except IntegrityError:
        # Carrera: otro request con el mismo (org_id, idempotency_key) ganó
        # la inserción del log entre nuestro SELECT y este commit. Tratamos
        # como reintento idempotente: no reinsertamos, devolvemos lo que
        # quedó persistido.
        db.rollback()
        if idempotency_key:
            prev = db.query(IngestLog).filter(
                IngestLog.org_id == ctx.org_id,
                IngestLog.idempotency_key == idempotency_key,
            ).first()
            if prev:
                return _log_to_response(prev)
        logger.error("IntegrityError inesperado en ingest_metric_data", exc_info=True)
        raise HTTPException(status_code=409, detail="Conflicto de idempotencia")

    if not body.dry_run and to_insert:
        invalidate_metric_df_cache(metric_id)

    return response_body


# ─────────────────────────────────────────────────────────────────────────
# GET /api/ingest/metrics/{metric_id}/schema
# ─────────────────────────────────────────────────────────────────────────

@router.get("/metrics/{metric_id}/schema")
def get_metric_schema(
    metric_id: int,
    db: Session = Depends(get_db),
    ctx: ApiKeyContext = Depends(require_scope("metrics:read")),
):
    metric = _get_metric_or_404(db, metric_id, ctx.org_id)
    fields = _expected_fields(metric)

    links = db.query(MetricDimension).filter(MetricDimension.id_metric == metric_id).all()
    dim_ids = [lnk.id_dimension for lnk in links]
    dims = (
        db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all()
        if dim_ids else []
    )

    return {
        "metric_id": metric.id_metric,
        "name": metric.name,
        "data_type": metric.data_type,
        "fields": [{"name": f.get("name"), "type": f.get("type", "str")} for f in fields],
        "dimensions": [{"name": d.name, "type": d.data_type} for d in dims],
    }


# ─────────────────────────────────────────────────────────────────────────
# POST /api/ingest/pipelines/{pipeline_id}/trigger
#
# Reusa la sanitización de uploads de W0 (`_INPUT_KEY_RE`, `MAX_UPLOAD_BYTES`,
# basename) tal como `backend/routers/pipelines.py::upload_pipeline_files`.
#
# Ejecución SÍNCRONA: no hay cola real (fuera de alcance de W1, ver
# docs/planes/w1_ingesta_api.md). Cada llamada crea un `PipelineRunner`
# nuevo (sin estado en `ACTIVE_RUNNERS`, que está keyed por user_id de
# sesión JWT y no aplica a auth por API key) y corre `run_all()`:
#   - Si termina -> status "completed".
#   - Si un step pide más archivos (`RequestUserFiles` con specs faltantes)
#     -> status "needs_review": el integrador debe volver a llamar al
#     endpoint con el `input_key` faltante (los archivos ya subidos quedan
#     en disco, `RequestUserFiles` los descubre en la siguiente corrida).
#   - Si falla -> status "failed".
# ─────────────────────────────────────────────────────────────────────────

@router.post("/pipelines/{pipeline_id}/trigger")
async def trigger_pipeline(
    pipeline_id: int,
    input_key: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    ctx: ApiKeyContext = Depends(require_scope("ingest:write")),
):
    _get_pipeline_or_404(db, pipeline_id, ctx.org_id)

    if not _INPUT_KEY_RE.match(input_key or ""):
        raise HTTPException(status_code=400, detail=f"input_key inválido: {input_key!r}")

    upload_dir = UPLOADS_DIR / str(pipeline_id) / input_key
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_root = upload_dir.resolve()

    saved_files: List[str] = []
    for file in files:
        safe_name = Path(file.filename or "").name.strip()
        if not safe_name or safe_name in (".", ".."):
            raise HTTPException(status_code=400, detail=f"Nombre de archivo inválido: {file.filename!r}")
        file_path = (upload_dir / safe_name).resolve()
        if upload_root not in file_path.parents:
            raise HTTPException(status_code=400, detail=f"Nombre de archivo inválido: {file.filename!r}")

        size = 0
        excede = False
        with open(file_path, "wb") as buffer:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    excede = True
                    break
                buffer.write(chunk)
        if excede:
            file_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail=f"Archivo '{safe_name}' supera el máximo de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
            )
        saved_files.append(safe_name)

    endpoint_name = f"pipelines/{pipeline_id}/trigger"
    config = _get_pipeline_config_from_db(pipeline_id, ctx.org_id, db)

    status_out = "failed"
    rows_ok = 0
    rows_failed = 0
    detail: Optional[str] = None

    if not config:
        detail = "El pipeline no tiene configuración"
    else:
        try:
            runner = PipelineRunner(config, pipeline_id=pipeline_id, db=db, org_id=ctx.org_id, user_id=None)
            results = runner.run_all()
            last = results[-1] if results else {}
            if last.get("status") == "waiting_input":
                status_out = "needs_review"
                detail = (
                    "El pipeline requiere más archivos/input. Volvé a llamar a este "
                    "endpoint con el input_key correspondiente (ver "
                    "docs/planes/w1_ingesta_api.md, sección 'Fuera de alcance')."
                )
            else:
                status_out = "completed"
                rows_ok = 1
        except Exception as e:  # noqa: BLE001 — se audita y no se propaga el detalle interno
            db.rollback()
            status_out = "failed"
            rows_failed = 1
            detail = "Error interno ejecutando el pipeline"
            logger.error("Error ejecutando pipeline vía ingest trigger (pipeline_id=%s)", pipeline_id, exc_info=True)

    log_row = IngestLog(
        org_id=ctx.org_id,
        api_key_id=ctx.api_key_id,
        idempotency_key=None,
        endpoint=endpoint_name,
        status="success" if status_out == "completed" else "error",
        rows_ok=rows_ok,
        rows_failed=rows_failed,
    )
    db.add(log_row)
    db.commit()
    db.refresh(log_row)

    response = {
        "job_id": log_row.id,
        "status": status_out,
        "files": saved_files,
    }
    if detail:
        response["detail"] = detail
    return response
