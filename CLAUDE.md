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
| `main` | Producción. Se promociona desde `devtest` una vez validado en staging |
| `dev` | Rama activa de desarrollo. Trabajar aquí por defecto |
| `devtest` | **Staging**. Render auto-deploya esta rama en `rgenerator-staging`. Mergear `dev` → `devtest` para disparar un deploy |

### Entornos

| Entorno | Backend | DB | Frontend |
|---|---|---|---|
| **Local (WSL)** | `python backend/api.py` en conda env `rgenerator` | Docker PostgreSQL (`report_generator-db-1`) | `npm run dev` en `frontend/` |
| **Staging (Render)** | `rgenerator-staging.onrender.com` (Docker, rama `devtest`) | `rgenerator-staging-db` PG16 Oregon (Free) | Static Site en Render con `.env.staging` |
| **Producción** | Pendiente — rama `main`, en Render | Probable **Neon** (São Paulo) por latencia desde Chile | Pendiente |

Detalle vivo del deploy en `memory/project_deploy_status.md`.

---

## Stack

- **Frontend**: React 18 + Vite, Tailwind CSS 4, react-router-dom
- **Backend**: FastAPI + Uvicorn (`backend/api.py`), SQLAlchemy ORM, Alembic para migraciones
- **Auth**: JWT con `python-jose` + bcrypt, multi-tenancy por `org_id`
- **Base de datos**: PostgreSQL 16 (local en Docker, Render en cloud)
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

```bash
# Tests unitarios de steps
pytest tests/steps/test_pipeline_steps.py -v

# Con cobertura
pytest tests/steps/test_pipeline_steps.py --cov=rgenerator

# ETL desde CLI
python scripts/run_etl.py ./config/simce_estudiantes_lenguaje.txt

# Generar PDF
python scripts/generate_report.py --schema <schema.json> --data <data.csv> --tipo <type> --output <output.pdf>

# Export/import DB (para seed de Render o backup)
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

En Render, `data/pipeline_runs/` y `data/output/` requieren un Persistent Disk (plan Starter). Staging actual no tiene disk — las ejecuciones largas pierden artifacts al redeployar.

### Config del dominio (no DB)

- `config/*.txt` — mapeos de columnas, header rows, enrichment para ETL específicos de cada evaluación
- `data/database/reports_templates/` — plantillas de gráficos y tablas para `GenerateGraphics`/`GenerateTables`

---

## Deploy a Render

- **IaC**: `render.yaml` define backend + DB (+ disk en prod)
- **Seed inicial de DB**: `scripts/db_seed.py import --input db_seed.json --clear` desde local apuntando al External URL de la PG de Render
- **Rama staging**: Render service `rgenerator-staging` sigue `dev`
- **Docker**: Dockerfile multi-stage con targets `dev` y `prod`. Render usa `prod`

Detalles y credenciales en `memory/project_deploy_status.md`.

---

## Skills de administración

Tareas recurrentes documentadas en **[.agents/workflows/](./.agents/workflows/)**:

- `/add-step` — Crear o modificar un paso de pipeline
- `/add-metric` — Crear una nueva métrica (API REST o SQLAlchemy)
- `/new-pipeline` — Construir un nuevo pipeline JSON desde cero
- `/add-chart` — Agregar un gráfico o tabla al sistema de dashboards

## Roadmap

Pendientes, deuda técnica y mejoras planificadas en **[ROADMAP.md](./ROADMAP.md)**.
