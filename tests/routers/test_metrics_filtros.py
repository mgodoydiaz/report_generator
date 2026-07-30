"""Tests de los filtros server-side de /api/metrics/{id}/data y /data/facets.

Cubre:

    GET /api/metrics/{id}/data?filters=...   filtro exacto por dimensión
    GET /api/metrics/{id}/data?q=...         búsqueda libre
    GET /api/metrics/{id}/data/facets        valores distintos por dimensión

El filtrado ocurre DENTRO de la query paginada (ver `_aplicar_filtros` en
`backend/routers/metrics.py`), así que estos tests verifican tanto `items`
como `total` — un filtro aplicado en Python después de paginar daría un
`total` sin filtrar y páginas incompletas.
"""
from __future__ import annotations

import json
from urllib.parse import quote

import pytest

from tests.factories import (
    auth_header_for,
    make_dimension,
    make_metric,
    make_metric_data,
    make_org,
    make_user,
)


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def metrica_filtrable(db_session, org):
    """Métrica con 2 dimensiones (Año, Mes) y 6 filas conocidas.

    Año | Mes        | value
    ----+------------+-------
    2025| MARZO      | 10
    2025| NOVIEMBRE  | 20
    2026| MARZO      | 30
    2026| NOVIEMBRE  | 40
    2026| NOVIEMBRE  | 50
    2024| JULIO      | 60
    """
    dim_anio = make_dimension(db_session, org, name="Año")
    dim_mes = make_dimension(db_session, org, name="Mes")
    metric = make_metric(
        db_session, org, name="Puntaje", data_type="float",
        dimensions=[dim_anio, dim_mes],
    )
    filas = [
        ("2025", "MARZO", "10"),
        ("2025", "NOVIEMBRE", "20"),
        ("2026", "MARZO", "30"),
        ("2026", "NOVIEMBRE", "40"),
        ("2026", "NOVIEMBRE", "50"),
        ("2024", "JULIO", "60"),
    ]
    for anio, mes, val in filas:
        make_metric_data(
            db_session, metric, value=val,
            dimensions_json={
                str(dim_anio.id_dimension): anio,
                str(dim_mes.id_dimension): mes,
            },
        )
    return metric, dim_anio, dim_mes


def _filters(**por_dim) -> str:
    """Serializa {dim_id: [valores]} tal como lo manda el frontend."""
    return quote(json.dumps(por_dim))


# ─────────────────────────────────────────────────────────────────────────
# Retrocompatibilidad
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestSinFiltros:
    def test_sin_params_devuelve_todo(self, client_auth, metrica_filtrable):
        metric, _, _ = metrica_filtrable
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/data")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 6
        assert len(body["items"]) == 6
        # Forma del item intacta
        assert set(body["items"][0]) >= {"id_data", "id_metric", "value", "dimensions_json", "created_at"}

    def test_filters_vacio_equivale_a_sin_filtros(self, client_auth, metrica_filtrable):
        metric, _, _ = metrica_filtrable
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/data?filters={_filters()}&q=")
        assert r.json()["total"] == 6

    def test_filters_json_invalido_400(self, client_auth, metrica_filtrable):
        metric, _, _ = metrica_filtrable
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/data?filters=no-es-json")
        assert r.status_code == 400

    def test_filters_con_clave_no_numerica_400(self, client_auth, metrica_filtrable):
        metric, _, _ = metrica_filtrable
        raw = quote(json.dumps({"Curso'; DROP TABLE metric_data; --": ["x"]}))
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/data?filters={raw}")
        assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────
