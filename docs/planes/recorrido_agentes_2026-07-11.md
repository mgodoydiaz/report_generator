# Recorrido del proyecto con agentes — 2026-07-11

Tres agentes exploraron backend, frontend y el subsistema de reportes.
Grafo de conocimiento generado con graphify en `graphify-out/graph.html`
(3.276 nodos, 6.109 aristas, 232 comunidades).

## Top 10 mejoras priorizadas (todo el proyecto)

1. **[Seguridad] Path traversal en uploads de pipelines** — `routers/pipelines.py:140,147`:
   `input_key` y `file.filename` se concatenan al path sin sanitizar. Sanear con
   `Path(...).name` + lista blanca de `input_key`.
2. **[Seguridad] `eval()` sobre config de pipelines** — `tooling/etl_tools.py:193-208`:
   `condicion`/`expresion` del `config_json` se evalúan con `eval`. Migrar a
   `simpleeval`/`asteval` o DSL acotado.
3. **[Bug latente] Sesión DB obsoleta en `ACTIVE_RUNNERS`** — `routers/pipelines.py:183+`:
   el runner cacheado retiene la sesión del primer request (ya cerrada) en
   `/input` y `/step`. Refrescar `runner.ctx.db = db` en cada request.
4. **[Seguridad] JWT_SECRET con default silencioso** (`auth.py:23`) y **CORS `*` con
   credenciales** (`api.py:19-25`). Fallar en arranque sin secret; restringir orígenes.
5. **[Arquitectura] 4 copias del mismo código matplotlib y 5 formatos de spec de
   gráfico** — ver `docs/planes/plan_tablas_graficos_modulares.md` (plan completo).
6. **[Frontend] Sin capa API centralizada** — `apiGet/apiPost` duplicados literalmente
   en Tables.jsx:860 y Charts.jsx:809; muchos `fetch` crudos no disparan logout en 401.
   Crear `src/api/client.js` sobre `fetchAuth`.
7. **[Frontend] Recharts legacy listo para morir** — solo lo usan
   `SIMCE_PRESET_LAYOUT`, `Help.jsx` y layouts viejos en DB. Migrar esos 3 puntos y
   eliminar `tooling/charts/` + `recharts` del bundle.
8. **[Rendimiento] Cache de DataFrames sin invalidar tras escrituras** —
   `invalidate_metric_df_cache()` solo se llama en tables.py:688; los writers de
   `metrics.py`, `data_ops` y `SaveToMetric` no invalidan (dashboards desfasados 60s).
9. **[Operación] Endpoints `async` con trabajo bloqueante** (`run_all()` pandas/PDF
   bloquea el event loop con `--workers 1`) + errores devueltos como HTTP 200
   (`return {"error": ...}`) + 0 logging estructurado (~58 prints).
10. **[Tests] Sin tests de tenancy negativos** (org A accediendo a recursos de org B)
    ni de los routers `data_ops`, `organizations`, `users`, `superadmin` — justo la
    superficie de mayor riesgo.

## Informes completos de los agentes

Los tres informes detallados (25 + 18 + inventario completo de specs) están
en el hilo de la sesión de Claude del 2026-07-11. Los planes accionables:

- `docs/planes/plan_tablas_graficos_modulares.md` — refactor tablas/gráficos
- `docs/informes_word.md` — generador Word por indicador (IMPLEMENTADO en
  la rama `feature/reportes-word-indicadores`)

## Notas positivas

- El filtrado multi-tenant por `org_id` está aplicado consistentemente
  (no se encontraron fugas cross-org en queries de negocio).
- El motor PDF v2 (`reports/`) con registries es la base arquitectónica
  correcta — el plan de refactor converge hacia ese patrón.
- 529 tests verdes en la suite (`pytest -m "not slow"`).
