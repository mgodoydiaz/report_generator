# -*- coding: utf-8 -*-
"""
reparar_identidades_dia_2026.py
===============================
Recupera las identidades perdidas (Nombre y Nombre_Norm) del cohorte DIA
LECTURA·DIAGNOSTICO·2026, cargado el 2026-05-05 con un pipeline que descartaba
la columna `Nombre del Estudiante` (no matcheaba por nombre exacto con la
dimension `Nombre`).

Metodo — validado empiricamente (375/375 en dev, tolerancia 1e-9):
  1. El roster fuente se reconstruye desde los XLS originales (un CSV por
     colegio, generado aparte, con Logro recalculado con la formula del
     pipeline como checksum).
  2. Las filas huerfanas conservan Establecimiento y Curso, y el orden de
     insercion (`id_data` ascendente) preserva el orden del XLS (N° de lista
     ascendente) dentro de cada curso.
  3. Se une posicionalmente roster <-> filas por (Establecimiento, Curso) y se
     exige que el `Logro` guardado coincida con el recalculado en CADA fila.
     Si UNA fila no coincide, se aborta entero: no hay aplicacion parcial.

Solo toca filas del cohorte que NO tienen ni Nombre ni Nombre_Norm. Las filas
sanas no se leen siquiera. Antes de escribir deja un respaldo CSV con el
dimensions_json original de cada fila afectada.

Uso:
  # dev (dentro del contenedor backend)
  python reparar_identidades_dia_2026.py --rosters /tmp --dry-run
  python reparar_identidades_dia_2026.py --rosters /tmp --aplicar --backup /tmp/respaldo_dev.csv

  # prod (desde el host, con el DATABASE_URL de .env.railway)
  python scripts/reparar_identidades_dia_2026.py --rosters <dir> --env-file .env.railway --dry-run
  python scripts/reparar_identidades_dia_2026.py --rosters <dir> --env-file .env.railway \
      --aplicar --backup respaldo_prod.csv
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

TOL = 1e-9
METRIC = 6
ORG = 1
COHORTE = {"Año": "2026", "Hito": "DIAGNOSTICO", "Asignatura": "LECTURA"}
ROSTERS = {"roster_16843.csv": "PANGUIPULLI", "roster_16844.csv": "PULLINQUE"}
CANONICO = {"PANGUIPULLI": "Liceo PHP Panguipulli", "PULLINQUE": "Liceo PHP Pullinque"}


def cargar_rosters(carpeta: Path) -> dict:
    """{(estab_canonico, curso): [fila_roster ordenada por N° de lista]}"""
    grupos = defaultdict(list)
    for nombre_csv, clave in ROSTERS.items():
        ruta = carpeta / nombre_csv
        if not ruta.exists():
            raise SystemExit(f"ERROR: falta {ruta}")
        with open(ruta, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                assert clave in r["Establecimiento"].upper(), \
                    f"{nombre_csv}: establecimiento inesperado {r['Establecimiento']!r}"
                grupos[(CANONICO[clave], r["Curso"])].append(r)
    for k in grupos:
        grupos[k].sort(key=lambda x: int(x["Numero_Lista"]))
    return grupos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rosters", type=Path, required=True)
    ap.add_argument("--env-file", default=None,
                    help="con esto usa ese DATABASE_URL (prod); sin esto, backend.database (dev)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--backup", type=Path, default=None)
    args = ap.parse_args()
    if args.aplicar == args.dry_run:
        raise SystemExit("ERROR: usa exactamente uno de --dry-run / --aplicar")
    if args.aplicar and not args.backup:
        raise SystemExit("ERROR: --aplicar exige --backup <archivo>")

    import sqlalchemy as sa
    if args.env_file:
        from dotenv import dotenv_values
        url = dotenv_values(args.env_file).get("DATABASE_URL", "")
        if not url:
            raise SystemExit(f"ERROR: sin DATABASE_URL en {args.env_file}")
        eng = sa.create_engine(url, connect_args={"connect_timeout": 30})
        destino = url.split("@")[-1].split("/")[0]
    else:
        from backend.database import engine as eng
        destino = "backend.database (dev)"
    print(f"destino: {destino}")

    grupos_roster = cargar_rosters(args.rosters)
    total_roster = sum(len(v) for v in grupos_roster.values())
    print(f"roster: {total_roster} alumnos en {len(grupos_roster)} grupos (estab, curso)")

    with eng.connect() as c:
        dims = dict(c.execute(sa.text(
            "SELECT name, id_dimension FROM dimensions WHERE org_id=:o AND name IN "
            "('Establecimiento','Año','Hito','Asignatura','Curso','Nombre','Nombre_Norm')"),
            {"o": ORG}).fetchall())
        faltan = {'Establecimiento','Año','Hito','Asignatura','Curso','Nombre','Nombre_Norm'} - set(dims)
        if faltan:
            raise SystemExit(f"ERROR: faltan dimensiones {faltan}")
        print(f"dims: {dims}")
        dE, dC = str(dims['Establecimiento']), str(dims['Curso'])
        dN, dNN = str(dims['Nombre']), str(dims['Nombre_Norm'])

        cond_cohorte = " AND ".join(
            f"dimensions_json::jsonb ->> '{dims[k]}' = '{v}'" for k, v in COHORTE.items())
        filas = c.execute(sa.text(f"""
            SELECT id_data, dimensions_json, value FROM metric_data
            WHERE id_metric = {METRIC} AND org_id = {ORG} AND {cond_cohorte}
              AND NOT (dimensions_json::jsonb ? '{dN}')
              AND NOT (dimensions_json::jsonb ? '{dNN}')
            ORDER BY id_data
        """)).fetchall()
        print(f"filas huerfanas en el cohorte: {len(filas)}")

        grupos_db = defaultdict(list)
        for id_data, dj, val in filas:
            d = json.loads(dj)
            grupos_db[(d.get(dE), d.get(dC))].append(
                (id_data, d, json.loads(val).get("Logro")))

        # ---- verificacion total antes de tocar nada ----
        errores, plan = [], []
        for k, filas_db in sorted(grupos_db.items()):
            r = grupos_roster.get(k)
            if r is None:
                errores.append(f"grupo {k}: {len(filas_db)} filas en DB sin roster"); continue
            if len(r) != len(filas_db):
                errores.append(f"grupo {k}: DB={len(filas_db)} vs roster={len(r)}"); continue
            malos = sum(1 for (_, _, lg), rr in zip(filas_db, r)
                        if lg is None or rr["Logro_xls"] in ("", None)
                        or abs(float(lg) - float(rr["Logro_xls"])) > TOL)
            if malos:
                errores.append(f"grupo {k}: {malos}/{len(r)} checksums de Logro NO coinciden")
                continue
            plan.append((k, filas_db, r))
        sobra_roster = set(grupos_roster) - set(grupos_db)
        for k in sorted(sobra_roster):
            print(f"  aviso: grupo {k} del roster sin filas huerfanas en DB (quiza ya sano)")

        print(f"\ngrupos verificados OK: {len(plan)}   con error: {len(errores)}")
        for e in errores:
            print(f"  ERROR {e}")
        listas = sum(len(f) for _, f, _ in plan)
        print(f"filas listas para reparar (checksum 100%): {listas}")
        for k, f, _ in sorted(plan):
            print(f"   {k[0][:28]:<30} {k[1]:<16} {len(f):>4} filas")

        if errores:
            print("\nABORTADO: hay grupos que no verifican. No se escribio nada.")
            return 1
        if args.dry_run:
            print("\n--dry-run: verificacion completa, no se escribio nada.")
            return 0

        # ---- respaldo y aplicacion en una transaccion ----
        with open(args.backup, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["id_data", "dimensions_json_original"])
            for _, filas_db, _ in plan:
                for id_data, d, _ in filas_db:
                    w.writerow([id_data, json.dumps(d, ensure_ascii=False)])
        print(f"respaldo: {args.backup} ({listas} filas)")

    with eng.begin() as c:
        n = 0
        for _, filas_db, r in plan:
            for (id_data, d, _), rr in zip(filas_db, r):
                d2 = dict(d)
                d2[dN] = rr["Nombre_Estudiante"]
                d2[dNN] = rr["Nombre_Norm"]
                c.execute(sa.text("UPDATE metric_data SET dimensions_json=:j WHERE id_data=:i"),
                          {"j": json.dumps(d2, ensure_ascii=False), "i": id_data})
                n += 1
        print(f"actualizadas {n} filas (transaccion unica)")

    with eng.connect() as c:
        quedan = c.execute(sa.text(f"""
            SELECT count(*) FROM metric_data
            WHERE id_metric = {METRIC} AND org_id = {ORG} AND {cond_cohorte}
              AND NOT (dimensions_json::jsonb ? '{dN}')
        """)).scalar()
        print(f"filas del cohorte que siguen sin Nombre: {quedan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
