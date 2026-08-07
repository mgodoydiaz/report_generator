# -*- coding: utf-8 -*-
"""
retirar_nombre_norm.py
======================
Quita la dimensión `Nombre_Norm` (y cualquier hermana `X_Norm` de la
convención deprecada) de `metric_dimensions` en TODAS las métricas de una
organización.

Contexto (retiro de `Nombre_Norm`, 2026-08-07): la clave normalizada dejó
de ser un dato persistido — la identidad de lectura se calcula al vuelo con
`normalizar_nombre` (RUT → nombre normalizado en memoria) y `Nombre` es la
única fuente de verdad visible. Al desasociar la dimensión:

  - Los lectores (`LoadMetricToDF`, dashboards, export) dejan de proyectar
    la columna.
  - Los caminos de escritura dejan de poder mapearla (además `SaveToMetric`
    ya la descarta explícitamente).
  - Los valores históricos en `metric_data.dimensions_json` QUEDAN INERTES
    por defecto: no se borran, no molestan y siguen disponibles para
    scripts de reparación (`restaurar_nombres_legibles.py`). `--strip-json`
    los elimina, solo si se pide explícitamente.
  - La fila de `dimensions` NO se borra: conserva el nombre para que
    cualquier lector que resuelva ids siga rotulando la clave heredada.

Idempotente, org-scoped y con dry-run por defecto.

Uso:
    python scripts/retirar_nombre_norm.py --org 1              # dry-run
    python scripts/retirar_nombre_norm.py --org 1 --apply
    python scripts/retirar_nombre_norm.py --org 1 --apply --strip-json
"""
from __future__ import annotations

import argparse
import json

#: Sufijos de la convención deprecada (misma tupla que usa SaveToMetric).
SUFIJOS_NORM = ("_Norm", "_norm", "_NORM")


def _es_nombre_norm(nombre) -> bool:
    return isinstance(nombre, str) and any(
        nombre.endswith(s) and len(nombre) > len(s) for s in SUFIJOS_NORM
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--org", type=int, default=1, help="org_id (default 1)")
    ap.add_argument("--apply", action="store_true",
                    help="escribe los cambios (sin esto es dry-run)")
    ap.add_argument("--strip-json", action="store_true",
                    help="además elimina los valores de esas dimensiones en "
                         "metric_data.dimensions_json (por defecto quedan inertes)")
    args = ap.parse_args()

    from backend.database import SessionLocal
    from backend.models import Dimension, Metric, MetricData, MetricDimension

    db = SessionLocal()
    try:
        dims_norm = db.query(Dimension).filter(
            Dimension.org_id == args.org
        ).all()
        dims_norm = [d for d in dims_norm if _es_nombre_norm(d.name)]
        if not dims_norm:
            print(f"Org {args.org}: no hay dimensiones con sufijo _Norm. Nada que hacer.")
            return 0

        ids_norm = {d.id_dimension: d.name for d in dims_norm}
        print(f"Org {args.org}: dimensiones de la convención deprecada:")
        for d in dims_norm:
            print(f"  · id {d.id_dimension}  '{d.name}'")

        # Asociaciones metric_dimensions de métricas de la org.
        metricas = {m.id_metric: m.name for m in
                    db.query(Metric).filter(Metric.org_id == args.org).all()}
        links = db.query(MetricDimension).filter(
            MetricDimension.id_dimension.in_(ids_norm.keys()),
            MetricDimension.id_metric.in_(metricas.keys() or [0]),
        ).all()

        print(f"\nAsociaciones en metric_dimensions a retirar: {len(links)}")
        for lnk in links:
            print(f"  · métrica {lnk.id_metric} '{metricas.get(lnk.id_metric)}' "
                  f"↔ dim {lnk.id_dimension} '{ids_norm.get(lnk.id_dimension)}'")

        if args.apply:
            for lnk in links:
                db.delete(lnk)

        # Valores históricos en dimensions_json (solo con --strip-json).
        filas_con_valor = 0
        filas_limpiadas = 0
        if args.strip_json:
            claves = {str(i) for i in ids_norm}
            rows = (
                db.query(MetricData)
                .filter(MetricData.id_metric.in_(metricas.keys() or [0]))
                .all()
            )
            for row in rows:
                try:
                    dims = json.loads(row.dimensions_json) \
                        if isinstance(row.dimensions_json, str) else dict(row.dimensions_json or {})
                except (TypeError, ValueError):
                    continue
                presentes = claves & set(dims.keys())
                if not presentes:
                    continue
                filas_con_valor += 1
                if args.apply:
                    for k in presentes:
                        dims.pop(k, None)
                    row.dimensions_json = json.dumps(dims, ensure_ascii=False)
                    filas_limpiadas += 1
            print(f"\n--strip-json: {filas_con_valor} filas de metric_data traen la "
                  f"clave; {'limpiadas ' + str(filas_limpiadas) if args.apply else 'se limpiarían'}.")
        else:
            print("\nLos valores históricos en dimensions_json quedan inertes "
                  "(no se borran; usar --strip-json para limpiarlos).")

        if args.apply:
            db.commit()
            print(f"\nAplicado: {len(links)} asociaciones retiradas.")
        else:
            print(f"\n--dry-run (default): {len(links)} asociaciones se retirarían. "
                  f"Repetir con --apply para escribir.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
