import pandas as pd
import os
from pathlib import Path

# Paths to the db
base_dir = Path(r"c:\\Users\\magod\\Documents\\Proyectos\\Informes PHP\\website-ui\\data\\database")

indicators_path = base_dir / "indicators.xlsx"
indicator_metrics_path = base_dir / "indicator_metrics.xlsx"

# Create indicators.xlsx if it doesn't exist
if not indicators_path.exists():
    df_ind = pd.DataFrame(columns=["id_indicator", "name", "description", "type", "updated_at"])
    df_ind.to_excel(indicators_path, index=False)
    print("Created indicators.xlsx")
else:
    print("indicators.xlsx already exists")

# Create indicator_metrics.xlsx if it doesn't exist
if not indicator_metrics_path.exists():
    df_rel = pd.DataFrame(columns=["id_indicator", "id_metric"])
    df_rel.to_excel(indicator_metrics_path, index=False)
    print("Created indicator_metrics.xlsx")
else:
    print("indicator_metrics.xlsx already exists")
