from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
from datetime import datetime
from config import DIMENSIONS_DB_PATH, DIMENSION_VALUES_DB_PATH

router = APIRouter(prefix="/api/dimensions", tags=["dimensions"])

# --- Pydantic Models ---
class DimensionBase(BaseModel):
    name: str
    data_type: str = "str"
    validation_mode: str = "free" # free, list
    description: Optional[str] = ""

class DimensionCreate(DimensionBase):
    pass

class DimensionUpdate(DimensionBase):
    pass

class DimensionValueCreate(BaseModel):
    value: str
    is_active: bool = True

class DimensionValueUpdate(BaseModel):
    value: Optional[str] = None
    is_active: Optional[bool] = None

# --- Helpers ---
def get_df(path):
    if not path.exists():
        return pd.DataFrame()
    return pd.read_excel(path).fillna("")

def save_df(df, path):
    df.to_excel(path, index=False)

# --- Endpoints: Dimensions ---

@router.get("/")
async def get_dimensions():
    try:
        df = get_df(DIMENSIONS_DB_PATH)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_dimension(dim: DimensionCreate):
    try:
        df = get_df(DIMENSIONS_DB_PATH)
        
        # Generar ID
        next_id = 1
        if not df.empty and 'id_dimension' in df.columns:
            next_id = int(df['id_dimension'].max()) + 1
            
        new_row = {
            "id_dimension": next_id,
            "name": dim.name,
            "data_type": dim.data_type,
            "validation_mode": dim.validation_mode,
            "description": dim.description,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_df(df, DIMENSIONS_DB_PATH)
        
        return {"status": "success", "data": new_row}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{dim_id}")
async def delete_dimension(dim_id: int):
    try:
        # Borrar dimensión
        df = get_df(DIMENSIONS_DB_PATH)
        df = df[df['id_dimension'] != dim_id]
        save_df(df, DIMENSIONS_DB_PATH)
        
        # Borrar valores asociados (Cascada)
        df_vals = get_df(DIMENSION_VALUES_DB_PATH)
        if not df_vals.empty:
            df_vals = df_vals[df_vals['id_dimension'] != dim_id]
            save_df(df_vals, DIMENSION_VALUES_DB_PATH)
            
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints: Dimension Values ---

@router.get("/{dim_id}/values")
async def get_dimension_values(dim_id: int):
    try:
        df = get_df(DIMENSION_VALUES_DB_PATH)
        if df.empty:
            return []
            
        # Filtrar por id_dimension
        filtered = df[df['id_dimension'] == dim_id]
        return filtered.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{dim_id}/values")
async def add_dimension_value(dim_id: int, val: DimensionValueCreate):
    try:
        df = get_df(DIMENSION_VALUES_DB_PATH)
        
        next_id = 1
        if not df.empty and 'id_value' in df.columns:
            next_id = int(df['id_value'].max()) + 1
            
        new_row = {
            "id_value": next_id,
            "id_dimension": dim_id,
            "value": val.value,
            "is_active": val.is_active,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_df(df, DIMENSION_VALUES_DB_PATH)
        
        return {"status": "success", "data": new_row}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/values/{val_id}")
async def delete_dimension_value(val_id: int):
    try:
        df = get_df(DIMENSION_VALUES_DB_PATH)
        df = df[df['id_value'] != val_id]
        save_df(df, DIMENSION_VALUES_DB_PATH)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
