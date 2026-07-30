# Inventario de indicadores — Fundación PHP (org_id = 1)

Fecha de extracción: 2026-07-30. Rama `dev2` (HEAD `0a6e7a0`). Fuente: DB `rgenerator_dev` del compose de desarrollo (`docker-compose.dev.yml`, servicio `db`), backend local en `:8001`, y lectura directa de `backend/rgenerator/reports/*`. Todos los datos de esta ficha fueron verificados contra la base de datos o la API en el momento de escribir este documento — no contra memoria ni documentación previa.

Organización: `organizations.id = 1` → **Fundación PHP**. La org 6 (Colegio Demo) queda fuera de alcance.

---

## 1. Matriz resumen

| Indicador | engine_type | Pipeline(s) asociado(s) | Métricas de carga (rol · filas) | Tabs dashboard | Gráficos/tablas | Informes disponibles hoy |
|---|---|---|---|---|---|---|
| **1 · SIMCE** | `simce` (campo) | SIMCE (IA) — id 14 | 4 · Resultados SIMCE por Estudiante (estudiantes · 1286); 5 · Resultados SIMCE por Pregunta (preguntas · 1680) | 4 | 15 (10 gráf. + 5 tablas) | 4/4 períodos + 1 custom (SIMCE oficial) = 5/5 |
| **2 · DIA** | `dia` (campo) | DIA (IA) — id 21 | 6 · Resultados DIA por estudiante (estudiantes · 5647); 7 · Resultados DIA por Pregunta (preguntas · 2386) | 5 | 19 (13 gráf. + 6 tablas) | 4/4 períodos + 1 custom (DIA oficial) = 5/5 |
| **3 · IDEL** | `pdl_idel` (inferido por nombre) | — sin pipeline | 8 · Resultados IDEL (estudiantes · 3890) | 3 | 9 (7 gráf. + 2 tablas) | 4/4 períodos + 1 custom (PDL IDEL-Woodcock) = 5/5 |
| **4 · Cálculo Veloz** | *(vacío, no infiere)* | — sin pipeline | 9 · Resultados Cálculo Veloz (estudiantes · 5151) | 4 | 18 (13 gráf. + 5 tablas) | 2/4 períodos (falla semestral y anual, sin datos 2026) + 0 custom = 2/5 |
| **5 · Fluidez Lectora** | *(vacío, no infiere)* | — sin pipeline | 10 · Resultados Fluidez Lectora (estudiantes · 414) | 4 | 14 (10 gráf. + 4 tablas) | 2/4 períodos (falla semestral y anual, sin dimensión Año) + 0 custom = 2/5 |
| **6 · SIMCE Panguipulli** | `simce_panguipulli` (inferido por nombre) | EMN Aptus (IA) — id 26 | 24 · Resultados SIMCE Panguipulli por Estudiante (estudiantes · 1695); 26 · Resultados SIMCE Panguipulli por Habilidad (otro/habilidad · 180) | 4 | 10 (7 gráf. + 3 tablas) | 0/4 períodos (pdf_layout vacío) + 1 custom (SIMCE Panguipulli oficial) = 1/5 |

Notas de la matriz:
- "Informes disponibles hoy" cuenta las 4 cards de período (`GET /api/indicators/{id}/report-options`, grupo `periodo`) más las cards de `especializados` (informes custom hardcodeados).
- El pipeline **EMN Aptus (IA)** (id 26) también escribe una tercera métrica, **25 · Resultados EMN Aptus por OA** (921 filas), que **no está vinculada a ningún indicador** de la org 1 — ver ficha del indicador 6 y observaciones generales.

---

## 2. Fichas por indicador

### 2.1 · Indicador 1 — SIMCE (`id_indicator=1`)

**Datos**

| Métrica | Dimensiones asociadas (`metric_dimensions`) | Filas por año |
|---|---|---|
| 4 · Resultados SIMCE por Estudiante | Establecimiento, Año, Curso, RUT, Nombre, Asignatura, Mes, N Prueba | 2025: 1090 · 2026: 196 |
| 5 · Resultados SIMCE por Pregunta | Establecimiento, Año, Curso, Asignatura, Mes, N Prueba, Pregunta, Habilidad, Eje Temático | 2025: 1420 · 2026: 260 |

