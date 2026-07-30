"""Resolver de períodos temporales para informes.

El tiempo vive en dimensiones ("Año", "Mes", "Hito", "Versión",
"N Prueba") y — desde el tipo de dato de dimensión "fecha" — también en
columnas con fechas reales ("Fecha": "2026-04-07"). Este módulo traduce
un período declarativo — "la última prueba", "el semestre en curso", "el
año en curso", "un rango YYYY-MM" — a un dict de filtros por NOMBRE de
columna que cualquier motor de informes puede aplicar.

Una columna de tipo fecha actúa como fuente de AÑO **y** de MES: por eso
Fluidez Lectora, que no tiene dimensión "Año", igual puede resolver los
informes semestral y anual.

Todas las funciones son PURAS (no tocan la DB): reciben un DataFrame ya
cargado (`cargar_dataframes_indicator`) y devuelven un `ResultadoPeriodo`.

Semántica del semestre: calendario escolar chileno.
    meses 1–7  → 1er semestre (marzo a julio, con enero/febrero de holgura)
    meses 8–12 → 2º semestre

Uso típico:
    >>> from datetime import date
    >>> res = resolver_periodo(df, {"tipo": "ultima_prueba"}, date.today())
    >>> res.filtros
    {'Mes': 'NOVIEMBRE', 'Año': '2025'}
    >>> res.tipo_layout
    'evaluacion'
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Mapping, Optional

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────
# Mapeos de nombres de período → número de mes
# ─────────────────────────────────────────────────────────────────────────

MESES_A_NUMERO: dict[str, int] = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "SETIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}

NUMERO_A_MES: dict[int, str] = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL", 5: "MAYO", 6: "JUNIO",
    7: "JULIO", 8: "AGOSTO", 9: "SEPTIEMBRE", 10: "OCTUBRE",
    11: "NOVIEMBRE", 12: "DICIEMBRE",
}

# Hitos DIA → mes representativo (protocolo de la fundación).
HITO_A_MES: dict[str, int] = {
    "INICIO": 3,
    "INTERMEDIO": 6,
    "CIERRE": 11,
}

# Alias de hitos que aparecen en los datos reales del pipeline DIA.
_HITO_ALIASES: dict[str, str] = {
    "DIAGNOSTICO": "INICIO",
    "DIAGNOSTICA": "INICIO",
    "INICIAL": "INICIO",
    "MEDIO": "INTERMEDIO",
    "INTERMEDIA": "INTERMEDIO",
    "FINAL": "CIERRE",
    "SALIDA": "CIERRE",
}

# Versiones IDEL → mes representativo (3 aplicaciones al año).
VERSION_A_MES: dict[str, int] = {
    "v1": 4,
    "v2": 8,
    "v3": 11,
}

# Lookup tolerante de versiones: los datos IDEL guardan la versión como
# "1"/"2"/"3" (sin la "v"), así que hay que aceptar ambas formas. Se
# deriva de VERSION_A_MES para que exista UNA sola fuente de verdad.
_VERSION_LOOKUP: dict[str, int] = {}
for _clave, _mes in VERSION_A_MES.items():
    _VERSION_LOOKUP[_clave.upper()] = _mes           # "V1"
    _VERSION_LOOKUP[_clave.upper().lstrip("V")] = _mes  # "1"
del _clave, _mes

# Tokens que identifican cada tipo de columna temporal.
_TOKENS_ANIO = ("ano", "anos", "anio", "anios", "year", "years")
_TOKENS_MES_LIKE = ("mes", "fecha", "hito", "version")  # en orden de preferencia
_TOKENS_ORDINAL = ("prueba", "ensayo")
_TOKENS_FECHA = ("fecha", "fechas", "date", "dates")

# Valores de `dimensions.data_type` que declaran una columna como fecha.
# Se acepta la forma en español y las inglesas por retrocompatibilidad.
TIPOS_DATO_FECHA = frozenset({"fecha", "date", "datetime", "timestamp"})

# Una columna sin declarar se toma como fecha si al menos este porcentaje
# de la muestra parsea como fecha real.
UMBRAL_PARSEO_FECHA = 0.9
_MUESTRA_MAX = 500

# Semánticas de columna mes-like. Determinan cómo se interpreta un valor:
# en una columna "Versión", "1" es v1 (abril), NO enero.
SEMANTICA_MES = "mes"
SEMANTICA_FECHA = "fecha"
SEMANTICA_HITO = "hito"
SEMANTICA_VERSION = "version"

# Tipos de período soportados por `resolver_periodo`.
TIPOS_PERIODO = ("ultima_prueba", "semestral", "anual", "personalizado")


# ─────────────────────────────────────────────────────────────────────────
# Normalización
# ─────────────────────────────────────────────────────────────────────────

def _sin_tildes(texto: str) -> str:
    """'Año' → 'ano'. Quita tildes/diéresis y baja a minúsculas."""
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return s.strip().lower()


def _tokens(nombre: str) -> list[str]:
    """'N° Prueba' → ['n', 'prueba']. Tokeniza por cualquier no-alfanumérico."""
    return [t for t in re.split(r"[^a-z0-9]+", _sin_tildes(nombre)) if t]


def _menciona_token(nombre: str, tokens: Iterable[str]) -> bool:
    """True si alguno de `tokens` es una palabra completa de `nombre`."""
    tokens = tuple(tokens)
    return any(p in tokens for p in _tokens(nombre))


def _menciona_substring(nombre: str, tokens: Iterable[str]) -> bool:
    """True si alguno de `tokens` aparece como substring de `nombre`."""
    norm = _sin_tildes(nombre)
    return any(t in norm for t in tokens)


def _primera_columna(cols: list[str], tokens: Iterable[str]) -> Optional[str]:
    """Primera columna que mencione `tokens`, priorizando match por palabra.

    Dos pasadas: primero token exacto (así 'Año' gana a 'Plano', que solo
    matchea por substring), después substring para nombres pegados tipo
    'AñoEscolar'.
    """
    tokens = tuple(tokens)
    exacta = next((c for c in cols if _menciona_token(c, tokens)), None)
    if exacta:
        return exacta
    return next((c for c in cols if _menciona_substring(c, tokens)), None)


def tipo_mes_like(nombre: Optional[str]) -> Optional[str]:
    """Semántica de una columna mes-like a partir de su NOMBRE.

    Necesario porque el mismo valor significa cosas distintas según la
    columna: en "Mes", "1" es enero; en "Versión", "1" es v1 (abril).

    Args:
        nombre: nombre de columna (ej "Mes", "Fecha", "Hito", "Versión").

    Returns:
        `SEMANTICA_MES` | `SEMANTICA_FECHA` | `SEMANTICA_HITO` |
        `SEMANTICA_VERSION`, o None si el nombre no es mes-like.

    Ejemplo:
        >>> tipo_mes_like("Versión")
        'version'
        >>> tipo_mes_like("Curso") is None
        True
    """
    if not nombre:
        return None
    for token in _TOKENS_MES_LIKE:
        if _menciona_token(nombre, (token,)) or _menciona_substring(nombre, (token,)):
            return token
    return None


# ─────────────────────────────────────────────────────────────────────────
# Fechas reales (tipo de dato de dimensión "fecha")
# ─────────────────────────────────────────────────────────────────────────

# "2026-04-07", "2026/04/07", "2026-04-07 00:00:00", "2026-04-07T10:30"
_RE_FECHA_ISO = re.compile(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:[ T].*)?$")
# "07-04-2026", "7/4/2026", "07-04-2026 00:00:00"
_RE_FECHA_LATINA = re.compile(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})(?:[ T].*)?$")


def parsear_fecha(valor: Any) -> Optional[date]:
    """Valor de celda → `date`, o None si no es una fecha.

    Formatos aceptados (los tres que aparecen en los datos reales de la
    fundación, más los objetos nativos de pandas/datetime):

        ISO      "2026-04-07", "2026-04-07 00:00:00", "2026/04/07"
        latino   "07-04-2026", "07/04/2026"  (día primero, SIEMPRE)
        nativos  `pd.Timestamp`, `datetime`, `date`

    Deliberadamente NO usa `pd.to_datetime` con inferencia: pandas
    interpreta "07-04-2026" como 4 de julio (mes primero) y en Chile eso
    es el 7 de abril. El parseo es determinista y estricto — "2026",
    "2026-04" o "abril" devuelven None.
    """
    if valor is None:
        return None
    if isinstance(valor, (pd.Timestamp, datetime, date)):
        try:
            if pd.isna(valor):
                return None
        except (TypeError, ValueError):  # pragma: no cover — defensivo
            pass
        if isinstance(valor, (pd.Timestamp, datetime)):
            return valor.date()
        return valor
    if isinstance(valor, float) and pd.isna(valor):
        return None

    crudo = str(valor).strip()
    if not crudo:
        return None

    m = _RE_FECHA_ISO.match(crudo)
    if m:
        anio, mes, dia = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = _RE_FECHA_LATINA.match(crudo)
        if not m:
            return None
        dia, mes, anio = int(m.group(1)), int(m.group(2)), int(m.group(3))

    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def tasa_parseo_fecha(valores: Iterable[Any]) -> float:
    """Fracción [0.0–1.0] de `valores` no vacíos que parsean como fecha."""
    utiles = []
    for v in valores or []:
        if v is None:
            continue
        if isinstance(v, float) and pd.isna(v):
            continue
        if not isinstance(v, (pd.Timestamp, datetime, date)) and str(v).strip() == "":
            continue
        utiles.append(v)
    if not utiles:
        return 0.0
    ok = sum(1 for v in utiles if parsear_fecha(v) is not None)
    return ok / len(utiles)


def _tipo_declarado(nombre: str, tipos: Optional[Mapping[str, Any]]) -> Optional[str]:
    """`data_type` declarado para una columna (match tolerante a tildes)."""
    if not tipos:
        return None
    objetivo = _sin_tildes(nombre)
    for clave, valor in tipos.items():
        if _sin_tildes(clave) == objetivo:
            return _sin_tildes(valor) if valor else None
    return None


def es_columna_fecha(
    nombre: str,
    tipos: Optional[Mapping[str, Any]] = None,
    muestra: Optional[Iterable[Any]] = None,
) -> bool:
    """True si la columna se puede tratar como fecha real.

    Dos vías, en este orden:
        1. metadata: `data_type` de la dimensión ∈ `TIPOS_DATO_FECHA`.
        2. heurística: ≥`UMBRAL_PARSEO_FECHA` de la muestra parsea como
           fecha. Sin muestra se cae al nombre ("Fecha", "Date").
    """
    if _tipo_declarado(nombre, tipos) in TIPOS_DATO_FECHA:
        return True
    if muestra is None:
        return _menciona_token(nombre, _TOKENS_FECHA) or _menciona_substring(
            nombre, _TOKENS_FECHA
        )
    return tasa_parseo_fecha(muestra) >= UMBRAL_PARSEO_FECHA


def _primera_columna_fecha(
    cols: list[str],
    tipos: Optional[Mapping[str, Any]],
    muestras: Optional[Mapping[str, Iterable[Any]]],
) -> Optional[str]:
    """Elige LA columna fecha: declarada > nombrada > detectada por valores."""
    declarada = next(
        (c for c in cols if _tipo_declarado(c, tipos) in TIPOS_DATO_FECHA), None
    )
    if declarada:
        return declarada

    nombradas = [
        c for c in cols
        if _menciona_token(c, _TOKENS_FECHA) or _menciona_substring(c, _TOKENS_FECHA)
    ]
    for c in nombradas:
        if muestras is None:
            return c
        if tasa_parseo_fecha(muestras.get(c) or []) >= UMBRAL_PARSEO_FECHA:
            return c

    if muestras:
        for c in cols:
            if tasa_parseo_fecha(muestras.get(c) or []) >= UMBRAL_PARSEO_FECHA:
                return c
    return None


def muestras_de_dataframe(
    df: "pd.DataFrame", limite: int = _MUESTRA_MAX
) -> dict[str, list]:
    """{columna: primeros valores no nulos} para la heurística de fechas."""
    muestras: dict[str, list] = {}
    if df is None:
        return muestras
    for c in df.columns:
        try:
            muestras[str(c)] = df[c].head(limite).dropna().tolist()
        except Exception:  # pragma: no cover — defensivo
            muestras[str(c)] = []
    return muestras


def _version_a_mes(crudo: str) -> Optional[int]:
    """'1' / 'v1' / 'V1' / '1.0' → 4 (abril). None si no es una versión."""
    norm = _sin_tildes(crudo).upper().replace(" ", "")
    if norm in _VERSION_LOOKUP:
        return _VERSION_LOOKUP[norm]
    # "1.0" (pandas suele castear la columna a float)
    try:
        entero = str(int(float(norm)))
    except (TypeError, ValueError):
        return None
    return _VERSION_LOOKUP.get(entero)


def _hito_a_mes(crudo: str) -> Optional[int]:
    """'DIAGNOSTICO' → 3. None si no es un hito conocido."""
    norm = _sin_tildes(crudo).upper()
    hito = _HITO_ALIASES.get(norm, norm)
    return HITO_A_MES.get(hito)


def a_numero_mes(valor: Any, semantica: Optional[str] = None) -> Optional[int]:
    """Traduce un valor de columna mes-like a número de mes 1–12.

    Acepta:
        - nombres de mes en español, con o sin tilde: "MARZO", "Setiembre"
        - numéricos: 3, "3", "03", 3.0
        - hitos DIA: "INICIO", "DIAGNOSTICO", "CIERRE"
        - versiones IDEL: "v1", "V2", "3"
        - fechas ISO / dd-mm-yyyy: "2025-11-04", "04/11/2025"

    Args:
        valor: el valor crudo de la celda.
        semantica: semántica de la COLUMNA de donde sale el valor (ver
            `tipo_mes_like`). Manda sobre la forma del valor: con
            `semantica="version"`, "1"/"2"/"3" se resuelven como v1/v2/v3
            (abril/agosto/noviembre) y NO como enero/febrero/marzo — que
            era el bug que hacía que los informes semestral y anual de
            IDEL salieran idénticos (QA 2026-07-30, P1-3).

    Devuelve None si no se puede interpretar.
    """
    if valor is None:
        return None
    if isinstance(valor, float) and pd.isna(valor):
        return None
    if isinstance(valor, (pd.Timestamp, date)):
        return int(valor.month)

    crudo = str(valor).strip()
    if not crudo:
        return None

    # ── La semántica de la columna manda sobre la forma del valor ──
    if semantica == SEMANTICA_VERSION:
        mes = _version_a_mes(crudo)
        if mes is not None:
            return mes
    elif semantica == SEMANTICA_HITO:
        mes = _hito_a_mes(crudo)
        if mes is not None:
            return mes

    # Numérico directo ("3", "03", "3.0")
    try:
        n = int(float(crudo))
        if 1 <= n <= 12:
            return n
    except (TypeError, ValueError):
        pass

    norm = _sin_tildes(crudo).upper()

    if norm in MESES_A_NUMERO:
        return MESES_A_NUMERO[norm]

    mes = _hito_a_mes(crudo)
    if mes is not None:
        return mes

    # Versiones IDEL: "v1" / "V1" (case-insensitive contra las keys)
    if norm in _VERSION_LOOKUP and norm.startswith("V"):
        return _VERSION_LOOKUP[norm]

    # Fecha ISO "YYYY-MM-DD" o "YYYY-MM"
    m = re.match(r"^(\d{4})-(\d{1,2})", crudo)
    if m:
        mes = int(m.group(2))
        if 1 <= mes <= 12:
            return mes
    # Fecha "DD/MM/YYYY" o "DD-MM-YYYY", con o sin hora
    fecha = parsear_fecha(crudo)
    if fecha is not None:
        return fecha.month

    return None


def _a_entero(valor: Any) -> Optional[int]:
    """Parsea un valor a int, o None si no se puede."""
    if valor is None:
        return None
    if isinstance(valor, float) and pd.isna(valor):
        return None
    try:
        return int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return None


def semestre_de_mes(mes: int) -> int:
    """1 para meses 1–7, 2 para 8–12 (calendario escolar chileno)."""
    return 1 if int(mes) <= 7 else 2


def _meses_del_semestre(semestre: int) -> tuple[int, int]:
    """(mes_inicio, mes_fin) del semestre indicado."""
    return (1, 7) if semestre == 1 else (8, 12)


# ─────────────────────────────────────────────────────────────────────────
# Detección de columnas temporales
# ─────────────────────────────────────────────────────────────────────────

def detectar_columnas_temporales(
    columns: Iterable[str],
    tipos: Optional[Mapping[str, Any]] = None,
    muestras: Optional[Mapping[str, Iterable[Any]]] = None,
) -> dict[str, Optional[str]]:
    """Clasifica las columnas de un DataFrame en roles temporales.

    Args:
        columns: nombres de columna (humanizados por `data.py`).
        tipos: {columna: data_type} del catálogo de dimensiones. Un
            `data_type` de `TIPOS_DATO_FECHA` marca la columna como fecha
            real sin necesidad de heurística.
        muestras: {columna: valores} para la heurística de parseo (ver
            `muestras_de_dataframe`). Sin esto la detección de fechas cae
            al nombre de la columna.

    Returns:
        dict con keys:
            "anio"     nombre de la columna de año (o None)
            "mes_like" columna que aporta el mes: Mes | Fecha | Hito |
                       Versión, en ese orden de preferencia (o None)
            "ordinal"  columna con el número de prueba/ensayo (o None)
            "fecha"    columna con fechas reales, fuente de año Y mes
                       (o None)

    Ejemplo:
        >>> detectar_columnas_temporales(["Curso", "Año", "Mes", "N Prueba"])
        {'anio': 'Año', 'mes_like': 'Mes', 'ordinal': 'N Prueba', 'fecha': None}
    """
    cols = [str(c) for c in columns]

    anio = _primera_columna(cols, _TOKENS_ANIO)

    mes_like = None
    for token in _TOKENS_MES_LIKE:
        mes_like = _primera_columna(cols, (token,))
        if mes_like:
            break

    ordinal = _primera_columna(cols, _TOKENS_ORDINAL)
    fecha = _primera_columna_fecha(cols, tipos, muestras)

    # Una columna fecha declarada por metadata puede llamarse "Aplicación"
    # y no matchear ningún token mes-like: igual aporta el mes.
    if fecha and not mes_like:
        mes_like = fecha

    return {"anio": anio, "mes_like": mes_like, "ordinal": ordinal, "fecha": fecha}


def detectar_columnas_temporales_df(
    df: "pd.DataFrame",
    tipos: Optional[Mapping[str, Any]] = None,
) -> dict[str, Optional[str]]:
    """`detectar_columnas_temporales` muestreando el propio DataFrame."""
    if df is None:
        return detectar_columnas_temporales([], tipos)
    return detectar_columnas_temporales(df.columns, tipos, muestras_de_dataframe(df))


def semantica_columna(
    nombre: Optional[str],
    cols: Optional[Mapping[str, Optional[str]]] = None,
) -> Optional[str]:
    """Semántica de una columna, considerando la fecha detectada.

    `tipo_mes_like` solo mira el NOMBRE; si la columna fue detectada como
    fecha (por metadata o por sus valores) manda `SEMANTICA_FECHA` aunque
    se llame "Aplicación".
    """
    if nombre and cols and nombre == cols.get("fecha"):
        return SEMANTICA_FECHA
    return tipo_mes_like(nombre)


def _componentes_temporales(
    row: Mapping[str, Any],
    cols: Mapping[str, Optional[str]],
) -> tuple[int, int, int, int]:
    """(anio, mes, dia, ordinal) de una fila. -1 donde falte.

    El año y el mes se derivan de la columna fecha cuando no hay columnas
    Año/Mes explícitas — es lo que habilita los informes semestral y anual
    en indicadores como Fluidez Lectora.
    """
    col_anio = cols.get("anio")
    col_mes = cols.get("mes_like")
    col_ord = cols.get("ordinal")
    col_fecha = cols.get("fecha")

    fecha = parsear_fecha(row.get(col_fecha)) if col_fecha else None

    anio = _a_entero(row.get(col_anio)) if col_anio else None
    if anio is None and fecha is not None:
        anio = fecha.year

    mes = (
        a_numero_mes(row.get(col_mes), semantica_columna(col_mes, cols))
        if col_mes else None
    )
    if mes is None and fecha is not None:
        mes = fecha.month

    ordinal = _a_entero(row.get(col_ord)) if col_ord else None

    return (
        anio if anio is not None else -1,
        mes if mes is not None else -1,
        fecha.day if fecha is not None else -1,
        ordinal if ordinal is not None else -1,
    )


def clave_temporal(
    row: Mapping[str, Any],
    cols: Mapping[str, Optional[str]],
) -> tuple[int, int, int]:
    """Clave ordenable (anio, mes, ordinal) de una fila. -1 donde falte.

    Args:
        row: fila como dict o `pd.Series`.
        cols: salida de `detectar_columnas_temporales`.

    Returns:
        Tupla de 3 enteros comparable con `max()`. Los valores no
        parseables degradan a -1 (van al final del orden).
    """
    anio, mes, _dia, ordinal = _componentes_temporales(row, cols)
    return (anio, mes, ordinal)


def clave_temporal_detallada(
    row: Mapping[str, Any],
    cols: Mapping[str, Optional[str]],
) -> tuple[int, int, int, int]:
    """`clave_temporal` con el DÍA entre el mes y el ordinal.

    Necesaria para ordenar por fecha real: sin el día, dos pruebas del
    mismo mes ("2026-04-02" y "2026-04-13") empatan y la "última prueba"
    la termina eligiendo el orden de las filas. Cuando no hay columna
    fecha el día es siempre -1 y el orden es idéntico al de
    `clave_temporal`.
    """
    return _componentes_temporales(row, cols)


def hay_columna_temporal(cols: Mapping[str, Optional[str]]) -> bool:
    """True si se detectó al menos una columna temporal."""
    return any(cols.get(k) for k in ("anio", "mes_like", "ordinal", "fecha"))


# ─────────────────────────────────────────────────────────────────────────
# Resultado
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class ResultadoPeriodo:
    """Período resuelto contra datos reales.

    Attributes:
        tipo: el tipo pedido ("ultima_prueba" | "semestral" | "anual" |
            "personalizado").
        filtros: {nombre_columna: valor | [valores]} listos para el loader.
        tipo_layout: "evaluacion" (un punto en el tiempo) o "historico"
            (varios) — determina qué pdf_layout usar.
        descripcion: texto legible para la UI ("NOVIEMBRE 2025").
        disponible: False si el período no se pudo resolver.
        motivo: explicación accionable cuando `disponible` es False.
        columnas: las columnas temporales detectadas (debug/introspección).
    """
    tipo: str
    filtros: dict[str, Any] = field(default_factory=dict)
    tipo_layout: str = "evaluacion"
    descripcion: str = ""
    disponible: bool = True
    motivo: Optional[str] = None
    columnas: dict[str, Optional[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialización plana para respuestas JSON."""
        return {
            "tipo": self.tipo,
            "filtros": self.filtros,
            "tipo_layout": self.tipo_layout,
            "descripcion": self.descripcion,
            "disponible": self.disponible,
            "motivo": self.motivo,
        }


