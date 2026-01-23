"""Archivo contiene la definición de los steps que se pueden añadir a una pipeline."""

# Librerias estandar
from datetime import datetime
from pathlib import Path
import pandas as pd
import os 
from typing import Callable, Optional, Dict, List

# Importaciones internas de RGenerator
from .step import Step
from rgenerator.tooling.config_tools import cargar_config_desde_json, parsear_lista_desde_config

##### Steps definidos para SIMCE 

class InitRun(Step):
    """
    Step inicial para configurar el contexto de la corrida. Parámetros recomendados son:
    {
    "evaluation": "simce", 
    "base_dir": Path, 
    "year": 2025,
    "asignatura": "Lenguaje", 
    "numero_prueba": 5
    }
    """
    def __init__(self, **kwargs):
        super().__init__(name="InitRun")
        self.params = kwargs
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def run(self, context):
        before = self._snapshot_artifacts(context)

        # Identidad del run o task
        context.evaluation = self.params.get("evaluation", "unknown_evaluation")
        context.run_id = self.timestamp


        # ATENCION A CAMBIO
        # Agregar un id unico a la corrida, run o task, gestionar algun tipo de software como sidekiq, celery, airflow, etc.
        # context.run_id = # get_unique_id_somehow()

        # Se migran los parametros del InitRun al contexto en params
        if not hasattr(context, "params") or context.params is None:
            context.params = {}
        for k, v in self.params.items():
            context.params[k] = v       

        # carpetas estandar
        ########################################
        # ATENCION A CAMBIO
        # ESTO DEBERIA CAMBIAR POR ALGUNA BASE DE DATOS

        context.base_dir = self.params.get("base_dir")
        context.work_dir = context.base_dir / context.evaluation / context.run_id
        context.inputs_dir = context.base_dir / "inputs"
        context.aux_dir = context.work_dir / "aux_files"
        context.outputs_dir = context.work_dir / "outputs"

        for d in [context.work_dir, context.inputs_dir, context.aux_dir, context.outputs_dir]:
            d.mkdir(parents=True, exist_ok=True)

        context.status = "RUNNING"
        self._log_artifacts_delta(context, before)


class LoadConfig(Step):
    def __init__(
        self,
        config_path: Path | str,
        list_keys: list[str] | None = None,
    ):
        super().__init__(name="load_config")
        self.config_path = Path(config_path)
        self.list_keys = list_keys or [
            "columnas_relevantes",
            "columnas_relevantes_habilidades",
        ]

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)
        if not self.config_path.exists():
            raise FileNotFoundError(f"No se encontró config: {self.config_path}")

        config = cargar_config_desde_json(str(self.config_path))

        # Normaliza defaults
        tipo_etl = str(config.get("tipo_etl", "estudiantes")).strip().lower()
        nombre_salida = str(config.get("nombre_salida", "salida_etl.xlsx")).strip()

        # Asegura params en el contexto
        if not hasattr(ctx, "params") or ctx.params is None:
            ctx.params = {}

        # Guarda config cruda y params normalizados
        ctx.params["config_path"] = str(self.config_path)
        ctx.params["tipo_etl"] = tipo_etl
        ctx.params["nombre_salida"] = nombre_salida

        # Parsea listas declaradas en el txt si existen
        for key in self.list_keys:
            if key in config:
                valor = config.get(key)
                if isinstance(valor, list):
                    ctx.params[key] = valor
                else:
                    ctx.params[key] = parsear_lista_desde_config(config, key)

        # Copia el resto tal cual, sin pisar lo ya normalizado
        for k, v in config.items():
            if k not in ctx.params:
                ctx.params[k] = v

        # Define ruta de salida estándar de esta corrida
        if hasattr(ctx, "outputs_dir"):
            ctx.outputs["excel_salida"] = ctx.outputs_dir / nombre_salida

        # Deja una marca simple para debug
        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)


