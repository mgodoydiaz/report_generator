"""
fix_layout_historico_fl.py — Repara el alias `_evaluacion` en los layouts PDF
del indicador Fluidez Lectora.

Por qué
-------
El layout histórico de Fluidez Lectora declaraba el eje temporal como
`"_evaluacion"`:

    {"component": "GroupedBarByPeriod", "valueField": "_logro_1",
     "groupField": "_curso", "periodField": "_evaluacion"}
    {"component": "StackedCountByGroup", "groupField": "_evaluacion",
     "levelField": "_nivel_de_logro"}

`_evaluacion` NO es un rol conocido (`_KNOWN_ROLES` en
`backend/rgenerator/core/report_steps.py` declara `evaluacion_num`, no
`evaluacion`) ni una columna real de la métrica. `_resolve_field` devuelve el
alias tal cual, ningún record trae la clave `_evaluacion`, el eje X queda sin
categorías y el gráfico sale COMPLETAMENTE en blanco (ejes -0.04..0.04, la
leyenda con los cursos pero sin barras).

El alias correcto es `"_evaluacion_num"`, que `_resolve_field` traduce a la
primera columna del rol temporal del indicador (en Fluidez Lectora,
"N Prueba"). Es el mismo alias que ya usa el layout de evaluación.

El bug nunca se vio porque las cards semestral/anual de Fluidez Lectora
estaban no-disponibles hasta que se agregó el tipo de dimensión fecha; el
layout histórico jamás se ejercitó. El mismo layout roto vino del seed
`scripts/_seed_validation_layouts.py`, así que es muy probable que exista
igual en producción.

Qué hace
--------
Busca los indicadores de Fluidez Lectora POR NOMBRE (contiene "fluidez", sin
tildes ni mayúsculas) o por `report_engine_type`, NO por id — el id cambia
entre entornos. En `pdf_layout` y `pdf_layout_historico` reemplaza cada string
exactamente igual a `"_evaluacion"` por `"_evaluacion_num"`, en cualquier
profundidad del JSON.

Idempotente: correrlo dos veces no cambia nada la segunda vez (después del
reemplazo ya no queda ningún `"_evaluacion"`).

Salvaguarda: si el indicador NO declara el rol `evaluacion_num` en
`column_roles`, se salta — `_evaluacion_num` tampoco resolvería a una columna
real y el gráfico seguiría vacío. Ese caso hay que arreglarlo configurando el
rol temporal, no acá.

Uso (dentro del contenedor backend o con DATABASE_URL apuntando a la DB)
-----------------------------------------------------------------------
    python scripts/fix_layout_historico_fl.py                  # dry-run, todas las orgs
    python scripts/fix_layout_historico_fl.py --org 1          # dry-run, solo org 1
    python scripts/fix_layout_historico_fl.py --org 1 --apply  # escribe
"""

import argparse
import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.models import Indicator

# Alias roto → alias correcto. `_evaluacion` no es un rol de `_KNOWN_ROLES`;
# `_evaluacion_num` sí, y resuelve a la primera columna del rol temporal.
ALIAS_ROTO = "_evaluacion"
ALIAS_CORRECTO = "_evaluacion_num"

# Rol temporal que debe existir para que el alias corregido resuelva.
ROL_TEMPORAL = "evaluacion_num"

# Campos de `indicators` que guardan un layout PDF.
CAMPOS_LAYOUT = ("pdf_layout", "pdf_layout_historico")

# Marcas para reconocer el indicador sin depender del id.
MARCA_NOMBRE = "fluidez"
MARCAS_ENGINE = ("fluidez", "fluidez_lectora", "fl")


def _sin_tildes(texto) -> str:
    """'Fluidez Lectora' → 'fluidez lectora' (sin tildes, para comparar)."""
    s = unicodedata.normalize("NFKD", str(texto or ""))
    return s.encode("ascii", "ignore").decode("ascii").strip().lower()


def es_fluidez_lectora(indicador) -> bool:
    """El indicador es de Fluidez Lectora, por nombre o por engine."""
    if MARCA_NOMBRE in _sin_tildes(indicador.name):
        return True
    return _sin_tildes(indicador.report_engine_type) in MARCAS_ENGINE


def _parse_layout(raw):
    """El layout es Text: puede venir None, vacío o malformado."""
    if not raw:
        return None
    if isinstance(raw, dict):
        return dict(raw)
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _reemplazar(nodo, contador):
    """Devuelve `nodo` con cada `_evaluacion` cambiado por `_evaluacion_num`.

    Recorre dicts y listas a cualquier profundidad. Solo toca strings que sean
    EXACTAMENTE el alias roto: no hace reemplazo de subcadenas, para no romper
    `_evaluacion_num` (que ya contiene el alias) ni textos libres.

    `contador` es una lista de un elemento usada como acumulador de cambios.
    """
    if isinstance(nodo, dict):
        return {k: _reemplazar(v, contador) for k, v in nodo.items()}
    if isinstance(nodo, list):
        return [_reemplazar(v, contador) for v in nodo]
    if isinstance(nodo, str) and nodo == ALIAS_ROTO:
        contador[0] += 1
        return ALIAS_CORRECTO
    return nodo


