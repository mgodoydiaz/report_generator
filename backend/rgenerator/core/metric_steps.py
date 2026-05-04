from datetime import datetime
import pandas as pd
import json
from typing import Optional, Dict, Any
from rgenerator.core.step import Step
from backend.auditing import make_metric_data
from backend.models import Metric, MetricDimension, MetricData, Dimension


def _parse_meta_json(raw):
    """Parsea meta_json desde string o dict."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return json.loads(raw.replace("'", '"'))
        except Exception:
            return {}
    return {}


def _build_dim_name_to_id(db, metric_id: int) -> Dict[str, int]:
    """Construye mapa {nombre_dimension: id_dimension} para una métrica."""
    dim_links = db.query(MetricDimension).filter(
        MetricDimension.id_metric == metric_id
    ).all()
    dim_ids = [lnk.id_dimension for lnk in dim_links]
    if not dim_ids:
        return {}
    dims = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all()
    return {d.name: d.id_dimension for d in dims}


def _build_dim_id_to_name(db, metric_id: int) -> Dict[int, str]:
    """Construye mapa {id_dimension: nombre_dimension} para una métrica."""
    dim_links = db.query(MetricDimension).filter(
        MetricDimension.id_metric == metric_id
    ).all()
    dim_ids = [lnk.id_dimension for lnk in dim_links]
    if not dim_ids:
        return {}
    dims = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all()
    return {d.id_dimension: d.name for d in dims}


class SaveToMetric(Step):
    """
    Guarda un DataFrame (artifact) en la tabla metric_data de PostgreSQL.

    Parámetros:
        metric_id (int): ID de la métrica destino.
        input_key (str): Clave del artifact (DataFrame) a importar.
        clear_existing (bool): Si es True, borra los datos existentes antes de insertar.
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

        if not ctx.db:
            raise RuntimeError("No hay sesión de base de datos disponible en el contexto (ctx.db)")

        # 1. Obtener DataFrame del contexto
        if self.input_key not in ctx.artifacts:
            raise ValueError(f"Artifact '{self.input_key}' no encontrado. Disponibles: {list(ctx.artifacts.keys())}")

        df_input = ctx.artifacts[self.input_key]
        if not isinstance(df_input, pd.DataFrame):
            raise TypeError(f"El artifact '{self.input_key}' no es un DataFrame.")

        print(f"[{self.name}] DataFrame shape: {df_input.shape}")
        print(f"[{self.name}] DataFrame columnas: {df_input.columns.tolist()}")

        if df_input.empty:
            print(f"[{self.name}] El DataFrame de entrada está vacío. No se guardarán datos.")
            return

        # 2. Cargar definición de la métrica desde PostgreSQL
        metric = ctx.db.query(Metric).filter(
            Metric.id_metric == self.metric_id,
            Metric.org_id == ctx.org_id,
        ).first()
        if not metric:
            raise ValueError(f"Métrica ID {self.metric_id} no encontrada")

        meta = _parse_meta_json(metric.meta_json)

        # 3. Construir mapa de dimensiones: nombre → id_dimension
        dim_name_to_id = _build_dim_name_to_id(ctx.db, self.metric_id)
        print(f"[{self.name}] Dimensiones inferidas: {list(dim_name_to_id.keys())}")
        print(f"[{self.name}] Tipo de dato: {metric.data_type}, Nombre métrica: {metric.name}")

        # 4. Limpiar datos existentes si se solicita
        if self.clear_existing:
            deleted = ctx.db.query(MetricData).filter(
                MetricData.id_metric == self.metric_id
            ).delete(synchronize_session=False)
            print(f"[{self.name}] Se eliminaron {deleted} registros previos de la métrica {self.metric_id}")

        # 5. Iterar filas del DataFrame y construir registros
        new_data_points = []

        for _, row in df_input.iterrows():
            # Extraer dimensiones
            dims_json = {}
            for dim_name, dim_id in dim_name_to_id.items():
                if dim_name in df_input.columns:
                    val = row[dim_name]
                    if pd.notna(val):
                        dims_json[str(dim_id)] = str(val)

            # Extraer valor según tipo de métrica
            final_value = None

            if metric.data_type == 'object':
                val_obj = {}
                fields = meta.get('fields', [])
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
                value_col = metric.name
                if value_col in df_input.columns:
                    v = row[value_col]
                    if pd.notna(v):
                        if metric.data_type == 'int':
                            final_value = str(int(v))
                        elif metric.data_type == 'float':
                            final_value = str(float(v))
                        else:
                            final_value = str(v)

            if final_value is not None:
                new_data_points.append(make_metric_data(
                    metric_id=self.metric_id,
                    value=final_value,
                    dimensions=dims_json,
                    org_id=ctx.org_id,
                    user_id=ctx.user_id,
                    via=("pipeline" if ctx.user_id else "pipeline_cron"),
                ))

        # 6. Guardar en PostgreSQL
        if new_data_points:
            ctx.db.add_all(new_data_points)
            ctx.db.commit()
            print(f"[{self.name}] Se guardaron {len(new_data_points)} registros en PostgreSQL")
        else:
            print(f"[{self.name}] No se generaron registros nuevos.")


