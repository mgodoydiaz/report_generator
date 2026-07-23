# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Contexto de arranque (leer siempre primero)

**Report Generator** — software para Fundación PHP que automatiza la generación de informes académicos (SIMCE y otras evaluaciones) mediante una UI web respaldada por un pipeline ETL + generación de reportes.

- **Repo en GitHub**: `mgodoydiaz/report_generator`
- **Carpeta local (Windows)**: `C:\Users\magod\Documents\Proyectos\Informes PHP\website-ui` (el rename local a `report-generator` está pendiente)
- **Dueño / desarrollador único**: Miguel Godoy
- **Idioma de trabajo**: español (commits, issues, conversación)

### Ramas

| Rama | Rol |
|---|---|
| `main` | Producción. Railway auto-deploya esta rama. Mergear `dev` → `main` para promover. |
| `dev` | Rama activa de desarrollo. Trabajar aquí por defecto. |

### Entornos

| Entorno | Backend | DB | Frontend |
|---|---|---|---|
| **Local (WSL)** | `python backend/api.py` en conda env `rgenerator` | Docker PostgreSQL (`report_generator-db-1`) | `npm run dev` en `frontend/` |
| **Producción** | Railway us-east4 (Docker, rama `main`) — `api.rgenerator.mgodoy.dev` | Supabase PG17 `us-east-1` (N. Virginia) — proyecto `rgenerator-us` | Railway, dominio `rgenerator.mgodoy.dev` |

Detalle vivo del deploy en `DEPLOYMENT.md` y `memory/project_deploy_status.md`.

---

## Stack

- **Frontend**: React 18 + Vite, Tailwind CSS 4, react-router-dom
- **Backend**: FastAPI + Uvicorn (`backend/api.py`), SQLAlchemy ORM, Alembic para migraciones
- **Auth**: JWT con `python-jose` + bcrypt, multi-tenancy por `org_id`
- **Base de datos**: PostgreSQL (16 local en Docker, 17 en cloud Supabase)
- **ETL library**: paquete `rgenerator` (`backend/rgenerator/`) instalado en modo editable
- **Generación de PDFs**: LaTeX/MikTeX + docxtpl (pendiente migrar a algo más liviano — ver ROADMAP)
- **Procesamiento**: pandas, camelot-py, PyMuPDF, matplotlib

---

## Running the Application

**Windows (atajo):**
```bash
run_software.bat  # abre backend + frontend en dos terminales
```

**Backend (WSL o Windows)** — puerto 8000:
```bash
conda activate rgenerator
python backend/api.py
```

**Frontend** — puerto 5173:
```bash
cd frontend
npm run dev
```

**Variables de entorno clave** (ver `.env.example` si existe, o `memory/project_deploy_status.md`):
- `DATABASE_URL` (backend lee esto para conectar a PG)
- `JWT_SECRET`
- `VITE_API_BASE_URL` (frontend — se resuelve según `.env.{development,staging,production}`)

---

## Tests y scripts

Ver **[TESTING.md](./TESTING.md)** para el plan completo, capas (unit/integration/E2E),
fixtures (`db_session`, `client`, `client_auth`) y convenciones.

```bash
# Toda la suite (sin lentos)
pytest -q -m "not slow"

# Solo unit (rápido, ideal pre-commit)
pytest -q -m unit

# Solo integration (con DB SQLite in-memory + TestClient FastAPI)
pytest -q -m integration

# Coverage de backend
pytest --cov=backend --cov-report=term-missing

# Archivo específico
pytest tests/steps/test_derived_fields_engine.py -v

# Reintentar lo que falló la última vez
pytest --lf

# ETL desde CLI
python scripts/run_etl.py ./config/simce_estudiantes_lenguaje.txt

# Generar PDF
python scripts/generate_report.py --schema <schema.json> --data <data.csv> --tipo <type> --output <output.pdf>

# Export/import DB (para seed inicial en Supabase o backup)
python scripts/db_seed.py export --output db_seed.json
python scripts/db_seed.py import --input db_seed.json --clear

# Migraciones
alembic upgrade head
alembic revision --autogenerate -m "mensaje"
```

---

## Instalación

```bash
conda env create -f environment.yml
conda activate rgenerator
pip install -e .              # instala el paquete rgenerator en editable

cd frontend && npm install
```

---

## Arquitectura

### Ruta de import canónica del paquete ETL

El paquete `backend/rgenerator/` se importa SIEMPRE como **`backend.rgenerator.*`** (imports relativos dentro del paquete). La ruta corta `rgenerator.*` está bloqueada con ImportError en el `__init__` — creaba una segunda instancia de cada módulo y `isinstance`/`except` entre clases de rutas distintas fallaba silenciosamente. Guardia: `tests/regresion/test_import_canonico.py`.

