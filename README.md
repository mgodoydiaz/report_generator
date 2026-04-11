# 📊 Report Generator · Fundación PHP

Este repositorio contiene una aplicación web y motor ETL diseñado para la creación automatizada de informes de resultados de pruebas académicas (SIMCE, ensayos corporativos, etc.) para la Fundación People Help People.

## ✨ Propósito

El sistema permite procesar archivos brutos de resultados (Excel, CSV), cruzarlos con información de estudiantes y preguntas, y calcular métricas y dimensiones para finalmente generar informes PDF (LaTeX) y reportes editables (Word) listos para entregar a los establecimientos educacionales de la fundación.

## � Características Principales

- **Motor de Pipelines (ETL)**: Orquestador basado en pasos (`init_steps`, `io_steps`, `etl_steps`, `metric_steps`, `report_steps`) altamente configurable a través de archivos JSON.
- **Frontend Moderno**: Interfaz de usuario construida con **React 18 + Vite y Tailwind CSS 4**, que permite ejecutar y monitorear pipelines, cargar datos cuando el pipeline lo requiere (pausa dinámica), y revisar catálogos de dimensiones y métricas.
- **Backend API**: Servidor construido con **FastAPI** (`backend/api.py`) que expone los endpoints para interactuar con el motor base `rgenerator`.
- **Generación de Reportes**: Gráficos automatizados generados con `matplotlib` e informes completos usando plantillas `LaTeX` o archivos editables usando `docxtpl` (Jinja2 para Word).

## ▶️ Instalación y Uso Rápido

### Prerrequisitos
- [Miniconda](https://docs.anaconda.com/miniconda/) o Anaconda.
- [Node.js](https://nodejs.org/) (versión 18+ recomendada) y npm.

### 1. Configurar Entorno Backend

```bash
# Crear entorno desde el archivo environment.yml
conda env create -f environment.yml

# Activar el entorno
conda activate rgenerator

# Instalar el paquete rgenerator en modo editable
pip install -e .
```

### 2. Configurar Entorno Frontend

```bash
cd frontend
npm install
```

### 3. Configurar PostgreSQL

La base de datos es PostgreSQL. Ver instrucciones de instalación más abajo según tu sistema operativo.

Una vez instalado y creada la base de datos, configura las variables de entorno:

```bash
cp .env.example .env
# Editar .env con tus credenciales de PostgreSQL y un JWT_SECRET
```

Luego ejecuta la migración inicial (crea tablas y migra datos desde los Excel):

```bash
conda activate rgenerator
python scripts/migrate_excel_to_pg.py
```

Esto crea el usuario admin por defecto: `admin@fundacionphp.cl` / `admin1234`

### 4. Ejecutar la Aplicación

**Windows (recomendado):**
```cmd
run_software.bat
```

Inicia automáticamente PostgreSQL (servicio Windows), el backend en `http://127.0.0.1:8000` y el frontend en `http://localhost:5173`.

**Manual:**
```bash
# Backend
conda activate rgenerator
python -m backend.api

# Frontend (otra terminal)
cd frontend
npm run dev
```

---

## 🐘 Instalación de PostgreSQL

### Windows

Descargar el instalador desde [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) y seguir el asistente. Al finalizar, abrir pgAdmin o `psql` y ejecutar:

```sql
CREATE USER mgodoy WITH PASSWORD 'tu_password';
CREATE DATABASE rgenerator_dev OWNER mgodoy;
GRANT ALL PRIVILEGES ON DATABASE rgenerator_dev TO mgodoy;
```

### Ubuntu / Debian (Linux o WSL)

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# Iniciar el servicio
sudo service postgresql start

# Crear usuario y base de datos
sudo -u postgres psql <<EOF
CREATE USER mgodoy WITH PASSWORD 'tu_password';
CREATE DATABASE rgenerator_dev OWNER mgodoy;
GRANT ALL PRIVILEGES ON DATABASE rgenerator_dev TO mgodoy;
EOF
```

Verificar que la conexión funciona:

```bash
psql -h localhost -U mgodoy -d rgenerator_dev -c "\dt"
```

**Para WSL:** PostgreSQL corre en Linux pero es accesible desde Windows en `localhost:5432`. El backend de Windows se conecta normalmente.

## 📂 Estructura del Proyecto

- `backend/` : Código central. Contiene el servidor FastAPI (`api.py`), la configuración y el paquete `rgenerator` (el motor ETL y generador de reportes).
- `frontend/` : Interfaz de usuario React interactiva para gestionar y correr pipelines.
- `data/` : Directorio principal de datos y bases de datos locales:
  - `database/`: Bases de datos Excel (`metrics.xlsx`, `dimensions.xlsx`, etc.) y configuraciones de pipelines en JSON.
  - `input/`: Archivos base.
  - `output/`: Reportes generados.
  - `pipeline_runs/` y `tmp/`: Artefactos transaccionales generados en ejecuciones.
- `docs/` : Documentación técnica adicional, diagramas y tutoriales.
- `config/` : Archivos de texto o configuraciones heredadas (legacy/migrando).
- `scripts/` : Scripts de terminal para ejecutar procesos ETL aislados o tareas de mantención.
- `.agents/workflows/` : Recetario e instrucciones para que Agentes de IA asistan en el desarrollo y administración del sistema.

## 🎯 Futuro y Roadmap

El proyecto se encuentra en constante evolución hacia una arquitectura SaaS más robusta. 
Puedes consultar el archivo **[`ROADMAP.md`](./ROADMAP.md)** para ver la deuda técnica, el backlog de tareas pendientes y el historial de versiones del sistema.

---

👨‍💻 Desarrollado por Miguel Godoy Díaz
