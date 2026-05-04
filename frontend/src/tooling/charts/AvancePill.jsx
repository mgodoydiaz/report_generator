import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { pct } from './constants';

/**
 * Pill de Avance/Mejora con color (verde positivo, rojo negativo) e icono
 * de tendencia.
 *
 * @param val      Valor numérico crudo (slope o delta del derived_fields engine).
 * @param format   "%" para multiplicar por 100 (escala 0-1, ej Rend SIMCE),
 *                 "#" para mostrar como número absoluto (ej Puntaje CV 0-100,
 *                 PPM Fluidez Lectora). Default "%" por compatibilidad.
 *
 * En SIMCE/DIA value_field=Rend (0-1) → "%" muestra "+6%".
 * En CV value_field=Puntaje (0-100) → "#" muestra "+3" puntos.
 * En FL value_field=Cantidad (PPM 0-300) → "#" muestra "+15" ppm.
 */
export default function AvancePill({ val, format = '%' }) {
    const n = parseFloat(val);
    if (isNaN(n)) return <span className="text-slate-300">—</span>;
    const color = n > 0 ? "text-emerald-600" : n < 0 ? "text-rose-600" : "text-slate-400";
    const Icon = n > 0 ? TrendingUp : n < 0 ? TrendingDown : Minus;
    const display = format === '%' ? pct(Math.abs(n)) : Math.round(Math.abs(n)).toString();
    return (
        <span className={`flex items-center gap-1 font-bold text-sm ${color}`}>
            <Icon size={14} />
            {n !== 0 ? display : ""}
        </span>
    );
}
