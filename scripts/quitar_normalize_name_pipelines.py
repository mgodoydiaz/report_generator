# -*- coding: utf-8 -*-
"""
quitar_normalize_name_pipelines.py
==================================
Retira el kind deprecado `normalize_name` de los pipelines VIVOS de una
organización (tabla `pipelines`, columna `config_json`) — los JSON del repo
son solo plantillas; lo que ejecuta la app vive en la DB.

Contexto (retiro de `Nombre_Norm`, 2026-08-07): el nombre reordenado
("PEREZ JUAN SOTO") no debe persistirse ni mostrarse. `Nombre` queda como
única fuente de verdad visible y la clave de agrupación se normaliza AL
VUELO con el parámetro `entity_normalize` de agg/slope/delta.

Transformación, por cada `ApplyDerivedFields` con un derived field
`normalize_name` (name=N, value_field=VF):

  1. Se elimina el derived field `normalize_name`.
  2. En su lugar se inserta un kind `copy` que produce la columna ORIGINAL
     (N sin el sufijo `_Norm`, típicamente `Nombre`) desde VF — el texto
     tal cual del archivo. Antes esa copia era un efecto secundario de
     `apply_normalize_name`; sin ella el pipeline dejaría de poblar la
     dimensión `Nombre`.
  3. Los derived fields del mismo paso cuyo `entity_field` referencie N
     pasan a usar la columna original con `entity_normalize: [original]`,
     y se les agrega "Año" al `entity_field` si no lo traían — fix
     deliberado de la fuga de cohortes 2025→2026 documentada en
     `docs/reportes/qa_informes_2026-08-03/dia.md` (P1-1). El Año llega al
     DataFrame vía `EnrichWithUserInput` + RunExcelETL/RunDIAPDFExtraction
     (ver `scripts/dia_ano_por_usuario.py`).

Idempotente, org-scoped y con dry-run por defecto (patrón de
`scripts/dia_ano_por_usuario.py`).

Uso:
    python scripts/quitar_normalize_name_pipelines.py --org 1           # dry-run
    python scripts/quitar_normalize_name_pipelines.py --org 1 --apply
"""
from __future__ import annotations

import argparse
import json

#: Sufijos de la convención deprecada (misma tupla que usa SaveToMetric).
SUFIJOS_NORM = ("_Norm", "_norm", "_NORM")

#: Columna de cohorte que se agrega a los entity_field afectados.
CAMPO_ANIO = "Año"


def _columna_original(name: str) -> str:
    """'Nombre_Norm' → 'Nombre'. Si no hay sufijo, devuelve el mismo nombre."""
    for sufijo in SUFIJOS_NORM:
        if name.endswith(sufijo) and len(name) > len(sufijo):
            return name[: -len(sufijo)]
    return name


