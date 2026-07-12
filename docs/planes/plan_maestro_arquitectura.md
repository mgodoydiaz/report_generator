# Plan Maestro de Arquitectura — Report Generator

Fecha: 2026-07-11 · Rol: arquitectura senior · Rama: `feature/reportes-word-indicadores`
Supersede a: `plan_tablas_graficos_modulares.md` (absorbido como W3/W4) y
complementa `recorrido_agentes_2026-07-11.md` (hallazgos de base).

---

## 1. Visión del producto

Funciones núcleo (hoy):
1. **ETL** — pipelines de carga y transformación de evaluaciones.
2. **Base de datos** — métricas/dimensiones multi-tenant (PostgreSQL).
3. **Dashboards** — visualización interactiva por indicador.
4. **Generación de informes** — PDF (WeasyPrint v2) y Word (docxtpl, nuevo).

Próximas capacidades (esta hoja de ruta):
5. **Multi-pivote para informes** — pivotes configurables y reutilizables entre dashboard e informes.
6. **Agentes IA en el producto** — chat que crea/edita configuración (pipelines, specs, dashboards, informes) dentro del software.
7. **Acceso inclusivo móvil** — smartphones y tablets como ciudadanos de primera clase.
8. **Alimentación por API externa segura** — ingesta de datos desde sistemas de terceros sin pasar por la UI.

### Principios de arquitectura

- **Una spec, N renderers**: toda tabla/gráfico se declara una vez (`ChartConfig`/`TableConfig`) y se renderiza en Plotly (web), matplotlib (PDF/Word) o export (xlsx). Nunca duplicar lógica de visualización.
- **La API es el producto**: la UI, los agentes IA y la ingesta externa consumen la MISMA API REST. Si el agente no puede hacerlo por API, la API está incompleta.
- **Multi-tenant primero**: `org_id` en cada query, cada API key, cada acción de agente.
- **Todo cambio de configuración es auditable y reversible** (prerequisito duro para dejar que un agente IA escriba configuración).

---

## 2. Workstreams

### W0 — Hardening de seguridad y operación (PRIMERO, bloquea todo lo demás)

La ingesta externa y los agentes IA multiplican la superficie de ataque; no se
construyen sobre las vulnerabilidades ya detectadas.

| # | Acción | Referencia |
|---|---|---|
| 0.1 | Sanitizar uploads (path traversal): `Path(name).name` + lista blanca de `input_key` | `routers/pipelines.py:140,147` |
| 0.2 | Reemplazar `eval()` por `simpleeval` en condiciones/expresiones de ETL | `tooling/etl_tools.py:193-208` |
| 0.3 | Refrescar `runner.ctx.db = db` por request (sesión obsoleta en `ACTIVE_RUNNERS`) | `routers/pipelines.py:183+` |
| 0.4 | `JWT_SECRET` obligatorio en arranque; CORS por env var con orígenes explícitos | `auth.py:23`, `api.py:19` |
| 0.5 | Rate limiting en `/api/auth/login` (slowapi) + límite de tamaño de uploads | `routers/auth.py:41` |
| 0.6 | Logging estructurado (reemplazar ~58 prints); errores con código HTTP correcto (no `{"error": ...}` con 200) | global |
| 0.7 | Invalidar cache de DataFrames en TODOS los writers de `MetricData` | `routers/tables.py:118` |

**QA**: tests automatizados de tenancy negativo (org A → recursos org B = 403/404),
tests de path traversal con nombres maliciosos, test de arranque sin JWT_SECRET.
Manual: intento de login por fuerza bruta y upload de `../../etc/x` desde la UI.

**Esfuerzo**: 2-3 sesiones. **Sin dependencias.**

---

### W1 — Ingesta por API externa segura

Objetivo: que un sistema tercero (plataforma de la fundación, Google Forms,
otro colegio) alimente `MetricData` sin tocar la UI ni los pipelines manuales.

**Diseño:**
1. **API keys por organización** — tabla `api_keys` (`org_id`, `key_hash` bcrypt,
   `scopes`, `expires_at`, `last_used_at`, `revoked`). Nunca se almacena la key
   en claro; se muestra una sola vez al crearla. UI de gestión en /settings
   (solo admin). Header `X-API-Key`, resolución → `org_id` igual que el JWT.
2. **Endpoints de ingesta** (`backend/routers/ingest.py`, prefijo `/api/ingest`):
   - `POST /api/ingest/metrics/{metric_id}/data` — batch de records JSON
     validados contra `meta_json.fields` y dimensiones de la métrica.
   - `POST /api/ingest/pipelines/{pipeline_id}/trigger` — dispara un pipeline
     con archivos adjuntos (multipart), reutilizando el flujo de uploads YA
     saneado en W0.
   - `GET /api/ingest/status/{job_id}` — estado de la ingesta.
