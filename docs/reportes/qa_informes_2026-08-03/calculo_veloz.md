# QA de informes — Cálculo Veloz (indicador 4, org 1)

**Fecha**: 2026-08-03 · **Revisor**: crítico de informes (agente) · **Métrica**: 9 «Resultados Cálculo Veloz» (5151 filas)
**Motor**: genérico `pdf_layout` / `pdf_layout_historico` (WeasyPrint). Sin `report_engine_type`, sin módulo custom.
**PDFs revisados**: `calculo_veloz_ultima_prueba.pdf` (2 págs), `calculo_veloz_personalizado.pdf` (2 págs)
**PNG a 150 dpi**: `data/output/qa_indicadores/2026-08-03/png/calculo_veloz/`

---

## Puntaje: **69 / 100**

| Eje | Peso | Puntaje | Comentario |
|---|---:|---:|---|
| Correctitud de datos | 40 | **34** | Aritmética impecable: 143/143 celdas de la tabla y 30/30 segmentos apilados reproducidos por SQL sin una sola discrepancia. Se descuenta por lo que el informe **no dice**: mezcla dos escalas de puntaje incompatibles sin advertencia y arrastra 56 filas con `Fecha` nula y 18 filas fechadas en febrero rotuladas MAYO. |
| Cobertura de período | 15 | **13** | «Última prueba» resuelve correcto a OCTUBRE 2025 prueba 2 (2025-10-23, la fecha máxima real). «Personalizado» cubre los 6 meses con datos, sin huecos ni sobras. Se descuenta porque ningún informe expone `N Prueba`: con 2 pruebas/mes, el histórico promedia p1+p2 y borra justo la granularidad que la fundación pidió. |
| Calidad visual | 30 | **16** | El informe por evaluación está limpio (colores correctos, sin `nan`, tablas en margen, pie con nombre de organización). El histórico está roto en su premisa: los 3 gráficos ordenan el eje de meses **alfabéticamente**, y 2 de 3 llevan una leyenda de 18 series ilegible. |
| Disponibilidad de modos | 15 | **6** | 2 de 4 modos devuelven 400. La ingeniería es correcta (degradación limpia, mensaje al usuario, card deshabilitada antes del clic), pero el resultado de producto es inaceptable: un director en agosto 2026, con 2025 completo cargado, no puede obtener ni el anual ni el semestral. |

---

## Verificación de datos — PDF vs. recalculado por SQL

Todas las consultas contra `metric_data` (`id_metric = 9`, `org_id = 1`), conteo por estudiante único
(`DISTINCT Establecimiento || Nombre`). Dimensiones: 3=Establecimiento, 4=Año, 5=Curso, 7=Nombre,
9=Mes, 10=N Prueba, 21=Fecha.

### 1. Cuadro Resumen por Curso — pág. 1, `calculo_veloz_ultima_prueba.pdf`

Filtro: `Mes = OCTUBRE`, `N Prueba = 2`, `Año = 2025`.

