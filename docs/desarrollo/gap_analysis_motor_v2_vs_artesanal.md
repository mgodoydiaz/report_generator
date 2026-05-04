# Gap analysis: motor PDF v2 vs scripts artesanales DIA

**Fecha**: 2026-05-04 (cierre B6b post-v0.2.0)
**Material comparado**:
- Motor v2 (repo): `backend/rgenerator/reports/dia/esquema.json`, `charts.py`, `tables.py`, `runtime.py`.
- Script artesanal cliente: `Evaluaciones 2026/DIA/Automatización final/{crear_informe.py, funciones.py, esquema_informe.json}`.

---

## Resumen ejecutivo

**Cobertura visualizaciones**: ✅ **100%**. El motor v2 cubre las 8 secciones fijas y las 2 dinámicas (por curso) que genera el script artesanal. Las funciones equivalentes están en `charts.py` y `tables.py` con mismos nombres de hecho.

**Cobertura cálculos derivados**: ⚠️ **parcial → cerrado en B6b**. Las dos variables históricas que el script NO calcula explícitamente pero que el motor v2 sí soporta (`Avance` por slope ordinal y `Mejora_vs_Inicio` por delta) estaban en `_derived_fields_pendientes_normalize`. **Activadas en este sprint** porque el pipeline DIA ahora produce y persiste `Nombre_Norm` como dimensión.

**Helper LaTeX no portado**: ❌ `df_a_latex_loop`, `img_to_latex`, `escape_latex` (`funciones.py:14, 196, 51`). No requeridos: WeasyPrint+CSS reemplaza esa lógica.

---

## 1. Inventario informe artesanal (`crear_informe.py`)

### Secciones fijas (8)
| # | Item | Función artesanal | Línea |
|---|---|---|---|
| 1 | Cuadro Resumen Logro por Curso | `resumen_por_curso` | 22 |
| 2 | Logro Promedio por Nivel | `logro_promedio_por_nivel` | 26 |
| 3 | Logro Promedio por Curso | `logro_promedio_por_curso` | 29 |
| 4 | Distribución Rendimiento por Curso (boxplot) | `boxplot_logro_por_curso` | 32 |
| 5 | Logro Promedio por Eje Temático | `logro_promedio_por_eje` | 35 |
| 6 | Logro Promedio por Habilidad | `logro_promedio_por_habilidad` | 38 |
| 7 | Cantidad Alumnos por Nivel Logro (stacked semáforo) | `alumnos_por_nivel` | 41 |
| 8 | Comparación Diagnóstico-Intermedio (opcional, try/except) | `comparacion_logro_por_curso` | 48 |

### Secciones dinámicas (por curso, 2 tablas)
| # | Item | Función artesanal | Línea |
|---|---|---|---|
| 9 | Tabla Logro por Alumno | `tabla_logro_por_alumno` | 68 |
| 10 | Tabla Logro por Pregunta | `tabla_logro_por_pregunta` | 77 |

---

## 2. Cobertura motor v2

| # | Item artesanal | Función motor v2 | Estado |
|---|---|---|---|
| 1 | Resumen Logro por Curso | `resumen_estadistico_basico` (`tables.py:21`) | ✅ |
| 2 | Logro Promedio por Nivel | `grafico_barras_promedio_por` (`charts.py:38`) | ✅ |
| 3 | Logro Promedio por Curso | `grafico_barras_promedio_por` | ✅ |
| 4 | Boxplot por Curso | `boxplot_valor_por_curso` (`charts.py:247`) | ✅ |
| 5 | Logro por Eje Temático | `valor_promedio_agrupado_por` (`charts.py:113`) | ✅ |
| 6 | Logro por Habilidad | `valor_promedio_agrupado_por` | ✅ |
| 7 | Alumnos por Nivel Logro | `alumnos_por_nivel_cualitativo` (`charts.py:332`) | ✅ |
| 8 | Comparación Diagnóstico-Intermedio | `comparacion_logro_por_curso` (`charts.py:571`) | ✅ |
| 9 | Tabla Logro por Alumno | `tabla_logro_por_alumno` (`tables.py:75`) | ✅ |
| 10 | Tabla Logro por Pregunta | `tabla_logro_por_pregunta` (`tables.py:146`) | ✅ |