3. **Garantías**: idempotencia por `Idempotency-Key` (reintentos seguros),
   límite de tamaño/rate por key, validación estricta con Pydantic (rechazo
   con detalle de filas inválidas, opción `dry_run=true`), invalidación de
   cache (W0.7) y registro en tabla `ingest_log` para auditoría.
4. **Scopes**: `ingest:write`, `metrics:read` — una key de solo-ingesta no
   puede leer datos de otras métricas.

**QA automatizada**: suite `tests/routers/test_ingest.py` — key inválida/revocada/
expirada, cross-org, payload malformado, idempotencia (2 POST = 1 inserción),
dry-run. **Manual**: ingesta real desde `curl`/Postman contra staging con una
key de prueba, verificar que el dashboard refleja los datos.

**Esfuerzo**: 2-3 sesiones. **Depende de**: W0 (0.1, 0.5, 0.6, 0.7).

---

### W2 — Motor de pivotes (base del multi-pivote)

Objetivo: un motor de pivote único, server-side, parametrizable y reutilizable,
que hoy está fragmentado (PivotTable Plotly en frontend, `_table_section` en
PDF v1, groupbys ad-hoc en cada `tables.py`).

**Diseño:**
1. **`backend/rgenerator/core/pivot_engine.py`**: función pura
   `pivot(df, spec) -> DataFrame` con spec declarativa:
   ```json
   {"rows": ["Curso"], "cols": ["Mes"], "values": [{"field": "Logro", "agg": "mean"}],
    "totals": {"rows": true, "cols": true}, "format": {"Logro": ".1%"},
    "order": {"Mes": ["Marzo", "Abril", "..."]}}
   ```
   Implementación sobre `pandas.pivot_table` + post-formato. Soporta múltiples
   `values` (multi-métrica) y múltiples niveles en rows/cols (multi-pivote).
2. **`PivotConfig`** como tipo de `TableConfig` (schemas_table): las tablas
   configuradas en /tables pueden ser pivotes; el endpoint `/api/tables/{id}/data`
   delega en el motor.
3. **Consumidores**: dashboard (`PivotTable` Plotly recibe el resultado ya
   pivoteado — se adelgaza el JS), informes PDF v2 (nueva fn en `TABLE_REGISTRY`
   que recibe un `pivot_spec`), informes Word (`tabla_desde_df(pivot(...))`),
   export xlsx.

**Multi-pivote para informes** = una sección de informe declara una LISTA de
pivot_specs (ej: mismo pivote iterado por curso, o 3 pivotes con distinta
agrupación en una página). El runtime v2 ya itera secciones dinámicas; solo se
añade el tipo de sección `pivot`.

**QA automatizada**: tests unitarios del motor (totales, NaN, orden custom,
multi-values, df vacío) + snapshot tests de los DataFrames resultantes.
**Manual**: comparar 2-3 pivotes contra los Excel históricos de la fundación
(mismos números) — usar la skill `/quality-review` sobre el PDF resultante.

**Esfuerzo**: 2 sesiones motor + 1 por consumidor. **Depende de**: nada (paralelo a W1).

---

### W3 — Spec única de tablas/gráficos (refactor modular Python + JS)

Actualización del plan F0-F4 anterior, ahora al servicio del multi-pivote (W2)
y de los agentes IA (W5): **si toda visualización es una spec declarativa, un
agente puede escribirla**.

1. **F0 Consolidación Python**: `reports/charts.py`/`tables.py` como única
   fuente; borrar duplicados (`tooling/plot_tools.py`, `tooling/report_tools.py`,
   `report_docx_tools.py`); unificar `_to_field_name` y paletas (`reports/theme.py`).
2. **F1 Contrato**: adapter `ChartConfig → CHART_REGISTRY` (matplotlib) y campo
   `matplotlib_fn` en `CHART_TYPE_META` junto a `plotly_component`. Un Spec de
   /charts se renderiza idéntico en web, PDF y Word.
3. **F2 Motor v1 sobre el registry**: eliminar el switch `_chart_to_png_b64`
   (report_steps.py:290) delegando en el adapter.
4. **F3 Frontend**: matar Recharts (migrar `SIMCE_PRESET_LAYOUT`, `Help.jsx`,
   layouts en DB) → borrar `recharts`; partir `dashboardRenderer.jsx`;
   **cliente API único** `src/api/client.js` sobre `fetchAuth` (prerequisito
   del rediseño móvil W6 y del chat W5).
5. **F4 Contrato generado**: `GET /api/reports/charts` genera el JSON de
   componentes que el frontend valida en build.

