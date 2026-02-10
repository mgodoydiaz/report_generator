from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Dict, Optional
import pandas as pd
import shutil
import os
import json
from config import BASE_DIR, PIPELINES_DB_PATH, PIPELINES_DIR, UPLOADS_DIR
from rgenerator.tooling.pipeline_tools import PipelineRunner, run_pipeline
from rgenerator.tooling.data_tools import safe_json_to_text, safe_text_to_json

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])

# Store active sessions in memory (Global state for this module)
ACTIVE_RUNNERS: Dict[int, PipelineRunner] = {}

def _update_last_run(pipeline_id):
    try:
        df = pd.read_excel(PIPELINES_DB_PATH)
        df.loc[df['id_evaluation'] == pipeline_id, 'last_run'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        df.to_excel(PIPELINES_DB_PATH, index=False)
    except Exception as ex:
        print(f"Error actualizando Excel: {ex}")

def _get_pipeline_config_from_excel(pipeline_id: int) -> Optional[dict]:
    """Lee la configuración JSON desde la columna 'jsonb' del Excel."""
    try:
        if not PIPELINES_DB_PATH.exists():
            return None
        df = pd.read_excel(PIPELINES_DB_PATH)
        row = df[df['id_evaluation'] == pipeline_id]
        if not row.empty and 'jsonb' in row.columns:
            json_text = row.iloc[0]['jsonb']
            if pd.notna(json_text):
                return safe_text_to_json(json_text)
    except Exception as e:
        print(f"Error leyendo config desde Excel: {e}")
    return None

@router.get("/")
@router.get("", include_in_schema=False)
async def get_pipelines():
    try:
        if not PIPELINES_DB_PATH.exists():
            return {"error": f"Archivo no encontrado en {PIPELINES_DB_PATH}"}
        
        df = pd.read_excel(PIPELINES_DB_PATH)
        
        # Reemplazar NaN con None para evitar error "Out of range float values"
        df = df.where(pd.notnull(df), None)
        
        if 'last_run' in df.columns:
            # Asegurar que last_run sea string, tratando None como ""
            df['last_run'] = df['last_run'].fillna("").astype(str)
            
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

@router.post("/{pipeline_id}/upload")
async def upload_pipeline_files(pipeline_id: int, input_key: str = Form(...), files: List[UploadFile] = File(...)):
    try:
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

        return {"status": "success", "message": f"Cargados {len(saved_files)} archivos para {input_key}", "files": saved_files}
    except Exception as e:
        return {"error": str(e)}

@router.post("/{pipeline_id}/run")
async def execute_pipeline(pipeline_id: int):
    try:
        os.system("cls") # Limpiar consola del servidor windows
        
        if pipeline_id in ACTIVE_RUNNERS:
            runner = ACTIVE_RUNNERS[pipeline_id]
            runner.run_all()
            result = {"status": "success", "message": "Pipeline completado", "artifacts": list(runner.ctx.artifacts.keys())}
            del ACTIVE_RUNNERS[pipeline_id]
        else:
            config = _get_pipeline_config_from_excel(pipeline_id)
            if not config:
                return {"error": f"No se encontró la configuración del pipeline para el ID {pipeline_id} en el Excel"}
                
            result = run_pipeline(config, workflow_id=pipeline_id)

        if result["status"] == "success":
            _update_last_run(pipeline_id)

        return result
    except Exception as e:
        return {"error": str(e)}

@router.post("/{pipeline_id}/step")
async def execute_pipeline_step(pipeline_id: int):
    try:
        if pipeline_id not in ACTIVE_RUNNERS:
            config = _get_pipeline_config_from_excel(pipeline_id)
            if not config:
                return {"error": f"No se encontró la configuración del pipeline en el Excel"}
                
            ACTIVE_RUNNERS[pipeline_id] = PipelineRunner(config, workflow_id=pipeline_id)

        runner = ACTIVE_RUNNERS[pipeline_id]
        result = runner.step()

        if result.get("finished"):
            _update_last_run(pipeline_id)
            del ACTIVE_RUNNERS[pipeline_id]

        return result
    except Exception as e:
        if workflow_id in ACTIVE_RUNNERS:
            del ACTIVE_RUNNERS[workflow_id]
        return {"error": str(e)}

@router.post("/{pipeline_id}/reset")
async def reset_pipeline_session(pipeline_id: int):
    if pipeline_id in ACTIVE_RUNNERS:
        del ACTIVE_RUNNERS[pipeline_id]
    return {"status": "success"}

@router.get("/{pipeline_id}/config")
async def get_pipeline_config(pipeline_id: int):
    try:
        config = {
            "pipeline_metadata": {"id_evaluation": pipeline_id, "name": "", "description": "", "input": "EXCEL", "output": "XLSX"},
            "context": {"base_dir": "."},
            "pipeline": []
        }
        
        if not PIPELINES_DB_PATH.exists():
            return config

        df = pd.read_excel(PIPELINES_DB_PATH)
        row = df[df['id_evaluation'] == pipeline_id]
        
        if row.empty:
            return config

        # Población desde columnas básicas
        config["pipeline_metadata"]["name"] = str(row.iloc[0]['pipeline'])
        config["pipeline_metadata"]["description"] = row.iloc[0]['description'] if pd.notna(row.iloc[0]['description']) else ""
        config["pipeline_metadata"]["input"] = str(row.iloc[0]['input']) if 'input' in row.columns and pd.notna(row.iloc[0]['input']) else "EXCEL"
        config["pipeline_metadata"]["output"] = str(row.iloc[0]['output']) if 'output' in row.columns and pd.notna(row.iloc[0]['output']) else "XLSX"

        # Población desde jsonb
        if 'jsonb' in row.columns:
            json_config = safe_text_to_json(row.iloc[0]['jsonb'])
            if json_config and isinstance(json_config, dict):
                config["context"] = json_config.get("context", config["context"])
                config["pipeline"] = json_config.get("pipeline", config["pipeline"])
                # Conservar metadatos del Excel como prioridad
                config_meta = json_config.get("pipeline_metadata", json_config.get("workflow_metadata", {}))
                for k, v in config_meta.items():
                    if k not in config["pipeline_metadata"] or not config["pipeline_metadata"][k]:
                        config["pipeline_metadata"][k] = v

        return config
    except Exception as e:
        return {"error": str(e)}

@router.post("/config")
async def create_pipeline_config(config: dict):
    return await save_pipeline_config_logic(pipeline_id=0, config=config)

# Helper function para reutilizar lógica
async def save_pipeline_config_logic(pipeline_id: int, config: dict):
    try:
        df = pd.read_excel(PIPELINES_DB_PATH)
        metadata = config.get("pipeline_metadata", {})
        
        target_id = pipeline_id
        is_new = False
        
        if pipeline_id == 0 or pipeline_id not in df['id_evaluation'].values:
            is_new = True
            new_name = metadata.get("name", "Nuevo Proceso")
            if new_name in df['pipeline'].values:
                return {"error": f"Ya existe un proceso llamado '{new_name}'. Por favor elige otro nombre."}

            if len(df) > 0:
                target_id = int(df['id_evaluation'].max()) + 1
            else:
                target_id = 1
        
        # Ya no guardamos archivos JSON físicos
        # pipeline_filename = f"pipeline{target_id:03d}.json"
        # pipeline_path = PIPELINES_DIR / pipeline_filename
        # PIPELINES_DIR.mkdir(parents=True, exist_ok=True)
        # with open(pipeline_path, 'w', encoding='utf-8') as f:
        #     json.dump(config, f, indent=4, ensure_ascii=False)
        
        steps_list = config.get("pipeline", [])
        steps_text = " -> ".join([s.get("step", "Sin nombre") for s in steps_list])
        config_json_text = safe_json_to_text(config)

        if is_new:
            new_row = {
                'id_evaluation': target_id,
                'pipeline': metadata.get("name", "Nuevo Proceso"),
                'description': metadata.get("description", ""),
                'steps': steps_text,
                'jsonb': config_json_text,
                'input': str(metadata.get("input", "EXCEL")).upper(),
                'output': str(metadata.get("output", "XLSX")).upper(),
                'last_run': ''
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            if metadata.get("name"): df.loc[df['id_evaluation'] == target_id, 'pipeline'] = metadata.get("name")
            if metadata.get("description"): df.loc[df['id_evaluation'] == target_id, 'description'] = metadata.get("description")
            df.loc[df['id_evaluation'] == target_id, 'steps'] = steps_text
            df.loc[df['id_evaluation'] == target_id, 'jsonb'] = config_json_text
            if metadata.get("input"): df.loc[df['id_evaluation'] == target_id, 'input'] = str(metadata.get("input")).upper()
            if metadata.get("output"): df.loc[df['id_evaluation'] == target_id, 'output'] = str(metadata.get("output")).upper()
        
        df.to_excel(PIPELINES_DB_PATH, index=False)
        return {"status": "success", "message": f"Configuración guardada para el ID {target_id}", "new_id": target_id}
    except Exception as e:
        return {"error": str(e)}

@router.post("/{pipeline_id}/config")
async def save_pipeline_config_endpoint(pipeline_id: int, config: dict):
    return await save_pipeline_config_logic(pipeline_id, config)

@router.delete("/{pipeline_id}")
async def delete_pipeline(pipeline_id: int):
    try:
        df = pd.read_excel(PIPELINES_DB_PATH)
        if pipeline_id not in df['id_evaluation'].values:
            return {"error": "Pipeline no encontrado"}
        
        df = df[df['id_evaluation'] != pipeline_id]
        df.to_excel(PIPELINES_DB_PATH, index=False)
        
        # Ya no eliminamos archivos JSON físicos
        # pipeline_filename = f"pipeline{pipeline_id:03d}.json"
        # pipeline_path = PIPELINES_DIR / pipeline_filename
        # if pipeline_path.exists():
        #     os.remove(pipeline_path)
            
        uploads_dir = UPLOADS_DIR / str(pipeline_id)
        if uploads_dir.exists():
            shutil.rmtree(uploads_dir)
            
        return {"status": "success", "message": f"Pipeline {pipeline_id} eliminado correctamente"}
    except Exception as e:
        return {"error": str(e)}
