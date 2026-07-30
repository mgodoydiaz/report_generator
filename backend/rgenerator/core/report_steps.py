"""Steps de generación de reportes: PDF (motor v1 indicador + motor v2 HTML).

Tras la limpieza B6b post-v0.2.0 quedaron solo `RenderPDFReport` (motor
viejo basado en indicator.pdf_layout, usado por el botón Generar Reporte
en /results) y `RenderHtmlReport` (motor moderno paridad LaTeX vía
WeasyPrint, usado por el endpoint /api/reports/{tipo}). Steps removidos:

- `GenerateGraphics`: generaba PNG con matplotlib y los dejaba en
  filesystem. Reemplazado por _chart_to_png_b64 + base64 inline en el
  motor v2.
- `GenerateTables`: generaba XLSX intermedios. Reemplazado por
  `_table_section` que renderiza HTML directo en el PDF.
- `RenderReport` (LaTeX): legacy, requería pdflatex. Migrado a
  `RenderHtmlReport` (WeasyPrint, paridad visual).
- `GenerateDocxReport`: docx2pdf frágil en Linux/Docker. Sin uso real.
"""

# Librerias estandar
from pathlib import Path
import os
import json
import pandas as pd
from typing import Optional, Dict, List

# Importaciones internas de RGenerator
from .step import Step
from ..reports.filtering import matches
from backend.config import REPORTS_TEMPLATES_DIR


