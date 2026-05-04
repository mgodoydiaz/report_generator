"""Script seed: inserta pipelines preconfigurados que usan RenderHtmlReport.

Crea (o actualiza) registros en la tabla `pipelines` de la BD para los 4
informes con paridad LaTeX ya soportados:

- SIMCE Lenguaje 2° Medio
- SIMCE Matemáticas 2° Medio
- DIA Diagnóstico Matemáticas Nivel Medio
- DIA Diagnóstico Lectura Nivel Medio

Cada pipeline asume que las métricas y dimensiones ya están cargadas en BD
(via los pipelines ETL existentes que poblaron `metric_data`). El pipeline
solo encadena: LoadMetricToDF (estudiantes + preguntas) → GenerateGraphics
→ GenerateTables → RenderHtmlReport.

Uso:
    conda activate rgenerator
    python scripts/seed_html_pipeline.py [--org-id 1] [--dry-run]

Si --dry-run, imprime el JSON de los pipelines pero no toca la BD.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))


# IDs de métricas en la BD (ajustar según seed real). Estos vienen del
# inventario Carril B ya cargado en Supabase.
METRIC_IDS = {
    "simce_lenguaje_estudiantes": 1,    # ajustar al ID real
    "simce_lenguaje_preguntas": 2,
    "simce_matematicas_estudiantes": 3,
    "simce_matematicas_preguntas": 4,
    "dia_estudiantes": 6,
    "dia_preguntas": 7,
}


def build_pipeline_simce(asignatura: str, schema_filename: str) -> dict:
    """Pipeline SIMCE genérico (Lenguaje o Matemáticas)."""
    suffix = "lenguaje" if "Lenguaje" in asignatura else "matematicas"
    estudiantes_id = METRIC_IDS.get(f"simce_{suffix}_estudiantes")
    preguntas_id = METRIC_IDS.get(f"simce_{suffix}_preguntas")

    return {
        "workflow_metadata": {
            "name": f"Informe SIMCE {asignatura} - HTML",
            "description": f"Genera informe PDF para SIMCE {asignatura} 2° Medio "
                           "con motor RenderHtmlReport (paridad visual LaTeX vía WeasyPrint).",
            "evaluation": f"simce_{suffix}",
            "engine": "html",
        },
        "context": {
            "asignatura": asignatura.upper(),
            "numero_prueba": 5,
        },
        "pipeline": [
            {"step": "InitRun", "params": {}},
            {
                "step": "LoadMetricToDF",
                "params": {
                    "metric_id": estudiantes_id,
                    "output_key": "df_estudiantes",
                    "filters": {"Asignatura": asignatura.upper()},
                },
            },
            {
                "step": "LoadMetricToDF",
                "params": {
                    "metric_id": preguntas_id,
                    "output_key": "df_preguntas",
                    "filters": {"Asignatura": asignatura.upper()},
                },
            },
            {
                "step": "GenerateGraphics",
                "params": {
                    # Las definiciones de gráficos vienen del schema JSON
                    # complementario charts_simce_<asignatura>.json (en
                    # data/database/reports_templates/). El step las lee.
                    "charts_schema_path": f"data/database/reports_templates/charts_simce_{suffix}.json",
                },
            },
            {
                "step": "GenerateTables",
                "params": {
                    "tables_schema_path": f"data/database/reports_templates/tables_simce_{suffix}.json",
                },
            },
            {
                "step": "RenderHtmlReport",
                "params": {
                    "report_schema_path": f"backend/schemas/{schema_filename}",
                    "output_filename": f"informe_simce_{suffix}.pdf",
                },
            },
        ],
    }


def build_pipeline_dia(area: str, schema_filename: str) -> dict:
    """Pipeline DIA Diagnóstico (Matemáticas o Lectura) Nivel Medio."""
    suffix = "matematicas" if "Matem" in area else "lectura"
    return {
        "workflow_metadata": {
            "name": f"Informe DIA Diagnóstico {area} Nivel Medio - HTML",
            "description": f"Genera informe PDF para DIA Diagnóstico {area} Nivel Medio "
                           "con motor RenderHtmlReport.",
            "evaluation": f"dia_{suffix}",
            "engine": "html",
        },
        "context": {
            "area": area.upper(),
        },
        "pipeline": [
            {"step": "InitRun", "params": {}},
            {
                "step": "LoadMetricToDF",
                "params": {
                    "metric_id": METRIC_IDS["dia_estudiantes"],
                    "output_key": "df_estudiantes",
                    "filters": {"Asignatura": area.upper()},
                },
            },
            {
                "step": "LoadMetricToDF",
                "params": {
                    "metric_id": METRIC_IDS["dia_preguntas"],
                    "output_key": "df_preguntas",
                    "filters": {"Asignatura": area.upper()},
                },
            },
            {
                "step": "GenerateGraphics",
                "params": {
                    "charts_schema_path": f"data/database/reports_templates/charts_dia_{suffix}.json",
                },
            },
            {
                "step": "GenerateTables",
                "params": {
                    "tables_schema_path": f"data/database/reports_templates/tables_dia_{suffix}.json",
                },
            },
            {
                "step": "RenderHtmlReport",
                "params": {
                    "report_schema_path": f"backend/schemas/{schema_filename}",
                    "output_filename": f"informe_dia_{suffix}.pdf",
                },
            },
        ],
    }


PIPELINES = [
    ("simce_lenguaje_html", build_pipeline_simce("Lenguaje", "esquema_informe_lenguaje.json")),
    ("simce_matematicas_html", build_pipeline_simce("Matemáticas", "esquema_informe.json")),
    ("dia_matematicas_html", build_pipeline_dia("Matemáticas", "esquema_informe_dia_matematicas.json")),
    ("dia_lectura_html", build_pipeline_dia("Lectura", "esquema_informe_dia_lectura.json")),
]


def upsert_pipeline(db, org_id: int, name: str, config: dict) -> None:
    """Inserta o actualiza un pipeline por (org_id, name)."""
    from backend.models import Pipeline  # import lazy

    existing = db.query(Pipeline).filter(
        Pipeline.org_id == org_id,
        Pipeline.name == name,
    ).first()

    if existing:
        existing.config_json = json.dumps(config, ensure_ascii=False)
        print(f"  ↻ actualizado: {name} (id={existing.id_pipeline})")
    else:
        new_pipeline = Pipeline(
            org_id=org_id,
            name=name,
            config_json=json.dumps(config, ensure_ascii=False),
        )
        db.add(new_pipeline)
        db.flush()
        print(f"  ✚ creado: {name} (id={new_pipeline.id_pipeline})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org-id", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true",
                        help="Imprime los pipelines sin tocar la BD")
    args = parser.parse_args()

    if args.dry_run:
        print("=== DRY RUN: no se modifica la BD ===\n")
        for name, config in PIPELINES:
            print(f"\n## Pipeline: {name}")
            print(json.dumps(config, indent=2, ensure_ascii=False))
        return

    from backend.database import SessionLocal
    print(f"Insertando {len(PIPELINES)} pipelines en org_id={args.org_id}...")
    db = SessionLocal()
    try:
        for name, config in PIPELINES:
            upsert_pipeline(db, args.org_id, name, config)
        db.commit()
        print(f"\n✅ {len(PIPELINES)} pipelines guardados.")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Rollback por error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