| Curso | Alumnos PDF / SQL | Punt. prom PDF / SQL | Punt. mín | Punt. máx | Nota prom | INICIAL | BÁSICO | INTERMEDIO | AVANZ. | EXP. |
|---|---|---|---|---|---|---|---|---|---|---|
| III°C  | 22 / **22** | 46.2 / **46.2** | 23 / **23** | 60 / **60** | 3.3 / **3.3** | 9 / **9** | 9 / **9** | 4 / **4** | 0 / **0** | 0 / **0** |
| III°P  | 21 / **21** | 51.6 / **51.6** | 22 / **22** | 60 / **60** | 3.6 / **3.6** | 3 / **3** | 17 / **17** | 1 / **1** | 0 / **0** | 0 / **0** |
| IV°A   | 30 / **30** | 50.3 / **50.3** | 23 / **23** | 60 / **60** | 3.5 / **3.5** | 6 / **6** | 21 / **21** | 3 / **3** | 0 / **0** | 0 / **0** |
| IV°C   | 23 / **23** | 56.7 / **56.7** | 34 / **34** | 60 / **60** | 3.8 / **3.8** | 1 / **1** | 12 / **12** | 10 / **10** | 0 / **0** | 0 / **0** |
| IV°MA  | 28 / **28** | 51.8 / **51.8** | 27 / **27** | 60 / **60** | 3.6 / **3.6** | 6 / **6** | 13 / **13** | 9 / **9** | 0 / **0** | 0 / **0** |
| IV°MB  | 24 / **24** | 42.6 / **42.6** | 11 / **11** | 60 / **60** | 3.1 / **3.1** | 9 / **9** | 14 / **14** | 1 / **1** | 0 / **0** | 0 / **0** |
| IV°P   | 16 / **16** | 56.5 / **56.5** | 43 / **43** | 60 / **60** | 3.8 / **3.8** | 0 / **0** | 9 / **9** | 7 / **7** | 0 / **0** | 0 / **0** |
| I°A    | 31 / **31** | 52.0 / **52.0** | 14 / **14** | 60 / **60** | 3.6 / **3.6** | 5 / **5** | 15 / **15** | 11 / **11** | 0 / **0** | 0 / **0** |
| I°B    | 23 / **23** | 46.6 / **46.6** | 5 / **5** | 60 / **60** | 3.3 / **3.3** | 8 / **8** | 13 / **13** | 2 / **2** | 0 / **0** | 0 / **0** |
| I°C    | 27 / **27** | 54.2 / **54.2** | 37 / **37** | 60 / **60** | 3.7 / **3.7** | 1 / **1** | 19 / **19** | 7 / **7** | 0 / **0** | 0 / **0** |
| I°D    | 24 / **24** | 43.0 / **43.0** | 7 / **7** | 60 / **60** | 3.2 / **3.2** | 8 / **8** | 11 / **11** | 5 / **5** | 0 / **0** | 0 / **0** |
| **Total** | **269 / 269** | — | — | — | — | **56** | **153** | **60** | **0** | **0** |

**143 de 143 celdas coinciden.** El N total (269) y el número de cursos (11) también: OCTUBRE prueba 2
efectivamente solo cubre 11 cursos, contra 17 en el resto del año. No es una pérdida del informe.

### 2. Gráfico «Puntaje y Nota Promedio por Curso» — pág. 1

Las 22 etiquetas (11 puntajes + 11 notas) reproducen exactamente la columna correspondiente de la tabla.

### 3. Gráfico «Distribución de Nivel por Curso» — pág. 2

Los 30 segmentos apilados con su etiqueta numérica coinciden 1:1 con las columnas INICIAL/BÁSICO/INTERMEDIO
de la tabla anterior. Suma por curso = columna «Alumnos». ✅

### 4. Histograma de Puntajes — pág. 2

| Comprobación | PDF | SQL |
|---|---|---|
| Suma de las 15 barras | 269 | **269** |
| Barra superior (bin ≈ [56.3, 60]) | 126 | **126** (`Puntaje >= 56.34`) |
| Alumnos con puntaje exactamente 60 | — | **60** (22 % del total) |

✅ Exacto. El histograma revela un **efecto techo severo**: 47 % de los alumnos cae en el último bin.

### 5. «Distribución de Nivel a través del Año» — pág. 2, `calculo_veloz_personalizado.pdf`

| Mes | N PDF / SQL | INICIAL | BÁSICO | INTERMEDIO | AVANZADO | EXPERTO |
|---|---|---|---|---|---|---|
| ABRIL | 877 / **877** | 118 / **118** | 124 / **124** | 104 / **104** | 122 / **122** | 409 / **409** |
| AGOSTO | 930 / **930** | 224 / **224** | 511 / **511** | 195 / **195** | 0 / **0** | 0 / **0** |
| JUNIO-JULIO | 849 / **849** | 259 / **259** | 429 / **429** | 161 / **161** | 0 / **0** | 0 / **0** |
| MAYO | 883 / **883** | 107 / **107** | 121 / **121** | 125 / **125** | 102 / **102** | 428 / **428** |
| OCTUBRE | 676 / **676** | 147 / **147** | 383 / **383** | 146 / **146** | 0 / **0** | 0 / **0** |
| SEPTIEMBRE | 936 / **936** | 217 / **217** | 514 / **514** | 205 / **205** | 0 / **0** | 0 / **0** |

✅ **30 de 30 segmentos exactos.** Los 6 meses suman 5151 = total de la métrica: no se pierde ni se duplica una fila.

### 6. «Evolución del Puntaje / Nota Promedio por Curso y Mes» — pág. 1, personalizado

