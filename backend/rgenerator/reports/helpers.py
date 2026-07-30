"""Utilidades comunes del motor PDF v2.

- df_a_html_table: equivalente HTML del df_a_latex_loop. Detecta columnas
  numéricas / porcentajes y alinea a derecha; texto a izquierda. Headers en
  bold. Bordes negros 0.5pt vía la clase CSS `report-table` del template.
- embed_png_b64: lee un PNG de disco y devuelve `data:image/png;base64,...`
  para embeberlo inline en el HTML (evita paths absolutos en WeasyPrint).
- format_curso_corto: "I A (TPI-510)" → "I A".

Además concentra tres utilidades transversales que charts.py y tables.py
comparten (hallazgos del QA visual 2026-07-30):

- Ausencia de dato (`MARCA_SIN_DATO`, `es_sin_dato`, `texto_celda`,
  `formatear_valor`): ningún informe debe mostrar el literal `nan` ni
  `nan%`. La regla es formatear DESPUÉS de decidir si hay valor.
- Identidad del estudiante (`serie_identidad_estudiante`,
  `contar_estudiantes`): los conteos de "alumnos" cuentan estudiantes
  distintos, no filas — un df por-pregunta o por-subprueba tiene varias
  filas por estudiante.
- Orden cronológico (`ordenar_valores_temporales`): los ejes temporales se
  ordenan con la semántica real (meses en español, hitos DIA, versiones
  IDEL, N° Prueba, Año), no alfabéticamente.
"""
from __future__ import annotations

import base64
import re
import unicodedata
from html import escape as html_escape
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

# `periodos` es la fuente de verdad de la semántica temporal del proyecto
# (MESES_A_NUMERO, HITO_A_MES, VERSION_A_MES). Solo se lee.
from .periodos import a_numero_mes


# ─────────────────────────────────────────────────────────────────────────
# Normalización de nombres de columna
# ─────────────────────────────────────────────────────────────────────────

def _norm(nombre: Any) -> str:
    """'Nombre_Norm' → 'nombre norm'. Sin tildes, minúsculas, tokens por espacio."""
    s = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


# ─────────────────────────────────────────────────────────────────────────
# Ausencia de dato
# ─────────────────────────────────────────────────────────────────────────

#: Texto visible cuando un valor no existe. Convención heredada del informe
#: PDL IDEL, que el QA 2026-07-30 marcó como referente.
MARCA_SIN_DATO = "—"

# Literales que aparecen cuando un NaN ya fue convertido a texto antes de
# llegar acá: `f"{float('nan'):.0%}"` → "nan%", `str(pd.NaT)` → "NaT".
_RE_SIN_DATO = re.compile(
    r"^\s*[-+]?(?:nan|nat|none|null|<na>|inf|infinity)\s*[%‰]?\s*$",
    re.IGNORECASE,
)


def es_sin_dato(valor: Any) -> bool:
    """True si `valor` representa ausencia de dato.

    Cubre None, NaN/NaT de pandas, el string vacío y los literales que
    quedan cuando un NaN se formateó antes de tiempo ("nan", "nan%",
    "NaT", "None").
    """
    if valor is None:
        return True
    try:
        if pd.isna(valor):
            return True
    except (TypeError, ValueError):
        # Arrays / listas: pd.isna devuelve un array → ambiguo. No es NaN.
        pass
    if isinstance(valor, str):
        return not valor.strip() or bool(_RE_SIN_DATO.match(valor))
    return False


def texto_celda(valor: Any) -> str:
    """Texto visible de un valor de celda. Ausencia de dato → `—`."""
    if es_sin_dato(valor):
        return MARCA_SIN_DATO
    return str(valor)


