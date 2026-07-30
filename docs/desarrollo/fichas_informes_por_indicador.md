# Fichas de especificación por indicador — Fase 1 del motor único de informes

**Fecha**: 2026-07-30 · **Estado**: **FASE 1 CERRADA — decisiones de Miguel abajo**

> **Decisiones de Miguel (2026-07-30), pregunta por pregunta:**
> **SIMCE**: (1) detalle alumno/pregunta SOLO en última prueba; (2) riesgo persistente SÍ en el anual, al final, indicando curso y puntajes; (3) heatmap Curso×Eje excluido.
> **DIA**: (4) comparativa de establecimientos NO va en el PDF por colegio — gráfico aparte, en ROADMAP; (5) detalle por curso solo en última prueba; (6) heatmap excluido.
> **IDEL**: (7) son 3 pruebas anuales → card **semestral deshabilitada** para este indicador (con motivo explicativo); (8) roster iterado por curso — referencia de estilo entregada: `Desktop\PDF_test\referencias\referencia_idel_panguipulli_2025.pdf` (OJO: es del 2026-04-22, anterior a la corrección del glosario — vale para layout, NO para nombres de subpruebas: usar el glosario oficial de CLAUDE.md); (9) tabla resumen ad-hoc se mantiene — **el informe custom pdl_idel es la base del módulo IDEL**.
> **Cálculo Veloz**: (10) módulo custom nuevo; (11) riesgo persistente SÍ; (12) listado redundante descartado.
> **Fluidez Lectora**: (13) diseñar semestral/anual completos (degradan con gracia con 1 medición); (14) crear tab de Tendencia en el dashboard; (15) van AMBAS distribuciones (Categoría y Calidad Lectora).
> **Panguipulli**: (16) secciones de evolución se auto-omiten con un único punto temporal (regla general del motor); (17) sin Eje Temático confirmado — revisar más adelante; (18) sin datos 2026 aceptado.
> Criterio inicial de "riesgo persistente" (a calibrar en el piloto): nivel más bajo del indicador en las 2 últimas evaluaciones consecutivas. · **Fuentes**: [plan_motor_unico_informes.md](./plan_motor_unico_informes.md), [inventario_indicadores_2026-07-30.md](./inventario_indicadores_2026-07-30.md), [comparacion_simce_referencia_2026-07-30.md](../reportes/comparacion_simce_referencia_2026-07-30.md), `indicators.dashboard_layout` y `specs.charts_list/tables_list` (DB `rgenerator_dev`, verificado en esta sesión).

Cómo leer cada tabla de secciones: la columna "Fuente en el dashboard" cita el **tab** y el **título real** del gráfico/tabla tal como está en `dashboard_layout`/`specs` (con su `id_spec` entre paréntesis). Las columnas Última/Semestral/Anual usan ✓ (va tal cual), ✗ (no va, con motivo) o **variante** (misma fuente, pero con un cambio: columna de comparación, recorte temporal, u origen distinto dentro del mismo indicador). El criterio de inclusión es de **informe impreso** (inspirado en el formato oficial SIMCE: portada/resumen → gráficos generales → detalle por curso), no "todo lo que hay en el dashboard" — selectores interactivos, matrices que exigen dos filtros simultáneos y heatmaps redundantes con un gráfico de barras ya propuesto quedan fuera por defecto, y se explica por qué en cada caso.

Nota de nomenclatura: "última prueba" es el nombre genérico del modo `ultima_prueba` del plan, pero el nombre de la unidad temporal real cambia por indicador — "prueba" en SIMCE/Cálculo Veloz, "hito" en DIA, "versión" en IDEL, "evaluación" en Fluidez Lectora. Cada ficha usa el término real de su indicador en el encabezado de columna cuando corresponde. "Informes hoy" en cada cabecera resume la cobertura ya confirmada en el inventario (cards de período 0-4/4 más el custom "formato oficial" si existe) — es el punto de partida real sobre el que se construye la propuesta, no el objetivo final.

---

## 1 · SIMCE (`id_indicator=1`)

