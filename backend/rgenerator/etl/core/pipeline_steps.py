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
    Inicializa el contexto base de la corrida y copia parametros al contexto.

    Parametros (kwargs):
        evaluation: nombre de la evaluacion.
        base_dir: ruta base del trabajo.
        inputs_dir: ruta de inputs (opcional; por defecto base_dir/inputs).
        anio/year, asignatura, mes, numero_prueba, etc.
        Cualquier otra clave se copia a ctx.params.

    Efectos:
        - define context.evaluation y context.run_id (timestamp).
        - copia kwargs a context.params.
        - define context.base_dir e inputs_dir.
        - actualiza context.status a "RUNNING".

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
        """Guarda kwargs en self.params y genera un timestamp de corrida."""
        super().__init__(name="InitRun")
        self.params = kwargs
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def run(self, context):
        """Actualiza el RunContext con identidad, parametros y rutas base."""
        before = self._snapshot_artifacts(context)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__

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
        context.last_step = self.name
        self._log_artifacts_delta(context, before)


class LoadConfig(Step):
    """
    Carga configuracion desde JSON y normaliza parametros en el contexto.

    Parametros:
        config_path (obligatorio): ruta al archivo JSON.

    Efectos:
        - ctx.params["config_path"] y ctx.params["output_filename"].
        - copia el resto del JSON a ctx.params sin sobrescribir lo anterior.
        - si existe ctx.outputs_dir, define ctx.outputs["consolidated_excel"].

    Ejemplo:
        LoadConfig("config/simce_estudiantes_lenguaje.json")
    """
    def __init__(
        self,
        config_path: Path | str,
    ):
        """Normaliza config_path a Path y guarda la ruta."""
        super().__init__(name="LoadConfig")
        self.config_path = Path(config_path)

    def run(self, ctx):
        """Lee el JSON, actualiza ctx.params y prepara la salida estandar."""
        before = self._snapshot_artifacts(ctx)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__
        if not self.config_path.exists():
            raise FileNotFoundError(f"No se encontró config: {self.config_path}")

        config = cargar_config_desde_json(str(self.config_path))

        # Normaliza defaults
        output_filename = str(config.get("output_filename")).strip()

        # Asegura params en el contexto
        if not hasattr(ctx, "params") or ctx.params is None:
            ctx.params = {}

        # Guarda config cruda y params normalizados
        ctx.params["config_path"] = str(self.config_path)
        ctx.params["output_filename"] = output_filename

        # Copia el resto tal cual, sin pisar lo ya normalizado
        for k, v in config.items():
            if k not in ctx.params:
                ctx.params[k] = v

        # Define ruta de salida estándar de esta corrida
        if hasattr(ctx, "outputs_dir"):
            ctx.outputs["consolidated_excel"] = ctx.outputs_dir / output_filename

        # Deja una marca simple para debug
        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)


class DiscoverInputs(Step):
    """
    Escanea un directorio y clasifica archivos segun reglas.

    Parametros:
        rules (obligatorio): dict {tipo: {extension?, contains?, exclude_prefix?}}.

    Efectos:
        - inicializa ctx.inputs[tipo] como listas vacias.
        - agrega rutas encontradas en ctx.inputs[tipo].
        - si el directorio no existe, registra advertencia y termina.

    Ejemplo:
        DiscoverInputs(rules={"estudiantes": {"extension": ".xlsx",
                      "contains": "Resultados"}})
    """
    def __init__(self, rules: dict):
        """Guarda las reglas de clasificacion de archivos."""
        super().__init__(name="DiscoverInputs")
        self.rules = rules

    def run(self, ctx):
        """Escanea ctx.inputs_dir y clasifica archivos en ctx.inputs."""
        before = self._snapshot_artifacts(ctx)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__
        input_dir = ctx.inputs_dir
        
        # 1. Inicializar las listas en el contexto según las claves del diccionario
        # Así aseguramos que existan aunque no se encuentren archivos (quedarán vacías)
        for key in self.rules.keys():
            ctx.inputs[key] = []

        if not input_dir.exists():
            self._log(f"Advertencia: Directorio {input_dir} no existe.")
            ctx.last_step = self.name
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

        #self._log(f"DiscoverInputs: Se encontraron {files_found} archivos clasificados en {list(self.rules.keys())}.")
        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)

