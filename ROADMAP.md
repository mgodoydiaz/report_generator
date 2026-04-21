# ROADMAP

Pendientes, deuda técnica y mejoras planificadas para Report Generator.

---

## Tech Debt

| # | Área | Descripción |
|---|------|-------------|
| 1 | Base de datos | Base de datos en Excel sin soporte de concurrencia ni transacciones — migrar a PostgreSQL |
| 6 | Infraestructura | Generación de PDFs usa LaTeX/MikTeX (~1 GB) — **RESUELTO en M3**: migrado a WeasyPrint. Steps LaTeX (`RenderReport`) siguen en el código pero están sin probar. |
| 8 | Steps legacy | `GenerateTables`, `GenerateGraphics`, `RenderReport` (LaTeX) y `GenerateDocxReport` están sin tests actualizados y posiblemente rotos. Auditar en rama `dev-legacy-audit` antes de construir pipelines encima. Decidir cuáles conservar, cuáles eliminar. |
| 9 | Infraestructura | `data/org_assets/` (logos subidos por usuarios) requiere **Persistent Disk** en Render. En staging (Free tier) no hay disk — los logos se pierden en cada redeploy. Provisionar disk antes de usar logos en producción. |
| 7 | Infraestructura | Imagen Docker del backend usa Miniconda (~500 MB base) — migrar a `python:3.11-slim` + `requirements.txt` + `apt-get` para deps de sistema (ghostscript, libpq); más liviano, más estándar y builds más rápidas |
| 2 | Backend | Helpers duplicados `get_df`/`save_df` en `routers/dimensions.py` y `routers/metrics.py` — consolidar en módulo compartido |
| 3 | Frontend | Páginas `Results` y `Help` sin implementar (placeholders) |
| 4 | Seguridad | Sin autenticación ni RBAC |
| 5 | Tests | Archivos en `tests/` (`manual_qa.py`, `test_manual_pipeline.py`, `pipeline.py`) desactualizados — usan `LoadConfig` (deprecado) |

---

## Backlog

### General
- [ ] Definir y cambiar el nombre del software

### Infraestructura y despliegue
- [ ] Crear imagen Docker y contenerizar la aplicación
- [ ] Migrar el entorno de ejecución final a Linux
- [ ] Levantar servidor de producción
- [ ] Evaluar Free Tier en AWS o GCP para hosting
- [ ] Crear base de datos en la nube (AWS RDS u equivalente)
- [ ] Publicar el servicio en línea

### Base de datos
- [ ] Configurar PostgreSQL como motor principal
- [ ] Diseñar y crear el esquema de base de datos
- [ ] Agregar columnas `user_id` y `customer_id` para soporte multitenancy

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
- [ ] Implementar generación de gráficos, tablas, reportes y dashboards desde el frontend
- [ ] Perfilamiento y configuración por usuario
- [ ] Implementar multitenancy (múltiples organizaciones/clientes)
- [ ] Falta agregar Habilidad y Eje Temático como métrica
- [ ] Agregar un paso que, dependiendo de la dimensión, enriquezca una métrica
- [ ] Agregar un consolidado de pasos (agregar el enriquecer por métrica)
- [ ] Completar pruebas e implementación con: Lenguaje, Matemáticas SIMCE, Cálculo Veloz, y PDL

### Calidad y documentación
- [ ] Escribir suite de tests automatizados
- [x] Crear documentación de pasos y guía de uso — (Migrado a `.agents/workflows/`)

---

## Historial de versiones

| Versión | Fecha | Descripción |
|---------|-------|-------------|
| v0.0.1 | 2026-03-03 | Primera versión etiquetada — pipeline SIMCE Lenguaje funcional, ETL + reportes + métricas |
