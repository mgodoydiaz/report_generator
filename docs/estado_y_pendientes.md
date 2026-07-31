# Estado del proyecto y pendientes

**Última actualización**: 2026-07-30 · **Versión desplegada**: `v0.7.0` (commit `167cf5a`) · **Producción**: Railway + Supabase `us-east-1`, operativa y verificada.

Documento vivo. Complementa a [ROADMAP.md](../ROADMAP.md) (backlog histórico) y a [diagnostico_general_2026-07-30.md](./reportes/diagnostico_general_2026-07-30.md) (estado por área).

---

## 1. Qué se hizo en v0.7.0

### Descarga de informes (el objetivo del sprint)

| Cambio | Detalle |
|---|---|
| **Selector por períodos** | 4 tarjetas: última prueba / semestral / anual / personalizado. El personalizado abre un panel con filtros por dimensión y rango de meses. Resolver en `backend/rgenerator/reports/periodos.py` con semántica escolar chilena (1er semestre ene–jul). |
| **Registro de informes Python** | `backend/rgenerator/reports/custom/` con auto-descubrimiento: un informe nuevo = un archivo `.py`. Endpoint `POST /api/reports/custom/{nombre}`. Ver el README de esa carpeta. |
| **Asignatura obligatoria** | Cuando un indicador tiene ≥2 asignaturas, el informe exige elegir una (chip heredado del dashboard o selector en el modal). Se eliminó el default silencioso a "LENGUAJE". |
| **Motor único — piloto SIMCE** | `custom/simce.py` con 4 modos, helpers compartidos en `custom/_secciones.py`, despacho desde `export-pdf` con fallback al motor v1. Retrocompatibilidad del formato oficial verificada byte a byte. |
| **Riesgo persistente** | Sección al final del informe anual: el par de evaluaciones debe incluir la última del período; los que dejaron de rendir van en tabla aparte. Indica cuál fue la última evaluación considerada. |
| **Word** | Retirado del selector por decisión de producto (los endpoints y el registro siguen intactos, listos para reactivar). |

### Calidad visual de los informes (QA de 15 P0 + gate del piloto)

- Filtros sin datos → **400 accionable** en vez de PDF vacío con apariencia legítima.
- Los errores de sección ya no imprimen tracebacks dentro del PDF.
- `nan` → `—` en todas las tablas; números a 2 decimales (esto además resolvió el desborde de márgenes: las celdas traían artefactos tipo `0.5700000000000001`).
- Conteos de alumnos por estudiante único (antes sumaban filas de la métrica de preguntas).
- Orden temporal cronológico en gráficos; preguntas en orden numérico (antes 1, 10, 11… 2).
- Período compuesto (Año + Hito): el DIA sin filtros ya no mezcla 2025 con 2026.
- Contraste WCAG en etiquetas sobre segmentos claros.
- **Pie izquierdo = nombre de la organización** en todos los motores (denylist + fallback + script de limpieza de DB).

### Datos e ingesta

| Cambio | Detalle |
|---|---|
| **`Nombre` / `Nombre_Norm`** | El pipeline creaba solo la columna normalizada. Ahora toda carga deja ambas, en los 4 caminos de escritura (pipelines, import de /values, alta manual, API de ingesta). |
| **`EnrichWithLookup`** | Con llave homónima (`left_on == right_on`) pandas colapsa las columnas y el step borraba la llave: así se perdió la dimensión `Pregunta` en SIMCE mayo 2026. Corregido + pipeline blindado. |
| **Guard de cobertura 0%** | Si una carga deja una dimensión asociada completamente vacía, se emite un aviso (habría cazado el bug anterior el mismo día). |
| **Backfill en producción** | 359 nombres copiados + 17.048 normalizados + 260 filas con su dimensión `Pregunta` restaurada. |

### Plataforma

- **Filtros server-side en `/values`**: filtros por dimensión + búsqueda con debounce sobre la query paginada, endpoint de facetas, y `ORDER BY` que faltaba (la paginación podía repetir filas).
- **Tipo de dimensión `date`**: el resolver deriva año y mes desde una columna de fecha. Fluidez Lectora pasó de 2/5 a 4/5 informes disponibles.
- **Organización de prueba "Colegio Demo"** (`scripts/crear_org_demo.py`): datos sintéticos con casos borde sembrados, para probar sin tocar datos reales.
- **1.566 tests** automatizados en verde.

### Documentación

- [Guía rápida de usuario](./tutoriales/guia_rapida_usuario.md) (+ Word con la plantilla personal) — 4 pasos con capturas reales, lenguaje revisado para usuario no técnico.
- [Anexo de carga por evaluación](./tutoriales/anexo_carga_pipelines.md) — un capítulo por pipeline.
- [Mapa de la aplicación](./desarrollo/mapa_aplicacion.md), [inventario de indicadores](./desarrollo/inventario_indicadores_2026-07-30.md), [plan del motor único](./desarrollo/plan_motor_unico_informes.md), [contrato técnico](./desarrollo/contrato_motor_unico.md), [fichas por indicador](./desarrollo/fichas_informes_por_indicador.md).

---

## 2. Pendientes

