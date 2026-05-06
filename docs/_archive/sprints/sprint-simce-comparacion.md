# Plan — Indicador SIMCE Comparación (Pullinque ↔ Panguipulli)

## Contexto

Pullinque ya está cargado en `metric 4` (estudiantes) y `metric 5` (preguntas) con datos ricos
(B/M/O, Puntaje, SIMCE, Nota, Logro, Rend). Panguipulli vino del portal Aptus en formato EMN
y se cargó en `metric 24/25/26` con `PorcLogro`/`LogroNormalizado` agregados (sin pregunta-por-pregunta).
Los formatos son **incompatibles a nivel de métrica fuente** (escalas y semánticas distintas).

**Necesidad**: tener un indicador "**SIMCE Comparación**" para llevar a dirección que muestre
la evolución mes a mes de Pullinque vs Panguipulli en una sola vista, usando como denominador
común el **% de logro** (`Rend` en Pullinque ≈ `PorcLogro` en Panguipulli) más la dimensión
**Habilidad** (que sí existe en ambos lados).

**Decisiones tomadas en esta sesión**:
- Alcance **A2**: mostrar todos los meses de cada colegio (con gaps en meses no coincidentes)
  para que dirección vea la mejora mes a mes de cada uno.
- Camino técnico **A**: métrica derivada nueva, sin tocar metric 4/5/24/25/26 ni el pipeline 26.
- Dejar metrics 24/25/26 + pipeline 26 EMN como están (revisión separada pendiente —
  probablemente se cree un indicador "SIMCE Panguipulli" aparte y luego se decide qué quitar).
- Disclaimer metodológico visible en el indicador (pruebas distintas, escalas distintas).

**Cobertura real disponible para comparar** (consulta SQL ya hecha):

| | Pullinque (metric 4) | Panguipulli (metric 24) |
|---|---|---|
| Niveles | Solo II° medio (4 cursos) | 4°b, 8°b, II° medio (5 cursos) |
| Meses 2025 | Abr, Jun, Ago, Oct, Oct2 | Abr, May, Ago, Sep |
| Asignaturas | LENGUAJE, **MATEMATICAS** (con S) | LENGUAJE, **MATEMATICA**, HISTORIA |
| Métrica común | `Rend` (0–1) | `PorcLogro` (0–1) |
| Intersección estricta | II° medio × LENGUAJE/MATEM × Abr/Ago | (igual) |

Para A2 vamos a mostrar todo y marcar visualmente las celdas no comparables.

---

## Alcance del cambio

### 1. Una métrica derivada nueva

**`metric 27` — "SIMCE Comparación General"** (ID exacto definido por la DB).

- **Dimensiones**: `Establecimiento, Año, Asignatura, Mes, Nivel, Curso, Fuente`
  - Todas existen ya en `dimensions`. Si `Fuente` no existe se crea (1 dimensión nueva).
- **Tipo**: `object`
- **Value JSON**:
  ```json
  {
    "logro_promedio": 0.612,
    "n_estudiantes": 27,
    "fuente_label": "SIMCE-IA" | "EMN-Aptus"
  }
  ```

### 2. Un step custom `BuildSIMCEComparison`

Crearlo en lugar de hacerlo via `LoadMetricToDF` + steps encadenados, porque **no existe step
de groupby ni de concat** entre 2 artifacts (verificado en exploración). Encapsular la lógica
en un step custom es más limpio y reutilizable.