def _no_disponible(tipo: str, motivo: str, cols: dict | None = None,
                   tipo_layout: str = "evaluacion") -> ResultadoPeriodo:
    return ResultadoPeriodo(
        tipo=tipo,
        filtros={},
        tipo_layout=tipo_layout,
        descripcion="",
        disponible=False,
        motivo=motivo,
        columnas=cols or {},
    )


# ─────────────────────────────────────────────────────────────────────────
# Descripciones legibles
# ─────────────────────────────────────────────────────────────────────────

def _mes_like_legible(valor: Any, semantica: Optional[str]) -> str:
    """Valor de columna mes-like → texto para mostrar al usuario.

    - Versión: "3" → "v3" (el crudo "3 2026" era ilegible, QA P2-1).
    - Fecha: Timestamp → "07-04-2026" (sin la hora 00:00:00, QA P1-12).
    - Resto: el crudo en mayúsculas.
    """
    if isinstance(valor, (pd.Timestamp, date)):
        return valor.strftime("%d-%m-%Y")
    crudo = str(valor).strip()
    if semantica == SEMANTICA_VERSION and _version_a_mes(crudo) is not None:
        return crudo if crudo.upper().startswith("V") else f"v{crudo}"
    if semantica == SEMANTICA_FECHA:
        # "2026-04-07 00:00:00" → "07-04-2026" (viene como string del df)
        parsed = parsear_fecha(crudo)
        if parsed is not None:
            return parsed.strftime("%d-%m-%Y")
    return crudo.upper()


