"""Informe SIMCE — formato oficial + los 4 modos del motor único.

Dos caminos, deliberadamente separados:

``modo=None``
    El informe "formato oficial" de siempre: delega en
    `dispatch_v2.generar_pdf_v2`, que exige un filtro temporal y arma el
    PDF con `simce/esquema.json`. **Byte-compatible** con la versión previa
    al motor único — lo invoca `POST /api/reports/custom/simce`, que nunca
    manda `modo`.

``modo ∈ MODOS_SOPORTADOS``
    El piloto del motor único (contrato §4): el módulo arma sus propios
    DataFrames y su propia lista de secciones según el período, y los pasa
    a `runtime.construir_pdf` como esquema EN MEMORIA (N5). No usa el
    `pdf_layout` del indicador. Lo invoca
    `POST /api/indicators/{id}/export-pdf` con `{"periodo": {...}}`.

Reglas de las fichas que este módulo materializa:

- Detalle por alumno / por pregunta / por curso SOLO en `ultima_prueba`
  (decisiones 1 y 5).
- Las secciones de evolución se AUTO-OMITEN con un único punto temporal, y
  el informe explica por qué (decisión 16).
- Riesgo persistente al final del modo anual (decisión 2).
- Heatmap Curso × Eje excluido de todos los modos (decisión 3).
- Habilidad y Eje Temático cruzados por Curso, como el esquema vigente
  validado contra la referencia Pullinque (resolución de la tensión T5).
- Sin portada de página completa: bloque de título y a continuación el
  contenido (salvedad del dueño, OK de fase 2).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from sqlalchemy.orm import Session

from . import _secciones as sec
from .. import asignatura as asignaturas
from .. import periodos
from ..branding import (
    aplicar_center_header,
    formatear_filtros,
    lineas_encabezado_prueba,
    valor_unico,
)
from ..data import cargar_dataframes_indicator
from ..dispatch_v2 import aplicar_pie_organizacion, generar_pdf_v2
from ..errores import DatosInsuficientes, mensaje_sin_datos
from ...core.derived_fields_engine import apply_derived_fields

LABEL = "Informe de evaluación SIMCE (formato oficial)"
DESCRIPCION = (
    "PDF con el formato oficial del ensayo SIMCE. Requiere filtrar a un "
    "solo punto temporal (Mes o N° de prueba)."
)
FORMATO = "pdf"
ENGINE_TYPES = ["simce"]
REQUIERE_FILTRO_TEMPORAL = ["Mes", "N Prueba", "Numero_Prueba"]
# El SIMCE se genera por asignatura: mezclarlas contaría pares
# alumno×asignatura como alumnos distintos.
REQUIERE_ASIGNATURA = True
FILENAME = "informe_simce.pdf"

#: Modos que el módulo SABE generar (contrato §4). Incluye `semestral`, que
#: sigue implementado y accesible por API aunque ya no se ofrezca.
MODOS_SOPORTADOS = ["ultima_prueba", "semestral", "anual", "personalizado"]

#: Modos PÚBLICOS: los que el selector de informes ofrece como tarjeta.
#: `semestral` fue RETIRADO el 2026-08-03 por decisión del dueño (mismo
#: patrón que los informes Word): desde que los períodos se anclan en la
#: última evaluación con datos, semestral y anual devuelven casi siempre el
#: mismo recorte. El código que lo implementa se conserva íntegro y
#: `POST /api/indicators/{id}/export-pdf` con `{"periodo":{"tipo":"semestral"}}`
#: sigue respondiendo 200. Para reactivarlo basta devolver "semestral" a esta
#: lista y reinsertar la card en `backend/routers/indicators.py`.
MODOS = ["ultima_prueba", "anual", "personalizado"]
MOTIVO_MODO_NO_DISPONIBLE: dict[str, str] = {}

#: Título del informe (también es la 1ª línea del encabezado del esquema).
TITULO = "Informe Ensayo SIMCE"

#: Niveles de logro SIMCE, de MEJOR a PEOR. Se usan si el indicador no
#: declara `achievement_levels`.
NIVELES_SIMCE = ["Adecuado", "Elemental", "Insuficiente"]
NIVEL_RIESGO = "Insuficiente"

#: Evaluaciones consecutivas que exige el riesgo persistente.
N_EVALUACIONES_RIESGO = 2

_ESQUEMA_PATH = Path(__file__).resolve().parent.parent / "simce" / "esquema.json"

_NOTA_SIN_EVOLUCION = (
    "El período seleccionado tiene una sola evaluación registrada, así que "
    "no hay evolución que graficar todavía. Los gráficos de tendencia "
    "aparecerán automáticamente cuando exista una segunda prueba en el "
    "período."
)
_NOTA_SIN_RIESGO_PERSISTENTE = (
    "El riesgo persistente compara el nivel de cada estudiante en dos "
    "evaluaciones consecutivas, la última de ellas la más reciente del "
    "período. El período seleccionado no tiene dos evaluaciones "
    "consecutivas con datos, o ningún estudiante quedó en nivel "
    "Insuficiente en ambas."
)


# ─────────────────────────────────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────────────────────────────────

def generar(
    db: Session,
    *,
    indicator_id: int,
    org_id: int,
    modo: Optional[str] = None,
    filtros: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> bytes:
    """Bytes del PDF SIMCE.

    Args:
        db: sesión SQLAlchemy.
        indicator_id, org_id: indicador y multi-tenancy.
        modo: uno de `MODOS`, o None para el informe "formato oficial".
        filtros: `{nombre_columna: valor | [valores]}` — nombres humanos
            ("Asignatura", "Mes", "Año"), nunca ids de dimensión.
        params: `{"periodo_desc": str}` — la descripción del período que
            ya resolvió `periodos.py` y que el despacho inyecta. Es la
            FUENTE ÚNICA del período: alimenta el bloque de título y el
            encabezado corrido. Sin ella el módulo la recalcula (fallback
            para invocación directa, ver `_descripcion_periodo`).
        overrides: overrides de esquema/branding.

    Returns:
        Bytes del PDF.

    Raises:
        ValueError: modo desconocido (mensaje en español, → HTTP 400).
        DatosInsuficientes: la combinación de filtros no tiene datos.
        AsignaturaRequerida: el indicador trae ≥2 asignaturas sin fijar una.
    """
    if modo is None:
        return generar_pdf_v2(
            db,
            tipo="simce",
            indicator_id=indicator_id,
            org_id=org_id,
            filtros=filtros,
            overrides=overrides,
        )

    if modo not in MODOS_SOPORTADOS:
        raise ValueError(
            f"El informe SIMCE no genera el modo '{modo}'. "
            f"Modos disponibles: {', '.join(MODOS_SOPORTADOS)}."
        )

    return _generar_por_modo(
        db,
        indicator_id=indicator_id,
        org_id=org_id,
        modo=modo,
        filtros=filtros,
        params=params,
        overrides=overrides,
    )


# ─────────────────────────────────────────────────────────────────────────
# Preparación de DataFrames
# ─────────────────────────────────────────────────────────────────────────

def _derived_fields_del_esquema() -> list[dict]:
    """Configs de derived_fields del `simce/esquema.json` para `estudiantes`.

    Se reutiliza el JSON en vez de duplicar las definiciones: es la MISMA
    fuente de verdad que usa el informe "formato oficial"
    (`Logro_Promedio_Estudiante`, `Avance`, `Mejora_vs_Inicio`).
    """
    if not _ESQUEMA_PATH.exists():  # pragma: no cover — defensivo
        return []
    with open(_ESQUEMA_PATH, encoding="utf-8") as f:
        esquema = json.load(f)
    for entrada in esquema.get("derived_fields") or []:
        if entrada.get("df_input") == "estudiantes":
            return entrada.get("configs") or []
    return []


def _branding_base() -> dict:
    """`branding` del esquema de disco (logos, pie, número de página)."""
    if not _ESQUEMA_PATH.exists():  # pragma: no cover — defensivo
        return {}
    with open(_ESQUEMA_PATH, encoding="utf-8") as f:
        return dict((json.load(f).get("branding") or {}))


def _columnas_temporales(df: pd.DataFrame) -> dict:
    return periodos.detectar_columnas_temporales_df(df)


def _partir_temporales(filtros: dict, cols: dict) -> tuple[dict, dict]:
    """(estructurales, temporales) según las columnas temporales detectadas."""
    nombres = {v for k, v in cols.items() if v}
    temporales = {k: v for k, v in filtros.items() if k in nombres}
    estructurales = {k: v for k, v in filtros.items() if k not in nombres}
    return estructurales, temporales


def _filtros_ultima_prueba(df: pd.DataFrame, cols: dict) -> dict:
    """Filtros que aíslan la ÚLTIMA prueba presente en `df`."""
    if df is None or df.empty:
        return {}
    mejor_clave, mejor_row = None, None
    for _, row in df.iterrows():
        clave = periodos.clave_temporal_detallada(row, cols)
        if mejor_clave is None or clave > mejor_clave:
            mejor_clave, mejor_row = clave, row
    if mejor_row is None:  # pragma: no cover — defensivo
        return {}

    filtros: dict[str, Any] = {}
    for rol in ("anio", "mes_like", "ordinal"):
        columna = cols.get(rol)
        if not columna:
            continue
        valor = mejor_row.get(columna)
        if valor is None or str(valor) == "" or (
            isinstance(valor, float) and pd.isna(valor)
        ):
            continue
        filtros[columna] = str(valor)
    return filtros


def _clave_bucket(row, cols: dict, modo: str) -> Optional[tuple]:
    """Clave del período comparable: (año) en anual, (año, semestre) en semestral."""
    anio, mes, _dia, _ord = periodos._componentes_temporales(row, cols)
    if anio < 0:
        return None
    if modo == "semestral":
        if mes < 0:
            return None
        return (anio, periodos.semestre_de_mes(mes))
    return (anio,)


def _etiqueta_bucket(clave: Optional[tuple], modo: str) -> str:
    """'2025' / '1er sem. 2026'. Vacío si no hay clave."""
    if not clave:
        return ""
    if modo == "semestral" and len(clave) == 2:
        anio, semestre = clave
        return f"{'1er' if semestre == 1 else '2º'} sem. {anio}"
    return str(clave[0])


def _periodo_previo(
    df_completo: pd.DataFrame,
    df_periodo: pd.DataFrame,
    cols: dict,
    modo: str,
) -> tuple[pd.DataFrame, Optional[tuple], Optional[tuple]]:
    """(filas del período anterior, clave actual, clave anterior).

    El "período anterior" es el bucket inmediatamente previo CON DATOS: el
    año anterior en `anual`/`personalizado`, el semestre anterior (que puede
    caer en el año anterior) en `semestral`. Sin datos previos devuelve un
    DataFrame vacío y clave None — la columna comparada sale "—".
    """
    vacio = df_completo.iloc[0:0]
    if df_completo is None or df_completo.empty or df_periodo is None or df_periodo.empty:
        return vacio, None, None

    actuales = {
        c for c in (_clave_bucket(r, cols, modo) for _, r in df_periodo.iterrows())
        if c
    }
    if not actuales:
        return vacio, None, None
    clave_actual = min(actuales)

    claves = pd.Series(
        [_clave_bucket(r, cols, modo) for _, r in df_completo.iterrows()],
        index=df_completo.index,
        dtype="object",
    )
    anteriores = {c for c in claves.tolist() if c and c < clave_actual}
    if not anteriores:
        return vacio, max(actuales), None
    clave_previa = max(anteriores)
    # `claves == clave_previa` compararía elemento a elemento contra cada
    # componente de la tupla; el map es la comparación que queremos.
    mascara = claves.map(lambda c: c == clave_previa).astype(bool)
    return df_completo[mascara], max(actuales), clave_previa


def _preparar_dataframes(
    db: Session,
    *,
    indicator_id: int,
    org_id: int,
    modo: str,
    filtros: dict[str, Any] | None,
) -> dict:
    """DataFrames y metadatos de la corrida (§4, tabla de dataframes).

    Devuelve un dict con `dataframes`, `asignatura`, `establecimiento`,
    `periodo_desc`, `filtros_desc` y `niveles`.
    """
    filtros = dict(filtros or {})
    resto, elegidas = asignaturas.partir_filtros(filtros)

    # Se carga el HISTÓRICO completo: las derived_fields (slope/delta) y la
    # comparación con el período anterior necesitan ver todas las pruebas.
    dataframes = cargar_dataframes_indicator(
        db, indicator_id=indicator_id, org_id=org_id, filtros=None
    )
    df_estudiantes = dataframes.get("estudiantes")
    df_preguntas = dataframes.get("preguntas")
    if df_estudiantes is None or df_preguntas is None:
        raise DatosInsuficientes(
            "El indicador debe tener metrics 'estudiantes' y 'preguntas' "
            "asociadas para generar el informe SIMCE."
        )

    cols = _columnas_temporales(df_estudiantes)
    estructurales, temporales = _partir_temporales(resto, cols)

    # 1) Filtros estructurales del usuario (Curso, Establecimiento, …).
    if estructurales:
        recortados = periodos.aplicar_filtros_a_dataframes(
            {"estudiantes": df_estudiantes, "preguntas": df_preguntas}, estructurales
        )
        df_estudiantes = recortados["estudiantes"]
        df_preguntas = recortados["preguntas"]

    # 2) Asignatura: el informe cubre UNA sola (levanta AsignaturaRequerida).
    columna_asignatura, valores_asignatura = asignaturas.dimension_asignatura(
        {"estudiantes": df_estudiantes, "preguntas": df_preguntas}
    )
    asignatura = asignaturas.resolver_seleccion(valores_asignatura, elegidas)
    if columna_asignatura and asignatura:
        recortados = asignaturas.filtrar_dataframes(
            {"estudiantes": df_estudiantes, "preguntas": df_preguntas},
            columna_asignatura,
            asignatura,
        )
        df_estudiantes = recortados["estudiantes"]
        df_preguntas = recortados["preguntas"]

    if len(df_estudiantes) == 0:
        raise DatosInsuficientes(mensaje_sin_datos(formatear_filtros(filtros)))

    # 3) derived_fields ANTES de recortar el período (regla ya documentada
    #    en runtime.py:243-249: slope/delta necesitan el histórico entero).
    configs = _derived_fields_del_esquema()
    if configs:
        df_estudiantes = apply_derived_fields(df_estudiantes, configs)

    # 4) Recorte al período del modo.
    recorte = periodos.aplicar_filtros_a_dataframes(
        {"estudiantes": df_estudiantes, "preguntas": df_preguntas}, temporales
    )
    df_est_periodo, df_preg_periodo = recorte["estudiantes"], recorte["preguntas"]
    if len(df_est_periodo) == 0:
        raise DatosInsuficientes(mensaje_sin_datos(formatear_filtros(filtros)))

    # 5) Recorte a UNA prueba (la última del período).
    filtros_prueba = _filtros_ultima_prueba(df_est_periodo, cols)
    recorte = periodos.aplicar_filtros_a_dataframes(
        {"estudiantes": df_est_periodo, "preguntas": df_preg_periodo}, filtros_prueba
    )
    df_est_prueba, df_preg_prueba = recorte["estudiantes"], recorte["preguntas"]

    # 6) Período anterior (solo lo consume el cuadro resumen comparado).
    df_est_previo, clave_actual, clave_previa = _periodo_previo(
        df_estudiantes, df_est_periodo, cols, modo
    )

    dataframes = {
        "estudiantes": df_estudiantes,
        "estudiantes_periodo": df_est_periodo,
        "estudiantes_prueba": df_est_prueba,
        "estudiantes_previo": df_est_previo,
        "preguntas": df_preguntas,
        "preguntas_periodo": df_preg_periodo,
        "preguntas_prueba": df_preg_prueba,
    }

    return {
        "dataframes": dataframes,
        "asignatura": asignatura or "",
        "establecimiento": valor_unico(df_est_periodo, "Establecimiento"),
        "columna_temporal": cols.get("mes_like") or cols.get("ordinal"),
        "columnas_temporales": cols,
        "etiqueta_actual": _etiqueta_bucket(clave_actual, modo),
        "etiqueta_previa": _etiqueta_bucket(clave_previa, modo),
        "filtros_efectivos": filtros,
        "temporales": temporales,
    }


# ─────────────────────────────────────────────────────────────────────────
# Secciones por modo (contrato §4.1 / §4.2)
# ─────────────────────────────────────────────────────────────────────────

def _niveles_y_colores(achievement_levels: Any) -> tuple[list[str], dict]:
    """(niveles de MEJOR a PEOR, {nivel: color}) desde `achievement_levels`.

    `Indicator.achievement_levels` guarda `[{name, color, order}]` con
    `order` ascendente del PEOR al mejor. Si el indicador no lo declara se
    cae a los tres niveles SIMCE y a la paleta semáforo por defecto.
    """
    crudo = achievement_levels
    if isinstance(crudo, str):
        try:
            crudo = json.loads(crudo or "[]")
        except (TypeError, ValueError):
            crudo = []
    if not isinstance(crudo, list) or not crudo:
        return list(NIVELES_SIMCE), {}

    entradas = [e for e in crudo if isinstance(e, dict) and e.get("name")]
    if not entradas:
        return list(NIVELES_SIMCE), {}
    entradas.sort(key=lambda e: e.get("order") or 0, reverse=True)
    niveles = [str(e["name"]) for e in entradas]
    colores = {str(e["name"]): e.get("color") for e in entradas if e.get("color")}
    return niveles, colores


def _seccion_chart(titulo: str, fn: str, df_input: str, params: dict,
                   break_before: bool = False) -> dict:
    seccion = {"tipo": "chart", "titulo": titulo, "fn": fn,
               "df_input": df_input, "params": params}
    if break_before:
        seccion["break_before"] = True
    return seccion


def _secciones_comunes(df_est: str, df_preg: str, niveles: list[str],
                       colores: dict) -> list[dict]:
    """Secciones 3 a 9 del contrato: idénticas en los 4 modos.

    (La 1 es el bloque de título y la 2 varía: simple en `ultima_prueba`,
    comparada con el período anterior en los demás.)
    """
    return [
        sec.seccion_resumen(
            df_est, columna="Simce", formato="number",
            titulo="Resumen de Puntaje SIMCE por Curso",
        ),
        _seccion_chart(
            "Rendimiento Promedio por Curso", "grafico_barras_promedio_por", df_est,
            {
                "columna_valor": "Rend",
                "agrupar_por": "Curso",
                "titulo": "Rendimiento Promedio por Curso",
                "ylabel": "Rendimiento (%)",
            },
        ),
        _seccion_chart(
            "Distribución de Puntaje SIMCE por Curso", "boxplot_valor_por_curso", df_est,
            {
                "columna_valor": "Simce",
                "agrupar_por": "Curso",
                "titulo_grafico": "Distribución de Puntaje SIMCE por Curso",
                "ylabel": "Puntaje SIMCE",
                "formato": "number",
            },
        ),
        _seccion_chart(
            "Cantidad de Alumnos por Nivel de Logro y Curso",
            "alumnos_por_nivel_cualitativo", df_est,
            {
                "columna_nivel": "Logro",
                "agrupar_por": "Curso",
                "lista_niveles": list(niveles),
                "color_overrides": dict(colores),
                "titulo_grafico": "Cantidad de Alumnos por Nivel de Logro y Curso",
                "titulo_leyenda": "Nivel de Logro",
                "ylabel": "Cantidad de Alumnos",
            },
        ),
        _seccion_chart(
            "Composición Global por Nivel", "composicion_por_nivel", df_est,
            {
                "columna_nivel": "Logro",
                "lista_niveles": list(niveles),
                "color_overrides": dict(colores),
                "titulo_grafico": "Composición Global por Nivel",
                "titulo_leyenda": "Nivel de Logro",
                "etiqueta_barra": "Establecimiento",
            },
        ),
        _seccion_chart(
            "Logro Promedio por Habilidad", "valor_promedio_agrupado_por", df_preg,
            {
                "columna_valor": "Logro",
                "agrupar_principal_por": "Curso",
                "agrupar_secundario_por": "Habilidad",
                "titulo_grafico": "Logro Promedio por Habilidad",
                "titulo_leyenda": "Habilidad",
                "formato": "percent",
            },
        ),
        _seccion_chart(
            "Logro Promedio por Eje Temático", "valor_promedio_agrupado_por", df_preg,
            {
                "columna_valor": "Logro",
                "agrupar_principal_por": "Curso",
                "agrupar_secundario_por": "Eje Temático",
                "titulo_grafico": "Logro Promedio por Eje Temático",
                "titulo_leyenda": "Eje Temático",
                "formato": "percent",
            },
        ),
    ]


def _secciones_detalle_ultima_prueba() -> list[dict]:
    """Secciones 10 y 11: detalle por alumno y por pregunta (decisión 1)."""
    return [
        {
            "tipo": "table",
            "titulo": "Estudiantes en Riesgo",
            "fn": "tabla_logro_por_alumno",
            "df_input": "estudiantes_prueba",
            "params": {
                "parametros": {"Logro": NIVEL_RIESGO},
                "sort_by": "Rend",
                "formatos": {"Rend": "percent", "Simce": "number"},
                "columnas": ["Curso", "Nombre", "Rend", "Simce"],
                "columnas_renombrar": {
                    "Nombre": "Estudiante",
                    "Rend": "Logro",
                    "Simce": "SIMCE",
                },
            },
        },
        {
            "tipo": "table",
            "titulo": "Estadística por Pregunta del Establecimiento",
            "fn": "crear_tabla_estadistica_por_pregunta",
            "df_input": "preguntas_prueba",
            "break_before": True,
            "params": {
                "parametros": {},
                "columnas_alternativas": ["A", "B", "C", "D", "E"],
                "columnas_data": ["Pregunta", "Correcta", "Distractor"],
            },
        },
    ]


def _secciones_dinamicas_por_curso() -> dict:
    """Sección 12: una página por curso con sus dos tablas de detalle."""
    return sec.secciones_por_curso(
        [
            {
                "tipo": "table",
                "titulo": "Logro por Alumno - {curso}",
                "fn": "tabla_logro_por_alumno",
                "df_input": "estudiantes_prueba",
                "params": {
                    "parametros": {"Curso": "{curso}"},
                    "sort_by": "Rend",
                    "formatos": {
                        "Rend": "percent",
                        "Simce": "number",
                        "Logro_Promedio_Estudiante": "percent",
                        "Avance": "percent",
                        "Mejora_vs_Inicio": "percent",
                    },
                    "columnas": [
                        "Nombre", "Rend", "Simce", "Logro",
                        "Logro_Promedio_Estudiante", "Avance", "Mejora_vs_Inicio",
                    ],
                    "columnas_renombrar": {
                        "Nombre": "Estudiante",
                        "Rend": "Logro",
                        "Simce": "SIMCE",
                        "Logro": "Nivel",
                        "Logro_Promedio_Estudiante": "Promedio Año",
                        "Avance": "Avance",
                        "Mejora_vs_Inicio": "Mejora",
                    },
                },
            },
            {
                "tipo": "table",
                "titulo": "Logro por Pregunta - {curso}",
                "fn": "tabla_logro_por_pregunta",
                "df_input": "preguntas_prueba",
                "params": {
                    "valor_agrupacion": "{curso}",
                    "agrupar_por": "Curso",
                    "sort_by": "Logro",
                    "columnas": ["Pregunta", "Habilidad", "Eje Temático", "Logro"],
                    "columnas_renombrar": {"Pregunta": "N° Pregunta"},
                },
            },
        ],
        df_iterar="estudiantes_prueba",
        iterar_por="Curso",
    )


def _secciones_evolucion(
    dataframes: dict,
    columna_temporal: Optional[str],
    niveles: Optional[list[str]] = None,
    colores: Optional[dict] = None,
) -> list[dict]:
    """Secciones 10-12 de los modos histórico, auto-omitidas con 1 punto."""
    df = dataframes.get("estudiantes_periodo")
    niveles = list(niveles or NIVELES_SIMCE)
    bloque: list[dict] = []
    bloque += sec.seccion_evolucion(
        _seccion_chart(
            "Evolución del Logro Promedio por Curso y Mes",
            "valor_promedio_agrupado_por", "estudiantes_periodo",
            {
                "columna_valor": "Rend",
                "agrupar_principal_por": "Curso",
                "agrupar_secundario_por": columna_temporal or "Mes",
                "titulo_grafico": "Evolución del Logro Promedio por Curso y Mes",
                "titulo_leyenda": columna_temporal or "Mes",
                "y_lims": [0, 1],
                "formato": "percent",
            },
        ),
        df, columna_temporal,
    )
    bloque += sec.seccion_evolucion(
        _seccion_chart(
            "Evolución del Puntaje SIMCE Promedio por Curso y Mes",
            "valor_promedio_agrupado_por", "estudiantes_periodo",
            {
                "columna_valor": "Simce",
                "agrupar_principal_por": "Curso",
                "agrupar_secundario_por": columna_temporal or "Mes",
                "titulo_grafico": "Evolución del Puntaje SIMCE Promedio por Curso y Mes",
                "titulo_leyenda": columna_temporal or "Mes",
                "formato": "number",
            },
        ),
        df, columna_temporal,
    )
    bloque += sec.seccion_evolucion(
        _seccion_chart(
            "Evolución de Niveles por Curso y Mes",
            "alumnos_por_nivel_curso_y_mes", "estudiantes_periodo",
            {
                "columna_nivel": "Logro",
                "columna_curso": "Curso",
                "columna_mes": columna_temporal or "Mes",
                # De PEOR a MEJOR: el peor queda en la base del stack.
                "lista_niveles": list(reversed(niveles)),
                "color_overrides": dict(colores or {}),
                "orden_meses": None,
                "titulo_grafico": "Evolución de Niveles por Curso y Mes",
                "titulo_leyenda": "Nivel de Logro",
                "ylabel": "Cantidad de Alumnos",
            },
        ),
        df, columna_temporal,
    )

    if not bloque:
        return [{
            "tipo": "nota",
            "titulo": "Evolución del período",
            "texto": _NOTA_SIN_EVOLUCION,
        }]
    return bloque


def _secciones(
    modo: str,
    dataframes: dict,
    *,
    niveles: Optional[list[str]] = None,
    colores: Optional[dict] = None,
    columna_temporal: Optional[str] = None,
    etiqueta_actual: str = "",
    etiqueta_previa: str = "",
    riesgo: Optional[sec.RiesgoPersistente] = None,
) -> tuple[list[dict], dict]:
    """(secciones_fijas, secciones_dinamicas) del modo pedido.

    Es la función que testean los smokes de `tests/reports/test_simce_modos.py`:
    permite verificar títulos, orden, `fn` y `df_input` sin renderizar PDF
    (WeasyPrint no está en todos los hosts).

    `riesgo` es el resultado de `_secciones.riesgo_persistente`. Sin él se
    reconstruye desde las tablas ya publicadas en `dataframes` (queda sin
    la descripción de la última evaluación, que no es un DataFrame).
    """
    if modo not in MODOS_SOPORTADOS:
        raise ValueError(
            f"El informe SIMCE no genera el modo '{modo}'. "
            f"Modos disponibles: {', '.join(MODOS_SOPORTADOS)}."
        )

    niveles = list(niveles or NIVELES_SIMCE)
    colores = dict(colores or {})
    es_ultima = modo == "ultima_prueba"
    df_est = "estudiantes_prueba" if es_ultima else "estudiantes_periodo"
    df_preg = "preguntas_prueba" if es_ultima else "preguntas_periodo"

    if es_ultima:
        primera = [sec.seccion_resumen(
            df_est, columna="Rend", formato="percent",
            titulo="Resumen de Logro por Curso",
        )]
    else:
        primera = [sec.seccion_resumen_comparado(
            "resumen_logro_comparado",
            titulo=(
                f"Resumen de Logro por Curso (vs {etiqueta_previa})"
                if etiqueta_previa else "Resumen de Logro por Curso"
            ),
        )]

    fijas = primera + _secciones_comunes(df_est, df_preg, niveles, colores)

    if es_ultima:
        fijas += _secciones_detalle_ultima_prueba()
        return fijas, _secciones_dinamicas_por_curso()

    fijas += _secciones_evolucion(dataframes, columna_temporal, niveles, colores)

    if modo in ("anual", "personalizado"):
        fijas += sec.secciones_riesgo_persistente(
            riesgo if riesgo is not None else _riesgo_desde_dataframes(dataframes),
            texto_sin_datos=_NOTA_SIN_RIESGO_PERSISTENTE,
            nivel_objetivo=NIVEL_RIESGO,
            n_evaluaciones=N_EVALUACIONES_RIESGO,
        )

    return fijas, {}


def _riesgo_desde_dataframes(dataframes: dict) -> sec.RiesgoPersistente:
    """Reconstruye el resultado del riesgo desde las tablas publicadas."""
    def _df(key: str) -> pd.DataFrame:
        valor = dataframes.get(key)
        return valor if valor is not None else pd.DataFrame()

    return sec.RiesgoPersistente(
        vigentes=_df("riesgo_persistente"),
        sin_evaluacion_reciente=_df("riesgo_sin_evaluacion_reciente"),
    )


# ─────────────────────────────────────────────────────────────────────────
# Construcción del PDF por modo
# ─────────────────────────────────────────────────────────────────────────

def _generar_por_modo(
    db: Session,
    *,
    indicator_id: int,
    org_id: int,
    modo: str,
    filtros: dict[str, Any] | None,
    params: dict[str, Any] | None,
    overrides: dict[str, Any] | None,
) -> bytes:
    from backend.models import Indicator

    from .. import runtime

    preparado = _preparar_dataframes(
        db, indicator_id=indicator_id, org_id=org_id, modo=modo, filtros=filtros
    )
    dataframes = preparado["dataframes"]
    columna_temporal = preparado["columna_temporal"]

    indicador = (
        db.query(Indicator)
        .filter(Indicator.id_indicator == indicator_id, Indicator.org_id == org_id)
        .first()
    )
    niveles, colores = _niveles_y_colores(
        getattr(indicador, "achievement_levels", None)
    )

    # Tablas que el módulo calcula en Python y publica como df_input.
    if modo != "ultima_prueba":
        dataframes["resumen_logro_comparado"] = sec.tabla_resumen_comparado(
            dataframes["estudiantes_periodo"],
            dataframes["estudiantes_previo"],
            columna="Rend",
            etiqueta_actual=(
                f"Promedio {preparado['etiqueta_actual']}".strip()
                if preparado["etiqueta_actual"] else "Promedio"
            ),
            etiqueta_previo=(
                f"Promedio {preparado['etiqueta_previa']}".strip()
                if preparado["etiqueta_previa"] else "Período anterior"
            ),
            formato="percent",
        )
    riesgo: Optional[sec.RiesgoPersistente] = None
    if modo in ("anual", "personalizado"):
        riesgo = sec.riesgo_persistente(
            dataframes["estudiantes_periodo"],
            columna_nivel="Logro",
            nivel_objetivo=NIVEL_RIESGO,
            columna_temporal=columna_temporal or "Mes",
            n_evaluaciones=N_EVALUACIONES_RIESGO,
            columnas_puntaje=["Rend", "Simce"],
            formatos={"Rend": "percent", "Simce": "number"},
        )
        dataframes["riesgo_persistente"] = riesgo.vigentes
        dataframes["riesgo_sin_evaluacion_reciente"] = riesgo.sin_evaluacion_reciente

    fijas, dinamicas = _secciones(
        modo, dataframes,
        niveles=niveles, colores=colores,
        columna_temporal=columna_temporal,
        etiqueta_actual=preparado["etiqueta_actual"],
        etiqueta_previa=preparado["etiqueta_previa"],
        riesgo=riesgo,
    )

    df_principal = (
        "estudiantes_prueba" if modo == "ultima_prueba" else "estudiantes_periodo"
    )
    # FUENTE ÚNICA del período (QA 2026-07-30, P1-1): manda la descripción
    # que resolvió `periodos.py` y que inyecta el despacho. El cálculo
    # propio queda de FALLBACK para la invocación directa del módulo (sin
    # router), donde nadie la provee.
    periodo_desc = str((params or {}).get("periodo_desc") or "").strip()
    if not periodo_desc:
        periodo_desc = _descripcion_periodo(preparado, modo)

    esquema = {
        **sec.bloque_titulo(
            titulo=TITULO,
            establecimiento=preparado["establecimiento"],
            asignatura=preparado["asignatura"],
            periodo_desc=periodo_desc,
        ),
        "branding": _branding_base(),
        "secciones_fijas": fijas,
        "secciones_dinamicas": dinamicas,
    }

    # El pie izquierdo SIEMPRE es la organización (regla dura del README) y
    # el encabezado central lleva las líneas reales de la corrida cuando el
    # llamador no mandó uno propio.
    overrides = aplicar_pie_organizacion(db, org_id, overrides)
    overrides = aplicar_center_header(
        overrides,
        base=(esquema.get("branding") or {}).get("center_header") or [TITULO],
        lineas=_lineas_encabezado(preparado, dataframes[df_principal], modo, periodo_desc),
    )

    return runtime.construir_pdf(
        "simce",
        dataframes,
        overrides=overrides,
        df_principal=df_principal,
        filtros_desc=formatear_filtros(preparado["filtros_efectivos"]),
        esquema=esquema,
    )


def _lineas_encabezado(
    preparado: dict, df_principal: pd.DataFrame, modo: str, periodo_desc: str
) -> list[str]:
    """Líneas 2 y 3 del encabezado corrido.

    La ÚLTIMA línea es siempre `periodo_desc` — la misma cadena que va al
    bloque de título. Es lo que garantiza que la primera página y el
    encabezado de las páginas siguientes no puedan contradecirse (QA
    2026-07-30, P1-1).
    """
    if modo == "ultima_prueba":
        lineas = list(
            lineas_encabezado_prueba(df_principal, preparado["asignatura"], None, None)
        )
    else:
        lineas = [str(preparado["asignatura"] or "").strip(), periodo_desc]

    if periodo_desc:
        lineas = (lineas[:-1] if lineas else []) + [periodo_desc]
    return lineas


def _descripcion_periodo(preparado: dict, modo: str) -> str:
    """FALLBACK del texto del período ('MAYO 2026', '2025').

    Solo se usa cuando el llamador NO inyectó `params["periodo_desc"]`, es
    decir en la invocación directa del módulo. Por el despacho normal manda
    siempre la descripción de `periodos.ResultadoPeriodo`, que es la misma
    que va al encabezado corrido: tener dos fuentes hacía que en
    `personalizado` el título dijera "2025" y el encabezado
    "ENERO 2025 – JULIO 2025" (QA 2026-07-30, P1-1).
    """
    if modo == "ultima_prueba":
        cols = preparado["columnas_temporales"]
        df = preparado["dataframes"]["estudiantes_prueba"]
        valores = {
            col: valor_unico(df, col)
            for col in (cols.get("mes_like"), cols.get("anio"), cols.get("ordinal"))
            if col
        }
        return periodos._describir_evaluacion(valores, cols)
    etiqueta = preparado["etiqueta_actual"]
    return etiqueta or formatear_filtros(preparado["temporales"])
