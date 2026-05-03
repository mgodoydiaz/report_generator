"""Motor de cálculo de campos derivados (derived_fields).

Recibe un DataFrame y una lista de configs declarativas, devuelve un
DataFrame nuevo con las columnas derivadas agregadas. Los kinds soportados
son funciones puras por kind, registradas en `KIND_REGISTRY`. El
orquestador (`apply_derived_fields`) itera la lista respetando el orden
declarado. Permite encadenamiento: una función posterior puede usar la
columna calculada por una previa.

Kinds soportados:

- `agg`: groupby por entity + agregación. Resultado broadcast a todas las
  filas del grupo. Ej: `Logro_Promedio_Estudiante = mean(Rend) por Rut`.
- `slope`: regresión lineal expansiva por entity ordenada por time_field.
  Para cada fila, calcula la pendiente usando los puntos del estudiante
  hasta esa fila inclusive. Ej: `Avance` SIMCE.
- `delta`: último valor menos primero por entity. Broadcast a todas las
  filas. Útil para "fin de año vs inicio".

Soporta `value_type: ordinal`: si los valores son cualitativos
(ej: Insuficiente, Elemental, Adecuado), se mapean a 1..N usando
`ordinal_levels` antes de calcular, y la columna resultante queda en
formato numérico (no se revierte porque la salida típicamente es numérica).
"""
from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────
# Helpers comunes
# ─────────────────────────────────────────────────────────────────────────

def _as_numeric(series: pd.Series, value_type: str, ordinal_levels: list | None) -> pd.Series:
    """Devuelve la serie como números reales.

    Si value_type == 'ordinal' usa ordinal_levels para mapear (case-insensitive,
    strip de espacios). Valores no presentes en la lista quedan como NaN.

    Si value_type == 'numeric' (o no especificado) hace pd.to_numeric con
    errores a NaN.
    """
    if value_type == "ordinal":
        if not ordinal_levels:
            raise ValueError("value_type='ordinal' requiere ordinal_levels no vacío")
        # Normalizar levels y series para matching tolerante
        levels_norm = [str(lv).strip().lower() for lv in ordinal_levels]
        mapping = {name: i + 1 for i, name in enumerate(levels_norm)}

        def _to_num(v):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return np.nan
            key = str(v).strip().lower()
            return mapping.get(key, np.nan)

        return series.map(_to_num).astype(float)
    # default numeric
    return pd.to_numeric(series, errors="coerce")


def _ordered_by_time(group: pd.DataFrame, time_field: str) -> pd.DataFrame:
    """Devuelve el grupo ordenado ascendente por time_field.

    El orden usa pd.to_numeric si es posible (para que '1','2','10' queden
    1<2<10 y no '1','10','2'). Si falla, ordena por string.
    """
    if time_field not in group.columns:
        return group
    try:
        sort_key = pd.to_numeric(group[time_field], errors="coerce")
        if sort_key.notna().any():
            return group.assign(_sort_key=sort_key).sort_values("_sort_key").drop(columns="_sort_key")
    except Exception:
        pass
    return group.sort_values(time_field)


# ─────────────────────────────────────────────────────────────────────────
# Kind: agg
# ─────────────────────────────────────────────────────────────────────────

