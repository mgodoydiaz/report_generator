"""Orden temporal del motor PDF v1: la combinación snapshot y el eje de los
gráficos.

Primera mitad — el "último período" es la última COMBINACIÓN temporal.

El rol `evaluacion_num` puede declarar VARIAS columnas: DIA usa Hito + Año,
SIMCE Mes + Año, Fluidez Lectora N Prueba + Fecha. El filtro snapshot resolvía
el período con `evaluacion_num[0]` e ignoraba el resto, así que sin filtro de
año del usuario DIAGNOSTICO 2025 y DIAGNOSTICO 2026 caían en la misma
evaluación (en la data real de la org 1 el snapshot terminaba en INTERMEDIO
2025 por orden alfabético, con 3940 filas en vez de las 935 de la última).

La regla: la última combinación de todas las columnas del rol, ordenando cada
columna por (1) el orden declarado en `indicator.temporal_config`, (2) la
semántica de `reports.periodos` (años como int, hitos/meses/versiones por su
mes representativo), (3) `_natural_sort_key`.

Segunda mitad — el EJE de los gráficos usa el mismo orden declarado
(`clave_orden_categorias`). Antes ordenaba con `_natural_sort_key` a secas e
ignoraba `temporal_config`, así que un gráfico titulado "Evolución ... por Mes"
salía ABRIL·AGOSTO·JUNIO-JULIO·MAYO·OCTUBRE·SEPTIEMBRE (QA Cálculo Veloz
2026-08-03, H2).
"""
from __future__ import annotations

import pytest

from backend.rgenerator.core.report_steps import (
    METRIC_ID_KEY,
    _chart_to_png_b64,
    _natural_sort_key,
    _table_section,
    clave_orden_categorias,
    columnas_snapshot_temporal,
    columnas_temporales_del_rol,
    combinaciones_temporales,
    etiqueta_combinacion_temporal,
    filtrar_records_por_combinacion,
    orden_valor_temporal,
    ultima_combinacion_temporal,
)


# `column_roles` real del indicador DIA (org 1, id 2): el rol temporal declara
# Hito y Año, cada uno duplicado por las dos métricas vinculadas.
COLUMN_ROLES_DIA = {
    "logro_1": [
        {"metric_id": 6, "column": "Logro"},
        {"metric_id": 7, "column": "Logro"},
    ],
    "nivel_de_logro": [
        {"metric_id": 6, "column": "Nivel Logro"},
        {"metric_id": 7, "column": "Nivel Logro"},
    ],
    "evaluacion_num": [
        {"metric_id": 6, "column": "Hito"},
        {"metric_id": 7, "column": "Hito"},
        {"metric_id": 6, "column": "Año"},
        {"metric_id": 7, "column": "Año"},
    ],
}

# `temporal_config` real de DIA: Año numérico sin orden explícito, Hito con el
# orden del protocolo de la fundación.
TEMPORAL_CONFIG_DIA = {
    "levels": [
        {"label": "Año", "sort_mode": "numeric", "order": []},
        {"label": "Hito", "sort_mode": "custom",
         "order": ["DIAGNOSTICO", "INTERMEDIO", "CIERRE"]},
    ],
}

NIVELES = ["Inicial", "Intermedio", "Avanzado"]


class _IndicadorFake:
    """Stub mínimo con los atributos que leen `_table_section` / `_chart`."""

    def __init__(self, column_roles, achievement_levels=None,
                 role_formats=None, temporal_config=None):
        self.column_roles = column_roles
        self.achievement_levels = achievement_levels or []
        self.role_formats = role_formats or {}
        self.temporal_config = temporal_config or {}


# ──────────────────────── columnas del rol temporal ──────────────────────────

