"""Archivo contiene la definición de los steps que se pueden añadir a una pipeline."""

# Librerias estandar
from datetime import datetime
from pathlib import Path
import pandas as pd
import json
import os
import shutil
from typing import Callable, Optional, Dict, List

# Importaciones internas de RGenerator
from .step import Step, WaitingForInputException
from rgenerator.tooling.config_tools import cargar_config_desde_json
from rgenerator.tooling import plot_tools, report_tools
from rgenerator.tooling.report_docx_tools import render_docx_report
from config import UPLOADS_DIR, PIPELINE_RUNS_DIR, SPECS_DB_PATH, REPORTS_TEMPLATES_DIR
from rgenerator.tooling.constants import formato_informe_generico, indice_alfabetico
import shutil
from rgenerator.tooling.data_tools import safe_text_to_json

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

        # Carpetas estándar - todo centralizado en PIPELINE_RUNS_DIR
        pipeline_id = context.pipeline_id or "local"
        context.work_dir = PIPELINE_RUNS_DIR / "runs" / str(pipeline_id) / context.run_id
        context.inputs_dir = context.work_dir / "inputs"
        context.aux_dir = context.work_dir / "aux_files"
        context.outputs_dir = context.work_dir / "outputs"

        # Crear directorios
        for d in [context.work_dir, context.inputs_dir, context.aux_dir, context.outputs_dir]:
            d.mkdir(parents=True, exist_ok=True)

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


class LoadConfigFromSpec(Step):
    """
    Carga configuración desde la base de datos de specs (templates.xlsx).

    Lee la columna 'config_json' del spec indicado y carga todas las
    secciones al contexto del pipeline. Es genérico: funciona con specs
    de tipo ETL, Reporte, Dashboard, etc.

    Parámetros:
        spec_id (int): ID del spec/template en templates.xlsx.

    Efectos en ctx.params:
        - etlParams → se transforman a formato plano (header_row, select_columns, etc.)
        - variables_documento → ctx.params["variables_documento"]
        - secciones_fijas → ctx.params["secciones_fijas"]
        - secciones_dinamicas → ctx.params["secciones_dinamicas"]
        - Cualquier otra sección presente se copia tal cual.

    Ejemplo:
        LoadConfigFromSpec(spec_id=1)
    """
    def __init__(self, spec_id: int):
        super().__init__(name="LoadConfigFromSpec")
        self.spec_id = spec_id

    def _transform_etl_params(self, etl_params: list) -> dict:
        """
        Transforma etlParams del formato spec al formato plano.

        Formatos soportados:
          - text:      {"id": "header_row", "value": "23"}           → {"header_row": 23}
          - list_text:  {"id": "select_columns", "value": ["A","B"]} → {"select_columns": ["A","B"]}
          - list_pair:  {"id": "rename_columns", "value": [{"key":"B","val":"Buenas"},...]} → {"rename_columns": {"B":"Buenas",...}}
        """
        result = {}
        for param in etl_params:
            param_id = param.get("id")
            value = param.get("value")
            param_type = param.get("type", "text")

            if param_id == "output_name":
                continue  # Se omite output_filename

            if param_type == "list_pair" and isinstance(value, list):
                if param_id == "enrich_data":
                    # Conservar lista completa para preservar flags como user_input
                    result[param_id] = value
                else:
                    result[param_id] = {item["key"]: item["val"] for item in value if "key" in item and "val" in item}
            elif param_type == "text" and isinstance(value, str):
                try:
                    result[param_id] = int(value)
                except ValueError:
                    try:
                        result[param_id] = float(value)
                    except ValueError:
                        result[param_id] = value
            else:
                result[param_id] = value

        return result

    def run(self, ctx):
        """Lee el spec desde Excel y carga todas las secciones al contexto."""
        before = self._snapshot_artifacts(ctx)

        if not SPECS_DB_PATH.exists():
            raise FileNotFoundError(f"No se encontró la base de datos de specs: {SPECS_DB_PATH}")

        df = pd.read_excel(SPECS_DB_PATH)
        # Buscar por id_spec
        if 'id_spec' not in df.columns:
            # Fallback si por alguna razón no se renombró
            col_id = 'id_template'
        else:
            col_id = 'id_spec'
            
        row = df[df[col_id] == self.spec_id]

        if row.empty:
            raise ValueError(f"No se encontró spec con {col_id}={self.spec_id}")

        config_raw = row.iloc[0].get('config_json', '')
        # Intentar cargar JSON seguro
        config = safe_text_to_json(config_raw)
        
        if not config:
             # Si no hay config_json valido, quizas es un spec antiguo sin migrar
             raise ValueError(f"Spec {self.spec_id} no tiene configuración válida en config_json")

        # Asegurar que ctx.params exista
        if not hasattr(ctx, "params") or ctx.params is None:
            ctx.params = {}

        loaded_keys = []

        # --- etlParams: transformar a formato plano ---
        etl_params = config.get("etlParams", [])
        
        if etl_params:
            flat_params = self._transform_etl_params(etl_params)
            for k, v in flat_params.items():
                
                # Forzar actualización desde el Spec (sobrescribir si existe)
                ctx.params[k] = v
            loaded_keys.append(f"etlParams({len(flat_params)})")

        # --- Otras secciones: copiar tal cual ---
        direct_sections = ["variables_documento", "secciones_fijas", "secciones_dinamicas"]
        for section in direct_sections:
            if section in config and config[section]:
                ctx.params[section] = config[section]
                loaded_keys.append(section)

        # --- Secciones desconocidas: copiar también ---
        known_keys = {"etlParams"} | set(direct_sections)
        for k, v in config.items():
            if k not in known_keys and k not in ctx.params:
                ctx.params[k] = v
                loaded_keys.append(k)

        self._log(f"Spec {self.spec_id} cargado: {', '.join(loaded_keys) if loaded_keys else 'vacío'}")

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
                header_row = header_conf.get(nombre_archivo, header_conf.get("default", 0))

                # 3.2: Lectura del Excel
                temp_df = pd.read_excel(ruta_archivo, header=header_row)

                # 3.3: Select columns
                if select_columns:
                    temp_df = temp_df[[col for col in select_columns if col in temp_df.columns]]

                # 3.4: Renombrar columnas (Estandarizacion)
                if column_mapping:
                    temp_df.rename(columns=column_mapping, inplace=True)

                # 3.5: Enriquecimiento POR ARCHIVO (datos recopilados por EnrichWithUserInput)
                user_inputs_store = getattr(ctx, "user_inputs", {}).get("enrich_per_file", {})
                file_user_data = user_inputs_store.get(nombre_archivo, {})
                for col, val in file_user_data.items():
                    temp_df[col] = val

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

