# QA UX — Recorrido de un usuario final no-técnico (Fundación PHP)

**Fecha**: 2026-07-22
**Rama revisada**: `dev3`
**Método**: lectura de código (frontend `frontend/src/`, backend `backend/`), sin ejecutar la app. Simulación mental del recorrido de un profesor/administrativo de una fundación educacional que **no sabe programar**, sin ayuda de Miguel.

**Contexto declarado por el dueño**: "estoy casi seguro que nos falta mucho para que un usuario pueda ver las cosas". Este informe confirma esa sospecha y la cuantifica.

---

## 1. Resumen — veredicto por flujo

| # | Flujo | Veredicto | Motivo principal |
|---|---|---|---|
| 1 | Onboarding (cuenta nueva) | **BLOQUEADO** | No existe registro ni invitación. Todo pasa por CLI o panel `/superadmin` operado por Miguel. |
| 2 | Primer dato (subir archivo + ejecutar pipeline) | **BLOQUEADO** | El pipeline debe construirlo Miguel a mano en JSON; si el ETL falla, el usuario ve "Error interno del servidor" sin ninguna pista. |
| 3 | Ver resultados (`/results`) | **BLOQUEADO** (org nueva) / **CON FRICCIÓN** (org ya configurada) | Sin indicadores previamente configurados, el selector queda vacío y el mensaje de ayuda es engañoso ("Selecciona un indicador" sin decir que no hay ninguno). |
| 4 | Descargar informe PDF/Word | **CON FRICCIÓN** | Funciona bien una vez configurado, pero requiere que Miguel haya armado el "Editor de Layout" antes; hay 3 botones de descarga distintos con jerga ("motor v1/v2", "weasyprint") sin explicación. |
| 5 | Ayuda (`/help`) | **BLOQUEADO** para el usuario final | La página `/help` es documentación de API para quien construye dashboards (JSON, `groupField`, `entity_field`, "kind: piecewise_linear"). No hay ni una guía de "cómo veo mis resultados" o "cómo descargo mi informe". |
| 6 | Estados vacíos (org nueva) | **CRÍTICO** | Prácticamente toda la app depende de datos org-scoped que no existen al crear una organización: 0 pipelines, 0 indicadores, 0 specs, 0 métricas. Algunos vacíos están bien resueltos, otros inducen a error. |
| 7 | Idioma y tono | **CON FRICCIÓN generalizada** | El menú lateral y algunas pantallas están bien traducidas; pero pipelines, `/help`, mensajes de "motor de informe" y nombres de step en ejecución exponen jerga de desarrollador (JSON, DataFrame, step, params, engine). |

---

## 2. Los 7 flujos con evidencia

### Flujo 1 — Onboarding
**BLOQUEADO** para cualquier persona fuera de Miguel.

- No hay ruta `/register`, `/signup` ni "olvidé mi contraseña" en el frontend: `frontend/src/App.jsx:37-67` solo define `/login` como ruta pública; `frontend/src/pages/Login.jsx:39-123` no tiene ningún link de registro/recuperación.
- Backend: `backend/routers/auth.py:60-105` solo expone `/api/auth/login` y `/api/auth/me`. No existe endpoint de registro ni de reset de contraseña (`grep` sobre `backend/` no encontró rutas de invitación/recuperación).
- Crear la **primera organización y el primer superadmin** solo es posible por CLI: `backend/cli.py:20-58` (`create-superadmin`, prompts interactivos por terminal) y `backend/cli.py:61-85` (`create-org`).
- Crear organizaciones y usuarios adicionales día a día sí tiene UI, pero exclusivamente para superadmin en `/superadmin` (`frontend/src/pages/SuperAdmin.jsx:159-162`, `backend/routers/superadmin.py:97-303`).
- Una vez que el admin de una organización existe, ese admin **sí puede** crear usuarios de su propia org desde `/users` (`frontend/src/pages/Users.jsx:121-129`, `frontend/src/components/NewUserDrawer.jsx`). Pero la contraseña la fija el admin manualmente en un campo de texto (`NewUserDrawer.jsx:44,57-58`) — no hay invitación por correo ni cambio de contraseña forzado en el primer login.

### Flujo 2 — Primer dato (subir archivo + ejecutar pipeline)
**BLOQUEADO** en la práctica.

