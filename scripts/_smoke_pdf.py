"""Smoke test: importa report_steps y genera un PDF para indicator dado."""
import sys, os
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

# Forzar conexion a local
os.environ['DATABASE_URL'] = 'postgresql://mgodoy:holapocompadre977@localhost:5432/rgenerator_dev'

from backend.database import SessionLocal
from backend.models import Indicator
from rgenerator.core.report_steps import build_pdf_bytes

db = SessionLocal()
try:
    target_id = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    out = sys.argv[2] if len(sys.argv) > 2 else f'/tmp/informe_indicator_{target_id}.pdf'
    ind = db.query(Indicator).filter(Indicator.id_indicator == target_id).first()
    if not ind:
        print(f'No existe indicator id={target_id}'); sys.exit(1)
    print(f'Generando PDF para indicator id={target_id} "{ind.name}"...')
    pdf_bytes = build_pdf_bytes(ind, db, org_id=1)
    with open(out, 'wb') as f:
        f.write(pdf_bytes)
    size_kb = len(pdf_bytes) / 1024
    print(f'OK: {out} ({size_kb:.1f} KB)')
finally:
    db.close()
