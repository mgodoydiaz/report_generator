/**
 * Functions — página de funciones reusables (B10).
 *
 * Hoy contiene 1 sección:
 *   - Mapeos: tablas reusables {valor → label} por rangos o discreto
 *
 * Pendiente para próximas iteraciones:
 *   - Bulk operations sobre metric_data (replace + recalcular columna)
 *   - Funciones derivadas guardadas (wrappers de agg/slope/delta)
 */
import { useState } from 'react';
import { Map as MapIcon, Wrench, Wand2 } from 'lucide-react';
import MappingsManager from '../components/functions/MappingsManager';
import BulkOpsManager from '../components/functions/BulkOpsManager';

const SECTIONS = [
  { id: 'mappings', label: 'Mapeos', icon: MapIcon, description: 'Tablas valor → categoría reusables (rangos o discreto)' },
  { id: 'bulk', label: 'Operaciones masivas', icon: Wand2, description: 'Buscar/reemplazar y recalcular columnas con mapeos' },
  { id: 'derived', label: 'Funciones derivadas', icon: Wrench, description: 'Wrappers de agg/slope/delta (próx.)' },
];

export default function Functions() {
  const [section, setSection] = useState('mappings');

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-3xl font-bold text-slate-800 dark:text-white">Funciones</h1>
        <p className="text-sm text-slate-400 mt-1">
          Mapeos reusables, operaciones masivas y funciones derivadas.
        </p>
      </div>

      {/* Tabs de sección */}
      <div className="flex border-b border-slate-200 dark:border-slate-800">
        {SECTIONS.map((s) => {
          const Icon = s.icon;
          const active = section === s.id;
          const disabled = s.id === 'derived';
          return (
            <button
              key={s.id}
              onClick={() => !disabled && setSection(s.id)}
              disabled={disabled}
              className={`inline-flex items-center gap-1.5 px-4 py-2 text-sm border-b-2 ${
                active
                  ? 'border-indigo-600 text-indigo-600 font-semibold'
                  : disabled
                    ? 'border-transparent text-slate-300 cursor-not-allowed'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
              title={disabled ? 'Próximamente' : s.description}
            >
              <Icon size={14} /> {s.label}
              {disabled && <span className="text-[10px] px-1.5 py-0 rounded bg-slate-100 text-slate-400 ml-1">Próx.</span>}
            </button>
          );
        })}
      </div>

      {/* Contenido */}
      {section === 'mappings' && <MappingsManager />}
      {section === 'bulk' && <BulkOpsManager />}
      {section === 'derived' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-12 text-center text-slate-400">
          Sección en desarrollo
        </div>
      )}
    </div>
  );
}