- **Familia**: A (estructura compartida con DIA y Panguipulli).
- **Estado de datos**: activo, con 196/260 filas de 2026 ya cargadas vía pipeline sobre una base histórica de import CSV; un solo establecimiento (Pullinque). Hay un defecto de datos conocido y ajeno a esta ficha (la carga 2026-MAYO no guardó la dimensión `Pregunta`, documentado en la comparación con la referencia) que no cambia qué secciones corresponden, solo qué tan pobladas salen hoy.
- **Informes hoy**: 4/4 cards de período + 1 custom (`custom_simce`, ya validado visualmente contra la referencia, ~58% de secciones idénticas).
- **Reuso disponible**: el motor `custom_simce` (`esquema.json`) ya implementa como secciones fijas el resumen por curso, logro por curso, niveles apilados, boxplot y logro por habilidad, más las secciones dinámicas de logro por alumno/pregunta por curso — la propuesta de esta ficha reordena y completa ese esquema, no parte de cero.

| Sección | Fuente en el dashboard | Última prueba | Semestral | Anual |
|---|---|---|---|---|
| Portada (título + subtítulo establecimiento) | branding, sin fuente en dashboard | ✓ | ✓ | ✓ |
| Resumen de Logro por Curso | tab Vista General → tabla *Resumen por Curso* (spec 17) | ✓ | variante (+ columna semestre anterior) | variante (+ columna año anterior) |
| Rendimiento por Curso | tab Vista General → gráfico *Rendimiento por Curso* (spec 106) | ✓ | ✓ | ✓ |
| Distribución de Rendimiento por Curso (boxplot) | tab Vista General → gráfico (spec 107) | ✓ | ✓ | ✓ |
| Composición Global por Nivel | tab Vista General → gráfico (spec 108) | ✓ | ✓ | ✓ |
| Niveles por Curso (barras apiladas) | tab Vista General → gráfico (spec 109) | ✓ | ✓ | ✓ |
| Logro por Habilidad | tab Por Curso → gráfico (spec 22), agregado sin filtro de curso | ✓ | ✓ | ✓ |
| Logro por Eje Temático | tab Por Curso → gráfico (spec 23), agregado sin filtro de curso | ✓ | ✓ | ✓ |
| Heatmap Curso × Eje Temático | tab Por Curso → gráfico (spec 111) | ✗ redundante con Eje Temático de barras | ✗ | ✗ |
| Estadística por Pregunta | tab Por Curso → tabla (spec 14) | ✓ | pregunta abierta (ver más abajo) | pregunta abierta |
| Logro por Alumno (por curso, paginado) | tab Por Estudiante → tabla (spec 12) | ✓ | pregunta abierta | pregunta abierta |
| Logro por Pregunta (por curso, paginado) | tab Por Curso → tabla (spec 13) | ✓ | pregunta abierta | pregunta abierta |
| Estudiantes en Riesgo | tab Por Curso → tabla (spec 105) | ✓ | variante (¿riesgo persistente?) | variante (¿riesgo persistente?) |
| Evolución de Logro/Puntaje/Niveles por Mes (3 gráficos) | tab Tendencia (specs 138, 139, 140) | ✗ no aplica (es foto de un momento) | ✓ | ✓ (pendiente el fix de eje multi-año del plan, fase 2) |

**Orden propuesto — Última prueba**: Portada → Resumen por Curso → Rendimiento por Curso → Distribución → Niveles por Curso → Composición Global → Logro por Habilidad → Logro por Eje Temático → Estadística por Pregunta → [por curso: Logro por Alumno, Logro por Pregunta, salto de página entre cursos].

**Orden propuesto — Semestral/Anual**: igual bloque de establecimiento (Resumen→...→Eje Temático) → los 3 gráficos de Tendencia → detalle por curso solo si Miguel confirma que corresponde (pregunta abierta 1).

**Preguntas abiertas**:
1. La Estadística por Pregunta y el detalle por Alumno/Pregunta por curso, ¿van también en semestral y anual (multiplicando páginas por cada prueba del período, ej. 3-4 pruebas × 4 cursos) o solo en última prueba, que es donde ya funcionan hoy?
2. ¿Se agrega una vista de "riesgo persistente" (multi-prueba) para el anual, análoga a la que ya existe en IDEL (spec 145), o el listado actual de una sola prueba (spec 105) basta también para el anual?
3. El heatmap Curso × Eje Temático (spec 111) no está en el informe oficial actual y se propone excluirlo por redundante — ¿confirma o lo quiere para algún modo igual?

---

## 2 · DIA (`id_indicator=2`)

