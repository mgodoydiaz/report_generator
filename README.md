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
pip install -e backend/
```

### 2. Configurar Entorno Frontend

```bash
cd frontend
npm install
```

### 3. Ejecutar la Aplicación Completa

Para iniciar simultáneamente el Backend (puerto 8000) y el Frontend (puerto 5173), puedes usar los scripts provistos en la raíz del proyecto:

**En Windows:**
```cmd
run_software.bat
```

**En Linux / Mac:**
```bash
bash run_software.sh
```

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