### Backend (`backend/`)

```
backend/
├── api.py                  FastAPI app, CORS, monta 9 routers
├── auth.py                 JWT + bcrypt, get_current_user dependency
├── cli.py                  Comandos administrativos (bootstrap, crear superadmin, etc.)
├── config.py               Paths centralizados (DATA_DIR, REPORTS_TEMPLATES_DIR, etc.)
├── database.py             engine, SessionLocal, Base, get_db, init_db
├── models.py               Modelos SQLAlchemy — TODAS las tablas con org_id
├── schemas/                Esquemas JSON de informes (plantillas de dominio)
├── routers/
│   ├── auth.py             /api/auth (login, refresh, me)
│   ├── users.py            /api/users (CRUD, solo admin)
│   ├── superadmin.py       /api/superadmin (panel cross-org)
│   ├── pipelines.py        /api/pipelines — CRUD + ejecución + uploads
│   ├── specs.py            /api/specs — plantillas de configuración
│   ├── dimensions.py       /api/dimensions — catálogo de dimensiones
│   ├── metrics.py          /api/metrics — métricas + import/export + metric_data
│   ├── indicators.py       /api/indicators — indicadores con dashboard_layout
│   └── results.py          /api/results — consultas agregadas para dashboards
└── rgenerator/
    ├── core/
    │   ├── context.py           RunContext (inputs, artifacts, outputs, status, db, org_id)
    │   ├── step.py              Step base + WaitingForInputException
    │   ├── pipeline_steps.py    Re-exports de los módulos especializados
    │   ├── init_steps.py        InitRun, LoadConfigFromSpec (usa ctx.db)
    │   ├── io_steps.py          DiscoverInputs, RequestUserFiles, ExportConsolidatedExcel, DeleteTempFiles
    │   ├── etl_steps.py         RunExcelETL, EnrichWithUserInput, EnrichWithContext, ModifyColumnValues
    │   ├── report_steps.py      GenerateGraphics, GenerateTables, RenderReport, GenerateDocxReport
    │   └── metric_steps.py      SaveToMetric, LoadMetricToDF (usan ctx.db)
    └── tooling/
        ├── pipeline_tools.py    PipelineRunner (recibe db + org_id), STEP_MAPPING, load_pipeline_config
        ├── config_tools.py
        ├── data_tools.py
        ├── plot_tools.py
        ├── report_tools.py
        └── report_docx_tools.py
```

### Modelo de ejecución de pipelines

Los pipelines se guardan como filas en la tabla `pipelines` (columna `config_json` contiene el JSON completo). El JSON tiene `workflow_metadata`, `context` y un array `pipeline` de `{step, params}`.

`PipelineRunner` (`tooling/pipeline_tools.py`):
1. Recibe `db: Session` y `org_id: int` al construirse
2. Los inyecta en `RunContext` para que cualquier step pueda hacer queries multi-tenant
3. Mapea nombres de step → clases vía `STEP_MAPPING`
4. Ejecuta secuencialmente pasando el mismo `RunContext`

**Pausa interactiva**: un step puede lanzar `WaitingForInputException` para pedir archivos o datos al usuario. El router responde con status `NEEDS_REVIEW`, el frontend lo muestra, y al completarse se reanuda.

**`RunContext` (`core/context.py`) — campos clave:**
- `db: Session` — sesión SQLAlchemy para queries dentro de steps
- `org_id: int` — filtro multi-tenant obligatorio en queries
- `inputs: Dict[str, List[Path]]` — archivos de entrada por rol (`estudiantes`, `preguntas`, etc.)
- `artifacts: Dict[str, Any]` — DataFrames/objetos intermedios entre steps
- `outputs: Dict[str, Path]` — paths de outputs finales
- `status: NEW | RUNNING | NEEDS_REVIEW | DONE | FAILED`
- `last_artifact_key` — clave del último artifact producido

### Frontend (`frontend/src/`)

```
src/
├── App.jsx             Router (7 páginas activas + 2 placeholders)
├── constants.js        API_BASE_URL (desde VITE_API_BASE_URL), STEP_OPTIONS, STEP_TRANSLATIONS, STEP_DEFAULT_PARAMS
├── pages/              Home, Pipelines, Specs, Dimensions, Values, Metrics, Execution
├── components/
│   ├── Layout, Sidebar, modales y drawers
│   ├── PipelineExecutionModal  — ejecución multi-paso con pausas
│   └── pipeline-steps/         — renderers de UI por tipo de step
└── tooling/
    ├── plotly-charts/  Componentes Plotly (nuevos) — dashboardRenderer los registra
    ├── charts/         Componentes Recharts (legacy, solo mantener)
    └── dashboardRenderer.jsx
```