| Serie · mes | PDF (lectura de barra) | SQL |
|---|---|---|
| III°A · ABRIL — Puntaje | ≈ 85 | **85.1** |
| III°A · MAYO — Puntaje | ≈ 71 | **71.2** |
| III°A · ABRIL — Nota | ≈ 5.9 | **5.92** |
| I°C · ABRIL — Puntaje | ≈ 77 | **76.6** |
| I°C · OCTUBRE — Puntaje | ≈ 52 | **52.5** |

✅ Coincide dentro del error de lectura del gráfico.

**Veredicto aritmético: sin un solo error numérico en 4 páginas.**

---

## Hallazgos

### 🔴 H1 — Los niveles de logro mezclan dos escalas incompatibles sin advertencia
`calculo_veloz_personalizado.pdf` pág. 2 · también contamina la tabla y el gráfico de nivel de la pág. 1–2 de «última prueba»

Los datos de 2025 contienen **dos pruebas distintas bajo la misma métrica**:

| Meses | Puntaje máx. | Nota máx. | Filas |
|---|---|---|---|
| ABRIL, MAYO | 100 | 7.0 | 1760 |
| JUNIO-JULIO … OCTUBRE | **60** | **4.0** | 3391 |

Los umbrales de `Nivel` son absolutos y los mismos para ambas escalas (verificado por SQL):
INICIAL 0–39 · BÁSICO 40–59 · INTERMEDIO 60–72 · AVANZADO 73–85 · EXPERTO 86–100.

Consecuencia mecánica en la escala de 60 puntos: **AVANZADO y EXPERTO son estructuralmente
inalcanzables**, e INTERMEDIO solo se alcanza con puntaje **exactamente 60**, es decir con prueba
perfecta (707 alumnos en el año).

El gráfico «Distribución de Nivel a través del Año» presenta esto como si el establecimiento hubiera
colapsado: 409 EXPERTO en ABRIL → 0 desde junio en adelante. **Un director que lea esa página
concluirá que hubo una caída catastrófica del cálculo veloz.** No la hubo: cambió el instrumento.
Lo mismo vale para la columna «Nota máx. 4.0» en las 11 filas de la tabla de octubre — una nota
chilena tope de 4.0 para una prueba perfecta es una señal de alarma que el informe imprime sin comentar.

Es un problema de origen del dato, pero el informe es la última línea de defensa y no dice nada.
Mínimo: nota al pie cuando el rango de `Puntaje` del período no es homogéneo; ideal: normalizar a
porcentaje de logro antes de graficar niveles a través del año.

### 🔴 H2 — El eje de meses se ordena alfabéticamente en los 3 gráficos del informe histórico
`calculo_veloz_personalizado.pdf` págs. 1 y 2

Eje X impreso: **ABRIL · AGOSTO · JUNIO-JULIO · MAYO · OCTUBRE · SEPTIEMBRE**.
Orden real: ABRIL · MAYO · JUNIO-JULIO · AGOSTO · SEPTIEMBRE · OCTUBRE.

Un gráfico titulado «**Evolución** del Puntaje Promedio por Curso y Mes» con el eje temporal
desordenado no es un gráfico de evolución. Es el defecto más caro del informe porque ataca
directamente la decisión de producto para CV («foco en última evaluación + **tendencia mensual**»).

**Causa raíz localizada.** En `backend/rgenerator/core/report_steps.py`:

```python
# GroupedBarByPeriod, línea ~879
periods = sorted({str(r.get(pf, '')) for r in records_vf if r.get(pf) is not None},
                 key=_natural_sort_key)
# StackedCountByGroup, línea ~802
groups = sorted({str(r.get(gf, '')) for r in records_filtered if r.get(gf) is not None},
                key=_natural_sort_key)
```

`_natural_sort_key` (línea 678) es un orden alfanumérico natural — correcto para cursos, sin sentido
para meses. Ninguno de los dos componentes consulta `temporal_config`, **aunque el indicador 4 ya lo
tiene bien configurado**:

```json
{"label": "Mes", "sort_mode": "custom",
 "order": ["MARZO","ABRIL","MAYO","JUNIO-JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"]}
```

El orden declarado por el usuario se guarda, se muestra en la UI y **el motor PDF lo ignora**.
Las piezas para arreglarlo ya existen en el repo y están a pocas líneas:

