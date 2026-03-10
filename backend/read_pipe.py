import pandas as pd
import json
import math

df = pd.read_excel('../data/database/pipelines.xlsx')
row = df[df['pipeline_id'] == 14].iloc[0]

def clean_value(v):
    if pd.isna(v):
        return None
    if isinstance(v, (pd.Timestamp, pd.Timedelta)):
        return str(v)
    if 'int' in str(type(v)):
        return int(v)
    if 'float' in str(type(v)):
        return float(v)
    return v

data = {c: clean_value(row[c]) for c in df.columns}
with open('temp.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
