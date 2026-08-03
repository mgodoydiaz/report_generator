# QA de dashboards de Resultados — org 1 (Fundación PHP)

**Fecha**: 2026-08-03 · **Rama**: `dev` · **Entorno**: dev local
(backend `localhost:8001`, frontend `localhost:5173`, DB canónica `report_generator-db-1`)
**Alcance**: los 6 indicadores de la org 1 — SIMCE (1), DIA (2), IDEL (3),
Cálculo Veloz (4), Fluidez Lectora (5), SIMCE Panguipulli (6).
**Usuario**: `qa.admin@rgenerator.local` (admin, org 1).

**Método**

1. Lectura de `Indicator.dashboard_layout` de los 6 indicadores; enumeración de
   tabs / rows / items; resolución de cada `spec_id` contra `specs` y llamada al
   endpoint real (`GET /api/charts/{id}/data`, `GET /api/tables/{id}/data`).
2. **Recálculo independiente** de charts y tablas representativos con SQL crudo
   sobre `metric_data` (parseo de `dimensions_json` / `value` con `::json ->>`),
   sin pasar por `_load_metric_to_df`, y diff contra la respuesta del endpoint.
3. Réplica de la lógica de color del frontend (`ChartRenderer.jsx`:
   `resolvePalette` + `palette_reversed` + `pickSeriesColor`) para calcular el
   color **efectivo** de cada categoría de nivel y compararlo con
   `Indicator.achievement_levels`.
4. Recorrido en navegador con sesión real, extrayendo el estado renderizado de
   Plotly (`gd.data`, `gd.layout`) por pestaña. Evidencia en
   `data/output/qa_indicadores/2026-08-03/dashboards/`.

**Resumen de resolución**: los **80 items** `configured_chart` / `configured_table`
de los 6 layouts resuelven HTTP 200. No hay specs faltantes, ni desalineación de
tipo, ni errores de consola. El problema no es que no cargue: es **qué muestra**.

---

## Tabla de puntajes

| # | Indicador | Correctitud de datos /40 | Completitud config /25 | Semántica /20 | Visual/render /15 | **Total /100** |
|---|---|---:|---:|---:|---:|---:|
| 5 | **Fluidez Lectora** | 36 | 21 | 9 | 14 | **80** |
| 4 | **Cálculo Veloz** | 25 | 23 | 10 | 14 | **72** |
| 6 | **SIMCE Panguipulli** | 23 | 19 | 10 | 12 | **64** |
| 1 | **SIMCE** | 10 | 22 | 3 | 14 | **49** |
| 2 | **DIA** | 11 | 20 | 3 | 10 | **44** |
| 3 | **IDEL** | 1 | 11 | 7 | 6 | **25** |

Promedio ponderado de la org: **55,7 / 100**.

Desglose de descuentos por indicador en cada sección.

---

## 1. SIMCE (id 1) — 49/100

**Layout**: 4 tabs, 15 items configurados (10 charts + 5 tablas). Métricas 4
(1.286 filas, por estudiante) y 5 (1.680 filas, por pregunta). Todos resuelven.

### Correctitud de datos — 10/40

Las agregaciones del motor son **exactas**. Se recalcularon con SQL y hubo
**0 discrepancias numéricas** en: spec 108 (pie por Logro), spec 106 (media de
`Rend` por curso), spec 109 (12 celdas curso×nivel), spec 138 (24 celdas
curso×mes) y la tabla 17 (N, media, mín, máx, SIMCE por curso). El problema es
**qué se está contando y sobre qué universo**.

