/**
 * Tables — editor de tablas configurables (B7).
 *
 * Layout 3 paneles:
 *   [Sidebar lista]  [Editor 3 tabs (Origen|Columnas|Comportamiento)]  [Preview live]
 *
 * Cada tabla = Spec con type='Tablas'. CRUD vía /api/tables.
 * Preview live: POST /api/tables/preview con la config draft (sin persistir).
 */
import { useEffect, useMemo, useState } from 'react';
import {
  Plus, Save, Trash2, Copy, Database, Columns, Sliders, X, Loader2,
  Search, GripVertical, Eye, EyeOff, ChevronDown, ChevronRight, AlertCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import { TableRenderer } from '../components/tables';

const EMPTY_CONFIG = {
  version: 1,
  data_source: { metric_id: null, filters: {}, derived_fields_override: [] },
  columns: [],
  behavior: {
    grouping: null,
    sorting: [],
    pagination: { enabled: true, page_size: 50 },
    export: { csv: true, xlsx: true },
    search: true,
  },
};

export default function Tables() {
  const [tables, setTables] = useState([]);
  const [loadingList, setLoadingList] = useState(false);
  const [filter, setFilter] = useState('');

  const [selectedId, setSelectedId] = useState(null);
  const [draftMeta, setDraftMeta] = useState({ name: '', description: '', is_draft: true });
  const [draftConfig, setDraftConfig] = useState(EMPTY_CONFIG);
  const [unsaved, setUnsaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('source');

  const [metrics, setMetrics] = useState([]);
  const [indicators, setIndicators] = useState([]);
  const [dimensions, setDimensions] = useState([]);

  // ── Catálogos ───────────────────────────────────────────────────────
  useEffect(() => {
    apiGet('/metrics/').then((r) => setMetrics(r || [])).catch(() => {});
    apiGet('/indicators/').then((r) => setIndicators(r || [])).catch(() => {});
    apiGet('/dimensions/').then((r) => setDimensions(r || [])).catch(() => {});
  }, []);

  // ── Lista de tablas ─────────────────────────────────────────────────
  const reloadList = () => {
    setLoadingList(true);
    apiGet('/tables/')
      .then((r) => setTables(Array.isArray(r) ? r : []))
      .catch((e) => toast.error(`Error cargando tablas: ${e.message}`))
      .finally(() => setLoadingList(false));
  };
  useEffect(reloadList, []);

  // ── Detalle de la seleccionada ─────────────────────────────────────
  useEffect(() => {
    if (!selectedId) return;
    apiGet(`/tables/${selectedId}`).then((r) => {
      setDraftMeta({
        name: r.name || '',
        description: r.description || '',
        is_draft: r.is_draft ?? true,
      });
      setDraftConfig(r.config || EMPTY_CONFIG);
      setUnsaved(false);
    }).catch((e) => toast.error(`Error cargando tabla: ${e.message}`));
  }, [selectedId]);

  // ── Columnas disponibles según métrica seleccionada ────────────────
  // Resuelve localmente desde los catálogos ya cargados (metrics + dimensions).
  // Evita llamada extra a /api/metrics/{id} que NO existe en el backend.
  const metricColumns = useMemo(() => {
    const mid = draftConfig?.data_source?.metric_id;
    if (!mid) return [];
    const m = metrics.find((x) => x.id_metric === mid);
    if (!m) return [];
    const cols = [];
    // Dimensiones — resolver nombre desde el catálogo global
    const dimById = new Map(dimensions.map((d) => [d.id_dimension, d]));
    (m.dimension_ids || []).forEach((id) => {
      const d = dimById.get(id);
      if (d) cols.push({ key: d.name, kind: 'dimension', type: d.data_type });
    });
    // Fields del meta_json (data_type=object → meta.fields[*])
    try {
      const meta = typeof m.meta_json === 'string' ? JSON.parse(m.meta_json || '{}') : (m.meta_json || {});
      (meta.fields || []).forEach((f) => cols.push({ key: f.name, kind: 'field', type: f.type }));
    } catch (e) {}
    return cols;
  }, [draftConfig?.data_source?.metric_id, metrics, dimensions]);

  // ── Helpers de mutación ─────────────────────────────────────────────
  const updateConfig = (updater) => {
    setDraftConfig((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      return next;
    });
    setUnsaved(true);
  };

  const updateMeta = (patch) => {
    setDraftMeta((prev) => ({ ...prev, ...patch }));
    setUnsaved(true);
  };

  const handleNew = () => {
    setSelectedId(null);
    setDraftMeta({ name: 'Nueva tabla', description: '', is_draft: true });
    setDraftConfig(EMPTY_CONFIG);
    setUnsaved(true);
    setActiveTab('source');
  };

  const handleSave = async () => {
    if (!draftMeta.name?.trim()) {
      toast.error('Nombre obligatorio');
      return;
    }
    if (!draftConfig.data_source?.metric_id) {
      toast.error('Selecciona una métrica en el tab Origen');
      return;
    }
    setSaving(true);
    try {
      if (selectedId) {
        await apiPut(`/tables/${selectedId}`, {
          name: draftMeta.name,
          description: draftMeta.description,
          is_draft: draftMeta.is_draft,
          config: draftConfig,
        });
        toast.success('Tabla guardada');
      } else {
        const r = await apiPost('/tables/', {
          name: draftMeta.name,
          description: draftMeta.description,
          is_draft: draftMeta.is_draft,
          config: draftConfig,
        });
        setSelectedId(r.id_spec);
        toast.success(`Tabla creada (id ${r.id_spec})`);
      }
      setUnsaved(false);
      reloadList();
    } catch (e) {
      toast.error(`Error guardando: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDuplicate = async () => {
    if (!selectedId) return;
    try {
      const r = await apiPost(`/tables/${selectedId}/duplicate`, {});
      toast.success(`Duplicada (id ${r.id_spec})`);
      reloadList();
      setSelectedId(r.id_spec);
    } catch (e) { toast.error(e.message); }
  };

  const handleDelete = async () => {
    if (!selectedId) return;
    if (!confirm(`¿Eliminar "${draftMeta.name}"?`)) return;
    try {
      await apiDelete(`/tables/${selectedId}`);
      toast.success('Eliminada');
      setSelectedId(null);
      setDraftConfig(EMPTY_CONFIG);
      setDraftMeta({ name: '', description: '', is_draft: true });
      reloadList();
    } catch (e) { toast.error(e.message); }
  };

  // ── Filtro sidebar ──────────────────────────────────────────────────
  const filteredTables = useMemo(() => {
    if (!filter.trim()) return tables;
    const q = filter.toLowerCase();
    return tables.filter((t) =>
      (t.name || '').toLowerCase().includes(q) ||
      String(t.metric_id || '').includes(q)
    );
  }, [tables, filter]);

  return (
    <div className="grid grid-cols-12 gap-3 h-[calc(100vh-100px)]">
      {/* SIDEBAR */}
      <aside className="col-span-3 lg:col-span-2 flex flex-col bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
        <div className="p-2 border-b border-slate-200 bg-slate-50">
          <button
            onClick={handleNew}
            className="w-full inline-flex items-center justify-center gap-1 px-2 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            <Plus size={14} /> Nueva tabla
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
          {!loadingList && filteredTables.length === 0 && (
            <div className="p-3 text-xs text-slate-400">Sin tablas. Crea una nueva.</div>
          )}
          {filteredTables.map((t) => {
            const isSel = t.id_spec === selectedId;
            return (
              <button
                key={t.id_spec}
                onClick={() => setSelectedId(t.id_spec)}
                className={`w-full text-left px-3 py-2 border-b border-slate-100 hover:bg-slate-50 ${isSel ? 'bg-indigo-50 border-l-2 border-l-indigo-500' : ''}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800 truncate">{t.name}</span>
                  {t.is_draft && <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">draft</span>}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  Métrica {t.metric_id ?? '—'} · {t.n_columns} cols
                </div>
              </button>
            );
          })}
        </div>
      </aside>

      {/* EDITOR */}
      <main className="col-span-5 lg:col-span-5 flex flex-col bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
        {/* Header del editor */}
        <div className="flex items-start justify-between gap-3 p-3 border-b border-slate-200 bg-slate-50">
          <div className="flex-1 min-w-0">
            <input
              type="text"
              value={draftMeta.name}
              onChange={(e) => updateMeta({ name: e.target.value })}
              placeholder="Nombre de la tabla"
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
              Publicada
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
                <button
                  onClick={handleDuplicate}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs border border-slate-300 rounded hover:bg-slate-100"
                  title="Duplicar"
                ><Copy size={12} /></button>
                <button
                  onClick={handleDelete}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs border border-rose-300 text-rose-600 rounded hover:bg-rose-50"
                  title="Eliminar"
                ><Trash2 size={12} /></button>
              </>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-200 bg-white">
          {[
            { id: 'source', label: 'Origen', icon: Database },
            { id: 'columns', label: 'Columnas', icon: Columns },
            { id: 'behavior', label: 'Comportamiento', icon: Sliders },
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

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'source' && (
            <SourceTab
              cfg={draftConfig}
              metrics={metrics}
              metricColumns={metricColumns}
              onChange={(ds) => updateConfig((p) => ({ ...p, data_source: ds }))}
            />
          )}
          {activeTab === 'columns' && (
            <ColumnsTab
              cfg={draftConfig}
              metricColumns={metricColumns}
              indicators={indicators}
              onChange={(cols) => updateConfig((p) => ({ ...p, columns: cols }))}
            />
          )}
          {activeTab === 'behavior' && (
            <BehaviorTab
              cfg={draftConfig}
              metricColumns={metricColumns}
              onChange={(b) => updateConfig((p) => ({ ...p, behavior: b }))}
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
        <div className="flex-1 overflow-hidden">
          {draftConfig?.data_source?.metric_id ? (
            <TableRenderer
              draftConfig={draftConfig}
              pageSize={20}
              className="h-full"
              key={JSON.stringify(draftConfig)}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-slate-400 text-sm bg-white border border-dashed border-slate-300 rounded">
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
// Tab: Origen (data source)
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
        {ds.metric_id && (
          <p className="text-[11px] text-slate-500 mt-1">
            {dimColumns.length} dimensiones · {metricColumns.filter((c) => c.kind === 'field').length} valores
          </p>
        )}
      </div>

      {ds.metric_id && dimColumns.length > 0 && (
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Filtros base (igualdad)</label>
          <p className="text-[11px] text-slate-500 mb-2">
            Filtros aplicados siempre. Usa <code>extra_filters</code> para filtros del consumidor (dashboard/PDF).
          </p>
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
// Tab: Columnas
// ─────────────────────────────────────────────────────────────────────

function ColumnsTab({ cfg, metricColumns, indicators, onChange }) {
  const cols = cfg.columns || [];
  // Para una columna ya usada: si es dimensión la ocultamos (no tiene
  // sentido duplicarla); si es field numérico la mantenemos visible
  // para permitir multi-agg (ej Logro mean + Logro max).
  const usedSources = new Set(cols.map((c) => c.source_key || c.key));
  const available = metricColumns.filter((mc) => {
    if (mc.kind === 'dimension') return !usedSources.has(mc.key);
    return true; // fields siempre disponibles para re-agregar
  });

  const addColumn = (key) => {
    const meta = metricColumns.find((m) => m.key === key);
    const isNumeric = meta && (meta.type === 'int' || meta.type === 'float');
    // Si la key ya existe en alguna columna, generar alias único usando
    // source_key. Permite multi-agg sobre la misma columna fuente
    // (ej Logro_mean / Logro_max / Logro_min en una tabla resumen).
    const existingKeys = new Set(cols.map((c) => c.key));
    const isDuplicate = existingKeys.has(key);
    let newKey = key;
    if (isDuplicate) {
      // Buscar suffix libre
      const candidates = ['mean', 'max', 'min', 'sum', 'count', 'std', '2', '3', '4'];
      for (const suffix of candidates) {
        const candidate = `${key}_${suffix}`;
        if (!existingKeys.has(candidate)) {
          newKey = candidate;
          break;
        }
      }
      // Fallback: timestamp
      if (newKey === key) newKey = `${key}_${Date.now() % 10000}`;
    }
    onChange([...cols, {
      key: newKey,
      header: isDuplicate ? newKey : key,
      source_key: isDuplicate ? key : null,
      format: isNumeric ? 'float' : 'text',
      decimals: 1,
      agg: isDuplicate ? 'mean' : null,
      color_scale: null,
      width: null,
      pinned: false,
      hidden: false,
    }]);
  };
  const updateCol = (idx, patch) => {
    onChange(cols.map((c, i) => (i === idx ? { ...c, ...patch } : c)));
  };
  const removeCol = (idx) => onChange(cols.filter((_, i) => i !== idx));
  const moveCol = (idx, dir) => {
    const ni = idx + dir;
    if (ni < 0 || ni >= cols.length) return;
    const next = [...cols];
    [next[idx], next[ni]] = [next[ni], next[idx]];
    onChange(next);
  };

  return (
    <div className="space-y-4">
      {available.length > 0 && (
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Agregar columna</label>
          <div className="flex flex-wrap gap-1">
            {available.map((c) => (
              <button
                key={c.key}
                onClick={() => addColumn(c.key)}
                className={`text-[11px] px-2 py-1 rounded border ${c.kind === 'dimension'
                  ? 'border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100'
                  : 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'}`}
              >
                + {c.key} <span className="opacity-60">({c.type})</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-1">Columnas en la tabla ({cols.length})</label>
        {cols.length === 0 && <p className="text-xs text-slate-400">Aún sin columnas. Agrega arriba.</p>}
        <div className="space-y-2">
          {cols.map((c, idx) => (
            <ColumnRow
              key={`${c.key}-${idx}`}
              col={c}
              idx={idx}
              total={cols.length}
              indicators={indicators}
              onUpdate={(patch) => updateCol(idx, patch)}
              onRemove={() => removeCol(idx)}
              onMove={(dir) => moveCol(idx, dir)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function ColumnRow({ col, idx, total, indicators, onUpdate, onRemove, onMove }) {
  const [expanded, setExpanded] = useState(false);
  const isNumeric = ['int', 'float', 'percent'].includes(col.format);
  return (
    <div className="border border-slate-200 rounded bg-slate-50">
      <div className="flex items-center gap-2 px-2 py-1.5">
        <button onClick={() => setExpanded((v) => !v)} className="text-slate-400 hover:text-slate-700">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <GripVertical size={12} className="text-slate-300" />
        <span className="text-xs font-mono text-slate-500 w-6 text-right">{idx + 1}.</span>
        <input
          type="text"
          value={col.header}
          onChange={(e) => onUpdate({ header: e.target.value })}
          className="flex-1 px-2 py-0.5 text-sm border border-slate-200 rounded bg-white"
        />
        <select
          value={col.format}
          onChange={(e) => onUpdate({ format: e.target.value })}
          className="px-1 py-0.5 text-xs border border-slate-200 rounded bg-white"
          title="Formato"
        >
          {['text', 'int', 'float', 'percent', 'date'].map((f) => (
            <option key={f} value={f}>{f}</option>
          ))}
        </select>
        <button
          onClick={() => onUpdate({ hidden: !col.hidden })}
          className="text-slate-400 hover:text-slate-700"
          title={col.hidden ? 'Oculta — clic para mostrar' : 'Ocultar columna'}
        >
          {col.hidden ? <EyeOff size={12} /> : <Eye size={12} />}
        </button>
        <button onClick={() => onMove(-1)} disabled={idx === 0} className="text-slate-400 hover:text-slate-700 disabled:opacity-30">↑</button>
        <button onClick={() => onMove(1)} disabled={idx === total - 1} className="text-slate-400 hover:text-slate-700 disabled:opacity-30">↓</button>
        <button onClick={onRemove} className="text-rose-400 hover:text-rose-600"><X size={12} /></button>
      </div>
      {expanded && (
        <div className="border-t border-slate-200 px-3 py-2 bg-white space-y-2 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-slate-500 mb-0.5">Key (alias en la tabla)</label>
              <input
                type="text"
                value={col.key}
                onChange={(e) => onUpdate({ key: e.target.value })}
                className="w-full px-1.5 py-0.5 border border-slate-200 rounded font-mono"
              />
            </div>
            <div>
              <label className="block text-slate-500 mb-0.5">
                Source (campo fuente en data) <span className="text-slate-400 normal-case">— opcional, para multi-agg</span>
              </label>
              <input
                type="text"
                value={col.source_key || ''}
                onChange={(e) => onUpdate({ source_key: e.target.value || null })}
                placeholder={`(usa "${col.key}")`}
                className="w-full px-1.5 py-0.5 border border-slate-200 rounded font-mono"
              />
            </div>
            {isNumeric && (
              <div>
                <label className="block text-slate-500 mb-0.5">Decimales</label>
                <input
                  type="number" min={0} max={6}
                  value={col.decimals}
                  onChange={(e) => onUpdate({ decimals: Number(e.target.value) })}
                  className="w-full px-1.5 py-0.5 border border-slate-200 rounded"
                />
              </div>
            )}
            <div>
              <label className="block text-slate-500 mb-0.5">Aggregación (cuando hay grouping)</label>
              <select
                value={col.agg || ''}
                onChange={(e) => onUpdate({ agg: e.target.value || null })}
                className="w-full px-1.5 py-0.5 border border-slate-200 rounded"
              >
                <option value="">(ninguna)</option>
                {['mean', 'sum', 'min', 'max', 'count', 'nunique', 'first'].map((a) =>
                  <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-slate-500 mb-0.5">Ancho (px, opcional)</label>
              <input
                type="number"
                value={col.width || ''}
                onChange={(e) => onUpdate({ width: e.target.value ? Number(e.target.value) : null })}
                className="w-full px-1.5 py-0.5 border border-slate-200 rounded"
                placeholder="auto"
              />
            </div>
          </div>
          <ColorScaleEditor
            scale={col.color_scale}
            onChange={(s) => onUpdate({ color_scale: s })}
            indicators={indicators}
          />
        </div>
      )}
    </div>
  );
}

function ColorScaleEditor({ scale, onChange, indicators }) {
  const kind = scale?.kind || '';
  return (
    <div className="border-t border-slate-100 pt-2">
      <label className="block text-slate-500 mb-1">Color por celda</label>
      <select
        value={kind}
        onChange={(e) => {
          const k = e.target.value;
          if (!k) return onChange(null);
          if (k === 'linked_indicator') return onChange({ kind: 'linked_indicator', indicator_id: indicators[0]?.id_indicator || null, level_field: 'Nivel Logro' });
          if (k === 'diverging') return onChange({ kind: 'diverging', min_color: '#ef4444', neutral_color: '#fef3c7', max_color: '#22c55e', midpoint: 0.5 });
          if (k === 'sequential') return onChange({ kind: 'sequential', base_color: '#3b82f6' });
        }}
        className="w-full px-1.5 py-0.5 border border-slate-200 rounded"
      >
        <option value="">— Sin color —</option>
        <option value="linked_indicator">Vinculado a indicador (achievement_levels)</option>
        <option value="diverging">Divergente (rojo→amarillo→verde)</option>
        <option value="sequential">Secuencial (color base)</option>
      </select>
      {kind === 'linked_indicator' && (
        <div className="grid grid-cols-2 gap-2 mt-2">
          <div>
            <label className="block text-slate-500 mb-0.5">Indicador</label>
            <select
              value={scale.indicator_id || ''}
              onChange={(e) => onChange({ ...scale, indicator_id: Number(e.target.value) })}
              className="w-full px-1.5 py-0.5 border border-slate-200 rounded"
            >
              <option value="">—</option>
              {indicators.map((i) => <option key={i.id_indicator} value={i.id_indicator}>[{i.id_indicator}] {i.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-slate-500 mb-0.5">Columna con nivel</label>
            <input
              type="text" value={scale.level_field || ''}
              onChange={(e) => onChange({ ...scale, level_field: e.target.value })}
              className="w-full px-1.5 py-0.5 border border-slate-200 rounded"
              placeholder="Nivel Logro"
            />
          </div>
        </div>
      )}
      {kind === 'diverging' && (
        <div className="grid grid-cols-4 gap-2 mt-2">
          <ColorInput label="Bajo" value={scale.min_color} onChange={(v) => onChange({ ...scale, min_color: v })} />
          <ColorInput label="Neutro" value={scale.neutral_color} onChange={(v) => onChange({ ...scale, neutral_color: v })} />
          <ColorInput label="Alto" value={scale.max_color} onChange={(v) => onChange({ ...scale, max_color: v })} />
          <div>
            <label className="block text-slate-500 mb-0.5">Punto medio</label>
            <input type="number" step="0.1" value={scale.midpoint}
              onChange={(e) => onChange({ ...scale, midpoint: Number(e.target.value) })}
              className="w-full px-1.5 py-0.5 border border-slate-200 rounded" />
          </div>
        </div>
      )}
      {kind === 'sequential' && (
        <ColorInput label="Color base" value={scale.base_color} onChange={(v) => onChange({ ...scale, base_color: v })} />
      )}
    </div>
  );
}

function ColorInput({ label, value, onChange }) {
  return (
    <div>
      <label className="block text-slate-500 mb-0.5">{label}</label>
      <div className="flex items-center gap-1">
        <input type="color" value={value} onChange={(e) => onChange(e.target.value)} className="w-8 h-7 border-0 p-0 rounded" />
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)} className="flex-1 px-1 py-0.5 border border-slate-200 rounded font-mono text-[11px]" />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Tab: Comportamiento
// ─────────────────────────────────────────────────────────────────────

function BehaviorTab({ cfg, metricColumns, onChange }) {
  const b = cfg.behavior || {};
  const update = (patch) => onChange({ ...b, ...patch });
  const allCols = (cfg.columns || []).map((c) => c.key);

  return (
    <div className="space-y-5 text-sm">
      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-1">Agrupar por</label>
        <select
          value={b.grouping?.by || ''}
          onChange={(e) => update({ grouping: e.target.value ? { by: e.target.value } : null })}
          className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded"
        >
          <option value="">— Sin agrupación —</option>
          {metricColumns.filter((c) => c.kind === 'dimension').map((c) =>
            <option key={c.key} value={c.key}>{c.key}</option>)}
        </select>
        {b.grouping && (
          <p className="text-[11px] text-slate-500 mt-1">
            Define `agg` por columna en el tab Columnas (mean/sum/min/max…).
          </p>
        )}
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-1">Orden inicial</label>
        {(b.sorting || []).map((s, i) => (
          <div key={i} className="flex items-center gap-2 mb-1">
            <select
              value={s.column}
              onChange={(e) => {
                const next = [...b.sorting];
                next[i] = { ...next[i], column: e.target.value };
                update({ sorting: next });
              }}
              className="flex-1 px-2 py-1 text-xs border border-slate-200 rounded"
            >
              {allCols.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select
              value={s.dir}
              onChange={(e) => {
                const next = [...b.sorting];
                next[i] = { ...next[i], dir: e.target.value };
                update({ sorting: next });
              }}
              className="px-1.5 py-1 text-xs border border-slate-200 rounded"
            >
              <option value="asc">↑ asc</option>
              <option value="desc">↓ desc</option>
            </select>
            <button onClick={() => update({ sorting: b.sorting.filter((_, j) => j !== i) })}
              className="text-rose-400 hover:text-rose-600"><X size={12} /></button>
          </div>
        ))}
        <button
          onClick={() => update({ sorting: [...(b.sorting || []), { column: allCols[0] || '', dir: 'asc' }] })}
          disabled={!allCols.length}
          className="text-xs text-indigo-600 hover:text-indigo-700 disabled:opacity-50"
        >+ Agregar criterio de orden</button>
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-1">Paginación</label>
        <div className="flex items-center gap-3">
          <label className="inline-flex items-center gap-1 text-xs">
            <input
              type="checkbox" checked={b.pagination?.enabled ?? true}
              onChange={(e) => update({ pagination: { ...b.pagination, enabled: e.target.checked } })}
              className="accent-indigo-600"
            /> Habilitada
          </label>
          <label className="inline-flex items-center gap-1 text-xs">
            Tamaño:
            <input
              type="number" min={5} max={500}
              value={b.pagination?.page_size ?? 50}
              onChange={(e) => update({ pagination: { ...b.pagination, page_size: Number(e.target.value) } })}
              className="w-16 px-1.5 py-0.5 border border-slate-200 rounded"
            />
          </label>
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-1">Export</label>
        <div className="flex items-center gap-3 text-xs">
          <label className="inline-flex items-center gap-1">
            <input
              type="checkbox" checked={b.export?.csv ?? true}
              onChange={(e) => update({ export: { ...b.export, csv: e.target.checked } })}
              className="accent-indigo-600"
            /> CSV
          </label>
          <label className="inline-flex items-center gap-1">
            <input
              type="checkbox" checked={b.export?.xlsx ?? true}
              onChange={(e) => update({ export: { ...b.export, xlsx: e.target.checked } })}
              className="accent-indigo-600"
            /> XLSX
          </label>
        </div>
      </div>

      <div>
        <label className="inline-flex items-center gap-1 text-xs font-semibold text-slate-700">
          <input
            type="checkbox" checked={b.search ?? true}
            onChange={(e) => update({ search: e.target.checked })}
            className="accent-indigo-600"
          /> Búsqueda global
        </label>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// API helpers
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
