# QA — Pipelines y suite de tests (Report Generator)

**Fecha**: 2026-07-22
**Rama**: `dev3`
**Comando ejecutado**: `python -m pytest -q -m "not slow" --tb=short`

---

## 1. Resultado de la corrida

```
703 passed, 1 skipped, 4 deselected, 2 failed in 70.21s
```

Los **2 fallos son de entorno Windows** (confirmado, no hay bugs de producto detrás):

| Test | Causa | Naturaleza |
|---|---|---|
| `tests/routers/test_pivot_endpoints.py::TestPdfV2Pivot::test_construir_pdf_bytes` | `ModuleNotFoundError: No module named 'weasyprint'` | weasyprint no está instalado en el conda env `rgenerator` local (requiere librerías nativas de Linux/Cairo — normal en Windows) |
| `tests/routers/test_w0_hardening.py::test_backend_auth_no_importa_sin_jwt_secret` | `OSError: [WinError 10106]` al importar `_overlapped` en un subprocess | Problema de proveedor de sockets asíncronos de Windows al lanzar `python -c "..."` como subprocess, no relacionado con la lógica del test |

No se encontró **ningún otro fallo**. 1 skip esperado (`test_pdf_steps_stub.py:167`, falta PDF DIA real / fitz-camelot). 4 tests deselected corresponden a `@pytest.mark.slow` (excluidos por el flag, no fallan).

**Veredicto**: suite verde. Nada que arreglar en el corto plazo a nivel de resultados de test.

---

## 2. Inventario de tests y evaluación de formato

### 2.1 Estructura

```
tests/
├── conftest.py            228 líneas — fixtures compartidas (engine, db_session, client, org, user, auth_headers, client_auth)
├── factories.py            194 líneas — make_org/make_user/make_dimension/make_metric/make_metric_data/make_indicator
├── test_app_boot.py         85 líneas — smoke de boot FastAPI (suelto en la raíz)
├── test_infra_smoke.py     133 líneas — suelto en la raíz
├── e2e/        1 archivo   174 líneas — flujo completo login→dashboard→pdf (marcado slow)
├── reports/    3 archivos  485 líneas — motor PDF v2 / Word
├── regresion/  5 archivos  568 líneas — bugs puntuales ya resueltos (1 test = 1 regresión, con cita del incidente)
├── routers/   15 archivos 3673 líneas — un archivo por router de backend/routers/
└── steps/     10 archivos 2530 líneas — steps de rgenerator/core + engines internos
```
Total: **36 archivos de test, 9662 líneas**.

### 2.2 Lo que ya está bien (contrario a la percepción de "mal formato")

- **Fixtures compartidas sólidas**: `conftest.py` implementa SAVEPOINT anidado para aislar cada test con rollback automático, más `factories.py` con contadores monotónicos para evitar colisiones UNIQUE. No hay duplicación de setup de DB entre archivos — todos usan `db_session`/`client`/`factories.*`.
- **Docstrings de módulo excelentes** en los mejores exponentes (`test_pivot_engine.py`, `test_charts_router.py`, `test_pipelines_router.py`, `test_app_boot.py`): explican qué cubren, por qué, y **documentan explícitamente qué NO cubren y por qué** (ver hallazgo H1). Esto es un patrón a preservar, no a cambiar.
- **Tests de comportamiento, no de implementación**: la gran mayoría pega contra el `TestClient`/API pública o contra funciones puras con contratos matemáticos (pivot_engine), no contra detalles internos.
- `tests/routers/` es **100% consistente**: los 15 archivos agrupan en clases `TestXxx` por endpoint/escenario (éxito, 401, 404, multi-tenancy, 422, edge cases) — un patrón replicable.
- `tests/regresion/` tiene una convención clara y valiosa: 1 test = 1 bug histórico, con referencia al incidente en el docstring.

### 2.3 El problema real de formato

**No es la calidad de los tests — es la inconsistencia de convención dentro de `tests/steps/`.**

| Archivo | Estilo | Marcadores |
|---|---|---|
| `test_pivot_engine.py` (706 líneas) | 52 funciones sueltas `test_*`, sin clases | 0 |
| `test_analysis_tools.py` | 17 funciones sueltas | 0 |
| `test_validate_dataframe.py` | 14 funciones sueltas | 0 |
| `test_apply_derived_fields_step.py` | 6 funciones sueltas | 0 |
| `test_derived_fields_engine.py` (888 líneas) | 12 clases `TestXxx` | usa marcadores parcialmente |
| `test_report_html_tools.py` | 7 clases `TestXxx` | 0 |
| `test_run_excel_etl.py` | 3 clases `TestXxx` | usa marcadores |
| `test_safe_eval.py` | 3 clases `TestXxx` | usa marcadores |
| `test_pdf_steps_stub.py` | mixto (2 clases + 5 funciones) | 0 |

