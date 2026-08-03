# QA de informes — Indicador IDEL (id 3, org 1)

**Fecha**: 2026-08-03 · **Revisor**: crítico de informes (agente QA)
**Fuente de datos**: `metric_data` de la métrica 8 ("Resultados IDEL"), org 1 — 3.890 filas, establecimiento único Panguipulli.
**PDFs revisados**: `data/output/qa_indicadores/2026-08-03/`

| PDF | Motor | Págs | Revisadas |
|---|---|---|---|
| `idel_ultima_prueba.pdf` | v1 (`pdf_layout`, WeasyPrint) | 2 | 1–2 |
| `idel_semestral.pdf` | v1 (`pdf_layout_historico`) | 2 | 1–2 |
| `idel_anual.pdf` | v1 (`pdf_layout_historico`) | 2 | 1–2 |
| `idel_personalizado.pdf` | v1 (`pdf_layout_historico`) | 2 | 1–2 |
| `idel_custom_pdl_idel.pdf` | IDEL matplotlib (`scripts/report_pdl_idel.py`, 1132 líneas) | 41 | **1–41 (todas)** |

---

## Puntaje: **63 / 100**

| Dimensión | Puntos | Obtenido | Comentario |
|---|---|---|---|
| Correctitud de datos | 40 | **23** | Motor IDEL: impecable, 6/6 verificaciones exactas. Motor v1: todos los gráficos de valor rinden **0.0** (bug de rol). Cierre p41 aritméticamente correcto pero analíticamente inválido. |
| Cobertura de período | 15 | **12** | Los 4 modos resuelven bien las versiones. Personalizado ≡ anual (sin diferenciación); el motor IDEL ignora los períodos. |
| Calidad visual | 30 | **17** | Motor IDEL: tipografía y tablas de nivel profesional, etiquetas oficiales 100 % correctas. Lastrado por paleta hardcodeada, rosters ilegibles y los 2-págs degenerados. |
| Disponibilidad de modos | 15 | **11** | Único indicador con los 4 modos generados, pero el contenido de los modos está hueco. |

---

## 1. Verificación de datos (PDF vs recalculado por SQL)

Todas las consultas se corrieron sobre `metric_data` (métrica 8, org 1) vía
`docker compose -f docker-compose.dev.yml exec -T db psql`. Roles de columna del indicador:
`nivel_de_logro → "Nivel de Riesgo"`, `evaluacion_num → "Versión"`, `habilidad → "Evaluación"` (subprueba).
Claves reales del `value` JSON: `Puntaje`, `Nivel de Riesgo`, `Género`, `Evaluadora`.

### 1.1 Motor IDEL (41 págs) — 6 verificaciones independientes

| # | Qué | Página | PDF | Recalculado SQL | ¿OK? |
|---|---|---|---|---|---|
| 1 | Mapa de riesgo, 1° BÁSICO 2026/v3, % Crítico+Alto por subprueba | p1 | CT 84 · FLO 74 · FNL 26 · FSF 79 · ILP 42 · VSD 5 | 84.2 · 73.7 · 26.3 · 78.9 · 42.1 · 5.3 | ✅ |
| 2 | Cobertura de estudiantes por curso (únicos / 1 / 2 / 3 evals) | p1 | 1°: 72/4/32/36 · 2°: 87/23/37/27 · 3°: 67/5/39/23 · 4°: 63/35/22/6 · 5°: 66/31/12/23 · 6°: 35/7/9/19 | idéntico (6 filas × 4 columnas) | ✅ |
| 3 | Promedio de puntaje por subprueba × evaluación, 1° BÁSICO (42 celdas) | p2 | CT 10.7/13.6/5.4/8.0/9.9/5.4/8.0/9.9 · FLO —/27.1/—/9.2/17.4/2.5/9.2/17.4 · FNL, FSF, ILP, VSD ídem | 42/42 coinciden a 1 decimal | ✅ |
| 4 | Matriz de transición CT, 1° BÁSICO 2026/v1→v3 | p4 | C→C 12 · C→A 2 · C→Cierto 1 · A→A 1 · A→Cierto 1 | idéntico | ✅ |
| 5 | N pareado por subprueba (2026/v1→v3) | p4 | CT 17 · FLO 19 · FNL 17 · FSF 17 · ILP 19 · VSD 17 | idéntico | ✅ |
| 6 | Estudiantes en riesgo persistente, 1° BÁSICO | p5–p6 | "de 54" | 54 pares alumno×subprueba con Crít./Alto en v1 **y** v3 | ✅ |
| 7 | Distribución de niveles por versión, 2026 | p2 (1°) | v1 90/117/187/148 · v2 49/22/34/15 · v3 32/27/36/19 | idéntico | ✅ |