class EnrichWithUserInput(Step):
    """
    Solicita datos de enriquecimiento al usuario durante la ejecución del pipeline.

    Este paso detecta campos de enrich_data marcados con user_input=True,
    identifica los archivos a procesar, y pausa la ejecución para solicitar
    valores específicos por archivo al usuario.

    Debe colocarse ANTES de RunExcelETL en el pipeline.

    Flujo:
        1. Lee enrich_data de ctx.params y filtra campos con user_input=True.
        2. Descubre los archivos subidos en ctx.inputs.
        3. Verifica si ctx.user_inputs ya tiene los valores necesarios.
        4. Si faltan valores -> lanza WaitingForInputException (pausa el pipeline).
        5. Si todos los valores están -> pasa sin hacer nada (RunExcelETL los aplicará).
    """
    def __init__(self, input_key: Optional[str] = None):
        super().__init__(
            name="EnrichWithUserInput",
            description="Solicita datos de enriquecimiento por archivo al usuario"
        )
        self.input_key = input_key

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)

        # 1. Obtener campos que requieren input del usuario
        enrich_data = ctx.params.get("enrich_data", [])
        
        if isinstance(enrich_data, list):
            user_input_fields = [p for p in enrich_data if isinstance(p, dict) and p.get("user_input")]
        else:
            # Fallback seguro
            user_input_fields = []

        if not user_input_fields:
            self._log(f"[{self.name}] No hay campos que requieran input del usuario. Saltando.")
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 2. Descubrir archivos a procesar
        input_key = self.input_key
        if not input_key:
            input_key = ctx.params.get("input_key") or ctx.params.get("default_input_key")
            if not input_key and hasattr(ctx, "inputs") and len(ctx.inputs) == 1:
                input_key = next(iter(ctx.inputs.keys()))

        if not input_key or input_key not in getattr(ctx, "inputs", {}):
            raise ValueError(f"[{self.name}] No se encontró input_key '{input_key}' en ctx.inputs.")

        archivos = ctx.inputs.get(input_key, [])
        file_names = [os.path.basename(f) for f in archivos]

        if not file_names:
            self._log(f"[{self.name}] No hay archivos para procesar. Saltando.")
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 3. Verificar si ya tenemos todos los inputs
        user_inputs_store = getattr(ctx, "user_inputs", {}).get("enrich_per_file", {})

        missing_data = False
        for fname in file_names:
            for field in user_input_fields:
                col_key = field.get("key")
                if not user_inputs_store.get(fname, {}).get(col_key):
                    missing_data = True
                    break
            if missing_data:
                break

        if missing_data:
            # 4. Pausar ejecución y solicitar datos al frontend
            input_details = {
                "type": "enrich_per_file",
                "files": file_names,
                "fields": [
                    {"key": f.get("key"), "label": f.get("val") or f.get("key")}
                    for f in user_input_fields
                ]
            }
            raise WaitingForInputException(self.name, input_details)

        # 5. Todos los inputs disponibles, continuar
        self._log(f"[{self.name}] Inputs recibidos para {len(file_names)} archivos. Continuando.")
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
            # Importar enrich_data del contexto, EXCLUYENDO campos user_input
            # (esos se manejan en RunExcelETL por archivo)
            raw_enrich = ctx.params.get("enrich_data", {})
            if isinstance(raw_enrich, list):
                # Formato lista de {key, val, user_input?}
                self.context_mapping = {
                    p.get("key"): p.get("val") 
                    for p in raw_enrich 
                    if p.get("key") and not p.get("user_input")
                }
            else:
                # Formato dict legacy {col: val}
                self.context_mapping = raw_enrich

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

