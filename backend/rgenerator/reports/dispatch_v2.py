"""Despacho compartido del motor PDF v2 (simce / simce_panguipulli / dia).

Extraído de `backend/routers/reports.py::generar_reporte` para que el
endpoint legacy `POST /api/reports/{tipo}` y los informes del registro
`reports/custom/` usen EXACTAMENTE la misma lógica: validación de filtro
temporal, separación filtros estructurales/temporales, carga de
DataFrames y despacho al `crear_informe.construir` de cada tipo.

Contrato de errores (el router los traduce a HTTP):
    TipoNoSoportado  → 404
    DatosInsuficientes / ValueError → 400
    cualquier otra   → 500
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .branding import formatear_filtros, pie_saneado
from .data import cargar_dataframes_indicator
from .errores import DatosInsuficientes, TipoNoSoportado, mensaje_sin_datos


__all__ = [
    "TIPOS_V2",
    "FILTROS_TEMPORALES_V2",
    "TipoNoSoportado",
    "DatosInsuficientes",
    "validar_tipo",
    "separar_filtros",
    "aplicar_pie_organizacion",
    "generar_pdf_v2",
]


# Tipos que sirve el motor v2 (paridad LaTeX).
TIPOS_V2: tuple[str, ...] = ("simce", "simce_panguipulli", "dia")

# Dimensiones temporales aceptadas por tipo. Sin al menos una, el informe
# mezclaría meses/hitos distintos y los gráficos quedarían sucios.
FILTROS_TEMPORALES_V2: dict[str, list[str]] = {
    "simce": ["Mes", "N Prueba", "Numero_Prueba"],
    "simce_panguipulli": ["Mes", "N Prueba", "Numero_Prueba"],
    "dia": ["Hito", "Año"],
}


def validar_tipo(tipo: str) -> None:
    """Levanta `TipoNoSoportado` si `tipo` no lo sirve el motor v2."""
    if tipo not in TIPOS_V2:
        raise TipoNoSoportado(
            f"Tipo '{tipo}' no soportado. Disponibles: {', '.join(TIPOS_V2)}"
        )


def separar_filtros(tipo: str, filtros: dict[str, Any] | None) -> tuple[dict, dict]:
    """Separa los filtros en (estructurales, temporales) para `tipo`.

    Los estructurales van al loader (recortan el dataset antes de armar el
    DataFrame); los temporales van a `crear_informe.construir`, que los
    aplica DESPUÉS de las derived_fields para que slope/delta vean todo el
    histórico.

    Raises:
        DatosInsuficientes: si no hay ningún filtro temporal.
    """
    aplicados = filtros or {}
    requeridos = FILTROS_TEMPORALES_V2.get(tipo, [])
    if not any(k in aplicados for k in requeridos):
        raise DatosInsuficientes(
            f"El motor v2 requiere al menos un filtro temporal para mantener "
            f"un solo punto en el tiempo. Para '{tipo}', aplicar uno de: "
            f"{', '.join(requeridos)}."
        )
    temporales_set = set(requeridos)
    estructurales = {k: v for k, v in aplicados.items() if k not in temporales_set}
    temporales = {k: v for k, v in aplicados.items() if k in temporales_set}
    return estructurales, temporales


def aplicar_pie_organizacion(
    db: Session,
    org_id: int,
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    """Inyecta `branding.left_footer = org.name` si no viene definido.

    El pie izquierdo de todos los informes debe identificar a la
    organización dueña de los datos. Solo se rellena cuando el llamador no
    pidió un pie explícito (string no vacío) y ese pie no está en
    `branding.LEFT_FOOTER_DENYLIST`: los layouts legacy traían el nombre
    del desarrollador y el fallback nunca se activaba (QA 2026-07-30,
    P1-1).
    """
    from backend.models import Organization

    out = dict(overrides or {})
    branding = dict(out.get("branding") or {})
    pie = pie_saneado(branding.get("left_footer"))
    if not pie:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if org and org.name:
            pie = org.name
    if pie or "left_footer" in branding:
        branding["left_footer"] = pie
    if branding:
        out["branding"] = branding
    return out


def _entero_o(valor: Any, default: int) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return default


def generar_pdf_v2(
    db: Session,
    *,
    tipo: str,
    indicator_id: int,
    org_id: int,
    filtros: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> bytes:
    """Genera los bytes del PDF v2 para `tipo`.

    Args:
        db: sesión SQLAlchemy.
        tipo: "simce" | "simce_panguipulli" | "dia".
        indicator_id: indicador con las metrics asociadas.
        org_id: multi-tenancy.
        filtros: {nombre_columna: valor | [valores]} — debe incluir al
            menos un filtro temporal del tipo (ver `FILTROS_TEMPORALES_V2`).
        overrides: overrides del esquema (ej `{"branding": {...}}`).

    Returns:
        Bytes del PDF.

    Raises:
        TipoNoSoportado: tipo desconocido.
        DatosInsuficientes: falta filtro temporal, faltan metrics
            requeridas, o la combinación de filtros no tiene datos.
        ValueError: el indicador no existe / no tiene metrics (del loader).
    """
    from .dia import crear_informe as dia_informe
    from .simce import crear_informe as simce_informe
    from .simce_panguipulli import crear_informe as simce_panguipulli_informe

    validar_tipo(tipo)
    estructurales, temporales = separar_filtros(tipo, filtros)

    dataframes = cargar_dataframes_indicator(
        db,
        indicator_id=indicator_id,
        org_id=org_id,
        filtros=estructurales,
    )

    overrides = aplicar_pie_organizacion(db, org_id, overrides)

    df_estudiantes = dataframes.get("estudiantes", None)

    # Guardia temprana: los filtros ESTRUCTURALES ya vaciaron el dataset.
    # `data.py` omite la key del rol cuando la metric quedó sin filas, así
    # que "falta el df" puede significar dos cosas muy distintas; ver
    # `_error_por_datos`. Los filtros temporales los aplica cada
    # `crear_informe`, que vuelve a validar vía
    # `runtime.construir_pdf(df_principal=...)`.
    if df_estudiantes is not None and len(df_estudiantes) == 0:
        raise DatosInsuficientes(mensaje_sin_datos(formatear_filtros(estructurales)))

    def _error_por_datos(roles: list[str], mensaje_metrics: str) -> DatosInsuficientes:
        """Distingue "faltan metrics" de "los filtros vaciaron el dataset".

        Solo se ejecuta en el camino de error (termina en un 400), así que
        puede permitirse una recarga sin filtros para saber si las metrics
        existen de verdad.
        """
        if estructurales:
            sin_filtros = cargar_dataframes_indicator(
                db, indicator_id=indicator_id, org_id=org_id, filtros=None
            )
            if all(sin_filtros.get(r) is not None for r in roles):
                return DatosInsuficientes(
                    mensaje_sin_datos(formatear_filtros(estructurales))
                )
        return DatosInsuficientes(mensaje_metrics)

    if tipo == "simce":
        df_preguntas = dataframes.get("preguntas", None)
        if df_estudiantes is None or df_preguntas is None:
            raise _error_por_datos(
                ["estudiantes", "preguntas"],
                "El indicator debe tener metrics 'estudiantes' y 'preguntas' asociadas",
            )
        n_prueba_raw = temporales.get("N Prueba") or temporales.get("Numero_Prueba", 5)
        return simce_informe.construir(
            df_estudiantes,
            df_preguntas,
            asignatura=estructurales.get("Asignatura", "LENGUAJE"),
            numero_prueba=_entero_o(n_prueba_raw, 5),
            mes=temporales.get("Mes"),
            overrides=overrides,
        )

    if tipo == "simce_panguipulli":
        # Variante Panguipulli: usa df_estudiantes (metric 24) + df_habilidad
        # (metric 26) en lugar de df_preguntas. data.py asigna a metric 26 el
        # rol "otros" → key "metric_26"; acá se intentan varias keys conocidas.
        # No se usa `or` porque pandas no permite evaluar la verdad de un DF.
        df_habilidad = dataframes.get("habilidad")
        if df_habilidad is None:
            df_habilidad = dataframes.get("metric_26")
        if df_habilidad is None:
            df_habilidad = next(
                (v for k, v in dataframes.items() if k.startswith("metric_")),
                None,
            )
        if df_estudiantes is None or df_habilidad is None:
            raise _error_por_datos(
                ["estudiantes"],
                "El indicator SIMCE Panguipulli debe tener metrics 'por Estudiante' "
                "y 'por Habilidad' asociadas",
            )
        n_prueba_raw = temporales.get("N Prueba") or temporales.get("Numero_Prueba", 4)
        return simce_panguipulli_informe.construir(
            df_estudiantes,
            df_habilidad,
            asignatura=estructurales.get("Asignatura", "LENGUAJE"),
            numero_prueba=_entero_o(n_prueba_raw, 4),
            mes=temporales.get("Mes"),
            overrides=overrides,
        )

    # dia
    df_preguntas = dataframes.get("preguntas", None)
    if df_estudiantes is None or df_preguntas is None:
        raise _error_por_datos(
            ["estudiantes", "preguntas"],
            "El indicator DIA debe tener metrics 'estudiantes' y 'preguntas' asociadas",
        )
    return dia_informe.construir(
        df_estudiantes,
        df_preguntas,
        hito=temporales.get("Hito"),
        anio=temporales.get("Año"),
        overrides=overrides,
    )
