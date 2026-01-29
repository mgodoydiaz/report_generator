from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pathlib import Path
import os

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
EXCEL_PATH = BASE_DIR / "data" / "database" / "workflows.xlsx"

@app.get("/api/workflows")
async def get_workflows():
    try:
        if not EXCEL_PATH.exists():
            return {"error": f"Archivo no encontrado en {EXCEL_PATH}"}
        
        # Leer el Excel
        df = pd.read_excel(EXCEL_PATH)
        
        # Convertir fechas a string para JSON si es necesario
        if 'last_run' in df.columns:
            df['last_run'] = df['last_run'].fillna("").astype(str)
            
        # Convertir a lista de diccionarios
        data = df.to_dict(orient="records")
        return data
    except Exception as e:
        return {"error": str(e)}

from rgenerator.tooling.pipeline_tools import run_pipeline

@app.post("/api/workflows/{workflow_id}/run")
async def execute_workflow(workflow_id: int):
    try:
        os.system("cls")
        pipeline_filename = f"pipeline{workflow_id:03d}.json"
        pipeline_path = BASE_DIR / "data" / "database" / "pipelines" / pipeline_filename
        
        if not pipeline_path.exists():
            return {"error": f"No se encontró la configuración del pipeline para el ID {workflow_id}"}
        
        # Ejecutar el pipeline
        result = run_pipeline(pipeline_path)
        
        # Actualizar la fecha de última ejecución en el Excel si fue exitoso
        if result["status"] == "success":
            try:
                df = pd.read_excel(EXCEL_PATH)
                df.loc[df['id_evaluation'] == workflow_id, 'last_run'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                df.to_excel(EXCEL_PATH, index=False)
            except Exception as ex:
                print(f"Error actualizando Excel: {ex}")

        return result
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/workflows/{workflow_id}/config")
async def get_workflow_config(workflow_id: int):
    try:
        # 1. Buscar metadatos en el Excel
        excel_metadata = {"name": "", "description": "", "output": "XLSX"}
        if EXCEL_PATH.exists():
            df = pd.read_excel(EXCEL_PATH)
            row = df[df['id_evaluation'] == workflow_id]
            if not row.empty:
                excel_metadata["name"] = str(row.iloc[0]['evaluation'])
                excel_metadata["description"] = str(row.iloc[0]['description']) if pd.notna(row.iloc[0]['description']) else ""
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
            import json
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
        df = pd.read_excel(EXCEL_PATH)
        metadata = config.get("workflow_metadata", {})
        
        target_id = workflow_id
        is_new = False
        
        # Si workflow_id es 0 o no está en el Excel, es uno nuevo
        if workflow_id == 0 or workflow_id not in df['id_evaluation'].values:
            is_new = True
            # ID correlativo
            if len(df) > 0:
                target_id = int(df['id_evaluation'].max()) + 1
            else:
                target_id = 1
        
        pipeline_filename = f"pipeline{target_id:03d}.json"
        pipeline_dir = BASE_DIR / "data" / "database" / "pipelines"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        pipeline_path = pipeline_dir / pipeline_filename
        
        import json
        with open(pipeline_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        # Actualizar o insertar en el Excel
        try:
            if is_new:
                new_row = {
                    'id_evaluation': target_id,
                    'evaluation': metadata.get("name", "Nuevo Workflow"),
                    'description': metadata.get("description", ""),
                    'output': metadata.get("output", "XLSX"),
                    'last_run': ''
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                if metadata.get("name"):
                    df.loc[df['id_evaluation'] == target_id, 'evaluation'] = metadata.get("name")
                if metadata.get("description"):
                    df.loc[df['id_evaluation'] == target_id, 'description'] = metadata.get("description")
                if metadata.get("output"):
                    df.loc[df['id_evaluation'] == target_id, 'output'] = metadata.get("output")
            
            df.to_excel(EXCEL_PATH, index=False)
        except Exception as ex:
            print(f"Error actualizando Excel tras guardado de config: {ex}")

        return {"status": "success", "message": f"Configuración guardada para el ID {target_id}", "new_id": target_id}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Agregamos reload=True para desarrollo
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
