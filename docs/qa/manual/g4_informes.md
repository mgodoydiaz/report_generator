# G4 — Generación de informes

**Precondiciones**: indicadores SIMCE, DIA e IDEL con datos; al menos uno con layout PDF configurado.

| # | Acción | Esperado |
|---|---|---|
| 1 | /results → botón "Generar Reporte" (motor v1) en indicador con layout | PDF descarga y refleja los filtros activos |
| 2 | Mismo botón en indicador SIN layout configurado | Mensaje accionable, no error críptico ni botón muerto |
| 3 | Botón "Generar v2" en indicador SIMCE con filtro temporal (Mes/N Prueba) | PDF con formato paridad LaTeX correcto |
| 4 | "Generar v2" SIN filtro temporal | Error 400 explicando qué filtro falta (no 500) |
| 5 | Modal de branding v2: cambiar nombre/comuna | El PDF refleja el override; los defaults NO deben ser "Miguel Godoy Díaz"/"Panguipulli" hardcodeados para otras orgs (QA frontend) |
| 6 | Informe Word por indicador | .docx descarga y abre bien en Word |
| 7 | Forzar error en Word (indicador sin metrics asociadas) | Error claro, sin filtrar detalle interno (regresión P0-5) |
| 8 | Comparar cifras del PDF v1, v2 y dashboard para el MISMO filtro | Los tres coinciden (fuente única de filtrado) |
