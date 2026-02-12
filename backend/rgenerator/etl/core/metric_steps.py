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
    Guarda un DataFrame (artifact) en lmetric_data.xlsx para una métrica específica.
    
    Parámetros:
        metric_id (int): ID de la métrica destino.
        input_key (str): Clave del artifact (DataFrame) a importar.
        value_column (str): Nombre de la columna en el DF que contiene el valor de la métrica.
        dimension_columns (List[str]): Lista de columnas en el DF que corresponden a dimensiones.
                                       Si es None, se intentará inferir usando las dimensiones definidas en la BD.
        clear_existing (bool): Si es True, borra los datos existentes para este metric_id antes de insertar (CUIDADO).
    """
    def __init__(
        self, 
        metric_id: int, 
        input_key: str, 
        value_column: str = "value", 
        dimension_columns: Optional[List[str]] = None,
        clear_existing: bool = False
    ):
        super().__init__(name="SaveToMetric")
        self.metric_id = metric_id
        self.input_key = input_key
        self.value_column = value_column
        self.dimension_columns = dimension_columns
        self.clear_existing = clear_existing

    def run(self, ctx):
        print(f"[{self.name}] Iniciando guardado para métrica ID {self.metric_id} desde artifact '{self.input_key}'")
        
        # 1. Obtener DataFrame del contexto
        if self.input_key not in ctx.artifacts:
            raise ValueError(f"Artifact '{self.input_key}' no encontrado en el contexto.")
        
        df_input = ctx.artifacts[self.input_key]
        if not isinstance(df_input, pd.DataFrame):
             raise TypeError(f"El artifact '{self.input_key}' no es un DataFrame.")
             
        if df_input.empty:
            print(f"[{self.name}] El DataFrame de entrada está vacío. No se guardarán datos.")
            return

        # 2. Validar que exista la métrica y obtener sus dimensiones requeridas
        if not METRICS_DB_PATH.exists():
            raise FileNotFoundError(f"No se encontró la base de datos de métricas: {METRICS_DB_PATH}")
            
        metrics_df = pd.read_excel(METRICS_DB_PATH)
        if self.metric_id not in metrics_df['id_metric'].values:
            raise ValueError(f"Métrica ID {self.metric_id} no encontrada en metrics.xlsx")

        # 3. Identificar columnas de dimensión
        target_dims = []
        if self.dimension_columns:
            target_dims = self.dimension_columns
        else:
            # Inferir desde metric_dimensions + dimensions
            if METRIC_DIMENSIONS_DB_PATH.exists() and DIMENSIONS_DB_PATH.exists():
                md_df = pd.read_excel(METRIC_DIMENSIONS_DB_PATH)
                dim_df = pd.read_excel(DIMENSIONS_DB_PATH)
                
                # Obtener IDs de dimensiones para esta métrica
                dim_ids = md_df[md_df['id_metric'] == self.metric_id]['id_dimension'].tolist()
                
                # Obtener nombres de las dimensiones
                # Asumimos que el nombre en dimensions.xlsx coincide con la columna en el DF
                target_dims = dim_df[dim_df['id_dimension'].isin(dim_ids)]['name'].tolist()
                print(f"[{self.name}] Dimensiones inferidas para métrica {self.metric_id}: {target_dims}")
        
        # Validar que las columnas existan en el DF
        missing_cols = [col for col in target_dims if col not in df_input.columns]
        if missing_cols:
            raise ValueError(f"Faltan columnas de dimensión en el DataFrame: {missing_cols}")
            
        if self.value_column not in df_input.columns:
            raise ValueError(f"Falta la columna de valor '{self.value_column}' en el DataFrame.")

        # 4. Cargar metric_data existente
        if not METRIC_DATA_DB_PATH.exists():
            # Crear estructura inicial si no existe
            df_metric_data = pd.DataFrame(columns=['id_data', 'id_metric', 'value', 'dimensions_json', 'updated_at', 'created_at'])
        else:
            df_metric_data = pd.read_excel(METRIC_DATA_DB_PATH)

        # 5. Limpiar datos existentes si se solicita
        if self.clear_existing:
            original_count = len(df_metric_data)
            df_metric_data = df_metric_data[df_metric_data['id_metric'] != self.metric_id]
            print(f"[{self.name}] Se eliminaron {original_count - len(df_metric_data)} registros previos de la métrica {self.metric_id}")

        # 6. Preparar nuevos registros
        new_records = []
        
        # Determinar próximo ID
        next_id = 1
        if not df_metric_data.empty:
            next_id = df_metric_data['id_data'].max() + 1
            
        current_time = datetime.now().isoformat()
        
        for idx, row in df_input.iterrows():
            # Construir JSON de dimensiones
            dims_dict = {col: row[col] for col in target_dims}
            dims_json = json.dumps(dims_dict, ensure_ascii=False)
            
            # Obtener Valor
            val = row[self.value_column]
            
            new_records.append({
                'id_data': next_id,
                'id_metric': self.metric_id,
                'value': val,
                'dimensions_json': dims_json,
                'updated_at': current_time, # Podría ser null si es creación pura, pero updated sirve
                'created_at': current_time
            })
            next_id += 1
            
        # 7. Concatenar y guardar
        if new_records:
            df_new = pd.DataFrame(new_records)
            df_metric_data = pd.concat([df_metric_data, df_new], ignore_index=True)
            
            # Guardar en Excel
            df_metric_data.to_excel(METRIC_DATA_DB_PATH, index=False)
            print(f"[{self.name}] Se guardaron {len(new_records)} registros en metric_data.xlsx")
        else:
            print(f"[{self.name}] No se generaron registros nuevos.")
            
