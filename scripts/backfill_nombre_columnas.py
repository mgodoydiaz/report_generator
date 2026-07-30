"""
backfill_nombre_columnas.py — Rellena las dimensiones `Nombre` / `Nombre_Norm`
que quedaron a medias en cargas históricas.

Contexto del bug
----------------
`SaveToMetric` mapea columnas del DataFrame a dimensiones por nombre EXACTO.
El XLS de la Agencia DIA trae la columna "Nombre del Estudiante", y el
pipeline solo derivaba `Nombre_Norm` a partir de ella: como ninguna columna
se llamaba "Nombre", esa dimensión quedó nula en el 100% de las cargas 2026.
Las cargas 2025, en cambio, poblaban `Nombre` pero no existía todavía el
kind `normalize_name`, así que quedaron sin `Nombre_Norm`.

El fix del pipeline (ver `apply_normalize_name` y `SaveToMetric`) evita que
vuelva a ocurrir. Este script repara los datos YA cargados:

  - `Nombre` vacío y `Nombre_Norm` presente  → `Nombre` = `Nombre_Norm`
    (el original ya se perdió; mostrar el nombre reordenado es mejor que un
    guion en el informe).
  - `Nombre_Norm` vacío y `Nombre` presente  → `Nombre_Norm` =
    normalizar_nombre(`Nombre`), con LA MISMA función canónica del pipeline.
  - Ambas presentes → no se toca.
  - Ninguna presente → fila sin identidad, irreparable, se reporta.

Uso (dentro del contenedor backend)
-----------------------------------
    python scripts/backfill_nombre_columnas.py --org 1              # dry-run
    python scripts/backfill_nombre_columnas.py --org 1 --apply      # escribe

`--org` es obligatorio y no existe modo "todas las orgs": el backfill es una
escritura masiva y debe decidirse organización por organización. En concreto,
la org demo tiene filas con `Nombre` nulo sembradas a propósito como casos
borde de los tests (`tests/regresion/test_crear_org_demo.py`) y NO debe
backfillearse.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.models import Dimension, Metric, MetricData, MetricDimension
# Función canónica de normalización — la misma que usa el kind
# `normalize_name` del pipeline. No reimplementar aquí: si divergen, las
# claves de join entre hitos dejan de coincidir.
from backend.rgenerator.core.derived_fields_engine import normalizar_nombre

NOMBRE = "Nombre"
NOMBRE_NORM = "Nombre_Norm"


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


def _resolver_dimensiones(db, org_id):
    """Resuelve los ids de `Nombre` y `Nombre_Norm` POR NOMBRE dentro de la org.

    Los ids difieren entre organizaciones, así que nunca deben hardcodearse.
    Devuelve (id_nombre, id_norm); cualquiera puede ser None.
    """
    dims = db.query(Dimension).filter(
        Dimension.org_id == org_id,
        Dimension.name.in_([NOMBRE, NOMBRE_NORM]),
    ).all()
    mapa = {d.name: d.id_dimension for d in dims}
    return mapa.get(NOMBRE), mapa.get(NOMBRE_NORM)


def _metricas_con_nombre(db, org_id, id_nombre, id_norm):
    """Métricas de la org que declaran `Nombre` y/o `Nombre_Norm`.

    Las métricas "por Pregunta" / "por OA" / "por Habilidad" son
    agregados que NO tienen estudiante: contarlas como filas "sin
    identidad" inflaría el resumen con miles de falsos irreparables.
    """
    filas = (
        db.query(MetricDimension.id_metric)
        .join(Metric, Metric.id_metric == MetricDimension.id_metric)
        .filter(
            Metric.org_id == org_id,
            MetricDimension.id_dimension.in_([id_nombre, id_norm]),
        )
        .distinct()
        .all()
    )
    return {f[0] for f in filas}


def backfill(db, org_id, aplicar=False):
    """Recorre `metric_data` de la org y completa el par Nombre/Nombre_Norm.

    Devuelve un dict con el resumen, o None si la org no tiene las
    dimensiones necesarias.
    """
    id_nombre, id_norm = _resolver_dimensiones(db, org_id)
    if id_nombre is None or id_norm is None:
        faltantes = [
            n for n, v in ((NOMBRE, id_nombre), (NOMBRE_NORM, id_norm))
            if v is None
        ]
        print(
            f"La organización {org_id} no tiene la(s) dimensión(es) "
            f"{', '.join(faltantes)}. No hay nada que backfillear."
        )
        return None

    k_nombre, k_norm = str(id_nombre), str(id_norm)
    print(
        f"Organización {org_id} — dimensiones resueltas: "
        f"{NOMBRE}={id_nombre}, {NOMBRE_NORM}={id_norm}"
    )

    metricas = _metricas_con_nombre(db, org_id, id_nombre, id_norm)
    if not metricas:
        print(
            f"Ninguna métrica de la organización {org_id} usa {NOMBRE} / "
            f"{NOMBRE_NORM}. No hay nada que backfillear."
        )
        return None
    print(f"Métricas con dimensiones de nombre: {sorted(metricas)}")

    resumen = {
        "revisadas": 0,
        "copiadas_nombre": 0,     # Nombre ← Nombre_Norm
        "normalizadas_norm": 0,   # Nombre_Norm ← normalizar(Nombre)
        "sin_identidad": 0,
        "ya_completas": 0,
        "por_metrica": defaultdict(lambda: {
            "revisadas": 0,
            "copiadas_nombre": 0,
            "normalizadas_norm": 0,
            "sin_identidad": 0,
        }),
    }

    filas = db.query(MetricData).filter(
        MetricData.org_id == org_id,
        MetricData.id_metric.in_(metricas),
    ).all()

    for fila in filas:
        dims = _parse_dimensions(fila.dimensions_json)
        val_nombre = (dims.get(k_nombre) or "").strip()
        val_norm = (dims.get(k_norm) or "").strip()

        resumen["revisadas"] += 1
        por_m = resumen["por_metrica"][fila.id_metric]
        por_m["revisadas"] += 1

        if val_nombre and val_norm:
            resumen["ya_completas"] += 1
            continue

        if not val_nombre and not val_norm:
            resumen["sin_identidad"] += 1
            por_m["sin_identidad"] += 1
            continue

        if not val_nombre and val_norm:
            dims[k_nombre] = val_norm
            resumen["copiadas_nombre"] += 1
            por_m["copiadas_nombre"] += 1
        else:
            normalizado = normalizar_nombre(val_nombre)
            if not normalizado:
                # Nombre con solo espacios/símbolos: no produce clave útil.
                resumen["sin_identidad"] += 1
                por_m["sin_identidad"] += 1
                continue
            dims[k_norm] = normalizado
            resumen["normalizadas_norm"] += 1
            por_m["normalizadas_norm"] += 1

        if aplicar:
            fila.dimensions_json = json.dumps(dims, ensure_ascii=False)

    if aplicar:
        db.commit()

    return resumen


def _imprimir_resumen(resumen, nombres_metricas, aplicar):
    modo = "APLICADO" if aplicar else "DRY-RUN (no se escribió nada)"
    print(f"\n=== Resumen backfill Nombre / Nombre_Norm — {modo} ===")
    print(f"Filas revisadas .................. {resumen['revisadas']}")
    print(f"Ya completas (sin cambios) ....... {resumen['ya_completas']}")
    print(f"Nombre <- Nombre_Norm ............ {resumen['copiadas_nombre']}")
    print(f"Nombre_Norm <- normalizar(Nombre)  {resumen['normalizadas_norm']}")
    print(f"Sin identidad (irreparables) ..... {resumen['sin_identidad']}")

    print("\n--- Por métrica ---")
    cabecera = f"{'ID':>4}  {'Métrica':<45} {'Rev':>6} {'N<-Nrm':>7} {'Nrm<-N':>7} {'SinId':>6}"
    print(cabecera)
    print("-" * len(cabecera))
    for id_metric in sorted(resumen["por_metrica"]):
        d = resumen["por_metrica"][id_metric]
        if not (d["copiadas_nombre"] or d["normalizadas_norm"] or d["sin_identidad"]):
            continue
        nombre = (nombres_metricas.get(id_metric) or "?")[:45]
        print(
            f"{id_metric:>4}  {nombre:<45} {d['revisadas']:>6} "
            f"{d['copiadas_nombre']:>7} {d['normalizadas_norm']:>7} {d['sin_identidad']:>6}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Backfill de las dimensiones Nombre / Nombre_Norm en metric_data."
    )
    parser.add_argument(
        "--org", type=int, required=True,
        help="ID de la organización a procesar (obligatorio; no hay modo 'todas')."
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Escribe los cambios. Por defecto el script corre en dry-run."
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        nombres_metricas = {
            m.id_metric: m.name
            for m in db.query(Metric).filter(Metric.org_id == args.org).all()
        }
        resumen = backfill(db, args.org, aplicar=args.apply)
        if resumen is None:
            return 0
        _imprimir_resumen(resumen, nombres_metricas, args.apply)
        if not args.apply:
            print("\nDry-run: volvé a correr con --apply para escribir los cambios.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
