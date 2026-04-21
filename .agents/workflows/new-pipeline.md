---
description: Crear un nuevo pipeline desde cero
---
# `/new-pipeline` — Crear un nuevo pipeline desde cero

> **Modo autónomo (Claude sin UI):** El pipeline vive en PostgreSQL — crear y ejecutar solo con API REST. Ver flujo httpx al final.

Skill ejecutable: el asistente guía al usuario con preguntas para construir el JSON del pipeline, propone la secuencia de pasos, y lo persiste en la tabla `pipelines` de PostgreSQL.

> **Nota**: los pipelines viven como filas en PostgreSQL (`pipelines.config_json`). No se guardan como archivos sueltos. El `pipeline_id` lo autogenera la DB.

## Instrucciones para el Asistente

### 1. Recopilar el objetivo del pipeline

Preguntar en un solo mensaje:

- Nombre del pipeline y descripción breve
- Tipo de input (Excel, PDF, otro)
- Tipo de output deseado: reporte PDF, reporte Word, Excel consolidado, solo métricas, combinación
- Contexto: colegio, año, tipo de evaluación (si aplica)

### 2. Leer el contexto disponible

Listar los pipelines existentes para no duplicar nombres y proponer otros como referencia:

```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/pipelines/
```

O vía SQLAlchemy:

```python
from backend.database import SessionLocal
from backend.models import Pipeline, Spec, User

db = SessionLocal()
org_id = db.query(User).filter(User.email == "<email>").first().org_id

existentes = db.query(Pipeline).filter(Pipeline.org_id == org_id).all()
specs = db.query(Spec).filter(Spec.org_id == org_id).all()
```

Si el usuario menciona una evaluación conocida, buscar el `Spec` correspondiente para usar con `LoadConfigFromSpec`.

### 3. Proponer la secuencia de pasos

Según las respuestas, proponer los pasos en orden. Guía orientativa:

| Objetivo | Pasos típicos |
|----------|--------------|
| ETL básico | `InitRun` → `DiscoverInputs` → `RunExcelETL` → `ExportConsolidatedExcel` |
| ETL + métrica | + `EnrichWithContext` → `SaveToMetric` |
| ETL + reporte | + `GenerateGraphics` → `GenerateTables` → `RenderReport` |
| Enriquecimiento manual | + `RequestUserFiles` o `EnrichWithUserInput` antes del reporte |

Mostrar la propuesta al usuario y ajustar según sus comentarios.

### 4. Completar los parámetros de cada paso

Para cada paso, inferir o preguntar los parámetros necesarios (`input_key`, `output_key`, `spec_id`, `metric_id`, etc.). Usar los templates de `STEP_DEFAULT_PARAMS` en `frontend/src/constants.js` como referencia de qué pedir.

### 5. Confirmar y persistir

Mostrar el JSON completo al usuario antes de guardar. La descripción del pipeline debe incluir al final `(IA)` para indicar que fue generado con asistencia de IA — el usuario puede quitarlo si prefiere.

**Estructura del payload:**

```json
{
  "pipeline_metadata": {
    "name": "Nombre del Pipeline",
    "description": "Descripción del proceso (IA)",
    "input": "Excel",
    "output": "Reporte PDF"
  },
  "context": {
    "base_dir": "./data"
  },
  "pipeline": [
    { "step": "InitRun", "params": {} },
    { "step": "...", "params": { ... } }
  ]
}
```

**Crear en la DB vía API:**

```bash
curl -X POST http://localhost:8000/api/pipelines/config \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d @nuevo_pipeline.json
```

La respuesta incluye el `new_id` asignado por PostgreSQL.

**O vía SQLAlchemy** (si el backend no está corriendo):

```python
import json
from backend.models import Pipeline

row = Pipeline(
    pipeline="Nombre del Pipeline",
    description="Descripción (IA)",
    config_json=json.dumps(payload, ensure_ascii=False),
    hidden=False,
    org_id=org_id,
)
db.add(row)
db.commit()
db.refresh(row)
print(f"Pipeline creado con id {row.pipeline_id}")
```

### 6. Confirmar guardado

Leer el pipeline recién creado (por `pipeline_id`) y mostrar al usuario el resumen para confirmar que quedó bien persistido.

---

## Notas

- **Multi-tenant**: El `org_id` se toma del usuario autenticado (vía API) o hay que pasarlo explícitamente (vía SQLAlchemy). Un pipeline solo es visible para usuarios de la misma organización.
- **Pipelines legacy en archivos**: Los antiguos `data/database/pipelines/pipeline<NNN>.json` ya no se usan en runtime; si aparecen, son material de referencia para migrar.
- **Clave de metadata**: La clave canónica es `pipeline_metadata`. `workflow_metadata` sigue soportado como fallback por compatibilidad con configs antiguos.

---

## Flujo autónomo completo (Python httpx — sin UI)

```python
import httpx, json

BASE = "http://localhost:8000/api"
TOKEN = httpx.post(f"{BASE}/auth/login",
    json={"email": "admin@org.cl", "password": "secreto"}).json()["access_token"]
H = {"Authorization": f"Bearer {TOKEN}"}

PIPELINE_JSON = {
    "pipeline_metadata": {
        "name": "ETL IDEL-Woodcock 2025 (IA)",
        "description": "Carga datos IDEL desde Excel largo y guarda en métrica",
        "input": "Excel",
        "output": "Métrica"
    },
    "context": {"base_dir": "./data"},
    "pipeline": [
        {"step": "InitRun",         "params": {"evaluation": "IDEL_2025", "base_dir": "./data"}},
        {"step": "RequestUserFiles", "params": {"file_specs": [
            {"id": "consolidado_largo", "label": "Consolidado IDEL largo", "multiple": False, "optional": False}
        ]}},
        {"step": "RunExcelETL",     "params": {"input_key": "consolidado_largo", "output_key": "df_idel"}},
        {"step": "SaveToMetric",    "params": {"metric_id": 9, "input_key": "df_idel", "clear_existing": False}},
        {"step": "DeleteTempFiles", "params": {}},
    ]
}

# Crear
r = httpx.post(f"{BASE}/pipelines/config", headers=H, json=PIPELINE_JSON)
pid = r.json()["new_id"]
print("Pipeline creado:", pid)

# Ejecutar (el backend maneja RequestUserFiles con pausa interactiva)
httpx.post(f"{BASE}/pipelines/{pid}/run", headers=H)
```

**Nota sobre `RequestUserFiles`:** Si el pipeline tiene ese step, la primera ejecución pausará con `status: NEEDS_REVIEW`. El usuario sube el archivo desde la UI, luego se reanuda llamando `POST /api/pipelines/{id}/resume` (o el botón en la UI).
