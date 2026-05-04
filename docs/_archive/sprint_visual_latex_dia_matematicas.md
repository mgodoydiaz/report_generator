# Sprint visual LaTeX paridad — DIA Matemáticas (notas Bloque 1)

Fecha: 2026-05-03
Caso piloto: **Indicator id=2 (DIA Diagnóstico Matemáticas)**

## Estado del PDF DIA actual (lo que `RenderPDFReport` produce hoy)

Layout actual seedeado por [`scripts/_seed_validation_layouts.py:106-133`](../../scripts/_seed_validation_layouts.py) (función `dia_evaluacion()`):

| # | Tipo | Heading | Componente | Notas |
|---|---|---|---|---|
| 1 | Tabla | Cuadro Resumen Logro por Curso | `SummaryTable` | `valueField=_logro_1`, `groupField=_curso`, `comparePrevious=True`, `periodField=_hito` |
| 2 | Gráfico | Logro Promedio por Curso | `BarByGroup` | barras simples, `showValues=True` |
| 3 | Gráfico | Cantidad de Alumnos por Nivel de Logro | `StackedCountByGroup` | apiladas, `levelField=_nivel_de_logro` |
| 4 | Gráfico | Logro Promedio por Eje Temático | `BarByGroup` | groupField=`_eje_tematico` |
| 5 | Gráfico | Logro Promedio por Habilidad | `BarByGroup` | groupField=`_habilidad` |

(El layout histórico añade 2 gráficos `GroupedBarByPeriod` + `StackedCountByGroup` por hito.)

## Estética actual (qué hay que cambiar)

Paleta hardcoded en [`backend/rgenerator/core/report_steps.py:322-654`](../../backend/rgenerator/core/report_steps.py) y [`backend/rgenerator/templates/report_base.html`](../../backend/rgenerator/templates/report_base.html):

**HTML/CSS** (`report_base.html`):
- `@page size: A4` (LaTeX usa letter)
- Márgenes `3cm 2.2cm 2.2cm 2.2cm` (LaTeX usa `3.5cm 2.5cm 2cm 2.5cm`)
- Fuente `DejaVu Sans` 10pt (LaTeX usa Segoe UI 11pt)
- `h2 color: #4f46e5` morado con `border-bottom: 2px solid #e0e7ff` (LaTeX h3 negro bold sin borde)
- `.cover` con gradientes `#4f46e5 → #06b6d4` (LaTeX no tiene portada)
- `table th { background: #4f46e5; color: white }` (LaTeX usa fondo blanco, header bold negro, bordes 0.5pt sólidos)
- `tr:nth-child(even)` con zebra (LaTeX no tiene zebra)
- Header running con 3 cajas separadas `@top-left/@top-center/@top-right` (LaTeX y `report_latex_paridad.html` usan una sola caja con regla 0.4pt continua)

**Matplotlib** (`_chart_to_png_b64`):
- Paleta indigo/cyan `#6366f1, #8b5cf6, #06b6d4, #f59e0b, #10b981, #f43f5e, #3b82f6, #a855f7` (LaTeX usa `Set2`)
- Default semáforo `#dc2626, #ea580c, #eab308, #16a34a, ...` (LaTeX usa `#1f9e89, #f1a340, #e64b35`)
- `edgecolor='white' linewidth=0.5-0.6` en barras (LaTeX usa `edgecolor='black' linewidth=1.2-1.5`)
- `dpi=120` (LaTeX usa 300)
- `figsize=(7, 3.5)` (LaTeX usa `(8, 4)` o `(10, 6)` o `(12, 6)`)
- Grid `alpha=0.4` (LaTeX usa `alpha=0.6`)
- Gauge color `#4f46e5`, Histogram color `#6366f1` (LaTeX usa Set2[0] verde)

## Comparación con el LaTeX ideal (`docs/pdf_examples/Informe DIA Panguipulli Matemáticas Diagnóstico 2026.pdf`)