def formatear_valor(valor: Any, formato: str = "number", decimales: int | None = None) -> str:
    """Formatea un número decidiendo PRIMERO si hay dato.

    Args:
        valor: valor a formatear.
        formato: "percent" (×100 con %), "number" (entero), "decimal"
            (1 decimal) o cualquier spec de `format()` (ej ".2f").
        decimales: sobreescribe los decimales del formato.

    Returns:
        String formateado, o `MARCA_SIN_DATO` si no hay valor. Nunca
        devuelve "nan" ni "nan%".
    """
    if es_sin_dato(valor):
        return MARCA_SIN_DATO
    try:
        num = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    if formato == "percent":
        return f"{num:.{0 if decimales is None else decimales}%}"
    if formato == "number":
        return f"{num:.{0 if decimales is None else decimales}f}"
    if formato == "decimal":
        return f"{num:.{1 if decimales is None else decimales}f}"
    try:
        return format(num, formato)
    except (TypeError, ValueError):
        return str(valor)


def formatear_serie(serie: pd.Series, formato: str = "number",
                    decimales: int | None = None) -> pd.Series:
    """`formatear_valor` aplicado a una Series (devuelve Series de strings)."""
    return serie.map(lambda v: formatear_valor(v, formato, decimales))


# ─────────────────────────────────────────────────────────────────────────
# Identidad del estudiante
# ─────────────────────────────────────────────────────────────────────────

# Prioridad de columnas para identificar a un estudiante. Un grupo = un
# nivel de prioridad; dentro del grupo gana el primer patrón que exista.
# Las cargas del indicador DIA traen `Nombre` en 2025 y `Nombre_Norm` en
# 2026 (ninguna trae ambas), así que la identidad se resuelve por coalesce
# entre grupos, no eligiendo una sola columna (P0-3 del QA 2026-07-30).
_GRUPOS_IDENTIDAD: tuple[tuple[str, ...], ...] = (
    ("rut", "run", "rut alumno", "rut estudiante", "rut del estudiante"),
    ("nombre norm", "nombre normalizado"),
    ("nombre", "estudiante", "alumno", "nombre alumno", "nombre estudiante",
     "nombre completo"),
)

# Grupos que sirven como NOMBRE visible (el RUT no se muestra en la columna
# "Estudiante").
_GRUPOS_NOMBRE: tuple[tuple[str, ...], ...] = _GRUPOS_IDENTIDAD[1:]

_PATRONES_LISTA = ("n lista", "no lista", "nro lista", "num lista", "numero lista",
                   "n de lista", "numero de lista")


def _columnas_de_grupos(df: pd.DataFrame,
                        grupos: Iterable[Iterable[str]]) -> list[str]:
    """Columnas del df que matchean `grupos`, en orden de prioridad."""
    por_norm: dict[str, str] = {}
    for c in df.columns:
        por_norm.setdefault(_norm(c), c)
    out: list[str] = []
    for grupo in grupos:
        for patron in grupo:
            col = por_norm.get(patron)
            if col is not None and col not in out:
                out.append(col)
                break
    return out


def columnas_identidad_estudiante(df: pd.DataFrame) -> list[str]:
    """Columnas que identifican al estudiante, de mayor a menor prioridad.

    Orden: RUT → Nombre_Norm → Nombre/Estudiante/Alumno.
    """
    return _columnas_de_grupos(df, _GRUPOS_IDENTIDAD)


def columnas_nombre_estudiante(df: pd.DataFrame) -> list[str]:
    """Columnas usables como NOMBRE visible del estudiante (sin RUT)."""
    return _columnas_de_grupos(df, _GRUPOS_NOMBRE)


def _columnas_lista_curso(df: pd.DataFrame) -> tuple[str, str] | None:
    """(columna N° Lista, columna Curso) si ambas existen. Clave compuesta."""
    por_norm: dict[str, str] = {}
    for c in df.columns:
        por_norm.setdefault(_norm(c), c)
    col_lista = next((por_norm[p] for p in _PATRONES_LISTA if p in por_norm), None)
    col_curso = por_norm.get("curso")
    if col_lista and col_curso:
        return (col_lista, col_curso)
    return None


def _serie_texto(serie: pd.Series) -> pd.Series:
    """Serie de strings limpios; ausencia de dato → pd.NA."""
    return serie.map(lambda v: pd.NA if es_sin_dato(v) else str(v).strip())


