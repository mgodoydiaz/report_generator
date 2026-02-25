"""Steps de entrada/salida de archivos: descubrir, solicitar, exportar y limpiar."""

# Librerias estandar
from pathlib import Path
import os
import shutil
from typing import Optional, List, Dict

# Importaciones internas de RGenerator
from .step import Step, WaitingForInputException
from config import UPLOADS_DIR


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
            output_filename: str = "",
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