### Layout de datos (filesystem)

PostgreSQL es la base de datos. El filesystem solo guarda **archivos**, no datos de negocio:

```
data/
├── database/          LEGACY — Excel files que fueron migrados a PG. Se mantienen como seed de referencia
│   └── reports_templates/  plantillas Word/LaTeX (sí se usan en tiempo de ejecución)
├── input/             archivos brutos de entrada
├── output/            reportes generados
├── pipeline_runs/     artifacts por ejecución (uploads/, tmp/)
└── tmp/               trabajo temporal
```

En Railway, `data/pipeline_runs/` y `data/output/` viven en un Volume montado al contenedor. Las ejecuciones largas persisten entre redeploys.

### Config del dominio (no DB)

- `config/*.txt` — mapeos de columnas, header rows, enrichment para ETL específicos de cada evaluación
- `data/database/reports_templates/` — plantillas de gráficos y tablas para `GenerateGraphics`/`GenerateTables`

---

## Deploy a Producción

- **Backend**: Railway us-east4, sigue `main`. Auto-deploya en push. Dockerfile multi-stage target `prod`.
- **DB**: Supabase PG17 `us-east-1` (proyecto `rgenerator-us`). Conexión via `DATABASE_URL` configurada en Railway → Variables. Migrada desde `sa-east-1` el 2026-05-19 para colocar DB y backend en la misma región (RTT 150 ms → 10 ms).
- **Seed inicial / migraciones de specs**: correr `scripts/_oneshot/_seed_dashboards_v2.py` y `scripts/db_seed.py` desde el contenedor de prod o desde local apuntando al `DATABASE_URL` externo.
- **Variables de entorno**: ver `DEPLOYMENT.md` para la lista completa. Copia local de referencia en `.env.railway` (gitignored).

Runbook completo en **[DEPLOYMENT.md](./DEPLOYMENT.md)** y estado vivo en `memory/project_deploy_status.md`.

---

## Glosario de dominio

### Siglas IDEL (PDL IDEL-Woodcock)

El indicador IDEL maneja 6 subpruebas. En la base de datos se almacenan como **siglas** (raw values) — los nombres largos solo se muestran en UI y reportes. Confirmado con la fundación 2026-05-06:

| Sigla | Nombre oficial |
|---|---|
| CT  | Comprensión de Textos |
| FLO | Fluidez en la Lectura Oral |
| FNL | Fluidez en Nombrar Letras |
| FSF | Fluidez en Segmentación de Fonemas |
| ILP | Identificación de Letras y Palabras |
| VSD | Vocabulario Sobre Dibujos |

**No confundir** (errores históricos a evitar):
- FNL ≠ "Segmentación Fonémica" — esa es FSF.
- FLO ≠ "Fluidez Lectora" a secas — la oficial incluye "Oral".
- VSD: "Dibujos" en plural y "Sobre" con S mayúscula en estilo informe.

**Fuentes de verdad** (mantener sincronizadas si se cambia algo):
- `frontend/src/tooling/idelLabels.js` (export `IDEL_SUBPRUEBA_LABELS`)
- `scripts/_oneshot/dashboards_v2/helpers.py` (const `IDEL_SUBPRUEBA_ALIASES`, formato "SIGLA · Nombre")
- `scripts/report_pdl_idel.py` (dict de mapping en cabecera)

### Niveles de riesgo IDEL

4 niveles ordinales (peor → mejor) con colores oficiales en `Indicator.achievement_levels`:

| Nivel | Color hex |
|---|---|
| Crítico | #dc2626 |
| Alto Riesgo | #ea580c |
| Cierto Riesgo | #eab308 |
| Bajo Riesgo | #22c55e |

Los gráficos del dashboard heredan estos colores via `aesthetics.color_overrides` (no via paleta), lo que garantiza consistencia con la página de Indicadores. El usuario puede ajustar por chart desde `/charts` → tab Estética.

### Versiones IDEL

Cada año tiene 3 versiones (`v1`, `v2`, `v3`) excepto **5° y 6° BÁSICO que no rinden v3** (protocolo). El dashboard tiene una nota explicativa en el tab Tendencia. La columna `Versión` se almacena como string ordinal (no numérico).

---

## Skills de administración

Tareas recurrentes documentadas en **[.agents/workflows/](./.agents/workflows/)**:

- `/add-step` — Crear o modificar un paso de pipeline
- `/add-metric` — Crear una nueva métrica (API REST o SQLAlchemy)
- `/new-pipeline` — Construir un nuevo pipeline JSON desde cero
- `/add-chart` — Agregar un gráfico o tabla al sistema de dashboards

## Roadmap

Pendientes, deuda técnica y mejoras planificadas en **[ROADMAP.md](./ROADMAP.md)**.