**QA automatizada**: tests de paridad (misma spec → mismos números en dataset
Plotly y en el DataFrame matplotlib), regresión visual de PNGs por hash
perceptual en los informes de referencia. **Manual**: `/quality-review` de un
informe SIMCE y uno DIA antes/después de cada fase.

**Esfuerzo**: 4-6 sesiones. **Depende de**: nada; F3.4 (cliente API) conviene ANTES de W6.

---

### W4 — Convergencia de informes (PDF v2 + Word + multi-pivote)

1. Registrar tipos de informe PDF v2 por descubrimiento (igual que Word):
   eliminar el dispatch hardcodeado `if tipo == "simce"...` de
   `routers/reports.py` → registry `{tipo: módulo}` autodescubierto de
   `reports/<tipo>/`. Un informe nuevo = carpeta nueva, cero cambios al router.
2. Sección `pivot` en esquemas v2 y en contextos Word (consume W2).
3. Informes Word específicos por indicador (IDEL, CV, FL) con el scaffold
   `scripts/nuevo_informe_word.py` — la fundación edita la plantilla en Word.
4. (Opcional) PDF server-side desde Word vía LibreOffice headless en el
   contenedor Railway (`soffice --convert-to pdf`), como flag `?formato=pdf`.

**QA**: los 15 tests Word existentes + tests por informe nuevo (placeholders
completos, render sin `{{` residuales). Manual: revisión de un .docx real por
la fundación (fidelidad de marca) antes de cada entrega.

**Esfuerzo**: 1-2 sesiones + 0.5 por informe. **Depende de**: W2 (para pivotes en informes).

---### W5 — Agentes IA en el producto (configuración por chat)

Objetivo: un chat dentro del software donde el usuario pide "créame un dashboard
de Cálculo Veloz con tendencia mensual" o "configura un pipeline para este Excel"
y el agente escribe la configuración real.

**Arquitectura (3 capas):**
1. **Capa de herramientas** — el agente NO toca la DB: usa la API REST existente
   con el JWT del usuario (mismos permisos, mismo org_id, misma auditoría).
   Definir el catálogo de tools sobre endpoints ya existentes:
   `crear_spec_chart`, `crear_spec_table`, `editar_dashboard_layout`,
   `crear_pipeline`, `listar_metricas`, `previsualizar_chart` (dry-run).
   Esto es la prueba ácida del principio "la API es el producto".
2. **Capa de agente** — servicio backend `backend/agent/` con Claude API
   (`claude-sonnet-5` por costo/latencia; escalar a modelos superiores solo si
   la calidad lo exige). Tool use en loop con streaming SSE al frontend.
   System prompt con el glosario de dominio (siglas IDEL, niveles, versiones)
   extraído de CLAUDE.md a un `domain_context.md` versionado.
3. **Capa de seguridad/UX**:
   - **Draft-first**: toda escritura del agente crea un BORRADOR que el usuario
     aprueba en la UI (diff visual del layout/spec) antes de persistir.
   - Tabla `agent_actions` (org_id, user_id, tool, payload, estado, timestamp)
     — auditoría completa y botón "deshacer".
   - Rate limit por org; sin acceso a endpoints de usuarios/superadmin.
   - API key de Anthropic en server, nunca en cliente.

**Fases**: (a) chat de solo-lectura que responde preguntas sobre los datos y
explica configuraciones (bajo riesgo, valor inmediato); (b) creación de specs
de charts/tables con draft-first; (c) dashboards completos y pipelines.

