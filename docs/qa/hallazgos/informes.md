# QA — Inventario y consolidación del motor de informes

Fecha: 2026-07-22 · Rama: `dev3` · Autor: agente QA (solo lectura, sin cambios de código)

## 0. Resumen ejecutivo

Hoy conviven **4 motores de generación de PDF/Word activos** + **2 caminos muertos**, expuestos al usuario por **4 puntos de entrada distintos en el frontend** (3 botones en `/results` + 1 en la página legacy `/results-recharts`). Cada motor tiene su **propio formato de filtros** (por id de dimensión vs. por nombre humano) y su **propia lógica de matching** — dos de las tres implementaciones soportan filtros multi-valor y una no, lo que **rompe silenciosamente** el PDF más usado (botón "Generar Reporte", motor v1) cuando el usuario selecciona más de un valor en un filtro. Además el motor v2 (paridad LaTeX) **descarta el filtro Año en informes DIA** sin avisar. Esto explica directamente la percepción del dueño del producto de que "muchos informes no salen en el formato deseado".

---

## 1. Tabla-inventario de motores/caminos

| # | Motor / camino | Entrada (código) | Formato de filtros | Tipos soportados | Plantilla/esquema | Invocado desde | Estado |
|---|---|---|---|---|---|---|---|
| 1 | **Motor v1 "weasyprint" (`build_pdf_bytes`)** | `backend/rgenerator/core/report_steps.py:976` (`build_pdf_bytes`), step `RenderPDFReport` (:1171) | `{id_dimension_str: valor}` — **solo igualdad simple, sin soporte de listas** (`_build_records`, :218-222) | Cualquier Indicator con `pdf_layout` configurado (genérico, incl. IDEL/CV/FL) | `indicator.pdf_layout` (JSON en BD, editor visual) + `report_base.html` (Jinja2) | `POST /api/indicators/{id}/export-pdf` (`backend/routers/indicators.py:306`) — botón **"Generar Reporte"** en `/results` (`GenerateReportModal.jsx`) y botón PDF en `/results-recharts` (legacy, `ResultsRecharts.jsx:78`) | **Vivo, primario** — pero con bug de filtros multi-valor (ver Hallazgo 1) |
| 2 | **Motor "pdl_idel" (hardcodeado)** | `backend/rgenerator/tooling/report_pdl_idel_tools.py` (`build_pdl_idel_pdf_bytes`), reusa `scripts/report_pdl_idel.py` | `{id_dimension_str: valor|[valor]}` traducido a kwargs fijos (Establecimiento/Año/Curso/Versión); **ignora cualquier otra dimensión** | Solo IDEL-Woodcock (metric_id hardcodeado, default 8) | Sin esquema declarativo — todo hardcodeado en Python/matplotlib (`PdfPages`) | Mismo endpoint `POST /api/indicators/{id}/export-pdf` con `engine=pdl_idel` (dispatcher en `indicators.py:397-405`) | **Vivo**, pero rígido y con IDs de dimensión hardcodeados |
| 3 | **Motor v2 "paridad LaTeX" (`reports/` package)** | `backend/rgenerator/reports/runtime.py`, `charts.py`, `tables.py`, `data.py` + `simce/`, `simce_panguipulli/`, `dia/` (`crear_informe.py` + `esquema.json`) | `{nombre_columna_humano: valor|[valor]}` — soporta listas (`data.py:196-202`) | **Solo simce, simce_panguipulli, dia** (`routers/reports.py:193-194`) — NO IDEL/FL/CV | `esquema.json` declarativo por tipo (`derived_fields`, `secciones_fijas`, `secciones_dinamicas`, `branding`) | `POST /api/reports/{tipo}` (`backend/routers/reports.py:171`) — botón **"Generar v2"** en `/results`, visible solo si el nombre del indicador contiene "simce"/"dia"/"panguipulli" (`Results.jsx:325-332`) | **Vivo**, más nuevo y mejor diseñado, pero con cobertura parcial y bug de filtro Año (Hallazgo 2) |
| 4 | **Informes Word (docxtpl)** | `backend/rgenerator/reports/word/engine.py`, `word/informes/resumen_indicador.py`, plantilla `word/templates/resumen_indicador.docx` | `{nombre_columna_humano: valor}` vía `cargar_dataframes_indicator` (mismo loader que motor v2) | Genérico — 1 solo informe registrado hoy (`resumen_indicador`) | Plantilla `.docx` con placeholders `{{ }}` (docxtpl) | `POST /api/reports/word/{nombre}` (`routers/reports.py:119`) — botón **"Word"** en `/results` (`GenerateWordReportModal.jsx`) | **Vivo**, pero solo 1 informe registrado (no hay "informes Word por indicador" plural pese al nombre del feature en memoria) |
| 5 | **`RenderHtmlReport` (step, motor "HTML→PDF" viejo)** | `backend/rgenerator/core/report_steps.py:1225` + `backend/rgenerator/tooling/report_html_tools.py` | N/A | Requiere `ctx.aux_dir` poblado por `GenerateGraphics`/`GenerateTables` | `backend/schemas/esquema_informe*.json` (formato `variables_documento`/`secciones_fijas`/`secciones_dinamicas`) | Registrado en `STEP_MAPPING` (`pipeline_tools.py:33`) pero **ningún pipeline en `db_seed.json` ni en `config/` lo referencia**; sus dependencias (`GenerateGraphics`, `GenerateTables`) fueron eliminadas del `STEP_MAPPING` (ver docstring `report_steps.py:1-16`) | **MUERTO** — código huérfano, no ejecutable hoy con éxito (aux_dir nunca se pobla) |
| 6 | **`scripts/generate_report.py`** (LaTeX CLI original) | Importa `from rgenerator import BASE_DIR,...` y `from funciones_informe import *` | N/A (hardcodea `pd.read_excel`) | SIMCE únicamente | LaTeX (`formato_informe.tex`, no incluido en este análisis) | CLI manual | **ROTO** — el paquete top-level `rgenerator` no existe (el paquete instalado es `backend.rgenerator`, ver `pyproject.toml: where=["backend"]`); `import rgenerator` falla con `ModuleNotFoundError` |
| 7 | **`scripts/report_pdl_idel.py`** (CLI standalone) | psycopg2 directo vía `DATABASE_URL` | Args CLI (`argparse`) | IDEL-Woodcock | Hardcodeado en Python | CLI manual, y reusado como librería por el motor #2 | **Vivo** (funciones puras reusadas por el endpoint; el CLI en sí es una herramienta operativa aparte) |