class DiscoverInputs(Step):
    """
    Escanea un directorio y clasifica archivos según un diccionario de reglas.
    """
    def __init__(self, rules: dict):
        super().__init__(name="DiscoverInputs")
        self.rules = rules

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)
        input_dir = ctx.inputs_dir
        
        # 1. Inicializar las listas en el contexto según las claves del diccionario
        # Así aseguramos que existan aunque no se encuentren archivos (quedarán vacías)
        for key in self.rules.keys():
            ctx.inputs[key] = []

        if not input_dir.exists():
            print(f"Advertencia: Directorio {input_dir} no existe.")
            self._log_artifacts_delta(ctx, before)
            return

        # 2. Escanear y Clasificar
        files_found = 0
        for archivo_nombre in os.listdir(input_dir):
            
            # Iteramos sobre cada "tipo" definido en las reglas
            for tipo, condiciones in self.rules.items():
                
                # Desempaquetamos condiciones con valores por defecto seguros
                extension = condiciones.get("extension", "")
                contains = condiciones.get("contains", "")
                exclude_prefix = condiciones.get("exclude_prefix", None)

                # Aplicamos la lógica (AND lógico)
                match = True
                
                # Check extensión
                if extension and not archivo_nombre.endswith(extension):
                    match = False
                
                # Check contenido del nombre
                if contains and contains not in archivo_nombre:
                    match = False
                
                # Check exclusiones (ej: temporales de excel ~$)
                if exclude_prefix and archivo_nombre.startswith(exclude_prefix):
                    match = False

                # Si pasa todos los filtros, lo guardamos
                if match:
                    full_path = input_dir / archivo_nombre
                    ctx.inputs[tipo].append(full_path)
                    files_found += 1

        print(f"DiscoverInputs: Se encontraron {files_found} archivos clasificados en {list(self.rules.keys())}.")
        self._log_artifacts_delta(ctx, before)

class RunExcelETL(Step):
    """
    Step GENÉRICO para cargar, normalizar headers y consolidar archivos Excel.
    
    Espera en ctx.params:
        - header_row: int o dict {"archivo.xlsx": 5, "default": 0}
        - column_mapping: dict { "ColumnaFea": "ColumnaBonita" }
    """
    def __init__(self, input_key: str, output_key: str):
        super().__init__(
            name=f"RunExcelETL_{input_key}",
            requires=[input_key],   # Ej: espera ctx.inputs['estudiantes']
            produces=[output_key]   # Ej: produce ctx.artifacts['df_consolidado']
        )
        self.input_key = input_key
        self.output_key = output_key

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)
        # --- PASO 1: Cargar inputs y parámetros desde el contexto ---
        archivos = ctx.inputs.get(self.input_key, [])
        if not archivos:
            print(f"Advertencia: No hay archivos en '{self.input_key}' para procesar.")
            ctx.artifacts[self.output_key] = pd.DataFrame()
            self._log_artifacts_delta(ctx, before)
            return

        # Obtenemos la config de headers (puede venir del txt cargado en LoadConfig)
        # Default global es 0 si no se especifica nada
        raw_header_config = ctx.params.get("header_row", 0)
        
        # Obtenemos el mapeo de columnas (renames)
        column_mapping = ctx.params.get("column_mapping", {})

        # --- PASO 2: Normalizar la configuración del header ---
        # Si el usuario pasó un solo entero, lo convertimos a la estructura de diccionario
        if isinstance(raw_header_config, int):
            header_conf = {"default": raw_header_config}
        elif isinstance(raw_header_config, dict):
            header_conf = raw_header_config
        else:
            # Fallback por seguridad
            header_conf = {"default": 0}

        df_list = []
        
        print(f"[{self.name}] Procesando {len(archivos)} archivos de tipo '{self.input_key}'...")

        # --- PASO 3: Iterar, Leer y Renombrar ---
        for ruta_archivo in archivos:
            nombre_archivo = os.path.basename(ruta_archivo)
            
            try:
                # 3.1: Determinar fila del header
                # Buscamos nombre exacto, si no está, usamos 'default'
                header_row = header_conf.get(nombre_archivo, header_conf.get("default", 0))

                # 3.2: Lectura del Excel
                # header=header_row le dice a pandas dónde leer los títulos
                temp_df = pd.read_excel(ruta_archivo, header=header_row)

                # 3.3: Renombrar columnas (Estandarización)
                # Esto es vital para que el concat posterior funcione bien
                if column_mapping:
                    # rename solo cambia las que encuentra, ignora las que no existen
                    temp_df.rename(columns=column_mapping, inplace=True)
                
                # OPCIONAL (Recomendado): Agregar origen para trazabilidad
                # temp_df["source_file"] = nombre_archivo

                df_list.append(temp_df)
                
            except Exception as e:
                print(f"Error leyendo archivo {nombre_archivo} con header_row={header_row}: {e}")
                continue

        # --- PASO 4: Consolidar y Guardar en Artifacts ---
        if df_list:
            df_consolidado = pd.concat(df_list, ignore_index=True)
            ctx.artifacts[self.output_key] = df_consolidado
            print(f"[{self.name}] Consolidado generado con {len(df_consolidado)} filas.")
        else:
            ctx.artifacts[self.output_key] = pd.DataFrame()
        self._log_artifacts_delta(ctx, before)

