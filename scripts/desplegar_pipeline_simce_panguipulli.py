# -*- coding: utf-8 -*-
"""
desplegar_pipeline_simce_panguipulli.py
=======================================
Crea en PRODUCCION el pipeline de SIMCE Panguipulli (Aptus) y sus 2 specs ETL.

Contexto (verificado 2026-08-05): produccion **nunca tuvo** este pipeline. Si
tiene los datos ya cargados (metricas 17 y 18, con 1695 y 180 filas) y el
indicador 8, pero la carga se hizo por otra via. Los IDs no coinciden con dev:

    dev                          produccion
    -------------------------    ---------------------------
    metrica 24 Estudiante   ->    metrica 17
    metrica 26 Habilidad    ->    metrica 18
    spec 49 / spec 51       ->    se crean nuevos (ids que asigne prod)
    indicador 6             ->    indicador 8

Por eso NO sirve copiar el config tal cual: hay que **remapear** los `spec_id` y
`metric_id`. Este script lo hace resolviendo las metricas **por nombre**, no por
id, que es lo unico estable entre ambos entornos.

Entrada: un paquete exportado de dev con los 2 specs y el pipeline.

    docker exec report_generator-db-1 psql -U mgodoy -d rgenerator_dev -t -A -c "
      SELECT json_build_object(
        'specs', (SELECT json_agg(json_build_object('id_spec',id_spec,'name',name,'type',type,
                  'metadata',metadata) ORDER BY id_spec) FROM specs WHERE id_spec IN (49,51)),
        'pipeline', (SELECT json_build_object('pipeline',pipeline,'description',description,
                     'config_json',config_json) FROM pipelines WHERE pipeline_id=26 AND org_id=1)
      )::text;" > paquete_dev.json

Uso:
    python scripts/desplegar_pipeline_simce_panguipulli.py --paquete paquete_dev.json --dry-run
    python scripts/desplegar_pipeline_simce_panguipulli.py --paquete paquete_dev.json

Idempotente: si los specs o el pipeline ya existen (por nombre y org), los
reutiliza o actualiza en vez de duplicarlos.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import sqlalchemy as sa

ORG = 1

# metrica de dev -> nombre canonico. En prod se resuelve por ese nombre.
METRICAS = {
    24: "Resultados SIMCE Panguipulli por Estudiante",
    26: "Resultados SIMCE Panguipulli por Habilidad",
}

# columnas que el pipeline deja en el DataFrame de cada grupo, para chequear
# que cubran lo que la metrica de produccion espera
COLUMNAS = {
    "Resultados SIMCE Panguipulli por Estudiante": {
        "Establecimiento", "Año", "Mes", "N Prueba", "Asignatura", "Nivel", "Curso",
        "RUT", "Nombre", "PorcLogro", "LogroNormalizado"},
    "Resultados SIMCE Panguipulli por Habilidad": {
        "Establecimiento", "Año", "Mes", "N Prueba", "Asignatura", "Nivel", "Curso",
        "Habilidad", "LogroCurso", "LogroHabilidad"},
}


def url_destino(env_file: str | None) -> str:
    from dotenv import dotenv_values
    import os
    if env_file:
        u = dotenv_values(env_file).get("DATABASE_URL", "")
        if u:
            return u
    u = os.getenv("DATABASE_URL", "")
    if not u:
        raise SystemExit("ERROR: no hay DATABASE_URL (ni --env-file ni variable de entorno)")
    return u


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paquete", type=Path, required=True)
    ap.add_argument("--env-file", default=".env.railway",
                    help="archivo con DATABASE_URL de destino (default .env.railway)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    paquete = json.loads(args.paquete.read_text(encoding="utf-8"))
    specs_dev = paquete["specs"]
    pipe_dev = paquete["pipeline"]
    cfg = json.loads(pipe_dev["config_json"])

    url = url_destino(args.env_file)
    print(f"destino: {url.split('@')[-1].split('/')[0]}")
    eng = sa.create_engine(url, connect_args={"connect_timeout": 30})

    with eng.begin() as c:
        # ---------- 1. resolver metricas por NOMBRE ----------
        mapa_metricas: dict[int, int] = {}
        for dev_id, nombre in METRICAS.items():
            filas = c.execute(sa.text(
                "SELECT id_metric FROM metrics WHERE name=:n AND org_id=:o"),
                {"n": nombre, "o": ORG}).fetchall()
            if len(filas) != 1:
                raise SystemExit(f"ERROR: en prod hay {len(filas)} metricas llamadas '{nombre}'. "
                                 "Se esperaba exactamente 1.")
            mapa_metricas[dev_id] = filas[0][0]
            # las dimensiones/fields de prod deben estar cubiertas por lo que produce el pipeline
            dims = [r[0] for r in c.execute(sa.text(
                "SELECT d.name FROM metric_dimensions md JOIN dimensions d "
                "ON d.id_dimension=md.id_dimension WHERE md.id_metric=:i"),
                {"i": filas[0][0]})]
            meta = c.execute(sa.text("SELECT meta_json FROM metrics WHERE id_metric=:i"),
                             {"i": filas[0][0]}).scalar()
            fields = [f["name"] for f in json.loads(meta or "{}").get("fields", [])]
            faltan = (set(dims) | set(fields)) - COLUMNAS[nombre]
            if faltan:
                raise SystemExit(f"ERROR: la metrica '{nombre}' de prod espera columnas que el "
                                 f"pipeline no produce: {sorted(faltan)}")
            print(f"  metrica dev {dev_id} -> prod {filas[0][0]}  '{nombre}'  "
                  f"({len(dims)} dims + {len(fields)} fields, todas cubiertas)")

        # ---------- 2. specs ----------
        mapa_specs: dict[int, int] = {}
        for s in specs_dev:
            existente = c.execute(sa.text(
                "SELECT id_spec FROM specs WHERE name=:n AND org_id=:o"),
                {"n": s["name"], "o": ORG}).fetchone()
            if existente:
                mapa_specs[s["id_spec"]] = existente[0]
                accion = f"ya existe -> id {existente[0]} (se actualiza metadata)"
                if not args.dry_run:
                    c.execute(sa.text("UPDATE specs SET metadata=:m, type=:t WHERE id_spec=:i"),
                              {"m": s["metadata"], "t": s.get("type"), "i": existente[0]})
            else:
                if args.dry_run:
                    mapa_specs[s["id_spec"]] = -1
                    accion = "se crea (id nuevo)"
                else:
                    nuevo = c.execute(sa.text(
                        "INSERT INTO specs (name, type, metadata, org_id) "
                        "VALUES (:n,:t,:m,:o) RETURNING id_spec"),
                        {"n": s["name"], "t": s.get("type"), "m": s["metadata"], "o": ORG}).scalar()
                    mapa_specs[s["id_spec"]] = nuevo
                    accion = f"creado -> id {nuevo}"
            print(f"  spec dev {s['id_spec']} '{s['name']}': {accion}")

        # ---------- 3. remapear el config ----------
        for step in cfg["pipeline"]:
            p = step.get("params", {}) or {}
            if step["step"] == "LoadConfigFromSpec" and "spec_id" in p:
                p["spec_id"] = mapa_specs[p["spec_id"]]
            elif step["step"] == "SaveToMetric" and "metric_id" in p:
                p["metric_id"] = mapa_metricas[p["metric_id"]]

        # ---------- 4. verificar ----------
        pasos = cfg["pipeline"]
        nombres = [s["step"] for s in pasos]
        assert len(pasos) == 13, f"se esperaban 13 pasos, hay {len(pasos)}"
        assert nombres.count("RequestUserFiles") == 2, "deben ser 2 pausas"
        assert nombres.count("SaveToMetric") == 2, "deben ser 2 SaveToMetric"
        destinos = sorted(s["params"]["metric_id"] for s in pasos if s["step"] == "SaveToMetric")
        assert destinos == sorted(mapa_metricas.values()), f"metricas destino: {destinos}"
        if not args.dry_run:
            assert all(v > 0 for v in mapa_specs.values()), "quedo un spec_id sin resolver"
            for s in pasos:
                if s["step"] == "LoadConfigFromSpec":
                    assert s["params"]["spec_id"] in mapa_specs.values(), "spec_id sin remapear"

        print(f"\n  pipeline '{pipe_dev['pipeline']}' — {len(pasos)} pasos")
        for i, s in enumerate(pasos, 1):
            p = s.get("params", {}) or {}
            det = ""
            if s["step"] == "LoadConfigFromSpec": det = f"spec {p.get('spec_id')}"
            elif s["step"] == "RequestUserFiles": det = p["file_specs"][0]["label"]
            elif s["step"] == "SaveToMetric":     det = f"-> metrica {p.get('metric_id')}"
            print(f"   {i:2d}. {s['step']:20s} {det}")

        # ---------- 5. escribir el pipeline ----------
        ya = c.execute(sa.text("SELECT pipeline_id FROM pipelines WHERE pipeline=:n AND org_id=:o"),
                       {"n": pipe_dev["pipeline"], "o": ORG}).fetchone()
        cfg_txt = json.dumps(cfg, ensure_ascii=False, indent=2)
        if args.dry_run:
            print(f"\n  pipeline: " + (f"ya existe (id {ya[0]}) -> se actualizaria" if ya else "se crearia"))
            print("\n--dry-run: no se escribio nada (la transaccion se revierte).")
            raise SystemExit(0)

        if ya:
            c.execute(sa.text("UPDATE pipelines SET config_json=:c, description=:d WHERE pipeline_id=:i"),
                      {"c": cfg_txt, "d": pipe_dev["description"], "i": ya[0]})
            print(f"\n  pipeline actualizado (id {ya[0]})")
        else:
            nuevo = c.execute(sa.text(
                "INSERT INTO pipelines (pipeline, description, config_json, hidden, org_id) "
                "VALUES (:n,:d,:c,false,:o) RETURNING pipeline_id"),
                {"n": pipe_dev["pipeline"], "d": pipe_dev["description"],
                 "c": cfg_txt, "o": ORG}).scalar()
            print(f"\n  pipeline creado (id {nuevo})")

    with eng.connect() as c:
        print("\n=== estado final en prod ===")
        for r in c.execute(sa.text("SELECT pipeline_id, pipeline FROM pipelines WHERE org_id=:o ORDER BY pipeline_id"), {"o": ORG}):
            print(f"   {r[0]:>3} | {r[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
