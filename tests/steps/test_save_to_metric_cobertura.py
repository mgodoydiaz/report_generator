"""Guard de cobertura de dimensiones en SaveToMetric.

Si una dimensión ASOCIADA a la métrica queda con 0% de cobertura en las filas
de la corrida, el paso debe avisar (logger.warning + logs del paso +
ctx.warnings) sin bloquear la carga. Nace del bug SIMCE mayo 2026: la carga
guardó 260 filas sin la dimensión `Pregunta` y nadie se enteró hasta que el
informe salió vacío.
"""
from __future__ import annotations

import json
import logging

import pandas as pd
import pytest

from backend.rgenerator.core.context import RunContext
from backend.rgenerator.core.metric_steps import SaveToMetric
from backend.models import Dimension, Metric, MetricData, MetricDimension, Organization


DIMENSIONES = ["Curso", "Pregunta"]


@pytest.fixture
def metrica_preguntas(db_session):
    """Métrica tipo object con dos dimensiones: Curso y Pregunta."""
    org = Organization(name="Org Cobertura", slug="org-cobertura", is_active=True)
    db_session.add(org)
    db_session.commit()

    metric = Metric(
        name="Resultados de prueba por Pregunta",
        data_type="object",
        meta_json=json.dumps({"fields": [{"name": "Logro", "type": "float"}]}),
        org_id=org.id,
    )
    db_session.add(metric)
    db_session.commit()

    dims = {}
    for nombre in DIMENSIONES:
        d = Dimension(name=nombre, data_type="str", org_id=org.id)
        db_session.add(d)
        db_session.commit()
        db_session.add(MetricDimension(id_metric=metric.id_metric, id_dimension=d.id_dimension))
        dims[nombre] = d
    db_session.commit()
    return {"org": org, "metric": metric, "dims": dims}


def _ctx(db_session, org_id, df, key="preguntas"):
    ctx = RunContext(db=db_session, org_id=org_id, user_id=None)
    ctx.artifacts[key] = df
    return ctx


@pytest.mark.integration
def test_avisa_cuando_falta_la_columna_de_una_dimension(metrica_preguntas, db_session, caplog):
    """Falta del todo la columna 'Pregunta' → warning, pero la carga entra."""
    metric = metrica_preguntas["metric"]
    df = pd.DataFrame({"Curso": ["II A", "II A"], "Logro": [0.5, 0.6]})
    ctx = _ctx(db_session, metrica_preguntas["org"].id, df)
    step = SaveToMetric(metric_id=metric.id_metric, input_key="preguntas")

    with caplog.at_level(logging.WARNING):
        step.run(ctx)

    # La carga NO se bloquea.
    guardadas = db_session.query(MetricData).filter(
        MetricData.id_metric == metric.id_metric
    ).all()
    assert len(guardadas) == 2

    # Y el aviso es visible por los tres canales.
    assert any("Pregunta" in r.message and "0% de cobertura" in r.message
               for r in caplog.records if r.levelno >= logging.WARNING)
    assert any("Pregunta" in w and "0% de cobertura" in w for w in ctx.warnings)
    assert any("Pregunta" in msg for msg in step.logs)
    # 'Curso' sí tiene cobertura: la única advertencia es la de 'Pregunta'.
    assert len(ctx.warnings) == 1
    assert not any("Dimensión 'Curso'" in w for w in ctx.warnings)


@pytest.mark.integration
def test_avisa_cuando_la_columna_existe_pero_esta_vacia(metrica_preguntas, db_session, caplog):
    """La columna existe pero es NaN en todas las filas → también avisa."""
    metric = metrica_preguntas["metric"]
    df = pd.DataFrame({
        "Curso": ["II A", "II B"],
        "Pregunta": [None, float("nan")],
        "Logro": [0.5, 0.6],
    })
    ctx = _ctx(db_session, metrica_preguntas["org"].id, df)
    step = SaveToMetric(metric_id=metric.id_metric, input_key="preguntas")

    with caplog.at_level(logging.WARNING):
        step.run(ctx)

    assert len(db_session.query(MetricData).filter(
        MetricData.id_metric == metric.id_metric).all()) == 2
    assert any("Pregunta" in w and "vacía/NaN" in w for w in ctx.warnings)


@pytest.mark.integration
def test_sin_advertencias_cuando_todas_las_dimensiones_tienen_datos(
    metrica_preguntas, db_session, caplog
):
    metric = metrica_preguntas["metric"]
    df = pd.DataFrame({
        "Curso": ["II A", "II A"],
        "Pregunta": [1, 2],
        "Logro": [0.5, 0.6],
    })
    ctx = _ctx(db_session, metrica_preguntas["org"].id, df)
    step = SaveToMetric(metric_id=metric.id_metric, input_key="preguntas")

    with caplog.at_level(logging.WARNING):
        step.run(ctx)

    assert ctx.warnings == []
    guardadas = db_session.query(MetricData).filter(
        MetricData.id_metric == metric.id_metric).all()
    dims = [json.loads(g.dimensions_json) for g in guardadas]
    id_pregunta = str(metrica_preguntas["dims"]["Pregunta"].id_dimension)
    assert sorted(d[id_pregunta] for d in dims) == ["1", "2"]


@pytest.mark.integration
def test_cobertura_parcial_no_dispara_advertencia(metrica_preguntas, db_session):
    """Con al menos una fila poblada no hay aviso: el guard es 0% estricto."""
    metric = metrica_preguntas["metric"]
    df = pd.DataFrame({
        "Curso": ["II A", "II A"],
        "Pregunta": [1, None],
        "Logro": [0.5, 0.6],
    })
    ctx = _ctx(db_session, metrica_preguntas["org"].id, df)
    SaveToMetric(metric_id=metric.id_metric, input_key="preguntas").run(ctx)

    assert ctx.warnings == []