class RunExcelETL(Step):
    """
    Consolida archivos Excel y guarda el resultado en artifacts.

    Parametros:
        input_key (opcional): clave en ctx.inputs con archivos a procesar.
            Si no se entrega, se intenta resolver desde el contexto.
        output_key (opcional): clave en ctx.artifacts para el DataFrame.
            Si no se entrega, se genera como "df_consolidado_{input_key}".

    Efectos:
        - ctx.artifacts[output_key] con DataFrame consolidado (o vacio).
        - ctx.last_artifact_key actualizado con output_key.

    Ejemplo:
        RunExcelETL(input_key="estudiantes", output_key="df_estudiantes_raw")
    """
    def __init__(self, input_key: Optional[str] = None, output_key: Optional[str] = None):
        """Configura claves de entrada/salida y el nombre del step."""
        resolved_output_key = output_key
        if input_key and not resolved_output_key:
            resolved_output_key = f"df_consolidado_{input_key}"
        super().__init__(
            name=f"RunExcelETL_{input_key}" if input_key else "RunExcelETL",
            requires=[input_key] if input_key else [],   # Ej: espera ctx.inputs['estudiantes']
            produces=[resolved_output_key] if resolved_output_key else []   # Ej: produce ctx.artifacts['df_consolidado']
        )
        self.input_key = input_key
        self.output_key = resolved_output_key

    def run(self, ctx):
        """Lee Excels, aplica select/rename y consolida en un DataFrame."""
        before = self._snapshot_artifacts(ctx)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__
        # Resolver input_key desde contexto si no fue entregado
        input_key = self.input_key
        if not input_key:
            input_key = ctx.params.get("input_key") or ctx.params.get("default_input_key")
            if not input_key and hasattr(ctx, "inputs") and len(ctx.inputs) == 1:
                input_key = next(iter(ctx.inputs.keys()))
        if not input_key:
            raise ValueError(f"[{self.name}] No se pudo resolver input_key desde el contexto.")
        self.input_key = input_key

        # Resolver output_key automaticamente si no fue entregado
        output_key = self.output_key or f"df_consolidado_{input_key}"
        self.output_key = output_key
        self.requires = [input_key]
        self.produces = [output_key]

        # --- PASO 1: Cargar inputs y parametros desde el contexto ---
        archivos = ctx.inputs.get(input_key, [])
        if not archivos:
            self._log(f"Advertencia: No hay archivos en '{input_key}' para procesar.")
            ctx.artifacts[output_key] = pd.DataFrame()
            ctx.last_artifact_key = output_key
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # Obtenemos la config de headers (puede venir del json cargado en LoadConfig)
        # Default global es 0 si no se especifica nada
        raw_header_config = ctx.params.get("header_row", 0)

        # Se obtienen los nombres de las columnas a mantener o seleccionar
        select_columns = ctx.params.get("select_columns", [])
        # Obtenemos el mapeo de columnas (renames)
        column_mapping = ctx.params.get("rename_columns", {})

        # --- PASO 2: Normalizar la configuracion del header ---
        # Si el usuario paso un solo entero, lo convertimos a la estructura de diccionario
        if isinstance(raw_header_config, int):
            header_conf = {"default": raw_header_config}
        elif isinstance(raw_header_config, dict):
            header_conf = raw_header_config
        else:
            # Fallback por seguridad
            header_conf = {"default": 0}

        df_list = []

        # --- PASO 3: Iterar, Leer y Renombrar ---
        for ruta_archivo in archivos:
            nombre_archivo = os.path.basename(ruta_archivo)

            try:
                # 3.1: Determinar fila del header
                # Buscamos nombre exacto, si no esta, usamos 'default'
                header_row = header_conf.get(nombre_archivo, header_conf.get("default", 0))

                # 3.2: Lectura del Excel
                # header=header_row le dice a pandas donde leer los titulos
                temp_df = pd.read_excel(ruta_archivo, header=header_row)

                # 3.3: Select columns
                if select_columns:
                    temp_df = temp_df[[col for col in select_columns if col in temp_df.columns]]

                # 3.4: Renombrar columnas (Estandarizacion)
                # Esto es vital para que el concat posterior funcione bien
                if column_mapping:
                    # rename solo cambia las que encuentra, ignora las que no existen
                    temp_df.rename(columns=column_mapping, inplace=True)

                df_list.append(temp_df)

            except Exception as e:
                self._log(f"Error leyendo archivo {nombre_archivo} con header_row={header_row}: {e}")
                continue

        # --- PASO 4: Consolidar y Guardar en Artifacts ---
        if df_list:
            df_consolidado = pd.concat(df_list, ignore_index=True)
            ctx.artifacts[output_key] = df_consolidado
        else:
            ctx.artifacts[output_key] = pd.DataFrame()
        ctx.last_artifact_key = output_key
        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)

