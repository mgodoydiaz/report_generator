"""
apply_pdl_layout_v2.py — Aplica el layout v2 al indicador id=3 (PDL/IDEL-Woodcock).

Uso:
    python scripts/apply_pdl_layout_v2.py [--dry-run]

El --dry-run imprime el JSON sin tocar la DB.
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine, text as sa_text

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL no configurado.")
    sys.exit(1)

INDICATOR_ID = 3

LAYOUT_V2 = {
    "tabs": [
        {
            "id": "panorama",
            "label": "Panorama",
            "rows": [
                {
                    "cols": 4,
                    "items": [
                        {"type": "TrendKPI", "label": "Total estudiantes",    "valueField": "_rut",           "aggregation": "unique_count",  "filter": {"_evaluacion_num": "latest"}},
                        {"type": "TrendKPI", "label": "% Crítico+Alto",       "valueField": "_is_concerning", "aggregation": "mean_percent",  "invertColors": True, "filter": {"_evaluacion_num": "latest"}},
                        {"type": "TrendKPI", "label": "Curso más crítico",    "aggregation": "top_group",     "groupField": "_curso",         "scoreField": "_is_concerning", "filter": {"_evaluacion_num": "latest"}},
                        {"type": "TrendKPI", "label": "Subprueba más crítica","aggregation": "top_group",     "groupField": "_habilidad",     "scoreField": "_is_concerning", "filter": {"_evaluacion_num": "latest"}},
                    ],
                },
                {
                    "cols": 1,
                    "items": [
                        {"type": "StackedCountByGroup", "title": "Niveles por curso (última evaluación)", "groupField": "_curso", "levelField": "_worst_level_label", "filter": {"_evaluacion_num": "latest"}},
                    ],
                },
                {
                    "cols": 2,
                    "items": [
                        {"type": "HeatmapMatrix", "title": "N Crítico+Alto por curso × subprueba", "xField": "_habilidad", "yField": "_curso", "valueField": "_is_concerning", "agg": "count_true",   "filter": {"_evaluacion_num": "latest"}},
                        {"type": "HeatmapMatrix", "title": "% Crítico+Alto por curso × subprueba", "xField": "_habilidad", "yField": "_curso", "valueField": "_is_concerning", "agg": "mean_percent", "filter": {"_evaluacion_num": "latest"}},
                    ],
                },
            ],
        },
        {
            "id": "por-curso",
            "label": "Por Curso",
            "rows": [
                {
                    "cols": 1,
                    "items": [{"type": "course_selector"}],
                },
                {
                    "cols": 3,
                    "items": [
                        {"type": "TrendKPI", "label": "CT",  "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": True, "dataSource": "cursoEstudiantes", "filter": {"_habilidad": "CT"}},
                        {"type": "TrendKPI", "label": "FLO", "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": True, "dataSource": "cursoEstudiantes", "filter": {"_habilidad": "FLO"}},
                        {"type": "TrendKPI", "label": "FNL", "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": True, "dataSource": "cursoEstudiantes", "filter": {"_habilidad": "FNL"}},
                    ],
                },
                {
                    "cols": 3,
                    "items": [
                        {"type": "TrendKPI", "label": "FSF", "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": True, "dataSource": "cursoEstudiantes", "filter": {"_habilidad": "FSF"}},
                        {"type": "TrendKPI", "label": "ILP", "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": True, "dataSource": "cursoEstudiantes", "filter": {"_habilidad": "ILP"}},
                        {"type": "TrendKPI", "label": "VSD", "valueField": "_is_concerning", "aggregation": "mean_percent", "invertColors": True, "dataSource": "cursoEstudiantes", "filter": {"_habilidad": "VSD"}},
                    ],
                },
                {
                    "cols": 1,
                    "items": [
                        {"type": "StackedCountByGroup", "title": "Niveles por subprueba (curso activo)", "groupField": "_habilidad", "levelField": "_logro", "dataSource": "cursoEstudiantes"},
                    ],
                },
                {
                    "cols": 2,
                    "items": [
                        {"type": "StudentRiskList", "dataSource": "cursoEstudiantes", "topN": 10},
                        {"type": "PivotTable", "dataSource": "cursoEstudiantes", "pivotConfig": {"rows": ["_nombre"], "cols": ["_habilidad"], "value": "_logro"}, "semaphoreField": "_logro"},
                    ],
                },
            ],
        },
        {
            "id": "por-subprueba",
            "label": "Por Subprueba",
            "rows": [
                {"cols": 1, "items": [{"type": "subprueba_selector"}]},
                {
                    "cols": 2,
                    "items": [
                        {"type": "BarByGroup",   "title": "Logro promedio por curso (subprueba activa)", "groupField": "_curso", "valueField": "_rend"},
                        {"type": "BoxPlotByGroup","title": "Distribución por curso",                      "groupField": "_curso", "valueField": "_rend"},
                    ],
                },
                {
                    "cols": 1,
                    "items": [
                        {"type": "StackedCountByGroup", "title": "Niveles por curso (subprueba activa)", "groupField": "_curso", "levelField": "_logro"},
                    ],
                },
                {
                    "cols": 1,
                    "items": [
                        {"type": "TrendLine", "title": "Tendencia por curso (subprueba activa)", "groupField": "_curso", "periodField": "_evaluacion_num", "valueField": "_rend"},
                    ],
                },
            ],
        },
        {
            "id": "sintesis",
            "label": "Síntesis",
            "rows": [
                {
                    "cols": 2,
                    "items": [
                        {"type": "ImprovementRateByGroup", "title": "Trayectoria por curso",     "groupField": "_curso",    "entityField": "_rut", "levelField": "_worst_level_label", "timeField": "_evaluacion_num"},
                        {"type": "ImprovementRateByGroup", "title": "Trayectoria por subprueba", "groupField": "_habilidad","entityField": "_rut", "levelField": "_logro",             "timeField": "_evaluacion_num"},
                    ],
                },
                {
                    "cols": 1,
                    "items": [
                        {"type": "TransitionMatrix", "timeField": "_evaluacion_num", "entityField": "_rut", "levelField": "_worst_level_label"},
                    ],
                },
                {
                    "cols": 2,
                    "items": [
                        {"type": "PivotTable", "title": "Niveles por estudiante × subprueba", "pivotConfig": {"rows": ["_curso", "_nombre"], "cols": ["_habilidad"], "value": "_worst_level_label"}, "semaphoreField": "_worst_level_label"},
                    ],
                },
            ],
        },
    ]
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Imprime el JSON sin escribir en la DB")
    args = parser.parse_args()

    print(f"\n=== Layout v2 PDL — indicador id={INDICATOR_ID} ===\n")

    if args.dry_run:
        print(json.dumps(LAYOUT_V2, indent=2, ensure_ascii=False))
        print("\n[DRY-RUN] Nada fue modificado.")
        return

    engine = create_engine(DATABASE_URL)
    layout_json = json.dumps(LAYOUT_V2, ensure_ascii=False)

    with engine.connect() as conn:
        # Leer layout actual
        row = conn.execute(
            sa_text("SELECT name, dashboard_layout FROM indicators WHERE id_indicator = :id"),
            {"id": INDICATOR_ID}
        ).fetchone()

        if not row:
            print(f"ERROR: Indicador id={INDICATOR_ID} no encontrado.")
            sys.exit(1)

        name, old_layout_raw = row
        old_tabs = (json.loads(old_layout_raw) if isinstance(old_layout_raw, str) else (old_layout_raw or {})).get("tabs", [])

        # Aplicar nuevo layout
        conn.execute(
            sa_text("UPDATE indicators SET dashboard_layout = :layout WHERE id_indicator = :id"),
            {"layout": layout_json, "id": INDICATOR_ID}
        )
        conn.commit()

        print(f"Indicador: [{INDICATOR_ID}] {name}")
        print(f"Layout anterior tabs: {len(old_tabs)}")
        print(f"Layout nuevo     tabs: {len(LAYOUT_V2['tabs'])}")
        print("\nOK Layout v2 aplicado correctamente.\n")


if __name__ == "__main__":
    main()
