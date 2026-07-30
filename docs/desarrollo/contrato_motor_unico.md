# Contrato técnico — Motor único de informes (Fase 2)

**Fecha**: 2026-07-30 · **Rama**: `dev2` (HEAD `ef1c582`) · **Estado**: contrato cerrado, listo para fase 3
**Entradas vinculantes**: [plan_motor_unico_informes.md](./plan_motor_unico_informes.md) (arquitectura OK) · [fichas_informes_por_indicador.md](./fichas_informes_por_indicador.md) (**18 decisiones de Miguel**, fase 1 cerrada) · [inventario_indicadores_2026-07-30.md](./inventario_indicadores_2026-07-30.md) (estado real).

Este documento **no reabre decisiones**: desarrolla el contrato para que la fase 3 (piloto SIMCE) y la fase 4 (migración) se codifiquen sin decisiones abiertas. Todo lo que hoy **no existe** en el código está marcado `NUEVO`.

---

## 1 · Contrato del módulo

Un indicador = **un módulo** en `backend/rgenerator/reports/custom/<nombre>.py`. El registro (`custom/__init__.py`) lo auto-descubre con `pkgutil.iter_modules`; el nombre del archivo es su identificador público. El contrato **extiende** el actual (documentado en `custom/README.md` y `custom/_ejemplo.py`) de forma aditiva: un módulo que no declare los atributos nuevos se comporta exactamente como hoy.

### 1.1 Atributos

| Atributo | Tipo | Estado | Semántica |
|---|---|---|---|
| `LABEL` | `str` | existe | Título de la card "formato oficial" en el selector. Obligatorio. |
| `DESCRIPCION` | `str` | existe | Subtítulo de esa card. Obligatorio. |
| `FORMATO` | `"pdf"` \| `"word"` | existe | Content-Type y extensión por defecto. Los módulos del motor único son siempre `"pdf"`. |
| `ENGINE_TYPES` | `list[str] \| None` | existe | `Indicator.report_engine_type` a los que aplica (`None` = todos). Resuelto por `engine_types.resolver_engine_type` (campo > heurística por nombre). |
| `REQUIERE_FILTRO_TEMPORAL` | `list[str]` | existe | Dimensiones temporales que la card "formato oficial" exige. **No aplica al despacho por período**: ahí el filtro temporal lo pone `periodos.py`. |
| `REQUIERE_ASIGNATURA` | `bool` | existe | El informe cubre UNA asignatura. Declarativo; quien exige es el motor (`asignatura.resolver_seleccion`, vía `dispatch_v2` o llamada propia). |
| `FILENAME` | `str` | existe | Nombre de descarga; default `informe_<nombre>.pdf`. |
| **`MODOS`** | `list[str]` | **NUEVO** | Subconjunto de `periodos.TIPOS_PERIODO` = `("ultima_prueba", "semestral", "anual", "personalizado")` que el módulo sabe generar. **Ausente o `[]` ⇒ retrocompatibilidad total**: el módulo sigue siendo solo "formato oficial" y las cards de período usan el path v1. |
| **`MOTIVO_MODO_NO_DISPONIBLE`** | `dict[str, str]` | **NUEVO** | `{modo: motivo pedagógico}` para modos que el módulo **deliberadamente** no sirve. Solo se consulta cuando el módulo declara `MODOS` no vacío y el modo pedido no está en él. Sin entrada para ese modo se usa un genérico. |

```python
# Ejemplo real — módulo IDEL (decisión 7: 3 pruebas anuales, no hay semestre)
MODOS = ["ultima_prueba", "anual", "personalizado"]
MOTIVO_MODO_NO_DISPONIBLE = {
    "semestral": (
        "IDEL se aplica en 3 versiones anuales (v1/v2/v3) que no se reparten "
        "por semestre. Usa el informe de última versión o el anual."
    ),
}
```

### 1.2 Firma de `generar`

```python
def generar(
    db: Session, *,
    indicator_id: int,
    org_id: int,
    modo: str | None = None,          # NUEVO — None ⇒ "formato oficial" (comportamiento actual)
    filtros: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> bytes: ...
```

- **`modo`**: uno de `MODOS`, o `None`. `None` **debe** seguir produciendo el informe de hoy (lo invoca `POST /api/reports/custom/{nombre}`, que no manda `modo`). Un `modo` no soportado ⇒ `ValueError` con texto de usuario (el router lo traduce a 400).
- **`filtros`**: `{nombre_columna: valor | [valores]}` — **nombres de columna humanizados** (`"Asignatura"`, `"Mes"`, `"Año"`, `"Hito"`), tal como los devuelve `periodos.ResultadoPeriodo.filtros` y los consume `data.cargar_dataframes_indicator`. **Nunca ids de dimensión.** Ver §2.3.
- **`params`**: libres por informe (ej `{"incluir_detalle_por_curso": False}`). El motor único no los necesita para los 3 modos base.
- **`overrides`**: overrides de esquema/branding (`{"branding": {"center_header": [...], "left_footer": "..."}}`). El módulo **debe** pasar sus overrides por `dispatch_v2.aplicar_pie_organizacion(db, org_id, overrides)` antes de renderizar (regla dura del README: el pie izquierdo es el nombre de la organización).
- **Errores**: `DatosInsuficientes` / `ValueError` con mensaje accionable en español (→ 400); nunca traceback al usuario. Secciones individuales que fallan las absorbe `runtime._error_seccion` con el aviso neutro `AVISO_SECCION_FALLIDA`.

