# PDL Dashboard — Master Plan (ancla de contexto)

> Archivo de resiliencia. Si el context window se corta, este doc permite retomar el trabajo sin leer toda la conversación previa.

## Estado actual

- **Rama:** `dev_1`
- **Indicador objetivo:** `id=3` (PDL / IDEL-Woodcock, evaluación de lectura por subpruebas)
- **Sprint activo:** Sprints 2-5 cerrados (priorizando escalabilidad). Siguiente: sprint de informes hardcodeados para cumplir entregas.
- **Plan origen:** `C:\Users\magod\.claude\plans\en-primer-lugar-quiero-foamy-whisper.md` (aprobado)
- **Fecha de plan aprobado:** 2026-04-21
- **Fecha de cierre v2:** 2026-04-21

## Índice de sprints

| # | Archivo | Estado |
|---|---|---|
| 1 | [sprint-01-foundations.md](./sprint-01-foundations.md) | ✅ completo |
| 2 | [sprint-02-components.md](./sprint-02-components.md) | ✅ completo (S2.1/S2.3/S2.4 en `f2cde85`; S2.2, S2.5–S2.9 en cierre Sprints 2-5) |
| 3 | [sprint-03-layout-pdl.md](./sprint-03-layout-pdl.md) | ✅ completo (layout v2 aplicado, Tab 3 "Por Subprueba" extendido) |
| 4 | [sprint-04-configurability.md](./sprint-04-configurability.md) | ✅ completo (configurableProps + formulario dinámico + color picker + tests vitest + docs) |
| 5 | [sprint-05-polish.md](./sprint-05-polish.md) | ✅ completo (microcopy + EmptyState + emojis/pattern_shape) |
| 6 | (futuro) Sprint 6 — Informe PDF WeasyPrint | 🔮 diferido |
| 7 | (próximo) Informes hardcodeados | 🚧 por arrancar — shortcut para cumplir entregas |

---

## Ramas de decisión (cronológico en la conversación)

### Rama 1 — Dashboard v1 (COMPLETADA ✅)

Plan original: construir `SubpruebaSelector` + `ImprovementRateByGroup` + layout 4 tabs para PDL.
- Se agregaron componentes Plotly nuevos
- Se creó layout 4-tab (Panorama / Por Curso / Por Subprueba / Síntesis)
- Mergeado a `dev`

Snapshot completo: [archive/dashboard-v1.md](./archive/dashboard-v1.md).

### Rama 2 — QA + fixes post-v1 (COMPLETADA ✅)

Bugs detectados en QA manual:
1. **PivotTable solo mostraba "NOMBRE | TOTAL"** — el layout usaba `columns:` pero el componente lee `cols:`. Fix en layout.
2. **Tab 2 PivotTable mostraba 196 rows (todos los cursos) en vez de 34 (solo curso activo)** — componente no respetaba `dataSource`. Fix: switch `dataSource: 'cursoEstudiantes'` en [dashboardRenderer.jsx](../frontend/src/tooling/dashboardRenderer.jsx).
3. **ImprovementRateByGroup "Sin datos para calcular transiciones"** — defaults apuntaban a `_rut` (campo inexistente) y `_nivel_de_riesgo` (campo real: `_logro`); entity key necesitaba composite `nombre||group`. Fix en [transition.jsx](../frontend/src/tooling/plotly-charts/transition.jsx).

Estado final: dashboard renderea todas las tabs, `71% mejoró 1° básico` valida contra PDF de referencia.

### Rama 3 — Crítica de analista + senior dev (COMPLETADA ✅)

Se generaron 3 informes por solicitud del usuario:

- **Informe 1 — Analista pedagógico:** problemas de mezcla de escalas entre subpruebas, KPIs sin accionabilidad, PivotTable sin valor, TrendLine ilegible, no responsivo en mobile.
- **Informe 2 — Desarrollador senior:** mover derived columns a capa de datos, flag `requiresSingleMetricContext`, eliminar charts legacy Recharts si no se usan, memoización.
- **Informe 3 — Esquema PDF:** diferido a Sprint 6 (WeasyPrint + matplotlib).

### Rama 4 — Radar de gaps (DISCUTIDA ✅)

Se propusieron 20 gaps adicionales; usuario dio feedback punto-por-punto:

**Adoptados:**
| # | Tema |
|---|---|
| 1 | RUT obligatorio — alumnos sin RUT se excluyen |
| 2 | Trayectorias incompletas: aparecen en tablas, se excluyen de charts de trayectoria |
| 3 | "Peor nivel" por estudiante en vistas cruzadas |
| 4 | Heatmaps solo Crítico+Alto |
| 5 | Paleta por indicador (no por layout) |
| 6 | Orden stacking guiado por `achievement_levels` |
| 8 | Limpiar filtros al cambiar tab |
| 9 | Botón Export PDF desde dashboard |
| 12 | Micro-copy interpretativo |
| 14 | Plotly Sankey para matriz de transición |
| 15 | Schema `configurableProps` configurable desde UI |
| 16 | Tests Chrome MCP E2E |

