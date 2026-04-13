# Pipeline Steps — Referencia

Todos los steps disponibles en el sistema ETL. Se registran en `STEP_MAPPING` dentro de `backend/rgenerator/tooling/pipeline_tools.py`.

---

## Init / Config

### `InitRun`
Inicializa el `RunContext`. Siempre debe ser el primer step.

### `LoadConfigFromSpec`
Carga parámetros de configuración desde una especificación (`Spec`) de la base de datos.

| Param | Descripción |
|---|---|
| `spec_id` | ID de la especificación a cargar |

---

## I/O

### `DiscoverInputs`
Busca archivos de entrada en `data/input/` según reglas definidas.

### `RequestUserFiles`
Pausa la ejecución y solicita al usuario que suba archivos. Lanza `WaitingForInputException`.

| Param | Descripción |
|---|---|
| `input_key` | Rol del archivo solicitado (ej: `"estudiantes"`) |
| `label` | Texto descriptivo para el usuario |

### `ExportConsolidatedExcel`
Exporta uno o más artefactos del contexto a un archivo Excel consolidado.

### `DeleteTempFiles`
Elimina archivos temporales generados durante la ejecución.

---

## ETL

### `RunExcelETL`
Procesa un Excel de entrada aplicando transformaciones (columnas, tipos, filtros).

### `EnrichWithContext`
Enriquece el DataFrame activo con valores del contexto (`ctx.params`).

### `EnrichWithUserInput`
Pausa la ejecución y solicita al usuario completar valores faltantes en el DataFrame.

### `ModifyColumnValues`
Aplica transformaciones sobre columnas específicas del artefacto activo.

---

## Reporting

### `GenerateGraphics`
Genera imágenes (PNG) a partir de un `charts_schema`. Ver [graficos-tablas.md](./graficos-tablas.md).

| Param | Descripción |
|---|---|
| `charts_schema` | Lista de gráficos a generar |
| `input_key` | Artefacto del contexto a usar como fuente |

### `GenerateTables`
Genera tablas Excel a partir de un `tables_schema`.

### `RenderReport`
Genera un PDF usando LaTeX a partir de un esquema de reporte.

### `GenerateDocxReport`
Genera un archivo Word (.docx) usando plantillas Jinja2 (docxtpl).

| Param | Descripción |
|---|---|
| `template_name` | Nombre del archivo de plantilla en `data/database/reports_templates/` |
| `context_key` | Artefacto del contexto con los datos a inyectar |

---

## Métricas

### `SaveToMetric`
Guarda datos del pipeline en una métrica de la base de datos.

| Param | Descripción |
|---|---|
| `metric_id` | ID de la métrica destino |
| `input_key` | Artefacto (DataFrame) con los datos |
| `clear_existing` | Si `true`, borra datos previos de la métrica antes de insertar |

El DataFrame debe tener columnas con los nombres de las dimensiones asociadas y los campos de valor de la métrica.

---

## Agregar un nuevo step

Ver el skill [`/add-step`](../skills/add-step.md).