### 1.3 Reglas transversales que todo módulo debe cumplir

Vinculantes (decisiones de Miguel + QA 2026-07-30 ya implementado):

1. **Evolución auto-omitida** con un único punto temporal (decisión 16) — vía `seccion_evolucion` (§3.2).
2. **Detalle por alumno / por pregunta / por curso SOLO en `ultima_prueba`** (decisiones 1 y 5).
3. **Riesgo persistente** = nivel más bajo del indicador en las **2 últimas evaluaciones consecutivas**; va **al final del modo anual**, con curso y puntajes (criterio inicial calibrable en el piloto).
4. **Heatmaps, selectores y matrices de 2 filtros simultáneos fuera del PDF** (decisiones 3, 6; roster IDEL).
5. **Asignatura obligatoria** donde el indicador trae ≥2 valores (SIMCE / DIA / Panguipulli).
6. **Presentación**: `nan` → `"—"` (`helpers.MARCA_SIN_DATO`), 2 decimales (`helpers.DECIMALES_AJUSTE_ANCHO`), orden natural y temporal (`helpers.ordenar_valores_categoricos`). Ya está en `tables.py`/`charts.py`; los módulos no deben reimplementarlo.
7. **Un salto de página por curso** en las secciones iteradas — **ya lo emite `runtime.py:307-309`** (ver tensión T3).

---

## 2 · Flujo de despacho

### 2.1 Pseudocódigo — `POST /api/indicators/{id}/export-pdf`

```
body = {periodo: {tipo, fecha_inicio?, fecha_fin?, filtros?}, filters?, engine?, branding_override?}

1. record = Indicator(id, org_id)                                    # 404 si no existe
2. datos  = _cargar_dataframes_best_effort(db, id, org_id)           # existe
3. si body.periodo:
       tipo_layout, filtros_por_id, descripcion, RESULTADO = _resolver_periodo_a_filtros(...)
                                                             # NUEVO: devolver también `RESULTADO`
                                                             # 400 si no disponible (ya lo hace)
4. _validar_asignatura(...)                                          # existe → 400 accionable
5. modulo = custom.modulo_de_indicador(engine_type)                  # NUEVO (§2.4)
6. si body.engine explícito         → FALLBACK v1 (escape hatch consciente del usuario)
   si modulo is None                → FALLBACK v1 (comportamiento actual)
   si modo not in custom.modos(modulo)
                                    → 400 con custom.motivo_modo(modulo, modo)
                                       (no debería ocurrir: report-options ya deshabilitó la card)
   si no                            → DESPACHO AL MÓDULO (7)
7. overrides = {}
   si descripcion y no body.branding_override:
       overrides["branding"] = {"center_header": branding.reemplazar_ultima_linea(header, descripcion)}
   si body.branding_override: overrides["branding"] = body.branding_override
   pdf = modulo.generar(db, indicator_id=id, org_id=org_id,
                        modo=body.periodo["tipo"],
                        filtros=RESULTADO.filtros | filtros_usuario_por_columna,   # §2.3
                        params=None, overrides=overrides)
   except (DatosInsuficientes, ValueError) as e → HTTP 400 str(e)
8. Response(pdf, application/pdf, filename=informe_<record.name>.pdf)
```

**FALLBACK v1** = el camino actual intacto: `engine == "weasyprint"` → `report_steps.build_pdf_bytes(record, db, org_id, filters=<por id_dimension>, pdf_layout_override=...)`; `engine == "pdl_idel"` → `report_pdl_idel_tools.build_pdl_idel_pdf_bytes`. Se depreca en la fase 5, no antes.

**El frontend NO cambia**: sigue haciendo `POST .../export-pdf` con `{"periodo": {...}}`. La única diferencia visible es el campo `motor` de la card en `report-options` (informativo).

### 2.2 Precedencia

`body.engine` explícito > módulo custom que declara el modo > `pdf_layout.engine` > `weasyprint`.
Motivo: `body.engine` es un override consciente (modal de admin) y debe permitir comparar v1 vs módulo durante la migración.

### 2.3 Filtros: la traducción es el punto delicado

Hoy conviven dos espacios de nombres:

| Consumidor | Espacio de claves | Fuente |
|---|---|---|
| `report_steps.build_pdf_bytes` (v1) | `{id_dimension: valor}` | `_mapa_columna_a_dimension` + `_normalizar_filtros_a_dimensiones` |
| `data.cargar_dataframes_indicator` (v2 / módulos) | `{nombre_columna: valor}` | `periodos.ResultadoPeriodo.filtros` |

`_resolver_periodo_a_filtros` **ya calcula ambos** pero solo retorna el primero (`indicators.py:829-831`). **NUEVO**: ampliar su retorno a `(tipo_layout, filtros_por_id, descripcion, resultado)` — `resultado.filtros` son los nombres de columna que necesita el módulo. Los `periodo.filtros` del usuario que vienen por id de dimensión deben invertirse con el mismo `_mapa_columna_a_dimension` antes de pasarlos al módulo.

Sin este cambio el módulo recibiría `{"12": "MAYO"}` y `data.py` lo convertiría a `_12`, que no matchea ninguna columna ⇒ informe silenciosamente vacío. **Test obligatorio** (§5.2).

### 2.4 Cambios exactos en `custom/__init__.py`

Aditivos, sin romper el registro actual:

```python
MOTIVO_MODO_GENERICO = "Este indicador no genera este informe."   # fallback

def modos(mod) -> list[str]:
    """Modos declarados por el módulo. [] ⇒ solo 'formato oficial' (retrocompat)."""

def soporta_modo(mod, modo: str | None) -> bool:
    """True si `modo` está en MODOS. `modo=None` ⇒ False (eso es el path custom clásico)."""

def motivo_modo(mod, modo: str) -> str:
    """MOTIVO_MODO_NO_DISPONIBLE.get(modo) o MOTIVO_MODO_GENERICO."""

def modulo_de_indicador(engine_type: str | None):
    """Módulo del motor único para ese engine_type: el único registrado que
    aplica_a(engine_type) Y declara MODOS. None si no hay. Con más de uno,
    el primero por orden alfabético (y se loguea warning: es un error de config)."""
```

`metadata()` suma dos keys: `"modos": modos(mod)` y `"motivos_modo": dict(getattr(mod, "MOTIVO_MODO_NO_DISPONIBLE", {}))`. `listar_informes()` / `informes_para()` no cambian de firma.

### 2.5 Cambios exactos en `routers/indicators.py`

**a) `report_options` (líneas 441-494) — cards de período, aditivo:**

```
modulo = custom.modulo_de_indicador(engine_type)      # una vez, antes del loop
por cada card:
    si modulo and card["tipo"] in custom.modos(modulo):
        opcion["motor"] = f"custom:{nombre_modulo}"
        # el requisito de pdf_layout NO aplica: el módulo trae sus secciones
        motivo = (error_datos or resultado.motivo si no disponible)
    elif modulo:                                       # módulo existe pero NO declara el modo
        opcion["motor"] = f"custom:{nombre_modulo}"
        opcion["disponible"] = False
        motivo = custom.motivo_modo(modulo, card["tipo"])
    else:
        # comportamiento actual: exige tiene[card["layout"]], motor "weasyprint"
```

Consecuencia inmediata y deseada: **SIMCE Panguipulli pasa de 0/4 a 4/4** cards sin tocar su `pdf_layout` vacío, en cuanto su módulo declare `MODOS`.
El campo `asignatura` de la card se sigue publicando igual (`_descriptor_asignatura`) — el módulo lo consume vía `filtros`.

**b) `export_pdf` (líneas 947-1061):** insertar el bloque de despacho descrito en §2.1 **entre** la resolución del período y la validación de `tipo in ("evaluacion","historico")` — el módulo no usa `pdf_layout`, así que el 422 por "sin secciones configuradas" no debe aplicarle. Capturar `DatosInsuficientes`/`ValueError` → 400; el `except Exception` → 500 genérico ya existente se mantiene.

**c) `REPORT_ENGINES`**: no se toca (es el catálogo del modal de admin, sigue describiendo el path v1).

---

## 3 · Helpers compartidos propuestos

Todos `NUEVO`, a implementar en el piloto (fase 3) en `backend/rgenerator/reports/custom/_secciones.py` (prefijo `_` ⇒ el registro lo ignora, es el lugar canónico para helpers compartidos según el README). Todos son **puros**: reciben DataFrames y devuelven listas de dicts de sección con el formato que consume `runtime._ejecutar_seccion` (`{tipo, titulo, fn, df_input, params, break_before?}`).

### 3.1 Portada y cuadro resumen

```python
def secciones_portada(*, titulo: str, establecimiento: str | None,
                      asignatura: str | None, periodo_desc: str) -> list[dict]
```
Devuelve `[{tipo:"heading", ...}, {tipo:"page_break"}]` más el bloque de overrides de `title`/`subtitle`/`filters_label` del esquema. **Semántica** (decisión transversal de la ficha, §7): título = nombre del informe + asignatura/nivel cuando aplique; subtítulo = nombre del establecimiento; tercera línea = período resuelto. Hoy `templates/informe_base.html` (líneas 255-257) ya renderiza `title`/`subtitle`/`filters_label` pero **no** como página propia con salto — eso es lo nuevo.

```python
def seccion_resumen(df_key: str, *, columna: str, formato: str = "percent",
                    agrupar_por: str = "Curso", titulo: str) -> dict
```
Azúcar sobre `tables.resumen_estadistico_basico` (existe). `Alumnos` cuenta estudiantes distintos, ya resuelto en la función.

```python
def seccion_resumen_comparado(df_actual: str, df_previo: str, *, columna: str,
                              etiqueta_previo: str, ...) -> dict
```
Variante "+ columna semestre/año anterior" que piden las fichas de SIMCE/DIA/Panguipulli. Une dos `resumen_estadistico_basico` por `agrupar_por`; la columna previa sale `"—"` cuando no hay período anterior cargado.

### 3.2 Sección de evolución period-aware (decisión 16)

```python
def seccion_evolucion(seccion: dict, df: pd.DataFrame, columna_temporal: str) -> list[dict]
```
**Semántica**: si `df[columna_temporal].dropna().nunique() <= 1` devuelve `[]` (la sección se auto-omite, sin aviso de error ni gráfico de una sola serie). Con ≥2 puntos devuelve `[seccion]`. La columna temporal se detecta con `periodos.detectar_columnas_temporales_df(df, tipos)["mes_like"]` (existe) y se ordena con `helpers.ordenar_valores_categoricos` / `clave_orden_temporal` (existen).
Esto cierra de una vez el defecto compartido SIMCE + Panguipulli (P1.8 de la comparación, pregunta abierta 1 de la ficha 6).

