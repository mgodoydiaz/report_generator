"""Seed inicial del catálogo de gráficos (B8).

Clones de los charts hardcoded en simce/esquema.json y dia/esquema.json
del motor PDF v2, ahora editables desde /charts.

Idempotente. Ejecutar:
    python /app/scripts/seed_chart_catalog.py
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, "/app")

from backend.database import SessionLocal
from backend.models import Spec, User


SPEC_TYPE = "Gráficos"


# ─────────────────────────────────────────────────────────────────────────
# Definiciones (clones de los esquemas SIMCE/DIA)
# ─────────────────────────────────────────────────────────────────────────


# SIMCE (metric 4 estudiantes, 5 preguntas)
SIMCE_RENDIMIENTO_BARRAS = {
    "name": "SIMCE — Rendimiento Promedio por Curso",
    "description": "Barras del Logro promedio (Rend) por Curso. Equivalente a `grafico_barras_promedio_por` del esquema SIMCE.",
    "config": {
        "version": 1,
        "chart_type": "bar",
        "data_source": {"metric_id": 4, "filters": {}},
        "mapping": {"x_field": "Curso", "y_field": "Rend", "aggregation": "mean"},
        "aesthetics": {
            "titulo": "Rendimiento Promedio por Curso",
            "y_label": "Rendimiento",
            "y_format": "percent",
            "y_lims": [0, 1],
        },
    },
}

SIMCE_BOXPLOT = {
    "name": "SIMCE — Distribución SIMCE por Curso",
    "description": "Boxplot del puntaje SIMCE por Curso. Equivalente a `boxplot_valor_por_curso`.",
    "config": {
        "version": 1,
        "chart_type": "box",
        "data_source": {"metric_id": 4, "filters": {}},
        "mapping": {"x_field": "Curso", "y_field": "SIMCE"},
        "aesthetics": {
            "titulo": "Distribución de Puntaje SIMCE por Curso",
            "y_label": "Puntaje SIMCE",
            "y_format": "int",
        },
    },
}

SIMCE_NIVELES_STACK = {
    "name": "SIMCE — Cantidad de Alumnos por Nivel",
    "description": "Stacked bars con paleta semáforo: count por (Curso × Logro). Equivalente a `alumnos_por_nivel_cualitativo`.",
    "config": {
        "version": 1,
        "chart_type": "stacked_bar",
        "data_source": {"metric_id": 4, "filters": {}},
        "mapping": {"x_field": "Curso", "stack_field": "Logro"},
        "aesthetics": {
            "titulo": "Cantidad de Alumnos por Nivel y Curso",
            "y_label": "Cantidad",
            "color_palette": "semaforo",
            "stack_order": ["Adecuado", "Elemental", "Insuficiente"],
            "legend_title": "Nivel de Logro",
        },
    },
}

SIMCE_HABILIDAD = {
    "name": "SIMCE — Logro por Habilidad",
    "description": "Barras agrupadas: Logro promedio por Curso × Habilidad. Equivalente a `valor_promedio_agrupado_por`.",
    "config": {
        "version": 1,
        "chart_type": "grouped_bar",
        "data_source": {"metric_id": 5, "filters": {}},
        "mapping": {
            "x_field": "Curso",
            "y_field": "Logro",
            "group_field": "Habilidad",
            "aggregation": "mean",
        },
        "aesthetics": {
            "titulo": "Logro Promedio por Habilidad",
            "y_label": "Logro",
            "y_format": "percent",
            "legend_title": "Habilidad",
        },
    },
}

SIMCE_EJE_TEMATICO = {
    "name": "SIMCE — Logro por Eje Temático",
    "description": "Barras agrupadas: Logro promedio por Curso × Eje Temático.",
    "config": {
        "version": 1,
        "chart_type": "grouped_bar",
        "data_source": {"metric_id": 5, "filters": {}},
        "mapping": {
            "x_field": "Curso",
            "y_field": "Logro",
            "group_field": "Eje Temático",
            "aggregation": "mean",
        },
        "aesthetics": {
            "titulo": "Logro Promedio por Eje Temático",
            "y_label": "Logro",
            "y_format": "percent",
            "legend_title": "Eje Temático",
        },
    },
}

SIMCE_EVOLUCION = {
    "name": "SIMCE — Evolución Logro por Mes",
    "description": "Línea por curso a través de los meses (Abril/Junio/Agosto/Octubre). Útil para tracking longitudinal.",
    "config": {
        "version": 1,
        "chart_type": "line",
        "data_source": {"metric_id": 4, "filters": {}},
        "mapping": {
            "x_field": "Mes",
            "y_field": "Rend",
            "group_field": "Curso",
            "aggregation": "mean",
        },
        "aesthetics": {
            "titulo": "Evolución del Logro Promedio por Curso y Mes",
            "y_label": "Logro",
            "y_format": "percent",
            "legend_title": "Curso",
            "y_lims": [0, 1],
        },
    },
}


# DIA (metric 6 estudiantes, 7 preguntas)
DIA_LOGRO_BARRAS = {
    "name": "DIA — Logro Promedio por Curso",
    "description": "Barras del Logro promedio por Curso DIA.",
    "config": {
        "version": 1,
        "chart_type": "bar",
        "data_source": {"metric_id": 6, "filters": {}},
        "mapping": {"x_field": "Curso", "y_field": "Logro", "aggregation": "mean"},
        "aesthetics": {
            "titulo": "Logro Promedio por Curso",
            "y_label": "Logro",
            "y_format": "percent",
            "y_lims": [0, 1],
        },
    },
}

DIA_LOGRO_NIVEL = {
    "name": "DIA — Logro Promedio por Nivel",
    "description": "Barras por Nivel (Primeros, Segundos, ... Cuartos Medios).",
    "config": {
        "version": 1,
        "chart_type": "bar",
        "data_source": {"metric_id": 6, "filters": {}},
        "mapping": {"x_field": "Nivel", "y_field": "Logro", "aggregation": "mean"},
        "aesthetics": {
            "titulo": "Logro Promedio por Nivel",
            "y_label": "Logro",
            "y_format": "percent",
            "y_lims": [0, 1],
        },
    },
}

DIA_BOXPLOT = {
    "name": "DIA — Distribución de Logro por Curso",
    "description": "Boxplot del Logro por Curso DIA.",
    "config": {
        "version": 1,
        "chart_type": "box",
        "data_source": {"metric_id": 6, "filters": {}},
        "mapping": {"x_field": "Curso", "y_field": "Logro"},
        "aesthetics": {
            "titulo": "Distribución de Logro por Curso",
            "y_label": "Logro",
            "y_format": "percent",
            "y_lims": [0, 1],
        },
    },
}

DIA_NIVELES_STACK = {
    "name": "DIA — Cantidad de Alumnos por Nivel de Logro",
    "description": "Stacked bars con paleta semáforo: count por (Curso × Nivel Logro).",
    "config": {
        "version": 1,
        "chart_type": "stacked_bar",
        "data_source": {"metric_id": 6, "filters": {}},
        "mapping": {"x_field": "Curso", "stack_field": "Nivel Logro"},
        "aesthetics": {
            "titulo": "Cantidad de Alumnos por Nivel de Logro y Curso",
            "y_label": "Cantidad",
            "color_palette": "semaforo",
            "stack_order": ["Avanzado", "Intermedio", "Inicial"],
            "legend_title": "Nivel de Logro",
        },
    },
}

DIA_EJE_TEMATICO = {
    "name": "DIA — Logro por Eje Temático",
    "description": "Barras agrupadas: Logro promedio por Curso × Eje Temático.",
    "config": {
        "version": 1,
        "chart_type": "grouped_bar",
        "data_source": {"metric_id": 7, "filters": {}},
        "mapping": {
            "x_field": "Curso",
            "y_field": "Logro",
            "group_field": "Eje Temático",
            "aggregation": "mean",
        },
        "aesthetics": {
            "titulo": "Logro Promedio por Eje Temático",
            "y_label": "Logro",
            "y_format": "percent",
            "legend_title": "Eje Temático",
            "y_lims": [0, 1],
        },
    },
}

DIA_HABILIDAD = {
    "name": "DIA — Logro por Habilidad",
    "description": "Barras agrupadas: Logro promedio por Curso × Habilidad.",
    "config": {
        "version": 1,
        "chart_type": "grouped_bar",
        "data_source": {"metric_id": 7, "filters": {}},
        "mapping": {
            "x_field": "Curso",
            "y_field": "Logro",
            "group_field": "Habilidad",
            "aggregation": "mean",
        },
        "aesthetics": {
            "titulo": "Logro Promedio por Habilidad",
            "y_label": "Logro",
            "y_format": "percent",
            "legend_title": "Habilidad",
            "y_lims": [0, 1],
        },
    },
}

DIA_GAUGE_LOGRO = {
    "name": "DIA — Logro Global (Gauge)",
    "description": "KPI medidor: Logro promedio global del establecimiento.",
    "config": {
        "version": 1,
        "chart_type": "gauge",
        "data_source": {"metric_id": 6, "filters": {}},
        "mapping": {"y_field": "Logro", "aggregation": "mean"},
        "aesthetics": {
            "titulo": "Logro Global",
            "y_format": "percent",
            "min_value": 0,
            "max_value": 1,
            "thresholds": [
                {"value": 0.4, "color": "#fee2e2"},
                {"value": 0.6, "color": "#fef3c7"},
                {"value": 1.0, "color": "#dcfce7"},
            ],
        },
    },
}


ALL_CHARTS = [
    SIMCE_RENDIMIENTO_BARRAS,
    SIMCE_BOXPLOT,
    SIMCE_NIVELES_STACK,
    SIMCE_HABILIDAD,
    SIMCE_EJE_TEMATICO,
    SIMCE_EVOLUCION,
    DIA_LOGRO_BARRAS,
    DIA_LOGRO_NIVEL,
    DIA_BOXPLOT,
    DIA_NIVELES_STACK,
    DIA_EJE_TEMATICO,
    DIA_HABILIDAD,
    DIA_GAUGE_LOGRO,
]


# ─────────────────────────────────────────────────────────────────────────
# Seed
# ─────────────────────────────────────────────────────────────────────────


def now_str() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def seed(org_id: int) -> None:
    db = SessionLocal()
    try:
        existing_names = {
            s.name for s in db.query(Spec).filter(
                Spec.org_id == org_id, Spec.type == SPEC_TYPE
            ).all()
        }
        created = 0
        skipped = 0
        for ch in ALL_CHARTS:
            name = ch["name"]
            if name in existing_names:
                print(f"  [skip] '{name}' ya existe")
                skipped += 1
                continue
            meta = {
                "description": ch["description"],
                "is_draft": False,
                "updated_at": now_str(),
            }
            spec = Spec(
                name=name,
                type=SPEC_TYPE,
                metadata_=json.dumps(meta, ensure_ascii=False),
                charts_list=json.dumps([ch["config"]], ensure_ascii=False),
                tables_list="[]",
                org_id=org_id,
            )
            db.add(spec)
            db.flush()
            print(f"  [ok]   {name}  (id={spec.id_spec}, type={ch['config']['chart_type']}, metric={ch['config']['data_source']['metric_id']})")
            created += 1
        db.commit()
        print(f"\nSeed completado: {created} creados, {skipped} ya existentes.")
    finally:
        db.close()


def main() -> None:
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            raise RuntimeError("No se encontró usuario admin")
        org_id = admin.org_id
        print(f"Sembrando catálogo de gráficos en org_id={org_id}...")
    finally:
        db.close()
    seed(org_id)


if __name__ == "__main__":
    main()
