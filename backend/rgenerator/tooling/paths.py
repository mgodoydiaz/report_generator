from pathlib import Path
import tomllib

BASE_DIR = Path(__file__).resolve().parents[3] # Sube desde backend/rgenerator hasta la raíz del proyecto
CONFIG_PATH = BASE_DIR / "config" / "settings.toml"

config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))

INPUT_DIR = BASE_DIR / config["paths"]["input_dir"]
OUTPUT_DIR = BASE_DIR / config["paths"]["output_dir"]
TMP_DIR = BASE_DIR / config["paths"]["tmp_dir"]
SCHEMAS_DIR = BASE_DIR / config["reports"]["schemas_dir"]