class ModifyColumnValues(Step):
    """
    Modifica valores de columnas usando reglas definidas (regex, replace, map, strip).
    
    Parametros:
        input_key (opcional): clave del artifact de entrada.
            Si no se entrega, usa ctx.last_artifact_key o ctx.params["default_artifact_key"].
        output_key (opcional): clave del artifact de salida.
            Si no se entrega, se deriva desde input_key (ej: df_modified_...).
        transformations (opcional): lista de reglas de transformación.
            Si no se entrega, busca en ctx.params["transformations"].
            
    Ejemplo de regla:
        {
            "columna": "Curso",
            "operacion": "regex",
            "parametros": {"patron": "° medio ", "reemplazo": " "}
        }
    """
    def __init__(
        self,
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        transformations: Optional[List[Dict]] = None
    ):
        resolved_output_key = output_key
        if input_key and not resolved_output_key:
             resolved_output_key = f"df_modified_{input_key}"
             
        super().__init__(
            name="ModifyColumnValues",
            requires=[input_key] if input_key else [],
            produces=[resolved_output_key] if resolved_output_key else []
        )
        self.input_key = input_key
        self.output_key = resolved_output_key
        self.transformations = transformations or []
        
    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)
        
        # 1. Resolver input/output
        input_key = self.input_key or ctx.last_artifact_key or ctx.params.get("default_artifact_key")
        if not input_key:
            raise ValueError(f"[{self.name}] No se pudo resolver input_key.")
            
        output_key = self.output_key or f"df_modified_{input_key}"
        self.input_key = input_key
        self.output_key = output_key
        
        # 2. Obtener Dataframe
        df = ctx.artifacts.get(input_key)
        if df is None or df.empty:
            self._log(f"[{self.name}] Warning: DataFrame vacío o inexistente en {input_key}")
            ctx.artifacts[output_key] = pd.DataFrame()
            ctx.last_artifact_key = output_key
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 3. Obtener transformaciones (desde init o context)
        transforms = self.transformations
        if not transforms:
            transforms = ctx.params.get("transformations", [])
            
        # 4. Aplicar transformaciones usando etl_tools
        from rgenerator.tooling.etl_tools import modificar_valores_columna
        
        # Trabajamos sobre copia
        df_mod = df.copy()
        try:
             df_mod = modificar_valores_columna(df_mod, transforms)
        except Exception as e:
            raise ValueError(f"[{self.name}] Error aplicando transformaciones: {e}")
            
        # 5. Guardar
        ctx.artifacts[output_key] = df_mod
        ctx.last_artifact_key = output_key
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
        print(output_path)
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


