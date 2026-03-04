# Skills — omniadmin rgenerator

Comandos de referencia para tareas recurrentes de administración y desarrollo del proyecto Report Generator.

---

## `/add-step` — Crear o modificar un paso de pipeline

Guía paso a paso para agregar un nuevo `Step` al sistema ETL.

### Contexto

Los pasos están organizados en módulos especializados bajo `backend/rgenerator/etl/core/`. Cada paso hereda de `Step` y se registra en varios puntos del sistema para que sea reconocible tanto en el backend como en el frontend.

---

### Checklist de implementación

#### 1. Elegir el módulo correcto

Agregar la clase en el archivo que corresponda según la categoría del paso:

| Módulo | Categoría | Ejemplos |
|--------|-----------|---------|
| `init_steps.py` | Inicialización y configuración | `InitRun`, `LoadConfigFromSpec` |
| `io_steps.py` | Entrada/salida de archivos | `DiscoverInputs`, `RequestUserFiles`, `ExportConsolidatedExcel` |
| `etl_steps.py` | Transformación y enriquecimiento | `RunExcelETL`, `EnrichWithContext`, `ModifyColumnValues` |
| `report_steps.py` | Generación de reportes | `GenerateGraphics`, `GenerateTables`, `RenderReport` |
| `metric_steps.py` | Guardado de métricas | `SaveToMetric` |

#### 2. Implementar la clase del paso

```python
# En backend/rgenerator/etl/core/<categoria>_steps.py

class NombreDelPaso(Step):
    """
    Una línea describiendo qué hace el paso.

    Parametros:
        param1 (tipo): descripción del parámetro.
        param2 (tipo, opcional): descripción. Default: valor.

    Efectos:
        - ctx.artifacts["clave"] con el resultado producido.
        - ctx.last_artifact_key actualizado.

    Ejemplo:
        NombreDelPaso(param1="valor", param2=123)
    """
    def __init__(self, param1: str, param2: int = 0):
        super().__init__(
            name="NombreDelPaso",
            requires=["artifact_requerido"],   # claves que deben existir en ctx.artifacts
            produces=["artifact_producido"],   # claves que este paso escribirá
        )
        self.param1 = param1
        self.param2 = param2

    def run(self, ctx):
        # Leer entradas desde ctx.artifacts o ctx.inputs
        df = ctx.artifacts["artifact_requerido"]

        # Lógica del paso
        resultado = df  # ... transformación

        # Escribir salidas
        ctx.artifacts["artifact_producido"] = resultado
        ctx.last_artifact_key = "artifact_producido"
```

> Si el paso debe pausar la ejecución para pedir archivos o datos al usuario, lanzar `WaitingForInputException` en lugar de continuar.

#### 3. Re-exportar desde `pipeline_steps.py`

**Archivo:** `backend/rgenerator/etl/core/pipeline_steps.py`

Agregar el import y el nombre en `__all__`:

```python
from .<modulo> import NombreDelPaso   # agregar en el bloque de imports

__all__ = [
    # ... otros pasos ...
    "NombreDelPaso",                  # agregar aquí
]
```

#### 4. Registrar en `STEP_MAPPING`

**Archivo:** `backend/rgenerator/tooling/pipeline_tools.py`

```python
STEP_MAPPING: Dict[str, Type[Step]] = {
    # ... otros pasos ...
    "NombreDelPaso": ps.NombreDelPaso,   # agregar aquí
}
```

> El runner valida los nombres de pasos contra este dict antes de ejecutarlos. Si el paso no está aquí, fallará al cargar el pipeline.

#### 5. Agregar metadata en el frontend

**Archivo:** `frontend/src/constants.js`

Tres secciones deben actualizarse:

```js
// 5a. Lista de pasos disponibles en el selector
export const STEP_OPTIONS = [
  // ... otros pasos ...
  "NombreDelPaso",
];

// 5b. Traducción al español para mostrar en la UI
export const STEP_TRANSLATIONS = {
  // ... otros pasos ...
  "NombreDelPaso": "Nombre Legible en Español",
};

// 5c. Plantilla de parámetros con comentarios explicativos
export const STEP_DEFAULT_PARAMS = {
  // ... otros pasos ...
  "NombreDelPaso": `{
  // param1: descripción del parámetro
  "param1": "valor_ejemplo",
  // param2 (opcional): descripción. Default: 0
  "param2": 0
}`,
};
```

#### 6. (Opcional) Agregar renderer de UI personalizado

Solo si el paso necesita interfaz interactiva durante la ejecución (como subida de archivos o ingreso de datos).

**Archivo:** `frontend/src/components/pipeline-steps/StepRenderer.jsx`

```jsx
import NombreDelPasoComponent from "./NombreDelPaso";

// Dentro del switch/condicional existente:
if (step.step === "NombreDelPaso") {
  return <NombreDelPasoComponent ... />;
}
```

Crear el componente en `frontend/src/components/pipeline-steps/NombreDelPaso.jsx`.

---

### Resumen de archivos a tocar

| # | Archivo | Qué agregar |
|---|---------|------------|
| 1 | `etl/core/<categoria>_steps.py` | Clase del paso |
| 2 | `etl/core/pipeline_steps.py` | Import + nombre en `__all__` |
| 3 | `tooling/pipeline_tools.py` | Entrada en `STEP_MAPPING` |
| 4 | `frontend/src/constants.js` | `STEP_OPTIONS`, `STEP_TRANSLATIONS`, `STEP_DEFAULT_PARAMS` |
| 5 | `frontend/src/components/pipeline-steps/StepRenderer.jsx` | Solo si necesita UI especial |

---

### Uso del paso en un pipeline JSON

```json
{
  "step": "NombreDelPaso",
  "params": {
    "param1": "valor",
    "param2": 123
  }
}
```

Los parámetros del JSON se pasan directamente como kwargs al `__init__` del paso.

---

## `/add-metric` — Crear una nueva métrica

Skill ejecutable: Claude guía el proceso interactivamente, lee los archivos Excel actuales y escribe los cambios directamente.

### Instrucciones para Claude

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

### Uso de la métrica en un pipeline

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

---

## `/new-pipeline` — Crear un nuevo pipeline desde cero

Skill ejecutable: Claude guía al usuario con preguntas para construir el JSON del pipeline, propone la secuencia de pasos, y lo escribe en `data/database/pipelines/`.

### Instrucciones para Claude

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

---

*Otros skills próximos: `/debug-run`*