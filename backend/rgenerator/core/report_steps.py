"""Steps de generación de reportes: gráficos, tablas, PDF y DOCX."""

# Librerias estandar
from pathlib import Path
import os
import shutil
import json
import pandas as pd
from typing import Optional, Dict, List

# Importaciones internas de RGenerator
from .step import Step
from rgenerator.tooling import plot_tools, report_tools
from rgenerator.tooling.report_docx_tools import render_docx_report
from backend.config import REPORTS_TEMPLATES_DIR
from rgenerator.tooling.constants import formato_informe_generico, indice_alfabetico


class GenerateGraphics(Step):
    """
    Genera gráficos utilizando herramientas de matplotlib definidas en plot_tools.

    Lee el esquema de gráficos desde ctx.params["charts_schema"] (cargado por un step
    previo como LoadConfigFromSpec) o directamente desde el constructor.

    Cada entrada del esquema tiene:
        - type: nombre de la función en plot_tools (ej: "grafico_barras_promedio_por")
        - input_key: clave del DataFrame en ctx.artifacts
        - output_filename: nombre del archivo de salida (ej: "logro_por_curso.png")
        - params: kwargs adicionales para la función

    Efectos:
        - Crea archivos .png en ctx.aux_dir.
        - Registra rutas generadas en ctx.artifacts["generated_charts"].
    """
    def __init__(self, charts_schema: Optional[List[Dict]] = None):
        """Inicializa el step, opcionalmente con esquema directo."""
        super().__init__(name="GenerateGraphics")
        self.charts_schema = charts_schema

    def run(self, ctx):
        """Genera los gráficos solicitados y registra las rutas en ctx.artifacts."""
        before = self._snapshot_artifacts(ctx)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__

        # 1. Resolver esquema: constructor directo, nuevo formato (charts_list) o legacy (charts_schema)
        schema = self.charts_schema
        if not schema:
            schema = ctx.params.get("charts_list") or ctx.params.get("charts_schema", [])

        if not schema:
            self._log(f"[{self.name}] Advertencia: No se encontraron definiciones de gráficos.")
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 2. Resolver directorio auxiliar
        aux_dir = getattr(ctx, "aux_dir", None)
        if not aux_dir:
            if hasattr(ctx, "base_dir"):
                aux_dir = ctx.base_dir / "aux_files"
            else:
                aux_dir = Path("aux_files")
            ctx.aux_dir = aux_dir

        if not aux_dir.exists():
            aux_dir.mkdir(parents=True, exist_ok=True)

        # 3. Iterar sobre el esquema y generar gráficos
        generated_charts = {}
        charts_generated = 0

        for chart_def in schema:
            chart_type = chart_def.get("type")
            input_key = chart_def.get("input_key")
            output_filename = chart_def.get("output_filename")
            params = chart_def.get("params", {})

            # Validar definición mínima
            if not chart_type or not input_key or not output_filename:
                self._log(f"[{self.name}] Error: Definición incompleta: {chart_def}")
                continue

            # Obtener la función desde plot_tools
            func = getattr(plot_tools, chart_type, None)
            if not func:
                self._log(f"[{self.name}] Error: La función '{chart_type}' no existe en plot_tools.")
                continue

            # Obtener el DataFrame desde artifacts (input_key puede ser string o list[string])
            if isinstance(input_key, list):
                keys = input_key
            else:
                keys = [input_key]

            dfs = [ctx.artifacts.get(k) for k in keys]
            missing = [k for k, d in zip(keys, dfs) if d is None]
            if missing:
                self._log(f"[{self.name}] Error: Artifacts no encontrados: {missing}")
                continue

            df = dfs[0]
            extra_dfs = {k: d for k, d in zip(keys[1:], dfs[1:])}

            # Preparar argumentos
            output_path = aux_dir / output_filename
            kwargs = params.copy()
            kwargs["nombre_grafico"] = str(output_path)
            kwargs.update(extra_dfs)

            try:
                func(df, **kwargs)
                generated_charts[output_filename] = output_path
                charts_generated += 1
            except Exception as e:
                self._log(f"[{self.name}] Error al generar gráfico '{output_filename}': {e}")

        # 4. Registrar rutas generadas en el contexto
        ctx.artifacts["generated_charts"] = generated_charts
        self._log(f"[{self.name}] {charts_generated}/{len(schema)} gráficos generados en {aux_dir}")

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)


