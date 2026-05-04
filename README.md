# Report Generator · Fundación PHP

Aplicación web para automatizar la generación de informes académicos a
partir de archivos brutos de evaluaciones (SIMCE, DIA, ensayos
diagnósticos). Procesa los datos, calcula métricas y produce reportes PDF
listos para entregar a establecimientos educacionales.

## Capacidades

- **Pipelines configurables**: motor ETL orquestado por pasos en JSON,
  con pausas dinámicas para que el usuario suba archivos cuando el
  pipeline lo requiere.
- **Catálogos de gráficos, tablas y mapeos**: editores web para
  configurar componentes reutilizables sin tocar código.
- **Dashboards interactivos**: visualización por evaluación, curso o
  estudiante, con filtros multi-valor por dimensión.
- **Generación de PDFs**: motor con paridad visual respecto al formato
  histórico de la fundación.
- **Multi-tenant**: separación por organización con autenticación JWT y
  roles `superadmin` / `admin` / `user`.

## Stack

React 18 + Vite · FastAPI · PostgreSQL 16 · SQLAlchemy + Alembic ·
WeasyPrint · Plotly + matplotlib.

## Cómo correrlo (desarrollo)

Todo el entorno local corre en Docker.

```bash
cp .env.example .env   # completar las variables requeridas
docker compose -f docker-compose.dev.yml up --build
```

Levanta tres servicios:

| Servicio  | Puerto | Descripción                  |
|-----------|--------|------------------------------|
| frontend  | 5173   | Vite dev server con HMR      |
| backend   | 8000   | FastAPI con hot-reload       |
| db        | 5432   | PostgreSQL 16                |

Para parar todo: `docker compose -f docker-compose.dev.yml down`.

Atajo en Windows: `run_software.bat`.

## Variables de entorno

Las claves obligatorias están comentadas en `.env.example`. Como
referencia rápida:

- `DATABASE_URL` — cadena de conexión PostgreSQL.
- `JWT_SECRET` — secreto para firmar tokens JWT.
- `VITE_API_URL` — URL del backend que el frontend debe consultar.

Los archivos `.env*` están en `.gitignore` y no se versionan.

## Estructura del repositorio

| Carpeta             | Contenido                                   |
|---------------------|---------------------------------------------|
| `backend/`          | API FastAPI + paquete `rgenerator`          |
| `frontend/`         | UI React                                    |
| `data/`             | inputs, outputs y artifacts de ejecuciones  |
| `docs/`             | documentación técnica y guías de usuario    |
| `scripts/`          | utilidades de mantención                    |
| `.agents/workflows/`| recetarios para asistentes de IA            |

## Deployment

La guía operativa para staging y producción (URLs, runbook de
restauración, rotación de credenciales, configuración de backups
programados) está en [`DEPLOYMENT.md`](./DEPLOYMENT.md).

## Roadmap y deuda técnica

Los pendientes activos, las decisiones de arquitectura y el historial de
versiones se mantienen en [`ROADMAP.md`](./ROADMAP.md).

---

Desarrollado por Miguel Godoy Díaz — Fundación People Help People.
