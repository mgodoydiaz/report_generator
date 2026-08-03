# Estado del proyecto y pendientes

**Última actualización**: 2026-07-31 · **Versión desplegada**: `v0.7.0` (commit `167cf5a`) · **Producción**: Railway + Supabase `us-east-1`, operativa y verificada.

> **En `dev`, sin commitear y sin mergear**: el P0 de autorización por rol y el fix del falso "guardado" del frontend (ver §2.5). Requieren GO explícito para pasar a `main`.

Documento vivo. Complementa a [ROADMAP.md](../ROADMAP.md) (backlog histórico) y a [diagnostico_general_2026-07-30.md](./reportes/diagnostico_general_2026-07-30.md) (estado por área).

---

## 1. Qué se hizo en v0.7.0

### Descarga de informes (el objetivo del sprint)

| Cambio | Detalle |
|---|---|
| **Selector por períodos** | 4 tarjetas: última prueba / semestral / anual / personalizado. El personalizado abre un panel con filtros por dimensión y rango de meses. Resolver en `backend/rgenerator/reports/periodos.py` con semántica escolar chilena (1er semestre ene–jul). |
| **Registro de informes Python** | `backend/rgenerator/reports/custom/` con auto-descubrimiento: un informe nuevo = un archivo `.py`. Endpoint `POST /api/reports/custom/{nombre}`. Ver el README de esa carpeta. |
| **Asignatura obligatoria** | Cuando un indicador tiene ≥2 asignaturas, el informe exige elegir una (chip heredado del dashboard o selector en el modal). Se eliminó el default silencioso a "LENGUAJE". |
| **Motor único — piloto SIMCE** | `custom/simce.py` con 4 modos, helpers compartidos en `custom/_secciones.py`, despacho desde `export-pdf` con fallback al motor v1. Retrocompatibilidad del formato oficial verificada byte a byte. |
| **Riesgo persistente** | Sección al final del informe anual: el par de evaluaciones debe incluir la última del período; los que dejaron de rendir van en tabla aparte. Indica cuál fue la última evaluación considerada. |
| **Word** | Retirado del selector por decisión de producto (los endpoints y el registro siguen intactos, listos para reactivar). |

### Calidad visual de los informes (QA de 15 P0 + gate del piloto)

- Filtros sin datos → **400 accionable** en vez de PDF vacío con apariencia legítima.
- Los errores de sección ya no imprimen tracebacks dentro del PDF.
- `nan` → `—` en todas las tablas; números a 2 decimales (esto además resolvió el desborde de márgenes: las celdas traían artefactos tipo `0.5700000000000001`).
- Conteos de alumnos por estudiante único (antes sumaban filas de la métrica de preguntas).
- Orden temporal cronológico en gráficos; preguntas en orden numérico (antes 1, 10, 11… 2).
- Período compuesto (Año + Hito): el DIA sin filtros ya no mezcla 2025 con 2026.
- Contraste WCAG en etiquetas sobre segmentos claros.
- **Pie izquierdo = nombre de la organización** en todos los motores (denylist + fallback + script de limpieza de DB).

### Datos e ingesta

| Cambio | Detalle |
|---|---|
| **`Nombre` / `Nombre_Norm`** | El pipeline creaba solo la columna normalizada. Ahora toda carga deja ambas, en los 4 caminos de escritura (pipelines, import de /values, alta manual, API de ingesta). |
| **`EnrichWithLookup`** | Con llave homónima (`left_on == right_on`) pandas colapsa las columnas y el step borraba la llave: así se perdió la dimensión `Pregunta` en SIMCE mayo 2026. Corregido + pipeline blindado. |
| **Guard de cobertura 0%** | Si una carga deja una dimensión asociada completamente vacía, se emite un aviso (habría cazado el bug anterior el mismo día). |
| **Backfill en producción** | 359 nombres copiados + 17.048 normalizados + 260 filas con su dimensión `Pregunta` restaurada. |

### Plataforma

- **Filtros server-side en `/values`**: filtros por dimensión + búsqueda con debounce sobre la query paginada, endpoint de facetas, y `ORDER BY` que faltaba (la paginación podía repetir filas).
- **Tipo de dimensión `date`**: el resolver deriva año y mes desde una columna de fecha. Fluidez Lectora pasó de 2/5 a 4/5 informes disponibles.
- **Organización de prueba "Colegio Demo"** (`scripts/crear_org_demo.py`): datos sintéticos con casos borde sembrados, para probar sin tocar datos reales.
- **1.566 tests** automatizados en verde.

### Documentación