| Gravedad | Hallazgo | Números |
|---|---|---|
| **Alta** | `spec 109` rotula el eje **"N° Estudiantes"** pero grafica **filas de evaluación**. | II A muestra 140+117+44 = **301**, y el curso tiene **61 RUTs únicos** (4,9x). Global: 1.286 filas / 236 RUTs = **5,45x**. Mismo defecto en `spec 140` (mismo `y_label`) y en la columna "N°" de la tabla `spec 17` (301/328/351/306 vs 61/62/60/56 alumnos). |
| **Alta** | **MAYO pertenece a 2026, todos los demás meses a 2025**, y el gráfico de tendencia los presenta como una secuencia de meses sin año. | SQL: 2025 ABRIL 232, JUNIO 220, AGOSTO 212, OCTUBRE 210, NOVIEMBRE 216 · **2026 MAYO 196**. Los charts 138/139/140 no tienen filtro de `Año`. |
| **Alta** | El pie "Composición Global" y la barra "Rendimiento por Curso" promedian **2 asignaturas y 2 años** juntos. | Lenguaje 642 filas + Matemáticas 644; 2025 1.090 + 2026 196. El KPI "LOGRO 44%" es ese promedio mezclado. |
| **Alta** | La tabla `spec 105` **"Estudiantes en Riesgo" no filtra riesgo**: devuelve el dataset completo. | `filters: {}`, `total_rows = 1286` (100% de la métrica). Solo está ordenada por `Rend asc`, así que la página 1 parece correcta y el export CSV trae todo. |
| **Media** | `Eje Temático` está vacío en **1.420 de 1.680 filas (84,5%)** y `Habilidad` en **300 (17,9%)**; esas filas se caen del `groupby` de los gráficos pero sí aparecen en la tabla. | "Logro por Eje" (spec 23) y el heatmap (spec 111) se calculan sobre el **15,5%** de los datos de preguntas. |
| **Media** | Categorías de `Habilidad` duplicadas por capitalización: se grafican como barras separadas. | `Argumentar Y Comunicar` 24 / `Argumentar y comunicar` 16 · `Resolver Problemas` 428 / `Resolver problemas` 52. |

### Completitud de configuración — 22/25
15/15 items resuelven con datos. Tabs coherentes. Se descuenta que existiendo
filtros de `Año` y `Asignatura` en la barra superior, ningún spec los fija por
defecto, así que la vista de entrada es siempre la mezclada.

### Semántica — 3/20

| Gravedad | Hallazgo |
|---|---|
| **Crítica** | **`spec 109` "Niveles por Curso" pinta el semáforo al revés**: `Insuficiente` → `#22c55e` (verde), `Elemental` → `#f59e0b`, `Adecuado` → `#ef4444` (rojo). Verificado en el navegador sobre `gd.data`. Los niveles declarados son `#dc2626` / `#eab308` / `#22c55e`. Está **al lado del pie 108**, que sí los pinta bien: dos gráficos contiguos con semántica de color opuesta. Causa: el spec no define `color_overrides` y usa `color_palette:"semaforo"` (`['#22c55e','#f59e0b','#ef4444']`) aplicada **por índice** sobre `stack_order:["Insuficiente","Elemental","Adecuado"]` sin `palette_reversed`. |
| **Alta** | **MAYO fuera de orden cronológico** en 3 gráficos: `stack_order` de 138 y 139 y `x_order` de 140 son `["ABRIL","JUNIO","AGOSTO","OCTUBRE","NOVIEMBRE","MAYO"]`. `Indicator.temporal_config` declara `["ABRIL","MAYO","JUNIO","AGOSTO","OCTUBRE","NOVIEMBRE"]`. Leído de izquierda a derecha, el gráfico sugiere una caída 0,57 → 0,47 al cierre del año. |
| **Media** | El eje de "Logro por Eje" mezcla ejes de Lenguaje (`LÍRICA`, `NARRATIVA`) con ejes de Matemáticas (`Geometría`, `Números`, `Álgebra y funciones`) más códigos opacos (`TMC`, `TMCFA`). |
| **Media** | `spec 140` sí pinta el semáforo correcto (tiene `palette_reversed: true`): el mismo indicador usa dos mapeos de color opuestos para los mismos 3 niveles según la pestaña. |

### Visual / render — 14/15
Renderiza limpio, sin errores de consola, sin desbordes; 4 cursos ⇒ leyendas
legibles. Latencia 0,6–0,7 s por gráfico.

---

## 2. DIA (id 2) — 44/100

**Layout**: 5 tabs, 18 items. Métricas 6 (5.647 filas) y 7 (2.386). Todos resuelven.

### Correctitud de datos — 11/40

Agregaciones exactas: 0 discrepancias en spec 25 (24 cursos), spec 28 (72 celdas
curso×nivel) y spec 98 (46 celdas hito×curso).

