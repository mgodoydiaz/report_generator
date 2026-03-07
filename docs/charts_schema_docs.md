# Documentación del Esquema de Gráficos (Charts Schema)

Este documento describe el uso y funcionamiento del esquema de configuración de gráficos (`charts_schema.json`) dentro del sistema de pipelines ETL.

## Funcionamiento

El archivo JSON de configuración de gráficos define una lista de tareas de visualización que serán ejecutadas por el step `GenerateGraphics`. Este step toma DataFrames generados previamente en la pipeline (almacenados en `ctx.artifacts`) y utiliza funciones de la librería `rgenerator.tooling.plot_tools` para crear imágenes (generalmente PNG).

## Step Responsable

El step encargado de procesar esta configuración es:

**Nombre de la Clase:** `GenerateGraphics`
**Ubicación:** `backend/rgenerator/etl/core/pipeline_steps.py`

### ¿Cómo lo llama?

El step `GenerateGraphics` busca la configuración de dos maneras:
1.  **Como argumento directo:** Al instanciar el step en el código Python de la pipeline.
    ```python
    GenerateGraphics(charts_schema=[...])
    ```
2.  **Desde el contexto (Context Params):** Busca la clave `"charts_schema"` dentro de los parámetros de la corrida (`ctx.params`). Esto permite inyectar la configuración desde un archivo JSON externo que define toda la pipeline (ej: `pipelineXYZ.json`).

## Ubicación y Estructura

Idealmente, la definición de los gráficos debe ir incrustada en el archivo JSON de definición de la pipeline que carga el usuario, o en un archivo de configuración separado que se carga con `LoadConfig`.

### Ejemplo Práctico

Si tienes un archivo de definición de pipeline (ej: `pipeline_simce_lenguaje.json`), podrías tener una sección `charts_schema` así:

```json
{
  "pipeline_name": "Simce Lenguaje 2025",
  "steps": [
    ...
  ],
  "params": {
    "charts_schema": [
        {
            "type": "grafico_barras_promedio_por",
            "input_key": "df_estudiantes_consolidado",
            "output_filename": "rendimiento_promedio_por_curso.png",
            "params": {
                "columna_valor": "Rend",
                "agrupar_por": "Curso",
                "titulo": "Rendimiento Promedio por Curso",
                "ylabel": "Rendimiento (%)"
            }
        },
        {
            "type": "boxplot_valor_por_curso",
            "input_key": "df_simce_raw",
            "output_filename": "distribucion_puntaje_simce.png",
            "params": {
                "columna_valor": "SIMCE",
                "titulo_grafico": "Distribución de Puntaje SIMCE",
                "formato": "number"
            }
        }
    ]
  }
}
```

## Salida

Las imágenes generadas se guardarán automáticamente en el directorio definido en `ctx.aux_dir` (por defecto `aux_files/` dentro del directorio de trabajo de la pipeline).
