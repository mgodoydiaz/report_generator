# QA — Matriz de indicadores (org 1)

- **Fecha de ejecución**: 2026-08-03T17:00:12
- **API**: `http://localhost:8000`  ·  **Usuario QA**: `qa.admin@rgenerator.local`
- **Salida**: `/app/data/output/qa_indicadores/2026-08-03`
- **Indicadores revisados**: 6

Leyenda: ✅ correcto · ⚠️ revisar (400 coherente con la cobertura de datos, o aviso menor) · ❌ falla · — no aplica.

## Tabla-resumen

| Indicador | ETL | Datos + última carga | Dashboard | Última prueba | Semestral | Anual | Personalizado | Informe especializado |
|---|---|---|---|---|---|---|---|---|
| **SIMCE** (id 1) | ✅ #14 SIMCE (IA) — last_run 2026-05-05 | ✅ 2966 filas — última eval: MAYO 2026 (prueba 1) | ✅ 18 items, 15 refs OK y con datos | ✅ 14 págs, 910 KB | ⚠️ Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador. | ✅ 5 págs, 853 KB | ✅ 5 págs, 854 KB | ✅ `simce`: 13 págs, 994 KB |
| **DIA** (id 2) | ✅ #21 DIA (IA) — last_run 2026-05-05 | ✅ 8033 filas — última eval: DIAGNOSTICO 2026 | ✅ 22 items, 19 refs OK y con datos | ✅ 3 págs, 425 KB | ⚠️ Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador. | ✅ 2 págs, 192 KB | ✅ 3 págs, 425 KB | ✅ `dia`: 44 págs, 1669 KB |
| **IDEL** (id 3) | ❌ sin pipeline asociado | ✅ 3890 filas — última eval: v3 2026 | ✅ 15 items, 9 refs OK y con datos | ✅ 2 págs, 160 KB | ✅ 2 págs, 146 KB | ✅ 2 págs, 154 KB | ✅ 2 págs, 156 KB | ✅ `pdl_idel`: 41 págs, 515 KB |
| **Cálculo Veloz** (id 4) | ❌ sin pipeline asociado | ✅ 5151 filas — última eval: OCTUBRE 2025 (prueba 2) | ✅ 23 items, 18 refs OK y con datos | ✅ 2 págs, 283 KB | ⚠️ Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador. | ⚠️ Sin datos del año en curso (2026) para este indicador. | ✅ 2 págs, 314 KB | — |
| **Fluidez Lectora** (id 5) | ❌ sin pipeline asociado | ✅ 414 filas — última eval: 13-04-2026 (prueba Ensayo 1) | ✅ 18 items, 14 refs OK y con datos | ✅ 3 págs, 226 KB | ⚠️ Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador. | ✅ 2 págs, 158 KB | ✅ 2 págs, 159 KB | — |
| **SIMCE Panguipulli** (id 6) | ✅ #26 EMN Aptus (IA) — last_run 2026-05-04 | ✅ 1875 filas — última eval: SEPTIEMBRE 2025 (prueba 4) | ✅ 12 items, 10 refs OK y con datos | ⚠️ El indicador no tiene secciones configuradas para el informe por evaluación. Agrega secciones en el Editor de Layout → pestaña Informe PDF → por evaluación. | ⚠️ Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador. | ⚠️ Sin datos del año en curso (2026) para este indicador. | ⚠️ El indicador no tiene secciones configuradas para el informe histórico. Agrega secciones en el Editor de Layout → pestaña Informe PDF → histórico. | ✅ `simce_panguipulli`: 4 págs, 640 KB |

## Hallazgos