@pytest.mark.unit
class TestColumnasTemporalesDelRol:
    def test_deduplica_y_pone_el_anio_primero(self):
        # Las entries de DIA repiten Hito y Año (una por métrica) y declaran
        # Hito antes que Año: el año manda en la tupla de orden.
        assert columnas_temporales_del_rol(COLUMN_ROLES_DIA) == ["Año", "Hito"]

    def test_una_sola_columna(self):
        roles = {"evaluacion_num": [{"metric_id": 8, "column": "Versión"}]}
        assert columnas_temporales_del_rol(roles) == ["Versión"]

    def test_sin_columna_de_anio_conserva_el_orden_declarado(self):
        # Fluidez Lectora: N Prueba + Fecha, ninguna es la columna de año.
        roles = {"evaluacion_num": [{"metric_id": 10, "column": "N Prueba"},
                                    {"metric_id": 10, "column": "Fecha"}]}
        assert columnas_temporales_del_rol(roles) == ["N Prueba", "Fecha"]

    def test_rol_ausente_o_vacio(self):
        assert columnas_temporales_del_rol({}) == []
        assert columnas_temporales_del_rol(None) == []
        assert columnas_temporales_del_rol({"evaluacion_num": []}) == []


@pytest.mark.unit
class TestColumnasSnapshotTemporal:
    def test_el_rol_manda_sobre_el_period_field_del_layout(self):
        # El layout de DIA declara periodField '_hito', que es UNA de las
        # columnas del rol: el snapshot usa la combinación completa.
        assert columnas_snapshot_temporal("_hito", COLUMN_ROLES_DIA) == ["Año", "Hito"]

    def test_default_mes_no_es_una_declaracion_del_usuario(self):
        assert columnas_snapshot_temporal("_mes", COLUMN_ROLES_DIA) == ["Año", "Hito"]
        assert columnas_snapshot_temporal(None, COLUMN_ROLES_DIA) == ["Año", "Hito"]

    def test_period_field_ajeno_al_rol_gana(self):
        # Comportamiento previo al fix para layouts que apuntan a un field que
        # el rol no declara.
        assert columnas_snapshot_temporal("_fecha", COLUMN_ROLES_DIA) == ["fecha"]

    def test_sin_rol_temporal_y_sin_period_field(self):
        assert columnas_snapshot_temporal(None, {}) == []


# ─────────────────────────── orden de un valor ───────────────────────────────

@pytest.mark.unit
class TestOrdenValorTemporal:
    def test_hitos_por_semantica_sin_config(self):
        # DIAGNOSTICO→INICIO (mes 3) < INTERMEDIO (6) < CIERRE (11).
        claves = [orden_valor_temporal("Hito", h)
                  for h in ("DIAGNOSTICO", "INTERMEDIO", "CIERRE")]
        assert claves == sorted(claves)

    def test_anio_como_entero(self):
        assert orden_valor_temporal("Año", "2025") < orden_valor_temporal("Año", "2026")

    def test_meses_en_espanol(self):
        # ABRIL (4) < NOVIEMBRE (11): el orden alfabético coincide acá, pero
        # AGOSTO (8) > JUNIO (6) solo se ordena bien con la semántica.
        assert orden_valor_temporal("Mes", "JUNIO") < orden_valor_temporal("Mes", "AGOSTO")

    def test_versiones_idel(self):
        assert orden_valor_temporal("Versión", "1") < orden_valor_temporal("Versión", "3")

    def test_config_declarada_manda_sobre_la_semantica(self):
        cfg = {"levels": [{"label": "Hito", "order": ["CIERRE", "DIAGNOSTICO"]}]}
        assert (orden_valor_temporal("Hito", "CIERRE", cfg)
                < orden_valor_temporal("Hito", "DIAGNOSTICO", cfg))
        # Sin la config, la semántica los ordena al revés.
        assert (orden_valor_temporal("Hito", "DIAGNOSTICO")
                < orden_valor_temporal("Hito", "CIERRE"))

    def test_valor_no_clasificable_queda_al_final(self):
        assert (orden_valor_temporal("Hito", "CIERRE")
                < orden_valor_temporal("Hito", "SIN DATO"))

    def test_orden_natural_no_explota_con_tipos_mezclados(self):
        # '1 A' produce partes int y str en `_natural_sort_key`; comparar contra
        # una clave puramente textual no debe lanzar TypeError.
        a = orden_valor_temporal("Etapa", "1 A")
        b = orden_valor_temporal("Etapa", "final")
        assert (a < b) or (b < a)


