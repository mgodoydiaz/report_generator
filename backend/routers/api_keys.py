"""
routers/api_keys.py — Gestión de API keys de la organización (W1).

Auth: JWT admin-only (`require_admin`). Todo filtrado por `org_id` del
usuario del token. El secreto en claro se devuelve UNA sola vez, en la
respuesta de creación; luego solo se expone el `prefix`.

La ingesta real (consumo de las keys) vive en `backend/routers/ingest.py`
(PARTE B) usando la dependency `get_org_from_api_key` / `require_scope` de
`backend/auth.py`.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api_keys import (
    deserializar_scopes,
    generar_api_key,
    serializar_scopes,
)
from backend.auth import require_admin
from backend.database import get_db
from backend.logging_config import get_logger
from backend.models import ApiKey, User

logger = get_logger(__name__)

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])

# Scopes reconocidos por el sistema. Rechazamos lo desconocido al crear para
# que un typo no genere una key que nunca autorizará nada.
SCOPES_VALIDOS = frozenset({"ingest:write", "metrics:read"})


# ─── Schemas ─────────────────────────────────────────────────
class ApiKeyCreate(BaseModel):
    name: str
    scopes: List[str] = []
    expires_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    """Metadata de una key — nunca incluye el secreto."""
    id: int
    name: str
    prefix: str
    scopes: List[str]
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    revoked: bool


class ApiKeyCreateResponse(ApiKeyResponse):
    """Respuesta de creación: incluye el secreto en claro UNA sola vez."""
    secret: str


def _to_response(k: ApiKey) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=k.id,
        name=k.name,
        prefix=k.prefix,
        scopes=deserializar_scopes(k.scopes),
        created_at=k.created_at,
        expires_at=k.expires_at,
        last_used_at=k.last_used_at,
        revoked=k.revoked,
    )


# ─── Endpoints ───────────────────────────────────────────────

@router.get("/", response_model=List[ApiKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Lista las API keys de la organización. Nunca expone el secreto."""
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.org_id == admin.org_id)
        .order_by(ApiKey.id)
        .all()
    )
    return [_to_response(k) for k in keys]


@router.post("/", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    body: ApiKeyCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Crea una API key. Devuelve el secreto en claro UNA sola vez."""
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")

    desconocidos = [s for s in body.scopes if s not in SCOPES_VALIDOS]
    if desconocidos:
        raise HTTPException(
            status_code=400,
            detail=f"Scopes inválidos: {desconocidos}. Válidos: {sorted(SCOPES_VALIDOS)}",
        )

    secreto_claro, prefix, key_hash = generar_api_key()

    key = ApiKey(
        org_id=admin.org_id,
        name=body.name.strip(),
        prefix=prefix,
        key_hash=key_hash,
        scopes=serializar_scopes(body.scopes),
        created_by_user_id=admin.id,
        expires_at=body.expires_at,
        revoked=False,
    )
    db.add(key)
    db.commit()
    db.refresh(key)

    # Log sin el secreto — solo prefix.
    logger.info(
        "API key creada id=%s prefix=%s org=%s por user=%s",
        key.id, key.prefix, key.org_id, admin.id,
    )

    resp = _to_response(key)
    return ApiKeyCreateResponse(**resp.model_dump(), secret=secreto_claro)


@router.delete("/{key_id}")
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Revoca (soft) una API key de la organización."""
    key = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.org_id == admin.org_id)
        .first()
    )
    if not key:
        raise HTTPException(status_code=404, detail="API key no encontrada")

    key.revoked = True
    db.commit()
    logger.info("API key revocada id=%s prefix=%s org=%s", key.id, key.prefix, key.org_id)

    return {"status": "success", "detail": f"API key '{key.name}' revocada"}