Equivalencia de gráficos del LaTeX referencia ([`docs/desarrollo/referencia_informe/DIA/funciones.py`](referencia_informe/DIA/funciones.py)) con el PDF actual:

| LaTeX `funciones.py` | Equivalente PDF actual | Estado |
|---|---|---|
| `resumen_por_curso` (tabla agg) | Sección 1 `SummaryTable` | OK estructural, falta paridad estética |
| `logro_promedio_por_curso` | Sección 2 `BarByGroup` _curso | OK estructural |
| `alumnos_por_nivel` (stacked bars) | Sección 3 `StackedCountByGroup` | OK estructural |
| `logro_promedio_por_eje` | Sección 4 `BarByGroup` _eje_tematico | OK estructural |
| `logro_promedio_por_habilidad` | Sección 5 `BarByGroup` _habilidad | OK estructural |
| `boxplot_logro_por_curso` | (no incluido en pdf_layout actual) | **Faltaría agregar si lo queremos en paridad** |
| `logro_promedio_por_nivel` | (no incluido) | Opcional — el LaTeX lo tiene como vista síntesis |

**Conclusión**: la **estructura** del PDF actual ya es compatible (5 secciones cubren las funciones LaTeX que más se usan). El gap está sólo en la **estética** — paleta, tipografía, márgenes, header/footer, bordes de tablas.

## Dashboard frontend `/results` (Indicator 2) — referencia secundaria

El dashboard `/results` (frontend, [`Results.jsx`](../../frontend/src/pages/Results.jsx) + [`dashboardRenderer.jsx`](../../frontend/src/tooling/dashboardRenderer.jsx)) muestra MUCHO MÁS que el PDF (KPIs, multiples tabs, selectores de curso, tablas detalle, etc.). Esto es esperable: el dashboard es interactivo, el PDF es un subset estático.

**Para este sprint NO se toca el dashboard frontend** — el foco es el PDF que sale del motor `RenderPDFReport`. La paleta indigo/cyan del frontend es una decisión separada (Tailwind theme) y no impacta el output de impresión.

## Plan de cambios estéticos para Bloque 3

Aplicar el "vocabulario visual LaTeX" (Bloque 2) a los 5 componentes que el PDF DIA usa hoy:

1. **SummaryTable** → bordes negros 0.5pt, header blanco/negro bold, sin zebra
2. **BarByGroup** (3 ocurrencias) → paleta `Set2`, edgecolor black 1.2pt, grid Y dashed alpha 0.6
3. **StackedCountByGroup** → paleta semáforo `#1f9e89/#f1a340/#e64b35` cuando level matchee niveles de logro

Y al template global:
- Letter, márgenes LaTeX, Segoe UI 11pt
- Header con regla 0.4pt continua
- Footer con regla 0.4pt
- Eliminar `.cover` y todo gradiente
- h2 negro bold sin border-bottom

## Decisiones tomadas (sin necesidad de levantar Docker)

- **NO se agregan gráficos adicionales** en este sprint (boxplot/logro_por_nivel del LaTeX) — primero paridad estética en lo que ya existe, después se evalúa.
- **NO se modifica el dashboard frontend** — fuera de scope.
- **NO se toca `_table_section`** salvo que el cambio de CSS no baste (las clases CSS del HTML deciden el estilo, los datos los aporta el backend).
- **NO se levanta el navegador para Bloque 1** — el análisis basado en código es suficiente y más determinista. La validación visual real ocurre en Bloque 4 con el PDF generado.

---

**Siguiente paso**: Bloque 2 → escribir `docs/desarrollo/visual_vocabulary_dia.md` consolidando paletas, tipografía, espaciados, headers y tablas extraídos del LaTeX referencia.

---

## Tabla de visto bueno por evaluación (Bloque 4)

Validación visual del PDF generado por `RenderPDFReport` para cada combinación `indicator × modo`. Estado al **2026-05-03** (post-refactor estética LaTeX).

