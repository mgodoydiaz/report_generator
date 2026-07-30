"""Conteos por nivel restringidos a la métrica de origen del rol (motor PDF v1).

Un indicador puede vincular varias métricas cuya misma columna se proyecta al
mismo field: en DIA, `column_roles.nivel_de_logro` apunta a la métrica 6
("Resultados DIA por estudiante") y a la 7 ("Resultados DIA por Pregunta"),
ambas con la columna "Nivel Logro". `_build_records` concatena las filas de
todas las métricas, así que `StackedCountByGroup` y las columnas de nivel de
`SummaryTable` sumaban preguntas como si fueran alumnos (barra 25 con 15
alumnos en la org demo).

La regla: la métrica fuente de un rol es `entries[0].metric_id` — misma
convención que `_resolve_field`, que ya privilegia la primera entrada.
"""
from __future__ import annotations

import pytest

from backend.rgenerator.core.report_steps import (
    METRIC_ID_KEY,
    _table_section,
    filtrar_records_por_metrica,
    metric_id_del_rol,
    rol_de_campo,
    rol_de_campo_de_valor,
    records_para_campo_de_valor,
)


# `column_roles` real del indicador DIA (org 1, id 2), recortado.
COLUMN_ROLES_DIA = {
    "logro_1": [
        {"metric_id": 6, "column": "Logro"},
        {"metric_id": 7, "column": "Logro"},
    ],
    "nivel_de_logro": [
        {"metric_id": 6, "column": "Nivel Logro"},
        {"metric_id": 7, "column": "Nivel Logro"},
    ],
    "habilidad": [
        {"metric_id": 6, "column": "Habilidad"},
        {"metric_id": 7, "column": "Habilidad"},
    ],
    "habilidad_2": [{"metric_id": 7, "column": "Eje Temático"}],
    "evaluacion_num": [{"metric_id": 6, "column": "Hito"}],
}

# `column_roles` de Fluidez Lectora (org 1, id 5): una sola métrica, el nivel
# vive en "Categoria" y la segunda categoría contada ("Calidad lectora") cuelga
# del rol habilidad — no de nivel_de_logro.
COLUMN_ROLES_FL = {
    "logro_1": [{"metric_id": 10, "column": "Cantidad"}],
    "nivel_de_logro": [{"metric_id": 10, "column": "Categoria"}],
    "habilidad": [{"metric_id": 10, "column": "Calidad lectora"}],
}


@pytest.mark.unit
class TestMetricIdDelRol:
    def test_rol_con_dos_metricas_devuelve_la_primera(self):
        assert metric_id_del_rol(COLUMN_ROLES_DIA, "nivel_de_logro") == 6

    def test_rol_con_una_metrica(self):
        assert metric_id_del_rol(COLUMN_ROLES_DIA, "habilidad_2") == 7

    def test_rol_ausente_devuelve_none(self):
        assert metric_id_del_rol(COLUMN_ROLES_DIA, "calidad_lectora") is None

    def test_column_roles_vacio_o_none(self):
        assert metric_id_del_rol({}, "nivel_de_logro") is None
        assert metric_id_del_rol(None, "nivel_de_logro") is None

    def test_rol_con_lista_vacia(self):
        assert metric_id_del_rol({"nivel_de_logro": []}, "nivel_de_logro") is None

    def test_entrada_sin_metric_id(self):
        roles = {"nivel_de_logro": [{"column": "Nivel Logro"}]}
        assert metric_id_del_rol(roles, "nivel_de_logro") is None

    def test_metric_id_string_se_coacciona_a_int(self):
        roles = {"nivel_de_logro": [{"metric_id": "6", "column": "Nivel Logro"}]}
        assert metric_id_del_rol(roles, "nivel_de_logro") == 6

    def test_metric_id_no_numerico_devuelve_none(self):
        roles = {"nivel_de_logro": [{"metric_id": "abc", "column": "X"}]}
        assert metric_id_del_rol(roles, "nivel_de_logro") is None