def _describir_evaluacion(valores: dict[str, Any], cols: dict) -> str:
    """'NOVIEMBRE 2025' / 'NOVIEMBRE 2025 (prueba 5)' / 'Prueba 3'."""
    partes: list[str] = []
    col_mes = cols.get("mes_like")
    col_anio = cols.get("anio")
    col_ord = cols.get("ordinal")

    if col_mes and valores.get(col_mes) not in (None, ""):
        partes.append(_mes_like_legible(valores[col_mes], semantica_columna(col_mes, cols)))
    if col_anio and valores.get(col_anio) not in (None, ""):
        partes.append(str(valores[col_anio]))

    base = " ".join(partes)
    if col_ord and valores.get(col_ord) not in (None, ""):
        sufijo = f"prueba {valores[col_ord]}"
        base = f"{base} ({sufijo})" if base else sufijo.capitalize()
    return base


def _describir_semestre(anio: int, semestre: int) -> str:
    """'1er semestre 2026 (enero–julio)'."""
    ini, fin = _meses_del_semestre(semestre)
    etiqueta = "1er" if semestre == 1 else "2º"
    return (
        f"{etiqueta} semestre {anio} "
        f"({NUMERO_A_MES[ini].lower()}–{NUMERO_A_MES[fin].lower()})"
    )


