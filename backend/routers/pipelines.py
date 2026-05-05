import json
import os
import shutil
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Pipeline, User
from backend.config import UPLOADS_DIR, PIPELINE_RUNS_DIR
from rgenerator.tooling.pipeline_tools import PipelineRunner
from rgenerator.tooling.data_tools import safe_json_to_text, safe_text_to_json

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])

# Store active sessions in memory (Global state for this module)
ACTIVE_RUNNERS: Dict[int, PipelineRunner] = {}


def _pipeline_to_dict(p: Pipeline) -> dict:
    return {
        "pipeline_id": p.pipeline_id,
        "pipeline": p.pipeline,
        "description": p.description or "",
        "config_json": p.config_json or "{}",
        "hidden": p.hidden or False,
        "last_run": p.last_run.strftime("%Y-%m-%d %H:%M:%S") if p.last_run else "",
    }


def _get_pipeline_config_from_db(pipeline_id: int, user: User, db: Session) -> Optional[dict]:
    """Read the pipeline config JSON from the database."""
    row = db.query(Pipeline).filter(
        Pipeline.pipeline_id == pipeline_id,
        Pipeline.org_id == user.org_id,
    ).first()
    if row and row.config_json and str(row.config_json).strip():
        return safe_text_to_json(row.config_json)
    return None


def _update_last_run(pipeline_id: int, user: User, db: Session):
    try:
        row = db.query(Pipeline).filter(
            Pipeline.pipeline_id == pipeline_id,
            Pipeline.org_id == user.org_id,
        ).first()
        if row:
            row.last_run = datetime.utcnow()
            db.commit()
    except Exception as ex:
        db.rollback()
        print(f"Error actualizando last_run: {ex}")


