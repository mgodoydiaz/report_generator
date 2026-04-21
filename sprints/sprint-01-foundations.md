# Sprint 1 — Fundaciones de datos

**Objetivo:** normalizar la capa de datos del dashboard antes de tocar componentes. Nada debe romperse: los charts siguen funcionando si ignoran los campos nuevos.

**Duración estimada (con IA):** ½ día (~4.5h)

**Precondición:** Plan v2 aprobado. Rama `dev` limpia.

---

## Checklist

### S1.1 · Extraer `_rut` en `processDataForDashboard` · 🧠 Sonnet · ⚡ medio · ⏱ 45min ✅

- [x] Detectar dimensión "rut" en `result.dimensions` (por nombre case-insensitive: "rut", "run", "documento")
- [x] Mapear a campo canónico `_rut` (string sin puntos ni guiones, uppercase)
- [x] Filtrar records sin RUT — log en consola: `[processDataForDashboard] Descartados N records sin RUT`
- [x] Agregar `_rut` a todos los records del output
- **Archivo:** [frontend/src/tooling/dataProcessing.js](../frontend/src/tooling/dataProcessing.js)
- **Verificación:** en `Results.jsx` console.log del primer record → debe contener `_rut: "123456789"`

### S1.2 · Deduplicación por `(_rut, _habilidad, _evaluacion_num)` · 🧠 Sonnet · ⚡ bajo · ⏱ 30min ✅

- [x] Después de extraer `_rut`, reducir records duplicados: `(_rut, _habilidad, _evaluacion_num)` debe ser único
- [x] Regla de tie-breaking: conservar el record con mayor `temporal_label` (fecha más reciente dentro del mismo período)
- [x] Log: `[processDataForDashboard] Colapsados N duplicados`
- **Archivo:** [frontend/src/tooling/dataProcessing.js](../frontend/src/tooling/dataProcessing.js)

### S1.3 · Derivar columnas de análisis · 🧠 Sonnet · ⚡ medio · ⏱ 1h ✅

Campos a agregar por record (o por estudiante según aplique):

- [x] `_worst_level_ord` — mínimo ordinal entre todas las subpruebas del mismo `(_rut, _evaluacion_num)` (Crítico=1 es peor)
- [x] `_worst_level_label` — label del peor nivel (ej. "Crítico")
- [x] `_worst_subprueba` — nombre de la subprueba donde alcanzó ese peor nivel
- [x] `_is_urgent` — boolean, `true` si `_worst_level_label ∈ {Crítico}`
- [x] `_is_concerning` — boolean, `true` si `_worst_level_label ∈ {Crítico, Alto Riesgo}`
- [x] `_trajectory` — `improving | stable | declining | incomplete` (requiere ≥2 evaluaciones)
- [x] `_n_evaluations` — cantidad de `_evaluacion_num` distintos para ese `_rut`
- **Archivo:** [frontend/src/tooling/dataProcessing.js](../frontend/src/tooling/dataProcessing.js)
- **Decisión:** computar en `processDataForDashboard` (capa de datos, no en cada chart)
- **Verificación:** fixture con 3 estudiantes (1 urgente, 1 concerning, 1 saludable) → valida labels

### S1.4 · Memoizar `processDataForDashboard` · 🧠 Haiku · ⚡ bajo · ⏱ 15min ✅

- [x] En [ResultsRecharts.jsx](../frontend/src/pages/ResultsRecharts.jsx) envolver la llamada en `useMemo` con dependencia en `result` (raw del backend)
- [x] Actualmente ya hay `useMemo` en `computeDashboardKPIs` — replicar patrón
- **Archivo:** [frontend/src/pages/ResultsRecharts.jsx](../frontend/src/pages/ResultsRecharts.jsx) (línea ~92)

### S1.5 · Migración: `achievement_levels → [{name, color, order}]` · 🧠 Sonnet · ⚡ medio · ⏱ 1h ✅

- [x] Crear migración Alembic nueva (`d4e5f6a7b8c9`)
- [x] En `upgrade()`: iterar `indicators` y transformar `achievement_levels` (dict/string[] → lista de objetos)
- [x] En `downgrade()`: revertir a dict simple `{name: order}`
- [ ] `alembic upgrade head` en local para verificar (pendiente ejecución manual)

### S1.6 · Centralizar paleta en `constants.js` · 🧠 Sonnet · ⚡ medio · ⏱ 1h ✅

- [x] Crear helper `getLevelPalette(achievement_levels)` en [frontend/src/tooling/plotly-charts/constants.js](../frontend/src/tooling/plotly-charts/constants.js)
- [x] Reemplazar hardcodes de colores en:
  - [transition.jsx](../frontend/src/tooling/plotly-charts/transition.jsx) — colores de barras mejoró/empeoró
  - [heatmap.jsx](../frontend/src/tooling/plotly-charts/heatmap.jsx) — default colorscale 'Viridis' → 'YlOrRd'
  - [distribution.jsx](../frontend/src/tooling/plotly-charts/distribution.jsx) — stacked level colors
- [x] Propagar `achievement_levels` desde `DashboardRenderer` → PieComposition, StackedCountByGroup, StackedCountByGroupAndPeriod, ImprovementRateByGroup, HeatmapMatrix

---

## Verificación Sprint 1

1. **Unit tests** (crear [tests/frontend/dataProcessing.test.js](../tests/frontend/dataProcessing.test.js)):
   - Fixture A: 10 estudiantes, 1 sin RUT → output tiene 9 estudiantes
   - Fixture B: 1 estudiante con 2 duplicados → dedup a 1
   - Fixture C: 1 estudiante con solo v1 → `_n_evaluations=1`, `_trajectory="incomplete"`
   - Fixture D: estudiante con Crítico en FLO + Bajo en CT → `_worst_level_label="Crítico"`, `_worst_subprueba="FLO"`
2. **Dev server:** `npm run dev` → cargar dashboard PDL indicador 3 → 0 errors en consola
3. **Regresión Chrome MCP:** Tab 4 → `ImprovementRateByGroup` sigue mostrando `71% mejoró 1° básico`
4. **DB:** `alembic upgrade head` limpio, sin pérdida de datos

---

## Commit sugerido al final del sprint

```
feat(dashboard): capa de datos con RUT, dedup, derived columns y paleta centralizada

- processDataForDashboard: extrae _rut, deduplica por (rut, habilidad, eval_num),
  deriva _worst_level_*, _is_urgent, _trajectory, _n_evaluations
- Memoización en Results.jsx
- Migración: achievement_levels → [{name, color, order}]
- Paleta centralizada en plotly-charts/constants.js (getLevelPalette)
- Reemplaza hardcodes de color en transition/heatmap/distribution

Ref: sprints/sprint-01-foundations.md
```
