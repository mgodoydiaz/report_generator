# Reporte de calidad — Smoke test SIMCE Lenguaje 2° Medio

**Fecha de revisión**: 2026-05-02
**PDF analizado**: `data/output/smoke_test_render_html.pdf`
**Tamaño**: 1.1 MB · **Páginas**: 6
**Score global**: 79/90 (88%)

---

## Resumen ejecutivo

PDF generado con `RenderHtmlReport` (motor WeasyPrint) sobre datos mock para SIMCE Lenguaje 2° Medio. **Paridad visual con el LaTeX referencia es muy buena** — header/footer, paleta de gráficos y alineación de tablas están a nivel de producción. Los únicos issues son cosméticos: la tabla "Reporte de estadísticas por pregunta" se corta entre página 5 y 6 dejando espacio en blanco, y la leyenda de mes en los gráficos de evolución cambia de posición entre páginas.

**Veredicto**: ⚪ **Listo con ajustes menores**

---

## Hallazgos por sección

### Página 1 — Título + Tabla resumen logro + Tabla resumen SIMCE + Gráfico rendimiento

- **Aporte informativo**: 5/5 — KPIs clave (logro % y SIMCE) + visualización inmediata de comparación entre cursos
- **Legibilidad**: 5/5 — tablas con bordes negros 0.5pt, alineación derecha en números, gráfico Set2 con valores encima de cada barra
- **Diseño**: 5/5 — título h1 cabe en una línea (post-fix de h1 a 18pt), subtítulo escuela con jerarquía clara, header con 2 logos + 3 líneas centradas perfectamente alineados
- **Sugerencias**: ninguna

### Página 2 — Distribución de Puntaje SIMCE por Curso (boxplot)

- **Aporte informativo**: 5/5 — el boxplot complementa al promedio de pág 1 mostrando dispersión y outliers
- **Legibilidad**: 4/5 — boxplot claro, paleta tab10 con alpha 0.6 funciona; los outliers (círculos blancos) podrían tener mejor contraste
- **Diseño**: 5/5 — bien centrado, espacio vertical adecuado
- **Sugerencias**: subir el linewidth de los boxes para que los outliers destaquen más

### Página 3 — Evolución Logro Promedio + Evolución SIMCE Promedio (barras agrupadas por mes)

- **Aporte informativo**: 5/5 — vista histórica esencial para coordinadores
- **Legibilidad**: 4/5 — etiquetas de valor sobre cada barra ayudan; ejes pequeños pero legibles
- **Diseño**: 4/5 — **leyenda 'Mes' en posición inconsistente**: en el gráfico de Logro está en top-right, en el de SIMCE está en bottom-left
- **Sugerencias**:
  - Forzar posición de leyenda consistente (recomiendo `loc='upper right'` para ambos)
  - El gráfico de SIMCE tiene la leyenda dentro del área del plot, podría taparar valores

### Página 4 — Cantidad de Alumnos por Nivel de Logro y Curso (stacked bar)

- **Aporte informativo**: 5/5 — visualización icónica del informe SIMCE, tres niveles claros
- **Legibilidad**: 5/5 — etiquetas blancas dentro de cada segmento (números 7, 12, 6, etc.), paleta intuitiva (rojo→naranja→verde)
- **Diseño**: 5/5 — leyenda lateral derecha bien posicionada
- **Sugerencias**: ninguna — esta página es referencia de calidad para otras

### Página 5 — Reporte de estadísticas por pregunta (filas 1-36 de 40)

- **Aporte informativo**: 4/5 — tabla densa útil para análisis pedagógico, A/%A/B/%B/.../Correcta/Distractor
- **Legibilidad**: 4/5 — font 8pt al límite, pero las columnas alternadas (número + %) se distinguen
- **Diseño**: 3/5 — **la tabla se corta entre página 5 y 6**, dejando un espacio incómodo. Idealmente debería caber entera o partirse en un lugar más natural (ej: pregunta 20)
- **Sugerencias**:
  - **[Media]** Bajar font-size de la tabla a 7pt para que las 40 filas quepan en una sola página, o
  - Marcar con `page-break-inside: avoid` y aceptar que pase entera a página 6

### Página 6 — Continuación tabla preguntas (37-40)

- **Aporte informativo**: 4/5 — completa la anterior
- **Legibilidad**: 5/5 — header de tabla se repite correctamente (`<thead>` con `display: table-header-group`)
- **Diseño**: 2/5 — **2 problemas**:
  1. Mucho espacio vacío (~70% de la página)
  2. No hay título de sección visible — quien abre directo en página 6 no sabe qué tabla es
- **Sugerencias**:
  - **[Media]** Si la tabla cabe entera en una sola página, partirla mejor sería innecesario
  - **[Baja]** Considerar agregar un caption tipo "Reporte de estadísticas por pregunta (continuación)" antes del header repetido