@router.get("/")
@router.get("", include_in_schema=False)
async def get_pipelines(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        pipelines = db.query(Pipeline).filter(Pipeline.org_id == user.org_id).all()
        records = [_pipeline_to_dict(p) for p in pipelines]
        return JSONResponse(content=json.loads(json.dumps(records, default=lambda o: None)))
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/{pipeline_id}/upload")
async def upload_pipeline_files(
    pipeline_id: int,
    input_key: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # Verify pipeline belongs to org
        row = db.query(Pipeline).filter(
            Pipeline.pipeline_id == pipeline_id,
            Pipeline.org_id == user.org_id,
        ).first()
        if not row:
            return {"error": "Pipeline no encontrado"}

        upload_dir = UPLOADS_DIR / str(pipeline_id) / input_key
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []
        for file in files:
            file_path = upload_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(file.filename)

        return {
            "status": "success",
            "message": f"Cargados {len(saved_files)} archivos para {input_key}",
            "files": saved_files,
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/{pipeline_id}/run")
async def execute_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        os.system("cls")

        # Si hay un runner previo en estado terminal (COMPLETED/FAILED),
        # lo descartamos para empezar un run nuevo desde cero. Sin esto, el
        # frontend reusaba el runner agotado y los steps ya ejecutados se
        # saltaban (bug: pedía archivos en orden incorrecto entre re-ejecuciones).
        existing = ACTIVE_RUNNERS.get(pipeline_id)
        if existing is not None and getattr(existing, "status", None) in ("COMPLETED", "FAILED"):
            del ACTIVE_RUNNERS[pipeline_id]

        if pipeline_id not in ACTIVE_RUNNERS:
            config = _get_pipeline_config_from_db(pipeline_id, user, db)
            if not config:
                return {"error": f"No se encontró la configuración del pipeline para el ID {pipeline_id}"}
            ACTIVE_RUNNERS[pipeline_id] = PipelineRunner(config, pipeline_id=pipeline_id, db=db, org_id=user.org_id, user_id=user.id)

        runner = ACTIVE_RUNNERS[pipeline_id]
        results = runner.run_all()
        last_result = results[-1] if results else {}

        if last_result.get("status") == "waiting_input":
            return last_result

        result = {
            "status": "success",
            "message": "Pipeline completado",
            "artifacts": list(runner.ctx.artifacts.keys()),
        }
        _update_last_run(pipeline_id, user, db)
        return result
    except Exception as e:
        if pipeline_id in ACTIVE_RUNNERS:
            del ACTIVE_RUNNERS[pipeline_id]
        return {"error": str(e)}


@router.post("/{pipeline_id}/input")
async def submit_pipeline_input(
    pipeline_id: int,
    input_data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Recibe input del usuario para reanudar un pipeline pausado."""
    try:
        if pipeline_id not in ACTIVE_RUNNERS:
            return {"error": "La sesión del pipeline no está activa."}

        runner = ACTIVE_RUNNERS[pipeline_id]

        if input_data.get("type") == "enrich_per_file":
            if not hasattr(runner.ctx, "user_inputs"):
                runner.ctx.user_inputs = {}
            enrich_store = runner.ctx.user_inputs.get("enrich_per_file", {})
            enrich_store.update(input_data.get("data", {}))
            runner.ctx.user_inputs["enrich_per_file"] = enrich_store
        elif input_data.get("type") == "enrich_once":
            # Valores globales del run (mode="once") — un valor por campo, aplica a todos los archivos.
            if not hasattr(runner.ctx, "user_inputs"):
                runner.ctx.user_inputs = {}
            global_store = runner.ctx.user_inputs.get("enrich_global", {})
            global_store.update(input_data.get("data", {}))
            runner.ctx.user_inputs["enrich_global"] = global_store

        results = runner.run_all()
        last_result = results[-1] if results else {}

        if last_result.get("status") == "waiting_input":
            return last_result

        result = {
            "status": "success",
            "message": "Pipeline completado",
            "artifacts": list(runner.ctx.artifacts.keys()),
        }
        _update_last_run(pipeline_id, user, db)
        return result
    except Exception as e:
        return {"error": str(e)}


@router.post("/{pipeline_id}/step")
async def execute_pipeline_step(
    pipeline_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # Idem que en /run: descartar runner terminal antes de crear nuevo.
        existing = ACTIVE_RUNNERS.get(pipeline_id)
        if existing is not None and getattr(existing, "status", None) in ("COMPLETED", "FAILED"):
            del ACTIVE_RUNNERS[pipeline_id]

        if pipeline_id not in ACTIVE_RUNNERS:
            config = _get_pipeline_config_from_db(pipeline_id, user, db)
            if not config:
                return {"error": "No se encontró la configuración del pipeline"}
            ACTIVE_RUNNERS[pipeline_id] = PipelineRunner(config, pipeline_id=pipeline_id, db=db, org_id=user.org_id, user_id=user.id)

        runner = ACTIVE_RUNNERS[pipeline_id]
        result = runner.step()

        if result.get("finished"):
            _update_last_run(pipeline_id, user, db)

        return result
    except Exception as e:
        if pipeline_id in ACTIVE_RUNNERS:
            del ACTIVE_RUNNERS[pipeline_id]
        return {"error": str(e)}


@router.post("/{pipeline_id}/reset")
async def reset_pipeline_session(
    pipeline_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if pipeline_id in ACTIVE_RUNNERS:
        del ACTIVE_RUNNERS[pipeline_id]
    return {"status": "success"}


@router.get("/{pipeline_id}/artifact/{artifact_key}")
async def download_artifact(
    pipeline_id: int,
    artifact_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if pipeline_id not in ACTIVE_RUNNERS:
        raise HTTPException(status_code=404, detail="La sesión del pipeline ha expirado o no existe.")

    runner = ACTIVE_RUNNERS[pipeline_id]
    artifact = runner.ctx.artifacts.get(artifact_key)

    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artefacto '{artifact_key}' no encontrado.")

    if isinstance(artifact, pd.DataFrame):
        output = BytesIO()
        try:
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                artifact.to_excel(writer, index=False)
        except Exception as e:
            print(f"Error generando Excel: {e}")
            output = BytesIO()
            artifact.to_csv(output, index=False)
            output.seek(0)
            headers = {"Content-Disposition": f'attachment; filename="{artifact_key}.csv"'}
            return StreamingResponse(output, headers=headers, media_type="text/csv")
        output.seek(0)
        headers = {"Content-Disposition": f'attachment; filename="{artifact_key}.xlsx"'}
        return StreamingResponse(
            output,
            headers=headers,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    elif isinstance(artifact, (str, Path)) and os.path.exists(artifact):
        file_path = Path(artifact)
        return FileResponse(path=file_path, filename=file_path.name, media_type="application/octet-stream")

    else:
        try:
            json_str = json.dumps(artifact, default=str, indent=2)
            return StreamingResponse(
                BytesIO(json_str.encode()),
                media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="{artifact_key}.json"'},
            )
        except Exception:
            raise HTTPException(status_code=400, detail="El tipo de artefacto no se puede descargar.")


@router.get("/{pipeline_id}/artifact/{artifact_key}/preview")
async def preview_artifact(
    pipeline_id: int,
    artifact_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if pipeline_id not in ACTIVE_RUNNERS:
        raise HTTPException(status_code=404, detail="La sesión del pipeline ha expirado.")

    runner = ACTIVE_RUNNERS[pipeline_id]
    artifact = runner.ctx.artifacts.get(artifact_key)

    if artifact is None:
        raise HTTPException(status_code=404, detail="Artefacto no encontrado.")

    if isinstance(artifact, pd.DataFrame):
        return artifact.to_csv(sep="\t", index=False)
    elif isinstance(artifact, (dict, list)):
        return json.dumps(artifact, indent=2, default=str)
    return str(artifact)


@router.get("/{pipeline_id}/config")
async def get_pipeline_config(
    pipeline_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        config = {
            "pipeline_metadata": {
                "pipeline_id": pipeline_id,
                "name": "",
                "description": "",
                "input": "EXCEL",
                "output": "XLSX",
            },
            "context": {"base_dir": "."},
            "pipeline": [],
        }

        row = db.query(Pipeline).filter(
            Pipeline.pipeline_id == pipeline_id,
            Pipeline.org_id == user.org_id,
        ).first()
        if not row:
            return config

        config["pipeline_metadata"]["name"] = row.pipeline or "Sin nombre"
        config["pipeline_metadata"]["description"] = row.description or ""

        if row.config_json and str(row.config_json).strip():
            json_config = safe_text_to_json(row.config_json)
            if json_config and isinstance(json_config, dict):
                config["context"] = json_config.get("context", config["context"])
                config["pipeline"] = json_config.get("pipeline", config["pipeline"])
                config_meta = json_config.get("pipeline_metadata", json_config.get("workflow_metadata", {}))
                for k, v in config_meta.items():
                    if k not in config["pipeline_metadata"] or not config["pipeline_metadata"][k]:
                        config["pipeline_metadata"][k] = v

        return config
    except Exception as e:
        return {"error": str(e)}


@router.post("/config")
async def create_pipeline_config(
    config: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _save_pipeline_config_logic(pipeline_id=0, config=config, db=db, user=user)


async def _save_pipeline_config_logic(pipeline_id: int, config: dict, db: Session, user: User):
    try:
        metadata = config.get("pipeline_metadata", {})
        new_name = metadata.get("name", "Nuevo Proceso")

        is_new = pipeline_id == 0
        if not is_new:
            row = db.query(Pipeline).filter(
                Pipeline.pipeline_id == pipeline_id,
                Pipeline.org_id == user.org_id,
            ).first()
            if not row:
                is_new = True

        if is_new:
            # Check for duplicate name within org
            existing = db.query(Pipeline).filter(
                Pipeline.pipeline == new_name,
                Pipeline.org_id == user.org_id,
            ).first()
            if existing:
                return {"error": f"Ya existe un proceso llamado '{new_name}'. Por favor elige otro nombre."}

        config_json_text = safe_json_to_text(config)

        if is_new:
            row = Pipeline(
                pipeline=new_name,
                description=metadata.get("description", ""),
                config_json=config_json_text,
                hidden=False,
                org_id=user.org_id,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        else:
            if metadata.get("name"):
                row.pipeline = metadata.get("name")
            if metadata.get("description") is not None:
                row.description = metadata.get("description")
            row.config_json = config_json_text
            db.commit()
            db.refresh(row)

        return {
            "status": "success",
            "message": f"Configuración guardada para el ID {row.pipeline_id}",
            "new_id": row.pipeline_id,
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}


@router.post("/{pipeline_id}/config")
async def save_pipeline_config_endpoint(
    pipeline_id: int,
    config: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _save_pipeline_config_logic(pipeline_id, config, db, user)


@router.patch("/{pipeline_id}/hidden")
async def toggle_pipeline_hidden(
    pipeline_id: int,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        row = db.query(Pipeline).filter(
            Pipeline.pipeline_id == pipeline_id,
            Pipeline.org_id == user.org_id,
        ).first()
        if not row:
            return {"error": "Pipeline no encontrado"}

        row.hidden = body.get("hidden", False)
        db.commit()
        return {"status": "success", "hidden": row.hidden}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}


@router.delete("/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        row = db.query(Pipeline).filter(
            Pipeline.pipeline_id == pipeline_id,
            Pipeline.org_id == user.org_id,
        ).first()
        if not row:
            return {"error": "Pipeline no encontrado"}

        db.delete(row)
        db.commit()

        uploads_dir = UPLOADS_DIR / str(pipeline_id)
        if uploads_dir.exists():
            shutil.rmtree(uploads_dir)

        return {"status": "success", "message": f"Pipeline {pipeline_id} eliminado correctamente"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
