# Generar informes PDF con paridad LaTeX (motor WeasyPrint)

A partir del 2026-05-01 el sistema soporta dos motores para generar informes PDF:

| Motor | Step interno | Uso |
|---|---|---|
| **LaTeX** (legacy) | `RenderReport` | Funcional pero requiere `xelatex`/MikTeX instalado en el servidor. Se mantiene como fallback. |
| **HTML + WeasyPrint** (nuevo, recomendado) | `RenderHtmlReport` | Mismo aspecto visual, sin dependencias externas pesadas. **Recomendado para todos los informes nuevos**. |

Ambos motores leen el **mismo esquema JSON** (`backend/schemas/esquema_informe_*.json` con `secciones_fijas` + `secciones_dinamicas`) y reusan los **mismos gráficos PNG y tablas XLSX** generados por `GenerateGraphics` y `GenerateTables`. Solo cambia la composición final del PDF.

---

## Cómo cambiar un pipeline existente para usar el motor HTML

En el JSON del pipeline (tabla `pipelines.config_json` en la BD, editable desde
`/pipelines` en la UI), reemplaza el step de salida:

**Antes (LaTeX)**:
```json
{
  "step": "RenderReport",
  "params": {
    "report_schema_path": "backend/schemas/esquema_informe_lenguaje.json"
  }
}
```

**Después (HTML)**:
```json
{
  "step": "RenderHtmlReport",
  "params": {
    "report_schema_path": "backend/schemas/esquema_informe_lenguaje.json"
  }
}
```

El step `RenderHtmlReport` acepta los mismos parámetros que `RenderReport`:

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `report_schema` | dict | — | Esquema directo (alternativa a `report_schema_path`). |
| `report_schema_path` | str | — | Ruta al JSON del esquema. |
| `output_filename` | str | `"informe.pdf"` | Nombre del archivo PDF generado en `outputs_dir`. |
| `template_name` | str | `"report_latex_paridad.html"` | Template Jinja2 en `backend/rgenerator/templates/`. |

---

## Esquemas disponibles

| Schema | Uso |
|---|---|
| `esquema_informe_lenguaje.json` | SIMCE Lenguaje 2° Medio (Pullinque) |
| `esquema_informe.json` | SIMCE Matemáticas 2° Medio (Pullinque) |
| `esquema_informe_dia_matematicas.json` | DIA Diagnóstico Matemáticas Nivel Medio (Panguipulli) |
| `esquema_informe_dia_lectura.json` | DIA Diagnóstico Lectura Nivel Medio (Panguipulli) |

Para crear un nuevo esquema (ej: para Cálculo Veloz, Fluidez Lectora, IDEL):
copia uno existente, ajusta `variables_documento` (header, título, escuela, logos)
y `secciones_fijas` (qué tablas y gráficos incluir, en qué orden).

---

## Ajustes visuales del template

El template HTML/CSS está en
`backend/rgenerator/templates/report_latex_paridad.html`. Cambios típicos:

- **Tipografía**: por defecto usa Inter (con fallback a DejaVu Sans / Segoe UI).
  Si prefieres otra, cambia `font-family` en el CSS al inicio del template.
- **Tamaño del título h1**: actualmente 18pt para que entre en 1 línea en letter
  paper con márgenes 2cm L/R. Para títulos más cortos puedes subir a 20-22pt.
- **Branding (logos)**: el esquema JSON apunta a paths relativos como
  `img/logo_php.png`. El step los resuelve automáticamente buscando en
  `aux_dir/`, `base_dir/`, y `data/database/reports_templates/img/`.

---

## Smoke test local

Para validar que el motor funciona sin tocar Supabase:

```bash
conda activate rgenerator
python scripts/smoke_test_render_html.py
```

Esto genera `data/output/smoke_test_render_html.pdf` con datos mock para SIMCE
Lenguaje 2° Medio. Compara visualmente contra `docs/pdf_examples/Informe SIMCE 5
Lenguaje.pdf` (PDF de referencia LaTeX).

---

## Limitaciones conocidas

1. **`docs/pdf_examples/`** está en `.gitignore` (contiene PII de estudiantes en
   las secciones dinámicas). Es referencia visual local, no se versiona.
2. **WeasyPrint en Windows** requiere GTK3 runtime instalado aparte. En **Linux
   (WSL Ubuntu o Docker)** funciona out-of-the-box con `apt install libpango-1.0-0
   libpangoft2-1.0-0`. Recomendado correr siempre en Linux.
3. **Secciones dinámicas** (logro por alumno, logro por pregunta por curso) se
   generan en el pipeline real (no en el smoke test) cuando se itera por curso.
   Cada una usa `page-break-before: always` igual que el `\newpage` del LaTeX.

---

## Migración progresiva

No es necesario migrar todos los pipelines de un día para otro. Recomendación:

1. **Pipelines nuevos** → usar `RenderHtmlReport` desde el día 1.
2. **Pipelines existentes** → mantener `RenderReport` LaTeX hasta que se necesite
   modificar el esquema. En ese momento, cambiar al motor HTML.
3. **Pipelines críticos en producción** → migrar después de validación visual con
   un sample real (no con datos mock).