Establecimiento único: **Pullinque**. `dimensions_json` de la métrica 4 incluye además la clave `22` (Nombre_Norm) en cada fila, pero esa dimensión **no está declarada** en `metric_dimensions` para la métrica 4 (sí lo está para la 6, DIA) — es un campo generado por `EnrichWithLookup` que viaja en los datos sin estar catalogado.

**Carga**: pipeline **SIMCE (IA)** (`pipeline_id=14`, 16 steps). Los `SaveToMetric` del config son `{"metric_id": 4, "input_key": "estudiantes"}` y `{"metric_id": 5, "input_key": "preguntas"}`. `created_via` en `metric_data`: mezcla real de `import_csv` (1090+1420 filas) y `pipeline` (196+260 filas) — la carga histórica fue por importación CSV directa y solo las corridas recientes (2026) pasaron por el pipeline.

**Dashboard** (4 tabs, `dashboard_layout.tabs`):
- **Vista General**: KPIs (inline) · tabla *Resumen por Curso* (spec 17, métrica 4, agrupada por Curso) · gráfico barras *Rendimiento por Curso* (spec 106) · boxplot *Distribución por Curso* (spec 107) · torta *Composición Global* (spec 108, sobre `Logro`) · barras apiladas *Niveles por Curso* (spec 109).
- **Por Curso**: selector de curso · barras agrupadas *Logro por Habilidad* (spec 22, métrica 5) · barras agrupadas *Logro por Eje* (spec 23) · heatmap *Curso × Eje* (spec 111) · tabla *Logro por Pregunta* (spec 13) · tabla *Estadística por Pregunta* (spec 14) · tabla *Estudiantes en Riesgo* (spec 105, métrica 4).
- **Por Estudiante**: selector de curso · tabla *Logro por Alumno* (spec 12, métrica 4).
- **Tendencia**: 3 gráficos de barras agrupadas por Mes (specs 138, 139, 140), sobre métrica 4.

**Informes**: `report-options` → 4/4 cards de período disponibles (última: MAYO 2026 prueba 1; semestral 1er sem. 2026; anual 2026; personalizado). Todas exigen elegir **Asignatura** (Lenguaje/Matemáticas, 2 valores). `pdf_layout`: 4 secciones (1 tabla + 3 gráficos). `pdf_layout_historico`: 3 secciones (3 gráficos). Custom aplicable: `custom_simce` → *"Informe de evaluación SIMCE (formato oficial)"* (`backend/rgenerator/reports/custom/simce.py`), disponible, requiere filtro temporal `Mes`/`N Prueba`/`Numero_Prueba` y asignatura.

**Observaciones**:
- Dato reciente y activo: ya hay 196/260 filas de 2026 cargadas vía pipeline, sobre una base histórica de import CSV.
- Un solo establecimiento (Pullinque) — el filtro de Establecimiento no aporta nada en este indicador.
- Clave `Nombre_Norm` presente en los datos pero no catalogada como dimensión de la métrica 4 (sí en la 6/DIA) — inconsistencia menor de catálogo.

---

### 2.2 · Indicador 2 — DIA (`id_indicator=2`)

**Datos**

| Métrica | Dimensiones asociadas | Filas por año |
|---|---|---|
| 6 · Resultados DIA por estudiante | Establecimiento, Año, Curso, Nombre, Asignatura, Habilidad, Hito, Nivel, Nombre_Norm | 2025: 4712 · 2026: 935 |
| 7 · Resultados DIA por Pregunta | Establecimiento, Año, Curso, Asignatura, Habilidad, Eje Temático, Hito, Nivel, N Pregunta, N OA, Indicador | 2025: 1320 · 2026: 1066 |

