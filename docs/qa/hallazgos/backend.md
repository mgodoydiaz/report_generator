# Auditoría backend HTTP — Report Generator

Fecha: 2026-07-22 · Rama auditada: `dev3` · Alcance: `backend/api.py`, `backend/auth.py`,
`backend/models.py`, `backend/database.py`, `backend/config.py`, `backend/api_keys.py`,
`backend/auditing.py`, `backend/rate_limit.py`, todos los `backend/routers/*.py` (17 routers
montados en `api.py`) y los módulos de `backend/rgenerator/` que esos routers invocan
directamente para resolver datos multi-tenant (`core/report_steps.py`, `reports/data.py`).

No se modificó código ni se hicieron operaciones git. Este documento es el único entregable.

---

## 1. Inventario de endpoints

Convención de columnas: **Auth** = mecanismo de autenticación · **org_id** = si la query
filtra explícitamente por la organización del actor · **Rol** = rol mínimo requerido.

### `backend/routers/auth.py` — prefix `/api/auth`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| POST | `/login` | Ninguna (pública, con rate-limit) | N/A | — |
| GET | `/me` | JWT | N/A (usa el propio user) | cualquiera |

### `backend/routers/users.py` — prefix `/api/users`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/` | JWT | Sí | cualquiera (misma org) |
| POST | `/` | JWT | Sí (hereda org del admin) | admin |
| PUT | `/{user_id}` | JWT | Sí | admin |
| DELETE | `/{user_id}` | JWT | Sí | admin (no auto-borrarse) |

### `backend/routers/superadmin.py` — prefix `/api/superadmin`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/organizations` | JWT | N/A (cross-org intencional) | superadmin |
| POST | `/organizations` | JWT | N/A | superadmin |
| PUT | `/organizations/{org_id}` | JWT | N/A | superadmin |
| DELETE | `/organizations/{org_id}` | JWT | N/A | superadmin |
| GET | `/organizations/{org_id}/users` | JWT | N/A | superadmin |
| GET | `/users` | JWT | N/A (todas las orgs) | superadmin |
| POST | `/organizations/{org_id}/users` | JWT | N/A | superadmin |
| PUT | `/users/{user_id}` | JWT | N/A (puede reasignar org) | superadmin |
| DELETE | `/users/{user_id}` | JWT | N/A | superadmin |

### `backend/routers/organizations.py` — prefix `/api/organizations`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/{org_id}/assets` | JWT | Sí (`user.org_id==org_id` o superadmin) | cualquiera |
| POST | `/{org_id}/assets` | JWT | Sí (ídem) | admin/superadmin |
| GET | `/{org_id}/assets/{asset_id}/download` | JWT | Sí (ídem) | cualquiera |
| DELETE | `/{org_id}/assets/{asset_id}` | JWT | Sí (ídem) | admin/superadmin |

### `backend/routers/pipelines.py` — prefix `/api/pipelines`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/` y `` (alias) | JWT | Sí | cualquiera |
| POST | `/{id}/upload` | JWT | Sí | cualquiera |
| POST | `/{id}/run` | JWT | Sí (al crear runner) | cualquiera |
| POST | `/{id}/input` | JWT | Sí (runner ya scoped) | cualquiera |
| POST | `/{id}/step` | JWT | Sí (al crear runner) | cualquiera |
| POST | `/{id}/reset` | JWT | N/A (runner keyed por user_id) | cualquiera |
| GET | `/{id}/artifact/{key}` | JWT | N/A (runner keyed por user_id) | cualquiera |
| GET | `/{id}/artifact/{key}/preview` | JWT | N/A (ídem) | cualquiera |
| GET | `/{id}/config` | JWT | Sí | cualquiera |
| POST | `/config` | JWT | Sí | cualquiera |
| POST | `/{id}/config` | JWT | Sí | cualquiera |
| PATCH | `/{id}/hidden` | JWT | Sí | cualquiera |
| DELETE | `/{id}` | JWT | Sí | cualquiera |

