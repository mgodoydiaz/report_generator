"""Detección y validación de la dimensión "asignatura" de un indicador.

Un indicador puede traer datos de VARIAS asignaturas: el DIA de la
fundación carga LECTURA y MATEMATICA del mismo alumno en las mismas
metrics. Un informe, en cambio, es SIEMPRE de una asignatura: si se genera
sin fijarla, todo conteo de "alumnos" pasa a contar pares
alumno×asignatura y los promedios mezclan pruebas distintas.

Este módulo es la fuente ÚNICA de tres decisiones:

1. **Detección** — qué columna/dimensión del indicador es la asignatura
   (`dimension_asignatura`). Match por nombre normalizado (sin tildes, en
   minúsculas) que CONTENGA "asignatura", así entran "Asignatura",
   "asignatura_evaluada" o "ASIGNATURÁ".
2. **Requerimiento** — elegir asignatura es obligatorio solo si esa
   columna existe Y tiene ≥2 valores distintos en los datos del indicador
   (`requiere_seleccion` / `descriptor`). Con 0 o 1 valor no hay nada que
   preguntar y los informes de CV / FL / IDEL no se ven afectados.
3. **Validación** — los filtros efectivos deben fijarla a EXACTAMENTE un
   valor (`resolver_seleccion`); 0 ó >1 es `AsignaturaRequerida` → 400.

Todas las funciones son PURAS (no tocan DB ni filesystem) y el módulo no
importa pandas: los DataFrames se manejan por duck-typing (`.columns`).
"""
from __future__ import annotations

import unicodedata
from typing import Any, Iterable, Mapping, Optional, Sequence

from .errores import AsignaturaRequerida


__all__ = [
    "CLAVE_ASIGNATURA",
    "UMBRAL_REQUERIDA",
    "AsignaturaRequerida",
    "normalizar",
    "es_nombre_asignatura",
    "dimension_asignatura",
    "requiere_seleccion",
    "descriptor",
    "descriptor_de",
    "valores_en_filtros",
    "mensaje_seleccion_requerida",
    "resolver_seleccion",
    "filtrar_dataframes",
    "partir_filtros",
]


# Subcadena que identifica a la dimensión, ya normalizada.
CLAVE_ASIGNATURA = "asignatura"

# Cantidad de valores distintos desde la cual elegir asignatura es obligatorio.
UMBRAL_REQUERIDA = 2


# ─────────────────────────────────────────────────────────────────────────
# Normalización
# ─────────────────────────────────────────────────────────────────────────

def normalizar(texto: Any) -> str:
    """'Asignatúra Evaluada' → 'asignatura evaluada'. Sin tildes, minúsculas."""
    s = unicodedata.normalize("NFKD", str(texto or ""))
    s = s.encode("ascii", "ignore").decode("ascii")
    return " ".join(s.split()).casefold()


def es_nombre_asignatura(nombre: Any) -> bool:
    """True si `nombre` corresponde a la dimensión de asignatura.

    Ejemplo:
        >>> es_nombre_asignatura("Asignatura")
        True
        >>> es_nombre_asignatura("ASIGNATURÁ")
        True
        >>> es_nombre_asignatura("asignatura_evaluada")
        True
        >>> es_nombre_asignatura("Curso")
        False
    """
    return CLAVE_ASIGNATURA in normalizar(nombre).replace("_", " ")


def _valores_limpios(crudos: Any) -> list[str]:
    """Valores distintos, sin vacíos, ordenados alfabéticamente (case-insensitive)."""
    if crudos is None:
        return []
    if isinstance(crudos, (str, bytes)):
        crudos = [crudos]
    vistos: dict[str, str] = {}
    try:
        iterable = list(crudos)
    except TypeError:  # pragma: no cover — defensivo ante valores no iterables
        iterable = [crudos]
    for valor in iterable:
        texto = str(valor).strip()
        if not texto or texto.lower() in ("nan", "none"):
            continue
        vistos.setdefault(texto.casefold(), texto)
    return [vistos[k] for k in sorted(vistos)]


# ─────────────────────────────────────────────────────────────────────────
# Detección
# ─────────────────────────────────────────────────────────────────────────

def _es_dataframe(objeto: Any) -> bool:
    """Duck-typing: tiene `.columns` y no es un Mapping."""
    return hasattr(objeto, "columns") and not isinstance(objeto, Mapping)


def _columnas(df: Any) -> list[str]:
    """Nombres de columna de un DataFrame como lista de str.

    No se usa `getattr(df, "columns", None) or []`: el `or` evalúa la
    verdad de un `pd.Index` y pandas levanta ValueError.
    """
    columnas = getattr(df, "columns", None)
    if columnas is None:
        return []
    return [str(c) for c in columnas]


