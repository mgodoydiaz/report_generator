# -*- coding: utf-8 -*-
"""
dia_cargar_items_1basico.py
===========================
Inserta en la métrica 7 ("Resultados DIA por Pregunta") los ítems 7-16 de Lectura
1° básico generados por `dia_1basico_items.py` (archivo `items_1basico_metric7.json`).

Esos ítems (Conciencia fonológica, Principio alfabético, Lectura de palabras) el PDF
DIA solo los grafica; salen del XLS por estudiante (L/NL). Ver
docs de diagnóstico sept 2026 y el docstring de `dia_1basico_items.py`.

Idempotente: antes de insertar busca, por cada registro, una fila existente con la
misma clave (Establecimiento, Año, Curso, Asignatura, Hito, N Pregunta) y la salta si
ya está. Usa `make_metric_data` (auditoría created_via = 'api_direct', sin usuario).

Uso:
    DATABASE_URL=... PYTHONPATH=. python scripts/dia_cargar_items_1basico.py --json <items_1basico_metric7.json> --dry-run
    DATABASE_URL=... PYTHONPATH=. python scripts/dia_cargar_items_1basico.py --json <items_1basico_metric7.json>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

METRIC_ID = 7
ORG = 1
# Clave de unicidad: Establecimiento, Año, Curso, Asignatura, Hito, N Pregunta
CLAVE = ("3", "4", "5", "8", "14", "16")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, help="items_1basico_metric7.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from sqlalchemy import text

    from backend.auditing import make_metric_data
    from backend.database import SessionLocal

    registros = json.loads(Path(args.json).read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        filtro = " AND ".join(f"dimensions_json::json->>'{k}' = :k{k}" for k in CLAVE)
        existe = text(f"SELECT 1 FROM metric_data WHERE org_id = :o AND id_metric = :m AND {filtro} LIMIT 1")
        nuevos, saltados = [], 0
        for r in registros:
            dims = r["dimensions_json"]
            faltan = [k for k in CLAVE if not str(dims.get(k, "")).strip()]
            if faltan:
                raise ValueError(f"registro sin dimensiones clave {faltan}: {dims}")
            params = {"o": ORG, "m": METRIC_ID, **{f"k{k}": str(dims[k]) for k in CLAVE}}
            if db.execute(existe, params).first():
                saltados += 1
                continue
            nuevos.append(make_metric_data(
                metric_id=METRIC_ID, value=json.dumps(r["value"]), dimensions=dims,
                org_id=ORG, user_id=None, via="api_direct",
            ))

        lotes = sorted({(d["dimensions_json"]["3"], d["dimensions_json"]["4"], d["dimensions_json"]["5"],
                         d["dimensions_json"]["14"]) for d in registros})
        print(f"{len(registros)} registros en el JSON · {len(nuevos)} a insertar · {saltados} ya existían")
        for l in lotes:
            print("   ", " · ".join(l))
        if args.dry_run or not nuevos:
            print("No se escribió nada." if args.dry_run else "Nada que insertar.")
            return 0
        db.add_all(nuevos)
        db.commit()
        print(f"Insertados {len(nuevos)} registros en la métrica {METRIC_ID}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