**Total: 4 motores vivos + 1 step muerto + 1 script roto = 6 caminos distintos de "generar informe" en el código, expuestos por 4 botones de UI.**

---

## 2. Diagrama de flujo de filtros (UI → PDF) y puntos de pérdida

```
┌─────────────────────────────────────────────────────────────────────┐
│  /results (Results.jsx)                                             │
│  MultiSelectFilters → selectedFilters = { "12": ["II A","II B"],    │
│                                            "7": ["2026"] }           │
│  (keyed por id_dimension, SOPORTA multi-valor — estado único        │
│   de la página, alimenta el dashboard vía /api/results)             │
└───────────────┬───────────────┬───────────────┬─────────────────────┘
                │               │               │
   ┌────────────┘   ┌───────────┘   ┌───────────┘
   ▼                ▼                ▼
[Botón "Generar    [Botón "Generar   [Botón "Word"]
 Reporte" — v1]     v2" — solo       filtrosWord = convierte
 initialFilters =   SIMCE/DIA]       dimId→nombre humano
 selectedFilters    params =         (igual que v2)
 (SIN CONVERTIR,    convierte
 sigue siendo       dimId→nombre     POST /api/reports/word/{nombre}
 {dimId: [...]})    humano           { filtros: {Curso:[...], Año:[...]} }
                    { filtros:              │
 POST /api/          {Curso:[...],          ▼
 indicators/{id}/    Hito:"CIERRE"} }   cargar_dataframes_indicator
 export-pdf                │            (data.py) — filtros aplicados
 { filters:                ▼            por nombre humano, SOPORTA
   {"12":["II A",...]} }  POST /api/    listas (_matches, :196-202)
        │                  reports/{tipo}      │
        ▼                  routers/reports.py  ▼
 build_pdf_bytes           :171               PDF/Word refleja
 (report_steps.py:976)        │                filtros ✔
        │                     ▼
        ▼              ⚠ split filtros_temporales vs
 _build_records            filtros_estructurales (:200-220)
 (report_steps.py:160)     Para DIA: requeridos=["Hito","Año"]
        │                  → AMBOS se separan a
        ▼                    filtros_temporales_dict,
 ⚠ PUNTO DE PÉRDIDA 1:       pero solo "Hito" se lee
 filtros.items() comparado    (routers/reports.py:309) y se
 con IGUALDAD DE STRING       pasa a dia_informe.construir().
 (:218-222). Si el valor      "Año" queda en el dict y
 es una LISTA (multi-select   NUNCA se usa.
 heredado del dashboard),
 str(["II A","II B"]) nunca  ⚠ PUNTO DE PÉRDIDA 2:
 matchea ningún valor de      dia/crear_informe.construir()
 dims_json → filtro          (dia/crear_informe.py:25-30)
 "aplicado" pero PDF          NI SIQUIERA ACEPTA parámetro
 vacío o con TODOS los        año — imposible pasarlo aunque
 registros (según el          se arregle el router.
 resto de filtros).           RESULTADO: el informe DIA v2
                               siempre mezcla todos los años
                               presentes en la metric para
                               el Hito elegido.
```