# ─────────────────────────────────────────────────────────────────────────
# Paletas LaTeX-paridad (ver docs/desarrollo/visual_vocabulary_dia.md).
# Usadas por _chart_to_png_b64 para alinear la estética de los gráficos
# embebidos en el PDF con el LaTeX referencia (Set2 + tab10 + semáforo
# negro/grises). NO introducir paletas adicionales sin actualizar el doc.
# ─────────────────────────────────────────────────────────────────────────
def _hex_from_rgba(rgba):
    r, g, b = rgba[0], rgba[1], rgba[2]
    return '#{:02x}{:02x}{:02x}'.format(int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


# Construidas perezosamente la primera vez que se llama _chart_to_png_b64,
# para no importar matplotlib al cargar el módulo (los pipelines que no
# generan PDFs no deberían pagarlo).
_PALETTE_CATEGORICAL = None  # Set2 (8 pasteles)  — categórico general
_PALETTE_BOXPLOT = None       # tab10 (10 saturados) — boxplots por categoría
PALETTE_SEMAFORO = {
    'Avanzado':       '#1f9e89', 'Adecuado':       '#1f9e89', 'Bajo Riesgo':   '#1f9e89',
    'Intermedio':     '#f1a340', 'Elemental':      '#f1a340', 'Cierto Riesgo': '#f1a340',
    'Inicial':        '#e64b35', 'Insuficiente':   '#e64b35', 'Crítico':       '#e64b35',
}
SEMAFORO_FALLBACK_ORDER = ['#e64b35', '#f1a340', '#1f9e89']  # rojo→naranja→verde por orden ordinal

MPL_RCPARAMS_LATEX = {
    'font.family': ['Segoe UI', 'Inter', 'DejaVu Sans'],
    'font.size': 9,
    'axes.titlesize': 10,
    'axes.labelsize': 9,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
}

CHART_DPI = 300


def _ensure_palettes():
    """Inicializa Set2 y tab10 a partir de matplotlib la primera vez."""
    global _PALETTE_CATEGORICAL, _PALETTE_BOXPLOT
    if _PALETTE_CATEGORICAL is None:
        import matplotlib.pyplot as plt  # noqa: WPS433
        _PALETTE_CATEGORICAL = [_hex_from_rgba(c) for c in plt.cm.Set2.colors]
        _PALETTE_BOXPLOT = [_hex_from_rgba(c) for c in plt.cm.tab10.colors]
    return _PALETTE_CATEGORICAL, _PALETTE_BOXPLOT


def _semaforo_color(level: str, ordinal_index: int = 0) -> str:
    """Retorna color semáforo para un nivel. Si no matchee, usa orden ordinal."""
    if level in PALETTE_SEMAFORO:
        return PALETTE_SEMAFORO[level]
    return SEMAFORO_FALLBACK_ORDER[ordinal_index % len(SEMAFORO_FALLBACK_ORDER)]


# ── Helpers compartidos para RenderPDFReport ─────────────────────────────────

def _to_field_name(name: str) -> str:
    """Normaliza el nombre de una columna a un field key con prefijo `_`.

    Quita tildes/acentos primero (NFKD + ASCII) para que 'Versión' se mapee a
    `_version` y no a `_versi_n`. Después minúsculas y reemplazo de no-alfanum.
    """
    import re
    import unicodedata
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    s = s.strip().lower()
    s = re.sub(r'[^a-z0-9_]', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return f'_{s}'


def _role_format_for_field(field: str, column_roles: dict, role_formats: dict) -> str:
    """Dado un field name (ej `_rend`), devuelve el format del rol que lo
    contiene (`'percent'`, `'number'`, etc.). Devuelve `'number'` por default.
    """
    if not isinstance(field, str) or not field.startswith('_'):
        return 'number'
    # Buscar role cuya primera columna se mapea a este field
    for role, entries in (column_roles or {}).items():
        if not isinstance(entries, list) or not entries:
            continue
        first = entries[0]
        if isinstance(first, dict):
            col = first.get('column', '')
            if col and _to_field_name(col) == field:
                return (role_formats or {}).get(role, 'number')
    return 'number'


def _format_value(val, fmt: str) -> str:
    """Formatea un valor numérico según el format del rol."""
    if val is None:
        return '—'
    try:
        v = float(val)
    except (TypeError, ValueError):
        return str(val)
    if fmt == 'percent':
        # Si el valor está entre 0 y 1, asumir fracción (0.65 → 65%)
        # Si está entre 1 y 100, asumir ya en escala (65 → 65%)
        if -1.5 <= v <= 1.5:
            return f'{v * 100:.0f}%'
        return f'{v:.0f}%'
    return f'{v:.1f}'


_KNOWN_ROLES = {
    'logro_1', 'logro_2', 'nivel_de_logro', 'habilidad', 'habilidad_2',
    'evaluacion_num', 'calidad_lectora',
}


def _resolve_field(field, column_roles: dict):
    """Si field es '_<role>' donde role está en column_roles, devuelve la columna real
    (ej '_logro_1' → '_cantidad'). Si es lista, mapea cada elemento. Si no aplica,
    devuelve el valor original."""
    if isinstance(field, list):
        return [_resolve_field(f, column_roles) for f in field]
    if not isinstance(field, str) or not field.startswith('_'):
        return field
    role = field[1:]
    if role not in _KNOWN_ROLES:
        return field
    entries = (column_roles or {}).get(role)
    if isinstance(entries, list) and entries:
        first = entries[0]
        col = first.get('column') if isinstance(first, dict) else None
        if col:
            return _to_field_name(col)
    return field


# Clave técnica que `_build_records` inyecta en cada record con la métrica de
# origen. NO es un campo de negocio: los consumidores que renderizan columnas
# dinámicamente (ej tabla plana sin flatTableConfig) deben excluirla.
METRIC_ID_KEY = '_metric_id'


def metric_id_del_rol(column_roles: dict, rol: str) -> Optional[int]:
    """Métrica de origen de un rol: `entries[0].metric_id` de `column_roles`.

    Misma convención que `_resolve_field`, que ya privilegia la primera entrada
    del rol para resolver el nombre de columna. Devuelve None si el rol no
    existe, está vacío o su primera entrada no declara `metric_id`.
    """
    entries = (column_roles or {}).get(rol)
    if not isinstance(entries, list) or not entries:
        return None
    first = entries[0]
    if not isinstance(first, dict):
        return None
    mid = first.get('metric_id')
    if mid is None:
        return None
    try:
        return int(mid)
    except (TypeError, ValueError):
        return None


def rol_de_campo(column_roles: dict, field) -> Optional[str]:
    """Rol cuya primera columna se mapea al field dado (ej `_nivel_logro` →
    `'nivel_de_logro'`). Devuelve None si ningún rol conocido lo produce.

    Se usa para saber de qué métrica proviene el campo que un gráfico está
    contando: el levelField/categoryField puede apuntar a un rol distinto de
    `nivel_de_logro` (ej `_habilidad` en Fluidez Lectora).
    """
    if not isinstance(field, str) or not field.startswith('_'):
        return None
    for rol, entries in (column_roles or {}).items():
        if not isinstance(entries, list) or not entries:
            continue
        first = entries[0]
        if isinstance(first, dict):
            col = first.get('column', '')
            if col and _to_field_name(col) == field:
                return rol
    return None


def filtrar_records_por_metrica(records: list, metric_id: Optional[int]) -> list:
    """Deja solo los records provenientes de `metric_id`.

    Un indicador puede vincular varias métricas cuya misma columna se proyecta
    al mismo field (ej DIA: metric 6 "por estudiante" y metric 7 "por Pregunta"
    ambas con "Nivel Logro"). Contar sin distinguir la métrica de origen suma
    preguntas como si fueran alumnos.

    Degrada a los records tal cual (fail-open) cuando `metric_id` es None,
    cuando ningún record trae la clave `_metric_id` (compat con tests/configs
    viejos que construyen records a mano) o cuando el filtro dejaría el
    conjunto vacío — preferimos el conteo inflado a un gráfico en blanco.
    """
    if metric_id is None or not records:
        return records
    if not any(METRIC_ID_KEY in r for r in records):
        return records
    filtrados = [r for r in records if r.get(METRIC_ID_KEY) == metric_id]
    return filtrados or records


def rol_de_campo_de_valor(column_roles: dict, field_original,
                          field_resuelto=None) -> Optional[str]:
    """Rol de un campo de VALOR, aceptando el alias de rol o el field resuelto.

    Los layouts escriben indistintamente `'_logro_1'` (alias del rol) o
    `'_logro'` (la columna ya resuelta). El primero se lee directo del nombre;
    el segundo se busca contra las columnas de los roles (`rol_de_campo`).
    """
    if (isinstance(field_original, str) and field_original.startswith('_')
            and field_original[1:] in _KNOWN_ROLES):
        return field_original[1:]
    return rol_de_campo(column_roles, field_resuelto or field_original)


def records_para_campo_de_valor(records: list, column_roles: dict, field_original,
                                field_resuelto=None, group_field: Optional[str] = None) -> list:
    """Records de la métrica dueña de un campo de valor (promedio/mín/máx).

    Mismo problema que en los conteos (`filtrar_records_por_metrica`): en DIA
    `logro_1` está declarado en la métrica 6 ("por estudiante") y en la 7 ("por
    Pregunta"), ambas con la columna "Logro" → el mismo field `_logro`. Sin
    filtrar, "Logro prom." promediaba alumnos junto con preguntas.

    `group_field` es una salvaguarda: hay layouts que cruzan la columna de
    valor compartida con una dimensión que SOLO existe en la otra métrica
    (DIA: "Logro Promedio por Eje Temático" agrupa por una dimensión de la
    métrica 7). Si al filtrar el campo de agrupación desaparece, se devuelven
    todos los records — mejor el promedio mezclado que un gráfico en blanco.
    """
    rol = rol_de_campo_de_valor(column_roles, field_original, field_resuelto)
    if not rol:
        return records
    filtrados = filtrar_records_por_metrica(records, metric_id_del_rol(column_roles, rol))
    if filtrados is records or not group_field:
        return filtrados
    if not any(r.get(group_field) not in (None, '') for r in filtrados):
        return records
    return filtrados


# ─────────────────────────────────────────────────────────────────────────────
# Combinación temporal — el "último período" de los componentes snapshot
#
# El rol `evaluacion_num` puede declarar VARIAS columnas (DIA: Hito + Año;
# SIMCE: Mes + Año; Fluidez Lectora: N Prueba + Fecha). Resolver el período con
# `evaluacion_num[0]` ignoraba el resto: sin filtro de año del usuario,
# DIAGNOSTICO 2025 y DIAGNOSTICO 2026 caían en la misma "última evaluación".
#
# El último período es la última COMBINACIÓN de todas esas columnas, y el
# filtro snapshot exige que el record calce con la combinación completa.
# ─────────────────────────────────────────────────────────────────────────────

# Prioridad de la clave de orden de un valor temporal (menor = más antiguo
# dentro de su tier; los tiers se comparan primero). Un valor que la columna no
# declara ni el módulo `periodos` sabe interpretar se considera "no
# clasificado" y queda al final del orden.
_TIER_DECLARADO = 0   # orden explícito de indicator.temporal_config
_TIER_SEMANTICO = 1   # semántica de reports.periodos (año, mes, hito, versión)
_TIER_NATURAL = 2     # fallback alfanumérico (_natural_sort_key)


def _columna_de_anio(columnas) -> Optional[str]:
    """Cuál de `columnas` es la de año, según `reports.periodos`."""
    try:
        from ..reports.periodos import detectar_columnas_temporales
        return detectar_columnas_temporales([str(c) for c in columnas]).get('anio')
    except Exception:
        return None


def _columna_desde_campo(campo: str) -> str:
    """`'_n_prueba'` → `'n prueba'`.

    Nombre pseudo-humano para poder reusar la semántica de `reports.periodos`
    y el lookup de `temporal_config` cuando el layout solo declara el field
    (`periodField`) y no el nombre de la dimensión. `_to_field_name` de la
    vuelta reconstruye el mismo field, así que el matcheo sigue siendo exacto.
    """
    return str(campo).lstrip('_').replace('_', ' ')


def columnas_temporales_del_rol(column_roles: dict,
                                rol: str = 'evaluacion_num') -> List[str]:
    """Columnas distintas declaradas en el rol temporal, con el año primero.

    El orden importa: es el orden de significancia de la tupla que decide cuál
    es la última combinación. La columna de año manda; el resto conserva el
    orden en que aparecen las entradas del rol.
    """
    entries = (column_roles or {}).get(rol)
    if not isinstance(entries, list):
        return []
    cols: List[str] = []
    for e in entries:
        col = e.get('column') if isinstance(e, dict) else None
        if col and str(col) not in cols:
            cols.append(str(col))
    if len(cols) < 2:
        return cols
    col_anio = _columna_de_anio(cols)
    if col_anio in cols:
        cols = [col_anio] + [c for c in cols if c != col_anio]
    return cols


def columnas_snapshot_temporal(period_field: Optional[str], column_roles: dict,
                               rol: str = 'evaluacion_num') -> List[str]:
    """Columnas que definen el "último período" de un componente snapshot.

    Manda el rol temporal del indicador (que puede declarar varias columnas).
    El `periodField` del layout solo se usa cuando apunta a un field ajeno al
    rol — ahí se respeta el layout, como antes del fix. `'_mes'` es el default
    histórico del renderer, no una declaración del usuario: se ignora.
    """
    cols = columnas_temporales_del_rol(column_roles, rol)
    campos = [_to_field_name(c) for c in cols]
    explicito = period_field if (period_field and period_field != '_mes') else None
    if explicito and explicito not in campos:
        return [_columna_desde_campo(explicito)]
    return cols


def _periodo_presente_en_records(period_field: Optional[str], records: list,
                                 column_roles: dict,
                                 rol: str = 'evaluacion_num') -> Optional[str]:
    """`period_field` si existe en los records; si no, el del rol temporal.

    Un `periodField` que ningún record trae deja el eje X sin categorías y el
    gráfico de tendencia sale COMPLETAMENTE en blanco, sin error ni pista. Pasa
    con cualquier alias que no sea un rol de `_KNOWN_ROLES`: `_resolve_field`
    lo devuelve tal cual (el caso real fue `'_evaluacion'` en el layout
    histórico de Fluidez Lectora, cuyo rol es `evaluacion_num`).

    El fallback es la primera columna del rol temporal que sí esté poblada en
    los records. Si tampoco hay, se devuelve el campo original: no hay nada
    mejor que ofrecer y el llamador mantiene su comportamiento previo.
    """
    if not records:
        return period_field
    if period_field and any(r.get(period_field) not in (None, '') for r in records):
        return period_field
    for columna in columnas_temporales_del_rol(column_roles, rol):
        campo = _to_field_name(columna)
        if any(r.get(campo) not in (None, '') for r in records):
            return campo
    return period_field


def _temporal_config_de_indicador(indicator) -> dict:
    """`indicator.temporal_config` parseado (patrón defensivo del archivo)."""
    raw = getattr(indicator, 'temporal_config', None)
    try:
        cfg = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        return {}
    return cfg if isinstance(cfg, dict) else {}


def _orden_declarado(columna: str, temporal_config: Optional[dict]) -> List[str]:
    """Lista `order` que `temporal_config` declara para `columna` (o vacía).

    El match es por field name para tolerar tildes y mayúsculas entre el
    `label` del config ("Versión") y el nombre de la dimensión ("versión").
    """
    levels = (temporal_config or {}).get('levels')
    if not isinstance(levels, list):
        return []
    objetivo = _to_field_name(columna)
    for lvl in levels:
        if not isinstance(lvl, dict):
            continue
        label = lvl.get('label') or ''
        if label and _to_field_name(str(label)) == objetivo:
            order = lvl.get('order')
            return [str(v) for v in order] if isinstance(order, list) else []
    return []


def _valor_semantico_temporal(columna: str, crudo: str) -> Optional[int]:
    """Valor comparable de un valor temporal según la semántica de su columna.

    Delega en `backend.rgenerator.reports.periodos`, única fuente de verdad de
    la semántica temporal del proyecto: años como entero, meses en español,
    hitos DIA (DIAGNOSTICO→INICIO=3, INTERMEDIO=6, CIERRE=11) y versiones IDEL.
    """
    try:
        from ..reports.periodos import _a_entero, a_numero_mes, tipo_mes_like
    except Exception:
        return None
    if _columna_de_anio([columna]):
        return _a_entero(crudo)
    semantica = tipo_mes_like(columna)
    if semantica:
        mes = a_numero_mes(crudo, semantica)
        if mes is not None:
            return mes
    return _a_entero(crudo)


def _clave_natural_estable(valor: str) -> tuple:
    """`_natural_sort_key` con las partes normalizadas a tuplas comparables.

    `_natural_sort_key` mezcla int y str en la misma lista; comparar dos claves
    que difieren de tipo en la misma posición explota. Acá cada parte se
    envuelve en `(0, numero, '')` o `(1, 0, texto)` — los números siguen
    ordenando antes que el texto, sin TypeError.
    """
    partes = []
    for p in _natural_sort_key(valor):
        if isinstance(p, int):
            partes.append((0, p, ''))
        else:
            partes.append((1, 0, str(p)))
    return tuple(partes)


def orden_valor_temporal(columna: str, valor, temporal_config: Optional[dict] = None) -> tuple:
    """Clave ordenable de `valor` dentro de la columna temporal `columna`.

    Orden de preferencia: (1) el orden declarado en `temporal_config` para esa
    dimensión, (2) la semántica de `reports.periodos`, (3) `_natural_sort_key`.
    Cada estrategia es un tier: un valor que la columna no declara queda
    después de todos los declarados.
    """
    crudo = '' if valor is None else str(valor)
    declarado = _orden_declarado(columna, temporal_config)
    if crudo in declarado:
        return (_TIER_DECLARADO, float(declarado.index(crudo)), ())
    n = _valor_semantico_temporal(columna, crudo)
    if n is not None:
        return (_TIER_SEMANTICO, float(n), ())
    return (_TIER_NATURAL, 0.0, _clave_natural_estable(crudo))


def combinaciones_temporales(records: list, columnas: List[str],
                             temporal_config: Optional[dict] = None) -> List[Dict[str, str]]:
    """Combinaciones temporales presentes en `records`, de la más antigua a la
    más reciente.

    Cada combinación es `{columna: valor}`. Se descartan las incompletas (algún
    valor vacío): sin el año no se puede ubicar la evaluación en el tiempo, y
    dejarla competir la hacía ganar por venir de un tier "no clasificado".
    Las columnas vacías en TODOS los records se ignoran (no participan del
    orden ni del filtro).

    Devuelve `[]` si no se puede resolver — el llamador mantiene entonces su
    comportamiento previo (fail-open).
    """
    if not columnas or not records:
        return []
    campos = [(str(c), _to_field_name(c)) for c in columnas]
    campos = [(c, f) for c, f in campos
              if any(r.get(f) not in (None, '') for r in records)]
    if not campos:
        return []

    combos = set()
    for r in records:
        valores = tuple(
            '' if r.get(f) in (None, '') else str(r.get(f)) for _, f in campos
        )
        if any(v == '' for v in valores):
            continue
        combos.add(valores)
    if not combos:
        return []

    def _clave(combo):
        return tuple(orden_valor_temporal(c, v, temporal_config)
                     for (c, _), v in zip(campos, combo))

    return [{c: v for (c, _), v in zip(campos, combo)}
            for combo in sorted(combos, key=_clave)]


def ultima_combinacion_temporal(records: list, columnas: List[str],
                                temporal_config: Optional[dict] = None) -> Optional[Dict[str, str]]:
    """`{columna: valor}` de la última combinación temporal de `records`.

    None si no hay columnas, no hay records o ninguna combinación es completa.
    """
    combos = combinaciones_temporales(records, columnas, temporal_config)
    return combos[-1] if combos else None


def filtrar_records_por_combinacion(records: list,
                                    combinacion: Optional[Dict[str, str]]) -> list:
    """Deja solo los records que calzan con la combinación temporal completa."""
    if not combinacion:
        return records
    pares = [(_to_field_name(c), str(v)) for c, v in combinacion.items()]
    return [r for r in records
            if all(str(r.get(f, '')) == v for f, v in pares)]


def etiqueta_combinacion_temporal(combinacion: Optional[Dict[str, str]]) -> str:
    """`{'Año': '2025', 'Hito': 'CIERRE'}` → `'2025 CIERRE'` (para headers).

    Las fechas a medianoche pierden la hora: los valores de una columna "Fecha"
    llegan como `'2025-10-09 00:00:00'` y el `Δ vs …` quedaba ilegible.
    """
    import re
    if not combinacion:
        return ''
    partes = []
    for v in combinacion.values():
        s = str(v).strip()
        if not s:
            continue
        s = re.sub(r'\s+00:00:00$', '', s)
        partes.append(s)
    return ' '.join(partes)


def _build_records(
    db,
    indicator,
    org_id: int,
    filters: Optional[Dict[str, object]] = None,
) -> list[dict]:
    """
    Construye lista plana de registros desde MetricData para un indicador.

    Cada record se etiqueta con `_metric_id` (la métrica de origen) para que
    los componentes de conteo puedan distinguir filas de métricas distintas
    que comparten nombre de columna. Ver `filtrar_records_por_metrica`.

    filters: dict opcional {id_dimension_str: valor} — se aplica sobre
        dimensions_json de cada MetricData antes de proyectar el record.
        Mismo contrato que GET /api/results/indicator/{id}/data?filters=...
    """
    from backend.models import IndicatorMetric, Metric, MetricDimension, MetricData, Dimension

    metric_links = db.query(IndicatorMetric).filter(
        IndicatorMetric.id_indicator == indicator.id_indicator
    ).all()
    metric_ids = [lnk.id_metric for lnk in metric_links]
    if not metric_ids:
        return []

    # org_id como defensa en profundidad: aunque los ids vengan validados
    # aguas arriba, un id cross-org jamás debe proyectar datos (QA H-02/H6).
    metrics = db.query(Metric).filter(
        Metric.id_metric.in_(metric_ids), Metric.org_id == org_id
    ).all()
    metrics_by_id = {m.id_metric: m for m in metrics}

    all_dim_ids = set()
    for mid in metric_ids:
        links = db.query(MetricDimension).filter(MetricDimension.id_metric == mid).all()
        all_dim_ids.update(lnk.id_dimension for lnk in links)

    dims_by_id = {}
    if all_dim_ids:
        dims = db.query(Dimension).filter(Dimension.id_dimension.in_(all_dim_ids)).all()
        dims_by_id = {d.id_dimension: d for d in dims}

    records = []
    for mid in metric_ids:
        m = metrics_by_id.get(mid)
        if not m:
            continue

        meta_fields = []
        try:
            mj = json.loads(m.meta_json) if isinstance(m.meta_json, str) else (m.meta_json or {})
            meta_fields = mj.get('fields', [])
        except Exception:
            pass

        dim_links = db.query(MetricDimension).filter(MetricDimension.id_metric == mid).all()
        dim_ids = [lnk.id_dimension for lnk in dim_links]

        data_rows = db.query(MetricData).filter(MetricData.id_metric == mid).all()
        for row in data_rows:
            try:
                dims_json = json.loads(row.dimensions_json) if isinstance(row.dimensions_json, str) else (row.dimensions_json or {})
            except Exception:
                dims_json = {}

            if filters and not all(
                matches(dims_json.get(fk, ""), fv)
                for fk, fv in filters.items()
            ):
                continue

            rec = {}
            # Value fields
            raw_val = row.value
            if meta_fields:
                try:
                    parsed = json.loads(raw_val) if isinstance(raw_val, str) else raw_val
                    if isinstance(parsed, dict):
                        for f in meta_fields:
                            fname = _to_field_name(f['name'])
                            rec[fname] = parsed.get(f['name'])
                    else:
                        key = _to_field_name(meta_fields[0]['name']) if meta_fields else _to_field_name(m.name)
                        rec[key] = parsed
                except Exception:
                    key = _to_field_name(m.name)
                    rec[key] = raw_val
            else:
                key = _to_field_name(m.name)
                try:
                    rec[key] = float(raw_val) if raw_val is not None else None
                except (ValueError, TypeError):
                    rec[key] = raw_val

            # Dimension fields
            for did in dim_ids:
                dim = dims_by_id.get(did)
                if dim:
                    dkey = _to_field_name(dim.name)
                    rec[dkey] = dims_json.get(str(did))

            # Métrica de origen (clave técnica, no de negocio).
            rec[METRIC_ID_KEY] = mid

            records.append(rec)

    return records


def _achievement_levels(indicator) -> list[dict]:
    """Devuelve lista [{name, color, order}] desde indicator.achievement_levels.

    Acepta también el formato legacy ["Avanzado", "Intermedio", ...] (strings)
    y lo normaliza a [{name, order}] para que los consumidores siempre puedan
    hacer .get('name'). El color cae al fallback semáforo si no está.
    """
    raw = getattr(indicator, 'achievement_levels', None) or '[]'
    try:
        levels = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        levels = []
    if not isinstance(levels, list):
        return []
    out = []
    for i, lv in enumerate(levels):
        if isinstance(lv, dict):
            out.append(lv)
        elif isinstance(lv, str):
            out.append({'name': lv, 'order': i})
    return out


def _natural_sort_key(s):
    """Orden alfanumérico natural: '1° MEDIO A' < '1° MEDIO B' < '2° MEDIO A'."""
    import re
    s = str(s)
    return [int(p) if p.isdigit() else p.lower()
            for p in re.split(r'(\d+)', s)]


def _chart_to_png_b64(item: dict, records: list[dict], indicator=None) -> str:
    """Renderiza un componente del dashboard como PNG base64 usando matplotlib."""
    import io, base64
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import collections

    # Estilo LaTeX-paridad (Segoe UI, tamaños chicos, ver visual_vocabulary_dia.md)
    plt.rcParams.update(MPL_RCPARAMS_LATEX)
    pal_cat, pal_box = _ensure_palettes()

    column_roles = {}
    if indicator is not None:
        try:
            column_roles = json.loads(indicator.column_roles) if isinstance(indicator.column_roles, str) else (indicator.column_roles or {})
        except Exception:
            column_roles = {}

    comp = item.get('component', '')
    # El field SIN resolver se conserva: `records_para_campo_de_valor` acepta
    # tanto el alias de rol ('_logro_1') como la columna resuelta ('_logro').
    x_field_orig = item.get('xField') or item.get('valueField', '')
    x_field = _resolve_field(x_field_orig, column_roles)
    y_field = _resolve_field(item.get('yField', ''), column_roles)
    group_field = _resolve_field(item.get('groupField', ''), column_roles)
    period_field = _resolve_field(item.get('periodField', '_mes'), column_roles)
    # StackedCountByGroup acepta 'levelField' o su alias 'categoryField' (los
    # layouts del Editor usan ambos). Ignorar categoryField hacía que dos
    # secciones con categorías distintas (_logro vs _habilidad) rendericen el
    # mismo gráfico (QA visual 2026-07-30, hallazgo P1-8 Fluidez Lectora).
    level_field = _resolve_field(item.get('levelField', '_logro') if comp != 'StackedCountByGroup'
                                 else item.get('levelField') or item.get('categoryField')
                                 or '_' + (column_roles.get('nivel_de_logro', [{}])[0].get('column', '') or '').lower().replace(' ', '_'),
                                 column_roles)

    # figsize por componente: barras simples medium (8,4), grouped/stacked
    # más anchos. Ver docs/desarrollo/visual_vocabulary_dia.md §11.
    if comp in ('GroupedBarByPeriod',) or (comp == 'BarByGroup' and isinstance(item.get('valueField'), list) and len(item.get('valueField', [])) > 1):
        figsize = (12, 6)
    elif comp == 'StackedCountByGroup':
        figsize = (10, 6)
    else:
        figsize = (8, 4)
    fig, ax = plt.subplots(figsize=figsize)

    try:
        if comp in ('StackedCountByGroup', 'DistribucionNiveles'):
            # Cuenta valores categóricos (level_field) agrupados por group_field.
            # Usa achievement_levels del indicator para orden y color.
            gf = group_field or '_curso'
            # Resolver levelField. Si vino del item, _resolve_field ya lo
            # tradujo (ej _nivel_de_logro → _logro). NO re-resolver acá: el
            # bug previo era hacer fallback cuando lf == '_logro', cayendo
            # a '_categoria' que no existe en SIMCE/DIA.
            lf = level_field

            def _lf_desde_rol():
                role_entries = column_roles.get('nivel_de_logro') or []
                if role_entries:
                    col = role_entries[0].get('column', '')
                    if col:
                        return _to_field_name(col)
                return None

            if not lf:
                lf = _lf_desde_rol()
            elif records and not any(r.get(lf) is not None for r in records):
                # El campo declarado no existe en los datos (ej layouts con el
                # alias '_logro' en indicadores cuyo nivel vive en otra columna,
                # como Fluidez Lectora → '_categoria'). Caer al rol en vez de
                # dibujar un gráfico vacío.
                lf = _lf_desde_rol() or lf
            if not lf:
                lf = '_categoria'  # último fallback

            # Contar SOLO los records de la métrica que aporta el campo `lf`.
            # Un indicador puede vincular dos métricas con la misma columna
            # (DIA: metric 6 "por estudiante" + metric 7 "por Pregunta", ambas
            # con "Nivel Logro" → mismo field `_nivel_logro`): sin filtrar, la
            # barra sumaba preguntas como alumnos (demo: 25 con 15 alumnos).
            # El rol se deriva del campo realmente usado, no siempre
            # nivel_de_logro (ej Fluidez Lectora cuenta `_calidad_lectora`,
            # rol habilidad). Si el campo no corresponde a ningún rol conocido,
            # no se filtra.
            rol_lf = rol_de_campo(column_roles, lf)
            records_metrica = filtrar_records_por_metrica(
                records, metric_id_del_rol(column_roles, rol_lf) if rol_lf else None
            )

            # Filtro a la última COMBINACIÓN temporal si hay más de una y
            # groupField no es una de las columnas de período (modo "snapshot"
            # por evaluación). En histórico, groupField suele ser el período
            # (_mes, _hito), entonces NO filtramos.
            columnas_periodo = columnas_snapshot_temporal(period_field, column_roles)
            campos_periodo = [_to_field_name(c) for c in columnas_periodo]

            records_filtered = records_metrica
            if campos_periodo and gf not in campos_periodo:
                combos = combinaciones_temporales(
                    records_metrica, columnas_periodo,
                    _temporal_config_de_indicador(indicator),
                )
                if len(combos) >= 2:
                    records_filtered = filtrar_records_por_combinacion(
                        records_metrica, combos[-1]
                    ) or records_metrica

            levels_cfg = _achievement_levels(indicator)
            level_order = [l.get('name', '') for l in levels_cfg] if levels_cfg else []
            # Solo guardamos colores realmente declarados en la config; los
            # niveles sin color caen al fallback semáforo (verde/naranja/rojo)
            # vía _semaforo_color en el loop de barras.
            level_colors = {l.get('name', ''): l.get('color')
                            for l in levels_cfg if l.get('color')}

            groups = sorted({str(r.get(gf, '')) for r in records_filtered if r.get(gf) is not None},
                            key=_natural_sort_key)
            observed = {str(r.get(lf, '')) for r in records_filtered
                        if r.get(lf) is not None and str(r.get(lf, '')) != ''}
            # Los achievement_levels solo aplican cuando el campo contado ES el
            # de niveles. Para otras categorías (ej Calidad Lectora vía
            # categoryField) los valores no intersectan la config y el orden
            # debe salir de los datos; los colores caen al fallback semáforo.
            if not level_order or not (set(level_order) & observed):
                level_order = sorted(observed)

            counts = {g: {l: 0 for l in level_order} for g in groups}
            for r in records_filtered:
                g = str(r.get(gf, ''))
                l = str(r.get(lf, ''))
                if g in counts and l in counts[g]:
                    counts[g][l] += 1

            bottom = [0] * len(groups)
            for i, level in enumerate(level_order):
                vals = [counts[g][level] for g in groups]
                # Prioridad: color del achievement_level del indicator → paleta
                # semáforo (Avanzado/Intermedio/Inicial) → fallback ordinal.
                col = level_colors.get(level) or _semaforo_color(level, i)
                bars = ax.bar(groups, vals, label=level, color=col, bottom=bottom, zorder=2)
                for b, v, btm in zip(bars, vals, bottom):
                    if v > 0:
                        ax.text(b.get_x() + b.get_width() / 2, btm + v / 2, str(v),
                                ha='center', va='center', fontsize=9, color='white', fontweight='bold')
                bottom = [a + b for a, b in zip(bottom, vals)]

            ax.set_ylabel(item.get('labelY', 'Cantidad de alumnos'))
            ax.spines[['top', 'right']].set_visible(False)
            ax.yaxis.grid(True, linestyle='--', alpha=0.6, zorder=0)
            if level_order:
                ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
            plt.xticks(rotation=20, ha='right')

        elif comp == 'GroupedBarByPeriod':
            # Barras agrupadas: una serie por groupField, eje X por periodField.
            gf = group_field or '_curso'
            pf = period_field or '_mes'
            vf_orig = item.get('xField') or item.get('valueField') or '_logro_1'
            if isinstance(vf_orig, list):
                vf_orig = vf_orig[0] if vf_orig else '_logro_1'
            vf = x_field if isinstance(x_field, str) else (x_field[0] if x_field else '_logro_1')
            vf = _resolve_field(vf, column_roles)

            # Detectar formato del role (percent vs number)
            role_formats = {}
            if indicator is not None:
                try:
                    role_formats = json.loads(indicator.role_formats) if isinstance(indicator.role_formats, str) else (indicator.role_formats or {})
                except Exception:
                    role_formats = {}
            fmt = _role_format_for_field(vf, column_roles, role_formats)

            # Promediar solo los records de la métrica dueña del campo de valor
            # (ver `records_para_campo_de_valor`). El eje X sigue siendo el
            # período completo: este componente es de tendencia, no snapshot.
            records_vf = records_para_campo_de_valor(
                records, column_roles, vf_orig, vf, group_field=gf
            )

            # El periodField declarado puede no existir en los datos: basta un
            # alias que no sea rol conocido (`'_evaluacion'` en el layout
            # histórico de Fluidez Lectora — el rol es `evaluacion_num`) para
            # que `_resolve_field` lo devuelva tal cual, el eje X quede sin
            # categorías y el gráfico salga en blanco sin ningún error.
            # Caer a la primera columna del rol temporal que sí esté en los
            # records, misma convención que el fallback de `levelField` en
            # StackedCountByGroup: mejor el eje del rol que un gráfico vacío.
            pf = _periodo_presente_en_records(pf, records_vf, column_roles)

            groups = sorted({str(r.get(gf, '')) for r in records_vf if r.get(gf) is not None},
                            key=_natural_sort_key)
            periods = sorted({str(r.get(pf, '')) for r in records_vf if r.get(pf) is not None},
                             key=_natural_sort_key)

            import numpy as np
            x = np.arange(len(periods))
            width = 0.8 / max(1, len(groups))
            colors = pal_cat
            max_val = 0
            for i, g in enumerate(groups):
                vals = []
                for p in periods:
                    nums = []
                    for r in records_vf:
                        if str(r.get(gf, '')) == g and str(r.get(pf, '')) == p:
                            v = r.get(vf)
                            if v is None or v == '':
                                continue
                            try: nums.append(float(v))
                            except (TypeError, ValueError): pass
                    vals.append(sum(nums) / len(nums) if nums else 0)
                max_val = max(max_val, max(vals) if vals else 0)
                offset = (i - (len(groups) - 1) / 2) * width
                ax.bar(x + offset, vals, width, label=g, color=colors[i % len(colors)],
                       edgecolor='gray', linewidth=0.8, zorder=2)
            ax.set_xticks(x); ax.set_xticklabels(periods)
            ax.set_ylabel(item.get('labelY', vf.lstrip('_').title()))
            ax.spines[['top', 'right']].set_visible(False)
            ax.yaxis.grid(True, linestyle='--', linewidth=0.9, alpha=0.6, zorder=0)
            # Formato percent: ylim 0-1 + ticker percent
            if fmt == 'percent' and max_val <= 1.5:
                ax.set_ylim(0, 1)
                from matplotlib.ticker import PercentFormatter as _PF
                ax.yaxis.set_major_formatter(_PF(1.0))
            # Leyenda: cuando hay muchos grupos, fuera del plot a la derecha
            if len(groups) > 8:
                ax.legend(fontsize=6, loc='center left', bbox_to_anchor=(1.01, 0.5), ncol=1)
            else:
                ax.legend(fontsize=7, loc='upper left', ncol=2)

        elif comp == 'BarByGroup':
            # Si valueField es lista → barras agrupadas (una por valueField).
            # Si es string → barras simples por groupField.
            gf = group_field or '_curso'
            vfs_orig = item.get('valueField', x_field)
            if isinstance(vfs_orig, str):
                vfs_orig = [vfs_orig]
            vfs_orig = list(vfs_orig)
            vfs = [_resolve_field(v, column_roles) for v in vfs_orig]

            # Detectar formato del primer vf para ylim/ticks
            role_formats = {}
            if indicator is not None:
                try:
                    role_formats = json.loads(indicator.role_formats) if isinstance(indicator.role_formats, str) else (indicator.role_formats or {})
                except Exception:
                    role_formats = {}
            fmt_first = _role_format_for_field(vfs[0] if vfs else '', column_roles, role_formats)

            # Filtrar a la última COMBINACIÓN temporal cuando hay más de una y
            # groupField no es una columna de período. Garantiza consistencia
            # con SummaryTable (issue 1A: tabla y gráfico mostraban valores
            # distintos en SIMCE por evaluación cuando la tabla filtraba al
            # último periodo y el gráfico promediaba todos).
            columnas_periodo = columnas_snapshot_temporal(period_field, column_roles)
            campos_periodo = [_to_field_name(c) for c in columnas_periodo]
            records_local = records
            if campos_periodo and gf not in campos_periodo:
                combos = combinaciones_temporales(
                    records, columnas_periodo,
                    _temporal_config_de_indicador(indicator),
                )
                if len(combos) >= 2:
                    records_local = filtrar_records_por_combinacion(
                        records, combos[-1]
                    ) or records

            groups = sorted({str(r.get(gf, '')) for r in records_local if r.get(gf) is not None},
                            key=_natural_sort_key)

            import numpy as np
            x = np.arange(len(groups))
            width = 0.8 / max(1, len(vfs))
            colors = pal_cat
            # Bordes: barras simples (1 vf) más gruesos en negro; barras
            # agrupadas (multi vf) más finos en gris para no saturar.
            edge_color, edge_width = ('black', 1.2) if len(vfs) == 1 else ('gray', 0.8)
            max_val = 0
            for i, (vf, vf_orig) in enumerate(zip(vfs, vfs_orig)):
                # Promediar SOLO los records de la métrica dueña del campo de
                # valor: con dos métricas que comparten la columna (DIA metric 6
                # estudiantes + metric 7 preguntas, ambas con "Logro") la barra
                # mezclaba alumnos con preguntas.
                recs_vf = records_para_campo_de_valor(
                    records_local, column_roles, vf_orig, vf, group_field=gf
                )
                vals = []
                for g in groups:
                    nums = []
                    for r in recs_vf:
                        if str(r.get(gf, '')) == g:
                            v = r.get(vf)
                            if v is None or v == '':
                                continue  # NO contar como 0, el field no existe en este record
                            try: nums.append(float(v))
                            except (TypeError, ValueError): pass
                    vals.append(sum(nums) / len(nums) if nums else 0)
                max_val = max(max_val, max(vals) if vals else 0)
                offset = (i - (len(vfs) - 1) / 2) * width
                bars = ax.bar(x + offset, vals, width,
                              label=vf.lstrip('_').replace('_', ' ').title(),
                              color=colors[i % len(colors)], zorder=2,
                              edgecolor=edge_color, linewidth=edge_width)
                if item.get('showValues', False):
                    for b, v in zip(bars, vals):
                        if fmt_first == 'percent' and -1.5 <= v <= 1.5:
                            label_str = f'{v * 100:.0f}%'
                        else:
                            label_str = f'{v:.1f}'
                        ax.text(b.get_x() + b.get_width() / 2, v + max(vals + [1]) * 0.01,
                                label_str, ha='center', va='bottom', fontsize=8,
                                bbox=dict(facecolor='white', edgecolor='none', pad=1, alpha=0.7))
            ax.set_xticks(x); ax.set_xticklabels(groups, rotation=20, ha='right')
            ax.spines[['top', 'right']].set_visible(False)
            ax.yaxis.grid(True, linestyle='--', linewidth=0.9, alpha=0.6, zorder=0)
            # Formato percent: ylim 0-1 + ticker percent
            if fmt_first == 'percent' and max_val <= 1.5:
                ax.set_ylim(0, 1)
                from matplotlib.ticker import PercentFormatter as _PF
                ax.yaxis.set_major_formatter(_PF(1.0))
            # Leyenda fuera del plot cuando hay muchos grupos o multi-value
            if len(vfs) > 1 and item.get('showLegend', True):
                if len(groups) > 8:
                    ax.legend(fontsize=7, loc='center left', bbox_to_anchor=(1.01, 0.5))
                else:
                    ax.legend(fontsize=8)

        elif comp in ('HeatmapMatrix',):
            x_f = item.get('xField', '')
            y_f = item.get('yField', '')
            v_f = item.get('valueField', '')
            xs = sorted({str(r.get(x_f, '')) for r in records if r.get(x_f) is not None})
            ys = sorted({str(r.get(y_f, '')) for r in records if r.get(y_f) is not None})
            z = []
            for y in ys:
                row_vals = []
                for x in xs:
                    vals = [float(r.get(v_f) or 0) for r in records
                            if str(r.get(x_f)) == x and str(r.get(y_f)) == y
                            and r.get(v_f) is not None]
                    row_vals.append(sum(vals) / len(vals) if vals else 0)
                z.append(row_vals)
            im = ax.imshow(z, aspect='auto', cmap='Greens')
            ax.set_xticks(range(len(xs))); ax.set_xticklabels(xs)
            ax.set_yticks(range(len(ys))); ax.set_yticklabels(ys)
            fig.colorbar(im, ax=ax)

        elif comp == 'GaugeIndicator':
            # Promedio de la métrica dueña del campo (ver BarByGroup).
            records_vf = records_para_campo_de_valor(
                records, column_roles, x_field_orig, x_field
            )
            vals = [float(r.get(x_field) or 0) for r in records_vf if r.get(x_field) is not None]
            val = sum(vals) / len(vals) if vals else 0
            ax.axis('off')
            ax.text(0.5, 0.6, f'{val:.1f}', ha='center', va='center',
                    fontsize=40, fontweight='bold', color='#111', transform=ax.transAxes)
            ax.text(0.5, 0.35, item.get('labelX', x_field), ha='center', va='center',
                    fontsize=11, color='#444', transform=ax.transAxes)

        elif comp == 'Histogram':
            # Distribución de la métrica dueña del campo (ver BarByGroup).
            records_vf = records_para_campo_de_valor(
                records, column_roles, x_field_orig, x_field
            )
            vals = [float(r.get(x_field) or 0) for r in records_vf if r.get(x_field) is not None]
            ax.hist(vals, bins=item.get('nbins', 10), color=pal_cat[0], alpha=0.85,
                    edgecolor='black', linewidth=1.0)
            ax.set_xlabel(item.get('labelX', x_field))
            ax.set_ylabel(item.get('labelY', 'Frecuencia'))
            ax.spines[['top', 'right']].set_visible(False)
            ax.yaxis.grid(True, linestyle='--', linewidth=0.9, alpha=0.6, zorder=0)

        else:
            # Barras genéricas: agrupa por x_field, promedia y_field
            buckets = collections.defaultdict(list)
            for r in records:
                xv = str(r.get(x_field, ''))
                yv = r.get(y_field or x_field)
                try:
                    buckets[xv].append(float(yv))
                except (TypeError, ValueError):
                    pass
            if buckets:
                labels = sorted(buckets.keys())
                vals = [sum(buckets[l]) / len(buckets[l]) for l in labels]
                colors = pal_cat
                ax.bar(labels, vals,
                       color=[colors[i % len(colors)] for i in range(len(labels))],
                       width=0.6, edgecolor='black', linewidth=1.2, zorder=3)
                ax.set_ylabel(item.get('labelY', y_field or ''))
                ax.yaxis.grid(True, linestyle='--', linewidth=0.9, alpha=0.6, zorder=0)
                ax.spines[['top', 'right']].set_visible(False)
                for i, (lbl, val) in enumerate(zip(labels, vals)):
                    ax.text(i, val + max(vals) * 0.01, f'{val:.1f}',
                            ha='center', va='bottom', fontsize=8)
                plt.xticks(rotation=30, ha='right')
            else:
                ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center',
                        transform=ax.transAxes, color='#444')
                ax.axis('off')

    except Exception as e:
        ax.text(0.5, 0.5, f'Error: {e}', ha='center', va='center',
                transform=ax.transAxes, color='#b91c1c', fontsize=8)
        ax.axis('off')

    # NOTA: el heading del gráfico viene del HTML (h2 sobre el chart-wrap),
    # no se setea ax.set_title para evitar duplicación con el LaTeX referencia
    # (que tampoco usa título inline en sus figuras).
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=CHART_DPI, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def _pivot_table_via_engine(records: list[dict], row_fields: list,
                            col_fields: list, values_cfg: list) -> dict:
    """PivotTable (PDF v1) calculado con el motor de pivotes W2.

    Delega toda la agregación en `backend.rgenerator.core.pivot_engine.pivot`
    (única fuente de verdad para pivotes) pero reconstruye el formato de
    salida histórico ({columns, rows}) del PDF v1: orden lexicográfico de
    filas/columnas, 2 decimales para agregaciones numéricas, conteo entero,
    y "—" para celdas sin datos. Ver docs/planes/w2_motor_pivotes.md.

    Args:
        records: filas (list de dicts) del informe.
        row_fields: campos de agrupación en filas.
        col_fields: campos de agrupación en columnas (puede ser vacío).
        values_cfg: lista de {field, aggregation, label}.

    Returns:
        {'columns': [...], 'rows': [[...], ...]} idéntico al de v1.
    """
    from .pivot_engine import pivot
    from backend.schemas_pivot import PivotSpec, PivotValue

    def _map_agg(a):
        a = a or 'avg'
        if a in ('sum', 'count', 'min', 'max'):
            return a
        # 'avg', 'mean' y cualquier otro → promedio (default v1).
        return 'mean'

    value_fields: list = []
    for vc in values_cfg:
        if vc['field'] not in value_fields:
            value_fields.append(vc['field'])

    # DataFrame con dimensiones stringificadas (igual que v1, que agrupaba por
    # str(rec.get(campo, ''))) y valores coercionados a numérico (float() con
    # exclusión de no convertibles → NaN, que el motor ignora).
    data: dict = {}
    for f in row_fields + col_fields:
        data[f] = [str(rec.get(f, '')) for rec in records]
    for f in value_fields:
        data[f] = [rec.get(f) for rec in records]
    df = pd.DataFrame(data)
    for f in value_fields:
        df[f] = pd.to_numeric(df[f], errors='coerce')

    spec = PivotSpec(
        rows=list(row_fields),
        cols=list(col_fields),
        values=[
            PivotValue(field=vc['field'], agg=_map_agg(vc.get('aggregation')),
                       label=vc.get('label', vc['field']))
            for vc in values_cfg
        ],
        totals={'rows': False, 'cols': False},
    )
    result = pivot(df, spec)

    # Lookup {(row_keys, col_keys, field, agg): valor_crudo}
    val_lookup: dict = {}
    for prow in result.rows:
        rk = tuple(prow.keys)
        for pcol, cell in zip(result.columns, prow.cells):
            val_lookup[(rk, tuple(pcol.keys), pcol.field, pcol.agg)] = cell.value

    # Columnas: todas las combinaciones presentes en records (incluidas las
    # sin datos numéricos), string-sort — igual que v1.
    col_keys = set()
    for rec in records:
        ck = tuple(str(rec.get(f, '')) for f in col_fields) if col_fields else ('',)
        col_keys.add(ck)
    col_keys_sorted = sorted(col_keys)

    # Filas: solo las que tienen ≥1 valor numérico (igual que v1), string-sort.
    row_keys = sorted(
        tuple(prow.keys) for prow in result.rows
        if any(c.value is not None for c in prow.cells)
    )

    header_row = ['/'.join(row_fields)]
    for ck in col_keys_sorted:
        ck_label = ' / '.join(ck) if any(ck) else ''
        for vc in values_cfg:
            lbl = vc.get('label', vc['field'])
            header_row.append(f'{ck_label} {lbl}'.strip())

    rows_out = []
    for rk in row_keys:
        row = [' / '.join(rk)]
        for ck in col_keys_sorted:
            engine_ck = () if not col_fields else ck
            for vc in values_cfg:
                agg = _map_agg(vc.get('aggregation'))
                val = val_lookup.get((rk, engine_ck, vc['field'], agg))
                if val is None:
                    row.append('—')
                elif agg == 'count':
                    row.append(str(int(round(val))))
                else:
                    row.append(f'{val:.2f}')
        rows_out.append(row)

    return {'columns': header_row, 'rows': rows_out}


def _table_section(item: dict, records: list[dict], indicator=None) -> dict:
    """Convierte un componente tabla en columnas + filas para el template HTML."""
    comp = item.get('component', '')

    column_roles = {}
    if indicator is not None:
        try:
            column_roles = json.loads(indicator.column_roles) if isinstance(indicator.column_roles, str) else (indicator.column_roles or {})
        except Exception:
            column_roles = {}

    if comp in ('SummaryTable', 'TablaResumenCursos'):
        # Tabla resumen por curso: Alumnos, Promedio, Min, Max, + count por nivel.
        gf = _resolve_field(item.get('groupField', '_curso'), column_roles)
        vfs = item.get('valueField')
        if isinstance(vfs, str): vfs = [vfs]
        if not vfs: vfs = ['_logro_1']
        vfs_resolved = [_resolve_field(v, column_roles) for v in vfs]

        compare_previous = bool(item.get('comparePrevious', False))
        period_field = _resolve_field(item.get('periodField', '_mes'), column_roles)
        columnas_periodo = columnas_snapshot_temporal(period_field, column_roles)
        campos_periodo = [_to_field_name(c) for c in columnas_periodo]

        # Resolver nivel_de_logro
        level_field = None
        role_entries = column_roles.get('nivel_de_logro') or []
        if role_entries:
            col = role_entries[0].get('column', '')
            if col: level_field = _to_field_name(col)

        # Records de la métrica que aporta el nivel de logro. Las columnas de
        # conteo por nivel y la columna "Alumnos" se calculan SOLO sobre ella:
        # con dos métricas vinculadas que comparten la columna (DIA metric 6
        # estudiantes + metric 7 preguntas) el conteo sumaba preguntas como
        # alumnos. Los promedios/mín/máx hacen lo propio con la métrica dueña de
        # SU campo de valor (ver `buckets` abajo).
        records_nivel = filtrar_records_por_metrica(
            records, metric_id_del_rol(column_roles, 'nivel_de_logro')
        )

        levels_cfg = _achievement_levels(indicator)
        level_names = [l.get('name', '') for l in levels_cfg] if levels_cfg else []

        # role_formats para mostrar percent vs number
        role_formats = {}
        if indicator is not None:
            try:
                role_formats = json.loads(indicator.role_formats) if isinstance(indicator.role_formats, str) else (indicator.role_formats or {})
            except Exception:
                role_formats = {}

        # Detectar las combinaciones temporales de los records (siempre, no solo
        # si comparePrevious). Si groupField NO es una columna de período,
        # asumimos que es un layout "por evaluación" y recortamos a la última
        # combinación. Esto evita que los counts se inflen sumando períodos —
        # y que DIAGNOSTICO 2025 se sume con DIAGNOSTICO 2026 por resolver el
        # período con una sola columna del rol.
        combo_actual = None
        combo_prev = None
        if campos_periodo and gf not in campos_periodo:
            combos = combinaciones_temporales(
                records, columnas_periodo, _temporal_config_de_indicador(indicator)
            )
            if combos:
                combo_actual = combos[-1]
            if compare_previous and len(combos) >= 2:
                combo_prev = combos[-2]

        def _pares(combo):
            if not combo:
                return None
            return [(_to_field_name(c), str(v)) for c, v in combo.items()]

        pares_actual = _pares(combo_actual)
        pares_prev = _pares(combo_prev)

        def _calza(r, pares):
            return pares is not None and all(
                str(r.get(f, '')) == v for f, v in pares
            )

        # Recolectar grupos y agregaciones. Cada campo de valor se promedia
        # SOLO sobre los records de su métrica fuente (DIA: `logro_1` está en la
        # métrica 6 y en la 7 con la misma columna "Logro" → "Logro prom."
        # mezclaba alumnos con preguntas).
        from collections import defaultdict
        buckets = defaultdict(list)
        buckets_prev = defaultdict(list)
        for vf, vf_orig in zip(vfs_resolved, vfs):
            recs_vf = records_para_campo_de_valor(
                records, column_roles, vf_orig, vf, group_field=gf
            )
            for r in recs_vf:
                g = str(r.get(gf, ''))
                if not g: continue
                try:
                    val = float(r.get(vf))
                except (TypeError, ValueError):
                    continue
                if combo_actual and _calza(r, pares_actual):
                    buckets[(g, vf)].append(val)
                elif combo_prev and _calza(r, pares_prev):
                    buckets_prev[(g, vf)].append(val)
                elif not combo_actual:
                    buckets[(g, vf)].append(val)

        groups = sorted({k[0] for k in buckets.keys()}, key=_natural_sort_key)

        # Headers
        header = [item.get('groupLabel', 'Curso'), 'Alumnos']
        show_delta = bool(combo_actual and combo_prev)
        etiqueta_prev = etiqueta_combinacion_temporal(combo_prev)
        for vf, vf_orig in zip(vfs_resolved, vfs):
            label = vf.lstrip('_').replace('_', ' ').title()
            header.append(f'{label} prom.')
            if show_delta:
                header.append(f'Δ vs {etiqueta_prev}')
            header.extend([f'{label} mín.', f'{label} máx.'])
        for lname in level_names:
            header.append(lname)

        def _fmt_delta(d, fmt='number'):
            if d is None:
                return '—'
            arrow = '▲' if d > 0.005 else ('▼' if d < -0.005 else '→')
            sign = '+' if d > 0 else ''
            if fmt == 'percent':
                return f'{arrow} {sign}{d * 100:.0f}%' if -1.5 <= d <= 1.5 else f'{arrow} {sign}{d:.0f}%'
            return f'{arrow} {sign}{d:.1f}'

        rows_out = []
        for g in groups:
            # Records de la combinación temporal actual (si se pudo resolver),
            # ya restringidos a la métrica dueña del nivel de logro.
            if combo_actual:
                actual_records = [r for r in records_nivel
                                  if str(r.get(gf, '')) == g and _calza(r, pares_actual)]
            else:
                actual_records = [r for r in records_nivel if str(r.get(gf, '')) == g]
            # Identidades distintas descartando vacíos: un `None` (fila sin
            # ninguna clave de identidad) sumaba un alumno fantasma al set.
            # `_nombre_norm` cierra la cadena porque es la clave estable de
            # identidad del estudiante (DIA trae filas con `Nombre` nulo y
            # `Nombre_Norm` poblado; los derived_fields ya la usan como
            # entity_field).
            identidades = {
                r.get('_rut') or r.get('_nombre') or r.get('_nombre_norm')
                for r in actual_records
            }
            identidades.discard(None)
            identidades.discard('')
            n_alumnos = len(identidades) or len(actual_records)
            row = [g, str(n_alumnos)]
            for vf, vf_orig in zip(vfs_resolved, vfs):
                fmt = _role_format_for_field(vf, column_roles, role_formats)
                # También probar con vf_orig por si vino con role-name
                if fmt == 'number' and isinstance(vf_orig, str) and vf_orig.startswith('_'):
                    fmt = (role_formats or {}).get(vf_orig[1:], 'number')

                vals = buckets.get((g, vf), [])
                vals_prev = buckets_prev.get((g, vf), [])
                if vals:
                    avg = sum(vals) / len(vals)
                    row.append(_format_value(avg, fmt))
                    if show_delta:
                        if vals_prev:
                            avg_prev = sum(vals_prev) / len(vals_prev)
                            row.append(_fmt_delta(avg - avg_prev, fmt))
                        else:
                            row.append('—')
                    row.extend([_format_value(min(vals), fmt), _format_value(max(vals), fmt)])
                else:
                    row.append('—')
                    if show_delta:
                        row.append('—')
                    row.extend(['—', '—'])
            # Counts por nivel — siempre sobre actual_records (que ya están filtrados al periodo actual si aplica)
            if level_field and level_names:
                for lname in level_names:
                    cnt = sum(1 for r in actual_records
                              if str(r.get(level_field, '')) == lname)
                    row.append(str(cnt))
            rows_out.append(row)

        return {'columns': header, 'rows': rows_out}

    if comp == 'PivotTable':
        cfg = item.get('pivotConfig', {})
        row_fields = cfg.get('rows', [])
        col_fields = cfg.get('cols', [])
        values_cfg = cfg.get('values', [])

        if not row_fields or not values_cfg:
            return {'columns': [], 'rows': []}

        # W2: la agregación se delega al motor de pivotes (única fuente de
        # verdad). El formato de salida histórico se conserva en el adapter.
        return _pivot_table_via_engine(records, row_fields, col_fields, values_cfg)

    else:
        # Tabla plana
        cfg = item.get('flatTableConfig', {})
        col_cfgs = cfg.get('columns', [])
        if not col_cfgs and records:
            # `_metric_id` es una clave técnica de _build_records: nunca debe
            # aparecer como columna en la tabla plana auto-generada.
            claves = [k for k in records[0].keys() if k != METRIC_ID_KEY]
            col_cfgs = [{'field': k, 'label': k} for k in claves[:8]]
        columns = [c.get('label', c.get('field', '')) for c in col_cfgs]
        fields = [c.get('field', '') for c in col_cfgs]
        sort_by = cfg.get('sortBy')
        sort_dir = cfg.get('sortDir', 'asc')
        recs = sorted(records, key=lambda r: str(r.get(sort_by, '') or ''),
                      reverse=(sort_dir == 'desc')) if sort_by else records
        rows_out = [[str(r.get(f, '') or '') for f in fields] for r in recs[:200]]
        return {'columns': columns, 'rows': rows_out}


def resolver_nombre_organizacion(db, org_id, default: str = '') -> str:
    """Resuelve el nombre de la organización dueña de los datos.

    Es el pie de página / autor por defecto de TODOS los informes: ninguno
    debe salir con un nombre personal hardcodeado (equivalente en el motor v2:
    `reports/dispatch_v2.aplicar_pie_organizacion`).

    Devuelve `default` si no hay sesión, no hay `org_id`, la organización no
    existe o su nombre está vacío — hay contextos (tests, pipelines sin DB)
    donde el step corre sin `ctx.db`.
    """
    if db is None or org_id is None:
        return default
    try:
        from backend.models import Organization
        org = db.query(Organization).filter(Organization.id == org_id).first()
    except Exception:
        return default
    if org and org.name:
        return org.name
    return default


def _etiquetas_de_filtros(db, filters: Optional[Dict[str, object]]) -> Dict[str, object]:
    """{id_dimension: valor} → {nombre_dimension: valor}, en el mismo orden.

    Los valores se devuelven CRUDOS (escalar o lista): quien los muestre
    debe pasarlos por `reports.branding.formatear_filtros` para no imprimir
    el `repr` de la lista (QA 2026-07-30, P1-2: "Mes: ['MAYO']").
    """
    if not filters:
        return {}
    try:
        from backend.models import Dimension
        dim_ids = []
        for k in filters.keys():
            try:
                dim_ids.append(int(k))
            except (ValueError, TypeError):
                continue
        dims = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all()
        nombre_por_id = {d.id_dimension: d.name for d in dims}
        etiquetas: Dict[str, object] = {}
        for k, v in filters.items():
            try:
                nombre = nombre_por_id.get(int(k), '')
            except (ValueError, TypeError):
                nombre = ''
            if nombre and v not in (None, '', [], ()):
                etiquetas[nombre] = v
        return etiquetas
    except Exception:
        return {}


def _load_branding(pdf_layout: dict, db, org_id: int) -> Optional[dict]:
    """Carga los assets de branding desde la DB y los convierte a base64."""
    import base64
    from backend.models import Organization, OrganizationAsset
    from backend.config import BASE_DIR

    brand_cfg = pdf_layout.get('branding')
    if not brand_cfg:
        return None

    assets_dir = BASE_DIR / 'data' / 'org_assets' / str(org_id)

    def _load_asset(asset_id) -> tuple:
        if not asset_id:
            return None, None
        asset = db.query(OrganizationAsset).filter(
            OrganizationAsset.id == asset_id,
            OrganizationAsset.org_id == org_id,
        ).first()
        if not asset:
            return None, None
        path = assets_dir / asset.filename
        if not path.exists():
            return None, None
        data = base64.b64encode(path.read_bytes()).decode('ascii')
        return data, asset.content_type

    left_b64, left_ct = _load_asset(brand_cfg.get('left_image_id'))
    right_b64, right_ct = _load_asset(brand_cfg.get('right_image_id'))

    center = brand_cfg.get('center_header', [])
    if isinstance(center, str):
        center = [center]

    # `pie_saneado` degrada a "" los pies legacy con nombre personal que
    # arrastran los layouts persistidos en la DB; el template cae entonces al
    # nombre de la organización (QA 2026-07-30, P1-1).
    from ..reports.branding import pie_saneado

    return {
        'left_image_b64': left_b64,
        'left_image_ct': left_ct or 'image/png',
        'right_image_b64': right_b64,
        'right_image_ct': right_ct or 'image/png',
        'center_header': center,
        'left_footer': pie_saneado(brand_cfg.get('left_footer', '')),
        'show_page_number': brand_cfg.get('show_page_number', True),
    }


def build_pdf_bytes(
    indicator,
    db,
    org_id: int,
    filters: Optional[Dict[str, object]] = None,
    branding_override: Optional[Dict[str, object]] = None,
    pdf_layout_override: Optional[Dict[str, object]] = None,
) -> bytes:
    """
    Genera el PDF como bytes para un indicador dado.
    Puede ser llamado desde el step o directamente desde el endpoint.

    filters: dict opcional {id_dimension_str: valor} que se propaga a
        _build_records para limitar los MetricData incluidos en charts/tablas.
    branding_override: dict opcional con overrides de branding ad‑hoc para
        esta generación (no se persiste). Se mergea sobre pdf_layout.branding
        antes de resolver assets y renderizar. Claves soportadas:
        left_image_id, right_image_id, center_header (list[str]),
        left_footer (str), show_page_number (bool).
    pdf_layout_override: dict opcional para usar un layout distinto al
        `indicator.pdf_layout` (ej: `pdf_layout_historico`). Si se pasa,
        este reemplaza completamente al layout persistido para esta
        generación (no se muta el indicator).
    """
    import locale
    from datetime import date
    from jinja2 import Environment, FileSystemLoader
    from weasyprint import HTML as WeasyprintHTML

    if pdf_layout_override is not None:
        pdf_layout = pdf_layout_override
    else:
        pdf_layout = indicator.pdf_layout
    if isinstance(pdf_layout, str):
        try:
            pdf_layout = json.loads(pdf_layout)
        except Exception:
            pdf_layout = {}

    # Merge branding_override sobre pdf_layout.branding (no muta el layout persistido)
    if branding_override:
        merged_layout = dict(pdf_layout)
        merged_branding = {**(pdf_layout.get('branding') or {}), **branding_override}
        merged_layout['branding'] = merged_branding
        pdf_layout = merged_layout

    raw_sections = pdf_layout.get('sections', [])
    records = _build_records(db, indicator, org_id, filters=filters)

    # ── Guardia de dataset vacío ──
    # Sin filas, todos los gráficos salen en blanco (ejes −0.04…0.04) y las
    # tablas con solo encabezados: un PDF que parece válido y no dice nada.
    # El router lo traduce a 400 accionable (QA 2026-07-30, P0-1).
    if not records:
        from ..reports.branding import formatear_filtros
        from ..reports.errores import DatosInsuficientes, mensaje_sin_datos
        etiquetas = _etiquetas_de_filtros(db, filters)
        raise DatosInsuficientes(mensaje_sin_datos(formatear_filtros(etiquetas)))

    # ── Auto-filtrar a la última evaluación si layout es modo "evaluacion" ──
    # Cuando el pdf_layout declara `"mode": "evaluacion"` y el usuario NO
    # filtró explícitamente las dimensiones temporales, recortamos records a la
    # última COMBINACIÓN temporal (todas las columnas del rol `evaluacion_num`,
    # ej Año + Hito). Esto evita que SummaryTable/StackedCount cuenten
    # registros de varios periodos (bug pre-fix: II A SIMCE mostraba 49
    # alumnos en counts cuando son 28 — sumaba todas las pruebas) y que dos
    # años con el mismo hito se fusionen en una sola evaluación.
    layout_mode = (pdf_layout.get('mode') or 'historico').lower()
    if layout_mode == 'evaluacion':
        # Resolver las columnas temporales del indicator (evaluacion_num)
        try:
            cr = json.loads(indicator.column_roles) if isinstance(indicator.column_roles, str) else (indicator.column_roles or {})
        except Exception:
            cr = {}
        columnas_periodo_auto = columnas_temporales_del_rol(cr)
        if columnas_periodo_auto:
            campos_periodo_auto = [_to_field_name(c) for c in columnas_periodo_auto]
            # Solo se respeta el filtro del usuario si cubre TODAS las columnas
            # temporales: filtrar únicamente el Hito (sin el Año) es justamente
            # el caso que fusionaba DIAGNOSTICO 2025 con DIAGNOSTICO 2026.
            campos_filtrados_usuario = set()
            if filters:
                try:
                    from backend.models import Dimension
                    dim_ids_in_filter = [int(k) for k in filters.keys()]
                    dims_in_filter = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids_in_filter)).all()
                    for d in dims_in_filter:
                        campos_filtrados_usuario.add(_to_field_name(d.name))
                except Exception:
                    pass
            user_filtered_period = all(
                campo in campos_filtrados_usuario for campo in campos_periodo_auto
            )
            if not user_filtered_period:
                combo_auto = ultima_combinacion_temporal(
                    records, columnas_periodo_auto,
                    _temporal_config_de_indicador(indicator),
                )
                if combo_auto:
                    # Mantener los de la evaluación más reciente. Para
                    # SummaryTable con comparePrevious hace falta el penúltimo
                    # período (delta), y esa tabla filtra internamente sobre los
                    # records que recibe: si recortáramos acá, el Δ quedaría
                    # vacío. Por eso NO recortamos si alguna sección lo pide
                    # (mantenemos histórico para que pueda comparar).
                    any_compare = any(
                        (sec.get('item') or {}).get('comparePrevious')
                        for sec in raw_sections
                        if sec.get('type') == 'table'
                    )
                    if not any_compare:
                        records = filtrar_records_por_combinacion(records, combo_auto) or records
                    # Si any_compare, dejamos records con todos los
                    # periodos. SummaryTable filtra a la última combinación
                    # internamente para counts, y StackedCount también lo hace
                    # por su propio filtro interno. (Ver fix en
                    # _chart_to_png_b64 y _table_section.)

    # Resolver nombre de la organización
    org_name = resolver_nombre_organizacion(db, org_id, default=str(org_id))

    # Cargar branding (logos + header)
    branding = _load_branding(pdf_layout, db, org_id)

    # ── Construir etiqueta de filtros aplicados (para enriquecer el cover) ──
    # {id_dimension: valor} → "Curso: 2°A · Mes: MAYO · Año: 2025".
    from ..reports.branding import formatear_filtros
    filters_label = formatear_filtros(_etiquetas_de_filtros(db, filters))

    # Si el layout declara `title` (sin sección cover explícita), inyectar
    # un encabezado minimalista al inicio del documento — al estilo LaTeX:
    # h1 grande centrado + subtítulo + filtros, sin portada con gradientes.
    layout_title = pdf_layout.get('title')
    layout_subtitle = pdf_layout.get('subtitle', '')
    has_cover_section = any(s.get('type') == 'cover' for s in raw_sections)

    # Renderizar cada sección
    rendered = []

    # Inyectar page_title si corresponde (antes de la primera sección)
    if layout_title and not has_cover_section:
        rendered.append({
            'type': 'page_title',
            'title': layout_title,
            'subtitle': layout_subtitle,
            'filters_label': filters_label,
        })

    for sec in raw_sections:
        t = sec.get('type')
        if t == 'cover':
            rendered.append({'type': 'cover', 'title': sec.get('title', indicator.name),
                             'subtitle': sec.get('subtitle', ''),
                             'filters_label': filters_label,
                             'org_label': org_name})
        elif t == 'page_break':
            rendered.append({'type': 'page_break'})
        elif t == 'text':
            rendered.append({'type': 'text', 'heading': sec.get('heading', ''),
                             'body': sec.get('body', '')})
        elif t == 'chart':
            item = sec.get('item', {})
            b64 = _chart_to_png_b64(item, records, indicator=indicator)
            rendered.append({'type': 'chart', 'heading': sec.get('heading', ''),
                             'image_b64': b64, 'caption': sec.get('caption', '')})
        elif t == 'table':
            item = sec.get('item', {})
            tdata = _table_section(item, records, indicator=indicator)
            rendered.append({'type': 'table', 'heading': sec.get('heading', ''),
                             'columns': tdata['columns'], 'rows': tdata['rows']})

    # Jinja2
    templates_dir = Path(__file__).parent.parent / 'templates'
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
    template = env.get_template('report_base.html')
    html_str = template.render(
        sections=rendered,
        org_name=org_name,
        report_date=date.today().strftime('%d/%m/%Y'),
        branding=branding,
    )

    return WeasyprintHTML(string=html_str).write_pdf()


