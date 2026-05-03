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

def _resolve_entity_keys(df: pd.DataFrame, entity_field, label: str) -> list[str]:
    """Normaliza entity_field a lista de columnas y valida existencia.

    Acepta string ("Rut") o lista (["Curso", "Nombre"]) para soportar
    groupby compuesto cuando no hay un id único de estudiante.
    """
    keys = entity_field if isinstance(entity_field, (list, tuple)) else [entity_field]
    keys = list(keys)
    missing = [k for k in keys if k not in df.columns]
    if missing:
        raise KeyError(f"{label}: entity_field columnas inexistentes: {missing}")
    return keys


def apply_agg(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Agregación por entity broadcast a todas las filas del grupo.

    Config esperado:
        name: nombre de la columna nueva
        value_field: columna numérica (o ordinal con ordinal_levels)
        entity_field: columna o lista de columnas por las que agrupar.
            Ej "Rut" (1 columna) o ["Curso", "Nombre"] (compuesto).
        agg: 'mean' | 'sum' | 'min' | 'max' | 'std' | 'count' | 'nunique'
        value_type: 'numeric' (default) | 'ordinal'
        ordinal_levels: lista (requerido si ordinal)
        min_points: mínimo de filas no-nulas para calcular (default 1).
                    Si la entidad tiene menos, NaN.

    Retorna df con la columna `name` agregada.
    """
    name = config["name"]
    value_field = config["value_field"]
    entity_keys = _resolve_entity_keys(df, config["entity_field"], f"agg '{name}'")
    agg_fn = config.get("agg", "mean")
    value_type = config.get("value_type", "numeric")
    ordinal_levels = config.get("ordinal_levels")
    min_points = int(config.get("min_points", 1))

    if value_field not in df.columns:
        raise KeyError(f"agg '{name}': value_field '{value_field}' no existe en el DataFrame")

    df = df.copy()
    series_num = _as_numeric(df[value_field], value_type, ordinal_levels)

    # Calcular agregación + count por entity (uno o varios campos)
    group_keys = [df[k] for k in entity_keys]
    grouped = series_num.groupby(group_keys)
    agg_series = grouped.agg(agg_fn)
    counts = grouped.count()

    # Aplicar min_points: entidades con count < min_points → NaN
    if min_points > 1:
        agg_series = agg_series.where(counts >= min_points, other=np.nan)

    # Broadcast a cada fila usando merge (soporta multi-key)
    if len(entity_keys) == 1:
        df[name] = df[entity_keys[0]].map(agg_series)
    else:
        agg_df = agg_series.reset_index().rename(columns={agg_series.name or 0: name})
        # Si la serie no tiene name, queda en columna 0 tras reset_index
        if name not in agg_df.columns:
            cols_no_keys = [c for c in agg_df.columns if c not in entity_keys]
            agg_df = agg_df.rename(columns={cols_no_keys[0]: name})
        # Si la columna `name` ya existía en df (re-aplicación), drop antes
        # del merge para evitar sufijos _x/_y de pandas.
        if name in df.columns:
            df = df.drop(columns=[name])
        df = df.merge(agg_df[entity_keys + [name]], on=entity_keys, how="left")
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
    entity_keys = _resolve_entity_keys(df, config["entity_field"], f"slope '{name}'")
    time_field = config["time_field"]
    value_type = config.get("value_type", "numeric")
    ordinal_levels = config.get("ordinal_levels")
    min_points = int(config.get("min_points", 2))

    for f in (value_field, time_field):
        if f not in df.columns:
            raise KeyError(f"slope '{name}': columna '{f}' no existe en el DataFrame")

    time_type = config.get("time_type", "numeric")
    time_ordinal_levels = config.get("time_ordinal_levels")

    df = df.copy()
    df["_value_num"] = _as_numeric(df[value_field], value_type, ordinal_levels)
    df["_time_num"] = _as_numeric(df[time_field], time_type, time_ordinal_levels)

    # Pre-agregar por (entity, time) si hay múltiples filas con el mismo
    # punto temporal por entidad. Caso real: DIA tiene varias filas por
    # estudiante en el mismo Hito (una por subprueba: Localizar /
    # Interpretar / Reflexionar). Para slope/delta nos interesa el
    # promedio del estudiante por hito, no cada subprueba.
    agg_per_time = (
        df.dropna(subset=["_value_num", "_time_num"])
        .groupby(entity_keys + ["_time_num"], as_index=False, sort=False)["_value_num"]
        .mean()
    )

    # Para cada entidad, ordenar y calcular pendiente expansiva sobre el
    # df agregado. Mapping (entity_value, time_num) → slope value;
    # después se broadcast a todas las filas originales del par.
    group_by_arg = entity_keys[0] if len(entity_keys) == 1 else entity_keys
    slope_map: dict = {}
    for entity_value, group in agg_per_time.groupby(group_by_arg, sort=False):
        ordered = group.sort_values("_time_num", kind="mergesort").reset_index(drop=True)
        x_values = ordered["_time_num"].to_numpy()
        y_values = ordered["_value_num"].to_numpy()

        # Para cada punto temporal del estudiante, calcular slope expansivo
        # con los puntos previos + actual, y asignarlo a TODAS las filas
        # originales que tienen ese (entity, time).
        for i in range(len(ordered)):
            time_at_i = float(x_values[i])
            x_slice = x_values[: i + 1]
            y_slice = y_values[: i + 1]
            mask = ~(np.isnan(x_slice) | np.isnan(y_slice))
            x_clean = x_slice[mask]
            y_clean = y_slice[mask]
            if len(x_clean) < min_points or len(np.unique(x_clean)) < 2:
                slope_val = np.nan
            else:
                try:
                    slope_val = float(np.polyfit(x_clean, y_clean, 1)[0])
                except (np.linalg.LinAlgError, ValueError):
                    slope_val = np.nan
            slope_map[(entity_value, time_at_i)] = slope_val

    # Broadcast: para cada fila original, lookup por (entity_value, time_num)
    def _lookup(row):
        if len(entity_keys) == 1:
            ev = row[entity_keys[0]]
        else:
            ev = tuple(row[k] for k in entity_keys)
        tn = row["_time_num"]
        if pd.isna(tn):
            return np.nan
        return slope_map.get((ev, float(tn)), np.nan)

    df[name] = df.apply(_lookup, axis=1)
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
    entity_keys = _resolve_entity_keys(df, config["entity_field"], f"delta '{name}'")
    time_field = config["time_field"]
    value_type = config.get("value_type", "numeric")
    ordinal_levels = config.get("ordinal_levels")
    min_points = int(config.get("min_points", 2))

    for f in (value_field, time_field):
        if f not in df.columns:
            raise KeyError(f"delta '{name}': columna '{f}' no existe en el DataFrame")

    time_type = config.get("time_type", "numeric")
    time_ordinal_levels = config.get("time_ordinal_levels")

    df = df.copy()
    df["_value_num"] = _as_numeric(df[value_field], value_type, ordinal_levels)
    df["_time_num"] = _as_numeric(df[time_field], time_type, time_ordinal_levels)

    # Pre-agregar por (entity, time) — caso DIA con varias subpruebas en el
    # mismo hito. Sin esto, "primero" y "último" pueden ser dos subpruebas
    # del mismo hito, dando deltas espurios.
    agg_per_time = (
        df.dropna(subset=["_value_num", "_time_num"])
        .groupby(entity_keys + ["_time_num"], as_index=False, sort=False)["_value_num"]
        .mean()
    )

    # Calcular delta por grupo (uno o varios campos)
    group_by_arg = entity_keys[0] if len(entity_keys) == 1 else entity_keys
    delta_records = []
    for entity_value, group in agg_per_time.groupby(group_by_arg, sort=False):
        valid = group.dropna(subset=["_value_num", "_time_num"])
        if len(valid) < min_points:
            delta_val = np.nan
        else:
            ordered = valid.sort_values("_time_num", kind="mergesort")
            delta_val = float(ordered["_value_num"].iloc[-1] - ordered["_value_num"].iloc[0])
        # entity_value puede ser tupla (multi-key) o escalar
        if len(entity_keys) == 1:
            delta_records.append({entity_keys[0]: entity_value, name: delta_val})
        else:
            row = dict(zip(entity_keys, entity_value))
            row[name] = delta_val
            delta_records.append(row)

    deltas_df = pd.DataFrame(delta_records)
    # Si `name` ya existía en df (re-aplicación), drop antes del merge para
    # evitar que pandas rename a name_x / name_y.
    if name in df.columns:
        df = df.drop(columns=[name])
    df = df.merge(deltas_df, on=entity_keys, how="left")
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
