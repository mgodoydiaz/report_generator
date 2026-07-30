# QA visual — Piloto SIMCE del motor único (gate de fase 3)

**Fecha**: 2026-07-30 · **Rama**: `dev2` (HEAD `698bd36`) · **Agente**: QA visual (Opus)
**Alcance**: gate §5.3 del [contrato del motor único](../desarrollo/contrato_motor_unico.md), revisión de los 7 PDFs del piloto, los 7 puntos "con lupa" del implementador y una batería adversarial.
**Referencia visual aprobada**: `Evaluaciones 2026/SIMCE/Pullinque Matemáticas Mayo/informe.pdf` (LaTeX, 14 págs).

> Este informe **reporta**; no modifica código. Las decisiones de paleta y de calibración del riesgo son del dueño.

---

## 0 · Veredicto

**NO-GO para abrir la fase 4 hoy · GO en cuanto se cierren los 2 P0.**

El piloto está bien construido: el contrato se implementó como se especificó, la retrocompatibilidad es exacta, la paridad estructural con la referencia Pullinque es completa (superset) y los 1482 tests pasan. Pero **el gate §5.3.1 dio un falso verde** (el generador no ejercita ni una sola card del piloto) y **el modo `personalizado` entrega en silencio un informe que no corresponde al período pedido**. Replicar el patrón a DIA hoy multiplicaría ambos por 6.

| Conteo | P0 | P1 | P2 |
|---|---|---|---|
| Hallazgos | **2** | **4** | **12** |

De los P1, **uno es preexistente** (P1-3, presente idéntico en el formato oficial de hoy) y no es regresión del piloto — pero bloquea la paridad con la referencia.

---

## 1 · Gate §5.3

| # | Criterio | Resultado |
|---|---|---|
| 1 | `generar_ejemplos_informes.py` ⇒ 0 ERROR | ⚠️ **0 errores, 28 archivos — pero falso verde** (ver P0-1) |
| 2 | Revisión de calidad de los modos | ✅ hecha (este documento) |
| 3 | Diff visual contra la referencia | ✅ hecho (§3) |
| 4 | `pytest -q -m "not slow"` | ✅ **1482 passed, 3 skipped, 0 failed** (94 s) |

### Cambios de conteo del generador

Salida de `docker compose -f docker-compose.dev.yml exec -T backend python scripts/generar_ejemplos_informes.py`:

```
Total: 28 | errores: 0 | salida: /app/data/tmp/ejemplos_informes
```

| Indicador | Antes del piloto | Ahora | Nota |
|---|---|---|---|
| SIMCE — 4 cards de período | generaban (motor `weasyprint`) | **OMITIDO** `motor desconocido custom:simce` | ⛔ P0-1 |
| SIMCE — formato oficial | OK | OK (1148 KB) | sin cambio |
| SIMCE Panguipulli — 4 cards | OMITIDO (sin `pdf_layout`) | OMITIDO (sin `pdf_layout`) | ✅ correcto hasta fase 4 |
| DIA / IDEL / Fluidez / Cálculo Veloz | igual | igual | sin cambio |

---

## 2 · Matriz PDF × criterio