# ──────────────────────── combinaciones temporales ───────────────────────────

def _records_dos_anios():
    """CIERRE 2025 y DIAGNOSTICO 2026: el hito "menor" pertenece al año mayor."""
    return (
        [{"_ano": "2025", "_hito": "CIERRE", "_curso": "1 A"} for _ in range(4)]
        + [{"_ano": "2026", "_hito": "DIAGNOSTICO", "_curso": "1 A"} for _ in range(3)]
    )


@pytest.mark.unit
class TestCombinacionesTemporales:
    def test_dos_columnas_el_anio_manda(self):
        combos = combinaciones_temporales(_records_dos_anios(), ["Año", "Hito"])
        assert combos == [
            {"Año": "2025", "Hito": "CIERRE"},
            {"Año": "2026", "Hito": "DIAGNOSTICO"},
        ]
        assert ultima_combinacion_temporal(_records_dos_anios(), ["Año", "Hito"]) == {
            "Año": "2026", "Hito": "DIAGNOSTICO",
        }

    def test_temporal_config_fuerza_el_orden(self):
        # Declarando CIERRE después de DIAGNOSTICO dentro del mismo año no
        # cambia nada (manda el año), pero con un solo año sí.
        records = [{"_ano": "2026", "_hito": "CIERRE"},
                   {"_ano": "2026", "_hito": "DIAGNOSTICO"}]
        cfg = {"levels": [{"label": "Hito", "order": ["CIERRE", "DIAGNOSTICO"]}]}
        assert ultima_combinacion_temporal(records, ["Año", "Hito"], cfg) == {
            "Año": "2026", "Hito": "DIAGNOSTICO",
        }
        # Con el orden del protocolo (DIAGNOSTICO primero) gana CIERRE.
        assert ultima_combinacion_temporal(
            records, ["Año", "Hito"], TEMPORAL_CONFIG_DIA
        ) == {"Año": "2026", "Hito": "CIERRE"}

    def test_una_columna_identico_al_orden_natural_previo(self):
        """Con una sola entrada en el rol el resultado no cambia."""
        records = [{"_mes": m} for m in ("ABRIL", "NOVIEMBRE", "MAYO")]
        previo = sorted({r["_mes"] for r in records}, key=_natural_sort_key)[-1]
        assert ultima_combinacion_temporal(records, ["Mes"]) == {"Mes": previo}
        assert previo == "NOVIEMBRE"

    def test_sin_datos_devuelve_none(self):
        assert combinaciones_temporales([], ["Año", "Hito"]) == []
        assert ultima_combinacion_temporal([], ["Año", "Hito"]) is None

    def test_sin_columnas_devuelve_none(self):
        assert ultima_combinacion_temporal(_records_dos_anios(), []) is None

    def test_columna_vacia_en_todos_los_records_se_ignora(self):
        records = [{"_ano": None, "_hito": "CIERRE"},
                   {"_ano": "", "_hito": "DIAGNOSTICO"}]
        # Sin año utilizable, el orden cae en la columna que sí tiene datos.
        assert ultima_combinacion_temporal(records, ["Año", "Hito"]) == {"Hito": "CIERRE"}

    def test_combinacion_incompleta_no_compite(self):
        records = _records_dos_anios() + [{"_ano": None, "_hito": "CIERRE"}]
        assert ultima_combinacion_temporal(records, ["Año", "Hito"]) == {
            "Año": "2026", "Hito": "DIAGNOSTICO",
        }

    def test_filtrar_por_combinacion_exige_todas_las_columnas(self):
        records = _records_dos_anios()
        combo = {"Año": "2026", "Hito": "DIAGNOSTICO"}
        assert len(filtrar_records_por_combinacion(records, combo)) == 3
        # Sin combinación no filtra (fail-open).
        assert filtrar_records_por_combinacion(records, None) is records

    def test_etiqueta_legible(self):
        assert etiqueta_combinacion_temporal(
            {"Año": "2025", "Hito": "CIERRE"}) == "2025 CIERRE"
        assert etiqueta_combinacion_temporal(None) == ""