- [Guía rápida de usuario](./tutoriales/guia_rapida_usuario.md) (+ Word con la plantilla personal) — 4 pasos con capturas reales, lenguaje revisado para usuario no técnico.
- [Anexo de carga por evaluación](./tutoriales/anexo_carga_pipelines.md) — un capítulo por pipeline.
- [Mapa de la aplicación](./desarrollo/mapa_aplicacion.md), [inventario de indicadores](./desarrollo/inventario_indicadores_2026-07-30.md), [plan del motor único](./desarrollo/plan_motor_unico_informes.md), [contrato técnico](./desarrollo/contrato_motor_unico.md), [fichas por indicador](./desarrollo/fichas_informes_por_indicador.md).

---

## 2. Pendientes

Prioridad: **P0** bloquea uso · **P1** visible y serio · **P2** pulido.

### 2.0 QA masivo con agentes (2026-08-03) — puntajes y hallazgos

Se corrió un QA integral de los 6 indicadores de la org 1 con verificación numérica independiente (SQL contra `metric_data`). Artefactos: matriz por indicador (`docs/reportes/qa_matriz_indicadores_2026-08-03.md`, script reutilizable `scripts/qa_matriz_indicadores.py`), críticas por informe (`docs/reportes/qa_informes_2026-08-03/*.md`), dashboards (`docs/reportes/qa_dashboards_2026-08-03.md`), mapa de capas de layout (`docs/desarrollo/mapa_capas_layout.md`), índice visual (`data/output/qa_indicadores/2026-08-03/index.html`).

| Indicador | Informes /100 | Dashboard /100 |
|---|---:|---:|
| SIMCE | 72 | 49 |
| Cálculo Veloz | 69 | 72 |
| Fluidez Lectora | 67 | 80 |
| IDEL | 63 | 25 |
| SIMCE Panguipulli | 62 | 64 |
| DIA | 54 | 44 |

**Conclusión transversal**: la aritmética de agregación es exacta en los 6 (0 discrepancias en ~100 recálculos SQL); los defectos son semánticos — resolución de períodos anclada al calendario, identidad de estudiantes (filas contadas como personas, anónimos descartados), roles/valores de columna desalineados (`Versión` "1/2/3" vs specs "v1/v2/v3", rol `logro_1` sin definir en IDEL), colores por índice sin `color_overrides` (semáforos invertidos en SIMCE y Panguipulli), y órdenes alfabéticos donde van cronológicos.

**Pre-requisitos de la fase 4 identificados por el QA** (cerrar antes de portar módulos): identidad DIA (375 filas Panguipulli sin nombre), fusión de establecimientos homónimos (`I D`/`II D` en dos colegios sin campo `Establecimiento` en informes), ~~anclaje del resolver de períodos~~ (✅ hecho), y extraer el esqueleto común de `simce.py` a un módulo parametrizado — GO de Miguel 2026-08-03.

**Fixes aplicados el 2026-08-03** (en `dev`, tras el QA; suite 1746 verde, build OK):

| Fix | Efecto verificado |
|---|---|
| UI dejaba de usar el motor único (`engine: 'weasyprint'` forzado) | SIMCE por UI: 183 KB → 983 KB (informe completo). Selector explícito del modal sigue funcional |
| Resolver de períodos anclado a la última evaluación con datos | Semestral/anual pasan de fallar en 5/6 a resolver en todos; período efectivo rotulado ("Evolución del año 2025") |
| **Tarjeta semestral retirada** (decisión de producto: ≈ anual tras el anclaje) | 3 tarjetas; API `tipo:"semestral"` sigue viva (patrón Word, reactivable) |
| Specs IDEL `v1/v2/v3` → `1/2/3` (decisión de Miguel; script `fix_specs_version_idel.py`) | Dashboard IDEL revive: 3.890 evaluaciones visibles, roster poblado, matriz de transición 4×4 |
| Semáforos por índice sin `color_overrides` — eran **10 specs en 4 indicadores** (script `fix_semaforo_color_overrides.py`) | Insuficiente rojo / Adecuado verde, desde `achievement_levels` |
| Rol `logro_1` faltante en IDEL (script `fix_column_roles_idel.py`) | PDF v1: etiquetas `0.0` → `21.5` (verificado por OCR); tabla resumen deja de decir "Sin datos" |
| Token `habilidad_prueba` en esquema Panguipulli | Gráfico de habilidades: promedio anual → prueba del informe (46.4% → 55.95% en el caso medido) |
| Orden temporal declarado (`temporal_config`) en gráficos y tablas del motor v1 | Meses cronológicos (CV) e hitos DIAGNÓSTICO→INTERMEDIO→CIERRE (DIA), antes alfabéticos |
| Página en blanco al cambiar a indicador con menos tabs | Reset/clamp del tab activo, barrido por los 6 indicadores |
| Tests deterministas de fecha (`periodos.hoy()` congelable) | La suite ya no se rompe al cruzar semestres |

