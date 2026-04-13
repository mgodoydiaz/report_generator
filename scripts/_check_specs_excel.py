import pandas as pd
df = pd.read_excel('data/database/specs.xlsx')
print("Columnas:", df.columns.tolist())
print()
for _, row in df.iterrows():
    print(f"id={row.get('id_spec')} name={row.get('name')}")
    print(f"  config_json={str(row.get('config_json'))[:300]}")
    print()