@pytest.mark.unit
class TestRolDeCampo:
    def test_campo_del_rol_nivel_de_logro(self):
        assert rol_de_campo(COLUMN_ROLES_DIA, "_nivel_logro") == "nivel_de_logro"

    def test_campo_de_otro_rol(self):
        # Fluidez Lectora cuenta "Calidad lectora", que es rol habilidad: la
        # métrica fuente NO siempre es la de nivel_de_logro.
        assert rol_de_campo(COLUMN_ROLES_FL, "_calidad_lectora") == "habilidad"
        assert rol_de_campo(COLUMN_ROLES_FL, "_categoria") == "nivel_de_logro"

    def test_campo_desconocido_devuelve_none(self):
        assert rol_de_campo(COLUMN_ROLES_DIA, "_curso") is None

    def test_campo_no_string_o_sin_prefijo(self):
        assert rol_de_campo(COLUMN_ROLES_DIA, "nivel_logro") is None
        assert rol_de_campo(COLUMN_ROLES_DIA, None) is None


@pytest.mark.unit
class TestFiltrarRecordsPorMetrica:
    def test_filtra_por_metric_id(self):
        records = [
            {METRIC_ID_KEY: 6, "_nivel_logro": "Inicial"},
            {METRIC_ID_KEY: 7, "_nivel_logro": "Inicial"},
            {METRIC_ID_KEY: 6, "_nivel_logro": "Avanzado"},
        ]
        assert len(filtrar_records_por_metrica(records, 6)) == 2

    def test_metric_id_none_no_filtra(self):
        records = [{METRIC_ID_KEY: 6}, {METRIC_ID_KEY: 7}]
        assert filtrar_records_por_metrica(records, None) == records

    def test_records_sin_metric_id_no_se_filtran(self):
        """Compat con tests/configs viejos que arman records a mano."""
        records = [{"_nivel_logro": "Inicial"}, {"_nivel_logro": "Avanzado"}]
        assert filtrar_records_por_metrica(records, 6) == records

    def test_records_vacios(self):
        assert filtrar_records_por_metrica([], 6) == []

    def test_filtro_vacio_degrada_a_todos(self):
        """Fail-open: mejor el conteo inflado que un gráfico en blanco."""
        records = [{METRIC_ID_KEY: 7, "_nivel_logro": "Inicial"}]
        assert filtrar_records_por_metrica(records, 6) == records


# ───────────────────────── regresión del conteo ──────────────────────────────

NIVELES = ["Inicial", "Intermedio", "Avanzado"]


def _records_dia_sinteticos():
    """15 alumnos (metric 6) + 10 preguntas (metric 7) con los MISMOS niveles.

    Reproduce el bug: sin distinguir la métrica de origen el conteo daba 25.
    """
    records = []
    for i in range(15):
        records.append({
            METRIC_ID_KEY: 6,
            "_curso": "3° Básico A",
            "_hito": "INTERMEDIO",
            "_nombre": f"Estudiante {i:02d}",
            "_nivel_logro": NIVELES[i % 3],
            "_logro": 0.5,
        })
    for j in range(10):
        records.append({
            METRIC_ID_KEY: 7,
            "_curso": "3° Básico A",
            "_hito": "INTERMEDIO",
            "_nivel_logro": NIVELES[j % 3],
            "_logro": 0.5,
        })
    return records


class _IndicadorFake:
    """Stub mínimo con los atributos que leen _table_section / _chart."""

    def __init__(self, column_roles, achievement_levels, role_formats=None):
        self.column_roles = column_roles
        self.achievement_levels = achievement_levels
        self.role_formats = role_formats or {}


