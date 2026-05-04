function BarPreview() {
  const heights = [42, 68, 55, 78, 50, 88];
  return (
    <svg viewBox="0 0 220 110" className="w-full max-w-[220px]">
      {heights.map((h, i) => (
        <rect
          key={i}
          x={12 + i * 33}
          y={110 - h}
          width={20}
          height={h}
          rx={4}
          fill={i % 2 === 0 ? "#4f46e5" : "#818cf8"}
          opacity={0.85}
        />
      ))}
      <line x1="8" y1="109" x2="212" y2="109" stroke="#e2e8f0" strokeWidth="1" />
    </svg>
  );
}

function LinePreview() {
  const pts1 = "10,90 50,65 90,55 130,40 170,30 210,22";
  const pts2 = "10,100 50,80 90,78 130,68 170,72 210,58";
  const dots1 = [[10, 90], [50, 65], [90, 55], [130, 40], [170, 30], [210, 22]];
  return (
    <svg viewBox="0 0 220 110" className="w-full max-w-[220px]">
      <polyline points={pts1} fill="none" stroke="#4f46e5" strokeWidth="2.5" strokeLinejoin="round" />
      <polyline points={pts2} fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinejoin="round" />
      {dots1.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={3.5} fill="#4f46e5" />
      ))}
      <line x1="8" y1="108" x2="212" y2="108" stroke="#e2e8f0" strokeWidth="1" />
    </svg>
  );
}

function PiePreview() {
  return (
    <svg viewBox="0 0 110 110" className="w-full max-w-[110px]">
      <path d="M55 55 L55 12 A43 43 0 0 1 98 55 Z" fill="#4f46e5" opacity="0.9" />
      <path d="M55 55 L98 55 A43 43 0 0 1 35 93 Z" fill="#818cf8" opacity="0.85" />
      <path d="M55 55 L35 93 A43 43 0 0 1 55 12 Z" fill="#c7d2fe" opacity="0.9" />
    </svg>
  );
}

function BoxPreview() {
  const boxes = [
    { x: 20, max: 15, q3: 35, med: 55, q1: 72, min: 90 },
    { x: 65, max: 10, q3: 28, med: 48, q1: 68, min: 88 },
    { x: 110, max: 18, q3: 40, med: 58, q1: 73, min: 92 },
    { x: 155, max: 8, q3: 30, med: 50, q1: 65, min: 85 },
  ];
  return (
    <svg viewBox="0 0 210 105" className="w-full max-w-[210px]">
      {boxes.map((b, i) => (
        <g key={i}>
          <line x1={b.x + 10} x2={b.x + 10} y1={b.min} y2={b.max} stroke="#4f46e5" strokeWidth="1.5" strokeDasharray="2,2" />
          <rect x={b.x} y={b.q3} width={20} height={b.q1 - b.q3} rx={3} fill="#818cf8" opacity={0.65} stroke="#4f46e5" strokeWidth={1.2} />
          <line x1={b.x} x2={b.x + 20} y1={b.med} y2={b.med} stroke="#4f46e5" strokeWidth={2} />
        </g>
      ))}
      <line x1="8" y1="100" x2="202" y2="100" stroke="#e2e8f0" strokeWidth="1" />
    </svg>
  );
}

