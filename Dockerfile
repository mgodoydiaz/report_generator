# ==============================================================
# BACKEND — Dockerfile multi-stage
#
# Stages:
#   base  → python:3.11-slim + deps de sistema + dependencias pip
#   dev   → hot-reload; el código se monta como volumen
#   prod  → código copiado dentro de la imagen, sin reload
#
# Uso:
#   docker compose up              (dev, usa target: dev)
#   docker compose -f docker-compose.prod.yml up  (prod)
# ==============================================================

# --------------------------------------------------------------
# Stage base: imagen Python slim + deps de sistema + pip
# --------------------------------------------------------------
FROM python:3.11-slim AS base

# Dependencias del sistema:
#   ghostscript      → requerido por camelot-py para extraer tablas de PDF
#   gcc              → compilador C para paquetes con extensiones nativas
#   libglib2.0-0     → requerido por camelot-py / OpenCV
#   libpango-1.0-0   → requerido por WeasyPrint (layout de texto)
#   libpangoft2-1.0-0 → fuentes TrueType para WeasyPrint
#   libharfbuzz0b    → shaping de texto para WeasyPrint
#   libffi-dev       → dependencia de WeasyPrint en build
RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    gcc \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python (capa cacheada si requirements.txt no cambia)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------------------
# Stage dev: desarrollo con hot-reload
# El código fuente se monta como volumen en docker-compose.dev.yml
# --------------------------------------------------------------
FROM base AS dev

EXPOSE 8000

# pip install . toma el código del volumen montado en /app
#
# --reload-dir backend: el bind mount trae el repo completo (~24k archivos, de los
# cuales 19.5k son frontend/node_modules y 3k son .git). Docker Desktop no propaga
# inotify a través de su capa de virtualización, así que el reloader caía a polling
# y recorría todo el árbol en bucle: ~11% de CPU constante para vigilar 99 .py.
# Acotarlo a backend/ deja el hot-reload igual de útil a costo cero.
CMD ["/bin/sh", "-c", "pip install -q . && uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend"]

# --------------------------------------------------------------
# Stage prod: imagen autocontenida lista para producción
# --------------------------------------------------------------
FROM base AS prod

COPY . .
RUN pip install --no-cache-dir .

# El entrypoint aplica migraciones Alembic antes de levantar uvicorn.
# Así cada deploy se auto-migra — no hace falta correr alembic a mano.
RUN chmod +x scripts/start.sh

EXPOSE 8000

CMD ["scripts/start.sh"]
