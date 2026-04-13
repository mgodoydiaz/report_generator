# Documentación — Report Generator

Índice de toda la documentación del proyecto.

## Estructura

```
docs/
├── usuario/         Guías de uso de la aplicación
├── desarrollo/      Referencia técnica para desarrolladores
└── skills/          Skills de Claude para tareas recurrentes
```

---

## Usuario

| Documento | Descripción |
|---|---|
| [Correr la aplicación](./usuario/correr-aplicacion.md) | Cómo instalar y ejecutar el sistema |
| [Base de datos — backup y restauración](./usuario/backup-base-datos.md) | Crear y restaurar backups de PostgreSQL |

---

## Desarrollo

| Documento | Descripción |
|---|---|
| [Arquitectura general](./desarrollo/arquitectura.md) | Stack, estructura de carpetas y modelo de ejecución |
| [Pipeline steps](./desarrollo/pipeline-steps.md) | Referencia de todos los pasos ETL disponibles |
| [Gráficos y tablas](./desarrollo/graficos-tablas.md) | Charts schema, plot_tools y sistema de dashboards |
| [Work log](./desarrollo/work-log.md) | Historial de cambios y decisiones técnicas |

---

## Skills de Claude

| Skill | Descripción |
|---|---|
| [`/add-step`](./skills/add-step.md) | Crear o modificar un paso de pipeline |
| [`/add-metric`](./skills/add-metric.md) | Crear una nueva métrica |
| [`/add-chart`](./skills/add-chart.md) | Agregar un gráfico o tabla al sistema |
| [`/new-pipeline`](./skills/new-pipeline.md) | Construir un pipeline JSON desde cero |