- **Familia**: A.
- **Estado de datos**: el más voluminoso (5647+2386 filas), único con **2 establecimientos** (Pullinque y Panguipulli), 24 cursos, 3 hitos (DIAGNOSTICO/INTERMEDIO/CIERRE). Es el único con 5 tabs de dashboard (agrega *Comparativa Establecimientos*, que no existe en ningún otro indicador).
- **Informes hoy**: 4/4 cards de período + 1 custom (`custom_dia`, sin QA visual formal todavía, a diferencia de SIMCE).
- **Reuso disponible**: `custom_dia` ya calcula `Avance` y `Mejora_vs_Inicio` por estudiante entre hitos (vía `Nombre_Norm`, clave estable) y ya implementa resumen, logro por nivel/curso, boxplot, niveles apilados, eje temático, habilidad y las tablas dinámicas por curso — falta agregar las secciones de Tendencia y decidir la de Comparativa Establecimientos (preguntas abiertas 1-2).

| Sección | Fuente en el dashboard | Última prueba | Semestral | Anual |
|---|---|---|---|---|
| Portada | branding | ✓ | ✓ | ✓ |
| Resumen de Logro por Curso | tab Vista General → tabla (spec 18) | ✓ | variante | variante |
| Logro Promedio por Nivel | tab Vista General → gráfico (spec 26) | ✓ | ✓ | ✓ |
| Logro Promedio por Curso | tab Vista General → gráfico (spec 25) | ✓ | ✓ | ✓ |
| Distribución de Logro por Curso (boxplot) | tab Vista General → gráfico (spec 27) | ✓ | ✓ | ✓ |
| Niveles de Logro por Curso (apiladas) | tab Vista General → gráfico (spec 28) | ✓ | ✓ | ✓ |
| Logro por Eje Temático | tab Por Curso → gráfico (spec 29), agregado sin filtro | ✓ | ✓ | ✓ |
| Logro por Habilidad | tab Por Curso → gráfico (spec 30), agregado sin filtro | ✓ | ✓ | ✓ |
| Heatmap Curso × Eje Temático | tab Por Curso → gráfico (spec 99) | ✗ redundante con Eje Temático | ✗ | ✗ |
| Logro por Pregunta (por curso, paginado) | tab Por Curso → tabla (spec 16) | ✓ | pregunta abierta | pregunta abierta |
| Estudiantes en Riesgo | tab Por Curso → tabla (spec 96) | ✓ | variante | variante |
| Logro por Alumno (por curso, paginado) | tab Por Estudiante → tabla (spec 15) | ✓ | pregunta abierta | pregunta abierta |
| Tendencia por Hito (línea) | tab Tendencia → gráfico (spec 98) | ✗ no aplica | ✓ | ✓ |
| Comparativa entre Hitos | tab Tendencia → tabla (spec 95) | ✗ no aplica | ✓ | ✓ |
| Curso × Establecimiento por hito (4 gráficos) + Tendencia por Establecimiento + Brecha | tab Comparativa Establecimientos (specs 100, 102-104, 101, 97) | pregunta abierta (ver 1) | pregunta abierta | pregunta abierta |

**Orden propuesto — Última prueba**: Portada → Resumen por Curso → Logro por Nivel → Logro por Curso → Distribución → Niveles apilados → Eje Temático → Habilidad → [por curso: Logro por Pregunta, Logro por Alumno, salto de página].

**Orden propuesto — Semestral/Anual**: mismo bloque de establecimiento → Tendencia por Hito → Comparativa entre Hitos → (si aplica) bloque Comparativa Establecimientos → detalle por curso si corresponde.

**Preguntas abiertas**:
1. La tab *Comparativa Establecimientos* compara Pullinque vs. Panguipulli en el mismo gráfico — ¿el informe de un establecimiento debe mostrar también al otro colegio, o esa comparación queda solo como vista interna de dashboard y no sale en ningún PDF?
2. Detalle por Alumno y por Pregunta (specs 15, 16) por curso: con 24 cursos y hasta 3 hitos, ¿van en semestral/anual (paginado por Hito × Curso) o solo en última prueba, como en SIMCE?
3. ¿Se corrige aquí también el heatmap Curso × Eje (excluirlo, igual que en SIMCE) o hay algún caso de uso donde sí aporta frente al gráfico de barras equivalente?

---

## 3 · IDEL (`id_indicator=3`)

