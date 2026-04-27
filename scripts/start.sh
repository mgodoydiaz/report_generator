#!/bin/sh
# start.sh — Entrypoint de producción para el backend.
#
# Aplica las migraciones Alembic pendientes antes de levantar el servidor.
# Si el schema ya está al día, alembic upgrade head es un no-op rápido.
# Si falla (p.ej. conflicto de migración), el deploy falla — esto es
# intencional: mejor caer con un error claro que levantar con schema roto.
set -e

echo "→ Aplicando migraciones Alembic..."
alembic upgrade head

echo "→ Iniciando uvicorn en puerto ${PORT:-8000}..."
exec uvicorn backend.api:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2
