# Comunicación Agente

**Pregunta 1:** ¿Qué es `AGENTS.md` dentro del repositorio?  
**Respuesta 1:** Recorrí todo `website-ui` con `find`/`rg` y confirmé que no existe un archivo con ese nombre en el árbol actual.

**Pregunta 2:** ¿Cuáles son las dependencias usadas en los imports de los `.py`?  
**Respuesta 2:** Parseé todos los archivos Python con `ast` y listé módulos estándar, terceros (`requests`, `pandas`, `numpy`, `matplotlib`, etc.) y los imports locales que conforman la librería del backend.

**Pregunta 3:** Lee el repositorio y actualiza `codex-review.md` con los hallazgos.  
**Respuesta 3:** Revisé la estructura real (`backend/rgenerator`) y reescribí `codex-review.md` detallando módulos faltantes, scripts vacíos, errores en `consolidar_dia.py` y riesgos operativos.

**Pregunta 4:** Revisa `legacy/backend/simce_things`, clasifica ETL/esquemas/reportes y mueve los esquemas a `rgenerator`.  
**Respuesta 4:** Identifiqué los scripts ETL (`script_unificar*.py`, `funciones.py`), los generadores de informes (`crear_informe_*.py`, `funciones_informe.py`) y trasladé `esquema_informe.json` a `backend/rgenerator/schemas/`, dejando registro en `backend/rgenerator/CHANGELOG.md`.

**Pregunta 5:** Actualiza el changelog con horario, crea este archivo de comunicación y revisa la concordancia entre `funciones`/`funciones_informe` vs `backend/rgenerator/tooling`.  
**Respuesta 5:** Actualicé `backend/rgenerator/CHANGELOG.md` con la hora `02:45`, abrí este registro y analicé en detalle `legacy/backend/simce_things/funciones*.py` frente a `backend/rgenerator/tooling/*` para reportar las coincidencias, duplicidades y brechas de funciones solicitadas.

**Pregunta 6:** Agrega en el changelog la consolidación de la función duplicada y revisa si `resumen_por_curso`, `logro_promedio_por_nivel` y `boxplot_logro_por_curso` tienen equivalentes en `tooling`.  
**Respuesta 6:** Eliminé la segunda definición de `valor_promedio_agrupado_por` en `backend/rgenerator/tooling/plot_tools.py`, dejé constancia en `backend/rgenerator/CHANGELOG.md` y confirmé que:
- `resumen_por_curso` se puede obtener con `tooling.report_tools.resumen_estadistico_basico` (agrupando por `Curso` sobre la columna `Logro`).
- `logro_promedio_por_nivel` es un caso particular de `tooling.plot_tools.grafico_barras_promedio_por` pasando `agrupar_por="Nivel"`.
- `boxplot_logro_por_curso` coincide con `tooling.plot_tools.boxplot_valor_por_curso` usando `columna_valor="Logro"`.
No es necesario crear funciones nuevas; solo documentar estos usos parametrizados.

**Pregunta 7:** Dentro de `rgenerator`, crea/edita los `__init__.py` necesarios para exponer las funciones y constantes de `tooling`.  
**Respuesta 7:** Añadí `backend/rgenerator/__init__.py` para registrar el paquete y extendí `backend/rgenerator/tooling/__init__.py` con importaciones explícitas de `etl_tools`, `plot_tools`, `report_tools` y `constants`, de modo que utilidades como `grafico_barras_promedio_por` o `formato_informe_generico` puedan importarse directamente desde `rgenerator.tooling`.

**Pregunta 8:** Crea una carpeta de testing con pytest para comprobar las importaciones.  
**Respuesta 8:** Preparé `tests/` con `conftest.py` (inyecta `backend/` al `sys.path`) y `test_rgenerator_imports.py`, que verifica que `import rgenerator` funciona y que `rgenerator.tooling` expone las funciones/constantes clave.

**Pregunta 9:** Crea `pyproject.toml` y `setup.py` para poder instalar la librería localmente en modo editable.  
**Respuesta 9:** Añadí `pyproject.toml` (especifica `setuptools`/`wheel` como build backend) y `setup.py`, que define metadata del paquete, dependencias principales y la ubicación del código (`backend/`). Con esto se puede ejecutar `pip install -e .` para usar `rgenerator` como librería instalada.

**Pregunta 10:** Deja la versión del paquete como una constante interna.  
**Respuesta 10:** Creé `backend/rgenerator/_version.py` con `__version__`, actualicé `backend/rgenerator/__init__.py` para exportarlo y ajusté `setup.py` para leer ese valor, de modo que la versión viva en un único lugar.

**Pregunta 11:** Crea un script `.py` para correr los tests y configura coverage.  
**Respuesta 11:** Añadí `run_tests.py` (ejecuta `pytest` con `--cov=backend/rgenerator --cov-report=term-missing`) y `.coveragerc` para centralizar la configuración de cobertura (source `backend/rgenerator`, omite scripts/tests, muestra líneas faltantes).
