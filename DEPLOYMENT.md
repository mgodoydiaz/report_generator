# Deployment

Runbook operacional de Report Generator en producción.

---

## Arquitectura

| Componente | Proveedor | Región | Plan |
|---|---|---|---|
| Backend FastAPI | Railway | `us-east4-eqdc4a` (Virginia, USA) | Hobby ($5/mes) |
| Base de datos PostgreSQL | Supabase | `sa-east-1` (São Paulo, Brasil) | Free |
| Frontend | _pendiente_ | — | — |

URL pública del backend: `https://rgenerator-backend-production.up.railway.app`

Versión productiva actual: tag `v0.2.x` en rama `main`.

### Por qué esta combinación

- **Supabase São Paulo**: latencia mínima desde Chile y Perú (mercados objetivo de la fundación). PG 17 administrado, backup manual via `pg_dump`.
- **Railway us-east4**: la región más cercana a São Paulo disponible en plan Hobby (~150 ms ↔ Supabase). No se pausa por inactividad. $5 incluye uso típico de FastAPI ligero.

---

## Variables de entorno en Railway

Configuradas en Railway → Service `rgenerator-backend` → Variables. La copia local de referencia está en `.env.railway` (gitignored).

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Supabase Session pooler (`aws-1-sa-east-1.pooler.supabase.com:5432`). Password URL-encoded |
| `JWT_SECRET` | 32 bytes hex (`secrets.token_hex(32)`). Distinto del local |
| `JWT_EXPIRE_HOURS` | `8` |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `SQL_ECHO` | `false` |
| `CORS_ORIGINS` | Coma-separadas. Ej: `https://mgodoy.dev,https://apps.mgodoy.dev` |
| `PORT` | (auto-inyectada por Railway, no setear) |

---

## Redeploy

### Trigger automático

Push a `main` en GitHub → Railway detecta el commit → build de Docker (multi-stage `python:3.11-slim` + apt deps + pip + copia código) → arranca contenedor con `scripts/start.sh` que:

1. Aplica migraciones Alembic (`alembic upgrade head`).
2. Levanta uvicorn en `0.0.0.0:$PORT` con 2 workers.

Tiempo típico: 3 a 5 minutos.

### Health check

```bash
curl -i https://rgenerator-backend-production.up.railway.app/
```

Debe responder `200 OK` con la página HTML de status.

### Rollback

En Railway → Service → Deployments → buscar el deployment anterior exitoso → menú `⋯` → "Redeploy".

O via git:

```bash
git revert <commit-malo>
git push origin main
```

---

## Backups de Supabase

Supabase Free no incluye backups automáticos. Los corre `scripts/backup_supabase.py`.

### Backup manual

```bash
python scripts/backup_supabase.py                    # default: 8 últimos en backups/
python scripts/backup_supabase.py --keep 16          # retener 16
python scripts/backup_supabase.py --output-dir D:/backups/rgenerator
```

Genera `backups/supabase_YYYYMMDD_HHMMSS.dump` (formato `pg_dump --format=custom`).

### Schedule (Windows Task Scheduler)

Helper: `scripts/run_supabase_backup.bat` (ya con logging a `backups/backup_supabase.log`).

Registrar tarea (lunes y viernes 03:00):

```cmd
schtasks /Create /TN "RGenerator-Supabase-Backup" ^
  /TR "\\wsl.localhost\Ubuntu\home\atlas\proyectos\report_generator\scripts\run_supabase_backup.bat" ^
  /SC WEEKLY /D MON,FRI /ST 03:00 /F
```

---

## Restaurar un backup

### Opción A — restaurar a Supabase (sobrescribiendo prod)

ATENCIÓN: destructivo. Hacer un dump fresco antes por si acaso.

```bash
# 1. Backup de seguridad antes
python scripts/backup_supabase.py --keep 16

# 2. Restaurar el dump elegido (drop + recreate de objetos)
PGPASSWORD='<password-supabase>' pg_restore \
  --clean --if-exists --no-owner --no-acl \
  -h aws-1-sa-east-1.pooler.supabase.com -p 5432 \
  -U postgres.xcpywlikzjdvhihlfbrn -d postgres \
  backups/supabase_YYYYMMDD_HHMMSS.dump

# 3. Resetear secuencias (idempotente)
PGPASSWORD='<password-supabase>' psql \
  -h aws-1-sa-east-1.pooler.supabase.com -p 5432 \
  -U postgres.xcpywlikzjdvhihlfbrn -d postgres \
  -f scripts/_reset_sequences.sql   # si existe; sino ver "Apéndice: reset secuencias"
```

