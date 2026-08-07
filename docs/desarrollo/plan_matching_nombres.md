# Plan — Matching numérico de nombres de estudiantes

**Fecha**: 2026-08-07 · **Estado**: propuesta aprobada para diseño, sin implementar
**Contexto**: post "salida de Nombre_Norm" (la normalización pasó a ser función interna de lectura). Idea original de Miguel: usar embeddings u otro método numérico para detectar que "Apellido Nombre" y "Nombre Apellido" son la misma persona, y a futuro asociar cada estudiante a su RUT.

## 1. El problema real

Con `Nombre_Norm` eliminado, la identidad de lectura es `RUT` → `normalizar_nombre(Nombre)` (clave interna con palabras ordenadas). Esa clave resuelve **exactamente** el caso "Apellido Nombre" vs "Nombre Apellido" — el reordenamiento puro ya está cubierto sin costo. Lo que la clave NO resuelve, y donde un método numérico sí aporta:

| Caso | Ejemplo real del dominio | ¿Clave ordenada lo resuelve? |
|---|---|---|
| Reorden de palabras | "PÉREZ SOTO JUAN" vs "Juan Pérez Soto" | ✅ Sí (gratis) |
| Tildes/mayúsculas | "GONZÁLEZ" vs "Gonzalez" | ✅ Sí |
| Typos | "GONZALES" vs "GONZÁLEZ", "NARVAEZ" vs "NARVÁES" | ❌ |
| Nombre omitido | "Juan Pérez Soto" vs "Juan Andrés Pérez Soto" | ❌ |
| Ortografías variables (frecuente en apellidos mapuche) | "CAQUILPÁN" vs "CAQUILPAN" vs "KAKILPAN" | ❌ (tildes sí, consonantes no) |
| Truncamiento de la fuente | "ROSARIO CONSTANZA BELÉN CAUPAN C." | ❌ |

**Conclusión de diseño**: los embeddings son la herramienta de *tercera* línea, no la primera. Para strings cortos como nombres, la similitud difusa clásica (token-set + edición) es más precisa, más barata, más explicable y no requiere infraestructura nueva. Los embeddings se reservan para la cola que el nivel difuso no resuelva.

## 2. Escalera de matching (N0 → N3)

```
N0  RUT exacto                    → match seguro, sin score
N1  clave normalizada ordenada    → normalizar_nombre() actual, match determinista
N2  score difuso 0..1             → rapidfuzz: token_set_ratio + Jaro-Winkler por token
N3  embeddings + pgvector         → solo la cola no resuelta por N2
```

- **N2 (el corazón del plan)**: score = combinación de (a) Jaccard sobre conjuntos de tokens normalizados (invariante al orden), (b) mejor emparejamiento por token con Jaro-Winkler (castiga poco los sufijos → bueno para typos al final), (c) bonus si los apellidos coinciden. Librería: `rapidfuzz` (C++, miles de comparaciones/segundo, sin GPU). Bloqueo por org + curso + año para no comparar todos contra todos.
- **N3 (si hace falta)**: embeddings de caracteres (fastText char n-grams o `sentence-transformers` mini multilingüe) sobre el nombre normalizado; almacenar en Postgres con **pgvector** (Supabase lo soporta nativo) y buscar por similitud coseno. Activar solo si la evaluación de N2 muestra una cola relevante de falsos negativos.

### Umbrales (a calibrar, no adivinar)

| Score N2 | Acción |
|---|---|
| ≥ 0.92 | Match automático (se registra como alias) |
| 0.75 – 0.92 | **Cola de revisión humana** (UI: "¿son la misma persona?") |
| < 0.75 | Personas distintas |

## 3. Registro maestro de estudiantes (la pieza que faltaba)

El matching necesita un lugar donde vivir. Nuevas tablas (org-scoped, como todo):

```
students:         id, org_id, rut (nullable, único por org), nombre_display,
                  created_at, updated_at
student_aliases:  id, student_id, alias_texto, alias_clave (normalizada),
                  score, origen (metric_id/carga), confirmado_por (nullable), created_at
```

- `nombre_display` = la variante legible más completa/frecuente.
- **Asociación con RUT** (la idea de Miguel): cuando una carga trae RUT + nombre (ej. SIMCE Panguipulli), se consolida: el student adquiere RUT y todos sus aliases quedan asociados. Cargas futuras sin RUT que matcheen un alias heredan la identidad completa.
- `metric_data` NO se modifica en F1-F2 (sin FK); el registro es una capa de resolución por encima. FK opcional en fase final.

## 4. Dataset de evaluación gratis

Ya tenemos ground truth para calibrar umbrales sin etiquetar a mano:

1. Los ~18k pares históricos `(Nombre, Nombre_Norm)` — pares positivos garantizados.
2. Estudiantes que aparecen en varias métricas/años con el mismo RUT (SIMCE Panguipulli) — positivos inter-fuente.
3. Pares negativos: compañeros del mismo curso (nombres distintos garantizados).

Métrica objetivo: **precision ≥ 0.995** en match automático (un falso merge es peor que un falso split), recall el que dé; el resto va a cola de revisión.

## 5. Fases

| Fase | Contenido | Estimación |
|---|---|---|
| F1 | Tablas `students`/`student_aliases` + migración Alembic + poblar desde datos existentes (RUT y clave normalizada, sin fuzzy) | 1 agente coder (~200k tokens) |
| F2 | Motor N2 con rapidfuzz + script de evaluación con el dataset §4 + calibración de umbrales + reporte | 1 agente (~250k) |
| F3 | Integración a la carga: hook post-SaveToMetric que resuelve identidad y alimenta la cola; endpoint + UI mínima de revisión ("¿misma persona?") | 2 agentes (~400k) |
| F4 | (condicional) pgvector + embeddings para la cola de N2 | 1 agente (~250k) |

## 6. Riesgos y decisiones abiertas

- **Homónimos reales** (hermanos, tocayos en el mismo colegio): el bloqueo por curso+año reduce el riesgo; el RUT lo elimina. Nunca auto-merge entre cursos distintos sin RUT.
- **Privacidad**: los embeddings de nombres son PII derivada; mantener org-scoped y no exportarlos. pgvector en la misma DB, sin servicios externos.
- **Decisión abierta para Miguel**: ¿la cola de revisión vive en `/values`, en una página nueva `/identidades`, o dentro del chatbot (ver plan_chatbot_ia.md §tools)?
