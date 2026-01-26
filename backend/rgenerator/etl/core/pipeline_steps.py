"""Archivo contiene la definición de los steps que se pueden añadir a una pipeline."""

# Librerias estandar
from datetime import datetime
from pathlib import Path
import pandas as pd
import os 
from typing import Callable, Optional, Dict, List

# Importaciones internas de RGenerator
from .step import Step
from rgenerator.tooling.config_tools import cargar_config_desde_json

##### Steps definidos para SIMCE 

class InitRun(Step):
    """
    Inicializa el contexto y directorios de la corrida.
    
    Parametros:
        Se reciben via kwargs. Claves esperadas para esta clase:
            - evaluation: Nombre de la evaluacion.
            - base_dir: Ruta base donde se crea la carpeta de trabajo.
            - anio / year: Anio de la evaluacion (se copia a ctx.params).
            - asignatura: Asignatura asociada.
            - mes: Mes asociado a la evaluacion.
            - numero_prueba: Numero de prueba.
        Cualquier otra clave se copia tal cual a ctx.params.
    
    Output:
        - ctx.params poblado con los parametros base.
        - ctx.work_dir, ctx.inputs_dir, ctx.aux_dir, ctx.outputs_dir creados.
        - ctx.status actualizado a "RUNNING".
    
    Ejemplo:
        InitRun(
            evaluation="simce",
            base_dir=Path("data"),
            anio=2025,
            asignatura="Lenguaje",
            mes="Noviembre",
            numero_prueba=5,
        )
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
        
        # base_dir puede existir dentro del contexto y en self.params venir vacío
        context.base_dir = Path(self.params.get("base_dir", context.base_dir))
        context.inputs_dir = Path(self.params.get("inputs_dir", context.base_dir / "inputs"))
        
        """
        context.aux_dir = context.work_dir / "aux_files"
        context.outputs_dir = context.work_dir / "outputs"
        context.work_dir = context.base_dir / context.evaluation / context.run_id
        for d in [context.work_dir, context.inputs_dir, context.aux_dir, context.outputs_dir]:
            d.mkdir(parents=True, exist_ok=True)
        """
        ########################################

        context.status = "RUNNING"
        self._log_artifacts_delta(context, before)


class LoadConfig(Step):
    """
    Carga configuracion desde JSON y normaliza parametros.
    
    Parametros:
        config_path (obligatorio): Ruta al archivo JSON.
    
    Output:
        - ctx.params con valores normalizados (nombre_salida, etc.).
        - ctx.outputs["excel_salida"] si existe ctx.outputs_dir.
    
    Ejemplo:
        LoadConfig("config/simce_estudiantes_lenguaje.json")
    """
    def __init__(
        self,
        config_path: Path | str,
    ):
        super().__init__(name="LoadConfig")
        self.config_path = Path(config_path)

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)
        if not self.config_path.exists():
            raise FileNotFoundError(f"No se encontró config: {self.config_path}")

        config = cargar_config_desde_json(str(self.config_path))

        # Normaliza defaults
        nombre_salida = str(config.get("nombre_salida", "salida_etl.xlsx")).strip()

        # Asegura params en el contexto
        if not hasattr(ctx, "params") or ctx.params is None:
            ctx.params = {}

        # Guarda config cruda y params normalizados
        ctx.params["config_path"] = str(self.config_path)
        ctx.params["nombre_salida"] = nombre_salida

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
    Escanea un directorio y clasifica archivos segun reglas.
    
    Parametros:
        rules (obligatorio): Diccionario con criterios por tipo.
            Opcionales: "extension", "contains", "exclude_prefix".
    
    Output:
        - ctx.inputs[tipo] con rutas clasificadas.
    
    Ejemplo:
        DiscoverInputs(rules={"estudiantes": {"extension": ".xlsx",
                      "contains": "Resultados"}})
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
            self._log(f"Advertencia: Directorio {input_dir} no existe.")
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

        self._log(f"DiscoverInputs: Se encontraron {files_found} archivos clasificados en {list(self.rules.keys())}.")
        self._log_artifacts_delta(ctx, before)

class RunExcelETL(Step):
    """
    Consolida archivos Excel y guarda el resultado en artifacts.
    
    Parametros:
        input_key (obligatorio): Clave en ctx.inputs con archivos a procesar.
        output_key (obligatorio): Clave en ctx.artifacts para el DataFrame.
    
    Output:
        - ctx.artifacts[output_key] con DataFrame consolidado (o vacio).
    
    Ejemplo:
        RunExcelETL(input_key="estudiantes", output_key="df_estudiantes_raw")
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
            self._log(f"Advertencia: No hay archivos en '{self.input_key}' para procesar.")
            ctx.artifacts[self.output_key] = pd.DataFrame()
            self._log_artifacts_delta(ctx, before)
            return

        # Obtenemos la config de headers (puede venir del json cargado en LoadConfig)
        # Default global es 0 si no se especifica nada
        raw_header_config = ctx.params.get("header_row", 0)

        # Se obtienen los nombres de las columnas a mantener o seleccionar
        select_columns = ctx.params.get("select_columns", [])
        # Obtenemos el mapeo de columnas (renames)
        column_mapping = ctx.params.get("rename_columns", {})

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
        
        self._log(f"[{self.name}] Procesando {len(archivos)} archivos de tipo '{self.input_key}'...")

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

                #3.3: Select columns 
                if select_columns:
                    temp_df = temp_df[[col for col in select_columns if col in temp_df.columns]]

                # 3.4: Renombrar columnas (Estandarización)
                # Esto es vital para que el concat posterior funcione bien
                if column_mapping:
                    # rename solo cambia las que encuentra, ignora las que no existen
                    temp_df.rename(columns=column_mapping, inplace=True)
                
                # OPCIONAL (Recomendado): Agregar origen para trazabilidad
                # temp_df["source_file"] = nombre_archivo

                df_list.append(temp_df)
                
            except Exception as e:
                self._log(f"Error leyendo archivo {nombre_archivo} con header_row={header_row}: {e}")
                continue

        # --- PASO 4: Consolidar y Guardar en Artifacts ---
        if df_list:
            df_consolidado = pd.concat(df_list, ignore_index=True)
            ctx.artifacts[self.output_key] = df_consolidado
            self._log(f"[{self.name}] Consolidado generado con {len(df_consolidado)} filas.")
        else:
            ctx.artifacts[self.output_key] = pd.DataFrame()
        self._log_artifacts_delta(ctx, before)

