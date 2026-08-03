# QA de informes — Fluidez Lectora (indicador 5, org 1)

**Fecha**: 2026-08-03 · **Revisor**: crítico de informes (agente QA)
**Motor**: v1 `pdf_layout` / `pdf_layout_historico` (WeasyPrint). Sin módulo custom, sin informe especializado.
**Métrica**: 10 — *Resultados Fluidez Lectora* · **414 filas** (la más chica del sistema).

## Puntaje: **67 / 100**

| Eje | Peso | Obtenido | Comentario |
|---|---:|---:|---|
| Correctitud de datos | 40 | **37** | 9/9 verificaciones SQL calzan exacto, incluido el vector completo de bins del histograma. Único descuento: columna fantasma "No Aplica" siempre en 0. |
| Cobertura de período | 15 | **6** | "Última prueba" muestra **1 curso de 12 (33/414 filas, 8 %)**. El propio informe histórico contradice ese recorte. |
| Calidad visual | 30 | **15** | Mes derivado OK ("ABRIL 2026"), pero subtítulo contradictorio, `_cantidad` filtrado a un eje, `role_labels` ignorado, leyenda de 12 series ilegible con 4 colisiones de color, gráficos degenerados no auto-omitidos, ~50 % de página en blanco. |
| Disponibilidad de modos | 15 | **9** | 3/4 modos; semestral 400 (defendible). Pero anual y personalizado producen contenido **idéntico**: 2 salidas distintas reales, no 3. |

---

## 1. Alcance revisado

| PDF | Págs | Páginas revisadas |
|---|---:|---|
| `fluidez_lectora_ultima_prueba.pdf` | 3 | 1, 2, 3 |
| `fluidez_lectora_anual.pdf` | 2 | 1, 2 |
| `fluidez_lectora_personalizado.pdf` | 2 | 1, 2 |
| `fluidez_lectora_semestral.pdf` | — | no existe (400 esperado) |

Total: **7 páginas** rasterizadas a 150 dpi en
`data/output/qa_indicadores/2026-08-03/png/fluidez_lectora/` y leídas una por una.

### Forma real del dato (clave para leer todo lo demás)

Las 414 filas son **una sola campaña** — `N Prueba = "Ensayo 1"` para el 100 % de las filas —
aplicada de forma escalonada en **8 fechas** distintas, un curso por fecha:

| Fecha | Curso | n | | Fecha | Curso | n |
|---|---|---:|---|---|---|---:|
| 2026-04-02 | 7° | 30 | | 2026-04-08 | II D | 37 |
| 2026-04-02 | I E | 37 | | 2026-04-09 | I C | 33 |
| 2026-04-03 | II A | 31 | | 2026-04-09 | II E | 38 |
| 2026-04-06 | 8° | 32 | | 2026-04-10 | I D | 34 |
| 2026-04-07 | I A | 37 | | 2026-04-10 | II B | 34 |
| 2026-04-08 | I B | 38 | | 2026-04-13 | II C | 33 |

**Σ = 414.** No hay serie temporal: hay un calendario de aplicación.

---

## 2. Tabla PDF vs. recalculado

Todos los recálculos contra `metric_data` (`id_metric=10`), leyendo
`value::json->>'Cantidad'` y `value::json->>'Categoria'`.

### 2.1 Última prueba (`Fecha = 2026-04-13` → curso II C), pág. 1–3

| # | Métrica | PDF | SQL | ¿Calza? |
|---|---|---|---|:-:|
| 1 | N alumnos | 33 | 33 | ✅ |
| 2 | PPM promedio | 153.7 | 153.7 | ✅ |
| 3 | PPM mínimo | 89.0 | 89 | ✅ |
| 4 | PPM máximo | 204.0 | 204 | ✅ |
| 5 | Categoría: MUY BAJA / BAJA / MEDIA / ALTA | 1 / 19 / 9 / 4 | 1 / 19 / 9 / 4 | ✅ |
| 6 | Categoría: No Aplica | 0 | 0 (nivel inexistente) | ⚠️ ver H-4 |
| 7 | Calidad lectora: Fluida / Silábica / Unidades Cortas | 31 / 1 / 1 | 31 / 1 / 1 | ✅ |
| 8 | Histograma PPM, 20 bins | ver pág. 3 | `[1,0,0,0,0,1,2,2,0,5,6,6,1,2,1,1,2,0,1,2]` | ✅ exacto |
| | Suma de niveles = N | 1+19+9+4 = 33 | 33 | ✅ |

### 2.2 Anual / personalizado (414 filas), pág. 1–2 de cada uno

