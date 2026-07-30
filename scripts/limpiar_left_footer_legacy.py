"""Vaciar `branding.left_footer` legacy en los layouts PDF persistidos.

QA visual 2026-07-30 (P1-1): los 12 informes por período salían con el pie
izquierdo "Miguel Godoy Díaz" — el nombre del desarrollador, no el de la
fundación. La causa no era el código sino los layouts guardados en la DB:
`indicators.pdf_layout` y `indicators.pdf_layout_historico` traían el
nombre hardcodeado, y el fallback al nombre de la organización solo actúa
cuando el pie viene VACÍO.

El runtime ya está blindado (`reports/branding.pie_saneado` degrada estos
valores a "" en los dos motores), así que este script es la limpieza de los
datos: deja el campo en "" para que la fuente de verdad sea la org.

Recorre TODAS las organizaciones. Idempotente.

Ejecutar (dev — la DB canónica es la del compose, nunca localhost:5432):
    docker compose -f docker-compose.dev.yml exec -T backend \
        python scripts/_oneshot/_limpiar_left_footer_legacy.py

    # solo mostrar lo que cambiaría
    ... python scripts/_oneshot/_limpiar_left_footer_legacy.py --dry-run

Verificar después:
    docker compose -f docker-compose.dev.yml exec -T db \
        psql -U mgodoy -d rgenerator_dev -c "select count(*) from indicators \
        where pdf_layout ilike '%godoy%' or pdf_layout_historico ilike '%godoy%';"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ejecutable tanto dentro del contenedor (/app) como desde el repo local.
_RAIZ = Path(__file__).resolve().parents[2]
for _p in ("/app", str(_RAIZ)):
    if _p not in sys.path and Path(_p).exists():
        sys.path.insert(0, _p)

from backend.database import SessionLocal                      # noqa: E402
from backend.models import Indicator, Organization             # noqa: E402
from backend.rgenerator.reports.branding import (              # noqa: E402
    LEFT_FOOTER_DENYLIST,
    es_pie_denegado,
)

CAMPOS = ("pdf_layout", "pdf_layout_historico")


def _como_dict(valor) -> dict | None:
    """Parsea el campo JSON del layout. None si no es un objeto usable."""
    if valor is None:
        return None
    if isinstance(valor, dict):
        return valor
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return None
        try:
            parsed = json.loads(texto)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="solo listar las filas afectadas, sin escribir",
    )
    args = parser.parse_args()

    db = SessionLocal()
    afectadas: list[tuple[int, str, str, str]] = []
    try:
        orgs = {o.id: o.name for o in db.query(Organization).all()}
        indicadores = db.query(Indicator).order_by(Indicator.id_indicator).all()
        print(f"Denylist: {', '.join(LEFT_FOOTER_DENYLIST)}")
        print(f"Revisando {len(indicadores)} indicadores de {len(orgs)} organizaciones…\n")

        for ind in indicadores:
            for campo in CAMPOS:
                layout = _como_dict(getattr(ind, campo, None))
                if not layout:
                    continue
                branding = layout.get("branding")
                if not isinstance(branding, dict):
                    continue
                pie = branding.get("left_footer")
                if not es_pie_denegado(pie):
                    continue

                afectadas.append((
                    ind.id_indicator,
                    orgs.get(ind.org_id, f"org {ind.org_id}"),
                    campo,
                    str(pie),
                ))
                if not args.dry_run:
                    branding["left_footer"] = ""
                    setattr(ind, campo, json.dumps(layout, ensure_ascii=False))

        if not afectadas:
            print("Nada por limpiar: ningún layout trae un pie de la denylist.")
            return 0

        ancho = max(len(f) for _, _, f, _ in afectadas)
        print(f"{'id':>4}  {'organización':<24}  {'campo':<{ancho}}  pie encontrado")
        print("-" * (34 + ancho + 20))
        for id_ind, org, campo, pie in afectadas:
            print(f"{id_ind:>4}  {org:<24}  {campo:<{ancho}}  {pie!r}")

        if args.dry_run:
            print(f"\n[dry-run] {len(afectadas)} filas quedarían en \"\". Sin escribir.")
            return 0

        db.commit()
        print(f"\n{len(afectadas)} filas actualizadas (left_footer = \"\").")
        print("El pie ahora lo resuelve el runtime con el nombre de la organización.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