> **Eje multi-año**: `_resolver_anual` fija un solo año, así que el colapso "mismo mes de años distintos" **no** afecta a los modos `anual`/`semestral`. Solo afecta a `personalizado` con rango multi-año. `NUEVO opcional`: `columna_periodo_compuesta(df, col_anio, col_mes) -> Series` que produce `"2025-10"` para usar como `agrupar_secundario_por`. Se implementa cuando se aborde `personalizado`, no bloquea el piloto.

### 3.3 Riesgo persistente

```python
def tabla_riesgo_persistente(
    df: pd.DataFrame, *,
    columna_nivel: str,            # "Logro" (SIMCE), "Nivel" (DIA/IDEL), "Nivel_Logro" (Panguipulli)
    nivel_objetivo: str,           # "Insuficiente" / "Crítico" / "INICIAL"
    columna_temporal: str,         # "Mes" / "Hito" / "Versión"
    n_evaluaciones: int = 2,
    columnas_puntaje: list[str] | None = None,   # ["Rend", "Simce"] → una columna por evaluación
) -> pd.DataFrame
```
**Semántica**: identidad del estudiante vía `helpers.serie_identidad_estudiante` (existe: RUT → Nombre_Norm → Nombre → Curso+N°Lista — cubre el RUT vacío de Cálculo Veloz). Se ordenan las evaluaciones con `clave_orden_temporal`, se toman las `n_evaluaciones` últimas **consecutivas presentes para ese estudiante**, y se incluye al estudiante si `columna_nivel == nivel_objetivo` en todas. Salida: `Curso · Estudiante · <puntaje eval n-1> · <puntaje eval n> · Nivel`, ordenada por curso (orden natural) y puntaje ascendente. Sin segunda evaluación ⇒ DataFrame vacío ⇒ la sección se omite igual que la evolución.

### 3.4 Iteración por curso

```python
def secciones_por_curso(secciones: list[dict], *, df_iterar: str,
                        iterar_por: str = "Curso") -> dict
```
Devuelve el bloque `secciones_dinamicas` del esquema (`{"iterar_por", "df_iterar", "secciones"}`). El runtime ya hace el orden natural (`ordenar_valores_categoricos`) y el `page_break` por valor. Existe solo para que los módulos no repitan la estructura ni la olviden.

### 3.5 Puente esquema-en-memoria (habilitante, NUEVO)

`runtime.construir_pdf(report_type, ...)` **exige** un `<report_type>/esquema.json` en disco (`runtime.py:220-222`). Los módulos del motor único construyen sus secciones en Python y varían por modo, y Cálculo Veloz / Fluidez Lectora no tienen carpeta de esquema.

**Cambio mínimo**: parámetro opcional `esquema: dict | None = None` en `construir_pdf`; cuando viene, se salta la lectura de disco y se usa tal cual (el resto del flujo — derived_fields, branding, secciones fijas, dinámicas, WeasyPrint — no cambia). Retrocompatible: sin el parámetro, el comportamiento es idéntico.
Alternativa descartada: pasar las secciones por `overrides` (funciona por accidente del merge superficial, pero solo para tipos que ya tienen esquema en disco).

---

## 4 · Especificación ejecutable — PILOTO SIMCE

Módulo: `backend/rgenerator/reports/custom/simce.py` (hoy es un wrapper de 46 líneas sobre `dispatch_v2`; se le agrega el camino por modo **sin quitar** el actual).

```python
MODOS = ["ultima_prueba", "semestral", "anual", "personalizado"]
MOTIVO_MODO_NO_DISPONIBLE = {}          # SIMCE sirve los 4
REQUIERE_ASIGNATURA = True              # ya está
```

**DataFrames que arma el módulo** (mismas keys que el esquema actual, ver `simce/crear_informe.py:114-119`):

| Key | Contenido |
|---|---|
| `estudiantes` | metric 4, filtrada por asignatura, **todas** las pruebas (base de derived_fields) |
| `estudiantes_periodo` | `estudiantes` recortado al período del modo (`NUEVO`; en `ultima_prueba` == `estudiantes_prueba`) |
| `estudiantes_prueba` | recortado a **una** prueba (última del período) |
| `preguntas` / `preguntas_periodo` / `preguntas_prueba` | ídem sobre metric 5 |

`derived_fields` (`Logro_Promedio_Estudiante`, `Avance`, `Mejora_vs_Inicio`) se aplican sobre `estudiantes` **antes** de recortar — regla ya implementada y comentada en `runtime.py:243-249`; no cambiar.

### 4.1 Modo `ultima_prueba`

