"""Tests del router /api/charts — Sprint 2 (cobertura 15% → 70%).

Cubre los 9 endpoints (CRUD + types + duplicate + data + preview) con el
patrón estándar: success, 401 sin auth, 404, multi-tenancy (otra org),
validation 422, edge cases (df vacío, config malformada).

Foco especial en el endpoint `/{id}/data` y `_build_dataset` — el módulo
donde explotó la traza del incidente 2026-05-19. Tests por chart_type
(bar, line, pie, stacked_bar, grouped_bar, histogram, gauge) suben la
cobertura de los branches del switch interno.
"""
from __future__ import annotations

import json

import pytest

from tests.factories import (
    make_dimension,
    make_metric,
    make_metric_data,
    make_org,
    make_user,
)


# ─────────────────────────────────────────────────────────────────────────
# Fixtures locales
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def chart_config_minimal():
    """Config válida mínima para crear un chart de tipo bar."""
    return {
        "chart_type": "bar",
        "data_source": {"metric_id": 1, "filters": {}},
        "mapping": {"x_field": "Curso", "y_field": "Logro", "aggregation": "mean"},
        "aesthetics": {},
    }


@pytest.fixture
def metric_con_datos(db_session, org):
    """Metric 'Logro' (float) con dimensión 'Curso' y 4 filas de data.

    Esquema resultante del DataFrame (lo que verá _build_dataset):

        Curso     Logro
        ----------------
        1° Básico 0.80
        1° Básico 0.60
        2° Básico 0.70
        2° Básico 0.50
    """
    dim_curso = make_dimension(db_session, org, name="Curso")
    metric = make_metric(
        db_session, org, name="Logro", data_type="float",
        dimensions=[dim_curso],
    )
    for curso, val in [
        ("1° Básico", "0.80"),
        ("1° Básico", "0.60"),
        ("2° Básico", "0.70"),
        ("2° Básico", "0.50"),
    ]:
        make_metric_data(
            db_session, metric,
            value=val,
            dimensions_json={str(dim_curso.id_dimension): curso},
        )
    return metric


@pytest.fixture
def chart_creado(db_session, org, metric_con_datos):
    """Crea un Spec tipo Gráficos directamente vía ORM (más rápido que API)
    apuntando a `metric_con_datos`. Devuelve el id_spec."""
    from backend.models import Spec
    cfg = {
        "version": 1,
        "chart_type": "bar",
        "data_source": {"metric_id": metric_con_datos.id_metric, "filters": {},
                        "derived_fields_override": []},
        "mapping": {"x_field": "Curso", "y_field": "Logro", "aggregation": "mean"},
        "aesthetics": {},
    }
    meta = {"description": "test", "is_draft": True, "updated_at": "2026-01-01"}
    spec = Spec(
        name="Chart de Prueba",
        type="Gráficos",
        metadata_=json.dumps(meta),
        charts_list=json.dumps([cfg]),
        tables_list="[]",
        org_id=org.id,
    )
    db_session.add(spec)
    db_session.commit()
    db_session.refresh(spec)
    return spec


@pytest.fixture
def otro_org_con_chart(db_session):
    """Crea otra org + chart en ella — para tests de multi-tenancy."""
    from backend.models import Spec
    other = make_org(db_session, name="Otra Org")
    cfg = {
        "version": 1,
        "chart_type": "bar",
        "data_source": {"metric_id": 999, "filters": {}, "derived_fields_override": []},
        "mapping": {"x_field": "X", "y_field": "Y"},
        "aesthetics": {},
    }
    spec = Spec(
        name="Chart de Otra Org",
        type="Gráficos",
        metadata_=json.dumps({"description": "", "is_draft": True}),
        charts_list=json.dumps([cfg]),
        tables_list="[]",
        org_id=other.id,
    )
    db_session.add(spec)
    db_session.commit()
    db_session.refresh(spec)
    return other, spec