Es el único indicador con **2 establecimientos**: Liceo PHP Panguipulli y Liceo PHP Pullinque. 24 cursos, 3 hitos (DIAGNOSTICO/INTERMEDIO/CIERRE), 427 valores distintos de "Indicador" (OA), 921 valores de Nombre_Norm.

**Carga**: pipeline **DIA (IA)** (`pipeline_id=21`, 11 steps, incluye `RunDIAPDFExtraction`). `SaveToMetric`: `{"metric_id": 6, "input_key": "estudiantes_derived"}`, `{"metric_id": 7, "input_key": "preguntas_derived"}`. `created_via`: `import_csv` (4913+1963) y `pipeline` (734+423) — igual patrón que SIMCE, histórico importado + corridas recientes por pipeline.

**Dashboard** (5 tabs — el único indicador con 5):
- **Vista General**: KPIs · tabla *Resumen por Curso* (spec 18) · barras *Logro por Nivel* (spec 26) · barras *Logro por Curso* (spec 25) · boxplot *Distribución por Curso* (spec 27) · barras apiladas *Niveles de Logro por Curso* (spec 28).
- **Por Curso**: selector · barras agrupadas *Logro por Eje Temático* (spec 29, métrica 7) · barras agrupadas *Logro por Habilidad* (spec 30) · heatmap *Curso × Eje* (spec 99) · tabla *Logro por Pregunta* (spec 16) · tabla *Estudiantes en Riesgo* (spec 96, métrica 6).
- **Por Estudiante**: selector · tabla *Logro por Alumno* (spec 15).
- **Tendencia**: línea *Tendencia por Hito* (spec 98) · tabla *Comparativa entre Hitos* (spec 95, agrupada por Curso+Hito).
- **Comparativa Establecimientos** (única en todo el catálogo): 4 gráficos de barras agrupadas Curso×Establecimiento por hito (specs 100, 102, 103, 104) · línea *Tendencia por Establecimiento* (spec 101) · tabla *Brecha entre Establecimientos* (spec 97).

**Informes**: 4/4 cards de período disponibles (última: DIAGNOSTICO 2026; semestral/anual 2026). Exigen Asignatura (LECTURA/MATEMATICA). `pdf_layout`: 5 secciones (1 tabla + 4 gráficos) — el más extenso. `pdf_layout_historico`: 2 secciones. Custom: `custom_dia` → *"Informe de evaluación DIA (formato oficial)"*, disponible, filtro temporal `Hito`/`Año`.

**Observaciones**:
- Único indicador con tab "Comparativa Establecimientos" — refleja que es el único con >1 establecimiento cargado; el resto del dashboard es prácticamente idéntico en estructura al de SIMCE (mismo patrón de tabs general/curso/estudiante/tendencia).
- 5647+2386 filas es, junto a Cálculo Veloz, el mayor volumen de datos de la org.

---

### 2.3 · Indicador 3 — IDEL (`id_indicator=3`)

**Datos**

| Métrica | Dimensiones asociadas | Filas por año |
|---|---|---|
| 8 · Resultados IDEL | Establecimiento, Año, Curso, RUT, Nombre, Evaluación, Versión | 2024: 845 · 2025: 2269 · 2026: 776 |

Único indicador con **3 años** de historia (2024-2026). 1 establecimiento (Panguipulli), 6 cursos (1° a 6° básico), 6 subpruebas (`Evaluación`: CT/FLO/FNL/FSF/ILP/VSD — ver glosario del proyecto), 3 versiones (v1/v2/v3).

**Carga**: **sin pipeline** en la org 1 — ningún `pipelines.config_json` tiene un `SaveToMetric` con `metric_id=8`. `created_via` es NULL en el 100% de las 3890 filas, y todas se insertaron en una única ráfaga (`min(created_at) = max(created_at)` prácticamente, 2026-05-03 20:48:48, ventana <1s) — consistente con una carga masiva por script (`carril_b`/oneshot), no con el flujo interactivo de pipeline ni con el importador CSV estándar (que sí deja `created_via='import_csv'`).