**Lógica del step** (pseudocódigo):
```python
def run(self, ctx):
    df_p = load_metric_data(ctx.db, metric_id=4, org_id=ctx.org_id)   # Pullinque
    df_e = load_metric_data(ctx.db, metric_id=24, org_id=ctx.org_id)  # Panguipulli

    # Normalizar
    df_p['Asignatura'] = df_p['Asignatura'].replace({'MATEMATICAS': 'MATEMATICA'})
    df_p['logro'] = df_p['Rend'].astype(float)
    df_p['Fuente'] = 'SIMCE-IA'
    df_p['Nivel'] = df_p['Curso'].apply(curso_a_nivel)  # 'II A'/'II B' etc → 'II° medio'

    df_e['logro'] = df_e['PorcLogro'].astype(float)
    df_e['Fuente'] = 'EMN-Aptus'
    # Panguipulli ya tiene Nivel

    # Concatenar
    df = pd.concat([df_p, df_e], ignore_index=True)

    # Groupby
    grouped = df.groupby(
        ['Establecimiento','Año','Asignatura','Mes','Nivel','Curso','Fuente']
    ).agg(logro_promedio=('logro', 'mean'),
          n_estudiantes=('logro', 'count')).reset_index()

    ctx.artifacts['comparacion'] = grouped
```

Después un `SaveToMetric(metric_id=27, input_key='comparacion', clear_existing=True)`
persiste todo en la métrica nueva.

### 3. Un pipeline "Reconstruir SIMCE Comparación" (botón en `/pipelines`)

```
InitRun → BuildSIMCEComparison → SaveToMetric(27, clear_existing=True)
```

**Esto responde tu pregunta de "menos manual"**: el usuario va a `/pipelines`, ve el pipeline
"Reconstruir SIMCE Comparación", click "Ejecutar" → recalcula metric 27 → el indicador
queda actualizado. **Sin scripts, sin terminal, sin uploads**.

Cada vez que cambien datos de Pullinque o Panguipulli (futuras cargas), basta con apretar
ese botón para refrescar la comparación.

### 4. Un indicador "SIMCE Comparación"

Crear vía `POST /api/indicators/` con `metric_ids: [27]` (la métrica derivada) más
opcionalmente `[5, 26]` para la pestaña Habilidades.

**`dashboard_layout`** con 4 pestañas:

- **Tab "Vista general"**:
  - Fila de **TrendKPI cards** (`frontend/src/tooling/plotly-charts/trendKpi.jsx`): 4 cards =
    Pullinque-Lenguaje, Pullinque-Mat, Panguipulli-Lenguaje, Panguipulli-Mat — cada una con
    promedio y sparkline mensual.
  - **FilterableTable** (`tables.jsx`) con columnas
    `Asignatura | Mes | Pullinque % | Panguipulli % | Δ (pp)` y celdas en gris cuando uno de
    los dos no tiene datos del mes (caveat A2).

- **Tab "Comparativa por mes"**:
  - 2 charts `DoubleGroupedBar` (`comparison.jsx`), uno por asignatura, eje X = Mes,
    2 barras por mes (Pullinque, Panguipulli).

- **Tab "Evolución temporal"**:
  - `TrendLine` (`evolution.jsx`) con 2 series (1 por colegio), filtros por asignatura y nivel.
    Los meses sin dato del otro colegio se ven como gap natural.

- **Tab "Por habilidad"** *(opcional, si alcanza el tiempo)*:
  - `RadarProfile` (`radar.jsx`) o `BarByGroup` con datos de metric 5 (Pullinque) +
    metric 26 (Panguipulli) — solo II° medio para que sea comparable.

**Disclaimer**: agregar al campo `description` del indicador (que ya se muestra en `/indicators`)
o como una fila de texto al inicio del primer tab:
> "Pullinque proviene de pruebas SIMCE-IA con detalle pregunta a pregunta. Panguipulli proviene
> de Ensayos de Medición Nacional (EMN) Aptus con resultados agregados por OA. La comparación
> se realiza sobre el % de logro promedio, único denominador común. Las escalas y procesos
> son distintos — interpretar como referencial."

---

## Archivos críticos a modificar / crear

### Backend

- `backend/rgenerator/core/etl_steps.py` (o archivo nuevo `comparison_steps.py`):
  agregar la clase `BuildSIMCEComparison(Step)`. Reusa el patrón de `LoadMetricToDF`
  (`metric_steps.py:170+`) para leer `metric_data`.
