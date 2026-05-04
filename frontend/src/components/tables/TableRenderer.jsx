/**
 * TableRenderer — renderiza una tabla configurada (Spec type=Tablas) con
 * TanStack Table v8. Consume el endpoint /api/tables/{id}/data del backend.
 *
 * Props:
 *   tableId (number, opcional): id persistido. Si se pasa, fetch a
 *     GET /api/tables/{id}/data.
 *   draftConfig (object, opcional): TableConfig draft. Si se pasa (y NO
 *     hay tableId), fetch a POST /api/tables/preview con la config en
 *     body. Útil para el editor live antes de guardar.
 *   extraFilters (object, opcional): filtros adicionales {dim: value}
 *   pageSize (number, opcional, default según config): tamaño de página override
 *   className (string, opcional)
 *   enableExport (bool, default true)
 *
 * Funcionalidad:
 * - Sort por click en header (multi-columna con shift)
 * - Paginación (server-side via offset/limit)
 * - Color scale por celda (lee `cell.color` del backend)
 * - Export CSV (en cliente con datos visibles)
 * - Loading / error / empty states
 */
import { useEffect, useMemo, useState, useCallback } from 'react';
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { ChevronUp, ChevronDown, ChevronsUpDown, Download, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../../constants';

const PAGE_SIZE_DEFAULT = 50;

export default function TableRenderer({
  tableId,
  draftConfig = null,
  extraFilters = null,
  pageSize: pageSizeProp,
  className = '',
  enableExport = true,
}) {
  const [columns, setColumns] = useState([]);
  const [rows, setRows] = useState([]);
  const [totalRows, setTotalRows] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(pageSizeProp || PAGE_SIZE_DEFAULT);
  const [sorting, setSorting] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // ── Fetch ───────────────────────────────────────────────────────────
  // Usa AbortController para cancelar requests en vuelo cuando el componente
  // se desmonta o cambian las dependencias. Sin esto, en sesiones largas con
  // navegación rápida entre indicadores, los .then(setState) terminan
  // ejecutándose sobre componentes desmontados — generando warnings y
  // pequeños leaks de memoria que se acumulan.
  const fetchData = useCallback(async (signal) => {
    if (!tableId && !draftConfig) return;
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('rg_token');
      const headers = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      let res;
      if (draftConfig) {
        // Modo preview live: POST /preview con config en body
        res = await fetch(`${API_BASE_URL}/tables/preview`, {
          method: 'POST',
          headers,
          signal,
          body: JSON.stringify({
            config: draftConfig,
            limit: pageSize,
            offset: page * pageSize,
            include_styles: true,
            extra_filters: extraFilters || null,
          }),
        });
      } else {
        const params = new URLSearchParams({
          limit: String(pageSize),
          offset: String(page * pageSize),
          include_styles: 'true',
        });
        if (extraFilters && Object.keys(extraFilters).length) {
          params.set('extra_filters', JSON.stringify(extraFilters));
        }
        res = await fetch(`${API_BASE_URL}/tables/${tableId}/data?${params}`, { headers, signal });
      }
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(`HTTP ${res.status}: ${msg.slice(0, 200)}`);
      }
      const data = await res.json();
      setColumns(data.columns || []);
      setRows(data.rows || []);
      setTotalRows(data.total_rows || 0);
    } catch (e) {
      if (e.name === 'AbortError') return;  // unmount o cambio de deps — silencioso
      setError(e.message || String(e));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [tableId, draftConfig, page, pageSize, extraFilters]);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchData(ctrl.signal);
    return () => ctrl.abort();
  }, [fetchData]);

  // Reset page cuando cambian filters externos
  useEffect(() => { setPage(0); }, [extraFilters, tableId]);

  // ── TanStack columns ────────────────────────────────────────────────
  const tanColumns = useMemo(() => columns.map((c) => ({
    id: c.key,
    accessorFn: (row) => row[c.key]?.raw ?? null,
    header: c.header,
    enableSorting: true,
    meta: { format: c.format, pinned: c.pinned, width: c.width },
    cell: ({ row }) => {
      const cell = row.original[c.key];
      if (!cell) return null;
      const style = cell.color ? { backgroundColor: cell.color, color: contrastTextColor(cell.color) } : undefined;
      const align = ['int', 'float', 'percent'].includes(c.format) ? 'text-right' : 'text-left';
      return (
        <div
          className={`px-3 py-1.5 ${align} text-sm`}
          style={style}
          title={cell.raw != null ? String(cell.raw) : ''}
        >
          {cell.formatted}
        </div>
      );
    },
  })), [columns]);

  const table = useReactTable({
    data: rows,
    columns: tanColumns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualPagination: true,
    pageCount: Math.max(1, Math.ceil(totalRows / pageSize)),
  });

  // ── Export CSV (client-side, página actual) ────────────────────────
  const handleExportCSV = () => {
    if (!columns.length || !rows.length) {
      toast.error('No hay datos para exportar');
      return;
    }
    const headers = columns.map((c) => csvEscape(c.header)).join(',');
    const lines = rows.map((row) =>
      columns.map((c) => csvEscape(row[c.key]?.formatted ?? '')).join(',')
    );
    const blob = new Blob(['﻿' + [headers, ...lines].join('\n')], {
      type: 'text/csv;charset=utf-8;',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tabla_${tableId}_pag${page + 1}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── Render ──────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className={`bg-rose-50 border border-rose-200 text-rose-700 p-4 rounded ${className}`}>
        <strong>Error cargando tabla:</strong> {error}
      </div>
    );
  }

  return (
    <div className={`bg-white border border-slate-200 rounded shadow-sm ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-100 bg-slate-50">
        <span className="text-xs text-slate-500">
          {loading ? (
            <span className="inline-flex items-center gap-1.5"><Loader2 size={12} className="animate-spin" /> Cargando…</span>
          ) : (
            `${totalRows.toLocaleString('es-CL')} filas`
          )}
        </span>
        {enableExport && (
          <button
            onClick={handleExportCSV}
            disabled={loading || !rows.length}
            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-white border border-slate-300 hover:bg-slate-50 disabled:opacity-50"
            title="Exportar página actual a CSV"
          >
            <Download size={12} /> CSV
          </button>
        )}
      </div>

      {/* Tabla */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead className="bg-slate-50">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => {
                  const meta = header.column.columnDef.meta || {};
                  const align = ['int', 'float', 'percent'].includes(meta.format) ? 'text-right' : 'text-left';
                  const sort = header.column.getIsSorted();
                  return (
                    <th
                      key={header.id}
                      className={`px-3 py-2 ${align} text-xs font-semibold text-slate-600 border-b border-slate-200 cursor-pointer select-none hover:bg-slate-100`}
                      style={{ width: meta.width || undefined }}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <span className="inline-flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {sort === 'asc' ? <ChevronUp size={12} /> :
                         sort === 'desc' ? <ChevronDown size={12} /> :
                         <ChevronsUpDown size={12} className="opacity-30" />}
                      </span>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="text-center py-8 text-slate-400 text-sm">
                  {loading ? '' : 'Sin datos'}
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="border-b border-slate-100 hover:bg-slate-50">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="p-0">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      {totalRows > pageSize && (
        <div className="flex items-center justify-between px-3 py-2 border-t border-slate-100 bg-slate-50 text-xs">
          <span className="text-slate-500">
            Página {page + 1} de {Math.max(1, Math.ceil(totalRows / pageSize))}
          </span>
          <div className="inline-flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              className="px-2 py-1 rounded border border-slate-300 hover:bg-slate-100 disabled:opacity-50"
            >Anterior</button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={(page + 1) * pageSize >= totalRows || loading}
              className="px-2 py-1 rounded border border-slate-300 hover:bg-slate-100 disabled:opacity-50"
            >Siguiente</button>
            <select
              value={pageSize}
              onChange={(e) => { setPageSize(Number(e.target.value)); setPage(0); }}
              className="px-1.5 py-1 rounded border border-slate-300 bg-white"
            >
              {[10, 25, 50, 100, 250].map((n) => <option key={n} value={n}>{n}/pág</option>)}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Utils ─────────────────────────────────────────────────────────────

function csvEscape(v) {
  const s = v == null ? '' : String(v);
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

/** Devuelve color de texto blanco/negro según luminancia del fondo. */
function contrastTextColor(hex) {
  if (!hex || !hex.startsWith('#') || (hex.length !== 7 && hex.length !== 4)) return undefined;
  let r, g, b;
  if (hex.length === 4) {
    r = parseInt(hex[1] + hex[1], 16);
    g = parseInt(hex[2] + hex[2], 16);
    b = parseInt(hex[3] + hex[3], 16);
  } else {
    r = parseInt(hex.slice(1, 3), 16);
    g = parseInt(hex.slice(3, 5), 16);
    b = parseInt(hex.slice(5, 7), 16);
  }
  // luminance perceptual
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum > 0.6 ? '#1f2937' : '#ffffff';
}
