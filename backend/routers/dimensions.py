from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user
from backend.models import User, Dimension, DimensionValue

router = APIRouter(prefix="/api/dimensions", tags=["dimensions"])

# --- Pydantic Models ---
class DimensionBase(BaseModel):
    name: str
    data_type: str = "str"
    validation_mode: str = "free"  # free, list
    description: Optional[str] = ""

class DimensionCreate(DimensionBase):
    pass

class DimensionUpdate(DimensionBase):
    pass

class DimensionValueCreate(BaseModel):
    value: str
    is_active: bool = True

class DimensionValueUpdate(BaseModel):
    value: Optional[str] = None
    is_active: Optional[bool] = None

# --- Endpoints: Dimensions ---

@router.get("/")
async def get_dimensions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        dims = db.query(Dimension).filter(Dimension.org_id == user.org_id).all()
        return [
            {
                "id_dimension": d.id_dimension,
                "name": d.name,
                "data_type": d.data_type,
                "validation_mode": d.validation_mode,
                "description": d.description or "",
                "updated_at": d.updated_at.strftime("%Y-%m-%d %H:%M:%S") if d.updated_at else "",
            }
            for d in dims
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_dimension(
    dim: DimensionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        new_dim = Dimension(
            name=dim.name,
            data_type=dim.data_type,
            validation_mode=dim.validation_mode,
            description=dim.description or "",
            org_id=user.org_id,
            updated_at=datetime.utcnow(),
        )
        db.add(new_dim)
        db.commit()
        db.refresh(new_dim)

        return {
            "status": "success",
            "data": {
                "id_dimension": new_dim.id_dimension,
                "name": new_dim.name,
                "data_type": new_dim.data_type,
                "validation_mode": new_dim.validation_mode,
                "description": new_dim.description or "",
                "updated_at": new_dim.updated_at.strftime("%Y-%m-%d %H:%M:%S") if new_dim.updated_at else "",
            },
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{dim_id}")
async def update_dimension(
    dim_id: int,
    dim: DimensionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        record = db.query(Dimension).filter(
            Dimension.id_dimension == dim_id,
            Dimension.org_id == user.org_id,
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="Dimensión no encontrada")

        record.name = dim.name
        record.data_type = dim.data_type
        record.validation_mode = dim.validation_mode
        if dim.description is not None:
            record.description = dim.description
        record.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(record)

        return {
            "status": "success",
            "data": {
                "id_dimension": record.id_dimension,
                "name": record.name,
                "data_type": record.data_type,
                "validation_mode": record.validation_mode,
                "description": record.description or "",
                "updated_at": record.updated_at.strftime("%Y-%m-%d %H:%M:%S") if record.updated_at else "",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{dim_id}")
async def delete_dimension(
    dim_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        record = db.query(Dimension).filter(
            Dimension.id_dimension == dim_id,
            Dimension.org_id == user.org_id,
        ).first()
        if record:
            db.delete(record)  # cascade deletes DimensionValues
            db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# --- Endpoints: Dimension Values ---

@router.get("/{dim_id}/values")
async def get_dimension_values(
    dim_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # Verify dimension belongs to org
        dim = db.query(Dimension).filter(
            Dimension.id_dimension == dim_id,
            Dimension.org_id == user.org_id,
        ).first()
        if not dim:
            return []

        values = db.query(DimensionValue).filter(
            DimensionValue.id_dimension == dim_id
        ).all()

        return [
            {
                "id_value": v.id_value,
                "id_dimension": v.id_dimension,
                "value": v.value,
                "is_active": v.is_active,
            }
            for v in values
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dim_id}/values")
async def add_dimension_value(
    dim_id: int,
    val: DimensionValueCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # Verify dimension belongs to org
        dim = db.query(Dimension).filter(
            Dimension.id_dimension == dim_id,
            Dimension.org_id == user.org_id,
        ).first()
        if not dim:
            raise HTTPException(status_code=404, detail="Dimensión no encontrada")

        new_val = DimensionValue(
            id_dimension=dim_id,
            value=val.value,
            is_active=val.is_active,
        )
        db.add(new_val)
        db.commit()
        db.refresh(new_val)

        return {
            "status": "success",
            "data": {
                "id_value": new_val.id_value,
                "id_dimension": new_val.id_dimension,
                "value": new_val.value,
                "is_active": new_val.is_active,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/values/{val_id}")
async def delete_dimension_value(
    val_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        record = db.query(DimensionValue).filter(DimensionValue.id_value == val_id).first()
        if record:
            # Verify the parent dimension belongs to org
            dim = db.query(Dimension).filter(
                Dimension.id_dimension == record.id_dimension,
                Dimension.org_id == user.org_id,
            ).first()
            if not dim:
                raise HTTPException(status_code=403, detail="Acceso denegado")
            db.delete(record)
            db.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
