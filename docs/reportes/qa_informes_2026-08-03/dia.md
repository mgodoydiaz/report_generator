# QA de informes — Indicador **DIA** (id 2, org 1)

**Fecha:** 2026-08-03 · **Rama:** `dev` · **DB:** `rgenerator_dev` (Docker `db-1`)
**Asignatura evaluada:** LECTURA · **Período de referencia:** `Hito=DIAGNOSTICO` + `Año=2026`
**Métricas:** `Resultados DIA por estudiante` (id 6, 5.647 filas) · `Resultados DIA por Pregunta` (id 7, 2.386 filas)

---

## 1. Puntaje

# 54 / 100

| Dimensión | Puntos | Máx | Comentario en una línea |
|---|---:|---:|---|
| Correctitud de datos | **22** | 40 | Promedios y conteos por nivel exactos; los conteos de **personas** están mal en el motor v1 y dos cursos homónimos de establecimientos distintos se fusionan sin avisar. |
| Cobertura de período | **8** | 15 | El recorte temporal es correcto (2025 excluido en todos los caminos), pero el **rótulo** del período miente en 6 de 8 páginas del motor v1. |
| Calidad visual | **14** | 30 | El formato oficial (44 págs) es sólido; los 3 informes de período muestran `0.5` en vez de `55 %`, gráficos degenerados y encabezado obsoleto. |
| Disponibilidad de modos | **10** | 15 | 3/4 tarjetas + custom responden 200; `semestral` 400 por calendario (descuento mínimo), pero `personalizado` es un clon byte a byte de `ultima_prueba`. |

**Páginas revisadas:** 52 de 52 rasterizadas a 150 dpi en
`data/output/qa_indicadores/2026-08-03/png/dia/`.
Inspección visual directa: `ultima_prueba` 1–3, `anual` 1–2, `personalizado` 1 (2 y 3 verificadas por diff de texto, idénticas a `ultima_prueba`), `custom:dia` 1–20, 26, 30, 39, 44 (22 de 44).
Las 44 páginas del formato oficial fueron además verificadas por extracción de texto completa (inventario de secciones, búsqueda de `nan`/`None`/`Traceback`, pie de página y numeración): **sin `nan`, sin tracebacks, pie y folio presentes en las 52 páginas**.

---

## 2. Verificación de datos — PDF vs recalculado

Recalculado con pandas sobre `metric_data` (métricas 6 y 7, `org_id=1`), filtrando
`Asignatura=LECTURA ∧ Hito=DIAGNOSTICO ∧ Año=2026` (576 filas de estudiante, 643 de pregunta).

