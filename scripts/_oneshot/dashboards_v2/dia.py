"""Dashboards DIA — specs y layout.

Modelo de datos:
    - id_metric=6 (Resultados DIA por estudiante): Logro (float), Nivel Logro
      (str: Inicial|Intermedio|Avanzado), Logro Promedio.
    - id_metric=7 (Resultados DIA por Pregunta): Logro (float), Nivel Logro.
    - Dimensiones compartidas: Establecimiento, Año, Curso, Asignatura,
      Habilidad, Hito (DIAGNOSTICO|INTERMEDIO|CIERRE), Nivel, Nombre.
    - Dimensiones solo de preguntas: Eje Temático, Pregunta, N OA, Indicador.

Tabs propuestos:
    1. Vista General      — KPIs, resumen, distribución, gráfico por nivel
    2. Por Curso          — selector + habilidades + ítems + estudiantes
    3. Por Estudiante     — riesgo + scatter habilidad-logro
    4. Tendencia          — comparación entre hitos (Diagnóstico/Intermedio/Cierre)
    5. Comparativa Establ.— promedios por curso × establecimiento, por hito

Specs creados (ASCII en nombres para evitar problemas de codificación):
    Tablas:
        DIA — Resumen por Curso
        DIA — Logro por Alumno
        DIA — Logro por Pregunta
        DIA — Comparativa entre Hitos (por curso)
        DIA — Estudiantes en Riesgo
        DIA — Brecha entre Establecimientos
    Gráficos:
        DIA — Logro Promedio por Curso
        DIA — Logro Promedio por Nivel
        DIA — Distribución de Logro por Curso (boxplot)
        DIA — Cantidad de Alumnos por Nivel de Logro (stacked)
        DIA — Logro por Eje Temático
        DIA — Logro por Habilidad
        DIA — Tendencia de Logro por Hito (line)
        DIA — Heatmap Curso × Eje Temático
        DIA — Logro por Curso × Establecimiento (grouped)
        DIA — Tendencia por Establecimiento (line)
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

METRIC_DIA_EST = 6
METRIC_DIA_PREG = 7

# Orden cronológico de hitos DIA (Diagnóstico → Intermedio → Cierre).
# Se aplica como x_order en charts con eje X = Hito para que no salga
# en orden alfabético (CIERRE primero, etc.).
DIA_HITO_ORDER = ["DIAGNOSTICO", "INTERMEDIO", "CIERRE"]


def seed_dia(db: Session, org_id: int, indicator_id_dia: int) -> Dict[str, int]:
    """Crea/actualiza specs DIA y devuelve mapa nombre→id_spec."""

    ids: Dict[str, int] = {}

    # ─────────────────────────────────────────────────────────────────────
    # TABLAS
    # ─────────────────────────────────────────────────────────────────────

    # 1. Resumen por curso (replica el "Cuadro Resumen Logro" del PDF pág. 1)
    ids["t_resumen_curso"] = upsert_table(
        db, org_id,
        name="DIA — Resumen por Curso",
        description=(
            "Cuadro resumen del logro por curso: N° alumnos, logro promedio, "
            "mínimo, máximo y desviación estándar. Reemplaza la primera "
            "página del informe DIA en PDF."
        ),
        config=table_config(
            metric_id=METRIC_DIA_EST,
            columns=[
                col_text("Curso", "Curso", pinned=True),
                col_agg("N_alumnos", "Logro", "N° Alumnos", agg="count", fmt="int", decimals=0),
                col_agg(
                    "Logro_mean", "Logro", "Logro Promedio",
                    agg="mean", fmt="percent", decimals=1,
                    color_scale=color_scale_diverging_logro(),
                ),
                col_agg("Logro_min", "Logro", "Logro Mín", agg="min", fmt="percent", decimals=1),
                col_agg("Logro_max", "Logro", "Logro Máx", agg="max", fmt="percent", decimals=1),
                col_agg("Logro_std", "Logro", "Desviación", agg="std", fmt="percent", decimals=2),
            ],
            grouping={"by": "Curso"},
            sorting=[{"column": "Curso", "dir": "asc"}],
            search=False,
        ),
    )

    # 2. Logro por Alumno con columna Avance (slope DIAGNOSTICO→CIERRE)
    ids["t_logro_alumno"] = upsert_table(
        db, org_id,
        name="DIA — Logro por Alumno",
        description=(
            "Detalle nominal: logro, nivel y avance por estudiante. "
            "Avance es la pendiente del logro a lo largo de los hitos "
            "(DIAGNOSTICO → INTERMEDIO → CIERRE) — positivo si mejora."
        ),
        config=table_config(
            metric_id=METRIC_DIA_EST,
            columns=[
                col_int("Numero Lista", "N°", width=70, pinned=True),
                col_text("Nombre", "Estudiante"),
                col_text("Curso", "Curso"),
                col_text("Hito", "Hito"),
                col_percent("Logro", "Logro"),
                {
                    "key": "Nivel Logro",
                    "header": "Nivel",
                    "format": "text",
                    "color_scale": color_scale_linked(indicator_id_dia, "Nivel Logro"),
                },
                col_percent("Avance", "Avance", decimals=1),
            ],
            sorting=[
                {"column": "Curso", "dir": "asc"},
                {"column": "Numero Lista", "dir": "asc"},
            ],
            page_size=50,
        ),
    )

    # 3. Logro por Pregunta — útil dentro del tab "Por Curso"
    # Nota: DIA preguntas usa la dimensión "N Pregunta" (int) en lugar de
    # "Pregunta" (string); SIMCE sí tiene "Pregunta".
    ids["t_logro_pregunta"] = upsert_table(
        db, org_id,
        name="DIA — Logro por Pregunta",
        description=(
            "Detalle del % de acierto por pregunta (N°), con habilidad y eje "
            "temático asociados. Ayuda a identificar ítems problemáticos."
        ),
        config=table_config(
            metric_id=METRIC_DIA_PREG,
            columns=[
                col_int("N Pregunta", "N° Preg.", width=80, pinned=True),
                col_text("Habilidad", "Habilidad"),
                col_text("Eje Temático", "Eje"),
                col_text("Curso", "Curso"),
                col_text("Hito", "Hito"),
                col_percent("Logro", "% Acierto"),
                col_text("Nivel Logro", "Nivel"),
            ],
            sorting=[
                {"column": "Curso", "dir": "asc"},
                {"column": "N Pregunta", "dir": "asc"},
            ],
            page_size=80,
        ),
    )

    # 4. Comparativa entre Hitos (por curso × hito)
    # Usa grouping multi-columna ["Curso", "Hito"]: cada fila es la
    # combinación (curso, hito), con logro promedio y N°. Para ver el
    # avance entre Diagnóstico, Intermedio y Cierre por curso.
    ids["t_hitos"] = upsert_table(
        db, org_id,
        name="DIA — Comparativa entre Hitos",
        description=(
            "Resumen del logro promedio por curso y hito. Cada fila es una "
            "combinación (curso, hito). Para comparar el avance entre "
            "Diagnóstico, Intermedio y Cierre. NOTA: si un curso aún no "
            "tiene Cierre, esa fila simplemente no aparece."
        ),
        config=table_config(
            metric_id=METRIC_DIA_EST,
            columns=[
                col_text("Curso", "Curso", pinned=True),
                col_text("Hito", "Hito"),
                col_agg(
                    "Logro_mean", "Logro", "Logro Promedio",
                    agg="mean", fmt="percent", decimals=1,
                    color_scale=color_scale_diverging_logro(),
                ),
                col_agg("N", "Logro", "N°", agg="count", fmt="int", decimals=0),
            ],
            grouping={"by": ["Curso", "Hito"]},
            sorting=[{"column": "Curso", "dir": "asc"}, {"column": "Hito", "dir": "asc"}],
            search=False,
        ),
    )

    # 5. Estudiantes en Riesgo (Logro < 0.4)
    ids["t_riesgo"] = upsert_table(
        db, org_id,
        name="DIA — Estudiantes en Riesgo",
        description=(
            "Estudiantes con logro inferior a 0.40 (insuficiente). Filtrar "
            "manualmente por curso si se necesita un detalle más fino. El "
            "umbral está fijado por convención de la organización."
        ),
        config=table_config(
            metric_id=METRIC_DIA_EST,
            columns=[
                col_text("Nombre", "Estudiante", pinned=True),
                col_text("Curso", "Curso"),
                col_text("Establecimiento", "Establecimiento"),
                col_text("Hito", "Hito"),
                col_percent("Logro", "Logro"),
                col_text("Nivel Logro", "Nivel"),
            ],
            filters={},  # el filtro de logro<0.4 se aplica en frontend o vía
                         # un derived_field. Por ahora se muestran todos y se
                         # ordenan ascendente por logro para que el techo
                         # quede al inicio.
            sorting=[{"column": "Logro", "dir": "asc"}],
            page_size=50,
        ),
    )

    # 6. Brecha entre establecimientos por curso
    # Multi-columna grouping: una fila por (curso × establecimiento).
    ids["t_brecha"] = upsert_table(
        db, org_id,
        name="DIA — Brecha entre Establecimientos",
        description=(
            "Logro promedio por curso desglosado por establecimiento. Útil "
            "para identificar diferencias sistemáticas a nivel directivo. "
            "Solo aplica cuando hay >1 establecimiento."
        ),
        config=table_config(
            metric_id=METRIC_DIA_EST,
            columns=[
                col_text("Curso", "Curso", pinned=True),
                col_text("Establecimiento", "Establecimiento"),
                col_agg(
                    "Logro_mean", "Logro", "Logro Promedio",
                    agg="mean", fmt="percent", decimals=1,
                    color_scale=color_scale_diverging_logro(),
                ),
                col_agg("N", "Logro", "N°", agg="count", fmt="int", decimals=0),
            ],
            grouping={"by": ["Curso", "Establecimiento"]},
            sorting=[{"column": "Curso", "dir": "asc"}],
            search=False,
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # GRÁFICOS
    # ─────────────────────────────────────────────────────────────────────

    # 1. Logro Promedio por Curso (bar)
    ids["c_logro_curso"] = upsert_chart(
        db, org_id,
        name="DIA — Logro Promedio por Curso",
        description="Barra horizontal: promedio de logro por curso.",
        config=chart_config(
            "bar", METRIC_DIA_EST,
            titulo="Logro Promedio por Curso",
            x_field="Curso", y_field="Logro",
            y_format="percent", y_lims=[0, 1], y_label="Logro",
            show_values=True,
        ),
    )

    # 2. Logro Promedio por Nivel (bar agrupada por Curso)
    ids["c_logro_nivel"] = upsert_chart(
        db, org_id,
        name="DIA — Logro Promedio por Nivel",
        description=(
            "Barras agrupadas por nivel (Octavos, Primeros Medios, etc.). "
            "Cada nivel muestra los cursos que lo componen."
        ),
        config=chart_config(
            "grouped_bar", METRIC_DIA_EST,
            titulo="Logro Promedio por Nivel",
            x_field="Nivel", y_field="Logro", group_field="Curso",
            y_format="percent", y_lims=[0, 1], y_label="Logro",
            show_values=True,
        ),
    )

    # 3. Distribución (boxplot) por curso
    ids["c_box_curso"] = upsert_chart(
        db, org_id,
        name="DIA — Distribución de Logro por Curso",
        description=(
            "Boxplot: caja-bigote del logro de los estudiantes por curso. "
            "Permite ver dispersión y outliers."
        ),
        config=chart_config(
            "box", METRIC_DIA_EST,
            titulo="Distribución de Logro por Curso",
            x_field="Curso", y_field="Logro",
            y_format="percent", y_lims=[0, 1], y_label="Logro",
        ),
    )

    # 4. Cantidad de alumnos por Nivel de Logro (stacked) — pág. 6 del PDF
    # palette_reversed=true porque el stack_order va de "peor" a "mejor"
    # (Inicial → Avanzado) y la paleta semáforo va al revés (verde, amarillo,
    # rojo). Sin reverse, Inicial saldría verde y Avanzado rojo.
    ids["c_stack_niveles"] = upsert_chart(
        db, org_id,
        name="DIA — Cantidad de Alumnos por Nivel de Logro",
        description="Barras apiladas: distribución Inicial/Intermedio/Avanzado por curso.",
        config=chart_config(
            "stacked_bar", METRIC_DIA_EST,
            titulo="Cantidad de Alumnos por Nivel de Logro",
            x_field="Curso", stack_field="Nivel Logro",
            stack_order=["Inicial", "Intermedio", "Avanzado"],
            color_palette="semaforo", palette_reversed=True,
            show_values=True,
            y_label="N° Estudiantes",
            legend_title="Nivel",
        ),
    )

    # 5. Logro por Eje Temático
    ids["c_eje"] = upsert_chart(
        db, org_id,
        name="DIA — Logro por Eje Temático",
        description="% acierto promedio por eje temático y curso.",
        config=chart_config(
            "grouped_bar", METRIC_DIA_PREG,
            titulo="Logro Promedio por Eje Temático",
            x_field="Eje Temático", y_field="Logro", group_field="Curso",
            y_format="percent", y_lims=[0, 1], y_label="% Acierto",
            show_values=True,
        ),
    )

    # 6. Logro por Habilidad
    ids["c_habilidad"] = upsert_chart(
        db, org_id,
        name="DIA — Logro por Habilidad",
        description="% acierto promedio por habilidad y curso.",
        config=chart_config(
            "grouped_bar", METRIC_DIA_PREG,
            titulo="Logro Promedio por Habilidad",
            x_field="Habilidad", y_field="Logro", group_field="Curso",
            y_format="percent", y_lims=[0, 1], y_label="% Acierto",
            show_values=True,
        ),
    )

    # 7. Tendencia por Hito (line) — orden cronológico DIAG→INT→CIERRE
    ids["c_tendencia"] = upsert_chart(
        db, org_id,
        name="DIA — Tendencia de Logro por Hito",
        description=(
            "Línea: evolución del logro promedio entre Diagnóstico, "
            "Intermedio y Cierre, segmentado por curso."
        ),
        config=chart_config(
            "line", METRIC_DIA_EST,
            titulo="Tendencia de Logro por Hito",
            x_field="Hito", y_field="Logro", group_field="Curso",
            y_format="percent", y_lims=[0, 1], y_label="Logro",
            x_label="Hito",
            x_order=DIA_HITO_ORDER,
        ),
    )

    # 8. Heatmap Curso × Eje Temático (analítico nuevo)
    ids["c_heatmap_eje"] = upsert_chart(
        db, org_id,
        name="DIA — Heatmap Curso × Eje Temático",
        description=(
            "Mapa de calor del % de acierto por curso × eje. Permite "
            "identificar techos transversales (eje débil en todos los "
            "cursos) o brechas localizadas."
        ),
        config=chart_config(
            "heatmap", METRIC_DIA_PREG,
            titulo="Heatmap Curso × Eje Temático",
            x_field="Eje Temático", group_field="Curso", y_field="Logro",
            y_format="percent", color_palette="rojo_calor", palette_reversed=True,
        ),
    )

    # 9. Logro por Curso × Establecimiento (grouped) — comparativa directiva
    ids["c_estab_curso"] = upsert_chart(
        db, org_id,
        name="DIA — Logro por Curso × Establecimiento",
        description=(
            "Comparativa cross-establecimiento. Cada barra es un curso, "
            "agrupada por establecimiento."
        ),
        config=chart_config(
            "grouped_bar", METRIC_DIA_EST,
            titulo="Logro por Curso × Establecimiento",
            x_field="Curso", y_field="Logro", group_field="Establecimiento",
            y_format="percent", y_lims=[0, 1], y_label="Logro",
            show_values=True,
        ),
    )

    # 10. Tendencia por Establecimiento (line, agrupado por establecimiento)
    ids["c_estab_tendencia"] = upsert_chart(
        db, org_id,
        name="DIA — Tendencia por Establecimiento",
        description=(
            "Línea: avance del logro promedio del establecimiento entre "
            "los hitos. Sirve para comparativa cross-establecimiento de "
            "tendencias."
        ),
        config=chart_config(
            "line", METRIC_DIA_EST,
            titulo="Tendencia de Logro por Establecimiento",
            x_field="Hito", y_field="Logro", group_field="Establecimiento",
            y_format="percent", y_lims=[0, 1], y_label="Logro",
            x_order=DIA_HITO_ORDER,
        ),
    )

    # 11. Logro por Curso × Establecimiento — split por hito (DIAG / INT / CIERRE)
    # Se crean 3 charts (uno por hito) usando filters. Permite ver "cómo le fue
    # a cada establecimiento curso por curso EN ESE HITO".
    for hito_label in ("DIAGNOSTICO", "INTERMEDIO", "CIERRE"):
        key = f"c_estab_curso_{hito_label.lower()}"
        ids[key] = upsert_chart(
            db, org_id,
            name=f"DIA — Curso × Establecimiento ({hito_label.title()})",
            description=(
                f"Logro por curso × establecimiento, filtrado solo al hito "
                f"{hito_label}. Sirve para ver el snapshot del hito sin "
                f"que la suma de hitos distorsione el promedio."
            ),
            config=chart_config(
                "grouped_bar", METRIC_DIA_EST,
                titulo=f"Curso × Establecimiento — {hito_label.title()}",
                x_field="Curso", y_field="Logro", group_field="Establecimiento",
                filters={"Hito": hito_label},
                y_format="percent", y_lims=[0, 1], y_label="Logro",
                show_values=True,
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
                    cfg_chart_item(ids["c_logro_nivel"], "Logro por Nivel"),
                    cfg_chart_item(ids["c_logro_curso"], "Logro por Curso"),
                ], cols=2),
                row([
                    cfg_chart_item(ids["c_box_curso"], "Distribución por Curso"),
                ], cols=1),
                row([
                    cfg_chart_item(ids["c_stack_niveles"], "Niveles de Logro por Curso"),
                ], cols=1),
            ]),
            tab("curso", "Por Curso", [
                row([course_selector_item()], cols=1),
                row([
                    cfg_chart_item(ids["c_eje"], "Logro por Eje Temático"),
                    cfg_chart_item(ids["c_habilidad"], "Logro por Habilidad"),
                ], cols=2),
                row([cfg_chart_item(ids["c_heatmap_eje"], "Heatmap Curso × Eje")], cols=1),
                row([cfg_table_item(ids["t_logro_pregunta"], "Logro por Pregunta")], cols=1),
                row([cfg_table_item(ids["t_riesgo"], "Estudiantes en Riesgo")], cols=1),
            ]),
            tab("estudiante", "Por Estudiante", [
                row([course_selector_item()], cols=1),
                row([cfg_table_item(ids["t_logro_alumno"], "Logro por Alumno")], cols=1),
            ]),
            tab("tendencia", "Tendencia", [
                row([cfg_chart_item(ids["c_tendencia"], "Tendencia por Hito")], cols=1),
                row([cfg_table_item(ids["t_hitos"], "Comparativa entre Hitos")], cols=1),
            ]),
            tab("estab", "Comparativa Establecimientos", [
                row([
                    cfg_chart_item(ids["c_estab_curso"], "Logro por Curso × Establecimiento"),
                ], cols=1),
                row([
                    cfg_chart_item(ids["c_estab_curso_diagnostico"], "Diagnóstico — Curso × Establecimiento"),
                ], cols=1),
                row([
                    cfg_chart_item(ids["c_estab_curso_intermedio"], "Intermedio — Curso × Establecimiento"),
                ], cols=1),
                row([
                    cfg_chart_item(ids["c_estab_curso_cierre"], "Cierre — Curso × Establecimiento"),
                ], cols=1),
                row([
                    cfg_chart_item(ids["c_estab_tendencia"], "Tendencia por Establecimiento"),
                ], cols=1),
                row([
                    cfg_table_item(ids["t_brecha"], "Brecha entre Establecimientos"),
                ], cols=1),
            ]),
        ]
    }

    update_indicator_layout(db, org_id, "DIA", layout)
    return ids
