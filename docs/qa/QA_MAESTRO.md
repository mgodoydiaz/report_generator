# QA Maestro — Recorrido completo del SaaS (dev3)

**Fecha**: 2026-07-22 · **Rama auditada**: `dev3` (= `dev2` + W2 pivotes) · **Método**: 5 agentes QA en paralelo (backend, frontend, motor de informes, pipelines/tests, UX usuario final)

Informes de detalle en [`docs/qa/hallazgos/`](./hallazgos/): [backend](./hallazgos/backend.md) · [frontend](./hallazgos/frontend.md) · [informes](./hallazgos/informes.md) · [pipelines_tests](./hallazgos/pipelines_tests.md) · [ux_usuario_final](./hallazgos/ux_usuario_final.md)

---

## Resumen ejecutivo

| Área | Hallazgos | Crítico | Alto | Estado general |
|---|---|---|---|---|
| Backend (111 rutas, 17 routers) | 8 | 0 | 2 | Sólido: sin fugas cross-org explotables, sin SQLi, sin eval inseguro |
| Frontend (17 páginas) | 12 | 1 | 4 | Funcional pero traga errores; descarga de artifacts rota |
| Motor de informes (6 caminos) | 9 | 2 | 3 | Fragmentado; **los filtros fallan en los 2 motores principales** |
| Pipelines + tests (703 tests) | — | 0 | — | Suite verde; huecos de cobertura en ejecución de pipelines y escritura a BD |
| UX usuario final (7 flujos) | — | 4 flujos bloqueados | — | **No demo-able sin acompañamiento** — confirma la intuición del dueño |

**Diagnóstico global**: la plataforma es técnicamente sana (seguridad y suite de tests en buen estado), pero (a) la generación de informes está fragmentada en 6 caminos con filtros rotos en los principales, y (b) un usuario final no técnico se bloquea en onboarding, errores opacos y estados vacíos engañosos.

---

## Prioridades consolidadas

### P0 — Roto de cara al usuario (arreglar ya, esfuerzo S)

| # | Hallazgo | Dónde | Fuente |
|---|---|---|---|
| P0-1 | Botón principal "Generar Reporte" (motor v1) ignora filtros multi-valor: `_build_records` compara string vs lista y falla silencioso | `report_steps.py` / motor v1 | informes H1 |
| P0-2 | Motor v2 DIA captura el filtro "Año" pero nunca lo aplica | `reports/dia/crear_informe.py` | informes H2 |
| P0-3 | Botón "Descargar" post-pipeline roto: `window.open()` sin JWT → 401 silencioso | `PipelineExecutionModal.jsx:101-103` | frontend C1 |
| P0-4 | Errores de pipeline aplastados a "Error interno del servidor" — propagar `str(e)` del step (ya es legible) | `pipelines.py:249-342` | ux #2 |
| P0-5 | `traceback.print_exc()` sin import → `NameError` enmascara errores de informes Word | `routers/reports.py` | backend H-01 |

### P1 — Riesgo o fricción importante (esfuerzo S-M)

- **org_id como defensa en profundidad**: `results.py`, `_build_records`, `reports/data.py` resuelven Metric/Dimension por id sin filtro org_id (hoy no explotable; falta test de regresión). (backend H-02, informes H6)
- **Páginas que tragan errores**: `Pipelines.jsx` no renderiza el error de carga; `Indicators.jsx` nunca dispara su `toast.error`. Falla de API ≈ "no hay datos". (frontend A2, A3)
- **5 archivos con cliente HTTP propio** (`Tables`, `Charts`, `MappingsManager`, `BulkOpsManager`, `ChartRenderer`) sin manejo de token expirado — unificar en `AuthContext.fetchAuth`. (frontend A4)
- **Estados vacíos engañosos** en `/execution`, `/results`, `Home`: distinguir "sin resultados de búsqueda" de "tu organización aún no tiene nada configurado". (ux #3)
- **ReDoS** en `POST /api/data-ops/replace` (regex de usuario sin timeout, backend single-worker) y **XSS por SVG** en upload de assets. (backend H-04, H-05)
- **`except: pass` en `SaveToMetric`** (`metric_steps.py:137-141`): pérdida silenciosa de datos al castear. (pipelines)
- **Errores `{"error":...}` con status 200** en `pipelines.py`/`specs.py`. (backend H-03)

### P2 — Estructural (iniciativas, esfuerzo L)

1. **Consolidación a motor único de informes** — arquitectura ya diseñada en [informes.md §4](./hallazgos/informes.md): loader único (filtrado `_matches` compartido con soporte multi-valor, org_id siempre) + renderer único pilotado por `esquema.json` declarativo por evaluación, motor v1 como fallback genérico, Word compartiendo loader. Incluye eliminar: `RenderHtmlReport`, `scripts/generate_report.py`, `/results-recharts`, esquemas legacy. Estimado 3-4 semanas.
2. **Cobertura de tests en lo que arriesga producción**: ejecución completa de `PipelineRunner` (0%), `SaveToMetric` (0%), `data_ops` replace/recalculate, `LoadConfigFromSpec`, steps Enrich*. (pipelines_tests §3)
3. **Camino a autoservicio del usuario final** — plan de 6 pasos en [ux_usuario_final.md §4](./hallazgos/ux_usuario_final.md): errores legibles, org piloto preconfigurada, estados vacíos, botón único de descarga, ayuda real para usuario final, invitación por correo.

---

## Decisiones de arquitectura tomadas (sesión 2026-07-22)

1. **Motor único de informes**: se adopta la propuesta de informes.md §4 (loader + renderer parametrizados por esquema). Secuencia: quick wins de filtros primero (P0-1, P0-2), consolidación mayor como iniciativa separada.
2. **Formato estándar de tests**: clases `TestXxx` con docstring de comportamiento + fixtures compartidas en `conftest.py` + markers obligatorios (`slow`, `db`, `integration`). Convención detallada y test modelo en [pipelines_tests.md](./hallazgos/pipelines_tests.md). Los tests existentes NO se reescriben en masa; los nuevos siguen la convención.
3. **Batería QA dual**: pytest automatizado (`tests/`) + guiones manuales ejecutables por agentes o humanos en `docs/qa/manual/` (formato paso/esperado/resultado).
4. **Agente de chat para indicadores**: backend con proveedor LLM intercambiable por env var (`LLM_PROVIDER=mock|anthropic`), modo mock por defecto, operativo al setear `ANTHROPIC_API_KEY`.

## Estado de ejecución

- [x] Recorrido QA (5 informes en `hallazgos/`)
- [ ] Batería de pruebas P0/P1 + guiones manuales
- [ ] Quick wins P0 (5 fixes S)
- [ ] Consolidación motor único (iniciativa L — diseño aprobado, pendiente ejecución)
- [ ] Agente de chat de indicadores

**Regla vigente**: NO merge a `main` sin confirmación explícita de Miguel.
