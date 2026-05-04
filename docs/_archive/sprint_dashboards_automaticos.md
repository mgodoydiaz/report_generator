# Sprint dashboards automáticos — scope (post-entrega lunes)

**Estado**: planificación. **No implementar antes del 2026-05-04 (entrega).**

Este documento captura el alcance del próximo gran sprint del proyecto, una vez cerrada la entrega de PDF paridad LaTeX. Es el siguiente paso natural en la evolución del software hacia "datos cargados → insight inmediato sin configuración manual".

---

## Contexto

Hoy un usuario que carga datos a una métrica nueva en `metric_data` debe:

1. Ir a `/indicators`, crear un indicador a mano
2. Asociar la métrica al indicador
3. Abrir `LayoutEditorModal` y arrastrar componentes (chart/table) configurando manualmente xField, yField, aggregation, etc.
4. Guardar
5. Ir a `/results` para finalmente ver el dashboard

Esa fricción es real: cada nueva métrica requiere ~10 minutos de configuración manual antes de ver el primer gráfico. Y muchos dashboards quedan "casi" configurados pero nunca se publican porque el usuario abandona la sesión.

**Visión del sprint**: cargar una métrica nueva genera **automáticamente** un dashboard con 3-6 visualizaciones razonables, listas para revisar y ajustar. El usuario edita lo que no le sirve, no parte desde cero.

---

## Estado actual del sistema (auditoría rápida)

| Componente | Path | Función |
|---|---|---|
| Renderer dashboards | [frontend/src/tooling/dashboardRenderer.jsx](frontend/src/tooling/dashboardRenderer.jsx) | Lee `dashboard_layout` JSON del indicador y monta los componentes Plotly correspondientes |
| Editor visual | [frontend/src/components/LayoutEditorModal.jsx](frontend/src/components/LayoutEditorModal.jsx) | Drag & drop manual de componentes, configuración por panel lateral |
| Componentes Plotly | [frontend/src/tooling/plotly-charts/](frontend/src/tooling/plotly-charts/) | Radar, transition, etc. — librería propia |
| Componentes Recharts (legacy) | [frontend/src/tooling/charts/](frontend/src/tooling/charts/) | Mantener solo, no extender |
| Páginas | [frontend/src/pages/Indicators.jsx](frontend/src/pages/Indicators.jsx), [Results.jsx](frontend/src/pages/Results.jsx) | CRUD de indicadores y visualización |
| Definiciones componentes | [frontend/src/components/add-component/componentDefs.js](frontend/src/components/add-component/componentDefs.js) | Catálogo de tipos de componentes disponibles |

**Backend**:
- `/api/indicators` (CRUD + dashboard_layout)
- `/api/metrics` (incluye `meta_json.fields` que describe qué campos tiene `value`)
- `/api/results/indicator/{id}/data` (data agregada para los charts)

---

## Pain points UX detectados

1. **Costo de arranque alto**: cargar 5 métricas hoy = ~50 min de configuración manual de dashboards. Para PHP que sube data trimestralmente esto es bloqueador.
2. **Decisión de qué graficar es repetitiva**: para casi toda métrica nueva el usuario termina haciendo bar (categórica vs numérica), boxplot (distribución), tabla pivot (drill-down). No hay valor en re-decidir cada vez.
3. **No hay feedback inmediato**: tras cargar data el usuario tiene que navegar 3 pantallas antes de "ver algo".
4. **Layouts huérfanos**: indicadores con `dashboard_layout` vacío o a medias se acumulan. No hay default razonable.
5. **Falta inspector de schema**: el usuario no sabe qué dimensiones/fields tiene la métrica que cargó hasta que abre el LayoutEditor.

---

## Visión propuesta

### Auto-generación al crear/asociar métrica

Cuando un indicador se crea o se le asocia una métrica nueva, el backend genera un `dashboard_layout` default basado en heurísticas sobre el `meta_json` y las dimensiones asociadas. El usuario lo abre y ya hay 4-6 paneles razonables.

### Heurísticas iniciales (regla → componente)

| Tipo de campo / dimensión | Componente sugerido | Notas |
|---|---|---|
| Métrica numérica + 1 dimensión categórica con < 15 valores | `BarChart` (avg por categoría) | Default principal |
| Métrica numérica + 1 dimensión temporal (Mes, Año, Fecha) | `LineChart` o `BarChart` (avg por periodo) | Detectar por nombre de dim |
| Métrica numérica + 2 dimensiones categóricas | `GroupedBarChart` | Hue secundario |
| Métrica numérica + 1 dimensión con muchos valores únicos | `BoxPlot` (distribución) | Si `n_unique > 15` |
| Métrica `object` con campo `Nivel` o `Categoria` | `StackedBarChart` (cantidad por nivel/categoría) | |
| Métrica con campo numérico continuo (sin agrupación obvia) | `Histogram` | |
| Catch-all | `PivotTable` (rows = primera dim, values = primera métrica) | Siempre incluir |

