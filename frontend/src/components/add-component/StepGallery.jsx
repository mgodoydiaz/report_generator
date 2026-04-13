import {
    BarChart2, BoxSelect, PieChart, AlignLeft, Layers,
    BarChartHorizontal, CalendarDays, TrendingUp, Radar,
    LayoutList, TableProperties, ListChecks,
    Sparkles, SlidersHorizontal,
} from 'lucide-react';
import { CHART_GROUPS, CHART_COMPONENTS, TABLE_COMPONENTS, SPECIAL_COMPONENTS } from './componentDefs';

// Ícono por componente id
const COMP_ICONS = {
    // Especiales
    kpis:                          Sparkles,
    course_selector:               SlidersHorizontal,
    // Tablas
    SummaryTable:                  TableProperties,
    DetailListTable:               LayoutList,
    DetailListWithProgress:        ListChecks,
    // Gráficos simples
    BarByGroup:                    BarChart2,
    BoxPlotByGroup:                BoxSelect,
    PieComposition:                PieChart,
    HorizontalBarByDimension:      BarChartHorizontal,
    StackedCountByGroup:           Layers,
    // Doble eje X
    DoubleGroupedBar:             CalendarDays,
    GroupedBarByPeriod:            CalendarDays,
    StackedCountByGroupAndPeriod:  CalendarDays,
    // Especiales
    RadarProfile:                  Radar,
    // Temporales
    TrendLine:                     TrendingUp,
};

const TYPE_COLOR = {
    kpis:            'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-700',
    course_selector: 'bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700',
    table:           'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-700',
    chart:           'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-700',
};

const ICON_COLOR = {
    kpis:            'text-amber-500',
    course_selector: 'text-slate-400',
    table:           'text-indigo-500',
    chart:           'text-emerald-600',
};

const CATEGORIES = [
    {
        key: 'special',
        label: 'Especiales',
        items: SPECIAL_COMPONENTS,
    },
    {
        key: 'table',
        label: 'Tablas',
        items: TABLE_COMPONENTS.filter(c => !c.legacy),
    },
    ...CHART_GROUPS.map(g => ({
        key: g.key,
        label: g.label,
        items: CHART_COMPONENTS.filter(c => c.group === g.key),
    })),
];

export default function StepGallery({ selectedComp, onSelect }) {
    return (
        <div className="space-y-5">
            {CATEGORIES.map(cat => (
                <div key={cat.key}>
                    <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">
                        {cat.label}
                    </p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {cat.items.map(comp => {
                            const compId = comp.id || comp.type;
                            const isSelected = (selectedComp?.id || selectedComp?.type) === compId;
                            const Icon = COMP_ICONS[compId];
                            const typeKey = comp.type === 'chart' ? 'chart'
                                : comp.type === 'table' ? 'table'
                                : compId;
                            const colorCard = isSelected
                                ? 'border-indigo-400 dark:border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 ring-2 ring-indigo-200 dark:ring-indigo-800/50'
                                : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50/50 dark:hover:bg-indigo-900/10';
                            const iconBg = TYPE_COLOR[typeKey] || TYPE_COLOR.chart;
                            const iconText = isSelected ? 'text-indigo-600 dark:text-indigo-400' : (ICON_COLOR[typeKey] || ICON_COLOR.chart);

                            return (
                                <button
                                    key={compId}
                                    onClick={() => onSelect(comp)}
                                    className={`relative flex flex-col items-start gap-2 p-3 rounded-xl border text-left transition-all ${colorCard}`}
                                >
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${iconBg}`}>
                                        {Icon && <Icon size={15} className={iconText} />}
                                    </div>
                                    <div>
                                        <p className={`text-xs font-medium leading-tight ${isSelected ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-800 dark:text-slate-200'}`}>
                                            {comp.label}
                                        </p>
                                        {comp.axisConfig?.length > 0 && (
                                            <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5 leading-tight">
                                                {comp.axisConfig.length} campo{comp.axisConfig.length > 1 ? 's' : ''} a configurar
                                            </p>
                                        )}
                                    </div>
                                    {isSelected && (
                                        <div className="absolute top-2 right-2 w-4 h-4 rounded-full bg-indigo-600 flex items-center justify-center">
                                            <svg width="9" height="9" viewBox="0 0 9 9" fill="none">
                                                <path d="M1.5 4.5L3.5 6.5L7.5 2.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                        </div>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </div>
            ))}
        </div>
    );
}