| # | Sección | Fuente | `df_input` | Params clave |
|---|---|---|---|---|
| 1 | Portada | `secciones_portada` **NUEVO** | — | título + establecimiento + asignatura + período |
| 2 | Resumen de Logro por Curso | `tables.resumen_estadistico_basico` | `estudiantes_prueba` | `columna="Rend", formato="percent", agrupar_por="Curso"` |
| 3 | Resumen de Puntaje SIMCE por Curso | `tables.resumen_estadistico_basico` | `estudiantes_prueba` | `columna="Simce", formato="number"` |
| 4 | Rendimiento Promedio por Curso | `charts.grafico_barras_promedio_por` | `estudiantes_prueba` | `columna_valor="Rend", agrupar_por="Curso"` |
| 5 | Distribución de Puntaje SIMCE por Curso | `charts.boxplot_valor_por_curso` | `estudiantes_prueba` | `columna_valor="Simce", formato="number"` |
| 6 | Cantidad de Alumnos por Nivel y Curso | `charts.alumnos_por_nivel_cualitativo` | `estudiantes_prueba` | `columna_nivel="Logro", lista_niveles=["Adecuado","Elemental","Insuficiente"]` |
| 7 | Composición Global por Nivel | `charts.composicion_por_nivel` **NUEVO** (torta/donut; no existe gráfico de composición en `CHART_REGISTRY`) | `estudiantes_prueba` | `columna_nivel="Logro"`, mismos colores semáforo que #6 |
| 8 | Logro Promedio por Habilidad | `charts.valor_promedio_agrupado_por` | `preguntas_prueba` | `columna_valor="Logro", Curso × Habilidad, formato="percent"` |
| 9 | Logro Promedio por Eje Temático | `charts.valor_promedio_agrupado_por` | `preguntas_prueba` | `columna_valor="Logro", Curso × "Eje Temático"` |
| 10 | Estudiantes en Riesgo | `tables.tabla_logro_por_alumno` | `estudiantes_prueba` | `parametros={"Logro": "Insuficiente"}, columnas=["Curso","Nombre","Rend","Simce"]` |
| 11 | Estadística por Pregunta del Establecimiento | `tables.crear_tabla_estadistica_por_pregunta` | `preguntas_prueba` | `break_before=true`, alternativas A-E |
| 12 | **Por curso** (`secciones_por_curso`, `df_iterar="estudiantes_prueba"`): Logro por Alumno (`tables.tabla_logro_por_alumno`) + Logro por Pregunta (`tables.tabla_logro_por_pregunta`) | existen | `estudiantes_prueba` / `preguntas_prueba` | idéntico al `esquema.json` actual (líneas 188-231) |

Cambio respecto al `simce/esquema.json` vigente: #8 y #9 pasan de `preguntas` (todo el año) a `preguntas_prueba`; y se quitan de este modo las dos secciones "Evolución … por Curso y Mes" (hoy fijas, líneas 100-128) — pasan al bloque de evolución de §4.2. Eso cierra P1.8 de la comparación con la referencia.

### 4.2 Modos `semestral` y `anual`

Idénticos entre sí salvo el recorte del período (lo fija `periodos.py`) y la última sección.

Secciones **1 a 9** de §4.1, con `df_input` = `estudiantes_periodo` / `preguntas_periodo` (promedios de todas las pruebas del período), y #2 en variante comparada (`seccion_resumen_comparado` **NUEVO** — columna del semestre/año anterior).

Luego el **bloque de evolución**, cada sección envuelta en `seccion_evolucion(...)` **NUEVO** (se auto-omite con 1 punto):

| # | Sección | Fuente | `df_input` | Params |
|---|---|---|---|---|
| 10 | Evolución del Logro Promedio por Curso y Mes | `charts.valor_promedio_agrupado_por` | `estudiantes_periodo` | `Rend`, Curso × Mes, `formato="percent"`, `y_lims=[0,1]` |
| 11 | Evolución del Puntaje SIMCE por Curso y Mes | `charts.valor_promedio_agrupado_por` | `estudiantes_periodo` | `Simce`, Curso × Mes, `formato="number"` |
| 12 | Evolución de Niveles por Curso y Mes | `charts.alumnos_por_nivel_curso_y_mes` | `estudiantes_periodo` | `columna_nivel="Logro", columna_curso="Curso", columna_mes="Mes"` |

**Solo en `anual`**, al final (decisión 2):

| 13 | Estudiantes en Riesgo Persistente | `tabla_riesgo_persistente` **NUEVO** | `estudiantes_periodo` | `nivel_objetivo="Insuficiente", columna_temporal="Mes", n_evaluaciones=2, columnas_puntaje=["Rend","Simce"]` |

