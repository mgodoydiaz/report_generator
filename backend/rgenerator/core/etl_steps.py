"""Steps de transformación y enriquecimiento de datos (ETL)."""

# Librerias estandar
import os
import re
import pandas as pd
from typing import Callable, Optional, Dict, List

# Importaciones internas de RGenerator
from .step import Step, WaitingForInputException
from .derived_fields_engine import apply_derived_fields


# ─────────────────────────────────────────────────────────────────────────
# Helpers para metadata_cells (lectura de celdas individuales pre-header)
# ─────────────────────────────────────────────────────────────────────────

_A1_RE = re.compile(r"^([A-Z]+)(\d+)$")


def _parse_a1(cell_ref: str) -> tuple[int, int]:
    """Convierte una referencia A1 ('B5') a (row_idx, col_idx) 0-indexed.

    'A1' → (0, 0); 'B5' → (4, 1); 'AA10' → (9, 26).
    """
    m = _A1_RE.match(cell_ref.strip().upper())
    if not m:
        raise ValueError(f"Referencia A1 inválida: '{cell_ref}'")
    col_letters, row_str = m.group(1), m.group(2)
    col = 0
    for ch in col_letters:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return int(row_str) - 1, col - 1


def _read_metadata_cells(filepath: str, cells: List[Dict]) -> Dict[str, object]:
    """Lee celdas individuales del XLS/XLSX antes del header de datos.

    `cells` es una lista de {"column_name": ..., "cell": "B5"}. Devuelve
    un dict {column_name: valor_de_la_celda}. Pensado para casos como
    DIA donde las primeras filas traen metadata (Establecimiento en B5,
    Curso en B6) y los datos arrancan desde una fila más abajo.
    """
    if not cells:
        return {}
    parsed = [(c["column_name"], _parse_a1(c["cell"])) for c in cells]
    max_row = max(row for _, (row, _) in parsed)
    raw = pd.read_excel(filepath, header=None, nrows=max_row + 1)
    result: Dict[str, object] = {}
    for col_name, (row_idx, col_idx) in parsed:
        try:
            result[col_name] = raw.iat[row_idx, col_idx]
        except (IndexError, KeyError):
            result[col_name] = None
    return result