class GenerateGraphics(Step):
    """
    Genera gráficos utilizando herramientas de matplotlib definidas en plot_tools.

    Lee el esquema de gráficos desde ctx.params["charts_schema"] (cargado por un step
    previo como LoadConfigFromSpec) o directamente desde el constructor.

    Cada entrada del esquema tiene:
        - type: nombre de la función en plot_tools (ej: "grafico_barras_promedio_por")
        - input_key: clave del DataFrame en ctx.artifacts
        - output_filename: nombre del archivo de salida (ej: "logro_por_curso.png")
        - params: kwargs adicionales para la función

    Efectos:
        - Crea archivos .png en ctx.aux_dir.
        - Registra rutas generadas en ctx.artifacts["generated_charts"].
    """
    def __init__(self, charts_schema: Optional[List[Dict]] = None):
        """Inicializa el step, opcionalmente con esquema directo."""
        super().__init__(name="GenerateGraphics")
        self.charts_schema = charts_schema

    def run(self, ctx):
        """Genera los gráficos solicitados y registra las rutas en ctx.artifacts."""
        before = self._snapshot_artifacts(ctx)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__

        # 1. Resolver esquema: constructor directo o ctx.params
        schema = self.charts_schema
        if not schema:
            schema = ctx.params.get("charts_schema", [])

        if not schema:
            self._log(f"[{self.name}] Advertencia: No se encontraron definiciones de gráficos.")
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 2. Resolver directorio auxiliar
        aux_dir = getattr(ctx, "aux_dir", None)
        if not aux_dir:
            if hasattr(ctx, "base_dir"):
                aux_dir = ctx.base_dir / "aux_files"
            else:
                aux_dir = Path("aux_files")
            ctx.aux_dir = aux_dir

        if not aux_dir.exists():
            aux_dir.mkdir(parents=True, exist_ok=True)

        # 3. Iterar sobre el esquema y generar gráficos
        generated_charts = {}
        charts_generated = 0

        for chart_def in schema:
            chart_type = chart_def.get("type")
            input_key = chart_def.get("input_key")
            output_filename = chart_def.get("output_filename")
            params = chart_def.get("params", {})

            # Validar definición mínima
            if not chart_type or not input_key or not output_filename:
                self._log(f"[{self.name}] Error: Definición incompleta: {chart_def}")
                continue

            # Obtener la función desde plot_tools
            func = getattr(plot_tools, chart_type, None)
            if not func:
                self._log(f"[{self.name}] Error: La función '{chart_type}' no existe en plot_tools.")
                continue

            # Obtener el DataFrame desde artifacts
            df = ctx.artifacts.get(input_key)
            if df is None:
                self._log(f"[{self.name}] Error: El artifact '{input_key}' no existe en el contexto.")
                continue

            # Preparar argumentos
            output_path = aux_dir / output_filename
            kwargs = params.copy()
            kwargs["nombre_grafico"] = str(output_path)

            try:
                func(df, **kwargs)
                generated_charts[output_filename] = output_path
                charts_generated += 1
            except Exception as e:
                self._log(f"[{self.name}] Error al generar gráfico '{output_filename}': {e}")

        # 4. Registrar rutas generadas en el contexto
        ctx.artifacts["generated_charts"] = generated_charts
        self._log(f"[{self.name}] {charts_generated}/{len(schema)} gráficos generados en {aux_dir}")

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)


