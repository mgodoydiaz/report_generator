# Sprint 2026-05-01 — Handoff

**Estado**: en pausa, listo para migrar a otra sesión.
**Objetivo del sprint**: dejar 3 PDFs validables (DIA, Fluidez Lectora, Cálculo Veloz) con datos 2026, sanear las métricas FL/CV al formato canónico y crear pipelines reproducibles.
**Plan completo**: [C:\Users\magod\.claude\plans\c-users-magod-documents-proyectos-infor-merry-sunset.md](file:///C:/Users/magod/.claude/plans/c-users-magod-documents-proyectos-infor-merry-sunset.md)

---

## ⚠️ COORDINACIÓN CON LA OTRA SESIÓN — leer antes de editar código

La sesión paralela "Document pending tasks and project status" también está trabajando con WeasyPrint. **Esta sesión ya modificó `backend/rgenerator/core/report_steps.py`** — si la otra sesión toca el mismo archivo va a haber conflicto en merge.

**Cambios concretos hechos aquí en `report_steps.py`:**

1. **Helpers nuevos justo después de `_to_field_name` (~línea 135)**:
   - `_KNOWN_ROLES` — set con `{'logro_1', 'logro_2', 'nivel_de_logro', 'habilidad', 'habilidad_2', 'evaluacion_num', 'calidad_lectora'}`.
   - `_resolve_field(field, column_roles)` — convierte `_logro_1` → `_cantidad` (FL) o `_nota` (CV) usando el primer entry de `column_roles[role]`. Soporta lista, string y devuelve original si no aplica.
   - `_achievement_levels(indicator)` — parsea `indicator.achievement_levels` y devuelve lista `[{name, color, order}]`.
   - `_natural_sort_key(s)` — split numérico para ordenar cursos `1° MEDIO A < 1° MEDIO B < 2° MEDIO A`.

2. **`_chart_to_png_b64` modificado**:
   - **Firma cambia**: `def _chart_to_png_b64(item, records, indicator=None)` — ahora acepta `indicator` para resolver column_roles.
   - **Resuelve fields**: `x_field`, `y_field`, `group_field`, `period_field`, `level_field` pasan por `_resolve_field` al inicio.
   - **Nuevas ramas (en orden)**: `StackedCountByGroup` / `DistribucionNiveles` (idéntico tratamiento), `GroupedBarByPeriod`, `BarByGroup` (con soporte multi-valueField). Las ramas viejas (`HeatmapMatrix`, `GaugeIndicator`, `Histogram`, else genérico) quedan intactas.

3. **`_table_section` modificado**:
   - **Firma cambia**: `def _table_section(item, records, indicator=None)`.
   - **Nueva rama al inicio**: `SummaryTable` y `TablaResumenCursos` — devuelve `{Curso, Alumnos, <campo> prom./mín./máx., counts por achievement_level}`.
   - Las ramas viejas (`PivotTable`, FlatTable) quedan intactas.

4. **`build_pdf_bytes` modificado**: dos llamadas pasan ahora `indicator=indicator`:
   ```python
   b64 = _chart_to_png_b64(item, records, indicator=indicator)
   tdata = _table_section(item, records, indicator=indicator)
   ```

**Si la otra sesión también tocó report_steps.py**: hacer `git diff` o `git stash` antes de editar más, y mergear manual. **NO usar git checkout/reset destructivos** sin coordinar.

**Si la otra sesión instaló WeasyPrint en otro env (WSL Ubuntu vía pip o un nuevo conda env)**: igualmente sirve; el código modificado se cargará desde ahí. Pero el smoke test debe correr donde WeasyPrint esté disponible (este sprint usó el container Docker `report_generator-backend-1`).

---

## Decisiones tomadas (no reabrir)

1. **CV value** = `{Puntaje, Nota, Nivel}` con Nivel calculado en ETL desde rangos del xlsx. **PIE eliminado.**
2. **FL value** = `{Cantidad, Categoria, Calidad lectora}` (PPM renombrado a Cantidad — alineado con xlsx canónico).
3. **DIA queda intacta** — métricas 6 y 7 se mantienen como están. Sólo se genera informe con datos cargados.
4. **Estrategia PDF**: se reúsa `Indicator.pdf_layout` y se completa `_chart_to_png_b64` con los componentes faltantes. NO se reemplaza el motor por un script estilo `referencia_informe/`.
5. **Trabajamos en local primero** — Supabase prod queda intacto hasta validar.

---

## Qué quedó LISTO (✅)

### DB local (Windows nativo PG18 + Docker PG16, sincronizadas)

| Cambio | Detalle |
|---|---|
| Dim **22 Seguimiento** | Nueva, validation_mode=list, valores: Normal, Intensivo |
| Metric **10 Resultados Fluidez Lectora** | Creada en local con meta_json `{Cantidad, Categoria, Calidad lectora}`, vinculada al indicator 5, 10 dimensiones registradas |
| Metric **9 Resultados Cálculo Veloz** | meta_json actualizado a `{Puntaje, Nota, Nivel}` (PIE removido) |
| Indicator **5 (FL)** | column_roles ahora apuntan a `Cantidad`/`Categoria`/`Calidad lectora`/`Evaluación`. role_labels actualizado |
| Spec **6 ETL Fluidez Lectora 2026** | header_row=0, rename `Rut→RUT` y `Prueba→Evaluación`, enrich `Año` por archivo (user_input) |
| Spec **7 ETL Cálculo Veloz 2026** | header_row=0, rename `Rut→RUT` y `N Evaluación→N Prueba`, enrich `Año` y `Establecimiento` |
| Pipeline **22 Cargar Fluidez Lectora 2026** | Steps: InitRun → LoadConfigFromSpec → RequestUserFiles → EnrichWithUserInput → RunExcelETL → ModifyColumnValues (Mes desde Fecha, Nivel desde Curso) → SaveToMetric(metric_id=10) |
| Pipeline **23 Cargar Cálculo Veloz 2026** | Steps: InitRun → LoadConfigFromSpec → RequestUserFiles → EnrichWithUserInput → RunExcelETL → ModifyColumnValues (concat Nombre+Apellido, Nivel y Nota piecewise desde Puntaje) → SaveToMetric(metric_id=9) |
| Users de prod traídos a local | 7 users + 2 organization_assets metadata vía pg_dump filtrado (binarios siguen en Railway) |
| Pipeline **21 DIA Lenguaje** | description marcado como "PENDIENTE: completar steps cuando haya xlsx 2026 muestra". Datos DIA 2025 (4712 estudiantes + 1320 preguntas) ya cargados en local |

### Código modificado

- [backend/rgenerator/core/report_steps.py](backend/rgenerator/core/report_steps.py)
  - **Helpers nuevos**: `_resolve_field(field, column_roles)` — convierte `_logro_1` → `_cantidad`/`_nota`. `_KNOWN_ROLES` set. `_achievement_levels(indicator)`. `_natural_sort_key(s)` para orden de cursos.
  - **`_chart_to_png_b64` ampliado** con ramas: `StackedCountByGroup`, `DistribucionNiveles`, `GroupedBarByPeriod`, `BarByGroup` (multi-value). Firma cambia: ahora acepta `indicator` para resolver roles.
  - **`_table_section` ampliado**: `SummaryTable`, `TablaResumenCursos` — devuelven Curso/Alumnos/Promedio/Mín/Máx/counts por nivel. Misma firma extendida con `indicator`.
  - **`build_pdf_bytes`** ahora pasa `indicator` a ambos helpers.

### Scripts creados

- [scripts/_create_fl_cv_specs_pipelines.py](scripts/_create_fl_cv_specs_pipelines.py) — idempotente, recrea specs y pipelines FL/CV 2026.
- [scripts/_smoke_pdf.py](scripts/_smoke_pdf.py) — smoke test: genera PDF para indicator dado vía `build_pdf_bytes`.
- [scripts/_test_chart_helpers.py](scripts/_test_chart_helpers.py) — testea cada chart/table del pdf_layout sin renderizar PDF completo (genera PNGs sueltos en `/tmp/chart_smoke/`).

### Backups

| Archivo | Qué contiene |
|---|---|
| [backups/metric10_fluidez_pre_fix_20260430_164026.json](backups/metric10_fluidez_pre_fix_20260430_164026.json) | Estado de FL en Supabase prod ANTES del fix de ayer (321 filas, PPM/Categoria/Letra) |
| [backups/local_pre_bloque1_20260501_204536.json](backups/local_pre_bloque1_20260501_204536.json) | Estado local ANTES del bloque 1 de hoy (5152 metric_data CV viejos, etc) |
| [backups/auth_prod_20260501_204251.sql](backups/auth_prod_20260501_204251.sql) | Dump de organizations/users/organization_assets de Supabase prod |
| [backups/local_full_20260501_210014.sql](backups/local_full_20260501_210014.sql) | Dump completo del PG nativo Windows POST bloque 1+2 (3.5 MB) |

---

## Qué quedó PENDIENTE (⏳)

### Crítico para terminar el sprint

1. **Cargar datos 2026 reales en FL y CV.**
   El usuario tiene xlsx con formato canónico (`Formatos recomendados.xlsx` hojas FL Hoja / CV Formato). Subirlos vía pipeline 22 o 23 desde el frontend.
   - FL columnas esperadas: `Establecimiento, Prueba, Curso, Fecha, Seguimiento, Rut, Nombre, Cantidad, Categoria, Calidad lectora`
   - CV columnas esperadas: `Curso, Mes, N Evaluación, Fecha, Rut, Nombre, Apellido, Puntaje, Nota`

2. **Smoke test de PDF dentro del backend Docker.**
   Quedó el container con código actualizado pero el script `_test_chart_helpers.py` falló porque hardcodea `DATABASE_URL=localhost`. Dentro del container hay que dejar la env var por defecto (`db:5432`) o pasar `host.docker.internal:5432` (ver Caveats).
   Comando esperado:
   ```bash
   wsl -d Ubuntu bash -c "docker exec -w /app -e DATABASE_URL='postgresql://mgodoy:holapocompadre977@db:5432/rgenerator_dev' report_generator-backend-1 python scripts/_test_chart_helpers.py"
   ```
   (El script setea `os.environ['DATABASE_URL']` a localhost — hay que **eliminar esa línea** para que respete la env del container.)

3. **Ajustar `pdf_layout` de cada indicator** una vez los gráficos se rendericen sin errores.
   - **FL (id 5)**: layout actual ya razonable. Agregar sección "Calidad lectora por curso" usando `StackedCountByGroup` con `levelField=_calidad_lectora`. Actualizar texto de Notas con rangos del xlsx.
   - **CV (id 4)**: layout flaco. Agregar tabla detalle por curso (lista alumnos ordenados por Puntaje desc).
   - **DIA (id 2)**: probablemente OK tal como está, sólo verificar que renderice con los datos 2025 cargados.

4. **Generar y validar los 3 PDFs** end-to-end. Iterar layouts si hace falta.

### Mejoras opcionales del Bloque 3 (sólo si sobra tiempo)

5. **Bloque 3.3 — Editor frontend de pdf_layout**. Hoy obliga a JSON crudo. Mejora mínima propuesta en el plan: validar que `component` exista en `COMPONENT_MAP` antes de guardar, y mostrar `caption`/`heading` como inputs separados (no un único textarea).
   Archivos: [frontend/src/pages/Indicators.jsx](frontend/src/pages/Indicators.jsx), [frontend/src/components/LayoutEditorModal.jsx](frontend/src/components/LayoutEditorModal.jsx).

### No urgente (mismo día / sprint actual)

6. **Skill `pdf-table-extract`** — Bloque 4 del plan. Crear `.claude/skills/pdf-table-extract/SKILL.md` que envuelva camelot-py para extraer tablas de PDF con 0–1 parámetros. Debe:
   - Inferir el PDF (último en `data/input/` o el adjunto al chat)
   - Probar `flavor='lattice'` y `flavor='stream'` y elegir el mejor por confidence
   - Mostrar preview (head 10) de cada tabla
   - Sugerir `column_mapping` para reusar en un Spec ETL

7. **Sincronizar cambios validados a Supabase prod** — al final del día. Actualmente Supabase está en estado pre-fix de hoy (todavía tiene PPM/Categoria/Letra en FL, sin metric 10 nueva, sin specs/pipelines 2026, con los 5152+321 metric_data viejos). **El usuario sigue debiendo borrar `metric_data` 9 y 10 viejos en prod** antes de cualquier sync. Posible camino: aplicar el dump local a prod (con cuidado de no pisar lo que ya está allá) o re-correr los mismos UPDATE/INSERT contra prod en orden.

### Para días siguientes (Bloque 5 del plan, no hoy)

8. **Versión profesor / versión directivo** de cada informe — un mismo `Indicator` con dos campos `pdf_layout_profesor` y `pdf_layout_directivo` (preferido por simplicidad), o dos `Indicator` separados. Decidir cuando lleguemos.
9. **Pipelines de carga para EPTL e IDEL 2026** — IDEL ya tiene métrica (id 8). EPTL no — crear desde cero (formato en hoja `EPTL Formato` del xlsx).
10. **Eliminar duplicación matplotlib/Plotly** o documentar la divergencia formal — no es bloqueante pero genera confusión a mediano plazo.
11. **Pipeline DIA Lenguaje completo** cuando haya xlsx 2026.

---

## Verificación end-to-end (extracto del plan)

Para cada uno de los 3 informes, verificar:

1. **Métrica saneada**:
   ```sql
   SELECT data_type, unit, meta_json FROM metrics WHERE id_metric IN (9,10);
   ```
   → tipos `object`, `unit=''`, `fields` lista las columnas del xlsx.

2. **Dimensiones registradas**:
   ```sql
   SELECT id_dimension FROM metric_dimensions WHERE id_metric IN (9,10) ORDER BY id_metric, id_dimension;
   ```
   → FL (10): `[3, 4, 5, 6, 7, 9, 15, 19, 21, 22]`. CV (9): `[3, 4, 5, 6, 7, 9, 10, 21]`.

3. **Carga reproducible**: subir el xlsx 2026 desde el frontend, ejecutar pipeline 22 (FL) o 23 (CV), verificar que `metric_data` se popula con `value` y `dimensions_json` correctos.

4. **Dashboard funciona**: abrir `/indicators/<id>` en el frontend (5, 4 o 2), verificar KPIs + tabla resumen + gráficos sin error en consola.

5. **PDF se genera**: ejecutar `RenderPDFReport` con `indicator_id` correspondiente o llamar el endpoint `/api/indicators/{id}/pdf`. Abrir el PDF — todas las secciones renderizan, no hay PNGs en blanco, las tablas tienen datos. Si una sección sale vacía: revisar que `valueField`/`groupField` del item resuelvan a una columna que existe en `records` (probablemente falta el `_resolve_field` o la rama del componente).

6. **Categorización correcta**:
   - **CV**: Puntaje=50 → Nivel="BÁSICO", Nota = 0.016667·50 + 1 = 1.83 (redondeado)
   - **CV**: Puntaje=80 → Nivel="AVANZADO", Nota = 0.075·80 - 0.5 = 5.5
   - **FL**: Cantidad=140 → Categoria="BAJA"; Cantidad=200 → "ALTA"

Comando útil de smoke (dentro del backend Docker):
```bash
wsl -d Ubuntu bash -c "docker exec -w /app report_generator-backend-1 python scripts/_smoke_pdf.py 5 /tmp/fl_local.pdf"
```
(El script `_smoke_pdf.py` también hardcodea `DATABASE_URL=localhost`. Quitar esa línea para que respete la env del container que apunta a `db:5432`.)

---

## Caveats / cosas a tener presentes

### Hay DOS PG locales corriendo en 5432

- **PG 18 nativo Windows** (`localhost:5432`, instalación en `C:\Program Files\PostgreSQL\18`) — donde hice todo el trabajo Bloque 1 y 2.
- **PG 16 Docker** dentro de WSL Ubuntu (container `report_generator-db-1`, alias `db:5432` en la red Docker) — usa el backend Docker.
- Los puertos chocan en el host pero el nativo Windows ganó. El backend Docker llega a su PG por DNS interno (`db`), no por `localhost`.
- **Sincronicé Docker → nativo** cargando el dump completo (`backups/local_full_20260501_210014.sql`) al PG Docker. Si reinicias los containers con volumes nuevos, ese estado se pierde.

### El conda env `rgenerator` está roto

- `pip install` falla por `ImportError: DLL load failed while importing pyexpat`.
- Workaround: usar el `python3` global de Windows (C:\Python313) o el container Docker.

### WeasyPrint no funciona en Windows nativo (falta GTK)

- En Windows nativo: `OSError: cannot load library 'libgobject-2.0-0'`.
- WSL Ubuntu sí podría funcionar pero no tiene `pip` instalado.
- **Solución usada**: backend Docker tiene WeasyPrint preinstalado vía `requirements.txt`. Ahí es donde hay que generar los PDFs.

### Hot-reload del backend Docker está activo

- El compose monta `.:/app` como bind mount.
- Mis cambios a `backend/rgenerator/core/report_steps.py` ya se reload-earon en el container (verificado en logs: `WatchFiles detected changes ... Reloading`).

### Sesión paralela existe

- Sesión "Document pending tasks and project status" (id `local_8414f51a-5adc-4ada-95fd-baf304da910a`), no corriendo, último activity 2026-05-01 20:48 UTC.
- No pude leer su transcript desde aquí (modo no-supervisado).
- El usuario va a continuar este sprint desde esa sesión usando este handoff como base.

### Dato curioso del Bloque 1 que NO causé yo

Cuando inspeccioné FL post-fix detecté que **172 de 321 filas en Supabase prod no tienen RUT (dim 6)** — todas las de 2° MEDIO. Es del ETL original, no del fix. Implicación: cualquier cruce estudiante-respuesta en 2° MEDIO se hace por Nombre (ambiguo). Para el sprint actual no importa porque vamos a recargar datos 2026 de cero, pero anótarlo como deuda en prod.

---

## Cómo retomar desde la otra sesión

```bash
# 1. Verificar que Docker está up con los 3 servicios
wsl -d Ubuntu bash -c "docker ps"

# 2. Verificar estado de la DB Docker (debe matchear nativo Windows)
wsl -d Ubuntu bash -c "docker exec report_generator-db-1 psql -U mgodoy -d rgenerator_dev -c 'SELECT id_metric, name FROM metrics ORDER BY id_metric; SELECT pipeline_id, pipeline FROM pipelines ORDER BY pipeline_id;'"

# 3. Si la DB Docker se reseteó, recargar el dump:
wsl -d Ubuntu bash -c "docker exec -i report_generator-db-1 psql -U mgodoy -d rgenerator_dev < /home/atlas/proyectos/report_generator/backups/local_full_20260501_210014.sql"

# 4. Smoke test del PDF (después de quitar el override de DATABASE_URL del script)
wsl -d Ubuntu bash -c "docker exec -w /app report_generator-backend-1 python scripts/_test_chart_helpers.py"

# 5. Levantar el frontend si está abajo
# (puerto 5173 ya está exponido por el container)
```

Frontend: http://localhost:5173 — ya hay 7 users de prod cargados, login con cualquiera de ellos.
Backend API: http://localhost:8000/docs — Swagger UI disponible.

---

## Referencias del repo

- [docs/desarrollo/referencia_informe/](docs/desarrollo/referencia_informe/) — código de referencia DIA y SIMCE, base para gráficos genéricos parametrizables.
- `Formatos recomendados.xlsx` — formato canónico de captura (FL, CV, EPTL).
- [CLAUDE.md](CLAUDE.md) — guía global del proyecto.
- [ROADMAP.md](ROADMAP.md) — pendientes a más largo plazo.