def _describir_rango(inicio: tuple[int, int] | None, fin: tuple[int, int] | None) -> str:
    """'NOVIEMBRE 2025 – MARZO 2026' a partir de tuplas (año, mes)."""
    def _fmt(t):
        anio, mes = t
        return f"{NUMERO_A_MES.get(mes, '')} {anio}".strip()

    if inicio and fin:
        if inicio == fin:
            return _fmt(inicio)
        return f"{_fmt(inicio)} – {_fmt(fin)}"
    if inicio:
        return f"Desde {_fmt(inicio)}"
    if fin:
        return f"Hasta {_fmt(fin)}"
    return ""


# ─────────────────────────────────────────────────────────────────────────
# Parseo de "YYYY-MM"
# ─────────────────────────────────────────────────────────────────────────

def parsear_ym(texto: Any) -> Optional[tuple[int, int]]:
    """'2026-03' → (2026, 3). Devuelve None si no parsea.

    Formatos aceptados:
        "YYYY-MM" / "YYYY-M" / "YYYY/MM"   → (año, mes)
        "YYYY"                             → (año, 0)  mes indeterminado:
                                             el caller decide si es 1 o 12
        fechas completas                   → (año, mes) del día concreto
                                             ("2019-01-01", "07-04-2026",
                                             `date`/`Timestamp`)

    Las fechas completas se aceptan porque el frontend y los clientes de la
    API mandan `fecha_inicio`/`fecha_fin` en "YYYY-MM-DD": antes devolvían
    None y el rango se descartaba EN SILENCIO, entregando el informe del
    dataset entero (QA piloto SIMCE 2026-07-30, P0-2).
    """
    if texto is None:
        return None
    if isinstance(texto, (pd.Timestamp, datetime, date)):
        fecha = parsear_fecha(texto)
        return (fecha.year, fecha.month) if fecha else None
    s = str(texto).strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})[-/](\d{1,2})$", s)
    if m:
        mes = int(m.group(2))
        if 1 <= mes <= 12:
            return (int(m.group(1)), mes)
        return None
    m = re.match(r"^(\d{4})$", s)
    if m:
        return (int(m.group(1)), 0)  # 0 = mes indeterminado, el caller decide
    fecha = parsear_fecha(s)
    if fecha is not None:
        return (fecha.year, fecha.month)
    return None


