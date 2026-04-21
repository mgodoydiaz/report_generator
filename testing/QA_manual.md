# QA Manual — Report Generator MVP

Checklist de verificación manual por milestone. Marcar con `[x]` al completar cada ítem.

---

## M0 — Renombre métrica IDEL → PDL

| # | Paso | Esperado |
|---|------|----------|
| 1 | Iniciar sesión como admin | Login exitoso |
| 2 | Ir a `/metrics` | Lista de métricas |
| 3 | Buscar métrica id 8 | Aparece como **"Resultados PDL"** (no "IDEL") |
| 4 | `GET /api/metrics/` con token | JSON contiene `"name": "Resultados PDL"` |
| 5 | Abrir cualquier Indicator que use métrica 8 | Dashboard muestra nombre correcto |

**Estado**: ✅ Completado en dev DB.

---

## M1 — Nuevos gráficos: Histograma, Mapa de Calor, Gauge

### Histograma (`Histogram`)

| # | Paso | Esperado |
|---|------|----------|
| 1 | Ir a Indicadores → abrir un indicador con datos numéricos | Dashboard visible |
| 2 | Abrir Editor de Layout → "Agregar componente" | Modal `AddComponentModal` abre |
| 3 | En el grupo "Gráficos simples", seleccionar **Histograma** | Avanza al paso 2 (configuración) |
| 4 | Seleccionar `valueField` (ej. Puntaje) | Campo seleccionado |
| 5 | (Opcional) Seleccionar `groupField` (ej. Curso) | Acepta sin error |
| 6 | Avanzar al paso 3 (vista previa) | Gráfico de barras de frecuencia renderiza sin errores |
| 7 | Confirmar y agregar al layout | Item aparece en el dashboard |
| 8 | Con datos reales: barras distribuidas correctamente por rango | Bins visibles, sin datos distorsionados |
| 9 | Sin `groupField`: histograma único sin leyenda | No muestra leyenda |
| 10 | Con `groupField`: series superpuestas con `opacity: 0.65` | Series diferenciadas por color |

### Mapa de Calor (`HeatmapMatrix`)

| # | Paso | Esperado |
|---|------|----------|
| 1 | En AddComponentModal, grupo **"Matrices / Calor"**, seleccionar **Mapa de Calor** | Avanza a config |
| 2 | Seleccionar `xField` (ej. `_curso`) | Campo xField guardado |
| 3 | Seleccionar `yField` (ej. `_evaluacion_num`) | Campo yField guardado |
| 4 | Seleccionar `valueField` (ej. Puntaje) | Campo valueField guardado |
| 5 | Vista previa | Matriz de celdas coloreadas por intensidad renderiza |
| 6 | Hover sobre celda | Tooltip muestra `"eje_y × eje_x: valor"` |
| 7 | Celdas sin datos (combinación inexistente) | Celda vacía o `null`, sin error |
| 8 | `showValues: true` | Valores numéricos dentro de cada celda |

### Medidor KPI (`GaugeIndicator`)

| # | Paso | Esperado |
|---|------|----------|
| 1 | En AddComponentModal, grupo **"Gráficos especiales"**, seleccionar **Medidor** | Avanza a config |
| 2 | Seleccionar `valueField` (ej. Puntaje) | Campo guardado |
| 3 | Vista previa | Gauge renderiza con arco rojo/amarillo/verde |
| 4 | Aguja apunta al promedio de los datos | Valor correcto |
| 5 | Formato `%`: gauge en rango 0–1, ticks con `%` | Correcto |
| 6 | Formato `#`: gauge en rango 0–100 (default) | Correcto |
| 7 | Sin datos | Mensaje "Sin datos" en lugar del gauge |

### Regresiones M1

| # | Paso | Esperado |
|---|------|----------|
| R1 | Gráficos existentes (BarByGroup, BoxPlot, etc.) siguen funcionando | Sin cambios en comportamiento |
| R2 | Build de producción `npm run build` pasa sin errores | ✅ `built in Xs` |
| R3 | `PLOTLY_REQUIRED_FIELDS` valida campos faltantes | Muestra `MissingConfigError` con campos faltantes listados |

---

## M2.1 — Tabla Pivote

| # | Paso | Esperado |
|---|------|----------|
| 1 | En AddComponentModal, grupo **"Tablas"**, seleccionar **Tabla Pivote** | Abre `PivotTableConfig` (UI de 3 zonas) |
| 2 | Arrastrar `_curso` a zona **Filas** | Campo aparece en zona Filas |
| 3 | Arrastrar `_asignatura` a zona **Columnas** | Campo aparece en zona Columnas |
| 4 | Arrastrar `Puntaje` a zona **Valores** con agregación `avg` | Campo aparece en zona Valores |
| 5 | Vista previa | Tabla HTML pivote renderiza correctamente |
| 6 | Celdas: promedio de Puntaje para cada combinación Curso × Asignatura | Valores correctos |
| 7 | Sin columnas configuradas | Tabla de una sola columna de valores por fila |
| 8 | Múltiples valores (ej. Puntaje + Nivel de Riesgo) | Columnas de valor adicionales visibles |
| 9 | Cambiar agregación de `avg` a `sum` | Totales correctos |
| 10 | Combinación sin datos | Celda muestra `—` |

