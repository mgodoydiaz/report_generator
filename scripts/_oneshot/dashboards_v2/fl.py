"""Dashboards Fluidez Lectora — specs y layout.

Mide PPM (palabras por minuto) leídas correctamente, asociadas a una
Categoría cualitativa (No Aplica|MUY BAJA|BAJA|MEDIA|ALTA) y a una
Calidad lectora ordinal (No Lector → Silábica → Palabra Por Palabra →
Unidades Cortas → Fluida; "No Aplica" como neutral).

Modelo de datos (id_metric=10):
    Value fields: Cantidad (int, PPM), Categoria (str).
    Dimensiones: Establecimiento, Curso, Fecha, N Prueba, Nombre, RUT,
                 Calidad lectora, Seguimiento.

achievement_levels (linked color):
    No Aplica | MUY BAJA | BAJA | MEDIA | ALTA

Tabs propuestos:
    1. Vista General         — KPIs, resumen, distribución global
    2. Por Curso             — selector + listado nominal + boxplot
    3. Calidad Lectora       — distribución, heatmap consistencia
    4. Refuerzo / Riesgo     — listado intensivo + lectores iniciales
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
    color_overrides_from_indicator,
    color_scale_linked,
    color_scale_sequential_blue,
    course_selector_item,
    kpis_item,
    note_item,
    row,
    tab,
    table_config,
    update_indicator_layout,
    upsert_chart,
    upsert_table,
)

METRIC_FL = 10

# Categoría cuantitativa: peor → mejor. "No Aplica" al final como neutral.
FL_CATEGORIA_ORDER = ["MUY BAJA", "BAJA", "MEDIA", "ALTA", "No Aplica"]

# Calidad lectora ordinal: peor → mejor. "No Aplica" al final como neutral.
# Confirmado con datos reales en metric_data 2026-05-06.
FL_CALIDAD_ORDER = [
    "No Lector",
    "Silábica",
    "Palabra Por Palabra",
    "Unidades Cortas",
    "Fluida",
    "No Aplica",
]

# Colores para Calidad lectora. La paleta `semaforo_4` solo cubre 4 entradas
# y aquí necesitamos 6 (incluido "No Aplica" como neutral). Usamos un mapping
# explícito alineado con la severidad: rojo → naranja → amarillo → lima →
# verde → gris. Coherente con los achievement_levels visuales del indicador.
FL_CALIDAD_COLORS = {
    "No Lector":           "#dc2626",  # rojo intenso
    "Silábica":            "#ea580c",  # naranja oscuro
    "Palabra Por Palabra": "#eab308",  # amarillo
    "Unidades Cortas":     "#84cc16",  # lima
    "Fluida":              "#22c55e",  # verde
    "No Aplica":           "#94a3b8",  # gris neutro
}


def seed_fl(db: Session, org_id: int, indicator_id_fl: int) -> Dict[str, int]:
    ids: Dict[str, int] = {}

    # Colores oficiales por categoría — leídos del indicador FL para
    # garantizar consistencia con la página de Indicadores. "No Aplica"
    # está como nivel #1 con verde (#2dd22d) en el indicador; lo
    # sobrescribimos a gris para que no compita visualmente con "ALTA"
    # (verde claro #80d22d).
    cat_colors = color_overrides_from_indicator(db, org_id, "Fluidez Lectora")
    if "No Aplica" in cat_colors:
        cat_colors["No Aplica"] = "#94a3b8"

    # ─────────────────────────────────────────────────────────────────────
    # TABLAS
    # ─────────────────────────────────────────────────────────────────────

    ids["t_resumen_curso"] = upsert_table(
        db, org_id,
        name="Fluidez Lectora — Resumen por Curso",
        description="N°, PPM promedio, mediana, min, max y % en riesgo (MUY BAJA + BAJA) por curso.",
        config=table_config(
            metric_id=METRIC_FL,
            columns=[
                col_text("Curso", "Curso", pinned=True),
                col_agg("N", "Cantidad", "N° Estudiantes", agg="count", fmt="int", decimals=0),
                col_agg(
                    "PPM_mean", "Cantidad", "PPM Promedio",
                    agg="mean", fmt="float", decimals=1,
                    color_scale=color_scale_sequential_blue(),
                ),
                col_agg("PPM_median", "Cantidad", "Mediana", agg="median", fmt="float", decimals=1),
                col_agg("PPM_min", "Cantidad", "Mínimo", agg="min", fmt="int", decimals=0),
                col_agg("PPM_max", "Cantidad", "Máximo", agg="max", fmt="int", decimals=0),
            ],
            grouping={"by": "Curso"},
            sorting=[{"column": "Curso", "dir": "asc"}],
            search=False,
        ),
    )

    ids["t_alumno"] = upsert_table(
        db, org_id,
        name="Fluidez Lectora — Listado de Estudiantes",
        description="Detalle nominal con PPM, categoría, calidad lectora y seguimiento.",
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
                col_text("Seguimiento", "Seguimiento"),
            ],
            sorting=[{"column": "Curso", "dir": "asc"}, {"column": "Nombre", "dir": "asc"}],
            page_size=50,
        ),
    )

    # Listado de estudiantes en seguimiento Intensivo — accionable para
    # el equipo de PIE / refuerzo.
    ids["t_intensivo"] = upsert_table(
        db, org_id,
        name="Fluidez Lectora — Estudiantes en Seguimiento Intensivo",
        description="Estudiantes marcados con Seguimiento=Intensivo. Lista nominal ordenada por PPM ascendente para priorizar atención.",
        config=table_config(
            metric_id=METRIC_FL,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_int("Cantidad", "PPM"),
                {
                    "key": "Categoria", "header": "Categoría", "format": "text",
                    "color_scale": color_scale_linked(indicator_id_fl, "Categoria"),
                },
                col_text("Calidad lectora", "Calidad lectora"),
            ],
            filters={"Seguimiento": "Intensivo"},
            sorting=[
                {"column": "Cantidad", "dir": "asc"},
                {"column": "Curso", "dir": "asc"},
            ],
            page_size=100,
        ),
    )

    # Lectores iniciales — categoría operacional (Calidad lectora ∈
    # {No Lector, Silábica}). Estos estudiantes requieren intervención
    # inmediata independientemente del seguimiento formal.
    ids["t_lectores_iniciales"] = upsert_table(
        db, org_id,
        name="Fluidez Lectora — Lectores Iniciales",
        description="Estudiantes con Calidad lectora = No Lector o Silábica. Población de máxima prioridad para intervención.",
        config=table_config(
            metric_id=METRIC_FL,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_int("Cantidad", "PPM"),
                col_text("Calidad lectora", "Calidad lectora"),
                col_text("Seguimiento", "Seguimiento"),
            ],
            filters={"Calidad lectora": ["No Lector", "Silábica"]},
            sorting=[
                {"column": "Calidad lectora", "dir": "asc"},
                {"column": "Curso", "dir": "asc"},
                {"column": "Nombre", "dir": "asc"},
            ],
            page_size=100,
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # GRÁFICOS
    # ─────────────────────────────────────────────────────────────────────

    # Bar PPM promedio por curso — vista rápida del rendimiento agregado.
    ids["c_ppm_curso"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — PPM Promedio por Curso",
        description="Barra: PPM promedio por curso con números sobre cada barra.",
        config=chart_config(
            "bar", METRIC_FL,
            titulo="PPM Promedio por Curso",
            x_field="Curso", y_field="Cantidad",
            y_label="PPM (palabras por minuto)",
            x_label="Curso",
            show_values=True,
        ),
    )

    # Boxplot — dispersión por curso, identifica outliers.
    ids["c_box_ppm"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Distribución de PPM por Curso",
        description="Boxplot: dispersión del PPM por curso. Muestra mediana, cuartiles y outliers.",
        config=chart_config(
            "box", METRIC_FL,
            titulo="Distribución de PPM por Curso",
            x_field="Curso", y_field="Cantidad",
            y_label="PPM",
            x_label="Curso",
        ),
    )

    # Pie composición por categoría con colores oficiales.
    ids["c_pie_categoria"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Composición por Categoría",
        description="Pie: distribución global de categorías cuantitativas (MUY BAJA → ALTA).",
        config=chart_config(
            "pie", METRIC_FL,
            titulo="Composición por Categoría",
            category_field="Categoria",
            color_overrides=cat_colors,
        ),
    )

    # Stacked Categoría por Curso — composición por curso.
    ids["c_stack_cat_curso"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Categoría por Curso",
        description="Stacked: composición de categorías por curso. Usa colores oficiales del indicador.",
        config=chart_config(
            "stacked_bar", METRIC_FL,
            titulo="Categoría por Curso",
            x_field="Curso", stack_field="Categoria",
            stack_order=FL_CATEGORIA_ORDER,
            color_overrides=cat_colors,
            y_label="N° Estudiantes",
            y_format="int",
            legend_title="Categoría",
            show_values=True,
        ),
    )

    # Pie de calidad lectora — descriptor cualitativo.
    ids["c_pie_calidad"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Composición por Calidad Lectora",
        description="Pie: distribución global de calidad lectora (No Lector → Fluida).",
        config=chart_config(
            "pie", METRIC_FL,
            titulo="Composición por Calidad Lectora",
            category_field="Calidad lectora",
            color_overrides=FL_CALIDAD_COLORS,
        ),
    )

    # Stacked Calidad por Curso — descriptor por curso.
    ids["c_stack_calidad_curso"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Calidad Lectora por Curso",
        description="Stacked: distribución de calidad lectora por curso.",
        config=chart_config(
            "stacked_bar", METRIC_FL,
            titulo="Calidad Lectora por Curso",
            x_field="Curso", stack_field="Calidad lectora",
            stack_order=FL_CALIDAD_ORDER,
            color_overrides=FL_CALIDAD_COLORS,
            y_label="N° Estudiantes",
            y_format="int",
            legend_title="Calidad",
            show_values=True,
        ),
    )

    # Heatmap Categoría × Calidad — consistencia entre indicador
    # cuantitativo y cualitativo.
    ids["c_heatmap_cat_calidad"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Categoría × Calidad Lectora",
        description=(
            "Heatmap: count de estudiantes por (Categoría × Calidad Lectora). "
            "Verifica la consistencia entre el indicador cuantitativo (PPM) "
            "y el cualitativo (calidad observada)."
        ),
        config=chart_config(
            "heatmap", METRIC_FL,
            titulo="Categoría × Calidad Lectora",
            x_field="Categoria", group_field="Calidad lectora", y_field="Cantidad",
            aggregation="count",
            color_palette="rojo_calor",
            x_order=FL_CATEGORIA_ORDER,
            stack_order=FL_CALIDAD_ORDER,
            x_label="Categoría",
            y_label="Calidad lectora",
            y_format="int",
        ),
    )

    # Heatmap Curso × Calidad — distribución por curso.
    ids["c_heatmap_curso_calidad"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Curso × Calidad Lectora",
        description="Heatmap: count de estudiantes por (Curso × Calidad Lectora). Identifica cursos con concentración de lectores iniciales.",
        config=chart_config(
            "heatmap", METRIC_FL,
            titulo="Curso × Calidad Lectora",
            x_field="Curso", group_field="Calidad lectora", y_field="Cantidad",
            aggregation="count",
            color_palette="rojo_calor",
            stack_order=FL_CALIDAD_ORDER,
            x_label="Curso",
            y_label="Calidad lectora",
            y_format="int",
        ),
    )

    # Pie composición por seguimiento.
    ids["c_pie_seguimiento"] = upsert_chart(
        db, org_id,
        name="Fluidez Lectora — Composición por Seguimiento",
        description="Pie: estudiantes en seguimiento Intensivo vs Normal.",
        config=chart_config(
            "pie", METRIC_FL,
            titulo="Estudiantes por Seguimiento",
            category_field="Seguimiento",
            color_overrides={"Intensivo": "#dc2626", "Normal": "#22c55e"},
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # LAYOUT
    # ─────────────────────────────────────────────────────────────────────
    # Nota: NO incluimos tab "Tendencia" porque a 2026-05-06 solo hay 1
    # ensayo cargado (Ensayo 1). Cuando se cargue Ensayo 2+ podemos
    # agregar el tab con el chart `line` clásico (similar al de CV).
    layout = {
        "tabs": [
            tab("general", "Vista General", [
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
                row([cfg_chart_item(ids["c_box_ppm"], "Distribución por Curso (filtrable)")], cols=1),
                row([cfg_table_item(ids["t_alumno"], "Listado de Estudiantes")], cols=1),
            ]),
            tab("calidad", "Calidad Lectora", [
                row([note_item(
                    "La 'Calidad lectora' es un descriptor cualitativo que un evaluador "
                    "asigna observando la lectura. Va desde 'No Lector' (no decodifica) "
                    "hasta 'Fluida' (lee con prosodia y ritmo). 'No Aplica' indica que el "
                    "estudiante no rindió el ensayo.",
                    tone="info",
                    title="Sobre la calidad lectora",
                )], cols=1),
                row([
                    cfg_chart_item(ids["c_pie_calidad"], "Composición Global"),
                    cfg_chart_item(ids["c_stack_calidad_curso"], "Calidad por Curso"),
                ], cols=2),
                row([cfg_chart_item(ids["c_heatmap_curso_calidad"], "Curso × Calidad")], cols=1),
                row([cfg_chart_item(ids["c_heatmap_cat_calidad"], "Categoría × Calidad (consistencia)")], cols=1),
            ]),
            tab("refuerzo", "Refuerzo / Riesgo", [
                row([note_item(
                    "Esta sección agrupa a los estudiantes que requieren atención "
                    "prioritaria. 'Seguimiento Intensivo' es el flag formal del equipo "
                    "PIE; 'Lectores Iniciales' captura a quienes aún no decodifican "
                    "(No Lector) o leen sílaba a sílaba (Silábica), independiente del "
                    "seguimiento formal.",
                    tone="warn",
                    title="Población prioritaria para intervención",
                )], cols=1),
                row([
                    cfg_chart_item(ids["c_pie_seguimiento"], "Estudiantes por Seguimiento"),
                ], cols=1),
                row([cfg_table_item(ids["t_intensivo"], "Estudiantes en Seguimiento Intensivo")], cols=1),
                row([cfg_table_item(ids["t_lectores_iniciales"], "Lectores Iniciales (No Lector / Silábica)")], cols=1),
            ]),
        ]
    }

    update_indicator_layout(db, org_id, "Fluidez Lectora", layout)
    return ids
