# Vocabulario visual LaTeX — DIA Matemáticas

Fuente de verdad para la paridad visual del PDF generado por `RenderPDFReport` con los informes LaTeX existentes.

Extraído de:
- [`docs/desarrollo/referencia_informe/DIA/formato_informe.tex`](referencia_informe/DIA/formato_informe.tex)
- [`docs/desarrollo/referencia_informe/DIA/funciones.py`](referencia_informe/DIA/funciones.py)
- [`docs/desarrollo/referencia_informe/DIA/crear_informe.py`](referencia_informe/DIA/crear_informe.py)
- [`docs/pdf_examples/Informe DIA Panguipulli Matemáticas Diagnóstico 2026.pdf`](../pdf_examples/Informe%20DIA%20Panguipulli%20Matem%C3%A1ticas%20Diagn%C3%B3stico%202026.pdf)

---

## 1. Página y márgenes (`\usepackage[...]{geometry}`)

| Parámetro | Valor LaTeX | Equivalente CSS |
|---|---|---|
| Tamaño papel | `letterpaper` | `size: letter` |
| Margen top | `top=3.5cm` | `margin-top: 3.5cm` |
| Margen bottom | `bottom=2cm` | `margin-bottom: 2cm` |
| Margen left | `left=2.5cm` | `margin-left: 2.5cm` |
| Margen right | `right=2.5cm` | `margin-right: 2.5cm` |
| Altura header | `headheight=61pt` | usar `padding-bottom` en `@top-center` para reservar espacio |

CSS final:
```css
@page {
  size: letter;
  margin: 3.5cm 2.5cm 2cm 2.5cm;
}
```

## 2. Tipografía

| Elemento | Valor LaTeX | Equivalente CSS |
|---|---|---|
| Fuente principal | `Segoe UI` (vía `\setmainfont`) | `font-family: "Segoe UI", Inter, "DejaVu Sans", Arial, sans-serif` |
| Tamaño base | `11pt` (`\documentclass[11pt]{article}`) | `font-size: 11pt` |
| Interlineado | `\spacing{1.1}` | `line-height: 1.1` |
| Espacio entre párrafos | `\setlength{\parskip}{5pt}` | `p { margin: 0 0 5pt 0 }` |
| Color base | (negro por defecto LaTeX) | `color: #111` |

## 3. Header

Estructura LaTeX (`\pagestyle{fancy}`):
```latex
\lhead{\pgfimage[height=2.0cm]{\leftimage}}
\rhead{\pgfimage[height=2.0cm]{\rightimage}}
\chead{\centerheaderone\\\centerheadertwo\\\centerheaderthree\\}
\renewcommand{\headrulewidth}{0.4pt}
```

Equivalente CSS (un solo running element con layout interno tipo tabla, copiar de [`report_latex_paridad.html:23-37`](../../backend/rgenerator/templates/report_latex_paridad.html)):

```css
@page {
  @top-center {
    content: element(headerBlock);
    width: 100%;
    vertical-align: bottom;
    padding-bottom: 4pt;
    border-bottom: 0.4pt solid black;
  }
}
#headerBlock { display: table; table-layout: fixed; width: 100%; }
#headerBlock .hb-left   { display: table-cell; width: 25%; text-align: left;   vertical-align: middle; }
#headerBlock .hb-center { display: table-cell; width: 50%; text-align: center; vertical-align: middle; font-size: 9pt; line-height: 1.25; }
#headerBlock .hb-right  { display: table-cell; width: 25%; text-align: right;  vertical-align: middle; }
#headerBlock img { height: 2cm; width: auto; }
```

**Importante**: una sola caja con regla horizontal continua. Las 3 cajas separadas (`@top-left`, `@top-center`, `@top-right`) que tiene hoy `report_base.html` cortan la línea — hay que unificar.

## 4. Footer

Estructura LaTeX:
```latex
\lfoot{\leftfooter}        % Autor (ej: "Miguel Godoy Díaz")
\cfoot{}                   % Vacío
\rfoot{\rightfooter}       % "Página X de Y" o similar
\renewcommand{\footrulewidth}{0.4pt}
```

Equivalente CSS:
```css
@page {
  @bottom-center {
    content: element(footerBlock);
    width: 100%;
    vertical-align: top;
    padding-top: 4pt;
    border-top: 0.4pt solid black;
  }
}
#footerBlock { display: table; table-layout: fixed; width: 100%; font-size: 9pt; }
#footerBlock .fb-left  { display: table-cell; width: 80%; text-align: left;  }
#footerBlock .fb-right { display: table-cell; width: 20%; text-align: right; }
#footerBlock .fb-right::before { content: counter(page); }
```

