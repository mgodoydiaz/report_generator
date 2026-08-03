# QA de informes — Indicador **SIMCE** (id 1, org 1)

- **Fecha**: 2026-08-03
- **Origen de los PDFs**: `data/output/qa_indicadores/2026-08-03/`
- **PNG revisados**: `data/output/qa_indicadores/2026-08-03/png/simce/` (150 dpi, 39 páginas)
- **Motor**: `report_engine_type = simce` → motor único `backend/rgenerator/reports/custom/simce.py`
- **Métricas**: id 4 `Resultados SIMCE por Estudiante` (1286 filas) · id 5 `Resultados SIMCE por Pregunta` (1680 filas)
- **Cobertura de datos**: 2025-04 → 2026-05. Última evaluación: **MAYO 2026 (prueba 1)**, Lenguaje, 100 estudiantes únicos, 4 cursos (II A–D), 35 preguntas.

## Puntaje total: **72 / 100**

| Dimensión | Puntaje | Comentario |
|---|---|---|
| Correctitud de datos | **30 / 40** | Todo lo verificable cuadra al 100 %, salvo la tabla de alternativas A–E (columna que no es un conteo) y un sesgo sistemático de ~1 pp en %A–%E. |
| Cobertura de período | **12 / 15** | `ultima_prueba` = exactamente MAYO 2026. `anual` = todo 2026 (que solo tiene esa evaluación). `semestral` 400 por anclaje al semestre calendario. |
| Calidad visual | **21 / 30** | El motor único sale profesional y sin artefactos. Restan paginación (tablas huérfanas, páginas casi vacías) y el camino legacy `custom:simce` con paleta y gráficos degenerados. |
| Disponibilidad de modos | **9 / 15** | 4/5 modos generan. Pero el modo estrella llega al usuario degradado (2 págs) por el bug de `engine` de la UI. |

---

## 1. Verificación de datos: PDF vs recálculo sobre `metric_data`

Recálculo hecho con pandas directamente sobre `metric_data` (métricas 4 y 5, `org_id = 1`), reconstruyendo las dimensiones desde `dimensions_json` (3 Establecimiento, 4 Año, 5 Curso, 6 RUT, 8 Asignatura, 9 Mes, 10 N Prueba, 11 Pregunta, 12 Habilidad, 13 Eje Temático).

### 1.1 Resumen de logro y puntaje por curso — `ultima_prueba` pág. 1

| Métrica | Curso | PDF | Recalculado | ¿Cuadra? |
|---|---|---|---|---|
| Alumnos | II A / B / C / D | 29 / 24 / 25 / 22 | 29 / 24 / 25 / 22 (`RUT.nunique()`) | ✅ |
| Total alumnos | — | 100 (n=100 en pág. 3) | 100 únicos, 100 filas | ✅ |
| Rend promedio | II A / B / C / D | 54 % / 51 % / 49 % / 45 % | 53.71 / 51.27 / 49.20 / 45.18 | ✅ |
| Rend mínimo | II A / B / C / D | 33 % / 24 % / 30 % / 12 % | 33.3 / 24.2 / 30.3 / 12.1 | ✅ |
| Rend máximo | II A / B / C / D | 76 % / 79 % / 79 % / 76 % | 75.8 / 78.8 / 78.8 / 75.8 | ✅ |
| SIMCE promedio | II A / B / C / D | 264 / 259 / 255 / 246 | 264.48 / 259.17 / 254.76 / 246.18 | ✅ |
| SIMCE mín / máx | II A | 221 / 312 | 221 / 312 | ✅ |
| SIMCE mín / máx | II D | 175 / 312 | 175 / 312 | ✅ |

> **Nota positiva**: el conteo de "Alumnos" usa estudiantes únicos de la métrica 4, no filas de la métrica de preguntas. El bug histórico **no** está presente (con la métrica 5 daría 35 por curso).

### 1.2 Niveles de logro — pág. 3

| Bloque | PDF | Recalculado | ¿Cuadra? |
|---|---|---|---|
| II A (Ins/Ele/Ade) | 7 / 15 / 7 | 7 / 15 / 7 | ✅ |
| II B | 8 / 11 / 5 | 8 / 11 / 5 | ✅ |
| II C | 13 / 8 / 4 | 13 / 8 / 4 | ✅ |
| II D | 11 / 8 / 3 | 11 / 8 / 3 | ✅ |
| Composición global | 19 % (19) / 42 % (42) / 39 % (39), n=100 | 19 / 42 / 39 sobre 100 | ✅ |
| Estudiantes en Riesgo (págs. 4–5) | 39 filas | 39 estudiantes en `Logro = Insuficiente` | ✅ |

