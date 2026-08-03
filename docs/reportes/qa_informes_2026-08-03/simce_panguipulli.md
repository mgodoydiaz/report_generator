# QA — Informes del indicador SIMCE Panguipulli (id 6, org 1)

**Fecha**: 2026-08-03 · **Rama**: `dev` · **Crítico**: agente QA informes
**Indicador**: `id_indicator=6`, `name='SIMCE Panguipulli'`, `org_id=1`, `report_engine_type=NULL` (se infiere `simce_panguipulli` por nombre)
**Métricas**: 24 `Resultados SIMCE Panguipulli por Estudiante` (1695 filas) · 26 `Resultados SIMCE Panguipulli por Habilidad` (180 filas). La 25 (`Resultados EMN Aptus por OA`) no está asociada al indicador — no la consume nadie.
**Última evaluación en datos**: SEPTIEMBRE 2025 (`N Prueba = 4`). Nada de 2026.

## PDFs revisados

| Archivo | Págs | Origen |
|---|---|---|
| `data/output/qa_indicadores/2026-08-03/simce_panguipulli_custom_simce_panguipulli_historia.pdf` | 4 | entregado (asignatura HISTORIA, ~32 filas/prueba) |
| `data/output/qa_indicadores/2026-08-03/simce_panguipulli_LENGUAJE_qa.pdf` | 10 | **generado en este QA** vía `dispatch_v2.generar_pdf_v2(tipo='simce_panguipulli', indicator_id=6, org_id=1, filtros={'Asignatura':'LENGUAJE','Mes':'SEPTIEMBRE'})` dentro del contenedor `backend`. 7 cursos, 185 alumnos — caso representativo. |

PNG a 150 dpi en `data/output/qa_indicadores/2026-08-03/png/simce_panguipulli/` y `.../png/simce_panguipulli_leng/`.

HISTORIA existe **solo** para `8° básico A` (34/37/32/32 filas en abril/mayo/agosto/septiembre): el encabezado "HISTORIA - 8° básico A" es honesto, no es un filtro. Pero un informe de un curso no ejercita nada del layout multi-curso, por eso se generó el de LENGUAJE.

---

## Puntaje: **62 / 100**

| Dimensión | Puntaje | Comentario |
|---|---|---|
| Correctitud de datos | **31 / 40** | 20+ cifras recalculadas contra `metric_data`: todas exactas salvo una sección completa que promedia las 4 pruebas del año en vez de la seleccionada (H-1), con error de hasta 10 puntos porcentuales. |
| Cobertura de período | **11 / 15** | Cubre 1 evaluación y la declara en el encabezado corrido de todas las páginas (asignatura + mes + año). Omite establecimiento, N° de prueba, y no advierte que 2 secciones son anuales. |
| Calidad visual | **20 / 30** | Sin `nan`, pie correcto, tablas dentro de márgenes, orden cronológico, colores de nivel consistentes. Contra: nombres de columna crudos en ejes, escala tipográfica inconsistente entre gráficos, ejes que no parten en 0, `-0%`. |
| Disponibilidad de modos | **0 / 15** | **0 de 4 tarjetas de período.** `pdf_layout` y `pdf_layout_historico` son `{}` y el módulo no declara `MODOS`. Verificado en vivo. |

**El puntaje bajo es la foto correcta**: el informe especializado es sólido y casi todo cuadra al decimal; lo que no existe es el producto por período. Y no existe de una forma peor que "no implementado" — ver H-2.

---

## Verificación de datos — PDF vs recalculado por SQL

Fuente: `metric_data`, `value::json->>'PorcLogro'` (métrica 24) y `->>'LogroHabilidad'` (métrica 26), filtrando `dimensions_json` por `8`=Asignatura, `9`=Mes, `5`=Curso, `12`=Habilidad.

### HISTORIA — SEPTIEMBRE 2025 (pág. 1-4)

