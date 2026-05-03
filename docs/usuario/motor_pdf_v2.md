# Motor PDF v2 — Generar informes con paridad LaTeX

Guía rápida para usar el nuevo motor PDF (paquete `backend/rgenerator/reports/`)
que produce informes WeasyPrint con look idéntico al LaTeX manual.

## Cuándo usarlo

El motor v2 es la opción cuando querés:

- Un PDF que se **vea como los informes LaTeX históricos** (mismos
  gráficos matplotlib, paleta Set2 + semáforo, header con logos +
  3 líneas + regla 0.4pt).
- Tablas **dinámicas por curso** al final del informe (Logro por Alumno
  + Logro por Pregunta de cada curso, igual que el LaTeX manual).
- Tabla **estadística por pregunta** del establecimiento con A/B/C/D/E
  (SIMCE).

Si querés un dashboard editable visualmente con cards arrastrables, el
motor v1 (botón "Generar Reporte" del Indicator) sigue activo y es la
opción correcta.

## Cómo generar un informe

1. Ir a **Resultados** (`/results`).
2. Seleccionar el indicador en el dropdown (DIA o SIMCE — IDEL/CV/FL
   todavía no están soportados por el motor v2).
3. **Aplicar al menos un filtro temporal**:
   - Para **DIA**: `Hito` o `Año`.
   - Para **SIMCE**: `Mes` o `N Prueba`.

   El botón "Generar v2" queda **deshabilitado** hasta que apliques uno
   de estos filtros. Esto es a propósito: el motor está pensado para un
   solo punto en el tiempo. Sin filtro mezclaría 5 evaluaciones del año
   y los gráficos saldrían sucios.

4. Click en **"Generar v2 (DIA)"** o **"Generar v2 (SIMCE)"** (botón
   outlined indigo, junto al "Generar Reporte" v1).
5. Toast "Generando informe v2…" mientras el backend procesa.
6. El PDF se descarga automáticamente como `informe_dia.pdf` o
   `informe_simce.pdf`.

Tiempo típico: 20-30 segundos para SIMCE (4 cursos), 40-60 segundos
para DIA (21 cursos × tablas dinámicas).

## Qué contiene cada informe

### DIA

1. Cuadro Resumen de Logro por Curso
2. Logro Promedio por Nivel (barras simples Set2)
3. Logro Promedio por Curso (barras simples Set2)
4. Distribución de Rendimiento por Curso (boxplot tab10)
5. Logro Promedio por Eje Temático (barras agrupadas por curso × eje)
6. Logro Promedio por Habilidad (barras agrupadas por curso × habilidad)
7. Cantidad de Alumnos por Nivel de Logro (stacked semáforo
   verde-naranja-rojo)
8. **Por cada curso (página nueva)**:
   - Tabla detalle de Logro por Alumno
   - Tabla detalle de Logro por Pregunta

### SIMCE

1. Resumen de Logro por Curso (tabla agregada, formato %)
2. Resumen de Puntaje SIMCE por Curso (tabla agregada, número entero)
3. Rendimiento Promedio por Curso (barras simples Set2)
4. Distribución de Puntaje SIMCE por Curso (boxplot tab10)
5. Evolución del Logro Promedio por Curso y Mes (barras agrupadas)
6. Evolución del Puntaje SIMCE Promedio por Curso y Mes
7. Cantidad de Alumnos por Nivel de Logro (stacked semáforo
   Adecuado-Elemental-Insuficiente)
8. Logro Promedio por Habilidad (barras agrupadas curso × habilidad)
9. Logro Promedio por Eje Temático (idem por curso × eje)
10. Estadística por Pregunta del Establecimiento (página propia,
    A/%A/B/%B/.../E/%E + Correcta + Distractor)
11. **Por cada curso (página nueva)**:
    - Tabla detalle de Logro por Alumno (con SIMCE)
    - Tabla detalle de Logro por Pregunta

## Limitaciones conocidas

- **Sólo DIA y SIMCE**. IDEL/Cálculo Veloz/Fluidez Lectora todavía no
  tienen esquema en el motor v2.
- **Branding 3 líneas del header** se setea en el esquema JSON
  (`backend/rgenerator/reports/{tipo}/esquema.json`). En el próximo
  iter habrá un modal en la UI para editarlo antes de descargar.
- **Filtros multi-nivel** (ej "Mes IN [OCTUBRE, NOVIEMBRE]"): pendiente.
  Hoy filtra solo por igualdad simple.
- **Cálculo de avance del estudiante** (regresión lineal entre pruebas
  del año, columna "Avance"): pendiente — la columna existe en el
  esquema LaTeX original pero el cálculo no está portado al motor v2.
- **Logos por organización** (custom): hoy se usan los logos PHP
  oficiales committeados en `backend/rgenerator/reports/assets/`.
  Para clientes adicionales, agregar el PNG ahí y referenciarlo en el
  esquema correspondiente.

## Para desarrolladores

- Agregar un gráfico nuevo: implementarlo en
  `backend/rgenerator/reports/charts.py` y registrarlo en
  `CHART_REGISTRY` con `display_name`, `description`,
  `required_params`. Después referenciarlo desde el `esquema.json`
  del informe.
- Agregar un informe nuevo: crear subdirectorio
  `backend/rgenerator/reports/{tipo}/` con `__init__.py`,
  `esquema.json` (declarativo) y `crear_informe.py` (adapta los
  DataFrames). Luego registrar `tipo` en
  `backend/routers/reports.py` (función `generar_reporte`).
- Endpoint de introspección: `GET /api/reports/charts` y
  `GET /api/reports/tablas` exponen los registries para el frontend.
- Smoke test sin DB: `python scripts/_smoke_test_engine_v2.py`
  (genera DIA y SIMCE con dummy data en `data/output/`).

Ver detalles arquitectónicos en `memory/project_pdf_engine_v2.md`.
