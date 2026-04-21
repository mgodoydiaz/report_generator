import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user
from backend.models import User, Organization, OrganizationAsset
from backend.config import BASE_DIR

router = APIRouter(prefix="/api/organizations", tags=["organizations"])

ASSETS_DIR = BASE_DIR / "data" / "org_assets"
ALLOWED_KINDS = {"logo", "cover", "footer"}
ALLOWED_CONTENT_TYPES = {
    "image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp", "image/svg+xml"
}


def _org_assets_dir(org_id: int) -> Path:
    p = ASSETS_DIR / str(org_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _check_admin(user: User):
    if user.role not in ("admin",) and not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Se requiere rol admin o superadmin")


def _asset_to_dict(a: OrganizationAsset) -> dict:
    return {
        "id": a.id,
        "org_id": a.org_id,
        "kind": a.kind,
        "name": a.name,
        "filename": a.filename,
        "content_type": a.content_type,
        "uploaded_at": a.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if a.uploaded_at else "",
        "url": f"/api/organizations/{a.org_id}/assets/{a.id}/download",
    }


@router.get("/{org_id}/assets")
async def list_assets(
    org_id: int,
    kind: str = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.org_id != org_id and not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sin acceso a esta organización")
    q = db.query(OrganizationAsset).filter(OrganizationAsset.org_id == org_id)
    if kind:
        q = q.filter(OrganizationAsset.kind == kind)
    return [_asset_to_dict(a) for a in q.order_by(OrganizationAsset.uploaded_at.desc()).all()]


@router.post("/{org_id}/assets")
async def upload_asset(
    org_id: int,
    file: UploadFile = File(...),
    kind: str = Query("logo"),
    name: str = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.org_id != org_id and not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sin acceso a esta organización")
    _check_admin(user)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=400, detail=f"kind debe ser uno de {ALLOWED_KINDS}")

    content_type = file.content_type or "image/png"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido: {content_type}")

    ext = Path(file.filename).suffix if file.filename else ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = _org_assets_dir(org_id) / filename

    content = await file.read()
    dest.write_bytes(content)

    asset = OrganizationAsset(
        org_id=org_id,
        kind=kind,
        name=name or file.filename or filename,
        filename=filename,
        content_type=content_type,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"status": "success", "data": _asset_to_dict(asset)}


@router.get("/{org_id}/assets/{asset_id}/download")
async def download_asset(
    org_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.org_id != org_id and not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sin acceso a esta organización")
    asset = db.query(OrganizationAsset).filter(
        OrganizationAsset.id == asset_id,
        OrganizationAsset.org_id == org_id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset no encontrado")

    path = _org_assets_dir(org_id) / asset.filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en disco")

    return FileResponse(path, media_type=asset.content_type, filename=asset.name)


@router.delete("/{org_id}/assets/{asset_id}")
async def delete_asset(
    org_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.org_id != org_id and not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sin acceso a esta organización")
    _check_admin(user)

    asset = db.query(OrganizationAsset).filter(
        OrganizationAsset.id == asset_id,
        OrganizationAsset.org_id == org_id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset no encontrado")

    path = _org_assets_dir(org_id) / asset.filename
    if path.exists():
        path.unlink()

    db.delete(asset)
    db.commit()
    return {"status": "success"}