def apply_agg(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Agregación por entity broadcast a todas las filas del grupo.

    Config esperado:
        name: nombre de la columna nueva
        value_field: columna numérica (o ordinal con ordinal_levels)
        entity_field: columna por la que agrupar (ej "Rut")
        agg: 'mean' | 'sum' | 'min' | 'max' | 'std' | 'count' | 'nunique'
        value_type: 'numeric' (default) | 'ordinal'
        ordinal_levels: lista (requerido si ordinal)
        min_points: mínimo de filas no-nulas para calcular (default 1).
                    Si la entidad tiene menos, NaN.

    Retorna df con la columna `name` agregada.
    """
    name = config["name"]
    value_field = config["value_field"]
    entity_field = config["entity_field"]
    agg_fn = config.get("agg", "mean")
    value_type = config.get("value_type", "numeric")
    ordinal_levels = config.get("ordinal_levels")
    min_points = int(config.get("min_points", 1))

    if value_field not in df.columns:
        raise KeyError(f"agg '{name}': value_field '{value_field}' no existe en el DataFrame")
    if entity_field not in df.columns:
        raise KeyError(f"agg '{name}': entity_field '{entity_field}' no existe en el DataFrame")

    df = df.copy()
    series_num = _as_numeric(df[value_field], value_type, ordinal_levels)

    # Calcular agregación + count por entity
    grouped = series_num.groupby(df[entity_field])
    agg_series = grouped.agg(agg_fn)
    counts = grouped.count()

    # Aplicar min_points: entidades con count < min_points → NaN
    if min_points > 1:
        agg_series = agg_series.where(counts >= min_points, other=np.nan)

    # Broadcast a cada fila vía map
    df[name] = df[entity_field].map(agg_series)
    return df


# ─────────────────────────────────────────────────────────────────────────
# Kind: slope (regresión lineal expansiva por entity)
# ─────────────────────────────────────────────────────────────────────────

def apply_slope(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Pendiente de regresión lineal expansiva por entity.

    Para cada fila:
        - Toma todas las filas previas + la actual del mismo `entity_field`,
          ordenadas por `time_field`.
        - Calcula la pendiente lineal (np.polyfit grado 1) sobre los puntos
          (time_field, value_field).
        - Si hay menos de `min_points` (default 2), valor = NaN.

    Config esperado:
        name, value_field, entity_field, time_field
        value_type, ordinal_levels (idem agg)
        min_points (default 2)

    Retorna df con la columna `name` agregada.
    """
    name = config["name"]
    value_field = config["value_field"]
    entity_field = config["entity_field"]
    time_field = config["time_field"]
    value_type = config.get("value_type", "numeric")
    ordinal_levels = config.get("ordinal_levels")
    min_points = int(config.get("min_points", 2))

    for f in (value_field, entity_field, time_field):
        if f not in df.columns:
            raise KeyError(f"slope '{name}': columna '{f}' no existe en el DataFrame")

    time_type = config.get("time_type", "numeric")
    time_ordinal_levels = config.get("time_ordinal_levels")

    df = df.copy()
    df["_value_num"] = _as_numeric(df[value_field], value_type, ordinal_levels)
    df["_time_num"] = _as_numeric(df[time_field], time_type, time_ordinal_levels)

    # Para cada entidad, ordenar y calcular pendiente expansiva.
    # Inicializamos la columna con NaN.
    result = pd.Series(index=df.index, dtype=float)

    for entity_value, group in df.groupby(entity_field, sort=False):
        ordered = group.sort_values("_time_num", kind="mergesort")
        x_values = ordered["_time_num"].to_numpy()
        y_values = ordered["_value_num"].to_numpy()

        for i, (idx, _row) in enumerate(ordered.iterrows()):
            # Tomar los puntos hasta i inclusive
            x_slice = x_values[: i + 1]
            y_slice = y_values[: i + 1]
            # Filtrar NaN en cualquiera de las dos series
            mask = ~(np.isnan(x_slice) | np.isnan(y_slice))
            x_clean = x_slice[mask]
            y_clean = y_slice[mask]
            if len(x_clean) < min_points or len(np.unique(x_clean)) < 2:
                result.loc[idx] = np.nan
                continue
            try:
                # polyfit grado 1: [pendiente, intercepto]
                slope = np.polyfit(x_clean, y_clean, 1)[0]
                result.loc[idx] = float(slope)
            except (np.linalg.LinAlgError, ValueError):
                result.loc[idx] = np.nan

    df[name] = result
    df.drop(columns=["_value_num", "_time_num"], inplace=True)
    return df


# ─────────────────────────────────────────────────────────────────────────
# Kind: delta (último valor menos primero por entity)
# ─────────────────────────────────────────────────────────────────────────

def apply_delta(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Diferencia último - primero por entity, broadcast a todas las filas.

    Config esperado:
        name, value_field, entity_field, time_field
        value_type, ordinal_levels (idem agg)
        min_points (default 2)

    Retorna df con la columna `name` agregada.
    """
    name = config["name"]
    value_field = config["value_field"]
    entity_field = config["entity_field"]
    time_field = config["time_field"]
    value_type = config.get("value_type", "numeric")
    ordinal_levels = config.get("ordinal_levels")
    min_points = int(config.get("min_points", 2))

    for f in (value_field, entity_field, time_field):
        if f not in df.columns:
            raise KeyError(f"delta '{name}': columna '{f}' no existe en el DataFrame")

    time_type = config.get("time_type", "numeric")
    time_ordinal_levels = config.get("time_ordinal_levels")

    df = df.copy()
    df["_value_num"] = _as_numeric(df[value_field], value_type, ordinal_levels)
    df["_time_num"] = _as_numeric(df[time_field], time_type, time_ordinal_levels)

    deltas: dict[Any, float] = {}
    for entity_value, group in df.groupby(entity_field, sort=False):
        valid = group.dropna(subset=["_value_num", "_time_num"])
        if len(valid) < min_points:
            deltas[entity_value] = np.nan
            continue
        ordered = valid.sort_values("_time_num", kind="mergesort")
        deltas[entity_value] = float(ordered["_value_num"].iloc[-1] - ordered["_value_num"].iloc[0])

    df[name] = df[entity_field].map(deltas)
    df.drop(columns=["_value_num", "_time_num"], inplace=True)
    return df


# ─────────────────────────────────────────────────────────────────────────
# Registry + orquestador
# ─────────────────────────────────────────────────────────────────────────

KIND_REGISTRY: dict[str, dict[str, Any]] = {
    "agg": {
        "fn": apply_agg,
        "display_name": "Agregación por entidad",
        "description": "Agrupa por entity y agrega (mean, sum, min, max, std, count, nunique). Broadcast a todas las filas del grupo.",
        "required_args": ["name", "value_field", "entity_field"],
        "optional_args": ["agg", "value_type", "ordinal_levels", "min_points"],
    },
    "slope": {
        "fn": apply_slope,
        "display_name": "Pendiente lineal expansiva",
        "description": "Para cada fila, regresión lineal sobre (time_field, value_field) usando los puntos hasta esa fila del mismo entity. Útil para Avance del estudiante.",
        "required_args": ["name", "value_field", "entity_field", "time_field"],
        "optional_args": ["value_type", "ordinal_levels", "time_type", "time_ordinal_levels", "min_points"],
    },
    "delta": {
        "fn": apply_delta,
        "display_name": "Último menos primero",
        "description": "Diferencia entre el último valor y el primero por entity, broadcast a todas las filas.",
        "required_args": ["name", "value_field", "entity_field", "time_field"],
        "optional_args": ["value_type", "ordinal_levels", "time_type", "time_ordinal_levels", "min_points"],
    },
}


def apply_derived_fields(df: pd.DataFrame, configs: list[dict]) -> pd.DataFrame:
    """Orquestador: aplica una lista de derived_fields en orden.

    Cada config debe tener al menos `kind` y los args requeridos por ese
    kind. Las funciones se ejecutan secuencialmente en el orden declarado;
    una posterior puede usar columnas creadas por una previa (encadenamiento
    transparente vía nombre de columna).

    Args:
        df: DataFrame de entrada.
        configs: lista de dicts {kind, name, ...args}.

    Returns:
        Nuevo DataFrame con las columnas derivadas agregadas. No muta el
        DataFrame original.

    Raises:
        ValueError: si algún kind no existe en el registry o falta un arg
            requerido.
        KeyError: si una columna referenciada no está en el DataFrame al
            momento de ejecutarse.
    """
    if not configs:
        return df.copy()

    out = df.copy()
    for i, config in enumerate(configs):
        if not isinstance(config, dict):
            raise ValueError(f"derived_fields[{i}] debe ser un dict, recibido: {type(config).__name__}")
        kind = config.get("kind")
        if kind not in KIND_REGISTRY:
            raise ValueError(
                f"derived_fields[{i}].kind = '{kind}' no soportado. "
                f"Disponibles: {list(KIND_REGISTRY.keys())}"
            )
        spec = KIND_REGISTRY[kind]
        # Validar args requeridos
        missing = [a for a in spec["required_args"] if a not in config]
        if missing:
            raise ValueError(
                f"derived_fields[{i}] (kind={kind}): args requeridos faltantes: {missing}"
            )
        # Ejecutar
        fn: Callable[[pd.DataFrame, dict], pd.DataFrame] = spec["fn"]
        out = fn(out, config)
    return out