## 5. Título del documento

LaTeX:
```latex
\begin{center}
    \huge{\documenttitle}\\        % ~24.88pt en 11pt base
    \vspace{0.5cm}
    \Large{\schoolname}\\          % ~17.28pt
    \vspace{0.5cm}
\end{center}
```

Equivalente CSS:
```css
h1.document-title {
  font-size: 18pt;          /* compromiso para que títulos largos quepan en una línea letter */
  text-align: center;
  font-weight: 700;
  margin: 0.6cm 0 0.3cm 0;
  letter-spacing: -0.3pt;   /* compensa el kerning más compacto del LaTeX */
}
h2.school-name {
  font-size: 13pt;
  text-align: center;
  font-weight: 400;
  color: #222;
  margin: 0 0 1cm 0;
}
```

(Estos selectores ya existen en [`report_latex_paridad.html:107-126`](../../backend/rgenerator/templates/report_latex_paridad.html), reutilizables.)

## 6. Títulos de sección (h2 actual del PDF)

LaTeX usa `\section{...}` con `Segoe UI Bold`, **sin línea horizontal debajo**, color negro. El `report_base.html` actual le pone `color: #4f46e5; border-bottom: 2px solid #e0e7ff` — eliminar ambas.

CSS objetivo:
```css
h2 {                /* o h3.section-title — equivalente al \section LaTeX */
  font-size: 13pt;
  font-weight: 700;
  color: #111;
  margin: 0.7cm 0 0.3cm 0;
  border: none;
  padding: 0;
}
```

## 7. Tablas

Estructura LaTeX (`df_a_latex_loop`, [`funciones.py:14-70`](referencia_informe/DIA/funciones.py)):
- `\begin{table}[H] \centering`
- `\begin{tabular}{|l|l|r|r|...}` — `|` columnas con borde, `l` para texto, `r` para números/porcentajes
- `\hline` antes de cada fila (todas las filas tienen borde superior e inferior)
- Header en `\textbf{...}` con `\multicolumn` para alineación per-columna
- Sin background, sin zebra

Equivalente CSS (copiable de [`report_latex_paridad.html:134-176`](../../backend/rgenerator/templates/report_latex_paridad.html)):
```css
table.data-table {                 /* mantener clase actual de report_base.html */
  border-collapse: collapse;
  margin: 0.3cm auto 0.6cm auto;
  font-size: 7.5pt;
  width: auto;                     /* no full-width como hoy; LaTeX centra con ancho propio */
}
table.data-table th,
table.data-table td {
  border: 0.5pt solid #000;
  padding: 2pt 6pt;
  vertical-align: middle;
}
table.data-table th {
  font-weight: 700;
  background: #fff;                /* fondo blanco, no #4f46e5 */
  color: #000;
}
/* Alineación: izquierda para texto, derecha para números */
table.data-table td.al-right,
table.data-table th.al-right { text-align: right; }
table.data-table td.al-left,
table.data-table th.al-left  { text-align: left; }
/* SIN zebra, SIN tr:nth-child(even) */
```

Tablas densas (muchas filas, ej: 40 preguntas): bajar a `font-size: 7pt; padding: 1.5pt 5pt` (clase `.dense`).

## 8. Paletas de gráficos

### 8.1 Categórico general (`Set2`)

Usado en: barras simples, agrupadas, por curso/eje/habilidad.

Definición Python:
```python
import matplotlib.pyplot as plt
PALETTE_CATEGORICAL = list(plt.cm.Set2.colors)
# Equivale a:
# [(0.40, 0.76, 0.65),  # #66c2a5  verde-agua
#  (0.99, 0.55, 0.38),  # #fc8d62  naranja salmón
#  (0.55, 0.63, 0.80),  # #8da0cb  azul-violeta
#  (0.91, 0.54, 0.76),  # #e78ac3  rosa
#  (0.65, 0.85, 0.33),  # #a6d854  verde lima
#  (1.00, 0.85, 0.18),  # #ffd92f  amarillo
#  (0.90, 0.77, 0.58),  # #e5c494  beige
#  (0.70, 0.70, 0.70)]  # #b3b3b3  gris
```

### 8.2 Boxplot (`tab10`)