Criterio de OK: el PDF "se ve de la misma familia" que el LaTeX referencia (header con regla 0.4pt, footer con regla, sin gradientes, paleta Set2/semáforo, tablas bordes negros, tipografía sans-serif neutra). NO se busca pixel-perfect.

| # | Indicator | Modo | PDF | Estética | Datos | Notas |
|---|---|---|---|---|---|---|
| 1 | DIA Matemáticas (id 2) | evaluación | `validation_dia_evaluacion.pdf` 554 KB | ✅ paridad LaTeX | ⚠ ver issues | header/footer/tablas/semáforo OK · issues: `0.8` vs `80%` (role_formats vacío) y "Eje Temático" vacío (cross-metric) |
| 2 | DIA Matemáticas (id 2) | histórico | `validation_dia_historico.pdf` 232 KB | ✅ paridad LaTeX | ⏳ pendiente revisión usuario | |
| 3 | SIMCE Lenguaje (id 1) | evaluación | `validation_simce_evaluacion.pdf` 205 KB | ✅ paridad LaTeX | ⏳ pendiente revisión usuario | filtro `Asignatura=LENGUAJE` aplicado |
| 4 | SIMCE Lenguaje (id 1) | histórico | `validation_simce_historico.pdf` 259 KB | ✅ paridad LaTeX | ⏳ pendiente revisión usuario | |
| 5 | IDEL / PDL (id 3) | evaluación | `validation_idel_evaluacion.pdf` 240 KB | ✅ paridad LaTeX | ⏳ pendiente revisión usuario | layout v2 con 8 subpruebas + KPIs riesgo |
| 6 | IDEL / PDL (id 3) | histórico | `validation_idel_historico.pdf` 179 KB | ✅ paridad LaTeX | ⏳ pendiente revisión usuario | |
| 7 | Cálculo Veloz (id 4) | evaluación | — | — | ⏸ skip | metric_data no cargada al 2026-05-01 |
| 8 | Cálculo Veloz (id 4) | histórico | — | — | ⏸ skip | |
| 9 | Fluidez Lectora (id 5) | evaluación | — | — | ⏸ skip | metric_data no cargada al 2026-05-01 |
| 10 | Fluidez Lectora (id 5) | histórico | — | — | ⏸ skip | |

### Issues fuera del scope visual (registrar para sprints futuros)

- **`role_formats` vacío en DIA (id 2)**: la columna `_logro_1` debería formatear como percent. El indicator tiene `role_formats = {}` en la DB. Fix: `UPDATE indicators SET role_formats = '{"_logro_1": "percent"}' WHERE id_indicator = 2;` (no se aplica en este sprint porque es modificación de datos no visual).
- **"Logro Promedio por Eje Temático" vacío en DIA**: el layout asume que `_logro_1` y `_eje_tematico` están en los mismos records. `_logro_1` viene de la métrica de estudiantes y `_eje_tematico` de preguntas — el join no se hace para esa combinación. Considerar usar `_logro` (de preguntas) como en SIMCE habilidades.
- **Fuente Inter/Segoe UI no instaladas en container**: matplotlib y WeasyPrint usan DejaVu Sans como fallback. Visualmente queda OK (sans-serif neutro), pero para paridad pixel-perfect agregar `apt-get install fonts-inter` al Dockerfile backend.

**Workflow**: por cada fila, generar el PDF, abrirlo, comparar con el LaTeX equivalente en `docs/pdf_examples/` (si existe), marcar OK/NOK aquí. Si NOK, listar el detalle visual a corregir y volver a Bloque 3 acotado.

Comando estándar (con Docker arriba):
```bash
docker exec -w /app -e DATABASE_URL="postgresql://mgodoy:holapocompadre977@db:5432/rgenerator_dev" \
  report_generator-backend-1 python scripts/_generate_validation_pdfs.py --indicators 1,2,3
```

(Cálculo Veloz e Fluidez Lectora se omiten hasta que se carguen sus métricas.)