### `backend/routers/specs.py` — prefix `/api/specs`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/` y `` (alias) | JWT | Sí | cualquiera |
| GET | `/{id}/config` | JWT | Sí | cualquiera |
| POST | `/config` | JWT | Sí | cualquiera |
| POST | `/{id}/config` | JWT | Sí | cualquiera |
| POST | `/{id}/duplicate` | JWT | Sí | cualquiera |
| DELETE | `/{id}` | JWT | Sí | cualquiera |

### `backend/routers/dimensions.py` — prefix `/api/dimensions`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/` | JWT | Sí | cualquiera |
| POST | `/` | JWT | Sí | cualquiera |
| PUT | `/{dim_id}` | JWT | Sí | cualquiera |
| DELETE | `/{dim_id}` | JWT | Sí | cualquiera |
| GET | `/{dim_id}/values` | JWT | Sí (vía dim) | cualquiera |
| POST | `/{dim_id}/values` | JWT | Sí (vía dim) | cualquiera |
| DELETE | `/values/{val_id}` | JWT | Sí (vía dim padre) | cualquiera |

### `backend/routers/metrics.py` — prefix `/api/metrics`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/` | JWT | Sí | cualquiera |
| POST | `/` | JWT | Sí (+ valida dimension_ids) | cualquiera |
| PUT | `/{id}` | JWT | Sí | cualquiera |
| DELETE | `/{id}` | JWT | Sí | cualquiera |
| GET | `/{id}/data` | JWT | Sí (vía metric) | cualquiera |
| POST | `/{id}/data` | JWT | Sí (vía metric) | cualquiera |
| POST | `/{id}/clear` | JWT | Sí (vía metric) | cualquiera |
| DELETE | `/data/{data_id}` | JWT | Sí (vía metric padre) | cualquiera |
| PUT | `/data/{data_id}` | JWT | Sí (vía metric padre) | cualquiera |
| POST | `/data/batch-delete` | JWT | Sí (whitelist de metric_ids de la org) | cualquiera |
| GET | `/{id}/export` | JWT | Sí (metric) — **Dimension.in_ sin org_id (ver H-06)** | cualquiera |
| GET | `/{id}/distinct/{column}` | JWT | Sí (metric) — ídem | cualquiera |
| GET | `/{id}/template` | JWT | Sí (metric) — ídem | cualquiera |
| POST | `/{id}/import` | JWT | Sí (metric) — ídem | cualquiera |

### `backend/routers/indicators.py` — prefix `/api/indicators`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/export-pdf/engines` | JWT | N/A | cualquiera |
| GET | `/` | JWT | Sí | cualquiera |
| POST | `/` | JWT | Sí (+ valida metric_ids) | cualquiera |
| PUT | `/{id}` | JWT | Sí | cualquiera |
| POST | `/{id}/layout` | JWT | Sí | cualquiera |
| POST | `/{id}/export-pdf` | JWT | Sí (indicador) — **MetricData sin org_id downstream (H-05)** | cualquiera |
| DELETE | `/{id}` | JWT | Sí | cualquiera |

### `backend/routers/results.py` — prefix `/api/results`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/indicator/{id}/data` | JWT | Sí (indicador) — **Metric/Dimension/MetricData descendientes sin org_id (H-05)** | cualquiera |

### `backend/routers/reports.py` — prefix `/api/reports`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/tipos` | JWT | N/A | cualquiera |
| GET | `/charts` | JWT | N/A | cualquiera |
| GET | `/tablas` | JWT | N/A | cualquiera |
| GET | `/word/informes` | JWT | N/A | cualquiera |
| GET | `/word/informes/{nombre}/placeholders` | JWT | N/A | cualquiera |
| POST | `/word/{nombre}` | JWT | Sí (`cargar_dataframes_indicator`) — **bug NameError (H-01)** | cualquiera |
| POST | `/{tipo}` | JWT | Sí (`cargar_dataframes_indicator`) | cualquiera |

