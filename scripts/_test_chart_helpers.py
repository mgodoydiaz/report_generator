"""Test directo de _chart_to_png_b64 y _table_section sin WeasyPrint."""
import sys, os, json, base64
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

os.environ['DATABASE_URL'] = 'postgresql://mgodoy:holapocompadre977@localhost:5432/rgenerator_dev'

from backend.database import SessionLocal
from backend.models import Indicator
from rgenerator.core.report_steps import _chart_to_png_b64, _table_section, _build_records, _resolve_field

db = SessionLocal()
out_dir = '/tmp/chart_smoke'
os.makedirs(out_dir, exist_ok=True)

for ind_id in [2, 4, 5]:
    ind = db.query(Indicator).filter(Indicator.id_indicator == ind_id).first()
    if not ind:
        print(f'  SKIP id={ind_id} (no existe)')
        continue
    print(f'\n== Indicator {ind_id} {ind.name} ==')

    column_roles = json.loads(ind.column_roles) if isinstance(ind.column_roles, str) else (ind.column_roles or {})
    print(f'  column_roles: {list(column_roles.keys())}')

    # Probar _resolve_field
    for f in ['_logro_1', '_logro_2', '_nivel_de_logro', '_curso', '_calidad_lectora']:
        resolved = _resolve_field(f, column_roles)
        if resolved != f:
            print(f'  {f} → {resolved}')

    pdf_layout = json.loads(ind.pdf_layout) if isinstance(ind.pdf_layout, str) else ind.pdf_layout
    sections = pdf_layout.get('sections', [])
    print(f'  pdf_layout sections: {len(sections)}')

    records = _build_records(db, ind, org_id=1)
    print(f'  records cargados: {len(records)}')
    if records:
        print(f'  sample keys: {sorted(list(records[0].keys()))[:12]}')

    # Renderizar cada chart/table
    for i, sec in enumerate(sections):
        t = sec.get('type')
        if t in ('chart', 'table'):
            item = sec.get('item', {})
            comp = item.get('component', '')
            heading = sec.get('heading', '')
            try:
                if t == 'chart':
                    b64 = _chart_to_png_b64(item, records, indicator=ind)
                    fname = f'{out_dir}/ind{ind_id}_sec{i}_{comp}.png'
                    with open(fname, 'wb') as f:
                        f.write(base64.b64decode(b64))
                    print(f'  [{i}] chart {comp:25s} "{heading}" → {os.path.basename(fname)} ({len(b64)//1024}KB b64)')
                else:
                    tdata = _table_section(item, records, indicator=ind)
                    print(f'  [{i}] table {comp:25s} "{heading}" → {len(tdata["columns"])} cols, {len(tdata["rows"])} rows')
                    if tdata['rows']:
                        print(f'      header: {tdata["columns"]}')
                        print(f'      row 0:  {tdata["rows"][0]}')
            except Exception as e:
                print(f'  [{i}] ERROR {comp}: {e}')

db.close()
print(f'\nPNGs en {out_dir}')
