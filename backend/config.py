from pathlib import Path

# Base del proyecto (carpeta raíz website-ui)
BASE_DIR = Path(__file__).resolve().parent.parent

# Directorios de datos
DB_DIR = BASE_DIR / "data" / "database"
REPORTS_TEMPLATES_DIR = DB_DIR / "reports_templates"
PIPELINE_RUNS_DIR = BASE_DIR / "data" / "pipeline_runs"
UPLOADS_DIR = PIPELINE_RUNS_DIR / "uploads"

# ──────────────────────────────────────────────────────────────
# LEGACY: paths Excel usados SOLO por resultspy.py (pendiente de eliminar).
# NO usar en código nuevo — toda la lógica de negocio usa PostgreSQL.
# ──────────────────────────────────────────────────────────────
PIPELINES_DB_PATH = DB_DIR / "pipelines.xlsx"
SPECS_DB_PATH = DB_DIR / "specs.xlsx"
DIMENSIONS_DB_PATH = DB_DIR / "dimensions.xlsx"
DIMENSION_VALUES_DB_PATH = DB_DIR / "dimension_values.xlsx"
METRICS_DB_PATH = DB_DIR / "metrics.xlsx"
METRIC_DIMENSIONS_DB_PATH = DB_DIR / "metric_dimensions.xlsx"
METRIC_DATA_DB_PATH = DB_DIR / "metric_data.xlsx"
INDICATORS_DB_PATH = DB_DIR / "indicators.xlsx"
INDICATOR_METRICS_DB_PATH = DB_DIR / "indicator_metrics.xlsx"
