"""Dashboards SIMCE — specs y layout.

Modelo de datos:
    - id_metric=4 (Resultados SIMCE por Estudiante): Rend (float, %), SIMCE
      (int), Logro (str: Insuficiente|Elemental|Adecuado).
    - id_metric=5 (Resultados SIMCE por Pregunta): Logro (float, %).
    - Dimensiones: Establecimiento, Año, Curso, Asignatura, Mes (ABRIL,
      JUNIO, AGOSTO, OCTUBRE), N Prueba, Pregunta, Habilidad, Eje Temático.

A diferencia de DIA, SIMCE no tiene Hito ordinal sino que se ensaya con
ensayos mensuales (ABRIL, JUNIO, AGOSTO, OCTUBRE). El "evaluacion_num"
mapea a Mes en column_roles.

Tabs propuestos:
    1. Vista General      — KPIs, resumen, distribución, niveles
    2. Por Curso          — preguntas + habilidades + eje temático
    3. Por Estudiante     — listado nominal con rend y nivel
    4. Tendencia          — evolución por mes + matriz de transición
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
    col_percent,
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

METRIC_SIMCE_EST = 4
METRIC_SIMCE_PREG = 5


def seed_simce(db: Session, org_id: int, indicator_id_simce: int) -> Dict[str, int]:
    ids: Dict[str, int] = {}

    # ─────────────────────────────────────────────────────────────────────
    # TABLAS
    # ─────────────────────────────────────────────────────────────────────

    ids["t_resumen_curso"] = upsert_table(
        db, org_id,
        name="SIMCE — Resumen por Curso",
        description="N° estudiantes, rendimiento promedio y rangos por curso.",
        config=table_config(
            metric_id=METRIC_SIMCE_EST,
            columns=[
                col_text("Curso", "Curso", pinned=True),
                col_agg("N", "Rend", "N°", agg="count", fmt="int", decimals=0),
                col_agg(
                    "Rend_mean", "Rend", "Rend Promedio",
                    agg="mean", fmt="percent", decimals=1,
                    color_scale=color_scale_diverging_logro(),
                ),
                col_agg("Rend_min", "Rend", "Rend Mín", agg="min", fmt="percent", decimals=1),
                col_agg("Rend_max", "Rend", "Rend Máx", agg="max", fmt="percent", decimals=1),
                col_agg(
                    "SIMCE_mean", "SIMCE", "SIMCE Estimado",
                    agg="mean", fmt="int", decimals=0,
                ),
            ],
            grouping={"by": "Curso"},
            sorting=[{"column": "Curso", "dir": "asc"}],
            search=False,
        ),
    )

    ids["t_alumno"] = upsert_table(
        db, org_id,
        name="SIMCE — Logro por Alumno",
        description=(
            "Detalle nominal por estudiante con Rend, SIMCE, Nivel y Avance. "
            "La columna Avance es la pendiente (slope) del logro a lo largo "
            "del año (ABRIL → NOVIEMBRE) — positiva si el estudiante mejora, "
            "negativa si empeora. Replica la página 8 del informe SIMCE."
        ),
        config=table_config(
            metric_id=METRIC_SIMCE_EST,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_text("Asignatura", "Asignatura"),
                col_text("Mes", "Mes"),
                col_percent("Rend", "Rendimiento"),
                {"key": "SIMCE", "header": "SIMCE", "format": "int", "decimals": 0},
                {
                    "key": "Logro", "header": "Nivel", "format": "text",
                    "color_scale": color_scale_linked(indicator_id_simce, "Logro"),
                },
                # Columna Avance del derived_columns "Avance" (slope). Se
                # renderiza en formato % con paleta divergente (rojo si
                # negativo, verde si positivo).
                col_percent("Avance", "Avance", decimals=1),
            ],
            sorting=[{"column": "Curso", "dir": "asc"}, {"column": "Nombre", "dir": "asc"}],
            page_size=50,
        ),
    )

    ids["t_pregunta"] = upsert_table(
        db, org_id,
        name="SIMCE — Logro por Pregunta",
        description="% acierto por pregunta, con habilidad y eje temático.",
        config=table_config(
            metric_id=METRIC_SIMCE_PREG,
            columns=[
                col_text("Pregunta", "Pregunta", pinned=True),
                col_text("Habilidad", "Habilidad"),
                col_text("Eje Temático", "Eje"),
                col_text("Curso", "Curso"),
                col_text("Mes", "Mes"),
                col_percent("Logro", "% Acierto"),
            ],
            sorting=[{"column": "Curso", "dir": "asc"}, {"column": "Pregunta", "dir": "asc"}],
            page_size=80,
        ),
    )

    # Replica la "Reporte de estadísticas por pregunta" del informe SIMCE
    # pág. 7. Columnas A/B/C/D/E + Correcta + Distractor + Logro.
    # Recomendación: filtrar por (Año, Asignatura, Mes, N° Prueba) antes
    # de leer la tabla — el promedio mezcla menos cuando hay un solo
    # snapshot. Cuando hay múltiples cursos, el % de cada alternativa
    # es el promedio simple entre cursos (no ponderado por N).
    ids["t_estad_pregunta"] = upsert_table(
        db, org_id,
        name="SIMCE — Estadística por Pregunta",
        description=(
            "Reporte de estadísticas por pregunta con porcentaje de respuestas "
            "por alternativa (A/B/C/D/E), alternativa correcta y distractor "
            "más frecuente. Replica la página 7 del informe SIMCE. "
            "Filtrar por (Año, Asignatura, Mes, N° Prueba) para un snapshot "
            "limpio."
        ),
        config=table_config(
            metric_id=METRIC_SIMCE_PREG,
            columns=[
                col_text("Pregunta", "Pregunta", pinned=True),
                col_agg("A", "A", "%A", agg="mean", fmt="percent", decimals=0),
                col_agg("B", "B", "%B", agg="mean", fmt="percent", decimals=0),
                col_agg("C", "C", "%C", agg="mean", fmt="percent", decimals=0),
                col_agg("D", "D", "%D", agg="mean", fmt="percent", decimals=0),
                col_agg("E", "E", "%E", agg="mean", fmt="percent", decimals=0),
                col_agg("Correcta", "Correcta", "Correcta", agg="first", fmt="text"),
                col_agg("Distractor", "Distractor", "Distractor", agg="first", fmt="text"),
                col_agg(
                    "Logro_mean", "Logro", "Dificultad",
                    agg="mean", fmt="percent", decimals=1,
                    color_scale=color_scale_diverging_logro(),
                ),
            ],
            grouping={"by": "Pregunta"},
            sorting=[{"column": "Pregunta", "dir": "asc"}],
            search=False,
            page_size=50,
        ),
    )

    ids["t_riesgo"] = upsert_table(
        db, org_id,
        name="SIMCE — Estudiantes en Riesgo",
        description=(
            "Estudiantes con rendimiento inferior a 0.40. La tabla está "
            "ordenada de menor a mayor para que el techo aparezca al inicio."
        ),
        config=table_config(
            metric_id=METRIC_SIMCE_EST,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_text("Asignatura", "Asignatura"),
                col_text("Mes", "Mes"),
                col_percent("Rend", "Rend"),
                col_text("Logro", "Nivel"),
            ],
            sorting=[{"column": "Rend", "dir": "asc"}],
            page_size=50,
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # GRÁFICOS
    # ─────────────────────────────────────────────────────────────────────

    ids["c_rend_curso"] = upsert_chart(
        db, org_id,
        name="SIMCE — Rendimiento por Curso",
        description="Promedio de rendimiento (Rend) por curso.",
        config=chart_config(
            "bar", METRIC_SIMCE_EST,
            titulo="Rendimiento Promedio por Curso",
            x_field="Curso", y_field="Rend",
            y_format="percent", y_lims=[0, 1], y_label="Rendimiento",
        ),
    )

    ids["c_box_curso"] = upsert_chart(
        db, org_id,
        name="SIMCE — Distribución de Rendimiento por Curso",
        description="Boxplot del rendimiento por curso.",
        config=chart_config(
            "box", METRIC_SIMCE_EST,
            titulo="Distribución de Rendimiento",
            x_field="Curso", y_field="Rend",
            y_format="percent", y_lims=[0, 1], y_label="Rendimiento",
        ),
    )

    ids["c_pie_logro"] = upsert_chart(
        db, org_id,
        name="SIMCE — Composición por Nivel",
        description="Distribución global Insuficiente/Elemental/Adecuado.",
        config=chart_config(
            "pie", METRIC_SIMCE_EST,
            titulo="Composición por Nivel",
            category_field="Logro",
            color_palette="semaforo",
        ),
    )

    ids["c_stack_niveles"] = upsert_chart(
        db, org_id,
        name="SIMCE — Cantidad por Nivel y Curso",
        description="Barras apiladas: distribución de niveles por curso.",
        config=chart_config(
            "stacked_bar", METRIC_SIMCE_EST,
            titulo="Niveles por Curso",
            x_field="Curso", stack_field="Logro",
            stack_order=["Insuficiente", "Elemental", "Adecuado"],
            color_palette="semaforo",
            y_label="N° Estudiantes",
            legend_title="Nivel",
        ),
    )

    ids["c_habilidad"] = upsert_chart(
        db, org_id,
        name="SIMCE — Logro por Habilidad",
        description="% acierto por habilidad, agrupado por curso.",
        config=chart_config(
            "grouped_bar", METRIC_SIMCE_PREG,
            titulo="Logro por Habilidad",
            x_field="Habilidad", y_field="Logro", group_field="Curso",
            y_format="percent", y_lims=[0, 1], y_label="% Acierto",
        ),
    )

    ids["c_eje"] = upsert_chart(
        db, org_id,
        name="SIMCE — Logro por Eje Temático",
        description="% acierto por eje temático, agrupado por curso.",
        config=chart_config(
            "grouped_bar", METRIC_SIMCE_PREG,
            titulo="Logro por Eje Temático",
            x_field="Eje Temático", y_field="Logro", group_field="Curso",
            y_format="percent", y_lims=[0, 1], y_label="% Acierto",
        ),
    )

    # Orden cronológico de meses en SIMCE 2025 (ABRIL → NOVIEMBRE).
    # Si en años futuros se usan otros meses, hay que extender la lista.
    SIMCE_MES_ORDER = ["ABRIL", "JUNIO", "AGOSTO", "OCTUBRE", "NOVIEMBRE", "MAYO"]

    # Replica el "Evolución del Logro Promedio por Curso y Mes" del informe
    # SIMCE pág. 2: barras agrupadas con el curso en el eje X y los meses
    # como series. Útil para ver lado a lado cómo evoluciona cada curso.
    ids["c_evolucion_logro"] = upsert_chart(
        db, org_id,
        name="SIMCE — Evolución Logro Promedio por Curso y Mes",
        description=(
            "Barras agrupadas: % logro promedio por curso, una serie por mes "
            "(ABRIL → NOVIEMBRE). Replica la página 2 del informe SIMCE."
        ),
        config=chart_config(
            "grouped_bar", METRIC_SIMCE_EST,
            titulo="Evolución del Logro Promedio por Curso y Mes",
            x_field="Curso", y_field="Rend", group_field="Mes",
            y_format="percent", y_lims=[0, 1], y_label="Rendimiento",
            stack_order=SIMCE_MES_ORDER,
            show_values=True,
        ),
    )

    # Replica "Evolución del SIMCE Promedio por Curso y Mes" del informe pág. 3:
    # barras agrupadas con puntaje SIMCE estimado por curso × mes.
    ids["c_evolucion_simce"] = upsert_chart(
        db, org_id,
        name="SIMCE — Evolución del SIMCE Promedio por Curso y Mes",
        description=(
            "Barras agrupadas: puntaje SIMCE estimado promedio por curso, "
            "una serie por mes. Replica la página 3 del informe."
        ),
        config=chart_config(
            "grouped_bar", METRIC_SIMCE_EST,
            titulo="Evolución del SIMCE Promedio por Curso y Mes",
            x_field="Curso", y_field="SIMCE", group_field="Mes",
            y_format="int", y_label="Puntaje SIMCE",
            stack_order=SIMCE_MES_ORDER,
            show_values=True,
        ),
    )

    # Replica "Evolución de Alumnos por Nivel de Logro, Curso y Mes" del
    # informe pág. 5: stacked bar agrupado con eje X de 2 niveles
    # (curso outer × mes inner) apilado por nivel de logro.
    ids["c_evolucion_niveles"] = upsert_chart(
        db, org_id,
        name="SIMCE — Evolución Niveles de Logro por Curso y Mes",
        description=(
            "Stacked bar agrupado: cantidad de estudiantes por nivel "
            "(Insuficiente/Elemental/Adecuado), agrupado por curso y mes. "
            "Replica la página 5 del informe SIMCE."
        ),
        config=chart_config(
            "stacked_grouped_bar", METRIC_SIMCE_EST,
            titulo="Evolución de Alumnos por Nivel, Curso y Mes",
            x_field="Mes", group_field="Curso", stack_field="Logro",
            stack_order=["Insuficiente", "Elemental", "Adecuado"],
            x_order=SIMCE_MES_ORDER,
            color_palette="semaforo",
            palette_reversed=True,
            show_values=True,
            y_label="N° Estudiantes",
            legend_title="Nivel",
        ),
    )

    ids["c_heatmap_curso_eje"] = upsert_chart(
        db, org_id,
        name="SIMCE — Heatmap Curso × Eje Temático",
        description="Mapa de calor del % acierto por curso × eje. Identifica techos transversales.",
        config=chart_config(
            "heatmap", METRIC_SIMCE_PREG,
            titulo="Heatmap Curso × Eje Temático",
            x_field="Eje Temático", group_field="Curso", y_field="Logro",
            y_format="percent", color_palette="rojo_calor", palette_reversed=True,
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
                    cfg_chart_item(ids["c_rend_curso"], "Rendimiento por Curso"),
                    cfg_chart_item(ids["c_box_curso"], "Distribución por Curso"),
                ], cols=2),
                row([
                    cfg_chart_item(ids["c_pie_logro"], "Composición Global"),
                    cfg_chart_item(ids["c_stack_niveles"], "Niveles por Curso"),
                ], cols=2),
            ]),
            tab("curso", "Por Curso", [
                row([course_selector_item()], cols=1),
                row([
                    cfg_chart_item(ids["c_habilidad"], "Logro por Habilidad"),
                    cfg_chart_item(ids["c_eje"], "Logro por Eje"),
                ], cols=2),
                row([cfg_chart_item(ids["c_heatmap_curso_eje"], "Heatmap Curso × Eje")], cols=1),
                row([cfg_table_item(ids["t_pregunta"], "Logro por Pregunta")], cols=1),
                row([cfg_table_item(ids["t_estad_pregunta"], "Estadística por Pregunta")], cols=1),
                row([cfg_table_item(ids["t_riesgo"], "Estudiantes en Riesgo")], cols=1),
            ]),
            tab("estudiante", "Por Estudiante", [
                row([course_selector_item()], cols=1),
                row([cfg_table_item(ids["t_alumno"], "Logro por Alumno")], cols=1),
            ]),
            tab("tendencia", "Tendencia", [
                row([cfg_chart_item(ids["c_evolucion_logro"], "Evolución Logro Promedio por Curso y Mes")], cols=1),
                row([cfg_chart_item(ids["c_evolucion_simce"], "Evolución SIMCE Promedio por Curso y Mes")], cols=1),
                row([cfg_chart_item(ids["c_evolucion_niveles"], "Evolución de Alumnos por Nivel, Curso y Mes")], cols=1),
            ]),
        ]
    }

    update_indicator_layout(db, org_id, "SIMCE", layout)
    return ids