| # | Dato | PDF | Recalculado | ✓ |
|---|---|---|---|---|
| 1 | N alumnos 8° básico A (p1) | 32 | 32 filas, 32 RUT distintos | ✓ |
| 2 | Promedio del curso (p1, p1-gráfico) | 40% | 0.395313 | ✓ |
| 3 | Mínimo / Máximo (p1) | 12% / 68% | 0.125 / 0.675 | ✓ (ver O-2) |
| 4 | Boxplot Q1/mediana/Q3 (p2) | ~30% / ~38.7% / ~45.6% | 0.300000 / 0.387500 / 0.456250 | ✓ |
| 5 | Evolución por mes (p2) | 37 / 43 / 46 / 40 % | 0.374811 / 0.432432 / 0.456250 / 0.395313 | ✓ |
| 6 | Alumnos por nivel (p3) | 19 / 11 / 2 | Insuf(≤0.40)=19, Elem(≤0.60)=11, Adec=2 | ✓ |
| 7 | **Logro por habilidad (p3)** | **40 / 42 / 42 %** | **Septiembre: 36.1 / 43.4 / 39.9 %** | **✗ H-1** |
| 8 | Detalle TUREDO (p4) | 68% · 63% · +5% · +16% | 0.675 · media 0.632372 · slope 0.049487 · delta 0.162179 | ✓ |
| 9 | Detalle MILLAGUIR (p4) | 12% · 23% · -5% · -16% | 0.125 · 0.234776 · -0.050321 · -0.157051 | ✓ |
| 10 | Detalle PAILAÑIR (p4) | 57% · 64% · -2% · -9% | 0.575 · 0.639423 · -0.024103 · -0.091667 | ✓ |
| 11 | Detalle RAIN (p4) | 42% · 45% · **-0%** · +1% | 0.425 · 0.449519 · -0.001859 · +0.014744 | ✓ valor / ✗ formato (O-1) |
| 12 | Detalle Guinel Fuentes (p4, solo 3 pruebas) | 42% · 34% · +7% · +14% | 0.425 · 0.335684 · slope 0.071475 (n=3) · delta 0.142949 | ✓ |
| 13 | Filas de la tabla de detalle (p4) | 32 | 32 | ✓ |

### LENGUAJE — SEPTIEMBRE 2025 (PDF generado, pág. 1-10)

| # | Dato | PDF | Recalculado | ✓ |
|---|---|---|---|---|
| 14 | Resumen por curso, 7 filas (p1) | 25/45/3/86 · 32/54/14/86 · 28/54/12/81 · 29/49/26/74 · 25/60/31/81 · 25/48/14/79 · 21/59/33/74 | 44.89/2.78/86.11 · 53.72/14.29/85.71 · 54.00/11.90/80.95 · 49.10/26.19/73.81 · 60.19/30.95/80.95 · 47.90/14.29/78.57 · 58.84/33.33/73.81 | ✓ (7/7 cursos, 12 cifras) |
| 15 | Evolución por curso y mes, 28 barras (p2) | 51/41/45/45 · 54/56/52/54 · 57/51/60/54 · 55/43/56/49 · 55/45/62/60 · 47/39/53/48 · 56/42/57/59 | idéntico a `avg` por curso×mes | ✓ (28/28) |
| 16 | Alumnos por nivel, 21 celdas (p3) | 13/5/7 · 7/14/11 · 7/10/11 · 10/10/9 · 3/10/12 · 7/11/7 · 2/8/11 | idéntico | ✓ (21/21, suman los N de la tabla) |
| 17 | **Logro por habilidad, 21 barras (p3)** | 51/42/43 · 60/45/52 · 64/48/53 · 61/45/47 · 65/51/52 · 54/40/45 · 61/46/52 | **coinciden con el promedio de LOS 4 MESES**, no con septiembre (ej. II° medio E "Reflexionar": PDF 46%, septiembre real **56%**) | **✗ H-1** |
| 18 | Un salto de página por curso (p4-p10) | 7 páginas, 1 por curso | 7 cursos | ✓ |

**Resultado**: 76 de 79 valores recalculados coinciden al punto porcentual. Los 3 grupos que fallan son todos la misma sección.

---

## Hallazgos

### H-1 · La sección "Logro Promedio por Habilidad" promedia el año entero, no la prueba del informe — **grave**
**Página 3 de ambos informes.** `backend/rgenerator/reports/simce_panguipulli/esquema.json:132` declara `"df_input": "habilidad"`. Ese DataFrame es el histórico completo filtrado solo por asignatura; el recorte a una prueba está en `"habilidad_prueba"`, que `crear_informe.py:103` **ya construye y ya publica** — simplemente nadie lo consume. Las otras 5 secciones de la prueba usan correctamente `estudiantes_prueba`.

Consecuencia: bajo un encabezado que dice "SEPTIEMBRE 2025" en cada página, el único gráfico que le dice al profesor *qué habilidad reforzar* muestra el promedio abril-septiembre. En HISTORIA invierte el ranking (el PDF sugiere Aplicar ≈ Comprender > Analizar; en septiembre es Aplicar 43% > Comprender 40% > Analizar 36%). En LENGUAJE el error llega a **10 pp**: II° medio E "Reflexionar sobre el texto" se informa 46% cuando en septiembre fue 56%; II° medio C "Reflexionar" se informa 51% cuando fue 59%.

