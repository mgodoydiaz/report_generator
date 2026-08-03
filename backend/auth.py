"""
auth.py — Autenticación JWT y utilidades de password.

Uso en routers:
    from backend.auth import get_current_user
    @router.get("/")
    def endpoint(user: User = Depends(get_current_user)): ...
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from backend.api_keys import deserializar_scopes, extraer_prefix, verificar_api_key
from backend.database import get_db
from backend.logging_config import get_logger
from backend.models import ApiKey, User

logger = get_logger(__name__)

# ─── Config ──────────────────────────────────────────────────
# Sin default: arrancar con un secreto público conocido significaría que
# cualquiera puede forjar tokens. Mismo patrón hard-fail que DATABASE_URL
# en database.py (load_dotenv ya corrió al importar backend.database).
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET no configurada. Definirla en .env (local) o en las "
        "variables del servicio (Railway → Variables). La app no arranca "
        "con un secreto por defecto."
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ─── Password helpers ────────────────────────────────────────
def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


# ─── JWT helpers ─────────────────────────────────────────────
def create_access_token(user_id: int, org_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "org_id": org_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── FastAPI dependency ──────────────────────────────────────
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extrae el usuario actual del JWT en el header Authorization."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_token(token)
    user_id = int(payload.get("sub", 0))
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o desactivado",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency: permite acceso a role=admin y a cualquier superadmin.

    El superadmin pasa aunque su `role` no sea "admin": está por encima de
    admin en toda la jerarquía. Esto replica el `_check_admin` que vivía en
    el cuerpo de organizations.py, para no degradar ese acceso al mover el
    chequeo a la firma del endpoint.
    """
    if user.role != "admin" and not getattr(user, "is_superadmin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return user


def require_editor(user: User = Depends(get_current_user)) -> User:
    """Dependency: permite escritura de dominio a admin y editor.

    `viewer` es un rol de solo lectura: puede hacer GET, previsualizar y
    descargar informes, pero no crear, modificar ni borrar. Las operaciones
    destructivas (borrado de entidades, vaciados masivos) usan `require_admin`,
    no esta dependency.
    """
    if user.role not in ("admin", "editor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu usuario es de solo lectura: se requiere rol de editor o administrador",
        )
    return user


def require_superadmin(user: User = Depends(get_current_user)) -> User:
    """Dependency: solo permite acceso a usuarios con is_superadmin=True."""
    if not getattr(user, "is_superadmin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere acceso de superadministrador",
        )
    return user


# ─── Auth por API key (ingesta externa W1) ───────────────────
# El header que porta el secreto de la key.
API_KEY_HEADER = "X-API-Key"

# Throttle de escritura de last_used_at: si el último uso fue hace menos de
# esto, no re-escribimos para no pegarle a la DB en cada request.
_LAST_USED_THROTTLE_SECONDS = 60


@dataclass
class ApiKeyContext:
    """Contexto de autenticación derivado de una API key válida.

    Es lo que devuelve `get_org_from_api_key` y lo que consumen los endpoints
    de ingesta (PARTE B). El `org_id` sale SIEMPRE de la key, nunca de un
    parámetro del request — garantía de tenancy dura.
    """
    org_id: int
    api_key_id: int
    scopes: List[str] = field(default_factory=list)

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": API_KEY_HEADER},
    )


def _touch_last_used(db: Session, api_key: ApiKey) -> None:
    """Actualiza `last_used_at` de forma throttled (máx 1 escritura/min).

    Best-effort: un fallo al registrar el uso no debe tumbar la request.
    """
    now = datetime.utcnow()
    last = api_key.last_used_at
    if last is not None and (now - last).total_seconds() < _LAST_USED_THROTTLE_SECONDS:
        return
    try:
        api_key.last_used_at = now
        db.commit()
    except Exception:  # noqa: BLE001 — best-effort, no romper auth por esto
        db.rollback()
        logger.warning("No se pudo actualizar last_used_at de api_key id=%s", api_key.id)


def get_org_from_api_key(
    request: Request,
    db: Session = Depends(get_db),
) -> ApiKeyContext:
    """Dependency FastAPI: autentica por header `X-API-Key`.

    Localiza la fila candidata por `prefix` (indexado), verifica el hash
    bcrypt del secreto completo, y valida que la key no esté revocada ni
    expirada. Devuelve un `ApiKeyContext` con `org_id`, `api_key_id` y
    `scopes`.

    Falla con 401 si la key está ausente, es inválida, está revocada o
    expirada. NUNCA loguea el secreto en claro.
    """
    secreto = request.headers.get(API_KEY_HEADER)
    if not secreto:
        raise _unauthorized("Falta el header X-API-Key")

    prefix = extraer_prefix(secreto)
    # Puede haber más de una key con el mismo prefix (colisión improbable pero
    # posible); verificamos el hash de cada candidata.
    candidatas = db.query(ApiKey).filter(ApiKey.prefix == prefix).all()

    api_key = None
    for candidata in candidatas:
        if verificar_api_key(secreto, candidata.key_hash):
            api_key = candidata
            break

    if api_key is None:
        raise _unauthorized("API key inválida")

    if api_key.revoked:
        raise _unauthorized("API key revocada")

    if api_key.expires_at is not None and api_key.expires_at < datetime.utcnow():
        raise _unauthorized("API key expirada")

    _touch_last_used(db, api_key)

    return ApiKeyContext(
        org_id=api_key.org_id,
        api_key_id=api_key.id,
        scopes=deserializar_scopes(api_key.scopes),
    )


def require_scope(scope: str):
    """Factory: devuelve una dependency que exige `scope` en la API key.

    Uso en la PARTE B (ingesta):
        @router.post(...)
        def endpoint(ctx: ApiKeyContext = Depends(require_scope("ingest:write"))):
            ...

    Responde 403 si la key es válida pero no tiene el scope; el 401 (key
    ausente/inválida) ya lo maneja `get_org_from_api_key`.
    """
    def _dependency(
        ctx: ApiKeyContext = Depends(get_org_from_api_key),
    ) -> ApiKeyContext:
        if not ctx.has_scope(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"La API key no tiene el scope requerido: {scope}",
            )
        return ctx

    return _dependency
