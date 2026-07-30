"""
marcar_dimensiones_fecha.py — Marca con `data_type='date'` las dimensiones
de una organización que contienen fechas reales.

Por qué
-------
El resolver de períodos (`backend/rgenerator/reports/periodos.py`) deriva
AÑO y MES de una columna de tipo fecha. Sin eso, un indicador que registra
"Fecha" pero no tiene dimensión "Año" — el caso de Fluidez Lectora — no
puede resolver los informes semestral ni anual y las cards salen no
disponibles "estructuralmente".

Marcar la dimensión como fecha es metadata: hace la detección explícita y
robusta (no depende del nombre de la columna ni de la heurística de
parseo).

Criterio de marcado
-------------------
Una dimensión se propone como fecha si:

  a) su nombre normalizado es exactamente "fecha" (sin tildes, minúsculas), o
  b) al menos `--umbral` (default 90%) de sus valores reales parsean como
     fecha con `periodos.parsear_fecha` — que acepta ISO ("2026-04-07",
     con o sin hora) y latino ("07-04-2026", "07/04/2026").

Los valores salen de `metric_data.dimensions_json` (los datos que de verdad
se cargaron) y, si ahí no hay nada, del catálogo `dimension_values`.

En el caso (a) igual se exige que exista al menos un valor parseable: una
dimensión llamada "Fecha" con basura adentro NO se marca.

Uso (dentro del contenedor backend o con DATABASE_URL apuntando a la DB)
-----------------------------------------------------------------------
    python scripts/marcar_dimensiones_fecha.py --org 1            # dry-run
    python scripts/marcar_dimensiones_fecha.py --org 1 --apply    # escribe

`--org` es obligatorio: el catálogo de dimensiones es por organización y
esto es una escritura de metadata que debe decidirse org por org.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.models import Dimension, DimensionValue, MetricData, MetricDimension
# Parser canónico: el mismo que usa el resolver de períodos. No
# reimplementar acá — si divergen, se marcan dimensiones que el resolver
# después no sabe leer.
from backend.rgenerator.reports.periodos import parsear_fecha, _sin_tildes

TIPO_FECHA = "date"
UMBRAL_DEFAULT = 0.9
MUESTRA_MAX = 2000


def _parse_dimensions(raw):
    """`dimensions_json` es Text; puede venir vacío o malformado."""
    if not raw:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _valores_de_dimension(db, org_id, id_dimension, limite=MUESTRA_MAX):
    """Valores reales de una dimensión: primero metric_data, luego el catálogo."""
    clave = str(id_dimension)
    valores = []

    # Solo las métricas que declaran la dimensión: mirar todo `metric_data`
    # de la org devolvería mayormente filas sin esta clave.
    ids_metricas = [
        m[0] for m in db.query(MetricDimension.id_metric).filter(
            MetricDimension.id_dimension == id_dimension
        ).distinct().all()
    ]
    if ids_metricas:
        filas = (
            db.query(MetricData.dimensions_json)
            .filter(
                MetricData.org_id == org_id,
                MetricData.id_metric.in_(ids_metricas),
            )
            .limit(limite)
            .all()
        )
        for (raw,) in filas:
            valor = _parse_dimensions(raw).get(clave)
            if valor is not None and str(valor).strip() != "":
                valores.append(valor)

    if not valores:
        valores = [
            v.value for v in db.query(DimensionValue).filter(
                DimensionValue.id_dimension == id_dimension
            ).limit(limite).all()
            if v.value is not None and str(v.value).strip() != ""
        ]
    return valores


def _tasa(valores):
    """(parseables, total, tasa) de una lista de valores."""
    if not valores:
        return 0, 0, 0.0
    ok = sum(1 for v in valores if parsear_fecha(v) is not None)
    return ok, len(valores), ok / len(valores)


def analizar(db, org_id, umbral=UMBRAL_DEFAULT):
    """[{dimension, motivo, ...}] con las dimensiones que deberían ser fecha."""
    propuestas = []
    dims = db.query(Dimension).filter(Dimension.org_id == org_id).order_by(
        Dimension.id_dimension
    ).all()

    for dim in dims:
        por_nombre = _sin_tildes(dim.name) == "fecha"
        valores = _valores_de_dimension(db, org_id, dim.id_dimension)
        ok, total, tasa = _tasa(valores)

        if por_nombre:
            # El nombre propone, los datos disponen: sin valores parseables
            # no se marca (podría ser una columna "Fecha" con texto libre).
            if ok == 0:
                continue
            motivo = f"nombre exacto 'fecha' ({ok}/{total} valores parsean)"
        elif total and tasa >= umbral:
            motivo = f"{tasa:.0%} de los valores parsean como fecha ({ok}/{total})"
        else:
            continue

        propuestas.append({
            "id_dimension": dim.id_dimension,
            "name": dim.name,
            "data_type_actual": dim.data_type or "",
            "ya_marcada": (dim.data_type or "").strip().lower() == TIPO_FECHA,
            "motivo": motivo,
            "muestra": [str(v) for v in valores[:3]],
        })
    return propuestas


def marcar(db, org_id, aplicar=False, umbral=UMBRAL_DEFAULT):
    """Detecta (y opcionalmente marca) las dimensiones fecha de UNA org.

    Args:
        db: sesión SQLAlchemy.
        org_id: organización a revisar (el catálogo es por org).
        aplicar: False = dry-run (no escribe nada).
        umbral: fracción mínima de valores que deben parsear como fecha.

    Returns:
        {"propuestas": [...], "marcadas": int} — `marcadas` es cuántas
        cambiarían (dry-run) o cambiaron (apply).
    """
    propuestas = analizar(db, org_id, umbral)
    pendientes = [p for p in propuestas if not p["ya_marcada"]]

    if aplicar and pendientes:
        for p in pendientes:
            record = db.query(Dimension).filter(
                Dimension.id_dimension == p["id_dimension"],
                Dimension.org_id == org_id,
            ).first()
            if record:
                record.data_type = TIPO_FECHA
        db.commit()

    return {"propuestas": propuestas, "marcadas": len(pendientes)}


def main():
    parser = argparse.ArgumentParser(
        description="Marca dimensiones de tipo fecha (data_type='date')."
    )
    parser.add_argument("--org", type=int, required=True, help="id de la organización")
    parser.add_argument("--apply", action="store_true",
                        help="escribe los cambios (por defecto: dry-run)")
    parser.add_argument("--umbral", type=float, default=UMBRAL_DEFAULT,
                        help=f"fracción mínima de valores fecha (default {UMBRAL_DEFAULT})")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        resumen = marcar(db, args.org, aplicar=args.apply, umbral=args.umbral)
        propuestas = resumen["propuestas"]

        if not propuestas:
            print(f"[org {args.org}] No se encontraron dimensiones de tipo fecha.")
            return

        print(f"[org {args.org}] Dimensiones detectadas como fecha:")
        for p in propuestas:
            estado = ("ya marcada" if p["ya_marcada"]
                      else f"{p['data_type_actual'] or '(vacío)'} → {TIPO_FECHA}")
            print(f"  #{p['id_dimension']:>4} {p['name']:<20} {estado:<18} "
                  f"[{p['motivo']}] ej: {', '.join(p['muestra'])}")

        if args.apply:
            print(f"\nOK — {resumen['marcadas']} dimensión(es) marcada(s) "
                  f"como '{TIPO_FECHA}'.")
        else:
            print(f"\nDRY-RUN — {resumen['marcadas']} dimensión(es) se marcarían. "
                  f"Repite con --apply para escribir.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