- **Familia**: B (a medida).
- **Estado de datos**: único indicador con **3 años** de historia (2024-2026), 1 establecimiento (Panguipulli), 6 subpruebas (CT/FLO/FNL/FSF/ILP/VSD) y 3 versiones por año (v1/v2/v3; 5°/6° básico no rinden v3). Sin pipeline, cargado por script masivo. IDEL no tiene "Mes" — su eje temporal es **Versión**, no un mes calendario. Eso afecta directamente qué significa "semestral" para este indicador (ver pregunta abierta 1).
- **Informes hoy**: 4/4 cards de período + 1 custom (`custom_pdl_idel`, motor propio en matplotlib, no comparte código con SIMCE/DIA).
- **Reuso disponible**: el motor actual ya dibuja el mapa de riesgo, la composición y los niveles apilados, y ya replica la matriz de transición y el gráfico "Niveles por Curso y Versión" (spec 142, descrito en el catálogo como réplica de la página 2 del informe oficial) — la mayor parte del contenido de semestral/anual ya existe, falta encajarlo en los 3 modos del motor único.

| Sección | Fuente en el dashboard | Última versión | Semestral | Anual |
|---|---|---|---|---|
| Portada | branding | ✓ | ✓ | ✓ |
| Cuadro Resumen Puntaje por Curso | **sin fuente 1:1 en `dashboard_layout`** — ya la genera el motor actual (`SummaryTable`) sin componente equivalente en Vista General | variante (mantener ad-hoc o buscar equivalente) | variante | variante |
| Composición Global por Nivel de Riesgo | tab Vista General → gráfico (spec 117) | ✓ | ✓ | ✓ |
| Niveles de Riesgo por Curso (apiladas) | tab Vista General → gráfico (spec 118) | ✓ | ✓ | ✓ |
| Mapa de Riesgo Curso × Subprueba | tab Vista General → heatmap (spec 143) | ✓ | variante | ✓ |
| Roster (Estudiante × Subprueba × Versión) | tab Por Curso → matriz pivote (spec 144), exige elegir curso **y** subprueba a la vez | ✗ no exportable tal cual (2 filtros simultáneos) | ✗ | ✗ |
| Listado de Estudiantes (por curso, paginado) | tab Por Curso → tabla (spec 113) | ✓ | pregunta abierta | pregunta abierta |
| Estudiantes en Riesgo Persistente | tab Por Curso → tabla (spec 145) | ✗ no aplica (exige historial) | variante | ✓ |
| Niveles de Riesgo por Versión (apiladas) | tab Tendencia → gráfico (spec 141) | ✗ no aplica | ✓ | ✓ |
| Niveles por Curso y Versión | tab Tendencia → gráfico (spec 142, réplica pág. 2 del informe oficial) | ✗ no aplica | ✓ | ✓ |
| Matriz de Transición Nivel inicial → final | tab Tendencia → heatmap (spec 147), exige selector de subprueba | ✗ no aplica en última versión | variante (transición entre 2 versiones) | ✓ (todo el año) |

**Orden propuesto — Última versión**: Portada → Resumen Puntaje por Curso → Composición Global → Niveles de Riesgo por Curso → Mapa de Riesgo Curso × Subprueba → Listado de Estudiantes por curso.

**Orden propuesto — Semestral/Anual**: mismo bloque → Niveles de Riesgo por Versión → Niveles por Curso y Versión → Matriz de Transición → Estudiantes en Riesgo Persistente.

**Preguntas abiertas**:
1. IDEL no tiene "Mes", solo Versión (v1/v2/v3 por año, y 5°/6° básico sin v3) — ¿qué corresponde exactamente a "semestral" acá? (¿v1 vs. v2? ¿se renombra el modo a "por versión" + "anual" y se descarta el semestral para este indicador?)
2. El Roster (spec 144) exige elegir curso y subprueba simultáneamente — ¿se fija una subprueba por defecto para el PDF (ej. la de mayor riesgo agregado) o se omite del informe impreso y queda solo como herramienta de dashboard?
3. La tabla "Resumen Puntaje por Curso" que ya usa el motor actual no tiene componente equivalente en `dashboard_layout` — ¿se mantiene como sección ad-hoc del informe (como hasta ahora) o se reemplaza por algo que sí exista en el dashboard?

---

## 4 · Cálculo Veloz (`id_indicator=4`)