**Orden ordinal de niveles**: correcto en todos los gráficos apilados y matrices — Crítico → Alto Riesgo → Cierto Riesgo → Bajo Riesgo (peor→mejor, de abajo hacia arriba), **no** alfabético.
**Orden de versiones**: correcto — 2024/v1 → 2024/v2 → 2025/v1 → … → 2026/v3 en todos los ejes.
**Etiquetas de subprueba**: **100 % correctas en las 41 páginas**. Ninguna de las trampas históricas aparece: FNL siempre "Fluidez en Nombrar Letras" (nunca "Segmentación Fonémica"), FSF siempre "Fluidez en Segmentación de Fonemas", FLO siempre incluye "Oral", VSD siempre "Vocabulario Sobre Dibujos" (plural, S mayúscula). Sin `nan` en ninguna celda: los huecos se rinden como `—`.

### 1.2 Motor v1 (2 págs × 4 modos)

| # | Qué | Página | PDF | Recalculado SQL | ¿OK? |
|---|---|---|---|---|---|
| 8 | Puntaje promedio por curso, v3 2026 | `ultima_prueba` p1 | **0.0** | 21.53 | ❌ |
| 9 | Puntaje promedio por evaluación (subprueba), v3 2026 | `ultima_prueba` p2 | **0.0** en las 6 | CT 9.95 · FLO 17.37 · FNL 30.84 · FSF 27.26 · ILP 18.42 · VSD 25.32 | ❌ |
| 10 | Cuadro Resumen Puntaje por Curso | `ultima_prueba` p1 | "Sin datos disponibles." | 1° BÁSICO, n=114, avg 21.53 | ❌ |
| 11 | Evolución del puntaje promedio por curso y versión | `anual`/`semestral`/`personalizado` p1 | línea plana en **0.0** | 1° 17.43 · 2° 25.26 · 4° 47.78 · 5° 49.28 | ❌ |
| 12 | Distribución/Evolución de nivel de riesgo | los 4 modos p2 | v1 90/117/187/148 · v2 49/22/34/15 · v3 32/27/36/19 | idéntico | ✅ |

Las secciones basadas en **niveles** son exactas; las basadas en **valor** están todas en cero.

---

## 2. Cobertura de período

| Modo | Cabecera del PDF | Versiones que aparecen de verdad | Esperado | ¿OK? |
|---|---|---|---|---|
| Única (`ultima_prueba`) | "v3 2026" / "Año: 2026 · Versión: 3" | solo 2026/v3 (114 registros, solo 1° BÁSICO) | solo v3 2026 | ✅ |
| Semestral | "2º semestre 2026 (agosto–diciembre)" / "Versión: 2 y 3" | 2026/v2 (120) y 2026/v3 (114) | desde la 1ª versión del semestre hasta la actual | ✅ |
| Anual | "2026" / "Año: 2026" | 2026/v1 (542), v2 (120), v3 (114) | todas las versiones 2026 | ✅ |
| Personalizado | "ABRIL 2026 – NOVIEMBRE 2026" / "Versión: 1, 2 y 3" | 2026/v1, v2, v3 | las versiones dentro del rango | ✅ (ver nota) |
| Custom IDEL | "Panguipulli · 2024/v1 → 2026/v3" | **todo el histórico 2024–2026** | — | sin modos |

**Nota sobre personalizado**: las páginas 1 y 2 son *byte-idénticas* a las de `anual` salvo la cabecera. Es correcto (todo 2026 cae dentro de abril–noviembre) pero revela que el modo personalizado no aporta granularidad: el mapeo versión→mes es tan grueso que cualquier rango que cubra el año colapsa en el modo anual.

**Protocolo 5°/6° sin v3**: en 2026 se cumple — 5° BÁSICO solo tiene v1 y ni el mapa de riesgo (p1) ni el cierre (p41) le atribuyen v3 en 2026, y ningún curso aparece como "sin datos" alarmante. **Pero en 2025 la base sí tiene v3 para 5° (26 alumnos, 104 registros) y 6° (22 alumnos, 88 registros)**, y el informe los rinde como período válido (p29–p40, y "5° BÁSICO 2025/v1 → v3" / "6° BÁSICO 2025/v1 → v3" en p41). O el protocolo cambió, o esos datos 2025 están mal cargados. Requiere confirmación con la fundación.

