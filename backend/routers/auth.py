"""Router de autenticación: login y perfil."""

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Organization
from backend.auth import (
    verify_password,
    create_access_token,
    get_current_user,
)
from backend.rate_limit import SlidingWindowLimiter

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ─── Rate limiting de login ──────────────────────────────────
# Dos capas: por (ip, email) para el ataque dirigido a una cuenta, y por
# ip sola (umbral más alto) para el barrido de muchas cuentas.
_LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
_LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_MINUTES", "15")) * 60
_limiter_cuenta = SlidingWindowLimiter(_LOGIN_MAX_ATTEMPTS, _LOGIN_WINDOW_SECONDS)
_limiter_ip = SlidingWindowLimiter(_LOGIN_MAX_ATTEMPTS * 4, _LOGIN_WINDOW_SECONDS)


def _client_ip(request: Request) -> str:
    """IP real del cliente (Railway pone la original en X-Forwarded-For)."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─── Schemas ─────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    org_id: int
    org_name: str
    is_superadmin: bool = False


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Endpoints ───────────────────────────────────────────────
@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = _client_ip(request)
    clave_cuenta = f"{ip}:{body.email.strip().lower()}"

    if _limiter_cuenta.is_blocked(clave_cuenta) or _limiter_ip.is_blocked(ip):
        retry = max(
            _limiter_cuenta.retry_after_seconds(clave_cuenta),
            _limiter_ip.retry_after_seconds(ip),
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos. Intenta de nuevo más tarde.",
            headers={"Retry-After": str(retry or _LOGIN_WINDOW_SECONDS)},
        )

    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        _limiter_cuenta.register_failure(clave_cuenta)
        _limiter_ip.register_failure(ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    _limiter_cuenta.reset(clave_cuenta)

    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    token = create_access_token(user.id, user.org_id, user.role)

    return LoginResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            name=user.name or "",
            email=user.email,
            role=user.role,
            org_id=user.org_id,
            org_name=org.name if org else "",
            is_superadmin=bool(user.is_superadmin),
        ),
    )


@router.get("/me", response_model=UserOut)
async def me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    return UserOut(
        id=user.id,
        name=user.name or "",
        email=user.email,
        role=user.role,
        org_id=user.org_id,
        org_name=org.name if org else "",
        is_superadmin=bool(user.is_superadmin),
    )
