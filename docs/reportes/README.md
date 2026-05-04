# Reportes de calidad de informes PDF

Esta carpeta contiene reportes de calidad emitidos por el agente de revisión
sobre los informes PDF que el sistema genera. Cada reporte evalúa un PDF
concreto en 3 dimensiones (Aporte informativo, Legibilidad, Diseño) y entrega
sugerencias accionables.

## Cómo generar un reporte

Desde Claude Code:

```
/quality-review <path-o-nombre-del-pdf>
```

Ejemplos:

```
/quality-review data/output/smoke_test_render_html.pdf
/quality-review informe_simce_lenguaje_2025_10.pdf
/quality-review                              # lista los PDFs disponibles y pregunta cuál
```

El comando lee el PDF visualmente, evalúa cada página y escribe el reporte
en este directorio con el nombre `calidad_<basename>_<YYYY-MM-DD>.md`.

## Estructura típica de un reporte

- **Resumen ejecutivo** — 2-3 oraciones, listo o no para entregar.
- **Hallazgos por página** — score 1-5 en cada dimensión + sugerencias.
- **Top sugerencias accionables** — ordenadas por prioridad, cada una con
  archivo/componente afectado para poder iterar.
- **Aspectos positivos** — qué preservar en próximas iteraciones.
- **Score por categoría** — tabla con totales y porcentajes.
- **Notas para próxima revisión** — chequeos para la siguiente vuelta.

## Workflow de iteración recomendado

1. Generar PDF con la configuración actual.
2. Correr `/quality-review` sobre ese PDF.
3. Leer el reporte y aplicar las sugerencias **[Alta prioridad]** y
   **[BLOQUEANTE]**.
4. Re-generar el PDF.
5. Re-correr `/quality-review` — el nuevo reporte se guarda con el mismo
   timestamp del día (sobrescribe) o con el siguiente día.
6. Iterar hasta tener score global > 80% y cero bloqueantes.

## Por qué emitir reportes y no solo comentar

Los reportes en disco:
- Quedan **versionados en el repo** (no se pierden entre sesiones).
- Permiten ver la **evolución** del mismo informe a través del tiempo.
- Sirven como **baseline** cuando alguien nuevo revisa el proyecto y quiere
  saber "qué se aprobó y qué quedó pendiente".
- Son **auditables**: el cliente o un colega pueden ver por qué tomamos las
  decisiones de diseño que tomamos.