def _rellenar_faltantes(ident: pd.Series, index: pd.Index) -> pd.Series:
    """Asigna un valor único a las filas sin identidad.

    Así el conteo degrada al número de filas (comportamiento anterior) en
    vez de perder registros, en lugar de contarlos todos como uno solo.
    """
    faltan = ident.isna()
    if faltan.any():
        ident = ident.copy()
        ident.loc[faltan] = [f"__fila_{i}" for i in index[faltan]]
    return ident


def serie_identidad_estudiante(df: pd.DataFrame) -> pd.Series | None:
    """Serie con la mejor identidad disponible por fila (coalesce).

    Recorre las columnas de identidad en orden de prioridad rellenando los
    nulos con la siguiente; si nada aplica prueba con (Curso, N° Lista).
    Las filas sin ninguna clave reciben un identificador único.

    Returns:
        Series alineada al índice del df, o None si el df no tiene ninguna
        columna de identidad (el caller decide si degrada a contar filas).
    """
    cols = columnas_identidad_estudiante(df)
    compuesta = _columnas_lista_curso(df)
    if not cols and not compuesta:
        return None

    ident = pd.Series(pd.NA, index=df.index, dtype="object")
    for col in cols:
        ident = ident.where(ident.notna(), _serie_texto(df[col]))
    if compuesta:
        col_lista, col_curso = compuesta
        lista = _serie_texto(df[col_lista])
        curso = _serie_texto(df[col_curso])
        combinada = pd.Series(
            [
                f"{c}#{l}" if (not pd.isna(c) and not pd.isna(l)) else pd.NA
                for c, l in zip(curso, lista)
            ],
            index=df.index,
            dtype="object",
        )
        ident = ident.where(ident.notna(), combinada)

    return _rellenar_faltantes(ident, df.index)


def contar_estudiantes(
    df: pd.DataFrame,
    agrupar_por: str | Sequence[str] | None = None,
    columna_identidad: str | None = None,
):
    """Cantidad de estudiantes DISTINTOS (no de filas).

    Args:
        df: DataFrame de entrada.
        agrupar_por: columna (o lista de columnas) por la que agrupar. None
            devuelve el total.
        columna_identidad: fuerza la columna de identidad. Si no se pasa se
            autodetecta con `serie_identidad_estudiante`.

    Returns:
        `int` si `agrupar_por` es None; si no, `pd.Series` indexada por el
        grupo. Si el df no tiene ninguna clave de identidad se degrada al
        conteo de filas (comportamiento histórico), que es correcto cuando
        hay una fila por estudiante.
    """
    if columna_identidad and columna_identidad in df.columns:
        ident = _rellenar_faltantes(_serie_texto(df[columna_identidad]), df.index)
    else:
        ident = serie_identidad_estudiante(df)

    if ident is None:
        if agrupar_por is None:
            return len(df)
        return df.groupby(agrupar_por, observed=False).size()

    if agrupar_por is None:
        return int(ident.nunique())

    if isinstance(agrupar_por, (list, tuple)):
        claves: Any = [df[c] for c in agrupar_por]
    else:
        claves = df[agrupar_por]
    return ident.groupby(claves, observed=False).nunique()


def coalescer_nombre_estudiante(df: pd.DataFrame, columna: str) -> pd.DataFrame:
    """Rellena los nulos de `columna` con las otras columnas de nombre.

    Mitigación de PRESENTACIÓN para el informe DIA: la carga 2026 dejó
    `Nombre` nulo con `Nombre_Norm` poblado y la de 2025 al revés, así que
    la columna "Estudiante" salía `nan` en ~60 de 67 páginas (P0-3 del QA
    2026-07-30). El problema de datos de fondo no se arregla acá.

    Returns:
        El mismo df si no había nada que rellenar; una copia si sí.
    """
    if columna not in df.columns:
        return df
    faltan = df[columna].map(es_sin_dato)
    if not faltan.any():
        return df

    alternativas = [c for c in columnas_nombre_estudiante(df) if c != columna]
    if not alternativas:
        return df

    out = df.copy()
    relleno = pd.Series(pd.NA, index=out.index, dtype="object")
    for alt in alternativas:
        relleno = relleno.where(relleno.notna(), _serie_texto(out[alt]))
    disponible = faltan & relleno.notna()
    if disponible.any():
        out.loc[disponible, columna] = relleno[disponible]
    return out