@pytest.mark.unit
class TestConteoPorNivelUnaSolaMetrica:
    """El conteo por nivel cuenta 15 alumnos, no 25 filas."""

    def test_helper_cuenta_solo_la_metrica_fuente(self):
        records = _records_dia_sinteticos()
        assert len(records) == 25

        mid = metric_id_del_rol(COLUMN_ROLES_DIA, "nivel_de_logro")
        filtrados = filtrar_records_por_metrica(records, mid)

        assert len(filtrados) == 15
        conteo = {n: sum(1 for r in filtrados if r["_nivel_logro"] == n)
                  for n in NIVELES}
        assert sum(conteo.values()) == 15
        assert conteo == {"Inicial": 5, "Intermedio": 5, "Avanzado": 5}

    def test_summary_table_no_suma_preguntas_como_alumnos(self):
        ind = _IndicadorFake(
            column_roles=COLUMN_ROLES_DIA,
            achievement_levels=[{"name": n, "order": i} for i, n in enumerate(NIVELES)],
        )
        item = {
            "component": "SummaryTable",
            "groupField": "_curso",
            "valueField": ["_logro_1"],
            "periodField": "_hito",
        }
        out = _table_section(item, _records_dia_sinteticos(), indicator=ind)

        assert out["columns"][:2] == ["Curso", "Alumnos"]
        assert out["columns"][-3:] == NIVELES
        assert len(out["rows"]) == 1
        fila = out["rows"][0]
        conteos = [int(v) for v in fila[-3:]]
        assert sum(conteos) == 15, f"conteo por nivel infló a {sum(conteos)}"
        assert fila[1] == "15"  # columna Alumnos


@pytest.mark.unit
class TestNAlumnosSinIdentidadFantasma:
    """Las filas sin rut/nombre/nombre_norm no suman un alumno extra."""

    def _item(self):
        return {
            "component": "SummaryTable",
            "groupField": "_curso",
            "valueField": ["_logro_1"],
            "periodField": "_hito",
        }

    def _indicador(self):
        return _IndicadorFake(
            column_roles={
                "logro_1": [{"metric_id": 6, "column": "Logro"}],
                "nivel_de_logro": [{"metric_id": 6, "column": "Nivel Logro"}],
                "evaluacion_num": [{"metric_id": 6, "column": "Hito"}],
            },
            achievement_levels=[{"name": n, "order": i} for i, n in enumerate(NIVELES)],
        )

    def test_fila_sin_identidad_no_cuenta(self):
        records = [
            {METRIC_ID_KEY: 6, "_curso": "1 A", "_hito": "H1",
             "_nombre": f"Alumno {i}", "_nivel_logro": "Inicial", "_logro": 0.5}
            for i in range(3)
        ]
        records.append({METRIC_ID_KEY: 6, "_curso": "1 A", "_hito": "H1",
                        "_nombre": None, "_nivel_logro": "Inicial", "_logro": 0.5})
        records.append({METRIC_ID_KEY: 6, "_curso": "1 A", "_hito": "H1",
                        "_nombre": "", "_nivel_logro": "Inicial", "_logro": 0.5})

        out = _table_section(self._item(), records, indicator=self._indicador())
        assert out["rows"][0][1] == "3"

    def test_nombre_norm_cierra_la_cadena_de_identidad(self):
        """DIA trae filas con `Nombre` nulo y `Nombre_Norm` poblado."""
        records = [
            {METRIC_ID_KEY: 6, "_curso": "1 A", "_hito": "H1",
             "_nombre": "Alumno A", "_nombre_norm": "ALUMNO A",
             "_nivel_logro": "Inicial", "_logro": 0.5},
            {METRIC_ID_KEY: 6, "_curso": "1 A", "_hito": "H1",
             "_nombre": None, "_nombre_norm": "ALUMNO B",
             "_nivel_logro": "Inicial", "_logro": 0.5},
        ]
        out = _table_section(self._item(), records, indicator=self._indicador())
        assert out["rows"][0][1] == "2"

    def test_sin_ninguna_clave_de_identidad_cae_a_len_records(self):
        records = [
            {METRIC_ID_KEY: 6, "_curso": "1 A", "_hito": "H1",
             "_nivel_logro": "Inicial", "_logro": 0.5}
            for _ in range(4)
        ]
        out = _table_section(self._item(), records, indicator=self._indicador())
        assert out["rows"][0][1] == "4"


