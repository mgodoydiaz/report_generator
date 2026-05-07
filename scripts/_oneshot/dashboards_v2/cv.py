"""Dashboards Cálculo Veloz — specs y layout.

Cálculo Veloz mide velocidad de cálculo aritmético. La cadencia operativa
real (confirmada con la fundación 2026-05-06) es:

    2 pruebas por mes × 6 meses (ABRIL → OCTUBRE) en un año académico.

Cada estudiante recibe Puntaje (operaciones correctas), Nota (transformación
piecewise-linear del puntaje), Nivel cualitativo y un flag PIE (Programa de
Integración Escolar).

Modelo de datos (id_metric=9):
    Value fields: Puntaje (int), Nota (float), Nivel (str), PIE (int 0/1).
    Dimensiones: Establecimiento, Año, Curso, Fecha, Mes, N Prueba, Nombre, RUT.

achievement_levels (peor → mejor):
    INICIAL | BÁSICO | INTERMEDIO | AVANZADO | EXPERTO

OBSERVACIÓN crítica de los datos 2025: hay un salto de dificultad entre
MAYO (nota promedio 5.3) y JUNIO-JULIO (3.3). Esto NO es un retroceso de
los alumnos sino que la prueba se vuelve más exigente al pasar al
2do semestre. El layout incluye una nota explicativa en el tab Tendencia
para evitar lecturas erróneas.

Tabs:
    1. Vista General      — KPIs, distribución global, niveles por curso
    2. Última Evaluación  — snapshot de la eval más reciente (foco accionable)
    3. Evolución Mensual  — tendencia mes a mes con nota explicativa
    4. Por Curso          — listado nominal con histograma y filtro vivo
"""
from __future__ import annotations

from typing import Dict

from sqlalchemy.orm import Session

from backend.rgenerator.tooling.curso_order import sort_cursos
from backend.routers.tables import _load_metric_to_df

