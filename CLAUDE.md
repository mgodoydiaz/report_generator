# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Report Generator** for Fundación PHP — automates generation of academic test result reports (SIMCE, etc.) through a web UI backed by an ETL/PDF pipeline.

## Running the Application

**Quick start (Windows):**
```bash
run_software.bat  # Opens two terminals: backend + frontend
```

**Backend** (FastAPI on port 8000):
```bash
conda activate rgenerator
python backend/api.py
```

**Frontend** (Vite/React on port 5173):
```bash
cd frontend
npm run dev
```

## Testing

```bash
# Run unit tests
pytest tests/steps/test_pipeline_steps.py -v

# With coverage
pytest tests/steps/test_pipeline_steps.py --cov=rgenerator

```

## ETL Scripts

```bash
conda activate rgenerator

# Run a full ETL pipeline from a config file
python scripts/run_etl.py ./config/simce_estudiantes_lenguaje.txt

# Generate a PDF report
python scripts/generate_report.py --schema <schema.json> --data <data.csv> --tipo <type> --output <output.pdf>

# Update templates registry
python scripts/update_templates_json.py
```

## Installation

```bash
conda env create -f environment.yml
conda activate rgenerator

# Install rgenerator package in editable mode
pip install -e .

# Frontend dependencies
cd frontend && npm install
```

## Architecture

### Stack
- **Frontend**: React 18 + Vite, Tailwind CSS 4, react-router-dom
- **Backend**: FastAPI + Uvicorn (`backend/api.py`)
- **ETL library**: `rgenerator` package (`backend/rgenerator/`)
- **Database**: Excel files in `data/database/` (7 `.xlsx` files — not concurrency-safe, migration to SQL planned)
- **PDF generation**: LaTeX/MikTeX + docxtpl for Word templates
- **Data processing**: pandas, camelot-py (PDF tables), PyMuPDF, matplotlib

### Backend structure

```
backend/
├── api.py              - FastAPI app with CORS, mounts 4 routers
├── config.py           - Centralized path constants (DATA_DIR, DB_DIR, etc.)
├── routers/
│   ├── pipelines.py    - CRUD + execution + file uploads (/api/pipelines)
│   ├── specs.py        - Specification templates (/api/specs)
│   ├── dimensions.py   - Dimension definitions (/api/dimensions)
│   └── metrics.py      - Metrics with import/export (/api/metrics)
└── rgenerator/
    ├── etl/
    │   ├── core/
    │   │   ├── context.py        - RunContext dataclass (pipeline execution state)
    │   │   ├── step.py           - Abstract Step base class + WaitingForInputException
    │   │   ├── pipeline_steps.py - Re-exportaciones de compatibilidad (agrupa módulos especializados)
    │   │   ├── init_steps.py     - InitRun, LoadConfigFromSpec
    │   │   ├── io_steps.py       - DiscoverInputs, RequestUserFiles, ExportConsolidatedExcel, DeleteTempFiles
    │   │   ├── etl_steps.py      - RunExcelETL, EnrichWithUserInput, EnrichWithContext, ModifyColumnValues
    │   │   ├── report_steps.py   - GenerateGraphics, GenerateTables, RenderReport, GenerateDocxReport
    │   │   └── metric_steps.py   - SaveToMetric step
    │   └── evaluaciones/
    │       └── simce_input_rules.py
    └── tooling/
        ├── pipeline_tools.py     - PipelineRunner, STEP_MAPPING dict, load_pipeline_config()
        ├── config_tools.py       - Config loading utilities
        ├── data_tools.py         - Data processing helpers
        ├── plot_tools.py         - Chart generation
        ├── report_tools.py       - Report generation
        └── report_docx_tools.py  - Word template rendering
```

### Pipeline execution model

Pipelines are JSON configs stored in `data/database/pipelines/`. Each pipeline has `workflow_metadata`, `context`, and a `pipeline` array of `{step, params}` objects. `PipelineRunner` in `tooling/pipeline_tools.py` maps step names to classes via `STEP_MAPPING` and executes them sequentially, passing a shared `RunContext`.

