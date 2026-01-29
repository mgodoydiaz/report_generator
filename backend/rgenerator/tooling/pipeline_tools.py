import json
from pathlib import Path
from typing import Dict, Type, List
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
    "DeleteTempFiles": ps.DeleteTempFiles
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

    # 2. Construir el pipeline
    pipeline = []
    for step_config in config.get("pipeline", []):
        step_name = step_config.get("step")
        params = step_config.get("params", {})
        
        if step_name not in STEP_MAPPING:
            raise ValueError(f"Paso desconocido en el pipeline: {step_name}")
        
        # Instanciar el paso con sus parámetros
        # Nota: La mayoría de los pasos en pipeline_steps.py usan los argumentos en el __init__
        step_class = STEP_MAPPING[step_name]
        
        try:
            step_instance = step_class(**params)
            pipeline.append(step_instance)
        except TypeError as e:
            raise TypeError(f"Error al instanciar el paso '{step_name}' con parámetros {params}: {e}")

    return ctx, pipeline

def run_pipeline(json_path: str | Path):
    """
    Ejecuta un pipeline completo desde un archivo JSON.
    """
    try:
        ctx, pipeline = load_pipeline_from_json(json_path)
        
        for step in pipeline:
            print()
            print("-"*20)
            print(os.getcwd())
            print(step.__class__.__name__)
            step.run(ctx)
            ctx.show_attrs()
            
        return {"status": "success", "message": "Pipeline ejecutado correctamente", "artifacts": list(ctx.artifacts.keys())}
    
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
