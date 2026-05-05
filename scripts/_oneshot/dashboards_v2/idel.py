"""Dashboards IDEL — specs y layout.

IDEL = Indicador de Desarrollo de Lectura. Aplica a estudiantes pequeños
(habitualmente Kínder–2° básico) y mide riesgo lector con un puntaje y un
nivel de riesgo.

Modelo de datos (id_metric=8):
    Value fields: Puntaje (int), Género (int), Evaluadora (str),
                  Nivel de Riesgo (str: Crítico|Alto Riesgo|Cierto Riesgo|Bajo Riesgo).
    Dimensiones: Establecimiento, Año, Curso, Evaluación, Nombre, RUT, Versión.

Tabs propuestos:
    1. Vista General  — KPIs, resumen, distribución, niveles
    2. Por Curso      — selector + listado nominal
    3. Tendencia      — evolución entre versiones (1ª vs 2ª aplicación)
"""
from __future__ import annotations

from typing import Dict

from sqlalchemy.orm import Session

from .helpers import (
    cfg_chart_item,
    cfg_table_item,
    chart_config,
    col_agg,
    col_int,
    col_text,
    color_scale_diverging_logro,
    color_scale_linked,
    course_selector_item,
    kpis_item,
    row,
    tab,
    table_config,
    update_indicator_layout,
    upsert_chart,
    upsert_table,
)

METRIC_IDEL = 8


