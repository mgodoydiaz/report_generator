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
        print(data)
        return data
    except Exception as e:
        return {"error": str(e)}

from rgenerator.tooling.pipeline_tools import run_pipeline

@app.post("/api/workflows/{workflow_id}/run")
async def execute_workflow(workflow_id: int):
    try:
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
                df.loc[df['id_evaluation'] == workflow_id, 'last_run'] = pd.Timestamp.now().strftime('%Y-%m-%d')
                df.to_excel(EXCEL_PATH, index=False)
            except Exception as ex:
                print(f"Error actualizando Excel: {ex}")

        return result
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Agregamos reload=True para desarrollo
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
