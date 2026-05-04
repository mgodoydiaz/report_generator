# Sprint 4 — Configurabilidad, tests, documentación

**Objetivo:** exponer todas las props relevantes de los componentes del dashboard en un formulario dinámico dentro del `LayoutEditorModal`. Hacerlo documentado y testeado.

**Duración estimada (con IA):** 1 día (~8.5h)

**Precondición:** Sprint 2 completo — todos los componentes nuevos existen.

---

## Checklist

### S4.1 · Schema `configurableProps` en `componentDefs.js` · 🧠 Sonnet · ⚡ medio · ⏱ 2h

- [ ] Por cada componente en [componentDefs.js](../frontend/src/components/add-component/componentDefs.js), agregar campo `configurableProps: []`
- [ ] Schema por prop:
  ```js
  {
    name: "topN",           // nombre de la prop que recibe el componente
    type: "number",         // text | number | select | boolean | color | field_picker | group_field
    label: "Top N",         // mostrado al usuario
    help: "Cuántos alumnos mostrar",  // tooltip
    default: 10,
    min: 1, max: 100,       // para number
    options: [...],         // para select
    fieldKind: "level",     // para field_picker: filtra dims del indicador
  }
  ```
- [ ] Priorizar los 12 componentes más usados:
  - `TrendKPI`, `StackedCountByGroup`, `HeatmapMatrix`, `PivotTable`, `StudentRiskList`, `TransitionMatrix`, `ImprovementRateByGroup`, `BarByGroup`, `BoxPlotByGroup`, `TrendLine`, `RadarByGroup`, `DistributionHist`

### S4.2 · `LayoutEditorModal` renderiza formulario dinámico · 🧠 Sonnet · ⚡ alto · ⏱ 2.5h

- [ ] En [LayoutEditorModal.jsx](../frontend/src/components/LayoutEditorModal.jsx): después de seleccionar un componente en el wizard, si `compDef.configurableProps?.length > 0`, renderizar un formulario
- [ ] Componentes de formulario por tipo:
  - `text` / `number` → `<input>`
  - `select` → `<select>` con `options`
  - `boolean` → `<input type="checkbox">`
  - `color` → `<input type="color">`
  - `field_picker` → `<select>` poblado con dims del indicador (filtrado por `fieldKind` si aplica)
  - `group_field` → `<select>` con los `column_roles` definidos
- [ ] El formulario actualiza el JSON del item en el layout
- [ ] Preserva props no declaradas en `configurableProps` (por si hay props custom)

### S4.3 · UI color picker + orden drag-drop en `NewIndicatorDrawer` · 🧠 Sonnet · ⚡ medio · ⏱ 1.5h

- [ ] Extender la sección `achievement_levels` en [NewIndicatorDrawer.jsx:843](../frontend/src/components/NewIndicatorDrawer.jsx)
- [ ] Por nivel: input de texto (name) + input color (`<input type="color">`) + botón ▲▼ para reordenar
- [ ] Al guardar, enviar al backend como `[{name, color, order}]` (ya soportado por la migración del Sprint 1.5)
- [ ] Preview: mostrar chips del nivel con su color al lado

### S4.4 · Doc `add-chart.md` · 🧠 Haiku · ⚡ bajo · ⏱ 45min

- [ ] Actualizar [.agents/workflows/add-chart.md](../.agents/workflows/add-chart.md) con sección nueva:
  - "Declarando `configurableProps`" — schema de cada tipo de prop, ejemplos
  - "Cómo probar tu componente desde el LayoutEditor"
  - Link a `componentDefs.js` como fuente de verdad

### S4.5 · Tests snapshot `processDataForDashboard` · 🧠 Sonnet · ⚡ medio · ⏱ 1h

- [ ] Crear [tests/frontend/dataProcessing.test.js](../tests/frontend/dataProcessing.test.js) usando vitest
- [ ] Fixture representativa PDL: 20 estudiantes × 3 evaluaciones × 6 subpruebas = 360 records
- [ ] Snapshots para:
  - Conteo final de records (esperado: 360 − sin_rut × 3 × 6)
  - `_worst_level_label` del primer estudiante por evaluación
  - Agregados por curso (% Crítico+Alto)
- [ ] Agregar script `npm run test:frontend` en package.json

### S4.6 · Test E2E Chrome MCP · 🧠 Sonnet · ⚡ medio · ⏱ 1h

- [ ] Crear [tests/e2e/pdl-dashboard.spec.js](../tests/e2e/pdl-dashboard.spec.js)
- [ ] Script (pseudocódigo Chrome MCP):
  1. Login como superadmin
  2. Navegar a `/results`
  3. Seleccionar indicador 3
  4. Click "Generar Dashboard"
  5. Tab 1: assert 4 KPIs + 1 stacked + 2 heatmaps renderean
  6. Tab 2: seleccionar "2° BÁSICO" → assert 6 mini-KPIs + StudentRiskList + PivotTable
  7. Tab 3: seleccionar subprueba → assert charts renderean
  8. Tab 4: assert Sankey visible + `ImprovementRateByGroup` muestra ~71% 1° básico
  9. Click "Exportar PDF" → verificar download
- [ ] Documentar cómo correrlo desde el README

### S4.7 · Smoke test indicadores SIMCE · 🧠 Haiku · ⚡ bajo · ⏱ 30min

- [ ] Chrome MCP: cargar cualquier indicador SIMCE (si existe en seed)
- [ ] Verificar que siga renderizando sin errors (no regresiones)
- [ ] Dashboard muestra al menos `totalEstudiantes > 0` en KPIs

---

## Verificación Sprint 4

- Abrir `LayoutEditorModal` → agregar `BarByGroup` → ver formulario con todas sus props editables
- Editar `achievement_levels` en `NewIndicatorDrawer` → color picker y orden drag-drop funcionan; persiste en DB
- `npm run test:frontend` → todos verdes
- E2E Chrome MCP → 9/9 pasos verdes
- Indicadores SIMCE siguen funcionando

---

## Commit sugerido

```
feat(dashboard): props configurables desde UI + tests E2E

- componentDefs: schema configurableProps en 12 componentes
- LayoutEditorModal: formulario dinámico por prop (text/number/select/bool/color/field)
- NewIndicatorDrawer: color picker + orden drag-drop para achievement_levels
- .agents/workflows/add-chart.md: documentación configurableProps
- tests/frontend: snapshots processDataForDashboard
- tests/e2e: flow completo Chrome MCP PDL
- Smoke regression: SIMCE sigue OK

Ref: sprints/sprint-04-configurability.md
```