Arreglo: un token en `esquema.json:132` (`"habilidad"` → `"habilidad_prueba"`). Si el promedio anual se quisiera conservar, debe ser una **segunda** sección con el título diciéndolo.

### H-2 · 0 de 4 tarjetas de período, y declarar `MODOS` a secas no lo arregla: rompe con 500 — **grave**
Verificado en vivo dentro del contenedor:
```
custom.modulo_de_indicador('simce_panguipulli')  → None
simce_panguipulli.MODOS                          → None
```
`indicators.py:422-427` calcula `tiene = {evaluacion: bool(pdf_layout['sections']), historico: ...}` = `{False, False}`, y como `modulo_custom is None` las 4 tarjetas caen en `_MOTIVO_SIN_LAYOUT` (`indicators.py:479`). El texto que ve el usuario es:

> "Este informe aún no está configurado — pide a tu administrador que agregue secciones en Editor de Layout → Informe PDF → por evaluación."

Ese consejo es **falso para este indicador**: si el admin llenara `pdf_layout` desde la UI obtendría el motor v1 genérico, no el formato por habilidad, y perdería el informe correcto que sí existe. No hay acción correcta disponible desde la interfaz.

Peor: `indicators.py:1149` invoca `modulo_custom.generar(db, ..., modo=modo_periodo, ...)`, pero `custom/simce_panguipulli.py:23-34` define `generar` **sin el kwarg `modo`**. Añadir `MODOS = [...]` y nada más habilita las 4 tarjetas y las convierte en 4 `TypeError` → HTTP 500 (el `except` del router solo captura `DatosInsuficientes`/`ValueError`). Ver el veredicto abajo.

### H-3 · Los gráficos no comparten escala tipográfica ni convención de ejes — **medio**
Comparando dentro de una misma página (p2 de ambos informes): el boxplot renderiza título y etiquetas ~2× más grandes que el gráfico de evolución que va inmediatamente debajo; parecen dos informes distintos pegados. Además:
- Las etiquetas de eje Y arrastran el **nombre crudo de la columna**: `PorcLogro (%)` (p2) y `LogroHabilidad (%)` (p3). El gráfico de la p1 sí usa el `ylabel` humano "Logro (%)" porque el esquema lo declara; las otras dos secciones no lo declaran y `charts.py` cae al nombre de columna.
- En HISTORIA el boxplot arranca el eje en **10%** mientras el gráfico de barras de la página anterior arranca en 0% — dos lecturas del mismo dato con base distinta.
- Formato de ticks inconsistente: `0% / 20% / 40%` en p1 vs `0.0% / 5.0% / 10.0%` en p3.

### H-4 · Nada advierte qué columnas son anuales dentro de un informe de una prueba — **medio**
Páginas 4+: la tabla por alumno mezcla "Logro" (la prueba) con "Promedio Año", "Avance" y "Mejora" (todo el año), sin nota al pie. "Avance" es una **pendiente de regresión** sobre el mes ordinal y "Mejora" es el **delta contra la primera prueba rendida por ese alumno** — que no es la misma para todos: Guinel Fuentes no rindió abril, así que su "Mejora +14%" se mide contra mayo mientras la del resto se mide contra abril. Ninguna de las dos definiciones aparece en el PDF.

### H-5 · Cobertura declarada incompleta — **menor**
El encabezado corrido (3 líneas, en todas las páginas) dice `Informe SIMCE Panguipulli / HISTORIA - 8° básico A / SEPTIEMBRE 2025`. Correcto y suficiente para no confundir la evaluación. Falta: el **establecimiento** (dimensión 3 = "Panguipulli", disponible en los datos) y el **N° de prueba** (4). El subtítulo es el genérico `"Resumen de la prueba seleccionada"` del esquema, donde el contrato §3.1 pide el nombre del establecimiento.

---

## Observaciones menores

