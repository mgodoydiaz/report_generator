---
description: Cargar datos de SIMCE Panguipulli (ensayos Aptus) — descarga desde Aptus y carga al sistema
---
# `/cargar-simce-panguipulli` — Cargar SIMCE Panguipulli (ensayos Aptus)

Skill operativa para poner datos nuevos de **SIMCE Panguipulli** (los ensayos que aplica
Aptus) dentro del sistema. Cubre las dos mitades del trabajo: **de dónde salen los archivos**
en la plataforma Aptus, y **cómo cargarlos**.

> El indicador es `id_indicator=6` (`SIMCE Panguipulli`, org 1) y se alimenta de **dos**
> métricas: **24** por Estudiante y **26** por Habilidad.
>
> ⚠️ **La métrica 25 (por OA) quedó fuera.** No está vinculada a ningún indicador y ningún
> dashboard ni informe la consume. El 2026-08-05 se eliminaron del pipeline sus 6 pasos, así
> que el colegio ya no descarga ese archivo. **La métrica y sus 921 filas se conservan**
> intactas por si algún día se ocupa. Ver
> `docs/desarrollo/inventario_indicadores_2026-07-30.md`.

---

## Parte 1 — Descargar los archivos desde Aptus

Los Excel los descarga el colegio desde la plataforma; no llegan por correo. Se
necesita una cuenta Aptus con acceso a los resultados del establecimiento.

1. <https://web.aptus.org> → iniciar sesión.
2. **Recursos Pedagógicos → Ver Resultados**. Se abre la pantalla *Resultados* con cuatro
   pestañas; la que sirve es **Ver Resultados** (queda activa por defecto).
3. Filtros de arriba:
   - **Periodo** = año de la evaluación.
   - **Colegio** = `016843 - Liceo Bicentenario De Exelencia Tecnico Profesional People Help People De Panguipulli`.
   - **Proyectos** y **Sostenedor** se dejan vacíos.
4. Columna izquierda, con **Evaluaciones** marcado (no *Seguimiento*):
   - **Tipo de proceso** = `EMN`.
   - **Proceso** = el mes con la grafía de Aptus: `EMN Abril`, `EMN Mayo`, `EMN agosto`, `EMN Septiembre`.
   - **Nivel** = `4° básico` / `8° básico` / `II° medio` (multi-select).
   - **Asignatura** = `Lenguaje y Comunicación` / `Matemática` / `Historia, Geografía y Ciencias Sociales` (multi-select).

   > **Nivel y Asignatura NO afectan los Excel.** El libro que descarga Aptus trae siempre el
   > **proceso completo** — todos los niveles y todas las asignaturas del mes. Los filtros solo
   > cambian la tabla en pantalla y el PDF de comparación.
   >
   > Verificado empíricamente sobre el histórico local de 66 archivos: solo hay **21 contenidos
   > únicos** (7 por tipo de informe = 1 por mes de 2024/2025). Los archivos guardados en
   > carpetas distintas de nivel/asignatura son copias byte-equivalentes. Consecuencia
   > operativa: **basta 1 descarga por mes y por tipo de informe**, y cualquier script que
   > recorra ese árbol recursivamente **debe deduplicar por contenido** o inflará los datos
   > ~3.15×.
5. Sobre la tabla hay un panel plegado **Informes**. Desplegarlo da cuatro enlaces, de los
   que solo sirven **dos**:
   - `Descargar informe de logros por Estudiante` → alimenta la métrica **24**
   - `Descargar informe de logros por Habilidad` → métrica **26**

   Los otros dos —`Descargar informe (comparación muestra de colegios)` (PDF) y
   `Descargar informe de logros por OA`— **no se usan**.

### Notas de operación

- Aptus entrega los archivos como `Informe_logro_por_estudiante (dd-mm-aaaa).xlsx`, con la
  fecha de descarga y **sin el mes**. Conviene renombrarlos agregando el mes
  (`Informe_logro_por_estudiante MAYO.xlsx`): el sistema no lee el mes del nombre — lo saca
  de la columna `NOMBRE PROCESO` de adentro — pero el operador necesita distinguirlos.