# ─────────────────────────────────────────────────────────────────────────
# Orden cronológico de ejes temporales
# ─────────────────────────────────────────────────────────────────────────

# Tokens que delatan una columna temporal. Alineados con `_TOKENS_MES_LIKE`
# / `_TOKENS_ORDINAL` / `_TOKENS_ANIO` de periodos.py.
_TOKENS_TEMPORALES = frozenset({
    "mes", "meses", "fecha", "fechas", "hito", "hitos", "version", "versiones",
    "prueba", "pruebas", "ensayo", "ensayos", "ano", "anos", "anio", "anios",
    "year", "years", "periodo", "periodos", "aplicacion", "aplicaciones",
    "semestre", "semestres", "trimestre", "trimestres", "eval", "evaluacion",
    "evaluaciones",
})

_RE_ANIO = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_RE_ENTERO = re.compile(r"\d+")
_SEPARADORES = " \t\r\n/-_.,;:·|()[]"


def es_columna_temporal(nombre: Any) -> bool:
    """True si el nombre de columna denota una dimensión temporal."""
    if nombre is None:
        return False
    return any(t in _TOKENS_TEMPORALES for t in _norm(nombre).split())


def clave_orden_temporal(valor: Any) -> tuple[int, float, str]:
    """Clave de orden cronológico de un valor de eje temporal.

    Devuelve `(año, posición_en_el_año, texto)`:

    - El año sale de un literal de 4 dígitos si está presente
      ("2024/v1" → 2024); si no, 0 (todos los valores comparten año).
    - La posición usa `periodos.a_numero_mes`, que entiende meses en
      español, hitos DIA (DIAGNOSTICO/INICIO → INTERMEDIO → CIERRE),
      versiones IDEL (v1 < v2 < v3) y fechas ISO. Si el valor no es
      interpretable como mes se usa el primer entero que aparezca
      (N° Prueba, "Ensayo 3") — así "3" y "13" quedan en orden numérico.
    - El texto rompe empates de forma estable.

    Ejemplos:
        >>> clave_orden_temporal("MAYO") < clave_orden_temporal("AGOSTO")
        True
        >>> clave_orden_temporal("DIAGNOSTICO") < clave_orden_temporal("CIERRE")
        True
        >>> clave_orden_temporal("2024/v2") < clave_orden_temporal("2025/v1")
        True
    """
    texto = "" if valor is None else str(valor).strip()

    m = _RE_ANIO.search(texto)
    if m:
        anio = int(m.group(0))
        resto = (texto[:m.start()] + " " + texto[m.end():]).strip(_SEPARADORES)
    else:
        anio, resto = 0, texto.strip(_SEPARADORES)

    posicion = a_numero_mes(resto) if resto else None
    if posicion is None:
        # Fecha completa ("2025-11-04"): el año ya se extrajo, el mes solo
        # se recupera leyendo el valor entero.
        posicion = a_numero_mes(texto)
    if posicion is None:
        m2 = _RE_ENTERO.search(resto)
        posicion = int(m2.group(0)) if m2 else 0

    return (anio, float(posicion), texto.upper())


def _es_numero(texto: str) -> bool:
    try:
        float(texto)
    except (TypeError, ValueError):
        return False
    return True


def valores_parecen_temporales(valores: Iterable[Any]) -> bool:
    """True si los valores se leen como períodos aun sin conocer la columna.

    Exige que al menos uno sea textual (para no confundir cursos numéricos)
    y que TODOS aporten año o posición. Es solo el fallback de
    `ordenar_valores_temporales` cuando no se pasa el nombre de columna.
    """
    hay_texto = False
    for v in valores:
        texto = str(v).strip()
        if not texto:
            return False
        if not _es_numero(texto):
            hay_texto = True
        anio, posicion, _ = clave_orden_temporal(texto)
        if anio == 0 and posicion == 0:
            return False
    return hay_texto