# ───────────────────── regresión: el snapshot respeta el año ─────────────────

def _records_dia_dos_diagnosticos():
    """Mismo hito (DIAGNOSTICO) en 2025 y 2026, con niveles distintos.

    2025: 6 alumnos, todos "Inicial". 2026: 9 alumnos, 3 por nivel.
    Sin combinación temporal los dos años se sumaban en la misma evaluación.
    """
    records = []
    for i in range(6):
        records.append({
            METRIC_ID_KEY: 6, "_curso": "1 A", "_ano": "2025",
            "_hito": "DIAGNOSTICO", "_nombre": f"Viejo {i:02d}",
            "_nivel_logro": "Inicial", "_logro": 0.2,
        })
    for i in range(9):
        records.append({
            METRIC_ID_KEY: 6, "_curso": "1 A", "_ano": "2026",
            "_hito": "DIAGNOSTICO", "_nombre": f"Nuevo {i:02d}",
            "_nivel_logro": NIVELES[i % 3], "_logro": 0.8,
        })
    return records


@pytest.fixture
def barras_espiadas(monkeypatch):
    """Captura las llamadas a `Axes.bar` de `_chart_to_png_b64`."""
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from matplotlib.axes import Axes

    capturadas: list[tuple] = []
    original = Axes.bar

    def _bar_espia(self, x, height, *args, **kwargs):
        capturadas.append((kwargs.get("label"), list(height)))
        return original(self, x, height, *args, **kwargs)

    monkeypatch.setattr(Axes, "bar", _bar_espia)
    return capturadas


@pytest.mark.unit
class TestSnapshotNoSumaDosAnios:
    def _indicador(self):
        return _IndicadorFake(
            column_roles=COLUMN_ROLES_DIA,
            achievement_levels=[{"name": n, "order": i} for i, n in enumerate(NIVELES)],
            temporal_config=TEMPORAL_CONFIG_DIA,
        )

    def test_stacked_cuenta_solo_el_anio_mas_reciente(self, barras_espiadas):
        item = {
            "component": "StackedCountByGroup",
            "groupField": "_curso",
            "levelField": "_nivel_de_logro",
        }
        _chart_to_png_b64(item, _records_dia_dos_diagnosticos(),
                          indicator=self._indicador())
        por_nivel = {label: vals for label, vals in barras_espiadas if label}
        total = sum(v for vals in por_nivel.values() for v in vals)
        assert total == 9, f"el snapshot sumó {total} (fusionó DIAGNOSTICO 2025 y 2026)"
        assert por_nivel["Inicial"] == [3]

    def test_summary_table_cuenta_solo_el_anio_mas_reciente(self):
        item = {
            "component": "SummaryTable",
            "groupField": "_curso",
            "valueField": ["_logro_1"],
            "periodField": "_hito",
        }
        out = _table_section(item, _records_dia_dos_diagnosticos(),
                             indicator=self._indicador())
        assert len(out["rows"]) == 1
        fila = out["rows"][0]
        assert fila[1] == "9"                       # Alumnos
        assert [int(v) for v in fila[-3:]] == [3, 3, 3]
        # El promedio también sale solo de 2026 (0.8, no la mezcla con 0.2).
        assert fila[2] == "0.8"

    def test_barbygroup_promedia_solo_el_anio_mas_reciente(self, barras_espiadas):
        item = {
            "component": "BarByGroup",
            "groupField": "_curso",
            "valueField": "_logro_1",
        }
        _chart_to_png_b64(item, _records_dia_dos_diagnosticos(),
                          indicator=self._indicador())
        alturas = [v for _, vals in barras_espiadas for v in vals]
        assert alturas == pytest.approx([0.8])


