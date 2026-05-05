"""Funciones de análisis estadístico para evaluaciones académicas.

Este módulo agrupa utilidades pandas-based usadas por:
    - El motor de derived_fields (vía configs declarativas)
    - Scripts puntuales que necesitan análisis ad-hoc
    - Reportes que requieran métricas no expresables fácilmente en JSON

El motor `derived_fields_engine` ya cubre:
    agg, slope, delta, row_threshold, row_mean_dynamic, lookup_range,
    lookup_dict, normalize_name, piecewise_linear.

Acá se agregan funciones que no encajan en el patrón "una columna a la vez":
    - student_risk_flag      : etiqueta de riesgo binaria por umbral
    - milestone_slope_per_group : pendiente entre hitos ordinales
    - milestone_delta_per_group : Δ entre hito inicial y final
    - establishment_gap      : brecha entre establecimientos por curso
    - item_discrimination    : correlación item-total (calidad psicométrica)
    - performance_quartiles  : cuartiles de rendimiento por grupo

Convención: todas las funciones reciben un DataFrame y devuelven un nuevo
DataFrame (o Series) sin modificar el original. Si una función necesita
columnas que no existen, lanza KeyError con mensaje claro.
"""
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────
# Riesgo de estudiantes
# ─────────────────────────────────────────────────────────────────────────


def student_risk_flag(
    df: pd.DataFrame,
    score_col: str = "Logro",
    threshold: float = 0.4,
    require_negative_slope: bool = False,
    slope_col: Optional[str] = None,
) -> pd.Series:
    """Marca estudiantes en riesgo según logro.

    El usuario definió 2026-05-05 que "riesgo = Logro < 0.4" (insuficiente).
    Si `require_negative_slope=True` y se entrega `slope_col`, se exige
    además pendiente negativa entre hitos para reducir falsos positivos
    (ej: estudiante que ya estaba bajo y empeora).

    Args:
        df: DataFrame con la columna de puntaje.
        score_col: Nombre de la columna de logro/puntaje. Debe estar en [0,1]
            si threshold es porcentual; en otro caso, ajustar threshold.
        threshold: Umbral por debajo del cual se considera riesgo.
        require_negative_slope: Si True, exige pendiente < 0 (combina criterios).
        slope_col: Nombre de la columna con la pendiente precalculada.

    Returns:
        Serie booleana del mismo largo que df, True = en riesgo.

    Examples:
        >>> df = pd.DataFrame({"Logro": [0.3, 0.5, 0.2, 0.7]})
        >>> student_risk_flag(df).tolist()
        [True, False, True, False]
    """
    if score_col not in df.columns:
        raise KeyError(f"Columna {score_col!r} no encontrada en df")

    score = pd.to_numeric(df[score_col], errors="coerce")
    base = score < threshold

    if require_negative_slope:
        if not slope_col or slope_col not in df.columns:
            raise KeyError(
                f"require_negative_slope=True requiere slope_col válido (recibido: {slope_col!r})"
            )
        slope = pd.to_numeric(df[slope_col], errors="coerce")
        return base & (slope < 0)

    return base.fillna(False)


# ─────────────────────────────────────────────────────────────────────────
# Análisis temporal por hito
# ─────────────────────────────────────────────────────────────────────────


# Orden canónico de hitos DIA. Si la organización usa otra nomenclatura,
# pasar `ordinal=` explícito a las funciones.
DIA_MILESTONES_ORDINAL: tuple[str, ...] = ("DIAGNOSTICO", "INTERMEDIO", "CIERRE")


