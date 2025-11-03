# Codex Review

## Critical Issues
- `backend/main.py:26`: `from reports import informe` raises `ModuleNotFoundError` because `backend/reports` does not contain an `informe.py`. The CLI entry point cannot execute the `report` command until an implementation exists.
- `backend/etl/consolidar_dia.py:17`: Functions such as `reconocer_cursos`, `region_darkness`, `extract_bold_alternatives`, `get_correct_percent`, `reemplazar_nivel_logro`, `calcular_nivel_logro`, `obtener_nivel`, and `extraer_establecimiento_y_curso` are re-exported in `backend/etl/__init__.py` but no definitions exist anywhere in the repository. Importing this module immediately fails and prevents the ETL path from running.
- `backend/etl/consolidar_dia.py:101`: `df_intermedio.at[:, 8] = establecimiento` (and the similar assignment on the next line) is invalid usage of `DataFrame.at`. The accessor only accepts scalar row/column labels; passing a slice raises `InvalidIndexError`. This stops PDF consolidation before any results are produced.

## High Priority Improvements
- `backend/etl/consolidar_dia.py:69`: When `dic_pages_por_curso` lacks an entry for the derived `curso`, `pages` becomes `None` and both `camelot.read_pdf(..., pages=pages)` and the subsequent `pages.split('-')` fail. Add a guard that either builds a default page range or raises a clear error with context.
- `backend/etl/consolidar_dia.py:87`: The code assumes Camelot returns numeric column keys (0–7) so assignments like `df_intermedio.at[j, 7] = rc` succeed. In practice Camelot often names columns as strings (`"0"`, `"1"`, …), which means these lookups miss the intended column and leave the `% respuestas` column untouched. Normalise the column names (e.g., `df_intermedio.columns = range(df_intermedio.shape[1])`) before iterating.
- `backend/etl/consolidar_dia.py:135`: `consolidar` defaults `dic_pages_por_curso` to `{}`, which silently masks missing mappings and feeds `pages=None` downstream. Consider failing fast (e.g., `if curso not in dic_pages_por_curso: raise KeyError`) so operators know to supply the correct ranges.

## Security & Operational Risks
- `aux_files/credentials.json`: Stores production credentials in plain text and is tracked in Git. Replace with environment variables or a secrets manager, and add the file to `.gitignore` to avoid accidental leaks.
- `aux_files/script_response.py`: Logs full HTML responses (which can contain user data) to disk without sanitisation. Limit the data captured or scrub sensitive fields before writing to prevent data leaks.

## Frontend Observations
- `frontend/src/pages/GenerarInforme.jsx`: Duplicates almost all logic from `frontend/src/InformeFormPrototype.jsx`. Consolidate shared logic into reusable hooks/components to reduce divergence and maintenance effort.
- `frontend/src/pages/GenerarInforme.jsx`: Uses `crypto.randomUUID()`, which is unsupported on older Safari builds. If legacy browser support is required, bundle a lightweight UUID polyfill or fall back to `crypto.getRandomValues`.

## Suggested Next Steps
1. Implement (or restore) the missing ETL helper functions and the report generation module so both CLI commands execute end to end.
2. Add regression tests for `procesar_xls`/`procesar_pdf` covering typical DIA inputs to lock in the data shapes and edge cases.
3. Introduce environment-driven configuration for secrets, file paths, and LaTeX templates to simplify deployment to other environments.
