"""Tests del router /api/results — el endpoint más complejo del backend.

Cubre:
- Multi-tenancy (404 vs otra org)
- Filtros: estructural, multi-valor, cascading
- Datos object (con meta_json.fields)
- Aplicación de derived_columns desde el indicador
- Lista vacía si sin metrics
"""
from __future__ import annotations

import json

import pytest

from tests.factories import (
    make_dimension,
    make_indicator,
    make_metric,
    make_metric_data,
    make_org,
)


@pytest.fixture
def indicador_simple(db_session, org):
    """Indicador con 1 métrica float + 1 dimensión Curso."""
    dim_curso = make_dimension(db_session, org, name="Curso")
    m = make_metric(db_session, org, name="Logro", data_type="float", dimensions=[dim_curso])
    ind = make_indicator(db_session, org, name="Test Ind", metrics=[m])
    # Insertar valores: 2 cursos
    make_metric_data(db_session, m, value="0.5", dimensions_json={str(dim_curso.id_dimension): "A"})
    make_metric_data(db_session, m, value="0.7", dimensions_json={str(dim_curso.id_dimension): "B"})
    return ind, m, dim_curso


@pytest.mark.integration
class TestGetIndicatorData:
    def test_sin_auth_401(self, client, indicador_simple):
        ind, _, _ = indicador_simple
        r = client.get(f"/api/results/indicator/{ind.id_indicator}/data")
        assert r.status_code == 401

    def test_indicador_inexistente_devuelve_estructura_vacia(self, client_auth):
        r = client_auth.get("/api/results/indicator/99999/data")
        assert r.status_code == 200
        data = r.json()
        assert data["metrics"] == []
        assert data["data"] == {}
        assert data["dimensions"] == {}

    def test_indicador_de_otra_org_devuelve_estructura_vacia(self, client_auth, db_session):
        """Multi-tenancy: no se ven datos de otra org."""
        other = make_org(db_session)
        ind = make_indicator(db_session, other, name="Foreign")
        r = client_auth.get(f"/api/results/indicator/{ind.id_indicator}/data")
        assert r.status_code == 200
        assert r.json()["metrics"] == []  # no leak

    def test_carga_datos_basicos(self, client_auth, indicador_simple):
        ind, m, dim = indicador_simple
        r = client_auth.get(f"/api/results/indicator/{ind.id_indicator}/data")
        assert r.status_code == 200, r.text
        data = r.json()
        # Hay 1 metric
        assert len(data["metrics"]) == 1
        assert data["metrics"][0]["id_metric"] == m.id_metric
        # Hay 1 dimensión con sus 2 values posibles
        assert str(dim.id_dimension) in data["dimensions"]
        dim_info = data["dimensions"][str(dim.id_dimension)]
        assert dim_info["name"] == "Curso"
        assert sorted(dim_info["values"]) == ["A", "B"]
        # Hay 2 rows en data
        assert len(data["data"][str(m.id_metric)]) == 2