def _viene_con_valor(crudo: Any) -> bool:
    """True si el caller mandó algo distinto de None/"" en ese extremo."""
    if crudo is None:
        return False
    if isinstance(crudo, float) and pd.isna(crudo):
        return False
    if isinstance(crudo, (pd.Timestamp, datetime, date)):
        return True
    return str(crudo).strip() != ""


# ─────────────────────────────────────────────────────────────────────────
# Resolución
# ─────────────────────────────────────────────────────────────────────────

def _filtrar_por_dict(df: pd.DataFrame, filtros: Mapping[str, Any]) -> pd.DataFrame:
    """Aplica {columna: valor | [valores]} sobre `df` comparando como string."""
    out = df
    for col, val in (filtros or {}).items():
        if col not in out.columns:
            continue
        if isinstance(val, (list, tuple, set)):
            permitidos = {str(v) for v in val}
            if not permitidos:
                continue
            out = out[out[col].astype(str).isin(permitidos)]
        else:
            out = out[out[col].astype(str) == str(val)]
    return out


def aplicar_filtros_a_dataframes(
    dataframes: Mapping[str, pd.DataFrame],
    filtros: Mapping[str, Any],
) -> dict[str, pd.DataFrame]:
    """Aplica `{columna: valor | [valores]}` a cada df del dict.

    Se usa para acotar los datos ANTES de resolver el período: la "última
    prueba" de LECTURA no tiene por qué ser la última del indicador cuando
    hay varias asignaturas. Las columnas que un df no tenga se ignoran.
    """
    if not filtros:
        return dict(dataframes or {})
    return {
        rol: _filtrar_por_dict(df, filtros)
        for rol, df in (dataframes or {}).items()
    }


