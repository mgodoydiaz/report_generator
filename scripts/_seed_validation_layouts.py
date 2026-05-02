"""Seed: pobla pdf_layout y pdf_layout_historico para los 5 indicators
(SIMCE, DIA, IDEL, Cálculo Veloz, Fluidez Lectora) en la BD local.

Construye layouts canónicos usando roles (_logro_1, _logro_2, _nivel_de_logro,
_habilidad, _evaluacion_num) que el _resolve_field traduce a las columnas
reales de cada métrica según indicator.column_roles.

Uso:
    DATABASE_URL='postgresql://mgodoy:holapocompadre977@localhost:5432/rgenerator_dev' \
        python scripts/_seed_validation_layouts.py

Idempotente: re-ejecutar sobreescribe los layouts.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# Default DATABASE_URL si no está en env
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://mgodoy:holapocompadre977@localhost:5432/rgenerator_dev",
)

from backend.database import SessionLocal  # noqa: E402
from backend.models import Indicator  # noqa: E402


# ─────────────────────── Branding compartido ────────────────────────────


BRANDING_PHP = {
    "left_image_id": None,
    "right_image_id": None,
    "center_header": ["Fundación PHP"],  # con tilde
    "left_footer": "Miguel Godoy Díaz",
    "show_page_number": True,
}


# ─────────────────────── Layouts por indicator ──────────────────────────


def simce_evaluacion() -> dict:
    return {
        "engine": "weasyprint",
        "mode": "evaluacion",
        "branding": BRANDING_PHP,
        "sections": [
            {"type": "cover", "title": "Informe SIMCE — Por evaluación",
             "subtitle": "Resumen de la prueba seleccionada"},
            {"type": "table", "heading": "Cuadro Resumen Logro por Curso",
             "item": {"component": "SummaryTable",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "comparePrevious": True}},
            {"type": "chart", "heading": "Logro Promedio por Curso",
             "item": {"component": "BarByGroup",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "showValues": True}},
            {"type": "chart", "heading": "Cantidad de Alumnos por Nivel de Logro",
             "item": {"component": "StackedCountByGroup",
                      "groupField": "_curso",
                      "levelField": "_nivel_de_logro"}},
            # SIMCE Habilidades: _habilidad solo está en metric 5 (preguntas).
            # Usamos _logro directo (que en metric 5 es % de aciertos por
            # pregunta) en vez de _logro_1 (que se resuelve a _rend, solo
            # presente en metric 4 = estudiantes).
            {"type": "chart", "heading": "Logro Promedio por Habilidad",
             "item": {"component": "BarByGroup",
                      "valueField": "_logro", "groupField": "_habilidad"}},
        ],
    }


def simce_historico() -> dict:
    return {
        "engine": "weasyprint",
        "mode": "historico",
        "branding": BRANDING_PHP,
        "sections": [
            {"type": "cover", "title": "Informe SIMCE — Histórico",
             "subtitle": "Evolución del rendimiento entre evaluaciones"},
            {"type": "chart", "heading": "Evolución del Logro Promedio por Curso y Mes",
             "item": {"component": "GroupedBarByPeriod",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "periodField": "_mes"}},
            {"type": "chart", "heading": "Evolución del Puntaje SIMCE por Curso y Mes",
             "item": {"component": "GroupedBarByPeriod",
                      "valueField": "_logro_2", "groupField": "_curso",
                      "periodField": "_mes"}},
            {"type": "chart", "heading": "Evolución de Alumnos por Nivel de Logro",
             "item": {"component": "StackedCountByGroup",
                      "groupField": "_mes",
                      "levelField": "_nivel_de_logro"}},
        ],
    }


def dia_evaluacion() -> dict:
    return {
        "engine": "weasyprint",
        "mode": "evaluacion",
        "branding": BRANDING_PHP,
        "sections": [
            {"type": "cover", "title": "Informe DIA — Por evaluación",
             "subtitle": "Resumen del hito seleccionado"},
            {"type": "table", "heading": "Cuadro Resumen Logro por Curso",
             "item": {"component": "SummaryTable",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "comparePrevious": True, "periodField": "_hito"}},
            {"type": "chart", "heading": "Logro Promedio por Curso",
             "item": {"component": "BarByGroup",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "showValues": True}},
            {"type": "chart", "heading": "Cantidad de Alumnos por Nivel de Logro",
             "item": {"component": "StackedCountByGroup",
                      "groupField": "_curso",
                      "levelField": "_nivel_de_logro"}},
            {"type": "chart", "heading": "Logro Promedio por Eje Temático",
             "item": {"component": "BarByGroup",
                      "valueField": "_logro_1", "groupField": "_eje_tematico"}},
            {"type": "chart", "heading": "Logro Promedio por Habilidad",
             "item": {"component": "BarByGroup",
                      "valueField": "_logro_1", "groupField": "_habilidad"}},
        ],
    }


def dia_historico() -> dict:
    return {
        "engine": "weasyprint",
        "mode": "historico",
        "branding": BRANDING_PHP,
        "sections": [
            {"type": "cover", "title": "Informe DIA — Histórico",
             "subtitle": "Evolución entre hitos del año"},
            {"type": "chart", "heading": "Evolución del Logro Promedio por Curso y Hito",
             "item": {"component": "GroupedBarByPeriod",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "periodField": "_hito"}},
            {"type": "chart", "heading": "Evolución de Alumnos por Nivel de Logro",
             "item": {"component": "StackedCountByGroup",
                      "groupField": "_hito",
                      "levelField": "_nivel_de_logro"}},
        ],
    }


def idel_evaluacion() -> dict:
    return {
        "engine": "weasyprint",
        "mode": "evaluacion",
        "branding": BRANDING_PHP,
        "sections": [
            {"type": "cover", "title": "Informe IDEL — Por evaluación",
             "subtitle": "Resultados de la versión seleccionada"},
            {"type": "table", "heading": "Cuadro Resumen Puntaje por Curso",
             "item": {"component": "SummaryTable",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "comparePrevious": True, "periodField": "_version"}},
            {"type": "chart", "heading": "Puntaje Promedio por Curso",
             "item": {"component": "BarByGroup",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "showValues": True}},
            {"type": "chart", "heading": "Distribución de Nivel de Riesgo por Curso",
             "item": {"component": "StackedCountByGroup",
                      "groupField": "_curso",
                      "levelField": "_nivel_de_logro"}},
            {"type": "chart", "heading": "Puntaje Promedio por Evaluación",
             "item": {"component": "BarByGroup",
                      "valueField": "_logro_1", "groupField": "_habilidad"}},
        ],
    }


def idel_historico() -> dict:
    return {
        "engine": "weasyprint",
        "mode": "historico",
        "branding": BRANDING_PHP,
        "sections": [
            {"type": "cover", "title": "Informe IDEL — Histórico",
             "subtitle": "Evolución entre versiones de la prueba"},
            {"type": "chart", "heading": "Evolución del Puntaje Promedio por Curso y Versión",
             "item": {"component": "GroupedBarByPeriod",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "periodField": "_version"}},
            {"type": "chart", "heading": "Evolución de Alumnos por Nivel de Riesgo",
             "item": {"component": "StackedCountByGroup",
                      "groupField": "_version",
                      "levelField": "_nivel_de_logro"}},
        ],
    }


def cv_evaluacion() -> dict:
    return {
        "engine": "weasyprint",
        "mode": "evaluacion",
        "branding": BRANDING_PHP,
        "sections": [
            {"type": "cover", "title": "Informe Cálculo Veloz — Por evaluación",
             "subtitle": "Resultados de la prueba seleccionada"},
            {"type": "table", "heading": "Cuadro Resumen por Curso",
             "item": {"component": "SummaryTable",
                      "valueField": ["_logro_2", "_logro_1"],
                      "groupField": "_curso",
                      "comparePrevious": True, "periodField": "_fecha"}},
            {"type": "chart", "heading": "Puntaje y Nota Promedio por Curso",
             "item": {"component": "BarByGroup",
                      "valueField": ["_logro_2", "_logro_1"],
                      "groupField": "_curso",
                      "showLegend": True, "showValues": True}},
            {"type": "chart", "heading": "Distribución de Nivel por Curso",
             "item": {"component": "StackedCountByGroup",
                      "groupField": "_curso",
                      "levelField": "_nivel_de_logro"}},
            {"type": "chart", "heading": "Histograma de Puntajes",
             "item": {"component": "Histogram",
                      "valueField": "_logro_2", "nbins": 15}},
        ],
    }


def cv_historico() -> dict:
    return {
        "engine": "weasyprint",
        "mode": "historico",
        "branding": BRANDING_PHP,
        "sections": [
            {"type": "cover", "title": "Informe Cálculo Veloz — Histórico",
             "subtitle": "Evolución de Puntaje y Nota entre pruebas"},
            {"type": "chart", "heading": "Evolución del Puntaje Promedio por Curso y Mes",
             "item": {"component": "GroupedBarByPeriod",
                      "valueField": "_logro_2", "groupField": "_curso",
                      "periodField": "_mes"}},
            {"type": "chart", "heading": "Evolución de la Nota Promedio por Curso y Mes",
             "item": {"component": "GroupedBarByPeriod",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "periodField": "_mes"}},
            {"type": "chart", "heading": "Distribución de Nivel a través del Año",
             "item": {"component": "StackedCountByGroup",
                      "groupField": "_mes",
                      "levelField": "_nivel_de_logro"}},
        ],
    }


def fl_evaluacion() -> dict:
    return {
        "engine": "weasyprint",
        "mode": "evaluacion",
        "branding": BRANDING_PHP,
        "sections": [
            {"type": "cover", "title": "Informe Fluidez Lectora — Por evaluación",
             "subtitle": "Resultados de la medición seleccionada"},
            {"type": "table", "heading": "Cuadro Resumen PPM por Curso",
             "item": {"component": "SummaryTable",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "comparePrevious": True, "periodField": "_evaluacion"}},
            {"type": "chart", "heading": "PPM Promedio por Curso",
             "item": {"component": "BarByGroup",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "showValues": True}},
            {"type": "chart", "heading": "Distribución de Categoría por Curso",
             "item": {"component": "DistribucionNiveles",
                      "groupField": "_curso",
                      "levelField": "_nivel_de_logro"}},
            {"type": "chart", "heading": "Distribución de Calidad Lectora por Curso",
             "item": {"component": "StackedCountByGroup",
                      "groupField": "_curso",
                      "levelField": "_calidad_lectora"}},
            {"type": "chart", "heading": "Histograma de PPM",
             "item": {"component": "Histogram",
                      "valueField": "_logro_1", "nbins": 20}},
        ],
    }


def fl_historico() -> dict:
    return {
        "engine": "weasyprint",
        "mode": "historico",
        "branding": BRANDING_PHP,
        "sections": [
            {"type": "cover", "title": "Informe Fluidez Lectora — Histórico",
             "subtitle": "Evolución de fluidez entre evaluaciones"},
            {"type": "chart", "heading": "Evolución PPM Promedio por Curso y Evaluación",
             "item": {"component": "GroupedBarByPeriod",
                      "valueField": "_logro_1", "groupField": "_curso",
                      "periodField": "_evaluacion"}},
            {"type": "chart", "heading": "Evolución de Categoría por Evaluación",
             "item": {"component": "StackedCountByGroup",
                      "groupField": "_evaluacion",
                      "levelField": "_nivel_de_logro"}},
        ],
    }


# ─────────────────────── Mapping y aplicación ────────────────────────────


LAYOUTS_BY_INDICATOR = {
    1: ("SIMCE", simce_evaluacion(), simce_historico()),
    2: ("DIA", dia_evaluacion(), dia_historico()),
    3: ("IDEL", idel_evaluacion(), idel_historico()),
    4: ("Cálculo Veloz", cv_evaluacion(), cv_historico()),
    5: ("Fluidez Lectora", fl_evaluacion(), fl_historico()),
}


def main():
    db = SessionLocal()
    try:
        for ind_id, (name, eval_layout, hist_layout) in LAYOUTS_BY_INDICATOR.items():
            ind = db.query(Indicator).filter(Indicator.id_indicator == ind_id).first()
            if not ind:
                print(f"  ⚠ indicator {ind_id} ({name}) no existe — skip")
                continue
            ind.pdf_layout = json.dumps(eval_layout, ensure_ascii=False)
            ind.pdf_layout_historico = json.dumps(hist_layout, ensure_ascii=False)
            print(f"  ✓ {ind_id} {name}: layouts evaluación ({len(eval_layout['sections'])} secs) + "
                  f"histórico ({len(hist_layout['sections'])} secs)")
        db.commit()
        print("\n✅ Layouts seedeados.")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Rollback: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