def milestone_slope_per_group(
    df: pd.DataFrame,
    group_cols: Sequence[str],
    milestone_col: str,
    score_col: str,
    ordinal: Sequence[str] = DIA_MILESTONES_ORDINAL,
) -> pd.DataFrame:
    """Calcula pendiente del logro promedio por grupo a lo largo de hitos.

    La pendiente se obtiene por regresión lineal simple sobre los pares
    (índice_hito, score_promedio). Útil para responder "¿qué cursos están
    mejorando vs cuáles se estancan?".

    Args:
        df: DataFrame con datos longitudinales.
        group_cols: Columnas que definen el grupo (ej ["Curso"] o
            ["Establecimiento", "Curso"]).
        milestone_col: Columna del hito (string ordinal).
        score_col: Columna de puntaje.
        ordinal: Orden canónico de los valores del milestone_col.
            Valores fuera del orden se ignoran.

    Returns:
        DataFrame con `group_cols + [n_hitos, slope, score_inicial, score_final]`.
        `slope` se expresa en "puntos por hito" (ej 0.10 = +10pp por hito).

    Examples:
        >>> df = pd.DataFrame({
        ...     "Curso": ["A","A","A","B","B"],
        ...     "Hito": ["DIAGNOSTICO","INTERMEDIO","CIERRE","DIAGNOSTICO","CIERRE"],
        ...     "Logro": [0.4, 0.55, 0.7, 0.6, 0.5],
        ... })
        >>> r = milestone_slope_per_group(df, ["Curso"], "Hito", "Logro")
        >>> round(r.set_index("Curso").loc["A", "slope"], 3)
        0.15
    """
    for col in [*group_cols, milestone_col, score_col]:
        if col not in df.columns:
            raise KeyError(f"Columna {col!r} no encontrada en df")

    ordinal_map = {name: i for i, name in enumerate(ordinal)}
    work = df[[*group_cols, milestone_col, score_col]].copy()
    work["_ord"] = work[milestone_col].map(ordinal_map)
    work[score_col] = pd.to_numeric(work[score_col], errors="coerce")
    work = work.dropna(subset=["_ord", score_col])

    if work.empty:
        cols = list(group_cols) + ["n_hitos", "slope", "score_inicial", "score_final"]
        return pd.DataFrame(columns=cols)

    avg = work.groupby([*group_cols, "_ord"], as_index=False)[score_col].mean()

    rows = []
    for keys, sub in avg.groupby(list(group_cols)):
        if not isinstance(keys, tuple):
            keys = (keys,)
        sub = sub.sort_values("_ord")
        x = sub["_ord"].to_numpy(dtype=float)
        y = sub[score_col].to_numpy(dtype=float)
        if len(x) >= 2:
            slope, _ = np.polyfit(x, y, 1)
        else:
            slope = np.nan
        rows.append({
            **dict(zip(group_cols, keys)),
            "n_hitos": int(len(x)),
            "slope": float(slope) if not np.isnan(slope) else None,
            "score_inicial": float(y[0]),
            "score_final": float(y[-1]),
        })

    return pd.DataFrame(rows)


def milestone_delta_per_group(
    df: pd.DataFrame,
    group_cols: Sequence[str],
    milestone_col: str,
    score_col: str,
    start: str = "DIAGNOSTICO",
    end: str = "CIERRE",
) -> pd.DataFrame:
    """Calcula la diferencia (end − start) del puntaje promedio por grupo.

    Más simple que `milestone_slope_per_group`: solo compara dos hitos
    explícitos. Si un grupo no tiene ambos hitos, su delta es NaN.

    Args:
        df: DataFrame.
        group_cols: Columnas de grupo.
        milestone_col: Columna del hito.
        score_col: Columna de puntaje.
        start: Hito inicial.
        end: Hito final.

    Returns:
        DataFrame con `group_cols + [score_inicio, score_fin, delta]`.
    """
    for col in [*group_cols, milestone_col, score_col]:
        if col not in df.columns:
            raise KeyError(f"Columna {col!r} no encontrada en df")

    work = df[[*group_cols, milestone_col, score_col]].copy()
    work[score_col] = pd.to_numeric(work[score_col], errors="coerce")

    avg = (
        work.groupby([*group_cols, milestone_col], as_index=False)[score_col]
        .mean()
        .rename(columns={score_col: "_avg"})
    )

    starts = avg[avg[milestone_col] == start].drop(columns=[milestone_col]).rename(
        columns={"_avg": "score_inicio"}
    )
    ends = avg[avg[milestone_col] == end].drop(columns=[milestone_col]).rename(
        columns={"_avg": "score_fin"}
    )

    out = starts.merge(ends, on=list(group_cols), how="outer")
    out["delta"] = out["score_fin"] - out["score_inicio"]
    return out


