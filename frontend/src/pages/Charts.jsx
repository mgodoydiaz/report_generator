/**
 * Charts — editor de gráficos configurables (B8).
 *
 * Layout 3 paneles análogo a /tables:
 *   [Sidebar lista]  [Editor 3 tabs (Origen|Tipo+Mapeo|Estética)]  [Preview live]
 *
 * Cada gráfico = Spec con type='Gráficos'. CRUD vía /api/charts.
 * Preview live: POST /api/charts/preview con la config draft.
 */
import { useEffect, useMemo, useState } from 'react';
import {
  Plus, Save, Trash2, Copy, Database, Sliders, BarChart3, X, Loader2,
  Search, Eye, AlertCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import { ChartRenderer } from '../components/charts';

const EMPTY_CONFIG = {
  version: 1,
  chart_type: 'bar',
  data_source: { metric_id: null, filters: {}, derived_fields_override: [] },
  mapping: { aggregation: 'mean' },
  aesthetics: { y_format: 'number', show_legend: true, bins: 10 },
};

export default function Charts() {
  const [charts, setCharts] = useState([]);
  const [loadingList, setLoadingList] = useState(false);
  const [filter, setFilter] = useState('');

  const [selectedId, setSelectedId] = useState(null);
  const [draftMeta, setDraftMeta] = useState({ name: '', description: '', is_draft: true });
  const [draftConfig, setDraftConfig] = useState(EMPTY_CONFIG);
  const [unsaved, setUnsaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('source');

  const [metrics, setMetrics] = useState([]);
  const [dimensions, setDimensions] = useState([]);
  const [chartTypesMeta, setChartTypesMeta] = useState({});

  // Catálogos
  useEffect(() => {
    apiGet('/metrics/').then((r) => setMetrics(r || [])).catch(() => {});
    apiGet('/dimensions/').then((r) => setDimensions(r || [])).catch(() => {});
    apiGet('/charts/types').then((r) => setChartTypesMeta(r || {})).catch(() => {});
  }, []);

  // Lista
  const reloadList = () => {
    setLoadingList(true);
    apiGet('/charts/')
      .then((r) => setCharts(Array.isArray(r) ? r : []))
      .catch((e) => toast.error(`Error: ${e.message}`))
      .finally(() => setLoadingList(false));
  };
  useEffect(reloadList, []);

  // Detalle
  useEffect(() => {
    if (!selectedId) return;
    apiGet(`/charts/${selectedId}`).then((r) => {
      setDraftMeta({
        name: r.name || '',
        description: r.description || '',
        is_draft: r.is_draft ?? true,
      });
      setDraftConfig(r.config || EMPTY_CONFIG);
      setUnsaved(false);
    }).catch((e) => toast.error(`Error cargando gráfico: ${e.message}`));
  }, [selectedId]);

  // Columnas disponibles (igual que en Tables: dimensiones + fields del meta_json)
  const metricColumns = useMemo(() => {
    const mid = draftConfig?.data_source?.metric_id;
    if (!mid) return [];
    const m = metrics.find((x) => x.id_metric === mid);
    if (!m) return [];
    const cols = [];
    const dimById = new Map(dimensions.map((d) => [d.id_dimension, d]));
    (m.dimension_ids || []).forEach((id) => {
      const d = dimById.get(id);
      if (d) cols.push({ key: d.name, kind: 'dimension', type: d.data_type });
    });
    try {
      const meta = typeof m.meta_json === 'string' ? JSON.parse(m.meta_json || '{}') : (m.meta_json || {});
      (meta.fields || []).forEach((f) => cols.push({ key: f.name, kind: 'field', type: f.type }));
    } catch (e) {}
    return cols;
  }, [draftConfig?.data_source?.metric_id, metrics, dimensions]);

  const updateConfig = (updater) => {
    setDraftConfig((prev) => (typeof updater === 'function' ? updater(prev) : updater));
    setUnsaved(true);
  };
  const updateMeta = (patch) => {
    setDraftMeta((prev) => ({ ...prev, ...patch }));
    setUnsaved(true);
  };

  const handleNew = () => {
    setSelectedId(null);
    setDraftMeta({ name: 'Nuevo gráfico', description: '', is_draft: true });
    setDraftConfig(EMPTY_CONFIG);
    setUnsaved(true);
    setActiveTab('source');
  };

  const handleSave = async () => {
    if (!draftMeta.name?.trim()) { toast.error('Nombre obligatorio'); return; }
    if (!draftConfig.data_source?.metric_id) { toast.error('Selecciona métrica'); return; }
    setSaving(true);
    try {
      if (selectedId) {
        await apiPut(`/charts/${selectedId}`, {
          name: draftMeta.name,
          description: draftMeta.description,
          is_draft: draftMeta.is_draft,
          config: draftConfig,
        });
        toast.success('Gráfico guardado');
      } else {
        const r = await apiPost('/charts/', {
          name: draftMeta.name,
          description: draftMeta.description,
          is_draft: draftMeta.is_draft,
          config: draftConfig,
        });
        setSelectedId(r.id_spec);
        toast.success(`Creado (id ${r.id_spec})`);
      }
      setUnsaved(false);
      reloadList();
    } catch (e) {
      toast.error(`Error: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDuplicate = async () => {
    if (!selectedId) return;
    try {
      const r = await apiPost(`/charts/${selectedId}/duplicate`, {});
      toast.success(`Duplicado (id ${r.id_spec})`);
      reloadList();
      setSelectedId(r.id_spec);
    } catch (e) { toast.error(e.message); }
  };

  const handleDelete = async () => {
    if (!selectedId) return;
    if (!confirm(`¿Eliminar "${draftMeta.name}"?`)) return;
    try {
      await apiDelete(`/charts/${selectedId}`);
      toast.success('Eliminado');
      setSelectedId(null);
      setDraftConfig(EMPTY_CONFIG);
      setDraftMeta({ name: '', description: '', is_draft: true });
      reloadList();
    } catch (e) { toast.error(e.message); }
  };

  const filteredCharts = useMemo(() => {
    if (!filter.trim()) return charts;
    const q = filter.toLowerCase();
    return charts.filter((c) =>
      (c.name || '').toLowerCase().includes(q) ||
      (c.chart_type || '').toLowerCase().includes(q)
    );
  }, [charts, filter]);

  return (
    <div className="grid grid-cols-12 gap-3 h-[calc(100vh-100px)]">
      {/* SIDEBAR */}
      <aside className="col-span-3 lg:col-span-2 flex flex-col bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
        <div className="p-2 border-b border-slate-200 bg-slate-50">
          <button
            onClick={handleNew}
            className="w-full inline-flex items-center justify-center gap-1 px-2 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            <Plus size={14} /> Nuevo gráfico
          </button>
          <div className="mt-2 relative">
            <Search size={12} className="absolute top-1.5 left-2 text-slate-400" />
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filtrar…"
              className="w-full pl-7 pr-2 py-1 text-xs border border-slate-200 rounded"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loadingList && <div className="p-3 text-xs text-slate-400">Cargando…</div>}
          {!loadingList && filteredCharts.length === 0 && (
            <div className="p-3 text-xs text-slate-400">Sin gráficos. Crea uno nuevo.</div>
          )}
          {filteredCharts.map((c) => {
            const isSel = c.id_spec === selectedId;
            return (
              <button
                key={c.id_spec}
                onClick={() => setSelectedId(c.id_spec)}
                className={`w-full text-left px-3 py-2 border-b border-slate-100 hover:bg-slate-50 ${isSel ? 'bg-indigo-50 border-l-2 border-l-indigo-500' : ''}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800 truncate">{c.name}</span>
                  {c.is_draft && <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">draft</span>}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  {c.chart_type ? `${c.chart_type} · ` : ''}Métrica {c.metric_id ?? '—'}
                </div>
              </button>
            );
          })}
        </div>
      </aside>

      {/* EDITOR */}
      <main className="col-span-5 lg:col-span-5 flex flex-col bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
        <div className="flex items-start justify-between gap-3 p-3 border-b border-slate-200 bg-slate-50">
          <div className="flex-1 min-w-0">
            <input
              type="text"
              value={draftMeta.name}
              onChange={(e) => updateMeta({ name: e.target.value })}
              placeholder="Nombre del gráfico"
              className="w-full text-base font-semibold bg-transparent border-0 focus:outline-none focus:ring-0 text-slate-900"
            />
            <input
              type="text"
              value={draftMeta.description}
              onChange={(e) => updateMeta({ description: e.target.value })}
              placeholder="Descripción (opcional)"
              className="w-full text-xs text-slate-500 bg-transparent border-0 focus:outline-none focus:ring-0 mt-0.5"
            />
          </div>
          <div className="flex items-center gap-1.5">
            <label className="inline-flex items-center gap-1 text-xs text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                checked={!draftMeta.is_draft}
                onChange={(e) => updateMeta({ is_draft: !e.target.checked })}
                className="accent-indigo-600"
              />
              Publicado
            </label>
            <button
              onClick={handleSave}
              disabled={saving || !unsaved}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
              Guardar
            </button>
            {selectedId && (
              <>
                <button onClick={handleDuplicate} className="px-2 py-1 text-xs border border-slate-300 rounded hover:bg-slate-100" title="Duplicar"><Copy size={12} /></button>
                <button onClick={handleDelete} className="px-2 py-1 text-xs border border-rose-300 text-rose-600 rounded hover:bg-rose-50" title="Eliminar"><Trash2 size={12} /></button>
              </>
            )}
          </div>
        </div>

        <div className="flex border-b border-slate-200 bg-white">
          {[
            { id: 'source', label: 'Origen', icon: Database },
            { id: 'type', label: 'Tipo & Mapeo', icon: BarChart3 },
            { id: 'aesthetics', label: 'Estética', icon: Sliders },
          ].map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`inline-flex items-center gap-1.5 px-4 py-2 text-sm border-b-2 ${
                  activeTab === t.id
                    ? 'border-indigo-600 text-indigo-600 font-medium'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              ><Icon size={14} /> {t.label}</button>
            );
          })}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'source' && (
            <SourceTab
              cfg={draftConfig}
              metrics={metrics}
              metricColumns={metricColumns}
              onChange={(ds) => updateConfig((p) => ({ ...p, data_source: ds }))}
            />
          )}
          {activeTab === 'type' && (
            <TypeAndMappingTab
              cfg={draftConfig}
              metricColumns={metricColumns}
              chartTypesMeta={chartTypesMeta}
              onChangeType={(ct) => updateConfig((p) => ({ ...p, chart_type: ct }))}
              onChangeMapping={(m) => updateConfig((p) => ({ ...p, mapping: m }))}
            />
          )}
          {activeTab === 'aesthetics' && (
            <AestheticsTab
              cfg={draftConfig}
              onChange={(a) => updateConfig((p) => ({ ...p, aesthetics: a }))}
            />
          )}
        </div>
      </main>

      {/* PREVIEW */}
      <aside className="col-span-4 lg:col-span-5 flex flex-col gap-2 overflow-hidden">
        <div className="text-xs text-slate-500 px-1 inline-flex items-center gap-1">
          <Eye size={12} /> Preview live
          {unsaved && <span className="text-amber-600">· cambios sin guardar</span>}
        </div>
        <div className="flex-1 overflow-hidden bg-white border border-slate-200 rounded shadow-sm p-3">
          {draftConfig?.data_source?.metric_id ? (
            <ChartRenderer
              draftConfig={draftConfig}
              key={JSON.stringify(draftConfig)}
              height={520}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-slate-400 text-sm">
              <div className="text-center">
                <AlertCircle size={24} className="mx-auto mb-2 opacity-50" />
                Selecciona una métrica en Origen para ver el preview
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────
// Tab: Origen
// ─────────────────────────────────────────────────────────────────────

function SourceTab({ cfg, metrics, metricColumns, onChange }) {
  const ds = cfg.data_source || {};
  const filters = ds.filters || {};
  const dimColumns = metricColumns.filter((c) => c.kind === 'dimension');

  const setMetric = (id) => {
    onChange({ ...ds, metric_id: id ? Number(id) : null, filters: {} });
  };

  const updateFilter = (k, v) => {
    const next = { ...filters };
    if (v === '' || v == null) delete next[k];
    else next[k] = v;
    onChange({ ...ds, filters: next });
  };

  return (
    <div className="space-y-5">
      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-1">Métrica</label>
        <select
          value={ds.metric_id || ''}
          onChange={(e) => setMetric(e.target.value)}
          className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded"
        >
          <option value="">— Seleccionar —</option>
          {metrics.map((m) => (
            <option key={m.id_metric} value={m.id_metric}>
              [{m.id_metric}] {m.name}
            </option>
          ))}
        </select>
      </div>

      {ds.metric_id && dimColumns.length > 0 && (
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Filtros base (igualdad)</label>
          <div className="space-y-1.5">
            {dimColumns.map((d) => (
              <div key={d.key} className="flex items-center gap-2">
                <span className="w-32 text-xs text-slate-600 truncate">{d.key}</span>
                <input
                  type="text"
                  value={filters[d.key] || ''}
                  onChange={(e) => updateFilter(d.key, e.target.value)}
                  placeholder="(sin filtro)"
                  className="flex-1 px-2 py-1 text-xs border border-slate-200 rounded"
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────
// Tab: Tipo & Mapeo
// ─────────────────────────────────────────────────────────────────────

function TypeAndMappingTab({ cfg, metricColumns, chartTypesMeta, onChangeType, onChangeMapping }) {
  const ct = cfg.chart_type;
  const meta = chartTypesMeta[ct] || {};
  const required = meta.required_fields || [];
  const optional = meta.optional_fields || [];
  const m = cfg.mapping || {};

  const setField = (k, v) => onChangeMapping({ ...m, [k]: v || null });

  // Lista de fields del df disponibles para mapeo
  const allFields = metricColumns.map((c) => c.key);

  return (
    <div className="space-y-5 text-sm">
      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-2">Tipo de gráfico</label>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
          {Object.entries(chartTypesMeta).map(([key, info]) => (
            <button
              key={key}
              onClick={() => onChangeType(key)}
              className={`text-left px-3 py-2 rounded border transition ${
                ct === key
                  ? 'border-indigo-500 bg-indigo-50 text-indigo-900'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              <div className="text-sm font-semibold">{info.display_name}</div>
              <div className="text-[10px] text-slate-500 mt-0.5 leading-tight">{info.description}</div>
            </button>
          ))}
        </div>
      </div>

      {ct && (
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-2">
            Mapeo de campos para "{meta.display_name || ct}"
          </label>
          <div className="space-y-2">
            {required.map((f) => (
              <FieldSelector
                key={f}
                label={f}
                required
                value={m[f] || ''}
                options={allFields}
                onChange={(v) => setField(f, v)}
              />
            ))}
            {optional.length > 0 && (
              <>
                <div className="text-[11px] text-slate-400 mt-3 mb-1">Opcionales:</div>
                {optional.map((f) => (
                  <FieldSelector
                    key={f}
                    label={f}
                    value={m[f] != null ? String(m[f]) : ''}
                    options={f === 'aggregation' ? ['mean', 'sum', 'min', 'max', 'count', 'nunique'] : allFields}
                    onChange={(v) => setField(f, v)}
                  />
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function FieldSelector({ label, value, options, required, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-28 text-xs text-slate-600 truncate">
        {label}{required && <span className="text-rose-500">*</span>}
      </span>
      <select
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1 px-2 py-1 text-xs border border-slate-200 rounded"
      >
        <option value="">—</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────
// Tab: Estética
// ─────────────────────────────────────────────────────────────────────

function AestheticsTab({ cfg, onChange }) {
  const a = cfg.aesthetics || {};
  const update = (patch) => onChange({ ...a, ...patch });

  return (
    <div className="space-y-4 text-sm">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Título</label>
          <input
            type="text" value={a.titulo || ''}
            onChange={(e) => update({ titulo: e.target.value })}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Formato Y</label>
          <select
            value={a.y_format || 'number'}
            onChange={(e) => update({ y_format: e.target.value })}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded"
          >
            <option value="number">Número (0.85)</option>
            <option value="percent">Porcentaje (85%)</option>
            <option value="int">Entero</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Etiqueta X</label>
          <input
            type="text" value={a.x_label || ''}
            onChange={(e) => update({ x_label: e.target.value })}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Etiqueta Y</label>
          <input
            type="text" value={a.y_label || ''}
            onChange={(e) => update({ y_label: e.target.value })}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Y mín</label>
          <input
            type="number" step="0.1"
            value={a.y_lims?.[0] ?? ''}
            onChange={(e) => {
              const v = e.target.value === '' ? null : Number(e.target.value);
              const max = a.y_lims?.[1] ?? null;
              update({ y_lims: v == null && max == null ? null : [v ?? 0, max ?? 1] });
            }}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Y máx</label>
          <input
            type="number" step="0.1"
            value={a.y_lims?.[1] ?? ''}
            onChange={(e) => {
              const v = e.target.value === '' ? null : Number(e.target.value);
              const min = a.y_lims?.[0] ?? null;
              update({ y_lims: v == null && min == null ? null : [min ?? 0, v ?? 1] });
            }}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-1">Paleta de color</label>
        <select
          value={a.color_palette || ''}
          onChange={(e) => update({ color_palette: e.target.value || null })}
          className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded"
        >
          <option value="">Default (categorical)</option>
          <option value="semaforo">Semáforo (verde/naranja/rojo)</option>
          <option value="viridis">Viridis (heatmap)</option>
        </select>
      </div>

      <div>
        <label className="inline-flex items-center gap-2 text-xs">
          <input
            type="checkbox" checked={a.show_legend !== false}
            onChange={(e) => update({ show_legend: e.target.checked })}
            className="accent-indigo-600"
          /> Mostrar leyenda
        </label>
      </div>

      {cfg.chart_type === 'histogram' && (
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Bins (histogram)</label>
          <input
            type="number" min={2} max={100}
            value={a.bins || 10}
            onChange={(e) => update({ bins: Number(e.target.value) })}
            className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded"
          />
        </div>
      )}
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────
// API helpers (idénticos a Tables.jsx)
// ─────────────────────────────────────────────────────────────────────

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
async function apiPut(path, body) {
  const token = localStorage.getItem('rg_token');
  const r = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return r.json();
}
async function apiDelete(path) {
  const token = localStorage.getItem('rg_token');
  const r = await fetch(`${API_BASE_URL}${path}`, {
    method: 'DELETE',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