| Gravedad | Hallazgo | Números |
|---|---|---|
| **Crítica** | La **"Tendencia por Hito" (`spec 98`) corre hacia atrás en el tiempo**. El punto DIAGNOSTICO es mayoritariamente de **2026**, mientras INTERMEDIO y CIERRE son 100% de **2025**. | DIAGNOSTICO: 444 filas 2025 (32,2%) + **935 filas 2026 (67,8%)** · INTERMEDIO: 3.940 filas, 100% 2025 · CIERRE: 328 filas, 100% 2025. Sin filtro de `Año` en el spec. |
| **Alta** | Cobertura radicalmente distinta por hito, sin advertencia en el gráfico. | DIAGNOSTICO 23 cursos / INTERMEDIO 19 / **CIERRE 4**. 20 de las 24 series de la línea terminan en INTERMEDIO. `spec 104` "Cierre — Curso × Establecimiento" tiene **1 sola serie** (Liceo PHP Pullinque). |
| **Alta** | `spec 96` **"Estudiantes en Riesgo" no filtra riesgo**: `filters: {}`, `total_rows = 5647` (el dataset completo). |
| **Alta** | **375 filas sin `Nombre` ni `Nombre_Norm`** (todas en DIAGNOSTICO). Quedan fuera de cualquier agregación por estudiante pero cuentan en los promedios por curso. |
| **Media** | El KPI "Total alumnos = **1.311**" cuenta nombres distintos a través de 2 años y 2 establecimientos, no estudiantes. |
| **Media** | `Logro` promedia `LECTURA` (2.631 filas) y `MATEMATICA` (3.016) sin separarlas por defecto. |

### Completitud de configuración — 20/25
18/18 items resuelven. Se descuenta por items estructuralmente degenerados
(`spec 104` monoserie) y por la falta de un filtro de `Año` por defecto en un
dataset que abarca dos años.

### Semántica — 3/20

| Gravedad | Hallazgo |
|---|---|
| **Alta** | `spec 26` "Logro por Nivel" grafica una **progresión de niveles escolares en orden alfabético**: `Cuartos, Octavos, Primeros, Primeros Medios, Quintos, Segundos, Segundos Medios, Septimos, Sextos, Terceros`. Sin `x_order`. Además los n son muy dispares (Octavos 55 vs Primeros Medios 2.428) y el gráfico no lo muestra. |
| **Alta** | Gráficos ilegibles por explosión de series: `spec 29` 14 x × **18 series** (252 barras), `spec 30` 7 x × **24 series** (168 barras), `spec 27` box con **24 trazas**, `spec 98` línea con **24 series sobre 3 puntos**. |
| **Media** | La tabla `spec 95` "Comparativa entre Hitos" no ordena por la secuencia de hitos: la primera fila es CIERRE. |
| **Baja** | Colores de nivel cercanos pero no exactos: `Inicial` renderiza `#ef4444` vs `#dc2626` declarado; `Intermedio` `#f59e0b` vs `#eab308`. (`spec 28` no define `color_overrides`; la dirección sí es correcta gracias a `palette_reversed`.) |

### Visual / render — 10/15
Sin errores de consola. Penaliza: leyendas de 24 entradas que desbordan el alto
del gráfico, y latencia de **1,4–2,5 s por gráfico** (la Vista General tarda
~8 s en completarse).

---

## 3. IDEL (id 3) — 25/100

**Layout**: 3 tabs, 8 items configurados. Métrica 8 (3.890 filas). Todos
devuelven HTTP 200 — y aun así **la mitad muestra cero información**.

### Correctitud de datos — 1/40

Lo que funciona: la Vista General es **exacta**. Recálculo con SQL de `spec 117`
(pie), `spec 118` (24 celdas curso×nivel) y `spec 143` (heatmap, 36 celdas de
% en riesgo): **0 discrepancias**.

Lo que no:

| Gravedad | Hallazgo | Números |
|---|---|---|
| **Crítica** | **La dimensión `Versión` (id 20) almacena `"1"`, `"2"`, `"3"`, pero los specs esperan `"v1"`, `"v2"`, `"v3"`.** Esto revienta 4 de los 8 items. |
| **Crítica** | `spec 141` "Niveles de Riesgo por Versión": **las 12 barras valen 0**. Eje Y auto-escalado a −1…1. Verificado en navegador. Debería mostrar v1 = 243/350/667/360 (1.620 evaluaciones), v2 = 194/232/567/494 (1.487), v3 = 84/132/299/268 (783). **3.890 evaluaciones invisibles.** |
| **Crítica** | `spec 142` "Niveles por Curso y Versión (réplica informe pág 2)": 6 cursos × 3 versiones × 4 niveles = **72 barras, todas 0**. |
| **Crítica** | `spec 144` "Roster — Niveles por Estudiante × Subprueba × Versión": 340 filas × 18 columnas = **6.120 celdas, todas "N/A"**. Verificado por endpoint (`no-nulas = 0`) y en pantalla. |
| **Crítica** | `spec 147` "Matriz de Transición": dataset `{"x": [], "y": [], "z": []}` — heatmap **vacío**. Los derivados `nivel_inicial`/`nivel_final` usan `time_ordinal_levels: ["v1","v2","v3"]` contra valores `1/2/3`. |
| **Alta** | `spec 145` "Estudiantes en Riesgo Persistente": `filters: {}` → **3.890 filas** (todo el dataset) y, además, **el `sorting` declarado no se aplica**: las primeras 10 filas tienen `Versiones_en_Riesgo = 0` cuando el máximo real es 4. El orden por columnas derivadas está roto (el orden por columnas reales, p. ej. `spec 105` sobre `Rend`, sí funciona). |
| **Alta** | Todos los gráficos **mezclan 3 años sin filtro por defecto**: 2024 = 845 filas, 2025 = 2.269, 2026 = 776. El pie "Composición Global" (39,4% Cierto Riesgo) es una foto de tres cohortes superpuestas. |
| **Alta** | **Identidad por nombre poco confiable**: 340 `Nombre` distintos vs **227 RUTs**. 18 RUTs tienen más de una grafía (`25.034.147-4` → "Ampuero **Alveal**" / "Ampuero **Alvial**"; `25.388.053-8` → "Mondaca Manosal**b**a" / "Mondaca Manosal**v**a"). Hay **184 combinaciones (Nombre, Subprueba, Versión) duplicadas**, todas cruzando 2025–2026. Los derivados `Versiones_en_Riesgo`, `nivel_inicial` y `nivel_final` usan `Nombre` como entidad. El KPI "TOTAL ALUMNOS 340" sobreestima en ~50%. |

### Completitud de configuración — 11/25
8 items configurados, **4 renderizan vacío o en cero** (50%). El tab Tendencia
completo (3/3 gráficos) no muestra dato alguno.

### Semántica — 7/20
Positivo: es el **único indicador con `color_overrides` exactos a
`achievement_levels`** en los 4 charts de nivel (`#dc2626` / `#ea580c` /
`#eab308` / `#22c55e`), y con `stack_order` peor→mejor correcto.

| Gravedad | Hallazgo |
|---|---|
| **Alta** | La nota del tab Tendencia afirma *"5° y 6° BÁSICO no rinden la evaluación v3 según el protocolo IDEL"*. **Los datos la contradicen**: 5° BÁSICO 2025 v3 = **104 filas**, 6° BÁSICO 2025 v3 = **88 filas**. O la nota está mal o los datos están mal cargados; en cualquier caso el dashboard afirma algo falso. |
| **Media** | Etiquetado de versión inconsistente dentro de una misma pestaña: el roster titula `v1 / v2 / v3` y la tabla "Listado de Estudiantes" justo abajo muestra `Versión = 2`. |
| **Media** | El selector de subprueba renderiza **`Ct · Flo · Fnl · Fsf · Ilp · Vsd`** en vez de las siglas oficiales `CT, FLO, FNL, FSF, ILP, VSD`. Las tablas y el heatmap sí usan el formato correcto ("CT · Comprensión de Textos"). |

### Visual / render — 6/15
Sin errores de consola, pero: el tab Tendencia muestra tres marcos de gráfico con
ejes en −1…1 y nada dibujado; el roster es una pared de 6.120 "N/A"; y al pasar
de un indicador con 5 tabs (DIA) a IDEL (3 tabs) **la página queda completamente
en blanco** — el índice de tab activa no se resetea y `tabs[activeTab]` queda
`undefined`, sin error ni mensaje.

---

## 4. Cálculo Veloz (id 4) — 72/100

**Layout**: 4 tabs, 16 items. Métrica 9 (5.151 filas). Todos resuelven. Es el
dashboard **mejor configurado** del conjunto.

### Correctitud de datos — 25/40

Verificaciones con 0 discrepancias: `spec 157` (pie por nivel, 5 categorías),
`spec 164` (media de `Nota` por mes), `spec 166` (30 celdas mes×nivel — las
únicas "diferencias" fueron combinaciones inexistentes devueltas como 0, que es
lo correcto), y el filtro de `spec 160` (`Mes=OCTUBRE`, `N Prueba=2` → 269 filas,
idéntico a SQL; la `Fecha` máxima real es `2025-10-23`, o sea el filtro **sí**
apunta a la toma más reciente).

