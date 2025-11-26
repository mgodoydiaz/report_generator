# Codex Review

## Critical Issues
- `backend/rgenerator/etl/__init__.py:9-25` re-exporta funciones (`reconocer_cursos`, `region_darkness`, `extract_bold_alternatives`, etc.) que no existen en ninguna parte del repositorio. Cualquier `import rgenerator.etl` levanta `ImportError`, impidiendo usar la librería ETL que se supone es el núcleo del backend.
- `backend/rgenerator/scripts/run_etl.py` y `backend/rgenerator/scripts/generate_report.py` están vacíos (0 bytes). El README documenta comandos para correr estos scripts, pero hoy no contienen lógica, flags ni invocaciones a la librería, por lo que la experiencia de consola prometida en la raíz es inexistente.
- `backend/rgenerator/reports/__init__.py` está vacío y no hay módulos dentro del paquete `reports`. El objetivo declarado es generar reportes académicos, pero no existe ningún API de generación de LaTeX/PDF en el paquete actual (solo queda código legacy bajo `legacy/`), por lo que no se puede producir ningún informe desde el backend activo.
- `backend/rgenerator/etl/consolidar_dia.py:101-103` usa `df_intermedio.at[:, 8] = establecimiento` y `df_intermedio.at[:, 9] = curso`. `.at` solo acepta índices escalares; pasar un slice levanta `InvalidIndexError` antes de consolidar los datos. Se debe usar `.loc[:, 8]` (o renombrar columnas) para escribir los valores.

## High Priority Improvements
- `backend/rgenerator/etl/consolidar_dia.py:69-84` obtiene `pages = dic_pages_por_curso.get(curso)` pero el argumento tiene `None` como valor por defecto. Si no se entrega un diccionario completo, `camelot.read_pdf(..., pages=None)` y `pages.split('-')` fallan con `TypeError`. Valida la entrada y entrega errores claros (o deriva las páginas desde el PDF).
- `backend/rgenerator/tooling/plot_tools.py:131` y `backend/rgenerator/tooling/plot_tools.py:480` definen dos veces la misma función `valor_promedio_agrupado_por`. La segunda definición pisa silenciosamente a la primera, haciendo difícil mantener y documentar la API; conviene unificar en una sola implementación parametrizable.
- `backend/rgenerator/etl/` en general sigue dependiendo de funciones que solo existen en `legacy/backend/simce_things`. Mientras no se porten (p. ej. reconocimiento de curso, cálculo de nivel de logro, extracción de respuestas desde PDFs), la nueva librería no puede completar ningún flujo DIA/SIMCE.

## Security & Operational Risks
- `aux_files/credentials.json` contiene credenciales reales (`rut_usuario` y contraseña) versionadas en texto plano. Este archivo debe moverse a variables de entorno o a un gestor de secretos y agregarse a `.gitignore` para evitar filtraciones.
- `aux_files/script_response.py` escribe respuestas completas de login/consulta (`login_response.html`, `list_response.html`) en disco sin sanitizar datos personales. Si se ejecuta contra sitios con información sensible queda registro local con RUTs, alumnos y cookies de sesión.

## Observaciones Adicionales
- A pesar de la carpeta `legacy/`, no existe una guía ni pruebas automatizadas que indiquen qué partes ya fueron migradas a `backend/rgenerator`. La ausencia de tests hace difícil validar futuras contribuciones.
- No hay definición de paquetes (`pyproject.toml` o `setup.cfg`) ni instrucciones para instalar la librería `rgenerator` como módulo reutilizable; hoy solo es código suelto dentro del repo.

## Suggested Next Steps
1. Portar (o reescribir) las funciones faltantes del ETL y exponer una API estable detrás de `rgenerator.etl`, agregando pruebas unitarias mínimas para XLS/PDF.
2. Implementar los scripts CLI (`run_etl.py`, `generate_report.py`) con `argparse` y llamadas reales al paquete, incluyendo manejo de errores y documentación de parámetros en el README.
3. Recrear el subpaquete `reports` con herramientas de render (tablas, gráficos, plantillas LaTeX) y tests que verifiquen la generación de un informe de ejemplo.
4. Eliminar credenciales en texto plano y documentar la configuración necesaria mediante variables de entorno o archivos `.env` ignorados por Git.