**Excluidas de semestral/anual** (decisión 1): Estadística por Pregunta (#11) y todo el bloque por curso (#12). **Excluido de todos los modos** (decisión 3): heatmap Curso × Eje (spec 111).

### 4.3 Modo `personalizado`

Mismas secciones que `anual`. `periodos._resolver_personalizado` decide el rango y `tipo_layout`; si el rango resuelve a un solo punto temporal el bloque de evolución se auto-omite y el informe queda equivalente a `ultima_prueba` sin el detalle por curso. Sin decisiones adicionales.

---

## 5 · Plan de tests

Capas y fixtures existentes: `db_session`, `client`, `client_auth`, `org` (`tests/conftest.py`), factories `make_indicator/make_metric/make_metric_data` (`tests/factories.py`), y el fixture local `simce_indicator` de `tests/reports/test_dispatch_v2.py:98` — **promoverlo a `tests/conftest.py`** para reusarlo (`NUEVO`, refactor menor).

### 5.1 Smoke por módulo y por modo — `tests/reports/test_<modulo>_modos.py` (NUEVO)

Sin renderizar PDF (WeasyPrint no está en todos los hosts, ver `runtime.py:32-34`): se testea la **lista de secciones**, exponiendo en cada módulo una función interna `_secciones(modo, dataframes) -> tuple[list, dict]`.

- `test_modos_declarados` — `MODOS` ⊆ `periodos.TIPOS_PERIODO`.
- `test_estructura_<modo>` — títulos y **orden exacto** de §4.1/§4.2; toda `fn` referenciada existe en `CHART_REGISTRY`/`TABLE_REGISTRY`; todo `df_input` está en el dict de dataframes.
- `test_detalle_por_curso_solo_en_ultima_prueba` — `secciones_dinamicas` presente en `ultima_prueba`, ausente en semestral/anual (decisión 1).
- `test_evolucion_se_omite_con_un_punto` — df con un solo `Mes` ⇒ ninguna sección de evolución (decisión 16).
- `test_riesgo_persistente_solo_en_anual_y_al_final` — presente y última en `anual`; ausente en el resto.
- `test_modo_desconocido_levanta_valueerror` con mensaje en español.
- `test_render_pdf` marcado `@pytest.mark.slow`, con `patch` de `runtime.construir_pdf` para verificar que se le pasa el `esquema`/`df_principal` correcto (patrón ya usado en `test_dispatch_v2.py:128`).

### 5.2 Tests del despacho — `tests/reports/test_despacho_modos.py` (NUEVO)

- **report-options**: indicador con módulo ⇒ card marcada `motor: "custom:<nombre>"`; indicador sin módulo ⇒ `"weasyprint"` y la exigencia de `pdf_layout` intacta.
- **modo no declarado ⇒ card deshabilitada**: indicador IDEL ⇒ card semestral con `disponible: false` y `motivo_no_disponible == MOTIVO_MODO_NO_DISPONIBLE["semestral"]`.
- **Panguipulli sin `pdf_layout`**: las 4 cards salen disponibles gracias al módulo (regresión del hueco 0/4 del inventario).
- **export-pdf delega**: `patch` del `generar` del módulo; assert de que se llamó con `modo` correcto y `filtros` con **nombres de columna** (`{"Mes": "ABRIL", "Año": "2026", "Asignatura": "Lenguaje"}`), no ids — el test que blinda §2.3.
- **fallback v1**: indicador sin módulo ⇒ se llama `build_pdf_bytes`; y con `body.engine="weasyprint"` sobre un indicador **con** módulo ⇒ también v1.
- **retrocompat**: `POST /api/reports/custom/simce` (sin `modo`) sigue devolviendo el formato oficial de hoy; `test_custom_registry.py` sigue verde (módulos sin `MODOS` no cambian de metadata salvo las dos keys nuevas).
- **errores**: módulo que levanta `DatosInsuficientes` ⇒ 400 con el texto; módulo que levanta `Exception` ⇒ 500 saneado.

### 5.3 Gate de QA visual por migración

Por cada módulo migrado, antes de dar la migración por cerrada:

1. `python scripts/generar_ejemplos_informes.py` (dentro del contenedor backend, contra la DB canónica `report_generator-db-1`) ⇒ un PDF por card disponible en `data/tmp/ejemplos_informes/`. **Criterio**: 0 ERROR en la tabla resumen y ninguna card que antes estaba disponible pase a fallar.
2. Skill `/quality-review` sobre los PDFs de los 3 modos ⇒ reporte en `docs/reportes/calidad_<indicador>_<fecha>.md`.
3. Diff visual contra la referencia cuando exista (SIMCE: `docs/reportes/comparacion_simce_referencia_2026-07-30.md`; IDEL: §6).
4. `pytest -q -m "not slow"` verde + `pytest tests/reports -v`.

---

## 6 · Orden de migración

Fase 3 = **SIMCE** (§4). Fase 4 en este orden:

### 6.1 DIA — `custom/dia.py`
`MODOS` los 4. Reusa todo el patrón de familia A. Secciones de la ficha 2 con `charts.grafico_barras_promedio_por` (Logro por Nivel y por Curso), `boxplot_valor_por_curso`, `alumnos_por_nivel_cualitativo`, `valor_promedio_agrupado_por` (Eje/Habilidad), y en histórico `charts.comparacion_logro_por_curso` (existe y está en `CHART_REGISTRY`, hoy sin uso en `dia/esquema.json`) alimentado por `tables.crear_df_comparacion` — ojo: **`crear_df_comparacion` NO está en `TABLE_REGISTRY`**, así que no se puede referenciar como `fn` de una sección; el módulo debe llamarla en Python para armar el df `comparacion` y pasarlo como un `df_input` más (o registrarla, decisión del implementador).
Pendientes: **Comparativa Establecimientos fuera del PDF** (decisión 4 — va a ROADMAP como gráfico aparte); detalle por curso/pregunta solo en `ultima_prueba` (decisión 5); heatmap excluido (decisión 6); **encabezado con 2 establecimientos** — no puede fijar un escudo único: usar solo `logo_php.png` a la izquierda y omitir `right_image` cuando el df trae >1 establecimiento (`branding.valor_unico` ya devuelve `None` en ese caso).

### 6.2 IDEL — `custom/pdl_idel.py`
`MODOS = ["ultima_prueba", "anual", "personalizado"]` + `MOTIVO_MODO_NO_DISPONIBLE["semestral"]` (decisión 7).
**Base del módulo = `scripts/report_pdl_idel.py`** (decisión 9), hoy invocado vía `tooling/report_pdl_idel_tools.build_pdl_idel_pdf_bytes`. Es matplotlib puro (no WeasyPrint): el módulo mantiene ese motor y solo lo hace period-aware — no se porta a `runtime.construir_pdf` en esta fase.

**Referencia de layout**: `C:\Users\magod\Desktop\PDF_test\referencias\referencia_idel_panguipulli_2025.pdf` (35 págs — panorama global con mapa de riesgo + cobertura; luego iteración por curso con distribución por evaluación, promedios/medianas por subprueba, grilla de boxplots 2×3 y matrices de transición). Corresponde a `render_panorama` / `render_course_page_a` / `render_course_page_b` / `render_course_page_transitions` / `render_course_page_persistent` / `render_course_roster` del script.

> ⚠️ **CAVEAT VINCULANTE**: ese PDF es del **2026-04-22**, anterior a la corrección del glosario oficial de subpruebas (**2026-05-06**, ver `CLAUDE.md` § "Siglas IDEL"). Trae etiquetas históricas **erróneas** (FNL como "Segmentación fonémica", FLO como "Fluidez lectora"). **La referencia vale para layout y estructura, NO para nombres.** El módulo debe usar el glosario oficial — CT Comprensión de Textos · FLO Fluidez en la Lectura Oral · FNL Fluidez en Nombrar Letras · FSF Fluidez en Segmentación de Fonemas · ILP Identificación de Letras y Palabras · VSD Vocabulario Sobre Dibujos — como ya hace la versión vigente de `scripts/report_pdl_idel.py` (`SUBPRUEBAS_LABEL`, líneas 96-107). Cualquier QA visual que compare contra el PDF de referencia debe reportar las diferencias de etiqueta como **conformidad**, no como defecto.

Otros pendientes: eje temporal = **Versión**, no Mes (`periodos.VERSION_A_MES` ya lo mapea); roster fuera del PDF impreso (2 filtros simultáneos) salvo el `render_course_roster` por curso ya existente, que sí va (decisión 8); "Cuadro Resumen Puntaje por Curso" se mantiene ad-hoc (decisión 9); 5°/6° básico sin v3 (nota de protocolo).

### 6.3 SIMCE Panguipulli — `custom/simce_panguipulli.py`
`MODOS` los 4. Es el clon de SIMCE con una dimensión menos (sin Eje Temático — decisión 17: se revisa más adelante si es del instrumento EMN Aptus o hueco de carga) y nombres de campo distintos (`PorcLogro`/`Nivel_Logro` en vez de `Rend`/`Logro`). **Ganancia inmediata**: pasa de 0/4 a 4/4 cards sin configurar `pdf_layout`. Hereda el fix de evolución (`seccion_evolucion`) que hoy dibuja siempre los 2 gráficos de tendencia. Sin datos 2026 ⇒ semestral/anual "no disponible con motivo" es correcto (decisión 18).

### 6.4 Cálculo Veloz — `custom/calculo_veloz.py` (módulo nuevo, decisión 10)
`MODOS` los 4. Requiere setear `Indicator.report_engine_type = "calculo_veloz"` en DB (hoy vacío y `inferir_engine_type` no lo reconoce). Identidad por Nombre (RUT 100% vacío) — `helpers.serie_identidad_estudiante` ya degrada correctamente. Riesgo persistente **sí** (decisión 11, `nivel_objetivo` = "INICIAL"/"BÁSICO"); listado redundante (spec 121) descartado (decisión 12). Sin datos 2026 ⇒ semestral/anual no disponibles con motivo (decisión de plan 4).

### 6.5 Fluidez Lectora — `custom/fluidez_lectora.py` (módulo nuevo)
`MODOS` los 4. Requiere `report_engine_type = "fluidez_lectora"`. El prerequisito estructural **ya está resuelto** en `dev2`: el tipo de dato de dimensión "fecha" y la derivación de año desde `Fecha` están en `periodos.py` (commit `41322c9`, `TIPOS_DATO_FECHA`/`es_columna_fecha`) y el layout histórico se corrigió en `ef1c582`. Van **ambas** distribuciones, Categoría y Calidad Lectora (decisión 15); heatmaps excluidos. Semestral/anual se **diseñan completos** y degradan con gracia con una sola medición (decisión 13) — es decir, el bloque de evolución se auto-omite hasta que exista un segundo Ensayo.
**Trabajo extra fuera del motor** (decisión 14): crear el **tab Tendencia en el dashboard** de FL, para respetar la regla "toda sección del PDF viene de un componente real". Es trabajo de `indicators.dashboard_layout` + `specs`, no del módulo — ver `/add-chart`.

### 6.6 Fase 5 — cierre
Retirar el path v1 de las cards de período (dejar `build_pdf_bytes` solo detrás de `body.engine` explícito), smoke por modo de los 6 módulos, y actualizar `custom/README.md` + `_ejemplo.py` con `MODOS`/`MOTIVO_MODO_NO_DISPONIBLE`.

---

## 7 · Inventario de lo `NUEVO` (todo lo que construye la fase 3+)

| # | Qué | Dónde | Fase |
|---|---|---|---|
| N1 | `MODOS`, `MOTIVO_MODO_NO_DISPONIBLE`, `modo=` en `generar` | cada `custom/*.py` | 3-4 |
| N2 | `modos()`, `soporta_modo()`, `motivo_modo()`, `modulo_de_indicador()`, 2 keys en `metadata()` | `custom/__init__.py` | 3 |
| N3 | Despacho a módulo en `export_pdf` + `motor` por card en `report_options` | `routers/indicators.py` | 3 |
| N4 | `_resolver_periodo_a_filtros` devuelve también el `ResultadoPeriodo` (filtros por nombre de columna) | `routers/indicators.py` | 3 |
| N5 | Parámetro `esquema: dict \| None` en `construir_pdf` (esquema en memoria) | `reports/runtime.py` | 3 |
| N6 | `secciones_portada`, `seccion_resumen`, `seccion_resumen_comparado`, `seccion_evolucion`, `tabla_riesgo_persistente`, `secciones_por_curso` | `custom/_secciones.py` | 3 |
| N7 | `charts.composicion_por_nivel` (torta/donut) + entrada en `CHART_REGISTRY` | `reports/charts.py` | 3 |
| N8 | `columna_periodo_compuesta` (eje Año-Mes para `personalizado` multi-año) | `reports/helpers.py` | 4 (opcional) |
| N9 | Fixture `simce_indicator` promovido a `conftest.py` | `tests/conftest.py` | 3 |
| N10 | `tests/reports/test_despacho_modos.py` + `test_<modulo>_modos.py` ×6 | `tests/reports/` | 3-4 |
| N11 | `report_engine_type` de Cálculo Veloz y Fluidez Lectora seteado en DB | script one-shot | 4 |
| N12 | Tab **Tendencia** en el dashboard de Fluidez Lectora | `indicators.dashboard_layout` + `specs` | 4 |

---

## 8 · Tensiones detectadas (para resolución del orquestador)

**T1 · `construir_pdf` exige esquema en disco.** La decisión de arquitectura dice "los módulos construyen listas de secciones por modo reutilizando runtime/charts/tables", pero `runtime.py:220-222` lee `<report_type>/esquema.json` y aborta con `FileNotFoundError` si no existe. Cálculo Veloz y Fluidez Lectora no tienen carpeta. **Resolución propuesta**: N5 (parámetro `esquema` opcional), retrocompatible y de bajo riesgo. Sin él, la fase 3 tendría que crear carpetas de esquema vacías como andamiaje.

**T2 · No existe ningún gráfico de composición (torta) en el motor v2.** `CHART_REGISTRY` tiene 6 funciones y ninguna es de composición global, pero **las 6 fichas** incluyen "Composición Global por Nivel" en los 3 modos. Es la única sección de las fichas sin fuente real. **Resolución propuesta**: N7 en el piloto (la comparten los 6 módulos). Alternativa de menor esfuerzo: sustituirla por una barra apilada única — pero se aleja de la referencia oficial.

**T3 · La ficha declara como defecto algo ya implementado.** El §7 de las fichas y el punto P1.7 de `comparacion_simce_referencia_2026-07-30.md` dicen que falta el salto de página por curso; `runtime.py:307-309` lo emite desde el commit `c90459f` (2026-05-03) y los 3 esquemas usan `secciones_dinamicas`. **Acción**: verificar en el QA visual del piloto; si el PDF sale bien paginado, corregir la ficha en vez de programar nada.

**T4 · `tabla_logro_por_alumno` filtra solo por igualdad escalar.** `tables.py:154-156` hace `df[key] == value`; la sección "Estudiantes en Riesgo" de Cálculo Veloz necesita `Nivel ∈ {INICIAL, BÁSICO}` (dos valores). **Resolución propuesta**: extender `parametros` para aceptar listas usando `filtering.matches` (existe y es la fuente de verdad de la semántica multi-valor). Cambio de 3 líneas, retrocompatible; se hace en la migración de CV, no en el piloto.

**T5 · La ficha SIMCE agrega Habilidad y Eje "sin filtro de curso"; el esquema vigente los cruza por Curso.** `simce/esquema.json:145-170` usa `agrupar_principal_por="Curso"` (barras agrupadas Curso × Habilidad), que es lo que valida la referencia Pullinque. La §4.1 mantiene el comportamiento **del esquema** (cruzado por Curso) por paridad visual. Si Miguel quería literalmente el agregado del establecimiento sin cursos, es un cambio de una línea — pero cambia el informe ya validado.

**T6 · `REQUIERE_FILTRO_TEMPORAL` queda ambiguo en el nuevo mundo.** Hoy la UI lo usa para exigir un filtro antes de habilitar la card "formato oficial". En el despacho por período el filtro temporal lo pone `periodos.py`, así que el atributo **no debe consultarse** en ese camino. Documentado en §1.1; conviene renombrarlo mentalmente como "requisito de la card formato oficial" y no tocarlo hasta la fase 5.

---

## OK de fase 2 (Miguel, 2026-07-30) — con una salvedad vinculante

**SIN portada de página completa.** El helper de "portada" es solo un **bloque de título** (título + subtítulo + período resuelto) en la primera página, seguido inmediatamente del contenido — igual que todos los PDF de referencia entregados (Pullinque, IDEL Panguipulli). Ninguna página dedicada exclusivamente a portada.

## Resoluciones de tensiones (orquestador, 2026-07-30)

- **T1 → APROBADO N5**: `runtime.construir_pdf` gana el parámetro `esquema: dict | None` (retrocompatible; con `None` sigue leyendo el JSON de disco). Se implementa en el piloto.
- **T2 → APROBADO N7, como barra apilada 100% horizontal** (no torta): más legible con 3-5 niveles, consistente con los componentes existentes y con los colores de `achievement_levels`. Nombre: `composicion_por_nivel`. Se implementa en el piloto.
- **T3 → SE CORRIGE LA FICHA, no el código**: el salto de página por curso ya existe desde c90459f; la observación de la ficha era obsoleta.
- **T4 → APROBADO**: fix de `tabla_logro_por_alumno` con `filtering.matches` (filtros multi-valor), programado para la migración de Cálculo Veloz (fase 4).
- **T5 → GANA EL ESQUEMA VIGENTE** (Habilidad/Eje cruzados por Curso): la paridad con la referencia Pullinque validada por el dueño pesa más que la propuesta de la ficha. Ficha anotada.
- **T6 → APROBADO tal como quedó documentado**: `REQUIERE_FILTRO_TEMPORAL` no se consulta en el despacho por período; limpieza formal en fase 5.