Los 3 scripts de configuración (semáforos, rol IDEL, specs Versión) son org-scoped, idempotentes, con dry-run — **pendientes de correr en producción con GO de Miguel**. Pendientes menores nuevos: 2 textos de display en DB aún dicen "v1, v2, v3" (description del spec 141 y nota del tab Tendencia); `derived_columns` de CV tiene un `slope` ordinal sin `ordinal_levels` (error tragado en silencio); decisión aparcada: filtro de tablas "Estudiantes en Riesgo" (propuesta de Miguel: bajo el primer cuartil); revisar en producción si IDEL 2026 v2/v3 son clones de 2025 como en dev.

### 2.1 Motor único — fases 4 y 5 (el trabajo grande que sigue)

| # | Pendiente | Notas |
|---|---|---|
| — | **Fase 4: migrar los 5 indicadores restantes** | Orden acordado: DIA → IDEL (base `scripts/report_pdl_idel.py`) → Panguipulli → Cálculo Veloz → Fluidez Lectora. Cada uno con QA visual como gate. Contrato y fichas ya están escritos: se codifica sin decisiones abiertas. |
| — | **Fase 5: deprecar el motor v1** | Retirar el fallback de las tarjetas, smoke tests por modo, actualizar docs. |
| P1 | Panguipulli muestra 0/4 tarjetas de período | Correcto hasta que tenga su módulo (fase 4). |
| P1 | Crear pestaña de Tendencia en el dashboard de Fluidez Lectora | Decisión 14 de las fichas: hoy las secciones de evolución de su informe no tienen fuente en el dashboard. |
| P2 | `report_engine_type` de CV y FL sin setear | Se setea cuando tengan módulo. |

### 2.2 Calidad de informes (del QA y la comparación con la referencia)

| # | Pendiente | Notas |
|---|---|---|
| P1 | Estadística por Pregunta: columnas A–E muestran proporciones (`0.57`) donde la referencia muestra conteos (`62`) | **Dato de origen**, no del motor. Bloquea que el motor reemplace del todo al informe LaTeX histórico. |
| P1 | Encabezado SIMCE incompleto | Faltan `N° 1` y `2° Medio`; el subtítulo dice "Resumen de la prueba" donde la referencia pone el nombre del colegio. |
| P1 | Habilidad y Eje Temático en orden alfabético | Debería ser orden curricular; además cambia el color de cada categoría respecto de la referencia. |
| P1 | `#ea580c` (Alto Riesgo, DIA) no alcanza contraste 4.5:1 con ningún color de texto | Límite de la paleta — decisión de diseño pendiente. |
| P2 | Falta el heatmap verde/amarillo en la tabla de estadística | Presente en la referencia de Pullinque. |
| P2 | Gráficos de "Evolución por Mes" con un solo mes filtrado | Degeneran a una serie única redundante; candidatos a auto-omitirse. |
| P2 | Fluidez Lectora describe el período como "06 2025" | Debería decir "JUNIO 2025": formateo del mes derivado de la columna fecha. |
| P2 | Tabla secundaria de riesgo persistente a 7 pt | La principal quedó a 8 pt; la secundaria bajó un escalón. |
| P2 | Eje X de gráficos de **tendencia** colapsa el mismo hito de años distintos | Distinto del filtro snapshot (ya corregido); cambiarlo afecta las tendencias de SIMCE/FL/CV, requiere decisión. |

### 2.3 Word (descopeado — retomar al final del proyecto)

Los endpoints y el registro siguen vivos; solo se retiraron las tarjetas del selector. Al retomar hay 4 defectos conocidos:

- **P0** La métrica se elige por lista fija y toma `Logro`, que en SIMCE es categórico → `N=0`, promedio vacío, gráfico en blanco (la numérica es `Rend`).
- **P0** Formato `%` incondicional produce valores absurdos (`15510.5%`).
- **P0** La plantilla `.docx` contiene un párrafo "GUÍA (borrar en la versión final)" que sale en todos los documentos.
- **P1** Los `.docx` no llevan encabezado ni pie con el nombre de la organización.

### 2.4 Datos e ingesta