| id | Página | Observación |
|---|---|---|
| O-1 | p4 (HISTORIA ×1, LENGUAJE ×6) | `-0%` en Avance/Mejora: pendientes de -0.19% que redondean a cero negativo. Debe ser `0%`. |
| O-2 | p1 | Redondeo bancario: `0.125 → 12%` y `0.675 → 68%`. Regla consistente pero el usuario lee "12%" donde el dato es 12.5%. |
| O-3 | p1 | Encabezados de tabla sin tilde: `Minimo`, `Maximo`. |
| O-4 | p3 | La leyenda del apilado lista Insuficiente→Adecuado de arriba a abajo mientras el stack los dibuja al revés. |
| O-5 | p4 (LENGUAJE, 3 filas) | Alumnos sin nombre: la fila sale con `—` (correcto, `helpers.MARCA_SIN_DATO`, **cero `nan` en todo el PDF**) pero una fila anónima en una tabla nominal no es accionable para el profesor. Es dato sucio de origen, no del motor. |
| O-6 | p4 | Casing heterogéneo entre cursos: `4° básico A` en Title Case, `II° medio E` en MAYÚSCULAS, y un alumno en Title Case dentro de una tabla en mayúsculas (HISTORIA, "Guinel Fuentes Joaquin Esteban"). Dato de origen; el motor no normaliza. |
| O-7 | p1 (HISTORIA) | Con un solo curso, el gráfico de barras ocupa el ancho completo con una sola barra. Cosmético, pero se ve roto. |
| O-8 | — | No hay portada; el contenido arranca en la p1 bajo el bloque de título. Es la salvedad aceptada por el dueño en fase 2, no un defecto. |
| O-9 | — | Pie izquierdo `Fundación PHP` = `organizations.name` de la org 1 ✓ (vía `dispatch_v2.aplicar_pie_organizacion`). Numeración de página presente en las 10 páginas ✓. |

**Referencias**: `/mnt/c/Users/magod/Desktop/PDF_test/referencias/` contiene únicamente `referencia_idel_panguipulli_2025.pdf`. **No hay referencia SIMCE Pullinque en el montaje**, así que la comparación con el formato oficial SIMCE se hizo contra el informe hermano de esta misma tanda (`simce_custom_simce_lenguaje.pdf`) y contra `simce/esquema.json`, no contra el PDF de referencia.

---

## Veredicto de hardcodeabilidad — ¿pasa de 0/4 a 4/4 solo declarando `MODOS`?

**No. La promesa del contrato (§2.5a) es correcta sobre la *habilitación* de las tarjetas y falsa sobre la *generación*.**

Lo que sí es cierto: `report_options` ya está implementado según §2.5a (`indicators.py:447-479`), `custom/__init__.py` ya expone `modos/soporta_modo/motivo_modo/modulo_de_indicador`, y `engine_types.inferir_engine_type` resuelve `"SIMCE Panguipulli"` → `simce_panguipulli` **antes** que `simce` (chequea `"panguipulli"` primero), así que no hay riesgo de que el módulo equivocado capture el indicador. En el momento en que `simce_panguipulli.py` declare `MODOS`, las 4 tarjetas se habilitan **sin tocar el `pdf_layout` vacío**. Eso funciona.

Lo que falta para que además *generen*:

**1. Firma de `generar` (bloqueante, 3 líneas).** `custom/simce_panguipulli.py:23` no acepta `modo`. El router lo pasa siempre (`indicators.py:1149`). Sin esto son 4 tarjetas que devuelven 500.

**2. Un `_generar_por_modo` propio (~110 líneas).** Clon de `simce.py:758-868` con las sustituciones de columna: `Rend`→`PorcLogro`, `Logro`(nivel)→`Nivel_Logro`, `Simce`→(no existe), `columnas_puntaje=["PorcLogro"]`.

**3. Un `_preparar_dataframes` propio (~130 líneas).** Clon de `simce.py:294-399`. Diferencias reales, no cosméticas:
   - El segundo DataFrame es `habilidad`, no `preguntas`. `data._role_from_metric_name("Resultados SIMCE Panguipulli por Habilidad")` devuelve `"otros"` (no matchea `pregunta` ni `estudiante`) — `dispatch_v2:242-249` hoy lo resuelve con una cadena de fallbacks (`habilidad` → `metric_26` → primer df restante). Hay que replicar esa resolución o, mejor, añadir la regla `"habilidad" → "habilidad"` en `data._role_from_metric_name` (**3 líneas, y sirve a los dos caminos**).
   - `Nivel_Logro` **no existe en los datos**: es un `row_threshold` derivado. `_derived_fields_del_esquema()` debe apuntar a `simce_panguipulli/esquema.json` y aplicarse **antes** del recorte de período (igual que en SIMCE, la regla ya está resuelta).
   - Hay que producir también `habilidad_periodo` y `habilidad_prueba` (el `simce.py` produce `preguntas_periodo`/`preguntas_prueba`; misma mecánica).

