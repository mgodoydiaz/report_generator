"""Tests de `scripts/marcar_dimensiones_fecha.py`.

El script marca con `data_type='date'` las dimensiones cuyos valores son
fechas reales. Es lo que habilita los informes semestral y anual en
indicadores sin dimensión "Año" (caso Fluidez Lectora).

Reglas que se verifican:
  - dry-run por defecto (no escribe);
  - `--apply` escribe;
  - alcance por organización (nunca toca otra org);
  - una dimensión llamada "Fecha" con basura adentro NO se marca;
  - una dimensión con otro nombre pero puras fechas SÍ se marca.
"""
from __future__ import annotations

import pytest

from tests.factories import (
    make_dimension, make_metric, make_metric_data, make_org,
)

pytestmark = pytest.mark.integration


def _metrica_con_dimension(db, org, dim, valores, nombre_metrica="Métrica"):
    """Métrica con `dim` y una fila de `metric_data` por cada valor."""
    metric = make_metric(db, org, name=nombre_metrica, data_type="float",
                         dimensions=[dim])
    for v in valores:
        make_metric_data(db, metric, value=1.0,
                         dimensions_json={str(dim.id_dimension): v})
    return metric


@pytest.fixture
def dim_fecha(db_session, org):
    dim = make_dimension(db_session, org, name="Fecha", data_type="str")
    _metrica_con_dimension(db_session, org, dim, [
        "2026-04-02 00:00:00", "2026-04-09 00:00:00", "2025-10-23 00:00:00",
    ])
    return dim


class TestDeteccion:
    def test_detecta_la_dimension_fecha(self, db_session, org, dim_fecha):
        from scripts.marcar_dimensiones_fecha import analizar
        props = analizar(db_session, org.id)
        assert [p["name"] for p in props] == ["Fecha"]
        assert props[0]["ya_marcada"] is False

    def test_no_detecta_dimensiones_de_texto(self, db_session, org):
        from scripts.marcar_dimensiones_fecha import analizar
        dim = make_dimension(db_session, org, name="Curso")
        _metrica_con_dimension(db_session, org, dim, ["I A", "I B", "II C"])
        assert analizar(db_session, org.id) == []

    def test_una_columna_fecha_con_basura_no_se_marca(self, db_session, org):
        from scripts.marcar_dimensiones_fecha import analizar
        dim = make_dimension(db_session, org, name="Fecha")
        _metrica_con_dimension(db_session, org, dim, ["s/i", "pendiente", "no aplica"])
        assert analizar(db_session, org.id) == []

    def test_nombre_neutro_con_puras_fechas_si_se_marca(self, db_session, org):
        from scripts.marcar_dimensiones_fecha import analizar
        dim = make_dimension(db_session, org, name="Toma")
        _metrica_con_dimension(db_session, org, dim,
                               ["07-04-2026", "13-04-2026", "02-05-2026"])
        props = analizar(db_session, org.id)
        assert [p["name"] for p in props] == ["Toma"]

    def test_el_umbral_es_configurable(self, db_session, org):
        from scripts.marcar_dimensiones_fecha import analizar
        dim = make_dimension(db_session, org, name="Aplicación")
        # 3 de 4 parsean = 75%
        _metrica_con_dimension(db_session, org, dim,
                               ["2026-04-07", "2026-04-08", "2026-04-09", "s/i"])
        assert analizar(db_session, org.id) == []                 # umbral 0.9
        assert len(analizar(db_session, org.id, umbral=0.7)) == 1

    def test_usa_el_catalogo_cuando_no_hay_datos_cargados(self, db_session, org):
        from backend.models import DimensionValue
        from scripts.marcar_dimensiones_fecha import analizar
        dim = make_dimension(db_session, org, name="Fecha")
        for v in ("2026-03-01", "2026-06-01"):
            db_session.add(DimensionValue(id_dimension=dim.id_dimension, value=v))
        db_session.commit()
        assert [p["name"] for p in analizar(db_session, org.id)] == ["Fecha"]


class TestMarcado:
    def test_dry_run_no_escribe(self, db_session, org, dim_fecha):
        from scripts.marcar_dimensiones_fecha import marcar
        resumen = marcar(db_session, org.id, aplicar=False)
        assert resumen["marcadas"] == 1
        db_session.refresh(dim_fecha)
        assert dim_fecha.data_type == "str"

    def test_apply_escribe(self, db_session, org, dim_fecha):
        from scripts.marcar_dimensiones_fecha import marcar
        resumen = marcar(db_session, org.id, aplicar=True)
        assert resumen["marcadas"] == 1
        db_session.refresh(dim_fecha)
        assert dim_fecha.data_type == "date"

    def test_es_idempotente(self, db_session, org, dim_fecha):
        from scripts.marcar_dimensiones_fecha import marcar
        marcar(db_session, org.id, aplicar=True)
        segunda = marcar(db_session, org.id, aplicar=True)
        assert segunda["marcadas"] == 0
        assert segunda["propuestas"][0]["ya_marcada"] is True

    def test_no_toca_otras_organizaciones(self, db_session, org, dim_fecha):
        from scripts.marcar_dimensiones_fecha import marcar
        otra = make_org(db_session, name="Otra", slug="otra-org")
        dim_ajena = make_dimension(db_session, otra, name="Fecha", data_type="str")
        _metrica_con_dimension(db_session, otra, dim_ajena,
                               ["2026-04-02 00:00:00"], nombre_metrica="Ajena")

        marcar(db_session, org.id, aplicar=True)

        db_session.refresh(dim_fecha)
        db_session.refresh(dim_ajena)
        assert dim_fecha.data_type == "date"
        assert dim_ajena.data_type == "str"
