# Plan de informes — selector de tipo, plantillas Word subibles y motor único

**Fecha**: 2026-07-22 · **Decidido con**: Miguel (por chat) · **Contexto**: [QA informes](../qa/hallazgos/informes.md)

## Fase 1 — Selector de tipo de informe ✅ (implementada en dev3)

- `Indicator.report_engine_type` (migración `b2c3d4e5f6a7`): motor especializado explícito (`simce | simce_panguipulli | dia | pdl_idel`), editable en el drawer de Indicadores ("Formato de informe oficial"). Reemplaza la heurística por substring del nombre (H5); queda fallback de inferencia por nombre para indicadores sin el campo.
- `GET /api/indicators/{id}/report-options`: catálogo único de informes del indicador — v1 evaluación/histórico (disponibles solo con secciones configuradas, con motivo accionable), pdl_idel, v2 según tipo (con `requiere_filtro_temporal`), e informes Word registrados. Cada opción trae su `invocacion`.
- `/results`: **un solo botón "Generar informe"** → `ReportSelectorModal` (cards con disponible/motivo) → despacha a los modales existentes (v1 con `initialTipo`/`initialEngine`, v2 con validación temporal movida al despacho, Word). Desaparecen los 3 botones y la jerga de motores (H3).

**Pendiente al aplicar en prod**: `alembic upgrade head` y setear `report_engine_type` en los indicadores existentes (dejan de depender del nombre).

## Fase 2 — Plantillas Word subibles por organización (próxima, L)

Visión: el usuario sube un `.docx` con placeholders, el software lo importa y aparece como tipo de informe en el selector.

1. Tabla `report_templates` (org_id, nombre, descripción, archivo, placeholders_detectados JSON, indicator_id opcional, created_by, timestamps). **Multi-tenant: cada org ve solo sus plantillas.**
2. `POST /api/report-templates` (multipart): validar extensión/MIME/tamaño; extraer placeholders con `docxtpl.get_undeclared_template_variables()`; validarlos contra el **catálogo de variables inyectables** (nombre indicador, filtros aplicados, fecha, niveles de logro, branding org, tablas y gráficos como imagen); guardar en `data/org_assets/{org}/report_templates/` (requiere Volume Railway — ROADMAP #9).
3. **Seguridad**: renderizar SIEMPRE con `jinja2.sandbox.SandboxedEnvironment` (docxtpl acepta env custom) — una plantilla subida es input no confiable (SSTI).
4. Las plantillas subidas aparecen automáticamente en `report-options` (formato word, motor docxtpl) y el motor Word resuelve plantilla desde DB además de las del repo.
5. UI: sección "Plantillas de informe" (subir, listar placeholders detectados, probar con datos del indicador, eliminar).
6. Semilla: plantilla base con el formato personal de Miguel (Cambria, acento #2E5E8C, encabezado/pie, 3 niveles de destacado — skill `plantilla-miguel`) adaptable al branding de cada org.

## Fase 3 — Consolidación motor único (L, diseño aprobado)

Según [informes.md §4](../qa/hallazgos/informes.md): loader único (filtrado `matches` compartido — ya existe `rgenerator/reports/filtering.py` — org_id siempre, split temporal declarativo por `esquema.json.temporal_dims`) + renderer único pilotado por `esquema.json` por tipo de evaluación (migrar IDEL a declarativo, crear esquemas FL/CV), motor v1 como fallback genérico, Word compartiendo loader. Eliminar: `RenderHtmlReport`, `report_html_tools.py`, `scripts/generate_report.py`, `funciones_informe.py`, `backend/schemas/esquema_informe*.json`, página `/results-recharts`.

Orden recomendado: Fase 2 puede ir antes o en paralelo con Fase 3 — el selector de Fase 1 ya desacopla la UI de los motores.
