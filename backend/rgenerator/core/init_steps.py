"""Steps de inicialización y carga de configuración del pipeline."""

# Librerias estandar
from datetime import datetime
import pandas as pd

# Importaciones internas de RGenerator
from .step import Step
from config import PIPELINE_RUNS_DIR, SPECS_DB_PATH
from rgenerator.tooling.data_tools import safe_text_to_json


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


# DEPRECADO: LoadConfig ha sido reemplazado por LoadConfigFromSpec.
# Se comenta para conservar historial. No usar en nuevos pipelines.
#
# class LoadConfig(Step):
#     """
#     Carga configuracion desde JSON y normaliza parametros en el contexto.
#     DEPRECADO: usar LoadConfigFromSpec (carga desde la BD de specs).
#     """
#     def __init__(self, config_path: Path | str):
#         super().__init__(name="LoadConfig")
#         self.config_path = Path(config_path)
#
#     def run(self, ctx):
#         before = self._snapshot_artifacts(ctx)
#         if not self.config_path.exists():
#             raise FileNotFoundError(f"No se encontró config: {self.config_path}")
#         config = cargar_config_desde_json(str(self.config_path))
#         output_filename = str(config.get("output_filename")).strip()
#         if not hasattr(ctx, "params") or ctx.params is None:
#             ctx.params = {}
#         ctx.params["config_path"] = str(self.config_path)
#         ctx.params["output_filename"] = output_filename
#         for k, v in config.items():
#             if k not in ctx.params:
#                 ctx.params[k] = v
#         if hasattr(ctx, "outputs_dir"):
#             ctx.outputs["consolidated_excel"] = ctx.outputs_dir / output_filename
#         ctx.last_step = self.name
#         self._log_artifacts_delta(ctx, before)


class LoadConfigFromSpec(Step):
    """
    Carga configuración desde la base de datos de specs (templates.xlsx).

    Lee la columna 'config_json' del spec indicado y carga todas las
    secciones al contexto del pipeline. Es genérico: funciona con specs
    de tipo ETL, Reporte, Dashboard, etc.

    Parámetros:
        spec_id (int): ID del spec/template en templates.xlsx.
        config_key (str, opcional): Si se especifica, los etlParams se guardan
            bajo ctx.params["_config"][config_key] en lugar de aplanarse
            directamente en ctx.params. Útil cuando el pipeline procesa
            múltiples tipos de archivo con configuraciones distintas.
            RunExcelETL buscará primero en ctx.params["_config"][input_key]
            antes de caer al ctx.params global.

    Efectos en ctx.params (sin config_key):
        - etlParams → se transforman a formato plano (header_row, select_columns, etc.)
        - variables_documento → ctx.params["variables_documento"]
        - secciones_fijas → ctx.params["secciones_fijas"]
        - secciones_dinamicas → ctx.params["secciones_dinamicas"]
        - Cualquier otra sección presente se copia tal cual.

    Efectos en ctx.params (con config_key):
        - etlParams → ctx.params["_config"][config_key]
        - El resto de secciones se copia igual al global.

    Ejemplo sin config_key (comportamiento anterior):
        LoadConfigFromSpec(spec_id=1)

    Ejemplo con config_key (config aislada por artifact):
        LoadConfigFromSpec(spec_id=3, config_key="habilidades")
    """
    def __init__(self, spec_id: int, config_key: str = None):
        super().__init__(name="LoadConfigFromSpec")
        self.spec_id = spec_id
        self.config_key = config_key

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
            if self.config_key:
                # Guardar config aislada por artifact, sin tocar el ctx.params global
                if "_config" not in ctx.params:
                    ctx.params["_config"] = {}
                ctx.params["_config"][self.config_key] = flat_params
                loaded_keys.append(f"etlParams({len(flat_params)}) -> _config[{self.config_key}]")
            else:
                # Comportamiento original: aplanar directo en ctx.params
                for k, v in flat_params.items():
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