class GenerateTables(Step):
    """
    Genera tablas utilizando funciones de report_tools.

    Lee el esquema de tablas desde ctx.params["tables_schema"] (cargado por un step
    previo) o directamente desde el constructor.

    Cada entrada del esquema tiene:
        - type: nombre de la función en report_tools (ej: "resumen_estadistico_basico")
        - input_key: clave del DataFrame en ctx.artifacts
        - output_filename: nombre del archivo de salida (ej: "resumen.xlsx")
          Usa {val} como placeholder cuando se usa iterate_by.
        - params: kwargs adicionales para la función
        - iterate_by (opcional): columna para generar una tabla por cada valor único.
          Inyecta el valor en params["parametros"][columna] y como kwarg raíz.

    Efectos:
        - Crea archivos .xlsx en ctx.aux_dir.
        - Registra rutas generadas en ctx.artifacts["generated_tables"].
    """
    def __init__(self, tables_schema: Optional[List[Dict]] = None):
        """Inicializa el step, opcionalmente con esquema directo."""
        super().__init__(name="GenerateTables")
        self.tables_schema = tables_schema

    def run(self, ctx):
        """Genera las tablas solicitadas y registra las rutas en ctx.artifacts."""
        before = self._snapshot_artifacts(ctx)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__

        # 1. Resolver esquema: constructor directo o ctx.params
        schema = self.tables_schema
        if not schema:
            schema = ctx.params.get("tables_schema", [])

        if not schema:
            self._log(f"[{self.name}] Advertencia: No se encontraron definiciones de tablas.")
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 2. Resolver directorio auxiliar
        aux_dir = getattr(ctx, "aux_dir", None)
        if not aux_dir:
            if hasattr(ctx, "base_dir"):
                aux_dir = ctx.base_dir / "aux_files"
            else:
                aux_dir = Path("aux_files")
            ctx.aux_dir = aux_dir

        if not aux_dir.exists():
            aux_dir.mkdir(parents=True, exist_ok=True)

        # 3. Iterar sobre el esquema y generar tablas
        generated_tables = {}
        tables_generated = 0

        for table_def in schema:
            func_name = table_def.get("type")
            input_key = table_def.get("input_key")
            output_filename = table_def.get("output_filename")
            params = table_def.get("params", {})
            iterate_by = table_def.get("iterate_by", None)

            # Validar definición mínima
            if not func_name or not input_key or not output_filename:
                self._log(f"[{self.name}] Error: Definición incompleta: {table_def}")
                continue

            func = getattr(report_tools, func_name, None)
            if not func:
                self._log(f"[{self.name}] Error: La función '{func_name}' no existe en report_tools.")
                continue

            df_full = ctx.artifacts.get(input_key)
            if df_full is None:
                self._log(f"[{self.name}] Error: El artifact '{input_key}' no existe en el contexto.")
                continue

            # Helper: ejecuta la función y guarda el resultado como Excel
            def process_and_save(df_k, filename_k, params_k, _func=func):
                try:
                    df_res = _func(df_k, **params_k)
                    output_path = aux_dir / filename_k
                    df_res.to_excel(output_path, index=False)
                    generated_tables[filename_k] = output_path
                    return True
                except Exception as e:
                    self._log(f"[{self.name}] Error generando tabla '{filename_k}': {e}")
                    return False

            if iterate_by:
                # Caso iterativo (ej: generar tabla por cada Curso)
                if iterate_by not in df_full.columns:
                    self._log(f"[{self.name}] Error: Columna '{iterate_by}' no existe en DataFrame.")
                    continue

                for val in sorted(df_full[iterate_by].unique(), key=str):
                    if "{val}" in output_filename:
                        fname = output_filename.replace("{val}", str(val))
                    else:
                        base, ext = os.path.splitext(output_filename)
                        fname = f"{base}_{val}{ext}"

                    iter_params = params.copy()
                    # Inyectar valor en parametros dict (para funciones que filtran con parametros)
                    if "parametros" not in iter_params:
                        iter_params["parametros"] = {}
                    if isinstance(iter_params.get("parametros"), dict):
                        iter_params["parametros"][iterate_by] = val
                    # También como kwarg raíz (para funciones como resumen_estadistico_basico)
                    iter_params[iterate_by] = val

                    if process_and_save(df_full, fname, iter_params):
                        tables_generated += 1
            else:
                if process_and_save(df_full, output_filename, params):
                    tables_generated += 1

        # 4. Registrar rutas generadas en el contexto
        ctx.artifacts["generated_tables"] = generated_tables
        self._log(f"[{self.name}] {tables_generated}/{len(schema)} tablas generadas en {aux_dir}")

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)