- Construir un pipeline nuevo obliga a editar JSON crudo en un editor de código con resaltado de sintaxis: `frontend/src/components/NewPipelineDrawer.jsx:446-467` (campo "Parámetros" = `react-simple-code-editor` con `highlight(code, languages.json)`). No hay wizard ni plantillas premontadas visibles para el usuario final.
- Cada organización parte con **cero pipelines** (tabla `pipelines` tiene `org_id` obligatorio, `backend/models.py:86`) — Miguel debe construir o copiar el pipeline por cada fundación/evaluación antes de que un usuario pueda hacer nada.
- **Errores de ejecución son opacos**: cualquier excepción de un step (columna faltante, archivo con formato incorrecto, hoja Excel mal armada) se relanza en `backend/rgenerator/tooling/pipeline_tools.py:149-151` (`except Exception as e: ... raise e`) y llega al router, que la captura genéricamente y devuelve siempre el mismo mensaje sin detalle:
  - `backend/routers/pipelines.py:249-252` (`/run`), `:302-304` (`/input`), `:339-342` (`/step`) → `return {"error": "Error interno del servidor"}`.
  - El detalle real (ej. `"[EnrichWithLookup] Columna llave 'RUT' no existe en 'estudiantes'."`, ver `backend/rgenerator/core/etl_steps.py:730-742`) queda solo en el log del servidor (`logger.error(..., exc_info=True)`), invisible para el usuario.
  - El frontend muestra ese string genérico tal cual: `frontend/src/components/PipelineExecutionModal.jsx:441-449` (`<p>{error}</p>`).
  - Consecuencia: frente a cualquier error real de ETL (muy probable con archivos Excel de colegios, encabezados corridos, columnas renombradas), el usuario no tiene ninguna pista de qué falló ni qué corregir. Su única opción es escribirle a Miguel.
- El paso de subir archivos (`RequestUserFiles`) en sí está bien resuelto para un usuario no técnico: drag & drop claro, en español, con estado "Listo" (`frontend/src/components/pipeline-steps/RequestUserFiles.jsx:45-120`). El problema no es esa pantalla, es todo lo que la rodea.
- Durante la ejecución, el modal muestra el nombre crudo de la clase Python del step en curso en vez de su traducción: `PipelineExecutionModal.jsx:378` → `` `Paso actual: ${currentStepData.step}` `` (ej. "RunExcelETL"), mientras que `GenericStep.jsx:10` sí usa `STEP_TRANSLATIONS`.

### Flujo 3 — Ver resultados (`/results`)
**BLOQUEADO** en una org nueva, **CON FRICCIÓN** en una ya configurada.

- Igual que pipelines, indicadores son 100% org-scoped (`backend/models.py:223`) — una org nueva parte con el selector "Indicador" vacío.
- El estado vacío es engañoso: cuando no hay indicador seleccionado, `frontend/src/pages/Results.jsx:454-464` siempre muestra *"Selecciona un indicador... Elige un indicador para visualizar su dashboard"* — el mismo mensaje se ve tanto si hay 20 indicadores disponibles como si hay 0. Un usuario de una org recién creada ve un `<select>` con una sola opción ("Seleccionar indicador...") y ningún indicio de que su organización aún no tiene nada configurado ni a quién pedírselo.
- Un `console.log` de debug quedó en producción: `Results.jsx:106` (`console.log('[Results] dashboard_layout recibido del servidor:', ...)`) — no es un bloqueo para el usuario, pero es ruido/deuda técnica visible en devtools.
- Una vez con datos, los filtros (`MultiSelectFilters`) y el dashboard renderizado están razonablemente bien resueltos y en español.

### Flujo 4 — Descargar informe PDF/Word
**CON FRICCIÓN.**

