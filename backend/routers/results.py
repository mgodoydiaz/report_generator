from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
import pandas as pd
import json
from config import (
    METRICS_DB_PATH, METRIC_DATA_DB_PATH, METRIC_DIMENSIONS_DB_PATH,
    DIMENSIONS_DB_PATH, INDICATORS_DB_PATH, INDICATOR_METRICS_DB_PATH
)
from routers._db import get_df

router = APIRouter(prefix="/api/results", tags=["results"])


@router.get("/indicator/{indicator_id}/data")
async def get_indicator_data(indicator_id: int, filters: Optional[str] = Query(None)):
    """
    Devuelve todos los datos de las métricas asociadas a un indicador,
    opcionalmente filtrados por dimensiones.

    filters: JSON string con {id_dimension: valor}, e.g. '{"1": "2025", "3": "Lenguaje"}'
    """
    try:
        # 1. Obtener métricas del indicador
        df_rels = get_df(INDICATOR_METRICS_DB_PATH)
        if df_rels.empty:
            return {"metrics": [], "data": {}, "dimensions": {}}

        metric_ids = df_rels[df_rels['id_indicator'] == indicator_id]['id_metric'].tolist()
        if not metric_ids:
            return {"metrics": [], "data": {}, "dimensions": {}}

        # 2. Cargar definiciones
        df_metrics = get_df(METRICS_DB_PATH)
        df_dims = get_df(DIMENSIONS_DB_PATH)
        df_metric_dims = get_df(METRIC_DIMENSIONS_DB_PATH)
        df_data = get_df(METRIC_DATA_DB_PATH)

        # Parsear filtros
        dim_filters = {}
        if filters:
            try:
                dim_filters = json.loads(filters)
            except:
                pass

        # 3. Construir info de métricas
        metrics_info = []
        all_dim_ids = set()

        for mid in metric_ids:
            row = df_metrics[df_metrics['id_metric'] == mid]
            if row.empty:
                continue
            m = row.iloc[0].to_dict()

            # Parsear meta_json
            try:
                if isinstance(m.get('meta_json'), str) and m['meta_json']:
                    m['meta_json'] = json.loads(m['meta_json'].replace("'", '"'))
                elif pd.isna(m.get('meta_json')) or m.get('meta_json') is None:
                    m['meta_json'] = {}
                elif not isinstance(m.get('meta_json'), dict):
                    m['meta_json'] = {}
            except:
                m['meta_json'] = {}

            # Dimensiones de la métrica
            dims = df_metric_dims[df_metric_dims['id_metric'] == mid]['id_dimension'].tolist()
            m['dimension_ids'] = dims
            all_dim_ids.update(dims)
            metrics_info.append(m)

        # 4. Info de dimensiones (nombre, valores únicos en los datos)
        dims_map = {}
        for _, d in df_dims.iterrows():
            did = d['id_dimension']
            if did in all_dim_ids:
                dims_map[str(int(did))] = {
                    "id": int(did),
                    "name": d['name'],
                    "data_type": d.get('data_type', 'str'),
                }

        # 5. Obtener datos filtrados por métrica
        data_by_metric = {}
        unique_dim_values = {str(int(did)): set() for did in all_dim_ids}

        for mid in metric_ids:
            metric_data = df_data[df_data['id_metric'] == mid].copy()
            if metric_data.empty:
                data_by_metric[int(mid)] = []
                continue

            rows = []
            for _, r in metric_data.iterrows():
                item = r.to_dict()

                # Parsear dimensions_json
                dims_json = {}
                try:
                    val = item['dimensions_json']
                    if isinstance(val, str):
                        dims_json = json.loads(val.replace("'", '"'))
                    elif isinstance(val, dict):
                        dims_json = val
                except:
                    pass
                item['dimensions_json'] = dims_json

                # Recolectar valores únicos de dimensiones (antes de filtrar)
                for dk, dv in dims_json.items():
                    if dk in unique_dim_values:
                        unique_dim_values[dk].add(str(dv))

                rows.append(item)

            data_by_metric[int(mid)] = rows

        # Agregar valores únicos a dims_map
        for dk, vals in unique_dim_values.items():
            if dk in dims_map:
                dims_map[dk]['values'] = sorted(list(vals))

        # 6. Aplicar filtros a los datos
        if dim_filters:
            for mid in data_by_metric:
                filtered = []
                for item in data_by_metric[mid]:
                    dims = item.get('dimensions_json', {})
                    match = True
                    for fk, fv in dim_filters.items():
                        if str(dims.get(fk, '')) != str(fv):
                            match = False
                            break
                    if match:
                        filtered.append(item)
                data_by_metric[mid] = filtered

        # 7. Parsear values de los datos
        for mid in data_by_metric:
            metric_row = df_metrics[df_metrics['id_metric'] == mid]
            if metric_row.empty:
                continue
            m = metric_row.iloc[0]
            data_type = m.get('data_type', 'float')

            for item in data_by_metric[mid]:
                val = item.get('value')
                if data_type == 'object' and isinstance(val, str):
                    try:
                        item['value'] = json.loads(val)
                    except:
                        pass

        # 8. Obtener column_roles del indicador
        df_indicators = get_df(INDICATORS_DB_PATH)
        column_roles = {}
        ind_row = df_indicators[df_indicators['id_indicator'] == indicator_id]
        if not ind_row.empty:
            cr = ind_row.iloc[0].get('column_roles')
            if isinstance(cr, str) and cr:
                try:
                    column_roles = json.loads(cr)
                except:
                    pass
            elif isinstance(cr, dict):
                column_roles = cr

        # 9. Obtener filter_dimensions del indicador
        filter_dimensions = []
        if not ind_row.empty:
            fd = ind_row.iloc[0].get('filter_dimensions')
            if isinstance(fd, str) and fd:
                try:
                    filter_dimensions = json.loads(fd)
                except:
                    pass
            elif isinstance(fd, list):
                filter_dimensions = fd

        # 10. Obtener temporal_config del indicador
        temporal_config = {}
        if not ind_row.empty:
            tc = ind_row.iloc[0].get('temporal_config')
            if isinstance(tc, str) and tc:
                try:
                    temporal_config = json.loads(tc)
                except:
                    pass
            elif isinstance(tc, dict):
                temporal_config = tc

        # 11. Obtener role_labels del indicador
        role_labels = {}
        if not ind_row.empty:
            rl = ind_row.iloc[0].get('role_labels')
            if isinstance(rl, str) and rl:
                 try: role_labels = json.loads(rl)
                 except: pass
            elif isinstance(rl, dict):
                 role_labels = rl

        # 11b. Obtener role_formats del indicador
        role_formats = {}
        if not ind_row.empty:
            rf = ind_row.iloc[0].get('role_formats')
            if isinstance(rf, str) and rf:
                try: role_formats = json.loads(rf)
                except: pass
            elif isinstance(rf, dict):
                role_formats = rf

        # 12. Obtener achievement_levels del indicador
        achievement_levels = []
        if not ind_row.empty:
            al = ind_row.iloc[0].get('achievement_levels')
            if isinstance(al, str) and al:
                 try: achievement_levels = json.loads(al)
                 except: pass
            elif isinstance(al, list):
                 achievement_levels = al

        return {
            "metrics": metrics_info,
            "dimensions": dims_map,
            "data": data_by_metric,
            "column_roles": column_roles,
            "role_labels": role_labels,
            "role_formats": role_formats,
            "filter_dimensions": filter_dimensions,
            "temporal_config": temporal_config,
            "achievement_levels": achievement_levels
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