- `report_steps._orden_declarado(columna, temporal_config)` (línea 389) — lee justamente ese `order`;
  hoy solo lo usa `combinaciones_temporales`.
- `reports/helpers.clave_orden_temporal(valor)` (línea 350) — orden cronológico que ya entiende meses
  en español, hitos DIA y versiones IDEL. Lo usa `custom/_secciones._orden_evaluaciones`.

Fix: en ambos componentes, reemplazar `key=_natural_sort_key` por el orden declarado cuando la
columna sea temporal, con `clave_orden_temporal` como fallback. Alcance: los 2 sitios citados.
Beneficia a todos los indicadores, no solo a CV.

Nota: el encabezado sí sale bien (`ABRIL 2025 – OCTUBRE 2025`) porque lo construye otro camino de
código — el contraste confirma que es un bug del renderer de gráficos, no de los datos.

### 🔴 H3 — `comparePrevious: true` está declarado pero nunca puede dispararse
`calculo_veloz_ultima_prueba.pdf` pág. 1

`pdf_layout` declara para el `SummaryTable`:

```json
{"component": "SummaryTable", "comparePrevious": true, "periodField": "_evaluacion_num", ...}
```

La tabla impresa **no tiene ninguna columna de comparación ni delta**. Es una funcionalidad muerta por
construcción: en modo «última prueba» el resolver aplica los filtros `Año=2025 · Mes=OCTUBRE ·
N Prueba=2` como filtros de usuario, y en `report_steps.py` (línea ~1624) la rama
`user_filtered_period` deja los records recortados a una sola combinación temporal, con lo que
`combinaciones_temporales` nunca devuelve las ≥2 combinaciones que `comparePrevious` exige.

Para Cálculo Veloz esto es la oportunidad perdida más grande del informe: con **2 pruebas al mes**,
comparar OCTUBRE p2 contra OCTUBRE p1 es exactamente la lectura que la fundación quiere y el layout
ya la pide. El comparativo existiría con solo cargar también la penúltima combinación temporal
cuando alguna sección lo declara.

### 🟠 H4 — Leyenda de 18 series ilegible en los dos gráficos de evolución
`calculo_veloz_personalizado.pdf` pág. 1

`GroupedBarByPeriod` dibuja una serie por curso: 18 cursos → 18 barras por mes de ~2 px y una leyenda
a ~6 pt fuera del área de trazado (`ax.legend(fontsize=6, ...)` cuando `len(groups) > 8`). La paleta
`pal_cat` cicla, así que hay colores repetidos entre series distintas. Es imposible seguir un curso.
Para «tendencia mensual» lo correcto es una línea por curso (o small multiples por nivel), no barras
agrupadas.

### 🟠 H5 — Nombre interno de campo filtrado al eje del histograma
`calculo_veloz_ultima_prueba.pdf` pág. 2

El eje X del histograma dice **`_puntaje`** — el nombre interno del campo, con guion bajo, sin la
etiqueta del rol («Puntaje»). El componente `Histogram` no aplica el `role_labels` del indicador
(`{"logro_2": "Puntaje"}`), a diferencia de `GroupedBarByPeriod` que sí hace
`vf.lstrip('_').title()`.

### 🟡 H6 — Orden de cursos no pedagógico
`calculo_veloz_ultima_prueba.pdf` págs. 1 y 2

Los cursos se imprimen **III°C, III°P, IV°A, IV°C, IV°MA, IV°MB, IV°P, I°A, I°B, I°C, I°D**: los
primeros medios quedan al final. `_natural_sort_key` no reconoce numerales romanos, y el símbolo `°`
(U+00B0) ordena después de las letras. Debería ser I° → II° → III° → IV°.

### 🟡 H7 — Filas con `Fecha` inconsistente que el informe absorbe en silencio
Ambos PDFs

Sobre la dimensión `Fecha` (tipo `date`), que es la que la decisión de producto eligió para CV:

- **56 filas** de `MAYO` prueba 2 tienen `Fecha` **vacía**.
- **18 filas** con `Fecha = 2025-02-14` están rotuladas `Mes = MAYO`.

Ninguna se pierde de los conteos (por eso los totales cuadran), pero cualquier informe que se ancle a
`Fecha` en vez de a `Mes` las va a tratar distinto. Es deuda de dato que conviene limpiar antes de que
un informe basado en `Fecha` la haga visible.

