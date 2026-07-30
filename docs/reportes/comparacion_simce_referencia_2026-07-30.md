# Comparación: informe SIMCE de referencia vs. el que genera el sistema hoy

**Fecha:** 2026-07-30
**Rama:** `dev3`
**Referencia (ground truth del dueño):** `C:\Users\magod\Documents\Proyectos\Informes PHP\Evaluaciones 2026\SIMCE\Pullinque Matemáticas Mayo\informe.pdf` (14 páginas)
**PDFs generados para la comparación:** `C:\Users\magod\Desktop\PDF_test\comparacion_simce\`

| Archivo | Camino | Páginas |
|---|---|---|
| `v2_custom_simce_matematicas_mayo.pdf` | `POST /api/reports/custom/simce` — motor v2 "formato oficial" | 13 |
| `v1_layout_indicador.pdf` | `POST /api/indicators/1/export-pdf` (periodo personalizado Mayo 2026) | 2 |
| `v1b_layout_indicador.pdf` | `POST /api/indicators/1/export-pdf` (periodo `ultima_prueba`) | 2 |
| `control_v2_simce_2025_octubre.pdf` | Motor v2 con datos 2025 — control para aislar un bug de datos | 13 |

**Indicador/motor que corresponde a Pullinque:** indicador **1 "SIMCE"** (`report_engine_type = "simce"`), motor **v2**.
Verificado en datos: la faceta `Establecimiento` de las métricas 4 y 5 (las del indicador 1) contiene un único valor, `"Pullinque"`. El indicador 6 "SIMCE Panguipulli" queda descartado por tres razones: su propia descripción en DB dice *"paralela a SIMCE Pullinque"*, su esquema no tiene secciones de pregunta / eje temático / puntaje SIMCE (que la referencia sí trae), y su `pdf_layout` está vacío (`{}`).

---

## 1. Inventario de la referencia (14 páginas)

Elementos comunes a **todas** las páginas:

- **Encabezado:** logo *People Help People* (izquierda), tres líneas de texto centradas — `Informe Ensayo SIMCE N° 1` / `Matemáticas 2° Medio` / `Mayo 2026` — y escudo del **Liceo Pullinque** (derecha). Debajo, una línea horizontal.
- **Pie:** línea horizontal, `Miguel Godoy Díaz` a la izquierda y número de página a la derecha.
- **Estilo de tablas:** bordes negros finos en todas las celdas, fila de cabecera en negrita, tabla centrada horizontalmente y ajustada a su contenido (no al ancho completo de la página).

| # | Pág. | Sección | Tipo | Contenido | Observaciones de estilo |
|---|---|---|---|---|---|
| 1 | 1 | Portada (sin página propia) | Texto | Título grande `Informe Ensayo SIMCE N° 1 - Matemáticas 2° Medio` en dos líneas; debajo, subtítulo `Liceo Técnico Profesional People Help People Pullinque` | El título arranca en la misma página que las dos primeras tablas: no hay portada dedicada |
| 2 | 1 | Cuadro Resumen Logro por Curso | Tabla | Columnas `Curso, Alumnos, Promedio, Mínimo, Máximo`. 4 filas: 2A(29), 2B(24), 2C(21), 2D(22). Valores en % | Números alineados a la derecha; cursos etiquetados `2A…2D` |
| 3 | 1 | Resumen Puntaje SIMCE por Curso | Tabla | Mismas columnas, valores en puntaje SIMCE entero (236, 216, 227, 216) | Idéntico formato a la anterior |
| 4 | 2 | Rendimiento Promedio por Curso | Gráfico de barras | Una barra por curso con etiqueta de valor encima (40%, 31%, 36%, 31%) | **Un color distinto por curso** (verde, naranja, azul-lila, rosa). Eje Y fijo 0–100 % con grilla punteada; eje X `Curso` con etiquetas rotadas; borde negro alrededor del área de trazado |
| 5 | 3 | Distribución de Puntaje SIMCE por Curso | Boxplot | Una caja por curso, con outlier visible en 2B (~278) | Un color por caja (azul, naranja, verde, rojo); mediana en negro grueso; eje Y automático (~175–295) |
| 6 | 4 | Cantidad de Alumnos por Nivel de Logro | Barras apiladas | Una barra por curso, apilada por nivel, con el conteo escrito dentro de cada segmento | Colores por nivel: Insuficiente rojo, Elemental naranja, Adecuado verde-azulado. Leyenda `Nivel de Logro` en caja arriba a la derecha; eje Y en pasos de 3 |
| 7 | 5 | Logro Promedio por Habilidad | Barras agrupadas | Grupos por curso; dentro de cada grupo, una barra por habilidad, con % encima | **Orden de series curricular**: Representar, Manipulación de expresiones matemáticas, Resolver problemas, Modelar, Argumentar y comunicar. Leyenda `Habilidad`. Eje Y etiquetado `Logro` |
| 8 | 5 | Logro Promedio por Eje Temático | Barras agrupadas | Igual estructura, series por eje | **Orden curricular**: Números, Álgebra y funciones, Geometría, Probabilidad y estadística. Comparte página con la sección anterior |
| 9 | 6 | Reporte de estadísticas por pregunta | Tabla | Una fila por pregunta (1–30). Columnas: `Pregunta, A, %A, B, %B, C, %C, D, %D, E, %E, Correcta, Distractor` | **Conteos enteros de alumnos** (62, 15, 11, 7, 0), no proporciones. **Heatmap** de fondo verde/amarillo sobre las celdas destacadas. Preguntas en **orden numérico 1→30**. Cabe completa en el ancho de página |
| 10 | 7 | Logro por Alumno – 2A | Tabla | Columnas `Estudiante, Logro, SIMCE, Nivel, Avance`. 29 filas ordenadas de mayor a menor logro | Nombres en mayúsculas; una fila por línea (sin envolver texto); Avance en 0 % para todos (es la 1.ª prueba del año) |
| 11 | 8 | Logro por Pregunta – 2A | Tabla | Columnas `N° Pregunta, Habilidad, Eje Temático, Logro`. 30 filas ordenadas por logro descendente | El número de pregunta aparece poblado (9, 1, 5, 16…) |
| 12 | 9 | Logro por Alumno – 2B | Tabla | Igual estructura, 22 filas | Cada tabla arranca en **página nueva** |
| 13 | 10 | Logro por Pregunta – 2B | Tabla | Igual estructura, 30 filas | |
| 14 | 11 | Logro por Alumno – 2C | Tabla | Igual estructura, 21 filas | |
| 15 | 12 | Logro por Pregunta – 2C | Tabla | Igual estructura, 30 filas | |
| 16 | 13 | Logro por Alumno – 2D | Tabla | Igual estructura, 22 filas | |
| 17 | 14 | Logro por Pregunta – 2D | Tabla | Igual estructura, 30 filas | |

En términos de **tipos de sección** distintos, la referencia tiene **12**: encabezado/pie, portada, 2 tablas resumen, 4 gráficos de establecimiento, 1 tabla de estadística por pregunta, y 2 tablas que se repiten por curso.

**Orden general:** resumen numérico → gráficos del establecimiento → detalle por pregunta del establecimiento → detalle por curso (alumnos y preguntas alternados, curso por curso).

---

## 2. Cómo se crea hoy ese informe

El camino que reproduce este informe es el **motor v2 "formato oficial"**, no el motor por layout. En términos simples:

1. El usuario entra a la página del indicador **SIMCE** (id 1) y en el selector de informes elige la tarjeta **"Informe de evaluación SIMCE (formato oficial)"**. Esa tarjeta la publica `backend/routers/indicators.py` (endpoint `report-options`, líneas 462-491), leyendo el registro de informes custom.
2. El frontend llama a **`POST /api/reports/custom/simce`** con `indicator_id: 1` y los filtros de la corrida (`Asignatura: Matemáticas`, `Mes: MAYO`, `Año: 2026`). El endpoint vive en `backend/routers/reports.py:191`.
3. Ese endpoint valida que el informe aplique al indicador comparando `ENGINE_TYPES = ["simce"]` (declarado en `backend/rgenerator/reports/custom/simce.py`) contra el `report_engine_type` del indicador, y delega en `generar_pdf_v2` de `backend/rgenerator/reports/dispatch_v2.py`.
4. `dispatch_v2` exige **al menos un filtro temporal** (Mes o N° de prueba) para no mezclar dos evaluaciones en el mismo informe, separa los filtros estructurales de los temporales, resuelve la asignatura, e inyecta el nombre de la organización como pie de página.
5. Los datos salen de la base, no de Excel: `backend/rgenerator/reports/data.py` arma dos DataFrames desde `metric_data` — **métrica 4** ("Resultados SIMCE por Estudiante") y **métrica 5** ("Resultados SIMCE por Pregunta") — traduciendo cada dimensión guardada (Curso, Mes, Asignatura, Pregunta, Habilidad, Eje Temático…) a su nombre de columna legible.
6. `backend/rgenerator/reports/simce/crear_informe.py` calcula primero las columnas derivadas del año completo (Promedio Año, Avance, Mejora) y recién después recorta a la prueba del mes pedido, para que la tendencia se calcule sobre todo el histórico.
7. La estructura del informe está declarada en **`backend/rgenerator/reports/simce/esquema.json`**: una lista `secciones_fijas` (las tablas y gráficos del establecimiento) y un bloque `secciones_dinamicas` que se repite por curso. Cada sección nombra la función que la dibuja.
8. Esas funciones viven en **`backend/rgenerator/reports/charts.py`** (`grafico_barras_promedio_por`, `boxplot_valor_por_curso`, `alumnos_por_nivel_cualitativo`, `valor_promedio_agrupado_por`) y **`backend/rgenerator/reports/tables.py`** (`resumen_estadistico_basico`, `crear_tabla_estadistica_por_pregunta`, `tabla_logro_por_alumno`, `tabla_logro_por_pregunta`).
9. Finalmente `backend/rgenerator/reports/runtime.py` compone el HTML con el encabezado/pie de `branding.py` y lo convierte a PDF con WeasyPrint.

En resumen: **para cambiar qué secciones salen y en qué orden se edita `esquema.json`; para cambiar cómo se ve cada gráfico o tabla se editan `charts.py` / `tables.py`; para cambiar logos, encabezado y pie se edita `branding.py`.**

**El otro camino** (`POST /api/indicators/1/export-pdf`, motor "weasyprint" por layout, configurado en `Indicator.pdf_layout`) también funciona y también se ofrece en el selector como *"Informe última prueba"*, pero produce un documento mucho más corto y genérico: no es el que corresponde a este informe.

---

## 3. Comparación sección por sección

Referencia = `informe.pdf`. Actual = `v2_custom_simce_matematicas_mayo.pdf` salvo que se indique otra cosa.

| Sección de la referencia | ¿Existe hoy? | Dónde (motor / página) | Diferencias |
|---|---|---|---|
| **Encabezado con logos PHP + Pullinque** | Sí | v2, todas las páginas | Las 3 líneas dicen `Informe Ensayo SIMCE / Matemáticas / MAYO 2026`. **Falta el `N° 1`** y **falta el nivel `2° Medio`**; el mes va en mayúsculas (`MAYO`) donde la referencia usa `Mayo`. Logos idénticos y bien posicionados |
| **Pie de página** | Sí | v2, todas las páginas | Dice `Fundación PHP` en vez de `Miguel Godoy Díaz`. **Es un cambio deliberado** (branding neutro, commit `bb1f865`) — no es una brecha. Numeración de página igual |
| **Título + subtítulo del establecimiento** | Parcial | v2 pág. 1 | El título es solo `Informe Ensayo SIMCE`: **le falta `N° 1 - Matemáticas 2° Medio`**. El subtítulo dice `Resumen de la prueba seleccionada` en vez del nombre del colegio (`Liceo Técnico Profesional People Help People Pullinque`) |
| **Cuadro Resumen Logro por Curso** | Sí | v2 pág. 1 | Equivalente. Mismos valores (40/31/36/31 %) y mismas columnas. Solo cambia el título (`Resumen de Logro por Curso`) y la etiqueta de curso (`II A` vs `2A`) |
| **Resumen Puntaje SIMCE por Curso** | Sí | v2 pág. 1 | Equivalente. Mismos valores (236/216/227/216) |
| **Rendimiento Promedio por Curso** | Sí | v2 pág. 1 | **Idéntico**: mismos colores por curso, mismo eje 0–100 %, mismas etiquetas de valor. Única diferencia: en la referencia ocupa página propia; aquí comparte página con las dos tablas |
| **Distribución de Puntaje SIMCE por Curso (boxplot)** | Sí | v2 pág. 2 | **Idéntico** en cajas, colores, outlier de II B y escala. El título del gráfico ahora lleva tilde (`Distribución`), la referencia no la tenía — mejora |
| **Cantidad de Alumnos por Nivel de Logro** | Sí | v2 pág. 3 | **Idéntico**: mismos apilados (19+10, 23+1, 15+6, 21+1), mismos colores y leyenda |
| **Logro Promedio por Habilidad** | Sí, con diferencia de orden | v2 pág. 4 | Mismos valores. **El orden de las series es alfabético** (Argumentar, Manipulación, Modelar, Representar, Resolver) en vez del orden curricular de la referencia (Representar, Manipulación, Resolver, Modelar, Argumentar). Como el color se asigna por posición, **cada habilidad queda de un color distinto** al de la referencia (p. ej. "Representar" es verde en la referencia y rosa hoy). Eje Y rotulado `Logro (%)` vs `Logro` |
| **Logro Promedio por Eje Temático** | Sí, con diferencia de orden | v2 pág. 4 | Mismo problema: orden alfabético (Geometría, Números, Probabilidad, Álgebra) en vez de curricular (Números, Álgebra, Geometría, Probabilidad), con el consiguiente cambio de colores |
| **Reporte de estadísticas por pregunta** | **No (tabla vacía)** | v2 pág. 5 | **Sale solo la fila de cabecera, sin ningún dato.** Causa raíz confirmada abajo. Además, el control con datos 2025 (`control_v2_simce_2025_octubre.pdf`, págs. 5-6) muestra que aun con datos la tabla tiene 4 defectos: preguntas en **orden lexicográfico** (1, 10, 11, 12, … 2, 20, 21…) en vez de numérico; valores como **proporciones con ruido de coma flotante** (`0.5700000000000001`) en vez de conteos enteros; **la tabla se desborda del margen derecho** y se cortan las columnas D, E, Correcta y Distractor; y **no tiene el heatmap** verde/amarillo |
| **Logro por Alumno – por curso** | Parcial | v2 págs. 6, 8, 10, 12 | Mismos alumnos, mismos valores y mismo orden. Pero: **agrega dos columnas que la referencia no tiene** (`Promedio Año`, que aquí es redundante porque repite el Logro al haber un solo mes, y `Mejora`); la columna `Avance` sale **vacía (`—`)** donde la referencia mostraba `0%`; y los nombres largos **se parten en dos líneas**, engordando la tabla |
| **Logro por Pregunta – por curso** | Parcial | v2 págs. 6-7, 8-9, 10-11, 12-13 | Mismas filas, mismos porcentajes y mismo orden por logro. Pero la columna **`N° Pregunta` sale toda en `—`**, lo que deja la tabla inutilizable para el docente (no se puede saber de qué pregunta se habla) |
| **Un curso por página** | No | v2 págs. 6-13 | La referencia arranca cada tabla en página nueva. Hoy las tablas se encadenan: la de preguntas de II A empieza al pie de la pág. 6 y se derrama a la 7, y así con cada curso |

### Elementos que el sistema genera hoy y la referencia NO tiene

| Elemento | Dónde | Comentario |
|---|---|---|
| Gráfico **"Evolución del Logro Promedio por Curso y Mes"** | v2 pág. 2 | **Degenerado**: como el informe está filtrado a un solo mes, dibuja una única serie (MAYO) — cuatro barras verdes idénticas al gráfico de la pág. 1. Ruido visual |
| Gráfico **"Evolución del Puntaje SIMCE Promedio por Curso y Mes"** | v2 pág. 3 | Mismo problema: una sola serie, redundante con la tabla de la pág. 1 |
| Columnas `Promedio Año` y `Mejora` | v2, tablas de alumno | No están en la referencia; con un solo mes de datos no aportan |
| Subtítulo `Resumen de la prueba seleccionada` | v2 pág. 1 | Ocupa el lugar donde la referencia pone el nombre del establecimiento |

### El motor v1 (layout del indicador) frente a la referencia

`v1_layout_indicador.pdf` produce **2 páginas** contra las 14 de la referencia. Cubre: una tabla resumen por curso (pág. 1), el gráfico de logro promedio por curso (pág. 1), el apilado por nivel de logro (pág. 2) y un gráfico de habilidad **agregado a nivel establecimiento, sin desglose por curso** (pág. 2). Le faltan por completo: puntaje SIMCE, boxplot, eje temático, estadística por pregunta y **todas** las tablas por curso. Además muestra los porcentajes como decimales crudos (`0.4`, `0.3`) y **no incluye el escudo del colegio**. `v1b` (periodo `ultima_prueba`) es prácticamente idéntico.

---

## 4. Causa raíz de las dos fallas críticas

Ambas fallas (tabla de estadísticas vacía y `N° Pregunta` en blanco) tienen **la misma causa, y es un problema de datos, no del motor de informes**:

> En la métrica 5 ("Resultados SIMCE por Pregunta"), **las 260 filas cargadas para 2026-MAYO no tienen guardada la dimensión `Pregunta` (id 11)**. Son las únicas del dataset en esa situación.

Conteo por carga, sobre las 1.680 filas de la métrica 5 en la organización 1:

| Año | Mes | Asignatura | ¿Tiene `Pregunta`? | ¿Tiene `Habilidad`? | ¿Tiene `Eje Temático`? | Filas |
|---|---|---|---|---|---|---|
| 2025 | ABRIL–NOVIEMBRE | ambas | **Sí** | parcial | **No** | 1.420 |
| **2026** | **MAYO** | Lenguaje | **No** | Sí | Sí | 140 |
| **2026** | **MAYO** | Matemáticas | **No** | Sí | Sí | 120 |

Es decir, la ingesta de 2026 usó un mapeo de columnas distinto al de 2025: ganó `Eje Temático` pero **perdió `Pregunta`**.

Las consecuencias son directas:

- `crear_tabla_estadistica_por_pregunta` (`backend/rgenerator/reports/tables.py:282`) hace `df.groupby("Pregunta")`. Con la columna 100 % nula el agrupamiento devuelve cero grupos → **tabla vacía**.
- `tabla_logro_por_pregunta` imprime la columna tal cual → **`—` en todas las filas**.

El control con datos 2025 (`control_v2_simce_2025_octubre.pdf`) confirma el diagnóstico: **la misma tabla se puebla correctamente** cuando la dimensión existe. El motor está bien; los datos de 2026 están incompletos.

Un segundo desajuste de datos, independiente: los campos `A`–`E` de la métrica 5 guardan **proporciones** (`0.636`) y no **conteos de alumnos** (`62`). La referencia muestra conteos. Aun corrigiendo la dimensión `Pregunta`, esas columnas no coincidirán con la referencia sin una conversión.

---

## 5. Veredicto de cobertura

Sobre las **12 secciones** distintas de la referencia:

| Estado | Cantidad | Secciones |
|---|---|---|
| **Cubiertas** (equivalentes) | **7** | Encabezado/pie con logos, Resumen Logro por Curso, Resumen Puntaje SIMCE, Rendimiento Promedio por Curso, Boxplot, Nivel de Logro apilado, y (con diferencia de orden/color) Habilidad y Eje Temático |
| **Parciales** | **4** | Portada/título, Logro por Alumno, Logro por Pregunta, y el propio encabezado si se exige el `N° 1 / 2° Medio` |
| **Faltantes o rotas** | **1** | Reporte de estadísticas por pregunta (sale vacía) |

**Cobertura: ~58 % de las secciones sale idéntica o equivalente; ~92 % está presente en alguna forma; una sección sale completamente vacía.** Estructuralmente el motor v2 ya replica el informe: el grueso de la distancia son datos incompletos y detalles de presentación, no secciones inexistentes.

---

## 6. Brechas priorizadas

### P0 — Bloqueantes (el informe no es entregable así)

1. **Recargar la dimensión `Pregunta` en los datos 2026 de la métrica 5.** Es la causa única de la tabla vacía y de los `—`. Corrige de golpe 5 de las 14 páginas de detalle. Es trabajo de ingesta/ETL, no del motor.
2. **Arreglar el orden de las preguntas en la tabla de estadísticas.** Hoy ordena como texto (1, 10, 11, … 2, 20). Convertir a numérico antes del `sort_values` en `crear_tabla_estadistica_por_pregunta` (`tables.py:302`).
3. **Arreglar el desborde de la tabla de estadísticas por pregunta.** Con 13 columnas se sale del margen derecho y se pierden `D`, `E`, `Correcta` y `Distractor`. Necesita ancho de fuente/columna reducido o página apaisada para esa sección.

### P1 — Necesarias para "verse igual"

4. **Completar las tres líneas del encabezado**: `Informe Ensayo SIMCE N° 1` + `Matemáticas 2° Medio` + `Mayo 2026`. Falta el número de ensayo y el nivel; el mes debería ir capitalizado, no en mayúsculas. Se toca en `lineas_encabezado_prueba` (`branding.py`).
5. **Poner el nombre del establecimiento como subtítulo de portada** en vez de `Resumen de la prueba seleccionada`, y completar el título con asignatura y nivel. Se toca en `esquema.json` (`title` / `subtitle`) más el override que arma `crear_informe.py`.
6. **Fijar el orden curricular de las series** de Habilidad (Representar, Manipulación, Resolver, Modelar, Argumentar) y de Eje Temático (Números, Álgebra, Geometría, Probabilidad). Esto además devuelve los colores originales, porque hoy se asignan por posición alfabética. Se resuelve agregando un parámetro de orden explícito a `valor_promedio_agrupado_por` y declarándolo en `esquema.json`.
7. **Un salto de página antes de cada tabla por curso.** El esquema ya soporta `break_before: true` (lo usa la sección de estadísticas); falta habilitarlo en las `secciones_dinamicas`.
8. **Quitar las dos secciones "Evolución … por Curso y Mes"** cuando el informe está filtrado a un solo mes: hoy dibujan una sola serie y duplican información. Alternativamente, omitirlas condicionalmente cuando hay un único punto temporal.

### P2 — Pulido

9. **Recortar las columnas de la tabla de alumnos** a las cinco de la referencia (`Estudiante, Logro, SIMCE, Nivel, Avance`), o al menos ocultar `Promedio Año` y `Mejora` cuando hay un solo mes; y mostrar `0%` en vez de `—` en `Avance` para la primera prueba del año.
10. **Recuperar el heatmap** verde/amarillo de la tabla de estadísticas por pregunta.
11. **Convertir `A`–`E` de proporción a conteo** de alumnos en la tabla de estadísticas, para igualar la referencia (y de paso eliminar el ruido de coma flotante tipo `0.5700000000000001`).
12. **Unificar la etiqueta de curso**: la referencia usa `2A…2D`, el sistema `II A…II D`. Es un tema de normalización de datos; conviene decidir cuál es la forma canónica.

### Qué motor conviene usar como base

**El motor v2 (`custom/simce`), sin dudarlo.** Ya reproduce la estructura completa del informe —las 12 secciones existen, 7 salen idénticas— y su esquema declarativo (`esquema.json`) permite cerrar la mayoría de las brechas P1 editando JSON, sin tocar código de render. El motor v1 por layout está a 2 páginas de 14 y carecería de las tablas por curso, la estadística por pregunta y el boxplot: llevarlo a paridad significaría reimplementar desde cero lo que v2 ya hace. La recomendación es dejar v1 como informe genérico/rápido de dashboard y consolidar v2 como el "formato oficial".

---

## Anexo — Cómo reproducir

```bash
docker compose -f docker-compose.dev.yml up -d      # backend en :8001

