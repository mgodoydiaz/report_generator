"""Orquestador del motor PDF v2.

Recibe (esquema + dataframes + params) y produce bytes PDF. No conoce de
SIMCE/DIA específicos — lee el `esquema.json` del tipo solicitado y ejecuta
las funciones declaradas usando `CHART_REGISTRY` y `TABLE_REGISTRY`.

Flujo:
    1) Carga esquema.json del report_type.
    2) Crea aux_dir temporal para PNGs intermedios.
    3) Para cada sección fija:
        - chart → llama charts.fn(df, ..., nombre_grafico=aux_dir/X.png)
                  → embebe como <img src="data:base64,...">
        - table → llama tables.fn(df, ...) → DataFrame
                  → renderiza con helpers.df_a_html_table
    4) Para secciones_dinamicas (iteración por curso/categoría): idem pero
       repitiendo por cada valor único (TODO en próximo iter).
    5) Renderiza informe_base.html con Jinja2.
    6) WeasyPrint → bytes PDF.
    7) Limpia aux_dir.
"""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from datetime import date
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader

# weasyprint requiere libs nativas (Pango/Cairo/GLib) que pueden no estar
# presentes en hosts Windows. Import lazy dentro de la función que lo usa
# para que importar este módulo no falle en setups de testing/dev.

from . import charts, tables
from .errores import DatosInsuficientes, mensaje_sin_datos
from .helpers import df_a_html_table, embed_png_b64, ordenar_valores_categoricos
from ..core.derived_fields_engine import apply_derived_fields

try:  # el logger del backend no está disponible en usos standalone del paquete
    from backend.logging_config import get_logger
    logger = get_logger(__name__)
except Exception:  # pragma: no cover — fallback defensivo
    import logging
    logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent
TEMPLATES_DIR = REPORTS_DIR / "templates"
ASSETS_DIR = REPORTS_DIR / "assets"

# Aviso que se imprime en el PDF cuando una sección falla. El detalle
# técnico (tipo de excepción + traceback) va SOLO al log: un informe que se
# entrega a la fundación no debe mostrar `ValueError: List of boxplot
# statistics...` (QA 2026-07-30, P0-1 / P0-2).
AVISO_SECCION_FALLIDA = "No fue posible generar esta sección con los datos disponibles."


def _resolve_logo_path(name: str | None) -> str | None:
    """Resuelve un nombre de logo a path absoluto en assets/. None si no existe."""
    if not name:
        return None
    p = ASSETS_DIR / name
    return str(p) if p.exists() else None


def _interpolar(obj: Any, context: dict) -> Any:
    """Reemplaza placeholders `{clave}` en strings recursivamente.

    Soporta dicts, listas y strings. Otros tipos se devuelven sin tocar.
    Usado para que un esquema con `{curso}` se concrete por iteración.

    Ejemplo:
        _interpolar({"titulo": "Logro - {curso}"}, {"curso": "I A"})
        → {"titulo": "Logro - I A"}
    """
    if isinstance(obj, str):
        try:
            return obj.format(**context)
        except (KeyError, IndexError):
            return obj
    if isinstance(obj, dict):
        return {k: _interpolar(v, context) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_interpolar(v, context) for v in obj]
    return obj


def _error_seccion(titulo: str, contexto: str, exc: BaseException | None = None) -> dict:
    """Sección de error: aviso neutro al PDF, detalle técnico al log.

    Args:
        titulo: título de la sección que falló (se conserva en el PDF).
        contexto: qué se estaba ejecutando, para el log ("chart 'x'").
        exc: excepción capturada, si hubo una. Se loguea con traceback.

    Returns:
        Dict de sección tipo "error" con el mensaje neutro.
    """
    if exc is not None:
        logger.error(
            "Sección de informe fallida (%s, título=%r)", contexto, titulo,
            exc_info=exc,
        )
    else:
        logger.error("Sección de informe no ejecutable (%s, título=%r)", contexto, titulo)
    return {"tipo": "error", "titulo": titulo, "msg": AVISO_SECCION_FALLIDA}


