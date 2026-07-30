# Diagnóstico general de la aplicación — 2026-07-30

Síntesis simple del estado de la plataforma tras el sprint de informes por período (rama `dev3`).
Detalle por documento: [mapa de la aplicación](../desarrollo/mapa_aplicacion.md) ·
[QA visual de informes](calidad_informes_selector_2026-07-30.md) · [org demo](../desarrollo/org_demo.md).

## Estado por área

| Área | Estado | Comentario |
|---|---|---|
| Descarga de informes (misión del merge) | ✅ | Modal con 4 informes de período + especializados; 34 opciones → 0 errores; sin `nan`, sin tracebacks en PDF, pie = nombre de la organización. |
| Motor de períodos | ✅ | última prueba / semestral / anual / personalizado resueltos server-side; cards no disponibles explican el motivo. |
| Registro de informes Python | ✅ | Carpeta `backend/rgenerator/reports/custom/` con auto-descubrimiento; agregar un informe = 1 archivo `.py` (ver README de la carpeta). |
| Dashboard (/results) | ✅ con reservas | Funciona; queda un chip pendiente: conteos v1 inflados cuando `nivel_de_logro` apunta también a la métrica de preguntas (afecta DIA). |
| Carga de datos (pipelines) | ✅ con reservas | Flujo estable; la carga DIA 2026 vino con Nombre/N° Lista nulos (mitigado en presentación; pipeline por unificar). |
| Word | ⏸ | Descopeado por decisión de producto — queda para el final del proyecto. |
| Seguridad / roles | ⚠️ | Los routers de dominio no exigen rol (un `viewer` puede crear/borrar). Backlog prioritario post-merge, junto a los P1 del QA maestro. |
| Configuración de indicadores | ⚠️ | Panguipulli sin layout PDF; header DIA con líneas stale (editable en Editor de Layout); SIMCE con 1 sola línea de header. |

## Qué se arregló en este sprint (resumen)

- 15 P0 y los P1 críticos del QA visual: PDFs vacíos con 200 → 400 accionable; excepciones ya no se imprimen en el informe; `nan` visible → "—"; conteos de alumnos por estudiante único; eje temporal cronológico; charts DIA robustos a nulos; tabla PDL IDEL legible; encabezados sin placeholders muertos y sincronizados con el período; "Miguel Godoy Díaz" erradicado de repo + DB con denylist de respaldo; FL ya no duplica el gráfico de Calidad Lectora.
- Suite: **1111 tests, 0 fallos** (WSL). En Windows solo los 2 fallos de entorno conocidos.

## Cómo probar sin tocar datos reales

Org sandbox **Colegio Demo** (`demo@rgenerator.local` / `demo1234`), con datos sintéticos y
edge cases sembrados. Recrear: `docker compose -f docker-compose.dev.yml exec -T backend python scripts/crear_org_demo.py --reset`.

## Al desplegar a producción

1. `alembic upgrade head`
2. `python scripts/limpiar_left_footer_legacy.py` (footer legacy en Supabase)
3. Setear `report_engine_type` de los indicadores + scripts de config SIMCE (`_fix_simce_temporal_order`, `_seed_simce_derived_columns`)