# Motor v2 — formato oficial (el que corresponde)
POST http://localhost:8001/api/reports/custom/simce
{"indicator_id": 1,
 "filtros": {"Asignatura": "Matemáticas", "Mes": "MAYO", "Año": "2026"}}

# Motor v1 — layout del indicador
POST http://localhost:8001/api/indicators/1/export-pdf
{"periodo": {"tipo": "personalizado",
             "filtros": {"Asignatura": "Matemáticas", "Mes": "MAYO", "Año": "2026"}}}

# Control que aísla el bug de datos (2025 sí tiene la dimensión Pregunta)
POST http://localhost:8001/api/reports/custom/simce
{"indicator_id": 1,
 "filtros": {"Asignatura": "Matemáticas", "Mes": "OCTUBRE", "Año": "2025"}}
```

Los valores reales de los filtros se consultan en `GET /api/metrics/4/data/facets` y `GET /api/metrics/5/data/facets`. Nótese que la asignatura se llama **`Matemáticas`** (no `MATEMATICA`) y el mes va en mayúsculas (`MAYO`).

### Archivos citados

- `backend/routers/reports.py:191` — endpoint `POST /api/reports/custom/{nombre}`
- `backend/routers/indicators.py:875` — endpoint `POST /{id}/export-pdf` (motor v1)
- `backend/routers/indicators.py:462-491` — publicación de la tarjeta del informe custom
- `backend/rgenerator/reports/custom/simce.py` — metadata del informe custom
- `backend/rgenerator/reports/dispatch_v2.py` — despacho compartido del motor v2
- `backend/rgenerator/reports/data.py` — carga de DataFrames desde `metric_data`
- `backend/rgenerator/reports/simce/crear_informe.py` — orquestación del informe SIMCE
- `backend/rgenerator/reports/simce/esquema.json` — estructura declarativa de secciones
- `backend/rgenerator/reports/tables.py:247-303` — `crear_tabla_estadistica_por_pregunta`
- `backend/rgenerator/reports/charts.py` — funciones de gráficos
- `backend/rgenerator/reports/branding.py` — encabezado, pie y logos
- `backend/rgenerator/reports/runtime.py` — composición HTML → PDF (WeasyPrint)