**Dashboard** (3 tabs, el más compacto):
- **Vista General**: KPIs · torta *Composición Global* (spec 117, sobre Nivel de Riesgo) · barras apiladas *Niveles por Curso* (spec 118) · heatmap *Mapa de Riesgo Curso × Subprueba* (spec 143, `y_field=es_riesgo`).
- **Por Curso**: selector de curso + selector de subprueba (campo `_habilidad`) · matriz pivote *Roster — Niveles por Estudiante × Subprueba × Versión* (spec 144) · tabla *Listado de Estudiantes* (spec 113) · tabla *Estudiantes en Riesgo Persistente* (spec 145).
- **Tendencia**: nota informativa sobre protocolo (5°/6° básico no rinden v3) · barras apiladas *Niveles de Riesgo por Versión* (spec 141) · gráfico `stacked_grouped_bar` *Niveles por Curso y Versión* (spec 142, réplica pág. 2 del informe oficial) · nota tip sobre cómo leer la matriz de transición · selector de subprueba · heatmap *Matriz de Transición Nivel inicial → final* (spec 147, `agg=nunique`).

**Informes**: 4/4 cards de período disponibles (última: v3 2026; sin campo Asignatura — IDEL no tiene esa dimensión). `pdf_layout`: 4 secciones (1 tabla + 3 gráficos). `pdf_layout_historico`: 2 secciones. Custom: `custom_pdl_idel` → *"Informe PDL IDEL-Woodcock"* (`backend/rgenerator/reports/custom/pdl_idel.py`), disponible, sin filtro temporal obligatorio.

**Observaciones**:
- Es el único indicador de la org con datos de 3 años distintos y con carga 100% vía script masivo (sin pipeline ni CSV UI) — un "motor único de informes" deberá poder generar el histórico sin depender de que exista un pipeline configurado.
- El dashboard usa 2 tipos de componente inline que no aparecen en ningún otro indicador: `subprueba_selector` y notas explicativas de protocolo (`note`), ambas específicas del dominio IDEL.

---

### 2.4 · Indicador 4 — Cálculo Veloz (`id_indicator=4`)

**Datos**

| Métrica | Dimensiones asociadas | Filas por año |
|---|---|---|
| 9 · Resultados Cálculo Veloz | Establecimiento, Año, Curso, RUT, Nombre, Mes, N Prueba, Fecha | 2025: 5151 (único año) |

1 establecimiento (Pullinque), 17 cursos (incluye enseñanza media: "III°A", "II°B", etc.), 2 valores de N Prueba (protocolo: 2 pruebas por mes). **La dimensión RUT está declarada pero el 100% de las 5151 filas tienen el campo vacío** (`dimensions_json->>'6' = ''` en las 5151 filas) — hueco de cobertura confirmado en DB, no solo en el catálogo.

**Carga**: **sin pipeline**. `created_via` NULL en el 100% de las filas; inserción en ráfaga única el 2026-03-23 07:00:58 (ventana <1s) — mismo patrón de carga masiva por script que IDEL.

**Dashboard** (4 tabs, el catálogo más rico en notas explicativas — 3 notes):
- **Vista General**: KPIs · tabla *Resumen Anual por Curso* (spec 153) · torta *Composición Global* (spec 157) · barras apiladas *Niveles por Curso* (spec 158) · barras *Nota Promedio por Curso* (spec 159).
- **Última Evaluación**: nota tip (vista fijada a Mes=OCTUBRE, N°Prueba=2) · nota info (cobertura parcial por curso es normal) · 4 gráficos (composición, niveles, nota, distribución de puntaje — specs 160-163) · tabla *Listado Completo* (spec 155) · tabla *Estudiantes en Riesgo INICIAL/BÁSICO* (spec 156).
- **Evolución Mensual**: nota warn (cambio de dificultad entre MAYO y JUNIO-JULIO no es retroceso real) · tabla *Resumen Mensual* (spec 154) · 4 gráficos de evolución mensual (specs 164-167).
- **Por Curso**: selector · boxplot e histograma de puntaje filtrables (specs 168, 127) · tabla *Listado de Estudiantes (todas las evaluaciones)* (spec 121).