### 1.3 Logro por habilidad y eje — pág. 4

| Curso | PDF (Interpretar / Localizar / Reflexionar) | Recalculado | ¿Cuadra? |
|---|---|---|---|
| II A | 53 / 53 / 42 | 53.3 / 53.4 / 41.8 | ✅ |
| II B | 49 / 60 / 37 | 49.4 / 59.7 / 37.0 | ✅ |
| II C | 45 / 63 / 38 | 45.1 / 62.7 / 37.9 | ✅ |
| II D | 41 / 49 / 43 | 40.6 / 49.2 / 43.2 | ✅ |

| Curso | PDF (LÍRICA / NARRATIVA / TMC / TMCFA) | Recalculado | ¿Cuadra? |
|---|---|---|---|
| II A | 38 / 44 / 69 / 37 | 38.2 / 44.0 / 69.3 / 37.4 | ✅ |
| II B | 44 / 45 / 62 / 28 | 44.4 / 45.5 / 61.8 / 27.5 | ✅ |
| II C | 35 / 48 / 59 / 27 | 35.3 / 47.7 / 58.9 / 27.2 | ✅ |
| II D | 29 / 39 / 59 / 29 | 28.8 / 38.6 / 59.2 / 29.3 | ✅ |

### 1.4 Logro por pregunta y por curso — págs. 7–14

| Curso | PDF (top preguntas) | Recalculado | ¿Cuadra? |
|---|---|---|---|
| II A | Q10 97 %, Q7 93 %, Q20 86 %, Q6 83 %, Q11 79 % | 96.6 / 93.1 / 86.2 / 82.8 / 79.3 | ✅ |
| II D | Q11 77 %, Q29 73 %, Q10 73 %, Q34 68 %, Q24 68 % | 77.3 / 72.7 / 72.7 / 68.2 / 68.2 | ✅ |

### 1.5 Comparación vs año anterior — `anual` / `personalizado` pág. 1

| Curso | PDF "Promedio 2025" | Recalculado (media Rend Lenguaje 2025) | ¿Cuadra? |
|---|---|---|---|
| II A | 55 % | 54.74 % | ✅ |
| II B | 46 % | 45.92 % | ✅ |
| II C | 50 % | 50.16 % | ✅ |
| II D | 51 % | 50.72 % | ✅ |

> **Salvedad de interpretación (no es bug)**: "II A 2026" y "II A 2025" son cohortes distintas. La columna compara el curso como unidad, no a los mismos estudiantes. Convendría una nota al pie.

### 1.6 ❌ Estadística por Pregunta del Establecimiento — `ultima_prueba` pág. 6 / `custom` pág. 5

**Aquí está el hallazgo de datos.** La métrica 5 guarda A/B/C/D/E como **proporciones por curso** (0–1). El informe hace `groupby("Pregunta")[A..E].sum()` y publica el resultado bajo encabezados `A`, `B`, `C`, `D`, `E` que el lector interpreta como conteo de alumnos.

| Pregunta | Columna | PDF | Conteo real de alumnos (Σ proporción × N del curso) | Δ |
|---|---|---|---|---|
| 1 | A | **1.04** | **26** | ×25 |
| 1 | B | **1.15** | **29** | ×25 |
| 2 | D | **2.80** | **71** | ×25 |
| 3 | D | **2.68** | **66** | ×25 |
| 8 | A | **2.78** | **70** | ×25 |
| 10 | B | **3.37** | **85** | ×25 |
| 11 | A | **3.12** | **78** | ×25 |
| — | Σ fila | ≈ 4.00 (= n.º de cursos) | 100 (= n.º de alumnos) | — |

Y el porcentaje asociado es la **media no ponderada** de las proporciones por curso, no el % del establecimiento:

| Pregunta | PDF %  | % ponderado real | Δ |
|---|---|---|---|
| Q1 %C | 19 % | 18.2 % | −0.8 pp |
| Q6 %B | 63 % | 64.0 % | +1.0 pp |
| Q7 %C | 77 % | 78.0 % | +1.0 pp |
| Q10 %B | 84 % | 85.0 % | +1.0 pp |
| Q9 %D | 57 % | 57.4 % | +0.4 pp |
| Q3 %A | 19 % | 20.0 % | +1.0 pp |

**Atenuante**: la referencia dorada del dueño (`/mnt/c/Users/magod/Desktop/PDF_test/informe_simce.pdf`, pág. 5) trae **el mismo defecto**, y peor: valores con ruido binario (`0.15000000000000002`) y preguntas ordenadas 1, 10, 11, 12… El output actual es una mejora estricta en formato y orden. Es un defecto **heredado**, no una regresión.

### 1.7 Datos de origen incompletos (no es bug del motor)

- **Q17 y Q35** llegan con `Correcta = NULL` en los 4 cursos → `Logro = 0.0` para todos. El PDF lo muestra honestamente como `—` en Correcta, pero imprime `0 %` de logro en todas las tablas por curso, lo que se lee como "nadie acertó" en vez de "sin clave de corrección".
- La columna **E** está en 0.00 / 0 % en las 35 preguntas de esta evaluación (ocupa 2 de 13 columnas sin aportar).

---

## 2. Cobertura de período

| Modo | Encabezado | Evaluaciones realmente contenidas | Veredicto |
|---|---|---|---|
| `ultima_prueba` | `MAYO 2026 (prueba 1)` | Solo MAYO 2026 p1 (100 alumnos = conteo exacto de esa evaluación) | ✅ Correcto |
| `anual` | `2026` | Solo MAYO 2026 p1 — porque 2026 no tiene otra evaluación cargada. Añade columna "Promedio 2025". Declara explícitamente la falta de evolución. | ✅ Correcto por dato; el modo no aporta nada extra sobre `ultima_prueba` hoy |
| `personalizado` | `MAYO 2026` | Solo MAYO 2026 p1 | ✅ Correcto |
| `semestral` | — | HTTP 400 | ⚠️ Coherente pero mal UX (ver H-05) |
| `custom:simce` | `MAYO 2026` | Solo MAYO 2026 p1 | ⚠️ Pero incluye secciones "Evolución … por Curso y Mes" que no tienen evolución que mostrar |

---

## 3. Rúbrica visual

### Lo que está bien

- Pie izquierdo **"Fundación PHP"** en las 39 páginas ✅
- Encabezado con logo Fundación PHP + escudo Pullinque + período correcto en las 5 salidas ✅
- **Cero** `nan`, `None`, `NaT`, `inf`, `undefined` o tracebacks en el texto de los 5 PDFs ✅
- **Cero** decimales con ruido de coma flotante (`0.5700000000000001`) — la regresión QA 2026-07-30 P0-B sigue cerrada ✅
- Preguntas en **orden numérico 1…35** en la tabla del establecimiento — la regresión P0-A sigue cerrada ✅
- Tablas dentro de márgenes, incluidas las 13 columnas de la estadística por pregunta ✅
- Colores de nivel del motor único = `Indicator.achievement_levels` (`#dc2626` Insuficiente, `#eab308` Elemental, `#22c55e` Adecuado) ✅
- Estados vacíos explicados con texto en caja en vez de gráfico degenerado (anual pág. 4 y 5) ✅

### Hallazgos por gravedad