def _claves_distintas(df: pd.DataFrame, cols: dict) -> set[tuple[int, int, int, int]]:
    """Set de claves temporales distintas presentes en `df`."""
    return {clave_temporal_detallada(row, cols) for _, row in df.iterrows()}


def _valores_de_columna(df: pd.DataFrame, columna: str) -> list:
    """Valores únicos no nulos de una columna (lista vacía si no existe)."""
    if df is None or df.empty or columna not in df.columns:
        return []
    return df[columna].dropna().unique().tolist()


def _ordenar_por_fecha(valores: Iterable[Any]) -> list[str]:
    """Ordena valores de una columna fecha cronológicamente (como strings)."""
    return sorted(
        {str(v) for v in valores},
        key=lambda v: (parsear_fecha(v) or date.min, str(v)),
    )


def _resolver_ultima_prueba(df: pd.DataFrame, cols: dict) -> ResultadoPeriodo:
    if not hay_columna_temporal(cols):
        return _no_disponible(
            "ultima_prueba",
            "No se detectó ninguna dimensión temporal (Año, Mes, Hito, "
            "Versión o N° Prueba) en los datos de este indicador.",
            cols,
        )
    if df.empty:
        return _no_disponible(
            "ultima_prueba", "Sin datos cargados para este indicador.", cols
        )

    mejor_clave: tuple[int, int, int, int] | None = None
    mejor_row: Mapping[str, Any] | None = None
    for _, row in df.iterrows():
        k = clave_temporal_detallada(row, cols)
        if mejor_clave is None or k > mejor_clave:
            mejor_clave, mejor_row = k, row

    if mejor_row is None:
        return _no_disponible(
            "ultima_prueba", "Sin datos cargados para este indicador.", cols
        )

    # Fijar CADA columna temporal detectada al valor de la clave máxima.
    # La columna fecha solo entra al filtro cuando ES la fuente del año: si
    # el indicador ya tiene Año/Mes/N Prueba (Cálculo Veloz), esas columnas
    # identifican la evaluación y fijar además el día la acotaría de más —
    # una prueba aplicada en varias jornadas perdería filas.
    roles = ("anio", "mes_like", "ordinal")
    if not cols.get("anio"):
        roles = roles + ("fecha",)

    filtros: dict[str, Any] = {}
    valores: dict[str, Any] = {}
    for rol in roles:
        col = cols.get(rol)
        if not col:
            continue
        valor = mejor_row.get(col)
        if valor is None or (isinstance(valor, float) and pd.isna(valor)) or str(valor) == "":
            continue
        filtros[col] = str(valor)
        valores[col] = valor

    if not filtros:
        return _no_disponible(
            "ultima_prueba",
            "Las dimensiones temporales están vacías en todos los registros.",
            cols,
        )

    return ResultadoPeriodo(
        tipo="ultima_prueba",
        filtros=filtros,
        tipo_layout="evaluacion",
        descripcion=_describir_evaluacion(valores, cols),
        columnas=cols,
    )


def _resolver_anual(df: pd.DataFrame, cols: dict, hoy: date) -> ResultadoPeriodo:
    col_anio = cols.get("anio")
    col_fecha = cols.get("fecha")
    anio = hoy.year

    if not col_anio and not col_fecha:
        return _no_disponible(
            "anual",
            "No se detectó una dimensión de año ni de fecha en los datos de "
            "este indicador — el informe anual no se puede acotar.",
            cols,
            tipo_layout="historico",
        )

    if not col_anio:
        # Año derivado de la columna fecha: el filtro se materializa como la
        # lista de fechas del año (el loader filtra por valores de columna).
        permitidos = [
            str(v) for v in _valores_de_columna(df, col_fecha)
            if (f := parsear_fecha(v)) is not None and f.year == anio
        ]
        if not permitidos:
            return _no_disponible(
                "anual",
                f"Sin datos del año en curso ({anio}) para este indicador.",
                cols,
                tipo_layout="historico",
            )
        return ResultadoPeriodo(
            tipo="anual",
            filtros={col_fecha: _ordenar_por_fecha(permitidos)},
            tipo_layout="historico",
            descripcion=str(anio),
            columnas=cols,
        )

    sub = df[df[col_anio].astype(str).str.strip() == str(anio)] if not df.empty else df
    if sub.empty:
        return _no_disponible(
            "anual",
            f"Sin datos del año en curso ({anio}) para este indicador.",
            cols,
            tipo_layout="historico",
        )

    return ResultadoPeriodo(
        tipo="anual",
        filtros={col_anio: str(anio)},
        tipo_layout="historico",
        descripcion=str(anio),
        columnas=cols,
    )


