"""Branding y etiquetas legibles de los informes (compartido v1 + v2).

Tres responsabilidades, todas transversales a los dos motores de PDF:

1. **Pie izquierdo** — debe identificar a la ORGANIZACIÓN dueña de los
   datos, nunca al desarrollador. Los layouts persistidos en
   `indicators.pdf_layout` arrastran valores legacy (ver
   `LEFT_FOOTER_DENYLIST`); `pie_saneado` los degrada a vacío para que el
   runtime caiga al nombre de la org.

2. **Encabezado central** — el `center_header` del esquema trae el NOMBRE
   del informe; las líneas de asignatura/período las construye el
   `crear_informe` de cada tipo con los params reales de la corrida
   (`aplicar_center_header`). Nunca se dejan literales tipo
   "Asignatura - Curso" o "Mes Año" en el JSON: salen impresos tal cual.

3. **Etiqueta de filtros** — los filtros llegan como escalares o listas;
   `formatear_filtros` los pasa a texto legible en vez del `repr` de
   Python ("Mes: ['MAYO']" → "Mes: MAYO").

Todas las funciones son PURAS (no tocan DB ni filesystem).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Mapping, Optional, Sequence


# ─────────────────────────────────────────────────────────────────────────
# Pie izquierdo
# ─────────────────────────────────────────────────────────────────────────

# Nombres personales que aparecieron hardcodeados en layouts persistidos
# (`indicators.pdf_layout` / `pdf_layout_historico`) de todas las orgs. El
# QA visual 2026-07-30 los encontró en el pie de los 12 informes por
# período. Se tratan como "sin valor" para que el runtime resuelva el
# nombre de la organización.
#
# Complementa (no reemplaza) a `tests/regresion/test_branding_sin_nombre_personal.py`,
# que audita los esquemas .json del repo: esta denylist cubre los layouts
# que viven en la DB, donde el test no llega.
LEFT_FOOTER_DENYLIST: tuple[str, ...] = (
    "Miguel Godoy Díaz",
    "Miguel Godoy",
)


def _plano(texto: Any) -> str:
    """Normaliza para comparar: sin tildes, sin espacios extra, minúsculas."""
    s = unicodedata.normalize("NFKD", str(texto or ""))
    s = s.encode("ascii", "ignore").decode("ascii")
    return " ".join(s.split()).casefold()


_DENYLIST_PLANA = frozenset(_plano(v) for v in LEFT_FOOTER_DENYLIST)


def es_pie_denegado(valor: Any) -> bool:
    """True si `valor` es uno de los pies legacy de `LEFT_FOOTER_DENYLIST`.

    La comparación ignora tildes, mayúsculas y espacios repetidos.

    Ejemplo:
        >>> es_pie_denegado("Miguel Godoy Díaz")
        True
        >>> es_pie_denegado("  miguel  godoy diaz ")
        True
        >>> es_pie_denegado("Fundación PHP")
        False
    """
    plano = _plano(valor)
    return bool(plano) and plano in _DENYLIST_PLANA


def pie_saneado(valor: Any) -> str:
    """Devuelve el pie izquierdo, o "" si es legacy/vacío.

    El "" es la señal que ya usan los dos motores para caer al nombre de
    la organización (`dispatch_v2.aplicar_pie_organizacion` en v2,
    `report_base.html` + `resolver_nombre_organizacion` en v1).
    """
    texto = str(valor or "").strip()
    if not texto or es_pie_denegado(texto):
        return ""
    return texto


# ─────────────────────────────────────────────────────────────────────────
# Etiqueta de filtros
# ─────────────────────────────────────────────────────────────────────────

_MEDIANOCHE = re.compile(r"^(\d{4}-\d{2}-\d{2})[ T]00:00:00(\.0+)?$")


def _escalar_legible(valor: Any) -> str:
    """Escalar → texto para mostrar. Recorta la medianoche de los timestamps.

    Las dimensiones de fecha se guardan como "2026-04-07 00:00:00"; la hora
    es ruido en un informe (QA 2026-07-30, P1-12).
    """
    texto = str(valor).strip()
    m = _MEDIANOCHE.match(texto)
    return m.group(1) if m else texto


def formatear_valor_filtro(valor: Any, max_items: int = 3) -> str:
    """Valor de filtro → texto legible (nunca el `repr` de una lista).

    Args:
        valor: escalar o iterable de valores.
        max_items: cuántos elementos se enumeran antes de resumir.

    Returns:
        "MAYO" · "MAYO, JUNIO" · "MAYO, JUNIO y 3 más".

    Ejemplo:
        >>> formatear_valor_filtro(["MAYO"])
        'MAYO'
        >>> formatear_valor_filtro(["1", "2", "3"])
        '1, 2 y 3'
        >>> formatear_valor_filtro(["A", "B", "C", "D", "E"])
        'A, B y 3 más'
        >>> formatear_valor_filtro("2026-04-07 00:00:00")
        '2026-04-07'
    """
    if valor is None:
        return ""
    if isinstance(valor, (str, bytes)):
        return _escalar_legible(valor)
    if isinstance(valor, Mapping):
        return formatear_filtros(valor)
    if isinstance(valor, Iterable):
        items = [_escalar_legible(v) for v in valor if str(v).strip() != ""]
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        if len(items) <= max_items:
            return f"{', '.join(items[:-1])} y {items[-1]}"
        resto = len(items) - max_items + 1
        return f"{', '.join(items[:max_items - 1])} y {resto} más"
    return str(valor).strip()


def formatear_filtros(filtros: Mapping[str, Any] | None, sep: str = " · ") -> str:
    """{"Mes": ["MAYO"], "Año": "2026"} → "Mes: MAYO · Año: 2026"."""
    partes = []
    for clave, valor in (filtros or {}).items():
        texto = formatear_valor_filtro(valor)
        if texto:
            partes.append(f"{clave}: {texto}")
    return sep.join(partes)


# ─────────────────────────────────────────────────────────────────────────
# Encabezado central
# ─────────────────────────────────────────────────────────────────────────

def _lineas_limpias(lineas: Optional[Sequence[Any]]) -> list[str]:
    """Lista de strings no vacíos (descarta None / "" / espacios)."""
    return [str(x).strip() for x in (lineas or []) if str(x or "").strip()]


def valor_unico(df: Any, columna: str) -> Optional[str]:
    """Único valor no nulo de `columna` en `df`, o None si hay 0 o >1.

    Se usa para construir las líneas del encabezado: si el informe cubre
    una sola asignatura/curso/mes se nombra; si mezcla varios se omite la
    línea en lugar de mentir. Duck-typing sobre el DataFrame para no
    acoplar este módulo a pandas.
    """
    columnas = getattr(df, "columns", None)
    if df is None or columnas is None or columna not in list(columnas):
        return None
    try:
        crudos = df[columna].dropna().unique().tolist()
    except Exception:  # pragma: no cover — defensivo ante dtypes raros
        return None
    valores = sorted({str(v).strip() for v in crudos if str(v).strip()})
    return valores[0] if len(valores) == 1 else None


def center_header_dinamico(
    base: Optional[Sequence[Any]],
    lineas: Optional[Sequence[Any]],
) -> list[str]:
    """Encabezado central = nombre del informe (del esquema) + líneas reales.

    Args:
        base: `branding.center_header` del esquema.json. Solo se conserva
            su PRIMERA línea (el nombre del informe); el resto histórico
            eran placeholders muertos ("Asignatura - Curso", "Mes Año").
        lineas: líneas construidas con los params de la corrida.

    Returns:
        Lista de líneas no vacías.

    Ejemplo:
        >>> center_header_dinamico(["Informe Ensayo SIMCE"], ["Lenguaje - II A", "MAYO 2026"])
        ['Informe Ensayo SIMCE', 'Lenguaje - II A', 'MAYO 2026']
    """
    base_limpia = _lineas_limpias(base)
    nombre = base_limpia[:1]
    return nombre + _lineas_limpias(lineas)


def aplicar_center_header(
    overrides: Optional[Mapping[str, Any]],
    base: Optional[Sequence[Any]],
    lineas: Optional[Sequence[Any]],
) -> dict[str, Any]:
    """Inyecta `branding.center_header` en `overrides` si el usuario no lo mandó.

    Un `center_header` explícito en los overrides SIEMPRE gana: es lo que
    el usuario configuró desde el modal de branding.

    Returns:
        Copia de `overrides` (nunca lo muta) con el header resuelto.
    """
    out = {k: v for k, v in (overrides or {}).items()}
    branding = dict(out.get("branding") or {})
    if _lineas_limpias(branding.get("center_header")):
        return out  # el usuario manda
    header = center_header_dinamico(base, lineas)
    if not header:
        return out
    branding["center_header"] = header
    out["branding"] = branding
    return out


def lineas_encabezado_prueba(
    df: Any,
    asignatura: Any = None,
    numero_prueba: Any = None,
    mes: Any = None,
) -> list[str]:
    """Líneas 2 y 3 del encabezado para un informe de UNA prueba (SIMCE).

    Reemplaza los literales muertos que traía `esquema.json`
    ("Asignatura - Curso", "Mes Año"), que salían impresos tal cual en
    todas las páginas (QA 2026-07-30, P0-11).

    Línea 2: "<Asignatura> - <Curso>" (el curso solo si el informe cubre
    uno solo). Línea 3: "<MES> <AÑO>", o "Prueba N° <n>" si no hay mes.

    Args:
        df: DataFrame ya filtrado a la prueba del informe.
        asignatura: asignatura del informe.
        numero_prueba: nº de prueba (fallback cuando no hay mes).
        mes: mes del informe; si es None se intenta deducir del df.
    """
    curso = valor_unico(df, "Curso")
    linea_asignatura = str(asignatura or "").strip()
    if curso:
        linea_asignatura = f"{linea_asignatura} - {curso}" if linea_asignatura else curso

    mes_efectivo = str(mes).strip() if mes else valor_unico(df, "Mes")
    anio = valor_unico(df, "Año")
    if mes_efectivo:
        linea_periodo = f"{mes_efectivo} {anio}".strip() if anio else mes_efectivo
    elif numero_prueba not in (None, ""):
        linea_periodo = f"Prueba N° {numero_prueba}"
        if anio:
            linea_periodo = f"{linea_periodo} · {anio}"
    else:
        linea_periodo = str(anio or "")

    return [linea_asignatura, linea_periodo]


def reemplazar_ultima_linea(
    center_header: Optional[Sequence[Any]],
    texto: str,
) -> list[str]:
    """Sustituye la última línea del encabezado por `texto`.

    Se usa en `export-pdf` con `periodo`: la última línea del layout es la
    del período y queda stale (el layout es configuración editable del
    usuario, el período lo resuelve el backend contra los datos). Las
    demás líneas NO se tocan.

    Devuelve [] si no hay encabezado configurado (no se inventa uno) y la
    lista sin cambios si `texto` viene vacío.

    Ejemplo:
        >>> reemplazar_ultima_linea(["Informe DIA", "Lectura", "Octubre 2025"], "DIAGNOSTICO 2026")
        ['Informe DIA', 'Lectura', 'DIAGNOSTICO 2026']
    """
    lineas = _lineas_limpias(center_header)
    if not lineas:
        return []
    nuevo = str(texto or "").strip()
    if not nuevo:
        return lineas
    if len(lineas) == 1:
        return [lineas[0], nuevo]
    return lineas[:-1] + [nuevo]