---

## Top sugerencias accionables

Ordenadas por prioridad. Cada sugerencia incluye dónde modificar.

1. **[Media]** Tabla "Reporte de estadísticas por pregunta" se corta entre páginas 5-6
   - **Dónde**: `backend/rgenerator/templates/report_latex_paridad.html` → `table.report-table { font-size: 8pt; }`
   - **Acción**: bajar `font-size` a 7pt (o ajustar `padding` de `<td>` a 2pt 5pt) para que las 40 filas quepan en una sola página. Verificar visualmente que sigue siendo legible.

2. **[Baja]** Leyenda 'Mes' en gráficos de evolución cambia posición entre página 3a y 3b
   - **Dónde**: `backend/rgenerator/tooling/plot_tools.py` → `valor_promedio_agrupado_por`, posición de `ax.legend(...)`
   - **Acción**: forzar `loc='upper right'` o `bbox_to_anchor=(1.02, 1)` consistente en todas las llamadas para que el ojo no tenga que rastrear la leyenda

3. **[Baja]** Página 6 con espacio en blanco grande
   - Resuelto automáticamente si se aplica la sugerencia #1

---

## Aspectos positivos a preservar

- **Header/footer impecables**: regla horizontal continua, logos a 2cm, 3 líneas centradas con buen kerning. **No tocar**.
- **Tipografía Inter** se ve sobria y profesional, similar a Segoe UI del LaTeX original.
- **Paleta Set2** consistente entre los gráficos de página 1 y 3 (mismo verde-agua, naranja, lila, rosa).
- **Tabla con alineación numérica correcta**: primera columna a la izquierda, números a la derecha, header bold. Esto está MUY bien.
- **Stacked bar de niveles** (página 4) con números en blanco dentro de cada segmento — patrón referencia para futuros gráficos similares.
- **Tamaño del archivo** (1.1 MB) muy similar al LaTeX original (1.12 MB) — embebido base64 no inflo significativamente.

---

## Score por categoría

| Categoría | Promedio | Sobre 5 | % |
|---|---|---|---|
| Aporte informativo | 4.7 | 5 | 93% |
| Legibilidad | 4.5 | 5 | 90% |
| Diseño | 4.0 | 5 | 80% |
| **Global** | 4.4 | 5 | **88%** |

---

## Notas para próxima revisión

- Re-correr el smoke test después de bajar font-size de tabla a 7pt y verificar que las 40 filas caben en página 5 sin romperse
- Comparar el PDF resultante contra `docs/pdf_examples/Informe SIMCE 5 Lenguaje.pdf` página por página
- Verificar que la consistencia de leyendas en gráficos de evolución se mantiene cuando se prueban con datos reales (no solo mock)
- Cuando esté listo el SummaryTable con `comparePrevious=true`, generar un PDF con datos de 2+ pruebas y validar que las flechas Δ se renderizan correctamente
- Pasar el agente sobre los 8 PDFs reales (4 informes × 2 modos) para tener baseline pre-entrega

---

**Generado por**: agente de calidad (`/quality-review` slash command, descrito en `.claude/commands/quality-review.md`)
**Próxima revisión sugerida**: tras aplicar sugerencias 1 y 2.

---

## Iteración 1 — 2026-05-02 (mismo día)

Se aplicó la sugerencia #1: bajar `font-size` de tablas de 8pt a 7.5pt y `padding` de `3pt 7pt` a `2pt 6pt` en `report_latex_paridad.html`.

**Resultado**:
- ✅ Las **40 filas de "Reporte de estadísticas por pregunta" ahora caben en una sola página** (la 5)
- ✅ El PDF bajó de 6 páginas a **5 páginas** — sin espacio en blanco
- ✅ La tabla sigue siendo perfectamente legible
- ✅ Tablas resumen de página 1 (4 filas) también se ven más compactas pero igual de claras

**Score actualizado tras iteración**:
| Categoría | Antes | Ahora | Δ |
|---|---|---|---|
| Aporte informativo | 4.7/5 | 4.7/5 | → |
| Legibilidad | 4.5/5 | 4.5/5 | → |
| Diseño | 4.0/5 | 4.7/5 | ▲ +0.7 |
| **Global** | 4.4/5 (88%) | 4.6/5 (**93%**) | ▲ +5 pp |

**Veredicto actualizado**: ⚪ → ✅ **Listo para producción** (con sugerencia #2 sobre leyendas de evolución como nice-to-have, no bloqueante).

Sugerencia #2 (posición consistente de leyenda en gráficos de evolución) no se aplicó en esta iteración — requiere tocar `plot_tools.py` y los layouts ya están armados con esa función. Se puede aplicar en una iteración aparte sin urgencia.