def transformar_config(cfg: dict) -> tuple[dict, list[str]]:
    """Aplica la transformación al config_json de UN pipeline.

    Devuelve (cfg, notas). Si notas está vacía, el pipeline no usaba
    normalize_name y no se toca.
    """
    notas: list[str] = []
    for paso in cfg.get("pipeline", []):
        if paso.get("step") != "ApplyDerivedFields":
            continue
        params = paso.get("params") or {}
        derived = params.get("derived_fields") or []
        norm_fields = [d for d in derived if d.get("kind") == "normalize_name"]
        if not norm_fields:
            continue

        nuevos: list[dict] = []
        renombres: dict[str, str] = {}  # N (normalizado) → columna original
        for d in derived:
            if d.get("kind") != "normalize_name":
                nuevos.append(d)
                continue
            n, vf = d.get("name", ""), d.get("value_field", "")
            original = _columna_original(n)
            renombres[n] = original
            ya_copiado = any(
                x.get("kind") == "copy" and x.get("name") == original
                for x in nuevos
            )
            if not ya_copiado:
                nuevos.append({"kind": "copy", "name": original, "value_field": vf})
                notas.append(
                    f"normalize_name '{n}' → copy '{original}' <- '{vf}' "
                    f"(texto original, sin reordenar)"
                )
            else:
                notas.append(f"normalize_name '{n}' eliminado (copy ya existía)")

        # Reapuntar los entity_field que usaban la clave normalizada.
        for d in nuevos:
            ef = d.get("entity_field")
            if ef is None:
                continue
            campos = [ef] if isinstance(ef, str) else list(ef)
            if not any(c in renombres for c in campos):
                continue
            campos = [renombres.get(c, c) for c in campos]
            normalizar = sorted({renombres[c] for c in ([ef] if isinstance(ef, str) else ef)
                                 if c in renombres})
            if CAMPO_ANIO not in campos:
                campos.insert(0, CAMPO_ANIO)
                notas.append(
                    f"{d.get('kind')} '{d.get('name')}': se agrega '{CAMPO_ANIO}' al "
                    f"entity_field (separa cohortes 2025/2026)"
                )
            d["entity_field"] = campos
            existentes = d.get("entity_normalize") or []
            d["entity_normalize"] = sorted(set(existentes) | set(normalizar))
            notas.append(
                f"{d.get('kind')} '{d.get('name')}': entity_field {campos} "
                f"con entity_normalize {d['entity_normalize']}"
            )

        params["derived_fields"] = nuevos

        desc = paso.get("description")
        if isinstance(desc, str) and "Nombre_Norm" in desc:
            paso["description"] = desc.replace(
                "Nombre_Norm", "columna Nombre (copia del texto original)"
            )
            notas.append("description del paso actualizada")

    return cfg, notas


def verificar(cfg: dict) -> None:
    """Invariantes tras la transformación. Lanza AssertionError si algo quedó mal."""
    for paso in cfg.get("pipeline", []):
        if paso.get("step") != "ApplyDerivedFields":
            continue
        derived = (paso.get("params") or {}).get("derived_fields") or []
        for d in derived:
            assert d.get("kind") != "normalize_name", \
                f"quedó un normalize_name: {d.get('name')}"
            ef = d.get("entity_field")
            campos = [ef] if isinstance(ef, str) else list(ef or [])
            con_sufijo = [c for c in campos if isinstance(c, str)
                          and any(c.endswith(s) and len(c) > len(s) for s in SUFIJOS_NORM)]
            assert not con_sufijo, \
                f"{d.get('kind')} '{d.get('name')}' sigue agrupando por {con_sufijo}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--org", type=int, default=1, help="org_id (default 1)")
    ap.add_argument("--apply", action="store_true",
                    help="escribe los cambios (sin esto es dry-run)")
    args = ap.parse_args()

    from backend.database import SessionLocal
    from backend.models import Pipeline

    db = SessionLocal()
    try:
        pipelines = db.query(Pipeline).filter(Pipeline.org_id == args.org).all()
        print(f"Org {args.org}: {len(pipelines)} pipelines en la tabla.\n")

        cambiados = 0
        for p in pipelines:
            try:
                cfg = json.loads(p.config_json)
            except (TypeError, ValueError):
                print(f"· pipeline {p.pipeline_id} '{p.pipeline}': config_json ilegible, se salta")
                continue
            cfg, notas = transformar_config(cfg)
            if not notas:
                continue
            verificar(cfg)
            cambiados += 1
            print(f"· pipeline {p.pipeline_id} '{p.pipeline}':")
            for n in notas:
                print(f"    - {n}")
            if args.apply:
                p.config_json = json.dumps(cfg, ensure_ascii=False, indent=2)

        if cambiados == 0:
            print("Ningún pipeline usa normalize_name: nada que hacer.")
            return 0

        if args.apply:
            db.commit()
            print(f"\nAplicado: {cambiados} pipeline(s) actualizados.")
        else:
            print(f"\n--dry-run (default): {cambiados} pipeline(s) cambiarían. "
                  f"Repetir con --apply para escribir.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