# ── Helpers compartidos para RenderPDFReport ─────────────────────────────────

def _to_field_name(name: str) -> str:
    import re
    s = name.strip().lower()
    s = re.sub(r'[^a-z0-9_]', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return f'_{s}'


def _build_records(db, indicator, org_id: int) -> list[dict]:
    """Construye lista plana de registros desde MetricData para un indicador."""
    from backend.models import IndicatorMetric, Metric, MetricDimension, MetricData, Dimension

    metric_links = db.query(IndicatorMetric).filter(
        IndicatorMetric.id_indicator == indicator.id_indicator
    ).all()
    metric_ids = [lnk.id_metric for lnk in metric_links]
    if not metric_ids:
        return []

    metrics = db.query(Metric).filter(Metric.id_metric.in_(metric_ids)).all()
    metrics_by_id = {m.id_metric: m for m in metrics}

    all_dim_ids = set()
    for mid in metric_ids:
        links = db.query(MetricDimension).filter(MetricDimension.id_metric == mid).all()
        all_dim_ids.update(lnk.id_dimension for lnk in links)

    dims_by_id = {}
    if all_dim_ids:
        dims = db.query(Dimension).filter(Dimension.id_dimension.in_(all_dim_ids)).all()
        dims_by_id = {d.id_dimension: d for d in dims}

    records = []
    for mid in metric_ids:
        m = metrics_by_id.get(mid)
        if not m:
            continue

        meta_fields = []
        try:
            mj = json.loads(m.meta_json) if isinstance(m.meta_json, str) else (m.meta_json or {})
            meta_fields = mj.get('fields', [])
        except Exception:
            pass

        dim_links = db.query(MetricDimension).filter(MetricDimension.id_metric == mid).all()
        dim_ids = [lnk.id_dimension for lnk in dim_links]

        data_rows = db.query(MetricData).filter(MetricData.id_metric == mid).all()
        for row in data_rows:
            try:
                dims_json = json.loads(row.dimensions_json) if isinstance(row.dimensions_json, str) else (row.dimensions_json or {})
            except Exception:
                dims_json = {}

            rec = {}
            # Value fields
            raw_val = row.value
            if meta_fields:
                try:
                    parsed = json.loads(raw_val) if isinstance(raw_val, str) else raw_val
                    if isinstance(parsed, dict):
                        for f in meta_fields:
                            fname = _to_field_name(f['name'])
                            rec[fname] = parsed.get(f['name'])
                    else:
                        key = _to_field_name(meta_fields[0]['name']) if meta_fields else _to_field_name(m.name)
                        rec[key] = parsed
                except Exception:
                    key = _to_field_name(m.name)
                    rec[key] = raw_val
            else:
                key = _to_field_name(m.name)
                try:
                    rec[key] = float(raw_val) if raw_val is not None else None
                except (ValueError, TypeError):
                    rec[key] = raw_val

            # Dimension fields
            for did in dim_ids:
                dim = dims_by_id.get(did)
                if dim:
                    dkey = _to_field_name(dim.name)
                    rec[dkey] = dims_json.get(str(did))

            records.append(rec)

    return records


def _chart_to_png_b64(item: dict, records: list[dict]) -> str:
    """Renderiza un componente del dashboard como PNG base64 usando matplotlib."""
    import io, base64
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import collections

    comp = item.get('component', '')
    x_field = item.get('xField') or item.get('valueField', '')
    y_field = item.get('yField', '')
    group_field = item.get('groupField', '')

    fig, ax = plt.subplots(figsize=(7, 3.5))

    try:
        if comp in ('HeatmapMatrix',):
            x_f = item.get('xField', '')
            y_f = item.get('yField', '')
            v_f = item.get('valueField', '')
            xs = sorted({str(r.get(x_f, '')) for r in records if r.get(x_f) is not None})
            ys = sorted({str(r.get(y_f, '')) for r in records if r.get(y_f) is not None})
            z = []
            for y in ys:
                row_vals = []
                for x in xs:
                    vals = [float(r.get(v_f) or 0) for r in records
                            if str(r.get(x_f)) == x and str(r.get(y_f)) == y
                            and r.get(v_f) is not None]
                    row_vals.append(sum(vals) / len(vals) if vals else 0)
                z.append(row_vals)
            im = ax.imshow(z, aspect='auto', cmap='Blues')
            ax.set_xticks(range(len(xs))); ax.set_xticklabels(xs, fontsize=8)
            ax.set_yticks(range(len(ys))); ax.set_yticklabels(ys, fontsize=8)
            fig.colorbar(im, ax=ax)

        elif comp == 'GaugeIndicator':
            vals = [float(r.get(x_field) or 0) for r in records if r.get(x_field) is not None]
            val = sum(vals) / len(vals) if vals else 0
            ax.axis('off')
            ax.text(0.5, 0.6, f'{val:.1f}', ha='center', va='center',
                    fontsize=40, fontweight='bold', color='#4f46e5', transform=ax.transAxes)
            ax.text(0.5, 0.35, item.get('labelX', x_field), ha='center', va='center',
                    fontsize=11, color='#64748b', transform=ax.transAxes)

        elif comp == 'Histogram':
            vals = [float(r.get(x_field) or 0) for r in records if r.get(x_field) is not None]
            ax.hist(vals, bins=item.get('nbins', 10), color='#6366f1', alpha=0.8, edgecolor='white')
            ax.set_xlabel(item.get('labelX', x_field), fontsize=9)
            ax.set_ylabel(item.get('labelY', 'Frecuencia'), fontsize=9)
            ax.spines[['top', 'right']].set_visible(False)

        else:
            # Barras genéricas: agrupa por x_field, promedia y_field
            buckets = collections.defaultdict(list)
            for r in records:
                xv = str(r.get(x_field, ''))
                yv = r.get(y_field or x_field)
                try:
                    buckets[xv].append(float(yv))
                except (TypeError, ValueError):
                    pass
            if buckets:
                labels = sorted(buckets.keys())
                vals = [sum(buckets[l]) / len(buckets[l]) for l in labels]
                colors = ['#6366f1', '#8b5cf6', '#06b6d4', '#f59e0b', '#10b981',
                          '#f43f5e', '#3b82f6', '#a855f7']
                ax.bar(labels, vals,
                       color=[colors[i % len(colors)] for i in range(len(labels))],
                       width=0.6, zorder=3)
                ax.set_ylabel(item.get('labelY', y_field or ''), fontsize=9)
                ax.yaxis.grid(True, linestyle='--', alpha=0.4, zorder=0)
                ax.spines[['top', 'right']].set_visible(False)
                for i, (lbl, val) in enumerate(zip(labels, vals)):
                    ax.text(i, val + max(vals) * 0.01, f'{val:.1f}',
                            ha='center', va='bottom', fontsize=8)
                plt.xticks(rotation=30, ha='right', fontsize=8)
            else:
                ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center',
                        transform=ax.transAxes, color='#94a3b8')
                ax.axis('off')

    except Exception as e:
        ax.text(0.5, 0.5, f'Error: {e}', ha='center', va='center',
                transform=ax.transAxes, color='#ef4444', fontsize=8)
        ax.axis('off')

    ax.set_title(item.get('labelX', ''), fontsize=10, pad=8)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def _table_section(item: dict, records: list[dict]) -> dict:
    """Convierte un componente tabla en columnas + filas para el template HTML."""
    comp = item.get('component', '')

    if comp == 'PivotTable':
        cfg = item.get('pivotConfig', {})
        row_fields = cfg.get('rows', [])
        col_fields = cfg.get('cols', [])
        values_cfg = cfg.get('values', [])

        if not row_fields or not values_cfg:
            return {'columns': [], 'rows': []}

        # Agrupación simple: filas × columnas
        import collections
        buckets = collections.defaultdict(list)
        col_keys = set()
        for rec in records:
            rk = tuple(str(rec.get(f, '')) for f in row_fields)
            ck = tuple(str(rec.get(f, '')) for f in col_fields) if col_fields else ('',)
            col_keys.add(ck)
            for vc in values_cfg:
                vv = rec.get(vc['field'])
                try:
                    buckets[(rk, ck, vc['field'])].append(float(vv))
                except (TypeError, ValueError):
                    pass

        row_keys = sorted({k[0] for k in buckets.keys()})
        col_keys_sorted = sorted(col_keys)

        # Headers
        header_row = ['/'.join(row_fields)]
        for ck in col_keys_sorted:
            ck_label = ' / '.join(ck) if any(ck) else ''
            for vc in values_cfg:
                lbl = vc.get('label', vc['field'])
                header_row.append(f'{ck_label} {lbl}'.strip())

        rows_out = []
        for rk in row_keys:
            row = [' / '.join(rk)]
            for ck in col_keys_sorted:
                for vc in values_cfg:
                    vals = buckets.get((rk, ck, vc['field']), [])
                    agg = vc.get('aggregation', 'avg')
                    if not vals:
                        row.append('—')
                    elif agg == 'sum':
                        row.append(f'{sum(vals):.2f}')
                    elif agg == 'count':
                        row.append(str(len(vals)))
                    elif agg == 'min':
                        row.append(f'{min(vals):.2f}')
                    elif agg == 'max':
                        row.append(f'{max(vals):.2f}')
                    else:
                        row.append(f'{sum(vals)/len(vals):.2f}')
            rows_out.append(row)

        return {'columns': header_row, 'rows': rows_out}

    else:
        # Tabla plana
        cfg = item.get('flatTableConfig', {})
        col_cfgs = cfg.get('columns', [])
        if not col_cfgs and records:
            col_cfgs = [{'field': k, 'label': k} for k in list(records[0].keys())[:8]]
        columns = [c.get('label', c.get('field', '')) for c in col_cfgs]
        fields = [c.get('field', '') for c in col_cfgs]
        sort_by = cfg.get('sortBy')
        sort_dir = cfg.get('sortDir', 'asc')
        recs = sorted(records, key=lambda r: str(r.get(sort_by, '') or ''),
                      reverse=(sort_dir == 'desc')) if sort_by else records
        rows_out = [[str(r.get(f, '') or '') for f in fields] for r in recs[:200]]
        return {'columns': columns, 'rows': rows_out}


