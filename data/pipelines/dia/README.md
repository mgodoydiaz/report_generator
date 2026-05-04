# Pipelines DIA — referencia

Estos JSON son **plantillas** generadas en el sprint B6b (2026-05-04) para
los pipelines DIA Matemáticas (id=19) y DIA Lectura (id=21) que en la
producción están casi vacíos (solo `InitRun`).

Migran a steps configurables la lógica del script artesanal
`script_consolidar_DIA.py` que el cliente usa hoy. Documento de
referencia: [`docs/desarrollo/script_dia_artesanal_referencia.md`](../../../docs/desarrollo/script_dia_artesanal_referencia.md).

## Qué cubren

- ✅ Lectura de XLS por curso con metadata pre-header (B5 = Establecimiento, B6 = Curso) vía el nuevo parámetro `metadata_cells` de `RunExcelETL`.
- ✅ Cálculo de `Logro` como mean horizontal de las preguntas (todas las columnas excepto las de metadata) vía `ApplyDerivedFields` con kind `row_mean_dynamic`. Reemplaza coma decimal y aplica `scale=0.01` (DIA viene 0-100).
- ✅ Asignación de `Nivel Logro` por umbral (≤0.4 Inicial, ≤0.6 Intermedio, resto Avanzado) vía kind `row_threshold`.
- ✅ Generación de `Nombre_Norm` (apellidos+nombre ordenados alfabéticamente) vía kind `normalize_name`. Resuelve el bug de matching entre hitos (DIAGNOSTICO viene "Nombre Apellido", INTERMEDIO viene "Apellido Nombre").
- ✅ Limpieza de prefijos en `Curso` ("1° básico A" → "1A").
- ✅ Pausa interactiva para que el usuario indique el `Hito` por archivo (DIAGNOSTICO / INTERMEDIO / FINAL).

## Estado tras cierre B6b (2026-05-04)

- ✅ **Step `RunDIAPDFExtraction`**: portado del script artesanal con las 5 funciones helper (camelot+fitz+análisis de píxeles para detectar bold). Validado contra PDF real (Panguipulli 7°A): 28 preguntas extraídas, Logro [0.20-0.80], Curso "7 A" detectado.
- ✅ **`Avance` y `Mejora_vs_Inicio`** activados en `backend/rgenerator/reports/dia/esquema.json` con `entity_field=["Curso","Nombre_Norm"]` y `time_field=Hito` ordinal. Funcionarán con ≥2 hitos cargados.
- ✅ **`metric_id`** resueltos (6 = estudiantes, 7 = preguntas).
- ✅ Pipelines DIA Matemáticas (id=19) y DIA Lenguaje (id=21) publicados en la DB.

## Cómo cargar a la DB

Reemplazar el contenido del pipeline existente:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"<email>","password":"<pwd>"}' | jq -r .access_token)

# DIA Matemáticas
curl -X PUT http://localhost:8000/api/pipelines/19/config \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d @data/pipelines/dia/dia_matematicas_pipeline.json

# DIA Lectura
curl -X PUT http://localhost:8000/api/pipelines/21/config \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d @data/pipelines/dia/dia_lectura_pipeline.json
```

Alternativa SQLAlchemy (si el backend no está arriba):

```python
import json
from backend.database import SessionLocal
from backend.models import Pipeline

db = SessionLocal()
for pid, fname in [(19, "dia_matematicas_pipeline.json"),
                   (21, "dia_lectura_pipeline.json")]:
    with open(f"data/pipelines/dia/{fname}", encoding="utf-8") as f:
        cfg = json.load(f)
    p = db.query(Pipeline).filter(Pipeline.pipeline_id == pid).first()
    p.config_json = json.dumps(cfg, ensure_ascii=False)
    db.commit()
```

## Verificación post-carga

Tras la primera ejecución verificar:

1. `RequestUserFiles` pausa pidiendo XLS (`status: NEEDS_REVIEW`).
2. `EnrichWithUserInput` pausa pidiendo `Hito` por archivo.
3. `RunExcelETL` produce `df_estudiantes_raw` con columnas `Establecimiento`, `Curso` correctas (las leyó de B5/B6).
4. `ApplyDerivedFields` produce `Logro` (0-1), `Nivel Logro` (string), `Nombre_Norm`.
5. `SaveToMetric` carga las filas a la métrica destino.