class LoadMetricToDF(Step):
    """
    Carga los datos de una métrica desde PostgreSQL y los convierte en un
    DataFrame plano, guardándolo como artifact en el contexto.

    Parámetros:
        metric_id (int): ID de la métrica a cargar.
        output_key (str): Clave del artifact donde se guardará el DataFrame.
        filters (dict, opcional): Filtros por nombre de dimensión.
    """
    def __init__(
        self,
        metric_id: int,
        output_key: str,
        filters: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name="LoadMetricToDF")
        self.metric_id = metric_id
        self.output_key = output_key
        self.filters = filters or {}

    def run(self, ctx):
        print(f"[{self.name}] Cargando métrica ID {self.metric_id} → artifact '{self.output_key}'")

        if not ctx.db:
            raise RuntimeError("No hay sesión de base de datos disponible en el contexto (ctx.db)")

        # 1. Cargar definición de la métrica
        metric = ctx.db.query(Metric).filter(
            Metric.id_metric == self.metric_id,
            Metric.org_id == ctx.org_id,
        ).first()
        if not metric:
            raise ValueError(f"Métrica ID {self.metric_id} no encontrada")

        meta = _parse_meta_json(metric.meta_json)

        # 2. Construir mapa ID dimensión → nombre
        dims_map = _build_dim_id_to_name(ctx.db, self.metric_id)
        print(f"[{self.name}] Dimensiones: {list(dims_map.values())}")

        # 3. Cargar datos de la métrica desde PostgreSQL
        data_rows = ctx.db.query(MetricData).filter(
            MetricData.id_metric == self.metric_id
        ).all()
        print(f"[{self.name}] Registros encontrados: {len(data_rows)}")

        # 4. Aplanar a DataFrame legible
        flat_data = []
        for row in data_rows:
            item: Dict[str, Any] = {}

            # Dimensiones
            dims_json: Dict[str, Any] = {}
            try:
                if isinstance(row.dimensions_json, str):
                    dims_json = json.loads(row.dimensions_json.replace("'", '"'))
                elif isinstance(row.dimensions_json, dict):
                    dims_json = row.dimensions_json
            except Exception:
                pass

            for dim_id, name in dims_map.items():
                item[name] = dims_json.get(str(dim_id))

            # Valor(es)
            value = row.value
            if metric.data_type == 'object':
                try:
                    val_obj = json.loads(value) if isinstance(value, str) else value
                    for k, v in val_obj.items():
                        item[k] = v
                except Exception:
                    item['Valor_Raw'] = str(value)
            else:
                item[metric.name] = value

            flat_data.append(item)

        df_result = pd.DataFrame(flat_data)

        # 5. Aplicar filtros
        if self.filters and not df_result.empty:
            for col, val in self.filters.items():
                if col in df_result.columns:
                    df_result = df_result[df_result[col].astype(str) == str(val)]
                else:
                    print(f"[{self.name}] Advertencia: columna de filtro '{col}' no existe en el DataFrame.")
            print(f"[{self.name}] Registros tras filtros: {len(df_result)}")

        ctx.artifacts[self.output_key] = df_result
        ctx.last_artifact_key = self.output_key
        print(f"[{self.name}] DataFrame guardado en artifact '{self.output_key}' — shape: {df_result.shape}")