| Gravedad | Hallazgo | Números |
|---|---|---|
| **Alta** | Los gráficos anuales **mezclan dos escalas de instrumento distintas**. Hasta MAYO el puntaje llega a 100; desde JUNIO-JULIO el máximo es 60. | `spec 166`: EXPERTO pasa de **428 (MAYO) a 0 (JUNIO-JULIO)** y AVANZADO de 102 a 0, en los 4 meses restantes. `spec 157` (pie anual), `spec 127` (histograma) y `spec 168` (box) agregan ambas escalas. La nota que lo explica está solo en el tab "Evolución Mensual"; los gráficos afectados en "Vista General" y "Por Curso" no la tienen. |
| **Media** | El pie anual `spec 157` cuenta **filas de prueba**, no estudiantes: 5.151 filas / 498 nombres = **10,3x**. (Las tablas 153 y 154 sí distinguen "Estudiantes únicos" de "Pruebas" — buena práctica que los gráficos no siguen.) |
| **Media** | **`RUT` está vacío en 5.151 de 5.151 filas**: la identidad depende solo de `Nombre`. |
| **Media** | Datos de fecha inconsistentes: **18 filas** etiquetadas `Mes = MAYO` con `Fecha = 2025-02-14` (febrero) y **56 filas** con `Fecha` nula. |
| **Media** | Los filtros de "Última Evaluación" están **cableados** (`Mes=OCTUBRE`, `N Prueba=2`) en 6 specs (160–163, 155, 156). Al cargar la toma siguiente el tab seguirá mostrando octubre, y la nota que dice "la prueba más reciente" pasará a ser falsa. |

### Completitud de configuración — 23/25
16/16 items resuelven con datos. 4 tabs bien diferenciados, con notas
explicativas de calidad. Descuento menor por las 2 series siempre-cero
(`AVANZADO`, `EXPERTO`) en los charts de "Última Evaluación".

### Semántica — 10/20
Positivo: `color_overrides` **exactos** a `achievement_levels` en los 5 charts de
nivel; `x_order` curricular explícito (`I°A…IV°P`) en todos los charts por curso;
orden de meses cronológico en los 3 charts temporales.

| Gravedad | Hallazgo |
|---|---|
| **Alta** | La tabla `spec 154` "Resumen Mensual" está ordenada **alfabéticamente**: ABRIL, AGOSTO, JUNIO-JULIO, MAYO, OCTUBRE, SEPTIEMBRE (`sorting: [{"column":"Mes","dir":"asc"}]`), mientras los 3 gráficos contiguos usan el orden cronológico. La tabla es el resumen de la misma serie que los gráficos. |
| **Media** | `spec 167` línea multi-serie con **17 series**, y su leyenda ordenada `III°A, III°C, III°MA, III°P, II°A, …, I°D` — no curricular, a diferencia del resto del dashboard. |
| **Baja** | 2 entradas de leyenda muertas (AVANZADO/EXPERTO en cero) en 2 charts de "Última Evaluación". |

### Visual / render — 14/15
Sin errores de consola. Muy rápido (20–35 ms por gráfico). Notas bien ubicadas.

---

## 5. Fluidez Lectora (id 5) — 80/100

**Layout**: 4 tabs, 13 items. Métrica 10 (414 filas / **412 RUTs** →
**1,00 filas por estudiante, sin inflación**). Todos resuelven.

### Correctitud de datos — 36/40

Verificaciones con 0 discrepancias: `spec 133` (pie por categoría),
`spec 131` (PPM medio en los 12 cursos), `spec 134` (sumas por stack).

Las tablas de riesgo **sí filtran**, a diferencia de SIMCE / DIA / IDEL /
Panguipulli: `spec 148` `{"Seguimiento":"Intensivo"}` → 51 filas, `spec 149`
`{"Calidad lectora":["No Lector","Silábica"]}` → 10 filas.

Solo hay un ensayo cargado (`N Prueba = Ensayo 1`), y el dashboard **no tiene
tab de tendencia** — no afirma nada que los datos no soporten.

| Gravedad | Hallazgo | Números |
|---|---|---|
| **Media** | `No Aplica` está declarado como nivel de logro pero **no ocurre nunca** en el campo que esos charts grafican (`Categoria`, 0 filas). Solo existe en `Calidad lectora` (3 filas). Produce un stack siempre en cero en `spec 134`, y un desajuste 4 vs 5 categorías entre el pie 133 y el stacked 134. |
| **Baja** | La métrica no tiene dimensión `Año` ni filtro de año (los datos son de 2026); si se cargan más ensayos, todo se mezclará sin control. |