class RequestUserFiles(Step):
    """
    Step que declara archivos requeridos que deben ser cargados por el usuario.
    En una ejecución interactiva, el frontend utiliza esta definición para mostrar los inputs.
    
    Parámetros:
        file_specs (List[Dict]): Lista de especificaciones {id, label, description, multiple}.
    """
    def __init__(self, file_specs: List[Dict]):
        super().__init__(name="RequestUserFiles")
        self.file_specs = file_specs

    def run(self, ctx):
        """
        En una ejecución automatizada, verifica que los archivos existan en ctx.inputs.
        En una ejecución interactiva, este paso toma los archivos cargados previamente 
        por el usuario y los incorpora al flujo.
        """
        before = self._snapshot_artifacts(ctx)
        
        if not ctx.pipeline_id:
            self._log("No se encontró pipeline_id en el contexto para RequestUserFiles.")
            return

        # Ruta centralizada de uploads (definida en config.py)
        uploads_root = UPLOADS_DIR / str(ctx.pipeline_id)

        if not uploads_root.exists():
            self._log(f"No se encontró directorio de subidas en {uploads_root}")
            # Si hay specs no-opcionales, pedir los archivos al usuario
            for spec in self.file_specs:
                if not spec.get("optional", False):
                    self._log(f"Solicitando input usuario para '{spec.get('id')}'")
                    raise WaitingForInputException(self.name, {"input_key": spec.get("id"), "spec": spec})
            return

        for spec in self.file_specs:
            input_key = spec.get("id")
            source_dir = uploads_root / input_key
            
            if source_dir.exists():
                # Directorio de destino dentro de la corrida
                target_dir = ctx.inputs_dir / input_key
                target_dir.mkdir(parents=True, exist_ok=True)
                
                discovered_files = []
                for file_path in source_dir.glob("*"):
                    if file_path.is_file():
                        # Mover o copiar a la carpeta de inputs de la corrida
                        dest_path = target_dir / file_path.name
                        shutil.copy2(file_path, dest_path)
                        discovered_files.append(dest_path)
                
                if discovered_files:
                    ctx.inputs[input_key] = discovered_files
                    self._log(f"Registrados {len(discovered_files)} archivos para '{input_key}'")
            else:
                if not spec.get("optional", False):
                    self._log(f"Solicitando input usuario para '{input_key}'")
                    raise WaitingForInputException(self.name, {"input_key": input_key, "spec": spec})

        # Limpiar uploads temporales después de copiar exitosamente
        if uploads_root.exists():
            shutil.rmtree(uploads_root)
            self._log(f"Limpiado directorio de uploads temporales: {uploads_root}")

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)

