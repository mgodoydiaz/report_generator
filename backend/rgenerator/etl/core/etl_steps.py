"""Steps de transformación y enriquecimiento de datos (ETL)."""

# Librerias estandar
import os
import pandas as pd
from typing import Callable, Optional, Dict, List

# Importaciones internas de RGenerator
from .step import Step, WaitingForInputException


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
            requires=[input_key] if input_key else [],
            produces=[resolved_output_key] if resolved_output_key else []
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
        df_lookup_slim = df_lookup[self.columns].copy()

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