### Completitud de configuración — 21/25
13/13 items resuelven. Descuento porque **`spec 132` se reutiliza literalmente**
en "Vista General" y en "Por Curso" (mismo `spec_id`), de modo que la pestaña
"Por Curso" no aporta nada hasta que se selecciona un curso; más el stack
siempre-cero.

### Semántica — 9/20

| Gravedad | Hallazgo |
|---|---|
| **Alta** | `achievement_levels` coloca **`No Aplica` en `order: 1`** — es decir, como el **peor** nivel de la escala ordinal — y lo pinta de **verde `#2dd22d`**. "No rindió" no pertenece a la escala de logro, y menos con el color del mejor desempeño. Cualquier componente que lea `achievement_levels` (p. ej. `color_scale: linked_indicator` en tablas) lo pintará verde. |
| **Media** | Los `color_overrides` de los specs 133/134/135/150 dicen `No Aplica: #94a3b8` (gris) — divergente de `#2dd22d` en `achievement_levels`: **el override está stale respecto del nivel**. En este caso el gris es más razonable, lo que confirma que la fuente de verdad quedó desactualizada. |
| **Media** | Toda la paleta del indicador se aparta del semáforo canónico del proyecto: `#d22d2d` / `#d2802d` / `#d2d22d` / `#80d22d` en vez de `#dc2626` / `#ea580c` / `#eab308` / `#22c55e`. |
| **Baja** | `spec 132` box con 12 trazas ⇒ 12 entradas de leyenda. |

### Visual / render — 14/15
Sin errores. 16–24 ms por gráfico. Orden curricular correcto
(`7°, 8°, I A … II E`). Notas explicativas bien redactadas.

---

## 6. SIMCE Panguipulli (id 6) — 64/100

**Layout**: 4 tabs, 10 items. Métricas 24 (1.695 filas) y 26 (180). Todos resuelven.

### Correctitud de datos — 23/40

Verificaciones con 0 discrepancias: `spec 173` (media de `PorcLogro` en 7 cursos),
`spec 177` (28 celdas curso×mes) y — notable — `spec 175`, cuyo pie reproduce
exactamente el campo derivado `row_threshold`: replicando el umbral declarado en
SQL (`<=0,4` Insuficiente, `<=0,6` Elemental, resto Adecuado) se obtiene
671 / 641 / 383, idéntico a lo que muestra el gráfico.

| Gravedad | Hallazgo | Números |
|---|---|---|
| **Alta** | Se mezclan **3 asignaturas** sin filtro por defecto en el pie global, la barra de rendimiento y la tabla resumen. | HISTORIA 135 filas, LENGUAJE 783, MATEMATICA 777. El "Logro Promedio" de cada curso promedia las tres. |
| **Alta** | La columna "N°" de la tabla `spec 170` es conteo de filas, no de estudiantes. | 4° básico A: **244 filas / 36 RUTs = 6,8x**. Global 1.695 filas / 225 RUTs = 7,53x. |
| **Alta** | `spec 172` **"Estudiantes en Riesgo" no filtra riesgo**: `filters: {}`, `total_rows = 1695` (dataset completo), solo ordenado por `PorcLogro asc`. |
| **Baja** | `spec 171` "Logro por Habilidad" grafica 8 habilidades × 7 cursos = **56 barras sobre 180 filas** (≈3,2 observaciones por barra). |

### Completitud de configuración — 19/25
10/10 items resuelven. Descuento principal: **es el único de los 6 indicadores
sin banda de KPIs** — su `dashboard_layout` no incluye ningún item `type:"kpis"`,
así que el dashboard abre directo con una tabla y no muestra total de alumnos,
logro promedio ni nivel predominante.

### Semántica — 10/20

| Gravedad | Hallazgo |
|---|---|
| **Crítica** | **`spec 176` "Niveles por Curso" pinta el semáforo invertido**, igual que SIMCE: `Insuficiente` → `#22c55e` (verde), `Adecuado` → `#ef4444` (rojo). Está **inmediatamente debajo del pie 175**, que los pinta al derecho. Verificado en el navegador. |
| **Media** | Los 3 charts de nivel (175, 176, 178) **no definen `color_overrides`** y dependen de la paleta `semaforo` del frontend, cuyos hexes no coinciden con `achievement_levels` ni siquiera cuando la dirección es correcta (`#ef4444` vs `#dc2626`, `#f59e0b` vs `#eab308`). |
| — | Positivo: el orden de meses de la tendencia (ABRIL, MAYO, AGOSTO, SEPTIEMBRE) y el orden de cursos son correctos. |

