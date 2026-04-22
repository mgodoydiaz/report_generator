# E2E · Dashboard PDL (Indicador 3)

**Runner:** Chrome MCP (en una conversación aparte, pegar este script como prompt).
**Precondición:** backend + frontend corriendo localmente; seed de DB con indicador 3 (IDEL-Woodcock) y layout v2 aplicado (`python scripts/apply_pdl_layout_v2.py`). Usuario superadmin creado.

No existe un framework E2E automatizado en el repo. Este documento es el guion que un operador humano ejecuta con Chrome MCP hasta que se decida adoptar Playwright o similar.

---

## Flujo

1. **Login**
   - Navegar a `http://localhost:5173`.
   - Escribir credenciales superadmin, click "Iniciar sesión".
   - Assert: URL pasa a `/` o `/pipelines` sin errores en consola.

2. **Ir a Results**
   - Click en el item "Resultados" del sidebar (`/results`).
   - Assert: dropdown de indicadores carga (> 0 opciones).

3. **Seleccionar indicador 3**
   - Elegir "IDEL" / "PDL" (o el nombre exacto del indicador 3) en el dropdown.
   - Click en "Generar Dashboard".
   - Assert: aparecen 4 tabs: Panorama, Por Curso, Por Subprueba, Síntesis.

4. **Tab 1 · Panorama**
   - Assert: 4 tarjetas KPI (Total estudiantes, % Crítico+Alto, Curso más crítico, Subprueba más crítica).
   - Assert: 1 gráfico stacked ("Niveles por curso") visible.
   - Assert: 2 heatmaps lado a lado (N Crítico+Alto, % Crítico+Alto).
   - Screenshot → guardar como `sprint5/tab1-panorama.png`.

5. **Tab 2 · Por Curso**
   - Click en tab "Por Curso".
   - Assert: selector de curso visible. Si no hay curso activo, el resto está oculto/vacío.
   - Click en "2° BÁSICO" (o el primero disponible).
   - Assert: 6 mini-KPIs (CT, FLO, FNL, FSF, ILP, VSD).
   - Assert: `StackedCountByGroup` con niveles por subprueba.
   - Assert: `StudentRiskList` con al menos 1 alumno.
   - Assert: `PivotTable` con celdas coloreadas por nivel (semáforo).
   - Screenshot → `sprint5/tab2-por-curso.png`.

6. **Tab 3 · Por Subprueba**
   - Click en tab "Por Subprueba".
   - Assert: selector de subprueba visible.
   - Click en "CT".
   - Assert: BarByGroup, BoxPlotByGroup, StackedCountByGroup, TrendLine renderizados.
   - Assert: **no** aparece warning en consola sobre requiresSingleMetricContext (hay selector).
   - Screenshot → `sprint5/tab3-por-subprueba.png`.

7. **Tab 4 · Síntesis**
   - Click en tab "Síntesis".
   - Assert: 2 `ImprovementRateByGroup` lado a lado.
   - Assert: `TransitionMatrix` (Sankey) renderizado.
   - Assert: `PivotTable` consolidado con semáforo de peor-nivel.
   - **Regresión v1:** texto "71%" visible en alguna barra de 1° básico en el primer `ImprovementRateByGroup` (o el porcentaje equivalente al dataset de referencia).
   - Screenshot → `sprint5/tab4-sintesis.png`.

8. **Export PDF**
   - Volver a Tab 1.
   - Click en el botón "PDF" (verde) al lado de "Generar Dashboard".
   - Assert: descarga un archivo `.pdf` > 0 bytes.

9. **Limpiar filtros al cambiar tab**
   - Tab 2 → elegir "2° BÁSICO".
   - Tab 4 → volver a Tab 2.
   - Assert: curso activo volvió a null (selector vacío).

10. **LayoutEditor — warning requiresSingleMetricContext**
    - Ir a `/indicators`, abrir el editor del indicador 3.
    - Crear un tab temporal "test-scale" con un `BarByGroup` sin filtro ni subprueba_selector.
    - Assert: banner naranja visible arriba del tab, mencionando `BarByGroup` y pidiendo agregar un filtro `_habilidad`.
    - Descartar cambios.

---

## Smoke regression SIMCE

1. Seleccionar un indicador SIMCE (si existe en el seed — `id=1` o similar).
2. Click "Generar Dashboard".
3. Assert: renderea sin errors en consola. KPIs muestran `totalEstudiantes > 0`.
4. Screenshot → `sprint5/smoke-simce.png`.

---

## Resultado esperado

- 9/9 pasos verdes (+1 smoke SIMCE).
- 0 errors en consola.
- 5 screenshots adjuntos al PR.
