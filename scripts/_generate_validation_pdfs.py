"""Genera los 6 PDFs de validación (SIMCE, DIA, IDEL × evaluacion+historico)
llamando directamente a build_pdf_bytes — sin pasar por endpoint ni auth.

Cálculo Veloz (id 4) y Fluidez Lectora (id 5) se omiten porque sus métricas
(9 y 10) no tienen metric_data cargados todavía.

Uso:
    python scripts/_generate_validation_pdfs.py [--indicators 1,2,3]
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
from backend.models import Indicator  # noqa: E402
from backend.rgenerator.core.report_steps import build_pdf_bytes  # noqa: E402


OUTPUT_DIR = ROOT / "data" / "output"


def _slug(s: str) -> str:
    return (s or "").lower().replace(" ", "_").replace("á", "a").replace("é", "e") \
        .replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n") \
        .replace("/", "-").strip()


def generate(indicator_id: int, tipo: str, db, org_id: int) -> tuple[Path, int] | None:
    """Devuelve (path, bytes) o None si no se pudo generar."""
    ind = db.query(Indicator).filter(
        Indicator.id_indicator == indicator_id,
        Indicator.org_id == org_id,
    ).first()
    if not ind:
        print(f"  ✗ indicator {indicator_id} no existe en org {org_id}")
        return None

    layout_str = ind.pdf_layout_historico if tipo == "historico" else ind.pdf_layout
    try:
        layout = json.loads(layout_str) if isinstance(layout_str, str) else (layout_str or {})
    except Exception:
        layout = {}

    if not layout.get("sections"):
        print(f"  ✗ {ind.name} ({tipo}): sin secciones — skip")
        return None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"validation_{_slug(ind.name)}_{tipo}.pdf"

    # Filtros por defecto para validación (cuando el indicator combina varios
    # subsets que no se filtran automáticamente). En el flujo real de la UI
    # el usuario aplica estos filtros desde el modal.
    # SIMCE indicator 1 mezcla LENGUAJE+MATEMATICAS — filtramos a Lenguaje.
    DEFAULT_FILTERS = {
        1: {"8": "LENGUAJE"},  # SIMCE: dim 8 = Asignatura
    }
    filters_default = DEFAULT_FILTERS.get(indicator_id)

    try:
        pdf_bytes = build_pdf_bytes(
            ind, db, org_id,
            filters=filters_default,
            branding_override=None,
            pdf_layout_override=layout,
        )
        out_path.write_bytes(pdf_bytes)
        size = out_path.stat().st_size
        print(f"  ✓ {ind.name} ({tipo}): {out_path.name} ({size:,} bytes, {len(layout['sections'])} secs)")
        return out_path, size
    except Exception as e:
        print(f"  ✗ {ind.name} ({tipo}): ERROR — {type(e).__name__}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--indicators", default="1,2,3",
                        help="comma-separated indicator IDs (default: 1,2,3 — los que tienen datos)")
    parser.add_argument("--org-id", type=int, default=1)
    args = parser.parse_args()

    ind_ids = [int(x.strip()) for x in args.indicators.split(",") if x.strip()]
    print(f"Generando PDFs para indicators {ind_ids} × [evaluacion, historico]...\n")

    db = SessionLocal()
    results = []
    try:
        for iid in ind_ids:
            for tipo in ("evaluacion", "historico"):
                r = generate(iid, tipo, db, args.org_id)
                if r:
                    results.append(r)
        db.close()
    except Exception:
        db.rollback()
        raise

    print(f"\n✅ Generados {len(results)} PDFs en {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
