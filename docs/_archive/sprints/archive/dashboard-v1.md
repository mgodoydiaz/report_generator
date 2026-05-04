# Archive — Dashboard PDL v1 (COMPLETADO)

> Este archivo conserva el plan original del dashboard PDL v1 que ya se mergeó a `dev`. Su propósito es histórico: permite entender decisiones antiguas sin contaminar el master plan activo.

**Periodo:** ~2026-04-18 a 2026-04-20
**Estado:** ✅ Mergeado en `dev`. Sucedido por el plan v2 (ver [../MASTER_PLAN.md](../MASTER_PLAN.md)).

---

## Objetivo original (v1)

Construir un dashboard interactivo para el indicador PDL (IDEL-Woodcock, `id_indicator=3`), con 4 pestañas:

1. **Panorama** — métricas globales del colegio
2. **Detalle por Curso** — drill-down al nivel de curso
3. **Por Subprueba** — comparación entre subpruebas (CT, FLO, FNL, FSF, ILP, VSD)
4. **Síntesis** — evolución temporal y tasa de mejora

## Componentes implementados

- `SubpruebaSelector` (nuevo) — dropdown para filtrar por habilidad
- `ImprovementRateByGroup` (nuevo) — barras stacked con % mejoró/mantuvo/empeoró por grupo
- Integración con `PivotTable`, `HeatmapMatrix`, `StackedCountByGroup`, `BarByGroup`, `BoxPlotByGroup`, `TrendLine`
- Layout JSON guardado en `indicators.dashboard_layout`

## QA ejecutada y bugs corregidos

| Bug | Ubicación | Fix |
|---|---|---|
| PivotTable mostraba solo "NOMBRE \| TOTAL" | layout JSON usaba `columns:` cuando componente lee `cols:` | Rename field en layout |
| Tab 2 PivotTable mostraba 196 rows (todos cursos) vs 34 esperados | Componente ignoraba `dataSource` | Add switch `dataSource: 'cursoEstudiantes'` en `dashboardRenderer.jsx` |
| "Sin datos para calcular transiciones" en ImprovementRateByGroup | Defaults apuntaban a `_rut` (no existía) y `_nivel_de_riesgo` (campo real: `_logro`); entity key simple no distinguía grupos | Update defaults en `transition.jsx`; entity key composite `rut\|\|group` |

## Validación final

- ✅ Todas las tabs renderean sin errors
- ✅ `71% mejoró 1° básico` en Tab 4 concuerda con PDF de referencia
- ✅ Selectores de curso y subprueba funcionales
- ✅ Filtros propagados al `dashboardRenderer`

## Limitaciones detectadas (que motivaron el v2)

1. **Mezcla de escalas entre subpruebas** — `BarByGroup`/`BoxPlotByGroup`/`TrendLine` mostraban métricas sumadas de subpruebas con escalas distintas, llevando a interpretaciones erróneas
2. **KPIs sin accionabilidad** — solo total de estudiantes, sin indicadores de urgencia
3. **PivotTable sin valor visual** — solo texto, sin coloreo por nivel
4. **No responsivo en mobile** — Tab 2 no colapsaba bien
5. **Usaba `_nombre` como key en lugar de `_rut`** — riesgo de colisiones con nombres repetidos
6. **Trayectorias incompletas mal manejadas** — estudiantes con 1 sola evaluación no se excluían de charts de trayectoria
7. **Paleta de colores generada dinámicamente (HSL)** sin persistir en DB — inconsistente entre indicadores

Estas limitaciones originaron la crítica de "analista pedagógico + desarrollador senior" y el radar de gaps que culminó en el plan v2.

## Archivos tocados (referencia histórica)

- `frontend/src/tooling/dashboardRenderer.jsx` — rendering por tab
- `frontend/src/tooling/plotly-charts/transition.jsx` — ImprovementRateByGroup
- `frontend/src/tooling/dataProcessing.js` — transformación de records
- `frontend/src/components/add-component/componentDefs.js` — registro
- `frontend/src/pages/ResultsRecharts.jsx` — estado global del dashboard
- Layout JSON en tabla `indicators`, columna `dashboard_layout`, fila `id_indicator=3`

## Commit relevante

Buscar en `git log` con:
```
git log --oneline --grep="dashboard.*PDL\|indicator.*3" dev
```

---

**Siguiente:** ver [../sprint-01-foundations.md](../sprint-01-foundations.md) para el rediseño v2.