- **[INFORME] 1 SIMCE** — el `engine` explícito de la UI desactiva el motor único: report-options anuncia motor 'custom:simce', pero el mismo período con engine='weasyprint' (lo que manda Results.jsx / GenerateReportModal.jsx) devuelve 2 págs en vez de 14: en indicators.py el módulo del motor único solo se resuelve `if modo_periodo and not engine_override`
- **[ETL] 3 IDEL** — sin asociación clara: ningún pipeline referencia sus métricas ni coincide por nombre
- **[ETL] 4 Cálculo Veloz** — sin asociación clara: ningún pipeline referencia sus métricas ni coincide por nombre
- **[ETL] 5 Fluidez Lectora** — sin asociación clara: ningún pipeline referencia sus métricas ni coincide por nombre
- **[ETL] 6 SIMCE Panguipulli** — pipeline #26 escribe métricas que este indicador no consume: metric_ids [25]
- **[CONFIG] 6 SIMCE Panguipulli** — card 'ultima_prueba' deshabilitada por falta de pdf_layout: Este informe aún no está configurado — pide a tu administrador que agregue secciones en Editor de Layout → Informe PDF → por evaluación.
- **[CONFIG] 6 SIMCE Panguipulli** — card 'semestral' deshabilitada por falta de pdf_layout: Este informe aún no está configurado — pide a tu administrador que agregue secciones en Editor de Layout → Informe PDF → histórico.
- **[CONFIG] 6 SIMCE Panguipulli** — card 'anual' deshabilitada por falta de pdf_layout: Este informe aún no está configurado — pide a tu administrador que agregue secciones en Editor de Layout → Informe PDF → histórico.
- **[CONFIG] 6 SIMCE Panguipulli** — card 'personalizado' deshabilitada por falta de pdf_layout: Este informe aún no está configurado — pide a tu administrador que agregue secciones en Editor de Layout → Informe PDF.
- **[ETL] (ninguno)** — pipeline #27 '[PRUEBA] DIA Lenguaje (IA)' sin indicador: metric_ids=[27, 28], steps=11
- **[ETL] (ninguno)** — pipeline #28 '[PRUEBA] SIMCE (IA)' sin indicador: metric_ids=[29, 30], steps=13
- **[ETL] (ninguno)** — pipeline #31 'Nuevo Proceso' sin indicador: metric_ids=[], steps=0

## Detalle por indicador

### 1 — SIMCE

- `report_engine_type`: `simce` · resuelto por la API: `simce` (origen `campo`)
- Métricas: `Resultados SIMCE por Estudiante` (id 4, 1286 filas), `Resultados SIMCE por Pregunta` (id 5, 1680 filas)
- Cobertura temporal detectada: 2025-04 → 2026-05 (6 puntos)
- Última fila cargada (`created_at`): 2026-05-05T18:14:35.312369
- Columnas temporales detectadas: anio=`Año`, mes_like=`Mes`, ordinal=`N Prueba`

**ETL** — metric_id en config_json

| Pipeline | Match | config_json | Steps | last_run |
|---|---|---|---|---|
| #14 SIMCE (IA) | metric_id | OK | 16 | 2026-05-05T18:14:35.325777 |

**Dashboard** — 18 items, 15 refs OK y con datos

_Todas las referencias existen y devuelven datos._

**Informes**

| Informe | Card disponible | HTTP | Clase | Detalle | Archivo |
|---|---|---|---|---|---|
| ultima_prueba | sí | 200 | ✅ ok | 14 págs, 910 KB | simce_ultima_prueba_lenguaje.pdf |
| semestral | NO (Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador.) | 400 | ⚠️ 400_esperado | Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador. | — |
| anual | sí | 200 | ✅ ok | 5 págs, 853 KB | simce_anual_lenguaje.pdf |
| personalizado | sí | 200 | ✅ ok | 5 págs, 854 KB | simce_personalizado_lenguaje.pdf |
| ultima_prueba (engine=weasyprint, como lo manda la UI) | sí | 200 | ✅ ok | 2 págs, 179 KB | simce_ultima_prueba_engine_weasyprint_lenguaje.pdf |
| custom:simce | — | 200 | ✅ ok | 13 págs, 994 KB | simce_custom_simce_lenguaje.pdf |

### 2 — DIA

- `report_engine_type`: `dia` · resuelto por la API: `dia` (origen `campo`)
- Métricas: `Resultados DIA por estudiante` (id 6, 5647 filas), `Resultados DIA por Pregunta` (id 7, 2386 filas)
- Cobertura temporal detectada: 2025-03 → 2026-03 (4 puntos)
- Última fila cargada (`created_at`): 2026-05-05T19:24:11.616041
- Columnas temporales detectadas: anio=`Año`, mes_like=`Hito`

**ETL** — metric_id en config_json

| Pipeline | Match | config_json | Steps | last_run |
|---|---|---|---|---|
| #21 DIA (IA) | metric_id | OK | 11 | 2026-05-05T18:42:05.464274 |

**Dashboard** — 22 items, 19 refs OK y con datos

_Todas las referencias existen y devuelven datos._

**Informes**

| Informe | Card disponible | HTTP | Clase | Detalle | Archivo |
|---|---|---|---|---|---|
| ultima_prueba | sí | 200 | ✅ ok | 3 págs, 425 KB | dia_ultima_prueba_lectura.pdf |
| semestral | NO (Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador.) | 400 | ⚠️ 400_esperado | Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador. | — |
| anual | sí | 200 | ✅ ok | 2 págs, 192 KB | dia_anual_lectura.pdf |
| personalizado | sí | 200 | ✅ ok | 3 págs, 425 KB | dia_personalizado_lectura.pdf |
| custom:dia | — | 200 | ✅ ok | 44 págs, 1669 KB | dia_custom_dia_lectura.pdf |