---

## 3. Hallazgos (con página)

### 🔴 H1 — El rol `logro_1` no existe: todos los gráficos de valor rinden 0.0 falsos
**Páginas**: `idel_ultima_prueba` p1 y p2 · `idel_semestral` p1 · `idel_anual` p1 · `idel_personalizado` p1 (5 de 8 páginas del motor v1).

El `pdf_layout` del indicador usa `"valueField": "_logro_1"` en tres de sus cuatro secciones, pero `column_roles` de IDEL solo define `nivel_de_logro`, `evaluacion_num` y `habilidad` — **no hay ningún rol `logro_1` mapeado a la clave `Puntaje`**. El motor resuelve el campo ausente a 0 y grafica ceros.

Gravedad máxima porque **no falla de forma visible**: el gráfico "Puntaje Promedio por Curso" imprime la etiqueta `0.0` sobre una barra de altura cero para 1° BÁSICO, cuando el promedio real es 21.53. Un lector concluye "el curso sacó 0 puntos", que es un hecho falso afirmado, no un dato faltante. El eje del gráfico histórico incluso filtra el nombre crudo del campo (`Logro_1`) como rótulo del eje Y.

La sección `SummaryTable` sí degrada bien ("Sin datos disponibles.", p1), lo que hace el contraste más peligroso: en la misma página conviven un "sin datos" honesto y un "0.0" mentiroso sobre el mismo dato.

**Arreglo**: agregar `"logro_1": [{"metric_id": 8, "column": "Puntaje"}]` a `column_roles` del indicador 3. Es un cambio de datos, no de código.

### 🔴 H2 — El cierre comparativo (p41) mezcla cohortes y cursos distintos
**Página**: 41, tabla "Evolución del promedio por subprueba (2024/v1 → 2026/v3)".

La tabla es **aritméticamente correcta** (verifiqué las 6 filas contra SQL: CT 16.3→9.9, FLO 52.2→17.4, FNL 32.5→30.8, FSF 35.0→27.3, VSD 25.1→25.3) pero compara poblaciones incomparables:

- **2024/v1** = 92 estudiantes de **1°, 2° y 3° BÁSICO**.
- **2026/v3** = 19 estudiantes de **1° BÁSICO solamente**.

Todo el "descenso" es un artefacto de composición: se comparan cursos mayores contra 1° básico. Restringido a 1° BÁSICO (comparación justa), CT va de 10.7 a 9.9 (Δ **−0.8**, no −6.3) y FLO **no tiene línea base 2024/v1** (Δ −34.8 es puro artefacto). El informe presenta cuatro flechas rojas ↓ como conclusión de portada trasera; es la afirmación más visible del documento y es incorrecta.

Defecto menor asociado en la misma tabla: la fila ILP tiene Δ = "—" pero **Tend. = "="**, es decir declara "sin cambio" donde no hay línea base. Debería ser "—".

### 🔴 H3 — Paleta hardcodeada: los colores corren un escalón hacia "seguro"
**Páginas**: 1 (heatmap), 2, 10, 17, 23, 29, 35 (gráficos apilados), 5, 6, 13, 20, 26, 32, 38 (chips de tabla), 7–9, 14–16, 21–22, 27–28, 33–34, 39–40 (rosters). Efectivamente todas las páginas con color de nivel.

`scripts/report_pdl_idel.py:78-83` define `LEVEL_COLORS` fijo e **ignora por completo `Indicator.achievement_levels`**:

| Nivel | Oficial (`achievement_levels`) | Hardcodeado en el motor | Efecto |
|---|---|---|---|
| Crítico | `#dc2626` rojo | `#dc2626` | ✅ igual |
| Alto Riesgo | `#ea580c` naranja | `#f59e0b` ámbar | se ve como el amarillo oficial de *Cierto* Riesgo |
| Cierto Riesgo | `#eab308` amarillo | `#84cc16` **lima** | se ve **verde** |
| Bajo Riesgo | `#22c55e` verde | `#16a34a` verde oscuro | ✅ similar |

**Efecto visual real, verificado en el PDF**: en p17 (3° BÁSICO, 2025/v1) la barra se lee como ~60 % verde cuando solo el **8 %** es Bajo Riesgo; el 52 % lima es Cierto Riesgo, que sigue siendo riesgo. En p2 (1° BÁSICO) la franja superior de cada barra parece "zona buena" y en realidad solo el 10–17 % lo es. En p10 (2° BÁSICO 2025/v2) la barra parece 76 % verde cuando el Bajo Riesgo es 41 %.

