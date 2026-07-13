# W1 — Ingesta por API externa segura

Rama: `feature/w1-ingesta-api` (sobre `dev2`). Workstream W1 del
[Plan Maestro](./plan_maestro_arquitectura.md).

Objetivo: que un sistema tercero (plataforma de la fundación, Google Forms,
otro colegio) alimente `metric_data` o dispare pipelines **sin pasar por la UI
ni por el login JWT de usuarios**, con autenticación por API key propia de la
organización, permisos acotados (scopes), idempotencia y auditoría.

## Mapa de archivos (dónde vive cada cosa)

```
backend/
├── models.py                    + ApiKey, IngestLog  (nuevas tablas)
├── api_keys.py                  NUEVO — crypto de keys: generar, hashear, verificar
├── auth.py                      + get_org_from_api_key (dependency X-API-Key → org + scopes)
├── routers/
│   ├── api_keys.py              NUEVO — /api/api-keys  (gestión, JWT admin-only)
│   └── ingest.py                NUEVO — /api/ingest    (ingesta, auth por API key)
alembic/versions/
└── <hash>_add_api_keys_and_ingest_log.py   NUEVO — migración
tests/routers/
├── test_api_keys.py             NUEVO — gestión + crypto
└── test_ingest.py               NUEVO — ingesta, scopes, idempotencia, tenancy
docs/planes/w1_ingesta_api.md    este archivo
```

Regla de localización: **todo lo de W1 lleva "api_key"/"ingest" en el nombre**.
Si buscas `grep -ri "api.key\|ingest" backend/` ves la superficie completa.

## Modelo de datos

### `ApiKey` (tabla `api_keys`)
| Campo | Tipo | Nota |
|---|---|---|
| `id` | int PK | |
| `org_id` | FK organizations | multi-tenant |
| `name` | str(200) | etiqueta legible ("Integración Forms 2026") |
| `prefix` | str(12) index | primeros chars visibles de la key (`rg_live_a1b2`) para identificarla en la UI sin revelar el secreto |
| `key_hash` | str(200) | bcrypt del secreto completo. **Nunca se guarda el secreto en claro** |
| `scopes` | Text (JSON array) | ej `["ingest:write","metrics:read"]` |
| `created_by_user_id` | FK users | quién la creó |
| `created_at` | datetime | |
| `expires_at` | datetime nullable | null = sin expiración |
| `last_used_at` | datetime nullable | se actualiza en cada uso (throttled) |
| `revoked` | bool default False | revocación lógica |

Formato de la key entregada al cliente (una sola vez, al crear):
`rg_live_<prefix4><32+ chars aleatorios url-safe>`. Se muestra completa **solo**
en la respuesta de creación; después solo se ve el `prefix`.

### `IngestLog` (tabla `ingest_log`)
| Campo | Tipo | Nota |
|---|---|---|
| `id` | int PK | |
| `org_id` | FK organizations | |
| `api_key_id` | FK api_keys nullable | qué key lo hizo |
| `idempotency_key` | str(80) nullable index | header `Idempotency-Key` del cliente |
| `endpoint` | str(80) | ej `metrics/12/data` |
| `status` | str(20) | `success` \| `error` \| `dry_run` |
| `rows_ok` / `rows_failed` | int | resultado |
| `response_hash` | str(64) nullable | hash de la respuesta cacheada para reintentos idempotentes |
| `created_at` | datetime | |

Constraint único: `(org_id, idempotency_key)` cuando `idempotency_key` no es null.

## Scopes

| Scope | Permite |
|---|---|
| `ingest:write` | POST a `/api/ingest/**` (cargar datos, disparar pipelines) |
| `metrics:read` | GET de introspección (schema de una métrica, para que el cliente sepa qué mandar) |

Una key sin el scope requerido → **403**. Sin key / key inválida / revocada /
expirada → **401**.

## Endpoints

