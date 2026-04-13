# ==============================================================
# BACKEND — Dockerfile multi-stage
#
# Stages:
#   base  → instala el entorno conda + dependencias del sistema
#   dev   → hot-reload; el código se monta como volumen
#   prod  → código copiado dentro de la imagen, sin reload
#
# Uso:
#   docker compose up              (dev, usa target: dev)
#   docker compose -f docker-compose.prod.yml up  (prod)
# ==============================================================

# --------------------------------------------------------------
# Stage base: imagen conda + deps de sistema + entorno Python
# --------------------------------------------------------------
FROM continuumio/miniconda3:latest AS base

# Dependencias del sistema:
#   ghostscript  → requerido por camelot-py para extraer tablas de PDF
#   libpq-dev    → headers para compilar psycopg2
#   gcc          → compilador C para paquetes con extensiones nativas
RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Crear el entorno conda primero (capa cacheada si environment.yml no cambia)
COPY environment.yml .
RUN conda env create -f environment.yml && conda clean -afy

# --------------------------------------------------------------
# Stage dev: desarrollo con hot-reload
# El código fuente se monta como volumen en docker-compose.yml,
# por eso no se copia aquí.
# --------------------------------------------------------------
FROM base AS dev

EXPOSE 8000

# pip install -e . toma el código del volumen montado en /app
CMD ["/bin/bash", "-c", \
    "conda run -n rgenerator pip install -e . -q && \
     conda run --no-capture-output -n rgenerator \
     uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload"]

# --------------------------------------------------------------
# Stage prod: imagen autocontenida lista para producción
# --------------------------------------------------------------
FROM base AS prod

# Copiar el proyecto e instalar el paquete rgenerator
COPY . .
RUN conda run -n rgenerator pip install . -q

EXPOSE 8000

CMD ["conda", "run", "--no-capture-output", "-n", "rgenerator", \
     "uvicorn", "backend.api:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
