# Estado del proyecto — Report Generator

**Última actualización**: 2026-05-01
**Entrega comprometida**: lunes 2026-05-04
**Rama activa**: `dev` (sincronizada con `devtest` y `main` en commit anterior)

> Este documento es el punto de entrada rápido para entender en qué estamos. Para detalles ver `cambios_pendientes_carril_b.md`, `carril_b_evaluaciones.md`, `ROADMAP.md` y `DEPLOYMENT.md`.

---

## Contexto en una frase

Software para Fundación PHP que automatiza informes académicos (SIMCE, DIA, CV, IDEL, Fluidez Lectora). Backend FastAPI + Supabase ya en producción (Railway), frontend pendiente de deploy. La semana entrante el foco es la UX de los informes PDF.

---

## Estado de entornos

| Entorno | Backend | DB | Frontend | Estado |
|---|---|---|---|---|
| **Local (WSL)** | conda env `rgenerator`, port 8000 | Docker PG local | `npm run dev`, port 5173 | ✅ Operativo |
| **Staging (Render)** | rama `devtest` autodeploy | Render PG16 Oregon | — | ⏳ Sin frontend |
| **Producción (Railway)** | rama `main` autodeploy | Supabase PG17 sa-east-1 | — | ⏳ Sin frontend |

Detalles operacionales (variables de entorno, backups, rotación de credenciales) en [DEPLOYMENT.md](../../DEPLOYMENT.md).

---

## Datos cargados (snapshot 2026-04-29)

| Evaluación | Filas | Estado |
|---|---|---|
| SIMCE 2025 Lenguaje (estudiantes + preguntas) | 2510 | ✅ En Supabase |
| DIA 2025 (Lenguaje + Mat, estudiantes + preguntas) | 6032 | ✅ En Supabase |
| Cálculo Veloz 2025 | 5152 | ✅ En Supabase |
| IDEL 2025 | 2286 | ✅ En Supabase |
| Fluidez Lectora 2025 | 321 (de 424) | ❌ No cargada (eliminado el SQL hoy) |
| Pullinque "todos leemos" | ~542 alumnos | ⏸️ Sin decisión (formato wide) |
| DIA 2026 | 8 PDFs | 🚫 Procesamiento externo |

**Total cargado**: ~15.980 filas en `metric_data`.

---

## Top 10 pendientes priorizados

| # | Pendiente | Sprint | Esfuerzo |
|---|---|---|---|
| 1 | UX minimalista de PDFs (matplotlib+seaborn, sin portada/texto) | Sprint 1 (hoy/sáb) | Medio |
| 2 | Pulido visual paleta seaborn vs LaTeX | Sprint 2 (dom) | Bajo |
| 3 | Tests pytest para `RenderPDFReport` modo minimal | Sprint 2 (dom) | Bajo |
| 4 | Smoke test end-to-end con 3 evaluaciones distintas | Sprint 3 (lun) | Bajo |
| 5 | Deploy frontend en producción | Sprint 3 (lun) | Medio |
| 6 | Backup pre-entrega Supabase | Sprint 3 (lun) | Bajo |
| 7 | Sprint dashboards automáticos (planificación, no implementación) | Sprint 2 (dom) | Bajo (scoping) |
| 8 | Auditoría steps legacy `RenderReport` LaTeX (¿realmente rotos?) | Post-entrega | Medio |
| 9 | Suite de tests + CI GitHub Actions | Post-entrega | Alto |
| 10 | Rotar PAT de GitHub embebido en remote | Post-entrega | Bajo |

---

## Flujo de generación de PDFs (estado 2026-05-01)

Tres motores coexistiendo:

1. **`RenderReport` (LaTeX + xelatex)** — Legacy robusto, plantillas en `data/database/reports_templates/`, requiere binario externo. Estética validada por el usuario, sirve como **referencia visual**. **Se mantiene esta semana, no se toca.**

2. **`GenerateDocxReport` (docxtpl + docx2pdf)** — Funcional, usado en pipelines específicos. No es prioridad migrar.

3. **`RenderPDFReport` (WeasyPrint + matplotlib inline)** — Motor moderno, ya en producción, soporta branding dinámico, layouts en JSON con secciones tipadas (`cover`, `text`, `chart`, `table`, `page_break`). **Se va a extender** con un nuevo modo `minimal` que omite portada/texto y solo renderiza gráficos seleccionados con seaborn (paleta limpia, tipografía consistente, sin spines, grid tenue).

Endpoints clave:
- `POST /api/indicators/{id}/export-pdf` — genera PDF desde indicador
- `GET /api/indicators/export-pdf/engines` — lista motores disponibles

UI: [GenerateReportModal.jsx](../../frontend/src/components/GenerateReportModal.jsx) — se va a extender con tab "Layout minimalista" + multi-select de gráficos.

---

## Sprints de esta semana

| Sprint | Día | Foco |
|---|---|---|
| 0 | viernes 1-may | Cleanup git, docs, memoria — **completado al cierre del día** |
| 1 | viernes/sábado | PDF minimalista core (backend + frontend) |
| 2 | domingo | Pulido visual + tests + scope dashboards |
| 3 | lunes | Validación end-to-end + deploy + entrega |

Plan completo y reuso de código en `C:\Users\magod\.claude\plans\trabajaremos-en-la-branch-shimmering-barto.md`.

---

## Hallazgos importantes

- **PAT de GitHub en `git remote`**: el remote `origin` tiene un personal access token embebido en la URL. No bloquea hoy (auth funciona), pero hay que rotarlo después de la entrega y reconfigurar el remote sin el token.
- **`data/evaluaciones_bulk_load/` eliminado** (2026-05-01): contenía PII de estudiantes (RUTs, nombres). Data ya estaba en Supabase, se eliminó del disco. `.gitignore` actualizado para evitar reaparición.
- **Scripts personales eliminados** (2026-05-01): `_gen_dia_2025_sql.py`, `generate_cv_2025_sql.py`, `_inventario_evaluaciones.py`. Eran one-shot con paths Windows hardcoded; cumplido el propósito, eliminados.
- **Steps legacy posiblemente rotos**: `GenerateTables`, `GenerateGraphics`, `RenderReport` (LaTeX) no tienen tests. Estado real desconocido — auditar post-entrega.

---

## Decisiones pendientes (post-lunes)

- Pullinque "todos leemos" formato wide: ¿transformar a long ahora o esperar más data?
- Dimensiones nuevas (PIE, Género, Evaluadora, Nivel Riesgo, Categoría, Letra): ¿cuándo agregarlas?
- Estandarización léxica DIA Estudiante vs DIA Pregunta (snake_case vs Title Case).
- Validaciones automáticas en ETL (abortar si > 50% RUTs vacíos).
- Persistent Disk en Railway/Render para `data/org_assets/` (logos).
- Task Scheduler Windows para backups Supabase.

---

## Punteros a otros documentos

- [`ROADMAP.md`](../../ROADMAP.md) — backlog técnico completo + historial de versiones
- [`DEPLOYMENT.md`](../../DEPLOYMENT.md) — runbook Railway + Supabase
- [`CLAUDE.md`](../../CLAUDE.md) — guía de desarrollo para Claude Code
- [`cambios_pendientes_carril_b.md`](cambios_pendientes_carril_b.md) — recomendaciones de cambios al software detectadas en Carril B
- [`carril_b_evaluaciones.md`](carril_b_evaluaciones.md) — documento maestro del trabajo de carga 2025/2026
- [`referencia_informe/`](referencia_informe/) — código LaTeX legacy de referencia (DIA, SIMCE)
