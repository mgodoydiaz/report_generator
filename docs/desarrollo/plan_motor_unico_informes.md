# Plan de estandarización — Motor único de informes

**Fecha**: 2026-07-30 · **Estado**: propuesta, pendiente de OK por fases · **Base factual**: [inventario_indicadores_2026-07-30.md](./inventario_indicadores_2026-07-30.md)

## Objetivo (definición de producto, Miguel)

Un solo motor de informes que, por indicador, genere **resumen de última prueba, semestral y anual**, mostrando la información suficiente de los dashboards, sin errores. Hardcodear por indicador es aceptable; lo que se unifica es el motor y la experiencia.

## Estado actual (por qué duele)

Dos motores vivos que se reparten mal el trabajo:

| | Motor v1 (layout) | Motor v2 (formato oficial) |
|---|---|---|
| Períodos (última/semestral/anual) | ✓ (`periodos.py`) | ✗ (solo un punto en el tiempo) |
| Calidad visual validada vs referencia | ✗ (2 páginas genéricas) | ✓ (14 páginas, paridad Pullinque) |
| Configuración | `pdf_layout` en DB por indicador | esquema JSON + `crear_informe.py` por evaluación |
| Cobertura hoy | 4 indicadores con layout; Panguipulli sin configurar | SIMCE, DIA, Panguipulli, PDL IDEL; CV y FL sin módulo |

Resultado: CV y FL solo tienen 2/5 informes, Panguipulli 1/5, y los que funcionan dependen de qué motor los atienda.

## Decisión de arquitectura (propuesta)

**El motor único = capa de render del v2** (registro de charts/tablas + template WeasyPrint, la que igualó la referencia) **+ `periodos.py`** (resolver ya compartido). Cada indicador tiene **un módulo** en `backend/rgenerator/reports/custom/` con un único punto de entrada:

```python
def generar(db, *, indicator_id, org_id, modo, filtros=None, params=None, overrides=None) -> bytes
# modo ∈ {"ultima_prueba", "semestral", "anual", "personalizado"}
```

- Las 4 cards de período del selector despachan al módulo del indicador cuando existe; el path v1 queda de fallback y se depreca al final.
- Las secciones de cada modo **espejan el dashboard** del indicador (misma información, sin errores): última prueba = foto de la última evaluación; semestral/anual = mismas vistas + evolución del período.
- Errores controlados heredados: sin datos → 400 accionable; asignatura requerida; secciones fallidas → aviso neutro (nunca traceback).

## Hechos del inventario que condicionan el plan

1. **Familia A (estructura compartida)**: SIMCE, DIA y Panguipulli tienen dashboards casi idénticos (tabs general/curso/estudiante/tendencia) → un patrón de módulo común con variaciones.
2. **Familia B (estructura propia)**: IDEL (subpruebas + matrices), Cálculo Veloz y Fluidez Lectora → módulos a medida (aceptado: hardcodeados).
3. **Prerequisitos de datos/config detectados**:
   - FL sin dimensión Año → semestral/anual imposibles hoy; **mitigación propuesta**: extender `periodos.py` para derivar el año desde la columna `Fecha` (FL la tiene en `evaluacion_num`).
   - CV con RUT 100% vacío → identidad por Nombre (ya soportado por la cadena de identidad).
   - CV y Panguipulli solo con datos 2025 → semestral/anual "del año en curso" saldrán no-disponibles con motivo (correcto); revisar si habrá cargas 2026.
   - Panguipulli: métrica 25 (921 filas) huérfana — cargada por su pipeline pero no asociada a ningún indicador. **Decisión de Miguel pendiente**: ¿se asocia o se ignora?
   - Gráficos de tendencia: el eje aún colapsa el mismo hito de años distintos → se corrige DENTRO del motor único (prerequisito del modo anual).
4. 3 de 6 indicadores no tienen pipeline (carga masiva histórica) — irrelevante para el motor (lee `metric_data`), relevante para la operación futura.

## Fases (cada una termina con OK de Miguel)

| # | Fase | Entregable | Estimación agentes |
|---|---|---|---|
| 0 | Inventario | ✅ hecho ([doc](./inventario_indicadores_2026-07-30.md)) | — |
| 1 | **Especificación por indicador**: 1 página por indicador con las secciones exactas de cada modo, mapeadas desde sus tabs/gráficos reales del dashboard | 6 fichas de especificación (doc) | 1 Sonnet (~150k) + revisión Fable |
| 2 | **Contrato del motor**: spec técnica del módulo (firma, secciones period-aware, derivación de año desde Fecha, fix de tendencia multi-año, manejo de vacíos) + adaptación del selector | doc técnico + tests de contrato definidos | Fable + 1 Opus chico (~120k) |
| 3 | **Piloto SIMCE**: módulo con los 3 modos, QA visual contra la referencia Pullinque | módulo + PDFs verificados | 1 Opus (~250k) + QA visual (~150k) |
| 4 | **Migración**: DIA → IDEL → Panguipulli → CV → FL (orden por valor/dificultad; FL al final por el prerequisito de Fecha→Año) | 5 módulos + QA por cada uno | 3-4 tandas Opus (~250k c/u) |
| 5 | **Deprecación y cierre**: retiro del path v1 en las cards, smoke tests por modo, docs y tutorial actualizados | limpieza + guardas | 1 Sonnet (~120k) |

Total estimado: ~1.8-2.2M tokens de agentes, repartido en 4-6 sesiones de trabajo.

## Riesgos

- **Doble mantenimiento transitorio** (fases 3-4): v1 y módulos conviven; mitigado porque v1 ya es fallback puro.
- **Datos faltantes ≠ bugs del motor**: los huecos (CV 2026, metric 25, FL Año) deben resolverse como datos/config o el QA visual los reportará eternamente.
- **Alcance de "información suficiente"**: la fase 1 es el contrato de contenido — sin OK explícito de las fichas, no se programa (regla del plan).

## Decisiones pendientes de Miguel

1. OK a la arquitectura (motor = capa v2 + períodos, un módulo por indicador, v1 a fallback→deprecación).
2. OK al orden de fases y al piloto SIMCE.
3. Métrica 25 huérfana de Panguipulli: ¿asociar o ignorar?
4. ¿Habrá cargas 2026 de CV y Panguipulli? (condiciona la utilidad de semestral/anual para ellos).