Y a nivel de repo completo: **10 de 36 archivos no usan ningún `@pytest.mark`** (unit/integration/slow), casi todos en `tests/steps/`. `pytest.ini` documenta `unit: <100ms — corre en pre-commit`, pero sin marcador esos archivos no pueden filtrarse selectivamente — quedan fuera de la intención declarada del propio `pytest.ini`.

### 2.4 Convención propuesta

1. **Clases `TestXxx` siempre**, incluso para funciones puras (pivot_engine, safe_eval, analysis_tools). Agrupar por comportamiento/contrato, no por "función bajo test". Es el mismo patrón que ya domina `tests/routers/`.
2. **Marcador obligatorio por clase** (`@pytest.mark.unit` en la clase alcanza a todos sus métodos): considerar un check de CI/pre-commit que falle si un archivo nuevo bajo `tests/` no declara ningún marcador (fácil de escribir con `ast` o `pytest --collect-only -q` + grep).
3. **Mover los sueltos de la raíz**: `test_app_boot.py` y `test_infra_smoke.py` → `tests/smoke/`, para que la partición por carpeta sea 100% por capa (routers/steps/reports/regresion/e2e/smoke).
4. **Adoptar el docstring de módulo de `test_pivot_engine.py`/`test_pipelines_router.py` como plantilla obligatoria**: qué cubre + qué NO cubre explícitamente y por qué.

**Ejemplo de test modelo** (siguiendo la convención propuesta, aplicable a un archivo hoy con funciones sueltas):

```python
"""Tests de <módulo> — <qué garantiza, en 1 línea>.

Cobertura:
- <bullet 1>
- <bullet 2>

Fuera de alcance (documentado a propósito):
- <qué no se cubre y por qué — ej. "ejecución end-to-end del step dentro
  de PipelineRunner: ver hallazgo de cobertura #1">
"""
from __future__ import annotations

import pytest

from rgenerator.core.mi_modulo import mi_funcion


@pytest.mark.unit
class TestMiFuncionCasosBase:
    def test_entrada_valida_devuelve_resultado_esperado(self):
        assert mi_funcion(x=1) == 2

    def test_entrada_vacia_no_lanza_excepcion(self):
        assert mi_funcion(x=None) is None


@pytest.mark.unit
class TestMiFuncionBordes:
    def test_valor_negativo_lanza_valueerror(self):
        with pytest.raises(ValueError):
            mi_funcion(x=-1)
```

---

## 3. Mapa de cobertura: steps y routers vs tests

### 3.1 Steps (`STEP_MAPPING`, `backend/rgenerator/tooling/pipeline_tools.py`)

Los 15 steps registrados coinciden 1:1 con las clases definidas en `backend/rgenerator/core/*.py` — no hay steps huérfanos ni referencias rotas en `STEP_MAPPING`.

| Step | Test dedicado | Usado en pipelines de producción (`data/pipelines/dia/*.json`) |
|---|---|---|
| `InitRun` | Solo indirecto (`test_ingest.py`) | sí |
| `LoadConfigFromSpec` | **Ninguno** | sí (implícito vía specs) |
| `RequestUserFiles` | Solo indirecto (`test_ingest.py`) | sí |
| `RunExcelETL` | `test_run_excel_etl.py` | sí |
| `EnrichWithUserInput` | **Ninguno** | sí |
| `EnrichWithContext` | **Ninguno** | sí |
| `EnrichWithLookup` | **Ninguno** | no visto en los 2 pipelines de muestra |
| `ModifyColumnValues` | Solo `test_safe_eval.py` (parcial) | — |
| `ApplyDerivedFields` | `test_apply_derived_fields_step.py` + `test_derived_fields_engine.py` | sí |
| `RunDIAPDFExtraction` | `test_pdf_steps_stub.py` (stub) | sí |
| `ValidateDataframe` | `test_validate_dataframe.py` | — |
| `SaveToMetric` | **Ninguno** | sí |
| `LoadMetricToDF` | **Ninguno** | no visto en los 2 pipelines de muestra |
| `RenderHtmlReport` | `test_report_html_tools.py` | — |
| `RenderPDFReport` | **Ninguno** | — |

**7 de 15 steps (47%) sin ningún test directo**, y de esos, 4 (`LoadConfigFromSpec`, `EnrichWithUserInput`, `EnrichWithContext`, `SaveToMetric`) están **activamente usados en los pipelines DIA reales** (`data/pipelines/dia/dia_matematicas_pipeline.json`, `dia_lectura_pipeline.json`).