@pytest.fixture
def barras_espiadas(monkeypatch):
    """Captura las llamadas a Axes.bar de `_chart_to_png_b64`.

    Devuelve una lista de (label, [alturas]) — permite verificar el conteo
    real del gráfico sin leer el PNG.
    """
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
class TestStackedCountByGroupUnaSolaMetrica:
    """El gráfico stacked cuenta solo la métrica dueña del campo contado."""

    def test_barra_suma_15_alumnos_no_25_filas(self, barras_espiadas):
        from backend.rgenerator.core.report_steps import _chart_to_png_b64

        ind = _IndicadorFake(
            column_roles=COLUMN_ROLES_DIA,
            achievement_levels=[{"name": n, "order": i} for i, n in enumerate(NIVELES)],
        )
        item = {
            "component": "StackedCountByGroup",
            "groupField": "_curso",
            "levelField": "_nivel_de_logro",
            "periodField": "_hito",
        }
        b64 = _chart_to_png_b64(item, _records_dia_sinteticos(), indicator=ind)
        assert b64

        por_nivel = {label: vals for label, vals in barras_espiadas if label}
        assert set(por_nivel) == set(NIVELES)
        total = sum(v for vals in por_nivel.values() for v in vals)
        assert total == 15, f"la barra sumó {total} (preguntas contadas como alumnos)"

    def test_fluidez_lectora_dos_stacked_distintos(self, barras_espiadas):
        """No-regresión del fix de `categoryField` (QA 2026-07-30, P1-8).

        FL tiene una sola métrica, así que el filtro por métrica es no-op y los
        dos gráficos deben seguir contando categorías distintas.
        """
        from backend.rgenerator.core.report_steps import _chart_to_png_b64

        ind = _IndicadorFake(column_roles=COLUMN_ROLES_FL, achievement_levels=[])
        records = []
        for cat, cal, n in [("BAJA", "Silábica", 3), ("MEDIA", "Unidades Cortas", 4),
                            ("ALTA", "Fluida", 5)]:
            for _ in range(n):
                records.append({
                    METRIC_ID_KEY: 10, "_curso": "I A", "_categoria": cat,
                    "_calidad_lectora": cal, "_cantidad": 100,
                })

        item_cat = {"component": "StackedCountByGroup", "groupField": "_curso",
                    "categoryField": "_logro"}
        _chart_to_png_b64(item_cat, records, indicator=ind)
        niveles_cat = {label for label, _ in barras_espiadas if label}

        barras_espiadas.clear()
        item_cal = {"component": "StackedCountByGroup", "groupField": "_curso",
                    "categoryField": "_habilidad"}
        _chart_to_png_b64(item_cal, records, indicator=ind)
        niveles_cal = {label for label, _ in barras_espiadas if label}

        assert niveles_cat == {"BAJA", "MEDIA", "ALTA"}
        assert niveles_cal == {"Silábica", "Unidades Cortas", "Fluida"}
        assert niveles_cat != niveles_cal


# ───────────── agregaciones de VALOR restringidas a su métrica ───────────────

@pytest.mark.unit
class TestRolDeCampoDeValor:
    def test_acepta_el_alias_del_rol(self):
        assert rol_de_campo_de_valor(COLUMN_ROLES_DIA, "_logro_1") == "logro_1"

    def test_acepta_el_field_ya_resuelto(self):
        assert rol_de_campo_de_valor(COLUMN_ROLES_DIA, "_logro", "_logro") == "logro_1"

    def test_campo_ajeno_a_todo_rol(self):
        assert rol_de_campo_de_valor(COLUMN_ROLES_DIA, "_promedio") is None