Prioridad: **P0** bloquea uso · **P1** visible y serio · **P2** pulido.

### 2.1 Motor único — fases 4 y 5 (el trabajo grande que sigue)

| # | Pendiente | Notas |
|---|---|---|
| — | **Fase 4: migrar los 5 indicadores restantes** | Orden acordado: DIA → IDEL (base `scripts/report_pdl_idel.py`) → Panguipulli → Cálculo Veloz → Fluidez Lectora. Cada uno con QA visual como gate. Contrato y fichas ya están escritos: se codifica sin decisiones abiertas. |
| — | **Fase 5: deprecar el motor v1** | Retirar el fallback de las tarjetas, smoke tests por modo, actualizar docs. |
| P1 | Panguipulli muestra 0/4 tarjetas de período | Correcto hasta que tenga su módulo (fase 4). |
| P1 | Crear pestaña de Tendencia en el dashboard de Fluidez Lectora | Decisión 14 de las fichas: hoy las secciones de evolución de su informe no tienen fuente en el dashboard. |
| P2 | `report_engine_type` de CV y FL sin setear | Se setea cuando tengan módulo. |

### 2.2 Calidad de informes (del QA y la comparación con la referencia)

| # | Pendiente | Notas |
|---|---|---|
| P1 | Estadística por Pregunta: columnas A–E muestran proporciones (`0.57`) donde la referencia muestra conteos (`62`) | **Dato de origen**, no del motor. Bloquea que el motor reemplace del todo al informe LaTeX histórico. |
| P1 | Encabezado SIMCE incompleto | Faltan `N° 1` y `2° Medio`; el subtítulo dice "Resumen de la prueba" donde la referencia pone el nombre del colegio. |
| P1 | Habilidad y Eje Temático en orden alfabético | Debería ser orden curricular; además cambia el color de cada categoría respecto de la referencia. |
| P1 | `#ea580c` (Alto Riesgo, DIA) no alcanza contraste 4.5:1 con ningún color de texto | Límite de la paleta — decisión de diseño pendiente. |
| P2 | Falta el heatmap verde/amarillo en la tabla de estadística | Presente en la referencia de Pullinque. |
| P2 | Gráficos de "Evolución por Mes" con un solo mes filtrado | Degeneran a una serie única redundante; candidatos a auto-omitirse. |
| P2 | Fluidez Lectora describe el período como "06 2025" | Debería decir "JUNIO 2025": formateo del mes derivado de la columna fecha. |
| P2 | Tabla secundaria de riesgo persistente a 7 pt | La principal quedó a 8 pt; la secundaria bajó un escalón. |
| P2 | Eje X de gráficos de **tendencia** colapsa el mismo hito de años distintos | Distinto del filtro snapshot (ya corregido); cambiarlo afecta las tendencias de SIMCE/FL/CV, requiere decisión. |

### 2.3 Word (descopeado — retomar al final del proyecto)

Los endpoints y el registro siguen vivos; solo se retiraron las tarjetas del selector. Al retomar hay 4 defectos conocidos:

- **P0** La métrica se elige por lista fija y toma `Logro`, que en SIMCE es categórico → `N=0`, promedio vacío, gráfico en blanco (la numérica es `Rend`).
- **P0** Formato `%` incondicional produce valores absurdos (`15510.5%`).
- **P0** La plantilla `.docx` contiene un párrafo "GUÍA (borrar en la versión final)" que sale en todos los documentos.
- **P1** Los `.docx` no llevan encabezado ni pie con el nombre de la organización.

### 2.4 Datos e ingesta

| # | Pendiente | Notas |
|---|---|---|
| P1 | **583 filas sin identidad en producción** (576 DIA + 7 Panguipulli) | Sin `Nombre` ni `Nombre_Norm`: irreparables sin los archivos fuente. El patrón (`I D`: 26 con nombre + 30 sin) sugiere **carga duplicada del mismo curso desde dos archivos**, lo que además podría estar inflando conteos. Requiere revisión con los archivos originales. |
| P1 | `RequestUserFiles` consume en silencio archivos residuales de `data/pipeline_runs/uploads/` | Un usuario puede cargar datos viejos sin darse cuenta (ya ocurrió durante las pruebas). Falta limpiar residuos y pedir confirmación antes de reutilizar. |
| P1 | El aviso de "columna esperada llegó vacía" no se muestra en pantalla | El backend lo emite y lo devuelve en la respuesta, pero `PipelineExecutionModal.jsx` no lo renderiza. Mejora barata y de alto valor. |
| P1 | `Numero Lista` ausente en las cargas 2026 | El XLS trae "Número de Lista" (con tilde) y la métrica declara "Numero Lista". Misma familia de bugs que `Nombre` y `Pregunta`. |
| P2 | El `config_json` del pipeline 14 no reproduce la corrida de mayo | El Curso guardado es `II C` y el step genera `2C`; los % A–E quedaron divididos por 100 sin que ningún step lo haga. Revisar **antes de la próxima carga SIMCE**. |
| P2 | Pipeline EMN Aptus sin `description` en sus `file_specs` | Los tres recuadros de carga muestran el texto genérico en vez de decir qué archivo va. |
| P2 | `data/input/Lenguaje/inputs/habilidades_lenguaje.xlsx` desactualizado | Tiene columnas `N°`/`Habilidad`; el pipeline hoy exige `Pregunta`, `Habilidad` y `Eje Temático`. |