class RenderPDFReport(Step):
    """
    Genera el informe PDF del indicador usando WeasyPrint.

    Parámetros:
        indicator_id (int): ID del indicador. Si no se pasa, se lee de ctx.params.

    Requiere:
        - ctx.db: sesión SQLAlchemy activa.
        - ctx.org_id: ID de organización para multi-tenancy.
        - El indicador debe tener pdf_layout configurado.

    Produce:
        - ctx.outputs['report_pdf']: Path al archivo informe.pdf generado.
    """

    def __init__(self, indicator_id: int = None):
        super().__init__(name='RenderPDFReport')
        self.indicator_id = indicator_id

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)
        ind_id = self.indicator_id or ctx.params.get('indicator_id')
        if not ind_id:
            self._log(f'[{self.name}] Error: indicator_id no especificado.')
            return

        from backend.models import Indicator
        indicator = ctx.db.query(Indicator).filter(
            Indicator.id_indicator == ind_id,
            Indicator.org_id == ctx.org_id,
        ).first()
        if not indicator:
            self._log(f'[{self.name}] Error: indicador {ind_id} no encontrado.')
            return

        try:
            pdf_bytes = build_pdf_bytes(indicator, ctx.db, ctx.org_id)

            out_dir = getattr(ctx, 'outputs_dir', None) or Path('.')
            out_dir = Path(out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / 'informe.pdf'
            out_path.write_bytes(pdf_bytes)

            ctx.outputs['report_pdf'] = out_path
            self._log(f'[{self.name}] PDF generado: {out_path}')
        except Exception as e:
            self._log(f'[{self.name}] Error generando PDF: {e}')
            raise

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)

