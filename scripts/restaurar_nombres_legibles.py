"""
restaurar_nombres_legibles.py — Restaura la dimensión `Nombre` legible en las
filas de `metric_data` donde quedó igual a `Nombre_Norm`.

Contexto del bug
----------------
El backfill de julio (`scripts/backfill_nombre_columnas.py`) copió
`Nombre_Norm` sobre `Nombre` cuando el nombre original faltaba. Resultado:
filas donde `Nombre` muestra el formato normalizado (palabras ordenadas
alfabéticamente, mayúsculas, sin tildes: "GONZALEZ JUAN PEREZ") en vez del
nombre real. El mismo estudiante SÍ aparece con nombre legible en otras
filas/métricas de la misma organización (misma clave normalizada o mismo
RUT); este script lo recupera desde ahí.

Fuentes de nombre legible (en orden)
------------------------------------
(a) Filas de la MISMA org (cualquier métrica) cuyo `Nombre` es legible
    (definición: `Nombre != normalizar_nombre(Nombre)` — conserva orden,
    tildes o mayúsculas originales) y normaliza a la clave `Nombre_Norm`
    de la fila objetivo.
(b) Filas de la MISMA org con el MISMO RUT (cuando la fila objetivo tiene
    RUT) y `Nombre` legible. Se usa cuando (a) no produce un ganador
    único: si (a) empató, el RUT desambigua entre los finalistas; si (a)
    quedó vacío, se toman los nombres legibles asociados al RUT (siempre
    gateados por la invariante de abajo).

Regla de elección entre variantes legibles
------------------------------------------
La variante MÁS FRECUENTE; en empate de frecuencia gana la MÁS LARGA; si
el empate persiste (misma frecuencia y mismo largo, strings distintos) la
fila se reporta como `ambigua` y NO se escribe.

Invariante (verificada antes de escribir CADA fila)
---------------------------------------------------
`normalizar_nombre(nombre_restaurado) == Nombre_Norm` de la fila. Solo se
escribe la clave `Nombre`; `Nombre_Norm` queda intacta y sigue siendo
coherente porque el nombre restaurado normaliza a la misma clave. Si la
invariante no calza (posible solo vía fuente RUT), la fila se aborta con
warning y se reporta como `invariante_violada`.

Uso (dentro del contenedor backend, o con DATABASE_URL apuntando a la DB)
-------------------------------------------------------------------------
    python scripts/restaurar_nombres_legibles.py                    # dry-run org 1
    python scripts/restaurar_nombres_legibles.py --org 1 --apply    # escribe

Con `--apply` se escribe SIEMPRE un respaldo CSV previo (id_data +
dimensions_json original) en `scripts/_respaldos/` o en la ruta `--backup`.
La lista completa de filas no restauradas (con su motivo) se exporta a CSV
(`--report`, con default también en `scripts/_respaldos/`).
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.models import Dimension, Metric, MetricData
# Función canónica de normalización — la misma que usa el kind
# `normalize_name` del pipeline y el backfill original. No reimplementar:
# si divergen, las claves de join entre hitos dejan de coincidir.
from backend.rgenerator.core.derived_fields_engine import normalizar_nombre

NOMBRE = "Nombre"
NOMBRE_NORM = "Nombre_Norm"
RUT = "RUT"

RESPALDOS_DIR = ROOT / "scripts" / "_respaldos"


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


def _val(dims, key):
    """Valor string stripeado de una clave de dimensión (o '')."""
    if key is None:
        return ""
    v = dims.get(key)
    return "" if v is None else str(v).strip()


def _es_legible(nombre):
    """Un nombre es legible si difiere de su propia normalización.

    Conserva orden, tildes o mayúsculas/minúsculas originales. Un valor ya
    normalizado ("GONZALEZ JUAN PEREZ") normaliza a sí mismo y NO cuenta.
    """
    return bool(nombre) and normalizar_nombre(nombre) != nombre


def _resolver_dimensiones(db, org_id):
    """Resuelve los ids de Nombre / Nombre_Norm / RUT POR NOMBRE en la org.

    Los ids difieren entre organizaciones (y entre dev y prod), así que
    nunca deben hardcodearse. RUT es opcional (puede ser None).
    """
    dims = db.query(Dimension).filter(
        Dimension.org_id == org_id,
        Dimension.name.in_([NOMBRE, NOMBRE_NORM, RUT]),
    ).all()
    mapa = {d.name: d.id_dimension for d in dims}
    return mapa.get(NOMBRE), mapa.get(NOMBRE_NORM), mapa.get(RUT)


def _elegir(candidatos):
    """Aplica la regla de elección sobre un Counter {nombre: frecuencia}.

    Devuelve (ganador, finalistas): la variante más frecuente; empate →
    la más larga. Si tras ambas reglas quedan varias (misma frecuencia y
    mismo largo), ganador es None y `finalistas` trae las empatadas.
    """
    if not candidatos:
        return None, []
    max_freq = max(candidatos.values())
    top = [n for n, c in candidatos.items() if c == max_freq]
    max_len = max(len(n) for n in top)
    finalistas = sorted(n for n in top if len(n) == max_len)
    if len(finalistas) == 1:
        return finalistas[0], finalistas
    return None, finalistas


def _nuevo_resumen_metrica():
    return {
        "objetivo": 0,
        "restauradas": 0,
        "sin_candidato": 0,
        "ambiguas": 0,
        "invariante_violada": 0,
    }


def restaurar(db, org_id, aplicar=False, backup_path=None, report_path=None):
    """Restaura nombres legibles en las filas objetivo de la org.

    Fila objetivo: `dimensions_json` tiene AMBAS claves y
    `Nombre.strip() == Nombre_Norm.strip() != ""`.

    Devuelve el resumen (dict) o None si la org no tiene las dimensiones
    Nombre / Nombre_Norm. Con `aplicar=True` exige `backup_path` y escribe
    el respaldo ANTES de modificar cualquier fila.
    """
    if aplicar and not backup_path:
        raise ValueError(
            "aplicar=True requiere un respaldo previo obligatorio: "
            "pasa backup_path (CSV con id_data + dimensions_json original)."
        )

    id_nombre, id_norm, id_rut = _resolver_dimensiones(db, org_id)
    if id_nombre is None or id_norm is None:
        faltantes = [
            n for n, v in ((NOMBRE, id_nombre), (NOMBRE_NORM, id_norm))
            if v is None
        ]
        print(
            f"La organización {org_id} no tiene la(s) dimensión(es) "
            f"{', '.join(faltantes)}. No hay nada que restaurar."
        )
        return None

    k_nombre, k_norm = str(id_nombre), str(id_norm)
    k_rut = str(id_rut) if id_rut is not None else None
    print(
        f"Organización {org_id} — dimensiones resueltas: "
        f"{NOMBRE}={id_nombre}, {NOMBRE_NORM}={id_norm}, "
        f"{RUT}={id_rut if id_rut is not None else '(no existe)'}"
    )

    # ── Pasada 1: cosecha de nombres legibles + detección de objetivos ──
    por_norm = defaultdict(Counter)   # clave normalizada -> Counter{nombre legible}
    por_rut = defaultdict(Counter)    # rut -> Counter{nombre legible}
    objetivos = []

    filas = (
        db.query(MetricData.id_data, MetricData.id_metric, MetricData.dimensions_json)
        .filter(MetricData.org_id == org_id)
        .yield_per(2000)
    )
    for id_data, id_metric, raw in filas:
        dims = _parse_dimensions(raw)
        nombre = _val(dims, k_nombre)
        rut = _val(dims, k_rut)

        if k_nombre in dims and k_norm in dims:
            norm = _val(dims, k_norm)
            if nombre and nombre == norm:
                objetivos.append({
                    "id_data": id_data,
                    "id_metric": id_metric,
                    "norm": norm,
                    "rut": rut,
                    "raw": raw,
                })
                continue  # una fila objetivo nunca es fuente (no es legible)

        if _es_legible(nombre):
            clave = normalizar_nombre(nombre)
            por_norm[clave][nombre] += 1
            if rut:
                por_rut[rut][nombre] += 1

    # ── Pasada 2: plan de restauración por fila objetivo ──
    resumen = {
        "objetivo": 0,
        "restauradas": 0,
        "sin_candidato": 0,
        "ambiguas": 0,
        "invariante_violada": 0,
        "por_metrica": defaultdict(_nuevo_resumen_metrica),
        "restauraciones": [],   # (id_data, id_metric, antes, despues, fuente)
        "no_restauradas": [],   # dicts para el CSV --report
    }
    plan = {}  # id_data -> nombre nuevo

    for obj in objetivos:
        resumen["objetivo"] += 1
        por_m = resumen["por_metrica"][obj["id_metric"]]
        por_m["objetivo"] += 1

        ganador, fuente, motivo = None, None, None

        candidatos_norm = por_norm.get(obj["norm"])
        if candidatos_norm:
            ganador, finalistas = _elegir(candidatos_norm)
            if ganador is not None:
                fuente = "norm"
            elif obj["rut"] and por_rut.get(obj["rut"]):
                # (b) el RUT desambigua entre los finalistas empatados de (a)
                sub = Counter({
                    n: c for n, c in por_rut[obj["rut"]].items()
                    if n in finalistas
                })
                ganador, _ = _elegir(sub)
                fuente = "rut" if ganador is not None else None
                if ganador is None:
                    motivo = "ambigua"
            else:
                motivo = "ambigua"
        elif obj["rut"] and por_rut.get(obj["rut"]):
            # (b) puro: sin candidatos por clave normalizada
            ganador, _ = _elegir(por_rut[obj["rut"]])
            fuente = "rut" if ganador is not None else None
            if ganador is None:
                motivo = "ambigua"
        else:
            motivo = "sin_candidato"

        # Invariante: el nombre restaurado debe normalizar a la MISMA clave
        # que ya tiene la fila (Nombre_Norm queda intacta y coherente).
        if ganador is not None and normalizar_nombre(ganador) != obj["norm"]:
            print(
                f"ADVERTENCIA: fila {obj['id_data']} — el candidato "
                f"{ganador!r} (fuente {fuente}) normaliza a "
                f"{normalizar_nombre(ganador)!r} y no a {obj['norm']!r}. "
                f"Se aborta la fila."
            )
            motivo = "invariante_violada"
            ganador = None

        if ganador is not None:
            plan[obj["id_data"]] = ganador
            resumen["restauradas"] += 1
            por_m["restauradas"] += 1
            resumen["restauraciones"].append(
                (obj["id_data"], obj["id_metric"], obj["norm"], ganador, fuente)
            )
        else:
            clave_resumen = {
                "sin_candidato": "sin_candidato",
                "ambigua": "ambiguas",
                "invariante_violada": "invariante_violada",
            }[motivo]
            resumen[clave_resumen] += 1
            por_m[clave_resumen] += 1
            resumen["no_restauradas"].append({
                "id_data": obj["id_data"],
                "id_metric": obj["id_metric"],
                "nombre_norm": obj["norm"],
                "rut": obj["rut"],
                "motivo": motivo,
            })

    # ── Respaldo previo + escritura ──
    if aplicar and plan:
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        with open(backup_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id_data", "dimensions_json"])
            for obj in objetivos:
                if obj["id_data"] in plan:
                    w.writerow([obj["id_data"], obj["raw"]])
        print(f"Respaldo previo escrito: {backup_path} ({len(plan)} filas)")

        ids = sorted(plan)
        for i in range(0, len(ids), 500):
            lote = ids[i:i + 500]
            for fila in db.query(MetricData).filter(
                MetricData.id_data.in_(lote)
            ).all():
                dims = _parse_dimensions(fila.dimensions_json)
                nombre = _val(dims, k_nombre)
                norm = _val(dims, k_norm)
                nuevo = plan[fila.id_data]
                # Re-verificación al momento de escribir: la fila sigue
                # siendo objetivo y la invariante calza.
                if not (nombre and nombre == norm
                        and normalizar_nombre(nuevo) == norm):
                    print(
                        f"ADVERTENCIA: fila {fila.id_data} cambió entre la "
                        f"lectura y la escritura; se omite."
                    )
                    resumen["restauradas"] -= 1
                    resumen["invariante_violada"] += 1
                    por_m = resumen["por_metrica"][fila.id_metric]
                    por_m["restauradas"] -= 1
                    por_m["invariante_violada"] += 1
                    resumen["no_restauradas"].append({
                        "id_data": fila.id_data,
                        "id_metric": fila.id_metric,
                        "nombre_norm": norm,
                        "rut": _val(dims, k_rut),
                        "motivo": "invariante_violada",
                    })
                    continue
                dims[k_nombre] = nuevo
                fila.dimensions_json = json.dumps(dims, ensure_ascii=False)
        db.commit()

    # ── CSV de no restauradas ──
    if report_path is not None:
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["id_data", "id_metric", "nombre_norm", "rut", "motivo"],
            )
            w.writeheader()
            for fila in resumen["no_restauradas"]:
                w.writerow(fila)
        print(
            f"Reporte de no restauradas: {report_path} "
            f"({len(resumen['no_restauradas'])} filas)"
        )

    return resumen


def _imprimir_resumen(resumen, nombres_metricas, aplicar):
    modo = "APLICADO" if aplicar else "DRY-RUN (no se escribió nada)"
    print(f"\n=== Resumen restauración de nombres legibles — {modo} ===")
    print(f"Filas objetivo (Nombre == Nombre_Norm)  {resumen['objetivo']}")
    print(f"Restauradas ........................... {resumen['restauradas']}")
    print(f"Sin candidato ......................... {resumen['sin_candidato']}")
    print(f"Ambiguas (empate irresoluble) ......... {resumen['ambiguas']}")
    print(f"Invariante violada (abortadas) ........ {resumen['invariante_violada']}")

    print("\n--- Por métrica ---")
    cabecera = (
        f"{'ID':>4}  {'Métrica':<45} {'Obj':>6} {'Rest':>6} "
        f"{'SinC':>6} {'Amb':>5} {'Inv':>5}"
    )
    print(cabecera)
    print("-" * len(cabecera))
    for id_metric in sorted(resumen["por_metrica"]):
        d = resumen["por_metrica"][id_metric]
        if not d["objetivo"]:
            continue
        nombre = (nombres_metricas.get(id_metric) or "?")[:45]
        print(
            f"{id_metric:>4}  {nombre:<45} {d['objetivo']:>6} "
            f"{d['restauradas']:>6} {d['sin_candidato']:>6} "
            f"{d['ambiguas']:>5} {d['invariante_violada']:>5}"
        )

    if resumen["restauraciones"]:
        print("\n--- Muestra (hasta 10 restauraciones) ---")
        for id_data, id_metric, antes, despues, fuente in resumen["restauraciones"][:10]:
            print(f"  [{id_data}] {antes!r} -> {despues!r}  (fuente: {fuente})")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Restaura la dimensión Nombre legible donde el backfill dejó "
            "Nombre == Nombre_Norm."
        )
    )
    parser.add_argument(
        "--org", type=int, default=1,
        help="ID de la organización a procesar (default: 1)."
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Escribe los cambios. Por defecto el script corre en dry-run."
    )
    parser.add_argument(
        "--backup", type=Path, default=None,
        help=(
            "Ruta del respaldo CSV previo (id_data + dimensions_json). "
            "Default: scripts/_respaldos/restaurar_nombres_<org>_<ts>.csv"
        ),
    )
    parser.add_argument(
        "--report", type=Path, default=None,
        help=(
            "Ruta del CSV con las filas no restauradas y su motivo. "
            "Default: scripts/_respaldos/no_restauradas_<org>_<ts>.csv"
        ),
    )
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = args.backup or (
        RESPALDOS_DIR / f"restaurar_nombres_{args.org}_{ts}.csv"
    )
    report_path = args.report or (
        RESPALDOS_DIR / f"no_restauradas_{args.org}_{ts}.csv"
    )

    db = SessionLocal()
    try:
        nombres_metricas = {
            m.id_metric: m.name
            for m in db.query(Metric).filter(Metric.org_id == args.org).all()
        }
        resumen = restaurar(
            db, args.org,
            aplicar=args.apply,
            backup_path=backup_path,
            report_path=report_path,
        )
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
