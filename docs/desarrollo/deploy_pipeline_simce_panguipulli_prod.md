# Pipeline de SIMCE Panguipulli (Aptus) en producción

**Estado: APLICADO el 2026-08-05.** Este documento queda como registro de lo que se hizo y
como referencia si hay que repetirlo en otro entorno.

## Lo que había, y lo que suponíamos

Se creía que producción tenía el pipeline `EMN Aptus (IA)` con 19 pasos y había que
simplificarlo. **Era falso.** Al inspeccionar antes de escribir:

| | dev | producción (antes) |
|---|---|---|
| Métrica Estudiante | 24 | **17** |
| Métrica Habilidad | 26 | **18** |
| Métrica OA | 25 | **no existe** |
| Indicador | 6 | **8** |
| Specs ETL | 49 / 51 | **no existían** |
| Pipeline | 26 | **no existía** |

Los datos sí estaban cargados (1695 filas en la 17, 180 en la 18 — los mismos totales que
dev), o sea que la carga histórica se hizo por otra vía y el pipeline nunca se desplegó.

> **La lección:** `scripts/simplificar_pipeline_simce_panguipulli.py` era la herramienta
> equivocada — habría abortado buscando un `pipeline_id=26` inexistente. Y copiar el
> `config_json` de dev tal cual habría sido **un error silencioso**: los `SaveToMetric`
> habrían apuntado a las métricas 24 y 26, que en producción no son las de Panguipulli.
> **Nunca asumas que los IDs coinciden entre entornos.**

## Lo que se hizo

Con `scripts/desplegar_pipeline_simce_panguipulli.py`, que **crea** en vez de modificar y
resuelve las métricas **por nombre** (lo único estable entre entornos):

1. Se crearon 2 specs ETL: **200** (Estudiantes) y **201** (Habilidad).
2. Se creó el pipeline **22 · `SIMCE Panguipulli (Aptus)`**, de 13 pasos, con los `spec_id` y
   `metric_id` remapeados a los de producción.

Todo en una transacción. **No se tocó ningún dato**: ni se borró, ni se modificaron métricas,
ni se alteraron las 1875 filas ya cargadas.

### Cómo se repite

```bash
# 1) exportar el paquete desde dev
docker exec report_generator-db-1 psql -U mgodoy -d rgenerator_dev -t -A -c "
  SELECT json_build_object(
    'specs', (SELECT json_agg(json_build_object('id_spec',id_spec,'name',name,'type',type,
              'metadata',metadata) ORDER BY id_spec) FROM specs WHERE id_spec IN (49,51)),
    'pipeline', (SELECT json_build_object('pipeline',pipeline,'description',description,
                 'config_json',config_json) FROM pipelines WHERE pipeline_id=26 AND org_id=1)
  )::text;" > paquete_dev.json

# 2) desplegar (el --dry-run revierte la transacción)
python scripts/desplegar_pipeline_simce_panguipulli.py --paquete paquete_dev.json --dry-run
python scripts/desplegar_pipeline_simce_panguipulli.py --paquete paquete_dev.json
```

Es idempotente: si los specs o el pipeline ya existen (por nombre y org), los actualiza en vez
de duplicarlos.

## Verificación posterior (2026-08-05)

| Chequeo | Resultado |
|---|---|
| Filas métrica 17 / 18 | 1695 / 180 — **intactas** |
| Pipeline 22, visible, 13 pasos | OK |
| `spec_id` → 200, 201 | OK |
| `metric_id` → 17, 18 | OK |
| Pausas → `estudiantes`, `habilidad` | OK |
| Dimensiones y fields de prod cubiertos por el pipeline | OK (9+2 y 8+2) |
| Derivaciones `Mes` / `N Prueba` / `Asignatura` / `Curso` / `Nombre` | presentes |
| Referencias al informe OA | ninguna |

## Lo que falta probar

**No se ejecutó una carga real en producción.** La estructura está verificada, pero el
pipeline no ha corrido allá con archivos de verdad. La primera vez conviene hacerlo con un
mes **nuevo** (no cargado aún), porque **la carga suma, no reemplaza**: repetir un mes ya
cargado duplicaría sus filas.

Para comparar contra dev: mayo 2025 inserta 443 filas en Estudiante y 45 en Habilidad.

## Revertir

```sql
DELETE FROM pipelines WHERE pipeline_id = 22 AND org_id = 1;
DELETE FROM specs WHERE id_spec IN (200, 201);
```

No hay datos que restaurar: el despliegue no escribió en `metric_data`.
