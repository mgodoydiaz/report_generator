# G3 — Dashboard y filtros

**Precondiciones**: indicador con datos (ej. IDEL o SIMCE) y dimensiones filtrables (Curso, Año, Mes/Hito).

| # | Acción | Esperado |
|---|---|---|
| 1 | /results → seleccionar indicador | Dashboard carga con KPIs/gráficos/tablas |
| 2 | Aplicar filtro de UN valor (ej. Curso=5A) | Todos los charts y tablas se actualizan coherentemente |
| 3 | Aplicar filtro MULTI-valor (ej. Curso=5A+5B) | Charts muestran la unión de ambos cursos |
| 4 | Combinar filtros (Curso + Año) | Cascada correcta: los valores disponibles de otros filtros se acotan |
| 5 | Quitar todos los filtros | Vuelve al estado completo sin residuos |
| 6 | Con filtros multi-valor activos, generar el PDF (botón principal) | **El PDF contiene exactamente los datos filtrados en pantalla** (regresión P0-1: antes salía vacío o completo) |
| 7 | En un indicador DIA, filtrar Año y generar informe v2 | El PDF respeta el Año (regresión P0-2) |
| 8 | Colores de niveles de riesgo IDEL en charts | Coinciden con la página de Indicadores (Crítico #dc2626, Alto #ea580c, Cierto #eab308, Bajo #22c55e) |
