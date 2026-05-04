"""Seed inicial del catálogo de tablas (B7).

Crea las tablas que ya están definidas en los esquemas SIMCE/DIA del
motor PDF v2, pero como Spec con type='Tablas' editables desde la UI
en /tables. Las 5 tablas son las "secciones dinámicas" de ambos
informes (1 fila por alumno o por pregunta), que encajan perfecto en
el TableConfig actual.

Las 2 tablas tipo "resumen estadístico" (count/mean/min/max/std del
mismo campo agrupado por Curso) NO se incluyen porque requieren
multi-agg sobre la misma columna — el TableConfig de v1 mapea 1
columna a 1 agg. Cuando se extienda el schema (v2), agregarlas.

Idempotente: si ya existe una tabla con el mismo nombre, no la
duplica.

Uso (dentro del container):
    python /app/scripts/seed_table_catalog.py
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, "/app")

from backend.database import SessionLocal
from backend.models import Spec, User


SPEC_TYPE = "Tablas"


# ─────────────────────────────────────────────────────────────────────────
# Definiciones de tablas (clones de los esquemas SIMCE/DIA)
# ─────────────────────────────────────────────────────────────────────────


def color_diverging(midpoint: float = 0.5) -> dict:
    """Rojo→amarillo→verde con midpoint configurable."""
    return {
        "kind": "diverging",
        "min_color": "#ef4444",
        "neutral_color": "#fef3c7",
        "max_color": "#22c55e",
        "midpoint": midpoint,
    }


def color_diverging_zero() -> dict:
    """Para Avance/Mejora: rojo si <0, verde si >0."""
    return {
        "kind": "diverging",
        "min_color": "#ef4444",
        "neutral_color": "#fef3c7",
        "max_color": "#22c55e",
        "midpoint": 0,
    }


# ── SIMCE ────────────────────────────────────────────────────────────────

SIMCE_LOGRO_POR_ALUMNO = {
    "name": "SIMCE — Logro por Alumno",
    "description": "Lista detalle: 1 fila por estudiante con Logro, SIMCE, nivel, promedio del año, avance y mejora desde inicio. Equivalente al `tabla_logro_por_alumno` del esquema SIMCE.",
    "config": {
        "version": 1,
        "data_source": {"metric_id": 4, "filters": {}},
        "columns": [
            {"key": "Nombre", "header": "Estudiante", "format": "text", "pinned": True},
            {"key": "Curso", "header": "Curso", "format": "text"},
            {"key": "Rend", "header": "Logro", "format": "percent", "decimals": 1, "color_scale": color_diverging()},
            {"key": "SIMCE", "header": "SIMCE", "format": "int"},
            {"key": "Logro", "header": "Nivel", "format": "text"},
            {"key": "Logro_Promedio_Estudiante", "header": "Promedio Año", "format": "percent", "decimals": 1, "color_scale": color_diverging()},
            {"key": "Avance", "header": "Avance", "format": "percent", "decimals": 2, "color_scale": color_diverging_zero()},
            {"key": "Mejora_vs_Inicio", "header": "Mejora", "format": "percent", "decimals": 1, "color_scale": color_diverging_zero()},
        ],
        "behavior": {
            "sorting": [{"column": "Rend", "dir": "desc"}],
            "pagination": {"enabled": True, "page_size": 50},
            "search": True,
        },
    },
}

SIMCE_LOGRO_POR_PREGUNTA = {
    "name": "SIMCE — Logro por Pregunta",
    "description": "Lista detalle por pregunta: número, habilidad, eje temático y % de respuestas correctas (Logro).",
    "config": {
        "version": 1,
        "data_source": {"metric_id": 5, "filters": {}},
        "columns": [
            {"key": "Pregunta", "header": "N° Pregunta", "format": "int", "pinned": True},
            {"key": "Curso", "header": "Curso", "format": "text"},
            {"key": "Habilidad", "header": "Habilidad", "format": "text"},
            {"key": "Eje Temático", "header": "Eje Temático", "format": "text"},
            {"key": "Logro", "header": "Logro", "format": "percent", "decimals": 1, "color_scale": color_diverging()},
        ],
        "behavior": {
            "sorting": [{"column": "Logro", "dir": "asc"}],
            "pagination": {"enabled": True, "page_size": 50},
            "search": True,
        },
    },
}

SIMCE_ESTADISTICA_PREGUNTA = {
    "name": "SIMCE — Estadística por Pregunta",
    "description": "Distribución de respuestas A/B/C/D/E por pregunta + alternativa correcta y distractor principal.",
    "config": {
        "version": 1,
        "data_source": {"metric_id": 5, "filters": {}},
        "columns": [
            {"key": "Pregunta", "header": "N° Pregunta", "format": "int", "pinned": True},
            {"key": "Curso", "header": "Curso", "format": "text"},
            {"key": "A", "header": "A", "format": "percent", "decimals": 0},
            {"key": "B", "header": "B", "format": "percent", "decimals": 0},
            {"key": "C", "header": "C", "format": "percent", "decimals": 0},
            {"key": "D", "header": "D", "format": "percent", "decimals": 0},
            {"key": "E", "header": "E", "format": "percent", "decimals": 0},
            {"key": "Correcta", "header": "Correcta", "format": "text"},
            {"key": "Distractor", "header": "Distractor", "format": "text"},
            {"key": "Logro", "header": "Logro", "format": "percent", "decimals": 1, "color_scale": color_diverging()},
        ],
        "behavior": {
            "sorting": [{"column": "Pregunta", "dir": "asc"}],
            "pagination": {"enabled": True, "page_size": 50},
            "search": True,
        },
    },
}


# ── DIA ──────────────────────────────────────────────────────────────────

DIA_LOGRO_POR_ALUMNO = {
    "name": "DIA — Logro por Alumno",
    "description": "Lista detalle por estudiante DIA: número de lista, nombre, logro, nivel y promedio del hito. Avance/Mejora se llenan cuando hay ≥2 hitos cargados.",
    "config": {
        "version": 1,
        "data_source": {"metric_id": 6, "filters": {}},
        "columns": [
            {"key": "Numero Lista", "header": "N° Lista", "format": "int", "pinned": True, "width": 80},
            {"key": "Nombre", "header": "Estudiante", "format": "text"},
            {"key": "Curso", "header": "Curso", "format": "text"},
            {"key": "Hito", "header": "Hito", "format": "text"},
            {"key": "Logro", "header": "Logro", "format": "percent", "decimals": 1, "color_scale": color_diverging()},
            {"key": "Nivel Logro", "header": "Nivel", "format": "text"},
            {"key": "Logro Promedio", "header": "Promedio", "format": "percent", "decimals": 1, "color_scale": color_diverging()},
        ],
        "behavior": {
            "sorting": [{"column": "Curso", "dir": "asc"}, {"column": "Numero Lista", "dir": "asc"}],
            "pagination": {"enabled": True, "page_size": 50},
            "search": True,
        },
    },
}

DIA_LOGRO_POR_PREGUNTA = {
    "name": "DIA — Logro por Pregunta",
    "description": "Lista detalle por pregunta DIA: número, eje temático, habilidad, indicador de evaluación y nivel de logro.",
    "config": {
        "version": 1,
        "data_source": {"metric_id": 7, "filters": {}},
        "columns": [
            {"key": "N Pregunta", "header": "N° Pregunta", "format": "int", "pinned": True, "width": 90},
            {"key": "Curso", "header": "Curso", "format": "text"},
            {"key": "Eje Temático", "header": "Eje Temático", "format": "text"},
            {"key": "Habilidad", "header": "Habilidad", "format": "text"},
            {"key": "Indicador", "header": "Indicador", "format": "text"},
            {"key": "Logro", "header": "Logro", "format": "percent", "decimals": 1, "color_scale": color_diverging()},
            {"key": "Nivel Logro", "header": "Nivel", "format": "text"},
        ],
        "behavior": {
            "sorting": [{"column": "Logro", "dir": "asc"}],
            "pagination": {"enabled": True, "page_size": 50},
            "search": True,
        },
    },
}


ALL_TABLES = [
    SIMCE_LOGRO_POR_ALUMNO,
    SIMCE_LOGRO_POR_PREGUNTA,
    SIMCE_ESTADISTICA_PREGUNTA,
    DIA_LOGRO_POR_ALUMNO,
    DIA_LOGRO_POR_PREGUNTA,
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
        for tbl in ALL_TABLES:
            name = tbl["name"]
            if name in existing_names:
                print(f"  [skip] '{name}' ya existe")
                skipped += 1
                continue
            meta = {
                "description": tbl["description"],
                "is_draft": False,  # publicadas (vienen del seed oficial)
                "updated_at": now_str(),
            }
            spec = Spec(
                name=name,
                type=SPEC_TYPE,
                metadata_=json.dumps(meta, ensure_ascii=False),
                charts_list="[]",
                tables_list=json.dumps([tbl["config"]], ensure_ascii=False),
                org_id=org_id,
            )
            db.add(spec)
            db.flush()
            print(f"  [ok]   {name}  (id={spec.id_spec}, metric={tbl['config']['data_source']['metric_id']}, cols={len(tbl['config']['columns'])})")
            created += 1
        db.commit()
        print(f"\nSeed completado: {created} creadas, {skipped} ya existentes.")
    finally:
        db.close()


def main() -> None:
    db = SessionLocal()
    try:
        # Toma el primer admin como referencia de org. Si hay multi-org,
        # ejecutar este script una vez por org_id deseado.
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            raise RuntimeError("No se encontró un usuario admin para inferir org_id")
        org_id = admin.org_id
        print(f"Sembrando catálogo de tablas en org_id={org_id}...")
    finally:
        db.close()
    seed(org_id)


if __name__ == "__main__":
    main()
