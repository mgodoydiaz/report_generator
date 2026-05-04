# Catálogo de Tablas (B7)

Editor visual para crear tablas configurables sin tocar JSON. Cada tabla
vive como un Spec con `type='Tablas'` y se puede insertar después en el
dashboard de cualquier indicador.

---

## Acceder

Ruta: `http://localhost:5173/tables`. Atajo en el sidebar
("Tablas", icono Table).

---

## Layout 3 paneles

```
┌──────────────┬────────────────────────────┬─────────────────┐
│ Mis Tablas   │ Editor (3 tabs)            │ Preview live    │
│ + filtro     │  Origen | Columnas | ...   │ TanStack Table  │
└──────────────┴────────────────────────────┴─────────────────┘
```

- **Sidebar**: lista de tablas existentes (cards con nombre, métrica,
  N° columnas, estado draft/publicada). Botón "+ Nueva tabla". Filtro
  por nombre.
- **Editor (panel central)**: nombre + descripción editables, toggle
  draft/publicada, botones Guardar/Duplicar/Eliminar, tabs de config.
- **Preview live**: renderiza la tabla con `<TableRenderer>` usando
  `POST /api/tables/preview` con la config draft (no requiere guardar).
  Refresca al cambiar cualquier cosa.

---

## Tabs del editor

### Origen
- Selector de Métrica (dropdown). Define la fuente de datos.
- Filtros base (uno por dimensión de la métrica). Aplican siempre.
  Para filtros del consumidor (dashboard/PDF), usar `extra_filters`
  desde el render.

### Columnas
- Botones rápidos para agregar columnas (auto-detectadas de la métrica:
  dimensiones en azul, fields en verde).
- Por columna desplegada:
  - **Header** (texto visible)
  - **Format** (text / int / float / percent / date)
  - **Decimals** (si numérico)
  - **Aggregación** para cuando hay grouping (mean / sum / min / max /
    count / nunique / first)
  - **Width** opcional (px)
  - **Color por celda** (3 modos):
    - **Vinculado a indicador**: usa los `achievement_levels` del
      indicador seleccionado. Bidireccional: si editás los colores del
      indicador, las tablas vinculadas se actualizan al consultarse.
      Necesita un `level_field` (columna del DataFrame con la categoría
      del nivel, ej "Nivel Logro").
    - **Divergente**: rojo→neutro→verde con punto medio configurable.
    - **Secuencial**: color base único.
- Reordenable con flechas ↑↓.
- Botón ojo para ocultar columnas (siguen disponibles para
  sorting/agg/filter).

### Comportamiento
- **Agrupar por** (1 nivel). Hace groupby + aplica los `agg` por columna.
- **Orden inicial** (multi-criterio).
- **Paginación** (toggle + tamaño).
- **Export** CSV / XLSX.
- **Búsqueda global** (toggle).

---

## Insertar una tabla en un dashboard

1. Crear y guardar la tabla en `/tables`.
2. Ir a `/indicators` → seleccionar indicador → "Editar Layout".
3. En cualquier fila, botón "**+ Tabla**" (verde, al lado de "+ Agregar").
4. Seleccionar la tabla desde el modal. Se inserta como item con shape
   `{type: 'configured_table', spec_id: X, title}`.
5. Guardar el layout. La tabla aparecerá en el dashboard con los
   filtros activos del dashboard (curso, hito) inyectados como
   `extra_filters`.

---

## API

| Verbo | Path | Propósito |
|---|---|---|
| GET | `/api/tables/` | Lista resumen (sidebar) |
| POST | `/api/tables/` | Crear |
| GET | `/api/tables/{id}` | Detalle (config completa) |
| PUT | `/api/tables/{id}` | Actualizar |
| DELETE | `/api/tables/{id}` | Borrar |
| POST | `/api/tables/{id}/duplicate` | Clonar |
| GET | `/api/tables/{id}/data` | Datos formateados (paginados, con colores) |
| POST | `/api/tables/preview` | Preview con config en body (sin persistir) |

---

## Schema de TableConfig

```json
{
  "version": 1,
  "data_source": {
    "metric_id": 6,
    "filters": {"Asignatura": "Lenguaje"},
    "derived_fields_override": []
  },
  "columns": [
    {
      "key": "Logro",
      "header": "Logro",
      "format": "percent",
      "decimals": 1,
      "agg": "mean",
      "color_scale": {
        "kind": "linked_indicator",
        "indicator_id": 5,
        "level_field": "Nivel Logro"
      }
    }
  ],
  "behavior": {
    "grouping": {"by": "Curso"},
    "sorting": [{"column": "Logro", "dir": "desc"}],
    "pagination": {"enabled": true, "page_size": 50},
    "export": {"csv": true, "xlsx": true},
    "search": true
  }
}
```

Validación con Pydantic en `backend/schemas_table.py`.

---

## Decisiones de diseño (B7)

- **PDF y Dashboard separados**: cuando una tabla pivot tiene sentido
  en dashboard pero no en PDF (porque el dashboard interactúa con
  filtros), se mantienen como flujos paralelos. Las tablas configuradas
  con este editor son para Dashboard. Para PDF siguen valiendo las 5
  funciones registradas en `motor v2/tables.py` declaradas en
  `dia/esquema.json` y `simce/esquema.json`.
- **1 Spec = 1 Tabla** (`tables_list[0]`).
- **TanStack Table v8**: estándar React, headless (estilado con Tailwind),
  sorting / paginación / export CSV nativos.
- **Color scales bidireccionales**: el modo `linked_indicator` lee
  `achievement_levels` del indicador EN TIEMPO DE CONSULTA, no copia.
  Si el indicador edita sus colores, las tablas vinculadas se
  actualizan automáticamente.

---

## TODO post-v1

- Migrar las 5 tablas hardcoded de `dia/esquema.json` y
  `simce/esquema.json` a este sistema (gradual, no urgente — siguen
  funcionando).
- `derived_fields_override` por tabla (placeholder reservado en el
  schema, pendiente implementar en el endpoint /data).
- Drag-drop reorder de columnas (hoy con flechas ↑↓).
- Pivot tables dinámicos.
- Snapshots / versionado.