### 2.5 Seguridad y arquitectura

| # | Pendiente | Notas |
|---|---|---|
| **P0** | **Autorización laxa en los routers de dominio** | Solo `/users`, `/api-keys` y `/superadmin` exigen rol. Pipelines, dimensiones, métricas, indicadores, specs, tablas y gráficos solo piden usuario autenticado: **un `viewer` puede crear y borrar cualquier cosa**. Es el pendiente más serio del proyecto. |
| P1 | P1s del QA maestro sin cerrar | Páginas que tragan errores de API; 5 archivos con cliente HTTP propio sin manejo de 401; estados vacíos engañosos; ReDoS en `/data-ops/replace`; XSS por SVG en assets; `except: pass` en `SaveToMetric`. |
| P2 | `/results-recharts` es una ruta huérfana | Dashboard legacy con lógica duplicada, alcanzable solo tecleando la URL. Candidata a eliminarse. |
| P2 | `/live-tracking` es un placeholder comercial | No hace tracking de nada. |

### 2.6 UX y funcionalidades

| # | Pendiente | Notas |
|---|---|---|
| P2 | Selector de rango de fechas en el modal cuando la dimensión es tipo `date` | El backend ya está listo (`data_type` viaja en `dimensiones_filtrables`); falta la UI. |
| P2 | El botón **Exportar** de `/values` ignora los filtros activos | Exporta la métrica completa. |
| P2 | Comparativa de establecimientos (DIA) | Decidido: gráfico aparte, **no** dentro del PDF por colegio. |

### 2.7 Documentación y operación

| # | Pendiente | Notas |
|---|---|---|
| P1 | **3 placeholders `### COMPLETAR POR MIGUEL ###`** en el anexo de cargas | (a) qué hace el usuario cuando cambie el año, ya que DIA lo tiene fijo en 2026; (b) de qué menú de la plataforma DIA se descargan sus dos archivos; (c) cómo llegan los tres informes de Aptus al colegio. |
| P2 | Falta un informe de referencia aprobado de **DIA** | Ya tenemos SIMCE Pullinque e IDEL Panguipulli en `Desktop\PDF_test\referencias\`. |
| P2 | Guiones de QA manual `g2`–`g4` desactualizados | Mencionan botones "v1/v2" que el selector unificado ya reemplazó. |
| P2 | `.githooks/pre-push` no es ejecutable | Git lo ignora en cada push (`chmod +x` lo arregla). |
| P2 | Mantener `.env.railway` como espejo fiel de Railway | Ya se corrigieron `DATABASE_URL` y `JWT_SECRET`; conviene no dejarlo envejecer, o dejar de mantener copia local. |

---

## 3. Esquema de ramas

**Limpieza hecha el 2026-07-31**: se eliminaron las 12 ramas obsoletas (`dev2`, `dev3`, `dev_1`, `dev_pdfs`, `devtest`, `implementar_docker`, `claude/agitated-diffie`, `feat/pdf-engine-fidel-latex` y las 4 `feature/*`). Antes de borrar se verificó con `git rev-list --count main..<rama>` que **las 14 tenían 0 commits fuera de main** — no se perdió nada. Los tags (`v0.7.0` y anteriores) siguen intactos y apuntan a su historia.

```
main ──────────────────────────────► PRODUCCIÓN (Railway auto-deploy)
  ▲
  │  merge con GO explícito de Miguel
  │
dev ─── rama de trabajo ÚNICA
```

| Rama | Rol |
|---|---|
| `main` | Producción. Railway auto-deploya. Solo se mergea con GO explícito. |
| `dev` | Desarrollo. **Trabajar siempre aquí.** |

Esto restablece la convención original de [CLAUDE.md](../CLAUDE.md), de la que nos habíamos desviado con las ramas integradoras `dev2`/`dev3`. Para trabajo experimental que no deba tocar `dev`, crear una `feature/*` puntual y borrarla al mergear.

---

## 4. Checklist de despliegue (para futuros releases)

El contenedor corre `alembic upgrade head` al arrancar, así que las migraciones son automáticas. Los scripts de datos/config son manuales, **siempre con dry-run antes del `--apply`**:

1. `scripts/db_seed.py export` — respaldo previo.
2. `scripts/limpiar_left_footer_legacy.py` — pie legacy en layouts.
3. `scripts/fix_layout_historico_fl.py` — alias `_evaluacion` roto.
4. `scripts/marcar_dimensiones_fecha.py --org N` — tipo `date`.
5. `scripts/backfill_nombre_columnas.py --org N` — pares Nombre/Nombre_Norm.
6. `scripts/fix_lookup_pregunta_pipeline_simce.py` + `scripts/reparar_pregunta_simce_2026.py` — si aplica.

Todos son idempotentes y org-scoped. Los pasos 2–6 **ya se aplicaron** en producción el 2026-07-30.