El sesgo es sistemático y siempre en la misma dirección: **subestima el riesgo**. Además rompe la consistencia con la página de Indicadores del frontend y con los dashboards, que sí heredan `achievement_levels` vía `aesthetics.color_overrides`.

### 🟠 H4 — Cabeceras del roster ilegibles y sin año
**Páginas**: 7, 8, 9 (48 columnas, ilegible) · 14, 15, 16 (36 columnas, marginal). Legibles a partir de ≤30 columnas (p21, 27, 33, 39).

Dos problemas distintos:

1. **Colisión**: con 48 columnas la fila de cabecera se rinde como `CTCTCTCTCTCTCTCTFLFLFLFLFLFLFLFLFNFNFN…` — literalmente ilegible. Es el bloque de mayor densidad informativa del informe (nivel por estudiante × subprueba × evaluación) y queda inutilizable justo para el curso con más historia.
2. **Ambigüedad del año** (afecta a *todas* las páginas de roster, incluso las legibles): la cabecera solo dice `CT v1 / CT v2 / CT v3 / CT v1 / …`. En p27 (4° BÁSICO) hay dos columnas rotuladas `CT v1` — una es 2025/v1 y la otra 2026/v1 — sin ninguna marca que las distinga. La leyenda de códigos explica C/A/R/B pero nunca el eje temporal.

### 🟠 H5 — Tres tratamientos distintos de "sin datos" en el mismo informe
- **Fila omitida** (correcto): p29 y p35 — las tablas de 5° y 6° BÁSICO simplemente no incluyen FNL ni FSF.
- **Texto "sin datos"** con hueco enorme: p30, p31, p36, p37 — dos placeholders de texto dejan ~40 % de la página en blanco.
- **Grilla 4×4 vacía** (chart degenerado): p12 (ILP N=0), p19 (ILP N=0), p25 (FNL y FSF N=0), p31, p37 — se dibuja la matriz completa con su tinte diagonal verde/gris/rosa y cero contenido. Parece un gráfico con datos hasta que uno lee "N=0" en el título.
- **Columnas muertas** en los rosters: p33, p34 (5°) y p39, p40 (6°) llevan las 6 columnas de FNL y FSF **enteramente vacías** — en p39 son 6 de 18 columnas (33 % del ancho) sin un solo valor.

La misma figura (p31) exhibe simultáneamente el placeholder de texto y la grilla vacía.

### 🟡 H6 — Rótulo "Cantidad de alumnos" cuenta registros, no alumnos
**Páginas**: `idel_ultima_prueba` p2, `idel_semestral` p2, `idel_anual` p2, `idel_personalizado` p2.

El eje Y dice "Cantidad de alumnos" y la barra de 2026/v3 suma 32+27+36+19 = **114**, que son los *registros* (19 alumnos × 6 subpruebas). Los alumnos reales son 19. Un director que lea "114 alumnos en 1° BÁSICO" en un curso de 19 se lleva una impresión seis veces inflada.

### 🟡 H7 — Desbordes tipográficos y de paginación
- **p23**, ambas tablas: "Fluidez en Segmentación de Fonemas" **no hace wrap y desborda** la celda "Descripción", invadiendo la columna 2025/v1. En p10 y p17 la misma cadena sí envuelve a dos líneas — el ancho de columna depende del número de períodos y a 4 columnas se rompe.
- **Huérfanas de paginación**: p9 (4 filas de 72 en una página completa), p26 (2 filas), p40 (**1 fila**). El chunk fijo de 34 filas produce páginas casi vacías.
- **p3**: con 8 períodos las etiquetas del eje X de los boxplots colisionan (`2024/v12024/v2025/v1…`) en los paneles CT, FNL, FSF y VSD. Con ≤6 períodos (p11, p18, p24) no ocurre.
- **Segmentos pequeños sin etiqueta**: p23 (2025/v2), p29 (2025/v1) y p35 (2025/v3) tienen una franja Crítico de ~2 % visible pero sin rótulo de porcentaje, y las columnas no suman 100 % a la vista.