---

## M2.2 — Tabla plana con filtros

| # | Paso | Esperado |
|---|------|----------|
| 1 | Seleccionar **Lista de Items** con filtros | Config muestra opción de filtros |
| 2 | Filtrar por `_curso = "2°A"` | Solo filas de ese curso |
| 3 | Ordenar por Puntaje descendente | Filas ordenadas |
| 4 | Sin filtros activos | Todas las filas |
| 5 | Filtro + orden combinados | Filas filtradas y ordenadas correctamente |

---

## M2.3 — Columnas calculadas

| # | Paso | Esperado |
|---|------|----------|
| 1 | En tabla (pivote o plana), agregar columna calculada | Input de expresión visible |
| 2 | Expresión `correctas / total * 100` | Nueva columna con valores correctos |
| 3 | Expresión inválida (ej. `import os`) | Error controlado, no crash |
| 4 | Columna calculada con nombre personalizado | Encabezado correcto |

---

## M3.0 — Spike tecnología PDF

| # | Paso | Esperado |
|---|------|----------|
| 1 | Ejecutar ejemplo WeasyPrint: `python docs/pdf_examples/weasyprint_demo.py` | Genera `demo_weasyprint.pdf` |
| 2 | Ejecutar ejemplo Typst: `typst compile docs/pdf_examples/demo.typ demo_typst.pdf` | Genera PDF con tipografía correcta |
| 3 | Ejecutar ejemplo ReportLab: `python docs/pdf_examples/reportlab_demo.py` | Genera `demo_reportlab.pdf` |
| 4 | Comparar los 3 PDFs: layout, tipografía, tamaño de archivo | Decidir tecnología |

---

## M3.1 — Schema pdf_layout

| # | Paso | Esperado |
|---|------|----------|
| 1 | `alembic upgrade head` | Migración aplica sin error |
| 2 | `SELECT pdf_layout FROM indicators LIMIT 3;` | Columna existe, valor `{}` o `null` |
| 3 | `GET /api/indicators/{id}` | Respuesta incluye campo `pdf_layout` |
| 4 | `PATCH /api/indicators/{id}` con `pdf_layout` nuevo | Se guarda correctamente |

---

## M3.2 — Tab PDF en LayoutEditorModal

| # | Paso | Esperado |
|---|------|----------|
| 1 | Abrir LayoutEditorModal de cualquier indicador | Aparece tab **"Informe PDF"** |
| 2 | Agregar sección Portada: título y texto | Sección visible en lista |
| 3 | Agregar sección Gráfico: dropdown muestra items del dashboard | Selección disponible |
| 4 | Reordenar secciones con DnD | Orden cambia |
| 5 | Guardar | `pdf_layout` actualizado en la DB |
| 6 | Reabrir modal | Layout PDF persistido correctamente |

---

## M3.3 + M3.4 — Step RenderPDFReport y endpoint

| # | Paso | Esperado |
|---|------|----------|
| 1 | `POST /api/indicators/{id}/export-pdf` con token válido | Responde con `Content-Type: application/pdf` |
| 2 | Descargar el PDF | Archivo `.pdf` válido, abre en visor |
| 3 | PDF contiene portada con título del indicador | ✅ |
| 4 | PDF contiene gráfico configurado como PNG | ✅ |
| 5 | PDF contiene tabla configurada | ✅ |
| 6 | Indicador sin `pdf_layout` | Error 400 con mensaje descriptivo |
| 7 | Token inválido | Error 401 |

---

## M4 — Deploy dev → devtest → main

### Pre-deploy checklist

- [ ] Todas las pruebas de M0–M3 pasan en entorno local Docker
- [ ] `npm run build` pasa sin errores
- [ ] `pytest tests/` pasa sin errores
- [ ] Migración Alembic incluida en el PR

### devtest (Render staging)

| # | Paso | Esperado |
|---|------|----------|
| 1 | Push `dev` → `devtest`, Render redeploy | Deploy exitoso |
| 2 | `alembic upgrade head` en staging | Migración aplicada |
| 3 | Login con credenciales de staging | Acceso correcto |
| 4 | Ver métricas: "Resultados PDL" visible | ✅ |
| 5 | Crear indicador de PDL con layout de dashboard | Dashboard renderiza |
| 6 | Descargar PDF del indicador | PDF correcto |

### Producción (main)

| # | Paso | Esperado |
|---|------|----------|
| 1 | Merge `devtest → main` en ventana de mantenimiento | Sin conflictos |
| 2 | Aplicar migraciones Alembic en prod DB | Sin errores |
| 3 | Smoke test: login admin | ✅ |
| 4 | Smoke test: ver dashboard PDL | ✅ |
| 5 | Smoke test: descargar PDF | ✅ |
| 6 | Verificar logs del backend primeros 15 minutos | Sin errores 500 |

---

## Notas de entorno

- **Docker local**: `docker compose -f docker-compose.dev.yml up`
- **Usuario test local**: ver `memory/project_deploy_status.md` para credenciales
- **API**: `http://localhost:8000`
- **Frontend**: `http://localhost:5173`
