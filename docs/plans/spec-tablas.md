# Plan: Spec de Tablas

## Contexto

Especificación para definir el conjunto de tablas a generar en una evaluación. Análoga al spec de Gráficos, pero orientada a producir archivos Excel (`.xlsx`) mediante funciones de `report_tools.py`.

---

## Estructura del config_json

```json
{
  "metadata": {
    "id": "simce_lenguaje_2025_tablas",
    "title": "Tablas SIMCE Lenguaje 2025",
    "evaluation": "simce_lenguaje",
    "year": 2025,
    "prueba_num": 1,
    "asignatura": "Lenguaje",
    "description": "Tablas de logro y estadísticas por curso"
  },
  "tables_list": [
    {
      "id": "resumen_logro_curso",
      "title": "Resumen de Logro por Curso",
      "category": "resumen",
      "type": "resumen_estadistico_basico",
      "input_key": "df_estudiantes",
      "output_filename": "resumen_logro_por_curso.xlsx",
      "iterate_by": null,
      "params": {
        "columna": "Rendimiento",
        "formato": "percent",
        "agrupar_por": "Curso"
      }
    },
    {
      "id": "logro_por_alumno",
      "title": "Logro por Alumno",
      "category": "detalle_curso",
      "type": "tabla_logro_por_alumno",
      "input_key": "df_estudiantes",
      "output_filename": "logro_por_alumno_{val}.xlsx",
      "iterate_by": "Curso",
      "params": {
        "parametros": {},
        "sort_by": "Rend"
      }
    }
  ]
}
```

---

## Campos de `metadata`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | string | Identificador único del conjunto |
| `title` | string | Nombre legible para el dashboard |
| `evaluation` | string | Evaluación asociada (ej. `simce_lenguaje`) |
| `year` | int | Año de la evaluación |
| `prueba_num` | int | Número de prueba dentro del año |
| `asignatura` | string | Asignatura evaluada |
| `description` | string | Descripción libre |

---

## Campos de cada entrada en `tables_list`

| Campo | Obligatorio | Descripción |
|---|---|---|
| `id` | recomendado | Identificador corto para referencia |
| `title` | recomendado | Nombre legible para el dashboard |
| `category` | opcional | Agrupación en dashboard (`resumen`, `detalle_curso`, etc.) |
| `type` | **sí** | Nombre de la función en `report_tools.py` |
| `input_key` | **sí** | Artifact(s) del contexto — `string` o `list[string]` |
| `output_filename` | **sí** | Nombre del `.xlsx` generado. Si usa `iterate_by`, incluir `{val}` |
| `iterate_by` | opcional | Columna por la que iterar — genera una tabla por valor único |
| `params` | **sí** | Parámetros específicos de la función |

---

## Funciones disponibles en `report_tools.py`

| `type` | Descripción |
|---|---|
| `resumen_estadistico_basico` | Stats (N, mean, min, max) agrupados por columna |
| `tabla_logro_por_alumno` | Tabla de logro por estudiante, ordenable |
| `tabla_logro_por_pregunta` | Tabla de logro por pregunta |
| `crear_tabla_estadistica_por_pregunta` | Distribución de respuestas (A/B/C/D/E) por pregunta |

---

## Pendientes de implementación

- [ ] Sección `Tablas` en `NewSpecDrawer.jsx` para editar `metadata` y `tables_list`
- [ ] `GenerateTables` lee `tables_list` desde `ctx.params["tables_spec"]["tables_list"]`
- [ ] `GenerateTables` genera `tables_manifest.json` en `aux_files/`