- **Familia**: B.
- **Estado de datos**: sin pipeline, cargado por script masivo, **todo el dato es de 2025** (5151 filas, 17 cursos incluida enseñanza media). RUT 100% vacío (identidad solo por Nombre). Hoy semestral/anual fallan por falta de datos 2026 — comportamiento correcto según decisión de Miguel (2026-07-30, punto 4 del plan), no un bug del motor.
- **Informes hoy**: 2/4 cards de período (última prueba y personalizado; semestral y anual fallan por falta de datos 2026) + 0 custom.
- **Reuso disponible**: **sin informe custom hoy** (`report_engine_type` vacío, no matchea ninguna heurística, no hay módulo en `reports/custom/`) — todo lo de esta ficha es propuesta nueva. En compensación, el dashboard de este indicador ya separa naturalmente sus 3 tabs por período — "Vista General" (agregado anual), "Última Evaluación" (foto del mes fijado) y "Evolución Mensual" (tendencia) — lo que mapea casi directo a los 3 modos del motor único.

| Sección | Fuente en el dashboard | Última prueba | Semestral | Anual |
|---|---|---|---|---|
| Portada | branding | ✓ | ✓ | ✓ |
| Resumen por Curso | tab Vista General → tabla (spec 153, "anual") / tab Evolución Mensual → tabla (spec 154, "mensual") | variante (usar spec 154 del mes) | variante (spec 154 recortado al semestre) | ✓ (spec 153) |
| Composición (Global / Última Evaluación) | tab Vista General → gráfico (spec 157) / tab Última Evaluación → gráfico (spec 160) | ✓ (spec 160) | variante (spec 157) | ✓ (spec 157) |
| Niveles por Curso | tab Vista General (spec 158, anual) / tab Última Evaluación (spec 161) | ✓ (spec 161) | variante (spec 158) | ✓ (spec 158) |
| Nota Promedio por Curso | tab Vista General (spec 159, anual) / tab Última Evaluación (spec 162) | ✓ (spec 162) | variante (spec 159) | ✓ (spec 159) |
| Distribución de Puntaje | tab Última Evaluación → gráfico (spec 163) / tab Por Curso → boxplot (spec 168, "anual") | ✓ (spec 163) | variante (spec 168) | ✓ (spec 168) |
| Listado Completo (por curso, paginado) | tab Última Evaluación → tabla (spec 155) | ✓ | pregunta abierta | pregunta abierta |
| Estudiantes en Riesgo INICIAL/BÁSICO | tab Última Evaluación → tabla (spec 156) | ✓ | variante (¿persistente?) | variante (¿persistente?) |
| Resumen Mensual | tab Evolución Mensual → tabla (spec 154) | ✗ no aplica | ✓ | ✓ |
| Evolución de Puntaje/Nota/Niveles por Mes (4 gráficos) | tab Evolución Mensual (specs 164-167) | ✗ no aplica | ✓ (recortado al semestre) | ✓ |
| Listado de Estudiantes (todas las evaluaciones) | tab Por Curso → tabla (spec 121) | ✗ redundante con Listado Completo | pregunta abierta | pregunta abierta |

**Orden propuesto — Última prueba**: Portada → Resumen del mes → Composición → Niveles → Nota Promedio → Distribución de Puntaje → Listado Completo por curso → Estudiantes en Riesgo.

**Orden propuesto — Semestral/Anual**: Portada → Resumen (semestral/anual) → Composición/Niveles/Nota anuales → Resumen Mensual → 4 gráficos de evolución mensual → Distribución de Puntaje anual → (pendiente definir) Listado/Riesgo.

**Preguntas abiertas**:
1. Hoy no existe módulo custom para Cálculo Veloz — para el motor único, ¿se construye un módulo nuevo en `reports/custom/` (como SIMCE/DIA) o basta con robustecer el `pdf_layout` genérico que ya tiene 4 secciones?
2. No existe una vista de "riesgo persistente" a través de varios meses (solo el snapshot de la última evaluación, spec 156) — ¿se agrega una versión multi-mes para el anual, análoga a la de IDEL (spec 145)?
3. El "Listado de Estudiantes (todas las evaluaciones)" (spec 121) es casi redundante con "Listado Completo" (spec 155) — ¿se descarta del PDF o se necesita para el anual (una fila por estudiante × mes, con 2 pruebas/mes de protocolo)?

---

## 5 · Fluidez Lectora (`id_indicator=5`)