**Resumen de los 2 puntos de pérdida confirmados:**

1. **Motor v1 (el botón principal "Generar Reporte")** recibe los filtros del dashboard tal cual (`initialFilters={selectedFilters}` en `Results.jsx:480`), que desde B9 son **listas** cuando el usuario selecciona más de un valor. `_build_records` en `report_steps.py:218-222` compara con `==` de strings, no con `in` — nunca soportó multi-valor. Si el usuario no toca el filtro en el modal (lo deja precargado desde el dashboard) y tenía más de un valor seleccionado, **el filtro se ignora silenciosamente y el PDF sale con datos incorrectos o vacío**.
2. **Motor v2 (DIA)** captura el filtro "Año" pero lo descarta antes de llegar a la función que construye el PDF — **el PDF DIA v2 nunca respeta el filtro de año**, solo el de Hito.

---

## 3. Hallazgos

### H1 — [CRÍTICA] Motor v1 no soporta filtros multi-valor → PDF con datos incorrectos o vacíos
- **Archivo:línea**: `backend/rgenerator/core/report_steps.py:218-222` (`_build_records`)
- **Detalle**: la comparación `str(dims_json.get(fk, "")) == str(fv)` no maneja `fv` de tipo lista/tupla. Los filtros del dashboard (`MultiSelectFilters`, ver `frontend/src/pages/Results.jsx`) están en formato multi-valor desde el sprint "B9". `GenerateReportModal.jsx:74` precarga esos mismos filtros (`initialFilters={selectedFilters}`) en el modal del motor v1 sin normalizar a escalar.
- **Contraste**: las otras dos implementaciones de matching en el repo (`backend/routers/results.py:179-185` y `backend/rgenerator/reports/data.py:196-202`) sí soportan listas (`isinstance(expected, (list, tuple, set))` → IN).
- **Fix sugerido**: unificar `_build_records` para usar la misma función `_matches` que ya existe en `results.py`/`data.py` (idealmente extraerla a un módulo compartido, ver sección 4). Mientras tanto, normalizar en el modal (`GenerateReportModal.jsx`) los filtros a escalar (tomar primer valor) o convertir `_build_records` a `_matches` con soporte `IN`.

### H2 — [CRÍTICA] Filtro "Año" descartado en informes DIA del motor v2
- **Archivo:línea**: `backend/routers/reports.py:200-220` (split `filtros_temporales`/`filtros_estructurales`) y `:301-315` (rama `tipo == "dia"`); `backend/rgenerator/reports/dia/crear_informe.py:25-30` (`construir()` sin parámetro `anio`)
- **Detalle**: `filtros_temporales["dia"] = ["Hito", "Año"]` marca ambos como temporales, así que ninguno llega al loader por id (`cargar_dataframes_indicator`). Pero en la rama `dia` del endpoint solo se lee `hito = filtros_temporales_dict.get("Hito")` (línea 309) — "Año" nunca se usa, y `dia_informe.construir()` ni siquiera tiene un parámetro para recibirlo.
- **Impacto**: si un colegio tiene datos DIA de 2025 y 2026 con los mismos hitos (DIAGNOSTICO/INTERMEDIO/CIERRE), filtrar por Año en la UI no tiene ningún efecto en el PDF — mezcla ambos años.
- **Fix sugerido**: agregar parámetro `anio: int | None` a `dia_informe.construir()`, filtrar `df_estudiantes`/`df_preguntas` por columna `Año` igual que se hace con `Hito`, y pasar `anio=filtros_temporales_dict.get("Año")` desde el router.