- **Automatización con navegador: parcialmente lograda.** Lo verificado el 2026-08-04:
  - El panel de resultados vive en un iframe **same-origin y accesible por JS**,
    `/apt_system/AptusDigitalResultados/getResultadoColegioHtml`. Se crea **solo después** de
    elegir Tipo de proceso + Proceso; antes de eso no existe, y por eso el árbol de
    accesibilidad y `document.querySelectorAll` del documento principal salen vacíos.
  - Dentro del iframe, los 4 enlaces de descarga son los primeros 4 `<a>`, en orden
    comparación / OA / Habilidad / Estudiante, identificables por el texto del elemento padre.
    **No tienen `href` ni `onclick`** — el handler se enlaza por JS, así que no hay URL que
    replicar.
  - Sus coordenadas en pantalla se pueden calcular vía `getBoundingClientRect()` sumando el
    offset del iframe y escalando por 1568/1920. **Requisito: el panel debe estar expandido**,
    si está plegado todos los rects colapsan al mismo punto con altura 0.
  - Los desplegables **Tipo de proceso** y **Proceso** se manejan bien haciendo `.click()` por
    JS sobre el `li` cuyo texto coincide. Los de **Nivel** y **Asignatura** no renderizan sus
    opciones como `li` y quedaron sin automatizar.
  - **Las descargas se lograron** (habilidad 8.893 B + estudiante 31.969 B) en una sesión donde
    Nivel y Asignatura **sí estaban seleccionados**. Sin esos filtros no se pudo reproducir la
    de Habilidad. Hipótesis más probable, **no confirmada**: la generación de los informes de
    Habilidad y OA exige Nivel y Asignatura seleccionados.
  - Conclusión práctica: automatizar hasta dejar el panel expandido es fiable; el clic final
    conviene intentarlo y **verificar que el archivo llegó a la carpeta de descargas**, con
    fallback a pedirle el clic al usuario.
- Los URLs de la pantalla son parametrizables, útil para volver a un punto exacto:
  `https://web.aptus.org/aptus-8/informes/verResultados?idPeriodo={año}&idColegio={colegio}&idProceso={mes}&idNivel={n1,n2}&idAsignatura={a1,a2}`
  IDs conocidos: `idPeriodo=31`→2025, `idColegio=936`→Panguipulli, `idProceso=293`→EMN Mayo,
  `idNivel` 5→4° básico y 9→8° básico, `idAsignatura` 1→Lenguaje y 2→Matemática.

---

## Parte 2 — Cargar en el sistema

Hay **un solo pipeline**: `SIMCE Panguipulli (Aptus)` (id 26), en la pantalla **Ejecución**.

No pide ningún dato al operador — el mes, la asignatura, el nivel y el curso salen de los
propios archivos, y el establecimiento queda fijo en `Panguipulli`. Son **13 pasos** y se
detiene **dos veces**:

| Pausa | Rol interno | Archivo | → métrica |
|---|---|---|---|
| Informe de logros por Estudiante | `estudiantes` | `Informe_logro_por_estudiante` | 24 |
| Informe de logros por Habilidad | `habilidad` | `Informe_logro_por_habilidad` | 26 |

Los dos `SaveToMetric` corren con `clear_existing: false` → **la carga es acumulativa**.
Repetir un mes ya cargado duplica sus filas; hay que verificar en **Valores** antes.

**Verificado en dev el 2026-08-05**: con los 2 archivos de mayo 2025 inserta 443 filas en la
métrica 24 y 45 en la 26, sin advertencias.

### Carga masiva del histórico

Para cargar varios meses o años de una vez, el pipeline obligaría a una corrida por mes. Para
eso está **`scripts/construir_importables_emn.py`**, que recorre el archivo local de
originales, deduplica por contenido y escribe archivos listos para **Valores → Importar**.

El endpoint `POST /api/metrics/{id}/import` matchea los encabezados **por string exacto**
(sensible a mayúsculas y tildes), lee **la primera hoja** y toma los encabezados de la
**fila 1**. Columnas extra se ignoran en silencio. Es **append**, nunca reemplaza: para
recargar hay que vaciar antes con `POST /api/metrics/{id}/clear`.

Columnas exactas:

- **Métrica 24 — Estudiante**: `Establecimiento, Año, Mes, N Prueba, Asignatura, Nivel, Curso, RUT, Nombre, PorcLogro, LogroNormalizado`
- **Métrica 26 — Habilidad**: `Establecimiento, Año, Mes, N Prueba, Asignatura, Nivel, Curso, Habilidad, LogroCurso, LogroHabilidad`

> Cuidado con los decimales: escribirlos como float nativo, no como texto con coma.

### Hubo un segundo pipeline

`SIMCE Panguipulli (Aptus) - Archivos importables` transformaba los archivos y los dejaba
descargables sin tocar la base, para revisar antes de cargar. **Se eliminó el 2026-08-05** al
consolidar en uno solo. Se puede recrear con `scripts/crear_pipeline_emn_importables.py`
(hay que ajustarle la constante del nombre de origen). No está desplegado en ninguna parte.

## Parte 3 — Transformaciones que aplica el pipeline

Quien prepare archivos para el Camino B debe replicar esto exactamente. Está declarado en los
specs 49 (estudiante), 50 (OA) y 51 (habilidad), con `header_row = 0`.

**Mapeo de columnas origen → destino**