### 🟡 H8 — Dos tipografías para el mismo indicador
El motor IDEL fuerza `font.family: "DejaVu Sans"` (`report_pdl_idel.py:140`); los 4 PDFs de modo salen del motor WeasyPrint con la sans por defecto (Helvetica/Arial). Un mismo indicador entregado en un mismo paquete se ve como dos productos distintos. También difiere el pie: el motor IDEL usa "Fundación PHP · Página N" con contexto de curso en la cabecera; el v1 usa "Fundación PHP" + número. Ambos sí llevan el nombre de la organización, lo que es correcto.

### ⚠️ Caveat de datos (no es defecto del informe) — 2026/v2 y 2026/v3 son clones de 2025
Detectado al ver que la tabla de p2 repite exactamente los mismos promedios y medianas de 2025/v2 y 2025/v3 en 2026/v2 y 2026/v3, en las 6 subpruebas y en ambos estadísticos. Verificado por SQL:

- El multiset `(subprueba, puntaje)` de 1° BÁSICO 2025/v3 vs 2026/v3 coincide en **80 de 80** combinaciones.
- La intersección de nombres de alumno entre ambos períodos es **0** (19 nombres distintos en cada uno).

Es decir: la cohorte 2026 tiene nombres nuevos pero la distribución de puntajes exacta de 2025. Lo mismo para v2. Es data sintética de siembra. **Consecuencia para este QA**: `ultima_prueba`, `semestral` y buena parte de `anual` están reportando números reciclados de 2025 presentados como 2026. No invalida la revisión de los motores, pero sí cualquier lectura pedagógica de los PDFs de modo.

---

## 4. Rúbrica visual: motor v1 (2 págs) vs motor IDEL (41 págs)

**¿El `pdf_layout` de v1 es un resumen digno? No — quedó pobre, y no solo por el bug.**

Aun arreglando H1, el layout de 4 secciones produce dos páginas con ~35 % de ocupación: la p1 de `ultima_prueba` tiene un título, una línea de "Sin datos disponibles." y un gráfico, dejando el 45 % inferior en blanco; la p1 de los modos históricos tiene un solo gráfico y el 60 % vacío. No hay una sola tabla de números que el usuario pueda leer, ninguna desagregación por estudiante, ningún indicador de N, ninguna comparación contra el período anterior más allá del flag `comparePrevious` de la tabla rota.

El contraste es brutal: para el mismo indicador, el motor IDEL entrega mapa de riesgo con escala continua, cobertura longitudinal, promedios y medianas por subprueba × evaluación, boxplots de distribución, matrices de transición 4×4 con semántica mejoró/mantuvo/empeoró, listas nominales de riesgo persistente y rosters completos. La calidad de composición del motor IDEL (jerarquía tipográfica, cabecera/pie con contexto de curso, tablas con encabezado índigo y filas alternadas, uso de `—` en vez de `nan`, etiquetas oficiales exactas) es la mejor del proyecto de los informes que he visto.

Dicho eso, el motor IDEL **no tiene modos de período** y su cierre analítico (H2) está mal, así que ninguno de los dos motores es entregable tal cual.

---

## 5. Veredicto de hardcodeabilidad

### 5.1 ¿Construir los modos de período en el módulo custom? — **Sí, y es el camino correcto**

`backend/rgenerator/reports/custom/pdl_idel.py` tiene **56 líneas**: es un wrapper delgado que solo resuelve el `Indicator` y delega en `build_pdl_idel_pdf_bytes(indicator, db, org_id, filters=filtros)`. Ya recibe `filtros` y los traduce internamente, pero declara `REQUIERE_FILTRO_TEMPORAL: list[str] = []` — no expone ningún modo.

La ruta de menor riesgo es **no reescribir el motor matplotlib**, sino:

1. Declarar los modos en el wrapper (`REQUIERE_FILTRO_TEMPORAL = ["unica", "semestral", "anual", "personalizado"]`) y traducir el modo a un filtro `(Año, Versión)` antes de llamar a `build_pdl_idel_pdf_bytes`.
2. Pasar ese filtro al motor, que **ya sabe** recortar el universo: `load_data()` acepta filtros y todas las funciones de render derivan sus períodos de `eval_ids_sorted(df)` / `par_evaluaciones_comparables(df)`. Un `df` recortado al período produce automáticamente las páginas correctas con menos columnas — que además es justo lo que resuelve H4 (menos períodos, cabeceras legibles) y H7 (menos períodos, sin colisión de ticks).
3. Para el modo "única" (una sola versión) hay que suprimir las secciones que exigen un par: matrices de transición (p4, 12, 19, 25, 31, 37), riesgo persistente (p5, 13, 20, 26, 32, 38) y el cierre (p41). Ese es el único trabajo estructural real.

