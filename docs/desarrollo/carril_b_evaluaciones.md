# Carril B — Carga masiva de evaluaciones 2025/2026

Documento maestro del trabajo de poblar la base de datos con todas las evaluaciones de Fundación PHP. Generado el 2026-04-27.

## Estrategia general

1. **Datos 2025 ya consolidados** (Excel "compilado" / "long") → carga directa a `metric_data` vía SQL bulk insert. **No pasan por pipeline ETL**.
2. **DIA 2026 (PDFs)** → procesado con el software ya hecho por el usuario. No lo tocamos en este carril.
3. **Datos generados se dejan en `data/evaluaciones_bulk_load/<evaluacion>.sql`** listos para revisión y aplicación con `psql`.
4. **Cambios al software** (modelos, dimensiones nuevas, dashboards, frontend) se documentan en `docs/desarrollo/cambios_pendientes_carril_b.md`. **No se aplican** hasta revisión con el usuario.

## Modelo de datos en `metric_data`

Cada fila del compilado se transforma a 1 fila en `metric_data` por columna métrica relevante. Patrón:

```sql
INSERT INTO metric_data (id_metric, value, dimensions_json, org_id) VALUES
(<id_metric>, '<valor>', '{"campo1": "v1", "campo2": "v2", ...}'::text, 1);
```

`id_metric` ya existe en BD para todas las evaluaciones (verificado):
| id_metric | Nombre |
|---|---|
| 4 | Resultados SIMCE por Estudiante |
| 5 | Resultados SIMCE por Pregunta |
| 6 | Resultados DIA por estudiante |
| 7 | Resultados DIA por Pregunta |
| 8 | Resultados IDEL |
| 9 | Resultados Cálculo Veloz |

`org_id = 1` (Fundación PHP). Todos los datos van a la misma org por ahora.

## Inventario de archivos detectado

### SIMCE 2025 (LENGUAJE — ya cargado, verificar Matemáticas)
- `SIMCE/Compilado/simce_2025_estudiantes.xlsx`: 1090 filas, 15 cols (Lenguaje 5 procesos: Abril/Junio/Agosto/Octubre/Octubre 2)
- `SIMCE/Compilado/simce_2025_preguntas.xlsx`: 1420 filas, 16 cols
- **TODO**: verificar si hay datos de SIMCE Matemáticas en otra carpeta o si todavía no se han recolectado

### DIA 2025 (Lenguaje + Matemáticas)
- `DIA/Compilado/dia_2025_estudiantes_long.xlsx`: 4712 filas, 12 cols. **Este es el bueno** (formato long).
  Cols: Nombre, Numero Lista, Curso, Establecimiento, Asignatura (LECTURA/MATEMATICA), Hito, Año, **Habilidad**, Logro, Nivel Logro, Nivel, Logro Promedio
- `DIA/Compilado/dia_2025_preguntas.xlsx`: 1320 filas, 13 cols

### Cálculo Veloz 2025
- `Cálculo Veloz/Datos/CV_2025_Compilado_Completo.xlsx`: 5152 filas, 12 cols (formato long, ideal)
  Cols: Establecimiento, Año, Curso, RUT, Nombre, Mes, N Prueba, Fecha, Puntaje, Nota, Nivel, PIE
- (Otros 3 Excel son versiones derivadas o wide; usamos solo el "Completo")

### Fluidez Lectora 2025
- `Fluidez Lectora/Datos/Consolidado_Agosto.xlsx`: 424 filas, 8 cols
  Cols: Nivel, Letra, Curso, Evaluación, RUN, Nombre, Cantidad PPM, Nivel
  + hoja "Parámetros" con rangos de categorías
- **Solo Agosto disponible** — falta verificar otros meses

### IDEL 2025
- `IDEL/Consolidado_IDEL_2025_largo.xlsx`: 2286 filas, 11 cols (formato long, ideal)
  Cols: Establecimiento, Año, RUT, Nombre, Curso, Género, Evaluadora, Evaluación (FNL/FSF/FLO), Versión, Puntaje, Nivel de Riesgo
- `IDEL/Mapeo_Niveles.xlsx`: tabla de niveles de riesgo por puntaje y evaluación

### En Pullinque todos leemos
- Carpeta `Datos/` — pendiente inspeccionar contenido

### DIA 2026 (PDFs)
- 8 PDFs en `Evaluaciones 2026/DIA/Lectura Diagnostico/`
- **Proceso aparte con el software del usuario.** No se carga en este carril.

## Cambios pendientes al software (documentados)

Ver archivo separado: `docs/desarrollo/cambios_pendientes_carril_b.md`

## Estado de archivos generados

| Evaluación | Archivo SQL | Filas estimadas | Status |
|---|---|---|---|
| SIMCE Lenguaje 2025 | (ya cargado) | 15.980 | ✅ |
| SIMCE Matemáticas 2025 | _pendiente verificar archivo origen_ | — | ⏸️ |
| DIA Lenguaje 2025 | `dia_2025.sql` | ~4700 (long) | ⏳ |
| DIA Matemáticas 2025 | (mismo archivo) | (compartido) | ⏳ |
| Cálculo Veloz 2025 | `cv_2025.sql` | ~5100 | ⏳ |
| Fluidez Lectora 2025 | `fl_2025.sql` | ~420 | ⏳ |
| IDEL 2025 | `idel_2025.sql` | ~2300 | ⏳ |
| Pullinque | (a inspeccionar) | — | ⏸️ |

## Cómo aplicar (después de revisión)

```bash
# Revisar contenido del SQL
less data/evaluaciones_bulk_load/cv_2025.sql

# Aplicar a Supabase (un archivo a la vez para control)
PGPASSWORD='<password>' psql \
  -h aws-1-sa-east-1.pooler.supabase.com -p 5432 \
  -U postgres.xcpywlikzjdvhihlfbrn -d postgres \
  -v ON_ERROR_STOP=1 \
  -f data/evaluaciones_bulk_load/cv_2025.sql

# Verificar que cargó
PGPASSWORD='<password>' psql ... -c \
  "SELECT count(*) FROM metric_data WHERE id_metric = 9;"
```

Cada SQL incluye:
- Validación de pre-condiciones (la métrica existe)
- INSERTs en lotes con `ON CONFLICT DO NOTHING` para idempotencia
- Comentario al final con el `expected_count`
