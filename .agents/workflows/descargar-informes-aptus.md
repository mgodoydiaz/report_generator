---
description: Descargar desde Aptus, con Chrome MCP, los informes de SIMCE Panguipulli (por Estudiante y por Habilidad)
---
# `/descargar-informes-aptus` — Bajar los informes desde Aptus con el navegador

Automatiza la descarga de los **dos** Excel que alimentan SIMCE Panguipulli:

| Informe | Alimenta la métrica |
|---|---|
| `Informe_logro_por_estudiante` | 24 · por Estudiante |
| `Informe_logro_por_habilidad` | 26 · por Habilidad |

El informe **por OA** y el **PDF de comparación** existen en la misma pantalla pero **no se
descargan**: ningún dashboard ni informe los consume.

Después de esto, los archivos se suben con el proceso **`SIMCE Panguipulli (Aptus)`** de la
pantalla **Ejecución**. La carga en sí está en [`/cargar-simce-panguipulli`](./cargar-simce-panguipulli.md).

---

## Reglas que no se rompen

1. **Nunca escribas las credenciales del usuario.** Ni usuario, ni contraseña, ni pegarlas
   desde ningún lado. El login lo hace la persona, a mano, y tú esperas.
2. **La carpeta de descargas es la del usuario que está corriendo esto**, no una ruta fija.
   Resuélvela; no la asumas.
3. **Confirma el mes antes de descargar.** Di en voz alta qué vas a bajar y espera el visto
   bueno, salvo que la persona ya haya dicho el mes.
4. **Verifica que los archivos llegaron.** Un clic que no descarga es el modo de falla más
   probable de esta skill. Si falta uno, pídele ese clic a la persona; no lo des por hecho.

---

## Paso 0 — Preparar

**Carga las herramientas de Chrome en una sola llamada** (si están diferidas):

```
ToolSearch: "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__find,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__browser_batch"
```

**Resuelve la carpeta de descargas del usuario actual:**

```powershell
$d = Join-Path $env:USERPROFILE 'Downloads'; if (Test-Path $d) { $d } else { $env:USERPROFILE }
```

Si la persona indicó otra carpeta, usa esa. Guarda la ruta: la vas a necesitar dos veces
(para comparar antes/después y para renombrar).

**Toma el inventario previo**, para poder distinguir lo nuevo de lo viejo:

```powershell
Get-ChildItem $carpeta -Filter 'Informe_logro*' | Select-Object Name, LastWriteTime
```

---

## Paso 1 — Abrir Aptus y esperar el login

Abre una pestaña y navega a `https://web.aptus.org/apt_system/home`.

Toma una captura. Si la sesión **ya está iniciada** (aparece «Mi Cuenta Aptus» con el nombre
de la persona), sigue al paso 2.

Si **no** está iniciada, **detente y dile a la persona algo así**:

> Abrí Aptus en el navegador. Inicia sesión con tu usuario y contraseña, y avísame cuando
> estés dentro. No voy a escribir tus credenciales.

Espera su respuesta. Cuando confirme, vuelve a capturar para verificar que efectivamente
entró antes de seguir.

---

## Paso 2 — Ir a la pantalla de resultados

Navega directo a:

```
https://web.aptus.org/aptus-8/informes/verResultados
```

Selecciona **Periodo** (el año) y **Colegio**. Para Panguipulli el colegio es
`016843 - Liceo Bicentenario De Exelencia Tecnico Profesional People Help People De Panguipulli`.

> Si ya vienen preseleccionados, no los toques.
>
> **Ojo**: los parámetros en la URL (`?idPeriodo=…&idColegio=…&idProceso=…`) **no restauran**
> los selectores. Sirven para volver a un punto, pero igual hay que elegir en pantalla.

### Cómo manejar estos desplegables

Son comboboxes con búsqueda, y los clics por coordenada son poco fiables. Lo que **sí**
funciona: abrir con un clic sobre el input y después hacer `.click()` por JS sobre el `li`
cuyo texto coincide exactamente.

Abrir un combo por su etiqueta:

```js
(function(){var l=Array.from(document.querySelectorAll('label,div,span')).filter(function(e){
  return e.children.length===0 && e.textContent.trim()==='Proceso';});
  if(!l.length) return 'no label';
  var i=l[0].parentElement.querySelector('input'); if(!i) return 'no input';
  i.click(); i.focus(); return 'abierto';}())
```