Además: **`PipelineRunner` — el orquestador que instancia y corre estos steps en secuencia — nunca se instancia en ningún test** (`grep -rn "PipelineRunner(" tests/` → 0 resultados fuera de un comentario). Esto está documentado explícitamente en `tests/routers/test_pipelines_router.py` líneas 12-14:

> "Saltea los endpoints de ejecución (run, step, input, reset, artifact, upload) — requieren un PipelineRunner activo en memoria + uploads filesystem, lo que merece un sprint dedicado."

### 3.2 Routers (`backend/routers/`)

| Router | Endpoints | Test dedicado | Cobertura real |
|---|---|---|---|
| `auth.py` | — | `test_auth_router.py` | buena |
| `users.py` | 4 | ninguno dedicado (toca solo vía `test_authz_y_jwt.py`/`test_tenancy_negativa.py`) | parcial |
| `superadmin.py` | 9 | ninguno dedicado (parcial vía tenancy/authz) | parcial |
| `pipelines.py` | CRUD + 6 de ejecución | `test_pipelines_router.py` | **CRUD sí, ejecución NO (0%)** |
| `specs.py` | 7 | ninguno | **0%** |
| `dimensions.py` | 7 (incl. delete de valores) | ninguno | **0%** |
| `metrics.py` | — | `test_metrics_router.py` | buena |
| `indicators.py` | — | `test_indicators_router.py` | buena |
| `results.py` | — | `test_results_router.py` | buena |
| `charts.py` | 9 | `test_charts_router.py` (851 líneas, el más completo del repo) | excelente |
| `tables.py` | — | `test_tables_router.py` | buena |
| `data_ops.py` | 3 (`distinct`, `replace`, `recalculate`) | ninguno | **0%** |
| `mappings.py` | 7 | ninguno | **0%** |
| `organizations.py` | 4 (assets: upload/download/delete) | solo tangencial vía `test_tenancy_negativa.py` | **casi 0%** |
| `ingest.py` | — | `test_ingest.py` | buena |
| `api_keys.py` | — | `test_api_keys.py` | buena |
| `reports.py` | — | `test_reports_router.py` | parcial (weasyprint bloquea local) |

### 3.3 Los 10 huecos de cobertura más riesgosos (priorizados)

