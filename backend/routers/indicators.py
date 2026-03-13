from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, List, Optional, Dict
import pandas as pd
import json
from datetime import datetime
from config import INDICATORS_DB_PATH, INDICATOR_METRICS_DB_PATH
from routers._db import get_df, save_df

router = APIRouter(prefix="/api/indicators", tags=["indicators"])

# --- Models ---
class IndicatorBase(BaseModel):
    name: str
    description: Optional[str] = ""
    type: str = "Evaluación" # Evaluación, Estudio, Alerta
    column_roles: Optional[Dict[str, Any]] = None  # {"logro_1": [{"metric_id": 1, "column": "Rend"}], ...}
    role_labels: Optional[Dict[str, str]] = None # Custom names for columns, e.g., {"logro_1": "Logro"}
    filter_dimensions: Optional[List[int]] = None  # IDs de dimensiones que aparecen como filtros en Results
    temporal_config: Optional[Dict[str, Any]] = None
    achievement_levels: Optional[List[str]] = None

class IndicatorCreate(IndicatorBase):
    metric_ids: List[int] = []

class IndicatorUpdate(IndicatorBase):
    metric_ids: Optional[List[int]] = None

# --- Endpoints ---

@router.get("/")
async def get_indicators():
    try:
        df_indicators = get_df(INDICATORS_DB_PATH)
        df_rels = get_df(INDICATOR_METRICS_DB_PATH)
        
        results = []
        for _, row in df_indicators.iterrows():
            indicator = row.to_dict()

            # Find associated metrics
            metrics = []
            if not df_rels.empty and 'id_indicator' in df_rels.columns:
                metrics = df_rels[df_rels['id_indicator'] == indicator['id_indicator']]['id_metric'].tolist()

            indicator['metric_ids'] = metrics

            # Parse column_roles JSON
            cr = indicator.get('column_roles')
            if isinstance(cr, str) and cr:
                try:
                    indicator['column_roles'] = json.loads(cr)
                except:
                    indicator['column_roles'] = {}
            elif not isinstance(cr, dict):
                indicator['column_roles'] = {}

            # Parse filter_dimensions JSON
            fd = indicator.get('filter_dimensions')
            if isinstance(fd, str) and fd:
                try:
                    indicator['filter_dimensions'] = json.loads(fd)
                except:
                    indicator['filter_dimensions'] = []
            elif not isinstance(fd, list):
                indicator['filter_dimensions'] = []

            # Parse role_labels JSON
            rl = indicator.get('role_labels')
            if isinstance(rl, str) and rl:
                try: indicator['role_labels'] = json.loads(rl)
                except: indicator['role_labels'] = {}
            elif not isinstance(rl, dict):
                indicator['role_labels'] = {}

            # Parse temporal_config JSON
            tc = indicator.get('temporal_config')
            if isinstance(tc, str) and tc:
                try:
                    indicator['temporal_config'] = json.loads(tc)
                except:
                    indicator['temporal_config'] = {}
            elif not isinstance(tc, dict):
                indicator['temporal_config'] = {}

            # Parse achievement_levels JSON
            al = indicator.get('achievement_levels')
            if isinstance(al, str) and al:
                try: indicator['achievement_levels'] = json.loads(al)
                except: indicator['achievement_levels'] = []
            elif not isinstance(al, list):
                indicator['achievement_levels'] = []

            results.append(indicator)
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_indicator(indicator: IndicatorCreate):
    try:
        df = get_df(INDICATORS_DB_PATH)
        
        # 1. Save Indicator
        next_id = 1
        if not df.empty and 'id_indicator' in df.columns:
            next_id = int(df['id_indicator'].max()) + 1
            
        new_row = {
            "id_indicator": next_id,
            "name": indicator.name,
            "description": indicator.description,
            "type": indicator.type,
            "column_roles": json.dumps(indicator.column_roles or {}, ensure_ascii=False),
            "role_labels": json.dumps(indicator.role_labels or {}, ensure_ascii=False),
            "filter_dimensions": json.dumps(indicator.filter_dimensions or [], ensure_ascii=False),
            "temporal_config": json.dumps(indicator.temporal_config or {}, ensure_ascii=False),
            "achievement_levels": json.dumps(indicator.achievement_levels or [], ensure_ascii=False),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Convert to single-row dataframe and concat
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_df(df, INDICATORS_DB_PATH)
        
        # 2. Save Relations (Metrics)
        if indicator.metric_ids:
            df_rels = get_df(INDICATOR_METRICS_DB_PATH)
            new_rels = []
            for metric_id in indicator.metric_ids:
                new_rels.append({"id_indicator": next_id, "id_metric": metric_id})
            
            df_rels = pd.concat([df_rels, pd.DataFrame(new_rels)], ignore_index=True)
            save_df(df_rels, INDICATOR_METRICS_DB_PATH)
            
        return {"status": "success", "data": {**new_row, "metric_ids": indicator.metric_ids}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{indicator_id}")
async def update_indicator(indicator_id: int, indicator: IndicatorUpdate):
    try:
        df = get_df(INDICATORS_DB_PATH)
        if indicator_id not in df['id_indicator'].values:
             raise HTTPException(status_code=404, detail="Indicador no encontrado")
             
        # Update Indicator
        idx = df[df['id_indicator'] == indicator_id].index[0]
        df.at[idx, 'name'] = indicator.name
        if indicator.description is not None: df.at[idx, 'description'] = indicator.description
        df.at[idx, 'type'] = indicator.type
        if indicator.column_roles is not None:
            df.at[idx, 'column_roles'] = json.dumps(indicator.column_roles, ensure_ascii=False)
        if indicator.role_labels is not None:
            df.at[idx, 'role_labels'] = json.dumps(indicator.role_labels, ensure_ascii=False)
        if indicator.filter_dimensions is not None:
            df.at[idx, 'filter_dimensions'] = json.dumps(indicator.filter_dimensions, ensure_ascii=False)
        if indicator.temporal_config is not None:
            df.at[idx, 'temporal_config'] = json.dumps(indicator.temporal_config, ensure_ascii=False)
        if indicator.achievement_levels is not None:
            df.at[idx, 'achievement_levels'] = json.dumps(indicator.achievement_levels, ensure_ascii=False)
        df.at[idx, 'updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_df(df, INDICATORS_DB_PATH)
        
        # Update Relations (if provided)
        if indicator.metric_ids is not None:
             df_rels = get_df(INDICATOR_METRICS_DB_PATH)
             # Delete previous relations
             if not df_rels.empty and 'id_indicator' in df_rels.columns:
                 df_rels = df_rels[df_rels['id_indicator'] != indicator_id]
             # Insert new
             new_rels = [{"id_indicator": indicator_id, "id_metric": mid} for mid in indicator.metric_ids]
             if new_rels:
                 df_rels = pd.concat([df_rels, pd.DataFrame(new_rels)], ignore_index=True)
             save_df(df_rels, INDICATOR_METRICS_DB_PATH)
             
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{indicator_id}")
async def delete_indicator(indicator_id: int):
    try:
        # 1. Delete Indicator
        df = get_df(INDICATORS_DB_PATH)
        if not df.empty and 'id_indicator' in df.columns:
            df = df[df['id_indicator'] != indicator_id]
            save_df(df, INDICATORS_DB_PATH)
        
        # 2. Delete Relations
        df_rels = get_df(INDICATOR_METRICS_DB_PATH)
        if not df_rels.empty and 'id_indicator' in df_rels.columns:
            df_rels = df_rels[df_rels['id_indicator'] != indicator_id]
            save_df(df_rels, INDICATOR_METRICS_DB_PATH)
            
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
