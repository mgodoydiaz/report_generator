"""Dashboards Cálculo Veloz — specs y layout.

Cálculo Veloz mide velocidad de cálculo aritmético. Cada estudiante recibe
un Puntaje (operaciones correctas en tiempo dado), una Nota (transformación
piecewise-linear del puntaje), un Nivel cualitativo y un flag PIE
(Programa de Integración Escolar).

Modelo de datos (id_metric=9):
    Value fields: Puntaje (int), Nota (float), Nivel (str), PIE (int 0/1).
    Dimensiones: Establecimiento, Año, Curso, Fecha, Mes, N Prueba, Nombre, RUT.

achievement_levels (color-coded en color_scale linked):
    INICIAL | BÁSICO | INTERMEDIO | AVANZADO | EXPERTO

Tabs propuestos:
    1. Vista General  — KPIs, resumen, distribución, niveles
    2. Por Curso      — selector + listado nominal con histograma
    3. Tendencia      — evolución entre N° Prueba
"""
from __future__ import annotations

from typing import Dict

from sqlalchemy.orm import Session

from .helpers import (
    cfg_chart_item,
    cfg_table_item,
    chart_config,
    col_agg,
    col_float,
    col_int,
    col_text,
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

METRIC_CV = 9


def seed_cv(db: Session, org_id: int, indicator_id_cv: int) -> Dict[str, int]:
    ids: Dict[str, int] = {}

    # ─────────────────────────────────────────────────────────────────────
    # TABLAS
    # ─────────────────────────────────────────────────────────────────────

    ids["t_resumen_curso"] = upsert_table(
        db, org_id,
        name="Cálculo Veloz — Resumen por Curso",
        description="N°, puntaje y nota promedio por curso.",
        config=table_config(
            metric_id=METRIC_CV,
            columns=[
                col_text("Curso", "Curso", pinned=True),
                col_agg("N", "Puntaje", "N°", agg="count", fmt="int", decimals=0),
                col_agg("Puntaje_mean", "Puntaje", "Puntaje Promedio", agg="mean", fmt="float", decimals=1),
                col_agg("Nota_mean", "Nota", "Nota Promedio", agg="mean", fmt="float", decimals=2),
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
        name="Cálculo Veloz — Listado de Estudiantes",
        description="Detalle nominal con puntaje, nota y nivel.",
        config=table_config(
            metric_id=METRIC_CV,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_text("Mes", "Mes"),
                col_int("Puntaje", "Puntaje"),
                col_float("Nota", "Nota", decimals=2),
                {
                    "key": "Nivel", "header": "Nivel", "format": "text",
                    "color_scale": color_scale_linked(indicator_id_cv, "Nivel"),
                },
                {"key": "PIE", "header": "PIE", "format": "int", "decimals": 0},
            ],
            sorting=[{"column": "Curso", "dir": "asc"}, {"column": "Nombre", "dir": "asc"}],
            page_size=50,
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # GRÁFICOS
    # ─────────────────────────────────────────────────────────────────────

    ids["c_nota_curso"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Nota Promedio por Curso",
        description="Barra: nota promedio por curso.",
        config=chart_config(
            "bar", METRIC_CV,
            titulo="Nota Promedio por Curso",
            x_field="Curso", y_field="Nota",
            y_label="Nota",
        ),
    )

    ids["c_puntaje_curso"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Puntaje Promedio por Curso",
        description="Barra: puntaje promedio (operaciones correctas) por curso.",
        config=chart_config(
            "bar", METRIC_CV,
            titulo="Puntaje Promedio por Curso",
            x_field="Curso", y_field="Puntaje",
            y_label="Puntaje",
        ),
    )

    ids["c_box_puntaje"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Distribución de Puntaje",
        description="Boxplot: dispersión del puntaje por curso.",
        config=chart_config(
            "box", METRIC_CV,
            titulo="Distribución de Puntaje por Curso",
            x_field="Curso", y_field="Puntaje",
            y_label="Puntaje",
        ),
    )

    ids["c_pie_nivel"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Composición por Nivel",
        description="Pie: composición global de niveles.",
        config=chart_config(
            "pie", METRIC_CV,
            titulo="Composición por Nivel",
            category_field="Nivel",
        ),
    )

    ids["c_stack_nivel_curso"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Niveles por Curso",
        description="Barras apiladas: niveles por curso.",
        config=chart_config(
            "stacked_bar", METRIC_CV,
            titulo="Niveles por Curso",
            x_field="Curso", stack_field="Nivel",
            stack_order=["INICIAL", "BÁSICO", "INTERMEDIO", "AVANZADO", "EXPERTO"],
            y_label="N° Estudiantes",
            legend_title="Nivel",
        ),
    )

    ids["c_hist_puntaje"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Histograma de Puntaje",
        description="Histograma global del puntaje.",
        config=chart_config(
            "histogram", METRIC_CV,
            titulo="Histograma de Puntaje",
            y_field="Puntaje",
            y_label="N° Estudiantes",
            x_label="Puntaje",
            bins=15,
        ),
    )

    ids["c_evolucion_prueba"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Evolución de Puntaje por N° Prueba",
        description="Línea: avance del puntaje promedio por curso a lo largo de las pruebas.",
        config=chart_config(
            "line", METRIC_CV,
            titulo="Evolución de Puntaje",
            x_field="N Prueba", y_field="Puntaje", group_field="Curso",
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
                    cfg_chart_item(ids["c_nota_curso"], "Nota por Curso"),
                    cfg_chart_item(ids["c_puntaje_curso"], "Puntaje por Curso"),
                ], cols=2),
                row([
                    cfg_chart_item(ids["c_box_puntaje"], "Distribución por Curso"),
                ], cols=1),
                row([
                    cfg_chart_item(ids["c_pie_nivel"], "Composición Global"),
                    cfg_chart_item(ids["c_stack_nivel_curso"], "Niveles por Curso"),
                ], cols=2),
            ]),
            tab("curso", "Por Curso", [
                row([course_selector_item()], cols=1),
                row([cfg_chart_item(ids["c_hist_puntaje"], "Histograma de Puntaje")], cols=1),
                row([cfg_table_item(ids["t_alumno"], "Listado de Estudiantes")], cols=1),
            ]),
            tab("tendencia", "Tendencia", [
                row([cfg_chart_item(ids["c_evolucion_prueba"], "Evolución por Prueba")], cols=1),
            ]),
        ]
    }

    update_indicator_layout(db, org_id, "Cálculo Veloz", layout)
    return ids