| # | Gravedad | Página exacta | Hallazgo |
|---|---|---|---|
| **H-01** | 🔴 Alta | `simce_ultima_prueba_engine_weasyprint_lenguaje.pdf` págs. 1–2 | **Lo que el usuario recibe hoy**: 2 págs en vez de 14, sin escudo del colegio, título genérico "Informe SIMCE — Por evaluación", y `Rend prom.` impreso como **0.5 en los 4 cursos** (proporción a 1 decimal en vez de %), con las barras del gráfico todas etiquetadas `0.5`. Se pierde toda la discriminación entre cursos. Faltan estadística por pregunta, eje temático, estudiantes en riesgo y las 8 págs de detalle por curso. Además el pie repite el período con espacio final (`"MAYO 2026 (prueba 1) "`). |
| **H-02** | 🔴 Alta | `ultima_prueba` pág. 6 · `custom` pág. 5 | Columnas A–E publican la **suma de proporciones por curso** (rango 0–4) bajo un encabezado que se lee como conteo de alumnos. Ver §1.6. |
| **H-03** | 🟠 Media | `custom` pág. 3 | El camino legacy `custom:simce` pinta "Cantidad de Alumnos por Nivel de Logro y Curso" con la **paleta por defecto** (rojo-naranjo / naranjo / turquesa) en vez de `achievement_levels`. En la misma máquina, `anual` pág. 3 y `ultima_prueba` pág. 3 sí usan los colores correctos → inconsistencia visible entre dos informes del mismo indicador. |
| **H-04** | 🟠 Media | `custom` págs. 2 y 3 | Gráficos degenerados: "Evolución del Logro Promedio por Curso y Mes" y "Evolución del Puntaje SIMCE Promedio por Curso y Mes" con **serie única (`Mes = MAYO`)** — quedan como barras por curso, duplicando exactamente el contenido de la pág. 1. La leyenda "Mes: MAYO" con un solo ítem lo hace evidente. |
| **H-05** | 🟠 Media | — (`semestral` 400) | El resolver ancla al **semestre calendario**; como el 2.º semestre 2026 (ago–dic) aún no tiene datos, el modo devuelve 400 aunque el 1.er semestre 2026 sí tiene MAYO. Coherente con la regla, pero el usuario lee "no hay informe semestral" cuando sí hay semestre con datos. |
| **H-06** | 🟡 Baja | `ultima_prueba` págs. 4→5 | Tabla huérfana: "Estudiantes en Riesgo" arranca al pie de la pág. 4 con **una sola fila** y sigue en la pág. 5 con las 38 restantes. |
| **H-07** | 🟡 Baja | `ultima_prueba` págs. 5, 10, 12, 14 · `custom` págs. 10, 13 | Las continuaciones de tabla arrancan pegadas a la regla del encabezado (sin padding superior), sin título de sección ni marca "(cont.)". |
| **H-08** | 🟡 Baja | `ultima_prueba` pág. 2 · `anual` pág. 5 · `personalizado` pág. 5 | Páginas con mucho vacío: el boxplot ocupa ~45 % de la pág. 2; las págs. 5 de anual y personalizado contienen **solo una caja de texto** de 3 líneas. |
| **H-09** | 🟡 Baja | Todas las págs. 1 | Encabezados de tabla **"Minimo" / "Maximo"** sin tilde. |
| **H-10** | 🟡 Baja | `ultima_prueba` pág. 6 | Casing inconsistente: encabezados `A B C D E` en mayúscula, valores de `Correcta` / `Distractor` en minúscula (`b`, `a, d`). |
| **H-11** | 🟡 Baja | `ultima_prueba` pág. 3 | Orden de leyenda inconsistente entre los dos gráficos de la misma página: el apilado va Insuficiente→Adecuado y la composición global va Adecuado→Insuficiente. |
| **H-12** | 🟡 Baja | `custom` pág. 3 | Etiqueta del eje Y = `Simce` (nombre de columna auto-capitalizado) en vez de "Puntaje SIMCE". |
| **H-13** | 🟡 Baja | `ultima_prueba` págs. 7, 9, 11, 13 · `custom` págs. 6, 8, 10, 12 | Las columnas **"Promedio Año", "Avance", "Mejora"** son degeneradas en `ultima_prueba`: "Promedio Año" repite exactamente "Logro" y Avance/Mejora son `—` en las 100 filas. 3 de 7 columnas sin información. |
| **H-14** | 🟡 Baja | Todas las tablas por curso | Contraste: las etiquetas numéricas sobre el segmento rojo `#dc2626` de la composición global van en azul oscuro, no en blanco — legible pero bajo. |

### Referencia dorada

`/mnt/c/Users/magod/Desktop/PDF_test/referencias/` **existe pero solo contiene `referencia_idel_panguipulli_2025.pdf`** — no hay referencia SIMCE Pullinque ahí. Se usó en su lugar `/mnt/c/Users/magod/Desktop/PDF_test/informe_simce.pdf` (14 págs, misma estructura). Conclusión de la comparación: el output actual **iguala la estructura** de la referencia y la **supera** en dos puntos (orden numérico de preguntas y formato de decimales), pero **hereda** el defecto de la columna A–E fraccionaria (§1.6).

---