### 🔵 H8 (producto, no del PDF) — El anclaje al calendario deja el indicador sin anual ni semestral

| Modo | HTTP | Mensaje |
|---|---|---|
| `ultima_prueba` | 200 | ✅ |
| `semestral` | **400** | «Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador.» |
| `anual` | **400** | «Sin datos del año en curso (2026) para este indicador.» |
| `personalizado` | 200 | ✅ |

`reports/periodos.py`:

```python
def _resolver_anual(df, cols, hoy):
    anio = hoy.year          # línea 993 → 2026
def _resolver_semestral(df, cols, hoy):
    anio = hoy.year          # línea 1049 → 2026
    semestre = semestre_de_mes(hoy.month)   # agosto → 2º semestre
```

El resolver ancla al **año y semestre del reloj**, no al último período con datos. Cálculo Veloz tiene
5151 filas de 2025 (abril a octubre, 15 fechas de aplicación) y **cero filas de 2026**. Resultado: un
director que hoy pida «informe anual» recibe un error, teniendo el año 2025 completo cargado.

Es el caso extremo, pero **no es un caso aislado**: en la matriz de esta misma tanda, el semestral
falla con 400 en **5 de los 6 indicadores** de la org, incluidos SIMCE y DIA que sí tienen datos 2026
— porque hoy es agosto (2º semestre) y sus datos son del 1er semestre.

La ingeniería está bien resuelta: el error es explícito, en lenguaje de usuario, y la card viene
deshabilitada desde `report-options` (el director no encuentra un botón muerto). El problema es de
**diseño de producto**, no de implementación.

Propuesta: que `anual` y `semestral` se anclen al **último período con datos** y no al reloj,
rotulando el encabezado con el período efectivo («Informe anual 2025 — último año con datos»).
Alternativa mínima: fallback al año anterior cuando el año en curso viene vacío. La primera opción es
mejor porque también arregla el semestral de SIMCE y DIA.

---

## Rúbrica visual — checklist

| Criterio | Resultado |
|---|---|
| Evolución degenerada a serie única con un solo mes (P2 del backlog) | ✅ **No ocurre**. El layout «última prueba» no incluye ningún gráfico de evolución; el histórico tiene 6 meses reales. |
| Mes como texto legible (no `10 2025`) | ✅ `ABRIL`, `JUNIO-JULIO`, `OCTUBRE` |
| Sin `nan` / `None` / celdas vacías | ✅ Ninguno en 4 páginas |
| Formato numérico limpio | ✅ Puntaje `#.0`, Nota `#.1`, conforme a `role_formats` |
| Colores = `achievement_levels` | ✅ Exacto: `#dc2626` `#ea580c` `#eab308` `#65a30d` `#16a34a` |
| Tablas dentro del margen | ✅ 13 columnas caben sin desborde ni corte |
| Pie de página = nombre de la organización | ✅ «Fundación PHP» + numeración |
| Período correcto en encabezado | ✅ `OCTUBRE 2025 (prueba 2)` y `ABRIL 2025 – OCTUBRE 2025` |
| Orden temporal del eje X | ❌ **Alfabético** (H2) |
| Etiquetas de eje sin nombres internos | ❌ `_puntaje` (H5) |
| Leyendas legibles | ❌ 18 series a 6 pt (H4); la leyenda de `BarByGroup` queda diminuta en el margen derecho |
| Series de escalas distintas en el mismo eje | ⚠️ Puntaje (0–60) y Nota (0–4) comparten eje Y: las barras de Nota son visualmente irrelevantes. Merecen eje secundario o gráfico aparte. |
| Sin portada | ✅ Conforme a la decisión de producto: `page_title` minimalista, sin cover |

---

## Veredicto de hardcodeabilidad — ¿conviene `reports/custom/calculo_veloz.py`?

**Sí, y es de los casos más baratos del catálogo.** Recomendación: **hacerlo, pero después de H2.**

### Qué se rescata del `pdf_layout` actual

Bastante — el layout no está mal pensado, está mal renderizado:

- ✅ **El «Cuadro Resumen por Curso» se rescata entero.** 143/143 celdas correctas, 13 columnas en
  margen, formato limpio. Es la mejor pieza de los dos informes y debe ser la sección 1 del módulo.
- ✅ **«Distribución de Nivel por Curso»** (apilado con conteos sobre las barras y colores de
  `achievement_levels`) se rescata tal cual.