### `backend/routers/tables.py` — prefix `/api/tables`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/` | JWT | Sí | cualquiera |
| POST | `/` | JWT | Sí | cualquiera |
| GET | `/{id}` | JWT | Sí | cualquiera |
| PUT | `/{id}` | JWT | Sí | cualquiera |
| DELETE | `/{id}` | JWT | Sí | cualquiera |
| POST | `/{id}/duplicate` | JWT | Sí | cualquiera |
| GET | `/{id}/data` | JWT | Sí (metric validado dentro) | cualquiera |
| POST | `/preview` | JWT | Sí | cualquiera |
| GET | `/{id}/export-pivot` | JWT | Sí | cualquiera |

### `backend/routers/charts.py` — prefix `/api/charts`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/types` | JWT | N/A | cualquiera |
| GET | `/` | JWT | Sí | cualquiera |
| POST | `/` | JWT | Sí | cualquiera |
| GET | `/{id}` | JWT | Sí | cualquiera |
| PUT | `/{id}` | JWT | Sí | cualquiera |
| DELETE | `/{id}` | JWT | Sí | cualquiera |
| POST | `/{id}/duplicate` | JWT | Sí | cualquiera |
| GET | `/{id}/data` | JWT | Sí | cualquiera |
| POST | `/preview` | JWT | Sí | cualquiera |

### `backend/routers/mappings.py` — prefix `/api/mappings`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/` | JWT | Sí | cualquiera |
| POST | `/` | JWT | Sí | cualquiera |
| GET | `/{id}` | JWT | Sí | cualquiera |
| PUT | `/{id}` | JWT | Sí | cualquiera |
| DELETE | `/{id}` | JWT | Sí | cualquiera |
| POST | `/{id}/duplicate` | JWT | Sí | cualquiera |
| POST | `/preview` | JWT | N/A (puro, sin DB) | cualquiera |
| GET | `/{id}/resolved` | JWT | Sí | cualquiera |

### `backend/routers/data_ops.py` — prefix `/api/data-ops`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| POST | `/distinct` | JWT | Sí (metric) | cualquiera |
| POST | `/replace` | JWT | Sí (metric) — **regex de usuario sin límite (H-04)** | cualquiera |
| POST | `/recalculate` | JWT | Sí (metric + mapping) | cualquiera |

### `backend/routers/api_keys.py` — prefix `/api/api-keys`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| GET | `/` | JWT | Sí | admin |
| POST | `/` | JWT | Sí | admin |
| DELETE | `/{key_id}` | JWT | Sí | admin |

### `backend/routers/ingest.py` — prefix `/api/ingest`

| Método | Ruta | Auth | org_id | Rol |
|---|---|---|---|---|
| POST | `/metrics/{id}/data` | API key (`X-API-Key`) | Sí (siempre desde `ctx.org_id`) | scope `ingest:write` |
| GET | `/metrics/{id}/schema` | API key | Sí | scope `metrics:read` |
| POST | `/pipelines/{id}/trigger` | API key | Sí | scope `ingest:write` |

### `backend/api.py`

| Método | Ruta | Auth | Nota |
|---|---|---|---|
| GET | `/` | Ninguna | Página de estado HTML, sin datos sensibles. OK sin auth. |

**Total: ~111 rutas HTTP** (contando alias `/`↔`""`) en 17 routers. Todas excepto
`POST /api/auth/login`, `GET /` y los 3 endpoints de `ingest.py` (que usan API key en vez de
JWT) exigen `get_current_user`/`require_admin`/`require_superadmin`. No se encontró ningún
endpoint mutante (POST/PUT/DELETE/PATCH) sin autenticación.

---

## 2. Hallazgos

### H-01 — ALTO — `NameError` no controlado enmascara los errores del informe Word
**Archivo:** `backend/routers/reports.py:149` y `:157` (`generar_informe_word`)