### 3 — IDEL

- `report_engine_type`: `null` · resuelto por la API: `pdl_idel` (origen `inferido`)
- Métricas: `Resultados IDEL` (id 8, 3890 filas)
- Cobertura temporal detectada: 2024-04 → 2026-11 (8 puntos)
- Última fila cargada (`created_at`): 2026-05-03T20:48:48.772490
- Columnas temporales detectadas: anio=`Año`, mes_like=`Version`

**ETL** — sin asociación clara

_Sin pipelines asociados._

**Dashboard** — 15 items, 9 refs OK y con datos

_Todas las referencias existen y devuelven datos._

**Informes**

| Informe | Card disponible | HTTP | Clase | Detalle | Archivo |
|---|---|---|---|---|---|
| ultima_prueba | sí | 200 | ✅ ok | 2 págs, 160 KB | idel_ultima_prueba.pdf |
| semestral | sí | 200 | ✅ ok | 2 págs, 146 KB | idel_semestral.pdf |
| anual | sí | 200 | ✅ ok | 2 págs, 154 KB | idel_anual.pdf |
| personalizado | sí | 200 | ✅ ok | 2 págs, 156 KB | idel_personalizado.pdf |
| custom:pdl_idel | — | 200 | ✅ ok | 41 págs, 515 KB | idel_custom_pdl_idel.pdf |

### 4 — Cálculo Veloz

- `report_engine_type`: `null` · resuelto por la API: `None` (origen `None`)
- Métricas: `Resultados Cálculo Veloz` (id 9, 5151 filas)
- Cobertura temporal detectada: 2025-04 → 2025-10 (7 puntos)
- Última fila cargada (`created_at`): 2026-03-23T07:00:59.248783
- Columnas temporales detectadas: anio=`Año`, mes_like=`Mes`, ordinal=`N Prueba`, fecha=`Fecha`
- Dimensiones con `data_type='date'`: `Fecha`

**ETL** — sin asociación clara

_Sin pipelines asociados._

**Dashboard** — 23 items, 18 refs OK y con datos

_Todas las referencias existen y devuelven datos._

**Informes**

| Informe | Card disponible | HTTP | Clase | Detalle | Archivo |
|---|---|---|---|---|---|
| ultima_prueba | sí | 200 | ✅ ok | 2 págs, 283 KB | calculo_veloz_ultima_prueba.pdf |
| semestral | NO (Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador.) | 400 | ⚠️ 400_esperado | Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador. | — |
| anual | NO (Sin datos del año en curso (2026) para este indicador.) | 400 | ⚠️ 400_esperado | Sin datos del año en curso (2026) para este indicador. | — |
| personalizado | sí | 200 | ✅ ok | 2 págs, 314 KB | calculo_veloz_personalizado.pdf |

### 5 — Fluidez Lectora

- `report_engine_type`: `null` · resuelto por la API: `None` (origen `None`)
- Métricas: `Resultados Fluidez Lectora` (id 10, 414 filas)
- Cobertura temporal detectada: 2026-04 → 2026-04 (1 puntos)
- Última fila cargada (`created_at`): 2026-05-04T04:22:19.701681
- Columnas temporales detectadas: mes_like=`Fecha`, ordinal=`N Prueba`, fecha=`Fecha`
- Dimensiones con `data_type='date'`: `Fecha`

**ETL** — sin asociación clara

_Sin pipelines asociados._

**Dashboard** — 18 items, 14 refs OK y con datos

_Todas las referencias existen y devuelven datos._

**Informes**

| Informe | Card disponible | HTTP | Clase | Detalle | Archivo |
|---|---|---|---|---|---|
| ultima_prueba | sí | 200 | ✅ ok | 3 págs, 226 KB | fluidez_lectora_ultima_prueba.pdf |
| semestral | NO (Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador.) | 400 | ⚠️ 400_esperado | Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador. | — |
| anual | sí | 200 | ✅ ok | 2 págs, 158 KB | fluidez_lectora_anual.pdf |
| personalizado | sí | 200 | ✅ ok | 2 págs, 159 KB | fluidez_lectora_personalizado.pdf |

### 6 — SIMCE Panguipulli

