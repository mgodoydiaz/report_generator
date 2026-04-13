# Correr la aplicación

## Requisitos previos

- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) o Anaconda
- [Node.js](https://nodejs.org/) 18+
- PostgreSQL 15+ (ver instrucciones abajo)
- MiKTeX (Windows) o `texlive-latex-base` (Linux) para generación de PDF

---

## Instalación inicial

### 1. Entorno Python

```bash
conda env create -f environment.yml
conda activate rgenerator
pip install -e .
```

### 2. Frontend

```bash
cd frontend
npm install
```

### 3. Variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales de PostgreSQL y JWT_SECRET
```

### 4. Migración de base de datos

```bash
conda activate rgenerator
python scripts/migrate_excel_to_pg.py
```

Crea las tablas, inserta la organización por defecto y migra los datos desde Excel.
Credenciales del admin creado: `admin@fundacionphp.cl` / `admin1234`

---

## Correr la aplicación

### Windows

```cmd
run_software.bat
```

Inicia automáticamente:
1. Servicio PostgreSQL (`postgresql-x64-18`)
2. Backend FastAPI → `http://127.0.0.1:8000`
3. Frontend Vite/React → `http://localhost:5173`

### Linux / WSL

```bash
chmod +x run_software.sh
./run_software.sh
```

### Manual

```bash
# Backend
conda activate rgenerator
python -m backend.api

# Frontend (otra terminal)
cd frontend
npm run dev
```

---

## Instalación de PostgreSQL

### Windows

Descargar desde [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) y seguir el asistente. Luego crear el usuario y base de datos:

```sql
CREATE USER mgodoy WITH PASSWORD 'tu_password';
CREATE DATABASE rgenerator_dev OWNER mgodoy;
GRANT ALL PRIVILEGES ON DATABASE rgenerator_dev TO mgodoy;
```

### Ubuntu / Debian (Linux o WSL)

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib

sudo service postgresql start

sudo -u postgres psql <<EOF
CREATE USER mgodoy WITH PASSWORD 'tu_password';
CREATE DATABASE rgenerator_dev OWNER mgodoy;
GRANT ALL PRIVILEGES ON DATABASE rgenerator_dev TO mgodoy;
EOF
```

Verificar conexión:
```bash
psql -h localhost -U mgodoy -d rgenerator_dev -c "\dt"
```

> **WSL:** PostgreSQL en Linux es accesible desde Windows en `localhost:5432` sin configuración adicional.

---

## Instalación de LaTeX (generación de PDF)

### Windows
Instalar [MiKTeX](https://miktex.org/download).

### Linux / WSL
```bash
sudo apt install texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended
# Opcional: soporte en español
sudo apt install texlive-lang-spanish
```

---

## Scripts de diagnóstico

```bash
# Verificar estado de la DB
python scripts/_check_db.py

# Re-migrar specs si están vacías
python scripts/_remigrate_specs.py
```
