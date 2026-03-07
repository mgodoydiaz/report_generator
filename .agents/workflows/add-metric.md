---
description: Crear una nueva métrica
---
# `/add-metric` — Crear una nueva métrica

Skill ejecutable: El asistente guía el proceso interactivamente, lee los archivos Excel actuales y escribe los cambios directamente.

## Instrucciones para el Asistente

Al invocar este skill, seguir estos pasos en orden:

**1. Recopilar información del usuario**

Preguntar (puede ser en un solo mensaje):
- Nombre de la métrica
- Tipo de dato: `int`, `float`, `str`, u `object` (si tiene múltiples campos de valor)
- Si el tipo es `object`: nombres y tipos de cada campo de valor
- Dimensiones de segmentación requeridas (ej. Año, Curso, Asignatura)
- Descripción y unidad (opcionales)

**2. Leer el estado actual de los Excel**

```python
import pandas as pd
from pathlib import Path

DB = Path("data/database")
df_dim = pd.read_excel(DB / "dimensions.xlsx")
df_met = pd.read_excel(DB / "metrics.xlsx")
df_md  = pd.read_excel(DB / "metric_dimensions.xlsx")
```

Mostrar al usuario las dimensiones existentes para que confirme cuáles reutilizar y cuáles hay que crear.

**3. Crear dimensiones faltantes** (si aplica)

Para cada dimensión nueva, agregar una fila a `dimensions.xlsx`:
- `id_dimension`: último ID existente + 1 (incrementar por cada nueva)
- `name`: nombre de la dimensión
- `data_type`: tipo del valor (`str`, `int`, `float`)
- `validation_mode`: `'free'` (cualquier valor) o `'list'` (valores controlados)

**4. Crear la métrica en `metrics.xlsx`**

Agregar una fila con:
- `id_metric`: último ID existente + 1
- `name`, `data_type`, `description`, `unit`, `created_at` (datetime actual)
- `meta_json`:
  - Tipo simple (`int`, `float`, `str`): `{}`
  - Tipo `object`: `{"fields": [{"name": "Campo", "type": "float"}, ...]}`

**5. Relacionar métrica con dimensiones en `metric_dimensions.xlsx`**

Por cada dimensión asociada, agregar una fila:
- `id`: último ID existente + 1 (incrementar por cada relación)
- `id_metric`: ID de la métrica recién creada
- `id_dimension`: ID de cada dimensión

**6. Confirmar antes de guardar**

Mostrar un resumen de todos los cambios al usuario y pedir confirmación antes de escribir los archivos. Solo guardar si el usuario aprueba.

**7. Verificar**

Después de guardar, leer los Excel nuevamente y confirmar que la métrica y sus relaciones quedaron escritas correctamente.

---

## Uso de la métrica en un pipeline

Una vez creada, agregar el paso `SaveToMetric` al JSON del pipeline:

```json
{
  "step": "SaveToMetric",
  "params": {
    "metric_id": <id_asignado>,
    "input_key": "nombre_del_artifact",
    "clear_existing": false
  }
}
```

El artifact debe ser un DataFrame con columnas que incluyan los nombres de las dimensiones y los campos de valor.