class RenderReport(Step):
    """
    Genera el informe PDF final utilizando LaTeX.

    Requiere:
        - Archivos generados en ctx.aux_dir (tablas excel, imágenes).
        - params["report_schema"]: Diccionario con la estructura del informe.
          Puede ser cargado previamente o pasado directamente.
    
    Efectos:
        - Genera 'variables.tex', 'contenido.tex' e 'informe.tex' en ctx.aux_dir.
        - Compila con xelatex.
        - Resultado final: 'informe.pdf' en ctx.outputs_dir.
    """
    def __init__(self, report_schema: Optional[Dict] = None):
        super().__init__(name="RenderReport")
        self.report_schema = report_schema

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__

        # 1. Obtener schema
        schema = self.report_schema or ctx.params.get("report_schema")
        if not schema:
             # Intento de cargar desde archivo si viene una ruta en params
             schema_path = ctx.params.get("report_schema_path")
             if schema_path:
                 try:
                     import json
                     with open(schema_path, "r", encoding="utf-8") as f:
                        schema = json.load(f)
                 except Exception as e:
                     self._log(f"Error cargando json de reporte desde {schema_path}: {e}")

        if not schema:
            self._log(f"[{self.name}] Error: No se encontró report_schema.")
            # No fallamos, solo retornamos
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 2. Rutas
        aux_dir = getattr(ctx, "aux_dir", None)
        if not aux_dir or not aux_dir.exists():
             # Fallback
             if hasattr(ctx, "base_dir"):
                 aux_dir = ctx.base_dir / "aux_files"
             else:
                 aux_dir = Path("aux_files")
        
        if not aux_dir.exists():
            self._log(f"[{self.name}] Error: aux_dir no existe ({aux_dir}).")
            return

        # Debemos movernos al directorio auxiliar para que latex encuentre las imagenes/tablas
        # Guardamos CWD original
        cwd_original = os.getcwd()
        os.chdir(aux_dir)

        try:
            # 3. Generar variables.tex
            new_command_format = "\\newcommand{{\\{}}}{{{}}}\n"
            with open("variables.tex", "w", encoding="utf-8") as f:
                f.write("% Variables del informe\n")
                variables = schema.get("variables_documento", {})
                
                # Inyectar variables desde el contexto si hacen falta
                if "evaluacion" not in variables and hasattr(ctx, "evaluation"):
                    variables["evaluacion"] = ctx.evaluation
                # Inyectar params como variables si se desea
                # for k,v in ctx.params.items(): ... (opcional)

                for key, value in variables.items():
                    # Sanitize key/value if needed
                    val_str = str(value).replace("_", "\\_") # Escape básico
                    f.write(new_command_format.format(key, val_str))
                f.write("\n")

            # 4. Generar contenido dinámico (secciones)
            # Combinamos fijas y dinámicas en orden
            secciones_fijas = schema.get("secciones_fijas", [])
            secciones_dinamicas = schema.get("secciones_dinamicas", [])
            
            # Nota: El script original las escribe secuencialmente. 
            # Aquí las unimos para procesar en un solo loop y asignar indices.
            todas_secciones = secciones_fijas + secciones_dinamicas
            
            # Lista de índices alfabéticos que usaremos en el informe.tex
            # Debemos importar indice_alfabetico (ya importado arriba)
            i_idx = 0
            lista_indices_tex = []
            
            with open("contenido.tex", "w", encoding="utf-8") as f:
                f.write("% Contenido generado\n")
                
                for seccion in todas_secciones:
                    if i_idx >= len(indice_alfabetico):
                        break 
                    
                    current_idx = indice_alfabetico[i_idx]
                    lista_indices_tex.append(current_idx)
                    
                    titulo = seccion.get("titulo", "")
                    
                    # Definimos el comando sectionX
                    cmd_section = f"\\section*{{{titulo}}}"
                    if seccion.get("newpage", False):
                        cmd_section = "\\newpage " + cmd_section
                    
                    f.write(new_command_format.format("section" + current_idx, cmd_section))

                    # Contenido (Tabla o Imagen)
                    tipo = seccion.get("tipo")
                    contenido_path = seccion.get("contenido") # Ruta relativa a aux_dir o absoluta
                    
                    latex_content = ""
                    if tipo == "tabla":
                         # Leer excel, generar latex
                         try:
                             p = Path(contenido_path)
                             if not p.is_absolute():
                                 p = aux_dir / contenido_path
                             
                             if p.exists():
                                 df_t = pd.read_excel(p)
                                 # Usamos la funcion de report_tools
                                 latex_content = report_tools.df_a_latex_loop(df_t)
                             else:
                                 # Intentar buscar file tal cual (por si generamos en run time)
                                 if Path(contenido_path).exists():
                                      df_t = pd.read_excel(contenido_path)
                                      latex_content = report_tools.df_a_latex_loop(df_t)
                                 else:
                                      latex_content = f"Error: Archivo {contenido_path} no encontrado."
                         except Exception as e:
                             latex_content = f"Error procesando tabla {contenido_path}: {e}"

                    elif tipo == "imagen":
                         opts = seccion.get("options", "")
                         # Para latex, mejor usar nombre de archivo relativo si está en el mismo dir
                         p = Path(contenido_path)
                         img_name = p.name
                         # Asegurarse que la imagen esté ahí. Si está en otro lado, copiarla?
                         # El script original copiaba imagenes estaticas a tmp/img. 
                         # Asumimos que GenerateGraphics ya dejó las imagenes en aux_dir.
                         latex_content = report_tools.img_to_latex(img_name, opts)
                    
                    f.write(new_command_format.format("content" + current_idx, latex_content))
                    i_idx += 1


            # 5. Generar informe.tex principal
            with open("informe.tex", "w", encoding="utf-8") as f:
                f.write(formato_informe_generico)
                f.write("\n")
                f.write("\\input{contenido.tex}\n") 
                for idx in lista_indices_tex:
                     f.write(f"\\section{idx}\n")
                     f.write(f"\\content{idx}\n")
                     f.write("\n")
                f.write("\\end{document}")
            
            # 6. Compilar
            self._log(f"[{self.name}] Compilando PDF...")
            # Detectar si estamos en windows para el comando
            cmd = "xelatex -interaction=nonstopmode informe.tex"
            ret = os.system(cmd)
            
            if ret == 0:
                self._log(f"[{self.name}] PDF generado exitosamente.")
                # Mover a outputs si existe output_dir
                if hasattr(ctx, "outputs_dir") and ctx.outputs_dir.exists():
                     target = ctx.outputs_dir / "informe.pdf"
                elif hasattr(ctx, "outputs"):
                     # Si outputs es dict pero no hay outputs_dir definido como path
                     # Usamos base_dir o lo dejamos en aux_dir
                     target = ctx.base_dir / "informe.pdf"
                else:
                     target = Path("informe.pdf").resolve() # en aux_dir
                
                src = aux_dir / "informe.pdf"
                if src.exists():
                    if src != target:
                        shutil.copy(src, target)
                    ctx.outputs["report_pdf"] = target
            else:
                self._log(f"[{self.name}] Advertencia: xelatex retornó código {ret}. Revisar logs en {aux_dir}.")
        
        except Exception as e:
            self._log(f"[{self.name}] Excepción durante RenderReport: {e}")
        finally:
            # Volver al directorio original
            os.chdir(cwd_original)

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)