class EnrichWithContext(Step):
    """
    Step GENÉRICO para enriquecer y limpiar DataFrames.
    
    Realiza 3 acciones en orden:
    1. Inyecta columnas constantes desde ctx.params (ej: Asignatura, Año).
    2. Ejecuta una función de limpieza personalizada (ej: limpiar_columnas).
    3. Filtra el DataFrame final para dejar solo las columnas relevantes.
    """
    def __init__(
        self, 
        input_key: str, 
        output_key: str,
        context_mapping: Dict[str, str],
        columns_param_key: str = "columnas_relevantes",
        cleaning_func: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None
    ):
        """
        Args:
            input_key: Clave del artifact de entrada (ej: 'df_estudiantes_raw').
            output_key: Clave del artifact de salida (ej: 'df_estudiantes_clean').
            context_mapping: Diccionario {"Nombre Columna Nueva": "Clave en ctx.params"}.
                             Ej: {"Asignatura": "asignatura", "Mes": "mes"}
            columns_param_key: Clave en ctx.params que contiene la LISTA de columnas a mantener.
            cleaning_func: Función Python que recibe un DF y devuelve un DF limpio.
        """
        super().__init__(
            name=f"Enrich_{output_key}",
            requires=[input_key],
            produces=[output_key]
        )
        self.input_key = input_key
        self.output_key = output_key
        self.context_mapping = context_mapping
        self.columns_param_key = columns_param_key
        self.cleaning_func = cleaning_func

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)
        # 1. Cargar DataFrame entrada
        df = ctx.artifacts.get(self.input_key)
        
        if df is None or df.empty:
            print(f"[{self.name}] Advertencia: DataFrame de entrada vacío o inexistente.")
            ctx.artifacts[self.output_key] = pd.DataFrame()
            self._log_artifacts_delta(ctx, before)
            return

        # Trabajamos sobre una copia para no alterar el artifact original por error
        df = df.copy()

        # 4. Filtrar Columnas Relevantes
        # Obtenemos la lista de columnas permitidas desde la config
        cols_to_keep = ctx.params.get(self.columns_param_key, [])
        
        if cols_to_keep:
            # Intersección: Solo pedimos las que realmente existen en el DF para evitar KeyErrors
            # (Útil si el Excel traía menos columnas de las esperadas)
            existing_cols = [c for c in cols_to_keep if c in df.columns]
            
            # Advertencia si faltan columnas importantes podría ir aquí
            if len(existing_cols) < len(cols_to_keep):
                missing = set(cols_to_keep) - set(existing_cols)
                print(f"[{self.name}] Nota: Se descartaron columnas solicitadas que no existen: {missing}")
            
            df = df[existing_cols]

        # 2. Inyectar columnas de contexto (Reemplaza a tu 'agregar_columnas_dataframe')
        # Itera sobre el mapa: Crea columna "X" con el valor de ctx.params["y"]
        for col_name, param_key in self.context_mapping.items():
            valor = ctx.params.get(param_key)
            if valor is not None:
                df[col_name] = valor
            else:
                print(f"[{self.name}] Advertencia: Parámetro '{param_key}' no encontrado en contexto.")

        # 3. Aplicar función de limpieza específica (Tu 'limpiar_columnas')
        if self.cleaning_func:
            try:
                # Aquí ocurre la magia de reutilización: el Step no sabe qué hace la función, solo la ejecuta.
                df = self.cleaning_func(df)
            except Exception as e:
                raise ValueError(f"Error ejecutando función de limpieza en {self.name}: {e}")

        # 5. Guardar salida
        ctx.artifacts[self.output_key] = df
        print(f"[{self.name}] Finalizado. Filas: {len(df)}. Columnas: {list(df.columns)}")
        self._log_artifacts_delta(ctx, before)

# Lista de pasos SIMCE (solo para planificar, sin programar todavía)
SIMCE_STEPS_PLAN = [
    "1) DiscoverInputs: identificar archivos y roles (estudiantes, preguntas, resultados por curso, etc.)",
    "2) LoadStudents: leer excels de estudiantes (con skiprows cuando corresponda)",
    "3) LoadQuestions: leer excels de preguntas (con skiprows cuando corresponda)",
    "4) NormalizeColumns: estandarizar nombres de columnas y tipos (RUT, Curso, Rend en 0..1, etc.)",
    "5) EnrichMetadata: agregar Asignatura, Mes, Numero_Prueba desde nombre de archivo o columnas",
    "6) Validate: validaciones mínimas (columnas obligatorias, valores nulos, rangos)",
    "7) Consolidate: unir todo en datasets consolidados (estudiantes_consolidado, preguntas_consolidado)",
    "8) ComputeKPIs: cálculos para tablas y gráficos (resúmenes por curso, por pregunta, por habilidad, etc.)",
    "9) BuildArtifacts: generar archivos intermedios (excels de tablas, png de gráficos) en aux_files",
    "10) RenderReport: usar esquema_informe.json para armar variables.tex e informe.tex y compilar PDF",
    "11) ExportDB: opcional, cargar consolidados y métricas a SQLite/Postgres",
    "12) Alerts: opcional, generar alertas (bajo logro, preguntas críticas, etc.)",
]
