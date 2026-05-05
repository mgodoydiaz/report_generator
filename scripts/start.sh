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
# --proxy-headers + --forwarded-allow-ips="*" hacen que uvicorn respete los
# headers X-Forwarded-Proto / X-Forwarded-For que Railway (y otros proxies)
# inyectan. Sin esto, los redirects 307 que hace FastAPI (ej: /api/metrics ->
# /api/metrics/) se construyen con http:// en lugar de https://, y el browser
# los bloquea por mixed content -> "Failed to fetch".
#
# --workers 1: el dict ACTIVE_RUNNERS en routers/pipelines.py vive en memoria
# del proceso. Con 2+ workers cada request del mismo pipeline puede caer en
# un worker distinto y no ver el runner cargado, rompiendo el flow
# upload/run/input. Mientras no haya backend de estado compartido (Redis u
# otra DB), nos quedamos en 1 worker. Para escalar, agregar Redis y mover
# ACTIVE_RUNNERS allí.
exec uvicorn backend.api:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 \
    --proxy-headers --forwarded-allow-ips='*'
