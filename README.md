# 📊 Report Generator · Fundación PHP

Este repositorio contiene una aplicación que facilita la creación automatizada de informes de resultados de pruebas académicas para la Fundación People Help People.

## ✨ Propósito

El proyecto busca apoyar a la fundación en la generación rápida y estandarizada de reportes, integrando resultados de pruebas en tablas y gráficos, y reduciendo el trabajo manual al transformar datos en informes PDF listos para entregar a los establecimientos educacionales.

## 📂 Estructura del proyecto

- `backend/` contiene la librería principal para ETL y generación de informes  
- `scripts/` contiene los programas ejecutables desde consola  
- `public/` contiene recursos estáticos como logos  
- `latex_templates/` almacena plantillas usadas para compilar los informes  
- `src/` corresponde al frontend prototipo original que será reescrito

## ▶️ Instalación y uso

### 1. Crear el environment con conda

```bash
conda env create -f environment.yml
conda activate rgenerator
```

### 2. Ejecutar ETL desde consola

```bash
python scripts/run_etl.py --input ruta_input --output ruta_output
```

### 3. Generar informe PDF desde consola

```bash
python scripts/generate_report.py --schema ruta_esquema.json --data ruta_datos.csv --tipo informe_tipo --output ruta_informe.pdf
```

## 🚀 Características principales --legacy-- 

- Formulario web para definir:
  - Variables del documento (logos, títulos, pie de página, autor, etc.).
  - Secciones fijas (tablas o gráficos).  
- Generación de archivo `esquema_informe.json` listo para alimentar el pipeline en Python.  
- Exportación a **PDF final** mediante LaTeX.  
- Persistencia de configuraciones en el navegador (localStorage).  

## 🎯 Futuro

Este proyecto se proyecta como base para un **SaaS de reportería académica**, que permita a colegios y fundaciones generar sus propios informes de manera autónoma y con personalización total.

---

👨‍💻 Desarrollado por Miguel Godoy Díaz
