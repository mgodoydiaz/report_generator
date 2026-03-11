import pandas as pd
import shutil
import os
import json
from typing import List, Dict, Optional
from io import BytesIO
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from config import BASE_DIR, PIPELINES_DB_PATH, UPLOADS_DIR, PIPELINE_RUNS_DIR
from rgenerator.tooling.pipeline_tools import PipelineRunner, run_pipeline
from rgenerator.tooling.data_tools import safe_json_to_text, safe_text_to_json, get_json_safe_df

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])

# Store active sessions in memory (Global state for this module)
ACTIVE_RUNNERS: Dict[int, PipelineRunner] = {}

def _update_last_run(pipeline_id):
    try:
        df = pd.read_excel(PIPELINES_DB_PATH)
        df.loc[df['pipeline_id'] == pipeline_id, 'last_run'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        df.to_excel(PIPELINES_DB_PATH, index=False)
    except Exception as ex:
        print(f"Error actualizando Excel: {ex}")

def _get_pipeline_config_from_excel(pipeline_id: int) -> Optional[dict]:
    """Lee la configuración JSON desde la columna 'config_json' del Excel."""
    try:
        if not PIPELINES_DB_PATH.exists():
            return None
        df = pd.read_excel(PIPELINES_DB_PATH)
        row = df[df['pipeline_id'] == pipeline_id]
        if not row.empty and 'config_json' in row.columns:
            json_text = row.iloc[0]['config_json']
            if json_text is not None and pd.notna(json_text) and str(json_text).strip():
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
        df = get_json_safe_df(df)
        
        if 'last_run' in df.columns:
            # Asegurar que last_run sea string, tratando None como ""
            df['last_run'] = df['last_run'].apply(lambda x: str(x) if x is not None else "")
            
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
        
        if pipeline_id not in ACTIVE_RUNNERS:
            config = _get_pipeline_config_from_excel(pipeline_id)
            if not config:
                return {"error": f"No se encontró la configuración del pipeline para el ID {pipeline_id} en el Excel"}
            ACTIVE_RUNNERS[pipeline_id] = PipelineRunner(config, pipeline_id=pipeline_id)

        runner = ACTIVE_RUNNERS[pipeline_id]
        results = runner.run_all()
        last_result = results[-1] if results else {}

        # Si un paso necesita input del usuario, mantener el runner activo
        if last_result.get("status") == "waiting_input":
            return last_result

        # Pipeline completado
        result = {"status": "success", "message": "Pipeline completado", "artifacts": list(runner.ctx.artifacts.keys())}
        # No eliminamos el runner aún para permitir la descarga de artefactos
        # del ACTIVE_RUNNERS[pipeline_id]
        _update_last_run(pipeline_id)
        return result
    except Exception as e:
        if pipeline_id in ACTIVE_RUNNERS:
            del ACTIVE_RUNNERS[pipeline_id]
        return {"error": str(e)}

@router.post("/{pipeline_id}/input")
async def submit_pipeline_input(pipeline_id: int, input_data: dict):
    """
    Recibe input del usuario para reanudar un pipeline pausado.
    input_data structure: { "type": "enrich_per_file", "data": { ... } }
    """
    try:
        if pipeline_id not in ACTIVE_RUNNERS:
             return {"error": "La sesión del pipeline no está activa."}
             
        runner = ACTIVE_RUNNERS[pipeline_id]
        
        # Actualizar contexto con inputs
        if input_data.get("type") == "enrich_per_file":
            if not hasattr(runner.ctx, "user_inputs"):
                runner.ctx.user_inputs = {}
            
            enrich_store = runner.ctx.user_inputs.get("enrich_per_file", {})
            enrich_store.update(input_data.get("data", {}))
            runner.ctx.user_inputs["enrich_per_file"] = enrich_store
            
        # Reanudar ejecución
        results = runner.run_all()
        last_result = results[-1] if results else {}
        
        # Verificar nuevamente si quedo pausado o termino
        if last_result.get("status") == "waiting_input":
             return last_result
             
        # Si termino exitosamente
        result = {"status": "success", "message": "Pipeline completado", "artifacts": list(runner.ctx.artifacts.keys())}
        _update_last_run(pipeline_id)
        return result

    except Exception as e:
        # No matamos el runner aqui por si fue un error de input valido
        return {"error": str(e)}

@router.post("/{pipeline_id}/step")
async def execute_pipeline_step(pipeline_id: int):
    try:
        if pipeline_id not in ACTIVE_RUNNERS:
            config = _get_pipeline_config_from_excel(pipeline_id)
            if not config:
                return {"error": f"No se encontró la configuración del pipeline en el Excel"}
                
            ACTIVE_RUNNERS[pipeline_id] = PipelineRunner(config, pipeline_id=pipeline_id)

        runner = ACTIVE_RUNNERS[pipeline_id]
        result = runner.step()

        if result.get("finished"):
            _update_last_run(pipeline_id)
            # No eliminamos el runner aún para permitir la descarga de artefactos
            # del ACTIVE_RUNNERS[pipeline_id]

        return result
    except Exception as e:
        if pipeline_id in ACTIVE_RUNNERS:
            del ACTIVE_RUNNERS[pipeline_id]
        return {"error": str(e)}

@router.post("/{pipeline_id}/reset")
async def reset_pipeline_session(pipeline_id: int):
    if pipeline_id in ACTIVE_RUNNERS:
        del ACTIVE_RUNNERS[pipeline_id]
    return {"status": "success"}

@router.get("/{pipeline_id}/artifact/{artifact_key}")
async def download_artifact(pipeline_id: int, artifact_key: str):
    """
    Descarga un artefacto generado por el pipeline.
    Si es un DataFrame, lo convierte a Excel en vuelo.
    Si es un archivo, lo descarga directamente.
    """
    if pipeline_id not in ACTIVE_RUNNERS:
        raise HTTPException(status_code=404, detail="La sesión del pipeline ha expirado o no existe.")

    runner = ACTIVE_RUNNERS[pipeline_id]
    artifact = runner.ctx.artifacts.get(artifact_key)

    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artefacto '{artifact_key}' no encontrado.")

    # Caso 1: DataFrame de Pandas -> Excel
    if isinstance(artifact, pd.DataFrame):
        output = BytesIO()
        try:
            # Usamos openpyxl explícitamente ya que xlsxwriter no está instalado
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                artifact.to_excel(writer, index=False)
        except Exception as e:
            # Fallback a csv si openpyxl falla
            print(f"Error generando Excel: {e}")
            output = BytesIO()
            artifact.to_csv(output, index=False)
            output.seek(0)
            headers = {"Content-Disposition": f'attachment; filename="{artifact_key}.csv"'}
            return StreamingResponse(output, headers=headers, media_type='text/csv')
            
        output.seek(0)
        headers = {"Content-Disposition": f'attachment; filename="{artifact_key}.xlsx"'}
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    # Caso 2: Ruta a archivo existente
    elif isinstance(artifact, (str, Path)) and os.path.exists(artifact):
        file_path = Path(artifact)
        return FileResponse(path=file_path, filename=file_path.name, media_type='application/octet-stream')
    
    # Caso 3: Otros tipos (Strings, dicts) -> JSON
    else:
        try:
            json_str = json.dumps(artifact, default=str, indent=2)
            return StreamingResponse(BytesIO(json_str.encode()), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{artifact_key}.json"'})
        except:
            raise HTTPException(status_code=400, detail="El tipo de artefacto no se puede descargar.")

@router.get("/{pipeline_id}/artifact/{artifact_key}/preview")
async def preview_artifact(pipeline_id: int, artifact_key: str):
    """
    Retorna una vista previa en texto del artefacto para copiar al portapapeles.
    """
    if pipeline_id not in ACTIVE_RUNNERS:
        raise HTTPException(status_code=404, detail="La sesión del pipeline ha expirado.")

    runner = ACTIVE_RUNNERS[pipeline_id]
    artifact = runner.ctx.artifacts.get(artifact_key)

    if artifact is None:
        raise HTTPException(status_code=404, detail="Artefacto no encontrado.")

    if isinstance(artifact, pd.DataFrame):
        # Retorna TSV (Tab Separated Values) que es ideal para pegar en Excel/Sheets
        return artifact.to_csv(sep='\t', index=False)
    
    elif isinstance(artifact, (dict, list)):
        return json.dumps(artifact, indent=2, default=str)
        
    return str(artifact)

@router.get("/{pipeline_id}/config")
async def get_pipeline_config(pipeline_id: int):
    try:
        config = {
            "pipeline_metadata": {"pipeline_id": pipeline_id, "name": "", "description": "", "input": "EXCEL", "output": "XLSX"},
            "context": {"base_dir": "."},
            "pipeline": []
        }
        
        if not PIPELINES_DB_PATH.exists():
            return config

        df = pd.read_excel(PIPELINES_DB_PATH)
        row = df[df['pipeline_id'] == pipeline_id]
        
        if row.empty:
            return config

        # Población desde columnas básicas
        config["pipeline_metadata"]["name"] = str(row.iloc[0]['pipeline']) if pd.notna(row.iloc[0]['pipeline']) else "Sin nombre"
        config["pipeline_metadata"]["description"] = str(row.iloc[0]['description']) if pd.notna(row.iloc[0]['description']) else ""
        config["pipeline_metadata"]["input"] = str(row.iloc[0]['input']) if 'input' in row.columns and pd.notna(row.iloc[0]['input']) else "EXCEL"
        config["pipeline_metadata"]["output"] = str(row.iloc[0]['output']) if 'output' in row.columns and pd.notna(row.iloc[0]['output']) else "XLSX"

        # Población desde config_json
        if 'config_json' in row.columns:
            json_config = safe_text_to_json(row.iloc[0]['config_json'])
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
        
        if pipeline_id == 0 or pipeline_id not in df['pipeline_id'].values:
            is_new = True
            new_name = metadata.get("name", "Nuevo Proceso")
            if new_name in df['pipeline'].values:
                return {"error": f"Ya existe un proceso llamado '{new_name}'. Por favor elige otro nombre."}

            if len(df) > 0:
                target_id = int(df['pipeline_id'].max()) + 1
            else:
                target_id = 1
        
        steps_list = config.get("pipeline", [])
        steps_text = " -> ".join([s.get("step", "Sin nombre") for s in steps_list])
        config_json_text = safe_json_to_text(config)

        if is_new:
            new_row = {
                'pipeline_id': target_id,
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
            if metadata.get("name"): df.loc[df['pipeline_id'] == target_id, 'pipeline'] = metadata.get("name")
            if metadata.get("description"): df.loc[df['pipeline_id'] == target_id, 'description'] = metadata.get("description")
            df.loc[df['pipeline_id'] == target_id, 'steps'] = steps_text
            df.loc[df['pipeline_id'] == target_id, 'config_json'] = config_json_text
            if metadata.get("input"): df.loc[df['pipeline_id'] == target_id, 'input'] = str(metadata.get("input")).upper()
            if metadata.get("output"): df.loc[df['pipeline_id'] == target_id, 'output'] = str(metadata.get("output")).upper()
        
        df.to_excel(PIPELINES_DB_PATH, index=False)
        return {"status": "success", "message": f"Configuración guardada para el ID {target_id}", "new_id": target_id}
    except Exception as e:
        return {"error": str(e)}

@router.post("/{pipeline_id}/config")
async def save_pipeline_config_endpoint(pipeline_id: int, config: dict):
    return await save_pipeline_config_logic(pipeline_id, config)

@router.patch("/{pipeline_id}/hidden")
async def toggle_pipeline_hidden(pipeline_id: int, body: dict):
    try:
        df = pd.read_excel(PIPELINES_DB_PATH)
        if pipeline_id not in df['pipeline_id'].values:
            return {"error": "Pipeline no encontrado"}
        if 'hidden' not in df.columns:
            df['hidden'] = False
        df.loc[df['pipeline_id'] == pipeline_id, 'hidden'] = body.get("hidden", False)
        df.to_excel(PIPELINES_DB_PATH, index=False)
        return {"status": "success", "hidden": body.get("hidden", False)}
    except Exception as e:
        return {"error": str(e)}

@router.delete("/{pipeline_id}")
async def delete_pipeline(pipeline_id: int):
    try:
        df = pd.read_excel(PIPELINES_DB_PATH)
        if pipeline_id not in df['pipeline_id'].values:
            return {"error": "Pipeline no encontrado"}
        
        df = df[df['pipeline_id'] != pipeline_id]
        df.to_excel(PIPELINES_DB_PATH, index=False)

        uploads_dir = UPLOADS_DIR / str(pipeline_id)
        if uploads_dir.exists():
            shutil.rmtree(uploads_dir)
            
        return {"status": "success", "message": f"Pipeline {pipeline_id} eliminado correctamente"}
    except Exception as e:
        return {"error": str(e)}
