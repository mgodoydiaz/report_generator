"""Normaliza valores de la dimensión Habilidad a Title Case en metric_data.

Resuelve el issue 2 del reporte de calidad: SIMCE preguntas (metric 5)
tiene "LOCALIZAR" + "Localizar" como dos categorías separadas porque los
xlsx originales venían con capitalización inconsistente.

Estrategia:
- Lee dimensions_json de cada metric_data y busca la dim 12 (Habilidad).
- Si está en mayúsculas o mixto, convierte a Title Case (primera letra
  de cada palabra en mayúscula, resto minúsculas).
- Actualiza el record en BD.

Uso:
    DATABASE_URL='postgresql://mgodoy:holapocompadre977@localhost:5432/rgenerator_dev' \
        python scripts/_normalize_habilidades.py [--dry-run]

Idempotente: re-ejecutar no cambia nada si los datos ya están normalizados.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://mgodoy:holapocompadre977@localhost:5432/rgenerator_dev",
)

from backend.database import SessionLocal  # noqa: E402
from backend.models import MetricData  # noqa: E402

# Dimensiones a normalizar (id_dimension → nombre)
TARGET_DIM_IDS = ["12", "13"]  # 12=Habilidad, 13=Eje Temático


def normalize_habilidad(s: str) -> str:
    """Title Case con manejo de palabras cortas en español.

    Solo afecta valores que usan ESPACIOS como separadores. Si el valor
    tiene underscores (`_`) o guiones (`-`), se asume formato máquina y
    se deja tal cual (ej: 'Algebra_y_Funciones', 'Eje-Tematico').

    Ejemplos:
        'LOCALIZAR' → 'Localizar'
        'localizar' → 'Localizar'
        'INTERPRETAR Y RELACIONAR' → 'Interpretar y Relacionar'
        'Resolver problemas' → 'Resolver Problemas'
        'Modelar' → 'Modelar'  (sin cambio si ya está OK)
        'Algebra_y_Funciones' → 'Algebra_y_Funciones'  (sin cambio, fmt máquina)
    """
    if not s or not isinstance(s, str):
        return s
    # No tocar valores con underscores o guiones — formato máquina,
    # asumimos consistente (si no lo es, normalizar requiere acuerdo
    # explícito sobre cuál es el "canónico").
    if '_' in s or '-' in s:
        return s
    stopwords = {'y', 'e', 'o', 'u', 'de', 'del', 'la', 'el', 'en'}
    parts = s.lower().split()
    out = []
    for i, w in enumerate(parts):
        if i == 0 or w not in stopwords:
            out.append(w.capitalize())
        else:
            out.append(w)
    return ' '.join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Imprime qué se cambiaría sin tocar la BD")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # Obtener todos los metric_data
        rows = db.query(MetricData).all()
        print(f"Total registros a inspeccionar: {len(rows):,}")

        changes_by_value = {}  # {(dim_id, valor_viejo): valor_nuevo}
        update_count = 0

        for row in rows:
            try:
                dims = json.loads(row.dimensions_json) if isinstance(row.dimensions_json, str) else (row.dimensions_json or {})
            except Exception:
                continue

            changed = False
            for dim_id in TARGET_DIM_IDS:
                if dim_id not in dims:
                    continue
                old = dims[dim_id]
                if not isinstance(old, str) or not old.strip():
                    continue
                new = normalize_habilidad(old)
                if new != old:
                    dims[dim_id] = new
                    changed = True
                    key = (dim_id, old)
                    changes_by_value[key] = new

            if changed:
                if not args.dry_run:
                    row.dimensions_json = json.dumps(dims, ensure_ascii=False)
                update_count += 1

        # Reporte
        print(f"\nValores normalizados detectados:")
        for (dim_id, old), new in sorted(changes_by_value.items()):
            print(f"  dim {dim_id}: '{old}' → '{new}'")

        print(f"\nTotal records que cambiarían: {update_count:,}")

        if args.dry_run:
            print("\n[DRY RUN] No se modificó la BD.")
            db.rollback()
        else:
            db.commit()
            print(f"\n✅ {update_count:,} records actualizados en BD.")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Rollback: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
