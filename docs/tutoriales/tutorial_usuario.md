# Tutorial de usuario — Report Generator

Guía paso a paso para el personal de Fundación PHP que usa la aplicación web de Report Generator: subir los resultados de una evaluación, revisar el dashboard y descargar el informe final.

## A quién está dirigido

A cualquier persona de la fundación que necesite cargar datos de una evaluación (SIMCE, DIA, IDEL, u otra), revisar los resultados en pantalla y descargar el informe en PDF o Word. No se requieren conocimientos técnicos.

## Requisitos antes de empezar

- Un usuario y contraseña de acceso a la plataforma (los entrega el administrador de tu organización).
- El archivo de resultados de la evaluación en Excel (o CSV), tal como lo entrega la agencia evaluadora o el colegio.
- Un navegador web actualizado (Chrome, Edge o Firefox).

> 💡 Si no tienes usuario todavía, pídeselo a la persona administradora de tu organización dentro de la plataforma.

## Índice

1. [Parte 1 — Subir los datos con el formato requerido](#parte-1--subir-los-datos-con-el-formato-requerido)
2. [Parte 2 — Ver el dashboard](#parte-2--ver-el-dashboard)
3. [Parte 3 — Descargar el informe](#parte-3--descargar-el-informe)
4. [Problemas frecuentes](#problemas-frecuentes)

---

## Parte 1 — Subir los datos con el formato requerido

### Paso 1: Ingresa a la plataforma

1. Abre la aplicación en tu navegador e inicia sesión con tu correo y contraseña.

![Captura: pantalla de inicio de sesión](pendiente)

### Paso 2: Ve a la sección "Pipelines"

1. En el menú lateral, haz clic en **Pipelines**. Ahí aparece la lista de procesos de carga configurados para tu organización (por ejemplo, "SIMCE Lenguaje", "DIA Matemáticas", "IDEL", etc.).
2. Busca el proceso que corresponde a la evaluación que quieres cargar y haz clic en el botón con el ícono de **Play** ("Ejecutar") en su fila.

![Captura: listado de pipelines con el botón Ejecutar](pendiente)

> 💡 Cada evaluación (SIMCE, DIA, IDEL...) tiene su propio proceso de carga, ya configurado por el equipo técnico. Tú solo necesitas ejecutarlo y entregar los archivos que te pida.

### Paso 3: Sigue el asistente paso a paso

Al ejecutar el proceso se abre una ventana con el progreso dividido en pasos numerados (un círculo por paso, a la izquierda). El sistema avanza pidiéndote información a medida que la necesita, y se detiene ("pausa") cuando requiere que tú entregues un archivo o completes un dato.

1. Haz clic en **Siguiente** para avanzar de a un paso, o en **Ejecutar Todo** para que el sistema corra automáticamente todos los pasos que no necesitan tu intervención, hasta la próxima pausa.

![Captura: modal de ejecución de pipeline con el progreso paso a paso](pendiente)

### Paso 4: Carga los archivos solicitados

Cuando el proceso llega a un paso que necesita archivos, verás una o más zonas para arrastrar o seleccionar archivos, cada una con su propia etiqueta y descripción. Lo habitual es que te pida dos tipos de archivo:

- **Archivo de estudiantes**: el Excel con los resultados de cada estudiante (nombre, RUT, curso, puntajes, logro, etc.), tal como lo entrega la agencia evaluadora o el colegio. En algunas evaluaciones se sube un archivo por curso.
- **Archivo de preguntas**: el detalle de resultados por pregunta (en algunas evaluaciones, como DIA, este archivo es un PDF oficial de la agencia; en otras es un Excel adicional).

1. Arrastra el archivo a la zona correspondiente, o haz clic sobre ella para elegirlo desde tu computador.
2. Repite para cada archivo solicitado. Los recuadros marcados como obligatorios deben completarse antes de continuar; los que dicen "opcional" puedes dejarlos vacíos.
3. Cuando un archivo queda cargado, la zona muestra un chip verde "Listo" y el nombre del archivo.
4. Haz clic en **Siguiente** (o **Continuar**) para subir los archivos y avanzar.

![Captura: zonas de carga de archivos con un archivo ya seleccionado](pendiente)

> ⚠️ El sistema espera columnas y encabezados específicos según la evaluación (por ejemplo, un archivo SIMCE de Lenguaje espera columnas como Nombre, RUT, Curso, Puntaje, Logro, con el encabezado en una fila determinada). Usa siempre el archivo tal como lo entrega la agencia evaluadora, sin reordenar columnas ni filas, y asegúrate de que los datos estén en la primera hoja del Excel.

### Paso 5: Completa los datos adicionales que te pida (si aplica)

Algunos procesos necesitan un dato extra que no viene en el archivo, como el **Hito** de la evaluación (por ejemplo, Diagnóstico, Intermedio o Final). En ese caso verás:

- Un formulario único, si el dato aplica a toda la carga.
- Una tabla con una fila por archivo, si el dato es distinto para cada archivo.

1. Completa el o los campos solicitados.
2. Haz clic en **Confirmar Datos** para continuar. El botón permanece deshabilitado hasta que todos los campos estén completos.

![Captura: tabla de datos adicionales por archivo](pendiente)

### Paso 6: Verifica que el proceso terminó bien

1. Cuando todos los pasos se completan, la ventana muestra "¡Proceso Completado!" con la lista de archivos generados.
2. Puedes hacer clic en el ícono de descarga para bajar un archivo generado, o en el ícono de copiar para pegarlo directo en Excel.
3. Haz clic en **Finalizar** para cerrar la ventana.

![Captura: pantalla de proceso completado con artefactos generados](pendiente)

> 💡 Los datos ya quedaron guardados en el sistema en este punto — puedes ir directo a la Parte 2 para revisarlos en el dashboard.

---

## Parte 2 — Ver el dashboard

### Paso 1: Ve a la sección "Resultados"

1. En el menú lateral, haz clic en **Resultados**.
2. En el selector **Indicador**, elige el indicador que quieres revisar (por ejemplo, "SIMCE Lenguaje 4° Básico" o "IDEL"). El dashboard se carga automáticamente.

![Captura: página de Resultados con el selector de indicador](pendiente)

### Paso 2: Aplica filtros

Debajo del selector de indicador aparece una fila de filtros, uno por cada dimensión disponible (por ejemplo Curso, Año, Mes, N° Prueba).

1. Haz clic en un filtro (por ejemplo "Curso") para abrir su lista de valores.
2. Busca un valor con el buscador o marca directamente las casillas de los valores que quieres ver. Puedes marcar **más de un valor** a la vez (por ejemplo, 5°A y 5°B juntos).
3. Cierra el desplegable haciendo clic fuera de él. Los valores elegidos aparecen como "chips" (etiquetas) debajo de los filtros; puedes quitar uno haciendo clic en su X.
4. Para quitar todos los filtros de una vez, usa el botón **Limpiar**.

![Captura: filtros multi-valor con chips activos](pendiente)

> 💡 Al elegir un valor en un filtro, las opciones disponibles en los otros filtros se acotan automáticamente para mostrar solo combinaciones que existen en los datos.

### Paso 3: Interpreta el dashboard

El dashboard se organiza en pestañas con KPIs (indicadores numéricos resumen), gráficos y tablas, según cómo esté configurado el indicador. Todos se actualizan juntos cuando cambias los filtros.

![Captura: dashboard con KPIs y gráficos](pendiente)

### Si un gráfico o tabla aparece vacío

Un gráfico vacío casi siempre significa que **no hay datos que cumplan la combinación de filtros elegida** (por ejemplo, un curso que no rindió esa prueba, o un mes sin resultados cargados). El sistema muestra además un aviso indicando que no se encontraron datos con los filtros seleccionados.

1. Revisa los chips de filtros activos arriba del dashboard.
2. Quita filtros de a uno (o usa **Limpiar** para sacarlos todos) hasta que vuelvan a aparecer datos.

---

## Parte 3 — Descargar el informe

### Paso 1: Abre el selector de informes

1. Con un indicador y (opcionalmente) filtros ya elegidos en el dashboard, haz clic en el botón **Generar informe**, junto al selector de indicador.
2. Se abre una ventana con dos secciones: **Informes del período** e **Informes especializados**.

![Captura: modal "Generar informe" con las dos secciones](pendiente)

### Paso 2: Elige un informe del período

Esta sección ofrece cuatro opciones estándar, ya resueltas contra los datos reales del indicador:

| Informe | Qué contiene |
|---|---|
| **Informe última prueba** | La evaluación más reciente registrada (un solo punto en el tiempo). |
| **Informe semestral** | La evolución de los resultados durante el semestre escolar en curso. |
| **Informe Anual** | La evolución de los resultados durante el año en curso. |
| **Informe Personalizado** | Tú eliges el rango de fechas y los filtros antes de generarlo. |

1. Haz clic directamente sobre la tarjeta del informe que quieres. Esto **descarga el PDF de inmediato**, usando la configuración guardada (encabezados y branding del último uso, o los valores por defecto).

![Captura: tarjetas de informes del período](pendiente)

### Paso 3: Usa el Informe Personalizado (opcional)

1. Haz clic sobre la tarjeta **Informe Personalizado**. Se despliega un panel con:
   - Filtros por dimensión (los mismos tipos de filtro que en el dashboard).
   - Un rango de fechas **Desde / Hasta**, en formato mes-año. Si lo dejas vacío, el informe usa todo el período disponible según los filtros elegidos.
2. Completa lo que necesites y haz clic en **Descargar**.

![Captura: panel expandido del Informe Personalizado con filtros y rango de fechas](pendiente)

> ⚠️ Si eliges una fecha "Desde" posterior a la fecha "Hasta", el sistema te avisa y no deja continuar hasta que corrijas el rango.

### Paso 4: Informes especializados

Esta sección reúne informes con un formato propio, distinto al informe estándar del período — por ejemplo:

- **Informe PDL IDEL-Woodcock** (formato oficial de esa evaluación).
- **Informe de evaluación SIMCE (formato oficial)** y **DIA (formato oficial)**.
- **Word — Resumen del Indicador** (un documento Word editable en vez de un PDF).

1. Haz clic sobre la tarjeta del informe especializado que necesitas para descargarlo con un clic.

> 💡 Algunos informes especializados piden que primero apliques en el dashboard un filtro que acote los datos a un solo punto en el tiempo (por ejemplo, un único Mes o N° de Prueba). Si falta, el sistema te lo indica antes de generar el informe.

### Paso 5: Personaliza antes de descargar (opcional)

Junto a cada tarjeta (salvo las de informes especializados con motor propio) hay un botón con ícono de **deslizadores** (⚙). Este botón abre un panel para ajustar, antes de descargar:

- Los logos y el encabezado del informe (hasta 3 líneas de texto centrado).
- El pie de página izquierdo (por defecto, el nombre de tu organización).
- Si mostrar o no el número de página.
- En algunos informes, también el nombre del archivo descargado.

1. Ajusta lo que necesites.
2. Haz clic en **Descargar** dentro del panel para generar el informe con esos cambios.

![Captura: botón de deslizadores para personalizar encabezados](pendiente)

> 💡 El pie de página izquierdo del PDF siempre identifica a tu organización (usa el nombre configurado en tu cuenta), salvo que lo hayas reemplazado manualmente en este panel.

### Tarjetas deshabilitadas

Si una tarjeta aparece atenuada (gris, no se puede hacer clic), el sistema explica el motivo directamente en su descripción. Los motivos más comunes son:

- **"Sin datos cargados para este indicador"** — todavía no se ha cargado información (ver Parte 1).
- **"Este informe aún no está configurado"** — falta que el administrador defina el diseño del informe en el editor de layout.
- **"Falta la plantilla .docx en el servidor"** — aplica solo a informes Word.

![Captura: tarjeta de informe deshabilitada con el motivo visible](pendiente)

---

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| Al ejecutar el pipeline, aparece "Faltan archivos: ..." | No cargaste uno de los archivos marcados como obligatorios. | Revisa la lista de archivos pedidos y carga el que falta antes de continuar. |
| El proceso se detiene con un error de "Columna llave [nombre] no existe" | El Excel subido no tiene esa columna, o el nombre de la columna no coincide exactamente con lo esperado. | Usa el archivo original de la agencia evaluadora sin renombrar ni reordenar columnas. |
| El proceso falla al leer el archivo con un error de encabezado o filas | Los datos no están en la primera hoja del Excel, o el encabezado quedó movido de fila. | Verifica que la hoja con los datos sea la primera del archivo y que no hayas insertado filas antes del encabezado. |
| El proceso queda "pegado" o da un error inesperado al reintentar | Quedó un intento anterior sin cerrar. | Cierra la ventana con **Cerrar** y vuelve a ejecutar el pipeline desde cero. |
| Un gráfico o tabla del dashboard aparece vacío | Los filtros activos no coinciden con ningún dato cargado. | Quita filtros de a uno, o usa **Limpiar**, hasta que reaparezcan datos. |
| La tarjeta de un informe aparece deshabilitada | Falta configuración (layout, plantilla) o no hay datos para ese período. | Lee el motivo indicado en la propia tarjeta; si falta configuración, avisa al administrador. |
| El "Informe Personalizado" no deja hacer clic en Descargar | El rango de fechas "Desde" es posterior a "Hasta". | Corrige el rango para que "Desde" sea igual o anterior a "Hasta". |
| Un informe especializado (SIMCE/DIA formato oficial) no descarga y pide un filtro | El informe necesita un único punto en el tiempo (un Mes o N° de Prueba) y no hay ninguno o hay varios seleccionados. | Aplica en el dashboard un filtro temporal con un solo valor antes de generarlo. |