- **Familia**: B.
- **Estado de datos**: el más pequeño de la org (414 filas), sin pipeline, **sin dimensión Año** (única entre los 6 indicadores) — hoy semestral/anual fallan por motivo estructural, no por falta de dato del año en curso. Miguel decidió (plan, punto 5) derivar el año desde `Fecha` con una migración de dimensión tipo "fecha", que se está ejecutando en paralelo a esta ficha. Hoy solo hay **una** medición cargada ("Ensayo 1"), así que incluso con el fix estructural no hay todavía un segundo punto para mostrar evolución real.
- **Informes hoy**: 2/4 cards de período (última prueba y personalizado; semestral y anual fallan por falta estructural de dimensión Año) + 0 custom.
- **Reuso disponible**: sin informe custom (mismo motivo que Cálculo Veloz) — toda esta ficha es propuesta nueva. `pdf_layout_historico` ya declara 2 gráficos de evolución que hoy no tienen ninguna tab que los respalde en el dashboard (ver pregunta abierta 2).

| Sección | Fuente en el dashboard | Última prueba | Semestral | Anual |
|---|---|---|---|---|
| Portada | branding | ✓ | ✓ | ✓ |
| Resumen por Curso | tab Vista General → tabla (spec 129) | ✓ | variante | variante |
| PPM Promedio por Curso | tab Vista General → gráfico (spec 131) | ✓ | ✓ | ✓ |
| Distribución de PPM por Curso (boxplot) | tab Vista General → gráfico (spec 132) | ✓ | ✓ | ✓ |
| Composición Global (por Categoría) | tab Vista General → gráfico (spec 133) | ✓ | ✓ | ✓ |
| Categoría por Curso (apiladas) | tab Vista General → gráfico (spec 134) | ✓ | ✓ | ✓ |
| Composición por Calidad Lectora | tab Calidad Lectora → gráfico (spec 150) | variante (ver pregunta 3) | variante | variante |
| Calidad Lectora por Curso (apiladas) | tab Calidad Lectora → gráfico (spec 135) | variante | variante | variante |
| Heatmap Curso × Calidad / Categoría × Calidad | tab Calidad Lectora → heatmaps (specs 151, 136) | ✗ analítico, no de reporte impreso | ✗ | ✗ |
| Listado de Estudiantes (por curso, paginado) | tab Por Curso → tabla (spec 130) | ✓ | pregunta abierta | pregunta abierta |
| Composición por Seguimiento | tab Refuerzo/Riesgo → gráfico (spec 152) | ✓ | ✓ | ✓ |
| Seguimiento Intensivo | tab Refuerzo/Riesgo → tabla (spec 148) | ✓ | ✓ | ✓ |
| Lectores Iniciales | tab Refuerzo/Riesgo → tabla (spec 149) | ✓ | ✓ | ✓ |
| Evolución PPM / Categoría por Evaluación (2 gráficos) | **sin tab equivalente hoy** — declarados en `pdf_layout_historico` sin componente en `dashboard_layout` | ✗ no aplica | pendiente (ver pregunta 2) | pendiente |

**Orden propuesto — Última prueba**: Portada → Resumen por Curso → PPM Promedio → Distribución → Composición Global → Categoría por Curso → Composición/Calidad por Curso → Listado por curso → Composición por Seguimiento → Seguimiento Intensivo → Lectores Iniciales.

**Orden propuesto — Semestral/Anual**: mismo bloque + gráficos de evolución (una vez exista una tab de Tendencia que los respalde) insertados antes del listado por curso.

**Preguntas abiertas**:
1. Con solo una medición cargada hoy, ¿los modos semestral/anual quedan diseñados-pero-no-probables hasta que exista una segunda carga, o se prioriza esa segunda carga antes de dar por cerrada esta ficha?
2. `pdf_layout_historico` ya declara 2 gráficos de evolución que no tienen tab equivalente en el dashboard (no existe "Tendencia" para FL) — ¿se crea esa tab para respetar la regla de "toda sección del PDF viene de un componente real", o el informe puede tener secciones que el dashboard no muestra?
3. "Categoría por Curso" (spec 134, escala Insuficiente→Avanzado del puntaje PPM) y "Calidad Lectora por Curso" (spec 135, escala Fluida→No Lector) clasifican el mismo PPM con dos escalas distintas — ¿van ambas al informe o se elige una para no duplicar el mensaje?

---

## 6 · SIMCE Panguipulli (`id_indicator=6`)