**Qué se reutiliza tal cual** (lo bueno del motor, todo parametrizado por el `df` de entrada):
- `render_panorama` — heatmap de riesgo + cobertura (p1). Verificado exacto.
- `render_course_page_a` / `_render_tabla_estadistico` — apilado de niveles + promedios + medianas (p2, 10, 17, 23, 29, 35). Verificado exacto, incluida la omisión correcta de subpruebas sin datos.
- `render_course_page_b` — boxplots (p3, 11, 18, 24, 30, 36).
- `render_table`, `new_page`, `section_heading`, `block_title`, `PageCounter` — todo el chasis tipográfico y de paginación.
- `SUBPRUEBAS_LABEL` / `SUBPRUEBAS_ORDER` — las etiquetas oficiales, que están perfectas y son la fuente que hoy funciona mejor de las tres declaradas en CLAUDE.md.
- `compute_subprueba_transitions`, `course_aggregate_transitions`, `par_evaluaciones_comparables` — para los modos con ≥2 versiones.

**Qué se reescribe**: solo `render_closing` (p41), por H2 — la comparación debe hacerse **por curso** (o al menos restringida a la intersección de cursos presentes en ambos extremos), nunca sobre el agregado global de períodos con composición distinta.

### 5.2 ¿Los colores/etiquetas mal se arreglan pasando `achievement_levels` como parámetro? — **Los colores sí; las etiquetas no hacen falta**

**Colores: sí, y es un arreglo de bajo riesgo.** `LEVEL_COLORS` (líneas 78–83) es un dict módulo-nivel consumido en solo tres puntos: `render_table` (línea 394–396, chips de nivel con alpha `33`), la leyenda de apilados (línea 497) y las barras (línea 509–514). El motor ya recibe el objeto `Indicator` completo en `build_pdl_idel_pdf_bytes`, así que basta construir el dict desde `indicator.achievement_levels` y pasarlo por parámetro en vez de leer la constante. `ACHIEVEMENT_LEVELS` y `LEVEL_VALUE` (el orden ordinal 1–4 que alimenta las matrices mejoró/empeoró) también deberían derivarse del campo `order` de `achievement_levels` en lugar de estar fijos, para que el motor no se rompa si la fundación agrega un quinto nivel.

Ojo con **no** tocar `DIR_COLORS` (líneas 88–91, verde/gris/rojo de mejoró/mantuvo/empeoró): ese es un eje semántico distinto del nivel de riesgo y hoy está bien resuelto — es correcto que no use la paleta de niveles.

**Etiquetas: no hay nada que arreglar.** `SUBPRUEBAS_LABEL` (línea 96) es correcto en las 6 subpruebas y se rinde bien en las 41 páginas. Lo que sí conviene es **invertir la dependencia**: hoy hay tres fuentes de verdad paralelas (`frontend/src/tooling/idelLabels.js`, `scripts/_oneshot/dashboards_v2/helpers.py`, `scripts/report_pdl_idel.py`) y solo se mantienen sincronizadas a mano. Los nombres deberían vivir en la BD (catálogo de dimensión "Evaluación") y los tres consumidores leerlos de ahí.

**El bug de `logro_1` (H1) no se arregla con parámetros**: es puramente configuración de datos — falta la entrada `logro_1` en `column_roles` del indicador 3.

---

## 6. Resumen ejecutivo

- El **motor IDEL matplotlib es sólido en datos**: 7 verificaciones independientes contra SQL, todas exactas, incluidas 42 celdas de una sola tabla. Órdenes ordinales y temporales correctos. Etiquetas de subprueba oficiales sin un solo error, evitando las tres trampas históricas documentadas.
- El **motor v1 está roto en su eje principal**: los 4 PDFs de modo publican `0.0` como puntaje real en 5 de 8 páginas por un rol de columna no mapeado.
- Los **4 modos de período resuelven correctamente qué versiones incluir**, pero el custom no los soporta y el personalizado no se distingue del anual.
- La **paleta hardcodeada** desplaza sistemáticamente la lectura visual hacia "menos riesgo del que hay".
- El **cierre comparativo (p41)** presenta como tendencia lo que es un artefacto de composición de cohortes.
- Los datos 2026/v2 y v3 son **clones de 2025** — cualquier lectura pedagógica de los modos actuales es inválida.
