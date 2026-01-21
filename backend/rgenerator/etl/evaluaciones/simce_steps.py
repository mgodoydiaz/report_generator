"""Archivo contiene la definición de los steps de SIMCE."""

# Librerias estandar
from datetime import datetime
from pathlib import Path
import pandas as pd

# Importaciones internas de RGenerator
from ..core.step import Step
from rgenerator.tooling.config_tools import cargar_config_desde_txt, parsear_lista_desde_config

class InitRun(Step):
    """
    Step inicial para configurar el contexto de la corrida.
    """
    def __init__(
            self,
            evaluation: str,
            base_dir: Path,
            year: int,
            asignatura: str,
            numero_prueba: int,
    ):
        super().__init__(name="InitRun")
        self.evaluation = evaluation
        self.base_dir = base_dir
        self.year = year
        self.asignatura = asignatura
        self.numero_prueba = numero_prueba
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def run(self, context):

        # Identidad del run o task
        context.evaluation = self.evaluation
        context.run_id = self.timestamp


        # ATENCION A CAMBIO
        # Agregar un id unico a la corrida, run o task, gestionar algun tipo de software como sidekiq, celery, airflow, etc.
        # context.run_id = # get_unique_id_somehow()

        # parametros base
        context.params = {
            "year": self.year,
            "asignatura": self.asignatura,
            "numero_prueba": self.numero_prueba,
        }

        # carpetas estandar
        ########################################
        # ATENCION A CAMBIO
        # ESTO DEBERIA CAMBIAR POR ALGUNA BASE DE DATOS

        context.base_dir = self.base_dir
        context.work_dir = self.base_dir / context.evaluation / context.run_id
        context.inputs_dir = context.base_dir / "inputs"
        context.aux_dir = context.work_dir / "aux_files"
        context.outputs_dir = context.work_dir / "outputs"

        for d in [context.work_dir, context.inputs_dir, context.aux_dir, context.outputs_dir]:
            d.mkdir(parents=True, exist_ok=True)

        context.status = "RUNNING"


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
        if not self.config_path.exists():
            raise FileNotFoundError(f"No se encontró config: {self.config_path}")

        config = cargar_config_desde_txt(str(self.config_path))

        # Normaliza defaults
        tipo_etl = config.get("tipo_etl", "estudiantes").strip().lower()
        nombre_salida = config.get("nombre_salida", "salida_etl.xlsx").strip()

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