def _resolver_semestral(df: pd.DataFrame, cols: dict, hoy: date) -> ResultadoPeriodo:
    col_anio = cols.get("anio")
    col_mes = cols.get("mes_like")
    col_fecha = cols.get("fecha")

    anio = hoy.year
    semestre = semestre_de_mes(hoy.month)
    mes_ini, mes_fin = _meses_del_semestre(semestre)

    if not col_anio and not col_fecha:
        return _no_disponible(
            "semestral",
            "No se detectó una dimensión de año ni de fecha en los datos de "
            "este indicador — el informe semestral no se puede acotar.",
            cols,
            tipo_layout="historico",
        )
    if not col_mes and not col_fecha:
        return _no_disponible(
            "semestral",
            "No se detectó una dimensión de mes (Mes, Fecha, Hito o "
            "Versión) — el informe semestral no se puede acotar.",
            cols,
            tipo_layout="historico",
        )

    if not col_anio:
        # Año y mes derivados de la misma columna fecha.
        permitidos = [
            str(v) for v in _valores_de_columna(df, col_fecha)
            if (f := parsear_fecha(v)) is not None
            and f.year == anio and mes_ini <= f.month <= mes_fin
        ]
        if not permitidos:
            return _no_disponible(
                "semestral",
                f"Sin datos del {_describir_semestre(anio, semestre)} para este indicador.",
                cols,
                tipo_layout="historico",
            )
        return ResultadoPeriodo(
            tipo="semestral",
            filtros={col_fecha: _ordenar_por_fecha(permitidos)},
            tipo_layout="historico",
            descripcion=_describir_semestre(anio, semestre),
            columnas=cols,
        )

    if df.empty:
        return _no_disponible(
            "semestral",
            f"Sin datos del {_describir_semestre(anio, semestre)} para este indicador.",
            cols,
            tipo_layout="historico",
        )

    semantica = semantica_columna(col_mes, cols)
    del_anio = df[df[col_anio].astype(str).str.strip() == str(anio)]
    permitidos: list[str] = []
    for valor in del_anio[col_mes].dropna().unique().tolist():
        mes = a_numero_mes(valor, semantica)
        if mes is not None and mes_ini <= mes <= mes_fin:
            permitidos.append(str(valor))

    if not permitidos:
        return _no_disponible(
            "semestral",
            f"Sin datos del {_describir_semestre(anio, semestre)} para este indicador.",
            cols,
            tipo_layout="historico",
        )

    # Orden cronológico de los valores permitidos (mejora legibilidad del filtro).
    permitidos = sorted(set(permitidos), key=lambda v: (a_numero_mes(v, semantica) or 0, str(v)))

    return ResultadoPeriodo(
        tipo="semestral",
        filtros={col_anio: str(anio), col_mes: permitidos},
        tipo_layout="historico",
        descripcion=_describir_semestre(anio, semestre),
        columnas=cols,
    )


def _resolver_personalizado(
    df: pd.DataFrame,
    periodo: Mapping[str, Any],
    cols: dict,
) -> ResultadoPeriodo:
    """Filtros libres + rango YYYY-MM opcional.

    LIMITACIÓN CONOCIDA: el rango se materializa como listas de valores
    permitidos POR COLUMNA (año ∈ [...] Y mes ∈ [...]), no como tupla
    (año, mes). Para rangos que cruzan el año (ej 2025-10 → 2026-03) el
    filtro resultante es un superconjunto del rango exacto. Es el precio
    de mantener el contrato `dict nombre → valores` que consumen todos los
    loaders del proyecto.

    REGLA DURA (QA piloto SIMCE 2026-07-30, P0-2): un rango que el caller
    pidió y que NO se puede honrar jamás degrada a "sin recorte temporal".
    Fecha ilegible, rango invertido o rango sin un solo punto temporal
    dentro devuelven `disponible=False` con motivo accionable — el router
    lo traduce a 400. Entregar en silencio un informe con datos de otro
    período es el peor modo de falla posible en un documento que va a un
    establecimiento, y esta función la comparten los 6 módulos del motor
    único.
    """
    filtros_usuario = dict(periodo.get("filtros") or {})
    crudo_inicio = periodo.get("fecha_inicio")
    crudo_fin = periodo.get("fecha_fin")
    inicio = parsear_ym(crudo_inicio)
    fin = parsear_ym(crudo_fin)

    ilegibles = [
        str(crudo).strip()
        for crudo, parseado in ((crudo_inicio, inicio), (crudo_fin, fin))
        if _viene_con_valor(crudo) and parseado is None
    ]
    if ilegibles:
        return _no_disponible(
            "personalizado",
            "No se pudo interpretar el rango de fechas "
            f"({', '.join(ilegibles)}). Usa el formato AAAA-MM "
            "(por ejemplo 2025-03) o AAAA-MM-DD.",
            cols,
        )

    # "2026" sin mes: inicio → enero, fin → diciembre.
    if inicio and inicio[1] == 0:
        inicio = (inicio[0], 1)
    if fin and fin[1] == 0:
        fin = (fin[0], 12)

    if inicio and fin and inicio > fin:
        return _no_disponible(
            "personalizado",
            "El rango de fechas está invertido: el inicio "
            f"({_describir_rango(inicio, inicio)}) es posterior al fin "
            f"({_describir_rango(fin, fin)}). Intercambia las fechas e "
            "inténtalo de nuevo.",
            cols,
        )

    filtros: dict[str, Any] = dict(filtros_usuario)
    col_anio = cols.get("anio")
    col_mes = cols.get("mes_like")
    col_fecha = cols.get("fecha")
    semantica = semantica_columna(col_mes, cols)

    if (inicio or fin) and not (col_anio or col_mes or col_fecha):
        return _no_disponible(
            "personalizado",
            "No se detectó ninguna dimensión temporal — no se puede aplicar "
            "un rango de fechas a este indicador.",
            cols,
        )

    # Base: filas que pasan los filtros de dimensión del usuario.
    base = _filtrar_por_dict(df, filtros_usuario) if not df.empty else df

    if inicio or fin:
        lim_ini = inicio or (-10_000, 1)
        lim_fin = fin or (10_000, 12)

        anios_ok: set[str] = set()
        meses_ok: set[str] = set()
        fechas_ok: set[str] = set()
        filas_ok: list[int] = []

        for idx, row in base.iterrows():
            # `_componentes_temporales` deriva año/mes de la columna fecha
            # cuando no hay dimensiones Año/Mes explícitas.
            anio_i, mes_i, _dia, _ord = _componentes_temporales(row, cols)
            anio = anio_i if anio_i >= 0 else None
            mes = mes_i if mes_i >= 0 else None

            if anio is None:
                # Sin año no hay forma de ubicar la fila en el rango.
                continue
            if mes is None:
                # Filas sin mes conocido: se incluyen si el AÑO cae dentro.
                dentro = lim_ini[0] <= anio <= lim_fin[0]
            else:
                dentro = lim_ini <= (anio, mes) <= lim_fin

            if dentro:
                filas_ok.append(idx)
                if col_anio and row.get(col_anio) not in (None, ""):
                    anios_ok.add(str(row.get(col_anio)))
                if col_mes and row.get(col_mes) not in (None, ""):
                    meses_ok.add(str(row.get(col_mes)))
                if col_fecha and row.get(col_fecha) not in (None, ""):
                    fechas_ok.add(str(row.get(col_fecha)))

        if not filas_ok:
            rango = _describir_rango(inicio, fin)
            return _no_disponible(
                "personalizado",
                "No hay datos en el período seleccionado"
                + (f" ({rango})." if rango else ".")
                + " Elige un rango con evaluaciones registradas.",
                cols,
            )

        if col_anio and anios_ok:
            filtros[col_anio] = sorted(anios_ok)
        if col_mes and meses_ok:
            filtros[col_mes] = sorted(
                meses_ok, key=lambda v: (a_numero_mes(v, semantica) or 0, str(v))
            )
        # La fecha solo entra al filtro cuando es la fuente del año (mismo
        # criterio que `_resolver_ultima_prueba`): con Año/Mes explícitos,
        # fijar además el día acotaría el rango de más.
        if col_fecha and fechas_ok and not col_anio and col_fecha not in filtros:
            filtros[col_fecha] = _ordenar_por_fecha(fechas_ok)

        resultante = base.loc[filas_ok]
        descripcion = _describir_rango(inicio, fin)
    else:
        resultante = base
        if resultante.empty and not df.empty:
            return _no_disponible(
                "personalizado", "Sin datos con los filtros seleccionados.", cols
            )
        partes = [f"{k}: {v}" for k, v in filtros_usuario.items()]
        descripcion = " · ".join(partes) if partes else "Todos los datos"

    claves = _claves_distintas(resultante, cols) if not resultante.empty else set()
    tipo_layout = "historico" if len(claves) > 1 else "evaluacion"

    return ResultadoPeriodo(
        tipo="personalizado",
        filtros=filtros,
        tipo_layout=tipo_layout,
        descripcion=descripcion,
        columnas=cols,
    )


