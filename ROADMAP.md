# ROADMAP

Pendientes, deuda técnica y mejoras planificadas para Report Generator.

---

## Tech Debt

| # | Área | Descripción |
|---|------|-------------|
| 1 | Base de datos | ~~Base de datos en Excel sin soporte de concurrencia ni transacciones — migrar a PostgreSQL~~ ✅ **Hecho** — PostgreSQL 16 como motor principal, Excel legacy archivado en `data/database/`. |
| 6 | Infraestructura | ~~Generación de PDFs usa LaTeX/MikTeX (~1 GB) — migrado a WeasyPrint.~~ ✅ **Hecho en M3**. Los steps LaTeX (`RenderReport`, `GenerateTables`, `GenerateGraphics`) siguen vivos pero sin tests — ver ítem #8. |
| 8 | Steps legacy | `GenerateTables`, `GenerateGraphics`, `RenderReport` (LaTeX) y `GenerateDocxReport` están sin tests actualizados y posiblemente rotos. Auditar en rama `dev-legacy-audit` antes de construir pipelines encima. Decidir cuáles conservar, cuáles eliminar. |
| 9 | Infraestructura | `data/org_assets/` (logos subidos por usuarios) requiere **Persistent Disk** en Render. En staging (Free tier) no hay disk — los logos se pierden en cada redeploy. Provisionar disk antes de usar logos en producción. |
| 7 | Infraestructura | ~~Imagen Docker del backend usa Miniconda (~500 MB base) — migrar a `python:3.11-slim`~~ ✅ **Hecho** — Dockerfile multi-stage con `python:3.11-slim` + apt-get (ghostscript, libpango, etc.) + `requirements.txt`. |
| 2 | Backend | ~~Helpers duplicados `get_df`/`save_df` en `routers/dimensions.py` y `routers/metrics.py` — consolidar en módulo compartido~~ ✅ **Hecho** — los routers migraron a SQLAlchemy; el módulo vestigial `backend/routers/_db.py` fue eliminado. |
| 3 | Frontend | ~~Páginas `Results` y `Help` sin implementar (placeholders)~~ ✅ **Hecho** — ambas páginas implementadas (Results con dashboards + generación de PDF; Help con catálogo de componentes). |
| 4 | Seguridad | ~~Sin autenticación ni RBAC~~ ✅ **Hecho** — JWT + bcrypt + `org_id` en todas las tablas de negocio (multi-tenancy). Roles: `superadmin`, `admin`, `user`. |
| 5 | Tests | Cobertura de tests mínima. Hoy sólo hay un `vitest` frontend (`tests/frontend/dataProcessing.test.js`) y un spec E2E en markdown (`tests/e2e/pdl-dashboard.spec.md`). Sin suite automatizada del backend, sin CI que corra nada. Ver "Próximos sprints → Crear tests". |

---

## Backlog

### Próximos sprints — Limpieza y consolidación

Prioridad alta. Pendientes concretos a tomar en las próximas iteraciones:

- [ ] **Eliminar archivos Excel legacy** de `data/database/` (quedan como "seed de referencia" pero ya están migrados a Postgres). Mantener sólo lo que se use en runtime (templates de reportes).
- [ ] **Barrer funcionalidades antiguas de Excel** en el código (`get_json_safe_df`, helpers de `pd.read_excel` en routers antiguos, steps `RunExcelETL` si aún queda residual). Auditar qué sigue vivo y eliminar el resto.
- [ ] **Quitar frontend deprecado** — componentes Recharts legacy en `frontend/src/tooling/charts/` que ya fueron reemplazados por los Plotly en `tooling/plotly-charts/`. Revisar uso antes de borrar.
- [ ] **Crear suite de tests** — pytest del backend (endpoints críticos, `build_pdf_bytes`, filtrado de `_build_records`, multi-tenancy). Ampliar vitest frontend. Configurar CI (GitHub Actions).
- [ ] **Documentar el sitio** — README del producto para usuarios finales, guía de onboarding de nuevas organizaciones, docs de LayoutEditor y del modal de generación de reportes.

