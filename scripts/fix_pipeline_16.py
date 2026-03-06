import pandas as pd
import json
from pathlib import Path

BASE_DIR = Path(".")
PIPELINES_DB = BASE_DIR / "data/database/pipelines.xlsx"

df_pipe = pd.read_excel(PIPELINES_DB)
row_idx = df_pipe.index[df_pipe['id_evaluation'] == 16][0]
pipeline_config = json.loads(df_pipe.at[row_idx, 'config_json'])

# Filter out LoadConfigFromSpec duplicates
new_pipeline = []
seen_spec_load = False
for step in pipeline_config['pipeline']:
    if step['step'] == 'LoadConfigFromSpec':
        if not seen_spec_load:
            new_pipeline.append(step)
            seen_spec_load = True
    else:
        new_pipeline.append(step)

pipeline_config['pipeline'] = new_pipeline

df_pipe.at[row_idx, 'config_json'] = json.dumps(pipeline_config, indent=4)
steps_str = " -> ".join([s['step'] for s in new_pipeline])
df_pipe.at[row_idx, 'steps'] = steps_str
df_pipe.to_excel(PIPELINES_DB, index=False)
print("Pipeline 16 fixed.")
