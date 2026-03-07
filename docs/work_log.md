# Registro de Trabajo: Nuevas Capacidades de Reporte

Este documento resume las adiciones realizadas al sistema de pipelines (`backend/rgenerator`) para soportar la generación automatizada de informes tanto en formato **LaTeX (PDF rico)** como en **DOCX (Word editable)**.

## 1. Nuevos Steps Implementados

Los siguientes steps han sido agregados a `backend/rgenerator/etl/core/pipeline_steps.py`:

*   **`GenerateGraphics(charts_schema)`**: 
    *   Genera gráficos utilizando `matplotlib` (vía `plot_tools`). 
    *   Configurable mediante un esquema JSON.
    *   Salida automática a `aux_files`.

*   **`GenerateTables(tables_schema)`**:
    *   Genera archivos Excel con tablas resumen (vía `report_tools`).
    *   Soporta iteración (ej: una tabla por curso).

*   **`RenderReport(report_schema)`**:
    *   Orquesta la creación de un informe PDF de alta calidad usando LaTeX.
    *   Genera dinámicamente archivos `.tex` basándose en el esquema.
    *   Compila usando `xelatex`.

*   **`GenerateDocxReport(template_name, context_key)`**:
    *   Genera informes Editables (.docx) usando plantillas Jinja2 (`docxtpl`).
    *   Permite inyección de texto, tablas dinámicas e imágenes.
    *   Soporta conversión automática a PDF (vía `docx2pdf`).

## 2. Herramientas Auxiliares (Tooling)

*   **`backend/rgenerator/tooling/report_docx_tools.py`**: Funciones helper para renderizar plantillas docx y convertir a PDF.
*   **`backend/rgenerator/tooling/report_tools.py`**: Funciones para generar tablas (resúmenes estadísticos) y formatear DataFrames a código LaTeX.

## 3. Pipelines de Demostración

Se han creado scripts independientes para validar estas funcionalidades:

*   **`pipeline_latex_demo.py`**: Ejecuta una pipeline completa que termina en un PDF LaTeX.
*   **`pipeline_docx_demo.py`**: Ejecuta una pipeline que genera un informe Word desde una plantilla, incrustando gráficos generados.
*   **`scripts/create_sample_docx.py`**: Script utilitario para generar una plantilla Word de ejemplo compatible con Jinja2.

## 4. Próximos Pasos Sugeridos

*   Integrar estos steps en las pipelines productivas (JSONs en `data/database/pipelines`).
*   Refinar las plantillas LaTeX (`formato_informe_generico`) para adaptarse a la identidad visual final.
*   Crear más tipos de gráficos en `plot_tools` según necesidad.