# filters
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestFiltroPorDimension:
    def test_una_dimension(self, client_auth, metrica_filtrable):
        metric, dim_anio, _ = metrica_filtrable
        raw = _filters(**{str(dim_anio.id_dimension): ["2026"]})
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/data?filters={raw}")
        body = r.json()
        assert body["total"] == 3
        assert {i["value"] for i in body["items"]} == {"30", "40", "50"}

    def test_dos_dimensiones_es_and(self, client_auth, metrica_filtrable):
        metric, dim_anio, dim_mes = metrica_filtrable
        raw = _filters(**{
            str(dim_anio.id_dimension): ["2026"],
            str(dim_mes.id_dimension): ["NOVIEMBRE"],
        })
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/data?filters={raw}")
        body = r.json()
        assert body["total"] == 2
        assert {i["value"] for i in body["items"]} == {"40", "50"}

    def test_multi_valor_es_in(self, client_auth, metrica_filtrable):
        metric, dim_anio, _ = metrica_filtrable
        raw = _filters(**{str(dim_anio.id_dimension): ["2024", "2025"]})
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/data?filters={raw}")
        body = r.json()
        assert body["total"] == 3
        assert {i["value"] for i in body["items"]} == {"10", "20", "60"}

    def test_valor_inexistente_devuelve_vacio(self, client_auth, metrica_filtrable):
        metric, dim_anio, _ = metrica_filtrable
        raw = _filters(**{str(dim_anio.id_dimension): ["1999"]})
        body = client_auth.get(f"/api/metrics/{metric.id_metric}/data?filters={raw}").json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_paginacion_con_filtro(self, client_auth, metrica_filtrable):
        """Página 2 con filtro: total filtrado, sin solapamiento entre páginas."""
        metric, dim_anio, _ = metrica_filtrable
        raw = _filters(**{str(dim_anio.id_dimension): ["2026"]})
        base = f"/api/metrics/{metric.id_metric}/data?filters={raw}&page_size=2"

        p1 = client_auth.get(f"{base}&page=1").json()
        p2 = client_auth.get(f"{base}&page=2").json()

        assert p1["total"] == 3 and p2["total"] == 3
        assert len(p1["items"]) == 2
        assert len(p2["items"]) == 1
        ids1 = {i["id_data"] for i in p1["items"]}
        ids2 = {i["id_data"] for i in p2["items"]}
        assert not (ids1 & ids2)
        assert {i["value"] for i in p1["items"]} | {i["value"] for i in p2["items"]} == {"30", "40", "50"}

    def test_include_audit_sigue_funcionando_con_filtro(self, client_auth, metrica_filtrable):
        metric, dim_anio, _ = metrica_filtrable
        raw = _filters(**{str(dim_anio.id_dimension): ["2026"]})
        body = client_auth.get(
            f"/api/metrics/{metric.id_metric}/data?filters={raw}&include_audit=true"
        ).json()
        assert body["total"] == 3
        assert all("audit" in i for i in body["items"])


# ─────────────────────────────────────────────────────────────────────────
# q
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestBusquedaLibre:
    def test_q_sobre_valor(self, client_auth, metrica_filtrable):
        metric, _, _ = metrica_filtrable
        body = client_auth.get(f"/api/metrics/{metric.id_metric}/data?q=60").json()
        assert body["total"] == 1
        assert body["items"][0]["value"] == "60"

    def test_q_sobre_dimension(self, client_auth, metrica_filtrable):
        metric, _, _ = metrica_filtrable
        body = client_auth.get(f"/api/metrics/{metric.id_metric}/data?q=NOVIEMBRE").json()
        assert body["total"] == 3
        assert {i["value"] for i in body["items"]} == {"20", "40", "50"}

    def test_q_es_case_insensitive(self, client_auth, metrica_filtrable):
        metric, _, _ = metrica_filtrable
        body = client_auth.get(f"/api/metrics/{metric.id_metric}/data?q=noviembre").json()
        assert body["total"] == 3

    def test_q_combinado_con_filters(self, client_auth, metrica_filtrable):
        metric, dim_anio, _ = metrica_filtrable
        raw = _filters(**{str(dim_anio.id_dimension): ["2026"]})
        body = client_auth.get(
            f"/api/metrics/{metric.id_metric}/data?filters={raw}&q=NOVIEMBRE"
        ).json()
        assert body["total"] == 2
        assert {i["value"] for i in body["items"]} == {"40", "50"}

    def test_q_sin_matches(self, client_auth, metrica_filtrable):
        metric, _, _ = metrica_filtrable
        body = client_auth.get(f"/api/metrics/{metric.id_metric}/data?q=zzzz").json()
        assert body["total"] == 0


