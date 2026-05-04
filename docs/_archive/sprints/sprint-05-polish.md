# Sprint 5 — Micro-copy, accesibilidad y pulido final

**Objetivo:** dejar el dashboard listo para que un profesor lo use sin necesidad de un analista al lado.

**Duración estimada (con IA):** ½ día (~3.75h)

**Precondición:** Sprints 1-4 completos. Layout v2 publicado.

---

## Checklist

### S5.1 · Micro-copy interpretativo · 🧠 Sonnet · ⚡ bajo · ⏱ 1.5h

- [ ] Crear helper `frontend/src/tooling/plotly-charts/microcopy.js` con pure functions por chart
- [ ] Cada función recibe los datos procesados del chart y retorna un string interpretado
- [ ] Renderizar debajo de cada chart como `<p className="text-sm text-slate-500 italic">`

Templates (todos determinísticos — sin IA):

| Chart | Template |
|---|---|
| `StackedCountByGroup` | "El curso con mayor riesgo urgente es **{curso_top}** con **{n_critico_alto}** estudiantes en Crítico+Alto ({pct}%). **{curso_bottom}** es el más saludable con {pct_bottom}%." |
| `HeatmapMatrix` | "La combinación más crítica es **{curso}×{subprueba}** ({pct} en Crítico+Alto, {n} estudiantes)." |
| `ImprovementRateByGroup` | "**{pct_mejoro}%** de los estudiantes mejoró de nivel entre {primera_eval} y {ultima_eval}. {curso_lider} lidera con {pct}% mejorados." |
| `PivotTable` footer | "{n_completos} estudiantes con evaluación completa · {n_parciales} parciales (excluidos de análisis de trayectoria)." |
| `TransitionMatrix` | "De los {n} alumnos en Crítico en {primera_eval}, **{n_salen}** salieron del nivel en {ultima_eval}." |

### S5.2 · Estados vacíos contextuales · 🧠 Haiku · ⚡ bajo · ⏱ 45min

- [ ] Tres mensajes distintos según causa:

| Causa | Mensaje |
|---|---|
| Filtros sin matches | "Ningún estudiante coincide con los filtros actuales. **[Botón: Limpiar filtros]**" |
| Curso sin subprueba | "El curso {curso} no rindió la subprueba {subprueba}." |
| Sin trayectoria | "Se requieren al menos 2 evaluaciones para calcular trayectorias. Datos actuales: {periodos_disponibles}." |

- [ ] Distinguir causas en los charts de trayectoria (revisar [transition.jsx:69](../frontend/src/tooling/plotly-charts/transition.jsx))

### S5.3 · Accesibilidad · 🧠 Haiku · ⚡ bajo · ⏱ 30min

- [ ] En Plotly stacked bars: agregar `marker.pattern.shape` distinto por nivel (ej. `""`, `"/"`, `"\\"`, `"x"` para crítico-alto-cierto-bajo) → ayuda a usuarios daltónicos
- [ ] En labels de niveles agregar emojis prefix: 🔴 Crítico, 🟠 Alto Riesgo, 🟡 Cierto Riesgo, 🟢 Bajo Riesgo
- [ ] Verificar contraste WCAG AA de la paleta nueva

### S5.4 · QA final Chrome MCP · 🧠 Sonnet · ⚡ bajo · ⏱ 45min

- [ ] Screenshot de cada uno de los 4 tabs
- [ ] Verificar que la paleta se mantiene consistente entre charts
- [ ] Redimensionar a 768px → todo colapsa limpio
- [ ] Click en botón "Exportar PDF" → descarga > 0 bytes
- [ ] Verificar que `LayoutEditorModal` abre sin errors
- [ ] Adjuntar screenshots en el PR

### S5.5 · Commit final · 🧠 Haiku · ⚡ bajo · ⏱ 15min

Mensaje:

```
feat(dashboard): PDL v2 completo — worst-level, Sankey, configurabilidad, A11y

Sprint 1: capa de datos (RUT, dedup, derived cols, memoización, paleta por indicador)
Sprint 2: TrendKPI, PivotTable semáforo, StudentRiskList, TransitionMatrix Sankey,
          responsividad Tab 2, export PDF/PNG/CSV, flag requiresSingleMetricContext
Sprint 3: layout v2 para indicador 3
Sprint 4: configurableProps + formulario dinámico + color picker + tests
Sprint 5: micro-copy interpretativo + estados vacíos + pattern_shape A11y + emojis

Verificación:
- Unit tests processDataForDashboard: fixtures con sin-RUT, duplicados, incompletos, peor-nivel
- E2E Chrome MCP: 4 tabs + 71% regresión
- Migración: achievement_levels → [{name, color, order}]
- Responsive: 768px OK

Diferidos (ver sprints/MASTER_PLAN.md): memoización backend, snapshots,
roles, benchmarks IDEL, Sprint 6 PDF WeasyPrint, telemetría, eval ECharts.
```

---

## Verificación end-to-end global (del plan)

1. **Unit:** `npm run test:frontend` → 100% pass
2. **Migración:** `alembic upgrade head` limpio
3. **Dev server:** 0 errors consola en dashboard PDL
4. **Chrome MCP E2E:** Login → Results → Indicator 3 → 4 tabs → Export
5. **Export:** PDF > 0 bytes, PNG desde modebar, CSV download
6. **Configurabilidad:** `LayoutEditorModal` → formulario dinámico; `NewIndicatorDrawer` → color picker
7. **Responsive:** 768px Tab 2 → 1 col sin overflow
8. **Accesibilidad:** `pattern_shape` visible
9. **No regresiones:** SIMCE OK
10. **Commit `dev`:** mensaje acordado

---

## Qué hacer después

1. Abrir PR `dev → main` cuando el usuario lo autorice
2. Desplegar staging → validar con datos reales de alguna escuela
3. Empezar Sprint 6 (PDF WeasyPrint) cuando el dashboard esté estable
