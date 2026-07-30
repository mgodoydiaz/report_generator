# Informes custom (hardcodeados en Python)

Un **informe custom** es un informe cuyo diseño NO se configura desde la UI
(Editor de Layout) sino que está escrito a mano en Python: SIMCE oficial, DIA,
PDL IDEL-Woodcock, etc.

Cada informe es **un archivo** en esta carpeta. El nombre del archivo ES el
identificador público del informe.

```
backend/rgenerator/reports/custom/
├── __init__.py              registro auto-descubierto
├── _ejemplo.py              plantilla (empieza con "_" → no se registra)
├── dia.py
├── pdl_idel.py
├── simce.py
└── simce_panguipulli.py
```

---

## Crear un informe nuevo

```bash
cp backend/rgenerator/reports/custom/_ejemplo.py \
   backend/rgenerator/reports/custom/mi_informe.py
```

Editar la metadata y la función `generar`. No hay nada más que registrar: el
`__init__.py` descubre los módulos con `pkgutil.iter_modules` cada vez que
arranca el proceso.

### Contrato del módulo

```python
LABEL = "Informe PDL IDEL-Woodcock"      # obligatorio — texto de la card en la UI
DESCRIPCION = "..."                       # obligatorio — subtítulo de la card
FORMATO = "pdf"                           # "pdf" | "word"
ENGINE_TYPES = ["pdl_idel"]               # None → aplica a TODOS los indicadores
REQUIERE_FILTRO_TEMPORAL = []             # ej ["Mes", "N Prueba"] — la UI lo exige
REQUIERE_ASIGNATURA = False               # True → el informe es de UNA asignatura
FILENAME = "informe_pdl_idel.pdf"         # opcional; default informe_<nombre>.pdf

def generar(db, *, indicator_id: int, org_id: int,
            filtros=None, params=None, overrides=None) -> bytes:
    ...
```

| Campo | Obligatorio | Para qué |
|---|---|---|
| `LABEL` | sí | Título de la card en el selector "Generar informe". |
| `DESCRIPCION` | sí | Texto de ayuda debajo del título. |
| `FORMATO` | no (`"pdf"`) | Define el `Content-Type` y la extensión por defecto. |
| `ENGINE_TYPES` | no (`None`) | Lista de `Indicator.report_engine_type` a los que aplica. `None` = todos. |
| `REQUIERE_FILTRO_TEMPORAL` | no (`[]`) | Dimensiones temporales que el informe necesita; el frontend obliga a elegir una antes de habilitar la descarga. |
| `REQUIERE_ASIGNATURA` | no (`False`) | `True` si el informe cubre UNA sola asignatura. Ver más abajo. |
| `FILENAME` | no | Nombre del archivo descargado. |
| `generar` | sí | Devuelve los bytes. Sin esta función el módulo se ignora con warning. |

### `REQUIERE_ASIGNATURA`

Los datos de un indicador pueden traer **varias asignaturas** (el DIA de la
fundación carga LECTURA y MATEMATICA del mismo alumno en las mismas metrics). Un
informe que las mezcla cuenta cada alumno una vez por prueba rendida: los "42
alumnos" del encabezado son en realidad 21 alumnos × 2 asignaturas.

El flag funciona igual que `REQUIERE_FILTRO_TEMPORAL` — **declarativo en el
módulo, obligatorio en el motor**:

| Capa | Qué hace |
|---|---|
| El módulo | Declara `REQUIERE_ASIGNATURA = True`. |
| `GET /api/indicators/{id}/report-options` | Publica el campo `asignatura` en la card **solo si** el módulo lo declara **y** los datos del indicador traen ≥2 asignaturas distintas. |
| `reports/asignatura.py` | Detecta la dimensión (nombre normalizado que contenga "asignatura") y sus valores reales. |
| `dispatch_v2.generar_pdf_v2` | Exige que los filtros la fijen a **exactamente un** valor; 0 ó >1 → `AsignaturaRequerida` → HTTP 400. |

Con 0 ó 1 asignatura en los datos no hay nada que preguntar: el campo se omite,
no hay 400 y el motor usa la única asignatura presente (nunca un literal por
defecto). Los informes de IDEL, Fluidez Lectora y Cálculo Veloz no se ven
afectados.

Un informe custom que **no** pase por `dispatch_v2` y sea por asignatura debe
llamar a `asignatura.resolver_seleccion` en su propio `generar`.

**Reglas duras**

- Toda query debe filtrar por `org_id` (multi-tenancy).
- `raise ValueError("mensaje para el usuario")` cuando falten datos o filtros:
  el endpoint responde `400` con ese texto tal cual.
- El pie izquierdo del PDF debe ser el nombre de la organización. Si usás el
  motor v2, llamá a `dispatch_v2.aplicar_pie_organizacion(db, org_id, overrides)`
  y pasá el resultado como `overrides` (los wrappers `simce`/`dia` ya lo hacen
  vía `generar_pdf_v2`).
- Un módulo que no importa (ImportError, dependencia faltante) se saltea con un
  warning en consola y **no** tumba el resto del registro.
- Los módulos que empiezan con `_` no se registran — usalos para helpers
  compartidos.

---

## Dónde aparece en la UI

`GET /api/indicators/{id}/report-options` devuelve el informe dentro de
`grupos.especializados` (y también en `opciones`, la lista plana de compat),
siempre que `ENGINE_TYPES` incluya el `engine_type` del indicador:

```json
{
  "id": "custom_pdl_idel",
  "label": "Informe PDL IDEL-Woodcock",
  "descripcion": "Informe especializado multi-curso ...",
  "formato": "pdf",
  "motor": "custom",
  "nombre": "pdl_idel",
  "requiere_filtro_temporal": [],
  "disponible": true,
  // Solo presente si REQUIERE_ASIGNATURA y los datos traen ≥2 asignaturas:
  // "asignatura": {"requerida": true, "dimension": "Asignatura",
  //                "valores": ["LECTURA", "MATEMATICA"]},
  "motivo_no_disponible": null,
  "invocacion": {
    "endpoint": "/api/reports/custom/pdl_idel",
    "params": {"indicator_id": 5}
  }
}
```

El `engine_type` sale de `Indicator.report_engine_type`; si está vacío se
infiere del nombre del indicador (heurística de retrocompatibilidad).

---

## Invocación

```
POST /api/reports/custom/{nombre}
{
  "indicator_id": 5,
  "filtros":   {"Mes": "NOVIEMBRE"},   // opcional
  "params":    {},                      // opcional, libre por informe
  "overrides": {"branding": {...}}      // opcional
}
```

| Código | Cuándo |
|---|---|
| `200` | Binario del informe con `Content-Disposition: attachment`. |
| `404` | `nombre` no está en el registro. |
| `400` | El informe no aplica al `engine_type` del indicador, `generar` levantó `ValueError`, o falta fijar la asignatura (`REQUIERE_ASIGNATURA`). |
| `500` | Cualquier otro error (se loguea con stacktrace, no se filtra al cliente). |

---

## Probarlo

```bash
# 1) El registro lo ve
python -c "from backend.rgenerator.reports import custom; print(custom.listar_informes())"

# 2) Tests del registro y del endpoint
pytest tests/reports/test_custom_registry.py -v

# 3) End-to-end contra el backend local (requiere weasyprint/matplotlib)
curl -X POST http://localhost:8000/api/reports/custom/pdl_idel \
     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"indicator_id": 5}' --output informe.pdf
```

Para un smoke de TODOS los informes de TODOS los indicadores:
`python scripts/generar_ejemplos_informes.py`.