### H3 — [ALTA] 4 puntos de entrada distintos para "generar informe" en la misma sesión de usuario
- **Archivo:línea**: `frontend/src/pages/Results.jsx:306-411` (3 botones: "Generar Reporte", "Generar v2", "Word") + `frontend/src/pages/ResultsRecharts.jsx:78-99` (4to camino, página legacy `/results-recharts` aún ruteada en `App.jsx:53`)
- **Detalle**: cada botón habla con un backend distinto, con distinto formato de filtro y comportamiento distinto ante el mismo estado de filtros del dashboard. No hay ninguna señal en la UI de qué motor produce el resultado "correcto" u oficial.
- **Fix sugerido**: ver Propuesta de consolidación (sección 4). Como paso intermedio de bajo esfuerzo, eliminar el botón de `/results-recharts` (página ya marcada legacy) y renombrar los botones para reflejar honestamente sus limitaciones ("PDF (histórico/multi-valor no soportado)" vs "PDF paridad LaTeX (solo 1 punto temporal)").

### H4 — [ALTA] Motor v2 no cubre IDEL/PDL, Fluidez Lectora ni Cálculo Veloz
- **Archivo:línea**: `backend/routers/reports.py:47-58` (`listar_tipos`), `:193-194` (whitelist `("simce", "simce_panguipulli", "dia")`)
- **Detalle**: el motor mejor diseñado (esquema declarativo, soporte de filtros multi-valor, derived_fields antes de filtrar) solo sirve 3 de ~6 tipos de evaluación de la fundación. IDEL cae al motor hardcodeado #2, y Fluidez Lectora/Cálculo Veloz dependen enteramente del motor v1 genérico (con el bug de H1).
- **Fix sugerido**: incluido en la propuesta de consolidación — generalizar `reports/data.py` + `runtime.py` como el único loader/renderer, con un `esquema.json` por tipo de evaluación (incluyendo IDEL, FL, CV).

### H5 — [ALTA] Detección de tipo del motor v2 por substring del nombre del indicador
- **Archivo:línea**: `frontend/src/pages/Results.jsx:325-332`
```js
const tipoV2 = nombre.includes('panguipulli') ? 'simce_panguipulli'
    : nombre.includes('simce') ? 'simce'
    : nombre.includes('dia') ? 'dia'
    : null;
```
- **Detalle**: heurística frágil basada en `indicator.name.toLowerCase()`. Un indicador nombrado, por ejemplo, "Comparativo DIA-SIMCE 2026" activaría `simce` (por el orden de los `includes`) aunque sea un indicador DIA. No hay campo explícito `tipo_motor_v2` en el modelo `Indicator`.
- **Fix sugerido**: agregar un campo explícito (ej. `Indicator.report_engine_type`) en vez de inferir por nombre.

### H6 — [MEDIA] `_build_records` (motor v1) no filtra `MetricData` por `org_id`
- **Archivo:línea**: `backend/rgenerator/core/report_steps.py:211` — `db.query(MetricData).filter(MetricData.id_metric == mid).all()`
- **Contraste**: `backend/rgenerator/reports/data.py:149-152` sí filtra explícitamente `MetricData.org_id == org_id` para el mismo tipo de query.
- **Detalle**: el indicador y sus `IndicatorMetric` están validados por `org_id`, y `_validate_metric_ids` (`routers/indicators.py:19-36`) previene enlazar métricas de otra org **al crear/editar** el indicador. Pero `_build_records` no repite ese filtro como defensa en profundidad — si esa validación se relaja en el futuro, o hay datos legados sin validar, `MetricData` de otra organización con el mismo `id_metric` (colisión de ID, restauración de seed, etc.) podría filtrarse al PDF.
- **Fix sugerido**: agregar `MetricData.org_id == org_id` explícito en `_build_records`, igual que en `data.py`.

