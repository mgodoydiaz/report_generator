from fastapi import APIRouter, HTTPException, Response, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import json
import io
from datetime import datetime
from config import METRICS_DB_PATH, METRIC_DIMENSIONS_DB_PATH, METRIC_DATA_DB_PATH, DIMENSIONS_DB_PATH
from routers._db import get_df, save_df

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
                meta_val = metric.get('meta_json')
                if isinstance(meta_val, str) and meta_val:
                    metric['meta_json'] = json.loads(meta_val.replace("'", '"'))
                elif pd.isna(meta_val) or meta_val is None:
                    metric['meta_json'] = {}
                elif not isinstance(meta_val, dict):
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
async def get_metric_data(metric_id: int, page: int = 1, page_size: int = 50):
    try:
        df = get_df(METRIC_DATA_DB_PATH)
        filtered = df[df['id_metric'] == metric_id].copy()
        
        total = len(filtered)
        
        # Aplicar paginación
        start = (page - 1) * page_size
        end = start + page_size
        page_df = filtered.iloc[start:end]
        
        # Parsear JSON para devolverlo como objeto real
        results = []
        for _, row in page_df.iterrows():
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
            
        return {"items": results, "total": total}
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

@router.put("/data/{data_id}")
async def update_metric_data(data_id: int, point: MetricDataPoint):
    try:
        df = get_df(METRIC_DATA_DB_PATH)
        
        # Validar existencia
        if data_id not in df['id_data'].values:
            raise HTTPException(status_code=404, detail="Data point not found")
        
        # Actualizar fila
        # Convertir dimensions_json a string si viene como dict
        dims_json = json.dumps(point.dimensions_json) if isinstance(point.dimensions_json, dict) else point.dimensions_json
        
        # Actualizar campos
        # Nota: value puede ser cualquier cosa. Si es objeto, asegurarnos de serializar si viene como tal?
        # Pydantic MetricDataPoint define value: Any.
        # Si nuestra DB espera string en value para objetos complejos (que no sean int/float nativos), debemos manejarlo.
        # Asumiremos que el frontend envía el valor listo o que pandas lo maneja. 
        # Para consistencia con create, serializamos si es dict/list.
        final_val = point.value
        if isinstance(final_val, (dict, list)):
             final_val = json.dumps(final_val)

        # Usar loc para update seguro
        mask = df['id_data'] == data_id
        df.loc[mask, 'value'] = final_val
        df.loc[mask, 'dimensions_json'] = dims_json
        # Opcional: updated_at
        
        save_df(df, METRIC_DATA_DB_PATH)
        return {"status": "success", "id_data": data_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class BatchDeleteRequest(BaseModel):
    ids: List[int]

@router.post("/data/batch-delete")
async def delete_metric_data_batch(req: BatchDeleteRequest):
    try:
        df = get_df(METRIC_DATA_DB_PATH)
        initial_len = len(df)
        df = df[~df['id_data'].isin(req.ids)]
        
        if len(df) < initial_len:
            save_df(df, METRIC_DATA_DB_PATH)
            
        return {"status": "success", "deleted_count": initial_len - len(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{metric_id}/export")
async def export_metric_data(metric_id: int, format: str = "excel"):
    try:
        # 1. Cargar Datos
        df_data = get_df(METRIC_DATA_DB_PATH)
        df_data = df_data[df_data['id_metric'] == metric_id].copy()
        
        # 2. Cargar Definiciones (Métrica y Dimensiones)
        df_metrics = get_df(METRICS_DB_PATH)
        metric = df_metrics[df_metrics['id_metric'] == metric_id].iloc[0].to_dict()
        
        # Parsear meta_json de la métrica si es necesario
        try:
            if isinstance(metric.get('meta_json'), str) and metric['meta_json']:
                metric['meta_json'] = json.loads(metric['meta_json'].replace("'", '"'))
        except:
            metric['meta_json'] = {}

        df_dims = get_df(DIMENSIONS_DB_PATH)
        dims_map = {row['id_dimension']: row['name'] for _, row in df_dims.iterrows()}
        
        # 3. Construir DataFrame Plano
        # Lista de diccionarios para el nuevo DF
        flat_data = []
        
        for _, row in df_data.iterrows():
            item = {}
            
            # 3.1 Procesar Dimensiones
            dims_json = {}
            try:
                val = row['dimensions_json']
                if isinstance(val, str):
                    dims_json = json.loads(val.replace("'", '"'))
                elif isinstance(val, dict):
                    dims_json = val
            except:
                pass
            
            # Mapear {id_dim: valor} -> {NombreDimensión: valor}
            for dim_id, val in dims_json.items():
                dim_name = dims_map.get(int(dim_id), f"Dim_{dim_id}")
                item[dim_name] = val
                
            # 3.2 Procesar Valor
            # Si es objeto, expandir
            value = row['value']
            if metric['data_type'] == 'object':
                try:
                    val_obj = {}
                    if isinstance(value, str):
                        val_obj = json.loads(value)
                    elif isinstance(value, dict):
                        val_obj = value
                    
                    # Expandir campos
                    for k, v in val_obj.items():
                        item[k] = v
                except:
                    item['Valor_Raw'] = str(value)
            else:
                item[metric['name']] = value
                
            flat_data.append(item)
            
        df_export = pd.DataFrame(flat_data)
        
        # 4. Generar Archivo
        stream = io.BytesIO()
        media_type = ""
        filename_ext = ""
        
        if format == 'excel':
            # Excel
            with pd.ExcelWriter(stream, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name="Datos")
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename_ext = "xlsx"
        elif format == 'csv':
            # CSV (;) y BOM para Excel
            # encoding='utf-8-sig' agrega BOM
            df_export.to_csv(stream, index=False, sep=';', encoding='utf-8-sig')
            media_type = "text/csv"
            filename_ext = "csv"
        elif format == 'txt':
            # TXT (Tablas \t)
            df_export.to_csv(stream, index=False, sep='\t', encoding='utf-8')
            media_type = "text/plain"
            filename_ext = "txt"
        else:
            raise HTTPException(status_code=400, detail="Formato no soportado")
            
        stream.seek(0)
        
        return StreamingResponse(
            stream, 
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename=export.{filename_ext}"}
        )

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{metric_id}/template")
async def get_metric_template(metric_id: int):
    try:
        # Cargar definiciones
        df_metrics = get_df(METRICS_DB_PATH)
        metric = df_metrics[df_metrics['id_metric'] == metric_id].iloc[0].to_dict()
        
        try:
            if isinstance(metric.get('meta_json'), str) and metric['meta_json']:
                metric['meta_json'] = json.loads(metric['meta_json'].replace("'", '"'))
        except:
            metric['meta_json'] = {}

        # Mapear IDs de Dimensión -> Nombres
        # Necesitamos saber qué dimensiones tiene esta métrica
        metric_dims = []
        try:
            md_df = get_df(METRIC_DIMENSIONS_DB_PATH)
            # Filtrar dimensiones asociadas a esta métrica
            rel_dims = md_df[md_df['id_metric'] == metric_id]['id_dimension'].tolist()
            
            # Obtener nombres
            d_df = get_df(DIMENSIONS_DB_PATH)
            for dim_id in rel_dims:
                dim_row = d_df[d_df['id_dimension'] == dim_id]
                if not dim_row.empty:
                    metric_dims.append(dim_row.iloc[0]['name'])
        except:
            pass

        # Construir columnas
        columns = []
        # 1. Dimensiones
        columns.extend(metric_dims)
        
        # 2. Valores
        if metric['data_type'] == 'object' and metric['meta_json'].get('fields'):
            for f in metric['meta_json']['fields']:
                columns.append(f['name'])
        else:
            columns.append(metric['name'])

        # Crear DF Vacío
        df_template = pd.DataFrame(columns=columns)
        
        stream = io.BytesIO()
        with pd.ExcelWriter(stream, engine='openpyxl') as writer:
            df_template.to_excel(writer, index=False, sheet_name="Plantilla")
            
        stream.seek(0)
        
        filename = f"Plantilla_{metric['name'].replace(' ', '_')}.xlsx"
        
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{metric_id}/import")
async def import_metric_data(metric_id: int, files: List[UploadFile] = File(...)):
    try:
        # Cargar definiciones Base
        df_metrics = get_df(METRICS_DB_PATH)
        metric = df_metrics[df_metrics['id_metric'] == metric_id].iloc[0].to_dict()
        
        # Parsear meta
        try:
            if isinstance(metric.get('meta_json'), str) and metric['meta_json']:
                metric['meta_json'] = json.loads(metric['meta_json'].replace("'", '"'))
        except:
            metric['meta_json'] = {}

        # Mapa de Dimensiones: Nombre -> ID
        dim_name_to_id = {}
        try:
            md_df = get_df(METRIC_DIMENSIONS_DB_PATH)
            rel_dims = md_df[md_df['id_metric'] == metric_id]['id_dimension'].tolist()
            
            d_df = get_df(DIMENSIONS_DB_PATH)
            for dim_id in rel_dims:
                row = d_df[d_df['id_dimension'] == dim_id]
                if not row.empty:
                    dim_name_to_id[row.iloc[0]['name']] = dim_id
        except:
            pass

        new_rows = []
        
        for file in files:
            contents = await file.read()
            # Detectar formato
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(contents), sep=';') # Asumimos ; por defecto
            else:
                df = pd.read_excel(io.BytesIO(contents))
            
            # Iterar filas
            for _, row in df.iterrows():
                # 1. Extraer Dimensiones
                dims_json = {}
                for dim_name, dim_id in dim_name_to_id.items():
                    if dim_name in df.columns:
                        val = row[dim_name]
                        # Guardar como string siempre para evitar NaN raros
                        if pd.notna(val):
                            dims_json[str(dim_id)] = str(val)
                
                # 2. Extraer Valor
                final_value = None
                
                if metric['data_type'] == 'object':
                    val_obj = {}
                    fields = metric['meta_json'].get('fields', [])
                    for f in fields:
                        fname = f['name']
                        if fname in df.columns:
                            val = row[fname]
                            if pd.notna(val):
                                # Convertir tipo si es necesario
                                if f['type'] == 'int':
                                    try: val = int(val)
                                    except: pass
                                elif f['type'] == 'float':
                                    try: val = float(val)
                                    except: pass
                                val_obj[fname] = val
                    final_value = json.dumps(val_obj)
                else:
                    value_col = metric['name']
                    if value_col in df.columns:
                        v = row[value_col]
                        if pd.notna(v):
                             if metric['data_type'] == 'int': final_value = int(v)
                             elif metric['data_type'] == 'float': final_value = float(v)
                             else: final_value = str(v)
                
                if final_value is not None:
                     new_rows.append({
                        "id_data": int(datetime.now().timestamp() * 1000000) + len(new_rows), # ID temporal simple
                        "id_metric": metric_id,
                        "value": final_value,
                        "dimensions_json": json.dumps(dims_json),
                        "created_at": datetime.now().isoformat()
                    })

        # Guardar en DB
        if new_rows:
            df_existing = get_df(METRIC_DATA_DB_PATH)
            df_new = pd.DataFrame(new_rows)
            # Asegurar IDs únicos (chapa)
            if not df_existing.empty:
                max_id = df_existing['id_data'].max()
                df_new['id_data'] = range(max_id + 1, max_id + 1 + len(df_new))
            else:
                df_new['id_data'] = range(1, 1 + len(df_new))
                
            df_final = pd.concat([df_existing, df_new], ignore_index=True)
            save_df(df_final, METRIC_DATA_DB_PATH)

        return {"status": "success", "imported": len(new_rows)}

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