Usado en: boxplots por curso (color por categoría con alpha=0.6, mediana negra, bordes negros).

```python
PALETTE_BOXPLOT = list(plt.cm.tab10.colors)
# Cicla con i % 10
```

### 8.3 Semáforo niveles de logro (custom)

Usado en: stacked bars de "Cantidad de Alumnos por Nivel de Logro" y todo gráfico que muestre niveles cualitativos.

```python
PALETTE_SEMAFORO = {
    'Avanzado':       '#1f9e89',   # verde-agua
    'Adecuado':       '#1f9e89',
    'Bajo Riesgo':    '#1f9e89',
    'Intermedio':     '#f1a340',   # naranja-amarillo
    'Elemental':      '#f1a340',
    'Cierto Riesgo':  '#f1a340',
    'Inicial':        '#e64b35',   # rojo
    'Insuficiente':   '#e64b35',
    'Crítico':        '#e64b35',
}
```

Cuando un level no matchee (ej: SIMCE usa "Insuficiente/Elemental/Adecuado"), buscar en el dict por nombre exacto. Si no está, fallback a `PALETTE_SEMAFORO` por orden ordinal del level (rojo → naranja → verde).

## 9. Estilos de gráfico por tipo

### 9.1 Barras simples (`logro_promedio_por_curso`, `logro_promedio_por_nivel`)

```python
fig, ax = plt.subplots(figsize=(8, 4))                          # o (5.95, 4) narrow
ax.bar(x, y, color=PALETTE_CATEGORICAL,
       edgecolor='black', linewidth=1.2, zorder=3)
ax.set_ylim(0, 1)                                                # cuando es percent
ax.yaxis.set_major_formatter(PercentFormatter(1.0))
ax.grid(axis='y', linestyle='--', linewidth=0.9, zorder=0)       # grid alpha implícito
ax.spines[['top', 'right']].set_visible(False)
# Etiquetas valor sobre barra
for bar, val in zip(bars, y):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
            f"{val:.0%}", ha='center', va='bottom', fontsize=8)
plt.savefig(..., dpi=300)
```

### 9.2 Barras agrupadas (`logro_promedio_por_eje`, `logro_promedio_por_habilidad`)

```python
fig, ax = plt.subplots(figsize=(12, 6))                          # wide
width = 0.18
for i, grupo in enumerate(grupos):
    bars = ax.bar(x + i*width - (width*len(grupos)/2), valores,
                  width, label=grupo, color=PALETTE_CATEGORICAL[i],
                  zorder=2, edgecolor='gray', linewidth=0.8)
    for bar, val in zip(bars, valores):
        ax.text(..., f"{val:.0%}", ha='center', va='bottom',
                fontsize=8, zorder=3,
                bbox=dict(facecolor='white', edgecolor='none', pad=1, alpha=0.7))
ax.legend(title=...)
plt.grid(axis='y', linestyle='--', linewidth=0.9, zorder=0)
```

Notas:
- `edgecolor='gray'` (no black) en barras agrupadas para no saturar visualmente.
- Etiquetas tienen `bbox` blanco semi-transparente.

### 9.3 Stacked bars semáforo (`alumnos_por_nivel`)

```python
fig, ax = plt.subplots(figsize=(10, 6))
bottom = None
for nivel in ['Inicial', 'Intermedio', 'Avanzado']:           # orden de menor a mayor
    bars = ax.bar(cursos, vals, label=nivel,
                  color=PALETTE_SEMAFORO[nivel],
                  bottom=bottom, zorder=2)
    # Etiqueta: número en blanco, bold, centrado
    for bar, val in zip(bars, vals):
        if val > 0:
            ax.text(..., f"{int(val)}",
                    ha='center', va='center',
                    fontsize=9, color='white', fontweight='bold')
    bottom = vals if bottom is None else bottom + vals
ax.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
ax.legend(title='Nivel de Logro', loc='upper left', bbox_to_anchor=(1, 1))
```

### 9.4 Boxplot (`boxplot_logro_por_curso`)

```python
fig, ax = plt.subplots(figsize=(6, 4))
bp = ax.boxplot(data, positions=np.arange(len(cursos)), widths=0.6,
                patch_artist=True, showfliers=True,
                medianprops=dict(color='black', linewidth=2),
                boxprops=dict(facecolor='none', edgecolor='black', linewidth=1.5),
                whiskerprops=dict(color='black'),
                capprops=dict(color='black'))
for patch, curso in zip(bp['boxes'], cursos):
    patch.set_facecolor(PALETTE_BOXPLOT[i % 10])
    patch.set_alpha(0.6)
plt.grid(axis='y', linestyle='--', alpha=0.6, linewidth=0.7, zorder=0)
```

