/**
 * MappingsManager — editor de mapeos (B10).
 *
 * Layout 3 paneles análogo a /tables y /charts:
 *   [Sidebar lista]  [Editor (kind + ranges/dict + default)]  [Preview live]
 *
 * Cada mapeo = Spec con type='Mapeo'. CRUD vía /api/mappings.
 * Preview live: POST /api/mappings/preview con la config draft + valores de prueba.
 */
import { useEffect, useMemo, useState } from 'react';
import {
  Plus, Save, Trash2, Copy, Search, X, Loader2, AlertCircle,
  Eye, ListTree, ArrowRightLeft,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../../constants';

const EMPTY_RANGE_CONFIG = {
  version: 1,
  kind: 'range',
  ranges: [
    { min: 0, max: 40, label: 'Bajo' },
    { min: 40, max: 70, label: 'Medio' },
    { min: 70, max: null, label: 'Alto' },
  ],
  match: 'left_inclusive',
  default: 'No Aplica',
  input_field_type: 'numeric',
  input_domain: '',
  mapping: {},
  case_insensitive: false,
};

const EMPTY_DISCRETE_CONFIG = {
  version: 1,
  kind: 'discrete',
  ranges: [],
  match: 'left_inclusive',
  mapping: { '1': 'Primeros', '2': 'Segundos' },
  case_insensitive: false,
  default: null,
  extract: null,
  input_field_type: 'string',
  input_domain: '',
};

export default function MappingsManager() {
  const [list, setList] = useState([]);
  const [loadingList, setLoadingList] = useState(false);
  const [filter, setFilter] = useState('');

  const [selectedId, setSelectedId] = useState(null);
  const [draftMeta, setDraftMeta] = useState({ name: '', description: '', is_draft: true });
  const [draftConfig, setDraftConfig] = useState(EMPTY_RANGE_CONFIG);
  const [unsaved, setUnsaved] = useState(false);
  const [saving, setSaving] = useState(false);

  const [previewValues, setPreviewValues] = useState('0\n45\n80\n200\nx\n');
  const [previewResult, setPreviewResult] = useState([]);
  const [previewing, setPreviewing] = useState(false);

  const reloadList = () => {
    setLoadingList(true);
    apiGet('/mappings/')
      .then((r) => setList(Array.isArray(r) ? r : []))
      .catch((e) => toast.error(`Error: ${e.message}`))
      .finally(() => setLoadingList(false));
  };
  useEffect(reloadList, []);

  useEffect(() => {
    if (!selectedId) return;
    apiGet(`/mappings/${selectedId}`).then((r) => {
      setDraftMeta({
        name: r.name || '',
        description: r.description || '',
        is_draft: r.is_draft ?? true,
      });
      setDraftConfig(r.config || EMPTY_RANGE_CONFIG);
      setUnsaved(false);
    }).catch((e) => toast.error(`Error: ${e.message}`));
  }, [selectedId]);

  // Auto-preview cuando cambia config o valores de prueba
  useEffect(() => {
    if (!draftConfig || (!draftConfig.ranges?.length && !Object.keys(draftConfig.mapping || {}).length)) {
      setPreviewResult([]);
      return;
    }
    const values = previewValues.split('\n').map((v) => v.trim()).filter((v) => v !== '');
    if (values.length === 0) { setPreviewResult([]); return; }
    setPreviewing(true);
    apiPost('/mappings/preview', { config: draftConfig, values })
      .then((r) => setPreviewResult(Array.isArray(r) ? r : []))
      .catch(() => setPreviewResult([]))
      .finally(() => setPreviewing(false));
  }, [draftConfig, previewValues]);

  const updateConfig = (patch) => {
    setDraftConfig((prev) => ({ ...prev, ...patch }));
    setUnsaved(true);
  };
  const updateMeta = (patch) => {
    setDraftMeta((prev) => ({ ...prev, ...patch }));
    setUnsaved(true);
  };

  const handleNew = (kind = 'range') => {
    setSelectedId(null);
    setDraftMeta({ name: 'Nuevo mapeo', description: '', is_draft: true });
    setDraftConfig(kind === 'range' ? EMPTY_RANGE_CONFIG : EMPTY_DISCRETE_CONFIG);
    setUnsaved(true);
  };

  const handleSave = async () => {
    if (!draftMeta.name?.trim()) { toast.error('Nombre obligatorio'); return; }
    setSaving(true);
    try {
      if (selectedId) {
        await apiPut(`/mappings/${selectedId}`, {
          name: draftMeta.name,
          description: draftMeta.description,
          is_draft: draftMeta.is_draft,
          config: draftConfig,
        });
        toast.success('Mapeo guardado');
      } else {
        const r = await apiPost('/mappings/', {
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
      const r = await apiPost(`/mappings/${selectedId}/duplicate`, {});
      toast.success(`Duplicado (id ${r.id_spec})`);
      reloadList();
      setSelectedId(r.id_spec);
    } catch (e) { toast.error(e.message); }
  };

  const handleDelete = async () => {
    if (!selectedId) return;
    if (!confirm(`¿Eliminar "${draftMeta.name}"?`)) return;
    try {
      await apiDelete(`/mappings/${selectedId}`);
      toast.success('Eliminado');
      setSelectedId(null);
      setDraftConfig(EMPTY_RANGE_CONFIG);
      setDraftMeta({ name: '', description: '', is_draft: true });
      reloadList();
    } catch (e) { toast.error(e.message); }
  };

  const filtered = useMemo(() => {
    if (!filter.trim()) return list;
    const q = filter.toLowerCase();
    return list.filter((m) => (m.name || '').toLowerCase().includes(q));
  }, [list, filter]);

  return (
    <div className="grid grid-cols-12 gap-3 h-[calc(100vh-220px)]">
      {/* SIDEBAR */}
      <aside className="col-span-3 lg:col-span-2 flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded shadow-sm overflow-hidden">
        <div className="p-2 border-b border-slate-200 bg-slate-50 dark:bg-slate-800 dark:border-slate-700 space-y-1.5">
          <div className="grid grid-cols-2 gap-1">
            <button
              onClick={() => handleNew('range')}
              className="inline-flex items-center justify-center gap-1 px-2 py-1.5 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700"
            >
              <Plus size={12} /> Rango
            </button>
            <button
              onClick={() => handleNew('discrete')}
              className="inline-flex items-center justify-center gap-1 px-2 py-1.5 text-xs bg-emerald-600 text-white rounded hover:bg-emerald-700"
            >
              <Plus size={12} /> Discreto
            </button>
          </div>
          <div className="relative">
            <Search size={12} className="absolute top-1.5 left-2 text-slate-400" />
            <input
              type="text" value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filtrar…"
              className="w-full pl-7 pr-2 py-1 text-xs border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loadingList && <div className="p-3 text-xs text-slate-400">Cargando…</div>}
          {!loadingList && filtered.length === 0 && (
            <div className="p-3 text-xs text-slate-400">Sin mapeos. Crea uno con los botones de arriba.</div>
          )}
          {filtered.map((m) => {
            const isSel = m.id_spec === selectedId;
            const Icon = m.kind === 'range' ? ListTree : ArrowRightLeft;
            return (
              <button
                key={m.id_spec}
                onClick={() => setSelectedId(m.id_spec)}
                className={`w-full text-left px-3 py-2 border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 ${isSel ? 'bg-indigo-50 dark:bg-indigo-900/20 border-l-2 border-l-indigo-500' : ''}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate inline-flex items-center gap-1">
                    <Icon size={12} className="text-slate-400 flex-shrink-0" /> {m.name}
                  </span>
                  {m.is_draft && <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">draft</span>}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  {m.kind || '—'} · {m.n_entries} {m.kind === 'range' ? 'tramos' : 'claves'}
                </div>
              </button>
            );
          })}
        </div>
      </aside>

      {/* EDITOR */}
      <main className="col-span-5 lg:col-span-5 flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded shadow-sm overflow-hidden">
        <div className="flex items-start justify-between gap-3 p-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
          <div className="flex-1 min-w-0">
            <input
              type="text"
              value={draftMeta.name}
              onChange={(e) => updateMeta({ name: e.target.value })}
              placeholder="Nombre del mapeo"
              className="w-full text-base font-semibold bg-transparent border-0 focus:outline-none focus:ring-0 text-slate-900 dark:text-slate-100"
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
            <label className="inline-flex items-center gap-1 text-xs text-slate-600 dark:text-slate-300 cursor-pointer">
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
                <button onClick={handleDuplicate} className="px-2 py-1 text-xs border border-slate-300 rounded hover:bg-slate-100 dark:hover:bg-slate-700" title="Duplicar"><Copy size={12} /></button>
                <button onClick={handleDelete} className="px-2 py-1 text-xs border border-rose-300 text-rose-600 rounded hover:bg-rose-50" title="Eliminar"><Trash2 size={12} /></button>
              </>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Tipo + meta */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Tipo</label>
              <select
                value={draftConfig.kind}
                onChange={(e) => {
                  const newKind = e.target.value;
                  if (newKind === 'range') {
                    updateConfig({ kind: 'range', ranges: draftConfig.ranges?.length ? draftConfig.ranges : EMPTY_RANGE_CONFIG.ranges });
                  } else {
                    updateConfig({ kind: 'discrete', mapping: Object.keys(draftConfig.mapping || {}).length ? draftConfig.mapping : EMPTY_DISCRETE_CONFIG.mapping });
                  }
                }}
                className="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 dark:bg-slate-800 rounded"
              >
                <option value="range">Por rangos (numérico)</option>
                <option value="discrete">Discreto (mapping clave→valor)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Default (si no clasifica)
              </label>
              <input
                type="text"
                value={draftConfig.default ?? ''}
                onChange={(e) => updateConfig({ default: e.target.value || null })}
                placeholder="(deja vacío = null)"
                className="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 dark:bg-slate-800 rounded"
              />
            </div>
          </div>

          {/* Editor por tipo */}
          {draftConfig.kind === 'range' ? (
            <RangeEditor cfg={draftConfig} onChange={updateConfig} />
          ) : (
            <DiscreteEditor cfg={draftConfig} onChange={updateConfig} />
          )}

          {/* Metadata semántica */}
          <details className="text-xs text-slate-500">
            <summary className="cursor-pointer hover:text-slate-700">
              Metadatos avanzados (tipo de campo esperado, dominio)
            </summary>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-semibold mb-0.5">Tipo de campo entrada</label>
                <select
                  value={draftConfig.input_field_type || 'numeric'}
                  onChange={(e) => updateConfig({ input_field_type: e.target.value })}
                  className="w-full px-2 py-1 text-xs border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded"
                >
                  <option value="numeric">Numérico</option>
                  <option value="string">Texto</option>
                  <option value="any">Cualquiera</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-semibold mb-0.5">Dominio (informativo)</label>
                <input
                  type="text"
                  value={draftConfig.input_domain || ''}
                  onChange={(e) => updateConfig({ input_domain: e.target.value })}
                  placeholder="ej: 0-100, 0-1, palabras/min"
                  className="w-full px-2 py-1 text-xs border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded"
                />
              </div>
            </div>
          </details>
        </div>
      </main>

      {/* PREVIEW */}
      <aside className="col-span-4 lg:col-span-5 flex flex-col gap-2 overflow-hidden">
        <div className="text-xs text-slate-500 px-1 inline-flex items-center gap-1">
          <Eye size={12} /> Probar mapeo
          {unsaved && <span className="text-amber-600">· cambios sin guardar</span>}
        </div>
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-3 flex flex-col flex-1 overflow-hidden">
          <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
            Valores de prueba (uno por línea)
          </label>
          <textarea
            value={previewValues}
            onChange={(e) => setPreviewValues(e.target.value)}
            rows={4}
            className="w-full px-2 py-1.5 text-xs font-mono border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded resize-none"
            placeholder="0&#10;45&#10;80&#10;200"
          />

          <div className="flex-1 overflow-y-auto mt-3">
            {previewing && <div className="text-xs text-slate-400 text-center py-2"><Loader2 size={14} className="animate-spin inline-block" /> Procesando…</div>}
            {!previewing && previewResult.length === 0 && (
              <div className="text-xs text-slate-400 text-center py-6 inline-flex flex-col items-center gap-1 w-full">
                <AlertCircle size={20} className="opacity-40" />
                Escribe valores arriba para probar el mapeo
              </div>
            )}
            {previewResult.length > 0 && (
              <table className="w-full text-xs">
                <thead className="text-slate-500 border-b border-slate-200 dark:border-slate-700">
                  <tr>
                    <th className="text-left py-1.5 px-2 font-semibold">Valor</th>
                    <th className="text-left py-1.5 px-2 font-semibold">→ Resultado</th>
                  </tr>
                </thead>
                <tbody>
                  {previewResult.map((r, i) => (
                    <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="py-1 px-2 font-mono">{String(r.value)}</td>
                      <td className="py-1 px-2">
                        {r.matched ? (
                          <span className="font-semibold text-emerald-700">{r.label}</span>
                        ) : r.label ? (
                          <span className="text-slate-500 italic">{r.label} <span className="text-[10px] text-amber-600">(default)</span></span>
                        ) : (
                          <span className="text-rose-500 italic">— sin match —</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────
// RangeEditor
// ─────────────────────────────────────────────────────────────────

function RangeEditor({ cfg, onChange }) {
  const ranges = cfg.ranges || [];

  const updateRange = (idx, patch) => {
    const next = ranges.map((r, i) => (i === idx ? { ...r, ...patch } : r));
    onChange({ ranges: next });
  };
  const addRange = () => {
    const last = ranges[ranges.length - 1];
    const min = last?.max ?? 0;
    onChange({ ranges: [...ranges, { min, max: null, label: 'Nuevo' }] });
  };
  const removeRange = (idx) => {
    onChange({ ranges: ranges.filter((_, i) => i !== idx) });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-slate-700 dark:text-slate-300">Tramos</h3>
        <div className="flex items-center gap-2">
          <select
            value={cfg.match || 'left_inclusive'}
            onChange={(e) => onChange({ match: e.target.value })}
            className="text-[11px] px-1.5 py-0.5 border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded"
            title="Comportamiento en los bordes"
          >
            <option value="left_inclusive">[min, max) izq inclusivo</option>
            <option value="right_inclusive">(min, max] der inclusivo</option>
            <option value="both_inclusive">[min, max] ambos inclusivo</option>
          </select>
          <button
            onClick={addRange}
            className="text-xs text-indigo-600 hover:text-indigo-700 inline-flex items-center gap-1"
          >
            <Plus size={12} /> Agregar tramo
          </button>
        </div>
      </div>
      <table className="w-full text-xs">
        <thead className="text-slate-500 border-b border-slate-200 dark:border-slate-700">
          <tr>
            <th className="text-left py-1.5 px-2 font-semibold w-20">Mín</th>
            <th className="text-left py-1.5 px-2 font-semibold w-20">Máx</th>
            <th className="text-left py-1.5 px-2 font-semibold">Label</th>
            <th className="w-8"></th>
          </tr>
        </thead>
        <tbody>
          {ranges.map((r, idx) => (
            <tr key={idx} className="border-b border-slate-100 dark:border-slate-800">
              <td className="py-1 px-2">
                <input
                  type="number" step="0.01"
                  value={r.min ?? ''}
                  onChange={(e) => updateRange(idx, { min: e.target.value === '' ? null : Number(e.target.value) })}
                  placeholder="-∞"
                  className="w-full px-1.5 py-0.5 text-xs border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded font-mono"
                />
              </td>
              <td className="py-1 px-2">
                <input
                  type="number" step="0.01"
                  value={r.max ?? ''}
                  onChange={(e) => updateRange(idx, { max: e.target.value === '' ? null : Number(e.target.value) })}
                  placeholder="+∞"
                  className="w-full px-1.5 py-0.5 text-xs border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded font-mono"
                />
              </td>
              <td className="py-1 px-2">
                <input
                  type="text"
                  value={r.label}
                  onChange={(e) => updateRange(idx, { label: e.target.value })}
                  className="w-full px-1.5 py-0.5 text-xs border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded"
                />
              </td>
              <td className="py-1 px-1">
                <button onClick={() => removeRange(idx)} className="text-rose-400 hover:text-rose-600">
                  <X size={12} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {ranges.length === 0 && <p className="text-xs text-slate-400 text-center py-3">Sin tramos. Agrega uno arriba.</p>}
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────
// DiscreteEditor
// ─────────────────────────────────────────────────────────────────

function DiscreteEditor({ cfg, onChange }) {
  const mapping = cfg.mapping || {};
  const entries = Object.entries(mapping);
  const extract = cfg.extract || null;

  const updateEntry = (idx, key, value) => {
    const next = { ...mapping };
    const oldKey = entries[idx][0];
    delete next[oldKey];
    next[key] = value;
    onChange({ mapping: next });
  };
  const addEntry = () => onChange({ mapping: { ...mapping, '': '' } });
  const removeEntry = (key) => {
    const next = { ...mapping };
    delete next[key];
    onChange({ mapping: next });
  };

  return (
    <div className="space-y-3">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-semibold text-slate-700 dark:text-slate-300">Pares clave → label</h3>
          <button onClick={addEntry} className="text-xs text-indigo-600 hover:text-indigo-700 inline-flex items-center gap-1">
            <Plus size={12} /> Agregar entrada
          </button>
        </div>
        <table className="w-full text-xs">
          <thead className="text-slate-500 border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="text-left py-1.5 px-2 font-semibold w-1/3">Clave</th>
              <th className="text-left py-1.5 px-2 font-semibold">Label</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([k, v], idx) => (
              <tr key={`${k}-${idx}`} className="border-b border-slate-100 dark:border-slate-800">
                <td className="py-1 px-2">
                  <input
                    type="text"
                    value={k}
                    onChange={(e) => updateEntry(idx, e.target.value, v)}
                    className="w-full px-1.5 py-0.5 text-xs font-mono border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded"
                  />
                </td>
                <td className="py-1 px-2">
                  <input
                    type="text"
                    value={v}
                    onChange={(e) => updateEntry(idx, k, e.target.value)}
                    className="w-full px-1.5 py-0.5 text-xs border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded"
                  />
                </td>
                <td className="py-1 px-1">
                  <button onClick={() => removeEntry(k)} className="text-rose-400 hover:text-rose-600">
                    <X size={12} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {entries.length === 0 && <p className="text-xs text-slate-400 text-center py-3">Sin entradas.</p>}
      </div>

      <details className="text-xs text-slate-500">
        <summary className="cursor-pointer hover:text-slate-700">Pre-procesamiento del valor (extract)</summary>
        <div className="mt-2 space-y-2 p-2 bg-slate-50 dark:bg-slate-800 rounded">
          <div>
            <label className="inline-flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={!!extract}
                onChange={(e) => onChange({ extract: e.target.checked ? { split: ' ', index: 0 } : null })}
                className="accent-indigo-600"
              />
              <span>Aplicar split o regex antes de buscar en el dict</span>
            </label>
          </div>
          {extract && (
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-[11px] mb-0.5">Split por</label>
                <input
                  type="text" value={extract.split || ''}
                  onChange={(e) => onChange({ extract: { ...extract, split: e.target.value || null, regex: null } })}
                  placeholder=' ' className="w-full px-1.5 py-0.5 text-xs border border-slate-200 dark:border-slate-700 dark:bg-slate-900 rounded font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] mb-0.5">Índice</label>
                <input
                  type="number" value={extract.index ?? 0}
                  onChange={(e) => onChange({ extract: { ...extract, index: Number(e.target.value) } })}
                  className="w-full px-1.5 py-0.5 text-xs border border-slate-200 dark:border-slate-700 dark:bg-slate-900 rounded"
                />
              </div>
              <div>
                <label className="block text-[11px] mb-0.5">Regex (alternativa)</label>
                <input
                  type="text" value={extract.regex || ''}
                  onChange={(e) => onChange({ extract: { ...extract, regex: e.target.value || null, split: null } })}
                  placeholder='ej: ^\\d+'
                  className="w-full px-1.5 py-0.5 text-xs border border-slate-200 dark:border-slate-700 dark:bg-slate-900 rounded font-mono"
                />
              </div>
            </div>
          )}
        </div>
      </details>

      <div>
        <label className="inline-flex items-center gap-1.5 text-xs">
          <input
            type="checkbox" checked={cfg.case_insensitive || false}
            onChange={(e) => onChange({ case_insensitive: e.target.checked })}
            className="accent-indigo-600"
          />
          Case insensitive
        </label>
      </div>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────
// API helpers
// ─────────────────────────────────────────────────────────────────

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
