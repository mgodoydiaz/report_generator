# G2 — Pipeline de punta a punta

**Precondiciones**: pipeline SIMCE Lenguaje (id 14) o DIA configurado; archivo Excel de prueba válido y uno inválido (sin columna clave).

| # | Acción | Esperado |
|---|---|---|
| 1 | /pipelines → ejecutar pipeline con archivo válido | Modal muestra progreso paso a paso con nombres traducidos |
| 2 | Si el pipeline pide archivos/datos (pausa interactiva) | El formulario es comprensible; al enviar, se reanuda |
| 3 | Al completar, botón "Descargar" del artifact | **Descarga real del archivo** (regresión P0-3: antes 401 silencioso) |
| 4 | Botón "Copiar" del artifact | Copia al portapapeles con toast de éxito |
| 5 | Re-ejecutar el mismo pipeline con el archivo INVÁLIDO | Error visible con el mensaje del step (ej. "Columna llave 'RUT' no existe...") — NO "Error interno del servidor" (regresión P0-4) |
| 6 | Cerrar el modal tras el error y volver a ejecutar con archivo válido | Corre limpio (el runner se resetea, sin estado zombie) |
| 7 | Verificar en /metrics que los datos cargados aparecen | La métrica destino tiene los registros nuevos |