**4. Constructores de secciones (~150 líneas).** Aquí el `esquema.json` de 4 páginas **sí sirve de base, pero solo para los `params` de los gráficos, no para la lógica de modos**:
   - **Sirve directo**: los 6 bloques `secciones_fijas` y el bloque `secciones_dinamicas` se copian casi literal a `_secciones_comunes` / `_secciones_dinamicas_por_curso`, con `df_input` parametrizado (`estudiantes_prueba` en `ultima_prueba`, `estudiantes_periodo` en los demás). Eso cubre las secciones 2-7 de los 4 modos.
   - **No sirve**: (a) no tiene resumen comparado contra el período anterior — hay que llamar `sec.tabla_resumen_comparado` + `sec.seccion_resumen_comparado`; (b) su sección de evolución es fija con `df_input: "estudiantes"` (histórico entero), y en `anual`/`semestral` debe ser `estudiantes_periodo` envuelta en `sec.seccion_evolucion` para la auto-omisión de la decisión 16; (c) no tiene riesgo persistente; (d) **viola la decisión 1/5 tal cual está**: pone la tabla por alumno siempre, y en `anual`/`semestral`/`personalizado` no debe ir.
   - Se **borran** respecto de SIMCE: resumen de Puntaje SIMCE, boxplot de Simce, evolución de Simce, "Logro Promedio por Eje Temático", "Estadística por Pregunta del Establecimiento" y "Logro por Pregunta - {curso}". Son ~6 secciones menos.

**5. Encabezado y período (~45 líneas).** Clon de `_lineas_encabezado` + `_descripcion_periodo` (`simce.py:869-911`), sin cambios de fondo.

**6. Constantes y `MODOS` (~30 líneas).** `MODOS = ["ultima_prueba","semestral","anual","personalizado"]` — Panguipulli aplica 4 pruebas al año (abril/mayo/agosto/septiembre), así que semestral y anual tienen sentido pedagógico igual que en SIMCE; `MOTIVO_MODO_NO_DISPONIBLE = {}`. `NIVELES = ["Adecuado","Elemental","Insuficiente"]`, `NIVEL_RIESGO = "Insuficiente"`. Ojo: `indicators` no declara `achievement_levels` para el id 6, así que `_niveles_y_colores` caerá al default — hay que llevarse también ese helper (~25 líneas) o dejar los colores por defecto.

**Total: ~500-550 líneas nuevas en `custom/simce_panguipulli.py`** (hoy tiene 43), de las cuales **~380 son copia casi verbatim de `simce.py`**: `_partir_temporales`, `_filtros_ultima_prueba`, `_clave_bucket`, `_etiqueta_bucket`, `_periodo_previo`, `_niveles_y_colores`, `_seccion_chart`, el esqueleto de `_preparar_dataframes` y el de `_generar_por_modo` no tienen **nada** de SIMCE: son la mecánica del motor único.

### Esfuerzo comparado con `custom/simce.py`
`simce.py` son 911 líneas y fue el piloto: hubo que inventar `_secciones.py` (757 líneas de helpers genéricos: `bloque_titulo`, `seccion_evolucion`, `riesgo_persistente`, `secciones_por_curso`, `tabla_resumen_comparado`…). **Todo eso ya está escrito y es agnóstico de columna** — recibe `columna_nivel`, `columna_temporal`, `columnas_puntaje`, `formatos` como argumentos, así que funciona con `PorcLogro`/`Nivel_Logro` sin tocarlo.

Estimación: **40-55% del esfuerzo de `simce.py`** — el trabajo conceptual está hecho, queda la transcripción. En sesiones: **1 sesión** para el port + tests de humo equivalentes a `tests/reports/test_simce_modos.py` (verifican títulos/orden/`fn`/`df_input` sin renderizar). Los 3 riesgos concretos son (a) el rol `habilidad` en `data.py`, (b) que `Nivel_Logro` es derivado y el riesgo persistente lo necesita presente en `estudiantes_periodo`, (c) que Panguipulli tiene 4 pruebas y no 5, así que el `_periodo_previo` semestral cae en un semestre con 2 pruebas — hay que verificar que `_clave_bucket` no devuelva un semestre vacío.

### Recomendación
Antes del port, **arreglar H-1** (un token en `esquema.json:132`): es 1 línea, corrige un número que hoy se le está mostrando mal al establecimiento, y el port heredaría el mismo error en los 4 modos si se copia el esquema tal cual.

Y evaluar la alternativa estructural: si el segundo módulo va a ser 380 líneas copiadas del primero, el candidato natural es extraer ese esqueleto a `_secciones.py` (o a un `_motor_unico.py`) parametrizado por un descriptor de columnas — `{"valor": "PorcLogro", "nivel": "Nivel_Logro", "secundario": "habilidad", "valor_secundario": "LogroHabilidad"}` — con `simce.py` y `simce_panguipulli.py` reducidos a ~150 líneas cada uno. DIA y Cálculo Veloz vienen después con la misma forma; hacer el segundo por copia garantiza que el tercero y el cuarto también lo sean.