Steps can raise `WaitingForInputException` to pause execution and request user-provided files or data — the API handles this by returning a "waiting" status, and the frontend resumes execution after the user uploads files.

**`RunContext` key fields** (from `etl/core/context.py`):
- `inputs: Dict[str, List[Path]]` — input files by role (e.g., `estudiantes`, `preguntas`)
- `artifacts: Dict[str, Any]` — intermediate dataframes/objects passed between steps
- `outputs: Dict[str, Path]` — final output paths by role
- `status: str` — `NEW | RUNNING | NEEDS_REVIEW | DONE | FAILED`
- `last_artifact_key` — key of the most recently produced artifact

**Key step categories** (definidos en módulos especializados bajo `etl/core/`):
- **Init/Config** (`init_steps.py`): `InitRun`, `LoadConfigFromSpec`
- **I/O** (`io_steps.py`): `DiscoverInputs`, `RequestUserFiles`, `ExportConsolidatedExcel`, `DeleteTempFiles`
- **ETL** (`etl_steps.py`): `RunExcelETL`, `EnrichWithContext`, `EnrichWithUserInput`, `ModifyColumnValues`
- **Reporting** (`report_steps.py`): `GenerateGraphics`, `GenerateTables`, `RenderReport`, `GenerateDocxReport`
- **Metrics** (`metric_steps.py`): `SaveToMetric`

### Frontend structure

```
frontend/src/
├── App.jsx             - Router setup (7 active pages + 2 placeholders)
├── pages/              - Home, Pipelines, Specs, Dimensions, Values, Metrics, Execution
└── components/         - Layout, Sidebar, modals, drawers, PipelineExecutionModal
```

`PipelineExecutionModal` handles the multi-step execution UI, including pausing for `RequestUserFiles` and `EnrichWithUserInput` steps. Step-specific UI renderers live in `components/pipeline-steps/`.

### Data directory layout

```
data/
├── database/           - Excel "DB" tables + pipelines/ JSON configs + reports_templates/
├── input/              - Raw input files
├── output/             - Generated reports
├── pipeline_runs/      - Per-run artifacts; uploads/ holds user-submitted files
└── tmp/                - Temporary working files
```

ETL config examples (column mappings, header rows, enrichment values) live in `config/`.
Chart/table template definitions for `GenerateGraphics`/`GenerateTables` live in `data/database/reports_templates/`.

## How-To: Crear una métrica desde el chat de Claude

Para crear una nueva métrica sin usar el frontend, sigue estos pasos. Requiere editar directamente los archivos Excel de la base de datos.

### Archivos involucrados

| Archivo | Propósito |
|---|---|
| `data/database/dimensions.xlsx` | Catálogo de dimensiones (columnas de segmentación) |
| `data/database/metrics.xlsx` | Definición de métricas |
| `data/database/metric_dimensions.xlsx` | Relación M-N entre métricas y dimensiones |

### Paso 1 — Definir el esquema de la métrica

Recopilar del usuario:
- **Nombre** de la métrica
- **Tipo de dato** (`int`, `float`, `str`, u `object` si hay múltiples campos de valor)
- **Campos de valor**: las columnas numéricas o textuales que se guardarán como dato. Si son más de uno, el tipo es `object` y se listan en `meta_json.fields`.
- **Dimensiones**: las columnas de segmentación (ej. Año, Curso, Asignatura). Estas **no** son el valor medido, sino los ejes por los que se filtra/agrega.

### Paso 2 — Verificar dimensiones existentes

Leer `data/database/dimensions.xlsx` y comparar las dimensiones requeridas contra las ya existentes. Identificar cuáles hay que crear.

Columnas del archivo: `id_dimension`, `name`, `data_type`, `validation_mode`.

- `data_type`: tipo del valor de la dimensión (`str`, `int`, `float`)
- `validation_mode`: `'free'` (cualquier valor) o `'list'` (valores controlados desde `dimension_values.xlsx`)

### Paso 3 — Crear dimensiones faltantes

