"""Router CRUD de usuarios — protegido por JWT, admin-only para escritura."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.auth import get_current_user, require_admin, hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


# ─── Schemas ─────────────────────────────────────────────────
class UserCreate(BaseModel):
    name: str = ""
    email: str
    password: str
    role: str = "editor"  # admin | editor | viewer


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    org_id: int
    is_active: bool

    class Config:
        from_attributes = True


# ─── Endpoints ───────────────────────────────────────────────

@router.get("/", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista los usuarios de la misma organización."""
    users = (
        db.query(User)
        .filter(User.org_id == current_user.org_id)
        .order_by(User.id)
        .all()
    )
    return [
        UserResponse(
            id=u.id,
            name=u.name or "",
            email=u.email,
            role=u.role,
            org_id=u.org_id,
            is_active=u.is_active,
        )
        for u in users
    ]


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Crea un usuario en la misma organización. Solo admin."""
    # Validar email único
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")

    # Validar role
    if body.role not in ("admin", "editor", "viewer"):
        raise HTTPException(status_code=400, detail="Rol inválido. Usar: admin, editor, viewer")

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        org_id=admin.org_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        name=user.name or "",
        email=user.email,
        role=user.role,
        org_id=user.org_id,
        is_active=user.is_active,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Actualiza un usuario. Solo admin."""
    user = (
        db.query(User)
        .filter(User.id == user_id, User.org_id == admin.org_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if body.name is not None:
        user.name = body.name
    if body.email is not None:
        # Verificar que no esté tomado
        existing = db.query(User).filter(User.email == body.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email ya registrado")
        user.email = body.email
    if body.role is not None:
        if body.role not in ("admin", "editor", "viewer"):
            raise HTTPException(status_code=400, detail="Rol inválido")
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        name=user.name or "",
        email=user.email,
        role=user.role,
        org_id=user.org_id,
        is_active=user.is_active,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Desactiva un usuario (soft delete). Solo admin. No puede auto-borrarse."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta")

    user = (
        db.query(User)
        .filter(User.id == user_id, User.org_id == admin.org_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.is_active = False
    db.commit()

    return {"status": "success", "detail": f"Usuario {user.email} desactivado"}
