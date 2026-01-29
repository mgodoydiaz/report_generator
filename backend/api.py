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

# Obtener la ruta del archivo evaluaciones.xlsx
# Asumiendo que se ejecuta desde la raíz del proyecto o desde la carpeta backend
BASE_DIR = Path(__file__).resolve().parent.parent
EXCEL_PATH = BASE_DIR / "data" / "database" / "evaluaciones.xlsx"

@app.get("/api/workflows")
async def get_workflows():
    try:
        if not EXCEL_PATH.exists():
            return {"error": f"Archivo no encontrado en {EXCEL_PATH}"}
        
        # Leer el Excel
        df = pd.read_excel(EXCEL_PATH)
        
        # Convertir fechas a string para JSON si es necesario
        if 'last_run' in df.columns:
            df['last_run'] = df['last_run'].astype(str)
            
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
        # Mapeo de IDs a archivos de pipeline (esto podría estar en una DB o en el Excel)
        # Por ahora, mapeamos el id 2 al archivo pipeline002.json
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
        pipeline_filename = f"pipeline{workflow_id:03d}.json"
        pipeline_path = BASE_DIR / "data" / "database" / "pipelines" / pipeline_filename
        
        if not pipeline_path.exists():
            # Devolver una estructura vacía si no existe
            return {
                "workflow_metadata": {"name": "", "description": ""},
                "context": {"base_dir": "./backend/tests"},
                "pipeline": []
            }
        
        import json
        with open(pipeline_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/workflows/{workflow_id}/config")
async def save_workflow_config(workflow_id: int, config: dict):
    try:
        pipeline_filename = f"pipeline{workflow_id:03d}.json"
        pipeline_dir = BASE_DIR / "data" / "database" / "pipelines"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        pipeline_path = pipeline_dir / pipeline_filename
        
        import json
        with open(pipeline_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        # También actualizar el Excel si el nombre o descripción cambiaron
        try:
            df = pd.read_excel(EXCEL_PATH)
            metadata = config.get("workflow_metadata", {})
            if workflow_id in df['id_evaluation'].values:
                if metadata.get("name"):
                    df.loc[df['id_evaluation'] == workflow_id, 'evaluation'] = metadata.get("name")
                if metadata.get("description"):
                    df.loc[df['id_evaluation'] == workflow_id, 'description'] = metadata.get("description")
                df.to_excel(EXCEL_PATH, index=False)
        except Exception as ex:
            print(f"Error actualizando Excel tras guardado de config: {ex}")

        return {"status": "success", "message": f"Configuración guardada en {pipeline_filename}"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Agregamos reload=True para desarrollo
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