El módulo usa `traceback.print_exc()` dentro de dos bloques `except Exception`, pero
`traceback` **nunca se importa** en el archivo (`grep '^import\|^from'` no lo muestra). Ante
cualquier excepción real al cargar datos o renderizar el Word, Python lanza `NameError:
name 'traceback' is not defined` *dentro* del `except`, lo que reemplaza la excepción
original y el `HTTPException(500, ...)` planeado nunca se levanta — FastAPI cae al manejador
genérico y el cliente recibe un 500 sin el mensaje útil que el desarrollador escribió.
Además, el mensaje que sí llega a construirse (`f"Error generando Word:
{type(e).__name__}: {e}"`) filtra detalles internos de la excepción a un usuario autenticado
cualquiera (no solo admin) — no es crítico por ser cross-org, pero es exposición de detalles
de implementación.

**Fix sugerido:** agregar `import traceback` al inicio del archivo; considerar loggear con
`logger.error(..., exc_info=True)` en vez de `traceback.print_exc()` (consistente con el resto
del backend) y devolver un mensaje genérico al cliente.

---

### H-02 — ALTO — Falta filtro `org_id` defensivo en las consultas de `MetricData`/`Metric`/`Dimension` que arman el payload de resultados e informes
**Archivos:**
- `backend/routers/results.py:99` (`Metric.id_metric.in_(metric_ids)`), `:126-128`
  (`Dimension.id_dimension.in_(all_dim_ids)`), `:141` (`MetricData.filter(MetricData.id_metric == mid)`)
- `backend/rgenerator/core/report_steps.py:182, 192, 211` (`_build_records`, usado por
  `build_pdf_bytes`, alcanzable desde `POST /api/indicators/{id}/export-pdf`)
- `backend/rgenerator/reports/data.py:266` (`Metric` sin `org_id`, aunque `MetricData` en la
  misma función sí filtra por `org_id` correctamente — ver línea 149-152)

En estos tres lugares, una vez obtenida la lista de `metric_ids` (vía `IndicatorMetric`), las
queries a `Metric`, `Dimension` y `MetricData` filtran **solo por el id**, no por `org_id`. Hoy
esto no es explotable porque `IndicatorMetric`/`MetricDimension` solo se escriben desde
`backend/routers/indicators.py` y `backend/routers/metrics.py`, y ambos pasan por
`_validate_metric_ids`/`_validate_dimension_ids` que exigen que el id pertenezca a la org del
actor — confirmado con `grep "IndicatorMetric(\|MetricDimension("` (únicos 4 call-sites, todos
guardados). Pero es un patrón fragil de "seguridad por invariante en otro archivo": cualquier
futuro código que inserte esas filas (migración, script de datos, nuevo endpoint, corrección de
bug) sin pasar por esa validación abre una fuga cross-org silenciosa — el escenario exacto que
CLAUDE.md marca como crítico. No hay test de regresión que fije este invariante.

**Fix sugerido:** agregar `Metric.org_id == org_id` / filtrar `Dimension`/`MetricData` por
`org_id` explícitamente en cada uno de estos helpers (defensa en profundidad, no solo
confiar en el invariante de creación), y agregar un test que verifique 404/vacío si se
fuerza un `metric_id` cross-org.

---

### H-03 — MEDIO — Manejo de errores inconsistente entre routers (200 OK con `{"error": ...}` vs `HTTPException`)
**Archivos:** `backend/routers/pipelines.py` (casi todos los endpoints), `backend/routers/specs.py`

Estos dos routers devuelven `return {"error": "..."}` con status HTTP **200** en vez de
levantar `HTTPException` con el código correcto (400/404/500), mientras que
`dimensions.py`, `metrics.py`, `indicators.py`, `tables.py`, `charts.py`, `mappings.py`,
`data_ops.py`, `ingest.py` sí usan `HTTPException` consistentemente. Cualquier cliente HTTP
que confíe en el status code (monitoring, `ingest.py`/integraciones futuras, tests) tratará
estos errores como éxitos. Es además inconsistente con el resto de la API ya migrada.

**Fix sugerido:** migrar `pipelines.py`/`specs.py` a `raise HTTPException(status_code=..., detail=...)`
igual que el resto de los routers B7+.

---

### H-04 — MEDIO — ReDoS potencial en `POST /api/data-ops/replace` (regex de usuario, backend single-worker)
**Archivo:** `backend/routers/data_ops.py:222-226` (`replace_values`, `match_type="regex"`)