### Opción B — clonar prod a una BD local para inspección

```bash
PGPASSWORD='<password-local>' pg_restore \
  --clean --if-exists --no-owner --no-acl \
  -h localhost -p 5432 -U mgodoy -d rgenerator_dev \
  backups/supabase_YYYYMMDD_HHMMSS.dump
```

---

## Rotar credenciales

### Password de Supabase

1. Supabase Dashboard → Project → Settings → Database → "Reset database password".
2. Copiar el nuevo password al gestor.
3. Actualizar `.env.supabase` local (en `SUPABASE_DB_PASSWORD` literal y en las 3 `DATABASE_URL_*` URL-encoded).
4. Actualizar la variable `DATABASE_URL` en Railway → Variables (URL-encoded).
5. Railway redeployea automáticamente al cambiar variables.
6. Validar con `curl /` y `POST /api/auth/login`.

### JWT_SECRET

1. Generar: `python -c "import secrets; print(secrets.token_hex(32))"`.
2. Actualizar en `.env.railway` local.
3. Actualizar variable `JWT_SECRET` en Railway → Variables.
4. **Efecto**: invalida todos los tokens emitidos hasta ahora. Los usuarios activos quedan deslogueados y deben volver a entrar.

### Caracteres reservados en URL

Si el password contiene `+`, `@`, `/`, `:`, `?`, `#`, `%`, hay que URL-encoded en cualquier `DATABASE_URL`:

| Char | Encoded |
|---|---|
| `+` | `%2B` |
| `@` | `%40` |
| `/` | `%2F` |
| `:` | `%3A` |
| `?` | `%3F` |
| `%` | `%25` |

El password literal (`SUPABASE_DB_PASSWORD`, flags `-p` o `PGPASSWORD`) NO se encodea.

---

## Pausa de Supabase Free

Supabase pausa el proyecto si no hay actividad en 7 días. Mitigaciones actuales:

- Backups via `pg_dump` los lunes y viernes ya cuentan como actividad.
- Cuando el sitio tenga frontend público o uso real, el tráfico mismo lo mantiene despierto.

Pendiente (opcional): configurar `cron-job.org` para pingear semanalmente un endpoint del backend que toque la DB (ej. `/api/health/db` cuando exista).

---

## Latencia esperada desde Chile

| Endpoint | Tiempo típico | Notas |
|---|---|---|
| `/` (sin DB) | ~210 ms | Solo RTT Temuco↔Railway |
| `/api/auth/login` | ~960 ms | Incluye RTT + bcrypt (~300 ms CPU) + query Railway↔Supabase |
| `GET /api/pipelines` (autenticado) | ~600-900 ms | Esperado, una query simple |

Si crecen mucho, sospechar:
- N+1 en el backend (ver con `SQL_ECHO=true` temporalmente).
- Falta de índices en alguna columna usada en JOINs.
- Pool de conexiones agotado (ver `pool_size` en `backend/database.py`).

---

## Logs y observabilidad

- **Logs del backend**: Railway → Service → Deployments → Deploy Logs (en vivo) o HTTP Logs.
- **Métricas (CPU/RAM/Egreso)**: Railway → Service → Metrics.
- **Logs de la DB**: Supabase Dashboard → Project → Logs → Postgres logs.
- **Queries lentas**: Supabase → Database → Query Performance.

---

## Apéndice: reset de secuencias post-restore

Si después de un restore las secuencias quedan desfasadas (`nextval` retorna IDs ya usados):

```sql
DO $$
DECLARE r RECORD; qry TEXT;
BEGIN
  FOR r IN
    SELECT n.nspname AS schema_name, c.relname AS seq_name,
           t.relname AS tbl_name, a.attname AS col_name
    FROM pg_class c
    JOIN pg_depend d ON d.objid = c.oid AND d.deptype = 'a'
    JOIN pg_class t ON d.refobjid = t.oid
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE c.relkind = 'S' AND n.nspname = 'public'
  LOOP
    qry := format(
      'SELECT setval(%L, COALESCE((SELECT MAX(%I) FROM %I.%I), 0) + 1, false)',
      r.schema_name||'.'||r.seq_name, r.col_name, r.schema_name, r.tbl_name
    );
    EXECUTE qry;
  END LOOP;
END $$;
```