**Informes**: solo **2/4** cards de período disponibles. *Última prueba* (OCTUBRE 2025, prueba 2) y *Personalizado* sí; **Semestral y Anual fallan** con motivo *"Sin datos del 1er semestre/año en curso (2026) para este indicador"* — la totalidad de los datos es de 2025 y hoy (2026-07-30) el año en curso es 2026. Sin Asignatura (no aplica). `pdf_layout`: 4 secciones (1 tabla + 3 gráficos). `pdf_layout_historico`: 3 secciones. **Sin informe custom** — `engine_type` no está seteado en `report_engine_type` y el nombre "Cálculo Veloz" no matchea ninguna heurística de `inferir_engine_type` (solo reconoce "panguipulli", "simce", "dia", "idel"/"pdl"); no existe módulo en `backend/rgenerator/reports/custom/` para este indicador.

**Observaciones**:
- **Todo el dato es de 2025**; los informes semestral/anual quedan inutilizables hasta que se cargue 2026, aunque el indicador esté activo y con dashboard rico.
- RUT declarado como dimensión pero 100% vacío — no se puede usar para identificar estudiantes unívocamente, solo Nombre.
- Es el indicador con más notas de UX en el dashboard (protocolo de 2 pruebas/mes, cambio de escala de dificultad) — señal de que el equipo tuvo que compensar con texto explicativo la complejidad del instrumento.
- Sin informe "formato oficial" — actualmente solo dashboard + PDF genérico por período.

---

### 2.5 · Indicador 5 — Fluidez Lectora (`id_indicator=5`)

**Datos**

| Métrica | Dimensiones asociadas | Filas |
|---|---|---|
| 10 · Resultados Fluidez Lectora | Establecimiento, Curso, RUT, Nombre, N Prueba, Fecha, Seguimiento, Calidad lectora | 2026 (por `Fecha`): 414 |

**No tiene dimensión "Año"** (única entre los 6 indicadores) — el período solo puede derivarse de `Fecha`. Único N Prueba: "Ensayo 1". 1 establecimiento (PHP Panguipulli), 12 cursos, RUT completo (412/412), 2 valores de Seguimiento (Normal/Intensivo), 6 categorías de Calidad Lectora (Fluida → No Lector).

**Carga**: **sin pipeline**. `created_via` NULL en el 100% de las 414 filas, ráfaga única 2026-05-04 04:22:19 (<1s) — mismo patrón de carga masiva por script que IDEL y Cálculo Veloz.

**Dashboard** (4 tabs):
- **Vista General**: KPIs · tabla *Resumen por Curso* (spec 129) · barras *PPM por Curso* (spec 131) · boxplot *Distribución por Curso* (spec 132) · torta *Composición Global* (spec 133, categoría) · barras apiladas *Categoría por Curso* (spec 134).
- **Por Curso**: selector · boxplot filtrable (spec 132, reutilizado) · tabla *Listado de Estudiantes* (spec 130).
- **Calidad Lectora**: nota info explicando la escala cualitativa · torta y barras apiladas por Calidad Lectora (specs 150, 135) · 2 heatmaps Curso×Calidad y Categoría×Calidad (specs 151, 136).
- **Refuerzo / Riesgo**: nota warn sobre población prioritaria · torta *Estudiantes por Seguimiento* (spec 152) · tabla *Seguimiento Intensivo* (spec 148) · tabla *Lectores Iniciales* (spec 149).

**Informes**: solo **2/4** disponibles. *Última prueba* (09-04-2026, Ensayo 1) y *Personalizado* sí; **Semestral y Anual fallan** con motivo *"No se detectó una dimensión de año en los datos de este indicador"* — distinto motivo que Cálculo Veloz (aquí es estructural: no hay columna Año, no solo falta el dato del año en curso). `pdf_layout`: 5 secciones (1 tabla + 4 gráficos) — el más extenso junto a DIA. `pdf_layout_historico`: 2 secciones. **Sin informe custom** — mismo motivo que Cálculo Veloz (no matchea heurística de `engine_type`, no hay módulo en `reports/custom/`).