## 10. Constantes globales sugeridas en `report_steps.py`

Al inicio del módulo o en bloque de constantes:

```python
import matplotlib.pyplot as plt

# Paletas LaTeX-paridad (ver docs/desarrollo/visual_vocabulary_dia.md)
PALETTE_CATEGORICAL = list(plt.cm.Set2.colors)
PALETTE_BOXPLOT     = list(plt.cm.tab10.colors)
PALETTE_SEMAFORO = {
    'Avanzado': '#1f9e89', 'Adecuado': '#1f9e89', 'Bajo Riesgo': '#1f9e89',
    'Intermedio': '#f1a340', 'Elemental': '#f1a340', 'Cierto Riesgo': '#f1a340',
    'Inicial': '#e64b35', 'Insuficiente': '#e64b35', 'Crítico': '#e64b35',
}

# rcParams globales (aplicar dentro de _chart_to_png_b64 antes de cada subplots)
MPL_RCPARAMS_LATEX = {
    'font.family': ['Segoe UI', 'Inter', 'DejaVu Sans'],
    'font.size': 9,
    'axes.titlesize': 10,
    'axes.labelsize': 9,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
}

CHART_FIGSIZE = {
    'narrow': (5.95, 4),     # logro por nivel (4-5 categorías)
    'medium': (8, 4),        # logro por curso (6-10 cursos)
    'wide':   (10, 6),       # stacked alumnos
    'xwide':  (12, 6),       # grouped bars eje/habilidad
}
CHART_DPI = 300              # subir de 120 a 300
```

## 11. Mapeo a `_chart_to_png_b64` ([report_steps.py:322-654](../../backend/rgenerator/core/report_steps.py))

| Componente | figsize sugerido | Paleta | Edgecolor | Notas |
|---|---|---|---|---|
| `BarByGroup` (1 valor) | medium `(8, 4)` | `PALETTE_CATEGORICAL` | `black 1.2pt` | etiquetas valor sobre barra cuando `showValues=True` |
| `BarByGroup` (multi valor) | xwide `(12, 6)` | `PALETTE_CATEGORICAL` | `gray 0.8pt` | leyenda dentro o fuera según cantidad |
| `GroupedBarByPeriod` | xwide `(12, 6)` | `PALETTE_CATEGORICAL` | `gray 0.8pt` | leyenda fuera si grupos > 8 |
| `StackedCountByGroup` | wide `(10, 6)` | `PALETTE_SEMAFORO` (fallback Set2) | sin edge o `none` | etiquetas valor blancas dentro de la barra |
| `BoxPlotByGroup` | medium `(8, 4)` | `PALETTE_BOXPLOT` cicled | `black 1.5pt` | sin relleno con alpha 0.6 |
| `Histogram` | medium `(8, 4)` | `PALETTE_CATEGORICAL[0]` (verde Set2) | `black 1.2pt` | |
| `GaugeIndicator` | medium `(8, 4)` | color `#111` | n/a | sólo texto, sin ejes |
| `HeatmapMatrix` | medium `(8, 4)` | `cmap='Greens'` o `'Greys'` | n/a | LaTeX no lo usa, mantener neutro |

## 12. Reglas de oro para cualquier cambio visual

1. **Si LaTeX no lo hace, NO se agrega**. Las clases CSS y paletas tienen su origen en `formato_informe.tex` o `funciones.py`.
2. **Negro y grises para estructura, color sólo en datos**. Header/footer/títulos/tablas son blancos y negros. El color aparece sólo en barras, boxes, stacked.
3. **Bordes negros en barras**, no blancos (el blanco hace que las barras "floten" sobre el fondo blanco; LaTeX las contiene con bordes negros).
4. **Grid Y dashed alpha 0.6, zorder=0** (detrás de barras). Nunca grid X.
5. **DPI 300**, no 120. Las imágenes embebidas en PDF se ven más nítidas y los textos dentro del gráfico no pixelan.
6. **Etiquetas de valor con bbox blanco semi-transparente** cuando se solapan con grid o bordes (sólo en barras agrupadas/apiladas).

---

**Próximo paso**: Bloque 3.1 — Refactor `report_base.html` aplicando secciones 1-7 de este documento.
