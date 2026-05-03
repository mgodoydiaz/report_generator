# Script artesanal DIA — referencia para portar a pipelines

**Origen**: `C:\Users\magod\Documents\Proyectos\Informes PHP\Evaluaciones 2026\DIA\Automatización final\script_consolidar_DIA.py`

Es el script que el cliente usa hoy para procesar DIA antes de cargar a
metric_data. Vamos a portarlo a steps configurables del runner. Acá
queda capturada la lógica para que un agente sin contexto pueda hacer la
migración.

---

## Inputs esperados (en una carpeta)

- N archivos `.xls` (uno por curso) con resultados de estudiantes DIA.
- N archivos `RBD*_diagnostico_2026.pdf` (uno por curso) con la sección
  "Resultados por pregunta".

## Outputs

- `resultados_estudiantes_consolidado.xlsx` — 1 fila por (estudiante ×
  ítem evaluado dentro del curso).
- `resultados_preguntas_consolidado.xlsx` — 1 fila por pregunta del PDF.

En el pipeline migrado, ambos van directo a `SaveToMetric` (sin pasar por
xlsx intermedio).

---

## Pasos del script (con líneas referencia del original)

### 1. Carga XLS de estudiantes (ETL)

```python
# script_consolidar_DIA.py:280-301
for xls_file in archivos_xls:
    workbook = xlrd.open_workbook(xls_file)
    sheet = workbook.sheet_by_index(0)
    establecimiento = sheet.cell_value(4, 1)  # celda B5
    curso = sheet.cell_value(5, 1)            # celda B6
    df = pd.read_excel(xls_file, header=12)   # datos desde fila 13
    df['Establecimiento'] = establecimiento
    df['Curso'] = curso
    resultados_estudiantes = pd.concat([resultados_estudiantes, df], ignore_index=True)
```

**A portar**: `RunExcelETL` no soporta hoy lectura de metadata previa al
header. Crear `RunExcelETL_DIA` o parametrizar con `metadata_cells`:
```json
{
    "step": "RunExcelETL",
    "params": {
        "input_key": "estudiantes",
        "output_key": "estudiantes",
        "header_row": 12,
        "metadata_cells": [
            {"column_name": "Establecimiento", "cell": "B5"},
            {"column_name": "Curso", "cell": "B6"}
        ]
    }
}
```

### 2. Cálculo de `Logro` (mean dynamic columns)

```python
# script_consolidar_DIA.py:307-315
metadata_cols = {"Número de Lista", "Nombre del Estudiante", "Establecimiento", "Curso"}
score_cols = [c for c in df.columns if c not in metadata_cols]
df[score_cols] = df[score_cols].replace(',', '.', regex=True).astype(float)
df['Logro'] = df[score_cols].mean(axis=1) / 100
```

**A portar**: nuevo kind para el engine `derived_fields` o un step nuevo:
```json
{
    "step": "ApplyDerivedFields",
    "params": {
        "derived_fields": [
            {
                "kind": "row_mean_dynamic",
                "name": "Logro",
                "exclude_columns": ["Número de Lista", "Nombre del Estudiante", "Establecimiento", "Curso"],
                "scale": 0.01,
                "preprocess": {"replace": {",": "."}, "cast": "float"}
            }
        ]
    }
}
```

Alternativa: usar `ModifyColumnValues` con regex para replace + crear
columna nueva con mean. Pero ensucia la config.

### 3. `Nivel de Logro` por umbral

```python
# script_consolidar_DIA.py:142-149
def calcular_nivel_logro(logro):
    if logro <= 0.4:   return "Inicial"
    elif logro <= 0.6: return "Intermedio"
    else:              return "Avanzado"

df['Nivel de Logro'] = df['Logro'].apply(calcular_nivel_logro)
```

**A portar**: nuevo kind `row_threshold` o usar `EnrichWithLookup` con
tabla de umbrales:
```json
{
    "step": "ApplyDerivedFields",
    "params": {
        "derived_fields": [{
            "kind": "row_threshold",
            "name": "Nivel de Logro",
            "value_field": "Logro",
            "thresholds": [
                {"max": 0.4,  "label": "Inicial"},
                {"max": 0.6,  "label": "Intermedio"},
                {"max": null, "label": "Avanzado"}
            ]
        }]
    }
}
```

### 4. `Nivel` por lookup curso → categoría

```python
# script_consolidar_DIA.py:151-181
dic_nivel = {
    "1": "Primeros", "2": "Segundos", "3": "Terceros",
    "4": "Cuartos", "5": "Quintos", "6": "Sextos",
    "7": "Septimos", "8": "Octavos",
    "I": "Primeros Medios", "II": "Segundos Medios",
    "III": "Terceros Medios", "IV": "Cuartos Medios",
}
def obtener_nivel(curso):
    valor = curso.split(" ")[0]
    return dic_nivel[valor]

df['Nivel'] = df['Curso'].apply(obtener_nivel)
```

