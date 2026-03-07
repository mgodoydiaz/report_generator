"""Steps de generación de reportes: gráficos, tablas, PDF y DOCX."""

# Librerias estandar
from pathlib import Path
import os
import shutil
import json
import pandas as pd
from typing import Optional, Dict, List

# Importaciones internas de RGenerator
from .step import Step
from rgenerator.tooling import plot_tools, report_tools
from rgenerator.tooling.report_docx_tools import render_docx_report
from config import REPORTS_TEMPLATES_DIR
from rgenerator.tooling.constants import formato_informe_generico, indice_alfabetico


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

        # 1. Resolver esquema: constructor directo, nuevo formato (charts_list) o legacy (charts_schema)
        schema = self.charts_schema
        if not schema:
            schema = ctx.params.get("charts_list") or ctx.params.get("charts_schema", [])

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

            # Obtener el DataFrame desde artifacts (input_key puede ser string o list[string])
            if isinstance(input_key, list):
                keys = input_key
            else:
                keys = [input_key]

            dfs = [ctx.artifacts.get(k) for k in keys]
            missing = [k for k, d in zip(keys, dfs) if d is None]
            if missing:
                self._log(f"[{self.name}] Error: Artifacts no encontrados: {missing}")
                continue

            df = dfs[0]
            extra_dfs = {k: d for k, d in zip(keys[1:], dfs[1:])}

            # Preparar argumentos
            output_path = aux_dir / output_filename
            kwargs = params.copy()
            kwargs["nombre_grafico"] = str(output_path)
            kwargs.update(extra_dfs)

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

        # 1. Resolver esquema: constructor directo, nuevo formato (tables_list) o legacy (tables_schema)
        schema = self.tables_schema
        if not schema:
            schema = ctx.params.get("tables_list") or ctx.params.get("tables_schema", [])

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
            iterate_param = table_def.get("iterate_param", None)

            # Validar definición mínima
            if not func_name or not input_key or not output_filename:
                self._log(f"[{self.name}] Error: Definición incompleta: {table_def}")
                continue

            func = getattr(report_tools, func_name, None)
            if not func:
                self._log(f"[{self.name}] Error: La función '{func_name}' no existe en report_tools.")
                continue

            # Obtener DataFrame(s) desde artifacts (input_key puede ser string o list[string])
            if isinstance(input_key, list):
                keys = input_key
            else:
                keys = [input_key]

            dfs = [ctx.artifacts.get(k) for k in keys]
            missing = [k for k, d in zip(keys, dfs) if d is None]
            if missing:
                self._log(f"[{self.name}] Error: Artifacts no encontrados: {missing}")
                continue

            df_full = dfs[0]
            extra_dfs = {k: d for k, d in zip(keys[1:], dfs[1:])}

            # Helper: ejecuta la función y guarda el resultado como Excel
            def process_and_save(df_k, filename_k, params_k, _func=func, _extra=extra_dfs):
                try:
                    df_res = _func(df_k, **params_k, **_extra)
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
                    # También como kwarg raíz: usa iterate_param si está definido,
                    # sino usa el nombre de la columna directamente
                    if iterate_param:
                        iter_params[iterate_param] = val
                    else:
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

                for key, value in variables.items():
                    # Sanitize key/value if needed
                    val_str = str(value).replace("_", "\\_") # Escape básico
                    f.write(new_command_format.format(key, val_str))
                f.write("\n")

            # 4. Generar contenido dinámico (secciones)
            # Combinamos fijas y dinámicas en orden
            secciones_fijas = schema.get("secciones_fijas", [])
            secciones_dinamicas = schema.get("secciones_dinamicas", [])

            todas_secciones = secciones_fijas + secciones_dinamicas

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
                         p = Path(contenido_path)
                         img_name = p.name
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
            cmd = "xelatex -interaction=nonstopmode informe.tex"
            ret = os.system(cmd)

            if ret == 0:
                self._log(f"[{self.name}] PDF generado exitosamente.")
                # Mover a outputs si existe output_dir
                if hasattr(ctx, "outputs_dir") and ctx.outputs_dir.exists():
                     target = ctx.outputs_dir / "informe.pdf"
                elif hasattr(ctx, "outputs"):
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