class RunExcelETL(Step):
    """
    Consolida archivos Excel y guarda el resultado en artifacts.

    Parametros:
        input_key (opcional): clave en ctx.inputs con archivos a procesar.
            Si no se entrega, se intenta resolver desde el contexto.
        output_key (opcional): clave en ctx.artifacts para el DataFrame.
            Si no se entrega, se genera como "df_consolidado_{input_key}".

    Parámetros vía ctx.params (o spec config):
        header_row: int o dict {nombre_archivo: int, "default": int}
            para distintas filas de header por archivo.
        select_columns: lista de columnas a mantener.
        rename_columns: dict {col_original: col_final}.
        enrich_data: lista de {key, val, user_input?}.
        metadata_cells: lista de {column_name, cell} para inyectar valores
            de celdas individuales pre-header como columnas. Pensado para
            DIA donde Establecimiento vive en B5 y Curso en B6.
            Ej: [{"column_name": "Curso", "cell": "B6"}].

    Efectos:
        - ctx.artifacts[output_key] con DataFrame consolidado (o vacio).
        - ctx.last_artifact_key actualizado con output_key.

    Ejemplo:
        RunExcelETL(input_key="estudiantes", output_key="df_estudiantes_raw")
    """
    def __init__(
        self,
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        header_row=None,
        select_columns=None,
        rename_columns=None,
        enrich_data=None,
        metadata_cells=None,
    ):
        """Configura claves de entrada/salida y los parámetros ETL inline.

        Los parámetros ETL (`header_row`, `select_columns`, `rename_columns`,
        `enrich_data`, `metadata_cells`) pueden venir tanto desde un Spec via
        `LoadConfigFromSpec` (en `ctx.params["_config"][input_key]`) como
        directamente en la config del step en el pipeline (kwargs aquí).
        Los kwargs tienen precedencia sobre el Spec/ctx.params si se entregan.
        """
        resolved_output_key = output_key
        if input_key and not resolved_output_key:
            resolved_output_key = f"df_consolidado_{input_key}"
        super().__init__(
            name=f"RunExcelETL_{input_key}" if input_key else "RunExcelETL",
            requires=[input_key] if input_key else [],
            produces=[resolved_output_key] if resolved_output_key else []
        )
        self.input_key = input_key
        self.output_key = resolved_output_key
        # Config inline: solo guardamos los que el usuario entregó (no None)
        # para que `run()` pueda fallback al Spec/ctx.params cuando falten.
        self._inline_config = {
            k: v for k, v in {
                "header_row": header_row,
                "select_columns": select_columns,
                "rename_columns": rename_columns,
                "enrich_data": enrich_data,
                "metadata_cells": metadata_cells,
            }.items() if v is not None
        }

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

        # Buscar config aislada por input_key (cargada con config_key en LoadConfigFromSpec)
        # Si no existe, caer al ctx.params global como fallback.
        # Precedencia: inline kwargs (constructor) > spec/ctx.params._config > ctx.params global.
        _artifact_config = ctx.params.get("_config", {}).get(input_key, {})

        def _resolve(key, default):
            if key in self._inline_config:
                return self._inline_config[key]
            return _artifact_config.get(key, ctx.params.get(key, default))

        # Obtenemos la config de headers (puede venir del json cargado en LoadConfig)
        # Default global es 0 si no se especifica nada
        raw_header_config = _resolve("header_row", 0)

        # Se obtienen los nombres de las columnas a mantener o seleccionar
        select_columns = _resolve("select_columns", [])
        # Obtenemos el mapeo de columnas (renames)
        column_mapping = _resolve("rename_columns", {})
        # Celdas individuales pre-header a inyectar como columnas (caso DIA)
        metadata_cells = _resolve("metadata_cells", [])

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

                # 3.5: Enriquecimiento POR ARCHIVO (datos recopilados por EnrichWithUserInput mode="per_file")
                user_inputs_store = getattr(ctx, "user_inputs", {}).get("enrich_per_file", {})
                file_user_data = user_inputs_store.get(nombre_archivo, {})
                for col, val in file_user_data.items():
                    temp_df[col] = val

                # 3.5.b: Enriquecimiento GLOBAL (datos recopilados por EnrichWithUserInput mode="once")
                global_user_data = getattr(ctx, "user_inputs", {}).get("enrich_global", {})
                for col, val in global_user_data.items():
                    if col not in temp_df.columns:  # no pisa per_file si ya cargó
                        temp_df[col] = val

                # 3.6: Inyectar metadata leída de celdas individuales pre-header
                # (caso DIA: Establecimiento en B5, Curso en B6, datos desde fila 13).
                if metadata_cells:
                    try:
                        meta_values = _read_metadata_cells(ruta_archivo, metadata_cells)
                        for col, val in meta_values.items():
                            temp_df[col] = val
                    except Exception as e:
                        self._log(
                            f"[{self.name}] Error leyendo metadata_cells de {nombre_archivo}: {e}"
                        )

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

    Detecta campos de `enrich_data` marcados con `user_input=True` y pausa
    el pipeline para pedirlos. Soporta dos modos:

      - mode="per_file"  → pide UN valor por (archivo, campo). Útil si los
        archivos pueden tener distinto Hito/Asignatura. Requiere archivos
        ya cargados al ejecutar.
      - mode="once"      → pide UN solo valor por campo, válido para todos
        los archivos del run. Útil para SIMCE (Año/Asignatura/Mes/N Prueba
        son globales). NO requiere archivos cargados — puede ir antes de
        cualquier RequestUserFiles.

    Los valores capturados se guardan en:
      - ctx.user_inputs["enrich_per_file"][filename][key] = val   (mode per_file)
      - ctx.user_inputs["enrich_global"][key] = val                (mode once)

    `RunExcelETL` y `RunDIAPDFExtraction` leen ambos almacenes y aplican las
    columnas resultantes a sus DataFrames.

    Parámetros:
        input_key: clave única en ctx.inputs cuyos archivos se procesan.
        input_keys: lista de claves en ctx.inputs. Junta todos sus archivos
            en una sola pausa.
        apply_to_all: si True (y no se da input_key/input_keys), aplica a
            todos los archivos disponibles en ctx.inputs.
        enrich_data: lista de campos {key, val, user_input}. Si se entrega
            inline, tiene precedencia sobre el Spec/ctx.params.
        mode: "per_file" (default) o "once".
    """
    def __init__(
        self,
        input_key: Optional[str] = None,
        input_keys: Optional[List[str]] = None,
        apply_to_all: bool = False,
        enrich_data: Optional[List[Dict]] = None,
        mode: str = "per_file",
    ):
        if mode not in ("per_file", "once"):
            raise ValueError(f"mode inválido: {mode!r}. Use 'per_file' o 'once'.")
        super().__init__(
            name="EnrichWithUserInput",
            description=(
                "Pide datos de enriquecimiento al usuario "
                + ("(una sola vez para todo el run)" if mode == "once" else "(uno por archivo)")
            )
        )
        self.input_key = input_key
        self.input_keys = input_keys
        self.apply_to_all = apply_to_all
        self._inline_enrich_data = enrich_data
        self.mode = mode

    def _resolve_input_keys(self, ctx) -> List[str]:
        """Devuelve la lista de input_keys a procesar según los modos disponibles."""
        if self.input_keys:
            return list(self.input_keys)
        if self.input_key:
            return [self.input_key]
        if self.apply_to_all:
            return list(getattr(ctx, "inputs", {}).keys())
        # Fallback: si solo hay 1 input_key cargado, usalo
        if hasattr(ctx, "inputs") and len(ctx.inputs) == 1:
            return [next(iter(ctx.inputs.keys()))]
        return []

    def _resolve_enrich_data(self, ctx, keys: List[str]) -> list:
        """Resuelve enrich_data: inline > spec del primer input_key > ctx.params global."""
        if self._inline_enrich_data is not None:
            return self._inline_enrich_data
        cfgs = ctx.params.get("_config", {})
        for k in keys:
            if k in cfgs and "enrich_data" in cfgs[k]:
                return cfgs[k]["enrich_data"]
        return ctx.params.get("enrich_data", [])

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)

        # En mode="once" no necesitamos archivos — puede ir antes de RequestUserFiles.
        if self.mode == "once":
            keys: List[str] = []  # no se usan
        else:
            keys = self._resolve_input_keys(ctx)
            if not keys:
                raise ValueError(
                    f"[{self.name}] No se pudo resolver input_key/input_keys. "
                    f"Pasá `input_key`, `input_keys=[...]` o `apply_to_all=True`."
                )

        enrich_data = self._resolve_enrich_data(ctx, keys)
        if isinstance(enrich_data, list):
            user_input_fields = [p for p in enrich_data if isinstance(p, dict) and p.get("user_input")]
        else:
            user_input_fields = []

        if not user_input_fields:
            self._log(f"[{self.name}] No hay campos que requieran input del usuario. Saltando.")
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # ── MODE: ONCE ────────────────────────────────────────────────
        if self.mode == "once":
            global_store = getattr(ctx, "user_inputs", {}).get("enrich_global", {})
            missing = [f for f in user_input_fields if not global_store.get(f.get("key"))]

            if missing:
                input_details = {
                    "type": "enrich_once",
                    "fields": [
                        {
                            "key": f.get("key"),
                            "label": f.get("label") or f.get("key"),
                            "default": f.get("val"),
                            "options": f.get("options"),
                        }
                        for f in user_input_fields
                    ],
                }
                raise WaitingForInputException(self.name, input_details)

            self._log(f"[{self.name}] Globals recibidos: {list(global_store.keys())}. Continuando.")
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # ── MODE: PER FILE ────────────────────────────────────────────
        archivos: List[str] = []
        for k in keys:
            archivos.extend(getattr(ctx, "inputs", {}).get(k, []))
        file_names = [os.path.basename(f) for f in archivos]

        if not file_names:
            self._log(f"[{self.name}] No hay archivos para procesar. Saltando.")
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

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
            input_details = {
                "type": "enrich_per_file",
                "files": file_names,
                "fields": [
                    {"key": f.get("key"), "label": f.get("val") or f.get("key")}
                    for f in user_input_fields
                ]
            }
            raise WaitingForInputException(self.name, input_details)

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
            # Buscar primero en config aislada por input_key, luego caer al global
            _artifact_config = ctx.params.get("_config", {}).get(input_key, {})
            raw_enrich = _artifact_config.get("enrich_data", ctx.params.get("enrich_data", {}))
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
                df = self.cleaning_func(df)
            except Exception as e:
                raise ValueError(f"Error ejecutando función de limpieza en {self.name}: {e}")

        # 5. Guardar salida
        ctx.artifacts[output_key] = df
        ctx.last_artifact_key = output_key
        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)


class EnrichWithLookup(Step):
    """
    Enriquece un DataFrame haciendo un lookup (join) contra otro artifact del contexto.

    Parametros:
        input_key (str): Clave del artifact principal en ctx.artifacts.
        lookup_key (str): Clave del artifact de lookup en ctx.artifacts.
        on (str): Columna llave compartida por ambos DataFrames.
            Usar cuando la columna tiene el mismo nombre en ambos lados.
            Mutuamente excluyente con left_on/right_on.
        left_on (str): Columna llave en el DataFrame principal.
            Usar junto con right_on cuando la llave tiene distinto nombre en cada lado.
        right_on (str): Columna llave en el DataFrame de lookup.
            Usar junto con left_on cuando la llave tiene distinto nombre en cada lado.
        columns (list): Columnas del lookup a incorporar al DataFrame principal.
            Debe incluir la columna llave si se usa right_on.
        output_key (str): Clave del artifact de salida en ctx.artifacts.
        how (str): Tipo de join. Default: "inner".

    Efectos:
        - ctx.artifacts[output_key] con DataFrame enriquecido.
        - ctx.last_artifact_key actualizado con output_key.

    Ejemplo con on:
        EnrichWithLookup(
            input_key="df_estudiantes",
            lookup_key="df_cursos",
            on="Curso",
            columns=["Nivel", "Jefe_UTP"],
            output_key="df_estudiantes_enriquecido",
        )

    Ejemplo con left_on/right_on:
        EnrichWithLookup(
            input_key="df_estudiantes",
            lookup_key="df_cursos",
            left_on="CursoID",
            right_on="ID_Curso",
            columns=["ID_Curso", "Nivel", "Jefe_UTP"],
            output_key="df_estudiantes_enriquecido",
        )
    """
    def __init__(
        self,
        input_key: str,
        lookup_key: str,
        columns: List[str],
        output_key: str,
        on: Optional[str] = None,
        left_on: Optional[str] = None,
        right_on: Optional[str] = None,
        how: str = "inner",
    ):
        super().__init__(
            name=f"EnrichWithLookup_{input_key}",
            requires=[input_key, lookup_key],
            produces=[output_key],
        )
        self.input_key = input_key
        self.lookup_key = lookup_key
        self.on = on
        self.left_on = left_on
        self.right_on = right_on
        self.columns = columns
        self.output_key = output_key
        self.how = how

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)

        # 1. Validar configuracion de llaves
        has_on = self.on is not None
        has_pair = self.left_on is not None and self.right_on is not None

        if not has_on and not has_pair:
            raise ValueError(
                f"[{self.name}] Debes especificar 'on' o el par 'left_on'/'right_on'."
            )
        if has_on and (self.left_on is not None or self.right_on is not None):
            raise ValueError(
                f"[{self.name}] Usa 'on' o 'left_on'/'right_on', no ambos a la vez."
            )
        if (self.left_on is None) != (self.right_on is None):
            raise ValueError(
                f"[{self.name}] 'left_on' y 'right_on' deben usarse juntos."
            )

        # 2. Obtener DataFrames
        df_main = ctx.artifacts.get(self.input_key)
        df_lookup = ctx.artifacts.get(self.lookup_key)

        if df_main is None:
            raise ValueError(f"[{self.name}] Artifact '{self.input_key}' no encontrado en ctx.artifacts.")
        if df_lookup is None:
            raise ValueError(f"[{self.name}] Artifact '{self.lookup_key}' no encontrado en ctx.artifacts.")

        if df_main.empty:
            self._log(f"[{self.name}] Advertencia: DataFrame principal '{self.input_key}' está vacío.")
            ctx.artifacts[self.output_key] = df_main.copy()
            ctx.last_artifact_key = self.output_key
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        if df_lookup.empty:
            self._log(f"[{self.name}] Advertencia: DataFrame de lookup '{self.lookup_key}' está vacío.")
            ctx.artifacts[self.output_key] = df_main.copy()
            ctx.last_artifact_key = self.output_key
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 3. Validar que las columnas llave existen
        if has_on:
            if self.on not in df_main.columns:
                raise ValueError(f"[{self.name}] Columna llave '{self.on}' no existe en '{self.input_key}'.")
            if self.on not in df_lookup.columns:
                raise ValueError(f"[{self.name}] Columna llave '{self.on}' no existe en '{self.lookup_key}'.")
        else:
            if self.left_on not in df_main.columns:
                raise ValueError(f"[{self.name}] Columna '{self.left_on}' no existe en '{self.input_key}'.")
            if self.right_on not in df_lookup.columns:
                raise ValueError(f"[{self.name}] Columna '{self.right_on}' no existe en '{self.lookup_key}'.")

        # 4. Validar columnas del lookup
        missing_cols = [c for c in self.columns if c not in df_lookup.columns]
        if missing_cols:
            raise ValueError(
                f"[{self.name}] Columnas no encontradas en '{self.lookup_key}': {missing_cols}. "
                f"Disponibles: {df_lookup.columns.tolist()}"
            )

        # 5. Recortar lookup a las columnas solicitadas
        # Si se usa right_on, incluirlo en el slice aunque no esté en columns
        # (es necesario para el merge). Se eliminará del resultado si no estaba en columns.
        if has_pair and self.right_on not in self.columns:
            cols_para_slim = [self.right_on] + self.columns
        else:
            cols_para_slim = self.columns
        df_lookup_slim = df_lookup[cols_para_slim].copy()

        # 6. Ejecutar merge
        try:
            if has_on:
                df_result = df_main.merge(df_lookup_slim, on=self.on, how=self.how)
            else:
                df_result = df_main.merge(
                    df_lookup_slim,
                    left_on=self.left_on,
                    right_on=self.right_on,
                    how=self.how,
                )
                # Eliminar la columna right_on del resultado si no fue pedida en columns
                if self.right_on not in self.columns and self.right_on in df_result.columns:
                    df_result = df_result.drop(columns=[self.right_on])
        except Exception as e:
            raise ValueError(f"[{self.name}] Error ejecutando merge: {e}")

        # 7. Log informativo
        rows_before = len(df_main)
        rows_after = len(df_result)
        if rows_after < rows_before:
            self._log(
                f"[{self.name}] Advertencia: el join redujo filas de {rows_before} a {rows_after}. "
                f"Verifica que las llaves coincidan correctamente."
            )
        else:
            self._log(f"[{self.name}] Join completado: {rows_before} → {rows_after} filas.")

        # 8. Guardar resultado
        ctx.artifacts[self.output_key] = df_result
        ctx.last_artifact_key = self.output_key
        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)
        

class ModifyColumnValues(Step):
    """
    Modifica valores de columnas usando reglas definidas (replace, map).

    Parametros:
        input_key (opcional): clave del artifact de entrada.
            Si no se entrega, usa ctx.last_artifact_key o ctx.params["default_artifact_key"].
        output_key (opcional): clave del artifact de salida.
            Si no se entrega, se deriva desde input_key (ej: df_modified_...).
        transformations (opcional): lista de reglas de transformación.
            Si no se entrega, busca en ctx.params["transformations"].

    Ejemplo de regla replace:
        {
            "columna": "Curso",
            "operacion": "replace",
            "valores": [
                {"patron": "° medio ", "reemplazo": ""},
                {"patron": "° básico ", "reemplazo": ""}
            ],
            "valor_completo": false,
            "default": null
        }

    Ejemplo de regla math:
        {
            "columna": "Rend",
            "operacion": "math",
            "valores": [
                {"condicion": "x > 1", "expresion": "x / 100"},
                {"condicion": "*",     "expresion": "x"}
            ]
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


class ApplyDerivedFields(Step):
    """
    Agrega columnas calculadas (derived_fields) al DataFrame.

    Aplica una lista declarativa de funciones (kinds: agg / slope / delta)
    al DataFrame que viene del step previo. Las columnas resultantes quedan
    disponibles para el resto del pipeline (incluido SaveToMetric, que las
    persiste en metric_data).

    Parámetros:
        input_key (opcional): clave del artifact de entrada.
            Default: ctx.last_artifact_key.
        output_key (opcional): clave del artifact de salida.
            Default: f"df_derived_{input_key}".
        derived_fields (opcional): lista de configs.
            Si no se entrega, busca en ctx.params["derived_fields"].

    Ejemplo de configs:
        [
          {"kind": "agg",   "name": "Logro_Promedio_Estudiante",
           "value_field": "Rend", "entity_field": "Rut", "agg": "mean"},
          {"kind": "slope", "name": "Avance",
           "value_field": "Rend", "entity_field": "Rut",
           "time_field": "Numero_Prueba", "min_points": 2},
          {"kind": "delta", "name": "Mejora_vs_Inicio",
           "value_field": "Rend", "entity_field": "Rut",
           "time_field": "Numero_Prueba"}
        ]

    Ver `derived_fields_engine.KIND_REGISTRY` para todos los kinds y args.
    """
    def __init__(
        self,
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        derived_fields: Optional[List[Dict]] = None,
    ):
        resolved_output_key = output_key
        if input_key and not resolved_output_key:
            resolved_output_key = f"df_derived_{input_key}"

        super().__init__(
            name="ApplyDerivedFields",
            requires=[input_key] if input_key else [],
            produces=[resolved_output_key] if resolved_output_key else [],
        )
        self.input_key = input_key
        self.output_key = resolved_output_key
        self.derived_fields = derived_fields or []

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)

        # 1. Resolver input/output
        input_key = self.input_key or ctx.last_artifact_key or ctx.params.get("default_artifact_key")
        if not input_key:
            raise ValueError(f"[{self.name}] No se pudo resolver input_key.")
        output_key = self.output_key or f"df_derived_{input_key}"
        self.input_key = input_key
        self.output_key = output_key

        # 2. Obtener DataFrame
        df = ctx.artifacts.get(input_key)
        if df is None or (hasattr(df, "empty") and df.empty):
            self._log(f"[{self.name}] Warning: DataFrame vacío o inexistente en {input_key}")
            ctx.artifacts[output_key] = pd.DataFrame() if df is None else df.copy()
            ctx.last_artifact_key = output_key
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 3. Resolver lista de derived_fields (init o context)
        configs = self.derived_fields or ctx.params.get("derived_fields", [])
        if not configs:
            self._log(f"[{self.name}] No hay derived_fields configurados; passthrough.")
            ctx.artifacts[output_key] = df.copy()
            ctx.last_artifact_key = output_key
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 3b. Resolver mapping_id en kinds lookup_range / lookup_dict.
        # Si un config tiene `mapping_id`, levantamos el Spec asociado y
        # mergeamos su contenido (ranges/mapping/extract/...) en el config
        # antes de pasar al engine. Permite reusar mapeos guardados desde
        # /functions sin duplicar la tabla en el JSON del pipeline.
        configs = self._resolve_mapping_refs(ctx, configs)

        # 4. Aplicar engine
        try:
            df_out = apply_derived_fields(df, configs)
        except Exception as e:
            raise ValueError(f"[{self.name}] Error aplicando derived_fields: {e}")

        added_cols = [c for c in df_out.columns if c not in df.columns]
        self._log(f"[{self.name}] Aplicadas {len(configs)} funciones, columnas nuevas: {added_cols}")

        # 5. Guardar
        ctx.artifacts[output_key] = df_out
        ctx.last_artifact_key = output_key
        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)

    # ---------------------------------------------------------------
    # Helper: resolver mapping_id → config inline para los kinds lookup_*
    # ---------------------------------------------------------------
    def _resolve_mapping_refs(self, ctx, configs):
        """Si un config tiene `mapping_id`, lo reemplaza con los campos
        del MappingConfig guardado (ranges, mapping, extract, default,
        match, case_insensitive). Los campos inline del config tienen
        precedencia (permite override).

        Requiere ctx.db y ctx.org_id. Si no están, devuelve configs
        sin tocar (modo standalone para tests).
        """
        db = getattr(ctx, "db", None)
        org_id = getattr(ctx, "org_id", None)
        out = []
        for c in configs:
            mid = c.get("mapping_id") if isinstance(c, dict) else None
            if not mid or db is None or org_id is None:
                out.append(c)
                continue
            try:
                from backend.routers.mappings import resolve_mapping_to_lookup_config
                resolved = resolve_mapping_to_lookup_config(db, org_id, int(mid))
            except Exception as e:
                self._log(f"[{self.name}] Warning: no se pudo resolver mapping_id={mid}: {e}")
                out.append(c)
                continue
            # Merge: el resolved trae las claves del mapeo, c sobrescribe
            # cualquier override inline (típicamente kind, name, value_field).
            merged = {**resolved, **{k: v for k, v in c.items() if k != "mapping_id"}}
            out.append(merged)
        return out