### Visual / render — 12/15
Sin errores de consola; 0,5–0,6 s por gráfico. Penaliza la ausencia de la banda
de KPIs, que hace que el dashboard se vea incompleto frente a los otros cinco.

---

## Top 5 de problemas transversales

### 1. La paleta `semaforo` aplicada por índice invierte el semáforo en 2 dashboards

`ChartRenderer.jsx` resuelve `color_palette: "semaforo"` a
`['#22c55e','#f59e0b','#ef4444']` (verde → rojo) y la asigna **por posición**
sobre el `stack_order`. Como los `stack_order` de niveles se declaran
peor→mejor (`["Insuficiente","Elemental","Adecuado"]`), sin `palette_reversed`
el resultado es el semáforo al revés.

Efecto medido (color renderizado vs `achievement_levels`):

| Spec | Indicador | Insuficiente | Elemental | Adecuado |
|---|---|---|---|---|
| 109 | SIMCE | **#22c55e verde** (esperado #dc2626) | #f59e0b (esp. #eab308) | **#ef4444 rojo** (esp. #22c55e) |
| 176 | SIMCE Panguipulli | **#22c55e verde** | #f59e0b | **#ef4444 rojo** |
| 140 | SIMCE | #ef4444 | #f59e0b | #22c55e (dirección OK, hex inexacto) |
| 178 | SIMCE Panguipulli | #ef4444 | #f59e0b | #22c55e (dirección OK, hex inexacto) |
| 28 | DIA | #ef4444 (esp. #dc2626) | #f59e0b (esp. #eab308) | #22c55e ✓ |

Los dashboards con `color_overrides` explícitos (IDEL, Cálculo Veloz) dan
**coincidencia exacta**. Los que dependen de la paleta dan, en el mejor caso,
hexes aproximados y, en el peor, el significado invertido.
**Regla derivable: todo chart cuyo `stack_field`/`category_field` sea un nivel de
logro debe llevar `color_overrides` derivado de `achievement_levels`; la paleta
por índice no es un fallback aceptable.**

### 2. Los gráficos y KPIs cuentan filas de evaluación y las rotulan como estudiantes

| Indicador | filas | estudiantes | factor | dónde se nota |
|---|---|---|---|---|
| IDEL | 3.890 | 227 RUTs | **17,1x** | KPI "340 alumnos"; pie de composición |
| Cálculo Veloz | 5.151 | 498 nombres | **10,3x** | pie anual `spec 157` |
| SIMCE Panguipulli | 1.695 | 225 RUTs | **7,5x** | columna "N°" de la tabla 170 |
| SIMCE | 1.286 | 236 RUTs | **5,4x** | eje "N° Estudiantes" de 109 y 140 |
| DIA | 5.647 | ~1.311 nombres | **4,3x** | KPI "1.311 alumnos" |
| Fluidez Lectora | 414 | 412 RUTs | 1,0x | — |

El caso más grave no es la inflación en sí (contar evaluaciones puede ser
legítimo) sino el **rótulo**: `spec 109` y `spec 140` dicen literalmente
`y_label: "N° Estudiantes"` sobre conteos de filas. Las tablas 153 y 154 de
Cálculo Veloz muestran el patrón correcto: dos columnas separadas,
"Estudiantes únicos" y "Pruebas".

### 3. Cuatro tablas "Estudiantes en Riesgo" no filtran riesgo

| Spec | Indicador | filtro | filas devueltas |
|---|---|---|---|
| 105 | SIMCE | `{}` | 1.286 (100% del dataset) |
| 96 | DIA | `{}` | 5.647 (100%) |
| 172 | SIMCE Panguipulli | `{}` | 1.695 (100%) |
| 145 | IDEL | `{}` | 3.890 (100%) — y **el `sorting` tampoco se aplica** |
| 156 | Cálculo Veloz | `Nivel ∈ {INICIAL, BÁSICO}` | 209 ✓ |
| 148/149 | Fluidez Lectora | `Seguimiento` / `Calidad lectora` | 51 / 10 ✓ |