# ─────────────────────────────────────────────────────────────────────────
# Multi-tenancy
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestTenancy:
    def test_metrica_de_otra_org_404(self, client_auth, db_session):
        otra = make_org(db_session, name="Otra Org Filtros")
        dim = make_dimension(db_session, otra, name="Año")
        m = make_metric(db_session, otra, name="Ajena", dimensions=[dim])
        make_metric_data(db_session, m, value="99", dimensions_json={str(dim.id_dimension): "2026"})

        raw = _filters(**{str(dim.id_dimension): ["2026"]})
        assert client_auth.get(f"/api/metrics/{m.id_metric}/data?filters={raw}").status_code == 404
        assert client_auth.get(f"/api/metrics/{m.id_metric}/data/facets").status_code == 404

    def test_filtro_no_cruza_datos_entre_orgs(self, client_auth, db_session, metrica_filtrable):
        """Misma dimensión-id lógica en otra org: cada usuario ve solo lo suyo."""
        metric, dim_anio, _ = metrica_filtrable

        otra = make_org(db_session, name="Org Vecina Filtros")
        dim_otra = make_dimension(db_session, otra, name="Año")
        m_otra = make_metric(db_session, otra, name="Puntaje Vecino", dimensions=[dim_otra])
        for val in ("777", "888"):
            make_metric_data(
                db_session, m_otra, value=val,
                dimensions_json={str(dim_otra.id_dimension): "2026"},
            )
        user_otra = make_user(db_session, otra, email="vecino@filtros.test")

        raw_mio = _filters(**{str(dim_anio.id_dimension): ["2026"]})
        body_mio = client_auth.get(f"/api/metrics/{metric.id_metric}/data?filters={raw_mio}").json()
        assert {i["value"] for i in body_mio["items"]} == {"30", "40", "50"}

        raw_otro = _filters(**{str(dim_otra.id_dimension): ["2026"]})
        r_otro = client_auth.get(
            f"/api/metrics/{m_otra.id_metric}/data?filters={raw_otro}",
            headers=auth_header_for(user_otra),
        )
        assert {i["value"] for i in r_otro.json()["items"]} == {"777", "888"}


# ─────────────────────────────────────────────────────────────────────────
# facets
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestFacets:
    def test_sin_auth_401(self, client, metrica_filtrable):
        metric, _, _ = metrica_filtrable
        assert client.get(f"/api/metrics/{metric.id_metric}/data/facets").status_code == 401

    def test_valores_distintos_por_dimension(self, client_auth, metrica_filtrable):
        metric, dim_anio, dim_mes = metrica_filtrable
        body = client_auth.get(f"/api/metrics/{metric.id_metric}/data/facets").json()

        assert set(body) == {str(dim_anio.id_dimension), str(dim_mes.id_dimension)}
        assert body[str(dim_anio.id_dimension)]["name"] == "Año"
        assert body[str(dim_anio.id_dimension)]["values"] == ["2024", "2025", "2026"]
        assert sorted(body[str(dim_mes.id_dimension)]["values"]) == ["JULIO", "MARZO", "NOVIEMBRE"]

    def test_metrica_sin_datos_devuelve_vacio(self, client_auth, db_session, org):
        dim = make_dimension(db_session, org, name="Curso")
        m = make_metric(db_session, org, name="Vacia", dimensions=[dim])
        assert client_auth.get(f"/api/metrics/{m.id_metric}/data/facets").json() == {}

    def test_descarta_nan_y_vacios(self, client_auth, db_session, org):
        dim = make_dimension(db_session, org, name="Curso")
        m = make_metric(db_session, org, name="Con Basura", dimensions=[dim])
        for v in ("1 A", "nan", "", "2 A", "1 A"):
            make_metric_data(db_session, m, value="1", dimensions_json={str(dim.id_dimension): v})
        body = client_auth.get(f"/api/metrics/{m.id_metric}/data/facets").json()
        assert body[str(dim.id_dimension)]["values"] == ["1 A", "2 A"]

    def test_orden_natural(self, client_auth, db_session, org):
        dim = make_dimension(db_session, org, name="Curso")
        m = make_metric(db_session, org, name="Cursos", dimensions=[dim])
        for v in ("10 A", "2 A", "1 A"):
            make_metric_data(db_session, m, value="1", dimensions_json={str(dim.id_dimension): v})
        body = client_auth.get(f"/api/metrics/{m.id_metric}/data/facets").json()
        assert body[str(dim.id_dimension)]["values"] == ["1 A", "2 A", "10 A"]

    def test_facets_alimentan_filtros_validos(self, client_auth, metrica_filtrable):
        """Todo valor devuelto por facets tiene ≥1 fila al usarlo como filtro."""
        metric, _, _ = metrica_filtrable
        facets = client_auth.get(f"/api/metrics/{metric.id_metric}/data/facets").json()
        for dim_id, meta in facets.items():
            for val in meta["values"]:
                raw = _filters(**{dim_id: [val]})
                body = client_auth.get(f"/api/metrics/{metric.id_metric}/data?filters={raw}").json()
                assert body["total"] > 0, f"{meta['name']}={val} no devolvió filas"