| # | Pendiente | Notas |
|---|---|---|
| P1 | **583 filas sin identidad en producción** (576 DIA + 7 Panguipulli) | **Hipótesis de carga duplicada DESMENTIDA por el QA 2026-08-03**: 0 colisiones por `Nombre_Norm`, los `Logro` no se solapan — son **375 alumnos de Panguipulli cargados sin nombre** (el cohorte LECTURA·DIAGNÓSTICO·2026). No inflan conteos: los **desinflan en el motor v1** (`report_steps.py:1356` descarta identidades `None` en cursos mixtos → "Alumnos=26" junto a niveles que suman 56). Acción correcta: recuperar identidades desde los archivos fuente, no des-duplicar. |
| P1 | `RequestUserFiles` consume en silencio archivos residuales de `data/pipeline_runs/uploads/` | Un usuario puede cargar datos viejos sin darse cuenta (ya ocurrió durante las pruebas). Falta limpiar residuos y pedir confirmación antes de reutilizar. |
| P1 | El aviso de "columna esperada llegó vacía" no se muestra en pantalla | El backend lo emite y lo devuelve en la respuesta, pero `PipelineExecutionModal.jsx` no lo renderiza. Mejora barata y de alto valor. |
| P1 | `Numero Lista` ausente en las cargas 2026 | El XLS trae "Número de Lista" (con tilde) y la métrica declara "Numero Lista". Misma familia de bugs que `Nombre` y `Pregunta`. |
| P2 | El `config_json` del pipeline 14 no reproduce la corrida de mayo | El Curso guardado es `II C` y el step genera `2C`; los % A–E quedaron divididos por 100 sin que ningún step lo haga. Revisar **antes de la próxima carga SIMCE**. |
| P2 | Pipeline EMN Aptus sin `description` en sus `file_specs` | Los tres recuadros de carga muestran el texto genérico en vez de decir qué archivo va. |
| P2 | `data/input/Lenguaje/inputs/habilidades_lenguaje.xlsx` desactualizado | Tiene columnas `N°`/`Habilidad`; el pipeline hoy exige `Pregunta`, `Habilidad` y `Eje Temático`. |

### 2.5 Seguridad y arquitectura

| # | Pendiente | Notas |
|---|---|---|
| ~~P0~~ | ~~**Autorización laxa en los routers de dominio**~~ · **RESUELTO en `dev` el 2026-07-31, pendiente de merge** | Se creó `require_editor` en `backend/auth.py` y se aplicó control de rol a **45 endpoints de escritura** en 11 routers: 35 con `require_editor` y 10 con `require_admin` (borrado de métrica/indicador/dimensión/pipeline, `metrics/clear`, `metrics/data/batch-delete`, `data-ops/replace` y `recalculate`, assets de organización). Quedan deliberadamente en `get_current_user` 8 endpoints que son **lecturas con POST** (los 3 `preview`, `data-ops/distinct`, `indicators/export-pdf` y los 3 de `reports`): un `viewer` debe poder previsualizar y descargar informes. `require_admin` ahora acepta también superadmin, para no degradar el `_check_admin` que vivía en el cuerpo de `organizations.py`. Verificado con 145 tests nuevos de matriz de roles + smoke sobre la app levantada. `ingest.py` se auditó aparte: sin hallazgos altos ni medios. |
| P1 | P1s del QA maestro sin cerrar | Páginas que tragan errores de API — **parcialmente resuelto** (ver fila siguiente); 5 archivos con cliente HTTP propio sin manejo de 401; estados vacíos engañosos; ReDoS en `/data-ops/replace`; XSS por SVG en assets; `except: pass` en `SaveToMetric`. |
| ~~P0~~ | ~~**Falso "guardado" ante cualquier error de API**~~ · **RESUELTO en `dev` el 2026-07-31, pendiente de merge** | Hallazgo del smoke del P0 anterior, y más grave que él: 12 archivos del frontend hacían `if (result.error) throw` sin comprobar `response.ok`. Como FastAPI responde `{"detail": ...}` y no `{"error": ...}`, la condición nunca se cumplía y la app mostraba **"Guardado" ante un 403, 401, 400 o 500**, cerrando el modal como si hubiera funcionado. Se agregó el helper `frontend/src/tooling/apiError.js` y se aplicó en los 12 archivos. De paso se eliminaron dos *mocks de éxito* heredados: `NewIndicatorDrawer` fabricaba un indicador falso con `id: Date.now()` ante cualquier error, e `Indicators.jsx` mostraba "Indicador eliminado (Mocked)" borrando de la vista un indicador que seguía existiendo. |
| P2 | `/results-recharts` es una ruta huérfana | Dashboard legacy con lógica duplicada, alcanzable solo tecleando la URL. Candidata a eliminarse. |
| P2 | `/live-tracking` es un placeholder comercial | No hace tracking de nada. |

