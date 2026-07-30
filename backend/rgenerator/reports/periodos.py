"""Resolver de períodos temporales para informes.

En este proyecto NO existe una columna de fecha real: el tiempo vive en
dimensiones ("Año", "Mes", "Hito", "Versión", "N Prueba"). Este módulo
traduce un período declarativo — "la última prueba", "el semestre en
curso", "el año en curso", "un rango YYYY-MM" — a un dict de filtros por
NOMBRE de columna que cualquier motor de informes puede aplicar.

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
from datetime import date
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
    # Fecha "DD/MM/YYYY" o "DD-MM-YYYY"
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", crudo)
    if m:
        mes = int(m.group(2))
        if 1 <= mes <= 12:
            return mes

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

def detectar_columnas_temporales(columns: Iterable[str]) -> dict[str, Optional[str]]:
    """Clasifica las columnas de un DataFrame en roles temporales.

    Args:
        columns: nombres de columna (humanizados por `data.py`).

    Returns:
        dict con keys:
            "anio"     nombre de la columna de año (o None)
            "mes_like" columna que aporta el mes: Mes | Fecha | Hito |
                       Versión, en ese orden de preferencia (o None)
            "ordinal"  columna con el número de prueba/ensayo (o None)

    Ejemplo:
        >>> detectar_columnas_temporales(["Curso", "Año", "Mes", "N Prueba"])
        {'anio': 'Año', 'mes_like': 'Mes', 'ordinal': 'N Prueba'}
    """
    cols = [str(c) for c in columns]

    anio = _primera_columna(cols, _TOKENS_ANIO)

    mes_like = None
    for token in _TOKENS_MES_LIKE:
        mes_like = _primera_columna(cols, (token,))
        if mes_like:
            break

    ordinal = _primera_columna(cols, _TOKENS_ORDINAL)

    return {"anio": anio, "mes_like": mes_like, "ordinal": ordinal}


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
    col_anio = cols.get("anio")
    col_mes = cols.get("mes_like")
    col_ord = cols.get("ordinal")

    anio = _a_entero(row.get(col_anio)) if col_anio else None
    mes = a_numero_mes(row.get(col_mes), tipo_mes_like(col_mes)) if col_mes else None
    ordinal = _a_entero(row.get(col_ord)) if col_ord else None

    return (
        anio if anio is not None else -1,
        mes if mes is not None else -1,
        ordinal if ordinal is not None else -1,
    )


def hay_columna_temporal(cols: Mapping[str, Optional[str]]) -> bool:
    """True si se detectó al menos una columna temporal."""
    return any(cols.get(k) for k in ("anio", "mes_like", "ordinal"))


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
        # "2026-04-07 00:00:00" → "2026-04-07" (viene como string del df)
        parsed = pd.to_datetime(crudo, errors="coerce")
        if parsed is not pd.NaT and not pd.isna(parsed):
            return parsed.strftime("%d-%m-%Y")
    return crudo.upper()


def _describir_evaluacion(valores: dict[str, Any], cols: dict) -> str:
    """'NOVIEMBRE 2025' / 'NOVIEMBRE 2025 (prueba 5)' / 'Prueba 3'."""
    partes: list[str] = []
    col_mes = cols.get("mes_like")
    col_anio = cols.get("anio")
    col_ord = cols.get("ordinal")

    if col_mes and valores.get(col_mes) not in (None, ""):
        partes.append(_mes_like_legible(valores[col_mes], tipo_mes_like(col_mes)))
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
    """'2026-03' → (2026, 3). Acepta 'YYYY-M', 'YYYY/MM' y 'YYYY' (mes 1/12
    lo decide el caller). Devuelve None si no parsea."""
    if texto is None:
        return None
    s = str(texto).strip()
    m = re.match(r"^(\d{4})[-/](\d{1,2})$", s)
    if m:
        mes = int(m.group(2))
        if 1 <= mes <= 12:
            return (int(m.group(1)), mes)
        return None
    m = re.match(r"^(\d{4})$", s)
    if m:
        return (int(m.group(1)), 0)  # 0 = mes indeterminado, el caller decide
    return None


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


def _claves_distintas(df: pd.DataFrame, cols: dict) -> set[tuple[int, int, int]]:
    """Set de claves temporales distintas presentes en `df`."""
    return {clave_temporal(row, cols) for _, row in df.iterrows()}


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

    mejor_clave: tuple[int, int, int] | None = None
    mejor_row: Mapping[str, Any] | None = None
    for _, row in df.iterrows():
        k = clave_temporal(row, cols)
        if mejor_clave is None or k > mejor_clave:
            mejor_clave, mejor_row = k, row

    if mejor_row is None:
        return _no_disponible(
            "ultima_prueba", "Sin datos cargados para este indicador.", cols
        )

    # Fijar CADA columna temporal detectada al valor de la clave máxima.
    filtros: dict[str, Any] = {}
    valores: dict[str, Any] = {}
    for rol in ("anio", "mes_like", "ordinal"):
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
    if not col_anio:
        return _no_disponible(
            "anual",
            "No se detectó una dimensión de año en los datos de este "
            "indicador — el informe anual no se puede acotar.",
            cols,
            tipo_layout="historico",
        )

    anio = hoy.year
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

    if not col_anio:
        return _no_disponible(
            "semestral",
            "No se detectó una dimensión de año en los datos de este "
            "indicador — el informe semestral no se puede acotar.",
            cols,
            tipo_layout="historico",
        )
    if not col_mes:
        return _no_disponible(
            "semestral",
            "No se detectó una dimensión de mes (Mes, Fecha, Hito o "
            "Versión) — el informe semestral no se puede acotar.",
            cols,
            tipo_layout="historico",
        )

    anio = hoy.year
    semestre = semestre_de_mes(hoy.month)
    mes_ini, mes_fin = _meses_del_semestre(semestre)

    if df.empty:
        return _no_disponible(
            "semestral",
            f"Sin datos del {_describir_semestre(anio, semestre)} para este indicador.",
            cols,
            tipo_layout="historico",
        )

    semantica = tipo_mes_like(col_mes)
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
    """
    filtros_usuario = dict(periodo.get("filtros") or {})
    inicio = parsear_ym(periodo.get("fecha_inicio"))
    fin = parsear_ym(periodo.get("fecha_fin"))

    # "2026" sin mes: inicio → enero, fin → diciembre.
    if inicio and inicio[1] == 0:
        inicio = (inicio[0], 1)
    if fin and fin[1] == 0:
        fin = (fin[0], 12)

    filtros: dict[str, Any] = dict(filtros_usuario)
    col_anio = cols.get("anio")
    col_mes = cols.get("mes_like")
    semantica = tipo_mes_like(col_mes)

    if (inicio or fin) and not (col_anio or col_mes):
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
        filas_ok: list[int] = []

        for idx, row in base.iterrows():
            anio = _a_entero(row.get(col_anio)) if col_anio else None
            mes = a_numero_mes(row.get(col_mes), semantica) if col_mes else None

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

        if not filas_ok:
            return _no_disponible(
                "personalizado",
                "Sin datos en el período seleccionado.",
                cols,
            )

        if col_anio and anios_ok:
            filtros[col_anio] = sorted(anios_ok)
        if col_mes and meses_ok:
            filtros[col_mes] = sorted(
                meses_ok, key=lambda v: (a_numero_mes(v, semantica) or 0, str(v))
            )

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
    cols = detectar_columnas_temporales(df.columns)

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

def elegir_df_temporal(dataframes: Mapping[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
    """Elige el DataFrame más apto para resolver períodos.

    Prefiere el rol "estudiantes"; si no lo tiene (o no aporta columnas
    temporales) toma el que más columnas temporales detecte. None si el
    dict está vacío.
    """
    if not dataframes:
        return None

    def _puntaje(df: pd.DataFrame) -> int:
        cols = detectar_columnas_temporales(df.columns)
        return sum(1 for k in ("anio", "mes_like", "ordinal") if cols.get(k))

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
) -> ResultadoPeriodo:
    """`resolver_periodo` sobre el dict {rol: df} de `cargar_dataframes_indicator`."""
    df = elegir_df_temporal(dataframes)
    if df is None:
        return _no_disponible(
            (periodo or {}).get("tipo") or "ultima_prueba",
            "Sin datos cargados para este indicador.",
        )
    return resolver_periodo(df, periodo, hoy)