### H7 — [MEDIA] Dos esquemas JSON homónimos con estructuras incompatibles
- **Archivo:línea**: `backend/schemas/esquema_informe*.json` (`variables_documento`/`secciones_fijas`/`secciones_dinamicas`) vs `backend/rgenerator/reports/{simce,dia,simce_panguipulli}/esquema.json` (`title`/`subtitle`/`branding`/`derived_fields`/`secciones_fijas`/`secciones_dinamicas`)
- **Detalle**: comparten el nombre "esquema" y parcialmente las claves (`secciones_fijas`/`secciones_dinamicas`), pero son consumidos por motores completamente distintos (uno muerto — `RenderHtmlReport`, ver H8 — y otro vivo). Alto riesgo de edición cruzada por error.
- **Fix sugerido**: eliminar `backend/schemas/esquema_informe*.json` junto con H8, o renombrarlos claramente (`esquema_legacy_latex_*.json`) si se conservan como referencia histórica.

### H8 — [MEDIA] Código muerto activo en el repo (aumenta la superficie de confusión)
- **Archivo:línea**:
  - `backend/rgenerator/core/report_steps.py:1225` (`RenderHtmlReport`) — registrado en `STEP_MAPPING` (`pipeline_tools.py:33`) pero depende de `GenerateGraphics`/`GenerateTables`, steps ya eliminados del mapping (docstring de `report_steps.py:1-16` lo confirma). Ningún pipeline en `db_seed.json` lo referencia.
  - `scripts/generate_report.py:2` — `from rgenerator import BASE_DIR,...` falla porque el paquete instalado es `backend.rgenerator` (`pyproject.toml`), no `rgenerator` top-level. Script 100% roto hoy.
  - `CLAUDE.md` (raíz del repo, sección Arquitectura) documenta `report_steps.py` como si aún tuviera `GenerateGraphics, GenerateTables, RenderReport, GenerateDocxReport` — desactualizado respecto al estado real (`RenderPDFReport`, `RenderHtmlReport`).
- **Fix sugerido**: eliminar `RenderHtmlReport` + `report_html_tools.py` + `scripts/generate_report.py` + `scripts/funciones_informe.py` + `backend/schemas/esquema_informe*.json` en un solo PR de limpieza; actualizar CLAUDE.md.

### H9 — [MEDIA] IDs de dimensión hardcodeados en el motor IDEL
- **Archivo:línea**: `backend/rgenerator/tooling/report_pdl_idel_tools.py:37-43` (`DIM_ESTABLECIMIENTO = "3"`, etc.)
- **Detalle**: si la métrica IDEL-Woodcock se re-siembra (re-seed) y las dimensiones obtienen otros `id_dimension`, el informe deja de encontrar columnas y falla (o peor, matchea la dimensión equivocada si el nuevo ID coincide por casualidad con otro significado). También ignora silenciosamente cualquier filtro de dimensión no contemplada en `_translate_filters` (documentado en el propio código, línea 117, pero no visible para el usuario final).
- **Fix sugerido**: resolver los IDs de dimensión por nombre (`Dimension.name == "Establecimiento"`) en vez de por ID fijo, igual que hace `data.py`.

### H10 — [BAJA] Lógica de carga de records duplicada 3 veces
- **Archivo:línea**: `report_steps.py:_build_records` (:160-256), `reports/data.py:_records_for_metric` (:113-212), `report_steps.py` usa además su propia copia de `_to_field_name`
- **Detalle**: tres implementaciones casi idénticas de "leer `MetricData` + `dimensions_json` + proyectar a dict humano-legible" con pequeñas diferencias de comportamiento (H1, H6) que ya han divergido. Cada bugfix debe aplicarse 2-3 veces.
- **Fix sugerido**: extraer un único loader compartido (ver propuesta de consolidación).

---

## 4. Propuesta de consolidación

### Arquitectura recomendada: un solo motor de datos + un solo motor de render, parametrizados por esquema

