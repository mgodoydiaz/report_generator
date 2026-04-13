# Arquitectura general

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | React 18 + Vite, Tailwind CSS 4, react-router-dom |
| Backend | FastAPI + Uvicorn (`backend/api.py`) |
| Base de datos | PostgreSQL (SQLAlchemy ORM) |
| ETL library | Paquete `rgenerator` (`backend/rgenerator/`) |
| PDF | LaTeX/MiKTeX + docxtpl para Word |
| Gráficos | matplotlib, Plotly (frontend) |
| Auth | JWT (python-jose + bcrypt) |

---

## Estructura del backend

```
backend/
├── api.py              FastAPI app, monta 10 routers
├── auth.py             JWT: generación, verificación, dependencias
├── database.py         SQLAlchemy engine, SessionLocal, init_db()
├── models.py           Modelos ORM: User, Organization, Pipeline, Metric, etc.
├── config.py           Constantes de rutas (DATA_DIR, DB_DIR, etc.)
├── routers/
│   ├── auth.py         Login, /me
│   ├── users.py        CRUD usuarios
│   ├── superadmin.py   Gestión de organizaciones (solo superadmin)
│   ├── pipelines.py    CRUD + ejecución + uploads
│   ├── specs.py        Especificaciones de reporte
│   ├── dimensions.py   Dimensiones y valores
│   ├── metrics.py      Métricas con import/export
│   ├── indicators.py   Indicadores y dashboards
│   ├── results.py      Datos de resultados por indicador
│   └── resultspy.py    Dashboards Plotly server-side
└── rgenerator/
    ├── etl/core/       Steps del pipeline
    └── tooling/        Herramientas: datos, gráficos, reportes
```

## Estructura del frontend

```
frontend/src/
├── App.jsx             Router (10 páginas)
├── context/
│   ├── AuthContext.jsx Estado global de auth + fetchAuth()
│   └── ThemeContext.jsx
├── pages/              Login, Home, Pipelines, Specs, Dimensions,
│                       Values, Metrics, Indicators, Results, Execution,
│                       Users, SuperAdmin, Resultspy
├── components/         Layout, Sidebar, drawers, modales
│   └── pipeline-steps/ UI por tipo de step
└── tooling/
    ├── charts/         Gráficos Recharts legacy
    ├── plotly-charts/  Gráficos Plotly
    └── dashboardRenderer.jsx
```

---

## Modelo de ejecución de pipelines

Los pipelines son JSONs en `data/database/pipelines/`. Cada uno tiene `workflow_metadata`, `context` y un array `pipeline` de `{step, params}`.

`PipelineRunner` en `tooling/pipeline_tools.py` mapea nombres de steps a clases via `STEP_MAPPING` y los ejecuta secuencialmente sobre un `RunContext` compartido.

Un step puede lanzar `WaitingForInputException` para pausar y pedir archivos al usuario. El API devuelve status `"waiting"`, el frontend muestra el uploader, y reanuda la ejecución al recibir los archivos.

### RunContext — campos clave

| Campo | Descripción |
|---|---|
| `inputs` | Archivos de entrada por rol (`estudiantes`, `preguntas`, etc.) |
| `artifacts` | DataFrames/objetos intermedios entre steps |
| `outputs` | Paths de salida finales por rol |
| `status` | `NEW \| RUNNING \| NEEDS_REVIEW \| DONE \| FAILED` |
| `last_artifact_key` | Clave del último artefacto producido |

---

## Autenticación

- Login via `POST /api/auth/login` → devuelve JWT
- Todas las rutas requieren `Authorization: Bearer <token>`
- El frontend usa `fetchAuth()` (en `AuthContext`) como wrapper de `fetch` que inyecta el token automáticamente
- Roles: `admin`, `user`, `superadmin`
