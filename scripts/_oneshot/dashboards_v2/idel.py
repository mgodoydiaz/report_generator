"""Dashboards IDEL — specs y layout.

IDEL = Indicador de Desarrollo de Lectura (PDL Woodcock). Aplica a
estudiantes pequeños (Kínder–6° básico) y mide riesgo lector cualitativo
en 6 subpruebas.

Modelo de datos (id_metric=8):
    Value fields: Puntaje (int), Género (int), Evaluadora (str),
                  Nivel de Riesgo (str: Crítico|Alto Riesgo|Cierto Riesgo|Bajo Riesgo).
    Dimensiones: Establecimiento ("Panguipulli"), Año, Curso ("1° BÁSICO"...),
                 Evaluación (subprueba: CT/FLO/FNL/FSF/ILP/VSD), Nombre, RUT,
                 Versión ("v1"/"v2"/"v3").

DECISIÓN DE DISEÑO (2026-05-06):
El indicador IDEL es CUALITATIVO. El informe PDL Woodcock no muestra
"puntaje promedio" porque las 6 subpruebas tienen escalas distintas
(CT 0-25, FLO 0-60, FSF 0-78, etc.) — promediarlas no tiene sentido
estadístico. Por eso este dashboard NO expone:
    - KPI "Puntaje promedio"
    - Bar "Puntaje por curso"
    - Boxplot "Distribución de puntaje"
    - Line "Evolución de puntaje"
    - Cols Puntaje promedio/min/max en tablas

En cambio expone solo análisis CUALITATIVO sobre niveles de riesgo,
agrupado por curso y subprueba.

Tabs:
    1. Vista General  — composición global, niveles por curso
    2. Por Curso      — selector + listado de estudiantes
    3. Tendencia      — distribución de niveles por versión (v1→v2→v3)
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

# Orden cronológico de versiones IDEL (v1 → v3).
IDEL_VERSION_ORDER = ["v1", "v2", "v3"]

# Orden de severidad de niveles (peor → mejor).
IDEL_NIVEL_ORDER = ["Crítico", "Alto Riesgo", "Cierto Riesgo", "Bajo Riesgo"]


def seed_idel(db: Session, org_id: int, indicator_id_idel: int) -> Dict[str, int]:
    ids: Dict[str, int] = {}

    # ─────────────────────────────────────────────────────────────────────
    # TABLAS
    # ─────────────────────────────────────────────────────────────────────

    # Resumen por curso: cuenta estudiantes únicos (no filas) y total
    # de evaluaciones (filas). NO se incluye Puntaje promedio porque
    # mezclaría escalas de 6 subpruebas distintas.
    ids["t_resumen_curso"] = upsert_table(
        db, org_id,
        name="IDEL — Resumen por Curso",
        description=(
            "N° de estudiantes únicos y N° de evaluaciones (filas) por curso. "
            "Cada estudiante puede tener hasta 18 evaluaciones (6 subpruebas × "
            "3 versiones), por eso N° evaluaciones es alto."
        ),
        config=table_config(
            metric_id=METRIC_IDEL,
            columns=[
                col_text("Curso", "Curso", pinned=True),
                # Conteo de estudiantes únicos (count distinct sobre Nombre).
                col_agg("Estudiantes", "Nombre", "Estudiantes únicos",
                        agg="nunique", fmt="int", decimals=0),
                # Total de evaluaciones (filas).
                col_agg("Evaluaciones", "Nivel de Riesgo", "Evaluaciones",
                        agg="count", fmt="int", decimals=0),
            ],
            grouping={"by": "Curso"},
            sorting=[{"column": "Curso", "dir": "asc"}],
            search=False,
        ),
    )

    ids["t_alumno"] = upsert_table(
        db, org_id,
        name="IDEL — Listado de Estudiantes",
        description=(
            "Detalle nominal: cada fila es un estudiante en una subprueba × "
            "versión. La columna Puntaje aparece como referencia, pero el "
            "análisis principal es por Nivel de Riesgo."
        ),
        config=table_config(
            metric_id=METRIC_IDEL,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_text("Evaluación", "Subprueba"),
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
            "Estudiantes con nivel de riesgo Crítico o Alto Riesgo. La tabla "
            "está ordenada para mostrar primero los casos más severos. "
            "Filtrar por curso y subprueba para ver listado focalizado."
        ),
        config=table_config(
            metric_id=METRIC_IDEL,
            # Filter: solo Crítico/Alto Riesgo (filtro server-side via
            # data_source.filters porque el field es value, no dimension)
            filters={},
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_text("Evaluación", "Subprueba"),
                col_text("Versión", "Versión"),
                col_int("Puntaje", "Puntaje"),
                {
                    "key": "Nivel de Riesgo", "header": "Nivel", "format": "text",
                    "color_scale": color_scale_linked(indicator_id_idel, "Nivel de Riesgo"),
                },
                col_text("Evaluadora", "Evaluadora"),
            ],
            sorting=[
                {"column": "Curso", "dir": "asc"},
                {"column": "Puntaje", "dir": "asc"},
            ],
            page_size=80,
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # GRÁFICOS — solo cualitativos
    # ─────────────────────────────────────────────────────────────────────

    ids["c_pie_riesgo"] = upsert_chart(
        db, org_id,
        name="IDEL — Composición por Nivel de Riesgo",
        description="Pie: distribución global de niveles de riesgo.",
        config=chart_config(
            "pie", METRIC_IDEL,
            titulo="Composición por Nivel de Riesgo",
            category_field="Nivel de Riesgo",
            color_palette="semaforo", palette_reversed=True,
        ),
    )

    # Mapa de riesgo (heatmap Curso × Subprueba) — replica pág 1 del informe.
    # El "es_riesgo" es un derived_column lookup_dict que mapea Nivel de
    # Riesgo a 0/1 (1 si Crítico o Alto Riesgo). El agg=mean da el % de
    # estudiantes en riesgo. Paleta rojo_calor: 0 = amarillo claro
    # (sin alerta), 1 = rojo intenso (alta concentración de Crítico+Alto).
    ids["c_mapa_riesgo"] = upsert_chart(
        db, org_id,
        name="IDEL — Mapa de Riesgo (Curso × Subprueba)",
        description=(
            "Heatmap del % de estudiantes en Crítico o Alto Riesgo por curso "
            "y subprueba. Réplica de la página 1 del informe PDL Woodcock. "
            "Rojo = mayor proporción en riesgo, amarillo = baja proporción."
        ),
        config=chart_config(
            "heatmap", METRIC_IDEL,
            titulo="Mapa de Riesgo — % Crítico o Alto Riesgo",
            x_field="Evaluación", group_field="Curso", y_field="es_riesgo",
            aggregation="mean", y_format="percent",
            color_palette="rojo_calor",
        ),
    )

    ids["c_stack_riesgo_curso"] = upsert_chart(
        db, org_id,
        name="IDEL — Niveles de Riesgo por Curso",
        description=(
            "Stacked bar: cantidad de evaluaciones por nivel y curso. "
            "Crítico abajo (rojo), Bajo Riesgo arriba (verde). "
            "Cada estudiante aporta múltiples filas (una por subprueba × "
            "versión), por eso la cantidad por curso es alta."
        ),
        config=chart_config(
            "stacked_bar", METRIC_IDEL,
            titulo="Niveles de Riesgo por Curso",
            x_field="Curso", stack_field="Nivel de Riesgo",
            stack_order=IDEL_NIVEL_ORDER,
            color_palette="semaforo", palette_reversed=True,
            show_values=True,
            y_label="N° Evaluaciones",
            legend_title="Nivel",
        ),
    )

    # Stacked apilado por versión: cómo cambia la composición de niveles
    # en cada aplicación (v1 → v2 → v3). Aproxima el "Distribución de
    # niveles por evaluación" que pide el informe.
    ids["c_stack_riesgo_version"] = upsert_chart(
        db, org_id,
        name="IDEL — Niveles de Riesgo por Versión",
        description=(
            "Stacked bar: cantidad de evaluaciones por nivel a lo largo de "
            "las 3 versiones del año (v1, v2, v3). Permite ver si la "
            "composición global mejora entre aplicaciones."
        ),
        config=chart_config(
            "stacked_bar", METRIC_IDEL,
            titulo="Niveles de Riesgo por Versión",
            x_field="Versión", stack_field="Nivel de Riesgo",
            stack_order=IDEL_NIVEL_ORDER,
            x_order=IDEL_VERSION_ORDER,
            color_palette="semaforo", palette_reversed=True,
            show_values=True,
            y_label="N° Evaluaciones",
            legend_title="Nivel",
        ),
    )

    # Roster pivot_matrix — replica la pág 6 del informe IDEL.
    # Filas = Estudiante, columnas = Subprueba×Versión, celda = Nivel.
    # Útil para ver de un vistazo el progreso de cada estudiante en
    # cada subprueba a lo largo de las 3 versiones del año.
    ids["c_roster"] = upsert_chart(
        db, org_id,
        name="IDEL — Roster (Estudiante × Subprueba × Versión)",
        description=(
            "Tabla pivote: cada fila es un estudiante, cada columna es una "
            "combinación Subprueba×Versión. La celda muestra el Nivel de "
            "Riesgo coloreado. Replica la página 6 del informe PDL Woodcock. "
            "Muy útil para ver progreso individual a lo largo de las 3 "
            "aplicaciones del año. RECOMENDACIÓN: filtrar por Curso para "
            "limitar el número de filas."
        ),
        config=chart_config(
            "pivot_matrix", METRIC_IDEL,
            titulo="Roster — Niveles por Estudiante",
            axis_field="Nombre",          # filas
            group_field="Evaluación",     # outer cols (Subprueba)
            x_field="Versión",            # inner cols
            y_field="Nivel de Riesgo",    # cell value
            stack_order=["CT", "FLO", "FNL", "FSF", "ILP", "VSD"],  # outer order
            x_order=IDEL_VERSION_ORDER,
        ),
    )

    # Stacked agrupado curso × versión × nivel — replica el informe pág 2
    # ("Distribución de niveles por evaluación") por cada curso.
    ids["c_stack_curso_version"] = upsert_chart(
        db, org_id,
        name="IDEL — Niveles por Curso y Versión",
        description=(
            "Stacked grouped bar: niveles apilados, eje X de 2 niveles "
            "(curso × versión). Replica la página 2 del informe IDEL — "
            "muestra la evolución del % de cada nivel a lo largo del año "
            "para cada curso."
        ),
        config=chart_config(
            "stacked_grouped_bar", METRIC_IDEL,
            titulo="Niveles por Curso y Versión",
            x_field="Versión", group_field="Curso", stack_field="Nivel de Riesgo",
            stack_order=IDEL_NIVEL_ORDER,
            x_order=IDEL_VERSION_ORDER,
            color_palette="semaforo", palette_reversed=True,
            show_values=True,
            y_label="N° Evaluaciones",
            legend_title="Nivel",
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # LAYOUT — sin componentes de Puntaje
    # ─────────────────────────────────────────────────────────────────────
    layout = {
        "tabs": [
            tab("general", "Vista General", [
                # KPIs: como column_roles ya no tiene logro_1 (Puntaje),
                # se mostrará solo Total Alumnos + Nivel Predominante.
                row([kpis_item()], cols=4),
                row([cfg_table_item(ids["t_resumen_curso"], "Resumen por Curso")], cols=1),
                row([cfg_chart_item(ids["c_mapa_riesgo"], "Mapa de Riesgo (Curso × Subprueba)")], cols=1),
                row([
                    cfg_chart_item(ids["c_pie_riesgo"], "Composición Global"),
                    cfg_chart_item(ids["c_stack_riesgo_curso"], "Niveles por Curso"),
                ], cols=2),
            ]),
            tab("curso", "Por Curso", [
                row([course_selector_item()], cols=1),
                row([cfg_chart_item(ids["c_roster"], "Roster — Niveles por Estudiante × Subprueba × Versión")], cols=1),
                row([cfg_table_item(ids["t_alumno"], "Listado de Estudiantes")], cols=1),
                row([cfg_table_item(ids["t_riesgo"], "Estudiantes en Riesgo")], cols=1),
            ]),
            tab("tendencia", "Tendencia", [
                row([cfg_chart_item(ids["c_stack_riesgo_version"], "Niveles de Riesgo por Versión")], cols=1),
                row([cfg_chart_item(ids["c_stack_curso_version"], "Niveles por Curso y Versión (réplica informe pág 2)")], cols=1),
            ]),
        ]
    }

    update_indicator_layout(db, org_id, "IDEL", layout)
    return ids