@pytest.mark.unit
class TestRecordsParaCampoDeValor:
    def _records(self):
        return [
            {METRIC_ID_KEY: 6, "_curso": "1 A", "_logro": 60},
            {METRIC_ID_KEY: 7, "_curso": "1 A", "_logro": 0, "_eje_tematico": "Números"},
        ]

    def test_filtra_a_la_metrica_del_rol(self):
        out = records_para_campo_de_valor(self._records(), COLUMN_ROLES_DIA, "_logro_1", "_logro")
        assert [r[METRIC_ID_KEY] for r in out] == [6]

    def test_campo_sin_rol_no_filtra(self):
        recs = self._records()
        assert records_para_campo_de_valor(recs, COLUMN_ROLES_DIA, "_promedio") is recs

    def test_group_field_de_otra_metrica_degrada_a_todos(self):
        """DIA: "Logro Promedio por Eje Temático" cruza `logro_1` (métrica 6)
        con una dimensión que solo existe en la 7 — filtrar dejaría el gráfico
        en blanco, así que se devuelven todos los records."""
        recs = self._records()
        out = records_para_campo_de_valor(
            recs, COLUMN_ROLES_DIA, "_logro_1", "_logro", group_field="_eje_tematico"
        )
        assert out is recs

    def test_group_field_presente_en_la_metrica_fuente_si_filtra(self):
        out = records_para_campo_de_valor(
            self._records(), COLUMN_ROLES_DIA, "_logro_1", "_logro", group_field="_curso"
        )
        assert [r[METRIC_ID_KEY] for r in out] == [6]


@pytest.mark.unit
class TestValoresNoMezclanMetricas:
    """"Logro prom." / mín / máx salen solo de la métrica fuente del campo.

    En DIA `logro_1` está declarado en la métrica 6 ("por estudiante") y en la 7
    ("por Pregunta"), ambas con la columna "Logro": el promedio mezclaba notas
    de alumnos con el logro por pregunta.
    """

    def _records(self):
        # Alumnos (métrica 6) con 60 y 70; preguntas (métrica 7) con 0 y 1.
        # Promedio correcto = 65; mezclado = 32.75.
        records = []
        for i, v in enumerate((60, 70)):
            records.append({
                METRIC_ID_KEY: 6, "_curso": "1 A", "_hito": "CIERRE",
                "_nombre": f"Alumno {i}", "_nivel_logro": "Inicial", "_logro": v,
            })
        for j, v in enumerate((0, 1)):
            records.append({
                METRIC_ID_KEY: 7, "_curso": "1 A", "_hito": "CIERRE",
                "_nivel_logro": "Inicial", "_logro": v,
            })
        return records

    def _indicador(self):
        return _IndicadorFake(
            column_roles=COLUMN_ROLES_DIA,
            achievement_levels=[{"name": n, "order": i} for i, n in enumerate(NIVELES)],
        )

    def test_summary_table_promedio_min_max(self):
        item = {
            "component": "SummaryTable",
            "groupField": "_curso",
            "valueField": ["_logro_1"],
            "periodField": "_hito",
        }
        out = _table_section(item, self._records(), indicator=self._indicador())
        fila = out["rows"][0]
        # [Curso, Alumnos, prom, mín, máx, ...niveles]
        assert fila[2] == "65.0", f"promedio mezclado: {fila[2]}"
        assert fila[3] == "60.0"
        assert fila[4] == "70.0"

    def test_barbygroup_promedia_solo_la_metrica_fuente(self, barras_espiadas):
        from backend.rgenerator.core.report_steps import _chart_to_png_b64

        item = {"component": "BarByGroup", "groupField": "_curso",
                "valueField": "_logro_1"}
        _chart_to_png_b64(item, self._records(), indicator=self._indicador())
        alturas = [v for _, vals in barras_espiadas for v in vals]
        assert alturas == pytest.approx([65.0])


@pytest.mark.unit
class TestTablaPlanaOcultaMetricId:
    """`_metric_id` es clave técnica: no debe salir como columna."""

    def test_columnas_auto_generadas_excluyen_metric_id(self):
        records = [{METRIC_ID_KEY: 6, "_curso": "1 A", "_logro": 0.5}]
        out = _table_section({"component": "FlatTable"}, records)
        assert METRIC_ID_KEY not in out["columns"]
        assert out["columns"] == ["_curso", "_logro"]
        assert out["rows"] == [["1 A", "0.5"]]
