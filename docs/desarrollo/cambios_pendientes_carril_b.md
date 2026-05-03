# Carril B — Cambios pendientes al software

Detectados durante el inventario y trabajo de los 5 sub-agentes. **NINGUNO se ha aplicado todavía** — son recomendaciones para revisión.

---

## 1. Hallazgo principal: data 2025 YA ESTÁ CARGADA

Los datos consolidados de SIMCE (Lenguaje + Matemáticas), DIA (Lectura + Matemática), Cálculo Veloz e IDEL ya están en Supabase desde la migración inicial. Total: **15.980 filas** distribuidas:

| id_metric | Métrica | Filas | Cubre |
|---|---|---|---|
| 4 | SIMCE Estudiante | 1090 | LENGUAJE 542 + MATEMATICAS 548 |
| 5 | SIMCE Pregunta | 1420 | ambos |
| 6 | DIA Estudiante | 4712 | LECTURA 2055 + MATEMATICA 2657 |
| 7 | DIA Pregunta | 1320 | ambos |
| 8 | IDEL | 2286 | FNL/FSF/FLO/ILP/CT/VSD |
| 9 | Cálculo Veloz | 5152 | meses ABRIL-OCTUBRE |

Los SQLs generados por los sub-agentes para esas evaluaciones quedaron archivados en `data/evaluaciones_bulk_load/_duplicados_data_ya_cargada/` (sirven como referencia y para regenerar si hay que recargar; no aplicar tal cual).

## 2. Lo que SÍ falta cargar

### Fluidez Lectora 2025
- **No existe la métrica** en BD.
- SQL generado: `data/evaluaciones_bulk_load/fl_2025.sql`. Crea la métrica + carga 321 filas (de 422; 101 sin PPM).
- Métrica propuesta: `Resultados Fluidez Lectora` (data_type=int, unit=PPM).
- **Pendiente decisión**: si aplicar el SQL ahora o esperar más datos.

### En Pullinque todos leemos
- 1 archivo abril 2025 con formato wide (17 hojas por curso, ~542 alumnos).
- No hay métrica creada y la estructura wide requiere transformación.
- **Pendiente decisión**: dejar para cuando haya datos de más meses, o procesar ya y crear métrica `Resultados Pullinque Lectura`.

### DIA 2026 (PDFs)
- 8 PDFs en `Evaluaciones 2026/DIA/Lectura Diagnostico/`.
- El usuario indicó que tiene un software propio para procesarlos. **No se trabaja en este carril**.
- Cuando el output esté listo, se carga vía un SQL bulk como los otros.

---

## 3. Cambios recomendados al software (NO aplicados)

### 3.1 Dimensiones nuevas en tabla `dimensions`

Detectadas durante el análisis, faltan en el catálogo:

| Dimensión | Origen | Justificación |
|---|---|---|
| `PIE` (int 0/1) | Cálculo Veloz | Programa de Integración Escolar; segmentar dashboards por inclusión |
| `Género` (categorical) | IDEL | Segmentación demográfica |
| `Evaluadora` (free text) | IDEL | Trazabilidad de quién evaluó |
| `Nivel de Riesgo` (categorical) | IDEL | Filtrar dashboards por nivel; hoy va en `value` |
| `Categoría` (Muy Baja/Baja/Media/Alta) | Fluidez Lectora | Segmentar por categoría PPM |
| `Letra` (sección del curso) | Fluidez Lectora | Filtrar por sección dentro de un curso |

**Acción propuesta**: migración Alembic que agrega estas dimensiones a `dimensions` y a las `metric_dimensions` correspondientes. Después un script que migre los `dimensions_json` existentes para que usen el `id_dimension` correcto en vez de la llave literal.

### 3.2 Estandarización léxica

- En `id_metric=6` (DIA Estudiante) las habilidades vienen `snake_case`: `Algebra_y_Funciones`, `Interpretar_y_Relacionar`.
- En `id_metric=7` (DIA Pregunta) vienen con espacios y minúscula: `Argumentar y comunicar`, `Interpretar y relacionar`.

Inconsistencia que confunde dashboards y joins. **Acción propuesta**: step de normalización en el ETL (un solo formato canónico, idealmente Title Case con espacios).

### 3.3 Mapeo de niveles de riesgo IDEL

Hoy el `Nivel de Riesgo` viene precalculado en el archivo origen. Si en el futuro queremos recalcular o auditar:

```
FNL: 0 Crítico / 10 Alto / 20 Cierto / 35 Bajo
FSF: 0 / 10 / 35 / 50
FLO: 0 / 10 / 28 / 56
ILP: 0 / 10 / 15 / 20
CT:  0 / 10 / 20 / 30
VSD: 0 / 10 / 20 / 30
```

**Acción propuesta**: persistir como `achievement_levels` del indicador IDEL, o como tabla nueva `metric_thresholds`. Hoy está hardcodeado/implícito.

### 3.4 Indicadores y dashboards faltantes

Hay datos cargados pero no necesariamente indicadores para visualizarlos. Verificar y crear si faltan:

- Indicador para Cálculo Veloz (si no existe ya)
- Indicador para IDEL con `dashboard_layout` que use el mapeo de niveles
- Indicador para Fluidez Lectora (cuando se cargue la métrica)

### 3.5 Calidad de datos detectados

- **Cálculo Veloz**: 5152/5152 filas con `RUT = NaN` (RUT vacío en origen). Sin RUT no se puede hacer match longitudinal entre meses. Hablar con el equipo que genera el archivo.
- **Cálculo Veloz**: 1 fila placeholder evidente (idx 5151: "NOMBRES APELLIDO PATERNO", Puntaje=29025, Nota=2176.4). Filtrar en pre-load.
- **Fluidez Lectora**: 172 filas con RUN nulo (toda la cohorte 2024-12).

**Acción propuesta**: validaciones automáticas en el ETL antes de cargar (ej. abortar si más del 50% de RUTs vienen vacíos en una métrica que los necesita).

### 3.6 Pendientes generales (ya en ROADMAP, recordatorio)

- Tabla `metric_data` está creciendo. Considerar índices compuestos en `(id_metric, org_id)` y en `dimensions_json` con `GIN` si las queries de dashboard se vuelven lentas.
- Dimensión `Curso` (id 5) tiene `validation_mode=list` pero los `dimension_values` pueden no incluir todos los valores que aparecen en los datos cargados (ej: I°A, II°A...). Auditar.

---

## 4. Decisión a tomar con el usuario

1. **¿Aplicar `fl_2025.sql`?** Crea la métrica nueva de Fluidez Lectora y carga 321 filas. (5 min)
2. **¿Trabajar Pullinque ahora?** Requiere transformación wide→long de 17 hojas. (1-2 h con un agente)
3. **¿Implementar los cambios al software 3.1–3.5?** Cada uno es ~30-60 min. Algunos pueden quedar como TODO en ROADMAP.
4. **¿Hacer validaciones automáticas al ETL?** Útil pero no urgente. Mejor cuando volvamos a cargar (DIA 2026).