- **Familia**: A.
- **Estado de datos**: estructuralmente casi un clon del dashboard de SIMCE (mismos 4 tabs, mismos tipos de componente), salvo que **no tiene KPIs** en Vista General y **no tiene dimensión Eje Temático** (solo Habilidad). Todo el dato es de 2025 (igual que Cálculo Veloz) → semestral/anual 2026 no disponibles hoy por falta de carga, comportamiento correcto según la misma decisión de Miguel que aplica a Cálculo Veloz.
- **Informes hoy**: 0/4 cards de período (`pdf_layout`/`pdf_layout_historico` vacíos — es un hueco de configuración, no de datos) + 1 custom.
- **Reuso disponible**: `custom_simce_panguipulli` ya implementa resumen por curso, rendimiento, boxplot, composición global, niveles apilados, logro por habilidad y logro por alumno por curso, además de un gráfico fijo de evolución por curso/mes que hoy se dibuja siempre (ver pregunta abierta 1) — la base es casi completa.

| Sección | Fuente en el dashboard | Última prueba | Semestral | Anual |
|---|---|---|---|---|
| Portada | branding | ✓ | ✓ | ✓ |
| Resumen de Logro por Curso | tab Vista General → tabla (spec 170) | ✓ | variante | variante |
| Rendimiento por Curso | tab Vista General → gráfico (spec 173) | ✓ | ✓ | ✓ |
| Distribución de Rendimiento por Curso (boxplot) | tab Vista General → gráfico (spec 174) | ✓ | ✓ | ✓ |
| Composición Global por Nivel | tab Vista General → gráfico (spec 175) | ✓ | ✓ | ✓ |
| Niveles por Curso (apiladas) | tab Vista General → gráfico (spec 176) | ✓ | ✓ | ✓ |
| Logro por Habilidad | tab Por Curso → gráfico (spec 171), agregado sin filtro | ✓ | ✓ | ✓ |
| Estudiantes en Riesgo | tab Por Curso → tabla (spec 172) | ✓ | variante (¿persistente?) | variante |
| Logro por Alumno (por curso, paginado) | tab Por Estudiante → tabla (spec 169) | ✓ | pregunta abierta | pregunta abierta |
| Evolución por Curso y Mes (2 gráficos) | tab Tendencia (specs 177, 178) | ✗ hoy el motor actual las dibuja siempre, incluso con un solo mes (mismo defecto ya diagnosticado en SIMCE) | ✓ | ✓ |

**Orden propuesto — Última prueba**: Portada → Resumen por Curso → Rendimiento por Curso → Distribución → Niveles por Curso → Composición Global → Logro por Habilidad → Logro por Alumno por curso.

**Orden propuesto — Semestral/Anual**: mismo bloque + Evolución por Curso y Mes (2 gráficos).

**Preguntas abiertas**:
1. El informe custom actual ya dibuja "Evolución del Logro Promedio por Curso y Mes" siempre, incluso filtrado a un solo mes (el mismo defecto ya diagnosticado en SIMCE) — ¿se corrige acá también condicionando la sección al modo, o se documenta como deuda compartida y se corrige una sola vez para ambos módulos?
2. Falta la dimensión Eje Temático (a diferencia de SIMCE/DIA) — ¿se confirma que es porque el instrumento EMN Aptus no la mide (dato correcto, sección de menos por diseño) y no un hueco de carga?
3. Igual que Cálculo Veloz, todo el dato es 2025 — ¿se acepta que semestral/anual salgan "sin datos con motivo" hasta que haya carga 2026, siguiendo la misma decisión ya tomada para Cálculo Veloz?

---

## 7 · Decisiones transversales (comunes a las 6 fichas)

