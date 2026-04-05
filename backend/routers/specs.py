import json
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user
from backend.models import User, Spec

router = APIRouter(prefix="/api/specs", tags=["specs"])


def _spec_to_dict(spec: Spec) -> dict:
    """Convert a Spec ORM object to a frontend-compatible dict."""
    try:
        meta = json.loads(spec.metadata_ or "{}")
    except Exception:
        meta = {}
    return {
        "id_spec": spec.id_spec,
        "name": spec.name,
        "type": spec.type or "Reporte",
        "description": meta.get("description", ""),
        "config_json": spec.metadata_ or "{}",
        "updated_at": meta.get("updated_at", ""),
    }


@router.get("/")
@router.get("", include_in_schema=False)
async def get_specs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        specs = db.query(Spec).filter(Spec.org_id == user.org_id).all()
        return [_spec_to_dict(s) for s in specs]
    except Exception as e:
        return {"error": str(e)}


@router.get("/{spec_id}/config")
async def get_spec_config(
    spec_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        spec = db.query(Spec).filter(
            Spec.id_spec == spec_id,
            Spec.org_id == user.org_id,
        ).first()
        if not spec:
            return {"error": "Especificación no encontrada"}

        try:
            config = json.loads(spec.metadata_ or "{}")
        except Exception:
            config = {}

        return {
            "name": spec.name,
            "description": config.get("description", ""),
            "type": spec.type or "Reporte",
            **config,
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/config")
async def create_spec_config(
    config: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _save_spec_config_logic(spec_id=0, config=config, db=db, user=user)


async def _save_spec_config_logic(spec_id: int, config: dict, db: Session, user: User):
    try:
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Build metadata JSON — store everything except name/type as flat config
        _meta_keys = {"name", "type"}
        meta_data = {k: v for k, v in config.items() if k not in _meta_keys}
        meta_data["updated_at"] = now_str
        metadata_str = json.dumps(meta_data, ensure_ascii=False)

        is_new = spec_id == 0
        if not is_new:
            spec = db.query(Spec).filter(
                Spec.id_spec == spec_id,
                Spec.org_id == user.org_id,
            ).first()
            if not spec:
                is_new = True

        if is_new:
            spec = Spec(
                name=config.get("name", "Nueva Especificación"),
                type=config.get("type", "Reporte"),
                metadata_=metadata_str,
                charts_list="[]",
                tables_list="[]",
                org_id=user.org_id,
            )
            db.add(spec)
            db.commit()
            db.refresh(spec)
        else:
            spec.name = config.get("name", spec.name)
            spec.type = config.get("type", spec.type)
            spec.metadata_ = metadata_str
            db.commit()
            db.refresh(spec)

        return {
            "status": "success",
            "message": f"Especificación {spec.id_spec} guardada",
            "new_id": spec.id_spec,
        }
    except Exception as e:
        db.rollback()
        import traceback; traceback.print_exc()
        return {"error": str(e)}


@router.post("/{spec_id}/config")
async def save_spec_config_endpoint(
    spec_id: int,
    config: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _save_spec_config_logic(spec_id, config, db, user)


@router.post("/{spec_id}/duplicate")
async def duplicate_spec(
    spec_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        spec = db.query(Spec).filter(
            Spec.id_spec == spec_id,
            Spec.org_id == user.org_id,
        ).first()
        if not spec:
            return {"error": "Especificación no encontrada"}

        try:
            config = json.loads(spec.metadata_ or "{}")
        except Exception:
            config = {}

        config["name"] = config.get("name", spec.name) + " (Copia)"
        config["type"] = config.get("type", spec.type or "Reporte")

        return await _save_spec_config_logic(0, config, db, user)
    except Exception as e:
        return {"error": str(e)}


@router.delete("/{spec_id}")
async def delete_spec(
    spec_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        spec = db.query(Spec).filter(
            Spec.id_spec == spec_id,
            Spec.org_id == user.org_id,
        ).first()
        if not spec:
            return {"error": "Especificación no encontrada"}

        db.delete(spec)
        db.commit()
        return {"status": "success", "message": f"Especificación {spec_id} eliminada"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
