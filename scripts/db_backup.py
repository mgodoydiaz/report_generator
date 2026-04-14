"""
db_backup.py — Crear y restaurar backups de la base de datos PostgreSQL.

Uso:
    # Crear backup
    python scripts/db_backup.py backup

    # Crear backup con nombre personalizado
    python scripts/db_backup.py backup --output backups/mi_backup.sql

    # Restaurar backup
    python scripts/db_backup.py restore backups/rgenerator_20240101_120000.sql
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent
BACKUP_DIR = ROOT / "backups"

sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mgodoy:holapocompadre977@localhost:5432/rgenerator_dev"
)


def parse_db_url(url: str) -> dict:
    p = urlparse(url)
    return {
        "host": p.hostname or "localhost",
        "port": str(p.port or 5432),
        "user": p.username or "",
        "password": p.password or "",
        "dbname": p.path.lstrip("/"),
    }


def run_backup(output_path: Path | None = None):
    db = parse_db_url(DATABASE_URL)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = BACKUP_DIR / f"rgenerator_{timestamp}.sql"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "PGPASSWORD": db["password"]}

    cmd = [
        "pg_dump",
        "-h", db["host"],
        "-p", db["port"],
        "-U", db["user"],
        "-d", db["dbname"],
        "--no-password",
        "-f", str(output_path),
    ]

    print(f"Creando backup de '{db['dbname']}' en {output_path} ...")
    result = subprocess.run(cmd, env=env)

    if result.returncode == 0:
        size_kb = output_path.stat().st_size // 1024
        print(f"✅ Backup creado exitosamente ({size_kb} KB): {output_path}")
    else:
        print("❌ Error al crear el backup.")
        sys.exit(1)


def run_restore(input_path: str):
    db = parse_db_url(DATABASE_URL)
    input_path = Path(input_path)

    if not input_path.exists():
        print(f"❌ Archivo no encontrado: {input_path}")
        sys.exit(1)

    confirm = input(
        f"⚠️  Esto sobreescribirá la base de datos '{db['dbname']}'. ¿Continuar? [s/N]: "
    )
    if confirm.lower() not in ("s", "si", "sí", "y", "yes"):
        print("Operación cancelada.")
        sys.exit(0)

    env = {**os.environ, "PGPASSWORD": db["password"]}

    # Terminar conexiones activas y limpiar la DB antes de restaurar
    drop_cmd = [
        "psql",
        "-h", db["host"],
        "-p", db["port"],
        "-U", db["user"],
        "--no-password",
        "-c",
        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{db['dbname']}' AND pid <> pg_backend_pid();",
        "postgres",
    ]
    subprocess.run(drop_cmd, env=env, capture_output=True)

    restore_cmd = [
        "psql",
        "-h", db["host"],
        "-p", db["port"],
        "-U", db["user"],
        "-d", db["dbname"],
        "--no-password",
        "-f", str(input_path),
    ]

    print(f"Restaurando backup desde {input_path} en '{db['dbname']}' ...")
    result = subprocess.run(restore_cmd, env=env)

    if result.returncode == 0:
        print(f"✅ Restauración completada exitosamente.")
    else:
        print("❌ Error durante la restauración.")
        sys.exit(1)


def list_backups():
    if not BACKUP_DIR.exists() or not any(BACKUP_DIR.glob("*.sql")):
        print("No hay backups disponibles en backups/")
        return
    backups = sorted(BACKUP_DIR.glob("*.sql"), reverse=True)
    print(f"Backups disponibles ({len(backups)}):")
    for b in backups:
        size_kb = b.stat().st_size // 1024
        print(f"  {b.name}  ({size_kb} KB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup y restauración de PostgreSQL")
    subparsers = parser.add_subparsers(dest="command")

    # backup
    backup_parser = subparsers.add_parser("backup", help="Crear un backup")
    backup_parser.add_argument("--output", help="Ruta del archivo de salida (opcional)")

    # restore
    restore_parser = subparsers.add_parser("restore", help="Restaurar un backup")
    restore_parser.add_argument("file", help="Ruta del archivo .sql a restaurar")

    # list
    subparsers.add_parser("list", help="Listar backups disponibles")

    args = parser.parse_args()

    if args.command == "backup":
        run_backup(args.output)
    elif args.command == "restore":
        run_restore(args.file)
    elif args.command == "list":
        list_backups()
    else:
        parser.print_help()