class GenerateDocxReport(Step):
    """
    Genera un informe DOCX (y opcionalmente PDF) usando una plantilla Word y docxtpl.
    
    Parametros:
        template_name (str): Nombre del archivo plantilla en backend/templates (o ruta absoluta).
        output_filename (str): Nombre del archivo de salida (ej: informe_final.docx).
        context_key (opcional): Clave en artifacts/params que contiene el diccionario de contexto.
                                Si no se da, se construye un contexto mezclando params y artifacts.
        convert_to_pdf (bool): Si True, intenta convertir a PDF usando docx2pdf.
        
    Efectos:
        - Crea archivo .docx en ctx.aux_dir.
        - Si convert_to_pdf=True, crea .pdf en ctx.outputs_dir.
    """
    def __init__(self, template_name: str, output_filename: str, context_key: str = None, convert_to_pdf: bool = True):
        super().__init__(name="GenerateDocxReport")
        self.template_name = template_name
        self.output_filename = output_filename
        self.context_key = context_key
        self.convert_to_pdf = convert_to_pdf

    def run(self, ctx):
        """Renderiza reporte Word/PDF usando un .docx como plantilla."""
        before = self._snapshot_artifacts(ctx)
        
        # 1. Resolver ruta de plantilla docx
        p = Path(self.template_name)
        if p.exists():
            template_path = p
        else:
            # 2. Buscar en carpeta centralizada (REPORTS_TEMPLATES_DIR)
            template_path = REPORTS_TEMPLATES_DIR / self.template_name
            if not template_path.exists():
                 # 3. Fallback: carpeta 'templates' del contexto
                if hasattr(ctx, "base_dir"):
                     template_path = ctx.base_dir / "templates" / self.template_name

        if not template_path.exists():
            self._log(f"[{self.name}] Error: Plantilla DOCX no encontrada: {self.template_name}")
            return
            return

        # 2. Construir Contexto
        if self.context_key:
            data_context = ctx.artifacts.get(self.context_key) or ctx.params.get(self.context_key, {})
        else:
            # Merge params and artifacts
            data_context = ctx.params.copy()

        # Asegurar aux_dir
        aux_dir = getattr(ctx, "aux_dir", None)
        if not aux_dir:
             if hasattr(ctx, "base_dir"):
                 aux_dir = ctx.base_dir / "aux_files"
             else:
                 aux_dir = Path("aux_files")
        
        if not aux_dir.exists():
            aux_dir.mkdir(parents=True, exist_ok=True)
             
        output_path = aux_dir / self.output_filename
        
        # 3. Renderizar
        try:
            self._log(f"[{self.name}] Renderizando plantilla {template_path}...")
            result_path = render_docx_report(template_path, data_context, output_path, auto_convert_pdf=self.convert_to_pdf)
            self._log(f"[{self.name}] Generado: {result_path}")
            
            # Registrar output
            if str(result_path).endswith(".pdf"):
                ctx.outputs["report_docx_pdf"] = result_path
            else:
                ctx.outputs["report_docx"] = result_path
                
        except Exception as e:
            self._log(f"[{self.name}] Error generando reporte Docx: {e}")

        ctx.last_step = self.name
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
