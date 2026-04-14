---
description: Crear o modificar un paso de pipeline
---
# `/add-step` — Crear o modificar un paso de pipeline

Guía paso a paso para agregar un nuevo `Step` al sistema ETL.

## Contexto

Los pasos están organizados en módulos especializados bajo `backend/rgenerator/etl/core/`. Cada paso hereda de `Step` y se registra en varios puntos del sistema para que sea reconocible tanto en el backend como en el frontend.

---

## Checklist de implementación

### 1. Elegir el módulo correcto

Agregar la clase en el archivo que corresponda según la categoría del paso:

| Módulo | Categoría | Ejemplos |
|--------|-----------|---------|
| `init_steps.py` | Inicialización y configuración | `InitRun`, `LoadConfigFromSpec` |
| `io_steps.py` | Entrada/salida de archivos | `DiscoverInputs`, `RequestUserFiles`, `ExportConsolidatedExcel` |
| `etl_steps.py` | Transformación y enriquecimiento | `RunExcelETL`, `EnrichWithContext`, `ModifyColumnValues` |
| `report_steps.py` | Generación de reportes | `GenerateGraphics`, `GenerateTables`, `RenderReport` |
| `metric_steps.py` | Guardado de métricas | `SaveToMetric` |

### 2. Implementar la clase del paso

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

### 3. Re-exportar desde `pipeline_steps.py`

**Archivo:** `backend/rgenerator/etl/core/pipeline_steps.py`

Agregar el import y el nombre en `__all__`:

```python
from .<modulo> import NombreDelPaso   # agregar en el bloque de imports

__all__ = [
    # ... otros pasos ...
    "NombreDelPaso",                  # agregar aquí
]
```

### 4. Registrar en `STEP_MAPPING`

**Archivo:** `backend/rgenerator/tooling/pipeline_tools.py`

```python
STEP_MAPPING: Dict[str, Type[Step]] = {
    # ... otros pasos ...
    "NombreDelPaso": ps.NombreDelPaso,   # agregar aquí
}
```

> El runner valida los nombres de pasos contra este dict antes de ejecutarlos. Si el paso no está aquí, fallará al cargar el pipeline.

### 5. Agregar metadata en el frontend

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

### 6. (Opcional) Agregar renderer de UI personalizado

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

## Resumen de archivos a tocar

| # | Archivo | Qué agregar |
|---|---------|------------|
| 1 | `etl/core/<categoria>_steps.py` | Clase del paso |
| 2 | `etl/core/pipeline_steps.py` | Import + nombre en `__all__` |
| 3 | `tooling/pipeline_tools.py` | Entrada en `STEP_MAPPING` |
| 4 | `frontend/src/constants.js` | `STEP_OPTIONS`, `STEP_TRANSLATIONS`, `STEP_DEFAULT_PARAMS` |
| 5 | `frontend/src/components/pipeline-steps/StepRenderer.jsx` | Solo si necesita UI especial |

---

## Uso del paso en un pipeline JSON

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