**Observaciones**:
- Es el indicador con menos filas de la org (414) y el único cuya lógica de período depende de `Fecha` en vez de `Año` — cualquier refactor de "motor único" deberá decidir si esta dimensión se homologa a Año o si el motor soporta ambos esquemas.
- Comparte con Cálculo Veloz la falta de informe oficial custom y el mismo patrón de carga (script masivo, sin pipeline).
- El campo `Curso` mezcla notación básica ("7°", "8°") con notación de media ("I A"…"I D") en el mismo indicador.

---

### 2.6 · Indicador 6 — SIMCE Panguipulli (`id_indicator=6`)

**Datos**

| Métrica | Dimensiones asociadas | Filas por año |
|---|---|---|
| 24 · Resultados SIMCE Panguipulli por Estudiante | Establecimiento, Año, Curso, RUT, Nombre, Asignatura, Mes, N Prueba, Nivel | 2025: 1695 (único año) |
| 26 · Resultados SIMCE Panguipulli por Habilidad | Establecimiento, Año, Curso, Asignatura, Mes, N Prueba, Habilidad, Nivel | 2025: 180 (único año) |

1 establecimiento (Panguipulli), 7 cursos (mezcla básica/media: "4° básico A"…"II° medio D"), 3 asignaturas (HISTORIA/LENGUAJE/MATEMATICA — único indicador con 3, el resto tiene 2 o 0).

**Carga**: pipeline **EMN Aptus (IA)** (`pipeline_id=26`, 19 steps, 3 `SaveToMetric`: `{"metric_id": 24, "input_key": "estudiantes"}`, `{"metric_id": 25, "input_key": "oa"}`, `{"metric_id": 26, "input_key": "habilidad"}`). **El pipeline escribe una tercera métrica (25 · Resultados EMN Aptus por OA, 921 filas) que no está enlazada a este indicador ni a ningún otro** de la org — dato huérfano generado por el mismo pipeline pero invisible en cualquier dashboard. `created_via` NULL en el 100% de las filas de 24 y 26, insertadas en ráfaga única el 2026-05-04 14:24:16 (mismo minuto/segundo que la métrica huérfana 25) — parece una corrida de backfill/migración más que una ejecución interactiva normal del pipeline (que sí debería dejar `created_via='pipeline'`, como ocurre con SIMCE/DIA).

**Dashboard** (4 tabs):
- **Vista General**: **sin card de KPIs** (único indicador sin ella) · tabla *Resumen por Curso* (spec 170, métrica 24) · barras *Rendimiento por Curso* (spec 173, `y_field=PorcLogro`) · boxplot *Distribución por Curso* (spec 174) · torta *Composición Global* (spec 175, `Nivel_Logro`) · barras apiladas *Niveles por Curso* (spec 176).
- **Por Curso**: selector · barras agrupadas *Logro por Habilidad* (spec 171, métrica 26) · tabla *Estudiantes en Riesgo* (spec 172, métrica 24).
- **Por Estudiante**: selector · tabla *Logro por Alumno* (spec 169).
- **Tendencia**: 2 gráficos de evolución por Curso/Mes (specs 177, 178).

Estructuralmente es casi un clon del dashboard de SIMCE (mismos 4 tabs, mismos tipos de componente), salvo por la ausencia de KPIs y el uso de nombres de campo distintos (`PorcLogro`/`Nivel_Logro` en vez de `Rend`/`Logro`).

**Informes**: **0/4** cards de período disponibles — `pdf_layout` y `pdf_layout_historico` están **vacíos** (`{}`, sin clave `sections`); las 4 cards devuelven el motivo *"Este informe aún no está configurado — pide a tu administrador que agregue secciones en Editor de Layout → Informe PDF..."* pese a que sí hay datos suficientes (la descripción resuelta muestra "SEPTIEMBRE 2025, prueba 4" como último dato real). Exige Asignatura (3 valores). Sí tiene disponible el custom: `custom_simce_panguipulli` → *"Informe de evaluación SIMCE Panguipulli (formato oficial)"* (`backend/rgenerator/reports/custom/simce_panguipulli.py`), que no depende de `pdf_layout` y por eso funciona igual.

