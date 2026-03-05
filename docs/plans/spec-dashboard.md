# Plan: Spec de Dashboard

## Contexto

Especificación de composición: define qué mostrar en la página de resultados (`Results.jsx`) para una evaluación. No genera artefactos por sí mismo — orquesta la visualización de los gráficos y tablas producidos por otros specs.

Un pipeline puede cargar un spec de Gráficos, uno de Tablas y uno de Dashboard. El Dashboard describe cómo organizar y presentar los resultados en el frontend.

---

## Estructura del config_json

```json
{
  "metadata": {
    "id": "simce_lenguaje_2025_dashboard",
    "title": "Dashboard SIMCE Lenguaje 2025",
    "evaluation": "simce_lenguaje",
    "year": 2025,
    "prueba_num": 1,
    "asignatura": "Lenguaje",
    "description": "Vista de resultados para SIMCE Lenguaje primer semestre"
  },
  "sections": [
    {
      "id": "resumen",
      "title": "Resumen General",
      "type": "mixed",
      "items": [
        { "ref_type": "chart", "ref_id": "rendimiento_promedio_curso" },
        { "ref_type": "table", "ref_id": "resumen_logro_curso" }
      ]
    },
    {
      "id": "detalle_curso",
      "title": "Detalle por Curso",
      "type": "charts",
      "items": [
        { "ref_type": "chart", "ref_id": "distribucion_puntaje_curso" },
        { "ref_type": "chart", "ref_id": "logro_por_nivel_cualitativo" }
      ]
    },
    {
      "id": "preguntas",
      "title": "Análisis por Pregunta",
      "type": "tables",
      "items": [
        { "ref_type": "table", "ref_id": "logro_por_pregunta" },
        { "ref_type": "table", "ref_id": "estadistica_por_pregunta" }
      ]
    }
  ]
}
```

---

## Campos de `metadata`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | string | Identificador único del dashboard |
| `title` | string | Nombre visible en la página de resultados |
| `evaluation` | string | Evaluación asociada |
| `year` | int | Año |
| `prueba_num` | int | Número de prueba |
| `asignatura` | string | Asignatura |
| `description` | string | Descripción libre |

---

## Campos de cada sección en `sections`

| Campo | Obligatorio | Descripción |
|---|---|---|
| `id` | **sí** | Identificador de la sección |
| `title` | **sí** | Título visible en el dashboard |
| `type` | **sí** | `charts` / `tables` / `mixed` — hint de layout para el frontend |
| `items` | **sí** | Lista de referencias a gráficos o tablas |

### Campos de cada item

| Campo | Descripción |
|---|---|
| `ref_type` | `"chart"` o `"table"` |
| `ref_id` | `id` del gráfico/tabla en su spec correspondiente |

---

## Relación con otros specs

El Dashboard **referencia** por `id` los elementos definidos en specs de tipo `Gráficos` y `Tablas`. El pipeline que lo usa carga los tres specs:

```json
{ "step": "LoadConfigFromSpec", "params": { "spec_id": 4 } },  // Gráficos
{ "step": "LoadConfigFromSpec", "params": { "spec_id": 5 } },  // Tablas
{ "step": "LoadConfigFromSpec", "params": { "spec_id": 6 } }   // Dashboard
```

El frontend resuelve las referencias cruzando `ref_id` contra los manifests generados por `GenerateGraphics` y `GenerateTables`.

---

## Preguntas abiertas

- ¿El Dashboard spec se carga en tiempo de ejecución del pipeline, o solo se usa en el frontend para renderizar resultados?
- ¿Un pipeline puede tener más de un spec de Gráficos (ej. uno por asignatura)?

---

## Pendientes de implementación

- [ ] Sección `Dashboard` en `NewSpecDrawer.jsx` para editar `metadata` y `sections`
- [ ] `Results.jsx` consume el Dashboard spec para organizar la vista de resultados
- [ ] Resolver referencias cruzadas entre `ref_id` y manifests generados