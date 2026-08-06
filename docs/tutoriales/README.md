# Tutoriales de usuario

Guías paso a paso dirigidas al personal no técnico de la fundación que usa la aplicación web (no a desarrolladores). Complementan `docs/qa/manual/` (que son guiones de prueba, no tutoriales) y los docs técnicos de `docs/usuario/`.

## Contenido

- [`guia_rapida_usuario.md`](./guia_rapida_usuario.md) — versión corta en 4 secciones (entrar, cargar datos, dashboard, informe), con pantallazos reales de la organización de demostración. Es la que se entrega a usuarios nuevos. La carga de datos tiene dos caminos: proceso configurado en **Ejecución**, o **Valores → Importar** con plantilla descargable.
- [`descarga_informes_aptus.html`](./descarga_informes_aptus.html) / [`.docx`](./descarga_informes_aptus.docx) / [`.pdf`](./descarga_informes_aptus.pdf) — guía visual de una sola tarea: cómo descargar los dos informes (por Estudiante y por Habilidad) desde la plataforma Aptus y subirlos. Incluye reproducciones dibujadas de las pantallas de Aptus (no capturas: la pantalla real muestra nombres y RUT de estudiantes). Es la que se entrega a quien hace la carga de SIMCE Panguipulli. Fuente editable: el `.html`. El PDF se regenera con `python -m weasyprint descarga_informes_aptus.html descarga_informes_aptus.pdf`; el Word con `scripts/generar_tutorial_aptus_docx.py` (usa la plantilla de Miguel e incrusta las pantallas como PNG).
- [`anexo_carga_pipelines.md`](./anexo_carga_pipelines.md) — detalle de la sección 2 de la guía rápida: un capítulo por proceso de carga real (SIMCE, DIA, SIMCE Panguipulli) con los archivos que pide cada uno, los datos extra y los errores frecuentes. La guía no repite este detalle, solo lo enlaza.
- [`tutorial_usuario.md`](./tutorial_usuario.md) — flujo completo: subir datos de una evaluación, revisar el dashboard de Resultados y descargar el informe (PDF/Word). Versión entregable en `tutorial_usuario.pdf` / `.docx` (10 páginas, con índice y las capturas de `img/` que aplican).

## Cómo mantenerlo al día

Este tutorial describe la UI tal como está implementada en el código, no un diseño ideal. Cuando cambie alguno de estos archivos, revisa si el tutorial quedó desactualizado:

- `frontend/src/components/PipelineExecutionModal.jsx` y `frontend/src/components/pipeline-steps/*` (Parte 1 — carga de datos).
- `frontend/src/components/ImportModal.jsx`, `frontend/src/pages/Values.jsx` y el endpoint `GET /api/metrics/{id}/template` de `backend/routers/metrics.py` (Parte 1b — carga manual con plantilla).
- `frontend/src/pages/Results.jsx` y `frontend/src/components/MultiSelectFilters.jsx` (Parte 2 — dashboard y filtros).
- `frontend/src/components/ReportSelectorModal.jsx` y `backend/routers/indicators.py` (endpoint `report-options`) (Parte 3 — descarga de informes).

En `tutorial_usuario.md` las capturas están marcadas con `![Captura: descripción](pendiente)` — reemplaza `pendiente` por la ruta real de la imagen cuando se agreguen.

## Recapturar los pantallazos de la guía rápida

Las 9 imágenes de `img/` se generan automáticamente contra la organización de demostración
("Colegio Demo", datos sintéticos). Con el stack de desarrollo levantado:

```bash
node docs/tutoriales/img/_capturar.mjs
```

Requiere Playwright instalado **fuera del repo** (para no tocar `package.json`):

```bash
mkdir -p ~/tmp_screenshots && cd ~/tmp_screenshots
npm init -y && npm i playwright && npx playwright install chromium
```

El script hace login, captura las 8 pantallas, descarga el informe PDF y convierte su
primera página con `_pdf_a_png.py` (que corre dentro del contenedor backend, donde vive
PyMuPDF). Los detalles y requisitos están en la cabecera de `img/_capturar.mjs`.

El modal **Importar Datos** solo se abre y se cierra con *Cancelar*: el script nunca
completa una importación real.