| Archivo | Columnas de Aptus → nombre interno |
|---|---|
| Estudiante | `NOMBRE PROCESO`→`Proceso_raw`, `AÑO`→`Año`, `NIVEL`→`Nivel`, `CURSO`→`Curso_letra`, `ASIGNATURA`→`Asignatura_raw`, `RUT`→`RUT`, `APELLIDO PATERNO`→`A_P`, `APELLIDO MATERNO`→`A_M`, `PRIMER NOMBRE`→`P_N`, `SEGUNDO NOMBRE`→`S_N`, `PORCENTAJE LOGRO`→`PorcLogro`, `LOGRO NORMALIZADO`→`LogroNormalizado` |
| OA | …ídem cabecera común…, `NÚMERO OA`→`N OA`, `OA`→`OA`, `LOGRO`→`Logro` |
| Habilidad | …ídem cabecera común…, `PORCENTAJE LOGRO CURSO`→`LogroCurso`, `HABILIDAD`→`Habilidad`, `PORCENTAJE LOGRO HABILIDAD`→`LogroHabilidad` |

Los tres inyectan `Establecimiento = "Panguipulli"` (valor fijo, no viene del Excel).

**Derivaciones por fila**

1. `Mes` = `NOMBRE PROCESO` sin el prefijo `EMN `, en mayúsculas → `"EMN Abril"` da `ABRIL`.
2. `N Prueba` según el mes: `ABRIL`→1, `MAYO`→2, `AGOSTO`→3, `SEPTIEMBRE`→4, cualquier otro→**0**.
   Un mes nuevo (marzo, octubre…) queda con `N Prueba = 0` — hay que ampliar el mapeo del
   pipeline antes de cargarlo.
3. `Asignatura`: contiene `Lenguaje`→`LENGUAJE`, contiene `Matem`→`MATEMATICA`,
   contiene `Historia`→`HISTORIA`, si no `Asignatura_raw.upper()`.
4. `Curso` = `Nivel` + espacio + `Curso_letra` → `"4° básico" + "A"` da `"4° básico A"`.
5. Solo estudiante: `Nombre` = `A_P A_M P_N S_N` unidos por espacio, descartando vacíos y `nan`.
6. Coma → punto en los decimales: `PorcLogro`, `LogroNormalizado`, `Logro`, `LogroCurso`,
   `LogroHabilidad`.

---

## Parte 4 — Estado de los datos (auditado 2026-08-03)

**Cargado en la base**: solo **2025**, y está completo — 4 meses (ABRIL/MAYO/AGOSTO/SEPTIEMBRE
→ N Prueba 1/2/3/4), 3 niveles (4° básico, 8° básico, II° medio) y 3 asignaturas (LENGUAJE 783,
MATEMATICA 777, HISTORIA 135 filas en la métrica 24). Ningún `N Prueba = 0`.

**Disponible en el histórico local pero SIN cargar**: todo **2024** — II° medio, meses
ABRIL/MAYO/SEPTIEMBRE, con 1 245 filas de estudiante, 425 de OA y 135 de habilidad. Cargarlo
daría comparación año contra año, que hoy el indicador no tiene.

**Antes de cargar 2024, revisar dos cosas:**

1. **`CIENCIAS NATURALES` aparecería como asignatura nueva.** Solo existe en 2024. No está en el
   mapeo de los specs (llega por el `else`, sin normalizar) y no tiene precedente en la base;
   conviene confirmar que los dashboards del indicador 6 la toleran, o filtrarla.
2. **`LogroNormalizado` viene mayormente nulo en 2024** (Aptus no lo entrega para varios cursos,
   sobre todo ABRIL). Cualquier gráfico que dependa de esa columna quedará parcial.

**6° básico no existe** en ningún original — Aptus no lo entrega para este colegio. No es un hueco.

### Deuda detectada: dimensión `Nombre_Norm` huérfana

El export de la métrica 24 trae una columna llamada `Dim_22`. Es la dimensión **22 =
`Nombre_Norm`** (nombre normalizado: tokens en orden alfabético y sin tildes, producido por
`backend/rgenerator/core/pares_nombre.py`). Tiene datos en `metric_data`, pero **no está asociada
a la métrica 24** en `metric_dimensions` — por eso el export cae al fallback `Dim_{id}` en
`backend/routers/metrics.py`.

Consecuencia: un export → import de ida y vuelta **pierde esa columna en silencio**, porque el
import matchea por nombre de dimensión vigente. Hay que decidir si se asocia `Nombre_Norm` a la
métrica 24 o si se limpian esos valores.

---

## Parte 5 — Verificar después de cargar

1. **Valores** → seleccionar la métrica → revisar que aparezcan el año y el mes cargados, y
   que `PorcLogro` esté en rango 0–1 (no 0–100).
2. Contar filas por (Año, Mes, Asignatura, Nivel) y compararlas con lo que traía el Excel de
   origen. Si hay el doble, se cargó dos veces.
3. Abrir el dashboard del indicador 6 y confirmar que el nuevo mes aparece en el tab
   Tendencia.

### Fallas conocidas

- **`N Prueba = 0`** → el mes del archivo no está en el mapeo del paso 2. Ampliar el
  `ModifyColumnValues` del pipeline 26.
- **Datos duplicados** → se corrió el mismo mes dos veces (`clear_existing: false`).
- **Columna aparece vacía tras un import manual** → el encabezado no calza carácter por
  carácter con el nombre de la dimensión. El import no avisa.