**Observaciones**:
- Único indicador **sin ningún informe PDF genérico disponible** — el layout está configurado en 0 (vacío), no es un problema de datos. Sí puede generar el informe "formato oficial" porque ese motor no lee `pdf_layout`.
- Único indicador con datos huérfanos confirmados: el pipeline que lo alimenta también puebla la métrica 25 (EMN Aptus por OA, 921 filas) que no cuelga de ningún indicador — ni de este ni de otro en la org.
- Único dashboard sin card de KPIs en "Vista General" — inconsistencia de plantilla frente a los otros 5 indicadores.
- Todo el dato es de 2025 (igual que Cálculo Veloz) — informes anuales/semestrales de 2026 fallarían igual que en Cálculo Veloz si el layout existiera.

---

## 3. Cobertura de informes por período

Fuente: `GET /api/indicators/{id}/report-options`, grupo `periodo` (cards *Última prueba / Semestral / Anual*) y grupo `especializados` (card *Formato oficial*).

| Indicador | Última prueba | Semestral | Anual | Formato oficial (custom) |
|---|---|---|---|---|
| 1 · SIMCE | ✓ | ✓ | ✓ | ✓ `custom_simce` |
| 2 · DIA | ✓ | ✓ | ✓ | ✓ `custom_dia` |
| 3 · IDEL | ✓ | ✓ | ✓ | ✓ `custom_pdl_idel` |
| 4 · Cálculo Veloz | ✓ | ✗ sin datos del 1er semestre 2026 | ✗ sin datos del año en curso (2026) | ✗ no existe módulo custom para este indicador |
| 5 · Fluidez Lectora | ✓ | ✗ no hay dimensión Año en los datos | ✗ no hay dimensión Año en los datos | ✗ no existe módulo custom para este indicador |
| 6 · SIMCE Panguipulli | ✗ `pdf_layout` sin secciones | ✗ `pdf_layout_historico` sin secciones | ✗ `pdf_layout_historico` sin secciones | ✓ `custom_simce_panguipulli` |

---

## Apéndice — metodología de verificación

- **Indicadores / pipelines / metrics / dimensions / metric_dimensions / specs**: `docker compose -f docker-compose.dev.yml exec -T db psql -U mgodoy -d rgenerator_dev` contra `rgenerator_dev`, filtrando `org_id=1` en cada tabla.
- **Conteos por año**: `dimensions_json::jsonb->>'4'` (id de dimensión "Año") agrupado por metric, salvo Fluidez Lectora (sin dimensión Año, se usó `Fecha`, id 21).
- **`created_via` / origen de carga**: `GROUP BY id_metric, created_via` sobre `metric_data`, más `min/max(created_at)` para distinguir ráfagas de backfill vs. inserciones distribuidas en el tiempo.
- **`SaveToMetric` → métrica**: parseo de `pipelines.config_json` (JSON con array `pipeline` de `{step, params}`) buscando `step == "SaveToMetric"` y extrayendo `params.metric_id` / `params.input_key`.
- **Dashboard**: parseo de `indicators.dashboard_layout` (`{"tabs": [{"id","label","rows":[{"cols","items":[...]}]}]}`), resolviendo cada `configured_chart`/`configured_table` contra `specs.charts_list` / `specs.tables_list` (primer elemento de cada array) para obtener `chart_type`, `metric_id` y `mapping`/`columns`.
- **Informes**: llamada real `GET /api/indicators/{id}/report-options` con JWT de org 1 (rol admin) generado ad-hoc contra el backend en `:8001`; token y script temporal (`data/tmp/_gen_token.py`) fueron borrados al terminar.
- Ningún dato de esta ficha proviene de `memory/*.md` ni de conversaciones previas — todo fue reconsultado en esta sesión.