class RenderHtmlReport(Step):
    """
    Equivalente WeasyPrint de RenderReport (LaTeX) — paridad visual con
    `formato_informe.tex`.

    Lee el MISMO esquema JSON que RenderReport (variables_documento +
    secciones_fijas + secciones_dinamicas), compone HTML con Jinja2 +
    `report_html_tools` y produce informe.pdf vía WeasyPrint.

    Parámetros:
        report_schema (dict, opcional): esquema directo. Si no se pasa,
            se lee de ctx.params['report_schema'] o ctx.params['report_schema_path'].
        output_filename (str): nombre del PDF de salida (default 'informe.pdf').
        template_name (str): nombre del template Jinja2 en
            backend/rgenerator/templates/ (default 'report_latex_paridad.html').

    Requiere:
        - ctx.aux_dir con tablas .xlsx e imágenes .png ya generadas (por
          GenerateGraphics + GenerateTables o pre-existentes).

    Opcional:
        - ctx.db + ctx.org_id: si el esquema no define `leftfooter` /
          `theauthor`, se rellenan con el nombre de la organización. Sin
          sesión de DB quedan vacíos (nunca un nombre personal).

    Produce:
        - ctx.outputs['report_pdf']: Path al PDF generado.
    """
    def __init__(self, report_schema: Optional[Dict] = None,
                 output_filename: str = "informe.pdf",
                 template_name: str = "report_latex_paridad.html"):
        super().__init__(name="RenderHtmlReport")
        self.report_schema = report_schema
        self.output_filename = output_filename
        self.template_name = template_name

    def run(self, ctx):
        from jinja2 import Environment, FileSystemLoader
        from weasyprint import HTML as WeasyprintHTML
        from ..tooling.report_html_tools import render_section, encode_image_b64

        before = self._snapshot_artifacts(ctx)
        if not getattr(self, "name", None):
            self.name = self.__class__.__name__

        # 1. Resolver schema (constructor → params → path)
        schema = self.report_schema or ctx.params.get("report_schema")
        if not schema:
            schema_path = ctx.params.get("report_schema_path")
            if schema_path:
                try:
                    with open(schema_path, "r", encoding="utf-8") as f:
                        schema = json.load(f)
                except Exception as e:
                    self._log(f"[{self.name}] Error cargando schema desde {schema_path}: {e}")

        if not schema:
            self._log(f"[{self.name}] Error: no se encontró report_schema.")
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # 2. Resolver aux_dir
        aux_dir = getattr(ctx, "aux_dir", None)
        if not aux_dir:
            aux_dir = (ctx.base_dir / "aux_files") if hasattr(ctx, "base_dir") else Path("aux_files")
        aux_dir = Path(aux_dir)
        if not aux_dir.exists():
            self._log(f"[{self.name}] Error: aux_dir no existe ({aux_dir}).")
            return

        base_dir = getattr(ctx, "base_dir", None)
        variables = dict(schema.get("variables_documento", {}))
        if "evaluacion" not in variables and getattr(ctx, "evaluation", None):
            variables["evaluacion"] = ctx.evaluation

        # 3. Branding (logos en header) + pie/autor por defecto
        branding = self._build_branding(variables, aux_dir, base_dir)

        # El pie izquierdo y el autor identifican a la organización dueña de
        # los datos, no a una persona. Los esquemas quedaron con la cadena
        # vacía; el nombre se resuelve acá en runtime contra la DB. Si el
        # esquema sí trae un valor explícito, ese gana — salvo que sea uno de
        # los pies legacy con nombre personal (`branding.LEFT_FOOTER_DENYLIST`),
        # que pueden venir de un spec guardado en la DB (QA 2026-07-30, P1-1).
        from ..reports.branding import pie_saneado

        org_name = resolver_nombre_organizacion(
            getattr(ctx, "db", None), getattr(ctx, "org_id", None)
        )
        leftfooter = pie_saneado(variables.get("leftfooter")) or org_name
        theauthor = pie_saneado(variables.get("theauthor")) or org_name

        # 4. Renderizar secciones (delega tablas e imágenes a report_html_tools)
        secciones_fijas = [
            render_section(s, aux_dir, base_dir)
            for s in schema.get("secciones_fijas", [])
        ]
        secciones_dinamicas = [
            render_section(s, aux_dir, base_dir)
            for s in schema.get("secciones_dinamicas", [])
        ]

        # 5. Render Jinja
        templates_dir = Path(__file__).parent.parent / "templates"
        env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
        template = env.get_template(self.template_name)
        html_str = template.render(
            documenttitle=variables.get("documenttitle", ""),
            schoolname=variables.get("schoolname", ""),
            centerheaderone=variables.get("centerheaderone", ""),
            centerheadertwo=variables.get("centerheadertwo", ""),
            centerheaderthree=variables.get("centerheaderthree", ""),
            leftfooter=leftfooter,
            theauthor=theauthor,
            branding=branding,
            secciones_fijas=secciones_fijas,
            secciones_dinamicas=secciones_dinamicas,
        )

        # 6. WeasyPrint → PDF (base_url permite resolver paths relativos en CSS)
        try:
            pdf_bytes = WeasyprintHTML(string=html_str, base_url=str(aux_dir)).write_pdf()
        except Exception as e:
            self._log(f"[{self.name}] Error en WeasyPrint: {e}")
            raise

        # 7. Escribir PDF
        out_dir = getattr(ctx, "outputs_dir", None) or aux_dir
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / self.output_filename
        out_path.write_bytes(pdf_bytes)

        ctx.outputs["report_pdf"] = out_path
        self._log(f"[{self.name}] PDF generado: {out_path} ({len(pdf_bytes)} bytes)")

        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)

    @staticmethod
    def _build_branding(variables: dict, aux_dir: Path, base_dir: Optional[Path]) -> dict:
        """Resuelve y codifica los logos `leftimage` / `rightimage` del esquema.

        Estrategia de resolución (igual a `formato_informe.tex` que usa rutas
        relativas a aux_dir, más fallback a `data/database/reports_templates/img/`
        donde están copiados los logos del repo):
            1. Path absoluto si existe.
            2. aux_dir / rel_path
            3. base_dir / rel_path (si base_dir presente)
            4. REPORTS_TEMPLATES_DIR / rel_path
            5. REPORTS_TEMPLATES_DIR / 'img' / basename(rel_path)
        """
        from ..tooling.report_html_tools import encode_image_b64

        def _resolve(rel_path):
            if not rel_path:
                return None
            p = Path(rel_path)
            if p.is_absolute() and p.exists():
                return p
            candidates = [aux_dir / rel_path]
            if base_dir is not None:
                candidates.append(Path(base_dir) / rel_path)
            candidates.append(REPORTS_TEMPLATES_DIR / rel_path)
            candidates.append(REPORTS_TEMPLATES_DIR / "img" / Path(rel_path).name)
            for c in candidates:
                if c.exists():
                    return c
            return None

        left = _resolve(variables.get("leftimage"))
        right = _resolve(variables.get("rightimage"))
        l_meta = encode_image_b64(left) if left else None
        r_meta = encode_image_b64(right) if right else None
        return {
            "left_image_b64": l_meta["b64"] if l_meta else None,
            "left_image_mime": l_meta["mime"] if l_meta else None,
            "right_image_b64": r_meta["b64"] if r_meta else None,
            "right_image_mime": r_meta["mime"] if r_meta else None,
        }