def build_pdf_bytes(indicator, db, org_id: int) -> bytes:
    """
    Genera el PDF como bytes para un indicador dado.
    Puede ser llamado desde el step o directamente desde el endpoint.
    """
    from datetime import date
    from jinja2 import Environment, FileSystemLoader
    from weasyprint import HTML as WeasyprintHTML

    pdf_layout = indicator.pdf_layout
    if isinstance(pdf_layout, str):
        try:
            pdf_layout = json.loads(pdf_layout)
        except Exception:
            pdf_layout = {}

    raw_sections = pdf_layout.get('sections', [])
    records = _build_records(db, indicator, org_id)

    # Renderizar cada sección
    rendered = []
    for sec in raw_sections:
        t = sec.get('type')
        if t == 'cover':
            rendered.append({'type': 'cover', 'title': sec.get('title', indicator.name),
                             'subtitle': sec.get('subtitle', '')})
        elif t == 'page_break':
            rendered.append({'type': 'page_break'})
        elif t == 'text':
            rendered.append({'type': 'text', 'heading': sec.get('heading', ''),
                             'body': sec.get('body', '')})
        elif t == 'chart':
            item = sec.get('item', {})
            b64 = _chart_to_png_b64(item, records)
            rendered.append({'type': 'chart', 'heading': sec.get('heading', ''),
                             'image_b64': b64, 'caption': sec.get('caption', '')})
        elif t == 'table':
            item = sec.get('item', {})
            tdata = _table_section(item, records)
            rendered.append({'type': 'table', 'heading': sec.get('heading', ''),
                             'columns': tdata['columns'], 'rows': tdata['rows']})

    # Jinja2
    templates_dir = Path(__file__).parent.parent / 'templates'
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
    template = env.get_template('report_base.html')
    html_str = template.render(
        sections=rendered,
        org_name=getattr(indicator, 'org_id', ''),
        report_date=date.today().strftime('%d de %B de %Y'),
    )

    return WeasyprintHTML(string=html_str).write_pdf()