| # | Dato | Fuente (pág.) | Valor en el PDF | Recalculado | Veredicto |
|---:|---|---|---:|---:|:--|
| 1 | Alumnos — `I D (TPI-510)` | v1 `ultima_prueba` p1 | **26** | **56** | ✗ subconteo de 30 |
| 2 | Alumnos — `II D (TPI-510)` | v1 `ultima_prueba` p1 | **22** | **57** | ✗ subconteo de 35 |
| 3 | Suma de la columna Alumnos | v1 `ultima_prueba` p1 | **511** | **576** | ✗ faltan 65 estudiantes |
| 4 | Suma Inicial / Intermedio / Avanzado | v1 `ultima_prueba` p1 | 144 / 197 / 235 = **576** | 144 / 197 / 235 = **576** | ✓ exacto |
| 5 | Barra apilada total | v1 `anual` p2 | 144 / 197 / 235 = **576** | idem | ✓ exacto y **sin fuga de 2025** |
| 6 | Logro prom. `I D (TPI-510)` | v1 `ultima_prueba` p1 | `0.5` | `0.4608` | ~ redondeo a 1 decimal |
| 7 | Logro máx. `II B (TPA-710)` | v1 `ultima_prueba` p1 | `1.0` | `0.9855` | ✗ se lee como puntaje perfecto |
| 8 | Logro prom. Eje `Narración` | v1 `ultima_prueba` p3 | `0.62` | `0.6266` | ✓ |
| 9 | Logro prom. Habilidad `Localizar` | v1 `ultima_prueba` p3 | `0.64` | `0.6382` | ✓ |
| 10 | Alumnos — `I D` / `II D` | v2 `custom:dia` p1 | **56 / 57** | **56 / 57** | ✓ (contradice #1 y #2) |
| 11 | Suma de la columna Alumnos | v2 `custom:dia` p1 | **576** | **576** | ✓ |
| 12 | Promedio `7 A` | v2 `custom:dia` p1 | `55 %` | `54,73 %` | ✓ |
| 13 | Promedio `II C (TPA-710)` | v2 `custom:dia` p1 | `69 %` | `69,16 %` | ✓ |
| 14 | Máximo `II C (TPA-710)` | v2 `custom:dia` p1 | `99 %` | `98,55 %` | ✓ |
| 15 | Logro por Nivel (4 barras) | v2 `custom:dia` p2 | 60 / 47 / 62 / 55 % | 60,41 / 47,19 / 62,38 / 54,73 % | ✓ exacto |
| 16 | `Promedio Hito` — ILAMANTE RODRIGUEZ | v2 `custom:dia` p39 | `69 %` | `23 %` (su valor 2026) | ✗ promedia 2025 |
| 17 | `Promedio Hito` — ASTORGA PULIDO | v2 `custom:dia` p39 | `29 %` | `20 %` | ✗ promedia 2025 |
| 18 | `Promedio Hito` — GUERRERO JARAMILLO | v2 `custom:dia` p12 | `56 %` | `31 %` | ✗ promedia 2025 |
| 19 | Filas de la tabla por pregunta `I D` | v2 `custom:dia` p12–14 | **62 filas / 31 N° Pregunta** (cada nº dos veces) | 31 Pullinque + 31 Panguipulli | ✗ fusión de establecimientos |
| 20 | Filas de la tabla por pregunta `II D` | v2 `custom:dia` p20–22 | **68 filas / 34 N° Pregunta** | 34 + 34 | ✗ fusión de establecimientos |

**El bug histórico del período compuesto sigue corregido en los agregados.**
En `metric_data` conviven `DIAGNOSTICO 2025` (444 filas LECTURA) y `DIAGNOSTICO 2026`
(576) más `INTERMEDIO 2025` (1.611). Ninguna de las 2.055 filas de 2025 entra en los
totales de `ultima_prueba` ni de `anual`: la suma de niveles cierra en 576 exacto.
El único residuo es el campo derivado del formato oficial (hallazgos #16–#18, ver P1-1).

### 2.1 Sobre las filas sin identidad

El patrón reportado en producción **existe igual en dev, pero no es una carga duplicada.**

- `LECTURA · DIAGNOSTICO · 2026` = **576 filas**, de las cuales **375 no tienen `Nombre` ni `Nombre_Norm`** (65 %).
- Las 375 son **todas de `Liceo PHP Panguipulli`**; las 201 con nombre son todas de `Liceo PHP Pullinque`.
- **No hay duplicación**: 0 grupos repetidos por `(Nombre_Norm, Curso, Establecimiento)` y 0 por `Nombre_Norm` a secas. Los `Logro` de los dos establecimientos casi no se solapan (2 y 3 valores comunes en los dos cursos homónimos, sobre 56 y 57 filas).
- `Numero Lista` está **100 % nulo** en las 576 filas, así que la clave compuesta `(Curso, N° Lista)` tampoco rescata identidad.

**Conclusión: las 375 filas no INFLAN los conteos — los DESINFLAN**, y solo en el motor
v1 (ver P0-1). En el formato oficial el conteo es correcto, pero el precio es que
20 páginas de "Logro por Alumno" salen anónimas.

Lo que sí produce una **fusión indebida**: `I D (TPI-510)` y `II D (TPI-510)` existen en
**los dos establecimientos**. Como ningún informe muestra `Establecimiento` ni agrupa por
él, esas dos filas de tabla y esas cuatro páginas de detalle mezclan dos colegios.

---

## 3. Hallazgos por gravedad

### P0 — bloqueantes

**P0-1 · La columna "Alumnos" pierde 65 de 576 estudiantes y se contradice en la misma fila**
`dia_ultima_prueba_lectura.pdf` p1 · `dia_personalizado_lectura.pdf` p1
La fila `I D (TPI-510)` dice **Alumnos = 26** y a la derecha, en la misma fila,
`Inicial 24 + Intermedio 20 + Avanzado 12 = 56`. `II D (TPI-510)`: **22** contra
`8 + 22 + 27 = 57`. La suma de la columna Alumnos da 511 y la de los niveles 576.
Causa exacta — `backend/rgenerator/core/report_steps.py:1356-1362`:

```python
identidades = {
    r.get('_rut') or r.get('_nombre') or r.get('_nombre_norm')
    for r in actual_records
}
identidades.discard(None)
identidades.discard('')
n_alumnos = len(identidades) or len(actual_records)
```

Con un curso 100 % sin nombre el set queda vacío y el `or` degrada bien a filas
(por eso `7 A = 30` es correcto). Pero con un curso **mixto** los 30 registros sin
identidad colapsan en el único `None` que se descarta, y se pierden en silencio.
El comentario del código dice que `_nombre_norm` "cierra la cadena": no la cierra
cuando la fila no tiene ninguna de las tres.

**P0-2 · El encabezado dice "Cierre" en un informe de DIAGNOSTICO**
`dia_ultima_prueba_lectura.pdf` p1–3 · `dia_personalizado_lectura.pdf` p1–3
Las dos primeras líneas del `center_header` están hardcodeadas en
`indicators.pdf_layout.branding` y quedaron congeladas de una corrida vieja:

```json
"center_header": ["Informe DIA Cierre", "Lectura Nivel Medio", "Octubre 2025"]
```

El motor solo reemplaza la 3ª línea (`DIAGNOSTICO 2026` / `MARZO 2026`) y deja las
otras dos. Resultado: 6 de 8 páginas del motor v1 se presentan como informe de
**Cierre** cuando el subtítulo, dos líneas más abajo, dice `Hito: DIAGNOSTICO`.
Además "Lectura **Nivel Medio**" es falso: el cohorte incluye `7 A` y `8 A` (básica).

**P0-3 · Dos establecimientos fusionados sin ninguna señal**
v2 `custom:dia` p11–14 (`I D`), p19–22 (`II D`) · v1 p1 (filas homónimas)
La tabla "Logro por Alumno - I D (TPI-510)" mezcla 26 alumnos con nombre de
Pullinque y 30 anónimos de Panguipulli en una sola lista de 56. Peor:
"Logro por Pregunta - I D (TPI-510)" trae **62 filas para 31 preguntas** — la
pregunta 1 aparece con 100 % y con 77 %, la 17 con 70 % y 58 %, la 22 con 13 % y
12 %… Para el lector es un error de datos evidente y no hay columna
`Establecimiento` que lo explique. `II D` idem con 68 filas / 34 preguntas.

**P0-4 · Los conteos de personas no coinciden entre los dos informes del mismo período**
v1 p1 vs v2 p1
Mismo indicador, misma asignatura, mismo hito, mismo día: el informe de período
dice que `I D` tiene 26 alumnos y el formato oficial dice 56. No hay una única
función de conteo (`report_steps._table_section` inline vs
`reports/helpers.contar_estudiantes`).

### P1 — graves

**P1-1 · Fuga residual 2025 → 2026 en el campo derivado `Logro_Promedio_Estudiante`**
v2 `custom:dia` p12 (1 caso) y p39 (2 casos)
`reports/dia/esquema.json` define el campo con
`entity_field: ["Curso", "Nombre_Norm"]` — **sin `Año`** — y se aplica antes del
recorte temporal. Los estudiantes que conservan la etiqueta de curso entre 2025 y
2026 (repitentes o cursos que no cambian de rótulo) reciben el promedio de todas
sus filas LECTURA de ambos años. Reproducido exacto 3/3 en pandas:

| Estudiante | Curso | Logro 2026 | "Promedio Hito" en el PDF | Media (Curso, Nombre_Norm) sin Año |
|---|---|---:|---:|---:|
| BENJAMIN EDUARDO ILAMANTE RODRIGUEZ | I C (TPA-710) | 23 % | **69 %** | 68,57 % |
| ANTONIO ASTORGA JAVIER PULIDO | I C (TPA-710) | 20 % | **29 %** | 29,41 % |
| DANDYEL GUERRERO JARAMILLO JOAN | I D (TPI-510) | 31 % | **56 %** | 55,95 % |

Hoy son 3 de 200 (1,5 %), pero el volumen crece con cada cohorte que repite curso,
y el caso de ILAMANTE es el peor posible: un alumno en nivel **Inicial** con 23 %
aparece con un "promedio" de 69 %.

**P1-2 · Formato numérico inservible en los tres informes de período**
v1 p1 (tabla) y p2–p3 (ejes de los gráficos)
`indicators.role_formats` está **vacío (`{}`)**, así que `_format_value` cae al
branch `number` (`f'{v:.1f}'`) sobre una escala 0–1. Consecuencias:
- Tres cursos con medias reales 0,3991 / 0,4034 / 0,4260 se imprimen todos como `0.4`.
- `0.9855` se imprime `1.0` — se lee como 100 % de logro.
- La tabla dice `0.5` donde el formato oficial dice `55 %` para el mismo dato.

**P1-3 · `anual` produce dos gráficos degenerados y ninguna tabla**
`dia_anual_lectura.pdf` p1 y p2
En 2026 solo existe un hito, así que "Evolución del Logro Promedio por Curso y
Hito" dibuja 18 barras de colores contra un único tick `DIAGNOSTICO`, con una
leyenda de 18 entradas en letra de 4 pt fuera del área de trazado; y "Evolución de
Alumnos por Nivel de Logro" es **una sola barra apilada** que ocupa la página.
No hay auto-omisión ni nota explicativa (SIMCE ya resolvió esto: decisión 16).
El informe entero son 2 páginas sin una sola tabla.

**P1-4 · `personalizado` es un clon de `ultima_prueba` y rotula el período de otra forma**
`dia_personalizado_lectura.pdf` p1–3
Diff de texto contra `ultima_prueba`: **la única diferencia en las 3 páginas** es
`DIAGNOSTICO 2026` → `MARZO 2026` en el encabezado. Y el subtítulo de la misma
página sigue diciendo `Hito: DIAGNOSTICO` — dos nombres para el mismo período en
el mismo documento. DIA no tiene dimensión `Mes`; anclar el rango personalizado a
meses de calendario es semánticamente ajeno al indicador.

**P1-5 · Los colores de nivel del formato oficial no son los de `achievement_levels`**
v2 `custom:dia` p4 (gráfico apilado)
`indicators.achievement_levels` para DIA es
`Inicial #dc2626 · Intermedio #eab308 · Avanzado #22c55e`.
Los informes v1 **sí** los respetan (p2 de `ultima_prueba`, p2 de `anual`); el
formato oficial de 44 páginas usa una paleta propia (naranja/ámbar/verde azulado).
El mismo nivel se ve de dos colores distintos según qué informe abra el usuario, y
ninguno de los dos coincide con `/indicadores`.

**Nota sobre contraste.** El `#ea580c` (Alto Riesgo) **no pertenece a DIA** — es de
IDEL; DIA tiene 3 niveles, no 4. El problema equivalente en DIA es el
`#eab308` (Intermedio): las etiquetas blancas en negrita sobre ese ámbar quedan en
~2,3:1 (`197`, `20`, `22` en `anual` p2 y `ultima_prueba` p2), por debajo de 4,5:1
y claramente peor que las mismas cifras sobre el rojo `#dc2626`. En el formato
oficial el ámbar es aún más claro. Recomendación: texto **negro** sobre el
segmento Intermedio, o mover las etiquetas fuera de la barra.

### P2 — moderados

- **P2-1 · 1.326 rayas em en 44 páginas.** La columna `N° Lista` está vacía en las
  18 tablas de alumno (el dato es 100 % nulo en la métrica) y `Estudiante` está
  vacía en 375 de 576 filas. Las tablas de `7 A`, `8 A`, `I A (TPT-610)`,
  `I B (TPT-610)`, `I C (TPT-610)`, `I E (TPI-510)`, `II A (TPT-610)`,
  `II B (TPT-610)`, `II C (TPT-610)`, `II E (TPI-510)` (v2 p5, 7, 15, 23, 25, 27,
  29, 31, 33, 35) son **listas de alumnos sin un solo alumno identificado**.
  Ninguna página advierte del vacío.
- **P2-2 · `Promedio Hito` es una columna degenerada.** Con un solo punto temporal
  repite `Logro` en 197 de 200 filas nombradas (y en las otras 3 está mal, P1-1).
  Debería auto-omitirse.
- **P2-3 · Orden alfabético donde corresponde orden pedagógico.** v2 p2, gráfico
  "Logro Promedio por Nivel": `Octavos · Primeros Medios · Segundos Medios ·
  Septimos`. El orden correcto es Séptimos → Octavos → Primeros Medios → Segundos
  Medios. (El orden **cronológico de hitos** sí está bien configurado en
  `temporal_config.order = [DIAGNOSTICO, INTERMEDIO, CIERRE]`; el problema es el eje
  `Nivel`, no el `Hito`.)
- **P2-4 · Gráficos cruzados ilegibles.** v2 p3 "Logro Promedio por Eje Temático"
  (18 cursos × 6 ejes = 108 barras) y p4 "por Habilidad" (54 barras): las etiquetas
  se pisan y producen artefactos legibles como `447%`, `6161%`, `3918%`, `424?%`.
  Sin valor analítico a este tamaño.
- **P2-5 · Títulos duplicados.** v2 p2, p3, p4: el encabezado de sección y el
  título interno de la figura dicen exactamente lo mismo.
- **P2-6 · Viudas de tabla.** v2 p26 abre con 2 filas huérfanas de la tabla de
  alumnos de `I A (TPT-610)`; v2 p5 cierra con un fragmento de 2 filas de la tabla
  de preguntas.
- **P2-7 · Acentos faltantes.** `Minimo`, `Maximo` (v2 p1), `Septimos` (v2 p2).
- **P2-8 · Branding cruzado.** El escudo de **Liceo Bicentenario Pullinque** aparece
  en las 44 páginas de un informe cuyo 65 % de los datos es de **Panguipulli**.
- **P2-9 · Barras degeneradas por ancho.** v1 p3 "Logro Promedio por Habilidad":
  3 barras ocupando el ancho completo de la página. Y los gráficos de p3 no llevan
  etiquetas de valor mientras el de p2 sí.

### Lo que está bien (para no perderlo)

- Recorte temporal correcto en los tres caminos: 2.055 filas de 2025 excluidas sin excepción.
- Conteos por nivel exactos en los 4 PDFs (144 / 197 / 235).
- Todos los promedios, mínimos y máximos del formato oficial reproducen la DB al punto porcentual.
- Cero `nan`, cero `None`, cero tracebacks en las 52 páginas.
- Pie `Fundación PHP` y folio presentes en las 52 páginas; tablas dentro de márgenes.
- El motor v1 **sí** honra `achievement_levels`.
- El boxplot por curso (v2 p3) es el único gráfico del set que muestra dispersión y está bien hecho.

---

## 4. Veredicto de hardcodeabilidad

`backend/rgenerator/reports/custom/dia.py` son 45 líneas: un wrapper de
`dispatch_v2.generar_pdf_v2` con `LABEL`, `FORMATO`, `ENGINE_TYPES`,
`REQUIERE_FILTRO_TEMPORAL` y `REQUIERE_ASIGNATURA`. **No declara `MODOS`**, así que
las 4 tarjetas de período (`ultima_prueba`, `semestral`, `anual`, `personalizado`)
caen al motor v1 genérico que arma las secciones desde
`indicators.pdf_layout` / `pdf_layout_historico`.

### ¿Declarar MODOS arregla lo que está mal en los PDFs de período?

**Sí, la mayor parte — y con evidencia directa, porque el camino del módulo ya
produce el resultado correcto para los mismos datos.**

| Defecto | ¿Lo arregla MODOS? | Por qué |
|---|:--:|---|
| P0-1 conteo de alumnos (26 vs 56) | **Sí** | El módulo usa `helpers.contar_estudiantes`, que degrada a un id único por fila sin identidad. El formato oficial imprime 56/57 y suma 576 exacto. |
| P0-2 encabezado "Cierre" / "Nivel Medio" | **Sí** | El `center_header` obsoleto vive en `pdf_layout.branding` de la DB. `dia/crear_informe.py` ya construye las líneas de asignatura y hito/año con los params reales de la corrida: el 44-pág dice `Informe DIA / LECTURA / DIAGNOSTICO 2026`, correcto. |
| P1-2 formato `0.5` en vez de `55 %` | **Sí** | `role_formats` vacío obliga a `_format_value(..., 'number')`. El esquema del módulo pasa `formato: "percent"` por sección. |
| P1-3 gráficos degenerados en `anual` | **Sí** | El módulo decide sus secciones según el período: se replica la decisión 16 de SIMCE (auto-omitir evolución con un solo punto temporal y explicar por qué). |
| P1-4 `personalizado` clonado y rotulado "MARZO 2026" | **Sí** | El módulo construye la etiqueta del período; para DIA debe ser `Hito + Año`, no el mes de calendario que devuelve `periodos.py`. |
| P1-5 colores de nivel | **Parcial** | El módulo puede leer `achievement_levels` y pasarlo como `color_overrides`, pero hoy el que se desvía es justamente el camino v2 — hay que arreglarlo ahí, no solo declarar MODOS. |
| P0-3 fusión de establecimientos | **No** | Es un problema del **eje de agrupación**, no del motor: hoy rompe igual el formato oficial. Hay que meter `Establecimiento` en la clave de grupo (o como columna/filtro obligatorio). |
| P1-1 fuga 2025 en `Logro_Promedio_Estudiante` | **No** | Es el `entity_field` del `derived_field` en `dia/esquema.json`: falta `Año`, o los campos derivados deben aplicarse **después** del recorte temporal. |
| P2-1 375 filas sin identidad | **No** | Problema de carga/ETL. Ningún motor lo resuelve; lo único que puede hacer el informe es advertirlo. |

**Recomendación:** declarar `MODOS` en `dia.py` (fase 4) resuelve 5 de los 7
defectos P0/P1 del camino de período, incluido el subconteo de alumnos y el
encabezado mentiroso. Pero **antes** hay que cerrar la clave de agrupación por
`Establecimiento` (P0-3) y el `entity_field` del campo derivado (P1-1), porque esos
dos ya están rompiendo el formato oficial y se heredarían tal cual a los modos.

### ¿Qué del formato oficial de 44 páginas vale la pena heredar?

**Heredar sí:**

1. **`formato: "percent"` en todo.** Es la ganancia de legibilidad más grande por
   línea de código: `0.4 / 0.4 / 0.4` pasa a `40 % / 40 % / 43 %`.
2. **`resumen_estadistico_basico` + `contar_estudiantes` como única función de
   conteo.** Elimina la contradicción 26-vs-56 y la contradicción interna de la fila.
3. **El encabezado construido desde los params de la corrida** (asignatura +
   hito/año), más logos de la organización y pie. Mata P0-2 de raíz.
4. **`boxplot_valor_por_curso` (p3).** El único gráfico del set que muestra
   dispersión; `II E (TPI-510)` con mediana 72 % y bigote hasta 0 % es información
   que ninguna barra de promedio comunica.
5. **"Logro Promedio por Nivel" (p2).** Cuatro barras, lectura inmediata: es el
   mejor candidato a abrir `ultima_prueba` antes de bajar a curso.

**Heredar solo en `ultima_prueba`, y solo tras arreglar los datos:**

6. **Detalle por alumno y por pregunta.** Misma regla que adoptó SIMCE (decisiones
   1 y 5). Hoy heredarlos significaría heredar 1.326 rayas em y las preguntas
   duplicadas de `I D` / `II D`.

**No heredar:**

7. Los gráficos cruzados Curso × Eje Temático y Curso × Habilidad (p3/p4): 108 y 54
   barras con etiquetas superpuestas. Si se quiere el cruce, va como tabla o como
   heatmap por Nivel, no por Curso.
8. La columna `Promedio Hito`: degenerada con un punto temporal y hoy incorrecta.

---

## 5. Nota sobre `semestral` (400)

`semestral` responde **400 esperado**: "Sin datos del 2º semestre 2026
(agosto–diciembre)". La última carga es `DIAGNOSTICO 2026` (marzo), así que el 400
es correcto y **descuenta 1 punto**.

Dicho eso, el modo es **conceptualmente ajeno a DIA**: el eje temporal del
indicador es `Hito` (`DIAGNOSTICO → INTERMEDIO → CIERRE`), no el calendario. Un
"semestre" para DIA debería resolverse como *"del hito X al hito Y del año en
curso"*. Mientras se ancle a meses, la tarjeta va a estar en 400 nueve meses al año
aunque haya datos de sobra.

---

## 6. Reproducibilidad

```bash
# Rasterizado (PyMuPDF 150 dpi) → png/dia/
python -c "import fitz; ..."   # 52 páginas

# Datos: métricas 6 y 7 del indicador 2, org 1
docker compose -f docker-compose.dev.yml exec -T db psql -U mgodoy -d rgenerator_dev \
  -c "SELECT im.id_metric, m.name, COUNT(md.id_data)
      FROM indicator_metrics im
      JOIN metrics m ON m.id_metric = im.id_metric
      LEFT JOIN metric_data md ON md.id_metric = m.id_metric
      WHERE im.id_indicator = 2 GROUP BY 1,2;"

# Recalculo en pandas dentro del contenedor backend
docker compose -f docker-compose.dev.yml exec -T backend python - < qa_dia.py
```

Archivos de referencia citados:

- `backend/rgenerator/core/report_steps.py:1356-1362` — subconteo de Alumnos (P0-1)
- `backend/rgenerator/core/report_steps.py:118-132` — `_format_value` (P1-2)
- `backend/rgenerator/reports/helpers.py:253-290` — `contar_estudiantes` (conteo correcto)
- `backend/rgenerator/reports/dia/esquema.json` — `derived_fields` (P1-1), `secciones_fijas`
- `backend/rgenerator/reports/custom/dia.py` — módulo sin `MODOS`
- `indicators.pdf_layout` / `pdf_layout_historico` (id 2) — `center_header` obsoleto (P0-2)
