"""Router de autenticación: login y perfil."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Organization
from backend.auth import (
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

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
