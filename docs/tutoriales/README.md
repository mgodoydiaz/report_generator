# Tutoriales de usuario

Guías paso a paso dirigidas al personal no técnico de la fundación que usa la aplicación web (no a desarrolladores). Complementan `docs/qa/manual/` (que son guiones de prueba, no tutoriales) y los docs técnicos de `docs/usuario/`.

## Contenido

- [`tutorial_usuario.md`](./tutorial_usuario.md) — flujo completo: subir datos de una evaluación, revisar el dashboard de Resultados y descargar el informe (PDF/Word).

## Cómo mantenerlo al día

Este tutorial describe la UI tal como está implementada en el código, no un diseño ideal. Cuando cambie alguno de estos archivos, revisa si el tutorial quedó desactualizado:

- `frontend/src/components/PipelineExecutionModal.jsx` y `frontend/src/components/pipeline-steps/*` (Parte 1 — carga de datos).
- `frontend/src/pages/Results.jsx` y `frontend/src/components/MultiSelectFilters.jsx` (Parte 2 — dashboard y filtros).
- `frontend/src/components/ReportSelectorModal.jsx` y `backend/routers/indicators.py` (endpoint `report-options`) (Parte 3 — descarga de informes).

Las capturas de pantalla están marcadas con `![Captura: descripción](pendiente)` — reemplaza `pendiente` por la ruta real de la imagen cuando se agreguen.