- **Portada**: título con nombre del informe + asignatura/nivel cuando aplique (SIMCE/DIA/Panguipulli) + período; subtítulo con el nombre del establecimiento (hoy varía entre indicadores — ver P1 del doc de comparación SIMCE, pendiente de unificar).
- **Encabezado** (todas las páginas): logo Fundación PHP a la izquierda, tres líneas centradas (nombre del informe / asignatura-nivel / mes-año o período), escudo del colegio a la derecha cuando el indicador tiene un único establecimiento; en DIA (2 establecimientos) el encabezado no puede fijar un escudo único — a resolver en el contrato técnico (fase 2).
- **Pie** (todas las páginas): línea horizontal + marca "Fundación PHP" a la izquierda (branding neutro, ya decidido en commit `bb1f865`) + número de página a la derecha.
- **Paginación por curso**: cada tabla de detalle por curso (Logro por Alumno, Logro por Pregunta, Listado de Estudiantes) debería arrancar en página nueva — hoy es un defecto conocido en el motor v2 (`comparacion_simce_referencia_2026-07-30.md`, punto P1.7) que aplica igual a los 3 indicadores de familia A.
- **Filtro de Asignatura**: obligatorio en SIMCE/DIA/Panguipulli (2-3 valores); no aplica a IDEL/Cálculo Veloz/Fluidez Lectora.
- **Manejo de "sin datos"**: mensaje neutro con motivo explícito, nunca traceback — ya implementado y correcto en Cálculo Veloz y Panguipulli (falta de 2026) y en Fluidez Lectora (falta de dimensión Año).
- **Exclusión sistemática**: selectores interactivos (curso, subprueba), matrices que exigen 2 filtros simultáneos a la vez (Roster IDEL) y heatmaps que cruzan las mismas dos dimensiones que ya tienen un gráfico de barras propuesto (Curso×Eje en SIMCE/DIA, Curso×Calidad y Categoría×Calidad en Fluidez Lectora) — se dejan fuera del PDF en todos los casos, quedan solo en dashboard.
- **Orden general heredado del oficial SIMCE**: portada → resumen numérico (tabla) → gráficos generales del establecimiento → detalle específico del instrumento (pregunta/subprueba) → evolución/tendencia (solo semestral/anual) → detalle por curso (alumno/pregunta), paginado.
- **Pregunta transversal repetida** (aparece en las 6 fichas de una forma u otra): ¿el detalle por estudiante/curso va también en semestral y anual, o solo en última prueba? Se dejó como pregunta abierta por indicador en vez de decidirla una sola vez, porque el volumen de páginas que implica varía mucho (4 cursos en SIMCE vs. 24 en DIA, por ejemplo).
- **Riesgo persistente (multi-prueba)** aparece como pregunta abierta en 3 fichas (SIMCE, DIA, Cálculo Veloz) porque IDEL ya tiene una vista equivalente (spec 145, "Estudiantes en Riesgo Persistente") y ninguno de los otros indicadores de familia A/B la tiene todavía — si Miguel la confirma para uno, probablemente aplica al resto por consistencia.
- **Pipeline vs. carga masiva**: SIMCE y DIA se alimentan de pipelines interactivos (`SaveToMetric` con `created_via='pipeline'` en las corridas recientes); IDEL, Cálculo Veloz y Fluidez Lectora se cargaron 100% por script de una sola vez (`created_via` NULL). Esto no cambia qué secciones corresponden — el motor único lee `metric_data`, no el origen — pero sí condiciona qué tan fácil es sumar una prueba nueva para poder probar semestral/anual con datos reales (relevante para Cálculo Veloz, Panguipulli y Fluidez Lectora).
- **Gating de la fase**: ninguna ficha se programa sin el OK explícito de Miguel a esa ficha puntual (regla del plan, sección "Riesgos"). Las preguntas abiertas de cada ficha son insumo directo para ese OK, no decisiones ya tomadas por este documento.

### Complejidad estimada por indicador

| Indicador | Complejidad | Por qué |
|---|---|---|
| SIMCE | **Media** | Familia A con motor oficial ya validado visualmente (~58% de cobertura contra la referencia); lo que falta es cerrar brechas de datos y detalle (dimensión Pregunta, orden curricular de series), no de estructura. |
| DIA | **Alta** | Familia A pero el dashboard más rico (5 tabs, 2 establecimientos, 24 cursos) y con una tab exclusiva (Comparativa Establecimientos) sin decisión tomada sobre si va al PDF — el volumen de páginas por curso también es el mayor de la org. |
| IDEL | **Media-Alta** | Familia B pero con motor oficial ya funcionando (matplotlib, réplica de página real); la complejidad viene de que su eje temporal es "Versión", no "Mes/Semestre", lo que obliga a redefinir qué significa "semestral" para este indicador. |
| Cálculo Veloz | **Alta** | Sin motor custom (hay que construirlo desde cero), dashboard con 4 tabs y varias secciones casi redundantes por resolver; semestral/anual bloqueados hoy por falta de datos 2026 (esperado, no bug). |
| Fluidez Lectora | **Alta** | Sin motor custom, sin dimensión Año (depende de una migración en curso en paralelo a esta ficha) y con una sola medición cargada — semestral/anual no se pueden ni probar todavía con datos reales. |
| SIMCE Panguipulli | **Baja-Media** | Estructura casi idéntica a SIMCE (mismo patrón, una dimensión menos) y motor custom ya funcionando; el pendiente principal es heredar el fix de "evolución de un solo mes" y confirmar el mismo comportamiento sin-datos-2026 ya aceptado para Cálculo Veloz. |
