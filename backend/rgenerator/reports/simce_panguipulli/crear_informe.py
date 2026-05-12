"""Constructor del informe SIMCE Panguipulli.

Variante del informe SIMCE pensada para los datos del establecimiento
Panguipulli (metrics 24 ex-EMN por Estudiante y 26 ex-EMN por Habilidad,
ahora "Resultados SIMCE Panguipulli por ...").

Diferencias clave con `simce/crear_informe.py`:
  - Recibe `df_habilidad` (metric 26) en lugar de `df_preguntas` (metric 5).
  - Trabaja con la columna `PorcLogro` en lugar de `Rend`.
  - El nivel cualitativo (Insuficiente/Elemental/Adecuado) se DERIVA en
    runtime desde PorcLogro vía `row_threshold` (definido en esquema.json).
  - No hay puntaje SIMCE estimado ni columnas Pregunta/Eje Temático.

Comparte el `runtime.py` y las bibliotecas charts/tables con SIMCE Pullinque.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .. import runtime
from ...core.derived_fields_engine import apply_derived_fields


def construir(
    df_estudiantes: pd.DataFrame,
    df_habilidad: pd.DataFrame,
    asignatura: str,
    numero_prueba: int,
    mes: str | None = None,
    overrides: dict | None = None,
) -> bytes:
    """Construye el PDF SIMCE Panguipulli para una asignatura + número de prueba.

    Args:
        df_estudiantes: DataFrame de la metric 24 (todas las pruebas).
        df_habilidad:   DataFrame de la metric 26 (logro por habilidad).
        asignatura: ej "LENGUAJE", "MATEMATICA" (mayúsculas como vienen en la DB).
        numero_prueba: número de prueba (1-4 en Panguipulli: Abril/Mayo/Agosto/Septiembre).
        mes: opcional, nombre del mes (prioridad sobre numero_prueba si está).
        overrides: opcional, dict para sobreescribir partes del esquema en
            runtime (ej {"branding": {"center_header": [...]}}).

    Returns:
        Bytes del PDF generado.
    """
    # Filtrar por asignatura. Soportamos que la columna no exista (en cuyo caso
    # se usa todo el dataset).
    if "Asignatura" in df_estudiantes.columns:
        df_estudiantes = df_estudiantes[df_estudiantes["Asignatura"] == asignatura].copy()
    if "Asignatura" in df_habilidad.columns:
        df_habilidad = df_habilidad[df_habilidad["Asignatura"] == asignatura].copy()

    # Aplicar derived_fields ANTES del filtro a una sola prueba — slope/delta
    # necesitan ver todo el histórico del estudiante. Las columnas derivadas
    # se heredan al df filtrado.
    esquema_path = Path(__file__).parent / "esquema.json"
    if esquema_path.exists():
        with open(esquema_path, encoding="utf-8") as f:
            esquema = json.load(f)
        for entry in (esquema.get("derived_fields") or []):
            target = entry.get("df_input")
            configs = entry.get("configs") or []
            if not configs:
                continue
            if target == "estudiantes":
                df_estudiantes = apply_derived_fields(df_estudiantes, configs)
            elif target == "habilidad":
                df_habilidad = apply_derived_fields(df_habilidad, configs)

    # Filtrar a una sola prueba: prioridad Mes > N Prueba.
    def _filter_to_one_prueba(df: pd.DataFrame) -> pd.DataFrame:
        if mes and "Mes" in df.columns:
            return df[df["Mes"].astype(str) == str(mes)].copy()
        n_prueba_col = next(
            (c for c in ("N Prueba", "Numero_Prueba", "N_Prueba", "Nro Prueba") if c in df.columns),
            None,
        )
        if n_prueba_col and df[n_prueba_col].notna().any():
            return df[df[n_prueba_col] == numero_prueba].copy()
        return df.copy()

    df_estudiantes_prueba = _filter_to_one_prueba(df_estudiantes)
    df_habilidad_prueba = _filter_to_one_prueba(df_habilidad)

    dataframes = {
        "estudiantes": df_estudiantes,                # df completo (para evolución por mes)
        "estudiantes_prueba": df_estudiantes_prueba,  # df filtrado a 1 prueba
        "habilidad": df_habilidad,                    # df habilidad filtrado por asignatura
        "habilidad_prueba": df_habilidad_prueba,      # df habilidad filtrado a 1 prueba
    }

    return runtime.construir_pdf("simce_panguipulli", dataframes, overrides=overrides)
