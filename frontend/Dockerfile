# ==============================================================
# FRONTEND — Dockerfile multi-stage
#
# Stages:
#   base   → instala dependencias npm (cacheadas)
#   dev    → Vite dev server con HMR; código montado como volumen
#   build  → genera los estáticos (npm run build)
#   prod   → nginx sirve los estáticos del stage build
#
# Uso:
#   docker compose up                                    (dev)
#   docker compose -f docker-compose.prod.yml up         (prod)
# ==============================================================

# --------------------------------------------------------------
# Stage base: Node + dependencias npm
# --------------------------------------------------------------
FROM node:20-alpine AS base

WORKDIR /app

# Instalar deps antes de copiar el código fuente (capa cacheada)
COPY package*.json ./
RUN npm ci

# --------------------------------------------------------------
# Stage dev: Vite dev server con hot-module replacement
# El código fuente se monta como volumen en docker-compose.yml.
# node_modules se mantiene en el contenedor (no se sobreescribe
# por el volumen anónimo declarado en compose).
# --------------------------------------------------------------
FROM base AS dev

EXPOSE 5173

CMD ["npm", "run", "dev"]

# --------------------------------------------------------------
# Stage build: compila los estáticos de producción
# --------------------------------------------------------------
FROM base AS build

COPY . .
RUN npm run build

# --------------------------------------------------------------
# Stage prod: nginx liviano sirve dist/
# --------------------------------------------------------------
FROM nginx:alpine AS prod

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