class RenderPDFReport(Step):
    """
    Genera el informe PDF del indicador usando WeasyPrint.

    Parámetros:
        indicator_id (int): ID del indicador. Si no se pasa, se lee de ctx.params.

    Requiere:
        - ctx.db: sesión SQLAlchemy activa.
        - ctx.org_id: ID de organización para multi-tenancy.
        - El indicador debe tener pdf_layout configurado.

    Produce:
        - ctx.outputs['report_pdf']: Path al archivo informe.pdf generado.
    """

    def __init__(self, indicator_id: int = None):
        super().__init__(name='RenderPDFReport')
        self.indicator_id = indicator_id

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)
        ind_id = self.indicator_id or ctx.params.get('indicator_id')
        if not ind_id:
            self._log(f'[{self.name}] Error: indicator_id no especificado.')
            return

        from backend.models import Indicator
        indicator = ctx.db.query(Indicator).filter(
            Indicator.id_indicator == ind_id,
            Indicator.org_id == ctx.org_id,
        ).first()
        if not indicator:
            self._log(f'[{self.name}] Error: indicador {ind_id} no encontrado.')
            return

        try:
            pdf_bytes = build_pdf_bytes(indicator, ctx.db, ctx.org_id)

            out_dir = getattr(ctx, 'outputs_dir', None) or Path('.')
            out_dir = Path(out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / 'informe.pdf'
            out_path.write_bytes(pdf_bytes)

            ctx.outputs['report_pdf'] = out_path
            self._log(f'[{self.name}] PDF generado: {out_path}')
        except Exception as e:
            self._log(f'[{self.name}] Error generando PDF: {e}')
            raise

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)