- `report_engine_type`: `null` · resuelto por la API: `simce_panguipulli` (origen `inferido`)
- Métricas: `Resultados SIMCE Panguipulli por Estudiante` (id 24, 1695 filas), `Resultados SIMCE Panguipulli por Habilidad` (id 26, 180 filas)
- Cobertura temporal detectada: 2025-04 → 2025-09 (4 puntos)
- Última fila cargada (`created_at`): 2026-05-04T14:24:16.982906
- Columnas temporales detectadas: anio=`Año`, mes_like=`Mes`, ordinal=`N Prueba`

**ETL** — metric_id en config_json

| Pipeline | Match | config_json | Steps | last_run |
|---|---|---|---|---|
| #26 EMN Aptus (IA) | metric_id | OK | 19 | 2026-05-04T14:24:16.988578 |

**Dashboard** — 12 items, 10 refs OK y con datos

_Todas las referencias existen y devuelven datos._

**Informes**

| Informe | Card disponible | HTTP | Clase | Detalle | Archivo |
|---|---|---|---|---|---|
| ultima_prueba | NO (Este informe aún no está configurado — pide a tu administrador que agregue secciones en Editor de Layout → Informe PDF → por evaluación.) | 422 | ⚠️ 400_esperado | El indicador no tiene secciones configuradas para el informe por evaluación. Agrega secciones en el Editor de Layout → pestaña Informe PDF → por evaluación. | — |
| semestral | NO (Este informe aún no está configurado — pide a tu administrador que agregue secciones en Editor de Layout → Informe PDF → histórico.) | 400 | ⚠️ 400_esperado | Sin datos del 2º semestre 2026 (agosto–diciembre) para este indicador. | — |
| anual | NO (Este informe aún no está configurado — pide a tu administrador que agregue secciones en Editor de Layout → Informe PDF → histórico.) | 400 | ⚠️ 400_esperado | Sin datos del año en curso (2026) para este indicador. | — |
| personalizado | NO (Este informe aún no está configurado — pide a tu administrador que agregue secciones en Editor de Layout → Informe PDF.) | 422 | ⚠️ 400_esperado | El indicador no tiene secciones configuradas para el informe histórico. Agrega secciones en el Editor de Layout → pestaña Informe PDF → histórico. | — |
| custom:simce_panguipulli | — | 200 | ✅ ok | 4 págs, 640 KB | simce_panguipulli_custom_simce_panguipulli_historia.pdf |

## PDFs generados

| Archivo | Páginas | Tamaño |
|---|---|---|
| `simce_ultima_prueba_lenguaje.pdf` | 14 | 910.6 KB |
| `simce_anual_lenguaje.pdf` | 5 | 853.9 KB |
| `simce_personalizado_lenguaje.pdf` | 5 | 854.5 KB |
| `simce_ultima_prueba_engine_weasyprint_lenguaje.pdf` | 2 | 179.1 KB |
| `simce_custom_simce_lenguaje.pdf` | 13 | 994.8 KB |
| `dia_ultima_prueba_lectura.pdf` | 3 | 426.0 KB |
| `dia_anual_lectura.pdf` | 2 | 192.7 KB |
| `dia_personalizado_lectura.pdf` | 3 | 425.8 KB |
| `dia_custom_dia_lectura.pdf` | 44 | 1669.8 KB |
| `idel_ultima_prueba.pdf` | 2 | 160.5 KB |
| `idel_semestral.pdf` | 2 | 146.0 KB |
| `idel_anual.pdf` | 2 | 154.6 KB |
| `idel_personalizado.pdf` | 2 | 156.0 KB |
| `idel_custom_pdl_idel.pdf` | 41 | 515.6 KB |
| `calculo_veloz_ultima_prueba.pdf` | 2 | 283.7 KB |
| `calculo_veloz_personalizado.pdf` | 2 | 314.1 KB |
| `fluidez_lectora_ultima_prueba.pdf` | 3 | 226.4 KB |
| `fluidez_lectora_anual.pdf` | 2 | 158.7 KB |
| `fluidez_lectora_personalizado.pdf` | 2 | 159.0 KB |
| `simce_panguipulli_custom_simce_panguipulli_historia.pdf` | 4 | 640.4 KB |

## Pipelines sin indicador asociado

| Pipeline | metric_ids | Steps | last_run |
|---|---|---|---|
| #27 [PRUEBA] DIA Lenguaje (IA) | [27, 28] | 11 | 2026-05-04T22:49:44.230174 |
| #28 [PRUEBA] SIMCE (IA) | [29, 30] | 13 | 2026-05-05T00:01:41.250336 |
| #31 Nuevo Proceso | — | 0 | — |
