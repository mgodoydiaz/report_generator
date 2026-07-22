# Auditoría frontend — Report Generator

Fecha: 2026-07-22 · Rama auditada: `dev3` · Alcance: `frontend/src/App.jsx`, `constants.js`,
`pages/*` (17 páginas), `components/*` (drawers, modales, `PipelineExecutionModal`,
`pipeline-steps/`, `add-component/`, `functions/`, `charts/`, `tables/`), `tooling/`
(`plotly-charts`, `charts` legacy Recharts, `dashboardRenderer`, `dataProcessing`), cruzado
contra los 17 routers de `backend/routers/*.py`.

No se modificó código ni se hicieron operaciones git. Este documento es el único entregable.
Complementa (sin duplicar) `docs/qa/hallazgos/backend.md` y
`docs/qa/hallazgos/ux_usuario_final.md` — varios hallazgos aquí son nuevos y no aparecen en
esos dos documentos (ver hallazgos 1, 2, 3, 4, 5, 8, 9 más abajo).

---

## 1. Mapa de páginas y rutas

`App.jsx:37-67`. 15 rutas protegidas + `/login` pública + `/superadmin` con guard propio.

| Ruta | Componente | En Sidebar | Estado | Notas |
|---|---|---|---|---|
| `/login` | `Login.jsx` | N/A (pública) | **Completa** | Loading/error bien manejados, sin registro (ver `ux_usuario_final.md` #1). |
| `/` | `Home.jsx` | Sí ("Inicio") | **Completa** (trivial) | Landing estática sin CTA ni datos reales. |
| `/execution` | `Execution.jsx` | Sí ("Ejecución") | **Parcial** | Error de API se traga en `console.error`, sin toast; ver Hallazgo 2. |
| `/values` | `Values.jsx` | Sí ("Valores") | **Completa** | CRUD de datos crudos por métrica, import/export, bien cubierto. |
| `/results` | `Results.jsx` | Sí ("Resultados") | **Completa** | Dashboard principal; tiene un `console.log` de debug (Hallazgo 6). |
| `/live-tracking` | `LiveTracking.jsx` | Sí ("Próximos módulos") | **Placeholder intencional** | Ruta llamada "live-tracking" pero renderiza una landing comercial estática de roadmap ("Módulo Noticias", "Panel Profesor", etc.), sin relación con seguimiento en vivo. Ver Hallazgo 9. |
| `/results-recharts` | `ResultsRecharts.jsx` | **No** (huérfana) | **Legacy/duplicada, desactualizada** | Accesible solo por URL directa. Copia antigua e incompleta de `Results.jsx`. Ver Hallazgo 5. |
| `/dimensions` | `Dimensions.jsx` | Sí ("Dimensiones") | **Completa** | |
| `/metrics` | `Metrics.jsx` | Sí ("Métricas") | **Completa** | |
| `/indicators` | `Indicators.jsx` | Sí ("Indicadores") | **Parcial** | Traga errores de API sin avisar al usuario; ver Hallazgo 3. |
| `/functions` | `Functions.jsx` | Sí ("Funciones") | **Parcial (declarado)** | Tab "Funciones derivadas" deshabilitado con badge "Próx." — correctamente comunicado, no es un hallazgo. |
| `/tables` | `Tables.jsx` | Sí ("Tablas") | **Completa** | Catálogo + editor + preview + export pivot. |
| `/charts` | `Charts.jsx` | Sí ("Gráficos") | **Completa** | Catálogo + editor + preview Plotly. |
| `/specs` | `Specs.jsx` | Sí ("Especificaciones") | **Completa** | Único page que sí renderiza su estado `error` (ver Hallazgo 1, contraste). |
| `/pipelines` | `Pipelines.jsx` | Sí ("Procesos") | **Parcial** | Captura `error` de la carga inicial pero nunca lo renderiza; ver Hallazgo 1. |
| `/users` | `Users.jsx` | Sí ("Usuarios") | **Completa** | |
| `/superadmin` | `SuperAdmin.jsx` | No (oculto a propósito, comentario explícito en `Sidebar.jsx:111`) | **Completa** | Guard `SuperAdminGuard` en `App.jsx:26-30` redirige si `!user?.is_superadmin`. |
| `/help` | `Help.jsx` | Sí ("Ayuda") | **Completa pero mal dirigida** | Documentación de props para quien arma dashboards, no para el usuario final (ya cubierto extensamente en `ux_usuario_final.md` Flujo 5, no se repite aquí). |

**Rutas huérfanas**: `/results-recharts` es la única ruta montada en `App.jsx` sin entrada en
`Sidebar.jsx` — accesible solo tecleando la URL. No es un placeholder, es código legacy real
y desactualizado (Hallazgo 5).

---

## 2. Llamadas API frontend ↔ endpoint backend

### 2.1 Endpoints usados correctamente (frontend ↔ backend alineados)

La gran mayoría de las ~90 llamadas API del frontend (ver `grep API_BASE_URL`, 33 archivos)
apuntan a rutas que existen en los routers y con el verbo correcto. Resumen por router:

| Router backend | Endpoints | Consumido desde frontend |
|---|---|---|
| `auth.py` | `/login`, `/me` | `AuthContext.jsx` |
| `users.py` | CRUD completo | `Users.jsx`, `NewUserDrawer.jsx` |
| `superadmin.py` | CRUD orgs/users cross-org | `SuperAdmin.jsx`, `OrgDrawer.jsx`, `SuperUserDrawer.jsx` |
| `dimensions.py` | CRUD + values | `Dimensions.jsx`, `NewDimensionDrawer.jsx`, `NewValueDrawer.jsx`, `Values.jsx` |
| `metrics.py` | CRUD + data + import/export/template | `Metrics.jsx`, `Values.jsx`, `NewMetricDrawer.jsx`, `NewIndicatorDrawer.jsx` |
| `indicators.py` | CRUD + `/export-pdf` + `/export-pdf/engines` | `Indicators.jsx`, `NewIndicatorDrawer.jsx`, `GenerateReportModal.jsx`, `LayoutEditorModal.jsx`, `ResultsRecharts.jsx` |
| `results.py` | `/indicator/{id}/data` | `Results.jsx`, `ResultsRecharts.jsx`, `StepPreview.jsx` |
| `pipelines.py` | CRUD + `/run` `/step` `/input` `/reset` `/upload` `/artifact` | `Pipelines.jsx`, `Execution.jsx`, `PipelineExecutionModal.jsx`, `NewPipelineDrawer.jsx` |
| `specs.py` | CRUD + `/config` + `/duplicate` | `Specs.jsx`, `NewSpecDrawer.jsx` |
| `tables.py` | CRUD + `/preview` + `/data` + `/export-pivot` | `Tables.jsx`, `TableRenderer.jsx`, `LayoutEditorModal.jsx` |
| `charts.py` | CRUD + `/preview` + `/data` + `/types` + `/duplicate` | `Charts.jsx`, `ChartRenderer.jsx`, `LayoutEditorModal.jsx` |
| `mappings.py` | CRUD + `/preview` + `/duplicate` + `/resolved` | `MappingsManager.jsx` |
| `data_ops.py` | `/replace`, `/recalculate` | `BulkOpsManager.jsx` (`/distinct` **no se usa**, ver 2.2) |
| `organizations.py` | `/assets` CRUD + download | `LayoutEditorModal.jsx` (branding assets) |
| `reports.py` | `/{tipo}`, `/word/informes`, `/word/{nombre}` | `GenerateReportV2Modal.jsx`, `GenerateWordReportModal.jsx` |

### 2.2 Desalineaciones y endpoints huérfanos

| Endpoint backend | Método | Usado en frontend | Observación |
|---|---|---|---|
| `/api/api-keys/` | GET/POST/DELETE | **No, ninguna UI** | CRUD completo de API keys para el `ingest` externo, sin ningún drawer/página que lo exponga. Un admin no tiene forma de generar ni revocar una key desde la UI. |
| `/api/ingest/metrics/{id}/data`, `/schema` | POST/GET | **No, ninguna UI** | Endpoint de ingesta externa (probablemente para integraciones futuras); no está documentado en `/help` ni referenciado desde ningún componente. Combinado con el punto anterior, la funcionalidad de "ingesta por API" es inalcanzable desde la UI — ni para usarla ni para generar las credenciales que necesita. |
| `/api/ingest/pipelines/{id}/trigger` | POST | **No, ninguna UI** | Ídem — disparo remoto de pipelines sin UI de gestión. |
| `/api/reports/tipos` | GET | **No** | Docstring del propio backend dice literalmente *"útil para que el frontend ofrezca... en un futuro editor visual"* (`backend/routers/reports.py:47-58`) — nunca se conectó. `GenerateReportV2Modal.jsx` hardcodea sus 3 tipos (`simce`, `simce_panguipulli`, `dia`) en el propio frontend en vez de pedirlos a este endpoint — doble mantención si cambian. |
| `/api/reports/charts` | GET | **No** | Mismo caso — pensado para "selector agregar gráfico" (comentario en el código), nunca conectado. `Charts.jsx` no lo usa, tiene su propio catálogo estático. |
| `/api/reports/tablas` | GET | **No** | Ídem. |
| `/api/reports/word/informes/{nombre}/placeholders` | GET | **No** | `GenerateWordReportModal.jsx` solo llama `/word/informes` (lista) y `POST /word/{nombre}` (generar); nunca pide los placeholders disponibles, aunque el backend los expone — podría usarse para mostrarle al usuario qué campos rellenará la plantilla antes de generar. |
| `/api/indicators/{id}/layout` | POST | **No** | Endpoint dedicado para actualizar solo `dashboard_layout`/`pdf_layout`/`pdf_layout_historico` sin tocar el resto del indicador (ver docstring en `backend/routers/indicators.py:279-281`). `LayoutEditorModal.jsx:1054-1071` en cambio hace un `PUT /indicators/{id}` completo, reenviando manualmente todos los campos (`name`, `description`, `type`, `column_roles`, etc.). Funciona porque el modal sí tiene esos datos cargados, pero el endpoint más seguro (parcial) queda sin usar — riesgo si en el futuro se agrega un campo al indicador y el `PUT` manual del modal no lo incluye, pisando datos sin querer. |
| `/api/data-ops/distinct` | POST | **No** | Solo `/replace` y `/recalculate` se usan desde `BulkOpsManager.jsx`; `/distinct` no tiene consumidor visible. |

**No se encontraron llamadas del frontend a endpoints inexistentes** (los ~90 paths
extraídos calzan 1:1 con rutas declaradas en los routers). El único caso de "endpoint que no
existe" está correctamente evitado con un workaround documentado en el propio código:
`Tables.jsx:90` y `Charts.jsx:76`, comentario *"Evita llamada extra a /api/metrics/{id} que
NO existe en el backend"* — el frontend resuelve las columnas de la métrica desde la lista ya
cargada en memoria en vez de pedir un detalle que no existe.

---

## 3. Hallazgos numerados

### CRÍTICO

**1. Descarga de artefactos de pipeline rota — `window.open` sin token de autenticación.**
`frontend/src/components/PipelineExecutionModal.jsx:101-103`:
```js
const downloadArtifact = (artifactName) => {
    window.open(`${API_BASE_URL}/pipelines/${pipelineId}/artifact/${artifactName}`, '_blank');
};
```
El endpoint `GET /api/pipelines/{id}/artifact/{key}` (`backend/routers/pipelines.py:355-360`)
requiere `Depends(get_current_user)`, que usa `OAuth2PasswordBearer` (`backend/auth.py:42`) —
**solo** lee el header `Authorization: Bearer <token>`, sin fallback por cookie ni por query
param. `window.open()` no puede adjuntar headers custom, así que esta petición siempre viaja
sin token y el backend responde `401 Unauthorized`. El botón "Descargar" (ícono `Download`,
línea 419-432, visible al terminar cualquier pipeline exitosamente) **no descarga nada** — el
usuario ve una pestaña nueva en blanco o un JSON de error, sin ningún toast que lo explique.
Es el paso final de todo pipeline exitoso (subir archivo → ejecutar → **descargar resultado**)
y está roto para cualquier usuario autenticado normal.
Contraste: el botón contiguo "Copiar" (`copyArtifact`, líneas 105-116) sí usa `fetchAuth` y
funciona — es el único workaround disponible hoy, pero solo sirve para contenido de texto
(Excel/CSV vía portapapeles), no para artefactos binarios/PDF.
**Fix sugerido**: reemplazar `window.open` por el mismo patrón `fetchAuth` + `blob` +
`URL.createObjectURL` + `<a download>` que ya usan correctamente `GenerateReportModal.jsx`,
`GenerateWordReportModal.jsx` y `TableRenderer.jsx:handleExportPivotXlsx`.

### ALTO

**2. `Pipelines.jsx` captura el error de carga pero nunca lo muestra — página se ve vacía en vez de fallida.**
`frontend/src/pages/Pipelines.jsx:16` declara `const [error, setError] = useState(null)`,
`fetchPipelines` (líneas 29-41) lo popula en el `catch`, pero **ningún JSX del archivo lee
`error`** (confirmado por grep — la única referencia es la declaración y el `setError`). Si
`GET /api/pipelines` falla (500, red caída, org sin token válido, etc.), la tabla simplemente
renderiza su estado vacío normal: *"No se encontraron procesos."* (línea 385) — indistinguible
de una organización que legítimamente no tiene pipelines. El usuario no tiene ninguna pista de
que hubo un error. Coincide exactamente con el criterio "página que se queda en blanco/engañosa
ante error de API = hallazgo ALTO" de este encargo.
Contraste directo: `Specs.jsx` implementa el mismo patrón (`error` state + `catch`) **y sí lo
renderiza** en un banner (`Specs.jsx:222-224`) — es la referencia correcta a copiar.
**Fix sugerido**: agregar un bloque `{error && <div className="...">{error}</div>}` como en
`Specs.jsx`, o al menos un `toast.error(err.message)` en el catch.

**3. `Indicators.jsx` traga errores de API sin avisar — peor que el caso anterior porque ni siquiera hay `catch` que dispare.**
`frontend/src/pages/Indicators.jsx:25-57`. El fetch usa `.catch(() => ({ ok: false, status: 404 }))`
para no reventar en `Promise.all`, y luego:
```js
let indicatorsData = [];
if (indicatorsRes.ok) { indicatorsData = await indicatorsRes.json(); ... }
```
Si la respuesta no es `ok` (401, 500, timeout — cualquier falla real de servidor), el código
**no lanza excepción**, simplemente deja `indicatorsData` en `[]` y sigue de largo. El `catch`
externo (línea 52-53, que sí hace `toast.error`) nunca se ejecuta en este escenario porque no
hay ningún `throw`. Resultado: ante un error real de backend, `/indicators` se ve exactamente
igual que una organización sin indicadores configurados — sin toast, sin log, sin ninguna señal.
**Fix sugerido**: si `!indicatorsRes.ok`, lanzar explícitamente `throw new Error(...)` para que
el catch externo sí dispare el toast, en vez de degradar silenciosamente a lista vacía.

**4. Manejo de token expirado inconsistente — 5 archivos reimplementan su propio cliente HTTP sin logout automático.**
`AuthContext.jsx:57-77` expone `fetchAuth`, que en un `401` llama `logout()` automáticamente
(borra el token y fuerza a `ProtectedRoute` a redirigir a `/login` en el siguiente render). Sin
embargo, estos archivos **no usan `fetchAuth`** — leen `rg_token` de `localStorage` directamente
y arman su propio `fetch` con headers manuales:
- `frontend/src/pages/Tables.jsx:976-1012` (`apiGet/apiPost/apiPut/apiDelete`)
- `frontend/src/pages/Charts.jsx:809-843` (mismas 4 funciones duplicadas)
- `frontend/src/components/functions/MappingsManager.jsx:646-680` (idem)
- `frontend/src/components/functions/BulkOpsManager.jsx:432-448` (idem, 2 de las 4)
- `frontend/src/components/charts/ChartRenderer.jsx:66-85`

En los 4 primeros, un `401` simplemente lanza `Error("HTTP 401")`, que el caller atrapa y
muestra como `toast.error('HTTP 401: ...')` — **sin cerrar sesión ni redirigir**. El usuario
con token vencido se queda en `/tables` o `/charts` viendo errores 401 repetidos en cada acción
(guardar, previsualizar, exportar) sin entender que debe volver a iniciar sesión, mientras que
en el resto de la app (`Pipelines`, `Dimensions`, `Metrics`, `Results`, etc., que sí usan
`fetchAuth`) la sesión expirada los saca a `/login` limpiamente.
**Fix sugerido**: eliminar las 4 implementaciones locales de `apiGet/apiPost/apiPut/apiDelete`
y reemplazarlas por `useAuth().fetchAuth`, igual que el resto de la app. Es además ~120 líneas
de código duplicado idéntico entre `Tables.jsx`, `Charts.jsx` y `MappingsManager.jsx`.

**5. `/results-recharts` — ruta huérfana que sirve una copia legacy y desactualizada de `Results.jsx`, con un bug ya corregido en la versión vigente.**
`ResultsRecharts.jsx` (308 líneas) no está enlazada en `Sidebar.jsx` pero sigue montada en
`App.jsx:53` y accesible por URL directa. El diff contra `Results.jsx` muestra que es una
versión anterior del mismo dashboard:
- Le faltan los 3 modales de exportación (`GenerateReportModal`, `GenerateReportV2Modal`,
  `GenerateWordReportModal`) y `MultiSelectFilters` — no están importados.
- Le falta el manejo de `derived_columns` del indicador.
- El `useEffect` de carga de dimensiones depende de `[selectedIndicator, indicators]`
  (`ResultsRecharts.jsx:73`), el mismo patrón que el comentario en `Results.jsx:121` señala
  explícitamente como causa de un bug ya resuelto: *"← SIN indicators en dependencias para
  evitar loop infinito"*. La corrección se aplicó solo en `Results.jsx`; `ResultsRecharts.jsx`
  conserva el patrón original.
- El único botón de exportación que sí tiene (`ResultsRecharts.jsx:84`, `export-pdf` directo)
  no pasa por ningún modal de configuración (branding, engine, tipo histórico/evaluación).
Cualquier usuario que llegue a esta URL (favorito viejo, link compartido, buscador interno)
ve una versión inferior y potencialmente inestable del dashboard principal.
**Fix sugerido**: eliminar la ruta y el archivo, o si se mantiene por alguna razón, al menos
aplicarle el mismo fix de dependencias que a `Results.jsx` para no exponer el bug conocido.

### MEDIO

**6. `console.log` de debug expuesto en producción.** `frontend/src/pages/Results.jsx:106`:
`console.log('[Results] dashboard_layout recibido del servidor:', JSON.stringify(layout, null, 2));`
precedido del comentario *"DEBUG — quitar cuando se confirme que el layout llega correcto"*.
Se dispara en cada cambio de indicador seleccionado, para todo usuario, en producción. (También
señalado en `ux_usuario_final.md` Flujo 3 — se repite aquí solo para el índice de archivo:línea.)
**Fix sugerido**: borrar la línea.

**7. Mezcla de voseo y tuteo/usted — inconsistente para una audiencia chilena (Fundación PHP).**
La mayoría de la app usa tuteo neutro/usted ("Ingrese con su cuenta", "Estás seguro de
eliminar..."), pero aparecen fragmentos en voseo rioplatense:
- `frontend/src/pages/LiveTracking.jsx:172`: *"Hacé click en cada uno para ver la propuesta."*
- `frontend/src/pages/LiveTracking.jsx:200`: *"¿Falta algún módulo? Lo agregamos al roadmap."* (tono correcto, pero el resto del bloque no es consistente con el resto de la app)
- `frontend/src/pages/Help.jsx:383`: *"...o pedile a tu administrador acceso al material extendido."*
- `frontend/src/pages/Charts.jsx:565`: *"Verificá que los nombres coincidan."*
Un colegio chileno no usa "vos"/"hacé"/"pedile"/"verificá" — lee como redactado por otra
persona o pegado de otra fuente sin revisar. No es solo jerga técnica (ya cubierto en
`ux_usuario_final.md`), es una inconsistencia de variante del español.
**Fix sugerido**: pasar esos 4 strings a la misma variante (tú/usted) que el resto de la app.

**8. Defaults hardcodeados con nombre de persona y de comuna específica en el modal de reporte v2.**
`frontend/src/components/GenerateReportV2Modal.jsx:38-57` — objeto `defaultsByTipo`:
```js
simce: { ..., autor: 'Miguel Godoy Díaz' },
simce_panguipulli: { line1: 'Informe SIMCE Panguipulli', ... autor: 'Miguel Godoy Díaz' },
dia: { ..., autor: 'Miguel Godoy Díaz' },
```
El autor por defecto de **cualquier** informe v2, para **cualquier** organización, es el
nombre del dueño/desarrollador único del sistema, y uno de los tres tipos de informe tiene
como título por defecto una comuna específica ("Panguipulli") en vez de un placeholder
genérico. Si un operador de otra fundación/colegio genera el informe sin editar estos campos
(el modal permite generar sin tocarlos), el PDF entregado a un cliente real queda con el
nombre de Miguel Godoy como autor y/o el nombre de otra comuna en el encabezado. El mismo
hardcode de "Panguipulli" existe también en el backend (`backend/routers/reports.py:56`, fuera
de alcance de este documento) — confirma que no es un placeholder de ejemplo sino un valor real
que quedó fijado en el código de dos capas.
**Fix sugerido**: usar el nombre de la organización actual (`user.org_id` → nombre real) y un
título genérico ("Informe SIMCE") como default, dejando "Panguipulli"/autor específico solo
como valor guardado en `localStorage` la primera vez que alguien de esa fundación lo edite.

### BAJO

**9. `/live-tracking`: nombre de ruta no coincide con el contenido.** La URL y el nombre del
componente (`LiveTracking.jsx`) sugieren seguimiento en vivo de ejecuciones de pipeline, pero
el archivo es, según su propio comentario de cabecera, un *"'Próximos módulos' — landing
comercial. Placeholder. Sin lógica activa."* (líneas 7-12) con 4 tarjetas de roadmap
("Módulo Noticias", "Módulo Estudiantes", "Panel Profesor", "Seguimiento Cobertura
Curricular"). El sidebar sí lo etiqueta correctamente ("Próximos módulos"), pero la URL/nombre
de archivo quedará confundiendo a cualquier desarrollador nuevo que busque la feature de
tracking en tiempo real. No es un bug para el usuario (el label del menú es correcto), es
deuda de nomenclatura.
**Fix sugerido**: renombrar ruta/archivo a `/roadmap` o `Roadmap.jsx` en el próximo refactor.

**10. Componente `UnderConstruction.jsx` sin ningún uso — código muerto.**
`frontend/src/components/UnderConstruction.jsx` define y exporta un componente que no se
importa desde ningún otro archivo del proyecto (`grep -rn "UnderConstruction" frontend/src`
solo devuelve su propia declaración).
**Fix sugerido**: eliminarlo, o si se pensaba usar para `/live-tracking`, usarlo ahí en vez de
la implementación ad-hoc actual.

**11. Bundle carga el paquete completo `recharts` (^3.8.0) solo para la página de documentación `/help`.**
Los 9 componentes legacy en `frontend/src/tooling/charts/*.jsx` (`GraficoLogroPorCurso`,
`GraficoBoxplotPorCurso`, etc.) importan directamente de `recharts`. Se confirmó que **ningún
dashboard real los monta** — el único importador fuera de `tooling/charts/index.js` es
`pages/Help.jsx` (galería de referencia). Es decir, la migración a Plotly (`tooling/plotly-charts`)
está funcionalmente completa en producción, pero el bundle sigue enviando la librería Recharts
completa al navegador de cada usuario únicamente para que la vea quien visita `/help`.
**Fix sugerido**: mover la sección "Gráficos/Tablas Legacy" de `Help.jsx` a un `React.lazy()` +
`Suspense`, o eliminarla si ya no aporta valor de referencia, para que `recharts` salga del
bundle principal.

**12. Endpoints backend sin ninguna UI — funcionalidad inalcanzable para el usuario.**
Ver tabla completa en sección 2.2. Resumen: gestión de API keys (`/api/api-keys`), ingesta
externa (`/api/ingest/*`) y los 3 endpoints de introspección de `reports.py` (`/tipos`,
`/charts`, `/tablas`) que el propio código backend documenta como pensados para el frontend
pero nunca se conectaron.

---

## 4. Guiones de QA manual sugeridos

### Guion A — Ejecutar un pipeline y descargar el resultado (valida Hallazgo 1)
1. Login con un usuario con al menos un pipeline configurado.
2. Ir a `/execution`, elegir un pipeline con salida `EXCEL` o `PDF`, click "Ejecutar Proceso".
3. Completar el flujo hasta `status === 'success'`.
4. En la lista de "Artefactos Generados", click en el ícono de descarga (nube/flecha hacia
   abajo) de cualquier artefacto.
5. **Esperado si el bug persiste**: se abre una pestaña nueva en blanco o con un JSON
   `{"detail":"Not authenticated"}`, no se descarga ningún archivo.
6. Como contraste, probar el ícono "Copiar" del mismo artefacto — debería funcionar y copiar
   el contenido al portapapeles.

### Guion B — Simular sesión expirada en `/tables` y `/charts` (valida Hallazgo 4)
1. Login normal, ir a `/tables`.
2. En devtools → Application → Local Storage, editar `rg_token` a un string inválido
   (o esperar a que el JWT real expire).
3. Intentar guardar una tabla nueva o cargar el preview de una existente.
4. **Esperado si el bug persiste**: aparece un toast "HTTP 401: ..." pero la app NO redirige a
   `/login` ni limpia la sesión — el usuario queda atascado repitiendo el error.
5. Repetir el mismo test en `/dimensions` o `/metrics` (que sí usan `fetchAuth`) para
   contrastar: ahí sí debería expulsar a `/login` limpiamente.

### Guion C — Provocar un error de servidor en listados (valida Hallazgos 2 y 3)
1. Con el backend corriendo, cortar la conexión a la base de datos (o detener el contenedor
   Postgres local) sin detener el backend, o bloquear temporalmente la ruta `/api/pipelines`
   vía proxy/devtools (Network → Block request URL).
2. Navegar a `/pipelines`. **Esperado si el bug persiste**: se ve "No se encontraron procesos"
   sin ningún indicio de error, igual que una organización sin pipelines.
3. Repetir bloqueando `/api/indicators` y navegar a `/indicators`. **Esperado si el bug
   persiste**: tabla vacía, "No hay indicadores registrados.", sin toast ni consola.
4. Repetir bloqueando `/api/specs` y navegar a `/specs` como control positivo: debería
   aparecer un banner de error visible (comportamiento correcto a preservar).

### Guion D — Recorrer `/results-recharts` vs `/results` (valida Hallazgo 5)
1. Con datos ya cargados en una organización, abrir `/results` y seleccionar un indicador con
   varios puntos temporales (para poder alternar filtros varias veces seguidas rápido).
2. Repetir la misma navegación en `/results-recharts` (URL directa).
3. Comparar: verificar que en `/results-recharts` no aparecen los botones de exportación
   Word/PDF v2, y alternar el indicador seleccionado varias veces rápido para intentar
   reproducir loops de refetch (Network tab: contar llamadas a
   `/api/results/indicator/.../data` por cada cambio — no debería haber más de 1-2 por click).

### Guion E — Revisión de tono/idioma (valida Hallazgo 7)
1. Recorrer `/help` (sección "Guías de uso"), `/live-tracking` completo (expandir las 4
   tarjetas) y `/charts` intentando guardar un gráfico de tipo `stack_order` con un nombre de
   nivel que no calce con el indicador (para disparar el toast de error de Charts.jsx:565).
2. Confirmar en cada pantalla si el texto usa "vos/hacé/pedile/verificá" (voseo) o
   "tú-usted/haz/pídele/verifica" (resto de la app) y anotar inconsistencias adicionales no
   cubiertas en este informe.

### Guion F — Generar informe v2 sin editar los defaults (valida Hallazgo 8)
1. Ir a `/results`, seleccionar un indicador de tipo SIMCE (o cuyo `id`/nombre matchee
   `simce_panguipulli` según la lógica de habilitación en `Results.jsx`), click en el botón
   de generación v2.
2. Sin editar ningún campo del modal, generar y descargar el PDF.
3. Verificar el encabezado y pie del PDF resultante: si el bug persiste, aparecerá
   "Miguel Godoy Díaz" como autor y/o "Informe SIMCE Panguipulli" como título, sin relación
   con la organización real que generó el informe.
