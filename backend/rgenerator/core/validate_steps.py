"""Steps de validación de DataFrames."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

import pandas as pd

from .step import Step


def _check_type(series: pd.Series, expected: str) -> List[str]:
    """Devuelve lista de índices que no cumplen el tipo. Lista vacía = OK.

    `expected` ∈ {"int", "float", "number", "str", "bool"}.
    """
    if expected in ("int", "float", "number"):
        coerced = pd.to_numeric(series, errors="coerce")
        # Cualquier valor no-NaN en original que quedó NaN tras coerce → fallo
        bad = series[coerced.isna() & series.notna()]
        if expected == "int":
            # int debe ser entero (no 1.5). Comparamos con su floor.
            non_null = coerced.dropna()
            non_int = non_null[non_null != non_null.apply(lambda v: float(int(v)))]
            return list(bad.index.tolist()) + list(non_int.index.tolist())
        return list(bad.index.tolist())
    if expected == "str":
        bad = series[series.notna() & ~series.map(lambda v: isinstance(v, str))]
        return list(bad.index.tolist())
    if expected == "bool":
        bad = series[series.notna() & ~series.map(lambda v: isinstance(v, bool))]
        return list(bad.index.tolist())
    raise ValueError(f"Tipo no soportado: '{expected}'")


def _check_range(series: pd.Series, mn=None, mx=None) -> List[int]:
    """Índices fuera de [mn, mx]. None = abierto."""
    coerced = pd.to_numeric(series, errors="coerce")
    bad_idx = []
    if mn is not None:
        bad_idx.extend(coerced[coerced < float(mn)].index.tolist())
    if mx is not None:
        bad_idx.extend(coerced[coerced > float(mx)].index.tolist())
    return list(set(bad_idx))


def _check_regex(series: pd.Series, pattern: str) -> List[int]:
    rx = re.compile(pattern)
    def _match(v):
        if pd.isna(v):
            return True  # nulls se chequean en otra regla
        return bool(rx.search(str(v)))
    bad = series[~series.map(_match)]
    return list(bad.index.tolist())


def _check_allowed(series: pd.Series, allowed: list) -> List[int]:
    allowed_set = set(allowed)
    bad = series[series.notna() & ~series.isin(allowed_set)]
    return list(bad.index.tolist())


class ValidateDataframe(Step):
    """Valida un DataFrame contra un schema declarativo.

    Uso típico: justo antes de `SaveToMetric` para evitar que basura
    llegue a `metric_data`.

    Parámetros del step:
        input_key: clave del artifact (DataFrame) a validar.
        schema (dict, opcional): si no se entrega se lee de
            ctx.params["validation_schema"].
        mode: 'strict' (default) lanza ValueError si hay errores;
              'warn' loguea warnings y pasa.

    Schema:
        {
          "required_columns": ["Logro", "Curso", "Hito"],
          "min_rows": 1,
          "columns": {
            "Logro": {
              "type": "float",          # int|float|number|str|bool
              "min": 0, "max": 1,       # rango numérico
              "nullable": false         # si false, NaN cuenta como error
            },
            "Curso": {"type": "str", "regex": "^[1-9I]+ ?[A-Z]?$"},
            "Hito":  {"type": "str", "allowed": ["DIAGNOSTICO","INTERMEDIO","FINAL"]}
          }
        }

    Efectos: passthrough — el DataFrame queda igual en el artifact de
    entrada. No produce un artifact nuevo.
    """

    def __init__(
        self,
        input_key: Optional[str] = None,
        schema: Optional[Dict] = None,
        mode: str = "strict",
    ):
        super().__init__(name="ValidateDataframe", requires=[input_key] if input_key else [])
        self.input_key = input_key
        self.schema = schema or {}
        if mode not in ("strict", "warn"):
            raise ValueError(f"mode debe ser 'strict' o 'warn', recibido '{mode}'")
        self.mode = mode

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)

        input_key = self.input_key or ctx.last_artifact_key
        if not input_key:
            raise ValueError(f"[{self.name}] No se pudo resolver input_key.")
        self.input_key = input_key

        schema = self.schema or ctx.params.get("validation_schema") or {}
        if not schema:
            self._log(f"[{self.name}] Sin schema; passthrough.")
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        df = ctx.artifacts.get(input_key)
        if df is None:
            raise ValueError(f"[{self.name}] Artifact '{input_key}' no encontrado.")
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"[{self.name}] Artifact '{input_key}' no es DataFrame.")

        errors: List[str] = []

        # 1. Required columns
        required = schema.get("required_columns", [])
        missing = [c for c in required if c not in df.columns]
        if missing:
            errors.append(f"Faltan columnas requeridas: {missing}")

        # 2. min_rows
        min_rows = int(schema.get("min_rows", 0))
        if len(df) < min_rows:
            errors.append(f"Filas insuficientes: {len(df)} < {min_rows}")

        # 3. Reglas por columna
        cols_rules = schema.get("columns", {})
        for col, rules in cols_rules.items():
            if col not in df.columns:
                if rules.get("required", False):
                    errors.append(f"Columna '{col}' requerida no existe")
                continue
            series = df[col]

            # Nullable
            if rules.get("nullable") is False:
                n_nulls = int(series.isna().sum())
                if n_nulls > 0:
                    errors.append(f"Columna '{col}': {n_nulls} valores nulos (nullable=false)")

            # Tipo
            t = rules.get("type")
            if t:
                bad_idx = _check_type(series, t)
                if bad_idx:
                    errors.append(
                        f"Columna '{col}': {len(bad_idx)} valores no son tipo '{t}' "
                        f"(filas {bad_idx[:5]}{'...' if len(bad_idx) > 5 else ''})"
                    )

            # Rango
            mn, mx = rules.get("min"), rules.get("max")
            if mn is not None or mx is not None:
                bad_idx = _check_range(series, mn, mx)
                if bad_idx:
                    errors.append(
                        f"Columna '{col}': {len(bad_idx)} valores fuera de rango "
                        f"[{mn},{mx}] (filas {bad_idx[:5]}{'...' if len(bad_idx) > 5 else ''})"
                    )

            # Regex
            rx = rules.get("regex")
            if rx:
                bad_idx = _check_regex(series, rx)
                if bad_idx:
                    errors.append(
                        f"Columna '{col}': {len(bad_idx)} valores no matchean regex "
                        f"'{rx}' (filas {bad_idx[:5]}{'...' if len(bad_idx) > 5 else ''})"
                    )

            # Allowed
            allowed = rules.get("allowed")
            if allowed:
                bad_idx = _check_allowed(series, allowed)
                if bad_idx:
                    errors.append(
                        f"Columna '{col}': {len(bad_idx)} valores no permitidos "
                        f"(allowed={allowed}, filas {bad_idx[:5]}{'...' if len(bad_idx) > 5 else ''})"
                    )

        # 4. Reportar
        if errors:
            msg = f"[{self.name}] Validación falló para '{input_key}':\n  - " + "\n  - ".join(errors)
            if self.mode == "strict":
                raise ValueError(msg)
            self._log(msg)
        else:
            self._log(f"[{self.name}] Validación OK ({len(df)} filas, {len(cols_rules)} reglas).")

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)