Usando un script Python con `pandas`, agregar las filas faltantes al archivo. El `id_dimension` debe ser `max(id_dimension) + 1` para cada nueva dimensión.

```python
import pandas as pd
from pathlib import Path

DB = Path("data/database")
df = pd.read_excel(DB / "dimensions.xlsx")

nuevas = [
    {"id_dimension": 14, "name": "Nueva Dimension", "data_type": "str", "validation_mode": "free"},
]
df = pd.concat([df, pd.DataFrame(nuevas)], ignore_index=True)
df.to_excel(DB / "dimensions.xlsx", index=False)
```

### Paso 4 — Crear la métrica en metrics.xlsx

Columnas del archivo: `id_metric`, `name`, `data_type`, `meta_json`, `description`, `unit`, `created_at`.

- Para métricas tipo `object`, `meta_json` debe ser un JSON string con la clave `"fields"`:
  ```json
  {"fields": [{"name": "A", "type": "float"}, {"name": "Correcta", "type": "str"}]}
  ```
- Para métricas simples (`int`, `float`, `str`), `meta_json` puede quedar vacío (`{}`).

```python
import json
from datetime import datetime

df_m = pd.read_excel(DB / "metrics.xlsx")
nueva_metrica = {
    "id_metric": int(df_m["id_metric"].max()) + 1,
    "name": "Nombre Métrica",
    "data_type": "object",  # o 'int', 'float', 'str'
    "meta_json": json.dumps({"fields": [
        {"name": "CampoA", "type": "float"},
        {"name": "CampoB", "type": "str"},
    ]}),
    "description": "Descripción opcional",
    "unit": "",
    "created_at": datetime.now().isoformat(),
}
df_m = pd.concat([df_m, pd.DataFrame([nueva_metrica])], ignore_index=True)
df_m.to_excel(DB / "metrics.xlsx", index=False)
```

### Paso 5 — Relacionar métrica con sus dimensiones en metric_dimensions.xlsx

Columnas del archivo: `id`, `id_metric`, `id_dimension`.

```python
df_md = pd.read_excel(DB / "metric_dimensions.xlsx")
metric_id = 5  # ID de la métrica recién creada
dim_ids = [4, 5, 8, 11, 12]  # IDs de las dimensiones a asociar

nuevas_rels = [{"id_metric": metric_id, "id_dimension": d} for d in dim_ids]
# Asignar IDs correlativos
start_id = int(df_md["id"].max()) + 1 if not df_md.empty else 1
for i, rel in enumerate(nuevas_rels):
    rel["id"] = start_id + i

df_md = pd.concat([df_md, pd.DataFrame(nuevas_rels)], ignore_index=True)
df_md.to_excel(DB / "metric_dimensions.xlsx", index=False)
```

### Paso 6 — Verificar

Confirmar que la métrica es accesible desde la API:
```
GET http://localhost:8000/api/metrics
```
O leer directamente el Excel para verificar que los IDs y relaciones quedaron correctos.

### Usar la métrica en un pipeline

Agregar el paso `SaveToMetric` en el JSON del pipeline:
```json
{
  "step": "SaveToMetric",
  "params": {
    "metric_id": 5,
    "input_key": "nombre_del_artifact",
    "clear_existing": false
  }
}
```
El artifact referenciado debe ser un DataFrame cuyas columnas incluyan:
- Los nombres de las dimensiones asociadas (ej. `"Año"`, `"Curso"`)
- Los campos de valor (para tipo `object`: `"CampoA"`, `"CampoB"`; para tipo simple: el nombre exacto de la métrica)

---

## Skills de administración

Tareas recurrentes de desarrollo y administración del proyecto están documentadas como flujos de trabajo en **[.agents/workflows/](./.agents/workflows/)**:

- `/add-step` — Crear o modificar un paso de pipeline (guía de referencia)
- `/add-metric` — Crear una nueva métrica interactivamente
- `/new-pipeline` — Construir un nuevo pipeline JSON desde cero

## Roadmap y Pendientes

Los pendientes, deuda técnica y mejoras planificadas se mantienen en **[ROADMAP.md](./ROADMAP.md)**.
