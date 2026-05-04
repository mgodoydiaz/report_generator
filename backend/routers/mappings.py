"""Router /api/mappings — CRUD de tablas de mapeo (B10).

Cada mapeo vive como un Spec con type='Mapeo'. El MappingConfig se
guarda en `metadata_` (single config por spec, sin charts_list/tables_list).

Endpoints:
    GET    /api/mappings/                 lista resumen
    POST   /api/mappings/                 crear
    GET    /api/mappings/{id}             leer detalle
    PUT    /api/mappings/{id}             actualizar
    DELETE /api/mappings/{id}             borrar
    POST   /api/mappings/{id}/duplicate   clonar
    POST   /api/mappings/preview          aplicar config a una lista de valores
                                          (para el editor live, sin persistir)
    GET    /api/mappings/{id}/resolved    devuelve el config listo para aplicar
                                          (lo usa el backend interno cuando un
                                          pipeline referencia mapping_id)
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Spec, User
from backend.schemas_mapping import (
    MappingConfig,
    MappingCreate,
    MappingPreviewRequest,
    MappingPreviewResult,
    MappingSummary,
    MappingUpdate,
)

router = APIRouter(prefix="/api/mappings", tags=["mappings"])


SPEC_TYPE = "Mapeo"


# ─────────────────────────────────────────────────────────────────────────
# Helpers de persistencia
# ─────────────────────────────────────────────────────────────────────────


def _now_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _parse_meta(spec: Spec) -> Dict[str, Any]:
    try:
        return json.loads(spec.metadata_ or "{}")
    except Exception:
        return {}


def _spec_to_config(spec: Spec) -> Optional[MappingConfig]:
    meta = _parse_meta(spec)
    cfg_raw = meta.get("mapping_config")
    if not cfg_raw:
        return None
    try:
        return MappingConfig(**cfg_raw)
    except Exception:
        return None


def _spec_to_summary(spec: Spec) -> MappingSummary:
    meta = _parse_meta(spec)
    cfg = meta.get("mapping_config") or {}
    n_entries = len(cfg.get("ranges") or []) + len(cfg.get("mapping") or {})
    return MappingSummary(
        id_spec=spec.id_spec,
        name=spec.name,
        description=meta.get("description", ""),
        is_draft=meta.get("is_draft", True),
        kind=cfg.get("kind"),
        n_entries=n_entries,
        input_field_type=cfg.get("input_field_type"),
        updated_at=meta.get("updated_at", ""),
    )


def _spec_to_full(spec: Spec) -> Dict[str, Any]:
    meta = _parse_meta(spec)
    return {
        "id_spec": spec.id_spec,
        "name": spec.name,
        "description": meta.get("description", ""),
        "is_draft": meta.get("is_draft", True),
        "updated_at": meta.get("updated_at", ""),
        "config": meta.get("mapping_config"),
    }


def _get_spec_or_404(db: Session, mapping_id: int, org_id: int) -> Spec:
    spec = db.query(Spec).filter(
        Spec.id_spec == mapping_id,
        Spec.org_id == org_id,
        Spec.type == SPEC_TYPE,
    ).first()
    if not spec:
        raise HTTPException(status_code=404, detail=f"Mapeo {mapping_id} no encontrado")
    return spec


# ─────────────────────────────────────────────────────────────────────────
# Aplicación del mapeo a un valor (puro, sin DB)
# ─────────────────────────────────────────────────────────────────────────


def apply_mapping(cfg: MappingConfig, value: Any) -> MappingPreviewResult:
    """Aplica el mapeo a un valor. Reusable por:
        - el endpoint /preview
        - el resolver interno que injecta el mapeo en derived_fields
    """
    raw_value = value
    matched = False
    label: Optional[str] = None

    if cfg.kind == "range":
        # Coerce a float; si falla, no clasifica.
        try:
            v = float(value) if value is not None and value != "" else None
        except (TypeError, ValueError):
            v = None
        if v is not None:
            for r in cfg.ranges:
                ok = True
                if r.min is not None:
                    if cfg.match == "right_inclusive":
                        if not (v > float(r.min)): ok = False
                    else:
                        if not (v >= float(r.min)): ok = False
                if ok and r.max is not None:
                    if cfg.match == "left_inclusive":
                        if not (v < float(r.max)): ok = False
                    else:
                        if not (v <= float(r.max)): ok = False
                if ok:
                    label = r.label
                    matched = True
                    break

    elif cfg.kind == "discrete":
        # Aplicar extract si existe
        s = "" if value is None else str(value)
        if cfg.extract:
            if cfg.extract.split is not None:
                parts = s.split(cfg.extract.split)
                s = parts[cfg.extract.index] if cfg.extract.index < len(parts) else ""
            elif cfg.extract.regex:
                try:
                    m = re.search(cfg.extract.regex, s)
                    s = m.group(0) if m else ""
                except re.error:
                    s = ""
        raw_value = s
        if cfg.case_insensitive:
            mapping_norm = {k.lower(): v for k, v in cfg.mapping.items()}
            label = mapping_norm.get(s.lower())
        else:
            label = cfg.mapping.get(s)
        matched = label is not None

    if label is None:
        label = cfg.default

    return MappingPreviewResult(
        value=value,
        raw_value=raw_value,
        label=label,
        matched=matched,
    )


def resolve_mapping_to_lookup_config(db: Session, org_id: int, mapping_id: int) -> Dict[str, Any]:
    """Resuelve un mapping_id al config inline esperado por
    derived_fields_engine (apply_lookup_range / apply_lookup_dict).

    Devuelve el dict que se inyecta en el config del kind para ser
    procesado por el engine. NO incluye `kind` ni `name` ni `value_field`
    — esos vienen del config del kind original.

    Raises HTTPException si el mapping no existe.
    """
    spec = _get_spec_or_404(db, mapping_id, org_id)
    cfg = _spec_to_config(spec)
    if not cfg:
        raise HTTPException(400, f"Mapeo {mapping_id} sin configuración válida")

    if cfg.kind == "range":
        return {
            "ranges": [r.model_dump() for r in cfg.ranges],
            "match": cfg.match,
            "default": cfg.default,
        }
    elif cfg.kind == "discrete":
        out = {
            "mapping": cfg.mapping,
            "case_insensitive": cfg.case_insensitive,
            "default": cfg.default,
        }
        if cfg.extract:
            out["extract"] = cfg.extract.model_dump(exclude_none=True)
        return out
    raise HTTPException(400, f"Mapeo {mapping_id} con kind no soportado: {cfg.kind}")


# ─────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────


@router.get("/", response_model=List[MappingSummary])
async def list_mappings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    specs = db.query(Spec).filter(
        Spec.org_id == user.org_id, Spec.type == SPEC_TYPE
    ).order_by(Spec.id_spec.desc()).all()
    return [_spec_to_summary(s) for s in specs]


@router.post("/")
async def create_mapping(
    payload: MappingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    meta = {
        "description": payload.description,
        "is_draft": payload.is_draft,
        "updated_at": _now_str(),
        "mapping_config": payload.config.model_dump(),
    }
    spec = Spec(
        name=payload.name,
        type=SPEC_TYPE,
        metadata_=json.dumps(meta, ensure_ascii=False),
        charts_list="[]",
        tables_list="[]",
        org_id=user.org_id,
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return {"status": "success", "id_spec": spec.id_spec}


@router.get("/{mapping_id}")
async def get_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, mapping_id, user.org_id)
    return _spec_to_full(spec)


@router.put("/{mapping_id}")
async def update_mapping(
    mapping_id: int,
    payload: MappingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, mapping_id, user.org_id)
    meta = _parse_meta(spec)
    if payload.name is not None:
        spec.name = payload.name
    if payload.description is not None:
        meta["description"] = payload.description
    if payload.is_draft is not None:
        meta["is_draft"] = payload.is_draft
    if payload.config is not None:
        meta["mapping_config"] = payload.config.model_dump()
    meta["updated_at"] = _now_str()
    spec.metadata_ = json.dumps(meta, ensure_ascii=False)
    db.commit()
    db.refresh(spec)
    return {"status": "success", "id_spec": spec.id_spec}


@router.delete("/{mapping_id}")
async def delete_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, mapping_id, user.org_id)
    db.delete(spec)
    db.commit()
    return {"status": "success", "message": f"Mapeo {mapping_id} eliminado"}


@router.post("/{mapping_id}/duplicate")
async def duplicate_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    spec = _get_spec_or_404(db, mapping_id, user.org_id)
    new = Spec(
        name=spec.name + " (Copia)",
        type=spec.type,
        metadata_=spec.metadata_,
        charts_list=spec.charts_list,
        tables_list=spec.tables_list,
        org_id=spec.org_id,
    )
    db.add(new)
    db.commit()
    db.refresh(new)
    return {"status": "success", "id_spec": new.id_spec}


@router.post("/preview", response_model=List[MappingPreviewResult])
async def preview_mapping(
    payload: MappingPreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Aplica un MappingConfig (en body) a una lista de valores y
    devuelve `[{value, raw_value, label, matched}]`. Sin persistencia."""
    return [apply_mapping(payload.config, v) for v in payload.values]


@router.get("/{mapping_id}/resolved")
async def get_resolved_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Devuelve el dict listo para inyectar como config a un kind
    `lookup_range` o `lookup_dict` de derived_fields. Util para el
    frontend del editor de pipelines (mostrar qué se va a aplicar)
    y debugging."""
    return resolve_mapping_to_lookup_config(db, user.org_id, mapping_id)
