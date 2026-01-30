import json
from pathlib import Path
from typing import Dict, Type, List, Optional
import re
from rgenerator.etl.core.context import RunContext
from rgenerator.etl.core.step import Step
import rgenerator.etl.core.pipeline_steps as ps
import os

# Diccionario que mapea el nombre del paso en JSON a la clase correspondiente en Python
STEP_MAPPING: Dict[str, Type[Step]] = {
    "InitRun": ps.InitRun,
    "LoadConfig": ps.LoadConfig,
    "DiscoverInputs": ps.DiscoverInputs,
    "RunExcelETL": ps.RunExcelETL,
    "EnrichWithContext": ps.EnrichWithContext,
    "ExportConsolidatedExcel": ps.ExportConsolidatedExcel,
    "DeleteTempFiles": ps.DeleteTempFiles,
    "RequestUserFiles": ps.RequestUserFiles
}

def load_pipeline_from_json(json_path: str | Path) -> tuple[RunContext, List[Step]]:
    """
    Lee un archivo JSON y construye el contexto y la lista de pasos (pipeline).
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de pipeline: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 1. Configurar el contexto
    # Si base_dir es relativo en el JSON, lo resolvemos respecto a la raíz del proyecto
    json_base_dir = config.get("context", {}).get("base_dir", ".")
    ctx = RunContext(base_dir=Path(json_base_dir))

    # Intentar extraer workflow_id del nombre del archivo (ej: pipeline001.json)
    match = re.search(r'pipeline(\d+)\.json', path.name)
    if match:
        ctx.workflow_id = int(match.group(1))

    # 2. Construir el pipeline
    pipeline = []
    for step_config in config.get("pipeline", []):
        step_name = step_config.get("step")
        params = step_config.get("params", {})
        
        if step_name not in STEP_MAPPING:
            raise ValueError(f"Paso desconocido en el pipeline: {step_name}")
        
        # Instanciar el paso con sus parámetros
        step_class = STEP_MAPPING[step_name]
        
        try:
            step_instance = step_class(**params)
            pipeline.append(step_instance)
        except TypeError as e:
            raise TypeError(f"Error al instanciar el paso '{step_name}' con parámetros {params}: {e}")

    return ctx, pipeline

class PipelineRunner:
    def __init__(self, json_path: str | Path):
        self.ctx, self.pipeline = load_pipeline_from_json(json_path)
        self.current_step_index = 0
        self.total_steps = len(self.pipeline)
        self.status = "IDLE" # IDLE, RUNNING, COMPLETED, FAILED

    def step(self):
        """Ejecuta el siguiente paso."""
        if self.current_step_index >= self.total_steps:
            self.status = "COMPLETED"
            return {"status": "completed", "message": "Pipeline completed"}

        step = self.pipeline[self.current_step_index]
        self.status = "RUNNING"
        
        try:
            print(f"-- Running step {self.current_step_index + 1}/{self.total_steps}: {step.__class__.__name__}")
            step.run(self.ctx)
            
            self.current_step_index += 1
            if self.current_step_index >= self.total_steps:
                self.status = "COMPLETED"
            
            return {
                "status": "success", 
                "step_index": self.current_step_index - 1, # Index executed
                "next_index": self.current_step_index,
                "step_name": step.__class__.__name__,
                "artifacts": list(self.ctx.artifacts.keys()),
                "finished": self.status == "COMPLETED"
            }
        except Exception as e:
            self.status = "FAILED"
            raise e

    def run_all(self):
        """Ejecuta todos los pasos restantes."""
        results = []
        while self.current_step_index < self.total_steps:
            res = self.step()
            results.append(res)
        return results

def run_pipeline(json_path: str | Path):
    """
    Ejecuta un pipeline completo desde un archivo JSON.
    Wrapper para compatibilidad con código existente.
    """
    try:
        runner = PipelineRunner(json_path)
        runner.run_all()
        return {"status": "success", "message": "Pipeline ejecutado correctamente", "artifacts": list(runner.ctx.artifacts.keys())}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Test rápido si se ejecuta directamente
    import os
    # Ajustar path si es necesario
    test_path = Path(__file__).parents[3] / "data" / "database" / "pipelines" / "pipeline002.json"
    if test_path.exists():
        run_pipeline(test_path)
    else:
        print(f"No se encontró el archivo de test en {test_path}")
