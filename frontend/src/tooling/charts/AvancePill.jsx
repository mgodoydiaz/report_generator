import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { pct } from './constants';

export default function AvancePill({ val }) {
    const n = parseFloat(val);
    if (isNaN(n)) return <span className="text-slate-300">—</span>;
    const color = n > 0 ? "text-emerald-600" : n < 0 ? "text-rose-600" : "text-slate-400";
    const Icon = n > 0 ? TrendingUp : n < 0 ? TrendingDown : Minus;
    return (
        <span className={`flex items-center gap-1 font-bold text-sm ${color}`}>
            <Icon size={14} />
            {n !== 0 ? pct(Math.abs(n)) : ""}
        </span>
    );
}
