# Informes Word por indicador (docxtpl)

Sistema de generación de informes `.docx` a partir de plantillas Word con
códigos `{{valor}}`, con **un archivo Python por informe** y **registro por
nombre**: el nombre del archivo es el identificador que usa el frontend.

## Arquitectura

```
backend/rgenerator/reports/word/
├── __init__.py        registry auto-descubierto (nombre → módulo)
├── engine.py          render docxtpl + tipos Grafico/Imagen + tabla_desde_df
├── informes/
│   └── <nombre>.py    UN archivo por informe/indicador
└── templates/
    └── <nombre>.docx  UNA plantilla Word por informe
```

- `POST /api/reports/word/{nombre}` — genera el .docx (body: `{indicator_id, filtros?, params?}`)
- `GET  /api/reports/word/informes` — lista informes registrados (para el selector del frontend)
- `GET  /api/reports/word/informes/{nombre}/placeholders` — códigos `{{valor}}` que espera la plantilla

Frontend: botón **Word** en `/results` → `GenerateWordReportModal.jsx`.

## Crear un informe nuevo

```bash
python scripts/nuevo_informe_word.py mi_informe --label "Mi Informe"
```

Esto crea:
1. `informes/mi_informe.py` — stub con `construir_contexto(dataframes, params) -> dict`
2. `templates/mi_informe.docx` — Word base editable que ya trae códigos de ejemplo

Flujo de trabajo:
1. Abrir la plantilla en Word y darle el diseño final, **manteniendo los códigos** `{{valor}}`.
2. En el módulo Python, devolver en `construir_contexto` un dict con una clave por código.
3. El frontend lo ve automáticamente en el selector (registry auto-descubierto).

## Contrato del módulo

```python
LABEL = "Mi Informe"                  # nombre legible (frontend)
DESCRIPCION = "..."                   # ayuda en el modal
PARAMS_ESPERADOS = ["titulo"]         # documentación de params
PLANTILLA = "mi_informe.docx"         # opcional; default <nombre>.docx

def construir_contexto(dataframes, params) -> dict:
    ...
```

`dataframes` es el dict `{rol: DataFrame}` de `cargar_dataframes_indicator`
(mismo loader que el motor PDF v2): `estudiantes`, `preguntas`, `metric_<id>`.

## Tipos especiales en el contexto

| Valor | Efecto en el Word |
|---|---|
| `str`, número, lista, dict | reemplazo Jinja normal |
| `tabla_desde_df(df, formatos={"Promedio": ".1%"})` | filas para loops `{%tr for fila in ... %}` |
| `Grafico(fn="grafico_barras_promedio_por", df=df, params={...})` | ejecuta la función del `CHART_REGISTRY` (motor v2) y la inserta como imagen |
| `Imagen(path="...")` | inserta un PNG/JPG existente |

## Reglas de plantilla (docxtpl)

- Valores simples: `{{ titulo }}` en cualquier texto.
- Filas dinámicas de tabla: fila propia con `{%tr for fila in resumen %}`,
  fila con `{{ fila.campo }}`, fila con `{%tr endfor %}`.
- Las claves de `tabla_desde_df` se normalizan: `"Categoría"` → `fila.categoria`.
- **No escribir sintaxis de etiquetas `{% %}` en texto normal** del documento
  (Jinja la interpretaría). Los códigos `{{ }}` sin clave en el contexto
  fallan el render — usar el endpoint de placeholders para verificar.

## Por qué .docx y no PDF

`docx2pdf` (el conversor del viejo `GenerateDocxReport`, eliminado en B6b)
requiere Word instalado y es frágil en Linux/Docker. Este sistema entrega el
`.docx` editable — la fundación puede retocarlo antes de imprimir/exportar.
Si más adelante se quiere PDF server-side, la vía es LibreOffice headless
(`soffice --convert-to pdf`) en el contenedor.
