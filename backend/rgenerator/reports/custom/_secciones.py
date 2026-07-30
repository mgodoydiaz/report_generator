"""Helpers compartidos por los módulos del motor único de informes.

El prefijo `_` es deliberado: `custom/__init__.py` ignora los módulos que
empiezan con guion bajo, así que este archivo NO se registra como informe.
Es el lugar canónico de los helpers compartidos (ver `custom/README.md`).

Todas las funciones son **puras**: reciben DataFrames y parámetros, y
devuelven dicts de sección con el formato que consume
`runtime._ejecutar_seccion` (`{tipo, titulo, fn, df_input, params,
break_before?}`) o DataFrames ya calculados. Ninguna toca la DB ni el
filesystem.

Contenido (contrato del motor único, §3 / ítem N6):

    bloque_titulo              título + subtítulo + período de la 1ª página
    seccion_resumen            azúcar sobre `tables.resumen_estadistico_basico`
    tabla_resumen_comparado    resumen actual + columna del período anterior
    seccion_resumen_comparado  sección que imprime esa tabla
    puntos_temporales          cuántos puntos distintos hay en el eje tiempo
    seccion_evolucion          envuelve una sección de evolución y la omite
                               cuando hay un único punto temporal
    tabla_riesgo_persistente   alumnos en el peor nivel en N evaluaciones
                               consecutivas
    secciones_por_curso        bloque `secciones_dinamicas` del esquema

**Salvedad vinculante del dueño (OK de fase 2, 2026-07-30)**: NO hay
portada de página completa. Lo que en el contrato se llamaba
`secciones_portada` es solo un BLOQUE DE TÍTULO en la primera página,
seguido inmediatamente del contenido — igual que todos los PDF de
referencia (Pullinque, IDEL Panguipulli). Por eso `bloque_titulo` devuelve
las claves `title`/`subtitle`/`filters_label` del esquema (que
`templates/informe_base.html` ya renderiza arriba de la primera página) y
NO una lista de secciones con `page_break`.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Sequence

import pandas as pd

from .. import periodos
from ..helpers import (
    MARCA_SIN_DATO,
    clave_orden_temporal,
    formatear_serie,
    ordenar_valores_categoricos,
    serie_identidad_estudiante,
)
from ..tables import resumen_estadistico_basico


__all__ = [
    "bloque_titulo",
    "secciones_portada",
    "seccion_resumen",
    "tabla_resumen_comparado",
    "seccion_resumen_comparado",
    "puntos_temporales",
    "seccion_evolucion",
    "tabla_riesgo_persistente",
    "secciones_por_curso",
]


# ─────────────────────────────────────────────────────────────────────────
# 1) Bloque de título (NO portada de página completa)
# ─────────────────────────────────────────────────────────────────────────

def bloque_titulo(
    *,
    titulo: str,
    establecimiento: Optional[str] = None,
    asignatura: Optional[str] = None,
    periodo_desc: str = "",
) -> dict:
    """Claves `title` / `subtitle` / `filters_label` de la primera página.

    Semántica (decisión transversal de las fichas, §7):
        title           nombre del informe + asignatura/nivel cuando aplique
        subtitle        nombre del establecimiento
        filters_label   período ya resuelto contra los datos

    Las tres las renderiza `templates/informe_base.html` al principio del
    documento, sin salto de página: es el bloque de título que pidió el
    dueño, no una portada.

    Args:
        titulo: nombre del informe ("Informe Ensayo SIMCE").
        establecimiento: nombre del establecimiento, si el informe cubre uno
            solo (`branding.valor_unico` devuelve None cuando hay varios).
        asignatura: asignatura del informe, si aplica.
        periodo_desc: período resuelto ("MAYO 2026", "1er semestre 2026").

    Returns:
        Dict con las tres claves, listo para mergear en el esquema.

    Ejemplo:
        >>> bloque_titulo(titulo="Informe Ensayo SIMCE", establecimiento="Pullinque",
        ...               asignatura="Matemáticas", periodo_desc="MAYO 2026")
        {'title': 'Informe Ensayo SIMCE — Matemáticas', 'subtitle': 'Pullinque', 'filters_label': 'MAYO 2026'}
    """
    partes = [str(titulo or "").strip()]
    asig = str(asignatura or "").strip()
    if asig:
        partes.append(asig)
    return {
        "title": " — ".join(p for p in partes if p),
        "subtitle": str(establecimiento or "").strip(),
        "filters_label": str(periodo_desc or "").strip(),
    }


#: Alias con el nombre que usa el contrato (§3.1). Se conserva para que la
#: trazabilidad contrato ↔ código sea directa, pero la implementación es la
#: del bloque de título: la portada de página completa quedó descartada.
secciones_portada = bloque_titulo


# ─────────────────────────────────────────────────────────────────────────
# 2) Cuadros resumen
# ─────────────────────────────────────────────────────────────────────────

def seccion_resumen(
    df_key: str,
    *,
    columna: str,
    titulo: str,
    formato: str = "percent",
    agrupar_por: str = "Curso",
) -> dict:
    """Sección de `tables.resumen_estadistico_basico` (Alumnos/Prom/Mín/Máx).

    Args:
        df_key: key del DataFrame en el dict que recibe el runtime.
        columna: columna numérica a resumir ("Rend", "Simce").
        titulo: título de la sección.
        formato: "percent" | "number".
        agrupar_por: columna categórica de agrupación.

    Returns:
        Dict de sección tipo "table".
    """
    return {
        "tipo": "table",
        "titulo": titulo,
        "fn": "resumen_estadistico_basico",
        "df_input": df_key,
        "params": {
            "columna": columna,
            "formato": formato,
            "agrupar_por": agrupar_por,
        },
    }


def tabla_resumen_comparado(
    df_actual: pd.DataFrame,
    df_previo: Optional[pd.DataFrame],
    *,
    columna: str,
    etiqueta_actual: str = "Período actual",
    etiqueta_previo: str = "Período anterior",
    formato: str = "percent",
    agrupar_por: str = "Curso",
) -> pd.DataFrame:
    """Resumen del período + columna con el promedio del período anterior.

    Une dos `resumen_estadistico_basico` por `agrupar_por`. Cuando no hay
    período anterior cargado (`df_previo` None o vacío) la columna sale
    completa con `MARCA_SIN_DATO` en vez de desaparecer: el lector tiene que
    ver que la comparación se intentó y que el dato no existe.

    Args:
        df_actual: filas del período del informe.
        df_previo: filas del período inmediatamente anterior, o None.
        columna: columna numérica a resumir.
        etiqueta_actual: encabezado de la columna de promedio del período.
        etiqueta_previo: encabezado de la columna comparada.
        formato: "percent" | "number".
        agrupar_por: columna categórica de agrupación.

    Returns:
        DataFrame [agrupar_por, Alumnos, <etiqueta_actual>, Mínimo, Máximo,
        <etiqueta_previo>].
    """
    base = resumen_estadistico_basico(
        df_actual, columna=columna, formato=formato, agrupar_por=agrupar_por,
    )
    base = base.rename(columns={"Promedio": etiqueta_actual})

    if df_previo is None or len(df_previo) == 0 or agrupar_por not in df_previo.columns:
        base[etiqueta_previo] = MARCA_SIN_DATO
        return base

    promedios = (
        df_previo.groupby(agrupar_por)[columna].mean()
        if columna in df_previo.columns
        else pd.Series(dtype="float64")
    )
    base[etiqueta_previo] = formatear_serie(
        base[agrupar_por].map(promedios),
        "percent" if formato == "percent" else "number",
    )
    return base


def seccion_resumen_comparado(df_key: str, *, titulo: str) -> dict:
    """Sección que imprime la tabla de `tabla_resumen_comparado`.

    La tabla la calcula el módulo (necesita DOS DataFrames y el runtime solo
    pasa uno por sección), la publica como un `df_input` más y esta sección
    la imprime con `tables.tabla_desde_dataframe`.

    Args:
        df_key: key del DataFrame YA calculado.
        titulo: título de la sección.
    """
    return {
        "tipo": "table",
        "titulo": titulo,
        "fn": "tabla_desde_dataframe",
        "df_input": df_key,
        "params": {},
    }


# ─────────────────────────────────────────────────────────────────────────
# 3) Evolución period-aware (decisión 16)
# ─────────────────────────────────────────────────────────────────────────

def puntos_temporales(
    df: Optional[pd.DataFrame],
    columna_temporal: Optional[str] = None,
    tipos: Optional[Mapping[str, Any]] = None,
) -> int:
    """Cuántos puntos distintos hay en el eje temporal de `df`.

    Con `columna_temporal` cuenta los valores distintos de esa columna
    combinados con el año cuando existe (para que "MAYO 2025" y "MAYO 2026"
    no colapsen en un solo punto). Sin ella detecta el eje con
    `periodos.detectar_columnas_temporales_df`.

    Returns:
        Número de puntos temporales distintos. 0 si no hay datos o no se
        detectó ninguna columna temporal.
    """
    if df is None or len(df) == 0:
        return 0

    cols = periodos.detectar_columnas_temporales_df(df, tipos)
    col_mes = columna_temporal or cols.get("mes_like") or cols.get("ordinal")
    col_anio = cols.get("anio")

    claves: list[str] = []
    if col_mes and col_mes in df.columns:
        claves.append(col_mes)
    if col_anio and col_anio in df.columns and col_anio not in claves:
        claves.append(col_anio)
    if not claves:
        return 0

    return int(df[claves].dropna(how="all").astype(str).drop_duplicates().shape[0])


def seccion_evolucion(
    seccion: dict,
    df: Optional[pd.DataFrame],
    columna_temporal: Optional[str] = None,
    tipos: Optional[Mapping[str, Any]] = None,
) -> list[dict]:
    """`[seccion]` si hay ≥2 puntos temporales; `[]` si hay uno solo.

    Decisión 16 de las fichas: un gráfico de "evolución" con un único punto
    en el tiempo no es un gráfico de evolución — es una barra suelta que
    induce a error. La sección se auto-omite en silencio (sin aviso de
    error), y es el módulo el que pone en el informe la nota que explica por
    qué no está.

    Args:
        seccion: dict de sección ya construido.
        df: DataFrame que alimentaría la sección.
        columna_temporal: eje temporal ("Mes", "Hito", "Versión"). Sin ella
            se detecta.
        tipos: `{columna: data_type}` del catálogo de dimensiones.

    Returns:
        Lista con 0 o 1 secciones, lista para extender el esquema.
    """
    if puntos_temporales(df, columna_temporal, tipos) <= 1:
        return []
    return [seccion]


# ─────────────────────────────────────────────────────────────────────────
# 4) Riesgo persistente (decisión 2)
# ─────────────────────────────────────────────────────────────────────────

def _orden_evaluaciones(valores: Iterable[Any]) -> list[str]:
    """Evaluaciones ordenadas cronológicamente (meses, hitos, versiones)."""
    return sorted({str(v) for v in valores if str(v).strip()}, key=clave_orden_temporal)


def _etiquetas_posicionales(n: int) -> list[str]:
    """Sufijos de las columnas de puntaje: ['previo', 'actual'] con n=2."""
    if n == 2:
        return ["previo", "actual"]
    return [f"#{i + 1}" for i in range(n)]


def tabla_riesgo_persistente(
    df: pd.DataFrame,
    *,
    columna_nivel: str,
    nivel_objetivo: str,
    columna_temporal: str,
    n_evaluaciones: int = 2,
    columnas_puntaje: Optional[Sequence[str]] = None,
    columna_curso: str = "Curso",
    columna_nombre: Optional[str] = None,
    formatos: Optional[Mapping[str, str]] = None,
) -> pd.DataFrame:
    """Alumnos en el peor nivel en las N evaluaciones consecutivas finales.

    Criterio inicial acordado en el contrato (§3.3, calibrable en el
    piloto): un estudiante entra si su `columna_nivel` es `nivel_objetivo`
    en las `n_evaluaciones` últimas evaluaciones **consecutivas presentes
    para él**. Un alumno que rindió una sola evaluación NO entra: no hay
    persistencia que demostrar.

    La identidad sale de `helpers.serie_identidad_estudiante` (RUT →
    Nombre_Norm → Nombre → Curso+N° Lista), que es lo que hace funcionar
    esto también donde el RUT viene vacío (Cálculo Veloz).

    Args:
        df: DataFrame del período, con todas sus evaluaciones.
        columna_nivel: "Logro" (SIMCE), "Nivel" (DIA/IDEL), "Nivel_Logro".
        nivel_objetivo: "Insuficiente" / "Crítico" / "INICIAL".
        columna_temporal: "Mes" / "Hito" / "Versión".
        n_evaluaciones: cuántas evaluaciones consecutivas exige el criterio.
        columnas_puntaje: columnas de puntaje a mostrar, una por evaluación
            (ej ["Rend", "Simce"]).
        columna_curso: columna de curso.
        columna_nombre: columna con el nombre visible. Sin ella se toma la
            primera de nombre que exista en el df.
        formatos: `{columna_puntaje: "percent"|"number"}` para el formato de
            las celdas.

    Returns:
        DataFrame `Curso · Estudiante · Evaluaciones · <puntaje previo> ·
        <puntaje actual> · … · Nivel`, ordenado por curso (orden natural) y
        puntaje ascendente. **Vacío** cuando no hay segunda evaluación o
        nadie cumple el criterio: el módulo omite la sección igual que con
        la evolución.

        Los encabezados de puntaje son POSICIONALES ("Rend previo", "Rend
        actual") y la columna `Evaluaciones` dice cuáles son para esa fila.
        Nombrar las columnas con el mes de cada estudiante multiplicaba la
        tabla: alumnos que rindieron pares distintos (ABRIL-JUNIO vs
        OCTUBRE-NOVIEMBRE) generaban una columna por par y el 80% de las
        celdas quedaban en "—".
    """
    requeridas = {columna_nivel, columna_temporal}
    if df is None or len(df) == 0 or not requeridas.issubset(set(df.columns)):
        return pd.DataFrame()

    evaluaciones = _orden_evaluaciones(df[columna_temporal].dropna().tolist())
    if len(evaluaciones) < n_evaluaciones:
        return pd.DataFrame()

    trabajo = df.copy()
    identidad = serie_identidad_estudiante(trabajo)
    if identidad is None:
        return pd.DataFrame()
    trabajo["__id"] = identidad
    trabajo["__eval"] = trabajo[columna_temporal].astype(str)

    if columna_nombre is None:
        from ..helpers import columnas_nombre_estudiante
        nombres = columnas_nombre_estudiante(trabajo)
        columna_nombre = nombres[0] if nombres else None

    posicion = {ev: i for i, ev in enumerate(evaluaciones)}
    filas: list[dict] = []

    for ident, grupo in trabajo.groupby("__id", sort=False):
        # Una fila por evaluación (si hay varias, la última gana).
        por_eval = {
            ev: sub.iloc[-1]
            for ev, sub in grupo.groupby("__eval", sort=False)
            if ev in posicion
        }
        if len(por_eval) < n_evaluaciones:
            continue
        presentes = sorted(por_eval, key=lambda e: posicion[e])
        ultimas = presentes[-n_evaluaciones:]
        # Consecutivas en el calendario del período: sin esto, un alumno con
        # ABRIL y NOVIEMBRE contaría como "dos evaluaciones seguidas".
        indices = [posicion[e] for e in ultimas]
        if indices != list(range(indices[0], indices[0] + n_evaluaciones)):
            continue
        if any(
            str(por_eval[e].get(columna_nivel)).strip() != str(nivel_objetivo).strip()
            for e in ultimas
        ):
            continue

        ultima = por_eval[ultimas[-1]]
        fila: dict[str, Any] = {
            "Curso": ultima.get(columna_curso, MARCA_SIN_DATO),
            "Estudiante": (
                ultima.get(columna_nombre) if columna_nombre else str(ident)
            ),
            "Evaluaciones": " → ".join(ultimas),
        }
        etiquetas = _etiquetas_posicionales(n_evaluaciones)
        for col in (columnas_puntaje or []):
            for etiqueta, ev in zip(etiquetas, ultimas):
                fila[f"{col} {etiqueta}"] = por_eval[ev].get(col)
        fila["Nivel"] = ultima.get(columna_nivel)
        col_orden = (columnas_puntaje or [None])[0]
        fila["__orden"] = (
            _valor_numerico(ultima.get(col_orden)) if col_orden else 0.0
        )
        filas.append(fila)

    if not filas:
        return pd.DataFrame()

    salida = pd.DataFrame(filas)
    orden_cursos = ordenar_valores_categoricos(
        sorted({str(c) for c in salida["Curso"]}), "Curso"
    )
    salida["__curso_orden"] = salida["Curso"].astype(str).map(
        {c: i for i, c in enumerate(orden_cursos)}
    )
    salida = salida.sort_values(by=["__curso_orden", "__orden"], na_position="last")
    salida = salida.drop(columns=["__curso_orden", "__orden"]).reset_index(drop=True)

    formatos = dict(formatos or {})
    for col in salida.columns:
        base = col.rsplit(" ", 1)[0]
        fmt = formatos.get(col) or formatos.get(base)
        if fmt:
            salida[col] = formatear_serie(salida[col], fmt)
    return salida


def _valor_numerico(valor: Any) -> float:
    """Float del valor, o +inf para que los faltantes queden al final."""
    try:
        num = float(valor)
    except (TypeError, ValueError):
        return float("inf")
    return float("inf") if pd.isna(num) else num


# ─────────────────────────────────────────────────────────────────────────
# 5) Iteración por curso
# ─────────────────────────────────────────────────────────────────────────

def secciones_por_curso(
    secciones: list[dict],
    *,
    df_iterar: str,
    iterar_por: str = "Curso",
) -> dict:
    """Bloque `secciones_dinamicas` del esquema (una página por curso).

    El runtime ya resuelve el orden natural de los valores
    (`helpers.ordenar_valores_categoricos`) y emite un `page_break` antes de
    cada uno; este helper existe para que los módulos no repitan la
    estructura ni se olviden de alguna clave.

    Args:
        secciones: plantillas de sección; `{curso}` se interpola por valor.
        df_iterar: key del DataFrame del que salen los valores.
        iterar_por: columna a iterar.
    """
    return {
        "iterar_por": iterar_por,
        "df_iterar": df_iterar,
        "secciones": list(secciones),
    }