def _de_dataframe(df: Any) -> tuple[Optional[str], list[str]]:
    """(columna, valores) de la asignatura en UN DataFrame."""
    columna = next((c for c in _columnas(df) if es_nombre_asignatura(c)), None)
    if columna is None:
        return None, []
    try:
        crudos = df[columna].dropna().unique().tolist()
    except Exception:  # pragma: no cover — defensivo ante dtypes raros
        return columna, []
    return columna, _valores_limpios(crudos)


def _nombre_de(item: Any) -> Optional[str]:
    """Nombre de una dimensión venga como dict, string u objeto ORM."""
    if isinstance(item, Mapping):
        for clave in ("name", "nombre", "dimension"):
            if item.get(clave):
                return str(item[clave])
        return None
    if isinstance(item, (str, bytes)):
        return str(item)
    nombre = getattr(item, "name", None)
    return str(nombre) if nombre else None


def _valores_de(item: Any) -> list[str]:
    """Valores declarados de una dimensión (solo cuando viene como dict).

    Para objetos ORM no se toca `.values`: en `Dimension` es una relación
    lazy y leerla acá dispararía queries desde un módulo que debe ser puro.
    """
    if isinstance(item, Mapping):
        for clave in ("values", "valores"):
            if item.get(clave) is not None:
                return _valores_limpios(item[clave])
    return []


def dimension_asignatura(fuente: Any) -> tuple[Optional[str], list[str]]:
    """Detecta la dimensión de asignatura y sus valores distintos.

    Args:
        fuente: cualquiera de estas formas —
            - `{rol: DataFrame}` (salida de `cargar_dataframes_indicator`);
            - un DataFrame suelto;
            - `[{"name": ..., "values": [...]}, ...]` (el
              `dimensiones_filtrables` de report-options);
            - lista de nombres o de objetos con `.name` (los valores salen
              vacíos: solo se puede afirmar que la dimensión existe);
            - `{nombre_dimension: [valores]}`.

    Returns:
        `(nombre_columna, valores)`. `(None, [])` si no hay dimensión de
        asignatura. Los valores vienen sin duplicados ni vacíos y ordenados.

    Ejemplo:
        >>> dimension_asignatura([{"name": "Asignatura", "values": ["B", "a"]}])
        ('Asignatura', ['a', 'B'])
        >>> dimension_asignatura([{"name": "Curso", "values": ["II A"]}])
        (None, [])
    """
    if fuente is None:
        return None, []

    if _es_dataframe(fuente):
        return _de_dataframe(fuente)

    if isinstance(fuente, Mapping):
        # {rol: DataFrame} — acumula los valores de todos los DataFrames.
        columna: Optional[str] = None
        acumulados: list[str] = []
        hay_dataframes = False
        for valor in fuente.values():
            if not _es_dataframe(valor):
                continue
            hay_dataframes = True
            nombre, valores = _de_dataframe(valor)
            if nombre is not None:
                columna = columna or nombre
                acumulados.extend(valores)
        if hay_dataframes:
            return columna, _valores_limpios(acumulados)
        # {nombre_dimension: [valores]}
        for clave, valores in fuente.items():
            if es_nombre_asignatura(clave):
                return str(clave), _valores_limpios(valores)
        return None, []

    if isinstance(fuente, Sequence) or isinstance(fuente, (set, frozenset)):
        for item in fuente:
            nombre = _nombre_de(item)
            if nombre and es_nombre_asignatura(nombre):
                return nombre, _valores_de(item)
        return None, []

    return None, []


def requiere_seleccion(valores: Optional[Sequence[str]]) -> bool:
    """True si hay ≥2 asignaturas distintas, o sea hay que elegir una."""
    return len(valores or []) >= UMBRAL_REQUERIDA


def descriptor_de(
    columna: Optional[str],
    valores: Optional[Sequence[str]],
) -> Optional[dict]:
    """Campo `asignatura` de la respuesta de report-options, o None.

    Devuelve None (el campo se OMITE) cuando no hay dimensión de
    asignatura o cuando los datos traen 0 ó 1 valor: en ese caso no hay
    nada que preguntarle al usuario.

    Ejemplo:
        >>> descriptor_de("Asignatura", ["LECTURA", "MATEMATICA"])
        {'requerida': True, 'dimension': 'Asignatura', 'valores': ['LECTURA', 'MATEMATICA']}
        >>> descriptor_de("Asignatura", ["LECTURA"]) is None
        True
    """
    if not columna or not requiere_seleccion(valores):
        return None
    return {
        "requerida": True,
        "dimension": str(columna),
        "valores": list(valores or []),
    }


def descriptor(fuente: Any) -> Optional[dict]:
    """`descriptor_de` resolviendo la detección desde `fuente`."""
    columna, valores = dimension_asignatura(fuente)
    return descriptor_de(columna, valores)


# ─────────────────────────────────────────────────────────────────────────
# Filtros efectivos
# ─────────────────────────────────────────────────────────────────────────