Los 7 PDFs del piloto (`C:\Users\magod\Desktop\PDF_test\piloto_simce\`), verificados con extracción de texto y render a 300 dpi.

| PDF | Págs | Secciones §4.1/§4.2 completas y en orden | Pie = org | Cero `nan`/`None` | Orden cronológico | Conteos honestos | Títulos correctos | ≤2 decimales | Sin desborde de margen |
|---|---|---|---|---|---|---|---|---|---|
| `00_retrocompat_*` ×2 pares | 13 | n/a (formato oficial) | ✅ | ✅ | ✅ | ⚠️ P1-3 | ✅ | ✅ | ✅ |
| `01_ultima_prueba_2026` | 15 | ✅ 12/12 | ✅ | ✅ | ✅ | ⚠️ P1-3 | ✅ | ✅ | ✅ |
| `02_semestral_2026` | 4 | ✅ 1-9 + nota de evolución | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `03_anual_2026` | 5 | ✅ 1-9 + nota evol. + nota riesgo | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `04_ultima_prueba_2025` | 17 | ✅ 12/12 | ✅ | ✅ | ✅ | ⚠️ P1-3 | ✅ | ✅ | ✅ |
| `05_personalizado_1sem_2025` | 8 | ✅ = anual (evol. + riesgo) | ✅ | ✅ | ✅ | ✅ | ❌ **P1-1** | ✅ | ✅ |
| `06_personalizado_anio_2025` | 7 | ✅ = anual (evol. + riesgo) | ✅ | ✅ | ✅ | ✅ | ⚠️ P1-1 | ✅ | ✅ |
| `07_fallback_calculo_veloz` | 2 | n/a (fallback v1) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Verificaciones transversales que pasaron limpias en los 7 PDFs**: cero ocurrencias de `nan`/`NaN`/`None`/`null`; cero números con >2 decimales; cero bloques de texto fuera del margen (612×792 pt, chequeo de bbox página a página); pie izquierdo = nombre de la organización (`Fundación PHP`, y `Colegio Demo` en la org demo) en el 100% de las páginas.

---

## 3 · Paridad con la referencia Pullinque

Estructura de la referencia (14 págs) contra `01_ultima_prueba_2026` (15 págs):

| Referencia | Piloto | Estado |
|---|---|---|
| Cuadro Resumen Logro por Curso (p1) | Resumen de Logro por Curso (p1) | ✅ |
| Resumen Puntaje SIMCE por Curso (p1) | ídem (p1) | ✅ |
| Rendimiento Promedio por Curso (p2) | ídem (p1) | ✅ densificado |
| Distribución de Puntaje SIMCE (p3) | ídem (p2) | ✅ |
| Cantidad de Alumnos por Nivel de Logro (p4) | + "y Curso" (p3) | ✅ |
| — | **Composición Global por Nivel** (p3) | ➕ nuevo (N7) |
| Logro por Habilidad + Eje Temático (p5) | ídem (p4) | ✅ |
| — | **Estudiantes en Riesgo** (p4-6) | ➕ nuevo |
| Reporte de estadísticas por pregunta (p6) | Estadística por Pregunta del Establecimiento (p7) | ⚠️ P1-3 |
| Logro por Alumno / por Pregunta × 4 cursos (p7-14) | ídem (p8-15) | ✅ |

**El piloto es un superset de la referencia**: las 7 secciones de la referencia están, en el mismo orden, más 2 secciones nuevas de las fichas. Un salto de página por curso, correcto (T3 del contrato confirmado: la ficha estaba obsoleta, el código ya lo hacía).

**Estética**: encabezado con logo PHP izq. + escudo del establecimiento der. + regla horizontal ✅; tablas centradas con bordes completos y cabecera en negrita ✅; misma familia tipográfica (Nimbus Sans) ✅; jerarquía 18 pt título / 12 pt subtítulo / 9 pt cuerpo ✅. Sin solapes reales en ninguna página (punto 4 del implementador: el jitter de matplotlib no produjo ningún cruce de elementos).

**Salvedad del dueño respetada**: bloque de título en la primera página seguido inmediatamente del contenido, **sin portada dedicada** ✅.

---

## 4 · Hallazgos

### P0-1 · El gate no ejercita ninguna card del piloto (falso verde)

**Dónde**: `scripts/generar_ejemplos_informes.py:198` y `:222`.
**Síntoma**: las 4 cards de período de SIMCE salen `OMITIDO — motor desconocido custom:simce`. El resumen dice "errores: 0" porque OMITIDO no cuenta como ERROR.
**Diagnóstico**: el despacho del script es una whitelist por igualdad exacta:

```python
elif op["motor"] in ("weasyprint", "pdl_idel"):
    body = {"engine": op["motor"]}
    ...
else:
    resumen.append((archivo, "OMITIDO", f"motor desconocido {op['motor']}"))
```

El piloto cambió `report_options` para publicar `motor = f"custom:{nombre_modulo}"` (`backend/routers/indicators.py:490`) y el script quedó sin actualizar. Verificado por API: las 4 cards de SIMCE salen `motor=custom:simce, disponible=True` — el backend está bien, el que no las sabe invocar es el script de QA.

Esto viola el segundo criterio de §5.3.1 ("ninguna card que antes estaba disponible pase a fallar"): antes del piloto SIMCE tenía `pdf_layout` y las 4 generaban.

**⚠️ Trampa al corregirlo**: la rama de `weasyprint` manda `body = {"engine": op["motor"]}`. Mandar `engine: "custom:simce"` sería doblemente incorrecto — por §2.2 un `body.engine` explícito **fuerza el fallback v1**, y además `REPORT_ENGINES` no lo tiene registrado (422). Para los motores `custom:*` hay que mandar **solo** `{"periodo": ...}` (+ asignatura), sin `engine`.

---

### P0-2 · `personalizado` con rango sin datos devuelve 200 con el informe de todo el dataset

**Reproducción** (`POST /api/indicators/1/export-pdf`, org 1):

| Caso | Body `periodo` | Esperado | Real |
|---|---|---|---|
| Rango vacío | `{"tipo":"personalizado","fecha_inicio":"2019-01-01","fecha_fin":"2019-12-31","filtros":{"Asignatura":["Matemáticas"]}}` | 400 accionable | **200 · 1524 KB · 7 págs** |
| Rango invertido | `fecha_inicio:"2025-12-01", fecha_fin:"2025-01-01"` | 400 accionable | **200 · 1524 KB · 7 págs** |

El PDF resultante trae **el año 2026 completo** (bloque de título: "2025"… encabezado: `Asignatura: ['Matemáticas']`), pesa más que el personalizado de todo 2025 (1334 KB) y no lleva ninguna marca de que el rango pedido no existía.

**Por qué es P0 y no P2**: no es un error de validación cosmético — el sistema entrega **en silencio** un informe con datos que no corresponden al período solicitado. Un usuario que pide "enero–diciembre 2019" recibe un PDF con aspecto legítimo lleno de datos de 2026. Es el peor modo de falla posible en un informe que va a un establecimiento.

**Diagnóstico**: cuando `_resolver_personalizado` no encuentra datos en el rango, no levanta `DatosInsuficientes` ni marca el resultado como no disponible; devuelve un resultado sin filtros temporales efectivos y con `descripcion` vacía. El módulo recibe `filtros` sin recorte temporal ⇒ carga todo. La `descripcion` vacía es además lo que destapa P1-2.

**Contraste**: la validación de asignatura sí está bien blindada (3 casos adversariales, los 3 con 400 accionable — ver §6).

---

### P1-1 · El bloque de título y el encabezado dan períodos distintos en `personalizado`

| PDF | Bloque de título (p1, 3ª línea) | Encabezado corrido (p2+) |
|---|---|---|
| `01_ultima_prueba_2026` | `MAYO 2026 (prueba 1)` | `MAYO 2026 (prueba 1)` ✅ |
| `02_semestral_2026` | `1er sem. 2026` | `1er semestre 2026 (enero–julio)` ✅ |
| `03_anual_2026` | `2026` | `2026` ✅ |
| `05_personalizado_1sem_2025` | **`2025`** | **`ENERO 2025 – JULIO 2025`** ❌ |
| `06_personalizado_anio_2025` | `2025` | `ENERO 2025 – DICIEMBRE 2025` ⚠️ |

En **05 el título miente**: dice "2025" cuando el informe cubre solo enero–julio. Si alguien comparte la primera página, comunica un año completo.

**Diagnóstico — doble fuente de verdad**: el router inyecta `ResultadoPeriodo.descripcion` en `branding.center_header` (contrato §2.1 paso 7), mientras el módulo calcula por su cuenta `_descripcion_periodo(preparado, modo)` para el bloque de título (`custom/simce.py:808` y `:846`), que en `personalizado` degrada al año. La `descripcion` resuelta por el router **nunca llega al bloque de título** — el contrato no previó ese canal. Fix natural: pasarla al módulo (p. ej. `params["periodo_desc"]`) y usarla en ambos lugares, dejando `_descripcion_periodo` como fallback para invocación directa.

---

### P1-2 · Repr de lista Python filtrado al encabezado

`rango_vacio_2019.pdf` y `rango_invertido.pdf` imprimen en el encabezado central de todas las páginas:

```
Asignatura: ['Matemáticas']
```

Corchetes y comillas de Python en un documento para un establecimiento. Aparece cuando `descripcion` queda vacía y cae el `filters_label` por defecto (`formatear_filtros` no desenvuelve listas de un elemento). Hoy solo se destapa por P0-2, pero el defecto de formato es independiente y puede aflorar en cualquier ruta que deje la descripción vacía.

---

### P1-3 · Estadística por Pregunta: los conteos A–E no son conteos *(preexistente, no es regresión)*

| Pregunta 1 | Referencia (LaTeX) | Piloto y formato oficial |
|---|---|---|
| A | **62** | **2.56** |
| %A | 65.3% | 64% |
| B | 15 | 0.66 |
| %B | 15.8% | 16% |

Los porcentajes son correctos; **las columnas de conteo absoluto no**. Ningún conteo de alumnos puede ser 2.56.

**Diagnóstico**: `tables.py:286` hace `df.groupby("Pregunta")[["A".."E"]].sum()`. En la carga actual de la métrica 5 esas columnas guardan **proporciones por curso**, así que la suma de los 4 cursos da ≈ 2.56 (= 4 × 0.64). `_formatear_alternativas` (`tables.py:320`) detecta que hay decimales y los imprime con 2 decimales — el docstring documenta el síntoma ("la métrica guarda conteos enteros en unas cargas y proporciones en otras") pero no resuelve la causa.

**Verificado que no es regresión del piloto**: `00_retrocompat_matematicas_DESPUES.pdf` (formato oficial) imprime exactamente los mismos valores. Es deuda anterior. **Pero bloquea el objetivo del motor único**: mientras la referencia LaTeX muestre 62 y el motor muestre 2.56, el motor no puede reemplazarla.

Salidas posibles (decisión del implementador): reconstruir el conteo como `proporción × n_alumnos` por curso antes de sumar, u ocultar las columnas absolutas cuando el dato es proporcional y dejar solo %A–%E.

**Pérdida adicional de fidelidad**: la referencia sombrea las celdas de la tabla (verde/amarillo) marcando alternativa correcta y distractor; el piloto la imprime en blanco y negro.

---

### P1-4 · Riesgo persistente mezcla alumnos que dejaron de rendir

Ver §5, punto 2.

---

### P2 (12)

| # | Hallazgo | Dónde | Diagnóstico |
|---|---|---|---|
| P2-1 | Etiquetas blancas ilegibles sobre los niveles claros | `01` p3, `06` p6 | Contraste WCAG: Insuficiente `#dc2626` 4.83:1 ✅; **Elemental `#eab308` 1.92:1** ❌; **Adecuado `#22c55e` 2.28:1** ❌ (mínimo 4.5). Con texto negro serían 10.95:1 y 9.22:1. Fix: color de etiqueta por luminancia del segmento. |
| P2-2 | Columna `Nivel` 100% constante | `05` p7-8, `06` p7 | 51/51 y 82/82 filas dicen "Insuficiente" — es el criterio de la tabla, no información. |
| P2-3 | Tabla de riesgo a 6 pt vs 8-9 pt del resto | `06` p7 | Rompe la jerarquía tipográfica interna del documento. |
| P2-4 | Habilidad/Eje en orden alfabético, no curricular | `01` p4, `02` p4 | La referencia usa orden curricular (Números, Álgebra, Geometría, Probabilidad); el piloto imprime Geometría, Números, Probabilidad, **Álgebra** — la tilde manda "Álgebra" al final. `ordenar_valores_categoricos` (`helpers.py:500`) preserva a propósito el orden del caller cuando no hay dígitos, así que el orden lo fija el `groupby` de pandas. Preexistente. |
| P2-5 | Leyendas en orden inverso entre dos gráficos de la misma página | `01` p3 | Arriba: Insuficiente→Adecuado. Abajo: Adecuado→Insuficiente. |
| P2-6 | "Estudiantes en Riesgo" ordenada de mejor a peor | `01` p4-6 | 43% → 20%: el alumno más crítico queda en la última página. Invertir. |
| P2-7 | Fila huérfana al pie de página | `01` p4 | El encabezado + 1 fila quedan solos antes del salto. |
| P2-8 | 3 columnas muertas en la primera prueba del año | `01` p8 | `Promedio Año` duplica `Logro` y `Avance`/`Mejora` salen "—" en el 100% de las filas. **No está roto**: en `04` (prueba 5 de 2025) se pueblan correctamente. Sugerencia: ocultar columnas derivadas 100% vacías. |
| P2-9 | Una nota de 3 líneas ocupa una página entera | `03` p5 | El `break_before` de la sección se aplica aunque degrade a nota. |
| P2-10 | "Minimo"/"Maximo" sin tilde | todos | Heredado de la referencia; consistente, pero es una falta de ortografía. |
| P2-11 | Barras que tocan el borde superior del área de trazado | `01` p3, `06` p6 | Falta headroom en el eje Y (`II A`=29 con tope 29; `II C`=34 con tope 34). |
| P2-12 | Mensaje de error poco específico | API | Asignatura inexistente ⇒ "Sin datos cargados para este indicador", sin nombrar la asignatura pedida. |

---

## 5 · Veredicto de los 7 puntos "con lupa"

### 1 · Colores de niveles — **NO es una regresión; requiere decisión del dueño solo sobre el matiz**

El planteamiento del implementador ("el gráfico pasa al semáforo vs los colores de la referencia") **parte de una premisa equivocada**: la referencia Pullinque **ya usa un semáforo**. Muestreo de píxeles:

| Nivel | Referencia (LaTeX) | Piloto (`achievement_levels`) |
|---|---|---|
| Insuficiente | `#e64b35` (tomate) | `#dc2626` (rojo) |
| Elemental | `#f1a340` (naranja) | `#eab308` (amarillo) |
| Adecuado | teal ≈ `#1aa090` | `#22c55e` (verde) |

La diferencia es de **saturación y matiz dentro del mismo esquema conceptual**, no de esquema. A favor del piloto: los colores salen de `Indicator.achievement_levels`, la misma fuente que la página de Indicadores y los dashboards — una sola fuente de verdad, exactamente lo que pide el contrato.

**Recomendación de QA**: mantener la paleta de `achievement_levels`. Lo que sí hay que corregir con independencia de la decisión estética es **P2-1**: las etiquetas blancas sobre Elemental (1.92:1) y Adecuado (2.28:1) son ilegibles. La referencia comparte el defecto (blanco sobre naranja ≈ 2.1:1), así que arreglarlo no aleja del original.

**→ Decisión del dueño**: ¿matiz de la referencia (tomate/naranja/teal) o matiz de los dashboards (rojo/amarillo/verde)? Capturas: `01_ultima_prueba_2026.pdf` p3 y `06_personalizado_anio_2025.pdf` p6 vs referencia p4.

### 2 · Riesgo persistente 2025 — **el criterio es correcto; la presentación necesita calibración**

Datos medidos:

| Informe | Filas | Pares de evaluaciones usados |
|---|---|---|
| `06` (año 2025) | **51** | OCTUBRE→NOVIEMBRE ×40 · ABRIL→JUNIO ×6 · JUNIO→AGOSTO ×4 · AGOSTO→OCTUBRE ×2 |
| `05` (1er sem 2025) | **82** | ABRIL→JUNIO ×82 |

Confirmado el diagnóstico del implementador: **12 de 51 (24%) son pares antiguos** — alumnos cuyas dos últimas evaluaciones fueron en abril-octubre y que no rindieron en noviembre. Aparecen mezclados con los 40 que sí están en riesgo *hoy*, sin ninguna marca que los distinga. Un jefe de UTP que trabaje esta lista va a buscar alumnos que ya no rinden.

Detalle contraintuitivo pero **correcto**: el 1er semestre tiene *más* alumnos en riesgo persistente (82) que el año completo (51), porque en el año se evalúan las **dos últimas** evaluaciones de cada alumno y muchos mejoraron hacia octubre-noviembre.

Legibilidad: las 51 filas **caben en una sola página** y el render a 300 dpi es limpio — columnas bien separadas, sin solapes, tildes y ñ presentes (las verifiqué en el texto: "ACUÑA", "AVENDAÑO", "BRICEÑO" están correctas). Orden: agrupado por curso en orden natural y ascendente por `Rend actual` dentro de cada curso, tal como pide §3.3 ✅.

**Calibraciones concretas propuestas para el dueño** (elegir una o combinar):

1. **Exigir que el par incluya la última evaluación del período.** Deja 40 filas en `06`, todas accionables hoy. Es la más simple y la que más ruido quita.
2. **Ventana máxima de antigüedad** (p. ej. el par debe caer dentro de las últimas 2 evaluaciones del establecimiento). Equivalente a la 1 pero tolera un alumno ausente en la última fecha.
3. **Mantener a todos y agregar una columna `Última evaluación`** o marcar visualmente las filas con par antiguo. Conserva la información ("este alumno estaba en riesgo y dejó de rendir" también es un dato de gestión) a cambio de una columna.
4. **Separar en dos tablas**: "En riesgo persistente (evaluación vigente)" y "Sin evaluación reciente". La más explícita pedagógicamente.

Recomendación de QA: **opción 1 como default + opción 3 como sección aparte** si el dueño quiere no perder a los que dejaron de rendir.

### 3 · Tabla de riesgo a 6 pt — **legible, pero inconsistente; la columna Nivel sí sobra**

- **¿Legible al imprimir?** Sí. Render a 300 dpi (§ verificación): trazo vectorial nítido, celdas con padding suficiente, sin colisiones. 6 pt está por debajo de lo cómodo pero es legible. El beneficio real: las 51 filas entran en una página.
- **¿La columna Nivel sobra?** **Sí, sin matices.** 51/51 y 82/82 filas dicen "Insuficiente" — es la condición de pertenencia a la tabla, no un dato. Es ~8% del ancho.
- **Propuesta**: quitar `Nivel` (mover el criterio al subtítulo de la sección: *"Alumnos en nivel Insuficiente en dos evaluaciones consecutivas"*) y usar el ancho liberado para **subir a 7 pt**. Con la calibración 1 del punto 2 (40 filas) incluso 8 pt cabría en una página, alineando la tabla con el resto del documento.

### 4 · Jitter de matplotlib — **ignorado, correctamente**

Comparé contenido, no bitmaps. Cero solapes reales: el chequeo de bbox página a página sobre `01`, `04`, `05` y `06` no encontró ningún bloque fuera del área de texto ni cruces. El diff de los pares `00_retrocompat_*_ANTES/DESPUES` da **texto e imágenes por página idénticos** — los 2 bytes de diferencia de tamaño son metadatos del PDF.

### 5 · Indicador 15 (org demo) — **✅ cambió de motor y sale bien**

`SIMCE Demo Lenguaje` (org 6, `report_engine_type='simce'`) publica las 4 cards con `motor=custom:simce`, todas disponibles. Generados los 3 modos contra datos demo:

| Modo | HTTP | Págs | Observaciones |
|---|---|---|---|
| `ultima_prueba` | 200 · 940 KB | 16 | `JULIO 2026 (prueba 2)`, pie = `Colegio Demo` ✅ |
| `semestral` | 200 · 1225 KB | 6 | **con bloque de evolución real** (2 pruebas en el semestre) |
| `anual` | 200 · 1227 KB | 7 | comparado vs 2025 ✅ |

Valor adicional: la org demo tiene 2 pruebas en 2026, así que **cubre el camino de evolución de `semestral`/`anual` que los datos de org 1 no podían ejercitar** (Pullinque solo tiene MAYO 2026). Bien elegido como caso de prueba.

Observación menor: el bloque de título dice `Informe Ensayo SIMCE — LENGUAJE` en mayúsculas (org 1 dice `— Matemáticas`). Viene del valor crudo del dato, no del motor.

### 6 · Panguipulli 0/4 — **✅ confirmado, y es correcto**

Las 4 cards siguen `disponible=false` con el motivo de layout sin configurar; el formato oficial (`custom_simce_panguipulli`) sigue OK (941 KB). Correcto: `custom/simce_panguipulli.py` todavía no declara `MODOS`, eso es fase 4 (§6.3 del contrato). Pasará a 4/4 en cuanto lo declare, sin tocar su `pdf_layout`.

### 7 · Este gate ES el §5.3 pendiente — **✅ ejecutado**, resultado en §1. Con la salvedad de que el punto 1 del gate está roto (P0-1) y hay que re-correrlo después de arreglar el script.

---

## 6 · Batería adversarial

`POST /api/indicators/{id}/export-pdf` salvo indicado.

| # | Caso | Esperado | Real | Veredicto |
|---|---|---|---|---|
| A4 | `personalizado` 2019-01-01 → 2019-12-31 (sin datos) | 400 accionable | **200, informe de 2026** | ❌ **P0-2** |
| A5 | `personalizado` rango invertido (dic → ene) | 400 accionable | **200, informe de 2026** | ❌ **P0-2** |
| A6 | Asignatura faltante | 400 accionable | 400 · *"Este indicador tiene datos de varias asignaturas (Lenguaje, Matemáticas). Selecciona una asignatura…"* | ✅ |
| A7 | Asignatura ambigua (2 valores) | 400 accionable | 400 · *"El informe cubre UNA sola asignatura y se seleccionaron 2…"* | ✅ |
| A8 | Asignatura inexistente ("Biología") | 400 accionable | 400 · *"Sin datos cargados para este indicador."* | ⚠️ P2-12 (mensaje impreciso) |
| A9 | Modo desconocido (`trimestral`) | 400 accionable | 400 · *"Tipo de período 'trimestral' desconocido. Válidos: ultima_prueba, semestral, anual, personalizado."* | ✅ |
| A11 | Escape hatch `engine=weasyprint` sobre indicador **con** módulo | fallback v1 | 200 · 209 KB · 2 págs (layout v1) | ✅ §2.2 respetado |
| A12 | `periodo.filtros` por **id de dimensión** (`{"8": ["Matemáticas"]}`) | idéntico a por nombre | 200 · 15 págs · **texto idéntico** al de `{"Asignatura": [...]}` | ✅ §2.3 blindado |
| B3 | `semestral` en org demo | 200 con evolución | 200 · 6 págs con evolución | ✅ |
| B7 | Formato oficial **sin modo** (`POST /api/reports/custom/simce`) | idéntico a hoy | **texto idéntico** a `00_retrocompat_*_DESPUES` en ambas asignaturas | ✅ retrocompat |

**Retrocompatibilidad — triple verificación**: (a) `ANTES` vs `DESPUES` del implementador: texto e imágenes por página idénticos; (b) mi regeneración independiente vs `DESPUES`: idéntica; (c) sin filtro temporal el endpoint sigue rechazando con el mensaje de siempre. La retrocompat del formato oficial está sólida.

---

## 7 · Recomendación para la fase 4

**No replicar el patrón a DIA hasta cerrar P0-1 y P0-2.** Razones:

1. **P0-1 deja la fase 4 sin red.** El gate §5.3.1 es el único chequeo automatizado de que las cards generan; si no reconoce `custom:*`, cada módulo que se migre desaparece silenciosamente del resumen. DIA, IDEL, Panguipulli, Cálculo Veloz y Fluidez Lectora se irían sumando como OMITIDO mientras el script sigue diciendo "errores: 0". Es un arreglo de pocas líneas y hay que hacerlo **antes** de migrar nada más.
2. **P0-2 se hereda por diseño.** `personalizado` está en los `MODOS` de los 6 módulos planificados y la resolución del rango vive en `periodos.py`, compartida. Migrar primero significa replicar el mismo modo de falla ×6 y luego arreglarlo en 6 lugares.
3. Todo lo demás es sólido y **no** bloquea: el contrato se implementó tal como se especificó, la retrocompat es exacta, §2.3 está blindado con evidencia, la paridad estructural con la referencia es completa y los 1482 tests pasan.

**Orden sugerido**: (1) arreglar el script del gate y re-correrlo con las 4 cards de SIMCE generando; (2) hacer que `personalizado` sin datos en el rango levante `DatosInsuficientes` → 400 (arrastra P1-2); (3) unificar la fuente del período entre router y módulo (P1-1); (4) decisiones del dueño sobre paleta y calibración del riesgo; (5) abrir fase 4 con DIA.

P1-3 (conteos A–E) es preexistente y puede ir en paralelo, pero **debe cerrarse antes de que el motor único reemplace al informe LaTeX** en producción.

---

## Anexo · Desvíos del contrato que recomiendo aceptar (no son defectos)

- **§3.2 y §3.3 dicen "se auto-omite"**; el piloto imprime en su lugar una **nota explicativa** en gris con borde izquierdo ("El período seleccionado tiene una sola evaluación registrada, así que no hay evolución que graficar todavía…"). El texto es pedagógico y evita que el lector se pregunte por qué falta la tendencia. El espíritu de la decisión 16 (no dibujar una serie de un punto) se respeta. **Recomiendo actualizar el contrato**, no quitar la nota. Ver `02` p4 y `03` p5.
- **T3 confirmado**: el salto de página por curso ya funcionaba; la ficha estaba obsoleta, como resolvió el orquestador.
- **T5 confirmado**: Habilidad y Eje salen cruzados por Curso, igual que el esquema vigente y la referencia.

---

*Evidencia reproducible: PDFs del piloto en `C:\Users\magod\Desktop\PDF_test\piloto_simce\`; recortes a 300 dpi `crop_riesgo_6pt.png` / `crop_riesgo_9pt.png` en la misma carpeta. Los scripts temporales de QA usados (`qa_piloto_probe.py`, `qa_piloto_adversarial*.py`, `qa_piloto_analisis*.py`) y sus salidas se borraron de `data/tmp/` al cerrar la revisión.*