# ─────────────────────────────────────────────────────────────────────────
# Brecha entre establecimientos
# ─────────────────────────────────────────────────────────────────────────


def establishment_gap(
    df: pd.DataFrame,
    score_col: str,
    pivot_col: str = "Establecimiento",
    keys: Sequence[str] = ("Curso",),
) -> pd.DataFrame:
    """Tabla wide de promedios por establecimiento × `keys`, con brecha.

    Para análisis cross-establecimiento (ej Panguipulli vs Pullinque),
    devuelve una columna por establecimiento con el promedio del score
    y una columna `gap` con la diferencia entre el primer y último
    establecimiento en orden alfabético.

    Args:
        df: DataFrame.
        score_col: Columna numérica del puntaje.
        pivot_col: Columna a girar (típicamente Establecimiento).
        keys: Columnas índice de la tabla wide (ej Curso, Nivel).

    Returns:
        DataFrame con columnas: keys + un campo por valor de pivot_col + gap.

    Examples:
        >>> df = pd.DataFrame({
        ...     "Establecimiento": ["A","A","B","B"],
        ...     "Curso": ["1°","2°","1°","2°"],
        ...     "Logro": [0.6, 0.7, 0.5, 0.8],
        ... })
        >>> establishment_gap(df, "Logro").set_index("Curso").columns.tolist()
        ['A', 'B', 'gap']
    """
    for col in [*keys, pivot_col, score_col]:
        if col not in df.columns:
            raise KeyError(f"Columna {col!r} no encontrada en df")

    work = df[[*keys, pivot_col, score_col]].copy()
    work[score_col] = pd.to_numeric(work[score_col], errors="coerce")

    pivot = work.pivot_table(
        index=list(keys), columns=pivot_col, values=score_col, aggfunc="mean"
    )

    pivot.columns = [str(c) for c in pivot.columns]
    cols_sorted = sorted(pivot.columns)
    pivot = pivot[cols_sorted]

    if len(cols_sorted) >= 2:
        pivot["gap"] = pivot[cols_sorted[0]] - pivot[cols_sorted[-1]]

    return pivot.reset_index()


# ─────────────────────────────────────────────────────────────────────────
# Discriminación de ítems (calidad psicométrica)
# ─────────────────────────────────────────────────────────────────────────