| # | Métrica | PDF | SQL | ¿Calza? |
|---|---|---|---|:-:|
| 9 | Categoría global: MUY BAJA / BAJA / MEDIA / ALTA | 68 / 205 / 99 / 42 | 68 / 205 / 99 / 42 | ✅ (Σ = 414) |
| 10 | PPM promedio por curso (12 barras) | 138.5·154·125·135·135·140.5·135·145·147.5·153.5·145·155 | 138.4·153.8·125.1·134.6·134.6·140.6·135.2·144.9·147.6·153.7·145.2·155.1 | ✅ |

**Promedio global recalculado**: 142.25 PPM sobre 414 registros.

> **Veredicto de datos: sin un solo número mal.** Ni `nan`, ni doble conteo, ni totales
> descuadrados. Lo que falla no es la aritmética — es el recorte al que se le aplica.

---

## 3. Hallazgos

### H-1 · CRÍTICO — "Última prueba" muestra el 8 % de la prueba
`fluidez_lectora_ultima_prueba.pdf`, **págs. 1, 2 y 3** (las tres).

El informe se titula *"Informe Fluidez Lectora — Resultados de la medición seleccionada"* y
subtitula *"Fecha: 2026-04-13 · N Prueba: Ensayo 1"*. Muestra **un curso, II C, 33 alumnos**.
La medición realmente seleccionada — el Ensayo 1 — son **12 cursos y 414 alumnos**.

Causa raíz: `column_roles.evaluacion_num` declara **dos** columnas —

```json
"evaluacion_num": [{"metric_id":10,"column":"N Prueba"},
                   {"metric_id":10,"column":"Fecha"}]
```

y los dos caminos las resuelven distinto:

- el **selector de período** (`ultima_prueba`) ancla en `Fecha` → `max(Fecha) = 2026-04-13` → 1 curso;
- el **eje de período de los gráficos históricos** (`periodField: "_evaluacion_num"`) ancla en
  `N Prueba` → `"Ensayo 1"` → los 12 cursos.

Es decir: **el propio informe histórico desmiente el recorte del informe de última prueba.**
Con este dataset `Fecha` no identifica una evaluación, identifica un día de aplicación.
El impacto es de interpretación grave: un director que abra este PDF concluye que su
establecimiento promedia 153.7 PPM cuando el promedio real del Ensayo 1 es 142.25, y que la
distribución es 1/19/9/4 cuando es 68/205/99/42. II C es, además, el **mejor curso salvo II E**
— el recorte no es solo parcial, es sesgado al alza.

**Fix**: cuando `evaluacion_num` tiene varias columnas, el resolver debe preferir la ordinal
(`N Prueba`) para definir *qué* evaluación es la última, y usar `Fecha` solo para derivar
año/mes. La fecha nunca debe particionar la cohorte.

### H-2 · ALTO — El histórico es dos páginas de "evolución" con un solo punto
`fluidez_lectora_anual.pdf` **págs. 1 y 2**; `fluidez_lectora_personalizado.pdf` **págs. 1 y 2**.

`pdf_layout_historico` define exactamente dos secciones, ambas de evolución:

1. *"Evolución PPM Promedio por Curso y Evaluación"* (`GroupedBarByPeriod`)
2. *"Evolución de Categoría por Evaluación"* (`StackedCountByGroup` sobre `_evaluacion_num`)

Con `N Prueba` de cardinalidad 1, **ambas degeneran a una sola categoría en el eje X** y
**no se auto-omiten**. El resultado es un informe de 2 páginas cuya palabra rectora es
"Evolución" y que no muestra ninguna. La gráfica 1 queda como un barras-por-curso disfrazado
(12 barras sobre una única etiqueta "Ensayo 1"); la gráfica 2 queda como una única barra apilada.

Se suma la **decisión 14 de las fichas**, que aquí se confirma: el `dashboard_layout` de FL tiene
4 tabs — *Vista General*, *Por Curso*, *Calidad Lectora*, *Refuerzo / Riesgo* — y **ninguno de
tendencia**. Las dos secciones de evolución del PDF **no tienen fuente en el dashboard**: están
escritas a mano en `pdf_layout_historico` y no las respalda ninguna vista revisada por el usuario.
Es la única parte del informe FL sin contraparte en pantalla, y es justamente la que se rompe.

**Fix**: guardia de degeneración — si el eje de período tiene < 2 valores, omitir la sección
(o degradarla a su equivalente no temporal con el título correcto). Y poblar el histórico desde
las 4 tabs que sí existen, en vez de inventar dos que no.

### H-3 · ALTO — Encabezado y subtítulo se contradicen; `role_labels` y nombres internos
`fluidez_lectora_personalizado.pdf` **pág. 1** (y anual pág. 1, última prueba pág. 3).

Cuatro defectos de rotulado, en orden de gravedad:

1. **Dos fuentes de verdad para el período.** El encabezado corrido dice **"ABRIL 2026"**
   (correcto — `ResultadoPeriodo.descripcion`), pero el subtítulo del bloque de título dice
   **"Fecha: 2026-04-02, 2026-04-03 y 6 más"** (`branding.formatear_filtros`, sobre los valores
   crudos del filtro). Es **exactamente el bug P1-1 que SIMCE ya arregló** — el docstring de
   `_descripcion_periodo` en `custom/simce.py:891` lo documenta textualmente. El camino
   `pdf_layout` v1 nunca recibió ese fix.

2. **`role_labels` ignorado.** El indicador declara `{"logro_1": "PPM", "nivel_de_logro": "Categoría"}`,
   pero la tabla de la pág. 1 rotula **"Cantidad prom." / "Cantidad mín." / "Cantidad máx."** y el
   eje Y de los gráficos dice **"Cantidad"** — el nombre crudo de la columna. El encabezado de la
   sección sí dice "PPM". El informe se contradice consigo mismo dentro de la misma página.

3. **Nombre interno filtrado a la vista.** El eje X del histograma (última prueba, **pág. 3**)
   dice literalmente **`_cantidad`** — con guion bajo. Es una columna interna del motor impresa
   en un PDF que va a un director de establecimiento.

4. **Buena noticia — el P2 conocido está resuelto.** El período *no* aparece como "04 2026":
   el encabezado del personalizado dice **"ABRIL 2026"** y el del anual **"2026"**. El resolver de
   fechas (`periodos.NUMERO_A_MES`) deriva bien el mes desde la dimensión `Fecha` sin dimensión Año.
   El P2 ya no está en el resolver: **está en el subtítulo del bloque de título**, que no lo usa.

### H-4 · MEDIO — Nivel "No Aplica" fantasma y colisión de verdes
`fluidez_lectora_ultima_prueba.pdf` **págs. 1 y 2**; anual/personalizado **pág. 2**.

`achievement_levels` declara 5 niveles, pero el campo `Categoria` solo produce 4:

| Nivel declarado | Color | Ocurrencias reales (414 filas) |
|---|---|---:|
| No Aplica | `#2dd22d` | **0** |
| MUY BAJA | `#d22d2d` | 68 |
| BAJA | `#d2802d` | 205 |
| MEDIA | `#d2d22d` | 99 |
| ALTA | `#80d22d` | 42 |

Consecuencias: (a) la tabla resumen gasta una columna que **siempre valdrá 0**; (b) las leyendas
de los dos gráficos apilados listan "No Aplica" con un verde `#2dd22d` **más saturado que el
verde `#80d22d` de ALTA**, contiguos en la leyenda — el nivel inexistente se ve *mejor* que el
mejor nivel real. Los 4 niveles que sí existen respetan sus colores oficiales correctamente.

Nota de calidad del dato origen (no es culpa del informe): 3 filas tienen
`Calidad lectora = "No Aplica"` pero traen PPM 50/149/150 y Categoría MUY BAJA/BAJA —
un alumno no puede "no aplicar" y a la vez leer 150 palabras por minuto.

### H-5 · MEDIO — Leyenda de 12 series ilegible, con 4 pares de color idénticos
`fluidez_lectora_anual.pdf` **pág. 1**; `fluidez_lectora_personalizado.pdf` **pág. 1**.

La leyenda de "Evolución PPM Promedio por Curso y Evaluación" tiene 12 entradas a ~4 pt —
tuve que ampliarla **6×** para leerla. Peor: la paleta tiene **8 colores y cicla**, así que:

| Colisión | Cursos |
|---|---|
| verde azulado | 7° y **II B** |
| naranjo | 8° y **II C** |
| azul | I A y **II D** |
| rosado | I B y **II E** |

Cuatro pares de cursos son **cromáticamente indistinguibles** en un gráfico cuya única función
es comparar cursos. Como además todas las barras comparten una sola categoría X, el color es la
*única* clave de identificación disponible: el gráfico no se puede leer.

### H-6 · BAJO — Densidad de página
Las 7 páginas usan aproximadamente la **mitad superior** del papel. `anual` pág. 2 y
`última prueba` pág. 3 llevan **un solo gráfico** cada una con ~55 % de la hoja en blanco.
Tres informes que caben cómodos en 1–2 páginas ocupan 3+2+2.

### Lo que sí está bien
- Pie de página = **"Fundación PHP"** (nombre de la org) pese a `branding.left_footer: ""` —
  el fallback funciona. Numeración de página correcta en las 7.
- Tablas **dentro del margen**, sin desborde, sin `nan`, sin celdas vacías.
- `SummaryTable` trae `comparePrevious: true` y, al no existir evaluación previa, **omite la
  columna de comparación en silencio** en vez de imprimir `nan` o `—`. Comportamiento correcto.
- Los 4 niveles reales usan sus colores oficiales de `achievement_levels`.
- El histograma reproduce bin por bin el `np.histogram(v, bins=20)` de referencia.

