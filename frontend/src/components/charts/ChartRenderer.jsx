/**
 * ChartRenderer — renderiza un gráfico configurado (Spec type=Gráficos)
 * directamente con Plotly. Consume /api/charts/{id}/data o
 * POST /api/charts/preview con la config draft.
 *
 * Soporta 10 tipos: bar | grouped_bar | stacked_bar | box | line | pie |
 * histogram | heatmap | radar | gauge.
 *
 * Estrategia: el backend devuelve un `dataset` ya preprocesado/agregado.
 * Acá lo convertimos a `traces` de Plotly según el `chart_type`.
 */
import { useEffect, useMemo, useState, useCallback } from 'react';
import Plot from 'react-plotly.js';
import { Loader2, AlertCircle } from 'lucide-react';
import { API_BASE_URL } from '../../constants';

const CATEGORY_COLORS = [
  '#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#84cc16',
];

const SEMAFORO_COLORS = ['#22c55e', '#f59e0b', '#ef4444']; // Avanzado / Intermedio / Inicial

export default function ChartRenderer({
  chartId,
  draftConfig = null,
  extraFilters = null,
  className = '',
  height = 360,
}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch con AbortController para cancelar requests al desmontar.
  const fetchData = useCallback(async (signal) => {
    if (!chartId && !draftConfig) return;
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
        res = await fetch(`${API_BASE_URL}/charts/preview`, {
          method: 'POST',
          headers,
          signal,
          body: JSON.stringify({ config: draftConfig, extra_filters: extraFilters || null }),
        });
      } else {
        const params = new URLSearchParams();
        if (extraFilters && Object.keys(extraFilters).length) {
          params.set('extra_filters', JSON.stringify(extraFilters));
        }
        res = await fetch(`${API_BASE_URL}/charts/${chartId}/data?${params}`, { headers, signal });
      }
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(`HTTP ${res.status}: ${msg.slice(0, 200)}`);
      }
      setData(await res.json());
    } catch (e) {
      if (e.name === 'AbortError') return;
      setError(e.message || String(e));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [chartId, draftConfig, extraFilters]);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchData(ctrl.signal);
    return () => ctrl.abort();
  }, [fetchData]);

  // pivot_matrix se renderiza como tabla HTML, no como Plotly
  const isPivotMatrix = data?.chart_type === 'pivot_matrix';

  const plotProps = useMemo(() => {
    if (!data || data.dataset?.empty) return null;
    if (isPivotMatrix) return null;  // tabla HTML, no Plotly
    return buildPlotProps(data);
  }, [data, isPivotMatrix]);

  if (error) {
    return (
      <div className={`bg-rose-50 border border-rose-200 text-rose-700 p-3 rounded text-sm ${className}`}>
        <strong>Error:</strong> {error}
      </div>
    );
  }
  if (loading && !data) {
    return (
      <div className={`flex items-center justify-center h-64 text-slate-400 ${className}`}>
        <Loader2 size={20} className="animate-spin" />
      </div>
    );
  }
  if (isPivotMatrix && data?.dataset && !data.dataset.empty) {
    return <PivotMatrixTable data={data} height={height} className={className} />;
  }
  if (!plotProps) {
    return (
      <div className={`flex items-center justify-center h-64 text-slate-400 text-sm bg-slate-50 border border-dashed border-slate-300 rounded ${className}`}>
        <div className="text-center">
          <AlertCircle size={20} className="mx-auto mb-1 opacity-50" />
          Sin datos para mostrar
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      <Plot
        data={plotProps.data}
        layout={{
          ...plotProps.layout,
          autosize: true,
          height,
          margin: { l: 50, r: 20, t: plotProps.layout.title ? 50 : 20, b: 60 },
          font: { family: 'system-ui, -apple-system, sans-serif', size: 12 },
        }}
        config={{ responsive: true, displaylogo: false, displayModeBar: false }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────────
// Construcción de traces Plotly por chart_type
// ─────────────────────────────────────────────────────────────────────────

function buildPlotProps({ chart_type, mapping, aesthetics, dataset }) {
  const t = aesthetics?.titulo || null;
  const yfmt = aesthetics?.y_format || 'number';
  const ylims = aesthetics?.y_lims;
  const showLegend = aesthetics?.show_legend !== false;
  const showValues = !!aesthetics?.show_values;

  // Formatea un número Y según el y_format del chart, para usar como text
  // sobre las barras / segmentos. Devuelve "" si el valor no es numérico.
  const fmtVal = (v) => {
    if (v == null || isNaN(v)) return '';
    if (yfmt === 'percent') return (v * 100).toFixed(1).replace(/\.0$/, '') + '%';
    if (yfmt === 'int') return String(Math.round(v));
    return Number.isInteger(v) ? String(v) : v.toFixed(1);
  };

  const yaxisFmt = yfmt === 'percent'
    ? { tickformat: '.0%', range: ylims || [0, 1] }
    : yfmt === 'int'
      ? { tickformat: 'd' }
      : ylims ? { range: ylims } : {};

  const layoutBase = {
    title: t ? { text: t, font: { size: 13, weight: 600 }, x: 0.5 } : undefined,
    xaxis: { title: aesthetics?.x_label || mapping?.x_field || '' },
    yaxis: { title: aesthetics?.y_label || mapping?.y_field || '', ...yaxisFmt },
    showlegend: showLegend,
    legend: aesthetics?.legend_title
      ? { title: { text: aesthetics.legend_title } }
      : {},
    hovermode: 'closest',
  };

  if (chart_type === 'bar') {
    return {
      data: [{
        type: 'bar',
        // Sin `name`, Plotly auto-genera "trace 0" en la leyenda. Como un
        // bar simple es una sola serie, el nombre es redundante. Le damos
        // un nombre vacío y desactivamos la leyenda por defecto.
        name: '',
        x: dataset.x,
        y: dataset.y,
        marker: { color: CATEGORY_COLORS[0] },
        text: showValues ? (dataset.y || []).map(fmtVal) : undefined,
        textposition: showValues ? 'outside' : 'none',
        hovertemplate: yfmt === 'percent' ? '%{x}: %{y:.1%}<extra></extra>' : '%{x}: %{y}<extra></extra>',
        showlegend: false,
      }],
      layout: { ...layoutBase, showlegend: false },
    };
  }

  if (chart_type === 'grouped_bar') {
    const traces = (dataset.series || []).map((s, i) => ({
      type: 'bar',
      name: s.name,
      x: dataset.x,
      y: s.y,
      marker: { color: CATEGORY_COLORS[i % CATEGORY_COLORS.length] },
      text: showValues ? (s.y || []).map(fmtVal) : undefined,
      textposition: showValues ? 'outside' : 'none',
    }));
    return { data: traces, layout: { ...layoutBase, barmode: 'group' } };
  }

  if (chart_type === 'stacked_bar') {
    const basePalette = aesthetics?.color_palette === 'semaforo'
      ? SEMAFORO_COLORS
      : CATEGORY_COLORS;
    const palette = aesthetics?.palette_reversed ? [...basePalette].reverse() : basePalette;
    const traces = (dataset.stacks || []).map((s, i) => ({
      type: 'bar',
      name: s.name,
      x: dataset.x,
      y: s.y,
      marker: { color: palette[i % palette.length] },
      // En stacked, "inside" muestra el número dentro del segmento.
      // Plotly oculta automáticamente los textos que no caben en el segmento.
      text: showValues ? (s.y || []).map(fmtVal) : undefined,
      textposition: showValues ? 'inside' : 'none',
      insidetextanchor: 'middle',
    }));
    return { data: traces, layout: { ...layoutBase, barmode: 'stack', yaxis: { ...layoutBase.yaxis, tickformat: 'd' } } };
  }

  if (chart_type === 'stacked_grouped_bar') {
    // Plotly soporta eje X categorical multi-nivel pasando x = [outer, inner].
    // Outer = group_field (ej Curso), inner = x_field (ej Mes). Visualmente
    // queda con una etiqueta superior por grupo y barras separadas por
    // categoría interna debajo.
    const basePalette = aesthetics?.color_palette === 'semaforo'
      ? SEMAFORO_COLORS
      : CATEGORY_COLORS;
    const palette = aesthetics?.palette_reversed ? [...basePalette].reverse() : basePalette;
    const xOuter = dataset.x_outer || [];
    const xInner = dataset.x_inner || [];
    const traces = (dataset.stacks || []).map((s, i) => ({
      type: 'bar',
      name: s.name,
      x: [xOuter, xInner],
      y: s.y,
      marker: { color: palette[i % palette.length] },
      text: showValues ? (s.y || []).map(v => (v && v > 0 ? fmtVal(v) : '')) : undefined,
      textposition: showValues ? 'inside' : 'none',
      insidetextanchor: 'middle',
    }));
    return {
      data: traces,
      layout: {
        ...layoutBase,
        barmode: 'stack',
        yaxis: { ...layoutBase.yaxis, tickformat: 'd' },
        // Mostrar líneas verticales discontinuas entre los grupos outer
        // ayuda a separar visualmente los cursos en el eje compuesto.
        xaxis: { ...layoutBase.xaxis, showdividers: true, dividercolor: '#cbd5e1', dividerwidth: 1 },
      },
    };
  }

  if (chart_type === 'box') {
    const traces = (dataset.x || []).map((cat, i) => ({
      type: 'box',
      name: cat,
      y: dataset.y_arrays[i],
      marker: { color: CATEGORY_COLORS[i % CATEGORY_COLORS.length] },
      boxpoints: false,
    }));
    return { data: traces, layout: { ...layoutBase, showlegend: false } };
  }

  if (chart_type === 'line') {
    if (dataset.series) {
      const traces = dataset.series.map((s, i) => ({
        type: 'scatter',
        mode: showValues ? 'lines+markers+text' : 'lines+markers',
        name: s.name,
        x: dataset.x,
        y: s.y,
        line: { color: CATEGORY_COLORS[i % CATEGORY_COLORS.length], width: 2 },
        marker: { size: 6 },
        text: showValues ? (s.y || []).map(fmtVal) : undefined,
        textposition: 'top center',
      }));
      return { data: traces, layout: layoutBase };
    }
    return {
      data: [{
        type: 'scatter',
        mode: showValues ? 'lines+markers+text' : 'lines+markers',
        x: dataset.x,
        y: dataset.y,
        line: { color: CATEGORY_COLORS[0], width: 2 },
        marker: { size: 6 },
        text: showValues ? (dataset.y || []).map(fmtVal) : undefined,
        textposition: 'top center',
      }],
      layout: layoutBase,
    };
  }

  if (chart_type === 'pie') {
    const basePalette = aesthetics?.color_palette === 'semaforo'
      ? SEMAFORO_COLORS
      : CATEGORY_COLORS;
    const palette = aesthetics?.palette_reversed ? [...basePalette].reverse() : basePalette;
    // Para pie, eliminamos xaxis e yaxis del layout (no aplican). Pasarlos
    // como `undefined` confunde a Plotly y puede dejar el chart colapsado
    // a height: 0. Hacemos un layout limpio omitiéndolos por destructuring.
    const { xaxis: _x, yaxis: _y, ...layoutPie } = layoutBase;
    return {
      data: [{
        type: 'pie',
        labels: dataset.labels,
        values: dataset.values,
        marker: { colors: palette },
        hole: 0.35,
        textinfo: 'label+percent',
      }],
      layout: layoutPie,
    };
  }

  if (chart_type === 'histogram') {
    return {
      data: [{
        type: 'histogram',
        x: dataset.values,
        marker: { color: CATEGORY_COLORS[0] },
        nbinsx: aesthetics?.bins || 10,
      }],
      layout: layoutBase,
    };
  }

  if (chart_type === 'heatmap') {
    // Paletas heatmap soportadas:
    //   "viridis"     → Viridis (default fríos→cálidos, percepción uniforme)
    //   "rojo_calor"  → YlOrRd (amarillo claro→naranja→rojo). Estándar para
    //                   "% en riesgo / % crítico" donde rojo = peor.
    //   (default)     → YlGnBu (amarillo→azul, neutro)
    const palette = aesthetics?.color_palette;
    const colorscale =
      palette === 'viridis' ? 'Viridis'
        : palette === 'rojo_calor' ? 'YlOrRd'
        : 'YlGnBu';
    // UX-6: Tooltip respeta y_format. Para percent muestra "35.0%", para
    // count entero, para number 2 decimales. Más útil que el genérico .2f.
    const heatmapHover =
      yfmt === 'percent' ? '%{y} × %{x}: %{z:.1%}<extra></extra>'
        : yfmt === 'int' ? '%{y} × %{x}: %{z:.0f}<extra></extra>'
        : '%{y} × %{x}: %{z:.2f}<extra></extra>';
    return {
      data: [{
        type: 'heatmap',
        x: dataset.x,
        y: dataset.y,
        z: dataset.z,
        colorscale,
        reversescale: !!aesthetics?.palette_reversed,
        hovertemplate: heatmapHover,
      }],
      layout: { ...layoutBase, yaxis: { ...layoutBase.yaxis, autorange: 'reversed' } },
    };
  }

  if (chart_type === 'radar') {
    const traces = (dataset.series || []).map((s, i) => ({
      type: 'scatterpolar',
      r: [...s.values, s.values[0]],
      theta: [...dataset.axes, dataset.axes[0]],
      fill: 'toself',
      name: s.name,
      line: { color: CATEGORY_COLORS[i % CATEGORY_COLORS.length] },
    }));
    return {
      data: traces,
      layout: {
        ...layoutBase,
        polar: { radialaxis: { visible: true, range: ylims || [0, 1] } },
        xaxis: undefined,
        yaxis: undefined,
      },
    };
  }

  if (chart_type === 'gauge') {
    const min = aesthetics?.min_value ?? 0;
    const max = aesthetics?.max_value ?? 1;
    // Para percent, escalar el value 0-1 a 0-100 y usar suffix; el gauge
    // axis también va en 0-100.
    const isPercent = yfmt === 'percent';
    const scaledValue = isPercent ? dataset.value * 100 : dataset.value;
    const axisMin = isPercent ? min * 100 : min;
    const axisMax = isPercent ? max * 100 : max;
    return {
      data: [{
        type: 'indicator',
        mode: 'gauge+number',
        value: scaledValue,
        number: isPercent
          ? { suffix: '%', valueformat: '.1f' }
          : { valueformat: '.2f' },
        gauge: {
          axis: { range: [axisMin, axisMax] },
          bar: { color: CATEGORY_COLORS[0] },
          steps: (aesthetics?.thresholds || []).map((th, i, arr) => ({
            range: [
              i === 0 ? axisMin : (isPercent ? arr[i - 1].value * 100 : arr[i - 1].value),
              isPercent ? th.value * 100 : th.value,
            ],
            color: th.color,
          })),
        },
      }],
      layout: {
        title: layoutBase.title,
        showlegend: false,
      },
    };
  }

  return { data: [], layout: layoutBase };
}


// ─────────────────────────────────────────────────────────────────────────
// PivotMatrixTable — renderer de chart_type='pivot_matrix' como tabla HTML
// ─────────────────────────────────────────────────────────────────────────

// Mapeo de niveles cualitativos comunes a colores. Cuando el cell value
// matchea (case-insensitive) una de estas claves, la celda se colorea.
// Si no matchea, queda en gris claro.
const PIVOT_LEVEL_COLORS = {
  // IDEL/PDL Woodcock
  'crítico': { bg: '#fee2e2', fg: '#991b1b' },
  'critico': { bg: '#fee2e2', fg: '#991b1b' },
  'alto riesgo': { bg: '#ffedd5', fg: '#9a3412' },
  'cierto riesgo': { bg: '#fef3c7', fg: '#854d0e' },
  'bajo riesgo': { bg: '#dcfce7', fg: '#166534' },
  // SIMCE / DIA
  'inicial': { bg: '#fee2e2', fg: '#991b1b' },
  'insuficiente': { bg: '#fee2e2', fg: '#991b1b' },
  'intermedio': { bg: '#fef3c7', fg: '#854d0e' },
  'elemental': { bg: '#fef3c7', fg: '#854d0e' },
  'avanzado': { bg: '#dcfce7', fg: '#166534' },
  'adecuado': { bg: '#dcfce7', fg: '#166534' },
  // CV
  'básico': { bg: '#ffedd5', fg: '#9a3412' },
  'experto': { bg: '#bbf7d0', fg: '#14532d' },
};

function cellStyle(value) {
  if (value == null || value === '') return { background: '#f8fafc', color: '#94a3b8' };
  const key = String(value).trim().toLowerCase();
  return PIVOT_LEVEL_COLORS[key] ? {
    background: PIVOT_LEVEL_COLORS[key].bg,
    color: PIVOT_LEVEL_COLORS[key].fg,
  } : { background: '#f1f5f9', color: '#475569' };
}

function PivotMatrixTable({ data, height, className }) {
  const ds = data.dataset;
  const title = data?.aesthetics?.titulo;
  const hasOuter = Array.isArray(ds.col_outer);
  const cols = hasOuter ? ds.col_inner : ds.cols;
  const cellsPerOuter = hasOuter ? ds.col_inner.length : 0;
  const totalCols = hasOuter ? ds.col_outer.length * cellsPerOuter : ds.cols.length;
  // UX-5: cuando hay muchas filas (típicamente Roster sin filtro de curso),
  // sugerir al usuario que aplique un filtro para una vista más manejable.
  const TOO_MANY_ROWS = 60;
  const showFilterHint = ds.rows.length > TOO_MANY_ROWS;

  return (
    <div className={className} style={{ height, overflow: 'auto' }}>
      {title && (
        <div className="text-center text-sm font-semibold text-slate-700 mb-2">{title}</div>
      )}
      {showFilterHint && (
        <div className="mb-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
          <span className="font-semibold">Tip:</span> Esta tabla muestra {ds.rows.length} filas.
          Aplica un filtro (ej: Curso) en el panel superior para una vista más enfocada.
        </div>
      )}
      <table className="text-xs border-collapse w-full">
        <thead className="sticky top-0 bg-slate-50">
          {hasOuter && (
            <tr>
              <th className="border border-slate-300 bg-slate-100 px-2 py-1 sticky left-0 z-10" rowSpan={2}>Estudiante</th>
              {ds.col_outer.map((g) => (
                <th key={g} colSpan={cellsPerOuter} className="border border-slate-300 bg-slate-100 px-2 py-1 text-center font-bold">
                  {g}
                </th>
              ))}
            </tr>
          )}
          <tr>
            {!hasOuter && (
              <th className="border border-slate-300 bg-slate-100 px-2 py-1 sticky left-0 z-10">Estudiante</th>
            )}
            {hasOuter
              ? ds.col_outer.flatMap((_, oi) => cols.map((c, ci) => (
                  <th key={`${oi}-${ci}`} className="border border-slate-300 px-1 py-1 text-center font-medium text-slate-600">
                    {c}
                  </th>
                )))
              : cols.map((c) => (
                  <th key={c} className="border border-slate-300 px-1 py-1 text-center font-medium text-slate-600">
                    {c}
                  </th>
                ))}
          </tr>
        </thead>
        <tbody>
          {ds.rows.map((rowName, ri) => (
            <tr key={rowName}>
              <td className="border border-slate-300 px-2 py-1 sticky left-0 bg-white whitespace-nowrap font-medium">
                {rowName}
              </td>
              {ds.cells[ri].map((val, ci) => {
                // Datos-10: celdas sin dato (combinación curso × subprueba ×
                // versión que no rinde el protocolo, ej v3 para 5°/6° BÁSICO)
                // se etiquetan como "N/A" en gris suave para distinguirlas
                // visualmente de niveles bajos.
                const isMissing = val == null || val === '';
                return (
                  <td
                    key={ci}
                    className={"border border-slate-300 px-1 py-1 text-center text-[11px] " + (isMissing ? "text-slate-400 italic bg-slate-50" : "")}
                    style={isMissing ? undefined : cellStyle(val)}
                  >
                    {isMissing ? 'N/A' : val}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
