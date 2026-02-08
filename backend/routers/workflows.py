from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Dict, Optional
import pandas as pd
import shutil
import os
import json
from config import BASE_DIR, WORKFLOWS_DB_PATH, PIPELINES_DIR, UPLOADS_DIR
from rgenerator.tooling.pipeline_tools import PipelineRunner, run_pipeline
from rgenerator.tooling.data_tools import safe_json_to_text, safe_text_to_json

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

# Store active sessions in memory (Global state for this module)
ACTIVE_RUNNERS: Dict[int, PipelineRunner] = {}

def _update_last_run(workflow_id):
    try:
        df = pd.read_excel(WORKFLOWS_DB_PATH)
        df.loc[df['id_evaluation'] == workflow_id, 'last_run'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        df.to_excel(WORKFLOWS_DB_PATH, index=False)
    except Exception as ex:
        print(f"Error actualizando Excel: {ex}")

@router.get("/")
async def get_workflows():
    try:
        if not WORKFLOWS_DB_PATH.exists():
            return {"error": f"Archivo no encontrado en {WORKFLOWS_DB_PATH}"}
        
        df = pd.read_excel(WORKFLOWS_DB_PATH)
        if 'last_run' in df.columns:
            df['last_run'] = df['last_run'].fillna("").astype(str)
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

@router.post("/{workflow_id}/upload")
async def upload_workflow_files(workflow_id: int, input_key: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        upload_dir = UPLOADS_DIR / str(workflow_id) / input_key
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

@router.post("/{workflow_id}/run")
async def execute_workflow(workflow_id: int):
    try:
        os.system("cls") # Limpiar consola del servidor windows
        
        if workflow_id in ACTIVE_RUNNERS:
            runner = ACTIVE_RUNNERS[workflow_id]
            runner.run_all()
            result = {"status": "success", "message": "Pipeline completado", "artifacts": list(runner.ctx.artifacts.keys())}
            del ACTIVE_RUNNERS[workflow_id]
        else:
            pipeline_filename = f"pipeline{workflow_id:03d}.json"
            pipeline_path = PIPELINES_DIR / pipeline_filename
            
            if not pipeline_path.exists():
                return {"error": f"No se encontró la configuración del pipeline para el ID {workflow_id}"}
                
            result = run_pipeline(pipeline_path)

        if result["status"] == "success":
            _update_last_run(workflow_id)

        return result
    except Exception as e:
        return {"error": str(e)}

@router.post("/{workflow_id}/step")
async def execute_workflow_step(workflow_id: int):
    try:
        if workflow_id not in ACTIVE_RUNNERS:
            pipeline_filename = f"pipeline{workflow_id:03d}.json"
            pipeline_path = PIPELINES_DIR / pipeline_filename
            
            if not pipeline_path.exists():
                return {"error": f"No se encontró la configuración del pipeline"}
                
            ACTIVE_RUNNERS[workflow_id] = PipelineRunner(pipeline_path)

        runner = ACTIVE_RUNNERS[workflow_id]
        result = runner.step()

        if result.get("finished"):
            _update_last_run(workflow_id)
            del ACTIVE_RUNNERS[workflow_id]

        return result
    except Exception as e:
        if workflow_id in ACTIVE_RUNNERS:
            del ACTIVE_RUNNERS[workflow_id]
        return {"error": str(e)}

@router.post("/{workflow_id}/reset")
async def reset_workflow_session(workflow_id: int):
    if workflow_id in ACTIVE_RUNNERS:
        del ACTIVE_RUNNERS[workflow_id]
    return {"status": "success"}

@router.get("/{workflow_id}/config")
async def get_workflow_config(workflow_id: int):
    try:
        excel_metadata = {"name": "", "description": "", "input": "EXCEL", "output": "XLSX"}
        if WORKFLOWS_DB_PATH.exists():
            df = pd.read_excel(WORKFLOWS_DB_PATH)
            row = df[df['id_evaluation'] == workflow_id]
            if not row.empty:
                excel_metadata["name"] = str(row.iloc[0]['pipeline'])
                excel_metadata["description"] = row.iloc[0]['description'] if pd.notna(row.iloc[0]['description']) else ""
                excel_metadata["input"] = str(row.iloc[0]['input']) if 'input' in row.columns and pd.notna(row.iloc[0]['input']) else "EXCEL"
                excel_metadata["output"] = str(row.iloc[0]['output']) if pd.notna(row.iloc[0]['output']) else "XLSX"

        # Intentar leer desde la columna 'config_json' del Excel primero
        json_config = None
        if WORKFLOWS_DB_PATH.exists():
             df = pd.read_excel(WORKFLOWS_DB_PATH) 
             row = df[df['id_evaluation'] == workflow_id]
             if not row.empty and 'config_json' in row.columns:
                 possible_json = row.iloc[0]['config_json']
                 if pd.notna(possible_json):
                     json_config = safe_text_to_json(possible_json)

        # Si no se pudo obtener del Excel, intentar del archivo (fallback)
        pipeline_filename = f"pipeline{workflow_id:03d}.json"
        pipeline_path = PIPELINES_DIR / pipeline_filename

        if json_config:
            # Usar configuración del Excel
            config["context"] = json_config.get("context", config["context"])
            config["pipeline"] = json_config.get("pipeline", config["pipeline"])
            config["workflow_metadata"].update(json_config.get("workflow_metadata", {}))
        elif pipeline_path.exists():
            # Fallback: Usar archivo JSON
            with open(pipeline_path, 'r', encoding='utf-8') as f:
                json_config = json.load(f)
                config["context"] = json_config.get("context", config["context"])
                config["pipeline"] = json_config.get("pipeline", config["pipeline"])
                config["workflow_metadata"].update(json_config.get("workflow_metadata", {}))

        # Asegurar metadatos actualizados desde Excel
        if WORKFLOWS_DB_PATH.exists():
             # Re-leer por si acaso (aunque ya lo leímos arriba, optimización menor)
             # Usamos excel_metadata que ya leímos al principio de la función, 
             # pero ojo con el scope, excel_metadata se define al inicio.
             config["workflow_metadata"]["name"] = excel_metadata["name"] or config["workflow_metadata"].get("name")
             config["workflow_metadata"]["description"] = excel_metadata["description"] or config["workflow_metadata"].get("description")
             config["workflow_metadata"]["input"] = excel_metadata.get("input", config["workflow_metadata"].get("input"))
             config["workflow_metadata"]["output"] = excel_metadata.get("output", config["workflow_metadata"].get("output"))

        return config
    except Exception as e:
        return {"error": str(e)}

@router.post("/config")
async def create_workflow_config(config: dict):
    return await save_workflow_config_logic(workflow_id=0, config=config)

# Helper function para reutilizar lógica
async def save_workflow_config_logic(workflow_id: int, config: dict):
    try:
        df = pd.read_excel(WORKFLOWS_DB_PATH)
        metadata = config.get("workflow_metadata", {})
        
        target_id = workflow_id
        is_new = False
        
        if workflow_id == 0 or workflow_id not in df['id_evaluation'].values:
            is_new = True
            new_name = metadata.get("name", "Nuevo Proceso")
            if new_name in df['pipeline'].values:
                return {"error": f"Ya existe un proceso llamado '{new_name}'. Por favor elige otro nombre."}

            if len(df) > 0:
                target_id = int(df['id_evaluation'].max()) + 1
            else:
                target_id = 1
        
        pipeline_filename = f"pipeline{target_id:03d}.json"
        pipeline_path = PIPELINES_DIR / pipeline_filename
        
        PIPELINES_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(pipeline_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        steps_list = config.get("pipeline", [])
        steps_text = " -> ".join([s.get("step", "Sin nombre") for s in steps_list])
        config_json_text = safe_json_to_text(config)

        if is_new:
            new_row = {
                'id_evaluation': target_id,
                'pipeline': metadata.get("name", "Nuevo Proceso"),
                'description': metadata.get("description", ""),
                'steps': steps_text,
                'config_json': config_json_text,
                'input': str(metadata.get("input", "EXCEL")).upper(),
                'output': str(metadata.get("output", "XLSX")).upper(),
                'last_run': ''
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            if metadata.get("name"): df.loc[df['id_evaluation'] == target_id, 'pipeline'] = metadata.get("name")
            if metadata.get("description"): df.loc[df['id_evaluation'] == target_id, 'description'] = metadata.get("description")
            df.loc[df['id_evaluation'] == target_id, 'steps'] = steps_text
            df.loc[df['id_evaluation'] == target_id, 'config_json'] = config_json_text
            if metadata.get("input"): df.loc[df['id_evaluation'] == target_id, 'input'] = str(metadata.get("input")).upper()
            if metadata.get("output"): df.loc[df['id_evaluation'] == target_id, 'output'] = str(metadata.get("output")).upper()
        
        df.to_excel(WORKFLOWS_DB_PATH, index=False)
        return {"status": "success", "message": f"Configuración guardada para el ID {target_id}", "new_id": target_id}
    except Exception as e:
        return {"error": str(e)}

@router.post("/{workflow_id}/config")
async def save_workflow_config_endpoint(workflow_id: int, config: dict):
    return await save_workflow_config_logic(workflow_id, config)

@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: int):
    try:
        df = pd.read_excel(WORKFLOWS_DB_PATH)
        if workflow_id not in df['id_evaluation'].values:
            return {"error": "Workflow no encontrado"}
        
        df = df[df['id_evaluation'] != workflow_id]
        df.to_excel(WORKFLOWS_DB_PATH, index=False)
        
        pipeline_filename = f"pipeline{workflow_id:03d}.json"
        pipeline_path = PIPELINES_DIR / pipeline_filename
        if pipeline_path.exists():
            os.remove(pipeline_path)
            
        uploads_dir = UPLOADS_DIR / str(workflow_id)
        if uploads_dir.exists():
            shutil.rmtree(uploads_dir)
            
        return {"status": "success", "message": f"Workflow {workflow_id} eliminado correctamente"}
    except Exception as e:
        return {"error": str(e)}
