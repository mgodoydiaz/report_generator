# 📊 Informe Generator · Fundación PHP

Este repositorio contiene una aplicación que facilita la **creación automatizada de informes de resultados de pruebas académicas** para la Fundación **People Help People**.

## ✨ Propósito

El proyecto busca:
- Apoyar a la fundación en la generación rápida y estandarizada de reportes.
- Integrar resultados de pruebas en tablas y gráficos.
- Reducir el trabajo manual al transformar datos en **informes PDF profesionales** listos para entregar a los establecimientos educacionales.

## 🛠️ Tecnologías utilizadas

- [React](https://react.dev/) con [Vite](https://vitejs.dev/) para la interfaz de usuario.  
- [Tailwind CSS](https://tailwindcss.com/)  para estilos.  
- [Python](https://www.python.org/) + LaTeX para la compilación de informes en PDF.  

## 📂 Estructura del proyecto

- `src/` → código fuente en React.  
- `public/` → archivos estáticos (logos, imágenes).  
- `InformeFormPrototype.jsx` → formulario que permite definir variables y secciones del informe.  
- `crear_informe.py` → script que integra la plantilla LaTeX y compila el PDF.  

## 🚀 Características principales

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
