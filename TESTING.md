# Testing

Plan y convenciones de testing para Report Generator.

> **CI**: corre en **local** vía git hook `pre-push` (no GitHub Actions). La suite "not slow" toma ~11s en local vs varios minutos en un runner remoto que tiene que armar la env conda desde cero. Activar el hook una sola vez con `git config core.hooksPath .githooks`.

---

## TL;DR — comandos diarios

```bash
# Todos los tests (sin los lentos)
pytest -q -m "not slow"

# Solo unit (rápido, ideal en pre-commit)
pytest -q -m unit

# Coverage
pytest --cov=backend --cov-report=term-missing

# Un archivo específico
pytest tests/steps/test_derived_fields_engine.py -v

# Solo lo que falló la última corrida
pytest --lf
```

---

## Capas de testing

```
        ┌─────────────────────────────┐
        │  E2E (smoke crítico)         │   pocos    ~30s
        ├─────────────────────────────┤
        │  Integration (routers + DB)  │   ~80      ~60s
        ├─────────────────────────────┤
        │  Unit (helpers, engine)      │   ~300     ~5s
        └─────────────────────────────┘
```

| Capa | Qué prueba | Tecnología |
|---|---|---|
| **Unit** | Funciones puras: `_to_field_name`, `apply_delta`, `_resolve_color_for_value`, validación Pydantic | `pytest` puro, sin DB |
| **Integration** | Endpoints HTTP completos con DB real (SQLite in-memory, mismas tablas que prod) | `TestClient` FastAPI + fixture `db_session` |
| **E2E** | Path crítico end-to-end: login → dashboard → PDF | `httpx` contra el backend completo |
| **Frontend** | (postergado) | Playwright |

---

## Markers

```python
@pytest.mark.unit          # <100ms, sin I/O. Default en pre-commit.
@pytest.mark.integration   # <500ms, usa db_session/client.
@pytest.mark.slow          # >1s — generación PDF, ETL completo. Excluido por default.
```

Uso:

```bash
pytest -m unit                  # solo unit
pytest -m "not slow"            # todo menos lentos
pytest -m "integration or slow" # solo lentos / integration
```

---

## Fixtures globales (`tests/conftest.py`)

| Fixture | Scope | Para qué |
|---|---|---|
| `engine` | session | SQLite in-memory con todas las tablas creadas (vía `Base.metadata.create_all`) |
| `db_session` | function | Sesión SQLAlchemy con rollback automático al finalizar cada test |
| `client` | function | `TestClient(app)` con `get_db` override apuntando a `db_session` |
| `org` | function | Crea una `Organization` lista para usar |
| `user` | function | Crea un `User` con password conocido vinculado a `org` |
| `auth_headers` | function | `{"Authorization": "Bearer <jwt>"}` para el `user` del fixture |
| `client_auth` | function | `TestClient` con `auth_headers` precargados (atajo) |

Ejemplo de uso:

```python
def test_get_indicators_filtra_por_org(client_auth, db_session, org):
    # Crear indicador en otra org → no debería aparecer
    other_org = Organization(name="otra", slug="otra")
    db_session.add(other_org)
    db_session.flush()
    db_session.add(Indicator(name="X", org_id=other_org.id))
    db_session.commit()

    r = client_auth.get("/api/indicators/")
    assert r.status_code == 200
    assert r.json() == []  # no ve el de otra org
```

---

## Plan en fases

### Fase 0 — Infraestructura ✅ (este commit)

- [x] `pytest.ini` con markers y testpaths
- [x] `tests/conftest.py` con fixtures globales
- [x] `tests/factories.py` con helpers para crear objetos
- [x] Test de smoke validando que los fixtures funcionan
- [x] Comandos documentados en `CLAUDE.md`

### Fase 1 — Regresión de bugs vistos en producción

Tests que **fallarían sin el fix correspondiente**:

- [ ] `apply_delta`/`apply_slope` sobre DataFrame vacío → columna NaN, no KeyError
- [ ] SIMCE: `df["Asignatura"] == "LENGUAJE"` matchea valores BD `"Lenguaje"` (case-insensitive)
- [ ] Routers de results/charts/tables/indicators son `def` (no `async def`) — escaneo del módulo
- [ ] Cache TTL: `invalidate_metric_df_cache(metric_id)` borra solo esa key
- [ ] Event listeners de `MetricData` invalidan cache tras `INSERT/UPDATE/DELETE`
- [ ] `/api/indicators` usa `selectinload` (no N+1) — comprobable con `count_queries`

### Fase 2 — Routers críticos

Orden de prioridad:

1. **`auth.py`** — JWT, bcrypt, expiración, `get_current_user` ✅ (100% cov)
2. **`/api/indicators`** — CRUD + multi-tenancy 401/403 (54% cov)
3. **`/api/results/indicator/{id}/data`** — el más complejo: filtros, cascading, derived_fields, paso 7.5 (54% cov)
4. **`/api/reports/{tipo}`** — PDF v2 (verificar generación sin crash, validar headers HTTP) (56% cov)
5. **`/api/metrics`** + `/api/metrics/{id}/data` — CRUD + import + paginación ✅ 66% (Sprint 5, falta `/import` con multipart upload)
6. **`/api/charts`** + `/api/tables` — render dataset, Pydantic schemas ✅ charts 82% (Sprint 2), tables 76% (Sprint 5)
7. **`/api/pipelines`** — CRUD + config (Sprint 5 → 41%, falta cubrir endpoints de ejecución que requieren PipelineRunner activo en memoria)

Patrón por endpoint: `test_success`, `test_404`, `test_403_other_org`, `test_validation_error`, `test_edge_case_empty_data`.

### Fase 3 — Motor PDF v2 (golden tests)

- [ ] Fixtures de datos fijos para SIMCE y DIA en `tests/fixtures/`
- [ ] Comparación por **contenido extraído** del PDF (PyMuPDF text) — más estable que diff binario
- [ ] Variantes: con/sin filtro de Mes, asignatura Lenguaje/Matemática, df vacío

### Fase 4 — E2E smoke

- [ ] Login → token JWT válido
- [ ] Login → cargar dashboard IDEL → KPIs correctos
- [ ] Login → seleccionar filtros → POST `/api/reports/simce` → PDF bytes válidos

### Fase 5 — Frontend (opcional, postergable)

- [ ] Playwright contra `npm run dev` + backend de test
- [ ] Tests de regresión: doble-fetch, filtros cascading, render de dashboards
- [ ] Visual regression con screenshots

---

## Convenciones

- **Cada bug arreglado → un test de regresión.** El test debe fallar antes del fix y pasar después. Es la garantía que no vuelva.
- **Naming**: `test_<accion>_<condicion>_<resultado>`. Ej: `test_get_indicators_other_org_returns_empty_list`.
- **Coverage objetivo**: 70% en `backend/routers/` y `backend/rgenerator/`. No buscar 100% — los `else` defensivos no aportan señal.
- **Sin tests → sin merge a `main`** (a futuro). En `dev` se permite work-in-progress.
- **Si el test depende de orden** (state mutable entre tests), es bug — usar `db_session` que rollback automáticamente.

---

## CI local con `pre-push` hook

Setup one-time (cada clon nuevo del repo):

```bash
git config core.hooksPath .githooks
```

Eso le dice a git que use los hooks versionados en [`.githooks/`](.githooks/) en lugar del default `.git/hooks/` (que es local, no versionado). El hook [`.githooks/pre-push`](.githooks/pre-push) corre:

```bash
pytest -q -m "not slow"
```

antes de cada `git push`. Si algún test falla, el push se aborta y muestra el output.

**Bypass de emergencia** (cuando sabes lo que haces — bug en CI, push de docs sin código, etc.):

```bash
git push --no-verify
```

**Por qué local y no GitHub Actions**:
- 11s en local vs ~5min en un runner remoto que arma la env conda desde cero.
- No depende de minutos de GitHub Actions ni de su disponibilidad.
- El feedback es inmediato: si los tests fallan, los ves antes que tu push llegue a un PR.

**Alternativa más estricta — pre-commit hook** (corre en cada commit, no en push):

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest unit
        entry: pytest -q -m unit
        language: system
        pass_filenames: false
```

```bash
pip install pre-commit && pre-commit install
```

## Configuración de coverage

[`pyproject.toml`](./pyproject.toml) tiene `[tool.coverage.run]` y `[tool.coverage.report]`. Archivos omitidos del cálculo (scratchpads y scripts legacy que ensucian el reporte sin valor de testing):

- `backend/test_eval.py` — scratch para `eval()` con pandas
- `backend/read_pipe.py` — script one-shot XLSX→JSON
- `backend/init_indicators_db.py` — bootstrap legacy con path Windows hardcoded
- `backend/cli.py`, `backend/__main__.py`
- `*/alembic/*`, `*/migrations/*`

---

## Herramientas (instaladas vía `environment.yml`)

| Tool | Para qué |
|---|---|
| `pytest` | Runner |
| `pytest-cov` | Coverage |
| `pytest-xdist` (opcional) | `pytest -n auto` para paralelizar |
| `httpx` | (incluido en FastAPI deps) cliente para TestClient |

---

## Cuando agregar un nuevo módulo

Workflow recomendado:

1. Escribir el código
2. **Escribir el test ANTES** del fix si es un bugfix (TDD ligero)
3. `pytest tests/path/al/test_nuevo.py -v` localmente
4. `pytest -q -m "not slow"` antes de commitear
5. Si bajó la cobertura del módulo tocado, agregar más tests
