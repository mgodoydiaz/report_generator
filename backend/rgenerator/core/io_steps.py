"""Steps de entrada/salida de archivos.

Tras la limpieza B6b post-v0.2.0 quedó solo `RequestUserFiles` (carga
interactiva por API). Steps removidos:

- `DiscoverInputs`: redundante con `RequestUserFiles`. Era del modelo
  CLI por carpetas. Ningún pipeline lo usaba.
- `ExportConsolidatedExcel`: legacy del modelo CLI. La salida productiva
  hoy va a la DB vía `SaveToMetric`. En Render Free además se perdía
  por falta de Persistent Disk.
- `DeleteTempFiles`: legacy del modelo CLI. La limpieza de uploads
  ahora es lazy en el container o por cron.
"""

# Librerias estandar
import shutil
from typing import List, Dict

# Importaciones internas de RGenerator
from .step import Step, WaitingForInputException
from backend.config import UPLOADS_DIR


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