---

## 4. Veredicto de hardcodeabilidad

**Sí, FL justifica `reports/custom/fluidez_lectora.py` — pero es el 5.º de 5 en prioridad.**
No porque sea fácil, sino porque su problema #1 (H-1) **no se arregla con un módulo custom**:
vive en el resolver de períodos y afecta a cualquier motor. Portar FL a custom sin corregir el
resolver produce un informe bonito del 8 % de los datos.

### Orden de ataque recomendado
1. **Primero el resolver** (fuera del módulo): preferencia ordinal en `evaluacion_num` multi-columna.
2. **Después el módulo**, que hereda el recorte ya correcto.

### Secciones que debería tener el módulo
El `dashboard_layout` de FL ya es el guion — 4 tabs revisados por el usuario. El módulo debería
transcribirlos, no inventar:

| Sección del módulo | Origen | Reutiliza de `_secciones.py` |
|---|---|---|
| Bloque de título + encabezado corrido | — | `bloque_titulo()` con `periodo_desc` único (mata H-3.1) |
| Resumen PPM por curso | tab *Vista General* → "Resumen por Curso" | `seccion_resumen_comparado()` |
| PPM promedio y distribución de Categoría por curso | tab *Vista General* | rescatar de `pdf_layout` |
| Detalle por curso | tab *Por Curso* | `secciones_por_curso()` — encaja casi 1:1 |
| Calidad lectora (composición, curso × calidad, consistencia Categoría × Calidad) | tab *Calidad Lectora* | sección propia; es lo distintivo de FL |
| Refuerzo / Riesgo (Seguimiento Intensivo, lectores iniciales) | tab *Refuerzo / Riesgo* | `secciones_riesgo_persistente()`, `tabla_riesgo_persistente()` — el mapeo más limpio |
| Evolución | **ninguno** (decisión 14) | `seccion_evolucion()` + `puntos_temporales()`, **con guardia `min_points ≥ 2`** |

### Qué se rescata del `pdf_layout` actual
- `SummaryTable` PPM por curso, `BarByGroup`, los dos `StackedCountByGroup` y el `Histogram`:
  **los 5 componentes son correctos y sus números están verificados**. Se portan tal cual.
- Se descarta: el `pdf_layout_historico` completo (2 secciones sin fuente y degeneradas, H-2)
  y la columna "No Aplica" de la tabla resumen (H-4).
- Se agrega lo que hoy falta y el dashboard ya tiene: Calidad Lectora y Refuerzo/Riesgo — que
  son, con `derived_columns` (`Avance`, `Mejora_vs_Inicio`), el valor pedagógico real de FL.

### ¿Dónde se arregla el formato del mes?
**En el módulo, no en el resolver.** El resolver ya está bien: produce "ABRIL 2026" y el
encabezado corrido lo imprime correcto. El defecto es que el **bloque de título del motor v1**
construye su propio subtítulo con `branding.formatear_filtros()` sobre los filtros crudos
("Fecha: 2026-04-02, 2026-04-03 y 6 más"). Un módulo custom usa `_secciones.bloque_titulo()` con
el `periodo_desc` que ya viene de `ResultadoPeriodo` — una sola fuente, exactamente la solución
que SIMCE documentó en su fix P1-1. Si además se quiere arreglar para todos los indicadores que
sigan en v1, el parche es de una línea en el bloque de título del motor v1.

### Esfuerzo relativo
Referencias leídas: `custom/simce.py` (911 líneas, módulo completo), `custom/_secciones.py`
(757, biblioteca compartida), `custom/dia.py` (45) y `custom/simce_panguipulli.py` (43) — ambos
meros *wrappers* de un generador preexistente.

FL **no puede ser wrapper** (no hay generador que envolver), pero es bastante más simple que SIMCE:
sin dimensión asignatura, sin dataframe de preguntas, una sola métrica, 4 niveles, 414 filas.
La mitad de las secciones sale directo de `_secciones.py`.

> **Estimación: ~250–350 líneas, ≈ 40 % del esfuerzo de `simce.py`.**
> Más el fix del resolver (H-1), que es transversal y debe ir primero.

---

## 5. Resumen ejecutivo

Fluidez Lectora es, paradójicamente, el indicador con **la aritmética más limpia y la narrativa
más rota** del set. Nueve de nueve verificaciones SQL calzan al decimal; el histograma se
reproduce bin por bin. Pero el informe de "última prueba" retrata el 8 % de la prueba, el
informe "histórico" dedica dos páginas a una evolución que no existe, y el encabezado se
contradice con su propio subtítulo dentro de la misma página. El bug P2 conocido
("06 2025" en vez de "JUNIO 2025") **está resuelto en el resolver** — reaparece solo en el
subtítulo, que no lo consulta.