- Tres botones de descarga coexisten en la misma barra (`Results.jsx:307-410`): "Generar Reporte" (motor v1/weasyprint), "Generar v2 (SIMCE/DIA)" (solo visible para indicadores cuyo nombre contiene "simce"/"dia", vía matching de string en `Results.jsx:329-332`) y "Word". Cada uno tiene reglas de habilitación distintas explicadas solo en el `title` (tooltip) con lenguaje técnico: *"El motor v2 requiere UN solo punto temporal..."*, *"Generar informe Word (.docx editable) desde plantilla con códigos {{valor}}"* (`Results.jsx:356-359`, `Results.jsx:403`). Un usuario no técnico no tiene forma de saber cuál botón usar ni por qué el v2 a veces está deshabilitado.
- El botón "Generar Reporte" (v1) queda deshabilitado si el indicador no tiene `pdf_layout.sections` configuradas, con el mensaje: *"Configura el informe PDF en el Editor de Layout → pestaña Informe PDF"* (`Results.jsx:312-316`) — acción que un usuario final no puede realizar (es configuración de administrador de contenido, con JSON de por medio).
- Cuando sí está configurado, el modal de generación (`frontend/src/components/GenerateReportModal.jsx`) funciona razonablemente bien: propaga el `detail` del backend en caso de error (`GenerateReportModal.jsx:154-160`) y descarga el PDF directamente. Pero expone selects de "Motor del informe" con nombres de librería ("weasyprint") sin explicar qué significan (`GenerateReportModal.jsx:264-292`).

### Flujo 5 — Ayuda (`/help`)
**BLOQUEADO** para autoservicio de un usuario final.

- Toda la página `/help` (`frontend/src/pages/Help.jsx`, ~950 líneas) es documentación de referencia para quien **configura** dashboards/pipelines (probablemente Miguel u otro admin técnico), no para quien **usa** los reportes:
  - Guía "Crear y ejecutar un pipeline" explica literalmente estructura JSON: `{ workflow_metadata, context, pipeline: [{ step, params }, ...] }` y nombres de step (`InitRun`, `RequestUserFiles`, `RunExcelETL`, `SaveToMetric`) — `Help.jsx:386-398`.
  - Guía "Funciones derivadas" habla de `derived_columns`, `kind: agg/slope/delta`, `entity_field`, `time_field` — `Help.jsx:426-437`.
  - El resto de la página (>500 líneas) es un catálogo de componentes de gráficos/tablas con nombres de props (`groupField`, `valueField`, `dimensionField`) — útil para un desarrollador de dashboards, inútil para un profesor que solo quiere ver el resultado de su colegio.
- No existe ninguna sección tipo FAQ, glosario en lenguaje simple, ni guía de "cómo veo el dashboard de mi colegio" o "cómo descargo el PDF". La única mención a soporte adicional es un aviso que redirige a "documentación técnica en `docs/` o pedile a tu administrador acceso al material extendido" (`Help.jsx:382-384`) — que tampoco resuelve nada para el usuario final.

### Flujo 6 — Estados vacíos (org recién creada)
**CRÍTICO**, aunque parcialmente mitigado en algunas pantallas.

- Página `/` (Home): mensaje de bienvenida genérico sin ningún CTA orientador ("usa el menú lateral para navegar entre pipelines, resultados y configuración" — `frontend/src/pages/Home.jsx:17`). No detecta ni comunica que la organización no tiene nada configurado.
- `/execution`: si no hay pipelines (o todos ocultos), muestra *"No se encontraron procesos / Prueba con otros términos de búsqueda"* (`frontend/src/pages/Execution.jsx:164-169`) — mensaje pensado para una búsqueda sin resultados, no para el caso real de "esta organización no tiene ningún proceso todavía". Induce al usuario a pensar que su búsqueda está mal, cuando el problema es que no hay nada que buscar.
- `/results`: igual problema, descrito en Flujo 3.
- `/indicators`, `/dimensions`, `/metrics`: sí tienen mensajes de vacío correctos y directos ("No hay indicadores registrados.", "No hay dimensiones registradas.", "No hay métricas registradas." — `Indicators.jsx:258`, `Dimensions.jsx:189`, `Metrics.jsx:219`), aunque estas páginas son de configuración técnica, no las que un usuario final visitaría.
- En conjunto: una organización nueva, recién creada por Miguel, aterriza a su primer usuario en una app donde casi todas las pantallas relevantes (Ejecución, Resultados) están vacías sin explicación clara de *por qué* ni *qué hacer al respecto* ("contacta a tu administrador para que configure tu primer proceso", por ejemplo, no existe en ningún lado).

### Flujo 7 — Idioma y tono
**CON FRICCIÓN generalizada**, mixto.