### Flujo

```
Usuario asocia métrica al indicador
        ↓
Backend: POST /indicators/{id}/auto-layout
        ↓
backend.indicators.autolayout.suggest(metric, dimensions) → dashboard_layout JSON
        ↓
Frontend: refresh y muestra dashboard con badge "Generado automáticamente — ajusta lo que necesites"
        ↓
Usuario edita en LayoutEditor (componentes ya están, solo afina)
```

---

## Sub-sprints sugeridos (post-lunes)

### Sub-sprint A — Backend autolayout (1-2 días)

- `backend/services/dashboard_autolayout.py` con:
  - `suggest_layout(metric, dimensions, sample_data) → dict`
  - Heurísticas implementadas para los 7 casos de la tabla
  - Tests unitarios de cada heurística (input → layout esperado)
- Endpoint `POST /api/indicators/{id}/auto-layout` que:
  - Resuelve métrica + dimensiones + sample de `metric_data`
  - Llama `suggest_layout`
  - Devuelve el JSON sin persistirlo (preview)
- Endpoint `POST /api/indicators/{id}/apply-auto-layout` que persiste

### Sub-sprint B — Frontend integración (1 día)

- Botón "Generar layout automático" en `Indicators.jsx` (con preview antes de aplicar)
- Trigger automático cuando se asocia una métrica nueva (con confirmación)
- Badge visual "Auto-generado" en `Results.jsx` con CTA "Ajustar"

### Sub-sprint C — Polish (0.5 día)

- Inspector de schema en `LayoutEditor` (panel lateral muestra `meta_json.fields` y dimensiones disponibles con tipos)
- Mejorar mensaje de "indicador sin layout" → ofrecer auto-generar
- Onboarding doc en `docs/usuario/dashboards_automaticos.md`

---

## Decisiones pendientes (necesitan input del usuario)

1. **¿Aplicar auto-layout silenciosamente al crear indicador, o requerir confirmación?**
   - Silencioso: friction 0, riesgo de "ruido" si las heurísticas eligen mal
   - Confirmación: 1 clic extra, mejor experiencia educativa
   - **Recomendación**: confirmación con preview, los primeros 3 meses; después evaluar pasar a silencioso

2. **¿Los dashboards auto-generados quedan marcados como tal en BD?**
   - Útil para métricas de adopción (cuántos usuarios editan vs aceptan default)
   - Agrega un campo boolean `dashboard_layout_auto_generated` en `Indicator`
   - **Recomendación**: sí, columna nueva con migración Alembic

3. **¿Las heurísticas son configurables por organización?**
   - Hoy: hardcoded en código
   - Futuro: tabla `org_settings` con overrides
   - **Recomendación**: hardcoded ahora, configurable cuando haya 2+ orgs con preferencias distintas

4. **¿Sample para detección de cardinalidad: cuánto?**
   - Para "muchos valores únicos" hay que contar. ¿Sobre toda la data o sample?
   - **Recomendación**: `SELECT DISTINCT ... LIMIT 100` — suficiente para clasificar < 15 vs ≥ 15

---

## No-goals (este sprint NO incluye)

- **No** se reemplaza el LayoutEditor manual — solo se le agrega un punto de partida
- **No** se cambia el formato de `dashboard_layout` (mismo schema actual)
- **No** se tocan los componentes Recharts legacy
- **No** se agregan nuevos tipos de chart (solo se eligen mejor entre los existentes)
- **No** se hace ML / clustering / detección de outliers — son reglas determinísticas

---

## Estimación total

| Sub-sprint | Días | Personas |
|---|---|---|
| A — Backend | 1.5 | 1 |
| B — Frontend | 1 | 1 |
| C — Polish | 0.5 | 1 |
| **Total** | **3 días** | **1 dev** |

Realista para una semana laboral con buffer de testing y ajustes a heurísticas tras feedback.

---

## Métricas de éxito

- **Tiempo desde "métrica cargada" a "primer gráfico visto"**: < 30 segundos (hoy: ~10 min)
- **% de indicadores con layout no-vacío en BD**: > 95% (hoy: ~40% estimado)
- **% de usuarios que editan el auto-layout vs lo aceptan tal cual**: idealmente 50/50 (significa que las heurísticas son buenas y el editor agrega valor)