- `backend/rgenerator/core/pipeline_steps.py`: agregar `from .etl_steps import BuildSIMCEComparison`.
- `backend/rgenerator/tooling/pipeline_tools.py:31` (`STEP_MAPPING`): registrar
  `"BuildSIMCEComparison": ps.BuildSIMCEComparison`.

### Scripts (uno solo, idempotente y reusable)

- `scripts/_create_simce_comparison.py` que crea:
  1. dimension `Fuente` si no existe
  2. metric 27 con sus dimensiones
  3. pipeline "Reconstruir SIMCE Comparación"
  4. indicator "SIMCE Comparación" con `dashboard_layout` armado

### Frontend

**Cero código nuevo**. Todos los charts ya existen en `frontend/src/tooling/plotly-charts/`:
- `comparison.jsx::DoubleGroupedBar`
- `tables.jsx::FilterableTable, SummaryTable`
- `trendKpi.jsx::TrendKPI`
- `evolution.jsx::TrendLine`
- `radar.jsx::RadarProfile`

Y todos están registrados en `dashboardRenderer.jsx::COMPONENT_MAP`.

El `dashboard_layout` JSON del indicador es lo único nuevo, y va en la DB.

---

## Verificación end-to-end

1. **Setup DB**: ejecutar `docker exec report_generator-backend-1 python scripts/_create_simce_comparison.py`.
   Verifica que crea: metric 27, pipeline nuevo, indicator nuevo. SQL:
   ```sql
   SELECT id_metric, name FROM metrics WHERE name LIKE 'SIMCE Comparación%';
   SELECT pipeline_id, pipeline FROM pipelines WHERE pipeline LIKE 'Reconstruir SIMCE%';
   SELECT id_indicator, name FROM indicators WHERE name LIKE 'SIMCE Comparación%';
   ```

2. **Ejecutar el pipeline desde la UI**: ir a `http://localhost:5173/pipelines`,
   buscar "Reconstruir SIMCE Comparación", click "Ejecutar". Esperar respuesta `success`.

3. **Validar metric 27**: SQL
   ```sql
   SELECT
     (md.dimensions_json::jsonb)->>'3' AS estab,
     (md.dimensions_json::jsonb)->>'8' AS asig,
     (md.dimensions_json::jsonb)->>'9' AS mes,
     COUNT(*) AS rows
   FROM metric_data md WHERE id_metric=27
   GROUP BY 1,2,3 ORDER BY 1,2,3;
   ```
   Debe mostrar Pullinque (5 meses × 2 asig) + Panguipulli (4 meses × 3 asig × 3 niveles).

4. **Validar indicador en UI**: ir a `http://localhost:5173/indicators`, abrir "SIMCE Comparación".
   - Vista general muestra 4 cards KPI con números coherentes.
   - Tabla con Δ tiene celdas en gris donde corresponde (Junio Pullinque sin Panguipulli, etc).
   - Tabs comparativa/evolución renderizan los charts.

5. **Smoke test del backend**: `curl http://localhost:8000/api/results/indicator/{id}/data | jq`
   debe devolver data de las 3 metrics asociadas.

6. **Re-run idempotencia**: re-ejecutar el pipeline desde UI, confirmar que los rows de
   metric 27 quedan iguales (clear_existing=True borra y reescribe sin duplicar).

---

## Pendientes explícitamente fuera de alcance

- Crear indicador "SIMCE Panguipulli" individual a partir de metric 24/25/26 — *queda pendiente*.
- Decidir si quitar metric 24/25/26 y pipeline 26 — *queda pendiente*.
- Cargar datos 2024 del ZIP — *queda pendiente*.
- Hacer commit a git — *cuando todo esté validado y aprobado*.

---

## Ubicación del plan

Este archivo está en:
**`C:\Users\magod\.claude\plans\1-a2-para-ir-groovy-starfish.md`**

(No está en el Desktop directo — está en la carpeta `.claude\plans\` del perfil del usuario,
que es donde Claude Code persiste los planes generados en modo Plan.)