def corregir_layout(layout):
    """`(layout_corregido, n_reemplazos)` — no muta el original."""
    contador = [0]
    corregido = _reemplazar(layout, contador)
    return corregido, contador[0]


def _tiene_rol_temporal(indicador) -> bool:
    """`column_roles` declara `evaluacion_num` con al menos una columna."""
    roles = _parse_layout(indicador.column_roles) or {}
    entries = roles.get(ROL_TEMPORAL)
    if not isinstance(entries, list) or not entries:
        return False
    return any(isinstance(e, dict) and e.get("column") for e in entries)


def analizar(db, org_id=None):
    """[{...}] con los indicadores de Fluidez Lectora y sus reemplazos.

    Args:
        db: sesión SQLAlchemy.
        org_id: si viene, restringe a esa organización; si no, todas.
    """
    query = db.query(Indicator)
    if org_id is not None:
        query = query.filter(Indicator.org_id == org_id)

    hallazgos = []
    for ind in query.order_by(Indicator.org_id, Indicator.id_indicator).all():
        if not es_fluidez_lectora(ind):
            continue

        cambios = {}
        for campo in CAMPOS_LAYOUT:
            layout = _parse_layout(getattr(ind, campo, None))
            if layout is None:
                continue
            corregido, n = corregir_layout(layout)
            if n:
                cambios[campo] = (corregido, n)

        hallazgos.append({
            "id_indicator": ind.id_indicator,
            "org_id": ind.org_id,
            "name": ind.name,
            "tiene_rol_temporal": _tiene_rol_temporal(ind),
            "cambios": cambios,
            "total": sum(n for _, n in cambios.values()),
        })
    return hallazgos


def corregir(db, org_id=None, aplicar=False):
    """Detecta (y opcionalmente escribe) la corrección del alias.

    Returns:
        {"hallazgos": [...], "corregidos": int, "reemplazos": int} —
        contadores de lo que cambiaría (dry-run) o cambió (apply).
    """
    hallazgos = analizar(db, org_id)
    pendientes = [h for h in hallazgos if h["total"] and h["tiene_rol_temporal"]]

    if aplicar and pendientes:
        for h in pendientes:
            record = db.query(Indicator).filter(
                Indicator.id_indicator == h["id_indicator"],
                Indicator.org_id == h["org_id"],
            ).first()
            if not record:
                continue
            for campo, (corregido, _n) in h["cambios"].items():
                setattr(record, campo, json.dumps(corregido, ensure_ascii=False))
            record.updated_at = datetime.utcnow()
        db.commit()

    return {
        "hallazgos": hallazgos,
        "corregidos": len(pendientes),
        "reemplazos": sum(h["total"] for h in pendientes),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Repara el alias '_evaluacion' en los layouts PDF de Fluidez Lectora."
    )
    parser.add_argument("--org", type=int, default=None,
                        help="id de la organización (default: todas)")
    parser.add_argument("--apply", action="store_true",
                        help="escribe los cambios (por defecto: dry-run)")
    args = parser.parse_args()

    ambito = f"org {args.org}" if args.org is not None else "todas las orgs"

    db = SessionLocal()
    try:
        resumen = corregir(db, org_id=args.org, aplicar=args.apply)
        hallazgos = resumen["hallazgos"]

        if not hallazgos:
            print(f"[{ambito}] No hay indicadores de Fluidez Lectora.")
            return

        print(f"[{ambito}] Indicadores de Fluidez Lectora:")
        for h in hallazgos:
            cab = (f"  #{h['id_indicator']:>4} org {h['org_id']:<3} "
                   f"{h['name']:<24}")
            if not h["total"]:
                print(f"{cab} sin '{ALIAS_ROTO}' — nada que hacer")
                continue
            if not h["tiene_rol_temporal"]:
                print(f"{cab} SALTADO: no declara el rol '{ROL_TEMPORAL}' "
                      f"({h['total']} ocurrencia(s) de '{ALIAS_ROTO}')")
                continue
            detalle = ", ".join(f"{campo}: {n}" for campo, (_, n) in h["cambios"].items())
            print(f"{cab} {ALIAS_ROTO} → {ALIAS_CORRECTO} [{detalle}]")

        if args.apply:
            print(f"\nOK — {resumen['corregidos']} indicador(es) corregido(s), "
                  f"{resumen['reemplazos']} reemplazo(s).")
        else:
            print(f"\nDRY-RUN — {resumen['corregidos']} indicador(es) se corregirían "
                  f"({resumen['reemplazos']} reemplazo(s)). "
                  f"Repite con --apply para escribir.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