```
┌────────────────────────────────────────────────────────────────┐
│  UI: un único componente "Generar informe" en /results          │
│  - Filtros SIEMPRE en formato {id_dimension: [valores]}         │
│    (el mismo que usa el dashboard — sin conversión a nombre)    │
│  - Selector de "tipo de informe" (evaluación/histórico) igual   │
│    que hoy, pero YA NO selector de "motor"                      │
└───────────────────────────┬───────────────────────────────────┘
                             ▼
                  POST /api/reports/{indicator_id}
                  { filters: {id_dim: [...]}, tipo, overrides }
                             ▼
┌────────────────────────────────────────────────────────────────┐
│  LOADER ÚNICO (evolución de reports/data.py)                    │
│  - filtra MetricData por org_id SIEMPRE                         │
│  - _matches() único con soporte IN, reutilizado también por     │
│    /api/results (fuente de verdad única del filtrado)           │
│  - separa filtros temporales/estructurales según                │
│    `esquema.json.temporal_dims` (declarativo, no hardcodeado    │
│    por tipo como hoy en routers/reports.py)                     │
└───────────────────────────┬───────────────────────────────────┘
                             ▼
┌────────────────────────────────────────────────────────────────┐
│  RENDERER ÚNICO (evolución de reports/runtime.py + charts.py +  │
│  tables.py), pilotado 100% por esquema.json declarativo:        │
│    - 1 esquema.json por tipo de evaluación: simce,               │
│      simce_panguipulli, dia, idel_pdl, fluidez_lectora,          │
│      calculo_veloz, + "genérico" (fallback = el actual           │
│      indicator.pdf_layout del motor v1, para indicadores ad-hoc) │
│    - Word usa el MISMO loader, solo cambia el template engine    │
│      (docxtpl en vez de WeasyPrint)                               │
└────────────────────────────────────────────────────────────────┘
```

### Qué se elimina
| Ítem | Esfuerzo |
|---|---|
| `RenderHtmlReport` step + `report_html_tools.py` (código muerto, H8) | S |
| `scripts/generate_report.py` + `scripts/funciones_informe.py` (roto, H8) | S |
| `backend/schemas/esquema_informe*.json` (esquema legacy sin consumidores vivos, H7) | S |
| Botón/página `/results-recharts` (duplica motor v1 con menos features, H3) | S |
| Modal "Generar v2" separado — se fusiona con el modal único | M |
| Endpoint `POST /api/reports/{tipo}` (whitelist de 3 tipos) — se reemplaza por `/api/reports/{indicator_id}` genérico | M |

### Qué se migra
| Ítem | Destino | Esfuerzo |
|---|---|---|
| Lógica de `_matches` con soporte multi-valor (`results.py`/`data.py`) | Módulo compartido `backend/rgenerator/reports/filtering.py`, usado por loader único, `results.py` y motor v1 (fix de H1) | M |
| `build_pdf_bytes` (motor v1, hoy pilotado por `indicator.pdf_layout` en BD) | Se convierte en el **fallback genérico** del renderer único, para indicadores sin `esquema.json` dedicado (mantiene flexibilidad del editor visual actual) | L |
| `report_pdl_idel_tools.py` (IDEL hardcodeado) | Se reescribe como `reports/idel_pdl/crear_informe.py` + `esquema.json`, resolviendo dimensiones por nombre en vez de ID fijo (fix de H9) | L |
| `word/engine.py` + `resumen_indicador.py` | Se mantiene, pero pasa a usar el loader único (ya casi lo hace — comparte `cargar_dataframes_indicator`) | S |
| Fluidez Lectora / Cálculo Veloz (hoy solo motor v1 genérico) | Nuevos `esquema.json` dedicados en `reports/fluidez_lectora/` y `reports/calculo_veloz/` (fix de H4) | L |
| Fix del filtro Año en DIA (H2) | Agregar parámetro + filtro en `dia/crear_informe.py`, independiente de la consolidación mayor — se puede hacer YA, sin esperar el rediseño | S |
| Campo explícito de tipo de motor en `Indicator` (fix H5) | Migración Alembic + UI de selección en vez de inferencia por nombre | M |

### Esfuerzo total estimado
- **Quick wins (hacer ya, sin esperar la consolidación)**: H2 (filtro Año DIA), H6 (org_id en `_build_records`), H8 (borrar código muerto) — todos **S**, se pueden resolver en un solo PR de 1-2 días.
- **Consolidación completa** (loader único + renderer único + esquemas para IDEL/FL/CV + UI unificada): **L**, estimado 3-4 semanas de trabajo de desarrollo enfocado, dado que implica reescribir el motor IDEL (hoy con matplotlib directo, no declarativo) y crear esquemas nuevos para FL/CV que hoy no tienen ningún informe "bonito" (dependen 100% del editor visual genérico).
- **Recomendación de secuencia**: 1) quick wins de filtros (H1, H2, H6) esta semana — resuelven directamente la queja de "los filtros no salen bien"; 2) limpieza de código muerto (H8) en paralelo, bajo riesgo; 3) diseño del esquema único y migración de IDEL/FL/CV como iniciativa separada, priorizada después de validar que los quick wins resolvieron la percepción del problema.
