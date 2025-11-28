# Changelog

## 2024-11-25 02:45
- Revisé `legacy/backend/simce_things` y clasifiqué su contenido:
  - **ETL**: `script_unificar.py`, `script_unificar2.py`, `funciones.py` (limpieza, enriquecimiento y consolidación de estudiantes).
  - **Generación de reportes PDF**: `crear_informe_lenguaje.py`, `crear_informe_matematicas.py`, `funciones_informe.py` (armado de tablas/gráficos y render LaTeX).
  - **Esquemas JSON**: `esquema_informe.json` (estructura de informes).
- Organicé los esquemas JSON en `backend/rgenerator/schemas/` y moví `legacy/backend/simce_things/esquema_informe.json` a `backend/rgenerator/schemas/esquema_informe.json` para centralizar los contratos de reporte dentro del paquete activo.
- Consolidé la función duplicada `valor_promedio_agrupado_por` dentro de `backend/rgenerator/tooling/plot_tools.py` para evitar mantener dos versiones divergentes.
- Creé `backend/rgenerator/__init__.py` y expuse funciones/constantes de `tooling` desde `backend/rgenerator/tooling/__init__.py` para poder importarlas directamente con `import rgenerator.tooling`.
- Añadí la carpeta `tests/` con `pytest` para verificar que el paquete `rgenerator` y sus reexportaciones de `tooling` se importan correctamente.
- Centralicé el número de versión en `backend/rgenerator/_version.py` y lo expongo como `rgenerator.__version__`.
- Incorporé `pyproject.toml` y un `setup.py` en la raíz para permitir la instalación local/editable del paquete `rgenerator` mediante `pip install -e .`, leyendo la versión desde dicho módulo.
- Agregué `run_tests.py` y `.coveragerc` para ejecutar `pytest` con cobertura (`pytest --cov`) de forma consistente.
