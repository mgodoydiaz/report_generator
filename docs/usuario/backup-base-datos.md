# Backup y restauración de la base de datos

El script `scripts/db_backup.py` permite crear y restaurar backups de PostgreSQL usando `pg_dump`.

Los archivos se guardan en la carpeta `backups/` (ignorada por git).

---

## Crear un backup

```bash
conda activate rgenerator

# Backup con nombre automático (backups/rgenerator_YYYYMMDD_HHMMSS.sql)
python scripts/db_backup.py backup

# Backup con nombre personalizado
python scripts/db_backup.py backup --output backups/antes_deploy.sql
```

## Listar backups disponibles

```bash
python scripts/db_backup.py list
```

## Restaurar un backup

```bash
python scripts/db_backup.py restore backups/rgenerator_20240101_120000.sql
```

Pedirá confirmación antes de sobreescribir la base de datos.

---

## Requisitos

`pg_dump` y `psql` deben estar en el PATH:

- **Windows:** Se instalan con PostgreSQL. Verificar en `C:\Program Files\PostgreSQL\18\bin\`.
- **Linux:** `sudo apt install postgresql-client`

---

## Recomendaciones

- Crear un backup antes de cualquier migración o deploy importante.
- Guardar copias externas de los archivos `.sql` periódicamente.