function RadarPreview() {
  const cx = 55, cy = 55, r = 42;
  const n = 6;
  const vals = [0.8, 0.6, 0.9, 0.5, 0.75, 0.85];
  const gridPts = Array.from({ length: n }, (_, i) => {
    const a = (i * 2 * Math.PI) / n - Math.PI / 2;
    return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`;
  }).join(" ");
  const dataPts = vals.map((v, i) => {
    const a = (i * 2 * Math.PI) / n - Math.PI / 2;
    return `${cx + v * r * Math.cos(a)},${cy + v * r * Math.sin(a)}`;
  }).join(" ");
  return (
    <svg viewBox="0 0 110 110" className="w-full max-w-[110px]">
      <polygon points={gridPts} fill="none" stroke="#e2e8f0" strokeWidth="1" />
      <polygon points={dataPts} fill="#4f46e5" fillOpacity={0.18} stroke="#4f46e5" strokeWidth={2} />
    </svg>
  );
}

function KpiPreview() {
  const cards = [
    { label: "Logro 1", val: "82%", color: "#4f46e5", bg: "#eef2ff" },
    { label: "Logro 2", val: "3.4", color: "#10b981", bg: "#ecfdf5" },
    { label: "Promedio", val: "127", color: "#f59e0b", bg: "#fffbeb" },
  ];
  return (
    <svg viewBox="0 0 230 80" className="w-full max-w-[230px]">
      {cards.map((c, i) => (
        <g key={i}>
          <rect x={i * 76 + 4} y={6} width={68} height={68} rx={10} fill={c.bg} stroke={c.color} strokeOpacity={0.3} strokeWidth={1} />
          <text x={i * 76 + 38} y={30} textAnchor="middle" fontSize={9} fill={c.color} opacity={0.7} fontFamily="system-ui">{c.label}</text>
          <text x={i * 76 + 38} y={55} textAnchor="middle" fontSize={20} fontWeight={600} fill={c.color} fontFamily="system-ui">{c.val}</text>
        </g>
      ))}
    </svg>
  );
}

function TablePreview() {
  return (
    <svg viewBox="0 0 220 100" className="w-full max-w-[220px]">
      <rect x={8} y={8} width={204} height={20} rx={5} fill="#4f46e5" fillOpacity={0.12} />
      {[34, 58, 82].map((y) => (
        <rect key={y} x={8} y={y} width={204} height={18} rx={4} fill="#f8fafc" stroke="#e2e8f0" strokeWidth={0.5} />
      ))}
      {[34, 58, 82].map((y, i) => (
        <rect key={y} x={144} y={y + 4} width={35 + i * 8} height={10} rx={5} fill="#4f46e5" fillOpacity={0.25 + i * 0.1} />
      ))}
    </svg>
  );
}

function StackPreview() {
  const groups = [[50, 30, 20], [40, 35, 25], [55, 25, 20], [45, 40, 15]];
  const colors = ["#4f46e5", "#818cf8", "#c7d2fe"];
  return (
    <svg viewBox="0 0 200 110" className="w-full max-w-[200px]">
      {groups.map((g, gi) => {
        let y = 105;
        return g.map((h, si) => {
          y -= h;
          return <rect key={si} x={20 + gi * 44} y={y} width={28} height={h} fill={colors[si]} opacity={0.85} rx={si === 0 ? 4 : 0} />;
        });
      })}
      <line x1="10" y1="107" x2="190" y2="107" stroke="#e2e8f0" strokeWidth="1" />
    </svg>
  );
}

const PREVIEWS = {
  bar: BarPreview,
  hbar: BarPreview,
  "grp-period": BarPreview,
  trend: LinePreview,
  "stack-period": LinePreview,
  pie: PiePreview,
  box: BoxPreview,
  radar: RadarPreview,
  kpi: KpiPreview,
  selector: KpiPreview,
  "tbl-resumen": TablePreview,
  "tbl-lista": TablePreview,
  "tbl-progreso": TablePreview,
  stack: StackPreview,
};

export default function Step3Preview({ comp, config, answers }) {
  const PreviewComp = PREVIEWS[comp?.id] ?? BarPreview;

  return (
    <div className="space-y-4">
      <div className="border border-dashed border-slate-300 dark:border-slate-600 rounded-2xl p-6 flex flex-col items-center gap-4 bg-slate-50/60 dark:bg-slate-800/30 min-h-[220px] justify-center">
        <PreviewComp />
        <div className="text-center">
          <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{comp?.name}</p>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Vista previa — datos de ejemplo</p>
        </div>
        <div className="flex flex-wrap gap-1.5 justify-center">
          {config.steps.map((s, i) => {
            const ans = answers[i];
            if (ans === undefined) return null;
            const opt = s.opts[ans];
            return (
              <span
                key={i}
                className="inline-flex items-center gap-1 text-[11px] bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-800/40 px-2 py-1 rounded-lg font-mono"
              >
                {opt.code}
              </span>
            );
          })}
        </div>
      </div>

      <div className="rounded-xl border border-emerald-200 dark:border-emerald-800/40 bg-emerald-50 dark:bg-emerald-900/10 px-4 py-3 flex items-start gap-3">
        <div className="w-5 h-5 min-w-[20px] rounded-full bg-emerald-500 flex items-center justify-center mt-0.5">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            <path d="M2 5L4 7L8 3" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div>
          <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">Listo para agregar</p>
          <p className="text-[11px] text-emerald-600/80 dark:text-emerald-500/80 mt-0.5 leading-relaxed">
            El componente <span className="font-medium">{comp?.name}</span> se añadirá al dashboard con la configuración seleccionada. Podrás reordenarlo libremente.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 divide-y divide-slate-100 dark:divide-slate-700/60">
        <div className="px-4 py-2.5 flex items-center justify-between">
          <span className="text-[11px] text-slate-500 dark:text-slate-400">Componente</span>
          <span className="text-xs font-medium text-slate-700 dark:text-slate-300">{comp?.name}</span>
        </div>
        {config.steps.map((s, i) => {
          const ans = answers[i];
          if (ans === undefined) return null;
          const opt = s.opts[ans];
          return (
            <div key={i} className="px-4 py-2.5 flex items-center justify-between">
              <span className="text-[11px] text-slate-500 dark:text-slate-400">
                {s.title.split("—")[0].trim()}
              </span>
              <span className="inline-flex items-center gap-1.5 text-xs">
                <span className="text-slate-700 dark:text-slate-300 font-medium">{opt.name}</span>
                <code className="text-[11px] font-mono bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 px-1.5 py-0.5 rounded">
                  {opt.code}
                </code>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