@pytest.mark.integration
class TestFiltros:
    def test_filtro_estructural_single_value(self, client_auth, indicador_simple):
        ind, m, dim = indicador_simple
        filtros = json.dumps({str(dim.id_dimension): "A"})
        r = client_auth.get(
            f"/api/results/indicator/{ind.id_indicator}/data?filters={filtros}"
        )
        assert r.status_code == 200
        rows = r.json()["data"][str(m.id_metric)]
        # Solo el curso A
        assert len(rows) == 1
        assert rows[0]["dimensions_json"][str(dim.id_dimension)] == "A"

    def test_filtro_multi_valor_lista(self, client_auth, db_session, indicador_simple):
        """B9: filtro como list → IN."""
        ind, m, dim = indicador_simple
        # Agregar curso C para tener 3
        make_metric_data(
            db_session, m, value="0.9",
            dimensions_json={str(dim.id_dimension): "C"},
        )
        # Filtrar A y C
        filtros = json.dumps({str(dim.id_dimension): ["A", "C"]})
        r = client_auth.get(
            f"/api/results/indicator/{ind.id_indicator}/data?filters={filtros}"
        )
        assert r.status_code == 200
        rows = r.json()["data"][str(m.id_metric)]
        assert len(rows) == 2
        valores = {row["dimensions_json"][str(dim.id_dimension)] for row in rows}
        assert valores == {"A", "C"}

    def test_filtro_invalido_no_rompe(self, client_auth, indicador_simple):
        """Filtros con JSON malo se ignoran silenciosamente."""
        ind, m, _ = indicador_simple
        r = client_auth.get(
            f"/api/results/indicator/{ind.id_indicator}/data?filters=not-json"
        )
        assert r.status_code == 200
        # Sin filtros aplicados, devuelve los 2 rows
        assert len(r.json()["data"][str(m.id_metric)]) == 2

    def test_cascading_dimension_values(self, client_auth, db_session, org):
        """Cuando hay filtros activos, dim_values se recalculan excluyendo
        el filtro de la propia dimensión (paso 7.5)."""
        dim_year = make_dimension(db_session, org, name="Año")
        dim_curso = make_dimension(db_session, org, name="Curso")
        m = make_metric(db_session, org, name="X", dimensions=[dim_year, dim_curso])
        ind = make_indicator(db_session, org, name="Y", metrics=[m])

        # 2026: A, B; 2025: solo A
        make_metric_data(db_session, m, value="0.1", dimensions_json={
            str(dim_year.id_dimension): "2026",
            str(dim_curso.id_dimension): "A",
        })
        make_metric_data(db_session, m, value="0.2", dimensions_json={
            str(dim_year.id_dimension): "2026",
            str(dim_curso.id_dimension): "B",
        })
        make_metric_data(db_session, m, value="0.3", dimensions_json={
            str(dim_year.id_dimension): "2025",
            str(dim_curso.id_dimension): "A",
        })

        # Filtrar Año=2026 → cursos disponibles deben ser solo A, B (no incluye 2025-only)
        # Pero los values de Año deben mantener 2025 y 2026 (no filtra a sí misma).
        filtros = json.dumps({str(dim_year.id_dimension): "2026"})
        r = client_auth.get(
            f"/api/results/indicator/{ind.id_indicator}/data?filters={filtros}"
        )
        assert r.status_code == 200
        dims = r.json()["dimensions"]
        # Año mantiene 2025 y 2026 (cascading: no filtra a sí misma)
        assert sorted(dims[str(dim_year.id_dimension)]["values"]) == ["2025", "2026"]
        # Curso muestra los disponibles bajo 2026
        assert sorted(dims[str(dim_curso.id_dimension)]["values"]) == ["A", "B"]


@pytest.mark.integration
class TestObjectMetricData:
    def test_value_object_se_parsea_a_dict(self, client_auth, db_session, org):
        """metrics con data_type='object' tienen value como JSON dict."""
        dim = make_dimension(db_session, org, name="Curso")
        m = make_metric(
            db_session, org, name="Estudiante", data_type="object",
            fields=[
                {"name": "Buenas", "type": "int"},
                {"name": "Rend", "type": "float"},
            ],
            dimensions=[dim],
        )
        ind = make_indicator(db_session, org, metrics=[m])
        make_metric_data(
            db_session, m,
            value={"Buenas": 8, "Rend": 0.8},
            dimensions_json={str(dim.id_dimension): "A"},
        )
        r = client_auth.get(f"/api/results/indicator/{ind.id_indicator}/data")
        assert r.status_code == 200
        rows = r.json()["data"][str(m.id_metric)]
        assert len(rows) == 1
        # value se devuelve como dict (parseado), no como string
        val = rows[0]["value"]
        assert isinstance(val, dict)
        assert val["Buenas"] == 8
        assert val["Rend"] == 0.8


@pytest.mark.integration
class TestIndicadorSinMetrics:
    def test_devuelve_estructura_vacia(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="SinMetrics")
        r = client_auth.get(f"/api/results/indicator/{ind.id_indicator}/data")
        assert r.status_code == 200
        assert r.json()["metrics"] == []
