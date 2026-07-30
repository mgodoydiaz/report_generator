# Tutoriales de usuario

Guías paso a paso dirigidas al personal no técnico de la fundación que usa la aplicación web (no a desarrolladores). Complementan `docs/qa/manual/` (que son guiones de prueba, no tutoriales) y los docs técnicos de `docs/usuario/`.

## Contenido

- [`guia_rapida_usuario.md`](./guia_rapida_usuario.md) — versión corta en 4 pasos, con pantallazos reales de la organización de demostración. Es la que se entrega a usuarios nuevos.
- [`tutorial_usuario.md`](./tutorial_usuario.md) — flujo completo: subir datos de una evaluación, revisar el dashboard de Resultados y descargar el informe (PDF/Word).

## Cómo mantenerlo al día

Este tutorial describe la UI tal como está implementada en el código, no un diseño ideal. Cuando cambie alguno de estos archivos, revisa si el tutorial quedó desactualizado:

- `frontend/src/components/PipelineExecutionModal.jsx` y `frontend/src/components/pipeline-steps/*` (Parte 1 — carga de datos).
- `frontend/src/pages/Results.jsx` y `frontend/src/components/MultiSelectFilters.jsx` (Parte 2 — dashboard y filtros).
- `frontend/src/components/ReportSelectorModal.jsx` y `backend/routers/indicators.py` (endpoint `report-options`) (Parte 3 — descarga de informes).

En `tutorial_usuario.md` las capturas están marcadas con `![Captura: descripción](pendiente)` — reemplaza `pendiente` por la ruta real de la imagen cuando se agreguen.

## Recapturar los pantallazos de la guía rápida

Las 8 imágenes de `img/` se generan automáticamente contra la organización de demostración
("Colegio Demo", datos sintéticos). Con el stack de desarrollo levantado:

```bash
node docs/tutoriales/img/_capturar.mjs
```

Requiere Playwright instalado **fuera del repo** (para no tocar `package.json`):

```bash
mkdir -p ~/tmp_screenshots && cd ~/tmp_screenshots
npm init -y && npm i playwright && npx playwright install chromium
```

El script hace login, captura las 7 pantallas, descarga el informe PDF y convierte su
primera página con `_pdf_a_png.py` (que corre dentro del contenedor backend, donde vive
PyMuPDF). Los detalles y requisitos están en la cabecera de `img/_capturar.mjs`.