### General
- [ ] Definir y cambiar el nombre del software

### Infraestructura y despliegue
- [x] Crear imagen Docker y contenerizar la aplicación
- [x] Migrar el entorno de ejecución final a Linux (Docker + WSL en dev; Render en staging)
- [ ] Levantar servidor de producción
- [ ] Evaluar Free Tier en AWS o GCP para hosting (staging actual en Render Free)
- [ ] Crear base de datos en la nube (AWS RDS u equivalente — staging usa Render Postgres; prod pendiente, probable Neon São Paulo)
- [ ] Publicar el servicio en línea (staging disponible en `rgenerator-staging.onrender.com`)
- [ ] **TODO: apagar la DB de Render staging** (en Oregon, latencia alta desde Chile, sin backups automáticos). Producción ya migró a Railway + Supabase São Paulo. El propio servicio web `rgenerator-staging` también puede apagarse cuando no sea necesario para validación.
- [ ] **TODO: registrar Task Scheduler para `scripts/backup_supabase.py`** (lunes y viernes 03:00). El script y el helper `scripts/run_supabase_backup.bat` ya están listos. Falta sólo registrar la tarea con `schtasks` (ver docstring del script). Definir antes la carpeta de destino definitiva (default `backups/` dentro del repo, gitignored — alternativa: ruta fuera del repo o OneDrive).
- [ ] **TODO: configurar ping anti-pausa de Supabase Free** (cron-job.org apuntando a un endpoint del backend en Railway que toque la DB, ej. `/api/health/db`, cada ≤6 días). Pendiente hasta tener Railway desplegado y el endpoint expuesto.

### Base de datos
- [x] Configurar PostgreSQL como motor principal
- [x] Diseñar y crear el esquema de base de datos
- [x] Agregar columnas `user_id` y `customer_id` para soporte multitenancy (implementado como `org_id` en todas las tablas de negocio)

### Backend
- [ ] Migrar backend a Django (objetivo: junio)
- [ ] Integrar Celery para procesamiento de tareas en segundo plano (batch jobs)
- [ ] Implementar logging estructurado de acciones y errores

### Especificaciones (Specs)
- [ ] `NewSpecDrawer.jsx`: agregar sección de edición para tipo `Gráficos` — formulario para `metadata` y `charts_list`
- [ ] `NewSpecDrawer.jsx`: agregar sección de edición para tipo `Tablas` — formulario para `metadata` y `tables_list`
- [ ] `NewSpecDrawer.jsx`: agregar sección de edición para tipo `Dashboard`

### Frontend / UX
- [ ] Corregir modo oscuro: legibilidad de texto y estados de botones
- [ ] Implementar sistema de internacionalización (i18n) con archivo de mensajes por idioma
- [ ] En Drawers de creación, agregar botón para abrir modal de edición completa
- [ ] En Drawer de carga de métrica, agregar selector o ayuda contextual para elegir métrica existente
- [ ] Visualización de workflows como mapa visual (grafo de pasos)
- [ ] Panel de notificaciones con historial de acciones

