from fastapi import APIRouter
import pandas as pd
import json
from config import SPECS_DB_PATH
from rgenerator.tooling.data_tools import get_json_safe_df, safe_text_to_json

router = APIRouter(prefix="/api/specs", tags=["specs"])

@router.get("/")
@router.get("", include_in_schema=False)
async def get_specs():
    try:
        if not SPECS_DB_PATH.exists():
            return []
        df = pd.read_excel(SPECS_DB_PATH)
        df = get_json_safe_df(df)
        
        # Asegurar que updated_at sea string para el frontend
        if 'updated_at' in df.columns:
            df['updated_at'] = df['updated_at'].apply(lambda x: str(x) if x is not None else "")
            
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

@router.get("/{spec_id}/config")
async def get_spec_config(spec_id: int):
    try:
        if not SPECS_DB_PATH.exists():
             return {"error": "Base de datos de especificaciones no encontrada"}

        df = pd.read_excel(SPECS_DB_PATH)
        row = df[df['id_spec'] == spec_id]
        if row.empty:
            return {"error": "Especificación no encontrada"}
        
        # Leer desde config_json
        config_raw = row.iloc[0].get('config_json')
        config = safe_text_to_json(config_raw) if pd.notna(config_raw) else {}
        
        return {
            "name": str(row.iloc[0]['name']) if pd.notna(row.iloc[0]['name']) else "Sin nombre",
            "description": str(row.iloc[0]['description']) if pd.notna(row.iloc[0]['description']) else "",
            "type": str(row.iloc[0]['type']) if pd.notna(row.iloc[0]['type']) else "Reporte",
            **config
        }
    except Exception as e:
        return {"error": str(e)}

@router.post("/config")
async def create_spec_config(config: dict):
    return await save_spec_config_logic(spec_id=0, config=config)

async def save_spec_config_logic(spec_id: int, config: dict):
    try:
        if not SPECS_DB_PATH.exists():
             # Crear archivo vacío con headers si no existe
             pd.DataFrame(columns=['id_spec', 'name', 'description', 'type', 'config_json', 'updated_at']).to_excel(SPECS_DB_PATH, index=False)

        df = pd.read_excel(SPECS_DB_PATH)
        is_new = spec_id == 0 or spec_id not in df['id_spec'].values
        
        target_id = spec_id
        if is_new:
            # Calcular nuevo ID
            target_id = int(df['id_spec'].max()) + 1 if len(df) > 0 else 1
            
        # Preparar JSON — pasar config completo, excluyendo claves que van en columnas separadas
        _meta_keys = {"name", "description", "type"}
        json_data = {k: v for k, v in config.items() if k not in _meta_keys}
        
        json_str = json.dumps(json_data, ensure_ascii=False)
            
        now_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if is_new:
            new_row = {
                'id_spec': target_id,
                'name': config.get("name", "Nueva Especificación"),
                'description': config.get("description", ""),
                'type': config.get("type", "Reporte"),
                'config_json': json_str,
                'updated_at': now_str
            }
            # Aseguramos columnas existentes (rellenar con None las que falten)
            for col in df.columns:
                if col not in new_row:
                    new_row[col] = None
            
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            idx = df['id_spec'] == target_id
            df.loc[idx, 'name'] = config.get("name")
            df.loc[idx, 'description'] = config.get("description")
            df.loc[idx, 'type'] = config.get("type")
            df.loc[idx, 'updated_at'] = now_str
            df.loc[idx, 'config_json'] = json_str
            
        df.to_excel(SPECS_DB_PATH, index=False)
        return {"status": "success", "message": f"Especificación {target_id} guardada", "new_id": target_id}
    except Exception as e:
        print(f"Error guardando spec: {e}")
        return {"error": str(e)}

@router.post("/{spec_id}/config")
async def save_spec_config_endpoint(spec_id: int, config: dict):
    return await save_spec_config_logic(spec_id, config)

@router.post("/{spec_id}/duplicate")
async def duplicate_spec(spec_id: int):
    try:
        if not SPECS_DB_PATH.exists():
            return {"error": "Base de datos no encontrada"}
            
        df = pd.read_excel(SPECS_DB_PATH)
        row = df[df['id_spec'] == spec_id]
        
        if row.empty:
            return {"error": "Especificación no encontrada"}
            
        # 1. Obtener configuración original
        original = row.iloc[0]
        config_raw = original.get('config_json')
        config = safe_text_to_json(config_raw)
        if config is None:
            config = {}
        
        # 2. Modificar nombre para la copia
        new_name = str(config.get('name', original['name'])) + " (Copia)"
        config['name'] = new_name
        config['description'] = str(config.get('description', original.get('description', '')))
        config['type'] = str(config.get('type', original.get('type', 'Reporte')))
        
        # 3. Guardar como nueva especificación (ID=0 fuerza creación)
        return await save_spec_config_logic(0, config)
        
    except Exception as e:
        return {"error": str(e)}

@router.delete("/{spec_id}")
async def delete_spec(spec_id: int):
    try:
        if not SPECS_DB_PATH.exists():
            return {"error": "Base de datos no encontrada"}
            
        df = pd.read_excel(SPECS_DB_PATH)
        
        # Verificar si existe
        if spec_id not in df['id_spec'].values:
            return {"error": "Especificación no encontrada"}
            
        # Eliminar
        df = df[df['id_spec'] != spec_id]
        df.to_excel(SPECS_DB_PATH, index=False)
        
        return {"status": "success", "message": f"Especificación {spec_id} eliminada"}
    except Exception as e:
        return {"error": str(e)}