El riesgo queda implícito en el `sorting` ascendente, de modo que la primera
página aparenta funcionar; el contador de filas y el export CSV entregan el
colegio completo. En IDEL ni siquiera eso: **el orden por columnas derivadas
(`Versiones_en_Riesgo`) no se aplica**, así que las primeras filas de la tabla de
"riesgo persistente" tienen 0 versiones en riesgo cuando el máximo real es 4.
(El orden por columnas reales, como `Rend` en `spec 105`, sí funciona.)

### 4. Los agregados mezclan años, asignaturas y escalas de instrumento sin decirlo

Ningún spec fija un `Año` por defecto, aunque la barra de filtros lo ofrece.

- **IDEL**: 2024 (845) + 2025 (2.269) + 2026 (776) en cada gráfico.
- **DIA**: el punto DIAGNOSTICO de la tendencia es **67,8% de 2026** mientras
  INTERMEDIO y CIERRE son 100% de 2025 — la serie temporal corre hacia atrás.
- **SIMCE**: MAYO es 2026 y el resto 2025, en un gráfico que solo muestra el mes.
- **SIMCE / DIA / Panguipulli**: 2–3 asignaturas promediadas en un solo "Logro".
- **Cálculo Veloz**: dos escalas del instrumento (máx 100 hasta MAYO, máx 60
  desde JUNIO-JULIO) en el mismo pie / histograma / boxplot anual.

El único indicador que documenta la trampa es Cálculo Veloz, con una nota — pero
solo en el tab donde el efecto es visible, no en los gráficos de otros tabs que
sufren lo mismo.

### 5. Órdenes de eje que ignoran la semántica del dominio

| Dónde | Orden renderizado | Orden correcto |
|---|---|---|
| SIMCE specs 138/139 (`stack_order`) y 140 (`x_order`) | ABRIL, JUNIO, AGOSTO, OCTUBRE, NOVIEMBRE, **MAYO** | el de `temporal_config`: ABRIL, MAYO, JUNIO, AGOSTO, OCTUBRE, NOVIEMBRE |
| DIA spec 26 (sin `x_order`) | Cuartos, Octavos, Primeros, Primeros Medios, Quintos, Segundos, Segundos Medios, Septimos, Sextos, Terceros | Primeros → Segundos Medios |
| CV spec 154 (tabla) | ABRIL, AGOSTO, JUNIO-JULIO, MAYO, OCTUBRE, SEPTIEMBRE | cronológico (los gráficos vecinos sí lo usan) |
| CV spec 167 (series) | III°A, III°C, III°MA, III°P, II°A, …, I°D | I° → IV° |
| FL `achievement_levels` | `No Aplica` en `order: 1` (el peor) | fuera de la escala ordinal |
| IDEL specs 141/142/144 | `x_order: ["v1","v2","v3"]` | los valores reales son `"1"`, `"2"`, `"3"` |

El último caso es el más caro: **una discrepancia de literal entre `x_order` y el
valor almacenado no produce error, produce ceros**. `_build_dataset` en
`backend/routers/charts.py` usa `int(sub.get(x, 0))` para `stacked_bar` y
`idx.get(..., 0)` para `stacked_grouped_bar`, así que un `x_order` que no matchea
devuelve un gráfico completo en cero, con HTTP 200 y sin advertencia. Lo mismo
en `pivot_matrix` (celdas `None`) y en los campos derivados temporales
(`time_ordinal_levels`). Un chequeo de intersección `x_order ∩ valores reales`
convertiría 4 gráficos silenciosamente vacíos en un error visible.

---

## Anexos

- Capturas y estado Plotly renderizado por pestaña:
  `data/output/qa_indicadores/2026-08-03/dashboards/`
- Archivos de referencia citados:
  - `backend/routers/charts.py` — `_build_dataset` (uso de `x_order` / `stack_order`)
  - `backend/routers/tables.py` — `_load_metric_to_df`, `_render_table_data`
  - `frontend/src/components/charts/ChartRenderer.jsx` — `resolvePalette`,
    `pickSeriesColor`, `SEMAFORO_COLORS`, `SEMAFORO_4_COLORS`
  - `frontend/src/tooling/dataProcessing.js` — `computeDashboardKPIs` (`totalAlumnos`)
  - `frontend/src/tooling/dashboardRenderer.jsx` — `ItemRenderer`
- Solo lectura sobre datos de negocio. No se modificó `backend/` ni `frontend/`.
  No se hizo commit.
