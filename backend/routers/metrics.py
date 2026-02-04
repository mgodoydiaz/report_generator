from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import json
from datetime import datetime
from config import METRICS_DB_PATH, METRIC_DIMENSIONS_DB_PATH, METRIC_DATA_DB_PATH

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

# --- Models ---
class MetricBase(BaseModel):
    name: str
    data_type: str = "float" # float, int, str, object
    description: Optional[str] = ""
    meta_json: Optional[Dict[str, Any]] = {} # Estructura para tipo objeto

class MetricCreate(MetricBase):
    dimension_ids: List[int] = [] 

class MetricUpdate(MetricBase):
    dimension_ids: Optional[List[int]] = None

class MetricDataPoint(BaseModel):
    value: Any
    dimensions_json: Dict[str, Any] # {"id_dimension": "valor"}

# --- Helpers ---
def get_df(path):
    if not path.exists(): return pd.DataFrame()
    return pd.read_excel(path).fillna("")

def save_df(df, path):
    df.to_excel(path, index=False)

# --- Endpoints: Metrics Definitions ---

@router.get("/")
async def get_metrics():
    try:
        df_metrics = get_df(METRICS_DB_PATH)
        df_rels = get_df(METRIC_DIMENSIONS_DB_PATH)
        
        results = []
        for _, row in df_metrics.iterrows():
            metric = row.to_dict()
            # Parsear meta_json
            try:
                if isinstance(metric['meta_json'], str) and metric['meta_json']:
                    metric['meta_json'] = json.loads(metric['meta_json'].replace("'", '"'))
                elif not isinstance(metric['meta_json'], dict):
                    metric['meta_json'] = {}
            except:
                metric['meta_json'] = {}
                
            # Buscar dimensiones asociadas
            dims = df_rels[df_rels['id_metric'] == metric['id_metric']]['id_dimension'].tolist()
            metric['dimension_ids'] = dims
            results.append(metric)
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_metric(metric: MetricCreate):
    try:
        df = get_df(METRICS_DB_PATH)
        
        # 1. Guardar Métrica
        next_id = 1
        if not df.empty and 'id_metric' in df.columns:
            next_id = int(df['id_metric'].max()) + 1
            
        new_row = {
            "id_metric": next_id,
            "name": metric.name,
            "data_type": metric.data_type,
            "description": metric.description,
            "meta_json": json.dumps(metric.meta_json) if metric.meta_json else "",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_df(df, METRICS_DB_PATH)
        
        # 2. Guardar Relaciones (Dimensiones)
        if metric.dimension_ids:
            df_rels = get_df(METRIC_DIMENSIONS_DB_PATH)
            new_rels = []
            for dim_id in metric.dimension_ids:
                new_rels.append({"id_metric": next_id, "id_dimension": dim_id})
            
            df_rels = pd.concat([df_rels, pd.DataFrame(new_rels)], ignore_index=True)
            save_df(df_rels, METRIC_DIMENSIONS_DB_PATH)
            
        return {"status": "success", "data": {**new_row, "dimension_ids": metric.dimension_ids}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{metric_id}")
async def update_metric(metric_id: int, metric: MetricUpdate):
    try:
        df = get_df(METRICS_DB_PATH)
        if metric_id not in df['id_metric'].values:
             raise HTTPException(status_code=404, detail="Métrica no encontrada")
             
        # Actualizar Métrica
        idx = df[df['id_metric'] == metric_id].index[0]
        df.at[idx, 'name'] = metric.name
        df.at[idx, 'data_type'] = metric.data_type
        if metric.description is not None: df.at[idx, 'description'] = metric.description
        if metric.meta_json is not None: df.at[idx, 'meta_json'] = json.dumps(metric.meta_json)
        df.at[idx, 'updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_df(df, METRICS_DB_PATH)
        
        # Actualizar Relaciones (Si se enviaron)
        if metric.dimension_ids is not None:
             df_rels = get_df(METRIC_DIMENSIONS_DB_PATH)
             # Borrar anteriores
             df_rels = df_rels[df_rels['id_metric'] != metric_id]
             # Insertar nuevas
             new_rels = [{"id_metric": metric_id, "id_dimension": dim_id} for dim_id in metric.dimension_ids]
             if new_rels:
                 df_rels = pd.concat([df_rels, pd.DataFrame(new_rels)], ignore_index=True)
             save_df(df_rels, METRIC_DIMENSIONS_DB_PATH)
             
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{metric_id}")
async def delete_metric(metric_id: int):
    try:
        # 1. Borrar Métrica
        df = get_df(METRICS_DB_PATH)
        df = df[df['id_metric'] != metric_id]
        save_df(df, METRICS_DB_PATH)
        
        # 2. Borrar Relaciones
        df_rels = get_df(METRIC_DIMENSIONS_DB_PATH)
        df_rels = df_rels[df_rels['id_metric'] != metric_id]
        save_df(df_rels, METRIC_DIMENSIONS_DB_PATH)
        
        # 3. Borrar Datos
        df_data = get_df(METRIC_DATA_DB_PATH)
        df_data = df_data[df_data['id_metric'] != metric_id]
        save_df(df_data, METRIC_DATA_DB_PATH)
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints: Metric Data values ---

@router.get("/{metric_id}/data")
async def get_metric_data(metric_id: int):
    try:
        df = get_df(METRIC_DATA_DB_PATH)
        filtered = df[df['id_metric'] == metric_id].copy()
        
        # Parsear JSON para devolverlo como objeto real
        results = []
        for _, row in filtered.iterrows():
            item = row.to_dict()
            try:
                # Excel a veces guarda el JSON como string con comillas simples o dobles
                if isinstance(item['dimensions_json'], str):
                     # Reemplazar comillas simples inválidas si es necesario (simple hack)
                     clean_json = item['dimensions_json'].replace("'", '"')
                     item['dimensions_json'] = json.loads(clean_json)
            except:
                item['dimensions_json'] = {}
            results.append(item)
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{metric_id}/data")
async def add_metric_data_point(metric_id: int, point: MetricDataPoint):
    try:
        df = get_df(METRIC_DATA_DB_PATH)
        
        next_id = 1
        if not df.empty and 'id_data' in df.columns:
            next_id = int(df['id_data'].max()) + 1
            
        json_str = json.dumps(point.dimensions_json)
        
        new_row = {
            "id_data": next_id,
            "id_metric": metric_id,
            "value": point.value,
            "dimensions_json": json_str,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_df(df, METRIC_DATA_DB_PATH)
        
        return {"status": "success", "data": new_row}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/data/{data_id}")
async def delete_data_point(data_id: int):
    try:
        df = get_df(METRIC_DATA_DB_PATH)
        df = df[df['id_data'] != data_id]
        save_df(df, METRIC_DATA_DB_PATH)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
