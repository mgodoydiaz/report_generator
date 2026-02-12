from pathlib import Path
from datetime import datetime
import pandas as pd
import json
import os
from typing import Optional, List, Dict
from rgenerator.etl.core.step import Step
from config import METRICS_DB_PATH, METRIC_DATA_DB_PATH, METRIC_DIMENSIONS_DB_PATH, DIMENSIONS_DB_PATH

class SaveToMetric(Step):
    """
    Guarda un DataFrame (artifact) en metric_data.xlsx para una métrica específica.
    
    Infiere automáticamente las columnas de dimensión y de valor a partir de la
    definición de la métrica en la base de datos, usando la misma lógica que el
    endpoint import_metric_data de la API.

    Parámetros:
        metric_id (int): ID de la métrica destino.
        input_key (str): Clave del artifact (DataFrame) a importar.
        clear_existing (bool): Si es True, borra los datos existentes para este
                               metric_id antes de insertar. Default: False.
    """
    def __init__(
        self, 
        metric_id: int, 
        input_key: str, 
        clear_existing: bool = False
    ):
        super().__init__(name="SaveToMetric")
        self.metric_id = metric_id
        self.input_key = input_key
        self.clear_existing = clear_existing

    def run(self, ctx):
        print(f"[{self.name}] Iniciando guardado para métrica ID {self.metric_id} desde artifact '{self.input_key}'")
        print(f"[{self.name}] Artifacts disponibles: {list(ctx.artifacts.keys())}")
        
        # 1. Obtener DataFrame del contexto
        if self.input_key not in ctx.artifacts:
            raise ValueError(f"Artifact '{self.input_key}' no encontrado en el contexto. Disponibles: {list(ctx.artifacts.keys())}")
        
        df_input = ctx.artifacts[self.input_key]
        if not isinstance(df_input, pd.DataFrame):
             raise TypeError(f"El artifact '{self.input_key}' no es un DataFrame.")
             
        print(f"[{self.name}] DataFrame shape: {df_input.shape}")
        print(f"[{self.name}] DataFrame columnas: {df_input.columns.tolist()}")

        if df_input.empty:
            print(f"[{self.name}] El DataFrame de entrada está vacío. No se guardarán datos.")
            return

        # 2. Cargar definición de la métrica
        if not METRICS_DB_PATH.exists():
            raise FileNotFoundError(f"No se encontró la base de datos de métricas: {METRICS_DB_PATH}")
            
        metrics_df = pd.read_excel(METRICS_DB_PATH)
        metric_row = metrics_df[metrics_df['id_metric'] == self.metric_id]
        if metric_row.empty:
            raise ValueError(f"Métrica ID {self.metric_id} no encontrada en metrics.xlsx")
        
        metric = metric_row.iloc[0].to_dict()

        # Parsear meta_json si existe
        try:
            if isinstance(metric.get('meta_json'), str) and metric['meta_json']:
                metric['meta_json'] = json.loads(metric['meta_json'].replace("'", '"'))
        except:
            metric['meta_json'] = {}

        # 3. Construir mapa de dimensiones: nombre → id_dimension
        dim_name_to_id = {}
        try:
            if METRIC_DIMENSIONS_DB_PATH.exists() and DIMENSIONS_DB_PATH.exists():
                md_df = pd.read_excel(METRIC_DIMENSIONS_DB_PATH)
                dim_df = pd.read_excel(DIMENSIONS_DB_PATH)
                
                rel_dim_ids = md_df[md_df['id_metric'] == self.metric_id]['id_dimension'].tolist()
                
                for dim_id in rel_dim_ids:
                    row = dim_df[dim_df['id_dimension'] == dim_id]
                    if not row.empty:
                        dim_name_to_id[row.iloc[0]['name']] = dim_id
        except Exception as e:
            print(f"[{self.name}] Advertencia al cargar dimensiones: {e}")

        print(f"[{self.name}] Dimensiones inferidas: {list(dim_name_to_id.keys())}")
        print(f"[{self.name}] Tipo de dato: {metric.get('data_type')}, Nombre métrica: {metric.get('name')}")

        # 4. Cargar metric_data existente
        if not METRIC_DATA_DB_PATH.exists():
            df_metric_data = pd.DataFrame(columns=['id_data', 'id_metric', 'value', 'dimensions_json', 'created_at'])
        else:
            df_metric_data = pd.read_excel(METRIC_DATA_DB_PATH)

        # 5. Limpiar datos existentes si se solicita
        if self.clear_existing:
            original_count = len(df_metric_data)
            df_metric_data = df_metric_data[df_metric_data['id_metric'] != self.metric_id]
            print(f"[{self.name}] Se eliminaron {original_count - len(df_metric_data)} registros previos de la métrica {self.metric_id}")

        # 6. Iterar filas del DataFrame y construir registros
        #    (misma lógica que import_metric_data en routers/metrics.py)
        new_rows = []

        for _, row in df_input.iterrows():
            # 6a. Extraer dimensiones
            dims_json = {}
            for dim_name, dim_id in dim_name_to_id.items():
                if dim_name in df_input.columns:
                    val = row[dim_name]
                    if pd.notna(val):
                        dims_json[str(dim_id)] = str(val)

            # 6b. Extraer valor según tipo de métrica
            final_value = None

            if metric.get('data_type') == 'object':
                # Tipo objeto: cada campo de meta_json.fields es una columna
                val_obj = {}
                fields = (metric.get('meta_json') or {}).get('fields', [])
                for f in fields:
                    fname = f['name']
                    if fname in df_input.columns:
                        val = row[fname]
                        if pd.notna(val):
                            if f.get('type') == 'int':
                                try: val = int(val)
                                except: pass
                            elif f.get('type') == 'float':
                                try: val = float(val)
                                except: pass
                            val_obj[fname] = val
                final_value = json.dumps(val_obj)
            else:
                # Tipo simple: la columna de valor tiene el nombre de la métrica
                value_col = metric['name']
                if value_col in df_input.columns:
                    v = row[value_col]
                    if pd.notna(v):
                        if metric['data_type'] == 'int': 
                            final_value = int(v)
                        elif metric['data_type'] == 'float': 
                            final_value = float(v)
                        else: 
                            final_value = str(v)

            if final_value is not None:
                new_rows.append({
                    "id_data": 0,  # Se asigna abajo
                    "id_metric": self.metric_id,
                    "value": final_value,
                    "dimensions_json": json.dumps(dims_json),
                    "created_at": datetime.now().isoformat()
                })

        # 7. Asignar IDs y guardar
        if new_rows:
            df_new = pd.DataFrame(new_rows)
            
            if not df_metric_data.empty:
                max_id = df_metric_data['id_data'].max()
                df_new['id_data'] = range(int(max_id) + 1, int(max_id) + 1 + len(df_new))
            else:
                df_new['id_data'] = range(1, 1 + len(df_new))

            df_final = pd.concat([df_metric_data, df_new], ignore_index=True)
            df_final.to_excel(METRIC_DATA_DB_PATH, index=False)
            print(f"[{self.name}] Se guardaron {len(new_rows)} registros en metric_data.xlsx")
        else:
            print(f"[{self.name}] No se generaron registros nuevos.")
