"""
routers/superadmin.py — CRUD de Organizaciones y sus Usuarios para Superadmin.

Prefix: /api/superadmin
Protección: require_superadmin (is_superadmin=True)
"""
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import hash_password, require_superadmin
from backend.database import get_db
from backend.models import Organization, User

router = APIRouter(prefix="/api/superadmin", tags=["superadmin"])


# ─── Pydantic Models ─────────────────────────────────────────────────────────

class OrgCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = ""
    is_active: bool = True


class OrgUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class UserCreate(BaseModel):
    name: Optional[str] = ""
    email: str
    password: str
    role: str = "editor"          # admin | editor | viewer
    is_active: bool = True
    is_superadmin: bool = False


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    org_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_superadmin: Optional[bool] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """Convierte 'Fundación PHP' → 'fundacion-php'."""
    text = text.lower().strip()
    # reemplaza caracteres acentuados
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def _org_to_dict(org: Organization, user_count: int = 0) -> dict:
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "description": org.description or "",
        "is_active": org.is_active,
        "created_at": org.created_at.strftime("%Y-%m-%d %H:%M:%S") if org.created_at else "",
        "updated_at": org.updated_at.strftime("%Y-%m-%d %H:%M:%S") if org.updated_at else "",
        "user_count": user_count,
    }


def _user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "name": u.name or "",
        "email": u.email,
        "role": u.role,
        "org_id": u.org_id,
        "is_active": u.is_active,
        "is_superadmin": u.is_superadmin or False,
        "created_at": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "",
    }


# ─── Organizations ────────────────────────────────────────────────────────────

@router.get("/organizations")
async def list_organizations(
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Lista todas las organizaciones con conteo de usuarios."""
    orgs = db.query(Organization).order_by(Organization.id).all()
    result = []
    for org in orgs:
        count = db.query(User).filter(User.org_id == org.id, User.is_active == True).count()
        result.append(_org_to_dict(org, user_count=count))
    return result


@router.post("/organizations")
async def create_organization(
    body: OrgCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    slug = body.slug or _slugify(body.name)

    # Validar slug único
    existing = db.query(Organization).filter(Organization.slug == slug).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"El slug '{slug}' ya existe")

    org = Organization(
        name=body.name,
        slug=slug,
        description=body.description or "",
        is_active=body.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return {"status": "success", "data": _org_to_dict(org)}


@router.put("/organizations/{org_id}")
async def update_organization(
    org_id: int,
    body: OrgUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    if body.name is not None:
        org.name = body.name
    if body.slug is not None:
        # Validar slug único excluyendo el propio
        dup = db.query(Organization).filter(
            Organization.slug == body.slug,
            Organization.id != org_id,
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"El slug '{body.slug}' ya existe")
        org.slug = body.slug
    if body.description is not None:
        org.description = body.description
    if body.is_active is not None:
        org.is_active = body.is_active
    org.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(org)
    count = db.query(User).filter(User.org_id == org.id, User.is_active == True).count()
    return {"status": "success", "data": _org_to_dict(org, user_count=count)}


@router.delete("/organizations/{org_id}")
async def delete_organization(
    org_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    # Verificar que no tenga usuarios activos
    active_users = db.query(User).filter(User.org_id == org_id, User.is_active == True).count()
    if active_users > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: la organización tiene {active_users} usuario(s) activo(s). Desactívalos primero.",
        )

    db.delete(org)
    db.commit()
    return {"status": "success", "message": f"Organización '{org.name}' eliminada"}


# ─── Users (cross-org) ───────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/users")
async def list_org_users(
    org_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Lista todos los usuarios de una organización específica."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    users = db.query(User).filter(User.org_id == org_id).order_by(User.id).all()
    return [_user_to_dict(u) for u in users]


@router.get("/users")
async def list_all_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Lista todos los usuarios de todas las organizaciones."""
    users = db.query(User).order_by(User.org_id, User.id).all()
    return [_user_to_dict(u) for u in users]


@router.post("/organizations/{org_id}/users")
async def create_user_in_org(
    org_id: int,
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Crea un usuario dentro de una organización específica."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    # Email único global
    dup = db.query(User).filter(User.email == body.email.strip().lower()).first()
    if dup:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    user = User(
        name=body.name or "",
        email=body.email.strip().lower(),
        password_hash=hash_password(body.password),
        org_id=org_id,
        role=body.role,
        is_active=body.is_active,
        is_superadmin=body.is_superadmin,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"status": "success", "data": _user_to_dict(user)}


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_superadmin),
):
    """Actualiza cualquier campo de un usuario (nombre, email, org, rol, is_superadmin)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if body.name is not None:
        user.name = body.name
    if body.email is not None:
        dup = db.query(User).filter(
            User.email == body.email.strip().lower(),
            User.id != user_id,
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail="El email ya está en uso")
        user.email = body.email.strip().lower()
    if body.password is not None and body.password.strip():
        user.password_hash = hash_password(body.password)
    if body.role is not None:
        user.role = body.role
    if body.org_id is not None:
        org = db.query(Organization).filter(Organization.id == body.org_id).first()
        if not org:
            raise HTTPException(status_code=400, detail="Organización destino no encontrada")
        user.org_id = body.org_id
    if body.is_active is not None:
        # No se puede desactivar a sí mismo
        if user.id == current.id and body.is_active is False:
            raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta")
        user.is_active = body.is_active
    if body.is_superadmin is not None:
        # No quitarse el superadmin a sí mismo
        if user.id == current.id and body.is_superadmin is False:
            raise HTTPException(status_code=400, detail="No puedes quitarte el rol de superadmin")
        user.is_superadmin = body.is_superadmin

    db.commit()
    db.refresh(user)
    return {"status": "success", "data": _user_to_dict(user)}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_superadmin),
):
    """Soft-delete: desactiva el usuario (no lo elimina de la DB)."""
    if user_id == current.id:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.is_active = False
    db.commit()
    return {"status": "success", "message": f"Usuario {user.email} desactivado"}