1. **[CRÍTICO] Ejecución de pipelines end-to-end** — endpoints `run/step/input/reset/artifact/upload` de `/api/pipelines` y `PipelineRunner` mismo: 0% cobertura, documentado como deuda conocida. Es el corazón funcional del producto.
2. **[CRÍTICO] `SaveToMetric`** (`backend/rgenerator/core/metric_steps.py`) — único punto de escritura de resultados ETL a PostgreSQL (`metric_data`), 0% cobertura, y con manejo de errores silencioso (ver H2).
3. **[ALTO] `data_ops.py::/replace` y `/recalculate`** — mutación masiva (find&replace estilo Excel con soporte regex, y recálculo de columna vía mapeo) sobre `MetricData` de una métrica completa, con `dry_run` pero también camino de escritura real. 0% cobertura.
4. **[ALTO] `LoadConfigFromSpec`** — se ejecuta al inicio de prácticamente todo pipeline (traduce `etlParams` del spec a parámetros planos, con coerción de tipos). 0% cobertura.
5. **[ALTO] `EnrichWithUserInput` / `EnrichWithContext` / `EnrichWithLookup`** — usados en los pipelines DIA de producción; la lógica de pausa interactiva (`WaitingForInputException`, modos `once`/`per_file`) nunca se ejercita. 0% cobertura.
6. **[ALTO] `LoadMetricToDF`** — camino de lectura simétrico a `SaveToMetric`, con parsing de JSON y aplanado de dimensiones. 0% cobertura.
7. **[MEDIO-ALTO] `organizations.py` assets (upload/download/delete)** — maneja archivos de organización en filesystem; el propio historial del proyecto (`memory/project_recorrido_agentes.md`) señala *path traversal* como hallazgo previo en el área de archivos. 0% cobertura de test.
8. **[MEDIO] `dimensions.py`** — catálogo transversal (referenciado por metrics, indicators, charts); incluye delete de valores de dimensión, sin ningún test que confirme que no rompe referencias existentes.
9. **[MEDIO] `specs.py`** — CRUD de specs que alimenta directamente a `LoadConfigFromSpec` (huecos #4 y #9 son la misma cadena sin ningún test en ningún extremo).
10. **[MEDIO] `RenderPDFReport`** (step) y **`mappings.py`** (router, incl. preview/resolved/duplicate) — ambos 0% cobertura; menor urgencia que los anteriores porque `RenderPDFReport` delega en `runtime.construir_pdf` que sí tiene tests parciales (bloqueados localmente por falta de weasyprint, pero corren en CI Linux).

---

## 4. Hallazgos de calidad en los steps (`backend/rgenerator/core/*.py`)

| # | Severidad | Archivo:línea | Hallazgo | Fix sugerido |
|---|---|---|---|---|
| H1 | Informativo | `tests/routers/test_pipelines_router.py:12-14` | Deuda de cobertura auto-documentada: ejecución de pipelines excluida a propósito. | Confirma hueco #1 de la sección 3.3 — priorizar un sprint dedicado como ya lo anticipa el propio comentario. |
| H2 | **Alto** | `backend/rgenerator/core/metric_steps.py:137-141` | `SaveToMetric` usa `except: pass` (bare, ni siquiera `except Exception:`) al castear valores de campos `object` a `int`/`float`. Si el cast falla, el valor queda `None` en el `dict` (la clave nunca se asigna) sin loggear qué fila/columna/valor falló — pérdida silenciosa de dato en el camino de escritura a producción. | Loggear `logger.warning(...)` con el valor original y la excepción; usar `except (ValueError, TypeError):` explícito. |
| H3 | **Alto** | `backend/rgenerator/core/metric_steps.py` (todo el archivo) | `SaveToMetric`/`LoadMetricToDF` sin ningún test (ver hueco #2/#6). | Crear `tests/steps/test_metric_steps.py` con `db_session` real cubriendo: object-type con `fields`, tipo simple float/int, `clear_existing`, filtros válidos/ inválidos en `LoadMetricToDF`, DataFrame vacío, invalidación del cache de `tables.py`. |
| H4 | Medio | `backend/rgenerator/core/report_steps.py` (≈15 bloques, líneas 205, 215, 237, 269, 306, 424, 483, 760, 795, 1013, 1037, 1055, 1112) | Múltiples `except Exception: pass`/fallback silencioso al parsear JSON de `meta_json`/`column_roles`/`role_formats`/`pdf_layout`. La mayoría son parseos tolerantes razonables (dato legado en formato variable), pero ninguno deja rastro si la causa es un bug real y no un dato legado. | Agregar `logger.debug`/`warning` con el motivo del fallback en al menos los casos que afectan la renderización final del PDF (líneas 1013, 1112). |
| H5 | Bajo | `backend/rgenerator/core/init_steps.py:83-111` | Bloque completo de la clase `LoadConfig` (deprecada) queda comentado como "historial" en el archivo fuente. Inofensivo, pero el propio git history ya cumple ese rol. | Eliminar el bloque comentado; si se quiere preservar el ejemplo, moverlo a un commit/doc, no al archivo activo. |
| H6 | Bajo | `CLAUDE.md` (sección Arquitectura → `report_steps.py`/`io_steps.py`) | Documentación desactualizada: describe clases `GenerateGraphics`, `GenerateTables`, `RenderReport`, `GenerateDocxReport`, `DiscoverInputs`, `ExportConsolidatedExcel`, `DeleteTempFiles` que **no existen** en el código actual de `dev3` (verificado con `grep -rn "class Generate\|class DiscoverInputs\|..." backend/` → 0 resultados). El módulo real solo expone `RenderPDFReport`/`RenderHtmlReport` (report_steps.py) y `RequestUserFiles` (io_steps.py). | Actualizar la sección de arquitectura de `CLAUDE.md` para reflejar el estado real de `backend/rgenerator/core/`. Riesgo: un agente que use CLAUDE.md como fuente de verdad puede intentar "arreglar" o extender clases que no existen. |
| H7 | N/A (no es bug) | — | Ningún step registrado en `STEP_MAPPING` está huérfano ni sin uso — las 15 clases de `core/*.py` mapean 1:1 con las 15 entradas de `STEP_MAPPING`. | Sin acción. |

---

## Resumen para priorización inmediata

- La suite está sana: **703 pasan, 2 fallos son 100% de entorno Windows**, cero regresiones reales.
- El formato de los tests es en general **bueno** (fixtures compartidas, factories, docstrings ejemplares) — el malestar percibido probablemente viene de la **inconsistencia dentro de `tests/steps/`** (mitad clases, mitad funciones sueltas, sin marcadores en 10/36 archivos), no de falta de calidad.
- El riesgo real está en **cobertura**, no en formato: la ejecución completa de pipelines (`PipelineRunner` + endpoints run/step/input/artifact) y los steps de escritura a BD (`SaveToMetric`, `LoadConfigFromSpec`, `EnrichWith*`) — todos usados en producción — tienen **0% de tests**, junto con 4 routers completos (`data_ops`, `mappings`, `dimensions`, `specs`).
