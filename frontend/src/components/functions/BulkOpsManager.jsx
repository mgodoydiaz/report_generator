/**
 * BulkOpsManager — operaciones masivas sobre metric_data (B10 sección 2).
 *
 * Dos tarjetas:
 *   1. Buscar/Reemplazar — find & replace estilo Excel sobre una columna
 *      de una métrica (field o dimension). Soporta exact/contains/regex.
 *   2. Recalcular columna — aplica un mapeo del catálogo a una columna
 *      source y guarda el resultado en target.
 *
 * Ambas tienen flujo "Vista previa → Aplicar" con dry_run para evitar
 * cambios accidentales. El backend valida org_id en cada request.
 */
import { useEffect, useMemo, useState } from 'react';
import {
  Replace, RefreshCw, ArrowRight, AlertTriangle, Loader2, Check, X,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../../constants';

export default function BulkOpsManager() {
  const [metrics, setMetrics] = useState([]);
  const [dimensions, setDimensions] = useState([]);
  const [mappings, setMappings] = useState([]);

  useEffect(() => {
    apiGet('/metrics/').then((r) => setMetrics(Array.isArray(r) ? r : [])).catch(() => {});
    apiGet('/dimensions/').then((r) => setDimensions(Array.isArray(r) ? r : [])).catch(() => {});
    apiGet('/mappings/').then((r) => setMappings(Array.isArray(r) ? r : [])).catch(() => {});
  }, []);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <ReplaceCard metrics={metrics} dimensions={dimensions} />
      <RecalculateCard metrics={metrics} dimensions={dimensions} mappings={mappings} />
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────────
// Helper: lista de columnas disponibles para una métrica
// ─────────────────────────────────────────────────────────────────────────

function useMetricColumns(metric, dimensions) {
  return useMemo(() => {
    if (!metric) return [];
    const cols = [];
    const dimById = new Map(dimensions.map((d) => [d.id_dimension, d]));
    (metric.dimension_ids || []).forEach((id) => {
      const d = dimById.get(id);
      if (d) cols.push({ name: d.name, kind: 'dimension', type: d.data_type });
    });
    try {
      const meta = typeof metric.meta_json === 'string'
        ? JSON.parse(metric.meta_json || '{}')
        : (metric.meta_json || {});
      (meta.fields || []).forEach((f) => cols.push({ name: f.name, kind: 'field', type: f.type }));
    } catch (e) {}
    return cols;
  }, [metric, dimensions]);
}


// ─────────────────────────────────────────────────────────────────────────
// CARD 1: Buscar / Reemplazar
// ─────────────────────────────────────────────────────────────────────────

function ReplaceCard({ metrics, dimensions }) {
  const [metricId, setMetricId] = useState(null);
  const [columnName, setColumnName] = useState('');
  const [find, setFind] = useState('');
  const [replace, setReplace] = useState('');
  const [matchType, setMatchType] = useState('exact');
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);

  const metric = useMemo(() => metrics.find((m) => m.id_metric === metricId), [metrics, metricId]);
  const columns = useMetricColumns(metric, dimensions);

  // Reset cuando cambia métrica
  useEffect(() => { setColumnName(''); setPreview(null); }, [metricId]);

  const runPreview = async (apply = false) => {
    if (!metricId || !columnName || !find) {
      toast.error('Faltan campos: métrica, columna, valor a buscar');
      return;
    }
    setBusy(true);
    try {
      const r = await apiPost('/data-ops/replace', {
        metric_id: metricId,
        column_name: columnName,
        find,
        replace,
        match_type: matchType,
        case_sensitive: caseSensitive,
        dry_run: !apply,
      });
      setPreview(r);
      if (apply) {
        toast.success(`Aplicado: ${r.n_would_change} cambios`);
      }
    } catch (e) {
      toast.error(`Error: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const handleApply = async () => {
    if (!preview || preview.n_would_change === 0) {
      toast.error('Corre primero la vista previa');
      return;
    }
    if (!confirm(`¿Aplicar ${preview.n_would_change} cambios? Esta acción no es reversible.`)) return;
    await runPreview(true);
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm">
      <h2 className="text-base font-bold text-slate-800 dark:text-slate-100 inline-flex items-center gap-2 mb-1">
        <Replace size={16} className="text-indigo-600" /> Buscar y reemplazar
      </h2>
      <p className="text-xs text-slate-500 mb-4">
        Reemplaza valores en una columna (field o dimension) de una métrica. Soporta exact / contains / regex.
      </p>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Métrica</label>
          <select
            value={metricId || ''}
            onChange={(e) => setMetricId(e.target.value ? Number(e.target.value) : null)}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 dark:bg-slate-800 rounded"
          >
            <option value="">— Seleccionar —</option>
            {metrics.map((m) => (
              <option key={m.id_metric} value={m.id_metric}>[{m.id_metric}] {m.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Columna</label>
          <select
            value={columnName}
            onChange={(e) => setColumnName(e.target.value)}
            disabled={!metric}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 dark:bg-slate-800 rounded disabled:opacity-50"
          >
            <option value="">— Seleccionar —</option>
            {columns.map((c) => (
              <option key={`${c.kind}-${c.name}`} value={c.name}>
                {c.name} ({c.kind === 'dimension' ? 'dim' : 'field'} · {c.type})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Buscar</label>
          <input
            type="text" value={find}
            onChange={(e) => setFind(e.target.value)}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 dark:bg-slate-800 rounded font-mono"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Reemplazar por</label>
          <input
            type="text" value={replace}
            onChange={(e) => setReplace(e.target.value)}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 dark:bg-slate-800 rounded font-mono"
          />
        </div>
        <div className="col-span-2 flex items-center gap-3 text-xs">
          <select
            value={matchType}
            onChange={(e) => setMatchType(e.target.value)}
            className="px-2 py-1 text-xs border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded"
          >
            <option value="exact">Coincidencia exacta</option>
            <option value="contains">Contiene</option>
            <option value="regex">Regex</option>
          </select>
          <label className="inline-flex items-center gap-1.5">
            <input
              type="checkbox" checked={caseSensitive}
              onChange={(e) => setCaseSensitive(e.target.checked)}
              className="accent-indigo-600"
            />
            <span>Distinguir mayúsculas</span>
          </label>
        </div>
      </div>

      <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
        <button
          onClick={() => runPreview(false)}
          disabled={busy || !metricId || !columnName || !find}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 disabled:opacity-50 rounded font-semibold"
        >
          {busy ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          Vista previa
        </button>
        <button
          onClick={handleApply}
          disabled={busy || !preview || preview.n_would_change === 0}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded font-semibold"
        >
          <Check size={12} /> Aplicar
        </button>
      </div>

      <PreviewPanel preview={preview} kind="replace" />
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────────
// CARD 2: Recalcular columna (con mapeo)
// ─────────────────────────────────────────────────────────────────────────

function RecalculateCard({ metrics, dimensions, mappings }) {
  const [metricId, setMetricId] = useState(null);
  const [sourceColumn, setSourceColumn] = useState('');
  const [targetColumn, setTargetColumn] = useState('');
  const [mappingId, setMappingId] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);

  const metric = useMemo(() => metrics.find((m) => m.id_metric === metricId), [metrics, metricId]);
  const columns = useMetricColumns(metric, dimensions);
  const fieldColumns = columns.filter((c) => c.kind === 'field');

  useEffect(() => { setSourceColumn(''); setTargetColumn(''); setPreview(null); }, [metricId]);

  const runPreview = async (apply = false) => {
    if (!metricId || !sourceColumn || !targetColumn || !mappingId) {
      toast.error('Faltan campos: métrica, source, target, mapeo');
      return;
    }
    setBusy(true);
    try {
      const r = await apiPost('/data-ops/recalculate', {
        metric_id: metricId,
        source_column: sourceColumn,
        target_column: targetColumn,
        mapping_id: mappingId,
        dry_run: !apply,
      });
      setPreview(r);
      if (apply) {
        toast.success(`Recalculado: ${r.n_changed} cambios`);
      }
    } catch (e) {
      toast.error(`Error: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const handleApply = async () => {
    if (!preview || preview.n_changed === 0) {
      toast.error('Corre primero la vista previa');
      return;
    }
    if (!confirm(`¿Aplicar ${preview.n_changed} cambios? Esta acción no es reversible.`)) return;
    await runPreview(true);
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm">
      <h2 className="text-base font-bold text-slate-800 dark:text-slate-100 inline-flex items-center gap-2 mb-1">
        <RefreshCw size={16} className="text-emerald-600" /> Recalcular columna
      </h2>
      <p className="text-xs text-slate-500 mb-4">
        Aplica un mapeo del catálogo a una columna source y guarda el resultado en target. Útil para
        re-aplicar Categoría/Nivel/Logro tras editar el mapeo.
      </p>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="col-span-2">
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Métrica</label>
          <select
            value={metricId || ''}
            onChange={(e) => setMetricId(e.target.value ? Number(e.target.value) : null)}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 dark:bg-slate-800 rounded"
          >
            <option value="">— Seleccionar —</option>
            {metrics.map((m) => (
              <option key={m.id_metric} value={m.id_metric}>[{m.id_metric}] {m.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            Columna source
          </label>
          <select
            value={sourceColumn}
            onChange={(e) => setSourceColumn(e.target.value)}
            disabled={!metric}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 dark:bg-slate-800 rounded disabled:opacity-50"
          >
            <option value="">— Seleccionar —</option>
            {columns.map((c) => (
              <option key={`${c.kind}-${c.name}`} value={c.name}>
                {c.name} ({c.kind === 'dimension' ? 'dim' : 'field'})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            Columna target <span className="text-slate-400 font-normal">(field)</span>
          </label>
          <input
            type="text" value={targetColumn}
            onChange={(e) => setTargetColumn(e.target.value)}
            list="target-fields"
            placeholder="Categoria, Nivel, Logro..."
            className="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 dark:bg-slate-800 rounded"
          />
          <datalist id="target-fields">
            {fieldColumns.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
          </datalist>
        </div>
        <div className="col-span-2">
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Mapeo</label>
          <select
            value={mappingId || ''}
            onChange={(e) => setMappingId(e.target.value ? Number(e.target.value) : null)}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 dark:bg-slate-800 rounded"
          >
            <option value="">— Seleccionar —</option>
            {mappings.map((m) => (
              <option key={m.id_spec} value={m.id_spec}>
                [{m.id_spec}] {m.name} ({m.kind})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
        <button
          onClick={() => runPreview(false)}
          disabled={busy || !metricId || !sourceColumn || !targetColumn || !mappingId}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 disabled:opacity-50 rounded font-semibold"
        >
          {busy ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          Vista previa
        </button>
        <button
          onClick={handleApply}
          disabled={busy || !preview || preview.n_changed === 0}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded font-semibold"
        >
          <Check size={12} /> Aplicar
        </button>
      </div>

      <PreviewPanel preview={preview} kind="recalculate" />
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────────
// PreviewPanel — muestra qué cambiaría
// ─────────────────────────────────────────────────────────────────────────

function PreviewPanel({ preview, kind }) {
  if (!preview) return null;

  const changeCount = kind === 'replace' ? preview.n_would_change : preview.n_changed;
  const totalRows = preview.n_total_rows;

  return (
    <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
      <div className="flex items-center gap-3 text-xs text-slate-600 dark:text-slate-400">
        <span><strong>{totalRows}</strong> filas totales</span>
        {kind === 'replace' && (
          <span><strong>{preview.n_matched}</strong> coinciden</span>
        )}
        <span className={changeCount > 0 ? 'text-amber-600 font-bold' : ''}>
          <strong>{changeCount}</strong> cambiarían
        </span>
        {preview.applied && (
          <span className="text-emerald-600 inline-flex items-center gap-1">
            <Check size={12} /> Aplicado
          </span>
        )}
      </div>
      {preview.sample_changes && preview.sample_changes.length > 0 && (
        <div className="mt-2 max-h-48 overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="text-slate-500 sticky top-0 bg-white dark:bg-slate-900">
              <tr>
                <th className="text-left py-1 px-1">Antes</th>
                <th className="text-left py-1 px-1 w-4"></th>
                <th className="text-left py-1 px-1">Después</th>
              </tr>
            </thead>
            <tbody>
              {preview.sample_changes.map((c, i) => (
                <tr key={i} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-0.5 px-1 font-mono text-slate-600">{c.before || c.source || '∅'}</td>
                  <td className="py-0.5 px-1 text-slate-300"><ArrowRight size={10} /></td>
                  <td className="py-0.5 px-1 font-mono text-emerald-700">{c.after || '∅'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {changeCount === 0 && preview.n_matched === 0 && kind === 'replace' && (
        <div className="text-xs text-slate-400 mt-2 inline-flex items-center gap-1">
          <AlertTriangle size={12} /> Sin coincidencias
        </div>
      )}
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────────
// API helpers
// ─────────────────────────────────────────────────────────────────────────

async function apiGet(path) {
  const token = localStorage.getItem('rg_token');
  const r = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
async function apiPost(path, body) {
  const token = localStorage.getItem('rg_token');
  const r = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return r.json();
}
