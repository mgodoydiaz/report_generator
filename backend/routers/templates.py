from fastapi import APIRouter
import pandas as pd
import json
from config import TEMPLATES_DB_PATH, TEMPLATES_DIR

router = APIRouter(prefix="/api/templates", tags=["templates"])

@router.get("/")
@router.get("", include_in_schema=False)
async def get_templates():
    try:
        if not TEMPLATES_DB_PATH.exists():
            return []
        df = pd.read_excel(TEMPLATES_DB_PATH)
        
        # Reemplazar NaN con None
        df = df.where(pd.notnull(df), None)
        
        if 'updated_at' in df.columns:
            df['updated_at'] = df['updated_at'].fillna("").astype(str)
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

@router.get("/{template_id}/config")
async def get_template_config(template_id: int):
    try:
        df = pd.read_excel(TEMPLATES_DB_PATH)
        row = df[df['id_template'] == template_id]
        if row.empty:
            return {"error": "Plantilla no encontrada"}
        
        config_path = row.iloc[0]['config_path']
        full_path = TEMPLATES_DIR / config_path
        
        if not full_path.exists():
            return {"error": "Archivo de configuración no encontrado"}
            
        with open(full_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        return {
            "name": str(row.iloc[0]['name']),
            "description": str(row.iloc[0]['description']),
            "type": str(row.iloc[0]['type']),
            "variables_documento": config.get("variables_documento", {}),
            "secciones_fijas": config.get("secciones_fijas", []),
            "secciones_dinamicas": config.get("secciones_dinamicas", []),
            "etlParams": config.get("etlParams", [])
        }
    except Exception as e:
        return {"error": str(e)}

@router.post("/config")
async def create_template_config(config: dict):
    return await save_template_config_logic(template_id=0, config=config)

async def save_template_config_logic(template_id: int, config: dict):
    try:
        df = pd.read_excel(TEMPLATES_DB_PATH)
        is_new = template_id == 0 or template_id not in df['id_template'].values
        
        target_id = template_id
        if is_new:
            target_id = int(df['id_template'].max()) + 1 if len(df) > 0 else 1
            
        filename = f"template{target_id:03d}.json"
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = TEMPLATES_DIR / filename
        
        json_data = {
            "variables_documento": config.get("variables_documento", {}),
            "secciones_fijas": config.get("secciones_fijas", []),
            "secciones_dinamicas": config.get("secciones_dinamicas", []),
            "etlParams": config.get("etlParams", [])
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
            
        now_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        if is_new:
            new_row = {
                'id_template': target_id,
                'name': config.get("name", "Nueva Plantilla"),
                'description': config.get("description", ""),
                'type': config.get("type", "Reporte"),
                'config_path': filename,
                'updated_at': now_str
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            df.loc[df['id_template'] == target_id, 'name'] = config.get("name")
            df.loc[df['id_template'] == target_id, 'description'] = config.get("description")
            df.loc[df['id_template'] == target_id, 'type'] = config.get("type")
            df.loc[df['id_template'] == target_id, 'updated_at'] = now_str
            
        df.to_excel(TEMPLATES_DB_PATH, index=False)
        return {"status": "success", "message": f"Plantilla {target_id} guardada", "new_id": target_id}
    except Exception as e:
        return {"error": str(e)}

@router.post("/{template_id}/config")
async def save_template_config_endpoint(template_id: int, config: dict):
    return await save_template_config_logic(template_id, config)
