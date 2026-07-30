# Guía rápida — Report Generator

Entrar, cargar los datos de una evaluación, mirar los resultados y descargar el informe.

> Las imágenes de esta guía son de una **organización de demostración**, con datos
> inventados. En tu cuenta verás los nombres y cursos de tu propio colegio.

---

## 1. Entrar a la aplicación

Abre la dirección de la plataforma e ingresa con tu correo y tu contraseña.

![Pantalla de inicio de sesión](img/login.png)

Si no las tienes, o la contraseña dejó de funcionar, pídeselas al administrador.

---

## 2. Cargar los datos

Hay **dos caminos** y se usa uno solo. Para saber cuál te toca, entra a **Ejecución** en el
menú de la izquierda: ahí está el Centro de Ejecución, con una tarjeta por cada proceso de
carga ya configurado para tu colegio. Si ves una con el nombre de tu evaluación, sigue el
camino 2.1; si no aparece ninguna, sigue el 2.2.

### 2.1 La evaluación tiene un proceso configurado (SIMCE, DIA)

Busca la tarjeta de tu evaluación y haz clic en **Ejecutar Proceso**.

![Centro de Ejecución con las tarjetas de proceso](img/pipelines.png)

Se abre una ventana que avanza por pasos. Cuando llegue a uno que necesita tus archivos,
se detiene y te muestra un recuadro por cada archivo pedido.

![Ventana de ejecución pidiendo los archivos](img/carga_archivos.png)

1. Arrastra el archivo al recuadro, o haz clic para buscarlo en tu computador.
2. Repite con cada recuadro. Los que dicen *opcional* puedes dejarlos vacíos.
3. Haz clic en **Siguiente** para continuar.
4. Si el proceso te pide un dato extra (por ejemplo, el hito de la evaluación),
   complétalo y confirma.

Cuando termine verás el mensaje **¡Proceso Completado!**: tus datos ya quedaron guardados.
Cierra la ventana con **Finalizar**.

Qué archivo va en cada recuadro, y qué no hay que tocarle a cada uno, está en el
[anexo de carga por evaluación](./anexo_carga_pipelines.md) — un capítulo por evaluación.

### 2.2 La evaluación no tiene proceso configurado

Los datos se suben a mano, desde una planilla Excel:

1. Entra a **Valores** en el menú de la izquierda y elige la métrica que vas a llenar.
2. Haz clic en **Importar**, arriba a la derecha de la tabla.
3. Si todavía no tienes la planilla, usa **Descargar Plantilla**: baja un Excel con las
   columnas exactas de esa métrica, listo para rellenar.
4. Rellena la plantilla, arrástrala al recuadro (o usa **Seleccionar Archivos**) y haz
   clic en **Importar**.

![Ventana Importar Datos, con el botón Descargar Plantilla](img/importar_valores.png)

> 💡 No cambies ni reordenes los títulos de las columnas de la plantilla: el sistema los
> usa para saber qué es cada dato.

### Revisa lo que quedó cargado

Sea cual sea el camino, entra después a **Valores**, elige la métrica y confirma que el
total de filas (arriba de la tabla) y los cursos y meses sean los que esperabas. Con
**Filtros** acotas por columna y con **Buscar en los datos...** encuentras un nombre o un
RUT concreto. Si ves datos repetidos o de una carga equivocada, avisa al administrador
antes de seguir: es más fácil corregirlo ahora que después.

![Página de Valores con los filtros abiertos](img/values.png)

---

## 3. Interpretar los resultados en el Dashboard

Entra a **Resultados** y elige tu indicador en la lista de arriba. El panel se arma solo.

![Dashboard del indicador con gráficos](img/dashboard.png)

- **Pestañas** (Vista General, Por Curso, Por Estudiante, Tendencia): cada una muestra un
  corte distinto de los mismos datos.
- **Tarjetas de resumen**: los números gruesos del total de alumnos, el rendimiento
  general y el nivel más frecuente.
- **Tablas y gráficos**: el detalle curso por curso.
- **Colores de los niveles de logro**: siempre los mismos en todo el sistema (rojo el
  nivel más bajo, verde el más alto), para leer un gráfico sin revisar la leyenda.

Para mirar solo una parte, usa los **filtros** que están bajo el indicador. Al elegir un
valor aparece una etiqueta (un "chip") con lo que está aplicado y todos los gráficos se
actualizan juntos. Quita un filtro con la **×** de su chip, o sácalos todos con **Limpiar**.

![Dashboard con un filtro de curso aplicado](img/dashboard_filtros.png)

> 💡 Si un gráfico se ve vacío, casi siempre es porque los filtros activos no dejan ningún
> dato. Quítalos de a uno hasta que reaparezca.

---

## 4. Exportar el informe

Con tu indicador en pantalla, haz clic en **Generar informe**. Un clic en la tarjeta que
necesites descarga el PDF de inmediato.

![Ventana Generar informe con las tarjetas de período](img/generar_informe.png)

| Tarjeta | Qué trae |
|---|---|
| **Informe última prueba** | Solo la evaluación más reciente. |
| **Informe semestral** | La evolución del semestre en curso. |
| **Informe Anual** | La evolución del año. |
| **Informe Personalizado** | Tú eliges el rango de fechas y los filtros. |

Más abajo, en **Informes especializados**, están los informes con el formato oficial de
cada evaluación. El botón de **deslizadores**, a la derecha de cada tarjeta, abre un panel
para ajustar los títulos del encabezado, el pie de página y el nombre del archivo antes de
descargar.

Una tarjeta gris no se puede descargar, y la razón está escrita en ella: *Sin datos
cargados para este indicador* (vuelve a la sección 2) o *Este informe aún no está
configurado* (avísale al administrador). Así se ve el PDF que descargas:

![Primera página del informe descargado](img/informe_pdf.png)

> 💡 Los informes especializados a veces piden que primero filtres a una sola prueba (un
> Mes o un N° de prueba). El sistema te lo indica antes de generarlo.

---

## Anexo — Archivos necesarios por evaluación

Lo que hay que tener a mano antes de empezar la carga. El detalle de cada archivo (nombre
del recuadro, formato y qué no hay que modificarle) está en el anexo enlazado:

- **SIMCE Pullinque**: Resultados por alumno · Resultados por pregunta · Habilidad y Eje
  Temático — [ver detalle](./anexo_carga_pipelines.md#1-simce)
- **DIA**: PDF de resultados · Excel con resultados por alumno —
  [ver detalle](./anexo_carga_pipelines.md#2-dia)
- **SIMCE Panguipulli**: *Pendiente el exporte de Aptus* —
  [ver detalle](./anexo_carga_pipelines.md#3-simce-panguipulli-ensayos-aptus)

Las evaluaciones que no están en esta lista se cargan por el camino 2.2.

---

¿Se te quedó algo en el camino? El [tutorial extendido](./tutorial_usuario.md) tiene el
paso a paso completo y una tabla de problemas frecuentes.
