# Guía de despliegue con Docker

Esta guía explica cómo levantar la aplicación en un servidor usando Docker, tanto en modo **desarrollo** como en modo **producción**.

---

## Requisitos previos

Instalar en el servidor:

- [Docker Engine](https://docs.docker.com/engine/install/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/install/) ≥ 2.20 (viene incluido en Docker Desktop)

Verificar que ambos estén disponibles:

```bash
docker --version
docker compose version
```

---

## 1. Clonar el repositorio

```bash
git clone https://github.com/mgodoydiaz/report_generator.git
cd report_generator
```

---

## 2. Configurar variables de entorno

Copiar la plantilla y completar los valores:

```bash
cp .env.example .env
```

Editar `.env` con un editor de texto (nano, vim, etc.):

```bash
nano .env
```

### Variables obligatorias

| Variable | Descripción | Ejemplo |
|---|---|---|
| `POSTGRES_USER` | Usuario de PostgreSQL | `rgenerator` |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL | `una_clave_segura` |
| `POSTGRES_DB` | Nombre de la base de datos | `rgenerator_dev` |
| `JWT_SECRET` | Clave secreta para tokens JWT | ver abajo |

Generar un `JWT_SECRET` seguro:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> **Importante:** el archivo `.env` nunca debe subirse al repositorio. Ya está incluido en `.gitignore`.

### Diferencia de variables entre dev y prod

En **desarrollo**, las variables tienen valores por defecto en el `docker-compose.dev.yml` y son opcionales. En **producción**, todas son obligatorias y deben estar en `.env` sin excepción.

Para producción agregar también:

```env
CORS_ORIGINS=https://tu-dominio.com
JWT_EXPIRE_HOURS=8
```

---

## 3. Despliegue en desarrollo

El entorno de desarrollo usa hot-reload tanto en el backend (uvicorn `--reload`) como en el frontend (Vite HMR). El código fuente se monta como volumen, por lo que los cambios se reflejan inmediatamente sin reconstruir la imagen.

### Construir e iniciar

```bash
docker compose up --build
```

La primera vez tarda varios minutos porque descarga la imagen de Miniconda e instala el entorno conda. Las siguientes veces usa la caché de Docker y es más rápido.

### Verificar que todo levantó

```bash
docker compose ps
```

Deberías ver los tres servicios en estado `running`:

```
NAME                    STATUS
reportgenerator-db-1        running (healthy)
reportgenerator-backend-1   running
reportgenerator-frontend-1  running
```

### Acceder a la aplicación

| Servicio | URL |
|---|---|
| Frontend (Vite) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Docs interactivos (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

### Iniciar en segundo plano

```bash
docker compose up --build -d
```

Ver los logs después:

```bash
docker compose logs -f
```

---

## 4. Despliegue en producción

El entorno de producción construye imágenes autocontenidas: el código se copia dentro de la imagen, el frontend se compila con `npm run build` y nginx lo sirve en el puerto 80. El backend corre con 2 workers sin hot-reload.

### Construir e iniciar

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

### Verificar el estado

```bash
docker compose -f docker-compose.prod.yml ps
```

### Acceder a la aplicación

| Servicio | URL |
|---|---|
| Frontend (nginx) | http://tu-servidor |
| Backend API | http://tu-servidor:8000 |
| Docs interactivos (Swagger) | http://tu-servidor:8000/docs |

> El frontend en producción hace proxy automático de las rutas `/api/*` al backend, por lo que desde el navegador todo se ve bajo el mismo dominio.

---

## 5. Comandos útiles

### Ver logs en tiempo real

```bash
# Todos los servicios
docker compose logs -f

# Solo el backend
docker compose logs -f backend

# Solo el frontend
docker compose logs -f frontend
```

Para producción, agregar `-f docker-compose.prod.yml` después de `docker compose`.

### Reiniciar un servicio sin reconstruir

```bash
docker compose restart backend
```

### Reconstruir solo un servicio

```bash
docker compose up --build backend
```

### Detener todo

```bash
# Dev
docker compose down

# Prod
docker compose -f docker-compose.prod.yml down
```

> `down` detiene y elimina los contenedores pero **no** elimina los volúmenes (la base de datos se mantiene).

### Eliminar también la base de datos

```bash
docker compose down -v
```

> Esto borra el volumen `postgres_data`. Úsalo solo si quieres comenzar desde cero.

### Abrir una terminal dentro de un contenedor

```bash
# Backend
docker compose exec backend bash

# Base de datos (cliente psql)
docker compose exec db psql -U rgenerator -d rgenerator_dev
```

---

## 6. Actualizar la aplicación en producción

Cuando hay cambios en el código:

```bash
# 1. Traer los últimos cambios
git pull origin main

# 2. Reconstruir e reiniciar los servicios afectados
docker compose -f docker-compose.prod.yml up --build -d

# 3. Verificar que levantó correctamente
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

---

## 7. Estructura de archivos Docker

```
report_generator/
├── Dockerfile                  # Backend (multi-stage: base / dev / prod)
├── docker-compose.dev.yml      # Entorno de desarrollo
├── docker-compose.prod.yml     # Entorno de producción
├── .dockerignore               # Archivos excluidos del contexto de build
├── .env.example                # Plantilla de variables de entorno
└── frontend/
    ├── Dockerfile              # Frontend (multi-stage: base / dev / build / prod)
    └── nginx.conf              # Configuración nginx para producción
```

---

## 8. Solución de problemas frecuentes

### El backend falla al iniciar

Verificar que la base de datos levantó correctamente:

```bash
docker compose logs db
```

Si PostgreSQL aún está iniciando, el backend reintentará la conexión. Si persiste, revisar que `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_DB` en `.env` coincidan con los del contenedor.

### Cambios en el frontend no se reflejan (dev)

El volumen anónimo de `node_modules` puede quedar desactualizado si se agregaron nuevas dependencias. Reconstruir:

```bash
docker compose up --build frontend
```

### Puerto ya en uso

Si el puerto 8000 o 5173 está ocupado, detener el proceso que lo usa o cambiar el mapeo en `docker-compose.dev.yml`:

```yaml
ports:
  - "8001:8000"   # host:contenedor
```

### La imagen tarda demasiado en construirse

La primera build del backend descarga Miniconda y el entorno conda completo (~1.5 GB). Es normal. Las builds posteriores usan la caché de Docker y son mucho más rápidas.

Si se agrega un paquete a `environment.yml`, solo esa capa se reconstruye.