`payload.find` se compila directo con `re.compile()` y se ejecuta con `rx.search(s)`/`rx.sub()`
sobre cada valor de cada fila de la métrica, sin timeout ni límite de complejidad. Cualquier
usuario autenticado con acceso a `/api/data-ops/replace` (no requiere rol admin) puede enviar
un patrón catastrófico (ej. `(a+)+$`) que cuelgue el hilo de la request. El propio código del
repo documenta en `backend/routers/pipelines.py:35-38` y `backend/rate_limit.py:4-7` que la
app debe correr con `--workers 1` — un ReDoS aquí bloquea el único worker para **todas las
organizaciones**, no solo la del atacante.

**Fix sugerido:** limitar la longitud de `find`, usar un timeout de evaluación (ej. `regex`
package con `timeout=`, o ejecutar en un thread con `signal.alarm`/`concurrent.futures` con
límite), o restringir el endpoint a rol admin como mitigación parcial.

---

### H-05 — MEDIO — Upload de assets de organización no valida el contenido real del archivo (solo `Content-Type` declarado por el cliente)
**Archivo:** `backend/routers/organizations.py:80-89` (`upload_asset`)

`content_type = file.content_type or "image/png"` se toma tal cual del header enviado por el
cliente y se valida contra una whitelist (`ALLOWED_CONTENT_TYPES`) que incluye
`image/svg+xml`, pero **no se verifican los bytes reales** (magic number / sanitización SVG).
Un admin de una organización puede subir un `.svg` con `<script>` embebido; el asset se sirve
después vía `GET /{org_id}/assets/{asset_id}/download` con
`media_type=asset.content_type` (`FileResponse`, línea 124). Si el frontend o un superadmin
(que puede ver assets de cualquier org, línea 111: `user.org_id != org_id and not
user.is_superadmin`) llega a incrustar ese SVG inline en vez de como `<img>` con sandbox,
hay un vector de XSS. Es un ataque de admin-a-admin/superadmin, no cross-tenant de datos, pero
vale la pena cerrarlo dado que superadmin cruza fronteras de organización por diseño.

**Fix sugerido:** sanitizar SVG en subida (ej. quitar `<script>`, `on*=` handlers) o excluir
`image/svg+xml` de `ALLOWED_KINDS`/`ALLOWED_CONTENT_TYPES`; opcionalmente validar magic bytes
con `python-magic` en vez de confiar en el header del cliente.

---

### H-06 — BAJO — Lookups de `Dimension`/`Metric` por id sin filtro `org_id` en múltiples helpers (fuga de metadata, no de datos)
**Archivos (no exhaustivo, mismo patrón repetido):**
`backend/routers/tables.py:199` (`_load_metric_to_df_uncached`), `backend/routers/charts.py:531`
(`_render_chart_data`), `backend/routers/data_ops.py:106` (`_resolve_column`),
`backend/routers/ingest.py:124` (`_dim_name_to_id`)

Igual que H-02 pero de menor impacto: estos helpers resuelven `id_dimension → nombre` sin
`org_id`, pero solo después de haber validado la `Metric`/`Spec` padre contra `org_id` (y el
`id_dimension` viene de `MetricDimension`, que sí está protegido en su único call-site). En el
peor caso, si algún día se rompe ese invariante, lo que se filtra es el **nombre** de una
dimensión de otra organización, no sus datos. Se agrupa aquí para no duplicar el mismo hallazgo
que H-02 con distinta severidad.

**Fix sugerido:** mismo que H-02 — agregar `Dimension.org_id == org_id` en estos `IN` queries
como defensa en profundidad.

---

### H-07 — BAJO — Email no se normaliza (case) de forma consistente al crear/actualizar usuarios
**Archivos:** `backend/routers/users.py:77,86,123-128` (sin `.lower()`/`.strip()`) vs.
`backend/routers/superadmin.py:235,241,270-276` (sí normaliza) vs. `backend/routers/auth.py:76`
(`login` compara `User.email == body.email` tal cual, sin normalizar)

