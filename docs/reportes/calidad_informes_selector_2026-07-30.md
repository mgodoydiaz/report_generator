# Calidad de los informes del selector — QA visual 2026-07-30

**Rama**: `dev3` (HEAD `e4069c0` + cambios sin commitear del selector v2)
**Entorno**: stack `docker-compose.dev.yml`, backend host `:8001`, DB canónica `report_generator-db-1`
**Organización**: `Fundación PHP` (única org, `id=1`)
**Salida**: `C:\Users\magod\Desktop\PDF_test\ejemplos_2026-07-30\` — 20 PDF (167 páginas) + 6 DOCX

---

## 1. Fase de generación

### 1.1 Script `scripts/generar_ejemplos_informes.py`

`34 opciones · 20 OK · 0 errores HTTP · 14 omitidas`

| Indicador | Opción | Estado | Detalle |
|---|---|---|---|
| Fluidez Lectora | periodo_ultima_prueba | OK | 158 KB |
| Fluidez Lectora | periodo_semestral | OMITIDO | sin dimensión de año |
| Fluidez Lectora | periodo_anual | OMITIDO | sin dimensión de año |
| Fluidez Lectora | periodo_personalizado | OMITIDO | requiere configuración manual |
| Fluidez Lectora | word_resumen_indicador | OK | 83 KB |
| IDEL | periodo_ultima_prueba / semestral / anual | OK | 160 / 155 / 154 KB |
| IDEL | periodo_personalizado | OMITIDO | requiere configuración manual |
| IDEL | custom_pdl_idel | OK | 490 KB |
| IDEL | word_resumen_indicador | OK | 91 KB |
| Cálculo Veloz | periodo_ultima_prueba | OK | 283 KB |
| Cálculo Veloz | periodo_semestral | OMITIDO | sin datos del 1er semestre 2026 |
| Cálculo Veloz | periodo_anual | OMITIDO | sin datos del año en curso (2026) |
| Cálculo Veloz | periodo_personalizado | OMITIDO | requiere configuración manual |
| Cálculo Veloz | word_resumen_indicador | OK | 91 KB |
| DIA | periodo_ultima_prueba / semestral / anual | OK | 521 / 198 / 197 KB |
| DIA | periodo_personalizado | OMITIDO | requiere configuración manual |
| DIA | custom_dia | **OK (falso positivo)** | 552 KB — PDF **vacío**, ver P0-1 |
| DIA | word_resumen_indicador | OK | 190 KB |
| SIMCE Panguipulli | periodo_* (4) | OMITIDO | layout PDF sin configurar |
| SIMCE Panguipulli | custom_simce_panguipulli | OK | 895 KB |
| SIMCE Panguipulli | word_resumen_indicador | OK | 118 KB |
| SIMCE | periodo_ultima_prueba / semestral / anual | OK | 222 / 187 / 186 KB |
| SIMCE | periodo_personalizado | OMITIDO | requiere configuración manual |
| SIMCE | custom_simce | OK | 1168 KB |
| SIMCE | word_resumen_indicador | OK | 82 KB |

Sin errores HTTP, pero **HTTP 200 no implica informe válido**: `dia__custom_dia.pdf`
salió con 552 KB y contenido totalmente vacío (ver P0-1).

### 1.2 Ejercicio manual de la API

**`GET /api/indicators/{id}/report-options`** — probado en los 6 indicadores
(JSON en `/tmp/qa_out/report_options_{1..6}.json` dentro de WSL).
Estructura correcta: `grupos.periodo` (4 cards) + `grupos.especializados`,
descripciones resueltas contra datos reales y motivos de no-disponibilidad
coherentes y accionables. Observaciones en P2-1 y P2-2.

**`POST /api/indicators/{id}/export-pdf` con `periodo.tipo = "personalizado"`**
(el script lo omite). Valores tomados de `dimensiones_filtrables`:

| Caso | Body | Resultado |
|---|---|---|
| SIMCE | `2025-01 → 2026-12`, `{"Curso": "II A"}` | HTTP 200, 242 KB |
| IDEL | `2024-01 → 2026-12`, `{"Curso": "1° BÁSICO"}` | HTTP 200, 159 KB |
| DIA | `2025-01 → 2026-12`, `{"Establecimiento": "Liceo PHP Pullinque"}` | HTTP 200, 201 KB |
| SIMCE (negativo) | `2019-01 → 2019-12`, sin filtros | **HTTP 400** `"Sin datos en el período seleccionado."` — correcto |

**`POST /api/reports/custom/dia`** con combo inexistente `{"Hito": "INTERMEDIO", "Año": "2026"}`
(INTERMEDIO solo existe en 2025): **HTTP 200 con PDF de 581 KB vacío**, sin 400.
Contraste directo con el motor weasyprint, que sí devuelve 400.

### 1.3 Cambio aplicado al script generador

`scripts/generar_ejemplos_informes.py`: `_valores_por_dimension` → `_datos_indicador`
(ahora devuelve también las filas) y `_filtro_temporal` valida la **combinación**
Hito+Año contra los datos. Antes elegía Hito y Año por separado y producía combos
vacíos. No se tocó código de aplicación.

---

## 2. Matriz documento × criterio

Criterios: **C1** encabezado/pie sin solapamientos · **C2** títulos correctos ·
**C3** gráficos con datos y estéticos · **C4** tablas sin NaN · **C5** uso eficiente
de páginas · **C6** pie izquierdo = nombre de la organización

| Documento | Pág | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `simce__periodo_ultima_prueba.pdf` | 2 | ✗ | ✓ | ✗ | ✗ | ~ | ✗ |
| `simce__periodo_semestral.pdf` | 2 | ✗ | ✗ | ✗ | n.a. | ✗ | ✗ |
| `simce__periodo_anual.pdf` | 2 | ✗ | ✓ | ✗ | n.a. | ✗ | ✗ |
| `simce__periodo_personalizado_…IIA.pdf` | 2 | ✗ | ✗ | ✗ | n.a. | ✗ | ✗ |
| `idel__periodo_ultima_prueba.pdf` | 2 | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| `idel__periodo_semestral.pdf` | 2 | ✗ | ✗ | ✗ | n.a. | ✗ | ✗ |
| `idel__periodo_anual.pdf` | 2 | ✗ | ✗ | ✗ | n.a. | ✗ | ✗ |
| `idel__periodo_personalizado_…1BASICO.pdf` | 2 | ✗ | ✗ | ✗ | n.a. | ✗ | ✗ |
| `dia__periodo_ultima_prueba.pdf` | 3 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| `dia__periodo_semestral.pdf` | 2 | ✗ | ✗ | ✗ | n.a. | ✗ | ✗ |
| `dia__periodo_anual.pdf` | 2 | ✗ | ✗ | ✗ | n.a. | ✗ | ✗ |
| `dia__periodo_personalizado_…Pullinque.pdf` | 2 | ✗ | ✗ | ✗ | n.a. | ✗ | ✗ |
| `calculo_veloz__periodo_ultima_prueba.pdf` | 2 | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ |
| `fluidez_lectora__periodo_ultima_prueba.pdf` | 3 | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ |
| `dia__custom_dia.pdf` (combo vacío) | 3 | ✗ | ✗ | ✗ | ✗ | n.a. | ✓ |
| `dia__custom_dia_DIAGNOSTICO_2026.pdf` | 67 | ✗ | ✗ | ✗ | ✗ | ~ | ✓ |
| `simce__custom_simce.pdf` | 14 | ✓ | ✗ | ✗ | ✗ | ~ | ✓ |
| `simce_panguipulli__custom_simce_panguipulli.pdf` | 10 | ✓ | ✗ | ✗ | ✗ | ~ | ✓ |
| `idel__custom_pdl_idel.pdf` | 40 | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ |
| `*__word_resumen_indicador.docx` (6) | — | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |

`~` = aceptable con reservas. Detalle por documento en la sección 3.

---

## 3. Hallazgos priorizados

### P0 — rompe el informe o entrega un dato falso

#### P0-1 · Combinación de filtros sin datos devuelve HTTP 200 con un PDF vacío que incluye el traceback

- **Documento**: `dia__custom_dia.pdf` (generado por el script), `_negativo_dia_custom_INTERMEDIO_2026.pdf`
- **Páginas**: 1–3 (todo el documento)
- **Reproducir**: `POST /api/reports/custom/dia` con
  `{"indicator_id": 2, "filtros": {"Hito": "INTERMEDIO", "Año": "2026"}}`.
  En los datos, `INTERMEDIO` solo existe en 2025 (cruce Hito×Año: CIERRE/2025=328,
  DIAGNOSTICO/2025=444, DIAGNOSTICO/2026=935, INTERMEDIO/2025=3940).
- **Síntoma**: 3 páginas con tabla de solo encabezados, todos los gráficos en
  blanco (ejes −0.04…0.04), dos secciones con "Sin datos disponibles" y, en la
  página 2, el texto literal
  `[Error en sección] ValueError: List of boxplot statistics and 'positions' values must have same the length`.
- **Causa probable**: `backend/rgenerator/reports/dispatch_v2.py::generar_pdf_v2`
  valida que EXISTA filtro temporal (`separar_filtros`) pero no que el DataFrame
  resultante tenga filas. `dia/crear_informe.py::_filtrar_temporal` puede devolver
  un df vacío sin error. `runtime.py::_ejecutar_seccion` (líneas 118–121, 128–131)
  captura la excepción y la **imprime en el PDF** en lugar de propagarla.
  El motor weasyprint sí levanta 400 (`periodos.py::_no_disponible`).
- **Fix sugerido**: en `generar_pdf_v2`, tras el filtro temporal, `raise
  DatosInsuficientes("Sin datos para los filtros seleccionados: …")` si el df
  queda vacío; y que `_ejecutar_seccion` nunca renderice el mensaje crudo de la
  excepción (logear y mostrar un texto neutro).

#### P0-2 · Dos gráficos del informe DIA oficial fallan con excepción visible incluso con datos válidos

- **Documento**: `dia__custom_dia_DIAGNOSTICO_2026.pdf`
- **Página**: 3
- **Síntoma**:
  - `Logro Promedio por Eje Temático` → `[Error en sección] IndexError: tuple index out of range`
  - `Logro Promedio por Habilidad` → `[Error en sección] ValueError: shape mismatch: objects cannot be broadcast to a single shape. Mismatch is between 'x' with shape (18,) and 'height' with shape (2,)`
- **Reproducir**: `POST /api/reports/custom/dia` con `{"Hito": "DIAGNOSTICO", "Año": "2026"}`.
- **Causa probable**: `valor_promedio_agrupado_por` en
  `backend/rgenerator/reports/charts.py`, invocada con
  `agrupar_principal_por: "Curso"` (18 cursos) + `agrupar_secundario_por:
  "Eje Temático" | "Habilidad"`. El shape `(2,)` frente a `(18,)` apunta a que el
  pivote colapsa a 2 columnas cuando la columna secundaria tiene nulos —
  `Eje Temático` es nulo en 1320/2386 filas del df de preguntas DIA.

#### P0-3 · Las tablas por alumno del DIA oficial no identifican al alumno: `N° Lista` y `Estudiante` = `nan`

- **Documento**: `dia__custom_dia_DIAGNOSTICO_2026.pdf`
- **Páginas**: 5–6 y ~60 de las 67 (una tabla por curso × 18 cursos)
- **Síntoma**: en `Logro por Alumno - 7 A` las 55 filas muestran `nan` en
  `N° Lista` y `Estudiante`; `Promedio Hito` es `nan%` en ~60% de las filas.
- **Causa raíz (dato, no render)**: en `metric_data` del indicador DIA, la
  dimensión `Nombre` y el campo `Numero Lista` son **nulos en 935/935 filas de
  DIAGNOSTICO 2026** (0 nulos en el resto de hitos/años). `Nombre_Norm` es el
  inverso: nulo en 4712/4712 filas de 2025 y en 375/935 de 2026. Es decir, hay dos
  cargas hechas con pipelines distintos y ninguna trae ambas claves.
  Consecuencia: `Logro_Promedio_Estudiante` (entity `Curso`+`Nombre_Norm`,
  `on_missing_entity: "null"`) degrada a NaN, y `Avance`/`Mejora_vs_Inicio` no
  pueden calcularse nunca porque ningún alumno tiene la misma clave en dos hitos.
- **Fix sugerido**: recargar los datos DIA 2026 con el pipeline que produce
  `Nombre`+`Numero Lista`; y en el render, no imprimir `nan` (usar `—`, como ya
  hace `report_pdl_idel`).

#### P0-4 · La columna `Avance` sale `nan%` en el 100% de las filas de los informes SIMCE oficiales

- **Documentos**: `simce__custom_simce.pdf` (pág 6–14, 31–70 apariciones por
  página), `simce_panguipulli__custom_simce_panguipulli.pdf` (pág 4–10)
- **Síntoma**: la columna `Avance` de `Logro por Alumno - <curso>` es `nan%` en
  todas las filas; `Mejora` también en filas aisladas.
- **Causa probable (dos capas)**:
  1. *Semántica*: `Avance` es un `slope` con `min_points: 2`. En el **primer**
     punto temporal del año no existe pendiente, así que un informe de la primera
     prueba tiene la columna estructuralmente vacía. Medido: nulos de `Avance` por
     mes en SIMCE → ABRIL 232/232, JUNIO 9/220, AGOSTO 2/212, OCTUBRE 6/210.
     El script eligió ABRIL. En Panguipulli, ABRIL 443/443.
  2. *Configuración desactualizada*: `backend/rgenerator/reports/simce/esquema.json`
     declara `time_ordinal_levels: ["ABRIL","JUNIO","AGOSTO","OCTUBRE","OCTUBRE 2"]`
     mientras los datos reales tienen `["ABRIL","AGOSTO","JUNIO","MAYO","NOVIEMBRE","OCTUBRE"]`.
     `MAYO` y `NOVIEMBRE` no están declarados y `"OCTUBRE 2"` no existe → esos
     meses tienen `Avance` **y** `Mejora_vs_Inicio` 100% nulos (MAYO/2026 196/196,
     NOVIEMBRE/2025 216/216).
- **Fix sugerido**: (a) sincronizar `time_ordinal_levels` con los datos o derivarlo
  de la dimensión; (b) ocultar la columna cuando no hay puntos suficientes;
  (c) formatear NaN como `—` en lugar de `nan%`.

#### P0-5 · `Habilidad` y `Eje Temático` = `nan` en toda la tabla `Logro por Pregunta` del SIMCE oficial

- **Documento**: `simce__custom_simce.pdf`
- **Página**: 14 (y las 3 tablas homólogas de los otros cursos)
- **Síntoma**: 35 filas con `Habilidad = nan` y `Eje Temático = nan`; solo se ve
  `N° Pregunta` y `Logro`.
- **Causa raíz (dato)**: en el df de preguntas de SIMCE, `Eje Temático` es nulo en
  1580/1680 filas (todos los meses salvo MAYO 2026) y `Habilidad` es nulo en
  300/1680 (ABRIL 2025: 260/260 — el mes que usa el informe). Falta el mapeo en
  el ETL de preguntas.

#### P0-6 · Los informes Word entregan instrucciones internas de la plantilla al cliente

- **Documentos**: los 6 `*__word_resumen_indicador.docx`
- **Ubicación**: 4.º párrafo del cuerpo
- **Texto literal**: `GUÍA (borrar en la versión final): esta plantilla se edita
  en Word. Todo texto entre llaves dobles es un código que el módulo Python
  informes/resumen_indicador.py reemplaza al generar el informe. Las tablas
  dinámicas usan etiquetas tr-for / tr-endfor en filas propias (ver la tabla de
  ejemplo). Las imágenes se insertan donde esté su código. OJO: no escribir
  sintaxis de etiquetas en texto normal — Jinja intentaría interpretarla.`
- **Causa**: el párrafo está en la plantilla
  `backend/rgenerator/reports/word/templates/resumen_indicador.docx` y nada lo
  elimina al renderizar.

#### P0-7 · Los informes Word muestran porcentajes imposibles (hasta 15 510 %)

- **Documentos**: `calculo_veloz` (`III°A → 5972.1%`), `fluidez_lectora`
  (`II°E → 15510.5%`), `idel` (`1° BÁSICO → 1952.1%`)
- **Causa**: `backend/rgenerator/reports/word/informes/resumen_indicador.py:71`
  aplica `formatos={"Promedio": ".1%"}` de forma incondicional. Con métricas que
  no son fracciones 0–1 (Puntaje 0–100, PPM 0–255) el promedio se multiplica por
  100. Verificado: Cálculo Veloz `Puntaje` mean = 56.6 → 5660 %; Fluidez
  `Cantidad` mean = 142.2 → 14 225 %; IDEL `Puntaje` mean = 37.9.
- **Fix sugerido**: elegir el formato según el rango de la métrica (o leer
  `Indicator.role_formats`), no fijarlo en el informe.

#### P0-8 · El informe Word de SIMCE sale sin datos: `N = 0`, `Promedio` vacío y gráfico en blanco

- **Documento**: `simce__word_resumen_indicador.docx`
- **Síntoma**: tabla con 4 filas (II A–II D), `N = 0` en todas y `Promedio` sin
  valor; la imagen embebida (`word/media/image1.png`) es un gráfico
  `Logro promedio por Curso` con ejes −0.04…0.04 y cero barras.
- **Causa**: `resumen_indicador.py:47` elige la columna de valor por una lista
  fija `("Logro", "Rend", "PorcLogro", "Puntaje")`. En SIMCE, `Logro` es
  **categórico** (`"Insuficiente"`, `"Elemental"`, `"Adecuado"`, dtype `str`), así
  que `pd.to_numeric(..., errors="coerce")` la deja 1286/1286 nula → `count = 0`,
  `mean = NaN`, df vacío al graficar. La columna numérica correcta es `Rend`
  (rol `logro_1` en `column_roles`).
- **Fix sugerido**: resolver la columna desde `Indicator.column_roles` y, en su
  defecto, descartar columnas no numéricas antes de elegir.

#### P0-9 · Los gráficos de "evolución" ordenan el eje temporal alfabéticamente

- **Documentos y páginas**:
  - `dia__periodo_personalizado_…Pullinque.pdf` pág 1 y 2 → eje `CIERRE,
    DIAGNOSTICO, INTERMEDIO` (el orden real es DIAGNOSTICO → INTERMEDIO → CIERRE)
  - `simce__custom_simce.pdf` pág 2 → `ABRIL, AGOSTO, JUNIO, MAYO, NOVIEMBRE, OCTUBRE`
  - `simce_panguipulli__custom…pdf` pág 2 → `ABRIL, AGOSTO, MAYO, SEPTIEMBRE`
  - `simce__periodo_personalizado_…IIA.pdf` pág 1 y 2 → `ABRIL, AGOSTO, JUNIO,
    MAYO, NOVIEMBRE, OCTUBRE`
- **Por qué es P0 y no cosmético**: el gráfico se titula "Evolución …" y la
  secuencia mostrada no es la real. Caso concreto en Panguipulli pág 2, II° medio C:
  se lee `55 → 62 → 45 → 60`, cuando cronológicamente es
  `ABRIL 55 → MAYO 45 → AGOSTO 62 → SEPTIEMBRE 60`. Un lector concluye lo
  contrario de lo que ocurrió.
- **Causa probable**: la capa de gráficos ordena las categorías con el `groupby`
  por defecto de pandas (alfabético). `periodos.py` sí ordena cronológicamente
  (`sorted(..., key=lambda v: (a_numero_mes(v) or 0, str(v)))`, líneas 571 y 659)
  y `HITO_A_MES` existe, pero ese orden no llega al chart. Revisar
  `backend/rgenerator/reports/charts.py` y el renderer de charts del motor
  weasyprint.

#### P0-10 · Encabezado del informe DIA por evaluación contradice su propio contenido

- **Documento**: `dia__periodo_ultima_prueba.pdf`
- **Páginas**: 1, 2, 3 (todas)
- **Síntoma**: el encabezado dice `Informe DIA Cierre / Lectura Nivel Medio /
  Octubre 2025` mientras el subtítulo del cuerpo dice `Año: 2026 · Hito:
  DIAGNOSTICO`. Además los gráficos incluyen ejes de Matemática (Geometría,
  Medición, Patrones y Álgebra, Álgebra y Funciones), así que "Lectura" también
  es falso.
- **Causa**: `indicators.pdf_layout` del indicador 2 trae
  `branding.center_header` con las tres líneas fijas, sin parametrizar por el
  período/asignatura efectivos.

#### P0-11 · Los tres informes oficiales muestran placeholders sin interpolar en el encabezado de todas las páginas

- **Documentos y páginas**:
  - `simce__custom_simce.pdf` — 14/14 páginas: `Informe Ensayo SIMCE / Asignatura - Curso / Mes Año`
  - `simce_panguipulli__custom…pdf` — 10/10 páginas: `Informe SIMCE Panguipulli / Asignatura - Curso / Mes Año`
  - `dia__custom_dia_DIAGNOSTICO_2026.pdf` — 67/67 páginas: `Informe DIA Diagnóstico / Asignatura Nivel Medio / Mes Año`
- **Causa**: `branding.center_header` está hardcodeado como texto plano en
  `backend/rgenerator/reports/{simce,simce_panguipulli,dia}/esquema.json`
  (verificado en `dia/esquema.json`: `["Informe DIA Diagnóstico", "Asignatura
  Nivel Medio", "Mes Año"]`). No hay sustitución con la asignatura / mes / año
  reales. `dispatch_v2.aplicar_pie_organizacion` resuelve el pie pero nadie
  resuelve el encabezado.

#### P0-12 · Los conteos "Cantidad de alumnos" están inflados: cuentan filas, no estudiantes

- **Documentos y páginas**:
  - `simce__periodo_ultima_prueba.pdf` pág 1 (tabla) y pág 2 (gráfico):
    II A declara `Alumnos = 31` y los niveles suman `26+25+7 = 58`.
    Igual II B `26` vs `48`, II C `26` vs `46`, II D `23` vs `44`.
  - `simce__periodo_semestral.pdf` / `anual.pdf` pág 2: total `117+60+19 = 196`
    frente a 106 estudiantes reales.
  - `idel__periodo_ultima_prueba.pdf` pág 2: `1° BÁSICO` totaliza 114 "alumnos"
    (≈19 estudiantes × 6 subpruebas).
  - `idel__periodo_semestral.pdf` / `anual.pdf` pág 2: versión 1 totaliza 542.
  - `dia__periodo_ultima_prueba.pdf` pág 2: `II D (TPI-510)` totaliza 198.
  - `dia__periodo_personalizado…pdf` pág 2: INTERMEDIO totaliza 2041.
- **Por qué es P0**: la tabla y el gráfico de la misma página se contradicen, y el
  gráfico está rotulado "Cantidad de alumnos".
- **Nota de contraste**: `calculo_veloz__periodo_ultima_prueba.pdf` pág 1 **sí**
  cuadra (III°C 22 = 9+9+4; IV°A 30 = 6+21+3), porque su métrica tiene una fila
  por estudiante. El defecto aparece cuando hay varias filas por estudiante
  (asignatura, habilidad, subprueba).
- **Fix sugerido**: contar distintos por la clave de estudiante
  (Rut / Nombre_Norm) en el agregador de niveles.

#### P0-13 · Columna `Alumnos` = 1 en todos los cursos del DIA por evaluación

- **Documento**: `dia__periodo_ultima_prueba.pdf`
- **Página**: 1
- **Síntoma**: las 18 filas de `Cuadro Resumen Logro por Curso` traen `Alumnos = 1`
  mientras el gráfico de la página 2 muestra 33–96 estudiantes por curso.
  (El informe oficial DIA sobre los mismos filtros muestra 25–94, también inflado
  ~2× por las dos asignaturas.)

#### P0-14 · La tabla `Promedios y medianas por subprueba` del PDL IDEL es ilegible

- **Documento**: `idel__custom_pdl_idel.pdf`
- **Páginas**: 2 y las homólogas de cada curso
- **Síntoma**: 16 columnas numéricas (8 evaluaciones × Prom/Med) comprimidas en el
  ancho de página: la fila de encabezados se superpone hasta quedar un borrón
  (`2022402402402502502502502502602602602602602602602602 6/v3 PromMe ProMe…`) y las
  celdas se pegan entre sí (`10.74.013.69.0 5.4 4.0 8.0 4.5 9.9 7.0`).
- **Sospecha adicional**: los valores parecen **duplicados** — en CT se lee
  `10.7 4.0 13.6 9.0 5.4 4.0 8.0 4.5 9.9 7.0 5.4 4.0 8.0 4.5 9.9 7.0`, donde los
  últimos 6 repiten los 6 anteriores. Revisar el pivote en
  `scripts/report_pdl_idel.py` / `backend/rgenerator/tooling/report_pdl_idel_tools.py`.

#### P0-15 · Etiquetas del eje X ilegibles en el gráfico de niveles del DIA oficial

- **Documento**: `dia__custom_dia_DIAGNOSTICO_2026.pdf`
- **Página**: 4
- **Síntoma**: los 18 nombres de curso se superponen hasta formar una mancha
  (`8I|A (TP|A50)7M8s6IT0)A8/7101)C-6IQA(7,101)6(0)0MnE5S(0DI0N)9A-5.10D0M)A6(0…`).
  Sin rotación ni reducción de fuente en `alumnos_por_nivel_cualitativo`.

---

### P1 — problema visual serio

#### P1-1 · El pie izquierdo de todos los informes weasyprint dice "Miguel Godoy Díaz"

- **Documentos**: los 12 `*__periodo_*.pdf` — **todas** sus páginas
  (`simce`, `idel`, `dia`, `calculo_veloz`, `fluidez_lectora`, en las 4 variantes
  de período). Verificado por extracción de texto: 1 aparición por página.
- **Criterio 6 incumplido.** En SIMCE/IDEL/CV/FL el nombre de la organización sí
  aparece, pero en el **encabezado**; en `dia__periodo_*` la organización no
  aparece en ninguna parte (el encabezado son las 3 líneas fijas del DIA), así que
  el único identificador del documento es el nombre del desarrollador.
- **Causa**: `indicators.pdf_layout` y `pdf_layout_historico` de los indicadores
  **1, 2, 3, 4 y 5** contienen `branding.left_footer = "Miguel Godoy Díaz"` en la
  DB. El indicador 6 está limpio.
  ```sql
  select id_indicator, name,
         (pdf_layout ilike '%godoy%')            as pdf_ev,
         (pdf_layout_historico ilike '%godoy%')  as pdf_hist
  from indicators order by id_indicator;
  -- 1..5 => t | t ; 6 => f | f
  ```
- **Por qué la guardia no lo detecta**: `tests/regresion/test_branding_sin_nombre_personal.py`
  audita solo los `.json` de `backend/schemas`, `backend/rgenerator/reports` y
  `data/database/reports_templates`. Los layouts vivos están en la DB, y
  `dispatch_v2.aplicar_pie_organizacion` solo rellena el pie **cuando viene
  vacío** — acá viene con valor, así que el fallback no actúa.
- **Fix sugerido**: (a) `UPDATE indicators SET pdf_layout = replace(...)` para
  vaciar `left_footer`; (b) extender la guardia a los layouts persistidos (test de
  integración sobre la tabla); (c) considerar que el runtime pise cualquier
  `left_footer` que coincida con un nombre personal.

#### P1-2 · Subtítulos con `repr` de listas de Python

- **Documentos y páginas**:
  - `simce__periodo_semestral.pdf` pág 1: `Año: 2026 · Mes: ['MAYO']`
  - `idel__periodo_semestral.pdf` / `anual.pdf` pág 1: `Año: 2026 · Versión: ['1', '2', '3']`
  - `simce__periodo_personalizado…pdf` pág 1: `Curso: II A · Año: ['2025', '2026'] · Mes: ['ABRIL', 'MAYO', 'JUNIO', 'AGOSTO', 'OCTUBRE', 'NOVIEMBRE']`
  - `dia__periodo_personalizado…pdf` pág 1: `Hito: ['DIAGNOSTICO', 'INTERMEDIO', 'CIERRE']`
- **Síntoma adicional**: en `simce__periodo_personalizado` la línea **desborda el
  ancho del bloque de texto** y sobrepasa la regla del encabezado por ambos lados;
  en `dia__periodo_personalizado` se parte en dos líneas mal centradas.
- **Causa**: el subtítulo hace `str()` del dict de filtros sin serializar las
  listas (`_resolver_semestral` y `_resolver_personalizado` devuelven listas por
  diseño, ver `periodos.py:575` y `:658-659`).

#### P1-3 · Los períodos "semestral" y "anual" de IDEL producen exactamente el mismo informe

- **Documentos**: `idel__periodo_semestral.pdf` vs `idel__periodo_anual.pdf`
  (páginas 1 y 2 idénticas salvo el subtítulo)
- **Causa**: en `periodos.py::a_numero_mes`, la rama numérica (líneas 160–165)
  se evalúa **antes** de `VERSION_A_MES` (líneas 176–179). Los datos IDEL guardan
  la versión como `"1"`, `"2"`, `"3"` (no `"v1"`), así que se interpretan como
  enero/febrero/marzo. Los tres caen en el 1er semestre → el filtro semestral
  incluye las 3 versiones, igual que el anual. Lo correcto sería v1→abril,
  v2→agosto, v3→noviembre, es decir v1 en el 1er semestre y v2/v3 en el 2.º.
- **Efecto colateral**: la descripción de la card "última prueba" queda como
  `Última evaluación registrada: 3 2026.` (P2-1).

#### P1-4 · Gráficos completamente vacíos presentados como si tuvieran datos

- `idel__periodo_ultima_prueba.pdf` pág 1: `Puntaje Promedio por Curso` — línea
  plana en 0.0, eje −0.04…0.04. Pág 2: `Puntaje Promedio por Evaluación` — 6
  líneas planas en 0.0 (CT, FLO, FNL, FSF, ILP, VSD).
- `idel__periodo_semestral.pdf` / `anual.pdf` / `personalizado.pdf` pág 1:
  `Evolución del Puntaje Promedio por Curso y Versión` — vacío, eje Y rotulado
  `Logro_1` (nombre interno de columna).
- `idel__periodo_ultima_prueba.pdf` pág 1: la tabla `Cuadro Resumen Puntaje por
  Curso` dice `Sin datos disponibles.` mientras el gráfico de la pág 2 sí tiene
  datos → el mismo informe se contradice.
- `idel__custom_pdl_idel.pdf` pág 40: `Tasa de mejora por curso` — ejes, leyenda
  y 6 etiquetas de curso, cero barras. Es el gráfico de síntesis del informe.
- `idel__custom_pdl_idel.pdf` pág 1: el heatmap `Mapa de riesgo` solo pinta la
  fila `1° BÁSICO`; las filas 2.º a 6.º quedan en blanco sin nota explicativa
  (la tabla de cobertura de la misma página muestra que esos cursos tienen
  estudiantes).
- **Causa probable**: el motor weasyprint por período lee la columna de valor de
  `column_roles` (`logro_1`), que en IDEL apunta a una columna que no queda
  numérica tras el filtro; y el renderer no distingue "sin datos" de "todo cero".

#### P1-5 · Encabezado de sección pegado a la regla del encabezado de página

- **Documentos y páginas**: 2.ª y 3.ª página de prácticamente todos los informes
  weasyprint — `simce__periodo_ultima_prueba` pág 2, `simce__periodo_semestral`
  pág 2, `simce__periodo_anual` pág 2, `simce__periodo_personalizado` pág 2,
  `idel__periodo_ultima_prueba` pág 2, `idel__periodo_semestral` pág 2,
  `idel__periodo_anual` pág 2, `dia__periodo_ultima_prueba` pág 2 y 3,
  `dia__periodo_personalizado` pág 2, `calculo_veloz` pág 2,
  `fluidez_lectora` pág 2 y 3.
- **Síntoma**: el `<h2>` de la primera sección de la página se dibuja a ras de la
  línea divisoria del encabezado (margen prácticamente nulo), mientras en la
  página 1 hay separación normal. Falta `margin-top` en el primer bloque de cada
  página del template.

#### P1-6 · Leyenda dibujada encima de los datos

- `simce__periodo_semestral.pdf` / `anual.pdf` pág 1: la leyenda de cursos se
  superpone a la primera barra en los dos gráficos.
- `simce__periodo_personalizado.pdf` pág 1: ídem (leyenda de 1 serie sobre la barra).
- `dia__periodo_personalizado.pdf` pág 1: leyenda de 8 cursos sobre el área de trazado.
- `idel__periodo_semestral/anual/personalizado` pág 1: leyenda dentro del plot.
- `calculo_veloz__periodo_ultima_prueba.pdf` pág 1: la leyenda `Puntaje / Nota`
  queda **flotando en el centro-derecha del área de datos**.

#### P1-7 · `Cálculo Veloz`: dos escalas incompatibles en el mismo eje

- **Documento**: `calculo_veloz__periodo_ultima_prueba.pdf`, pág 1
- **Síntoma**: `Puntaje y Nota Promedio por Curso` grafica Puntaje (0–60) y Nota
  (1–7) contra el mismo eje Y; las barras de Nota quedan reducidas a un muñón
  (3.3 junto a 46.2). Necesita eje secundario o dos paneles.

#### P1-8 · `Fluidez Lectora`: dos secciones con títulos distintos muestran el mismo gráfico

- **Documento**: `fluidez_lectora__periodo_ultima_prueba.pdf`, pág 2
- **Síntoma**: `Distribución de Categoría por Curso` y `Distribución de Calidad
  Lectora por Curso` renderizan datos y leyenda idénticos (12/17/8; No Aplica,
  MUY BAJA, BAJA, MEDIA, ALTA). Según `column_roles`, `habilidad` → `Calidad
  lectora` es una dimensión distinta de `nivel_de_logro` → `Categoria`.
  Uno de los dos encabezados no corresponde a su contenido.

#### P1-9 · Colores de leyenda indistinguibles

- `fluidez_lectora__periodo_ultima_prueba.pdf` pág 2: `No Aplica` y `ALTA` usan el
  mismo verde en las dos leyendas.
- `calculo_veloz__periodo_ultima_prueba.pdf` pág 2: `AVANZADO` y `EXPERTO` usan
  dos verdes casi idénticos.
- `idel__custom_pdl_idel.pdf` pág 2 vs `idel__periodo_*.pdf` pág 2: `Cierto Riesgo`
  se dibuja **lima** en el informe PDL y **amarillo** (`#eab308`, el oficial de
  `Indicator.achievement_levels`) en los informes por período. Los mismos 4
  niveles deberían verse igual en los dos informes del mismo indicador.

#### P1-10 · Nombres internos de columna expuestos como etiquetas de eje

- `fluidez_lectora__periodo_ultima_prueba.pdf` pág 3: eje X = `_cantidad`
- `calculo_veloz__periodo_ultima_prueba.pdf` pág 2: eje X = `_puntaje`
- `idel__periodo_semestral/anual/personalizado` pág 1: eje Y = `Logro_1`
- `simce__periodo_*` pág 1: ejes Y = `Rend`, `Simce`
- `simce_panguipulli__custom…pdf` pág 2: eje Y = `PorcLogro`

#### P1-11 · Logro mostrado como fracción con 1 decimal, perdiendo la información

- `simce__periodo_ultima_prueba.pdf` pág 1: `Rend prom.` = `0.5 / 0.4 / 0.4 / 0.4`
  para los 4 cursos (el gráfico revela 0.47 / 0.41 / 0.43 / 0.38); `Rend mín.` y
  `Rend máx.` quedan en `0.2 / 0.8`.
- `dia__periodo_ultima_prueba.pdf` pág 1: 8 de 18 cursos muestran `0.4`
  indistinguibles; `Logro mín. 0.0` y `Logro máx. 1.0` en casi todos.
- Los informes oficiales del mismo dato lo muestran como porcentaje (`53%`, `44%`),
  así que la inconsistencia es entre motores.

#### P1-12 · Fecha cruda con hora en el subtítulo de Fluidez Lectora

- **Documento**: `fluidez_lectora__periodo_ultima_prueba.pdf`, pág 1
- **Síntoma**: `Fecha: 2026-04-07 00:00:00 · N Prueba: Ensayo 1`.
  Mismo texto en la descripción de la card `periodo_ultima_prueba` del endpoint.
- **Causa**: `periodos.py::_describir_evaluacion` hace `str(valor).upper()` sobre
  un `Timestamp` sin formatear (línea 353).

#### P1-13 · `Fluidez Lectora` no puede generar informes semestral ni anual pese a tener el año en los datos

- **Motivo devuelto por el endpoint**: `"No se detectó una dimensión de año en los
  datos de este indicador — el informe semestral no se puede acotar."`
- **Realidad**: el indicador tiene la columna `Fecha` con timestamps completos
  (`2026-04-07`), de la que se puede derivar el año.
- **Causa**: `periodos.py::detectar_columnas_temporales` busca el año solo por
  nombre de columna (`_TOKENS_ANIO`) y no considera derivarlo de una columna de
  fecha, aunque `a_numero_mes` sí sabe leer fechas ISO. 2 de las 4 cards quedan
  inutilizables para este indicador.

#### P1-14 · Etiquetas del eje X superpuestas

- `dia__periodo_ultima_prueba.pdf` pág 1 y 2: los nombres de curso rotados se
  pisan entre sí (`7 A` / `8 A` / `I A (TPI-510)`).
- `simce__custom_simce.pdf` pág 2 y `simce_panguipulli__custom…pdf` pág 2: el
  gráfico de evolución se renderiza con una fuente notablemente menor que el resto
  del informe y las etiquetas de valor se solapan (`53% 52% 55% 54% 60% 53%`).
- `idel__custom_pdl_idel.pdf` pág 3: en los 6 paneles de boxplot las etiquetas
  `2024/v1 2024/v2 2025/v1 …` se pegan.
- `idel__custom_pdl_idel.pdf` pág 20: la fila de siglas del roster
  (`CTCTCTCT FLOFLOFLOFLO …`) queda ilegible.

#### P1-15 · El informe DIA mezcla asignaturas en un mismo agregado

- **Documento**: `dia__periodo_ultima_prueba.pdf` pág 2 y
  `dia__custom_dia_DIAGNOSTICO_2026.pdf` pág 6
- **Síntoma**: `Logro Promedio por Eje Temático` promedia en un solo gráfico ejes
  de Lenguaje (Narración, Poema, Texto dramático, Texto no literario, Texto de los
  medios) y de Matemática (Geometría, Medición, Números, Números y Operaciones,
  Patrones y Álgebra, Probabilidad y Estadística, Datos y Probabilidades, Álgebra y
  Funciones). Idem la tabla `Logro por Pregunta - 7 A`, que intercala preguntas de
  ambas asignaturas.
- **Además**: hay categorías duplicadas sin normalizar (`Números` y `Números y
  Operaciones`; `Datos y Probabilidades` y `Probabilidad y Estadística`).
- **Nota**: el placeholder `Asignatura Nivel Medio` del encabezado (P0-11) indica
  que el informe fue diseñado para generarse **por asignatura**; falta ese filtro.

#### P1-16 · Los `.docx` no tienen encabezado ni pie de página, y la organización no aparece

- **Documentos**: los 6 `*__word_resumen_indicador.docx`
- **Verificado**: el paquete OOXML no contiene `word/header*.xml` ni
  `word/footer*.xml`, y `word/document.xml` no tiene `headerReference` ni
  `footerReference`. La cadena `Fundación` / `PHP` no aparece en ninguna parte del
  documento.
- **Criterios 1 y 6 incumplidos por ausencia.**

#### P1-17 · La columna `N` de los `.docx` cuenta filas, no estudiantes

- `dia__word_resumen_indicador.docx`: `2 A → 289`, `4 A → 362`, `II D (TPI-510) → 304`
- `idel__word_resumen_indicador.docx`: `1° BÁSICO → 890`, `2° BÁSICO → 970`
- `calculo_veloz__word_resumen_indicador.docx`: `III°A → 373`, `II°C → 403`
- Cursos reales de ~25–35 estudiantes. Además el encabezado dice `Categoría`
  cuando el contenido es el curso, y `N` no indica qué cuenta.

---

### P2 — pulido

- **P2-1 · Descripciones de card poco legibles.** `GET /api/indicators/3/report-options`
  devuelve `"Última evaluación registrada: 3 2026."` (IDEL) — debería ser
  `"v3 · 2026"`. `GET /api/indicators/5/report-options` devuelve
  `"Última evaluación registrada: 2026-04-07 00:00:00 (prueba Ensayo 1)."`
  y `"(prueba Ensayo 1)"` duplica la palabra "prueba".
- **P2-2 · Capitalización inconsistente de los labels de card**: `Informe última
  prueba`, `Informe semestral`, `Informe Anual`, `Informe Personalizado`.
- **P2-3 · Encabezados de tabla sin tildes** en los tres informes oficiales:
  `Minimo`, `Maximo` (`simce__custom_simce.pdf` pág 1,
  `simce_panguipulli__custom…pdf` pág 1, `dia__custom_dia_DIAGNOSTICO_2026.pdf` pág 1).
- **P2-4 · Título duplicado** en los informes oficiales: el `<h2>` de la sección y
  el título embebido en el PNG dicen lo mismo (`Logro Promedio por Nivel`,
  `Rendimiento Promedio por Curso`, `Distribución de Logro por Curso`…).
  `dia__custom_dia_DIAGNOSTICO_2026.pdf` pág 2–3, `simce__custom_simce.pdf` pág 1–2,
  `simce_panguipulli__custom…pdf` pág 1–2.
- **P2-5 · Valores crudos sin normalizar en textos visibles**: `DIAGNOSTICO` sin
  tilde (`dia__periodo_ultima_prueba.pdf` pág 1 y
  `dia__periodo_personalizado…pdf` pág 1–2).
- **P2-6 · Nombres de estudiante truncados** en el roster del PDL IDEL
  (`idel__custom_pdl_idel.pdf` pág 20): `Fuentes Cortez Agustina Igna…`,
  `Gómez Maldonado Isidora Arac…`, `Huiriman Spuler Maximiliano …`, con margen
  lateral disponible.
- **P2-7 · Barra de color sin unidad** en el heatmap del PDL IDEL
  (`idel__custom_pdl_idel.pdf` pág 1): la escala 0–100 no dice que son porcentajes.
- **P2-8 · Metadatos de los `.docx`**: `dc:creator = "python-docx"`,
  `dc:title` vacío y `dcterms:created = 2013-12-23T23:15:00Z` (fecha de la
  plantilla base).
- **P2-9 · `Nota máx. = 4.0` en los 12 cursos** de
  `calculo_veloz__periodo_ultima_prueba.pdf` pág 1 — revisar si la escala de nota
  está topada; en escala chilena 1–7 llama la atención.

---

### Criterio 5 — páginas desperdiciadas

| Documento | Página | Desperdicio |
|---|---|---|
| `idel__periodo_ultima_prueba.pdf` | 1 | ~45 % en blanco (tabla reemplazada por "Sin datos disponibles.") |
| `idel__periodo_semestral/anual/personalizado.pdf` | 1 | ~60 % en blanco (un gráfico vacío) |
| `simce__periodo_semestral/anual/personalizado.pdf` | 2 | ~50 % en blanco (un gráfico) |
| `dia__periodo_ultima_prueba.pdf` | 3 | ~60 % en blanco (un gráfico que cabía en la pág 2) |
| `dia__periodo_personalizado…pdf` | 2 | ~50 % en blanco |
| `fluidez_lectora__periodo_ultima_prueba.pdf` | 1 y 3 | ~40 % y ~65 % en blanco |
| `idel__custom_pdl_idel.pdf` | 19 (y homólogas) | página completa para la frase "Sin estudiantes en riesgo persistente en este curso." |
| `simce__custom_simce.pdf` | 14 (y las 3 homólogas) | tabla de 4 columnas ocupando ~40 % del ancho; caben 2 columnas de preguntas por página → ahorra ~4 páginas |
| `simce_panguipulli__custom…pdf` | 9 y 10 | ~25 % en blanco cada una |
| `dia__custom_dia_DIAGNOSTICO_2026.pdf` | 5–67 | 2 tablas por curso × 18 cursos = 63 páginas; con el nombre del alumno arreglado (P0-3) la tabla `Logro por Alumno` de un curso de 55 registros se parte en 2 páginas por 5 columnas estrechas |

---

## 4. Lo que sí está bien

- `idel__custom_pdl_idel.pdf` es el informe más maduro: encabezado y pie
  consistentes en las 40 páginas (org a la izquierda, `Página N` a la derecha), uso
  de `—` para los faltantes en lugar de `nan`, nomenclatura de subpruebas
  **correcta** según el glosario (CT Comprensión de Textos, FLO Fluidez en la
  Lectura Oral, FNL Fluidez en Nombrar Letras, FSF Fluidez en Segmentación de
  Fonemas, ILP Identificación de Letras y Palabras, VSD Vocabulario Sobre
  Dibujos), leyenda de códigos explícita, y una grilla 2×3 de boxplots que
  aprovecha bien la página.
- La tabla `Evolución del promedio por subprueba` (pág 40) con Δ y flechas de
  tendencia es un buen modelo a replicar.
- `calculo_veloz__periodo_ultima_prueba.pdf` pág 1 es el único caso donde
  `Alumnos` cuadra con la suma de niveles.
- El motor weasyprint devuelve `400` con mensaje legible cuando el período no
  tiene datos, y los `motivo_no_disponible` del endpoint son accionables
  ("pide a tu administrador que agregue secciones en Editor de Layout → …").
- `dispatch_v2.aplicar_pie_organizacion` funciona: los 4 informes oficiales
  (`custom_*`) llevan `Fundación PHP` en el pie izquierdo.

---

## 5. Orden de ataque sugerido

1. **P1-1** (pie con nombre personal) — 12 de 20 PDF; un `UPDATE` y extender la guardia.
2. **P0-11** (placeholders en el encabezado) — 91 de 167 páginas.
3. **P0-1** + **P0-2** (excepciones visibles y 200 con PDF vacío) — bloquea la entrega.
4. **P0-4 / P0-3 / P0-5** (`nan` en tablas): formatear NaN como `—` es un fix
   transversal y barato; la recarga de datos DIA 2026 y el mapeo de habilidad/eje
   de SIMCE son trabajo de ETL.
5. **P0-9** (orden temporal alfabético) y **P0-12** (conteos inflados) — datos falsos.
6. **P0-6 / P0-7 / P0-8** (los tres bugs del Word) — un solo archivo,
   `word/informes/resumen_indicador.py`, más el párrafo de la plantilla.
7. **P1-5** (margen del primer encabezado por página) — una regla CSS, afecta 12 documentos.