def item_discrimination(
    df: pd.DataFrame,
    student_col: str,
    item_col: str,
    correct_col: str,
) -> pd.DataFrame:
    """Calcula índices de dificultad y discriminación por ítem.

    - **Dificultad** = % de estudiantes que respondieron correctamente.
      Convención: 0 = todos fallan, 1 = todos aciertan. Ítems con
      dificultad < 0.2 o > 0.9 suelen ser problemáticos.
    - **Discriminación** = correlación punto-biserial item-total. Mide
      cuánto el ítem distingue a estudiantes "buenos" de "malos". Valores
      > 0.3 son ideales; < 0.15 sugieren ítem mal redactado o ambiguo.

    Requiere DataFrame en formato largo: una fila por (estudiante, ítem)
    con `correct_col` ∈ {0, 1}.

    Args:
        df: DataFrame en formato largo.
        student_col: Columna que identifica al estudiante (ej RUT, Nombre).
        item_col: Columna del ítem/pregunta.
        correct_col: Columna 0/1 de respuesta correcta.

    Returns:
        DataFrame con columnas [item_col, n_respuestas, dificultad,
        discriminacion, calidad].

        `calidad` es una etiqueta heurística:
            - "buena": dificultad ∈ [0.3, 0.8] y discriminacion ≥ 0.3
            - "aceptable": dificultad ∈ [0.2, 0.9] y discriminacion ≥ 0.15
            - "revisar": fuera de los rangos anteriores

    Notes:
        El total se calcula como suma de aciertos del estudiante; la
        correlación se aproxima por rho de Pearson entre la respuesta
        binaria al ítem y el score total. No corrige por overlap (ítem
        forma parte del total), aceptable cuando hay >20 ítems.
    """
    for col in [student_col, item_col, correct_col]:
        if col not in df.columns:
            raise KeyError(f"Columna {col!r} no encontrada en df")

    work = df[[student_col, item_col, correct_col]].copy()
    work[correct_col] = pd.to_numeric(work[correct_col], errors="coerce")
    work = work.dropna(subset=[correct_col])

    if work.empty:
        return pd.DataFrame(
            columns=[item_col, "n_respuestas", "dificultad", "discriminacion", "calidad"]
        )

    totals = work.groupby(student_col)[correct_col].sum().rename("_total")
    work = work.join(totals, on=student_col)

    rows = []
    for item, sub in work.groupby(item_col):
        n = len(sub)
        dificultad = float(sub[correct_col].mean())
        if sub[correct_col].nunique() < 2 or sub["_total"].nunique() < 2:
            discriminacion = np.nan
        else:
            discriminacion = float(sub[correct_col].corr(sub["_total"]))

        if (
            np.isfinite(discriminacion)
            and 0.3 <= dificultad <= 0.8
            and discriminacion >= 0.3
        ):
            calidad = "buena"
        elif (
            np.isfinite(discriminacion)
            and 0.2 <= dificultad <= 0.9
            and discriminacion >= 0.15
        ):
            calidad = "aceptable"
        else:
            calidad = "revisar"

        rows.append({
            item_col: item,
            "n_respuestas": int(n),
            "dificultad": dificultad,
            "discriminacion": (
                None if not np.isfinite(discriminacion) else float(discriminacion)
            ),
            "calidad": calidad,
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────
# Cuartiles de rendimiento
# ─────────────────────────────────────────────────────────────────────────


def performance_quartiles(
    df: pd.DataFrame,
    group_col: str,
    score_col: str,
) -> pd.DataFrame:
    """Devuelve los cuartiles del puntaje por grupo (Q1, mediana, Q3, IQR).

    Útil para describir la dispersión interna de cada curso/nivel.
    Complementa al boxplot cuando se necesita la métrica numérica explícita.

    Args:
        df: DataFrame.
        group_col: Columna del grupo (ej Curso).
        score_col: Columna del puntaje.

    Returns:
        DataFrame con [group_col, n, Q1, mediana, Q3, IQR].
    """
    for col in [group_col, score_col]:
        if col not in df.columns:
            raise KeyError(f"Columna {col!r} no encontrada en df")

    work = df[[group_col, score_col]].copy()
    work[score_col] = pd.to_numeric(work[score_col], errors="coerce")
    work = work.dropna(subset=[score_col])

    rows = []
    for g, sub in work.groupby(group_col):
        s = sub[score_col]
        q1, med, q3 = s.quantile([0.25, 0.5, 0.75])
        rows.append({
            group_col: g,
            "n": int(len(s)),
            "Q1": float(q1),
            "mediana": float(med),
            "Q3": float(q3),
            "IQR": float(q3 - q1),
        })
    return pd.DataFrame(rows)


__all__ = [
    "DIA_MILESTONES_ORDINAL",
    "student_risk_flag",
    "milestone_slope_per_group",
    "milestone_delta_per_group",
    "establishment_gap",
    "item_discrimination",
    "performance_quartiles",
]
