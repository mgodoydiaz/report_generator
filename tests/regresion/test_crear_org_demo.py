"""Guardias de la organización demo (`scripts/crear_org_demo.py`).

Lo que protegen estos tests:
  * **Determinismo**: la nómina y los datos se generan con `random.seed(42)`;
    dos corridas deben producir exactamente lo mismo.
  * **Aislamiento**: absolutamente todo lo que crea el script cuelga del
    `org_id` de la demo. Una fila con otro `org_id` significaría que el
    sandbox contaminó datos reales.
  * **Branding neutro**: los layouts PDF dejan `left_footer` vacío (el
    runtime cae al nombre de la organización) y no mencionan a nadie por
    nombre. Complementa `test_branding_sin_nombre_personal.py`, que audita
    los esquemas .json.
  * **Casos borde**: el sandbox debe seguir trayendo las filas con
    `Eje Temático` nulo y con `Nombre` nulo + `Nombre_Norm` poblado, que
    son las que reproducen los bugs reales del pipeline DIA.
  * **`--reset` limpio**: `borrar_org` no debe dejar huérfanos.
"""
from __future__ import annotations

import json
import random
import re

import pytest

from scripts.crear_org_demo import (
    CORTE_DIA_INICIAL,
    CORTE_DIA_INTERMEDIO,
    CORTE_SIMCE_ELEMENTAL,
    CORTE_SIMCE_INSUFICIENTE,
    CURSOS_SIMCE,
    NIVELES_DIA,
    NIVELES_SIMCE,
    SEMILLA,
    SLUG_DEMO,
    _nivel_dia,
    _nivel_simce,
    _normalizar,
    borrar_org,
    construir,
    generar_nomina,
)


# ─────────────────────────────────────────────────────────────────────────
# Helpers puros
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_nomina_es_determinista():
    primera = generar_nomina(CURSOS_SIMCE, 1, random.Random(SEMILLA))
    segunda = generar_nomina(CURSOS_SIMCE, 1, random.Random(SEMILLA))
    assert primera == segunda
    assert len(primera) == 30
    assert primera[0]["nombre"] == "Estudiante Demo 01"
    assert primera[0]["rut"] == "DEMO-0001"
    # El offset separa los cursos: el primero en 0, el segundo por encima.
    assert primera[0]["offset"] == 0
    assert primera[-1]["offset"] > 0


@pytest.mark.unit
def test_normalizar_quita_tildes_y_sube_a_mayusculas():
    assert _normalizar("Estudiante Demo 07") == "ESTUDIANTE DEMO 07"
    assert _normalizar("  José  Ñuñez ") == "JOSE NUNEZ"


@pytest.mark.unit
def test_nivel_simce_respeta_los_cortes():
    assert _nivel_simce(CORTE_SIMCE_INSUFICIENTE - 1) == NIVELES_SIMCE[0]
    assert _nivel_simce(CORTE_SIMCE_INSUFICIENTE) == NIVELES_SIMCE[1]
    assert _nivel_simce(CORTE_SIMCE_ELEMENTAL - 1) == NIVELES_SIMCE[1]
    assert _nivel_simce(CORTE_SIMCE_ELEMENTAL) == NIVELES_SIMCE[2]


@pytest.mark.unit
def test_nivel_dia_respeta_los_cortes():
    assert _nivel_dia(CORTE_DIA_INICIAL - 0.01) == NIVELES_DIA[0]
    assert _nivel_dia(CORTE_DIA_INICIAL) == NIVELES_DIA[1]
    assert _nivel_dia(CORTE_DIA_INTERMEDIO - 0.01) == NIVELES_DIA[1]
    assert _nivel_dia(CORTE_DIA_INTERMEDIO) == NIVELES_DIA[2]


# ─────────────────────────────────────────────────────────────────────────
# Construcción completa contra SQLite in-memory
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture
def demo(db_session):
    """Corre `construir` una vez y devuelve (resumen, org_id)."""
    resumen = construir(db_session)
    return resumen, resumen["org"]["id"]


@pytest.mark.integration
def test_construir_deja_todo_bajo_la_org_demo(db_session, demo):
    from backend.models import (
        Dimension, DimensionValue, Indicator, Metric, MetricData, Spec, User,
    )

    resumen, org_id = demo
    assert resumen["org"]["slug"] == SLUG_DEMO

    # Ninguna fila con otro org_id: el sandbox no toca datos ajenos.
    for modelo in (Dimension, Metric, MetricData, Indicator, Spec, User):
        ajenas = db_session.query(modelo).filter(modelo.org_id != org_id).count()
        assert ajenas == 0, f"{modelo.__name__} tiene filas fuera de la org demo"

    assert db_session.query(Dimension).count() == 15
    assert db_session.query(Metric).count() == 4
    assert db_session.query(Indicator).count() == 2
    assert db_session.query(Spec).count() == 24
    assert db_session.query(MetricData).count() == 1850
    assert db_session.query(DimensionValue).count() > 0

    # Los valores de dimensión cuelgan de dimensiones de la org demo.
    ids_dims = {d.id_dimension for d in db_session.query(Dimension).all()}
    for valor in db_session.query(DimensionValue).all():
        assert valor.id_dimension in ids_dims


