"""Seed inicial del catálogo de mapeos (B10).

Tablas de mapeo extraídas de `Formatos recomendados.xlsx` del cliente:
- Categoría FL (Fluidez Lectora) por Cantidad
- Nivel CV (Cálculo Veloz) por Puntaje
- Categoría EPTL por Puntaje
- Nivel Logro DIA por Logro

Idempotente. Ejecutar:
    python /app/scripts/seed_mappings.py
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, "/app")

from backend.database import SessionLocal
from backend.models import Spec, User


SPEC_TYPE = "Mapeo"


# ─────────────────────────────────────────────────────────────────────────
# Definiciones (extraídas de Formatos recomendados.xlsx)
# ─────────────────────────────────────────────────────────────────────────


MAPPINGS = [
    {
        "name": "FL — Categoría por Cantidad",
        "description": "Fluidez Lectora: clasifica el número de palabras leídas por minuto. Si Cantidad viene como texto (no parseable), → No Aplica.",
        "config": {
            "version": 1,
            "kind": "range",
            "ranges": [
                {"min": 0,    "max": 111,  "label": "MUY BAJA"},
                {"min": 111,  "max": 155,  "label": "BAJA"},
                {"min": 155,  "max": 182,  "label": "MEDIA"},
                {"min": 182,  "max": None, "label": "ALTA"},
            ],
            "match": "left_inclusive",
            "default": "No Aplica",
            "input_field_type": "numeric",
            "input_domain": "0-300 palabras/min",
            "mapping": {},
            "case_insensitive": False,
        },
    },
    {
        "name": "CV — Nivel por Puntaje",
        "description": "Cálculo Veloz: clasifica puntaje 0-100 en niveles. Tramos según `Formatos recomendados.xlsx`.",
        "config": {
            "version": 1,
            "kind": "range",
            "ranges": [
                {"min": 0,   "max": 40,  "label": "INICIAL"},
                {"min": 40,  "max": 60,  "label": "BÁSICO"},
                {"min": 60,  "max": 73,  "label": "INTERMEDIO"},
                {"min": 73,  "max": 86,  "label": "AVANZADO"},
                {"min": 86,  "max": None, "label": "EXPERTO"},
            ],
            "match": "left_inclusive",
            "default": "No Aplica",
            "input_field_type": "numeric",
            "input_domain": "0-100",
            "mapping": {},
            "case_insensitive": False,
        },
    },
    {
        "name": "EPTL — Categoría Lector por Puntaje",
        "description": "EPTL: clasifica puntaje 0-14+ en categorías de lector.",
        "config": {
            "version": 1,
            "kind": "range",
            "ranges": [
                {"min": 0,   "max": 3,   "label": "Lector Inicial"},
                {"min": 3,   "max": 6,   "label": "Lector Básico"},
                {"min": 6,   "max": 8,   "label": "Lector Intermedio"},
                {"min": 8,   "max": 10,  "label": "Lector Avanzado"},
                {"min": 10,  "max": 14,  "label": "Súper Lector"},
                {"min": 14,  "max": None, "label": "Fuera de Rango"},
            ],
            "match": "left_inclusive",
            "default": "No Aplica",
            "input_field_type": "numeric",
            "input_domain": "0-15+",
            "mapping": {},
            "case_insensitive": False,
        },
    },
    {
        "name": "DIA — Nivel Logro por Logro",
        "description": "DIA: clasifica el % de logro (0-1) en Inicial / Intermedio / Avanzado. Reemplaza el row_threshold inline del pipeline DIA.",
        "config": {
            "version": 1,
            "kind": "range",
            "ranges": [
                {"min": 0,    "max": 0.4, "label": "Inicial"},
                {"min": 0.4,  "max": 0.6, "label": "Intermedio"},
                {"min": 0.6,  "max": None, "label": "Avanzado"},
            ],
            "match": "left_inclusive",
            "default": "No Aplica",
            "input_field_type": "numeric",
            "input_domain": "0-1",
            "mapping": {},
            "case_insensitive": False,
        },
    },
    {
        "name": "Curso → Nivel (DIA/SIMCE)",
        "description": "Mapeo discreto curso → nivel. Reemplaza el lookup_dict inline del pipeline DIA. Toma el primer token (split por espacio) y lo busca en el dict.",
        "config": {
            "version": 1,
            "kind": "discrete",
            "ranges": [],
            "match": "left_inclusive",
            "mapping": {
                "1": "Primeros",   "2": "Segundos", "3": "Terceros",
                "4": "Cuartos",    "5": "Quintos",  "6": "Sextos",
                "7": "Septimos",   "8": "Octavos",
                "I": "Primeros Medios",   "II": "Segundos Medios",
                "III": "Terceros Medios", "IV": "Cuartos Medios",
            },
            "extract": {"split": " ", "index": 0, "regex": None},
            "case_insensitive": False,
            "default": "Sin Nivel",
            "input_field_type": "string",
            "input_domain": "Curso (ej '1 A', 'II A')",
        },
    },
]


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
        for m in MAPPINGS:
            if m["name"] in existing_names:
                print(f"  [skip] '{m['name']}' ya existe")
                skipped += 1
                continue
            meta = {
                "description": m["description"],
                "is_draft": False,
                "updated_at": now_str(),
                "mapping_config": m["config"],
            }
            spec = Spec(
                name=m["name"],
                type=SPEC_TYPE,
                metadata_=json.dumps(meta, ensure_ascii=False),
                charts_list="[]",
                tables_list="[]",
                org_id=org_id,
            )
            db.add(spec)
            db.flush()
            n_entries = len(m["config"].get("ranges", [])) + len(m["config"].get("mapping", {}))
            print(f"  [ok]   {m['name']}  (id={spec.id_spec}, kind={m['config']['kind']}, entries={n_entries})")
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
        print(f"Sembrando catálogo de mapeos en org_id={org_id}...")
    finally:
        db.close()
    seed(org_id)


if __name__ == "__main__":
    main()
