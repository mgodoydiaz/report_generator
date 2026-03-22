# Plan: Modal "Agregar Componente" al Dashboard

## Contexto

Reemplazar el dropdown actual de "Agregar" en `LayoutEditorModal.jsx` por un modal completo de 3 pasos para seleccionar, configurar y previsualizar componentes del dashboard.

Mockup de referencia en `examples_and_mockups/ModalAddGraphiComponent/`.

---

## Decisiones de diseño tomadas

| Tema | Decisión |
|---|---|
| **Stepper lateral** | No. Usar indicador compacto `Paso X / Z` con flechas atrás/adelante y título del paso |
| **Ancho del modal** | Puede ser más ancho que el editor de layout actual (~900px) |
| **Íconos** | Lucide, no emojis |
| **Paso 2 — flujo** | Una pregunta por vez (wizard), no formulario junto |
| **Paso 3 — preview** | Botón opcional "Generar vista previa" para no bloquear el flujo. Requiere fetch al backend para obtener muestra de datos del indicador |
| **Configuraciones extra** | Aplicar solo a tipos donde tienen sentido |
| **Columnas extra** | Botón para agregar columnas no mapeadas en el indicador |

---

## Cambios ya realizados

- [x] Click fuera cierra el menú "Agregar" en `RowEditor` (ref + mousedown listener)

---

## Paso 1 — Galería de componentes

Usar la galería del mockup: grid de cards 2-3 columnas, agrupadas por categoría. Al seleccionar se marca con check y se habilita "Siguiente". Usar los `CHART_COMPONENTS`, `TABLE_COMPONENTS`, `SPECIAL_COMPONENTS` ya definidos en `LayoutEditorModal.jsx`.

**Estado:** pendiente de implementación.

---

## Paso 2 — Configuración

### Sub-pasos de ejes (ya existentes)

Se mantiene la lógica actual de `axisConfig` por tipo de componente. Cada `axisConfig` entry genera un sub-paso.

### Configuraciones adicionales por tipo

Después de los ejes, agregar sub-pasos o un formulario de opciones visuales. Lista de configuraciones posibles:

| Configuración | Tipo de control | Aplica a |
|---|---|---|
| **Título del gráfico** | Texto libre | Todos los charts y tablas |
| **Etiqueta eje Y** | Texto libre | Barras, Boxplot, Tendencia, Barras Agrupadas |
| **Etiqueta eje X** | Texto libre | Barras, Boxplot, Tendencia, Barras Agrupadas, Conteo Apilado |
| **Mostrar leyenda** | Toggle (on/off) | Todos los charts |
| **Posición de leyenda** | Select (arriba, abajo, derecha) | Todos los charts (si leyenda activa) |
| **Mostrar valores sobre barras** | Toggle | Barras, Barras Horizontales, Barras Agrupadas, Conteo Apilado |
| **Formato de valores** | Select (número, %, decimal) | Charts con valueField |
| **Paleta de colores** | Select de paletas predefinidas | Todos los charts | ⏳ PENDIENTE — los charts ya aceptan `colors[]` prop, falta: (1) definir paletas en `constants.js`, (2) agregar selector en `StepConfig`, (3) pasar `colors` desde `buildComponentProps` |
| **Ordenar barras** | Select (ascendente, descendente, original) | Barras, Barras Horizontales |
| **Columnas extra** | Botón "Agregar columna" → input texto para nombre de columna no mapeada | Todos |

> **Nota:** las configuraciones se guardan en el item del layout como propiedades adicionales (ej. `title`, `showLegend`, `labelY`, etc.)

**Estado completado:**
- [x] Título del gráfico (`title`) — guardado en item, aplicado en `ItemRenderer`
- [x] Etiqueta eje Y (`labelY`) — conectado a todos los charts Plotly con valueField
- [x] Etiqueta eje X (`labelX`) — conectado a charts con eje X categórico
- [x] Mostrar leyenda (`showLegend`) — conectado a todos los charts Plotly
- [x] Mostrar valores (`showValues`) — conectado a charts de barras y líneas

**Pendiente:**
- [ ] Paleta de colores (`colorPalette`) — ver nota en tabla

---

## Paso 3 — Vista previa

- Mostrar un SVG esquemático por defecto (como el mockup).
- Botón "Generar vista previa con datos" que hace fetch al backend para obtener una muestra de datos del indicador y renderiza el componente real.
- Mostrar resumen de configuración elegida (tabla clave-valor).

**Requiere:**
- Endpoint backend para obtener muestra de datos de un indicador (o usar un endpoint existente).
- Componente de preview que renderice el gráfico real con Plotly usando los datos de muestra.

**Estado:** pendiente.

---

## Arquitectura de archivos propuesta

```
frontend/src/components/
├── LayoutEditorModal.jsx          ← existente, se modifica para abrir el nuevo modal
└── add-component/
    ├── AddComponentModal.jsx      ← modal principal con lógica de pasos
    ├── StepGallery.jsx            ← paso 1: galería de componentes
    ├── StepConfig.jsx             ← paso 2: configuración de ejes + opciones
    └── StepPreview.jsx            ← paso 3: preview + resumen
```

---

## Orden de implementación

1. **AddComponentModal + StepGallery** — modal funcional con paso 1
2. **StepConfig — ejes** — migrar la lógica de AxisConfigurator al nuevo modal
3. **StepConfig — título y etiquetas** — primera config visual
4. **StepConfig — toggles** (leyenda, valores sobre barras)
5. **StepConfig — columnas extra** — botón para agregar columnas no mapeadas
6. **StepPreview — SVG esquemático** — preview estático por tipo
7. **StepPreview — datos reales** — fetch + render con Plotly
8. **Integración** — conectar con RowEditor para reemplazar el dropdown actual
