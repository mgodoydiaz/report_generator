---
description: Crear un nuevo pipeline desde cero
---
# `/new-pipeline` — Crear un nuevo pipeline desde cero

Skill ejecutable: El asistente guía al usuario con preguntas para construir el JSON del pipeline, propone la secuencia de pasos, y lo escribe en `data/database/pipelines/`.

## Instrucciones para el Asistente

**1. Recopilar el objetivo del pipeline**

Preguntar en un solo mensaje:
- Nombre del pipeline y descripción breve
- Tipo de input (Excel, PDF, otro)
- Tipo de output deseado: reporte PDF, reporte Word, Excel consolidado, solo métricas, combinación
- Contexto: colegio, año, tipo de evaluación (si aplica)

**2. Leer el contexto disponible**

Revisar los pipelines existentes en `data/database/pipelines/` para proponer el próximo ID de archivo (`pipeline<NNN>.json`). Revisar también specs disponibles en `data/database/` si el usuario menciona una evaluación conocida.

**3. Proponer la secuencia de pasos**

Según las respuestas, proponer los pasos en orden. Guía orientativa:

| Objetivo | Pasos típicos |
|----------|--------------|
| ETL básico | `InitRun` → `DiscoverInputs` → `RunExcelETL` → `ExportConsolidatedExcel` |
| ETL + métrica | + `EnrichWithContext` → `SaveToMetric` |
| ETL + reporte | + `GenerateGraphics` → `GenerateTables` → `RenderReport` |
| Enriquecimiento manual | + `RequestUserFiles` o `EnrichWithUserInput` antes del reporte |

Mostrar la propuesta al usuario y ajustar según sus comentarios.

**4. Completar los parámetros de cada paso**

Para cada paso de la secuencia, preguntar o inferir los parámetros necesarios (input_key, output_key, spec, metric_id, etc.). Usar los templates de `STEP_DEFAULT_PARAMS` en `frontend/src/constants.js` como referencia de qué pedir.

**5. Confirmar y escribir el JSON**

Mostrar el JSON completo al usuario antes de guardar. La descripción del pipeline debe incluir al final `(IA)` para indicar que fue generado con asistencia de IA — el usuario puede quitarlo si prefiere.

Estructura del archivo:

```json
{
    "workflow_metadata": {
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

Guardar en `data/database/pipelines/pipeline<NNN>.json`.

**6. Confirmar guardado**

Leer el archivo recién creado y mostrar confirmación al usuario.
