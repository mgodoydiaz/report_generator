import pandas as pd
import json
from pathlib import Path

BASE_DIR = Path(".")
PIPELINES_DB = BASE_DIR / "data/database/pipelines.xlsx"
SPECS_DB = BASE_DIR / "data/database/specs.xlsx"

# 1. Read Pipelines
df_pipe = pd.read_excel(PIPELINES_DB)
row_idx = df_pipe.index[df_pipe['id_evaluation'] == 16][0]
pipeline_config = json.loads(df_pipe.at[row_idx, 'config_json'])

# Find GenerateGraphics step and extract charts_schema
charts_schema = []
new_pipeline_steps = []
for step in pipeline_config['pipeline']:
    if step['step'] == 'GenerateGraphics':
        charts_schema = step['params'].get('charts_schema', [])
        # We replace the GenerateGraphics step with two nodes:
        # LoadConfigFromSpec (ID depends on our newly appended row below)
        new_pipeline_steps.append({
            "step": "LoadConfigFromSpec",
            "params": {"spec_id": 5}
        })
        new_pipeline_steps.append({
            "step": "GenerateGraphics",
            "params": {}
        })
    else:
        new_pipeline_steps.append(step)

pipeline_config['pipeline'] = new_pipeline_steps

# Save updated pipelines
df_pipe.at[row_idx, 'config_json'] = json.dumps(pipeline_config, indent=4)
# Update steps string representation
steps_str = " -> ".join([s['step'] for s in new_pipeline_steps])
df_pipe.at[row_idx, 'steps'] = steps_str
df_pipe.to_excel(PIPELINES_DB, index=False)

# 2. Add New Spec (Only if it hasn't been added already)
df_specs = pd.read_excel(SPECS_DB)
if "Gráficos SIMCE Lenguaje" not in df_specs['name'].values:
    new_spec_id = int(df_specs['id_spec'].max() + 1) if len(df_specs) > 0 else 1
    
    spec_config_json = {
        "metadata": {
            "id": "simce_lenguaje_graficos",
            "title": "Gráficos SIMCE Lenguaje",
            "evaluation": "simce_lenguaje"
        },
        "charts_schema": charts_schema
    }
    
    new_spec = pd.DataFrame([{
        "id_spec": new_spec_id,
        "name": "Gráficos SIMCE Lenguaje",
        "description": "Especificación extraída de la pipeline",
        "type": "Gráficos",
        "config_json": json.dumps(spec_config_json, ensure_ascii=False)
    }])

    # Align columns
    for col in df_specs.columns:
        if col not in new_spec.columns:
            new_spec[col] = pd.NA

    df_specs = pd.concat([df_specs, new_spec], ignore_index=True)
    df_specs.to_excel(SPECS_DB, index=False)
    print(f"Migración completa. Nuevo Spec ID creado: {new_spec_id}")
else:
    print("El spec ya había sido creado anteriormente.")