def resolver_periodo(
    df: pd.DataFrame,
    periodo: Mapping[str, Any],
    hoy: date,
    tipos: Optional[Mapping[str, Any]] = None,
) -> ResultadoPeriodo:
    """Resuelve un período declarativo contra los datos reales de un df.

    Args:
        df: DataFrame del indicador (columnas humanizadas por `data.py`).
        periodo: dict con:
            tipo: "ultima_prueba" | "semestral" | "anual" | "personalizado"
            fecha_inicio / fecha_fin: "YYYY-MM" (solo personalizado)
            filtros: {nombre_dim: valor | [valores]} (solo personalizado)
        hoy: fecha de referencia (inyectada para que la función sea pura
            y testeable).
        tipos: {columna: data_type} del catálogo de dimensiones. Sirve
            para declarar columnas de tipo fecha sin depender del nombre
            ni de la heurística de parseo.

    Returns:
        `ResultadoPeriodo`. Cuando `disponible` es False, `motivo` explica
        qué falta y `filtros` viene vacío.
    """
    tipo = (periodo or {}).get("tipo") or "ultima_prueba"
    if tipo not in TIPOS_PERIODO:
        return _no_disponible(
            tipo,
            f"Tipo de período '{tipo}' desconocido. Válidos: "
            f"{', '.join(TIPOS_PERIODO)}.",
        )

    if df is None:
        df = pd.DataFrame()
    cols = detectar_columnas_temporales_df(df, tipos)

    if tipo == "ultima_prueba":
        return _resolver_ultima_prueba(df, cols)
    if tipo == "anual":
        return _resolver_anual(df, cols, hoy)
    if tipo == "semestral":
        return _resolver_semestral(df, cols, hoy)
    return _resolver_personalizado(df, periodo or {}, cols)


# ─────────────────────────────────────────────────────────────────────────
# Conveniencia para múltiples DataFrames
# ─────────────────────────────────────────────────────────────────────────

def elegir_df_temporal(
    dataframes: Mapping[str, pd.DataFrame],
    tipos: Optional[Mapping[str, Any]] = None,
) -> Optional[pd.DataFrame]:
    """Elige el DataFrame más apto para resolver períodos.

    Prefiere el rol "estudiantes"; si no lo tiene (o no aporta columnas
    temporales) toma el que más columnas temporales detecte. None si el
    dict está vacío.
    """
    if not dataframes:
        return None

    def _puntaje(df: pd.DataFrame) -> int:
        cols = detectar_columnas_temporales_df(df, tipos)
        return sum(1 for k in ("anio", "mes_like", "ordinal", "fecha") if cols.get(k))

    preferido = dataframes.get("estudiantes")
    if preferido is not None and _puntaje(preferido) > 0:
        return preferido

    mejor, mejor_puntaje = None, -1
    for df in dataframes.values():
        p = _puntaje(df)
        if p > mejor_puntaje:
            mejor, mejor_puntaje = df, p
    return mejor if mejor is not None else preferido


def resolver_periodo_multi(
    dataframes: Mapping[str, pd.DataFrame],
    periodo: Mapping[str, Any],
    hoy: date,
    tipos: Optional[Mapping[str, Any]] = None,
) -> ResultadoPeriodo:
    """`resolver_periodo` sobre el dict {rol: df} de `cargar_dataframes_indicator`."""
    df = elegir_df_temporal(dataframes, tipos)
    if df is None:
        return _no_disponible(
            (periodo or {}).get("tipo") or "ultima_prueba",
            "Sin datos cargados para este indicador.",
        )
    return resolver_periodo(df, periodo, hoy, tipos)
