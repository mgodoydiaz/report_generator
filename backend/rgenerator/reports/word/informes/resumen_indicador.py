"""Informe Word genérico: resumen de cualquier Indicator.

Sirve como ejemplo vivo del contrato de informes Word y como informe
utilitario: funciona con cualquier indicador que tenga al menos una metric
con rol "estudiantes" (o, en su defecto, usa el primer DataFrame disponible).

Plantilla: templates/resumen_indicador.docx
Placeholders que espera la plantilla:
    {{ titulo }}, {{ subtitulo }}, {{ fecha }}, {{ n_registros }},
    {{ columnas }}, resumen (loop {%tr for fila in resumen %}),
    {{ grafico_logro }} (imagen, puede ser texto vacío si no aplica)
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from ..engine import Grafico, tabla_desde_df

LABEL = "Resumen del Indicador (Word)"
DESCRIPCION = (
    "Informe genérico: métricas base, resumen por curso y gráfico de logro "
    "promedio. Funciona con cualquier indicador con datos de estudiantes."
)
PARAMS_ESPERADOS = ["titulo", "subtitulo", "columna_valor", "agrupar_por"]


def _elegir_df(dataframes: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df_est = dataframes.get("estudiantes")
    if df_est is not None and len(df_est):
        return df_est
    # Fallback: primer DataFrame no vacío
    for df in dataframes.values():
        if len(df):
            return df
    raise ValueError("El indicador no tiene datos cargados")


def construir_contexto(dataframes: dict[str, pd.DataFrame], params: dict) -> dict:
    df = _elegir_df(dataframes)

    # Columna de valor y agrupación: params del frontend > autodetección
    columna_valor = params.get("columna_valor")
    if not columna_valor:
        numericas = df.select_dtypes("number").columns.tolist()
        preferidas = [c for c in ("Logro", "Rend", "PorcLogro", "Puntaje") if c in df.columns]
        columna_valor = (preferidas or numericas or [None])[0]

    agrupar_por = params.get("agrupar_por") or ("Curso" if "Curso" in df.columns else None)

    contexto: dict = {
        "titulo": params.get("titulo", "Resumen del Indicador"),
        "subtitulo": params.get("subtitulo", ""),
        "fecha": date.today().strftime("%d/%m/%Y"),
        "n_registros": len(df),
        "columnas": ", ".join(str(c) for c in df.columns),
        "resumen": [],
        "grafico_logro": "",
    }

    if columna_valor and agrupar_por and agrupar_por in df.columns:
        df_num = df.copy()
        df_num[columna_valor] = pd.to_numeric(df_num[columna_valor], errors="coerce")
        resumen = (
            df_num.groupby(agrupar_por)
            .agg(N=(columna_valor, "count"), Promedio=(columna_valor, "mean"))
            .reset_index()
            .rename(columns={agrupar_por: "Categoria"})
        )
        contexto["resumen"] = tabla_desde_df(resumen, formatos={"Promedio": ".1%"})
        contexto["grafico_logro"] = Grafico(
            fn="grafico_barras_promedio_por",
            df=df_num.dropna(subset=[columna_valor]),
            params={
                "columna_valor": columna_valor,
                "agrupar_por": agrupar_por,
                "titulo": f"{columna_valor} promedio por {agrupar_por}",
            },
        )

    return contexto