def ordenar_valores_temporales(
    valores: Iterable[Any],
    nombre_columna: Any = None,
) -> list:
    """Ordena `valores` cronológicamente si el eje es temporal.

    Si el eje no es temporal devuelve los valores tal como vinieron — el
    orden de un eje categórico lo decide el caller (o el esquema).

    Args:
        valores: valores únicos del eje.
        nombre_columna: nombre de la columna de origen. Cuando denota
            tiempo (Mes, Fecha, Hito, Versión, N° Prueba, Año…) el orden
            cronológico se aplica siempre.

    Returns:
        Lista ordenada (o la original si el eje no es temporal).
    """
    vals = list(valores)
    if len(vals) < 2:
        return vals
    if not (es_columna_temporal(nombre_columna) or valores_parecen_temporales(vals)):
        return vals
    return sorted(vals, key=clave_orden_temporal)


# ─────────────────────────────────────────────────────────────────────────
# Render de tablas
# ─────────────────────────────────────────────────────────────────────────

def df_a_html_table(df: pd.DataFrame, css_class: str = "report-table") -> str:
    """Convierte DataFrame → HTML <table> con alineación smart.

    - Columnas numéricas o que terminen en % → texto alineado a derecha.
    - Otras columnas → alineado a izquierda.
    - Headers en bold (vía CSS de la clase `report-table`).
    - Ausencia de dato (NaN, None, NaT y los literales "nan" / "nan%" que
      deja un formateo prematuro) → `—`. Nunca se imprime "nan".
    - Sin zebra. Bordes negros 0.5pt.

    Args:
        df: DataFrame a renderizar.
        css_class: clase CSS de la tabla. Default "report-table" (definida
            en templates/informe_base.html).

    Returns:
        HTML string.

    Equivalente LaTeX: df_a_latex_loop (en SIMCE/DIA funciones.py).
    """
    cols = df.columns.tolist()

    # Detectar columnas numéricas / porcentajes (igual que df_a_latex_loop).
    # `notnull().all()` se relaja a "hay al menos un número y ningún texto
    # no numérico" para que una columna con faltantes siga alineada a la
    # derecha en vez de degradar a texto.
    def _es_numerica(serie: pd.Series) -> bool:
        num = pd.to_numeric(serie, errors="coerce")
        sin_dato = serie.map(es_sin_dato)
        return bool(num.notnull().any() and (num.notnull() | sin_dato).all())

    numeric_cols_mask = [_es_numerica(df[c]) for c in cols]
    percent_cols_mask = [
        bool(df[c].map(lambda v: isinstance(v, str) and v.strip().endswith("%")).any())
        for c in cols
    ]
    is_numeric = [n or p for n, p in zip(numeric_cols_mask, percent_cols_mask)]

    # Render
    parts = [f'<table class="{css_class}">']

    # Header
    parts.append("<thead><tr>")
    for c, num in zip(cols, is_numeric):
        align_class = "al-right" if num else "al-left"
        parts.append(f'<th class="{align_class}">{html_escape(str(c))}</th>')
    parts.append("</tr></thead>")

    # Body
    parts.append("<tbody>")
    for _, row in df.iterrows():
        parts.append("<tr>")
        for val, num in zip(row.values, is_numeric):
            align_class = "al-right" if num else "al-left"
            parts.append(f'<td class="{align_class}">{html_escape(texto_celda(val))}</td>')
        parts.append("</tr>")
    parts.append("</tbody></table>")

    return "".join(parts)


def embed_png_b64(path: str | Path) -> str:
    """Lee un PNG de disco y devuelve data URI base64.

    Args:
        path: ruta al PNG.

    Returns:
        String "data:image/png;base64,iVBORw0KGgo..." apto para
        usar como `<img src="...">` en HTML.
    """
    p = Path(path)
    with open(p, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


def format_curso_corto(curso: str) -> str:
    """Limpia "I A (TPI-510)" → "I A". Útil para etiquetas de eje X.

    Args:
        curso: nombre completo del curso.

    Returns:
        Nombre sin texto entre paréntesis.
    """
    if not isinstance(curso, str):
        return str(curso)
    return curso.split(" (")[0]
