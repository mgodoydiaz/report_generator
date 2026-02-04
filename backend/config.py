from pathlib import Path

# Base del proyecto (carpeta raíz website-ui)
BASE_DIR = Path(__file__).resolve().parent.parent

# Rutas de Base de Datos (Excel)
DB_DIR = BASE_DIR / "data" / "database"

# Archivos Excel Principales
WORKFLOWS_DB_PATH = DB_DIR / "pipelines.xlsx"
TEMPLATES_DB_PATH = DB_DIR / "templates.xlsx"
DIMENSIONS_DB_PATH = DB_DIR / "dimensions.xlsx"
DIMENSION_VALUES_DB_PATH = DB_DIR / "dimension_values.xlsx"
METRICS_DB_PATH = DB_DIR / "metrics.xlsx"
METRIC_DIMENSIONS_DB_PATH = DB_DIR / "metric_dimensions.xlsx"
METRIC_DATA_DB_PATH = DB_DIR / "metric_data.xlsx"

# Directorios de Almacenamiento
PIPELINES_DIR = DB_DIR / "pipelines"
TEMPLATES_DIR = DB_DIR / "reports_templates"
UPLOADS_DIR = PIPELINES_DIR / "uploads"
