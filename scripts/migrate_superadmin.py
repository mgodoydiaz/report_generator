"""
scripts/migrate_superadmin.py — Agrega columnas para superadmin y organizaciones.

Ejecutar UNA vez:
    python scripts/migrate_superadmin.py
"""
import os
import sys
from pathlib import Path

# Asegura que backend/ esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mgodoy:holapocompadre977@localhost:5432/rgenerator_dev"
)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

migrations = [
    "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS description TEXT DEFAULT ''",
    "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_superadmin BOOLEAN DEFAULT FALSE",
]

for sql in migrations:
    cur.execute(sql)
    print(f"OK: {sql[:70]}")

# Marcar el primer admin como superadmin
cur.execute("UPDATE users SET is_superadmin = TRUE WHERE email = 'admin@fundacionphp.cl'")
print(f"Superadmin asignado: {cur.rowcount} usuario(s)")

conn.commit()
cur.close()
conn.close()
print("\nMigraciones completadas.")