# ═════════════════ orden declarado en el EJE de los gráficos ═════════════════
#
# QA Cálculo Veloz 2026-08-03 (H2): los 3 gráficos del informe histórico
# ordenaban el eje de meses alfabéticamente aunque el indicador ya declaraba el
# orden correcto en `temporal_config`. `_orden_declarado` existía pero solo lo
# consumía `combinaciones_temporales`.

# `temporal_config` real del indicador 4 (Cálculo Veloz, org 1). Los meses son
# el caso patológico: alfabéticamente AGOSTO va segundo y JUNIO-JULIO tercero.
TEMPORAL_CONFIG_CV = {
    "levels": [
        {"label": "Mes", "sort_mode": "custom",
         "order": ["MARZO", "ABRIL", "MAYO", "JUNIO-JULIO", "AGOSTO",
                   "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]},
        {"label": "N Prueba", "sort_mode": "numeric", "order": []},
    ],
}

COLUMN_ROLES_CV = {
    "logro_1": [{"metric_id": 9, "column": "Nota"}],
    "nivel_de_logro": [{"metric_id": 9, "column": "Nivel"}],
    "evaluacion_num": [{"metric_id": 9, "column": "Mes"},
                       {"metric_id": 9, "column": "N Prueba"}],
}

# El orden en que los meses llegan a los records: revuelto a propósito, para
# que ni el orden de inserción ni el alfabético den por casualidad el correcto.
MESES_CV_DESORDENADOS = ["OCTUBRE", "ABRIL", "SEPTIEMBRE", "JUNIO-JULIO",
                         "AGOSTO", "MAYO"]
MESES_CV_CRONOLOGICOS = ["ABRIL", "MAYO", "JUNIO-JULIO", "AGOSTO",
                         "SEPTIEMBRE", "OCTUBRE"]


@pytest.mark.unit
class TestClaveOrdenCategorias:
    def test_sin_config_es_el_orden_natural_de_siempre(self):
        # Identidad, no equivalencia: sin declaración el comportamiento no
        # cambia en absoluto respecto de antes del fix.
        assert clave_orden_categorias("Mes", None) is _natural_sort_key
        assert clave_orden_categorias("Mes", {}) is _natural_sort_key

    def test_order_vacio_cae_al_orden_natural(self):
        # DIA declara Año y IDEL declara Versión con `order: []` porque ya
        # ordenan solas. No deben pasar por el tier declarado.
        cfg = {"levels": [{"label": "Versión", "sort_mode": "numeric", "order": []}]}
        assert clave_orden_categorias("Versión", cfg) is _natural_sort_key

    def test_columna_no_declarada_cae_al_orden_natural(self):
        # Curso no es una dimensión temporal: el eje de cursos no se toca.
        assert clave_orden_categorias("_curso", TEMPORAL_CONFIG_CV) is _natural_sort_key

    def test_meses_de_calculo_veloz_salen_cronologicos(self):
        clave = clave_orden_categorias("_mes", TEMPORAL_CONFIG_CV)
        assert sorted(MESES_CV_DESORDENADOS, key=clave) == MESES_CV_CRONOLOGICOS
        # Y el alfabético (lo que hacía antes) NO es este orden.
        assert sorted(MESES_CV_DESORDENADOS, key=_natural_sort_key) != MESES_CV_CRONOLOGICOS

    def test_matchea_el_label_del_config_con_el_field_del_layout(self):
        # El layout trae `_mes`/`_version`; el config trae "Mes"/"Versión".
        cfg = {"levels": [{"label": "Versión", "order": ["v3", "v1", "v2"]}]}
        clave = clave_orden_categorias("_version", cfg)
        assert sorted(["v1", "v2", "v3"], key=clave) == ["v3", "v1", "v2"]

    def test_valores_no_declarados_quedan_despues_y_no_explotan(self):
        clave = clave_orden_categorias("_mes", TEMPORAL_CONFIG_CV)
        valores = ["SEPTIEMBRE", "SIN MES", "ABRIL", "2 A"]
        ordenados = sorted(valores, key=clave)
        assert ordenados[:2] == ["ABRIL", "SEPTIEMBRE"]
        assert set(ordenados[2:]) == {"SIN MES", "2 A"}

    def test_hitos_dia_respetan_el_protocolo(self):
        # Alfabéticamente sería CIERRE·DIAGNOSTICO·INTERMEDIO.
        clave = clave_orden_categorias("_hito", TEMPORAL_CONFIG_DIA)
        assert sorted(["INTERMEDIO", "CIERRE", "DIAGNOSTICO"], key=clave) == [
            "DIAGNOSTICO", "INTERMEDIO", "CIERRE",
        ]


@pytest.fixture
def ejes_espiados(monkeypatch):
    """Captura las categorías del eje X: las `x` de `bar` y los xticklabels.

    `StackedCountByGroup` pasa las categorías como `x` de `Axes.bar`;
    `GroupedBarByPeriod` usa posiciones numéricas y las etiqueta aparte con
    `set_xticklabels`.
    """
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from matplotlib.axes import Axes

    capturado: dict[str, list] = {"bar_x": [], "xticklabels": []}
    bar_original = Axes.bar
    labels_original = Axes.set_xticklabels

    def _bar_espia(self, x, height, *args, **kwargs):
        xs = list(x)
        if xs and all(isinstance(v, str) for v in xs):
            capturado["bar_x"] = xs
        return bar_original(self, x, height, *args, **kwargs)

    def _labels_espia(self, labels, *args, **kwargs):
        capturado["xticklabels"] = [str(l) for l in labels]
        return labels_original(self, labels, *args, **kwargs)

    monkeypatch.setattr(Axes, "bar", _bar_espia)
    monkeypatch.setattr(Axes, "set_xticklabels", _labels_espia)
    return capturado


def _records_cv_por_mes():
    """Un record por mes y curso, con el mes desordenado en la lista."""
    return [
        {METRIC_ID_KEY: 9, "_mes": mes, "_n_prueba": str(i + 1),
         "_curso": curso, "_nivel": NIVELES[i % 3], "_nota": 0.5 + i / 100}
        for i, mes in enumerate(MESES_CV_DESORDENADOS)
        for curso in ("1 A", "2 A")
    ]


@pytest.mark.unit
class TestEjeTemporalRespetaElOrdenDeclarado:
    def _indicador_cv(self):
        return _IndicadorFake(
            column_roles=COLUMN_ROLES_CV,
            achievement_levels=[{"name": n, "order": i} for i, n in enumerate(NIVELES)],
            temporal_config=TEMPORAL_CONFIG_CV,
        )

    def test_grouped_bar_ordena_el_eje_de_meses(self, ejes_espiados):
        item = {
            "component": "GroupedBarByPeriod",
            "groupField": "_curso",
            "periodField": "_mes",
            "valueField": "_logro_1",
        }
        _chart_to_png_b64(item, _records_cv_por_mes(), indicator=self._indicador_cv())
        assert ejes_espiados["xticklabels"] == MESES_CV_CRONOLOGICOS

    def test_grouped_bar_sin_temporal_config_conserva_el_alfabetico(self, ejes_espiados):
        """Fallback: sin declaración, el comportamiento previo intacto."""
        item = {
            "component": "GroupedBarByPeriod",
            "groupField": "_curso",
            "periodField": "_mes",
            "valueField": "_logro_1",
        }
        indicador = _IndicadorFake(column_roles=COLUMN_ROLES_CV)
        _chart_to_png_b64(item, _records_cv_por_mes(), indicator=indicador)
        assert ejes_espiados["xticklabels"] == sorted(
            MESES_CV_DESORDENADOS, key=_natural_sort_key
        )

    def test_stacked_ordena_el_eje_cuando_agrupa_por_mes(self, ejes_espiados):
        """Layout histórico: el groupField ES la columna de período."""
        item = {
            "component": "StackedCountByGroup",
            "groupField": "_mes",
            "levelField": "_nivel_de_logro",
        }
        _chart_to_png_b64(item, _records_cv_por_mes(), indicator=self._indicador_cv())
        assert ejes_espiados["bar_x"] == MESES_CV_CRONOLOGICOS

    def test_stacked_no_altera_el_eje_de_cursos(self, ejes_espiados):
        """Curso no está declarado en `temporal_config`: orden natural."""
        item = {
            "component": "StackedCountByGroup",
            "groupField": "_curso",
            "levelField": "_nivel_de_logro",
        }
        _chart_to_png_b64(item, _records_cv_por_mes(), indicator=self._indicador_cv())
        assert ejes_espiados["bar_x"] == ["1 A", "2 A"]

    def test_stacked_por_hito_sigue_el_protocolo_dia(self, ejes_espiados):
        """No romper DIA: DIAGNOSTICO→INTERMEDIO→CIERRE, no el alfabético."""
        records = [
            {METRIC_ID_KEY: 6, "_ano": "2026", "_hito": hito, "_curso": "1 A",
             "_nivel_logro": NIVELES[i % 3], "_logro": 0.5}
            for i, hito in enumerate(["INTERMEDIO", "CIERRE", "DIAGNOSTICO"])
        ]
        item = {
            "component": "StackedCountByGroup",
            "groupField": "_hito",
            "levelField": "_nivel_de_logro",
        }
        indicador = _IndicadorFake(
            column_roles=COLUMN_ROLES_DIA,
            achievement_levels=[{"name": n, "order": i} for i, n in enumerate(NIVELES)],
            temporal_config=TEMPORAL_CONFIG_DIA,
        )
        _chart_to_png_b64(item, records, indicator=indicador)
        assert ejes_espiados["bar_x"] == ["DIAGNOSTICO", "INTERMEDIO", "CIERRE"]

    def test_stacked_por_version_idel_no_cambia(self, ejes_espiados):
        """IDEL declara Versión con `order: []` → orden natural, como antes."""
        roles = {
            "nivel_de_logro": [{"metric_id": 8, "column": "Nivel"}],
            "evaluacion_num": [{"metric_id": 8, "column": "Versión"},
                               {"metric_id": 8, "column": "Año"}],
        }
        cfg = {"levels": [{"label": "Año", "sort_mode": "numeric", "order": []},
                          {"label": "Versión", "sort_mode": "numeric", "order": []}]}
        records = [
            {METRIC_ID_KEY: 8, "_ano": "2025", "_version": v, "_nivel": NIVELES[i % 3]}
            for i, v in enumerate(["3", "1", "2"])
        ]
        item = {
            "component": "StackedCountByGroup",
            "groupField": "_version",
            "levelField": "_nivel_de_logro",
        }
        indicador = _IndicadorFake(
            column_roles=roles,
            achievement_levels=[{"name": n, "order": i} for i, n in enumerate(NIVELES)],
            temporal_config=cfg,
        )
        _chart_to_png_b64(item, records, indicator=indicador)
        assert ejes_espiados["bar_x"] == ["1", "2", "3"]

    def test_summary_table_ordena_sus_filas_igual_que_los_graficos(self):
        """Tabla y gráfico en la misma página no pueden discrepar en el orden."""
        item = {
            "component": "SummaryTable",
            "groupField": "_mes",
            "valueField": ["_logro_1"],
            "periodField": "_mes",
        }
        out = _table_section(item, _records_cv_por_mes(),
                             indicator=self._indicador_cv())
        assert [fila[0] for fila in out["rows"]] == MESES_CV_CRONOLOGICOS