`User.email` tiene `unique=True` a nivel de columna (case-sensitive en Postgres por defecto),
pero solo `superadmin.py` normaliza a minúsculas antes de comparar/guardar. Un admin de
organización que cree un usuario vía `POST /api/users/` con
`Admin@Fundacion.cl` y otro con `admin@fundacion.cl` obtiene dos filas distintas que la
constraint de unicidad no detecta, generando confusión de identidad y posibles bypass del
chequeo "email ya registrado". No es explotable cross-org (el login sigue exigiendo password
correcto), pero es una debilidad de higiene de datos.

**Fix sugerido:** normalizar `email.strip().lower()` de forma uniforme en
`users.py`, `superadmin.py` y en la comparación de `auth.py:login`; considerar una migración
que normalice los emails existentes y agregue un índice único case-insensitive
(`CITEXT` o `func.lower(email)`).

---

### H-08 — BAJO — Rama muerta / no defendida en `GET /api/pipelines/{id}/artifact/{key}`
**Archivo:** `backend/routers/pipelines.py:395-397` (`download_artifact`)

La rama `elif isinstance(artifact, (str, Path)) and os.path.exists(artifact): ... return
FileResponse(path=file_path, ...)` permitiría descargar **cualquier ruta del filesystem del
servidor** si algún artifact llegara a contener un `str`/`Path` arbitrario. Hoy no es
explotable: se revisaron todos los steps (`grep "ctx.artifacts\["` en
`backend/rgenerator/core/*.py`) y ninguno asigna un artifact de tipo `str`/`Path` —
todos son `DataFrame`. Queda como código frágil: si un futuro step (ej. uno que exporte a
disco y guarde el path como artifact) no sanitiza el path, este endpoint se vuelve un
arbitrary-file-read para cualquier usuario autenticado de la organización dueña del pipeline.

**Fix sugerido:** cuando se implemente un step que guarde paths como artifact, validar que
el path resuelto quede dentro de un directorio permitido (`PIPELINE_RUNS_DIR`/`data/output`)
antes de servirlo, igual que ya se hace para uploads (`upload_root not in
file_path.parents`).

---

### H-09 — INFORMATIVO — Endpoint `refresh` documentado pero no implementado
**Archivo:** `backend/routers/auth.py`

`CLAUDE.md` describe el router como `/api/auth (login, refresh, me)`, pero no existe
`POST /api/auth/refresh` en el código — solo `login` y `me`. No es un problema de seguridad
(el JWT simplemente expira a las `JWT_EXPIRE_HOURS`, default 8h, y el usuario debe volver a
loguearse), pero vale la pena alinear la documentación o agregar el endpoint si se esperaba
sesión persistente más larga.

---

## Resumen de severidades

| Severidad | Cantidad | IDs |
|---|---|---|
| CRÍTICO | 0 | — |
| ALTO | 2 | H-01, H-02 |
| MEDIO | 3 | H-03, H-04, H-05 |
| BAJO | 3 | H-06, H-07, H-08 |
| INFORMATIVO | 1 | H-09 |

No se encontraron: endpoints mutantes sin autenticación, `eval()` inseguro (ya reemplazado
por `backend/rgenerator/tooling/safe_eval.py`), inyección SQL (todo el acceso a datos usa el
ORM de SQLAlchemy con filtros parametrizados), uso de `subprocess`/`os.system`/`pickle.load`,
ni fuga cross-org **confirmada y explotable** vía la API HTTP actual (el patrón de H-02/H-06
es una debilidad estructural, no un exploit verificado).

---

## 3. Casos de prueba recomendados (pytest)

Ubicación sugerida: `tests/routers/` (nuevo) siguiendo el patrón de
`tests/steps/test_pipeline_steps.py`. Usar 2 orgs (`org_a`, `org_b`) con 1 usuario cada una
como fixture base para todos los tests de tenancy.

