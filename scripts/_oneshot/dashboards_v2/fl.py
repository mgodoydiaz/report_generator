"""Dashboards Fluidez Lectora — specs y layout.

Mide PPM (palabras por minuto) leídas correctamente, asociadas a una
Categoría cualitativa (No Aplica|MUY BAJA|BAJA|MEDIA|ALTA) y a una
Calidad lectora (descriptor cualitativo de fluidez).

Modelo de datos (id_metric=10):
    Value fields: Cantidad (int, PPM), Categoria (str).
    Dimensiones: Establecimiento, Curso, Fecha, N Prueba, Nombre, RUT,
                 Calidad lectora, Seguimiento.

achievement_levels (linked color):
    No Aplica | MUY BAJA | BAJA | MEDIA | ALTA

Tabs propuestos:
    1. Resultados por Prueba — KPIs, resumen, distribución de PPM
    2. Por Curso             — selector + listado nominal
    3. Calidad Lectora       — heatmap categoría × calidad
    4. Tendencia             — evolución entre N° Prueba
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
    color_scale_linked,
    color_scale_sequential_blue,
    course_selector_item,
    kpis_item,
    row,
    tab,
    table_config,
    update_indicator_layout,
    upsert_chart,
    upsert_table,
)

METRIC_FL = 10


def seed_fl(db: Session, org_id: int, indicator_id_fl: int) -> Dict[str, int]:
    ids: Dict[str, int] = {}

    # ─────────────────────────────────────────────────────────────────────
    # TABLAS
    # ─────────────────────────────────────────────────────────────────────

    ids["t_resumen_curso"] = upsert_table(
        db, org_id,
        name="Fluidez Lectora — Resumen por Curso",
        description="N°, PPM promedio y rangos por curso.",
        config=table_config(
            metric_id=METRIC_FL,
            columns=[
                col_text("Curso", "Curso", pinned=True),
                col_agg("N", "Cantidad", "N°", agg="count", fmt="int", decimals=0),
                col_agg(
                    "PPM_mean", "Cantidad", "PPM Promedio",
                    agg="mean", fmt="float", decimals=1,
                    color_scale=color_scale_sequential_blue(),
                ),
                col_agg("PPM_min", "Cantidad", "PPM Mín", agg="min", fmt="int", decimals=0),
                col_agg("PPM_max", "Cantidad", "PPM Máx", agg="max", fmt="int", decimals=0),
            ],
            grouping={"by": "Curso"},
            sorting=[{"column": "Curso", "dir": "asc"}],
            search=False,
        ),
    )

    ids["t_alumno"] = upsert_table(
        db, org_id,
        name="Fluidez Lectora — Listado de Estudiantes",
        description="Detalle nominal con PPM, categoría y calidad lectora.",
        config=table_config(
            metric_id=METRIC_FL,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_text("Fecha", "Fecha"),
                col_int("Cantidad", "PPM"),
                {
                    "key": "Categoria", "header": "Categoría", "format": "text",
                    "color_scale": color_scale_linked(indicator_id_fl, "Categoria"),
                },
                col_text("Calidad lectora", "Calidad lectora"),
            ],
            sorting=[{"column": "Curso", "dir": "asc"}, {"column": "Nombre", "dir": "asc"}],
            page_size=50,
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # GRÁFICOS
    # ─────────────────────────────────────────────────────────────────────

    ids["c_ppm_curso"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — PPM Promedio por Curso",
        description="Barra: PPM promedio por curso.",
        config=chart_config(
            "bar", METRIC_FL,
            titulo="PPM Promedio por Curso",
            x_field="Curso", y_field="Cantidad",
            y_label="PPM",
        ),
    )

    ids["c_box_ppm"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Distribución de PPM por Curso",
        description="Boxplot: dispersión del PPM por curso.",
        config=chart_config(
            "box", METRIC_FL,
            titulo="Distribución de PPM por Curso",
            x_field="Curso", y_field="Cantidad",
            y_label="PPM",
        ),
    )

    ids["c_pie_categoria"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Composición por Categoría",
        description="Pie: distribución global de categorías de fluidez.",
        config=chart_config(
            "pie", METRIC_FL,
            titulo="Composición por Categoría",
            category_field="Categoria",
            color_palette="semaforo",
        ),
    )

    ids["c_stack_cat_curso"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Categoría por Curso",
        description="Stacked: distribución de categorías por curso.",
        config=chart_config(
            "stacked_bar", METRIC_FL,
            titulo="Categoría por Curso",
            x_field="Curso", stack_field="Categoria",
            stack_order=["MUY BAJA", "BAJA", "MEDIA", "ALTA", "No Aplica"],
            color_palette="semaforo",
            y_label="N° Estudiantes",
            legend_title="Categoría",
        ),
    )

    ids["c_stack_calidad_curso"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Calidad Lectora por Curso",
        description="Stacked: distribución de calidad lectora por curso.",
        config=chart_config(
            "stacked_bar", METRIC_FL,
            titulo="Calidad Lectora por Curso",
            x_field="Curso", stack_field="Calidad lectora",
            y_label="N° Estudiantes",
            legend_title="Calidad",
        ),
    )

    ids["c_heatmap_cat_calidad"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Categoría × Calidad Lectora",
        description=(
            "Heatmap: cantidad de estudiantes por (Categoría × Calidad Lectora). "
            "Permite ver la consistencia entre el indicador cuantitativo y "
            "el cualitativo."
        ),
        config=chart_config(
            "heatmap", METRIC_FL,
            titulo="Categoría × Calidad Lectora",
            x_field="Categoria", group_field="Calidad lectora", y_field="Cantidad",
            aggregation="count", color_palette="rojo_calor",
        ),
    )

    ids["c_evolucion_prueba"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Evolución de PPM por Prueba",
        description="Línea: avance del PPM promedio por curso entre pruebas.",
        config=chart_config(
            "line", METRIC_FL,
            titulo="Evolución de PPM",
            x_field="N Prueba", y_field="Cantidad", group_field="Curso",
            y_label="PPM",
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # LAYOUT
    # ─────────────────────────────────────────────────────────────────────
    layout = {
        "tabs": [
            tab("general", "Resultados por Prueba", [
                row([kpis_item()], cols=4),
                row([cfg_table_item(ids["t_resumen_curso"], "Resumen por Curso")], cols=1),
                row([
                    cfg_chart_item(ids["c_ppm_curso"], "PPM por Curso"),
                    cfg_chart_item(ids["c_box_ppm"], "Distribución por Curso"),
                ], cols=2),
                row([
                    cfg_chart_item(ids["c_pie_categoria"], "Composición Global"),
                    cfg_chart_item(ids["c_stack_cat_curso"], "Categoría por Curso"),
                ], cols=2),
            ]),
            tab("curso", "Por Curso", [
                row([course_selector_item()], cols=1),
                row([cfg_table_item(ids["t_alumno"], "Listado de Estudiantes")], cols=1),
            ]),
            tab("calidad", "Calidad Lectora", [
                row([cfg_chart_item(ids["c_stack_calidad_curso"], "Calidad por Curso")], cols=1),
                row([cfg_chart_item(ids["c_heatmap_cat_calidad"], "Categoría × Calidad")], cols=1),
            ]),
            tab("tendencia", "Tendencia", [
                row([cfg_chart_item(ids["c_evolucion_prueba"], "Evolución de PPM")], cols=1),
            ]),
        ]
    }

    update_indicator_layout(db, org_id, "Fluidez Lectora", layout)
    return ids