def _ejecutar_seccion(
    seccion: dict,
    dataframes: dict[str, pd.DataFrame],
    aux_dir: Path,
) -> dict:
    """Ejecuta UNA sección del esquema y devuelve un dict listo para Jinja.

    Args:
        seccion: dict del esquema con keys `tipo`, `titulo`, `fn`,
            `df_input`, `params`.
        dataframes: dict {role: DataFrame} disponibles.
        aux_dir: Path donde guardar PNGs intermedios.

    Returns:
        Dict con `tipo` y datos renderizados:
            chart → {tipo: "chart", titulo, image_b64}
            table → {tipo: "table", titulo, html}
            heading → {tipo: "heading", titulo}  (puramente visual)
            nota    → {tipo: "nota", titulo, texto} (párrafo explicativo)
    """
    tipo = seccion.get("tipo")
    titulo = seccion.get("titulo", "")

    if tipo == "heading":
        return {"tipo": "heading", "titulo": titulo}

    if tipo == "page_break":
        return {"tipo": "page_break"}

    if tipo == "nota":
        # Párrafo explicativo. Lo usan los módulos del motor único para
        # decir POR QUÉ una sección no está (evolución con un solo punto
        # temporal, riesgo persistente sin 2 evaluaciones consecutivas):
        # un informe que simplemente omite el bloque deja al lector
        # preguntándose si se rompió algo.
        return {
            "tipo": "nota",
            "titulo": titulo,
            "texto": seccion.get("texto", ""),
        }

    fn_name = seccion.get("fn")
    df_key = seccion.get("df_input")
    params = dict(seccion.get("params", {}))  # copia, no mutamos el esquema

    if df_key not in dataframes:
        return _error_seccion(titulo, f"DataFrame '{df_key}' no disponible")
    df = dataframes[df_key]

    if tipo == "chart":
        spec = charts.CHART_REGISTRY.get(fn_name)
        if not spec:
            return _error_seccion(titulo, f"chart '{fn_name}' no existe en CHART_REGISTRY")
        # Path PNG temporal
        png_path = aux_dir / f"{fn_name}_{abs(hash(json.dumps(params, sort_keys=True, default=str)))}.png"
        params["nombre_grafico"] = str(png_path)
        try:
            spec["fn"](df, **params)
        except Exception as e:  # defensivo: una sección rota no cae el informe
            return _error_seccion(titulo, f"chart '{fn_name}'", e)
        return {"tipo": "chart", "titulo": titulo, "image_b64": embed_png_b64(png_path)}

    if tipo == "table":
        spec = tables.TABLE_REGISTRY.get(fn_name)
        if not spec:
            return _error_seccion(titulo, f"table '{fn_name}' no existe en TABLE_REGISTRY")
        try:
            df_out = spec["fn"](df, **params)
        except Exception as e:
            return _error_seccion(titulo, f"table '{fn_name}'", e)
        return {"tipo": "table", "titulo": titulo, "html": df_a_html_table(df_out)}

    if tipo == "pivot":
        # Azúcar sintáctico para tabla pivote (motor W2). La sección declara
        # `spec` (un PivotSpec) y opcionalmente `filtro`, sin pasar por `fn`.
        # Multi-pivote: varias secciones `pivot`. Pivote por curso: usar las
        # secciones dinámicas (`iterar_por`) + filtro={"Curso": "{curso}"}.
        pivot_spec = seccion.get("spec")
        filtro = seccion.get("filtro")
        if not pivot_spec:
            return _error_seccion(titulo, "sección 'pivot' sin 'spec'")
        try:
            df_out = tables.tabla_pivote(df, spec=pivot_spec, filtro=filtro)
        except Exception as e:
            return _error_seccion(titulo, "pivot", e)
        return {"tipo": "table", "titulo": titulo, "html": df_a_html_table(df_out)}

    return _error_seccion(titulo, f"tipo de sección desconocido: {tipo}")


