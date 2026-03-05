# Referencia: plot_tools.py

Funciones disponibles para la generación de gráficos en `backend/rgenerator/tooling/plot_tools.py`.
Se invocan desde `GenerateGraphics` usando el campo `"type"` en cada entrada de `charts_list`.

---

## `grafico_barras_promedio_por`

Barras del promedio de una columna numérica, agrupadas por una columna categórica.

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `columna_valor` | str | — | Columna numérica a promediar |
| `agrupar_por` | str | `"Curso"` | Columna de agrupación (eje X) |
| `titulo` | str | `"Logro Promedio por Curso"` | Título del gráfico |
| `ylabel` | str | `"Logro (%)"` | Etiqueta eje Y |
| `nombre_grafico` | str | — | Ruta de salida (inyectado por el step) |

**Notas:** Eje Y fijo en rango 0–1 con formato porcentaje. Muestra etiqueta de valor sobre cada barra.

---

## `boxplot_valor_por_curso`

Distribución de una columna numérica por grupo (boxplot).

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `columna_valor` | str | — | Columna numérica a distribuir |
| `agrupar_por` | str | `"Curso"` | Columna de agrupación (eje X) |
| `titulo_grafico` | str | `"Distribución de Rendimiento por Curso"` | Título |
| `ylabel` | str | `""` | Etiqueta eje Y |
| `ylims` | tuple\|None | `None` | Límites del eje Y (ej: `[0, 1]`) |
| `formato` | str | `"number"` | `"number"` o `"percent"` |
| `nombre_grafico` | str | — | Ruta de salida |

---

## `alumnos_por_nivel_cualitativo`

Barras apiladas de cantidad de alumnos por nivel cualitativo (ej: Adecuado / Elemental / Insuficiente), agrupadas por curso.

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `columna_nivel` | str | `"Logro"` | Columna con el nivel cualitativo |
| `agrupar_por` | str | `"Curso"` | Columna de agrupación (eje X) |
| `lista_niveles` | list | `["Adecuado", "Elemental", "Insuficiente"]` | Niveles en orden de apilado (abajo → arriba) |
| `titulo_grafico` | str | `""` | Título del gráfico |
| `titulo_leyenda` | str | `""` | Título de la leyenda |
| `ylabel` | str | `""` | Etiqueta eje Y |
| `nombre_grafico` | str | — | Ruta de salida |

**Notas:** Colores fijos por nivel (verde-agua / amarillo / rojo). Muestra conteo dentro de cada segmento.

---

## `alumnos_por_nivel_curso_y_mes`

Barras apiladas de alumnos por nivel, con doble agrupación: curso × mes. Genera un bloque de barras por curso, subdividido por mes.

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `columna_nivel` | str | `"Logro"` | Columna con el nivel cualitativo |
| `columna_curso` | str | `"Curso"` | Columna de curso |
| `columna_mes` | str | `"Mes"` | Columna de mes |
| `lista_niveles` | tuple | `("Insuficiente", "Elemental", "Adecuado")` | Niveles en orden de apilado |
| `lista_paleta` | list | `["#C2A47A", "#2196F3", "#5FA59E"]` | Colores por nivel |
| `orden_cursos` | list | `["2A","2B","2C","2D"]` | Orden de cursos en el eje X |
| `orden_meses` | list | `["ABRIL","JUNIO","AGOSTO","OCTUBRE","NOVIEMBRE"]` | Orden de meses dentro de cada bloque |
| `titulo_grafico` | str | `"Comparación de Alumnos..."` | Título |
| `titulo_leyenda` | str | `"Nivel de Logro"` | Título de la leyenda |
| `ylabel` | str | `"Cantidad"` | Etiqueta eje Y |
| `mostrar_totales` | bool | `True` | Muestra el total encima de cada barra |
| `rot_x` | int | `90` | Rotación de etiquetas de mes |
| `nombre_grafico` | str | — | Ruta de salida |

**Retorna:** DataFrame pivot usado para generar el gráfico (útil para debug).

---

## `valor_promedio_agrupado_por`

Barras agrupadas con doble nivel de agrupación: un grupo principal (eje X) y un grupo secundario (series de barras dentro de cada grupo).

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `columna_valor` | str | — | Columna numérica a promediar |
| `agrupar_principal_por` | str | `"Curso"` | Agrupación principal (eje X) |
| `agrupar_secundario_por` | str | `""` | Agrupación secundaria (series de barras) |
| `orden_grupo_secundario` | str | `"Numero_Prueba"` | Columna para ordenar el grupo secundario |
| `titulo_grafico` | str | `""` | Título |
| `titulo_leyenda` | str | `""` | Título de la leyenda |
| `y_lims` | list\|None | `None` | Límites del eje Y |
| `formato` | str | `"number"` | `"number"` o `"percent"` |
| `nombre_grafico` | str | — | Ruta de salida |

---

## Notas comunes

- El parámetro `nombre_grafico` es inyectado automáticamente por `GenerateGraphics` — no es necesario incluirlo en `params` del spec.
- Todas las funciones guardan el archivo y retornan `None` (excepto `alumnos_por_nivel_curso_y_mes` que retorna el pivot).
- Resolución de salida: 300 dpi (salvo `grafico_barras_promedio_por` que usa el default de matplotlib).