class GenerateTables(Step):
    """
    Genera tablas utilizando funciones de report_tools.

    Lee el esquema de tablas desde ctx.params["tables_schema"] (cargado por un step
    previo) o directamente desde el constructor.

    Cada entrada del esquema tiene:
        - type: nombre de la función en report_tools (ej: "resumen_estadistico_basico")
        - input_key: clave del DataFrame en ctx.artifacts
        - output_filename: nombre del archivo de salida (ej: "resumen.xlsx")
          Usa {val} como placeholder cuando se usa iterate_by.
        - params: kwargs adicionales para la función
        - iterate_by (opcional): columna para generar una tabla por cada valor único.
          Inyecta el valor en params["parametros"][columna] y como kwarg raíz.

    Efectos:
        - Crea archivos .xlsx en ctx.aux_dir.
        - Registra rutas generadas en ctx.artifacts["generated_tables"].
    """
    def __init__(self, tables_schema: Optional[List[Dict]] = None):
        """Inicializa el step, opcionalmente con esquema directo."""
        super().__init__(name="GenerateTables")
        self.tables_schema = tables_schema

    def run(self, ctx):
        """Genera las tablas solicitadas y registra las rutas en ctx.artifacts."""
        before = self._snapshot_artifacts(ctx)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__

        # 1. Resolver esquema: constructor directo, nuevo formato (tables_list) o legacy (tables_schema)
        schema = self.tables_schema
        if not schema:
            schema = ctx.params.get("tables_list") or ctx.params.get("tables_schema", [])

        if not schema:
            self._log(f"[{self.name}] Advertencia: No se encontraron definiciones de tablas.")
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 2. Resolver directorio auxiliar
        aux_dir = getattr(ctx, "aux_dir", None)
        if not aux_dir:
            if hasattr(ctx, "base_dir"):
                aux_dir = ctx.base_dir / "aux_files"
            else:
                aux_dir = Path("aux_files")
            ctx.aux_dir = aux_dir

        if not aux_dir.exists():
            aux_dir.mkdir(parents=True, exist_ok=True)

        # 3. Iterar sobre el esquema y generar tablas
        generated_tables = {}
        tables_generated = 0

        for table_def in schema:
            func_name = table_def.get("type")
            input_key = table_def.get("input_key")
            output_filename = table_def.get("output_filename")
            params = table_def.get("params", {})
            iterate_by = table_def.get("iterate_by", None)
            iterate_param = table_def.get("iterate_param", None)

            # Validar definición mínima
            if not func_name or not input_key or not output_filename:
                self._log(f"[{self.name}] Error: Definición incompleta: {table_def}")
                continue

            func = getattr(report_tools, func_name, None)
            if not func:
                self._log(f"[{self.name}] Error: La función '{func_name}' no existe en report_tools.")
                continue

            # Obtener DataFrame(s) desde artifacts (input_key puede ser string o list[string])
            if isinstance(input_key, list):
                keys = input_key
            else:
                keys = [input_key]

            dfs = [ctx.artifacts.get(k) for k in keys]
            missing = [k for k, d in zip(keys, dfs) if d is None]
            if missing:
                self._log(f"[{self.name}] Error: Artifacts no encontrados: {missing}")
                continue

            df_full = dfs[0]
            extra_dfs = {k: d for k, d in zip(keys[1:], dfs[1:])}

            # Helper: ejecuta la función y guarda el resultado como Excel
            def process_and_save(df_k, filename_k, params_k, _func=func, _extra=extra_dfs):
                try:
                    df_res = _func(df_k, **params_k, **_extra)
                    output_path = aux_dir / filename_k
                    df_res.to_excel(output_path, index=False)
                    generated_tables[filename_k] = output_path
                    return True
                except Exception as e:
                    self._log(f"[{self.name}] Error generando tabla '{filename_k}': {e}")
                    return False

            if iterate_by:
                # Caso iterativo (ej: generar tabla por cada Curso)
                if iterate_by not in df_full.columns:
                    self._log(f"[{self.name}] Error: Columna '{iterate_by}' no existe en DataFrame.")
                    continue

                for val in sorted(df_full[iterate_by].unique(), key=str):
                    if "{val}" in output_filename:
                        fname = output_filename.replace("{val}", str(val))
                    else:
                        base, ext = os.path.splitext(output_filename)
                        fname = f"{base}_{val}{ext}"

                    iter_params = params.copy()
                    # Inyectar valor en parametros dict (para funciones que filtran con parametros)
                    if "parametros" not in iter_params:
                        iter_params["parametros"] = {}
                    if isinstance(iter_params.get("parametros"), dict):
                        iter_params["parametros"][iterate_by] = val
                    # También como kwarg raíz: usa iterate_param si está definido,
                    # sino usa el nombre de la columna directamente
                    if iterate_param:
                        iter_params[iterate_param] = val
                    else:
                        iter_params[iterate_by] = val

                    if process_and_save(df_full, fname, iter_params):
                        tables_generated += 1
            else:
                if process_and_save(df_full, output_filename, params):
                    tables_generated += 1

        # 4. Registrar rutas generadas en el contexto
        ctx.artifacts["generated_tables"] = generated_tables
        self._log(f"[{self.name}] {tables_generated}/{len(schema)} tablas generadas en {aux_dir}")

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)