### Gestión (JWT, admin de la org) — `backend/routers/api_keys.py`
- `POST /api/api-keys` → crea. Body `{name, scopes[], expires_at?}`. **Devuelve
  el secreto en claro UNA vez** + metadata. `require_admin`.
- `GET /api/api-keys` → lista las keys de la org (prefix, scopes, estado, uso).
  Nunca el secreto.
- `DELETE /api/api-keys/{id}` → revoca (soft, `revoked=True`). `require_admin`.

### Ingesta (API key) — `backend/routers/ingest.py`
- `POST /api/ingest/metrics/{metric_id}/data`
  - Auth: `get_org_from_api_key` con scope `ingest:write`.
  - Body: `{records: [{value, dimensions:{<nombre_dim>: valor}}...], dry_run?}`.
  - Valida cada record contra `meta_json.fields` (tipos) y las dimensiones
    registradas de la métrica; los nombres de dimensión humanos se resuelven a
    `id_dimension`. Rechaza con detalle por fila inválida.
  - Idempotencia: si viene `Idempotency-Key` y ya existe para la org, devuelve
    el resultado previo sin re-insertar.
  - Inserta vía `make_metric_data(via="api_direct", ip=...)` + invalida cache.
  - Respuesta: `{rows_ok, rows_failed, errors:[{index, reason}], dry_run}`.
- `POST /api/ingest/pipelines/{pipeline_id}/trigger`
  - Auth: scope `ingest:write`. Multipart (reusa la sanitización de uploads de
    W0.1). Encola/ejecuta el pipeline con los archivos. Devuelve `job_id`.
- `GET /api/ingest/metrics/{metric_id}/schema`
  - Auth: scope `metrics:read`. Devuelve fields + dimensiones esperadas (contrato
    para el integrador).

## Garantías de seguridad (checklist de revisión)

1. Secreto de la key **nunca** persistido ni logueado en claro (solo bcrypt hash + prefix).
2. Toda query de ingesta filtra por el `org_id` **derivado de la key** (no de un
   parámetro del request). Imposible cargar datos en otra org.
3. Scope insuficiente → 403; key inválida/revocada/expirada → 401.
4. `metric_id`/`pipeline_id` deben pertenecer a la org de la key (404 si no).
5. Idempotencia evita doble inserción en reintentos.
6. Límite de tamaño de payload y de archivos (reusa `MAX_UPLOAD_BYTES`).
7. `last_used_at` se actualiza para detectar keys zombis (throttle a 1/min para
   no escribir en cada request).

## Plan de pruebas de calidad

**Automatizadas** (`tests/routers/test_api_keys.py`, `test_ingest.py`):
- Crypto: la key generada verifica contra su hash; una alterada no; el secreto
  no aparece en el listado.
- Gestión: crear/listar/revocar; `require_admin` (editor → 403); una org no ve
  las keys de otra.
- Auth de ingesta: sin key → 401; key revocada → 401; expirada → 401; scope
  faltante → 403; key OK → 200.
- **Tenancy dura**: key de Org A no puede cargar en métrica de Org B (404), ni
  ver su schema. El `org_id` sale de la key, no del body.
- Validación: record con field de tipo inválido → va a `rows_failed` con razón;
  `dry_run=true` no inserta.
- Idempotencia: dos POST con la misma `Idempotency-Key` → una sola inserción,
  misma respuesta.
- Auditoría: las filas quedan con `created_via="api_direct"`.

**Manuales** (gate del workstream, documentar en `docs/reportes/`):
- Crear una key desde la UI (cuando exista) o por endpoint, y hacer una carga
  real con `curl`/Postman contra staging; verificar que el dashboard refleja los
  datos y que la fila aparece auditada como `api_direct`.
- Intentar cargar en otra org con la key propia → 404, confirmado.

## Fuera de alcance de W1 (a W-siguientes)
- UI de gestión de keys en el frontend (chip en /settings) — va con W6/settings.
- Rotación automática de keys y webhooks de notificación de ingesta.
- Cola asíncrona real para `trigger` (por ahora reusa el runner in-memory).