- Positivo: el menú lateral (`frontend/src/layouts/Sidebar.jsx:42-109`) usa buena traducción de dominio ("Procesos" en vez de "Pipelines", "Ejecución", "Valores", "Resultados"), y pantallas orientadas al usuario final como `RequestUserFiles.jsx` y `Login.jsx` están en español simple.
- Negativo — jerga de desarrollador visible en superficies que un usuario final sí puede tocar:
  - Nombres de step en inglés/CamelCase durante ejecución (`Paso actual: RunExcelETL`, `PipelineExecutionModal.jsx:378`).
  - Traducciones incompletas: `STEP_TRANSLATIONS["LoadMetricToDF"] = "Cargar Métrica como DataFrame"` (sigue con "DataFrame", término de pandas) — `frontend/src/constants.js:44`.
  - "Motor del informe" con opciones como "weasyprint" (`GenerateReportModal.jsx:269-286`).
  - Tooltips con jerga técnica de configuración ("Editor de Layout → pestaña Informe PDF", "motor v1", "motor v2 (paridad LaTeX)", "backend lo maneja" — `Results.jsx:312-316, 355-359`).
  - Toda la página `/help` (ver Flujo 5).
  - JSON crudo visible y editable en `/pipelines` (`NewPipelineDrawer.jsx`).

---

## 3. Hallazgos numerados con severidad

1. **[CRÍTICO]** No existe registro ni invitación de organizaciones/usuarios. Todo el onboarding pasa por CLI (`backend/cli.py`) o por el panel `/superadmin`, operado exclusivamente por Miguel. Sin workaround para el usuario final. — `backend/cli.py:20-85`, `backend/routers/auth.py:60-105`, `frontend/src/App.jsx:39`.
2. **[CRÍTICO]** Los errores de ejecución de pipeline se colapsan siempre al mensaje genérico "Error interno del servidor", perdiendo el mensaje específico y accionable que el step sí generó (ej. columna faltante). El usuario no puede autodiagnosticar ni un error trivial (archivo con la hoja equivocada, columna renombrada). — `backend/routers/pipelines.py:249-252,302-304,339-342`, `backend/rgenerator/tooling/pipeline_tools.py:149-151`.
3. **[CRÍTICO]** Crear/editar un pipeline requiere escribir JSON a mano en un editor de código (`NewPipelineDrawer.jsx`). No hay wizard, plantilla guiada, ni asistente para no-técnicos. Como cada pipeline es por organización (`org_id` obligatorio), Miguel debe construir manualmente el pipeline de cada evaluación para cada fundación antes de que cualquier usuario pueda subir un archivo. — `frontend/src/components/NewPipelineDrawer.jsx:446-467`, `backend/models.py:86`.
4. **[CRÍTICO]** La página `/help` es documentación de referencia técnica (JSON, props de componentes, `derived_columns`, `entity_field`) para quien configura dashboards, no una ayuda de autoservicio para el usuario final. No existe ninguna guía en lenguaje simple de "cómo veo mis resultados" o "cómo descargo mi informe". — `frontend/src/pages/Help.jsx` (completo).
5. **[CRÍTICO]** Los estados vacíos de `/execution` y `/results` en una organización sin datos configurados usan copy de "sin resultados de búsqueda" en vez de explicar que la organización aún no tiene nada configurado y qué hacer al respecto. — `frontend/src/pages/Execution.jsx:164-169`, `frontend/src/pages/Results.jsx:454-464`.
6. **[ALTO]** El botón de descarga de PDF (motor v1) se deshabilita si el indicador no tiene `pdf_layout.sections`, indicando al usuario que vaya al "Editor de Layout" — una tarea de configuración técnica que el usuario final no puede completar por sí mismo. — `frontend/src/pages/Results.jsx:225-230,312-316`.
7. **[ALTO]** Coexisten 3 botones de generación de informe (v1, v2, Word) con reglas de habilitación distintas explicadas solo en tooltips con jerga ("motor v2 requiere un solo punto temporal", "paridad LaTeX", "weasyprint"). Alto riesgo de que el usuario no sepa cuál usar. — `frontend/src/pages/Results.jsx:307-410`.
8. **[MEDIO]** Alta de usuarios: el admin de la organización fija la contraseña manualmente en un campo de texto; no hay invitación por correo ni cambio de contraseña obligatorio en el primer login. Funciona, pero exige que el admin comunique la clave por un canal externo (WhatsApp, papel, etc.), con el riesgo de higiene de credenciales que eso implica. — `frontend/src/components/NewUserDrawer.jsx:44,57-58`.
9. **[MEDIO]** Durante la ejecución del pipeline se muestra el nombre crudo de la clase del step actual ("RunExcelETL") en vez de su traducción a español, inconsistente con el resto del modal que sí traduce. — `frontend/src/components/PipelineExecutionModal.jsx:378` vs `GenericStep.jsx:10`.
10. **[BAJO]** Traducciones de step incompletas conservan jerga técnica ("Cargar Métrica como DataFrame"). — `frontend/src/constants.js:44`.
11. **[BAJO]** `console.log` de debug dejado en producción en `/results` (ruido en devtools, no afecta al usuario pero es deuda técnica). — `frontend/src/pages/Results.jsx:106`.