def seed_idel(db: Session, org_id: int, indicator_id_idel: int) -> Dict[str, int]:
    ids: Dict[str, int] = {}

    # ─────────────────────────────────────────────────────────────────────
    # TABLAS
    # ─────────────────────────────────────────────────────────────────────

    ids["t_resumen_curso"] = upsert_table(
        db, org_id,
        name="IDEL — Resumen por Curso",
        description="N° estudiantes y puntaje promedio por curso.",
        config=table_config(
            metric_id=METRIC_IDEL,
            columns=[
                col_text("Curso", "Curso", pinned=True),
                col_agg("N", "Puntaje", "N°", agg="count", fmt="int", decimals=0),
                col_agg(
                    "Puntaje_mean", "Puntaje", "Puntaje Promedio",
                    agg="mean", fmt="float", decimals=1,
                ),
                col_agg("Puntaje_min", "Puntaje", "Mínimo", agg="min", fmt="int", decimals=0),
                col_agg("Puntaje_max", "Puntaje", "Máximo", agg="max", fmt="int", decimals=0),
            ],
            grouping={"by": "Curso"},
            sorting=[{"column": "Curso", "dir": "asc"}],
            search=False,
        ),
    )

    ids["t_alumno"] = upsert_table(
        db, org_id,
        name="IDEL — Listado de Estudiantes",
        description="Detalle nominal con puntaje, nivel de riesgo y evaluadora.",
        config=table_config(
            metric_id=METRIC_IDEL,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_text("Versión", "Versión"),
                col_int("Puntaje", "Puntaje"),
                {
                    "key": "Nivel de Riesgo", "header": "Nivel", "format": "text",
                    "color_scale": color_scale_linked(indicator_id_idel, "Nivel de Riesgo"),
                },
                col_text("Evaluadora", "Evaluadora"),
            ],
            sorting=[{"column": "Curso", "dir": "asc"}, {"column": "Nombre", "dir": "asc"}],
            page_size=50,
        ),
    )

    ids["t_riesgo"] = upsert_table(
        db, org_id,
        name="IDEL — Estudiantes en Riesgo",
        description=(
            "Estudiantes con nivel de riesgo Crítico o Alto Riesgo, ordenados "
            "por puntaje ascendente para priorizar intervención."
        ),
        config=table_config(
            metric_id=METRIC_IDEL,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_int("Puntaje", "Puntaje"),
                {
                    "key": "Nivel de Riesgo", "header": "Nivel", "format": "text",
                    "color_scale": color_scale_linked(indicator_id_idel, "Nivel de Riesgo"),
                },
                col_text("Evaluadora", "Evaluadora"),
            ],
            sorting=[{"column": "Puntaje", "dir": "asc"}],
            page_size=80,
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # GRÁFICOS
    # ─────────────────────────────────────────────────────────────────────

    ids["c_puntaje_curso"] = upsert_chart(
        db, org_id,
        name="IDEL — Puntaje Promedio por Curso",
        description="Barra: puntaje promedio por curso.",
        config=chart_config(
            "bar", METRIC_IDEL,
            titulo="Puntaje Promedio por Curso",
            x_field="Curso", y_field="Puntaje",
            y_label="Puntaje",
        ),
    )

    ids["c_box_puntaje"] = upsert_chart(
        db, org_id,
        name="IDEL — Distribución de Puntaje por Curso",
        description="Boxplot: dispersión del puntaje por curso.",
        config=chart_config(
            "box", METRIC_IDEL,
            titulo="Distribución de Puntaje por Curso",
            x_field="Curso", y_field="Puntaje",
            y_label="Puntaje",
        ),
    )

    ids["c_pie_riesgo"] = upsert_chart(
        db, org_id,
        name="IDEL — Composición por Nivel de Riesgo",
        description="Pie: distribución global de niveles de riesgo.",
        config=chart_config(
            "pie", METRIC_IDEL,
            titulo="Composición por Nivel de Riesgo",
            category_field="Nivel de Riesgo",
            color_palette="semaforo",
        ),
    )

    ids["c_stack_riesgo_curso"] = upsert_chart(
        db, org_id,
        name="IDEL — Niveles de Riesgo por Curso",
        description="Stacked: cantidad de estudiantes por nivel de riesgo y curso.",
        config=chart_config(
            "stacked_bar", METRIC_IDEL,
            titulo="Niveles de Riesgo por Curso",
            x_field="Curso", stack_field="Nivel de Riesgo",
            stack_order=["Critico", "Alto riesgo", "Cierto riesgo", "Bajo riesgo"],
            color_palette="semaforo",
            y_label="N° Estudiantes",
            legend_title="Nivel",
        ),
    )

    ids["c_evolucion_version"] = upsert_chart(
        db, org_id,
        name="IDEL — Evolución de Puntaje por Versión",
        description=(
            "Línea: puntaje promedio por versión de la prueba (1ª vs 2ª "
            "aplicación), una línea por curso. Permite ver el avance entre "
            "aplicaciones."
        ),
        config=chart_config(
            "line", METRIC_IDEL,
            titulo="Evolución de Puntaje por Versión",
            x_field="Versión", y_field="Puntaje", group_field="Curso",
            y_label="Puntaje",
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # LAYOUT
    # ─────────────────────────────────────────────────────────────────────
    layout = {
        "tabs": [
            tab("general", "Vista General", [
                row([kpis_item()], cols=4),
                row([cfg_table_item(ids["t_resumen_curso"], "Resumen por Curso")], cols=1),
                row([
                    cfg_chart_item(ids["c_puntaje_curso"], "Puntaje por Curso"),
                    cfg_chart_item(ids["c_box_puntaje"], "Distribución por Curso"),
                ], cols=2),
                row([
                    cfg_chart_item(ids["c_pie_riesgo"], "Composición Global"),
                    cfg_chart_item(ids["c_stack_riesgo_curso"], "Riesgo por Curso"),
                ], cols=2),
            ]),
            tab("curso", "Por Curso", [
                row([course_selector_item()], cols=1),
                row([cfg_table_item(ids["t_alumno"], "Listado de Estudiantes")], cols=1),
                row([cfg_table_item(ids["t_riesgo"], "Estudiantes en Riesgo")], cols=1),
            ]),
            tab("tendencia", "Tendencia", [
                row([cfg_chart_item(ids["c_evolucion_version"], "Evolución por Versión")], cols=1),
            ]),
        ]
    }

    update_indicator_layout(db, org_id, "IDEL", layout)
    return ids
