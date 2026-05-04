/**
 * MultiSelectFilters — toolbar con dropdowns multi-valor + chips activos.
 *
 * Patrón estilo Linear/Notion. Ver `docs/desarrollo/filter_ui_examples.html`
 * sección "2. Multi-select dropdowns + chips activos" para la referencia
 * visual.
 *
 * Props:
 *   dimensions: { [dimId]: { name: string, values: string[] } }
 *   sortedDimIds: string[] — orden en que aparecen los dropdowns
 *   value: { [dimId]: string[] } — selección actual (multi-valor)
 *   onChange: (next) => void
 *   className?: string
 *   compact?: bool — versión más chica para modales
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, Search, X } from 'lucide-react';

export default function MultiSelectFilters({
  dimensions = {},
  sortedDimIds = [],
  value = {},
  onChange,
  className = '',
  compact = false,
}) {
  const [openDim, setOpenDim] = useState(null);
  const containerRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpenDim(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const setDimValue = (dimId, vals) => {
    const next = { ...value };
    if (!vals || vals.length === 0) delete next[dimId];
    else next[dimId] = vals;
    onChange(next);
  };

  const removeChipValue = (dimId, v) => {
    const current = value[dimId] || [];
    setDimValue(dimId, current.filter((x) => x !== v));
  };

  const clearAll = () => onChange({});

  const hasActive = Object.keys(value).some((k) => (value[k] || []).length > 0);

  const btnPad = compact ? 'px-2 py-1' : 'px-3 py-1.5';

  return (
    <div ref={containerRef} className={`space-y-2 ${className}`}>
      {/* Toolbar dropdowns */}
      <div className="flex flex-wrap items-center gap-2">
        {sortedDimIds.map((dimId) => {
          const dim = dimensions[dimId];
          if (!dim || !dim.values || dim.values.length === 0) return null;
          const selected = value[dimId] || [];
          const isOpen = openDim === dimId;
          return (
            <DimensionDropdown
              key={dimId}
              dim={dim}
              dimId={dimId}
              selected={selected}
              isOpen={isOpen}
              onToggle={() => setOpenDim(isOpen ? null : dimId)}
              onChangeSelection={(vals) => setDimValue(dimId, vals)}
              onClose={() => setOpenDim(null)}
              btnPad={btnPad}
            />
          );
        })}

        {hasActive && (
          <button
            onClick={clearAll}
            className={`${btnPad} text-xs text-slate-500 hover:text-rose-600 inline-flex items-center gap-1 ml-1`}
            title="Limpiar todos los filtros"
          >
            <X size={12} /> Limpiar
          </button>
        )}
      </div>

      {/* Chips activos */}
      {hasActive && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {sortedDimIds.flatMap((dimId) => {
            const vals = value[dimId] || [];
            const dim = dimensions[dimId];
            return vals.map((v) => (
              <span
                key={`${dimId}-${v}`}
                className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 text-[11px] font-semibold border border-indigo-200"
              >
                <span className="opacity-70 font-normal">{dim?.name || dimId}:</span>
                {String(v)}
                <button
                  onClick={() => removeChipValue(dimId, v)}
                  className="text-indigo-400 hover:text-rose-600 -mr-0.5"
                  title="Quitar"
                >
                  <X size={11} />
                </button>
              </span>
            ));
          })}
        </div>
      )}
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────────
// DimensionDropdown — un dropdown con search + checkboxes
// ─────────────────────────────────────────────────────────────────────────

function DimensionDropdown({ dim, dimId, selected, isOpen, onToggle, onChangeSelection, onClose, btnPad }) {
  const [search, setSearch] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setSearch('');
      // Focus search box on open
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const filteredValues = useMemo(() => {
    const q = search.trim().toLowerCase();
    const cleaned = (dim.values || []).filter((v) => {
      if (v === null || v === undefined) return false;
      const s = String(v).trim().toLowerCase();
      return s && s !== 'nan' && s !== 'nat' && s !== 'none' && s !== 'null';
    });
    if (!q) return cleaned;
    return cleaned.filter((v) => String(v).toLowerCase().includes(q));
  }, [dim.values, search]);

  const toggleValue = (v) => {
    if (selected.includes(v)) onChangeSelection(selected.filter((x) => x !== v));
    else onChangeSelection([...selected, v]);
  };

  const selectAll = () => onChangeSelection(filteredValues.map((v) => String(v)));
  const clearDim = () => onChangeSelection([]);

  const count = selected.length;
  const hasSelection = count > 0;

  return (
    <div className="relative">
      <button
        onClick={onToggle}
        className={`${btnPad} inline-flex items-center gap-1.5 text-xs rounded-lg border transition-all ${
          hasSelection
            ? 'border-indigo-500 bg-indigo-50 text-indigo-700 font-semibold'
            : 'border-slate-300 bg-white text-slate-600 hover:border-indigo-400'
        }`}
      >
        <span>{dim.name}</span>
        {hasSelection && (
          <span className="bg-indigo-600 text-white rounded-full px-1.5 py-0 text-[10px] font-bold leading-tight">
            {count}
          </span>
        )}
        <ChevronDown size={12} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 z-30 w-64 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl overflow-hidden">
          <div className="p-2 border-b border-slate-100 dark:border-slate-800">
            <div className="relative">
              <Search size={12} className="absolute top-2 left-2 text-slate-400" />
              <input
                ref={inputRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={`Buscar ${dim.name?.toLowerCase() || ''}...`}
                className="w-full pl-7 pr-2 py-1.5 text-xs border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded"
              />
            </div>
            <div className="flex items-center justify-between mt-1.5 text-[11px]">
              <button onClick={selectAll} className="text-indigo-600 hover:underline">
                Seleccionar todos ({filteredValues.length})
              </button>
              {hasSelection && (
                <button onClick={clearDim} className="text-rose-500 hover:underline">
                  Limpiar
                </button>
              )}
            </div>
          </div>
          <div className="max-h-60 overflow-y-auto py-1">
            {filteredValues.length === 0 && (
              <div className="px-3 py-3 text-xs text-slate-400 text-center">Sin resultados</div>
            )}
            {filteredValues.map((v) => {
              const checked = selected.map(String).includes(String(v));
              return (
                <label
                  key={String(v)}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleValue(String(v))}
                    className="accent-indigo-600"
                  />
                  <span className="truncate">{String(v)}</span>
                </label>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