class EnrichWithContext(Step):
    """
    Enriquecer y limpiar DataFrames con parametros del contexto.
    
    Parametros:
        input_key (obligatorio): Clave del artifact de entrada.
        output_key (obligatorio): Clave del artifact de salida.
        context_mapping (obligatorio): Mapa {"ColumnaNueva": "param_key"}.
        columns_param_key (opcional): Clave con columnas a mantener.
        cleaning_func (opcional): Funcion que recibe y devuelve DataFrame.
    
    Output:
        - ctx.artifacts[output_key] con DataFrame enriquecido.
    
    Ejemplo:
        EnrichWithContext("df_raw", "df_clean",
                          {"Asignatura": "asignatura"},
                          columns_param_key="select_columns")
    """
    def __init__(
        self, 
        input_key: str, 
        output_key: str,
        context_mapping: Dict[str, str] = {},
        cleaning_func: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None
    ):
        """
        Parametros:
            input_key (obligatorio): Clave del artifact de entrada.
            output_key (obligatorio): Clave del artifact de salida.
            context_mapping (opcional): Mapa {"ColumnaNueva": "param_key"}.
            cleaning_func (opcional): Funcion que recibe y devuelve DataFrame.
        """
        super().__init__(
            name=f"Enrich_{output_key}",
            requires=[input_key],
            produces=[output_key]
        )
        self.input_key = input_key
        self.output_key = output_key
        self.context_mapping = context_mapping
        self.cleaning_func = cleaning_func

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)
        # 1. Cargar DataFrame entrada
        df = ctx.artifacts.get(self.input_key)
        
        # Si self.context_mapping es diccionario vacío, se importa del contexto
        if not self.context_mapping:
            self.context_mapping = ctx.params.get("enrich_data", {})

        if df is None or df.empty:
            self._log(f"[{self.name}] Advertencia: DataFrame de entrada vacío o inexistente.")
            ctx.artifacts[self.output_key] = pd.DataFrame()
            self._log_artifacts_delta(ctx, before)
            return

        # Trabajamos sobre una copia para no alterar el artifact original por error
        df = df.copy()
        print(f"[{self.name}] Context Mapping: {self.context_mapping}")

        # 2. Inyectar columnas de contexto (Reemplaza a tu 'agregar_columnas_dataframe')
        # Itera sobre el mapa: Crea columna "X" con el valor de self.context_mapping["y"]
        for col_name, valor in self.context_mapping.items():
            try:
                df[col_name] = valor
            except Exception as e:
                self._log(f"[{self.name}] Error al inyectar columna '{col_name}': {e}")

        # 3. Aplicar función de limpieza específica (Tu 'limpiar_columnas')
        if self.cleaning_func:
            try:
                # Aquí ocurre la magia de reutilización: el Step no sabe qué hace la función, solo la ejecuta.
                df = self.cleaning_func(df)
            except Exception as e:
                raise ValueError(f"Error ejecutando función de limpieza en {self.name}: {e}")

        # 5. Guardar salida
        ctx.artifacts[self.output_key] = df
        self._log(f"[{self.name}] Finalizado. Filas: {len(df)}. Columnas: {list(df.columns)}")
        self._log_artifacts_delta(ctx, before)

