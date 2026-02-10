
import pandas as pd
import json
from pathlib import Path

def update_templates_with_json_column():
    db_path = Path('data/database/templates.xlsx')
    templates_dir = Path('data/database/reports_templates')
    
    if not db_path.exists():
        print(f"Error: {db_path} not found.")
        return

    print(f"Reading {db_path}...")
    df = pd.read_excel(db_path)
    
    def get_minified_json(row):
        config_path = row.get('config_path')
        if pd.isna(config_path):
            return ""
            
        fpath = templates_dir / str(config_path)
        if fpath.exists():
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Minify with separators=(',', ':')
                return json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            except Exception as e:
                print(f"Error processing {fpath}: {e}")
                return ""
        return ""

    print("Generating minified JSON strings...")
    df['config_json'] = df.apply(get_minified_json, axis=1)
    
    print(f"Saving updated Excel to {db_path}...")
    df.to_excel(db_path, index=False)
    print("Update complete.")

if __name__ == "__main__":
    update_templates_with_json_column()
