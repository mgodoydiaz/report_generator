"""
backup_supabase.py - Backup periodico de la BD Supabase con pg_dump.

Supabase Free no incluye backups automaticos (solo Pro tier en adelante),
asi que mantenemos copias locales con pg_dump --format=custom (.dump).

Uso:
    python scripts/backup_supabase.py
    python scripts/backup_supabase.py --keep 8       # retener ultimos 8 backups
    python scripts/backup_supabase.py --output-dir D:/backups/supabase

Carga las credenciales desde .env.supabase (gitignored). Conecta usando la
Session pooler (puerto 5432, IPv4) que funciona desde cualquier red.

Requiere pg_dump instalado y accesible en el PATH (el del Postgres local sirve).

Para schedularlo en Windows Task Scheduler usa el helper run_supabase_backup.bat
de esta misma carpeta (lunes y viernes 03:00):

    schtasks /Create /TN "RGenerator-Supabase-Backup" ^
        /TR "\\wsl.localhost\\Ubuntu\\home\\atlas\\proyectos\\report_generator\\scripts\\run_supabase_backup.bat" ^
        /SC WEEKLY /D MON,FRI /ST 03:00 /F

(Pendiente registrar la tarea: ver TODO en ROADMAP.md.)
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> dict[str, str]:
    """Parser minimo de KEY=VALUE para .env.supabase (sin dependencia de dotenv)."""
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Z0-9_]+)\s*=\s*(.*)$", line)
        if m:
            env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return env


def parse_session_pooler_url(url: str) -> dict[str, str]:
    """Extrae host/port/user/db/password de una URL postgresql:// (con URL-encoding)."""
    p = urlparse(url)
    if p.scheme != "postgresql":
        raise ValueError(f"Esquema esperado postgresql://, recibi: {p.scheme}")
    return {
        "host": p.hostname or "",
        "port": str(p.port or 5432),
        "user": unquote(p.username or ""),
        "password": unquote(p.password or ""),
        "dbname": (p.path or "/postgres").lstrip("/") or "postgres",
    }


def run_pg_dump(conn: dict[str, str], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "pg_dump",
        "-h", conn["host"],
        "-p", conn["port"],
        "-U", conn["user"],
        "-d", conn["dbname"],
        "--format=custom",
        "--no-owner",
        "--no-acl",
        "--file", str(output_path),
    ]
    env = {**os.environ, "PGPASSWORD": conn["password"]}
    print(f"-> pg_dump {conn['host']}:{conn['port']}/{conn['dbname']} -> {output_path.name}")
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"pg_dump fallo con exit code {proc.returncode}")


def cleanup_old_backups(dir_: Path, prefix: str, keep: int) -> int:
    """Elimina backups viejos manteniendo los ultimos `keep`. Retorna cuantos elimino."""
    backups = sorted(dir_.glob(f"{prefix}*.dump"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed = 0
    for old in backups[keep:]:
        old.unlink()
        print(f"   removido (retencion): {old.name}")
        removed += 1
    return removed


def main() -> None:
    ap = argparse.ArgumentParser(description="Backup pg_dump de Supabase con retencion.")
    ap.add_argument("--env-file", type=Path, default=ROOT / ".env.supabase",
                    help="Archivo de variables (.env.supabase)")
    ap.add_argument("--url-var", default="DATABASE_URL_SESSION",
                    choices=["DATABASE_URL_SESSION", "DATABASE_URL_DIRECT", "DATABASE_URL_TRANSACTION"],
                    help="Cual URL usar (Session pooler recomendado)")
    ap.add_argument("--output-dir", type=Path, default=ROOT / "backups",
                    help="Directorio destino (default: backups/)")
    ap.add_argument("--keep", type=int, default=8,
                    help="Cuantos backups retener (default: 8 -> ~2 meses si es semanal)")
    ap.add_argument("--prefix", default="supabase_",
                    help="Prefijo de los archivos de backup")
    args = ap.parse_args()

    if shutil.which("pg_dump") is None:
        raise SystemExit("ERROR: pg_dump no encontrado en PATH. Instala Postgres client.")

    env = load_env_file(args.env_file)
    url = env.get(args.url_var) or os.getenv(args.url_var, "")
    if not url:
        raise SystemExit(f"ERROR: no encuentro {args.url_var} en {args.env_file} ni en el entorno.")
    if "<PASTE_PASSWORD_HERE>" in url:
        raise SystemExit(f"ERROR: {args.url_var} todavia tiene el placeholder. Edita {args.env_file}.")

    conn = parse_session_pooler_url(url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = args.output_dir / f"{args.prefix}{timestamp}.dump"

    run_pg_dump(conn, output)
    size_kb = output.stat().st_size // 1024
    print(f"OK backup creado: {output} ({size_kb} KB)")

    cleanup_old_backups(args.output_dir, args.prefix, args.keep)


if __name__ == "__main__":
    main()