def valores_en_filtros(
    filtros: Optional[Mapping[str, Any]],
    claves: Iterable[Any] = (),
) -> list[str]:
    """Asignaturas que los filtros fijan explícitamente.

    Args:
        filtros: dict de filtros. Las claves pueden ser nombres de columna
            ("Asignatura") o ids de dimensión ("7"), según el endpoint.
        claves: claves adicionales que cuentan como "la asignatura" (ej el
            `id_dimension` traducido). Las claves cuyo NOMBRE ya es de
            asignatura se reconocen siempre.

    Returns:
        Valores distintos, sin vacíos, ordenados. Lista vacía si los
        filtros no la mencionan.
    """
    extras = {str(c) for c in claves if c is not None and str(c) != ""}
    encontrados: list[str] = []
    for clave, valor in (filtros or {}).items():
        if str(clave) not in extras and not es_nombre_asignatura(clave):
            continue
        if isinstance(valor, (list, tuple, set)):
            encontrados.extend(str(v) for v in valor)
        elif valor is not None:
            encontrados.append(str(valor))
    return _valores_limpios(encontrados)


def partir_filtros(
    filtros: Optional[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """Separa los filtros en (resto, asignaturas_elegidas).

    Necesario antes de cargar los datos: si la asignatura se aplicara en el
    loader, la detección vería siempre UNA sola y nunca pediría elegir.
    """
    resto: dict[str, Any] = {}
    elegidas: list[str] = []
    for clave, valor in (filtros or {}).items():
        if es_nombre_asignatura(clave):
            if isinstance(valor, (list, tuple, set)):
                elegidas.extend(str(v) for v in valor)
            elif valor is not None:
                elegidas.append(str(valor))
            continue
        resto[clave] = valor
    return resto, _valores_limpios(elegidas)


# ─────────────────────────────────────────────────────────────────────────
# Validación
# ─────────────────────────────────────────────────────────────────────────

def mensaje_seleccion_requerida(
    valores: Sequence[str],
    elegidas: Optional[Sequence[str]] = None,
) -> str:
    """Mensaje accionable del 400. Distingue "no elegiste" de "elegiste varias".

    Ejemplo:
        >>> mensaje_seleccion_requerida(["LECTURA", "MATEMATICA"])
        'Este indicador tiene datos de varias asignaturas (LECTURA, MATEMATICA). Selecciona una asignatura en los filtros del dashboard o en el selector del informe.'
    """
    disponibles = ", ".join(str(v) for v in valores)
    if elegidas and len(elegidas) > 1:
        seleccion = ", ".join(str(v) for v in elegidas)
        return (
            f"El informe cubre UNA sola asignatura y se seleccionaron "
            f"{len(elegidas)} ({seleccion}). Deja solo una en los filtros del "
            f"dashboard o en el selector del informe."
        )
    return (
        f"Este indicador tiene datos de varias asignaturas ({disponibles}). "
        f"Selecciona una asignatura en los filtros del dashboard o en el "
        f"selector del informe."
    )


def resolver_seleccion(
    valores: Optional[Sequence[str]],
    elegidas: Optional[Sequence[str]] = None,
) -> Optional[str]:
    """La asignatura del informe, o None si el indicador no tiene ninguna.

    Args:
        valores: asignaturas presentes en los datos del indicador.
        elegidas: asignaturas que los filtros efectivos fijan.

    Returns:
        La asignatura a usar. Con una sola asignatura en los datos se
        devuelve ESA (nunca un literal por defecto: el viejo
        `asignatura="LENGUAJE"` renombraba informes de Matemática).

    Raises:
        AsignaturaRequerida: hay ≥2 asignaturas en los datos y los filtros
            no la fijan a exactamente una → 400 accionable.
    """
    disponibles = list(valores or [])
    seleccion = _valores_limpios(elegidas)

    if not requiere_seleccion(disponibles):
        if len(seleccion) == 1:
            return seleccion[0]
        return disponibles[0] if disponibles else None

    if len(seleccion) != 1:
        raise AsignaturaRequerida(
            mensaje_seleccion_requerida(disponibles, seleccion)
        )
    return seleccion[0]


def filtrar_dataframes(
    dataframes: Mapping[str, Any],
    columna: Optional[str],
    asignatura: Optional[str],
) -> dict[str, Any]:
    """Recorta cada DataFrame a `asignatura` (comparación case-insensitive).

    Los roles que quedan sin filas se OMITEN, igual que hace `data.py`
    cuando una metric no aporta records: así las guardias de
    `dispatch_v2` ("falta el df de preguntas") siguen viendo el mismo
    contrato.
    """
    if not columna or not asignatura:
        return dict(dataframes or {})
    objetivo = str(asignatura).strip().casefold()
    out: dict[str, Any] = {}
    for rol, df in (dataframes or {}).items():
        if columna not in _columnas(df):
            out[rol] = df
            continue
        sub = df[
            df[columna].astype(str).str.strip().str.casefold() == objetivo
        ].copy()
        if len(sub) == 0:
            continue
        out[rol] = sub
    return out
