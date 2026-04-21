# Sprint 2 — Componentes nuevos y corregidos

**Objetivo:** entregar los componentes que el layout v2 necesita, sin tocar el layout todavía.

**Duración estimada (con IA):** 1 día (~10h)

**Precondición:** Sprint 1 completo y testeado. `achievement_levels` en formato nuevo disponible en frontend.

---

## Checklist

### S2.1 · `TrendKPI` · 🧠 Sonnet · ⚡ medio · ⏱ 1.5h

- [ ] Nuevo componente: `frontend/src/components/dashboard/TrendKPI.jsx`
- [ ] Props: `label`, `value`, `previousValue` (opcional), `sparklineData` (opcional array), `format` (number|percent), `invertColors` (default false — si true, menor es mejor)
- [ ] Render: label arriba, valor grande en el centro, Δ abajo coloreado (verde = mejora, rojo = empeora según `invertColors`), sparkline mini (SVG inline 80×20)
- [ ] Registrar en [componentDefs.js](../frontend/src/components/add-component/componentDefs.js)
- [ ] Render case en [dashboardRenderer.jsx](../frontend/src/tooling/dashboardRenderer.jsx)

### S2.2 · `PivotTable` con semáforo · 🧠 Sonnet · ⚡ medio · ⏱ 1.5h

- [ ] Extender [pivotTable.jsx](../frontend/src/tooling/plotly-charts/pivotTable.jsx) con prop `semaphoreField` (string: campo cuyo valor determina color) + `semaphoreMode` (`cell` | `row`)
- [ ] Usa paleta de `achievement_levels` (del Sprint 1) para colorear celdas cuyo valor coincida con un nivel
- [ ] Si el valor es numérico → colorear según thresholds del indicador
- [ ] Hover: badge con nombre del nivel
- **Archivo:** [frontend/src/tooling/plotly-charts/pivotTable.jsx](../frontend/src/tooling/plotly-charts/pivotTable.jsx)

### S2.3 · `StudentRiskList` · 🧠 Sonnet · ⚡ medio · ⏱ 1.5h

- [ ] Nuevo componente: `frontend/src/components/dashboard/StudentRiskList.jsx`
- [ ] Props: `records` (estudiantes), `topN` (default 10), `riskField` (default `_worst_level_ord`), `trajectoryField` (default `_trajectory`)
- [ ] Orden: `_worst_level_ord` asc (peor primero), tie-break por `_nombre`
- [ ] Cada row: avatar/inicial, nombre, RUT, badge del peor nivel con color, mini-badge de subprueba crítica, icon de trayectoria (↗ mejorando / → estable / ↘ empeorando)
- [ ] Link click → filtra el resto del dashboard por ese estudiante (emit `onStudentSelect`)

### S2.4 · `TransitionMatrix` (Sankey) · 🧠 Opus · ⚡ alto · ⏱ 2.5h

- [ ] Nuevo componente: `frontend/src/tooling/plotly-charts/transitionMatrix.jsx`
- [ ] Usa Plotly `type: 'sankey'`. Nodos = nivel × momento (4 niveles × 2 momentos = 8 nodos)
- [ ] Links = número de estudiantes que transitaron de nivel_v1 → nivel_vN
- [ ] Colorea links por destino (mismo sistema paleta)
- [ ] Props: `records`, `timeField` (default `_evaluacion_num`), `entityField` (default `_rut`), `levelField` (default `_worst_level_label`), `achievement_levels`
- [ ] Excluye estudiantes con `_n_evaluations < 2`
- [ ] Hover: "N estudiantes pasaron de {nivelA} a {nivelB}"
- [ ] Registrar en [componentDefs.js](../frontend/src/components/add-component/componentDefs.js) + [index.js](../frontend/src/tooling/plotly-charts/index.js)

### S2.5 · Responsividad Tab 2 · 🧠 Sonnet · ⚡ bajo · ⏱ 1h

- [ ] En [dashboardRenderer.jsx](../frontend/src/tooling/dashboardRenderer.jsx) el grid de Tab 2 debe ser `flex flex-wrap gap-4` con cards `min-w-[300px] flex-1 basis-[48%]`
- [ ] Breakpoint <1024px → `basis-full`
- [ ] Probar con DevTools responsive mode a 768px, 480px

### S2.6 · Limpiar filtros en `onTabChange` · 🧠 Haiku · ⚡ bajo · ⏱ 20min

- [ ] En [dashboardRenderer.jsx](../frontend/src/tooling/dashboardRenderer.jsx): `useEffect(() => { setCursoActivo(null); setSubpruebaActiva(null); setItemFilters({}); }, [activeTab])`
- [ ] Verificar que no rompa flujos que dependen de filtros persistentes (TreeView del usuario)

### S2.7 · Botón "Exportar PDF" · 🧠 Sonnet · ⚡ bajo · ⏱ 45min

- [ ] Header de [ResultsRecharts.jsx](../frontend/src/pages/ResultsRecharts.jsx): botón al lado del botón "Generar Dashboard"
- [ ] `onClick`: `POST /indicators/{id}/export-pdf` con `filters` en body
- [ ] Response: blob → trigger download con `{indicator_name}_{timestamp}.pdf`
- [ ] Loading state + toast de éxito/error
- **Endpoint:** ya existe en [backend/routers/indicators.py:219-254](../backend/routers/indicators.py:219)

### S2.8 · Plotly modebar + Export CSV · 🧠 Sonnet · ⚡ medio · ⏱ 1.5h

- [ ] En [PlotlyWrapper.jsx](../frontend/src/tooling/plotly-charts/PlotlyWrapper.jsx): habilitar `config: { displayModeBar: 'hover', toImageButtonOptions: { format: 'png', scale: 2 } }`
- [ ] Botón custom "Descargar CSV" por chart: usa los `records` del prop, los convierte a CSV y descarga
- [ ] Wrapper component `<ChartCard>` que envuelve cualquier chart y agrega botón export

### S2.9 · Flag `requiresSingleMetricContext` · 🧠 Haiku · ⚡ bajo · ⏱ 30min

- [ ] En [componentDefs.js](../frontend/src/components/add-component/componentDefs.js) agregar flag a `BarByGroup`, `BoxPlotByGroup`, `TrendLine`
- [ ] En [LayoutEditorModal.jsx](../frontend/src/components/LayoutEditorModal.jsx) mostrar warning naranja si el layout incluye uno de estos charts sin un filtro de subprueba/habilidad aplicado
- [ ] En dev mode (`import.meta.env.DEV`): `console.warn` desde `dashboardRenderer` si detecta el caso

---

## Verificación Sprint 2

- Chrome MCP: aislar cada componente nuevo (agregar temporalmente al layout de indicador 3)
- Responsive: redimensionar a 768px → Tab 2 colapsa limpio
- Click "Exportar PDF" → descarga > 0 bytes
- Modebar visible en todos los charts. Click PNG descarga
- Warning visible en consola al poner `BarByGroup` sin filtro

## Commit sugerido

```
feat(dashboard): componentes PDL v2 — TrendKPI, Sankey, semáforo, responsividad

- TrendKPI con Δ coloreado + sparkline
- PivotTable con prop semaphoreField (colorea por nivel)
- StudentRiskList con top alumnos urgentes
- TransitionMatrix Sankey (requires _n_evaluations >= 2)
- Tab 2 responsivo (flex-wrap + breakpoints)
- Filtros limpiados en onTabChange
- Botón Exportar PDF + modebar Plotly + CSV export
- Flag requiresSingleMetricContext para charts que mezclan escalas

Ref: sprints/sprint-02-components.md
```
