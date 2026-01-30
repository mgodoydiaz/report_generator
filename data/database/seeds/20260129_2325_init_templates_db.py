import pandas as pd
import datetime
import os

# Define the data directory
db_dir = r"c:\Users\magod\Documents\Proyectos\Informes PHP\website-ui\data\database"
excel_path = os.path.join(db_dir, "templates.xlsx")
templates_dir = os.path.join(db_dir, "reports_templates")

# Create templates directory if it doesn't exist
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)

# Define initial templates data
data = [
    {
        "id_template": 1,
        "name": "Informe Ensayo SIMCE Lenguaje",
        "description": "Plantilla estándar para informes de SIMCE Lenguaje 2° Medio.",
        "type": "Reporte",
        "config_path": "esquema_informe_lenguaje.json",
        "updated_at": "2026-01-29 23:00:00"
    }
]

# Create DataFrame
df = pd.DataFrame(data)

# Save to Excel
df.to_excel(excel_path, index=False)

print(f"Excel created at: {excel_path}")
print(f"Configuration folder ready at: {templates_dir}")