# ─────────────────────────────────────────────────────────────────────────
# GET /api/charts/types
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetChartTypes:
    def test_sin_auth_401(self, client):
        r = client.get("/api/charts/types")
        assert r.status_code == 401

    def test_lista_metadata_chart_types(self, client_auth):
        r = client_auth.get("/api/charts/types")
        assert r.status_code == 200
        data = r.json()
        # Esperamos al menos los tipos del v1
        for expected in ("bar", "line", "pie", "histogram", "gauge"):
            assert expected in data, f"chart_type '{expected}' falta en metadata"
        # Estructura mínima de cada tipo
        bar = data["bar"]
        assert "display_name" in bar
        assert "required_fields" in bar


# ─────────────────────────────────────────────────────────────────────────
# GET /api/charts/  +  POST /api/charts/
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestListCharts:
    def test_sin_auth_401(self, client):
        r = client.get("/api/charts/")
        assert r.status_code == 401

    def test_lista_vacia(self, client_auth):
        r = client_auth.get("/api/charts/")
        assert r.status_code == 200
        assert r.json() == []

    def test_lista_devuelve_charts_de_mi_org(self, client_auth, chart_creado):
        r = client_auth.get("/api/charts/")
        assert r.status_code == 200
        names = [c["name"] for c in r.json()]
        assert "Chart de Prueba" in names

    def test_lista_no_devuelve_charts_de_otra_org(self, client_auth, chart_creado, otro_org_con_chart):
        """Multi-tenancy: el usuario solo ve charts de SU org."""
        r = client_auth.get("/api/charts/")
        assert r.status_code == 200
        names = [c["name"] for c in r.json()]
        assert "Chart de Otra Org" not in names
        assert "Chart de Prueba" in names