def construir_pdf(
    report_type: str,
    dataframes: dict[str, pd.DataFrame],
    overrides: dict | None = None,
    df_principal: str | None = None,
    filtros_desc: str = "",
    esquema: dict | None = None,
) -> bytes:
    """Punto de entrada: genera bytes PDF para un tipo de informe.

    Args:
        report_type: "simce" | "dia" | etc. — coincide con el subdirectorio
            que contiene el esquema.json. Cuando se pasa `esquema` solo se
            usa como etiqueta (prefijo del directorio temporal).
        dataframes: dict {role: DataFrame}, ej {"estudiantes": df1,
            "preguntas": df2}. Las keys deben coincidir con las que el
            esquema declare en `df_input`.
        overrides: dict opcional para sobreescribir partes del esquema en
            runtime (ej {"branding": {"center_header": ["...", "...", "..."]}}).
            Útil para que el endpoint reciba parámetros de UI.
        df_principal: key del DataFrame sin el cual el informe no tiene
            sentido (ej "estudiantes_prueba"). Si viene y ese DataFrame
            quedó SIN FILAS tras los filtros, se aborta con
            `DatosInsuficientes` en lugar de emitir un PDF vacío con
            gráficos en blanco (QA 2026-07-30, P0-1).
        filtros_desc: filtros aplicados en texto legible, para el mensaje
            de error ("Hito: INTERMEDIO · Año: 2026").
        esquema: esquema YA construido en memoria. Cuando viene, NO se lee
            `<report_type>/esquema.json` del disco: es lo que permite a los
            módulos del motor único (`reports/custom/*.py`) armar sus
            secciones en Python y variarlas por modo, y a los indicadores
            sin carpeta de esquema (Cálculo Veloz, Fluidez Lectora) usar
            este runtime. Con `None` el comportamiento es idéntico al
            histórico (contrato motor único, N5 / tensión T1).

    Returns:
        Bytes del PDF generado.

    Raises:
        FileNotFoundError: si no existe el esquema.json del tipo solicitado
            y no se pasó `esquema`.
        DatosInsuficientes: si `df_principal` quedó vacío.
    """
    esquema_en_memoria = esquema is not None
    if not esquema_en_memoria:
        esquema_path = REPORTS_DIR / report_type / "esquema.json"
        if not esquema_path.exists():
            raise FileNotFoundError(
                f"No existe esquema para tipo '{report_type}': {esquema_path}"
            )

    # Guardia de dataset vacío ANTES de gastar tiempo en secciones: sin
    # filas todos los charts salen en blanco y las tablas con solo
    # encabezados — un PDF que parece válido pero no dice nada.
    if df_principal:
        df_ppal = dataframes.get(df_principal)
        if df_ppal is None or len(df_ppal) == 0:
            raise DatosInsuficientes(mensaje_sin_datos(filtros_desc))

    if esquema_en_memoria:
        # Copia profunda: los overrides mutan el dict y el módulo llamador
        # puede estar reutilizando su esquema entre corridas.
        esquema = copy.deepcopy(esquema)
    else:
        with open(esquema_path, "r", encoding="utf-8") as f:
            esquema = json.load(f)

    # Aplicar overrides (merge superficial, suficiente para esta versión)
    if overrides:
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(esquema.get(key), dict):
                esquema[key].update(value)
            else:
                esquema[key] = value

    # NOTA: las derived_fields del esquema se aplican en crear_informe.py
    # ANTES del filtro a un solo hito/prueba (las funciones temporales
    # como slope/delta necesitan ver el histórico completo). Aplicarlas
    # acá otra vez sobre dfs ya filtrados sobreescribiría con NaN.
    # Aquí solo se ejecutan si la columna calculada NO existe todavía
    # en el df (fallback para esquemas que NO tengan un crear_informe.py
    # custom que las aplique upstream).
    derived_fields_runtime = esquema.get("derived_fields") or []
    for entry in derived_fields_runtime:
        target_key = entry.get("df_input")
        configs = entry.get("configs") or []
        if target_key and configs and target_key in dataframes:
            df_target = dataframes[target_key]
            pending = [c for c in configs if c.get("name") not in df_target.columns]
            if pending:
                dataframes = dict(dataframes)
                dataframes[target_key] = apply_derived_fields(df_target, pending)

    # Resolver branding (logos a path absoluto + base64)
    branding = dict(esquema.get("branding", {}))
    for side in ("left_image", "right_image"):
        path = _resolve_logo_path(branding.get(side))
        if path:
            branding[f"{side}_b64"] = embed_png_b64(path)
        else:
            branding[f"{side}_b64"] = None

    # Ejecutar secciones dentro de un aux_dir temporal
    with tempfile.TemporaryDirectory(prefix=f"report_{report_type}_") as tmp_str:
        aux_dir = Path(tmp_str)

        rendered = []

        # 1) Secciones fijas. Cualquier sección con `break_before: true`
        # inserta un page_break antes (útil para tablas anchas que de otro
        # modo se cortan a media página).
        for sec in esquema.get("secciones_fijas", []):
            if sec.get("break_before"):
                rendered.append({"tipo": "page_break"})
            rendered.append(_ejecutar_seccion(sec, dataframes, aux_dir))

        # 2) Secciones dinámicas — iteran por valor único de `iterar_por`
        # del DataFrame `df_iterar`. Cada valor inserta page_break + las
        # secciones declaradas en `secciones`. Replica el flujo LaTeX:
        # `for curso in cursos: \newpage \section + tabla + tabla`.
        din_cfg = esquema.get("secciones_dinamicas") or {}
        # Filtrar comentarios JSON (keys que arrancan con _)
        din_cfg = {k: v for k, v in din_cfg.items() if not k.startswith("_")}
        if din_cfg:
            iterar_por = din_cfg.get("iterar_por")
            df_iterar_key = din_cfg.get("df_iterar")
            secciones_template = din_cfg.get("secciones", [])

            if iterar_por and df_iterar_key in dataframes and secciones_template:
                df_iterar = dataframes[df_iterar_key]
                if iterar_por in df_iterar.columns:
                    valores = df_iterar[iterar_por].dropna().unique().tolist()
                    # Orden alfanumérico natural (1 A, 1 B, 2 A, … 10 A):
                    # alfabético de base y numérico donde hay dígitos, para
                    # que "10 A" no se cuele entre "1 A" y "2 A" (P0-A).
                    valores = ordenar_valores_categoricos(
                        sorted(valores, key=lambda x: str(x)), iterar_por
                    )

                    for valor in valores:
                        # Page break antes de cada valor (igual a \newpage LaTeX)
                        rendered.append({"tipo": "page_break"})
                        # Context para interpolar {curso} en titulo y params.
                        # La key se deriva del nombre de la columna en lowercase
                        # (Curso → curso, Habilidad → habilidad, etc.).
                        ctx = {iterar_por.lower(): str(valor), "valor": str(valor)}
                        for sec_template in secciones_template:
                            sec_concreta = _interpolar(sec_template, ctx)
                            rendered.append(_ejecutar_seccion(sec_concreta, dataframes, aux_dir))

        # Renderizar HTML
        env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
        template = env.get_template("informe_base.html")
        html_str = template.render(
            title=esquema.get("title", "Informe"),
            subtitle=esquema.get("subtitle", ""),
            filters_label=esquema.get("filters_label", ""),
            secciones=rendered,
            branding=branding,
            report_date=date.today().strftime("%d/%m/%Y"),
        )

        # WeasyPrint — import lazy: requiere libs nativas no presentes en todo host
        from weasyprint import HTML as WeasyprintHTML
        return WeasyprintHTML(string=html_str, base_url=str(REPORTS_DIR)).write_pdf()