Elegir una opción:

```js
(function(){var o=Array.from(document.querySelectorAll('li')).filter(function(e){
  return e.textContent.trim()==='EMN Mayo';});
  if(!o.length) return 'no encontrado'; o[0].click(); return 'ok';}())
```

> ⚠️ **El `javascript_tool` se bloquea** si el script devuelve atributos `src` o `href`
> completos («Cookie/query string data»). Devuelve solo texto, números o `pathname`.

---

## Paso 3 — Elegir el proceso (el mes)

En la columna izquierda, con **Evaluaciones** marcado (no *Seguimiento*):

1. **Tipo de proceso** → `EMN`.
2. **Proceso** → el mes.

Para saber qué meses hay, abre el combo *Proceso* y lista las opciones:

```js
Array.from(document.querySelectorAll('li')).map(function(e){return e.textContent.trim()})
  .filter(function(s){return s.indexOf('EMN ')===0}).join(' | ')
```

Devuelve algo como `EMN Abril | EMN Mayo | EMN agosto | EMN Septiembre`.

**Por defecto toma la última opción de la lista** — es la más reciente según Aptus. No
intentes deducir el mes más avanzado interpretando los nombres: Aptus los escribe despareja
(`EMN agosto` en minúscula) y eso se rompe solo.

**Antes de descargar, dile a la persona qué vas a bajar y ofrécele cambiarlo:**

> Voy a descargar **EMN Septiembre**: el informe por Estudiante y el de Habilidad.
> Los meses disponibles son abril, mayo, agosto y septiembre. ¿Sigo con septiembre?

Si ya te indicó un mes al invocarte, úsalo sin preguntar de nuevo.

---

## Paso 4 — Nivel y Asignatura

Selecciona **un nivel y una asignatura** cualquiera.

> **Por qué, si no cambian el archivo.** El Excel que baja Aptus trae siempre el mes
> completo — todos los niveles y todas las asignaturas — así que el contenido no depende de
> estos filtros. Pero en las pruebas, **la descarga del informe de Habilidad solo funcionó con
> Nivel y Asignatura seleccionados**. Es una hipótesis no confirmada; ponerlos no cuesta nada
> y evita la falla.

Estos dos combos **no renderizan sus opciones como `li`**, así que el truco del paso 2 no
sirve. Ábrelos, toma una captura y haz clic por coordenada sobre la opción.

---

## Paso 5 — Desplegar el panel «Informes»

Sobre la tabla de resultados hay una barra gris plegada que dice **Informes**. Hay que
**expandirla**: mientras esté plegada, los enlaces existen en el DOM pero con altura 0, y
cualquier coordenada que calcules va a apuntar al mismo punto.

El panel vive en un **iframe same-origin** que se crea recién después de elegir el proceso:
`/apt_system/AptusDigitalResultados/getResultadoColegioHtml`. Es el **primer** iframe de la
página (el segundo es el widget de soporte, y es cross-origin).

Ubica el encabezado y clickéalo por coordenada:

```js
(function(){var f=document.querySelectorAll('iframe')[0];var fr=f.getBoundingClientRect();
 var d=f.contentDocument; if(!d) return 'sin acceso al iframe';
 var c=Array.from(d.querySelectorAll('*')).filter(function(e){
   return e.children.length<=1 && e.textContent.trim()==='Informes';});
 if(!c.length) return 'no esta el panel todavia';
 var r=c[0].getBoundingClientRect(); var k=1568/1920;
 return Math.round((fr.left+r.left+r.width/2)*k)+','+Math.round((fr.top+r.top+r.height/2)*k);}())
```

> El factor `k` convierte coordenadas del viewport a las del screenshot, que es el espacio en
> que trabaja `computer`. **No lo dejes fijo**: calcula `k = anchoScreenshot / window.innerWidth`
> con los valores reales de la sesión (una captura te da el ancho; `window.innerWidth` te lo
> da el JS). Con 1920 de viewport y 1568 de captura, `k = 0.8167`.

Si un desplegable quedó abierto, ciérralo antes (Escape o un clic en zona vacía): el overlay
intercepta el clic sobre el panel.

---

## Paso 6 — Descargar los dos informes

Con el panel expandido, calcula la posición de cada fila. **Identifícalas por el texto del
elemento padre, no por índice** — el orden es estable (comparación, OA, Habilidad,
Estudiante) pero el texto es a prueba de cambios:

```js
(function(){var f=document.querySelectorAll('iframe')[0];var fr=f.getBoundingClientRect();
 var d=f.contentDocument;var a=d.querySelectorAll('a');var k=1568/1920;var out=[];
 for(var i=0;i<Math.min(6,a.length);i++){var p=a[i].parentElement;var t=p?p.textContent.trim():'';
  if(!/Descargar informe/.test(t)) continue;
  var r=p.getBoundingClientRect();
  out.push(Math.round((fr.left+r.left+60)*k)+','+Math.round((fr.top+r.top+r.height/2)*k)+' :: '+t.slice(0,45));}
 return out.join('\n');}())
```

Si las alturas salen en 0, el panel no está expandido: vuelve al paso 5.

**Haz un clic real por coordenada** (`computer` → `left_click`) sobre las filas de
**Estudiante** y **Habilidad**. Espera unos 8 segundos entre uno y otro.

> **Usa clic real, no `.click()` por JS.** El clic programático no lleva gesto de usuario y
> Chrome puede bloquear la descarga. En las pruebas, por JS bajó el de Estudiante pero nunca
> el de Habilidad; por coordenada bajaron los dos.

**No clickees** la fila de OA ni la del PDF de comparación.

---

## Paso 7 — Verificar y renombrar

Vuelve a listar la carpeta de descargas y compara contra el inventario del paso 0:

```powershell
Get-ChildItem $carpeta -Filter 'Informe_logro*' |
  Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-10) } |
  Select-Object Name, Length, LastWriteTime
```

**Si faltó alguno**, no lo des por descargado. Reintenta ese clic una vez; si sigue sin
aparecer, dile a la persona exactamente cuál falta y pídele que lo clickee, con el panel ya
abierto en pantalla.

**Renombra los que llegaron** agregando el mes. Aptus los entrega como
`Informe_logro_por_estudiante (dd-mm-aaaa).xlsx`, con la fecha de descarga y sin el mes:

| Queda así | Debe quedar |
|---|---|
| `Informe_logro_por_estudiante (05-08-2026).xlsx` | `Informe_logro_por_estudiante SEPTIEMBRE.xlsx` |
| `Informe_logro_por_habilidad (05-08-2026).xlsx` | `Informe_logro_por_habilidad SEPTIEMBRE.xlsx` |

El sistema no lee el mes del nombre — lo saca de la columna `NOMBRE PROCESO` de adentro —
pero el renombre evita confundir descargas de meses distintos, que se ven casi iguales.

Si ya existe un archivo con ese nombre, no lo pises: avisa y deja el sufijo que puso Chrome.

---

## Paso 8 — Cerrar

Reporta:

- Qué mes se descargó y a qué carpeta.
- Los dos archivos con su nombre final y su tamaño.
- Si alguno lo tuvo que clickear la persona.

Y recuerda el siguiente paso: subirlos en **Ejecución → `SIMCE Panguipulli (Aptus)`**, que se
detiene dos veces (primero Estudiante, después Habilidad). **La carga suma, no reemplaza**: si
ese mes ya estaba cargado, se duplicaría.

---

## Cuando algo falla

| Síntoma | Qué pasa |
|---|---|
| `document.querySelectorAll('a')` no encuentra los enlaces | Estás mirando el documento principal. Los enlaces están dentro del iframe: usa `contentDocument`. |
| El JS devuelve «BLOCKED: Cookie/query string data» | Tu script devuelve `src` o `href` completos. Devuelve solo `pathname`, números o texto. |
| Las 4 filas dan la misma coordenada, altura 0 | El panel «Informes» está plegado. |
| El clic no descarga nada | Faltan Nivel/Asignatura, o usaste `.click()` por JS en vez de clic real. |
| El combo no se abre con clic por coordenada | Usa el método del paso 2: clic en el input y `.click()` por JS sobre el `li`. |
| Solo aparece el año 2025 en Periodo | Es lo que ofrece la cuenta. 2024 y 2026 no están disponibles hoy. |
| No hay iframe en la página | Todavía no eliges Tipo de proceso + Proceso; el iframe se crea recién ahí. |

## Lo que esta skill no hace

- **No inicia sesión.** Nunca.
- **No descarga el informe por OA** ni el PDF de comparación.
- **No sube los archivos** al sistema — eso es `/cargar-simce-panguipulli`.
- **No recorre varios meses** en una corrida. Un mes por invocación.