1. **H-01** — `test_word_report_error_returns_500_with_message`: forzar una excepción dentro
   de `cargar_dataframes_indicator` (mock) al llamar `POST /api/reports/word/{nombre}` y
   verificar que la respuesta es `500` con el `detail` esperado (no un 500 genérico de
   FastAPI por `NameError` no controlado). Este test falla hoy y debe pasar tras el fix.

2. **H-02 / H-06 (regresión de tenancy)** — `test_indicator_data_no_cross_org_leak`:
   - Crear `metric_A` en `org_a` con datos, `metric_B` en `org_b`.
   - Intentar, vía manipulación directa de la fila `IndicatorMetric` en el test (bypaseando
     `_validate_metric_ids` a propósito, simulando el escenario "invariante roto"), enlazar
     un indicador de `org_a` a `metric_B`.
   - Llamar `GET /api/results/indicator/{id}/data` autenticado como usuario de `org_a` y
     verificar que **no** aparecen datos de `metric_B` (debe fallar hoy, confirmando H-02;
     debe pasar tras agregar los filtros `org_id`).
   - Repetir el mismo escenario contra `POST /api/indicators/{id}/export-pdf`.

3. **H-02** — `test_validate_metric_ids_rejects_cross_org` /
   `test_validate_dimension_ids_rejects_cross_org`: test unitario directo de
   `_validate_metric_ids`/`_validate_dimension_ids` con ids de otra org, verificando 400.
   (Cubre el invariante actual, para detectar si alguna vez se rompe.)

4. **H-03** — `test_pipeline_endpoints_use_proper_status_codes`: parametrizado sobre
   `POST /api/pipelines/{id}/upload` con `pipeline_id` inexistente,
   `POST /api/pipelines/config` con nombre duplicado, y `POST /api/specs/config` equivalente
   — verificar que la respuesta HTTP no es `200` sino `4xx`/`5xx` según corresponda.

5. **H-04** — `test_replace_endpoint_rejects_or_bounds_catastrophic_regex`: enviar
   `match_type="regex"`, `find="(a+)+$"` contra una métrica con algunas filas cuyo valor sea
   una cadena tipo `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!"`
   y verificar que la request responde dentro de un timeout razonable (ej. `< 5s`) en vez de
   colgarse — usando `pytest-timeout` o ejecutando en un subproceso con límite de tiempo.

6. **H-05** — `test_upload_asset_rejects_svg_with_script` (o, si se decide permitir SVG,
   `test_upload_asset_sanitizes_svg_script`): subir un `.svg` con `<script>alert(1)</script>`
   con `Content-Type: image/svg+xml` y verificar que el endpoint lo rechaza (400) o que el
   contenido servido después por `download_asset` ya no contiene el `<script>`.

7. **H-07** — `test_user_email_case_insensitive_uniqueness`: crear `admin@org.cl` vía
   `POST /api/users/`, luego intentar crear `Admin@ORG.cl` y verificar 400 "email ya
   registrado" (falla hoy — hoy permite crear ambos).

8. **Cobertura de tenancy general (regresión amplia)** — `test_all_get_by_id_endpoints_404_cross_org`:
   test parametrizado que recorre los endpoints `GET/PUT/DELETE /{recurso}/{id}` de
   `dimensions`, `metrics`, `indicators`, `specs`, `tables`, `charts`, `mappings`,
   `api_keys` con un id válido pero de la organización equivocada, y verifica `404` en todos
   los casos (ya pasa hoy en el código revisado — sirve como red de seguridad ante refactors
   futuros).

9. **Login rate-limit (ya implementado, agregar test de regresión si no existe)** —
   `test_login_blocks_after_max_attempts` y `test_login_rate_limit_resets_on_success`, sobre
   `_limiter_cuenta`/`_limiter_ip` de `backend/routers/auth.py`.

10. **Ingest API-key tenancy** — `test_ingest_metric_data_org_always_from_api_key_not_body`:
    confirmar que aunque el body/headers intenten forzar un `org_id` distinto (no existe hoy
    ese campo, pero es la garantía de diseño documentada en `ingest.py`), el dato siempre
    queda escrito con `ctx.org_id` de la key usada.