class ExportConsolidatedExcel(Step):
    """
    Exporta DataFrame consolidado a archivo Excel.
    
    Parametros:
        input_key (obligatorio): Clave del artifact de entrada.
        output_path_param (obligatorio): Clave en ctx.params con ruta de salida.
    
    Output:
        - Archivo Excel en la ruta especificada.
    """
    def __init__(
            self, 
            input_key: str, 
            output_name: str ="", 
):
        super().__init__(
            name="ExportConsolidatedExcel",
            requires=[input_key]
        )
        self.input_key = input_key
        self.output_name = output_name


    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)
        df = ctx.artifacts.get(self.input_key)
        if df is None or df.empty:
            self._log(f"[{self.name}] Advertencia: DataFrame de entrada vacío o inexistente. No se exporta nada.")
            self._log_artifacts_delta(ctx, before)
            return

        if not self.output_name:
            self.output_name = ctx.params.get("nombre_salida", "salida_etl.xlsx")
        output_path = ctx.base_dir / self.output_name
        try:
            df.to_excel(output_path, index=False)
            self._log(f"[{self.name}] Exportado DataFrame a Excel en: {output_path}")
        except Exception as e:
            raise IOError(f"[{self.name}] Error exportando DataFrame a Excel: {e}")

        self._log_artifacts_delta(ctx, before)

class DeleteTempFiles(Step):
    """
    Elimina archivos y directorios temporales generados durante la corrida.
    
    Parametros:
        No recibe parametros.

    Output:
        - Archivos y directorios eliminados.
    """
    def __init__(self):
        super().__init__(name="DeleteTempFiles")

    def run(self, context):
        import shutil
        # base_dir puede existir dentro del contexto y en self.params venir vacío
        self.temp_dirs = [
            context.aux_dir,
            context.outputs_dir,
            context.work_dir
        ]
        
        for dir_path in self.temp_dirs:
            if dir_path.exists() and dir_path.is_dir():
                try:
                    shutil.rmtree(dir_path)
                    self._log(f"[{self.name}] Eliminado directorio temporal: {dir_path}")
                except Exception as e:
                    self._log(f"[{self.name}] Error eliminando directorio {dir_path}: {e}")
            else:
                self._log(f"[{self.name}] Directorio no existe o no es un directorio: {dir_path}")

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