- ✅ **El histograma** se rescata como diagnóstico del efecto techo; solo hay que etiquetar el eje y
  marcar la línea del puntaje máximo del instrumento.
- ⚠️ **«Puntaje y Nota Promedio por Curso»** se rescata la idea, no la ejecución: separar en dos
  gráficos o usar eje secundario.
- ❌ **Los dos `GroupedBarByPeriod` del histórico no se rescatan.** 18 series de barras agrupadas es
  el componente equivocado para tendencia; van reemplazados por líneas.

### Secciones que debería tener el módulo

Sin portada, foco en última evaluación + tendencia mensual:

1. **Encabezado minimalista** — `_secciones.bloque_titulo(...)`. Ya existe, reutilización directa.
2. **Cuadro resumen de la última prueba, comparado contra la prueba anterior del mismo mes** —
   `_secciones.tabla_resumen_comparado(df_actual, df_previo, columna="Puntaje", agrupar_por="Curso")`.
   Resuelve H3 sin tocar el motor genérico: el módulo custom carga los dos períodos por su cuenta.
   Es la sección de mayor valor del informe: «p2 vs p1 de octubre» es el dato que la fundación pide.
3. **Distribución de nivel del último mes** — apilado por curso, colores de `achievement_levels`.
4. **Tendencia mensual del puntaje promedio** — línea por curso, eje ordenado con
   `helpers.clave_orden_temporal`, envuelto en `_secciones.seccion_evolucion(...)` para que se
   auto-omita si hay un solo punto temporal (decisión 16, ya implementada). Con 2 pruebas/mes conviene
   que el eje sea **mes × N Prueba** (12 puntos), no mes (6 puntos): es la granularidad real del
   instrumento y hoy se está promediando a la basura.
5. **Nota de homogeneidad de escala** — bloque de texto automático que se imprime cuando el rango de
   `Puntaje` del período no es homogéneo. Es la mitigación directa de H1 y no existe en ninguna parte
   del sistema todavía.
6. *(opcional)* **Alumnos en riesgo persistente** — `_secciones.riesgo_persistente` /
   `secciones_riesgo_persistente` ya está escrito y probado para IDEL. Aplicado a CV daría «alumnos
   que llevan N pruebas seguidas en INICIAL», que es accionable para un jefe de UTP. Casi gratis.

### Esfuerzo relativo

| Referencia | Líneas | Naturaleza |
|---|---:|---|
| `custom/dia.py` | 45 | Wrapper puro sobre `dispatch_v2` |
| `custom/pdl_idel.py` | 56 | Wrapper puro sobre `report_pdl_idel_tools` |
| `custom/_ejemplo.py` | 92 | Plantilla con el contrato |
| `custom/_secciones.py` | 757 | Toolkit **compartido y ya escrito** |
| `custom/simce.py` | 911 | Módulo completo, pero con mucho peso propio de SIMCE (asignaturas, preguntas, ejes, secciones dinámicas por curso) |
| **`custom/calculo_veloz.py` estimado** | **≈ 200–280** | — |

**Aproximadamente un cuarto de `simce.py`.** Las razones del bajo costo:

- CV tiene **una sola asignatura** (`REQUIERE_ASIGNATURA = False`) y **una sola métrica** — se evita
  todo el aparato de `reports/asignatura.py` y de conciliación entre métricas que domina `simce.py`.
- No hay análisis por pregunta ni por eje: `simce.py` dedica `_secciones_comunes`,
  `_secciones_detalle_ultima_prueba` y `_secciones_dinamicas_por_curso` (≈ 250 líneas) a eso.
- `_secciones.py` ya aporta cuatro de las seis secciones propuestas.
- El contrato de `generar()` es estable y está documentado en `custom/_ejemplo.py` y `custom/README.md`.

Lo genuinamente nuevo son dos piezas: la **selección del período previo** cuando el eje es
`Mes × N Prueba` (≈ 40 líneas, análogo a `simce._periodo_previo`) y la **nota de homogeneidad de
escala** (≈ 30 líneas). El resto es ensamblaje.

**Orden recomendado.** Arreglar H2 primero: son dos líneas en `report_steps.py`, mejora el histórico de
los 6 indicadores de la org, y evita que el módulo custom de CV nazca cargando un workaround local
para un bug del motor genérico.