**Rechazados/diferidos:**
| # | Tema | Razón |
|---|---|---|
| 7 | Memoización backend-side | No prioritario hoy, queda como TODO |
| 10 | Snapshot/reproducibilidad | No necesario ahora |
| 11 | Vistas por rol (director/profesor) | Skip — todos ven lo mismo |
| 13 | Benchmarks IDEL | Aplica a indicadores tipo "Estudio"/"Alertas", no PDL |

### Rama 5 — PLAN ACTIVO — Dashboard v2

Sprints 1-5 definidos y aprobados. Archivo rector: este.
- Total: ~3.5 días efectivos con aceleración IA
- Modelos por tarea: Haiku (transforms simples, docs), Sonnet (código estándar), Opus (razonamiento complejo)

---

## TODO diferidos (tracked pero fuera del plan v2)

### Escalabilidad — pendientes de Sprints 2-5 (revisar tras informes hardcodeados)

1. **Quitar defaults hardcodeados de PDL en `dashboardRenderer.jsx`.**
   En `buildComponentProps` hay fallbacks cableados (`_curso`, `_rend`, `_logro`, `_habilidad`, `_evaluacion_num`) que asumen el schema del indicador PDL. Aplicar ese default en dominios distintos puede producir gráficos silenciosamente incorrectos (el campo existe con otro significado) o vacíos (el campo no existe y `filter`/`groupBy` devuelve sets vacíos). Plan tentativo: derivar defaults desde `indicator.column_roles` (el indicador ya declara qué columna juega cada rol), o subir el check al Editor de Layout y obligar a configurar `groupField`/`valueField`. Referencia: [frontend/src/tooling/dashboardRenderer.jsx](../frontend/src/tooling/dashboardRenderer.jsx) líneas con `?? '_curso'`, `?? '_rend'`, etc.

2. **RUT como clave: evaluar downgrade.**
   Sprint 1 introdujo `_rut` como clave primaria para dedup y derivaciones. Si un indicador no tiene dimensión RUT (o la tiene pero con nombre no detectable por `/\brut|run|documento\b/`), todos los records se descartan y el dashboard queda vacío. Alternativas: (a) fallback a clave `(_nombre, _curso)` cuando no hay RUT detectable; (b) detección por rol en `column_roles` en vez de nombre; (c) opt-out vía `indicator.dedup_strategy`. Referencia: [frontend/src/tooling/dataProcessing.js](../frontend/src/tooling/dataProcessing.js) — bloque `rutDimId` y filtro.

### Sprint siguiente — Informes hardcodeados (shortcut para cumplir entregas)

3. **Informes hardcodeados / personalizados** — ruta de atajo para plazos ajustados, consciente de que genera deuda. Propuesta: ejecutar scripts Python del backend llamándolos *por nombre*, sin plugin API genérica.
   - Organizar en `backend/reports/<tenant>/<report_id>.py` con una función canónica (`build(db, org_id, indicator_id, out_path) -> Path`).
   - Endpoint único `POST /api/indicators/{id}/run-report/{report_name}` que despacha al script por nombre, con allowlist declarada (evitar inyección).
   - Cada script puede tener hardcodes de columnas/plantillas específicas del cliente. Acompañar con comentario `# HARDCODED FOR {cliente} — revisar si {fecha}`.
   - Aislar todos los hardcodes dentro de esa carpeta para que la limpieza posterior sea un `grep` localizado.

### Fuera del plan v2 (preexistentes)

- Memoización backend-side / endpoint con cache
- Snapshot de datos (versionar `metric_data` por fecha)
- Role-based tab visibility
- Benchmarks IDEL externos (para Estudio/Alerta)
- **Sprint 6: Informe PDF** con matplotlib + WeasyPrint
- Telemetría de uso (`POST /api/telemetry`, eventos `tab_viewed`, `chart_interacted`)
- Evaluación de migración a ECharts

---

## Cómo retomar tras compactación

1. Leer este archivo completo.
2. Leer el sprint activo (ver "Sprint activo" arriba).
3. Ver `git log --oneline -20` para entender últimos commits.
4. Continuar desde la última tarea con estado ⏳ o ⏸.
5. El plan completo original está en `C:\Users\magod\.claude\plans\en-primer-lugar-quiero-foamy-whisper.md`.