## 4. Veredicto de hardcodeabilidad

SIMCE ya corre en el motor único (`backend/rgenerator/reports/custom/simce.py`). Reparto de responsabilidades:

### Se arregla en código (no es dato de origen)

| Hallazgo | Dónde |
|---|---|
| **H-02** (A–E fraccionario + % no ponderado) | `backend/rgenerator/reports/tables.py` → `crear_tabla_estadistica_por_pregunta()`, línea ~288: `df_preguntas.groupby("Pregunta")[columnas_alternativas].sum()`. El propio `_formatear_alternativas()` documenta la ambigüedad ("La métrica guarda conteos enteros en unas cargas y proporciones en otras"). Fix: cuando los valores son proporciones, multiplicar por el N de cada curso (disponible en `estudiantes_prueba`) antes de sumar, y calcular %A–%E sobre ese conteo ponderado. Alternativa mínima: renombrar la columna a "prom." o suprimirla y dejar solo %. |
| **H-01** (engine=weasyprint mata el motor único) | `backend/routers/indicators.py` — el módulo del motor único solo se resuelve `if modo_periodo and not engine_override`. La UI (`frontend/src/pages/Results.jsx` / `GenerateReportModal.jsx`) manda `engine='weasyprint'` siempre. Fix: ignorar `engine` cuando el indicador tiene `report_engine_type`, o dejar de enviarlo desde la UI. |
| **H-03**, **H-04**, **H-12** (paleta y gráficos degenerados del camino legacy) | `backend/rgenerator/reports/simce/esquema.json` — no declara `color_overrides` (líneas de las secciones "Evolución…", ~102–124) y hardcodea las secciones de evolución sin condicionarlas a que haya ≥2 puntos temporales. `custom/simce.py:784` sí resuelve `achievement_levels`; el esquema legacy no. Fix real: retirar `reports/simce/` y hacer que `custom:simce` despache al motor único. |
| **H-06**, **H-07**, **H-08** (paginación) | `backend/rgenerator/reports/runtime.py` / plantillas en `reports/templates/` — falta `break-inside: avoid` con umbral mínimo de filas, padding superior en continuaciones y fusión de secciones con poco contenido. |
| **H-09**, **H-10**, **H-11**, **H-13**, **H-14** (pulido) | `custom/simce.py` (`columnas_renombrar`, orden de leyenda, ocultar columnas cuando toda la serie es `—`) y `reports/charts.py` (color de etiqueta según luminancia del fondo, ya contemplado en el comentario de `charts.py:125`). |
| **H-05** (semestral) | `backend/rgenerator/reports/periodos.py` — el ancla al semestre calendario debería caer al **último semestre con datos** cuando el actual está vacío, o el mensaje debería ofrecer el 1.er semestre. |

### Es dato de origen (no se arregla en el motor)

- **Q17 y Q35 sin `Correcta`** en las 4 filas de curso de MAYO 2026 → `Logro = 0.0`. Hay que corregir la carga/ETL o la planilla origen. El motor ya lo muestra como `—` sin romperse; a lo sumo podría distinguir "sin clave" de "0 % de logro".
- **Columna E vacía** en toda la evaluación: la prueba no usa quinta alternativa. Podría ocultarse dinámicamente, pero el dato es correcto.
- **2026 con una sola evaluación**: por eso `anual` ≈ `ultima_prueba`. No es un defecto del informe.

---

## 5. Páginas revisadas

**39 páginas** rasterizadas a 150 dpi y con texto extraído íntegramente:

| PDF | Págs. | Revisión visual |
|---|---|---|
| `simce_ultima_prueba_lenguaje.pdf` | 14 | imágenes 1–7, 10 + texto 1–14 |
| `simce_ultima_prueba_engine_weasyprint_lenguaje.pdf` | 2 | imágenes 1–2 + texto 1–2 |
| `simce_anual_lenguaje.pdf` | 5 | imágenes 3, 4, 5 + texto 1–5 |
| `simce_personalizado_lenguaje.pdf` | 5 | imágenes 1, 5 + texto 1–5 |
| `simce_custom_simce_lenguaje.pdf` | 13 | imágenes 1, 2, 3, 5, 6, 13 + texto 1–13 |
| **Total** | **39** | **20 páginas inspeccionadas como imagen · 39 con texto extraído** |