### Funcionalidades
- [x] Implementar generación de gráficos, tablas, reportes y dashboards desde el frontend (dashboards en `Results`; descarga de PDF vía modal con motor `weasyprint` o `pdl_idel`)
- [x] **Motor PDF v2 con paridad LaTeX** (`backend/rgenerator/reports/`) — paquete independiente: charts.py + tables.py + runtime.py + templates HTML que replican el formato LaTeX referencia. Endpoint `POST /api/reports/{tipo}` (simce | dia). Botón "Generar v2" en `/results` con modal de branding editable. Validación de filtro temporal requerido. Detalle: `docs/usuario/motor_pdf_v2.md`.
- [x] **Campos derivados (`derived_fields`)** — engine que aplica funciones a columnas: `agg` (groupby + agregación), `slope` (regresión lineal expansiva), `delta` (último menos primero). Soporta `entity_field` compuesto (ej `["Curso", "Nombre"]`), `value_type=ordinal` con `ordinal_levels`, `time_type=ordinal` con `time_ordinal_levels`. Step `ApplyDerivedFields` para usar en pipelines ETL. Aplicado al pipeline SIMCE Lenguaje (id=14) y a esquemas v2 SIMCE/DIA.
- [ ] Perfilamiento y configuración por usuario
- [x] Implementar multitenancy (múltiples organizaciones/clientes)
- [ ] Falta agregar Habilidad y Eje Temático como métrica
- [ ] Agregar un paso que, dependiendo de la dimensión, enriquezca una métrica
- [ ] Agregar un consolidado de pasos (agregar el enriquecer por métrica)
- [ ] Completar pruebas e implementación con: Lenguaje, Matemáticas SIMCE, Cálculo Veloz, y PDL
- [ ] **Pipeline DIA Matemáticas / Lectura** — portar `script_consolidar_DIA.py` artesanal del cliente a steps configurables (ETL XLS estudiantes con header en fila 12, extracción de PDFs con camelot+fitz, normalización de nombres entre hitos, cálculo de Logro = mean dynamic columns). Ver `docs/desarrollo/script_dia_artesanal_referencia.md`.
- [ ] **Catálogo de tablas/layouts** — UI para configurar tablas de informe en base a una métrica (resumen por curso, estudiantes, preguntas) usando `derived_fields` como celdas calculadas.
- [ ] **Catálogo de generadores de gráficos** — `CHART_REGISTRY` ya existe; falta UI rica para configurar gráficos en informes y dashboards (matplotlib/seaborn/plotly/recharts).
- [ ] **Sprint de filtros transversales** — filtros multi-nivel (varios valores por dimensión) en resultados, dashboards, valores e informes. Hoy filtran solo por igualdad simple.
- [ ] **Página `/functions`** — UI catálogo + form por kind para editar `derived_fields` sin tocar JSON crudo. Hoy es placeholder. Por mientras, edición vía LayoutEditorModal.
- [ ] **Migrar `derived_fields` y esquemas a DB** — hoy viven en archivos del repo (`backend/rgenerator/reports/{tipo}/esquema.json`); migrar a campos del Indicator para edición desde UI.

### Calidad y documentación
- [ ] Escribir suite de tests automatizados
- [x] Crear documentación de pasos y guía de uso — (Migrado a `.agents/workflows/`)

---

## Issues conocidos (datos)

- **DIA: nombres invertidos entre hitos** — en LECTURA y MATEMÁTICAS, los nombres en `DIAGNOSTICO` vienen "Nombre Apellido" y en `INTERMEDIO` "Apellido Nombre". Resultado: 0 matches al agrupar por `(Curso, Nombre)`, lo que bloquea cálculo de `Avance` y `Mejora_vs_Inicio` entre hitos. Por eso esas columnas están desactivadas en `dia/esquema.json`. Solución: agregar un step de normalización de nombres al pipeline DIA (sort de palabras del nombre, o mejor: usar `Numero Lista` + `Curso` como clave compuesta si es estable entre hitos). Re-habilitar las 2 derived_fields cuando se resuelva.

---

## Historial de versiones

| Versión | Fecha | Descripción |
|---------|-------|-------------|
| v0.0.1 | 2026-03-03 | Primera versión etiquetada — pipeline SIMCE Lenguaje funcional, ETL + reportes + métricas |
| v0.2.0 | 2026-05-04 | Motor PDF v2 (paridad LaTeX) + campos derivados (agg/slope/delta) + step `ApplyDerivedFields` + modal de branding editable + 74 tests verdes. SIMCE Lenguaje muestra Avance del estudiante por regresión lineal en el PDF. |