from .helpers import (
    cfg_chart_item,
    cfg_table_item,
    chart_config,
    col_agg,
    col_float,
    col_int,
    col_text,
    color_overrides_from_indicator,
    color_scale_linked,
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

METRIC_CV = 9

# Orden cronológico de los meses CV. NO usar orden alfabético (ABRIL,
# AGOSTO, etc.) porque rompe la lectura de la línea de evolución.
CV_MES_ORDER = ["ABRIL", "MAYO", "JUNIO-JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE"]

# Niveles del achievement: peor → mejor. Constante única para stack_order.
CV_NIVEL_ORDER = ["INICIAL", "BÁSICO", "INTERMEDIO", "AVANZADO", "EXPERTO"]

# Última evaluación al cierre 2025 (Mes + N Prueba más recientes con datos).
# Cuando se carguen Noviembre o nuevos meses, actualizar acá. La alternativa
# automática sería un derived `es_ultima_eval` pero por simplicidad usamos
# filtro hardcoded — más legible y suficiente para MVP.
CV_ULTIMA_EVAL_FILTERS = {"Mes": "OCTUBRE", "N Prueba": "2"}


def seed_cv(db: Session, org_id: int, indicator_id_cv: int) -> Dict[str, int]:
    ids: Dict[str, int] = {}

    # Colores oficiales del indicador para Niveles (INICIAL rojo →
    # EXPERTO verde). Heredan del achievement_levels para garantizar
    # consistencia con la página de Indicadores.
    nivel_colors = color_overrides_from_indicator(db, org_id, "Cálculo Veloz")

    # Orden chileno de cursos: I°A < I°B < ... < II°A < ... < III°A < ...
    # Se calcula leyendo los cursos reales del df y aplicándolos como
    # x_order en cada chart con eje Curso. Sin esto, pandas/Plotly ordenan
    # alfabético y "III°A" sale antes de "II°A" rompiendo la lectura.
    df_full = _load_metric_to_df(db, org_id, METRIC_CV)
    curso_order = sort_cursos(df_full["Curso"].dropna().unique()) if "Curso" in df_full.columns else []
    # Subset de cursos que rinden la última eval (algunos cursos no la
    # administran). Se usa solo en charts del tab "Última Evaluación".
    df_ultima = df_full[
        (df_full["Mes"] == CV_ULTIMA_EVAL_FILTERS["Mes"]) &
        (df_full["N Prueba"].astype(str) == str(CV_ULTIMA_EVAL_FILTERS["N Prueba"]))
    ] if "Mes" in df_full.columns and "N Prueba" in df_full.columns else df_full
    curso_order_ultima = sort_cursos(df_ultima["Curso"].dropna().unique()) if "Curso" in df_ultima.columns else []

    # ─────────────────────────────────────────────────────────────────────
    # TABLAS
    # ─────────────────────────────────────────────────────────────────────

    # Resumen anual por curso.
    ids["t_resumen_curso"] = upsert_table(
        db, org_id,
        name="Cálculo Veloz — Resumen por Curso (anual)",
        description="N° de estudiantes únicos, pruebas totales, nota promedio, mediana y rango por curso.",
        config=table_config(
            metric_id=METRIC_CV,
            columns=[
                col_text("Curso", "Curso", pinned=True),
                col_agg("N_estudiantes", "Nombre", "Estudiantes únicos", agg="nunique", fmt="int", decimals=0),
                col_agg("N_pruebas", "Puntaje", "Pruebas totales", agg="count", fmt="int", decimals=0),
                col_agg("Nota_mean", "Nota", "Nota Promedio", agg="mean", fmt="float", decimals=2),
                col_agg("Nota_median", "Nota", "Nota Mediana", agg="median", fmt="float", decimals=2),
                col_agg("Puntaje_mean", "Puntaje", "Puntaje Promedio", agg="mean", fmt="float", decimals=1),
                col_agg("Puntaje_min", "Puntaje", "Puntaje Mín", agg="min", fmt="int", decimals=0),
                col_agg("Puntaje_max", "Puntaje", "Puntaje Máx", agg="max", fmt="int", decimals=0),
            ],
            grouping={"by": "Curso"},
            sorting=[{"column": "Curso", "dir": "asc"}],
            search=False,
        ),
    )

    # Resumen por mes (cronológico). Útil para ver el efecto del cambio
    # de dificultad entre semestres y la cobertura por mes.
    ids["t_resumen_mes"] = upsert_table(
        db, org_id,
        name="Cálculo Veloz — Resumen Mensual",
        description="Cobertura y rendimiento por mes. Cuando hay 2 pruebas en el mismo mes, agrega ambas.",
        config=table_config(
            metric_id=METRIC_CV,
            columns=[
                col_text("Mes", "Mes", pinned=True),
                col_agg("N_estudiantes", "Nombre", "Estudiantes únicos", agg="nunique", fmt="int", decimals=0),
                col_agg("N_pruebas", "Puntaje", "Pruebas", agg="count", fmt="int", decimals=0),
                col_agg("Nota_mean", "Nota", "Nota Promedio", agg="mean", fmt="float", decimals=2),
                col_agg("Puntaje_mean", "Puntaje", "Puntaje Promedio", agg="mean", fmt="float", decimals=1),
                col_agg("Puntaje_min", "Puntaje", "Mín", agg="min", fmt="int", decimals=0),
                col_agg("Puntaje_max", "Puntaje", "Máx", agg="max", fmt="int", decimals=0),
            ],
            grouping={"by": "Mes"},
            sorting=[{"column": "Mes", "dir": "asc"}],
            search=False,
        ),
    )

    # Listado nominal completo.
    ids["t_alumno"] = upsert_table(
        db, org_id,
        name="Cálculo Veloz — Listado de Estudiantes",
        description="Detalle nominal completo con puntaje, nota y nivel.",
        config=table_config(
            metric_id=METRIC_CV,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_text("Mes", "Mes"),
                col_text("N Prueba", "N° Prueba"),
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

    # Listado de la ÚLTIMA evaluación — vista accionable.
    ids["t_ultima_eval"] = upsert_table(
        db, org_id,
        name="Cálculo Veloz — Listado Última Evaluación",
        description="Estudiantes evaluados en la prueba más reciente (filtro: Mes=OCTUBRE, N° Prueba=2). Ordenado por Nota ascendente para priorizar atención.",
        config=table_config(
            metric_id=METRIC_CV,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_int("Puntaje", "Puntaje"),
                col_float("Nota", "Nota", decimals=2),
                {
                    "key": "Nivel", "header": "Nivel", "format": "text",
                    "color_scale": color_scale_linked(indicator_id_cv, "Nivel"),
                },
                {"key": "PIE", "header": "PIE", "format": "int", "decimals": 0},
            ],
            filters=CV_ULTIMA_EVAL_FILTERS,
            sorting=[
                {"column": "Nota", "dir": "asc"},
                {"column": "Curso", "dir": "asc"},
            ],
            page_size=100,
        ),
    )

    # Estudiantes en riesgo en la última evaluación (Nivel ∈ INICIAL/BÁSICO).
    ids["t_riesgo_ultima"] = upsert_table(
        db, org_id,
        name="Cálculo Veloz — Estudiantes en Riesgo (Última Evaluación)",
        description="Estudiantes con Nivel = INICIAL o BÁSICO en la prueba más reciente. Población prioritaria para refuerzo.",
        config=table_config(
            metric_id=METRIC_CV,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_int("Puntaje", "Puntaje"),
                col_float("Nota", "Nota", decimals=2),
                {
                    "key": "Nivel", "header": "Nivel", "format": "text",
                    "color_scale": color_scale_linked(indicator_id_cv, "Nivel"),
                },
                {"key": "PIE", "header": "PIE", "format": "int", "decimals": 0},
            ],
            filters={**CV_ULTIMA_EVAL_FILTERS, "Nivel": ["INICIAL", "BÁSICO"]},
            sorting=[
                {"column": "Nota", "dir": "asc"},
                {"column": "Curso", "dir": "asc"},
            ],
            page_size=100,
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # GRÁFICOS — VISTA GENERAL (anual)
    # ─────────────────────────────────────────────────────────────────────

    ids["c_pie_nivel"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Composición Global por Nivel",
        description="Pie: distribución global de niveles considerando todas las evaluaciones del año.",
        config=chart_config(
            "pie", METRIC_CV,
            titulo="Composición Global por Nivel",
            category_field="Nivel",
            color_overrides=nivel_colors,
        ),
    )

    ids["c_stack_nivel_curso"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Niveles por Curso (anual)",
        description="Stacked: composición de niveles agregada del año, por curso. Cada estudiante puede aportar múltiples filas (1 por evaluación).",
        config=chart_config(
            "stacked_bar", METRIC_CV,
            titulo="Niveles por Curso (anual)",
            x_field="Curso", stack_field="Nivel",
            stack_order=CV_NIVEL_ORDER,
            x_order=curso_order,
            color_overrides=nivel_colors,
            y_label="N° Evaluaciones",
            y_format="int",
            legend_title="Nivel",
            show_values=True,
        ),
    )

    ids["c_nota_curso"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Nota Promedio por Curso (anual)",
        description="Barra: nota promedio anual por curso.",
        config=chart_config(
            "bar", METRIC_CV,
            titulo="Nota Promedio por Curso (anual)",
            x_field="Curso", y_field="Nota",
            y_label="Nota promedio",
            x_label="Curso",
            x_order=curso_order,
            show_values=True,
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # GRÁFICOS — ÚLTIMA EVALUACIÓN
    # ─────────────────────────────────────────────────────────────────────

    ids["c_pie_nivel_ultima"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Composición Última Evaluación",
        description="Pie: distribución de niveles considerando solo la prueba más reciente.",
        config=chart_config(
            "pie", METRIC_CV,
            titulo="Composición — Última Evaluación",
            category_field="Nivel",
            color_overrides=nivel_colors,
            filters=CV_ULTIMA_EVAL_FILTERS,
        ),
    )

    ids["c_stack_nivel_curso_ultima"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Niveles por Curso (Última Evaluación)",
        description="Stacked: composición de niveles por curso solo en la última prueba. Vista accionable: muestra el estado actual de cada curso.",
        config=chart_config(
            "stacked_bar", METRIC_CV,
            titulo="Niveles por Curso — Última Evaluación",
            x_field="Curso", stack_field="Nivel",
            stack_order=CV_NIVEL_ORDER,
            x_order=curso_order_ultima,
            color_overrides=nivel_colors,
            y_label="N° Estudiantes",
            y_format="int",
            legend_title="Nivel",
            show_values=True,
            filters=CV_ULTIMA_EVAL_FILTERS,
        ),
    )

    ids["c_nota_curso_ultima"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Nota Promedio por Curso (Última Evaluación)",
        description="Barra: nota promedio por curso en la última prueba. Comparable cross-curso porque todos rinden el mismo formato.",
        config=chart_config(
            "bar", METRIC_CV,
            titulo="Nota Promedio por Curso — Última Evaluación",
            x_field="Curso", y_field="Nota",
            y_label="Nota",
            x_label="Curso",
            x_order=curso_order_ultima,
            show_values=True,
            filters=CV_ULTIMA_EVAL_FILTERS,
        ),
    )

    ids["c_box_ultima"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Distribución Puntaje (Última Evaluación)",
        description="Boxplot: dispersión del puntaje por curso en la última prueba. Identifica outliers altos y bajos.",
        config=chart_config(
            "box", METRIC_CV,
            titulo="Distribución de Puntaje por Curso — Última Evaluación",
            x_field="Curso", y_field="Puntaje",
            y_label="Puntaje",
            x_label="Curso",
            x_order=curso_order_ultima,
            filters=CV_ULTIMA_EVAL_FILTERS,
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # GRÁFICOS — EVOLUCIÓN MENSUAL
    # ─────────────────────────────────────────────────────────────────────

    # Línea con orden cronológico explícito de Mes.
    ids["c_evolucion_nota"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Evolución de Nota por Mes",
        description="Línea: nota promedio de todos los estudiantes mes a mes. Cuando hay 2 pruebas en el mismo mes, agrega ambas.",
        config=chart_config(
            "line", METRIC_CV,
            titulo="Evolución de Nota — Promedio Mensual",
            x_field="Mes", y_field="Nota",
            y_label="Nota promedio",
            x_label="Mes",
            x_order=CV_MES_ORDER,
            show_values=True,
        ),
    )

    ids["c_evolucion_puntaje"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Evolución de Puntaje por Mes",
        description="Línea: puntaje promedio mes a mes. Útil para identificar el salto de dificultad entre semestres.",
        config=chart_config(
            "line", METRIC_CV,
            titulo="Evolución de Puntaje — Promedio Mensual",
            x_field="Mes", y_field="Puntaje",
            y_label="Puntaje promedio",
            x_label="Mes",
            x_order=CV_MES_ORDER,
            show_values=True,
        ),
    )

    # Stacked Niveles por Mes — composición global mes a mes.
    ids["c_stack_nivel_mes"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Niveles por Mes",
        description="Stacked: cómo evoluciona la composición de niveles a lo largo del año. El 'salto de dificultad' al cambiar de semestre se ve como una caída en EXPERTO/AVANZADO.",
        config=chart_config(
            "stacked_bar", METRIC_CV,
            titulo="Niveles por Mes",
            x_field="Mes", stack_field="Nivel",
            stack_order=CV_NIVEL_ORDER,
            x_order=CV_MES_ORDER,
            color_overrides=nivel_colors,
            y_label="N° Evaluaciones",
            y_format="int",
            legend_title="Nivel",
            show_values=True,
        ),
    )

    # Línea por curso (multi-serie) — útil para ver qué curso avanzó más.
    ids["c_evolucion_curso"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Evolución de Nota por Curso",
        description="Línea con una serie por curso. Permite comparar qué cursos mejoran y cuáles se estancan a lo largo del año.",
        config=chart_config(
            "line", METRIC_CV,
            titulo="Evolución de Nota por Curso",
            x_field="Mes", y_field="Nota", group_field="Curso",
            y_label="Nota promedio",
            x_label="Mes",
            x_order=CV_MES_ORDER,
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # GRÁFICOS — POR CURSO
    # ─────────────────────────────────────────────────────────────────────

    ids["c_box_puntaje"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Distribución de Puntaje (anual)",
        description="Boxplot: dispersión del puntaje por curso considerando todas las evaluaciones del año.",
        config=chart_config(
            "box", METRIC_CV,
            titulo="Distribución de Puntaje por Curso (anual)",
            x_field="Curso", y_field="Puntaje",
            y_label="Puntaje",
            x_label="Curso",
            x_order=curso_order,
        ),
    )

    ids["c_hist_puntaje"] = upsert_chart(
        db, org_id,
        name="Cálculo Veloz — Histograma de Puntaje",
        description="Histograma global del puntaje. Filtrable por curso vía course_selector.",
        config=chart_config(
            "histogram", METRIC_CV,
            titulo="Histograma de Puntaje",
            y_field="Puntaje",
            y_label="N° Evaluaciones",
            x_label="Puntaje",
            bins=15,
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # LAYOUT
    # ─────────────────────────────────────────────────────────────────────
    layout = {
        "tabs": [
            tab("general", "Vista General", [
                row([kpis_item()], cols=4),
                row([cfg_table_item(ids["t_resumen_curso"], "Resumen Anual por Curso")], cols=1),
                row([
                    cfg_chart_item(ids["c_pie_nivel"], "Composición Global"),
                    cfg_chart_item(ids["c_stack_nivel_curso"], "Niveles por Curso"),
                ], cols=2),
                row([cfg_chart_item(ids["c_nota_curso"], "Nota Promedio por Curso")], cols=1),
            ]),
            tab("ultima", "Última Evaluación", [
                row([note_item(
                    "Vista filtrada a la prueba más reciente (Mes = OCTUBRE, "
                    "N° Prueba = 2). Es la foto actual del colegio y la base "
                    "para decidir refuerzo del próximo período. El listado de "
                    "riesgo aísla a los estudiantes en INICIAL/BÁSICO ordenados "
                    "por nota ascendente — los primeros son la prioridad #1.",
                    tone="tip",
                    title="Foco accionable",
                )], cols=1),
                row([note_item(
                    "Importante: no todos los cursos rinden todas las pruebas. "
                    "En esta evaluación participan solo los cursos que la "
                    "administraron — los que falten en los gráficos no son "
                    "ausentismo, sino que aún no entregaron datos para esta toma.",
                    tone="info",
                    title="Sobre la cobertura",
                )], cols=1),
                row([
                    cfg_chart_item(ids["c_pie_nivel_ultima"], "Composición Última Eval"),
                    cfg_chart_item(ids["c_stack_nivel_curso_ultima"], "Niveles por Curso"),
                ], cols=2),
                row([
                    cfg_chart_item(ids["c_nota_curso_ultima"], "Nota Promedio por Curso"),
                    cfg_chart_item(ids["c_box_ultima"], "Distribución de Puntaje"),
                ], cols=2),
                row([cfg_table_item(ids["t_ultima_eval"], "Listado Completo Última Evaluación")], cols=1),
                row([cfg_table_item(ids["t_riesgo_ultima"], "Estudiantes en Riesgo (INICIAL / BÁSICO)")], cols=1),
            ]),
            tab("tendencia", "Evolución Mensual", [
                row([note_item(
                    "El protocolo de Cálculo Veloz aplica 2 pruebas por mes. La "
                    "agregación de esta vista promedia ambas pruebas dentro del "
                    "mes. ATENCIÓN: entre MAYO y JUNIO-JULIO la prueba aumenta "
                    "su nivel de dificultad (cambio de semestre), por lo que la "
                    "caída de nota/puntaje en ese punto NO refleja un retroceso "
                    "de los alumnos sino un cambio de la escala del instrumento. "
                    "Compará dentro del semestre para una lectura limpia.",
                    tone="warn",
                    title="Cómo leer la evolución",
                )], cols=1),
                row([cfg_table_item(ids["t_resumen_mes"], "Resumen Mensual")], cols=1),
                row([
                    cfg_chart_item(ids["c_evolucion_nota"], "Nota Promedio Mensual"),
                    cfg_chart_item(ids["c_evolucion_puntaje"], "Puntaje Promedio Mensual"),
                ], cols=2),
                row([cfg_chart_item(ids["c_stack_nivel_mes"], "Composición de Niveles a lo Largo del Año")], cols=1),
                row([cfg_chart_item(ids["c_evolucion_curso"], "Evolución por Curso (multi-serie)")], cols=1),
            ]),
            tab("curso", "Por Curso", [
                row([course_selector_item()], cols=1),
                row([cfg_chart_item(ids["c_box_puntaje"], "Distribución de Puntaje (filtrable)")], cols=1),
                row([cfg_chart_item(ids["c_hist_puntaje"], "Histograma de Puntaje (filtrable)")], cols=1),
                row([cfg_table_item(ids["t_alumno"], "Listado de Estudiantes (todas las evaluaciones)")], cols=1),
            ]),
        ]
    }

    update_indicator_layout(db, org_id, "Cálculo Veloz", layout)
    return ids
