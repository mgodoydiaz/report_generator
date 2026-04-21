---
description: Crear una nueva métrica
---
# `/add-metric` — Crear una nueva métrica

> **Modo autónomo (Claude sin UI):** Usar Camino A (API REST) con el flujo de Python `httpx` documentado al final. No requiere editar archivos ni reiniciar el servidor.

Skill ejecutable: el asistente guía el proceso interactivamente, consulta el estado actual de la DB y escribe los cambios mediante la API REST o SQLAlchemy.

> **Nota**: Las métricas y dimensiones viven en PostgreSQL. Nunca editar los `.xlsx` de `data/database/` — son legacy y no se leen en runtime.

## Instrucciones para el Asistente

### 1. Recopilar información del usuario

Preguntar (puede ser en un solo mensaje):

- **Nombre** de la métrica
- **Tipo de dato**: `int`, `float`, `str`, u `object` (si tiene múltiples campos de valor)
- Si el tipo es `object`: nombres y tipos de cada campo de valor
- **Dimensiones de segmentación** (ej. Año, Curso, Asignatura)
- **Descripción** y **unidad** (opcionales)

### 2. Leer el estado actual

Hay dos caminos según el contexto. **Preguntar al usuario cuál prefiere** si no es obvio:

#### Camino A — Vía API REST (recomendado si el backend está corriendo)

```bash
# Autenticación primero (devuelve access_token)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "...", "password": "..."}'

# Listar dimensiones existentes
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/dimensions/

# Listar métricas existentes
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/metrics/
```

#### Camino B — Vía SQLAlchemy (si el backend no está arriba o se prefiere script)

```python
# Ejecutar desde la raíz del repo con conda env rgenerator activo
from backend.database import SessionLocal
from backend.models import Dimension, Metric, MetricDimension, User

db = SessionLocal()
org_id = db.query(User).filter(User.email == "<email_usuario>").first().org_id

dims = db.query(Dimension).filter(Dimension.org_id == org_id).all()
metrics = db.query(Metric).filter(Metric.org_id == org_id).all()
```

Mostrar al usuario las dimensiones existentes para que confirme cuáles reutilizar y cuáles hay que crear.

### 3. Crear dimensiones faltantes

#### Camino A — API

```bash
curl -X POST http://localhost:8000/api/dimensions/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nueva Dimension",
    "data_type": "str",
    "validation_mode": "free"
  }'
```

Campos:
- `data_type`: `str`, `int`, `float`
- `validation_mode`: `"free"` (cualquier valor) o `"list"` (valores controlados, se cargan aparte con `POST /api/dimensions/{id}/values`)

#### Camino B — SQLAlchemy

```python
new_dim = Dimension(
    name="Nueva Dimension",
    data_type="str",
    validation_mode="free",
    description="",
    org_id=org_id,
)
db.add(new_dim)
db.commit()
db.refresh(new_dim)
print(new_dim.id_dimension)
```

`id_dimension` es autogenerado por PostgreSQL — no hay que calcular `max(id)+1` manualmente.

### 4. Crear la métrica

#### Camino A — API

```bash
curl -X POST http://localhost:8000/api/metrics/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nombre Métrica",
    "data_type": "object",
    "description": "Descripción opcional",
    "meta_json": {
      "fields": [
        {"name": "CampoA", "type": "float"},
        {"name": "CampoB", "type": "str"}
      ]
    },
    "dimension_ids": [4, 5, 8, 11, 12]
  }'
```

Notas sobre `meta_json`:
- Tipo simple (`int`, `float`, `str`): puede ser `{}`
- Tipo `object`: debe llevar `{"fields": [{"name": "...", "type": "..."}, ...]}`

`dimension_ids` crea las relaciones en `metric_dimensions` en el mismo request — no hay paso extra como en el flujo Excel antiguo.

#### Camino B — SQLAlchemy

```python
import json
from backend.models import Metric, MetricDimension

new_m = Metric(
    name="Nombre Métrica",
    data_type="object",
    description="Descripción opcional",
    meta_json=json.dumps({
        "fields": [
            {"name": "CampoA", "type": "float"},
            {"name": "CampoB", "type": "str"},
        ]
    }),
    org_id=org_id,
)
db.add(new_m)
db.flush()  # necesario para obtener new_m.id_metric

for dim_id in [4, 5, 8, 11, 12]:
    db.add(MetricDimension(id_metric=new_m.id_metric, id_dimension=dim_id))

db.commit()
```

### 5. Confirmar antes de escribir

Mostrar al usuario un resumen de todos los cambios (nombres, IDs de dimensiones a crear, dimensiones a asociar, `meta_json`) y pedir confirmación explícita antes de ejecutar los requests/commits.

### 6. Verificar

Después de escribir, volver a leer (API o DB) y confirmar que:
- La métrica aparece con su `id_metric` asignado
- Las relaciones en `metric_dimensions` están todas presentes
- `meta_json` se guardó correctamente (verificar formato)

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

El artifact debe ser un `DataFrame` con columnas que incluyan:
- Los **nombres** de las dimensiones asociadas (ej. `"Año"`, `"Curso"`)
- Los **campos de valor**:
  - Para tipo `object`: las columnas definidas en `meta_json.fields`
  - Para tipo simple: una sola columna con el nombre exacto de la métrica

`SaveToMetric` usa `ctx.db` y `ctx.org_id` internamente — no necesita configuración adicional, solo requiere que el pipeline se ejecute desde el backend autenticado.

---

## Flujo autónomo completo (Python httpx — sin UI)

```python
import httpx

BASE = "http://localhost:8000/api"
TOKEN = httpx.post(f"{BASE}/auth/login",
    json={"email": "admin@org.cl", "password": "secreto"}).json()["access_token"]
H = {"Authorization": f"Bearer {TOKEN}"}

# 1. Crear dimensiones faltantes
dim_ids = []
for dim_name in ["Establecimiento", "Año", "Curso", "Evaluación", "Versión"]:
    r = httpx.post(f"{BASE}/dimensions/", headers=H,
        json={"name": dim_name, "data_type": "str", "validation_mode": "free"})
    dim_ids.append(r.json()["id_dimension"])

# 2. Crear métrica con dimensiones
r = httpx.post(f"{BASE}/metrics/", headers=H, json={
    "name": "Resultados IDEL-Woodcock",
    "data_type": "object",
    "description": "Puntaje y nivel de riesgo por subprueba Woodcock",
    "meta_json": {"fields": [
        {"name": "Puntaje", "type": "float"},
        {"name": "Nivel de Riesgo", "type": "str"},
    ]},
    "dimension_ids": dim_ids,
})
metric_id = r.json()["id_metric"]
print("Métrica creada:", metric_id)

# 3. Importar datos desde Excel (formato largo ya normalizado)
with open("data/input/idel/Consolidado_IDEL_2025_largo.xlsx", "rb") as f:
    httpx.post(f"{BASE}/metrics/{metric_id}/import", headers=H,
        files={"files": ("datos.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
print("Datos importados.")
```