class RenderReport(Step):
    """
    Genera el informe PDF final utilizando LaTeX.

    Requiere:
        - Archivos generados en ctx.aux_dir (tablas excel, imágenes).
        - params["report_schema"]: Diccionario con la estructura del informe.
          Puede ser cargado previamente o pasado directamente.

    Efectos:
        - Genera 'variables.tex', 'contenido.tex' e 'informe.tex' en ctx.aux_dir.
        - Compila con xelatex.
        - Resultado final: 'informe.pdf' en ctx.outputs_dir.
    """
    def __init__(self, report_schema: Optional[Dict] = None):
        super().__init__(name="RenderReport")
        self.report_schema = report_schema

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__

        # 1. Obtener schema
        schema = self.report_schema or ctx.params.get("report_schema")
        if not schema:
             # Intento de cargar desde archivo si viene una ruta en params
             schema_path = ctx.params.get("report_schema_path")
             if schema_path:
                 try:
                     with open(schema_path, "r", encoding="utf-8") as f:
                         schema = json.load(f)
                 except Exception as e:
                     self._log(f"Error cargando json de reporte desde {schema_path}: {e}")

        if not schema:
            self._log(f"[{self.name}] Error: No se encontró report_schema.")
            # No fallamos, solo retornamos
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 2. Rutas
        aux_dir = getattr(ctx, "aux_dir", None)
        if not aux_dir or not aux_dir.exists():
             # Fallback
             if hasattr(ctx, "base_dir"):
                 aux_dir = ctx.base_dir / "aux_files"
             else:
                 aux_dir = Path("aux_files")

        if not aux_dir.exists():
            self._log(f"[{self.name}] Error: aux_dir no existe ({aux_dir}).")
            return

        # Debemos movernos al directorio auxiliar para que latex encuentre las imagenes/tablas
        # Guardamos CWD original
        cwd_original = os.getcwd()
        os.chdir(aux_dir)

        try:
            # 3. Generar variables.tex
            new_command_format = "\\newcommand{{\\{}}}{{{}}}\n"
            with open("variables.tex", "w", encoding="utf-8") as f:
                f.write("% Variables del informe\n")
                variables = schema.get("variables_documento", {})

                # Inyectar variables desde el contexto si hacen falta
                if "evaluacion" not in variables and hasattr(ctx, "evaluation"):
                    variables["evaluacion"] = ctx.evaluation

                for key, value in variables.items():
                    # Sanitize key/value if needed
                    val_str = str(value).replace("_", "\\_") # Escape básico
                    f.write(new_command_format.format(key, val_str))
                f.write("\n")

            # 4. Generar contenido dinámico (secciones)
            # Combinamos fijas y dinámicas en orden
            secciones_fijas = schema.get("secciones_fijas", [])
            secciones_dinamicas = schema.get("secciones_dinamicas", [])

            todas_secciones = secciones_fijas + secciones_dinamicas

            i_idx = 0
            lista_indices_tex = []

            with open("contenido.tex", "w", encoding="utf-8") as f:
                f.write("% Contenido generado\n")

                for seccion in todas_secciones:
                    if i_idx >= len(indice_alfabetico):
                        break

                    current_idx = indice_alfabetico[i_idx]
                    lista_indices_tex.append(current_idx)

                    titulo = seccion.get("titulo", "")

                    # Definimos el comando sectionX
                    cmd_section = f"\\section*{{{titulo}}}"
                    if seccion.get("newpage", False):
                        cmd_section = "\\newpage " + cmd_section

                    f.write(new_command_format.format("section" + current_idx, cmd_section))

                    # Contenido (Tabla o Imagen)
                    tipo = seccion.get("tipo")
                    contenido_path = seccion.get("contenido") # Ruta relativa a aux_dir o absoluta

                    latex_content = ""
                    if tipo == "tabla":
                         # Leer excel, generar latex
                         try:
                             p = Path(contenido_path)
                             if not p.is_absolute():
                                 p = aux_dir / contenido_path

                             if p.exists():
                                 df_t = pd.read_excel(p)
                                 latex_content = report_tools.df_a_latex_loop(df_t)
                             else:
                                 # Intentar buscar file tal cual (por si generamos en run time)
                                 if Path(contenido_path).exists():
                                      df_t = pd.read_excel(contenido_path)
                                      latex_content = report_tools.df_a_latex_loop(df_t)
                                 else:
                                      latex_content = f"Error: Archivo {contenido_path} no encontrado."
                         except Exception as e:
                             latex_content = f"Error procesando tabla {contenido_path}: {e}"

                    elif tipo == "imagen":
                         opts = seccion.get("options", "")
                         p = Path(contenido_path)
                         img_name = p.name
                         latex_content = report_tools.img_to_latex(img_name, opts)

                    f.write(new_command_format.format("content" + current_idx, latex_content))
                    i_idx += 1


            # 5. Generar informe.tex principal
            with open("informe.tex", "w", encoding="utf-8") as f:
                f.write(formato_informe_generico)
                f.write("\n")
                f.write("\\input{contenido.tex}\n")
                for idx in lista_indices_tex:
                     f.write(f"\\section{idx}\n")
                     f.write(f"\\content{idx}\n")
                     f.write("\n")
                f.write("\\end{document}")

            # 6. Compilar
            self._log(f"[{self.name}] Compilando PDF...")
            cmd = "xelatex -interaction=nonstopmode informe.tex"
            ret = os.system(cmd)

            if ret == 0:
                self._log(f"[{self.name}] PDF generado exitosamente.")
                # Mover a outputs si existe output_dir
                if hasattr(ctx, "outputs_dir") and ctx.outputs_dir.exists():
                     target = ctx.outputs_dir / "informe.pdf"
                elif hasattr(ctx, "outputs"):
                     target = ctx.base_dir / "informe.pdf"
                else:
                     target = Path("informe.pdf").resolve() # en aux_dir

                src = aux_dir / "informe.pdf"
                if src.exists():
                    if src != target:
                        shutil.copy(src, target)
                    ctx.outputs["report_pdf"] = target
            else:
                self._log(f"[{self.name}] Advertencia: xelatex retornó código {ret}. Revisar logs en {aux_dir}.")

        except Exception as e:
            self._log(f"[{self.name}] Excepción durante RenderReport: {e}")
        finally:
            # Volver al directorio original
            os.chdir(cwd_original)

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)


