"""Tests del tipo de dato "fecha" de una dimensión, extremo a extremo.

Cubre:
  - el router de dimensiones (GET/POST/PUT) exponiendo y normalizando
    `data_type`, incluido el alias en español;
  - `report-options` de un indicador SIN dimensión Año pero CON una
    dimensión de tipo fecha: las cards semestral y anual pasan a estar
    disponibles (el caso Fluidez Lectora);
  - el campo aditivo `data_type` en `dimensiones_filtrables`.
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from tests.factories import make_dimension, make_indicator, make_metric, make_metric_data

LAYOUT_EVAL = json.dumps({"sections": [{"type": "kpi"}]})
LAYOUT_HIST = json.dumps({"sections": [{"type": "line"}]})


# ─────────────────────────────────────────────────────────────────────────
# Router de dimensiones
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestRouterDataType:
    def test_crear_dimension_fecha(self, client_auth):
        r = client_auth.post("/api/dimensions/", json={
            "name": "Fecha", "data_type": "date", "validation_mode": "free",
        })
        assert r.status_code == 200
        assert r.json()["data"]["data_type"] == "date"

    def test_el_alias_en_espanol_se_normaliza(self, client_auth):
        r = client_auth.post("/api/dimensions/", json={
            "name": "Toma", "data_type": "fecha", "validation_mode": "free",
        })
        assert r.status_code == 200
        assert r.json()["data"]["data_type"] == "date"

    @pytest.mark.parametrize("entrada,esperado", [
        ("texto", "str"), ("numero", "int"), ("número", "int"),
        ("str", "str"), ("int", "int"), ("float", "float"),
    ])
    def test_alias_de_los_tipos_clasicos(self, client_auth, entrada, esperado):
        r = client_auth.post("/api/dimensions/", json={
            "name": f"Dim {entrada}", "data_type": entrada,
        })
        assert r.json()["data"]["data_type"] == esperado

    def test_default_retrocompatible(self, client_auth):
        """Sin `data_type` la dimensión queda como texto."""
        r = client_auth.post("/api/dimensions/", json={"name": "Curso"})
        assert r.json()["data"]["data_type"] == "str"

    def test_listar_expone_data_type(self, client_auth, db_session, org):
        make_dimension(db_session, org, name="Fecha", data_type="date")
        r = client_auth.get("/api/dimensions/")
        assert r.status_code == 200
        tipos = {d["name"]: d["data_type"] for d in r.json()}
        assert tipos["Fecha"] == "date"

    def test_listar_normaliza_los_nulos_historicos(self, client_auth, db_session, org):
        """Filas viejas con `data_type` NULL se reportan como texto."""
        dim = make_dimension(db_session, org, name="Antigua")
        dim.data_type = None
        db_session.commit()
        r = client_auth.get("/api/dimensions/")
        tipos = {d["name"]: d["data_type"] for d in r.json()}
        assert tipos["Antigua"] == "str"

    def test_editar_cambia_el_tipo(self, client_auth, db_session, org):
        dim = make_dimension(db_session, org, name="Fecha", data_type="str")
        r = client_auth.put(f"/api/dimensions/{dim.id_dimension}", json={
            "name": "Fecha", "data_type": "fecha", "validation_mode": "free",
        })
        assert r.status_code == 200
        assert r.json()["data"]["data_type"] == "date"

    def test_no_se_puede_editar_una_dimension_de_otra_org(self, client_auth, db_session):
        from tests.factories import make_org
        otra = make_org(db_session, name="Otra", slug="otra")
        ajena = make_dimension(db_session, otra, name="Fecha")
        r = client_auth.put(f"/api/dimensions/{ajena.id_dimension}", json={
            "name": "Fecha", "data_type": "date",
        })
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────
# report-options con una dimensión fecha (caso Fluidez Lectora)
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture
def indicador_fluidez(db_session, org):
    """Indicador SIN dimensión Año: el tiempo vive en "Fecha".

    Dos aplicaciones del año en curso (una en cada semestre) y una del año
    anterior, para que semestral y anual no den el mismo recorte.
    """
    hoy = date.today()
    dims = {n: make_dimension(db_session, org, name=n,
                              data_type="date" if n == "Fecha" else "str")
            for n in ("Curso", "Fecha")}
    metric = make_metric(
        db_session, org,
        name="Fluidez Lectora por Estudiante",
        data_type="object",
        fields=[{"name": "PPM", "type": "float"}],
        dimensions=list(dims.values()),
    )
    fechas = [
        date(hoy.year, 3, 15),          # 1er semestre del año en curso
        date(hoy.year, 9, 15),          # 2º semestre del año en curso
        date(hoy.year - 1, 5, 20),      # año anterior
    ]
    for f in fechas:
        make_metric_data(
            db_session, metric,
            value={"PPM": 120},
            dimensions_json={
                str(dims["Curso"].id_dimension): "I A",
                str(dims["Fecha"].id_dimension): f"{f.isoformat()} 00:00:00",
            },
        )
    ind = make_indicator(
        db_session, org, name="Fluidez Lectora", metrics=[metric],
        pdf_layout=LAYOUT_EVAL, pdf_layout_historico=LAYOUT_HIST,
    )
    return ind, dims


@pytest.mark.integration
class TestReportOptionsConFecha:
    def _cards(self, body):
        return {o["id"]: o for o in body["grupos"]["periodo"]}

    def test_semestral_y_anual_quedan_disponibles(self, client_auth, indicador_fluidez):
        ind, _ = indicador_fluidez
        r = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options")
        assert r.status_code == 200
        cards = self._cards(r.json())
        assert cards["periodo_anual"]["disponible"] is True
        assert cards["periodo_semestral"]["disponible"] is True
        assert cards["periodo_ultima_prueba"]["disponible"] is True

    def test_la_descripcion_del_anual_es_el_anio_en_curso(self, client_auth, indicador_fluidez):
        ind, _ = indicador_fluidez
        r = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options")
        card = self._cards(r.json())["periodo_anual"]
        assert str(date.today().year) in card["descripcion"]

    def test_la_ultima_prueba_muestra_la_fecha_legible(self, client_auth, indicador_fluidez):
        ind, _ = indicador_fluidez
        r = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options")
        card = self._cards(r.json())["periodo_ultima_prueba"]
        # dd-mm-yyyy, sin la hora
        assert "00:00:00" not in card["descripcion"]
        assert f"15-09-{date.today().year}" in card["descripcion"]

    def test_dimensiones_filtrables_traen_el_data_type(self, client_auth, indicador_fluidez):
        ind, _ = indicador_fluidez
        r = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options")
        dims = {d["name"]: d for d in r.json()["dimensiones_filtrables"]}
        assert dims["Fecha"]["data_type"] == "date"
        assert dims["Curso"]["data_type"] == "str"

    def test_export_pdf_anual_resuelve_el_periodo(self, client_auth, indicador_fluidez):
        """El período anual se traduce a filtros por id de dimensión."""
        from backend.routers.indicators import _resolver_periodo_a_filtros
        from backend.models import Indicator
        ind, dims = indicador_fluidez
        # Se llama al helper directo: renderizar el PDF requiere WeasyPrint.
        import backend.database as _db  # noqa: F401 — asegura los modelos cargados
        from sqlalchemy.orm import object_session
        db = object_session(ind)
        tipo_layout, filtros, descripcion = _resolver_periodo_a_filtros(
            db, ind, ind.org_id, {"tipo": "anual"}
        )
        assert tipo_layout == "historico"
        assert descripcion == str(date.today().year)
        clave = str(dims["Fecha"].id_dimension)
        assert clave in filtros
        assert len(filtros[clave]) == 2   # las dos fechas del año en curso


# ─────────────────────────────────────────────────────────────────────────
# No regresión: indicador con dimensión Año explícita
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestNoRegresionIndicadorConAnio:
    def test_las_dimensiones_siguen_saliendo_con_su_tipo(self, client_auth, db_session, org):
        hoy = date.today()
        dims = {n: make_dimension(db_session, org, name=n,
                                  data_type="int" if n == "Año" else "str")
                for n in ("Curso", "Año", "Mes")}
        metric = make_metric(
            db_session, org, name="Resultados por Estudiante",
            data_type="object", fields=[{"name": "Logro", "type": "float"}],
            dimensions=list(dims.values()),
        )
        from backend.rgenerator.reports.periodos import NUMERO_A_MES
        make_metric_data(
            db_session, metric, value={"Logro": 0.5},
            dimensions_json={
                str(dims["Curso"].id_dimension): "II A",
                str(dims["Año"].id_dimension): str(hoy.year),
                str(dims["Mes"].id_dimension): NUMERO_A_MES[hoy.month],
            },
        )
        ind = make_indicator(db_session, org, name="SIMCE", metrics=[metric],
                             pdf_layout=LAYOUT_EVAL, pdf_layout_historico=LAYOUT_HIST)
        r = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options")
        assert r.status_code == 200
        body = r.json()
        dims_resp = {d["name"]: d for d in body["dimensiones_filtrables"]}
        assert dims_resp["Año"]["data_type"] == "int"
        cards = {o["id"]: o for o in body["grupos"]["periodo"]}
        assert cards["periodo_anual"]["disponible"] is True
        assert cards["periodo_anual"]["descripcion"].endswith(f"{hoy.year}.")
