---
description: Configurar el layout PDF de un indicador (secciones + branding)
---
# `/configure-pdf` — Configurar el informe PDF de un indicador

Skill ejecutable autónomamente: Claude configura el `pdf_layout` de un indicador via API REST sin tocar código ni la UI.

---

## Estructura de `pdf_layout`

```json
{
  "branding": {
    "left_image_id": 3,
    "right_image_id": 5,
    "center_header": [
      "Informe IDEL-Woodcock 2025",
      "Evaluación Diagnóstica de Lectura",
      "Pullinque — Versión 3 (Noviembre)"
    ],
    "left_footer": "Miguel Godoy Díaz",
    "show_page_number": true
  },
  "sections": [
    { "type": "cover",      "title": "Informe IDEL-Woodcock", "subtitle": "Resultados 2025" },
    { "type": "text",       "heading": "Introducción", "body": "El presente informe..." },
    { "type": "chart",      "heading": "Distribución por Nivel de Riesgo", "item": { "component": "StackedCountByGroup" }, "caption": "Fuente: evaluación Woodcock 2025" },
    { "type": "table",      "heading": "Resumen por Curso",                "item": { "component": "SummaryTable" } },
    { "type": "page_break" }
  ]
}
```

### Tipos de sección

| `type`       | Campos obligatorios                        | Campos opcionales        |
|:-------------|:-------------------------------------------|:-------------------------|
| `cover`      | `title`                                    | `subtitle`               |
| `text`       | `body`                                     | `heading`                |
| `chart`      | `item.component` (nombre del componente)   | `heading`, `caption`     |
| `table`      | `item.component` (nombre del componente)   | `heading`                |
| `page_break` | *(ninguno)*                                | —                        |

**Componentes de gráfico disponibles para PDF** (ver `/add-chart` para descripción completa):
`BarByGroup`, `HorizontalBarByDimension`, `GroupedBarByPeriod`, `BoxPlotByGroup`, `PieComposition`, `StackedCountByGroup`, `StackedCountByGroupAndPeriod`, `TrendLine`, `RadarProfile`

**Componentes de tabla disponibles para PDF:**
`SummaryTable`, `DetailListTable`, `DetailListWithProgress`

### Branding

| Campo            | Tipo          | Descripción                                          |
|:-----------------|:--------------|:-----------------------------------------------------|
| `left_image_id`  | `int \| null` | ID del asset (logo izquierdo). Ver `/upload-branding` |
| `right_image_id` | `int \| null` | ID del asset (logo derecho)                          |
| `center_header`  | `string[3]`   | Hasta 3 líneas de texto en el encabezado central     |
| `left_footer`    | `string`      | Texto pie de página izquierdo (autor)                |
| `show_page_number`| `bool`       | `true` = mostrar "Página N" en el pie derecho        |

Si `branding` es `null` o no está, el PDF se genera sin encabezado de logos (modo degradado).

---

## Flujo autónomo (Python httpx)

```python
import httpx

BASE = "http://localhost:8000/api"
TOKEN = httpx.post(f"{BASE}/auth/login",
    json={"email": "admin@org.cl", "password": "secreto"}).json()["access_token"]
H = {"Authorization": f"Bearer {TOKEN}"}

INDICATOR_ID = 4   # cambiar por el ID real

# 1. Listar assets de logos disponibles (ver /upload-branding para subir)
assets = httpx.get(f"{BASE}/organizations/<ORG_ID>/assets?kind=logo", headers=H).json()
print(assets)  # [{id, name, url, ...}, ...]

# 2. Configurar el pdf_layout con branding + secciones
pdf_layout = {
    "branding": {
        "left_image_id": 3,
        "right_image_id": 5,
        "center_header": [
            "Informe IDEL-Woodcock 2025",
            "Fundación PHP — Pullinque",
            "Noviembre 2025"
        ],
        "left_footer": "Miguel Godoy Díaz",
        "show_page_number": True,
    },
    "sections": [
        {"type": "cover", "title": "Resultados IDEL-Woodcock 2025", "subtitle": "Pullinque"},
        {"type": "chart", "heading": "Distribución de Niveles de Riesgo",
         "item": {"component": "StackedCountByGroup"}, "caption": "por subprueba y curso"},
        {"type": "table", "heading": "Resumen por Curso", "item": {"component": "SummaryTable"}},
        {"type": "page_break"},
        {"type": "text", "heading": "Notas metodológicas", "body": "Evaluación Woodcock IDEL..."},
    ]
}

r = httpx.post(f"{BASE}/indicators/{INDICATOR_ID}/layout", headers=H,
    json={"pdf_layout": pdf_layout})
print(r.json())   # {"status": "success"}

# 3. Descargar el PDF generado
pdf_resp = httpx.post(f"{BASE}/indicators/{INDICATOR_ID}/export-pdf", headers=H)
with open("informe_idel.pdf", "wb") as f:
    f.write(pdf_resp.content)
print("PDF guardado.")
```

---

## Notas

- El endpoint `POST /api/indicators/{id}/layout` solo actualiza los campos que se envían. Si se omite `dashboard_layout`, no se modifica.
- El PDF se genera en el momento de llamar `export-pdf` — no hay cache. Los datos vienen de `metric_data` filtrados por las dimensiones del indicador.
- Si el indicador no tiene secciones configuradas, `export-pdf` devuelve 422 con un mensaje explicativo.