class GenerateDocxReport(Step):
    """
    Genera un informe DOCX (y opcionalmente PDF) usando una plantilla Word y docxtpl.

    Parametros:
        template_name (str): Nombre del archivo plantilla en backend/templates (o ruta absoluta).
        output_filename (str): Nombre del archivo de salida (ej: informe_final.docx).
        context_key (opcional): Clave en artifacts/params que contiene el diccionario de contexto.
                                Si no se da, se construye un contexto mezclando params y artifacts.
        convert_to_pdf (bool): Si True, intenta convertir a PDF usando docx2pdf.

    Efectos:
        - Crea archivo .docx en ctx.aux_dir.
        - Si convert_to_pdf=True, crea .pdf en ctx.outputs_dir.
    """
    def __init__(self, template_name: str, output_filename: str, context_key: str = None, convert_to_pdf: bool = True):
        super().__init__(name="GenerateDocxReport")
        self.template_name = template_name
        self.output_filename = output_filename
        self.context_key = context_key
        self.convert_to_pdf = convert_to_pdf

    def run(self, ctx):
        """Renderiza reporte Word/PDF usando un .docx como plantilla."""
        before = self._snapshot_artifacts(ctx)

        # 1. Resolver ruta de plantilla docx
        p = Path(self.template_name)
        if p.exists():
            template_path = p
        else:
            # 2. Buscar en carpeta centralizada (REPORTS_TEMPLATES_DIR)
            template_path = REPORTS_TEMPLATES_DIR / self.template_name
            if not template_path.exists():
                 # 3. Fallback: carpeta 'templates' del contexto
                if hasattr(ctx, "base_dir"):
                     template_path = ctx.base_dir / "templates" / self.template_name

        if not template_path.exists():
            self._log(f"[{self.name}] Error: Plantilla DOCX no encontrada: {self.template_name}")
            return

        # 2. Construir Contexto
        if self.context_key:
            data_context = ctx.artifacts.get(self.context_key) or ctx.params.get(self.context_key, {})
        else:
            # Merge params and artifacts
            data_context = ctx.params.copy()

        # Asegurar aux_dir
        aux_dir = getattr(ctx, "aux_dir", None)
        if not aux_dir:
             if hasattr(ctx, "base_dir"):
                 aux_dir = ctx.base_dir / "aux_files"
             else:
                 aux_dir = Path("aux_files")

        if not aux_dir.exists():
            aux_dir.mkdir(parents=True, exist_ok=True)

        output_path = aux_dir / self.output_filename

        # 3. Renderizar
        try:
            self._log(f"[{self.name}] Renderizando plantilla {template_path}...")
            result_path = render_docx_report(template_path, data_context, output_path, auto_convert_pdf=self.convert_to_pdf)
            self._log(f"[{self.name}] Generado: {result_path}")

            # Registrar output
            if str(result_path).endswith(".pdf"):
                ctx.outputs["report_docx_pdf"] = result_path
            else:
                ctx.outputs["report_docx"] = result_path

        except Exception as e:
            self._log(f"[{self.name}] Error generando reporte Docx: {e}")

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)
