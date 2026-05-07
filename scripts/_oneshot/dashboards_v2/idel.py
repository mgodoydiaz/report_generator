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
    color_overrides_from_indicator,
    color_scale_linked,
    course_selector_item,
    kpis_item,
    note_item,
    row,
    subprueba_selector_item,
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

    # Colores oficiales por nivel — leídos del indicador IDEL para que los
    # gráficos stacked/pie hereden exactamente los mismos colores que se ven
    # en la configuración del indicador (Crítico=rojo, Alto Riesgo=naranja,
    # Cierto Riesgo=amarillo, Bajo Riesgo=verde). Si el indicador todavía
    # no tiene achievement_levels, queda {} y los charts caen al
    # color_palette por defecto.
    nivel_colors = color_overrides_from_indicator(db, org_id, "IDEL")

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

    # Estudiantes en riesgo persistente: ordenado desc por Versiones_en_Riesgo
    # (derived field que cuenta cuántas versiones del estudiante en la
    # subprueba están en Crítico o Alto Riesgo). Persistente = ≥2.
    # 3 = Crítico/Alto en TODAS las versiones (peor)
    # 2 = en 2 versiones (persistente)
    # 1 = un riesgo aislado (recuperable)
    # 0 = sin riesgo
    ids["t_riesgo"] = upsert_table(
        db, org_id,
        name="IDEL — Estudiantes en Riesgo Persistente",
        description=(
            "Estudiantes con nivel Crítico o Alto Riesgo, ordenados por "
            "persistencia. Versiones_en_Riesgo cuenta en cuántas de las 3 "
            "evaluaciones del año el estudiante estuvo en riesgo para esa "
            "subprueba. Valor 2 o 3 indica caso persistente que requiere "
            "intervención prioritaria."
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
                col_int("Versiones_en_Riesgo", "Versiones en Riesgo"),
                col_text("Evaluadora", "Evaluadora"),
            ],
            sorting=[
                # Primero los más persistentes (3, 2), luego 1, después 0.
                {"column": "Versiones_en_Riesgo", "dir": "desc"},
                {"column": "Curso", "dir": "asc"},
                {"column": "Nombre", "dir": "asc"},
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
            color_palette="semaforo_4", palette_reversed=True,
            color_overrides=nivel_colors,
        ),
    )

    # Cobertura: heatmap Curso × n_versiones_estudiante con count distinct
    # de Nombre. Replica la "Cobertura de estudiantes por curso" del
    # informe pág 1 (estudiantes únicos / en 1 eval / en 2 / en 3).
    ids["c_cobertura"] = upsert_chart(
        db, org_id,
        name="IDEL — Cobertura de Estudiantes por Curso",
        description=(
            "Matriz Curso × N° de versiones evaluadas. Cada celda muestra "
            "cuántos estudiantes únicos del curso participaron en exactamente "
            "1, 2 o 3 versiones del año. Replica la tabla 'Cobertura' de la "
            "página 1 del informe IDEL."
        ),
        config=chart_config(
            "heatmap", METRIC_IDEL,
            titulo="Estudiantes únicos evaluados en 1, 2 o 3 versiones",
            x_field="n_versiones_estudiante", group_field="Curso", y_field="Nombre",
            aggregation="nunique", color_palette="rojo_calor", palette_reversed=True,
            x_label="N° de versiones evaluadas (en el año)",
            y_label="Curso",
            y_format="int",
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
            color_palette="semaforo_4", palette_reversed=True,
            color_overrides=nivel_colors,
            show_values=True,
            y_label="N° Evaluaciones",
            y_format="int",
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
            color_palette="semaforo_4", palette_reversed=True,
            color_overrides=nivel_colors,
            show_values=True,
            y_label="N° Evaluaciones",
            y_format="int",
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

    # Matriz de transición — replica las 6 matrices de la pág 4 del informe
    # (una por subprueba). Heatmap de count(estudiantes únicos) cruzando
    # nivel_inicial × nivel_final. Diagonal = mantuvo, sobre diagonal =
    # mejoró, debajo = empeoró. El subprueba_selector permite ver subprueba
    # por subprueba; sin selector se mezcla todo (vista global).
    ids["c_transicion"] = upsert_chart(
        db, org_id,
        name="IDEL — Matriz de Transición (Nivel inicial × Nivel final)",
        description=(
            "Heatmap del recorrido entre v1 y la última versión disponible. "
            "Filas = nivel inicial; Columnas = nivel final. Cada celda es la "
            "cantidad de estudiantes únicos que pasaron de ese nivel inicial "
            "al final, dentro de la subprueba activa. Diagonal = mantuvo, "
            "sobre diagonal = mejoró, bajo diagonal = empeoró. Replica las 6 "
            "matrices de transición de la página 4 del informe IDEL Woodcock. "
            "RECOMENDACIÓN: usar el selector de subprueba para una lectura "
            "limpia (sin selector mezcla las 6 subpruebas)."
        ),
        config=chart_config(
            "heatmap", METRIC_IDEL,
            titulo="Matriz de Transición — Nivel inicial → Nivel final",
            x_field="nivel_final",       # columnas
            group_field="nivel_inicial", # filas
            y_field="Nombre",
            aggregation="nunique",
            color_palette="rojo_calor", palette_reversed=True,
            x_label="Nivel final",
            y_label="Nivel inicial",
            y_format="int",
            stack_order=IDEL_NIVEL_ORDER,  # orden cols (peor→mejor)
            x_order=IDEL_NIVEL_ORDER,      # orden rows
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
            color_palette="semaforo_4", palette_reversed=True,
            color_overrides=nivel_colors,
            show_values=True,
            y_label="N° Evaluaciones",
            y_format="int",
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
                row([cfg_chart_item(ids["c_cobertura"], "Cobertura de Estudiantes por Curso")], cols=1),
                row([cfg_chart_item(ids["c_mapa_riesgo"], "Mapa de Riesgo (Curso × Subprueba)")], cols=1),
                row([
                    cfg_chart_item(ids["c_pie_riesgo"], "Composición Global"),
                    cfg_chart_item(ids["c_stack_riesgo_curso"], "Niveles por Curso"),
                ], cols=2),
            ]),
            tab("curso", "Por Curso", [
                row([course_selector_item()], cols=1),
                # Selector de subprueba (Evaluación) — al activarlo, el Roster
                # y los listados se filtran a esa subprueba específica.
                row([subprueba_selector_item(field="_habilidad")], cols=1),
                row([cfg_chart_item(ids["c_roster"], "Roster — Niveles por Estudiante × Subprueba × Versión")], cols=1),
                row([cfg_table_item(ids["t_alumno"], "Listado de Estudiantes")], cols=1),
                row([cfg_table_item(ids["t_riesgo"], "Estudiantes en Riesgo")], cols=1),
            ]),
            tab("tendencia", "Tendencia", [
                row([note_item(
                    "5° y 6° BÁSICO no rinden la evaluación v3 según el protocolo IDEL. "
                    "Para esos cursos la columna v3 aparece vacía en el Roster y los "
                    "porcentajes de tendencia se calculan solo sobre 1° a 4° BÁSICO.",
                    tone="info",
                    title="Sobre las versiones evaluadas",
                )], cols=1),
                row([cfg_chart_item(ids["c_stack_riesgo_version"], "Niveles de Riesgo por Versión")], cols=1),
                row([cfg_chart_item(ids["c_stack_curso_version"], "Niveles por Curso y Versión (réplica informe pág 2)")], cols=1),
                row([note_item(
                    "Filtrá una subprueba para una lectura más precisa: sin filtro la matriz mezcla "
                    "las 6 subpruebas. Cada celda es la cantidad de estudiantes únicos que pasaron del "
                    "nivel inicial (filas) al final (columnas). Diagonal = mantuvo, sobre diagonal = "
                    "mejoró, bajo diagonal = empeoró.",
                    tone="tip",
                    title="Cómo leer la matriz de transición",
                )], cols=1),
                row([subprueba_selector_item(field="_habilidad")], cols=1),
                row([cfg_chart_item(ids["c_transicion"], "Matriz de Transición — Nivel inicial → Nivel final")], cols=1),
            ]),
        ]
    }

    update_indicator_layout(db, org_id, "IDEL", layout)
    return ids