### 2.6 UX y funcionalidades

| # | Pendiente | Notas |
|---|---|---|
| P2 | Selector de rango de fechas en el modal cuando la dimensión es tipo `date` | El backend ya está listo (`data_type` viaja en `dimensiones_filtrables`); falta la UI. |
| P2 | El botón **Exportar** de `/values` ignora los filtros activos | Exporta la métrica completa. |
| P2 | Comparativa de establecimientos (DIA) | Decidido: gráfico aparte, **no** dentro del PDF por colegio. |
| P2 | Ocultar o deshabilitar los botones de escritura para el rol `viewer` | Hoy un viewer ve "Nueva Dimensión", "Editar" y "Eliminar" en todas las páginas; al usarlos recibe un 403 con mensaje claro (ya no un falso éxito), pero es ruido evitable. Cosmético: el backend ya está blindado. |
| P2 | 6 tests de frontend rotos en `tests/frontend/dataProcessing.test.js` | Preexistentes y ajenos al sprint de autorización: llaman a `processDataForDashboard` con una firma que ya no coincide y revientan en `dataProcessing.js:229` (`data[mid]` con `data` undefined). Los otros 29 tests de frontend pasan. |

### 2.7 Documentación y operación

| # | Pendiente | Notas |
|---|---|---|
| P1 | **3 placeholders `### COMPLETAR POR MIGUEL ###`** en el anexo de cargas | (a) qué hace el usuario cuando cambie el año, ya que DIA lo tiene fijo en 2026; (b) de qué menú de la plataforma DIA se descargan sus dos archivos; (c) cómo llegan los tres informes de Aptus al colegio. |
| P2 | Falta un informe de referencia aprobado de **DIA** | Ya tenemos SIMCE Pullinque e IDEL Panguipulli en `Desktop\PDF_test\referencias\`. |
| P2 | Guiones de QA manual `g2`–`g4` desactualizados | Mencionan botones "v1/v2" que el selector unificado ya reemplazó. |
| P2 | `.githooks/pre-push` no es ejecutable | Git lo ignora en cada push (`chmod +x` lo arregla). |
| P2 | Mantener `.env.railway` como espejo fiel de Railway | Ya se corrigieron `DATABASE_URL` y `JWT_SECRET`; conviene no dejarlo envejecer, o dejar de mantener copia local. |

---

## 3. Esquema de ramas

**Limpieza hecha el 2026-07-31**: se eliminaron las 12 ramas obsoletas (`dev2`, `dev3`, `dev_1`, `dev_pdfs`, `devtest`, `implementar_docker`, `claude/agitated-diffie`, `feat/pdf-engine-fidel-latex` y las 4 `feature/*`). Antes de borrar se verificó con `git rev-list --count main..<rama>` que **las 14 tenían 0 commits fuera de main** — no se perdió nada. Los tags (`v0.7.0` y anteriores) siguen intactos y apuntan a su historia.

```
main ──────────────────────────────► PRODUCCIÓN (Railway auto-deploy)
  ▲
  │  merge con GO explícito de Miguel
  │
dev ─── rama de trabajo ÚNICA
```

| Rama | Rol |
|---|---|
| `main` | Producción. Railway auto-deploya. Solo se mergea con GO explícito. |
| `dev` | Desarrollo. **Trabajar siempre aquí.** |

Esto restablece la convención original de [CLAUDE.md](../CLAUDE.md), de la que nos habíamos desviado con las ramas integradoras `dev2`/`dev3`. Para trabajo experimental que no deba tocar `dev`, crear una `feature/*` puntual y borrarla al mergear.

---

## 4. Checklist de despliegue (para futuros releases)

El contenedor corre `alembic upgrade head` al arrancar, así que las migraciones son automáticas. Los scripts de datos/config son manuales, **siempre con dry-run antes del `--apply`**:

1. `scripts/db_seed.py export` — respaldo previo.
2. `scripts/limpiar_left_footer_legacy.py` — pie legacy en layouts.
3. `scripts/fix_layout_historico_fl.py` — alias `_evaluacion` roto.
4. `scripts/marcar_dimensiones_fecha.py --org N` — tipo `date`.
5. `scripts/backfill_nombre_columnas.py --org N` — pares Nombre/Nombre_Norm.
6. `scripts/fix_lookup_pregunta_pipeline_simce.py` + `scripts/reparar_pregunta_simce_2026.py` — si aplica.

Todos son idempotentes y org-scoped. Los pasos 2–6 **ya se aplicaron** en producción el 2026-07-30.
