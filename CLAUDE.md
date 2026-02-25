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
pytest backend/tests/steps/test_pipeline_steps.py -v

# With coverage
pytest backend/tests/steps/test_pipeline_steps.py --cov=rgenerator

# Manual pipeline integration test
python backend/tests/test_manual_pipeline.py
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
pip install -e backend/

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
    │   │   ├── pipeline_steps.py - 14 concrete step implementations (~1,465 lines)
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

**Key step categories** (all in `etl/core/pipeline_steps.py`):
- **Init/Config**: `InitRun`, `LoadConfig`, `LoadConfigFromSpec`
- **I/O**: `DiscoverInputs`, `RequestUserFiles`
- **ETL**: `RunExcelETL`, `EnrichWithContext`, `EnrichWithUserInput`
- **Export**: `ExportConsolidatedExcel`, `DeleteTempFiles`
- **Reporting**: `GenerateGraphics`, `GenerateTables`, `RenderReport`, `GenerateDocxReport`

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

## Known Issues / Tech Debt

- `pipeline_steps.py` is ~1,465 lines with 14 classes — planned refactor into per-responsibility files
- Excel database has no concurrency or transaction support — migration to PostgreSQL/SQLite planned
- Routers `dimensions.py` and `metrics.py` have duplicated `get_df`/`save_df` helpers
- `Results` and `Help` pages in the frontend are unimplemented placeholders
- No authentication or RBAC exists yet
- Legacy Streamlit app (`streamlit_app.py`, `streamlit_utils.py`) remains at root but is no longer the primary UI