**QA automatizada**: suite de evals con casos reales en español ("crea un
gráfico de barras de logro por curso para SIMCE") verificando el JSON resultante
contra schema Pydantic + golden files; tests de que el agente NUNCA puede
ejecutar tools fuera de su org (inyectar org ajeno en el prompt y verificar 403).
**Manual**: sesión de red-teaming de prompts (pedirle borrar datos, cambiar
usuarios, leer otra org) documentada en `docs/reportes/`.

**Esfuerzo**: 4-6 sesiones. **Depende de**: W0 (duro), W3-F3.4 (cliente API), idealmente W2/W3 (specs = lenguaje del agente).

---

### W6 — Acceso inclusivo móvil (smartphones y tablets)

1. **Auditoría responsive** con el browser embebido (viewport 375px y 768px)
   página por página; registrar hallazgos en `docs/reportes/audit_movil.md`.
2. **Layout**: Sidebar → drawer colapsable + bottom-nav en móvil; tablas con
   scroll horizontal contenido o vista de tarjetas; modales full-screen en
   móvil (los actuales `max-w-lg` centrados funcionan mal en teclado móvil);
   targets táctiles ≥44px.
3. **Dashboards**: Plotly con `responsive: true` y config móvil (menos
   modebar); KPIs apilados; filtros multi-select como bottom-sheet.
4. **PWA ligera**: manifest + iconos para "instalar" en el teléfono de los
   directores (sin offline complejo en esta fase).
5. **Accesibilidad** (deuda detectada: solo 3 atributos ARIA en todo src/):
   `aria-label` en botones-icono, `role="dialog"` + focus trap en modales,
   contraste AA. Beneficia a móvil y a escritorio.

**QA automatizada**: Playwright con proyectos `mobile-chrome` (Pixel 5) y
`tablet` (iPad) para los flujos críticos: login → seleccionar indicador →
filtrar → descargar informe. **Manual**: prueba real en tu teléfono vía la URL
de staging + checklist de 10 puntos (zoom, teclado, rotación, descarga de .docx).

**Esfuerzo**: 3-4 sesiones. **Depende de**: W3-F3 (cliente API y componentes partidos facilitan el retrofit).

---

## 3. Estrategia de QA transversal

**Pirámide automatizada** (hoy: 529 tests, gate `pytest -q -m "not slow"`):
- *Unit*: motores puros (pivot_engine, derived_fields, engine Word, adapters).
- *Integration*: routers con SQLite in-memory + TestClient (patrón existente).
  Añadir: tenancy negativo sistemático, ingest, agent tools.
- *E2E*: Playwright (nuevo, W6) — 4-5 flujos críticos, desktop + móvil, corre
  en CI antes de merge a `main`.
- *Regresión visual*: hash de PNGs de informes de referencia (W3) +
  `/quality-review` para inspección asistida de PDFs.
- *Evals de agente*: golden files de configuraciones generadas (W5).

**Gates manuales** (checklist por release, en `docs/reportes/`):
1. Informe PDF y Word de un indicador real → revisión visual (marca, números
   contra Excel fuente).
2. Flujo móvil completo en dispositivo físico.
3. Red-team básico del agente IA (cuando exista).
4. Smoke en producción post-deploy (login, dashboard, descarga).

**Regla de oro**: ningún workstream se declara terminado sin (a) sus tests
automatizados en verde en la suite, (b) su gate manual documentado.

---

## 4. Agentes recomendados por paso (desarrollo con Claude Code)

| Workstream | Agentes/skills recomendados | Uso |
|---|---|---|
| W0 Hardening | `Explore` (localizar todos los call-sites), `/security-review` antes del merge, `/code-review` alto | Cambios de seguridad exigen revisión adversarial, no solo tests |
| W1 Ingesta API | `Plan` (diseño de contrato/scopes), `general-purpose` (implementación), `/code-review` + `/verify` con curl real | El contrato público conviene planificarlo antes de codificar |
| W2 Pivotes | `general-purpose` (motor + tests unit), `/quality-review` sobre PDFs con pivotes | Motor puro = TDD directo |
| W3 Refactor specs | `Explore` very thorough (mapa de consumidores antes de borrar), `general-purpose` por fase, `/simplify` al final de F0, `/code-review ultra` al cerrar el workstream | El riesgo es romper consumidores no mapeados |
| W4 Informes | `general-purpose`, skill `docx` (plantillas Word), `/quality-review` por informe nuevo | — |
| W5 Agentes IA | `claude-code-guide` + skill `claude-api` (diseño tool use/streaming), `Plan` (arquitectura draft-first), `general-purpose` (evals) | No adivinar la API de Anthropic: consultar la skill |
| W6 Móvil | Browser embebido (viewports 375/768) para auditar y verificar, `general-purpose` (Playwright), `/verify` en cada página | Verificación visual obligatoria, no solo build verde |

Patrón general por paso: **Explore → Plan → implementar → `/verify` → `/code-review` → gate manual**. Para trabajos paralelos independientes (ej. W1 y W2), usar worktrees separados.

---

## 5. Secuenciación propuesta

```
Sprint 1  W0 completo (hardening)                        ← bloquea W1 y W5
Sprint 2  W1 (ingesta API)        ∥  W3-F0/F2 (consolidación Python)
Sprint 3  W2 (motor pivotes)      ∥  W3-F1 (adapter spec)
Sprint 4  W4 (informes + multi-pivote) ∥ W3-F3 (frontend, cliente API)
Sprint 5  W6 (móvil)              — usa cliente API y componentes de F3
Sprint 6+ W5 (agentes IA) fase a→b→c — llega con specs unificadas y API endurecida
```

Justificación del orden: seguridad primero (W0); la ingesta (W1) da valor
externo temprano; pivotes y specs (W2/W3) son la fundación técnica que hace
baratos los informes (W4), el móvil (W6) y sobre todo los agentes (W5) — un
agente que escribe UNA spec declarativa bien validada es un proyecto pequeño;
un agente que debe conocer 5 formatos de spec es inviable.