@pytest.mark.integration
def test_indicadores_listos_para_informe_y_dashboard(db_session, demo):
    from backend.models import Indicator, Spec

    _resumen, org_id = demo
    ids_specs = {
        s.id_spec for s in db_session.query(Spec).filter(Spec.org_id == org_id).all()
    }

    motores = set()
    for ind in db_session.query(Indicator).all():
        motores.add(ind.report_engine_type)

        for campo in ("pdf_layout", "pdf_layout_historico"):
            layout = json.loads(getattr(ind, campo))
            assert layout.get("sections"), f"{ind.name}.{campo} sin secciones"
            # Branding neutro: el pie lo resuelve el runtime con el nombre
            # de la organización, no un valor fijo.
            assert layout["branding"]["left_footer"] == ""
            assert not re.search(r"godoy", json.dumps(layout), re.IGNORECASE)

        # El dashboard solo puede referenciar specs de la propia org.
        dashboard = json.loads(ind.dashboard_layout)
        referenciados = {
            item["spec_id"]
            for tab in dashboard["tabs"]
            for fila in tab["rows"]
            for item in fila["items"]
            if "spec_id" in item
        }
        assert referenciados, f"{ind.name} sin specs en el dashboard"
        assert referenciados <= ids_specs, (
            f"{ind.name} referencia specs de otra organización: "
            f"{sorted(referenciados - ids_specs)}"
        )

    assert motores == {"simce", "dia"}


@pytest.mark.integration
def test_specs_apuntan_a_metricas_de_la_org_demo(db_session, demo):
    from backend.models import Metric, Spec

    _resumen, org_id = demo
    ids_metricas = {
        m.id_metric for m in db_session.query(Metric).filter(Metric.org_id == org_id)
    }
    for spec in db_session.query(Spec).all():
        configs = json.loads(spec.charts_list) + json.loads(spec.tables_list)
        assert configs, f"spec {spec.name} vacío"
        for config in configs:
            assert config["data_source"]["metric_id"] in ids_metricas


@pytest.mark.integration
def test_casos_borde_dia_presentes(db_session, demo):
    """El sandbox debe seguir reproduciendo los nulos del pipeline DIA real."""
    from backend.models import Dimension, Metric, MetricData

    _resumen, org_id = demo
    dims = {d.name: str(d.id_dimension) for d in db_session.query(Dimension).all()}
    metricas = {m.name: m.id_metric for m in db_session.query(Metric).all()}

    id_est = metricas["Resultados DIA Demo por Estudiante"]
    sin_nombre = 0
    for fila in db_session.query(MetricData).filter(MetricData.id_metric == id_est):
        valores = json.loads(fila.dimensions_json)
        if valores.get(dims["Nombre"]) is None:
            sin_nombre += 1
            # Sin Nombre_Norm las derived_columns degradarían a NaN.
            assert valores.get(dims["Nombre_Norm"])
    assert sin_nombre > 0, "faltan las filas DIA con Nombre nulo"

    id_preg = metricas["Resultados DIA Demo por Pregunta"]
    sin_eje = sum(
        1
        for fila in db_session.query(MetricData).filter(MetricData.id_metric == id_preg)
        if json.loads(fila.dimensions_json).get(dims["Eje Temático"]) is None
    )
    assert sin_eje > 0, "faltan las filas DIA con Eje Temático nulo"


@pytest.mark.integration
def test_borrar_org_no_deja_huerfanos(db_session, demo):
    from backend.models import (
        Dimension, DimensionValue, Indicator, IndicatorMetric, Metric,
        MetricData, MetricDimension, Organization, Spec, User,
    )

    _resumen, org_id = demo
    org = db_session.query(Organization).filter(Organization.id == org_id).one()
    borrar_org(db_session, org)

    for modelo in (
        Organization, User, Dimension, DimensionValue, Metric, MetricDimension,
        MetricData, Indicator, IndicatorMetric, Spec,
    ):
        assert db_session.query(modelo).count() == 0, (
            f"{modelo.__name__} quedó con filas después de borrar la org demo"
        )