class EnrichWithContext(Step):
    """
    Enriquece y limpia DataFrames con parametros del contexto.

    Parametros:
        input_key (opcional): clave del artifact de entrada.
            Si no se entrega, usa ctx.last_artifact_key o ctx.params["default_artifact_key"].
        output_key (opcional): clave del artifact de salida.
            Si no se entrega, se deriva desde input_key.
        context_mapping (opcional): dict {columna_nueva: valor}.
            Si no se entrega, usa ctx.params["enrich_data"].
        cleaning_func (opcional): funcion que recibe y devuelve DataFrame.

    Efectos:
        - ctx.artifacts[output_key] con DataFrame enriquecido.
        - ctx.last_artifact_key actualizado con output_key.

    Ejemplo:
        EnrichWithContext("df_raw", "df_clean",
                          {"Asignatura": "Lenguaje"})
    """
    def __init__(
        self, 
        input_key: Optional[str] = None, 
        output_key: Optional[str] = None,
        context_mapping: Optional[Dict[str, str]] = None,
        cleaning_func: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None
    ):
        """
        Inicializa el step y define reglas de enrichment opcionales.

        Parametros:
            input_key (opcional): clave del artifact de entrada.
            output_key (opcional): clave del artifact de salida.
            context_mapping (opcional): dict {columna_nueva: valor}.
            cleaning_func (opcional): funcion que transforma el DataFrame.
        """
        resolved_output_key = output_key
        if input_key and not resolved_output_key:
            resolved_output_key = self._derive_output_key(input_key)
        super().__init__(
            name=f"Enrich_{resolved_output_key}" if resolved_output_key else "EnrichWithContext",
            requires=[input_key] if input_key else [],
            produces=[resolved_output_key] if resolved_output_key else []
        )
        self.input_key = input_key
        self.output_key = resolved_output_key
        self.context_mapping = context_mapping or {}
        self.cleaning_func = cleaning_func

    @staticmethod
    def _derive_output_key(input_key: str) -> str:
        base = input_key
        if base.startswith("df_consolidado_"):
            base = base[len("df_consolidado_"):]
        elif base.startswith("df_"):
            base = base[len("df_"):]
        return f"df_enriched_{base}"

    def run(self, ctx):
        """Inyecta columnas de contexto y aplica limpieza opcional."""
        before = self._snapshot_artifacts(ctx)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__
        # Resolver input/output desde contexto si no fueron entregados
        input_key = self.input_key or ctx.last_artifact_key or ctx.params.get("default_artifact_key")
        if not input_key:
            raise ValueError(f"[{self.name}] No se pudo resolver input_key desde el contexto.")
        output_key = self.output_key or self._derive_output_key(input_key)
        self.input_key = input_key
        self.output_key = output_key
        self.requires = [input_key]
        self.produces = [output_key]
        # 1. Cargar DataFrame entrada
        df = ctx.artifacts.get(input_key)
        
        # Si self.context_mapping es diccionario vacío, se importa del contexto
        if not self.context_mapping:
            self.context_mapping = ctx.params.get("enrich_data", {})

        if df is None or df.empty:
            self._log(f"[{self.name}] Advertencia: DataFrame de entrada vacio o inexistente.")
            ctx.artifacts[output_key] = pd.DataFrame()
            ctx.last_artifact_key = output_key
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # Trabajamos sobre una copia para no alterar el artifact original por error
        df = df.copy()

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
        ctx.artifacts[output_key] = df
        ctx.last_artifact_key = output_key
        #self._log(f"[{self.name}] Finalizado. Filas: {len(df)}. Columnas: {list(df.columns)}")
        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)

class ExportConsolidatedExcel(Step):
    """
    Exporta un DataFrame a un archivo Excel.

    Parametros:
        input_key (opcional): clave del artifact de entrada.
            Si no se entrega, usa ctx.last_artifact_key o ctx.params["default_artifact_key"].
        output_filename (opcional): nombre del archivo de salida.
            Si no se entrega, usa ctx.params["output_filename"] o "salida_etl.xlsx".

    Efectos:
        - escribe el archivo en ctx.base_dir / output_filename.
        - guarda la ruta en ctx.outputs["consolidated_excel"].
    """
    def __init__(
            self, 
            input_key: Optional[str] = None, 
            output_filename: str ="", 
):
        """Guarda claves de entrada/salida para la exportacion."""
        super().__init__(
            name="ExportConsolidatedExcel",
            requires=[input_key] if input_key else []
        )
        self.input_key = input_key
        self.output_filename = output_filename


    def run(self, ctx):
        """Exporta el DataFrame de entrada a Excel."""
        before = self._snapshot_artifacts(ctx)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__
        input_key = self.input_key or ctx.last_artifact_key or ctx.params.get("default_artifact_key")
        if not input_key:
            raise ValueError(f"[{self.name}] No se pudo resolver input_key desde el contexto.")
        self.input_key = input_key
        self.requires = [input_key]

        df = ctx.artifacts.get(input_key)
        if df is None or df.empty:
            self._log(f"[{self.name}] Advertencia: DataFrame de entrada vacio o inexistente. No se exporta nada.")
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        if not self.output_filename:
            self.output_filename = ctx.params.get("output_filename", "salida_etl.xlsx")
        output_path = ctx.base_dir / self.output_filename
        try:
            df.to_excel(output_path, index=False)
            #self._log(f"[{self.name}] Exportado DataFrame a Excel en: {output_path}")
            ctx.outputs["consolidated_excel"] = output_path
        except Exception as e:
            raise IOError(f"[{self.name}] Error exportando DataFrame a Excel: {e}")

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)

class DeleteTempFiles(Step):
    """
    Elimina archivos y directorios temporales generados durante la corrida.

    Efectos:
        - intenta eliminar context.aux_dir, context.outputs_dir y context.work_dir.
        - registra mensajes por cada directorio.
    """
    def __init__(self):
        """Inicializa el step sin parametros."""
        super().__init__(name="DeleteTempFiles")

    def run(self, context):
        """Elimina directorios temporales si existen."""
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__
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

        context.last_step = self.name

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