@pytest.mark.integration
class TestCreateChart:
    def test_sin_auth_401(self, client, chart_config_minimal):
        r = client.post("/api/charts/", json={
            "name": "x", "config": chart_config_minimal,
        })
        assert r.status_code == 401

    def test_crear_chart_basico(self, client_auth, metric_con_datos, chart_config_minimal):
        chart_config_minimal["data_source"]["metric_id"] = metric_con_datos.id_metric
        r = client_auth.post("/api/charts/", json={
            "name": "Mi Chart", "description": "desc test",
            "config": chart_config_minimal,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "success"
        assert "id_spec" in body

    def test_crear_validacion_pydantic_422_si_falta_chart_type(self, client_auth, chart_config_minimal):
        """Sin chart_type → Pydantic 422."""
        del chart_config_minimal["chart_type"]
        r = client_auth.post("/api/charts/", json={
            "name": "X", "config": chart_config_minimal,
        })
        assert r.status_code == 422

    def test_crear_validacion_422_si_chart_type_no_soportado(self, client_auth, chart_config_minimal):
        chart_config_minimal["chart_type"] = "ufo_plot"
        r = client_auth.post("/api/charts/", json={
            "name": "X", "config": chart_config_minimal,
        })
        assert r.status_code == 422

    def test_crear_422_si_falta_metric_id_en_data_source(self, client_auth, chart_config_minimal):
        chart_config_minimal["data_source"] = {"filters": {}}
        r = client_auth.post("/api/charts/", json={
            "name": "X", "config": chart_config_minimal,
        })
        assert r.status_code == 422

    def test_chart_creado_persiste_org_id_del_user(self, client_auth, db_session, org, metric_con_datos, chart_config_minimal):
        """Lo que se crea debe quedar en la org del user autenticado."""
        from backend.models import Spec
        chart_config_minimal["data_source"]["metric_id"] = metric_con_datos.id_metric
        r = client_auth.post("/api/charts/", json={"name": "X", "config": chart_config_minimal})
        sid = r.json()["id_spec"]
        spec = db_session.query(Spec).get(sid)
        assert spec.org_id == org.id


# ─────────────────────────────────────────────────────────────────────────
# GET /api/charts/{id}
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetChart:
    def test_sin_auth_401(self, client, chart_creado):
        r = client.get(f"/api/charts/{chart_creado.id_spec}")
        assert r.status_code == 401

    def test_get_exitoso(self, client_auth, chart_creado):
        r = client_auth.get(f"/api/charts/{chart_creado.id_spec}")
        assert r.status_code == 200
        body = r.json()
        assert body["id_spec"] == chart_creado.id_spec
        assert body["name"] == "Chart de Prueba"
        assert body["config"]["chart_type"] == "bar"

    def test_404_si_no_existe(self, client_auth):
        r = client_auth.get("/api/charts/99999")
        assert r.status_code == 404

    def test_404_si_es_de_otra_org(self, client_auth, otro_org_con_chart):
        """Multi-tenancy: NO 403 leak — devuelve 404 para no revelar existencia."""
        _, other_spec = otro_org_con_chart
        r = client_auth.get(f"/api/charts/{other_spec.id_spec}")
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────
# PUT /api/charts/{id}
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestUpdateChart:
    def test_sin_auth_401(self, client, chart_creado):
        r = client.put(f"/api/charts/{chart_creado.id_spec}", json={"name": "X"})
        assert r.status_code == 401

    def test_404_si_no_existe(self, client_auth):
        r = client_auth.put("/api/charts/99999", json={"name": "X"})
        assert r.status_code == 404

    def test_404_si_es_de_otra_org(self, client_auth, otro_org_con_chart):
        _, other_spec = otro_org_con_chart
        r = client_auth.put(f"/api/charts/{other_spec.id_spec}", json={"name": "Hack"})
        assert r.status_code == 404

    def test_update_name_solamente(self, client_auth, chart_creado):
        r = client_auth.put(f"/api/charts/{chart_creado.id_spec}", json={"name": "Renombrado"})
        assert r.status_code == 200
        # Verificar persistencia
        g = client_auth.get(f"/api/charts/{chart_creado.id_spec}").json()
        assert g["name"] == "Renombrado"

    def test_update_description_solamente(self, client_auth, chart_creado):
        r = client_auth.put(f"/api/charts/{chart_creado.id_spec}", json={"description": "nueva desc"})
        assert r.status_code == 200
        g = client_auth.get(f"/api/charts/{chart_creado.id_spec}").json()
        assert g["description"] == "nueva desc"

    def test_update_config_completo(self, client_auth, chart_creado, metric_con_datos):
        new_cfg = {
            "version": 1,
            "chart_type": "pie",
            "data_source": {"metric_id": metric_con_datos.id_metric, "filters": {},
                            "derived_fields_override": []},
            "mapping": {"category_field": "Curso"},
            "aesthetics": {},
        }
        r = client_auth.put(f"/api/charts/{chart_creado.id_spec}",
                            json={"config": new_cfg})
        assert r.status_code == 200
        g = client_auth.get(f"/api/charts/{chart_creado.id_spec}").json()
        assert g["config"]["chart_type"] == "pie"

    def test_update_is_draft(self, client_auth, chart_creado):
        r = client_auth.put(f"/api/charts/{chart_creado.id_spec}", json={"is_draft": False})
        assert r.status_code == 200
        g = client_auth.get(f"/api/charts/{chart_creado.id_spec}").json()
        assert g["is_draft"] is False


# ─────────────────────────────────────────────────────────────────────────
# DELETE /api/charts/{id}
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestDeleteChart:
    def test_sin_auth_401(self, client, chart_creado):
        r = client.delete(f"/api/charts/{chart_creado.id_spec}")
        assert r.status_code == 401

    def test_delete_chart_inexistente_404(self, client_auth):
        r = client_auth.delete("/api/charts/99999")
        assert r.status_code == 404

    def test_delete_otro_org_404(self, client_auth, otro_org_con_chart):
        _, other_spec = otro_org_con_chart
        r = client_auth.delete(f"/api/charts/{other_spec.id_spec}")
        assert r.status_code == 404

    def test_delete_exitoso(self, client_auth, chart_creado):
        sid = chart_creado.id_spec
        r = client_auth.delete(f"/api/charts/{sid}")
        assert r.status_code == 200
        # Y ahora 404 al consultarlo
        assert client_auth.get(f"/api/charts/{sid}").status_code == 404


# ─────────────────────────────────────────────────────────────────────────
# POST /api/charts/{id}/duplicate
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestDuplicateChart:
    def test_sin_auth_401(self, client, chart_creado):
        r = client.post(f"/api/charts/{chart_creado.id_spec}/duplicate")
        assert r.status_code == 401

    def test_duplicate_404_si_no_existe(self, client_auth):
        r = client_auth.post("/api/charts/99999/duplicate")
        assert r.status_code == 404

    def test_duplicate_exitoso_crea_copia_con_sufijo(self, client_auth, chart_creado):
        r = client_auth.post(f"/api/charts/{chart_creado.id_spec}/duplicate")
        assert r.status_code == 200
        new_id = r.json()["id_spec"]
        assert new_id != chart_creado.id_spec
        copia = client_auth.get(f"/api/charts/{new_id}").json()
        assert copia["name"] == "Chart de Prueba (Copia)"
        # Misma config que el original
        assert copia["config"]["chart_type"] == "bar"


# ─────────────────────────────────────────────────────────────────────────
# GET /api/charts/{id}/data
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetChartData:
    def test_sin_auth_401(self, client, chart_creado):
        r = client.get(f"/api/charts/{chart_creado.id_spec}/data")
        assert r.status_code == 401

    def test_404_si_no_existe(self, client_auth):
        r = client_auth.get("/api/charts/99999/data")
        assert r.status_code == 404

    def test_404_si_es_de_otra_org(self, client_auth, otro_org_con_chart):
        _, other_spec = otro_org_con_chart
        r = client_auth.get(f"/api/charts/{other_spec.id_spec}/data")
        assert r.status_code == 404

    def test_data_bar_success(self, client_auth, chart_creado):
        """Bar chart: dataset = {x: [...], y: [...]} con mean por X."""
        r = client_auth.get(f"/api/charts/{chart_creado.id_spec}/data")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["chart_type"] == "bar"
        assert body["n_rows"] == 4
        ds = body["dataset"]
        assert "x" in ds and "y" in ds
        # Mean de Logro por Curso: 1° = 0.7, 2° = 0.6
        x_y = dict(zip(ds["x"], ds["y"]))
        assert x_y["1° Básico"] == pytest.approx(0.7)
        assert x_y["2° Básico"] == pytest.approx(0.6)

    def test_data_extra_filters_aplica(self, client_auth, chart_creado):
        """extra_filters como query string JSON debe filtrar el df."""
        filt = json.dumps({"Curso": "1° Básico"})
        r = client_auth.get(f"/api/charts/{chart_creado.id_spec}/data",
                            params={"extra_filters": filt})
        assert r.status_code == 200
        assert r.json()["n_rows"] == 2

    def test_data_extra_filters_invalido_se_ignora(self, client_auth, chart_creado):
        """Si extra_filters es JSON malformado, NO devuelve 400 — los ignora."""
        r = client_auth.get(f"/api/charts/{chart_creado.id_spec}/data",
                            params={"extra_filters": "{not-json"})
        assert r.status_code == 200
        assert r.json()["n_rows"] == 4

    def test_data_400_si_charts_list_vacia(self, client_auth, db_session, org):
        """Si el Spec tiene charts_list=[], el endpoint devuelve 400."""
        from backend.models import Spec
        spec = Spec(
            name="Empty", type="Gráficos",
            metadata_=json.dumps({}), charts_list="[]", tables_list="[]",
            org_id=org.id,
        )
        db_session.add(spec)
        db_session.commit()
        db_session.refresh(spec)
        r = client_auth.get(f"/api/charts/{spec.id_spec}/data")
        assert r.status_code == 400


@pytest.mark.integration
class TestGetChartDataPorTipo:
    """Subir cobertura de _build_dataset corriendo /data por chart_type.

    Cada tipo entra a una rama distinta del switch interno. Cubrimos los
    más comunes; los esotéricos (radar, pivot_matrix, gauge) quedan para
    sprints futuros si no aparecen en datos reales.
    """

    def _crear_chart(self, db_session, org, metric_id, chart_type, mapping):
        from backend.models import Spec
        cfg = {
            "version": 1, "chart_type": chart_type,
            "data_source": {"metric_id": metric_id, "filters": {},
                            "derived_fields_override": []},
            "mapping": mapping, "aesthetics": {},
        }
        spec = Spec(
            name=f"chart-{chart_type}", type="Gráficos",
            metadata_=json.dumps({}),
            charts_list=json.dumps([cfg]),
            tables_list="[]",
            org_id=org.id,
        )
        db_session.add(spec)
        db_session.commit()
        db_session.refresh(spec)
        return spec.id_spec

    def test_line(self, client_auth, db_session, org, metric_con_datos):
        sid = self._crear_chart(db_session, org, metric_con_datos.id_metric,
                                "line", {"x_field": "Curso", "y_field": "Logro"})
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text
        ds = r.json()["dataset"]
        assert "x" in ds and "y" in ds

    def test_pie(self, client_auth, db_session, org, metric_con_datos):
        sid = self._crear_chart(db_session, org, metric_con_datos.id_metric,
                                "pie", {"category_field": "Curso"})
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text
        ds = r.json()["dataset"]
        assert "labels" in ds and "values" in ds

    def test_histogram(self, client_auth, db_session, org, metric_con_datos):
        sid = self._crear_chart(db_session, org, metric_con_datos.id_metric,
                                "histogram", {"y_field": "Logro"})
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text
        ds = r.json()["dataset"]
        assert "values" in ds

    def test_box(self, client_auth, db_session, org, metric_con_datos):
        sid = self._crear_chart(db_session, org, metric_con_datos.id_metric,
                                "box", {"x_field": "Curso", "y_field": "Logro"})
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text

    def test_gauge(self, client_auth, db_session, org, metric_con_datos):
        sid = self._crear_chart(db_session, org, metric_con_datos.id_metric,
                                "gauge", {"y_field": "Logro"})
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text


# ─────────────────────────────────────────────────────────────────────────
# /data con métrica multi-dimensión — para chart_types más complejos
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def metric_multi_dim(db_session, org):
    """Metric con 3 dimensiones (Curso × Asignatura × Nivel) — habilita
    chart_types que requieren x_field + group_field + stack_field."""
    dim_curso = make_dimension(db_session, org, name="Curso")
    dim_asig = make_dimension(db_session, org, name="Asignatura")
    dim_nivel = make_dimension(db_session, org, name="Nivel")
    metric = make_metric(
        db_session, org, name="Logro", data_type="float",
        dimensions=[dim_curso, dim_asig, dim_nivel],
    )
    # 6 filas: 2 cursos × 2 asig × 1-2 niveles
    rows = [
        ("1° Básico", "Lenguaje", "Adecuado", "0.85"),
        ("1° Básico", "Lenguaje", "Elemental", "0.55"),
        ("1° Básico", "Matemática", "Adecuado", "0.80"),
        ("1° Básico", "Matemática", "Elemental", "0.50"),
        ("2° Básico", "Lenguaje", "Adecuado", "0.75"),
        ("2° Básico", "Matemática", "Elemental", "0.60"),
    ]
    for curso, asig, nivel, val in rows:
        make_metric_data(
            db_session, metric, value=val,
            dimensions_json={
                str(dim_curso.id_dimension): curso,
                str(dim_asig.id_dimension): asig,
                str(dim_nivel.id_dimension): nivel,
            },
        )
    return metric


def _spec_chart(db_session, org, metric_id, chart_type, mapping, aesthetics=None):
    """Helper genérico — crea un Spec con un chart inline."""
    from backend.models import Spec
    cfg = {
        "version": 1, "chart_type": chart_type,
        "data_source": {"metric_id": metric_id, "filters": {},
                        "derived_fields_override": []},
        "mapping": mapping,
        "aesthetics": aesthetics or {},
    }
    spec = Spec(
        name=f"chart-{chart_type}", type="Gráficos",
        metadata_=json.dumps({}),
        charts_list=json.dumps([cfg]),
        tables_list="[]",
        org_id=org.id,
    )
    db_session.add(spec)
    db_session.commit()
    db_session.refresh(spec)
    return spec.id_spec


@pytest.mark.integration
class TestGetChartDataTiposComplejos:
    """chart_types que requieren group_field, stack_field o axis_field."""

    def test_grouped_bar(self, client_auth, db_session, org, metric_multi_dim):
        sid = _spec_chart(db_session, org, metric_multi_dim.id_metric, "grouped_bar", {
            "x_field": "Curso", "y_field": "Logro", "group_field": "Asignatura",
        })
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text
        ds = r.json()["dataset"]
        assert "x" in ds and "series" in ds
        # Una serie por asignatura
        names = [s["name"] for s in ds["series"]]
        assert "Lenguaje" in names and "Matemática" in names

    def test_stacked_bar(self, client_auth, db_session, org, metric_multi_dim):
        sid = _spec_chart(db_session, org, metric_multi_dim.id_metric, "stacked_bar", {
            "x_field": "Curso", "stack_field": "Nivel",
        })
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text
        ds = r.json()["dataset"]
        assert "x" in ds and "stacks" in ds

    def test_stacked_grouped_bar(self, client_auth, db_session, org, metric_multi_dim):
        sid = _spec_chart(db_session, org, metric_multi_dim.id_metric, "stacked_grouped_bar", {
            "x_field": "Asignatura", "group_field": "Curso", "stack_field": "Nivel",
        })
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text
        ds = r.json()["dataset"]
        assert "x_outer" in ds and "x_inner" in ds and "stacks" in ds

    def test_heatmap(self, client_auth, db_session, org, metric_multi_dim):
        sid = _spec_chart(db_session, org, metric_multi_dim.id_metric, "heatmap", {
            "x_field": "Curso", "group_field": "Asignatura", "y_field": "Logro",
        })
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text
        ds = r.json()["dataset"]
        assert "x" in ds and "y" in ds and "z" in ds

    def test_radar_sin_group(self, client_auth, db_session, org, metric_multi_dim):
        sid = _spec_chart(db_session, org, metric_multi_dim.id_metric, "radar", {
            "axis_field": "Asignatura", "y_field": "Logro",
        })
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text
        ds = r.json()["dataset"]
        assert "axes" in ds and "series" in ds

    def test_radar_con_group(self, client_auth, db_session, org, metric_multi_dim):
        sid = _spec_chart(db_session, org, metric_multi_dim.id_metric, "radar", {
            "axis_field": "Asignatura", "y_field": "Logro", "group_field": "Curso",
        })
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text
        ds = r.json()["dataset"]
        # Una serie por curso
        assert len(ds["series"]) >= 2

    def test_line_con_group(self, client_auth, db_session, org, metric_multi_dim):
        sid = _spec_chart(db_session, org, metric_multi_dim.id_metric, "line", {
            "x_field": "Curso", "y_field": "Logro", "group_field": "Asignatura",
        })
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text
        ds = r.json()["dataset"]
        assert "x" in ds and "series" in ds

    def test_pivot_matrix_sin_outer(self, client_auth, db_session, org, metric_multi_dim):
        sid = _spec_chart(db_session, org, metric_multi_dim.id_metric, "pivot_matrix", {
            "axis_field": "Curso", "x_field": "Asignatura", "y_field": "Nivel",
        })
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text
        ds = r.json()["dataset"]
        assert "rows" in ds and "cols" in ds and "cells" in ds

    def test_pivot_matrix_con_outer(self, client_auth, db_session, org, metric_multi_dim):
        sid = _spec_chart(db_session, org, metric_multi_dim.id_metric, "pivot_matrix", {
            "axis_field": "Curso", "x_field": "Asignatura",
            "group_field": "Nivel", "y_field": "Logro",
        })
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200, r.text
        ds = r.json()["dataset"]
        assert "col_outer" in ds and "col_inner" in ds


@pytest.mark.integration
class TestAestheticsXOrder:
    """aesthetics.x_order ordena las categorías del eje X (rama menos común)."""

    def test_bar_con_x_order(self, client_auth, db_session, org, metric_con_datos):
        """Con x_order ["2° Básico", "1° Básico"] el orden del eje X se invierte."""
        sid = _spec_chart(
            db_session, org, metric_con_datos.id_metric, "bar",
            {"x_field": "Curso", "y_field": "Logro", "aggregation": "mean"},
            aesthetics={"x_order": ["2° Básico", "1° Básico"]},
        )
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200
        ds = r.json()["dataset"]
        assert ds["x"][0] == "2° Básico"
        assert ds["x"][1] == "1° Básico"

    def test_pie_con_y_field(self, client_auth, db_session, org, metric_multi_dim):
        """pie con y_field: agrega Y por categoría (no solo count)."""
        sid = _spec_chart(db_session, org, metric_multi_dim.id_metric, "pie", {
            "category_field": "Asignatura", "y_field": "Logro",
            "aggregation": "mean",
        })
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200
        ds = r.json()["dataset"]
        assert len(ds["labels"]) == 2  # Lenguaje y Matemática

    def test_gauge_con_agg_sum(self, client_auth, db_session, org, metric_con_datos):
        """gauge con sum (default es mean)."""
        sid = _spec_chart(db_session, org, metric_con_datos.id_metric, "gauge", {
            "y_field": "Logro", "aggregation": "sum",
        })
        r = client_auth.get(f"/api/charts/{sid}/data")
        assert r.status_code == 200
        ds = r.json()["dataset"]
        assert ds["value"] == pytest.approx(2.6)  # 0.8 + 0.6 + 0.7 + 0.5


@pytest.mark.integration
class TestPreviewErroresMapping:
    """ValueError en _build_dataset → 400 en /preview (línea 722-723)."""

    def test_400_bar_sin_x_field(self, client_auth, metric_con_datos):
        r = client_auth.post("/api/charts/preview", json={
            "config": {
                "chart_type": "bar",
                "data_source": {"metric_id": metric_con_datos.id_metric, "filters": {}},
                "mapping": {"y_field": "Logro"},  # falta x_field
            },
        })
        assert r.status_code == 400
        assert "bar requiere" in r.json()["detail"]

    def test_400_grouped_bar_sin_group_field(self, client_auth, metric_con_datos):
        r = client_auth.post("/api/charts/preview", json={
            "config": {
                "chart_type": "grouped_bar",
                "data_source": {"metric_id": metric_con_datos.id_metric, "filters": {}},
                "mapping": {"x_field": "Curso", "y_field": "Logro"},  # falta group_field
            },
        })
        assert r.status_code == 400

    def test_400_pie_sin_category_field(self, client_auth, metric_con_datos):
        r = client_auth.post("/api/charts/preview", json={
            "config": {
                "chart_type": "pie",
                "data_source": {"metric_id": metric_con_datos.id_metric, "filters": {}},
                "mapping": {"y_field": "Logro"},  # ni category_field ni x_field
            },
        })
        assert r.status_code == 400

    def test_400_radar_sin_axis_field(self, client_auth, metric_con_datos):
        r = client_auth.post("/api/charts/preview", json={
            "config": {
                "chart_type": "radar",
                "data_source": {"metric_id": metric_con_datos.id_metric, "filters": {}},
                "mapping": {"y_field": "Logro"},  # falta axis_field
            },
        })
        assert r.status_code == 400

    def test_empty_si_df_filtrado_vacio(self, client_auth, metric_con_datos):
        """Filtro que no matchea nada → dataset {'empty': True}, status 200."""
        r = client_auth.post("/api/charts/preview", json={
            "config": {
                "chart_type": "bar",
                "data_source": {
                    "metric_id": metric_con_datos.id_metric,
                    "filters": {"Curso": "Inexistente"},
                },
                "mapping": {"x_field": "Curso", "y_field": "Logro"},
            },
        })
        assert r.status_code == 200
        body = r.json()
        # Df vacío → dataset {"empty": True} o n_rows == 0
        assert body["n_rows"] == 0
        assert body["dataset"] == {"empty": True}


# ─────────────────────────────────────────────────────────────────────────
# POST /api/charts/preview
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestPreviewChart:
    def test_sin_auth_401(self, client):
        r = client.post("/api/charts/preview", json={
            "config": {
                "chart_type": "bar",
                "data_source": {"metric_id": 1, "filters": {}},
                "mapping": {"x_field": "X", "y_field": "Y"},
            },
        })
        assert r.status_code == 401

    def test_preview_success(self, client_auth, metric_con_datos):
        """Preview sin persistir: pasa la config directo en el body."""
        r = client_auth.post("/api/charts/preview", json={
            "config": {
                "chart_type": "bar",
                "data_source": {"metric_id": metric_con_datos.id_metric, "filters": {}},
                "mapping": {"x_field": "Curso", "y_field": "Logro", "aggregation": "mean"},
            },
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["chart_type"] == "bar"
        assert body["n_rows"] == 4

    def test_preview_422_config_invalida(self, client_auth):
        """chart_type no soportado en el body → 422 de Pydantic."""
        r = client_auth.post("/api/charts/preview", json={
            "config": {
                "chart_type": "ufo",
                "data_source": {"metric_id": 1, "filters": {}},
            },
        })
        assert r.status_code == 422

    def test_preview_extra_filters(self, client_auth, metric_con_datos):
        r = client_auth.post("/api/charts/preview", json={
            "config": {
                "chart_type": "bar",
                "data_source": {"metric_id": metric_con_datos.id_metric, "filters": {}},
                "mapping": {"x_field": "Curso", "y_field": "Logro"},
            },
            "extra_filters": {"Curso": "2° Básico"},
        })
        assert r.status_code == 200
        assert r.json()["n_rows"] == 2


# ─────────────────────────────────────────────────────────────────────────
# Regresión integrada: bug del 19-may
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestChartsRegresion19May:
    """Chart con derived_fields_override usando slope+ordinal sin time_ordinal_levels.

    En el incidente del 19-may esto generó traceback en logs (`apply_slope`
    → `_as_numeric` ValueError). El router atrapa con `except Exception`
    y degrada el chart sin la columna derivada. Este test fija el contrato:
    el endpoint NO devuelve 500 ante esa config malformada.
    """

    def test_slope_ordinal_sin_levels_no_500(self, client_auth, metric_con_datos):
        """Repro exacto del path de la traza: el endpoint sigue devolviendo 200."""
        cfg = {
            "chart_type": "bar",
            "data_source": {
                "metric_id": metric_con_datos.id_metric,
                "filters": {},
                "derived_fields_override": [{
                    "configs": [{
                        "kind": "slope",
                        "name": "Avance",
                        "value_field": "Logro",
                        "entity_field": "Curso",
                        "time_field": "Curso",
                        "time_type": "ordinal",
                        # falta time_ordinal_levels — el bug exacto del 19-may
                    }],
                }],
            },
            "mapping": {"x_field": "Curso", "y_field": "Logro"},
        }
        r = client_auth.post("/api/charts/preview", json={"config": cfg})
        # Lo importante: NO 500. El router degrada con except.
        assert r.status_code != 500, r.text
        assert r.status_code in (200, 400)
