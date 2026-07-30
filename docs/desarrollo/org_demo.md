# Organización demo (sandbox)

Organización de prueba autocontenida para probar dashboards, gráficos e
informes **sin tocar los datos reales de la fundación**. La crea
`scripts/crear_org_demo.py`.

## Cómo crearla / recrearla

Siempre desde el contenedor de dev, para que apunte a la DB canónica del
compose (`report_generator-db-1`):

```bash
docker compose -f docker-compose.dev.yml exec -T backend \
    python scripts/crear_org_demo.py            # falla si ya existe
docker compose -f docker-compose.dev.yml exec -T backend \
    python scripts/crear_org_demo.py --reset    # borra la demo y la recrea
```

El script imprime un resumen con los ids creados y los conteos por tabla.
**Los ids cambian en cada `--reset`** (autoincrement): tomar los del
resumen o consultar por slug / nombre, nunca hardcodearlos.

## Credenciales

| Campo | Valor |
|---|---|
| Organización | `Colegio Demo` (slug `colegio-demo`) |
| Usuario | `demo@rgenerator.local` |
| Contraseña | `demo1234` |
| Rol | `admin` de la org demo (no superadmin) |

Login normal por la UI o por `POST /api/auth/login`. El JWT que devuelve
trae el `org_id` de la demo, así que todo lo que se vea en la sesión es
exclusivamente contenido demo.

## Qué contiene

* **15 dimensiones** con sus catálogos (Año, Curso, Nivel, Asignatura, Mes,
  N Prueba, Hito, Nivel de Logro, Nombre, Nombre_Norm, RUT, Pregunta,
  N Pregunta, Habilidad, Eje Temático).
* **4 métricas** (~1.850 filas de `metric_data`), con la misma forma que las
  métricas reales de la fundación (`meta_json.fields` + dimensiones):

  | Métrica | Filas | Granularidad |
  |---|---|---|
  | Resultados SIMCE Demo por Estudiante | 150 | estudiante × evaluación |
  | Resultados SIMCE Demo por Pregunta | 1.500 | estudiante × pregunta × evaluación |
  | Resultados DIA Demo por Estudiante | 120 | estudiante × hito |
  | Resultados DIA Demo por Pregunta | 80 | curso × pregunta × hito |

* **2 indicadores** con `pdf_layout`, `pdf_layout_historico`,
  `dashboard_layout`, `column_roles`, `achievement_levels` y
  `derived_columns` completos:
  * `SIMCE Demo Lenguaje` — `report_engine_type='simce'`, 2 cursos de
    1° Medio, evaluaciones ABRIL/JULIO/NOVIEMBRE 2025 y ABRIL/JULIO 2026.
  * `DIA Demo Lectura` — `report_engine_type='dia'`, 2 cursos de 3° Básico,
    hitos DIAGNOSTICO/INTERMEDIO/CIERRE 2025 y DIAGNOSTICO 2026.

* **24 Specs** (18 gráficos + 6 tablas) con `metric_id` / `indicator_id`
  de la org demo. El `dashboard_layout` de cada indicador referencia solo
  esos `spec_id`: no hay ni una referencia cruzada a otra organización.

## Datos sintéticos

Deterministas (`random.seed(42)`): dos corridas producen exactamente los
mismos valores. Los estudiantes se llaman `Estudiante Demo NN` y los RUT
son `DEMO-NNNN` — nada parecido a un dato personal real.

* SIMCE: puntaje estimado en el rango ~250–350, con mejora leve entre
  evaluaciones y un efecto por curso, calibrado para que los **tres**
  niveles de logro (Insuficiente / Elemental / Adecuado) estén presentes
  también en la última evaluación.
* DIA: logro como fracción 0–1 con la misma lógica, niveles
  Inicial / Intermedio / Avanzado.

## Casos borde deliberados

El sandbox reproduce a propósito dos situaciones que aparecen en los datos
reales, para poder probar contra ellas:

* **DIA — `Eje Temático` nulo** en ~8 filas de la métrica de preguntas.
* **DIA — `Nombre` nulo con `Nombre_Norm` poblado** en 2 estudiantes (8
  filas). Por eso las `derived_columns` de DIA usan `Nombre_Norm` como
  `entity_field`: si usaran `Nombre`, esas filas degradarían a NaN.

## Branding

`branding.left_footer = ""` y `center_header = ["Colegio Demo", "Informe de
demostración"]`. El template cae al nombre de la organización cuando
`left_footer` está vacío, así que el pie del PDF dice "Colegio Demo" —
ninguna firma personal.

## Aislamiento

El script solo escribe bajo el `org_id` de la demo, y `--reset` borra
filtrando siempre por ese `org_id`. Verificado: con el token de la demo,
`GET /api/indicators/{id}/report-options` y
`POST /api/indicators/{id}/export-pdf` de indicadores de otra organización
responden **404**.
