# G6 — Multi-tenancy

**Precondiciones**: 2 organizaciones (A y B) con datos distintos y un usuario en cada una. Sesiones en ventanas separadas (o incógnito).

| # | Acción | Esperado |
|---|---|---|
| 1 | Usuario A: listar pipelines, metrics, indicadores | Solo ve los de la org A |
| 2 | Usuario A: tomar un id de indicador de la org B (por DB) y abrir `/results` con él / llamar `GET /api/results/indicator/{id_B}/data` | 404/403 — jamás datos de B |
| 3 | Usuario A: `POST /api/reports/word/{nombre}` con indicator_id de B | 400/404, sin datos de B (defensa org_id en loader) |
| 4 | Usuario A: descargar artifact de un pipeline de B (URL directa) | 403/404 |
| 5 | Usuario A: en /charts y /tables, verificar que specs/charts listados son solo de A | Sin cruces |
| 6 | Superadmin: panel cross-org | Sí ve ambas orgs (es su rol) |

**Nota**: la suite pytest ya cubre tenancy negativa a nivel API (`tests/routers/test_tenancy_negativa.py`); este guion valida que la UI no filtre por otros caminos.