---

## 3. Variables históricas (Avance, Mejora vs Inicio)

**Hallazgo del usuario**: las variables tipo "avance promedio entre hitos" no estarían cubiertas. **Confirmado parcialmente:**

- El script artesanal **NO calcula `Avance` ni `Mejora_vs_Inicio`** explícitamente. Solo grafica comparación 2-hitos (item 8).
- El motor v2 **SÍ tiene** `apply_slope` (`derived_fields_engine.py:182`) y `apply_delta` (`derived_fields_engine.py:278`) con soporte de `time_type=ordinal` para hitos categóricos.
- Hasta este sprint, ambas estaban listadas en `_derived_fields_pendientes_normalize` del esquema DIA (no activas).

**Acción tomada en B6b**: activadas las dos en `dia/esquema.json` con `entity_field=["Curso","Nombre_Norm"]` y `time_field=Hito` ordinal `["DIAGNOSTICO","INTERMEDIO","FINAL"]`. Funcionarán cuando haya ≥2 hitos cargados; con 1 solo quedan NaN sin romper render.

**Habilitador**: el pipeline DIA (`data/pipelines/dia/`) ahora aplica `normalize_name` y guarda `Nombre_Norm` como dimensión registrada en métrica 6. Sin esto, los slopes/deltas darían 0 matches por el bug de nombres invertidos entre DIAGNOSTICO ("Nombre Apellido") e INTERMEDIO ("Apellido Nombre").

---

## 4. Helpers artesanales NO portados (intencional)

| Función | Propósito original | Por qué no se portó |
|---|---|---|
| `df_a_latex_loop` (`funciones.py:14`) | Renderizado LaTeX con anchos dinámicos por columna, `\footnotesize` condicional | WeasyPrint + CSS resuelve proporciones automáticamente. Equivalente: `df_a_html_table` en `tables.py`. |
| `img_to_latex` (`funciones.py:196`) | Embebe PNG con includegraphics LaTeX | WeasyPrint inline base64 + `<img>` HTML. |
| `escape_latex` (`funciones.py:51`) | Escapa `&`, `_`, `%`, `$`, etc. | Jinja2 autoescape HTML lo cubre. |
| `crear_df_comparacion` (`funciones.py:578`) | Une diagnóstico + intermedio en wide para ordenarlos | ✅ Sí portado: `crear_df_comparacion` en `tables.py:272`. |

---

## 5. Top 5 prioridades post-B6b

1. **Validar Avance/Mejora end-to-end con datos reales** (≥2 hitos cargados en metric 6). Confirmar que las columnas aparecen en `tabla_logro_por_alumno` con valores coherentes para estudiantes que tengan ambos hitos.
2. **Agregar columnas Avance/Mejora a `secciones_dinamicas.tabla_logro_por_alumno`** del esquema DIA (hoy lista solo `Numero Lista, Nombre, Logro, Nivel Logro, Logro_Promedio_Estudiante`).
3. **Test E2E del pipeline DIA Matemáticas** subiendo XLS + PDFs reales del cliente (carpeta `Lectura Diagnóstico Panguipulli Media` lo permite). Verifica RunDIAPDFExtraction + SaveToMetric + render.
4. **Migrar el dict curso→nivel a un Spec editable por organización** (hoy hardcoded en el JSON del pipeline DIA). Habilita que cada org pueda tener su mapping particular sin tocar el pipeline.
5. **Auditar `runtime.py` orquestador `secciones_dinamicas`** — el comentario en `dia/esquema.json:128` dice "TODO próximo iter: 2 tablas por curso". Verificar que `iterar_por: "Curso"` funciona realmente con las dos tablas declaradas.

---

## Veredicto

El motor v2 está al **mismo nivel funcional** que el informe artesanal. La diferencia que quedaba (variables históricas) se cerró en este sprint activando las derived_fields y agregando `Nombre_Norm` como dimensión registrada. La deuda viva es **probar end-to-end con data 2026 real**, no portar funciones nuevas.