---

## 4. Camino mínimo a demo-able

Orden priorizado de lo indispensable para que **un usuario real de la fundación use el producto sin acompañamiento de Miguel**, aunque sea para una sola organización piloto:

1. **Arreglar el mensaje de error de pipelines** (hallazgo 2): al menos propagar el `str(e)` de la excepción del step (ya existe y es razonablemente legible, ej. "Columna llave 'RUT' no existe en 'estudiantes'") en vez de aplastarlo a "Error interno del servidor". Esto es la diferencia entre que el usuario pueda corregir su Excel solo o tenga que escribirle a Miguel cada vez.
2. **Preconfigurar completamente** (por Miguel, fuera de la UI actual, vía scripts existentes en `scripts/db_seed.py`/`scripts/_oneshot/`) los pipelines, indicadores, dimensiones y layouts PDF de la organización piloto **antes** de dar acceso al usuario — hoy es obligatorio porque no hay wizard, así que hay que asumirlo como paso operativo, no arreglarlo en código para la demo.
3. **Reescribir los estados vacíos** de `/execution`, `/results` y `Home` para el caso "esta organización todavía no tiene nada configurado" (mensaje claro + a quién contactar), en vez del copy de "sin resultados de búsqueda". Bajo costo, alto impacto en la primera impresión.
4. **Simplificar el flujo de descarga de informe**: unificar a un único botón claro por defecto (ocultar v2/engine picker si solo hay un layout disponible), y traducir el tooltip de "requiere Editor de Layout" a algo accionable ("Este informe aún no está configurado — pide a tu administrador que lo active").
5. **Crear una página de ayuda real para el usuario final** (separada de la actual, que puede quedar como "Ayuda avanzada" para admins): 3-4 pasos con capturas — cómo entrar, cómo elegir un indicador y filtrar, cómo descargar el PDF/Word.
6. **(Recomendado, no bloqueante para demo)** Flujo de invitación por correo con set-password propio, para no depender de que el admin comunique contraseñas manualmente.

## 5. Ideas rápidas (quick wins, <1 día c/u)

- Traducir `currentStepData.step` con `STEP_TRANSLATIONS` también en el header de "Ejecutando..." del modal de ejecución (`PipelineExecutionModal.jsx:378`), igual que ya hace `GenericStep.jsx`.
- Cambiar el copy de estado vacío en `/execution` para distinguir "sin resultados de tu búsqueda" (cuando hay `busqueda` no vacía) de "esta organización aún no tiene procesos configurados" (cuando `pipelines.length === 0` sin búsqueda) — mismo patch aplicable a `/results`.
- Eliminar el `console.log` de debug en `Results.jsx:106`.
- En `GenerateReportModal.jsx`, renombrar el select "Motor del informe" a algo como "Formato del informe" y ocultar nombres de librería (weasyprint) del label visible, dejándolos solo como valor interno.
- Agregar al mensaje de "Error interno del servidor" del pipeline un texto fijo de ayuda ("Revisa que el archivo tenga el formato esperado. Si el problema persiste, contacta a tu administrador con la fecha y hora de este intento") — mitiga el hallazgo 2 sin tocar la lógica de excepciones.
- En el Home (`Home.jsx`), agregar un CTA condicional simple: si el usuario no tiene indicadores/pipelines visibles, mostrar un aviso "Tu organización aún no tiene datos configurados — contacta a tu administrador" en vez del texto genérico fijo.
