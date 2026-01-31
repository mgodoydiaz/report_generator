from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pathlib import Path
import os
import shutil
import json
from typing import List, Dict

app = FastAPI()

# Configurar CORS para permitir peticiones desde el frontend (Vite suele usar el puerto 5173 o 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica el origen exacto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Obtener la ruta del archivo workflows.xlsx
BASE_DIR = Path(__file__).resolve().parent.parent
WORKFLOWS_EXCEL_PATH = BASE_DIR / "data" / "database" / "pipelines.xlsx"
TEMPLATES_EXCEL_PATH = BASE_DIR / "data" / "database" / "templates.xlsx"
TEMPLATES_DIR = BASE_DIR / "data" / "database" / "reports_templates"

# Store active sessions in memory
from rgenerator.tooling.pipeline_tools import PipelineRunner, run_pipeline
from rgenerator.tooling.data_tools import safe_json_to_text, safe_text_to_json



ACTIVE_RUNNERS: Dict[int, PipelineRunner] = {}

@app.get("/api/workflows")
async def get_workflows():
    try:
        if not WORKFLOWS_EXCEL_PATH.exists():
            return {"error": f"Archivo no encontrado en {WORKFLOWS_EXCEL_PATH}"}
        
        # Leer el Excel
        df = pd.read_excel(WORKFLOWS_EXCEL_PATH)
        
        # Convertir fechas a string para JSON si es necesario
        if 'last_run' in df.columns:
            df['last_run'] = df['last_run'].fillna("").astype(str)
            
        # Convertir a lista de diccionarios
        data = df.to_dict(orient="records")
        return data
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/workflows/{workflow_id}/upload")
async def upload_workflow_files(workflow_id: int, input_key: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        upload_dir = BASE_DIR / "data" / "database" / "pipelines" / "uploads" / str(workflow_id) / input_key
        # Limpiar directorio previo para este input_key si existe para evitar mezclar archivos de ejecuciones fallidas
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

def _update_last_run(workflow_id):
    try:
        df = pd.read_excel(WORKFLOWS_EXCEL_PATH)
        df.loc[df['id_evaluation'] == workflow_id, 'last_run'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        df.to_excel(WORKFLOWS_EXCEL_PATH, index=False)
    except Exception as ex:
        print(f"Error actualizando Excel: {ex}")

@app.post("/api/workflows/{workflow_id}/run")
async def execute_workflow(workflow_id: int):
    """Executes the workflow completely (Fast Forward). Resumes if active session exists."""
    try:
        os.system("cls")
        
        # Use active runner if exists, otherwise create new
        if workflow_id in ACTIVE_RUNNERS:
            runner = ACTIVE_RUNNERS[workflow_id]
            # Run remaining steps
            runner.run_all()
            result = {"status": "success", "message": "Pipeline completado", "artifacts": list(runner.ctx.artifacts.keys())}
            # Clean up
            del ACTIVE_RUNNERS[workflow_id]
        else:
            # Traditional clean run
            pipeline_filename = f"pipeline{workflow_id:03d}.json"
            pipeline_path = BASE_DIR / "data" / "database" / "pipelines" / pipeline_filename
            
            if not pipeline_path.exists():
                return {"error": f"No se encontró la configuración del pipeline para el ID {workflow_id}"}
                
            result = run_pipeline(pipeline_path)

        if result["status"] == "success":
            _update_last_run(workflow_id)

        return result
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/workflows/{workflow_id}/step")
async def execute_workflow_step(workflow_id: int):
    """Executes the next step of the workflow."""
    try:
        if workflow_id not in ACTIVE_RUNNERS:
            # Initialize session
            pipeline_filename = f"pipeline{workflow_id:03d}.json"
            pipeline_path = BASE_DIR / "data" / "database" / "pipelines" / pipeline_filename
            
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
            del ACTIVE_RUNNERS[workflow_id] # Clean on error
        return {"error": str(e)}

@app.post("/api/workflows/{workflow_id}/reset")
async def reset_workflow_session(workflow_id: int):
    """Clears any active session for this workflow."""
    if workflow_id in ACTIVE_RUNNERS:
        del ACTIVE_RUNNERS[workflow_id]
    return {"status": "success"}

@app.get("/api/workflows/{workflow_id}/config")
async def get_workflow_config(workflow_id: int):
    try:
        # 1. Buscar metadatos en el Excel
        excel_metadata = {"name": "", "description": "", "input": "EXCEL", "output": "XLSX"}
        if WORKFLOWS_EXCEL_PATH.exists():
            df = pd.read_excel(WORKFLOWS_EXCEL_PATH)
            row = df[df['id_evaluation'] == workflow_id]
            if not row.empty:
                excel_metadata["name"] = str(row.iloc[0]['pipeline'])
                excel_metadata["description"] = str(row.iloc[0]['description']) if pd.notna(row.iloc[0]['description']) else ""
                excel_metadata["input"] = str(row.iloc[0]['input']) if 'input' in row.columns and pd.notna(row.iloc[0]['input']) else "EXCEL"
                excel_metadata["output"] = str(row.iloc[0]['output']) if pd.notna(row.iloc[0]['output']) else "XLSX"

        # 2. Buscar configuración técnica en el JSON
        pipeline_filename = f"pipeline{workflow_id:03d}.json"
        pipeline_path = BASE_DIR / "data" / "database" / "pipelines" / pipeline_filename
        
        config = {
            "workflow_metadata": {"name": excel_metadata["name"], "description": excel_metadata["description"], "output": excel_metadata["output"]},
            "context": {"base_dir": "./backend/tests"},
            "pipeline": []
        }

        if pipeline_path.exists():
            with open(pipeline_path, 'r', encoding='utf-8') as f:
                json_config = json.load(f)
                # El JSON manda sobre la estructura técnica, pero el Excel sobre la metadata visible
                config["context"] = json_config.get("context", config["context"])
                config["pipeline"] = json_config.get("pipeline", config["pipeline"])
                # Fusionar metadata, priorizando el Excel para nombre/desc si vienen de ahí
                config["workflow_metadata"].update(json_config.get("workflow_metadata", {}))
                # Asegurar que los valores del Excel se mantienen si el JSON no los tiene
                config["workflow_metadata"]["name"] = excel_metadata["name"] or config["workflow_metadata"].get("name")
                config["workflow_metadata"]["description"] = excel_metadata["description"] or config["workflow_metadata"].get("description")
                config["workflow_metadata"]["input"] = excel_metadata["input"]
                config["workflow_metadata"]["output"] = excel_metadata["output"]

        return config
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/workflows/config") # Para nuevos workflows
async def create_workflow_config(config: dict):
    return await save_workflow_config(workflow_id=0, config=config)

@app.post("/api/workflows/{workflow_id}/config")
async def save_workflow_config(workflow_id: int, config: dict):
    try:
        df = pd.read_excel(WORKFLOWS_EXCEL_PATH)
        metadata = config.get("workflow_metadata", {})
        
        target_id = workflow_id
        is_new = False
        
        # Si workflow_id es 0 o no está en el Excel, es uno nuevo
        if workflow_id == 0 or workflow_id not in df['id_evaluation'].values:
            is_new = True
            
            # Comprobar si el nombre ya existe
            new_name = metadata.get("name", "Nuevo Proceso")
            if new_name in df['pipeline'].values:
                return {"error": f"Ya existe un proceso llamado '{new_name}'. Por favor elige otro nombre."}

            # ID correlativo
            if len(df) > 0:
                target_id = int(df['id_evaluation'].max()) + 1
            else:
                target_id = 1
        
        pipeline_filename = f"pipeline{target_id:03d}.json"
        pipeline_dir = BASE_DIR / "data" / "database" / "pipelines"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        pipeline_path = pipeline_dir / pipeline_filename
        
        with open(pipeline_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        # Preparar resumen de pasos y el JSON completo para el Excel
        steps_list = config.get("pipeline", [])
        steps_text = " -> ".join([s.get("step", "Sin nombre") for s in steps_list])
        config_json_text = safe_json_to_text(config)

        # Actualizar o insertar en el Excel
        try:
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
                if metadata.get("name"):
                    df.loc[df['id_evaluation'] == target_id, 'pipeline'] = metadata.get("name")
                if metadata.get("description"):
                    df.loc[df['id_evaluation'] == target_id, 'description'] = metadata.get("description")
                
                df.loc[df['id_evaluation'] == target_id, 'steps'] = steps_text
                df.loc[df['id_evaluation'] == target_id, 'config_json'] = config_json_text
                
                if metadata.get("input"):
                    df.loc[df['id_evaluation'] == target_id, 'input'] = str(metadata.get("input")).upper()
                if metadata.get("output"):
                    df.loc[df['id_evaluation'] == target_id, 'output'] = str(metadata.get("output")).upper()
            
            df.to_excel(WORKFLOWS_EXCEL_PATH, index=False)
        except Exception as ex:
            print(f"Error actualizando Excel tras guardado de config: {ex}")

        return {"status": "success", "message": f"Configuración guardada para el ID {target_id}", "new_id": target_id}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: int):
    try:
        # 1. Eliminar del Excel
        df = pd.read_excel(WORKFLOWS_EXCEL_PATH)
        if workflow_id not in df['id_evaluation'].values:
            return {"error": "Workflow no encontrado"}
        
        df = df[df['id_evaluation'] != workflow_id]
        df.to_excel(WORKFLOWS_EXCEL_PATH, index=False)
        
        # 2. Eliminar archivo JSON
        pipeline_filename = f"pipeline{workflow_id:03d}.json"
        pipeline_path = BASE_DIR / "data" / "database" / "pipelines" / pipeline_filename
        if pipeline_path.exists():
            os.remove(pipeline_path)
            
        # 3. Opcional: Eliminar carpeta de subidas
        uploads_dir = BASE_DIR / "data" / "database" / "pipelines" / "uploads" / str(workflow_id)
        if uploads_dir.exists():
            shutil.rmtree(uploads_dir)
            
        return {"status": "success", "message": f"Workflow {workflow_id} eliminado correctamente"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/templates")
async def get_templates():
    try:
        if not TEMPLATES_EXCEL_PATH.exists():
            return []
        df = pd.read_excel(TEMPLATES_EXCEL_PATH)
        if 'updated_at' in df.columns:
            df['updated_at'] = df['updated_at'].fillna("").astype(str)
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/templates/{template_id}/config")
async def get_template_config(template_id: int):
    try:
        df = pd.read_excel(TEMPLATES_EXCEL_PATH)
        row = df[df['id_template'] == template_id]
        if row.empty:
            return {"error": "Plantilla no encontrada"}
        
        config_path = row.iloc[0]['config_path']
        full_path = TEMPLATES_DIR / config_path
        
        if not full_path.exists():
            return {"error": "Archivo de configuración no encontrado"}
            
        import json
        with open(full_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        return {
            "name": str(row.iloc[0]['name']),
            "description": str(row.iloc[0]['description']),
            "type": str(row.iloc[0]['type']),
            "variables_documento": config.get("variables_documento", {}),
            "secciones_fijas": config.get("secciones_fijas", []),
            "secciones_dinamicas": config.get("secciones_dinamicas", [])
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/templates/config")
async def create_template_config(config: dict):
    return await save_template_config(template_id=0, config=config)

@app.post("/api/templates/{template_id}/config")
async def save_template_config(template_id: int, config: dict):
    try:
        df = pd.read_excel(TEMPLATES_EXCEL_PATH)
        is_new = template_id == 0 or template_id not in df['id_template'].values
        
        target_id = template_id
        if is_new:
            target_id = int(df['id_template'].max()) + 1 if len(df) > 0 else 1
            
        filename = f"template{target_id:03d}.json"
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = TEMPLATES_DIR / filename
        
        # Guardar JSON (solo la parte técnica)
        json_data = {
            "variables_documento": config.get("variables_documento", {}),
            "secciones_fijas": config.get("secciones_fijas", []),
            "secciones_dinamicas": config.get("secciones_dinamicas", [])
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
            
        # Actualizar Excel
        now_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        if is_new:
            new_row = {
                'id_template': target_id,
                'name': config.get("name", "Nueva Plantilla"),
                'description': config.get("description", ""),
                'type': config.get("type", "Reporte"),
                'config_path': filename,
                'updated_at': now_str
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            df.loc[df['id_template'] == target_id, 'name'] = config.get("name")
            df.loc[df['id_template'] == target_id, 'description'] = config.get("description")
            df.loc[df['id_template'] == target_id, 'type'] = config.get("type")
            df.loc[df['id_template'] == target_id, 'updated_at'] = now_str
            
        df.to_excel(TEMPLATES_EXCEL_PATH, index=False)
        return {"status": "success", "message": f"Plantilla {target_id} guardada", "new_id": target_id}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Agregamos reload=True para desarrollo
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