**A portar**: usar `EnrichWithLookup` (ya existe) con la tabla cargada
como spec, o un kind `row_lookup` con `extract_pattern` previo (split por
espacio para obtener "1" o "I" del curso).

### 5. ETL PDFs de preguntas (camelot + fitz)

```python
# script_consolidar_DIA.py:340-405
for archivo_pdf in archivos_pdf:
    # 5.1 Detectar páginas "N. Resultados por pregunta" automáticamente
    pages = detectar_paginas_tabla_preguntas(archivo_pdf)

    # 5.2 Extraer tablas con camelot lattice
    tablas = camelot.read_pdf(archivo_pdf, pages=pages, flavor="lattice")
    tablas_impares = [t for i, t in enumerate(tablas) if i % 2 == 1]

    # 5.3 Extraer establecimiento/curso de la página 1 con fitz
    establecimiento, curso, _ = extraer_establecimiento_y_curso(archivo_pdf)

    # 5.4 Identificar respuesta correcta marcada en negrita.
    # Usa análisis de píxeles: para cada token A:/B:/C:/D:/E: en negrita,
    # calcula la oscuridad media de su bbox y elige la más oscura.
    respuestas_correctas = extract_bold_alternatives(...)

    # 5.5 Para cada fila, calcular Logro = % de la alternativa correcta
    for row in df_intermedio.itertuples():
        cell_pct = row[4]  # texto tipo "A: 34.62%\nB: 7.69%\n..."
        if "RC" in cell_pct:
            rc = float(cell_pct.split('RC:')[1].split('\n')[0].replace('%', '')) / 100
        else:
            r_correcta = respuestas_correctas[i]['winner']
            porcentaje = get_correct_percent(cell_pct, r_correcta) / 100

    # 5.6 Normalizar columnas, limpieza de saltos de línea
    # 5.7 Agregar Nivel de Logro y Nivel (idem estudiantes)
```

**A portar**: step nuevo `RunDIAPDFExtraction`. Es la parte más compleja
porque mezcla camelot (tablas) + fitz (texto + análisis de píxeles para
detectar negritas). Mantener las funciones helper como están:
- `detectar_paginas_tabla_preguntas(pdf_path)` → rango "start-end"
- `extraer_establecimiento_y_curso(pdf_path)` → (str, str, dict)
- `extract_bold_alternatives(pdf, df, ...)` → lista de winners
- `region_darkness(page, bbox, zoom)` → float (oscuridad de un region)

Estas son específicas del formato Agencia DIA y el cliente las depuró
durante meses. NO reescribirlas — copiarlas tal cual al step nuevo.

---

## Bug de datos crítico para resolver en el step

Los nombres de estudiantes vienen invertidos entre hitos:
- `DIAGNOSTICO`: "Nombre Apellido" (ej "MARIANO JAZIEL ALARCÓN FLORES")
- `INTERMEDIO`: "Apellido Nombre" (ej "ALARCÓN FLORES MARIANO JAZIEL")

Esto bloquea el cálculo de `Avance` y `Mejora_vs_Inicio` entre hitos.
Soluciones a evaluar al portar:

1. **Step de normalización** que ordena alfabéticamente las palabras del
   nombre. Pierde la info "qué es nombre y qué es apellido", pero da una
   clave estable para matchear.
2. **Usar `Numero Lista` + `Curso`** como clave compuesta si es
   determinístico entre hitos (verificar).
3. **Usar RUT** si el cliente puede agregarlo a sus XLS.

Mientras no se resuelva, las 2 derived_fields temporales en
`backend/rgenerator/reports/dia/esquema.json` quedan comentadas (solo
`Logro_Promedio_Estudiante` activo).

---

## Funciones específicas a copiar literal del script

Copiar al nuevo step sin modificar (líneas referencia):

| Función | Líneas | Qué hace |
|---|---|---|
| `region_darkness` | 27-34 | Renderiza bbox y devuelve oscuridad media |
| `extract_bold_alternatives` | 36-111 | Asigna alternativa correcta a cada pregunta usando análisis de píxeles |
| `get_correct_percent` | 113-118 | Parsea "A: X%\nB: Y%..." y devuelve % de la correcta |
| `detectar_paginas_tabla_preguntas` | 183-212 | Regex de start/end de la sección |
| `extraer_establecimiento_y_curso` | 214-258 | Parsea bloques de la página 1 |
| `reemplazar_nivel_logro` | 131-140 | "nivel III" → "Avanzado" (legacy) |
| `calcular_nivel_logro` | 142-149 | Umbral 0-0.4-0.6-1 |
| `obtener_nivel` | 151-181 | Curso → "Primeros" / "Segundos Medios" |
| `reconocer_cursos` | 14-25 | Extrae cursos de nombres de archivos |
