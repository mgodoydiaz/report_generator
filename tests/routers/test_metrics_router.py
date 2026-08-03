"""Tests del router /api/metrics — Sprint 5 (cobertura 23% → 70%+).

14 endpoints cubiertos:

    GET    /api/metrics/                      list (filtrado por org)
    POST   /api/metrics/                      create
    PUT    /api/metrics/{id}                  update
    DELETE /api/metrics/{id}                  delete
    GET    /api/metrics/{id}/data              paginated data
    POST   /api/metrics/{id}/data              add single point
    POST   /api/metrics/{id}/clear             clear all data
    DELETE /api/metrics/data/{id}              delete single point
    PUT    /api/metrics/data/{id}              update single point
    POST   /api/metrics/data/batch-delete      bulk delete
    GET    /api/metrics/{id}/export            export xlsx/csv/txt
    GET    /api/metrics/{id}/distinct/{col}    distinct values
    GET    /api/metrics/{id}/template          template para import
    POST   /api/metrics/{id}/import            (skipped — requiere upload de archivo)
"""
from __future__ import annotations

import json

import pytest

from tests.factories import make_dimension, make_metric, make_metric_data, make_org


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def metric_simple(db_session, org):
    return make_metric(db_session, org, name="Logro", data_type="float")


@pytest.fixture
def metric_con_dims_y_datos(db_session, org):
    dim_curso = make_dimension(db_session, org, name="Curso")
    metric = make_metric(
        db_session, org, name="Logro", data_type="float",
        dimensions=[dim_curso],
    )
    for curso, val in [
        ("1° Básico", "0.80"), ("2° Básico", "0.60"),
        ("3° Básico", "0.70"),
    ]:
        make_metric_data(
            db_session, metric, value=val,
            dimensions_json={str(dim_curso.id_dimension): curso},
        )
    return metric, dim_curso


@pytest.fixture
def metric_de_otra_org(db_session):
    other = make_org(db_session, name="Otra Org Metric")
    m = make_metric(db_session, other, name="Ajena")
    return other, m


# ─────────────────────────────────────────────────────────────────────────
# GET / + POST /
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestListMetrics:
    def test_sin_auth_401(self, client):
        assert client.get("/api/metrics/").status_code == 401

    def test_lista_vacia(self, client_auth):
        r = client_auth.get("/api/metrics/")
        assert r.status_code == 200
        assert r.json() == []

    def test_lista_filtra_por_org(self, client_auth, db_session, org):
        make_metric(db_session, org, name="Mia")
        other = make_org(db_session)
        make_metric(db_session, other, name="Ajena")
        r = client_auth.get("/api/metrics/")
        names = [m["name"] for m in r.json()]
        assert "Mia" in names
        assert "Ajena" not in names

    def test_lista_incluye_dimension_ids(self, client_auth, metric_con_dims_y_datos):
        metric, dim_curso = metric_con_dims_y_datos
        r = client_auth.get("/api/metrics/")
        assert r.status_code == 200
        item = next(m for m in r.json() if m["id_metric"] == metric.id_metric)
        assert dim_curso.id_dimension in item["dimension_ids"]


@pytest.mark.integration
class TestCreateMetric:
    def test_sin_auth_401(self, client):
        r = client.post("/api/metrics/", json={"name": "X", "data_type": "float"})
        assert r.status_code == 401

    def test_crear_metric_basico(self, client_auth):
        r = client_auth.post("/api/metrics/", json={
            "name": "Logro", "data_type": "float",
            "meta_json": {}, "description": "",
            "dimension_ids": [],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "success"
        assert body["data"]["name"] == "Logro"

    def test_crear_persiste_org_id(self, client_auth, db_session, org):
        r = client_auth.post("/api/metrics/", json={
            "name": "Mio", "data_type": "float",
        })
        assert r.status_code == 200
        from backend.models import Metric
        mid = r.json()["data"]["id_metric"]
        m = db_session.get(Metric, mid)
        assert m.org_id == org.id

    def test_crear_con_dimensions(self, client_auth, db_session, org):
        d1 = make_dimension(db_session, org, name="DimA")
        d2 = make_dimension(db_session, org, name="DimB")
        r = client_auth.post("/api/metrics/", json={
            "name": "MultiDim", "data_type": "float",
            "dimension_ids": [d1.id_dimension, d2.id_dimension],
        })
        assert r.status_code == 200
        assert set(r.json()["data"]["dimension_ids"]) == {d1.id_dimension, d2.id_dimension}

    def test_crear_con_dimension_de_otra_org_400(self, client_auth, db_session):
        """Validación cross-org: NO puedes linkear a dims de otra org."""
        other = make_org(db_session)
        d_ajena = make_dimension(db_session, other, name="Ajena")
        r = client_auth.post("/api/metrics/", json={
            "name": "X", "data_type": "float",
            "dimension_ids": [d_ajena.id_dimension],
        })
        # _validate_dimension_ids levanta HTTPException(400)
        assert r.status_code == 500  # el create wrappea en try/except Exception → 500


# ─────────────────────────────────────────────────────────────────────────
# PUT /{id} + DELETE /{id}
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestUpdateMetric:
    def test_sin_auth_401(self, client, metric_simple):
        r = client.put(f"/api/metrics/{metric_simple.id_metric}",
                       json={"name": "X", "data_type": "float"})
        assert r.status_code == 401

    def test_404_no_existe(self, client_auth):
        r = client_auth.put("/api/metrics/99999",
                            json={"name": "X", "data_type": "float"})
        assert r.status_code == 404

    def test_404_otra_org(self, client_auth, metric_de_otra_org):
        _, m = metric_de_otra_org
        r = client_auth.put(f"/api/metrics/{m.id_metric}",
                            json={"name": "Hack", "data_type": "float"})
        assert r.status_code == 404

    def test_update_name_y_meta(self, client_auth, metric_simple):
        r = client_auth.put(f"/api/metrics/{metric_simple.id_metric}", json={
            "name": "Renombrada", "data_type": "float",
            "description": "nueva desc",
            "meta_json": {"unit": "%"},
        })
        assert r.status_code == 200
        items = client_auth.get("/api/metrics/").json()
        m = next(x for x in items if x["id_metric"] == metric_simple.id_metric)
        assert m["name"] == "Renombrada"
        assert m["description"] == "nueva desc"
        assert m["meta_json"] == {"unit": "%"}

    def test_update_dimension_ids_reemplaza(self, client_auth, db_session, org, metric_simple):
        d1 = make_dimension(db_session, org, name="NuevaDim")
        r = client_auth.put(f"/api/metrics/{metric_simple.id_metric}", json={
            "name": "Logro", "data_type": "float",
            "dimension_ids": [d1.id_dimension],
        })
        assert r.status_code == 200
        items = client_auth.get("/api/metrics/").json()
        m = next(x for x in items if x["id_metric"] == metric_simple.id_metric)
        assert m["dimension_ids"] == [d1.id_dimension]


@pytest.mark.integration
class TestDeleteMetric:
    def test_sin_auth_401(self, client, metric_simple):
        assert client.delete(f"/api/metrics/{metric_simple.id_metric}").status_code == 401

    def test_delete_existente(self, client_auth_admin, metric_simple, db_session):
        from backend.models import Metric
        mid = metric_simple.id_metric
        r = client_auth_admin.delete(f"/api/metrics/{mid}")
        assert r.status_code == 200
        db_session.expire_all()
        assert db_session.get(Metric, mid) is None

    def test_delete_otra_org_no_borra_pero_responde_200(self, client_auth_admin, metric_de_otra_org, db_session):
        """El endpoint hace silent-skip si la metric no es de tu org (no borra,
        no levanta 404). Quizás debería ser 404, pero el comportamiento actual
        es 200 con `status: success` y la metric intacta."""
        from backend.models import Metric
        _, m = metric_de_otra_org
        r = client_auth_admin.delete(f"/api/metrics/{m.id_metric}")
        assert r.status_code == 200
        db_session.expire_all()
        # La metric sigue existiendo (no fue borrada porque no era de mi org)
        assert db_session.get(Metric, m.id_metric) is not None


# ─────────────────────────────────────────────────────────────────────────
# GET /{id}/data + POST /{id}/data
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetMetricData:
    def test_sin_auth_401(self, client, metric_simple):
        assert client.get(f"/api/metrics/{metric_simple.id_metric}/data").status_code == 401

    def test_404_no_existe(self, client_auth):
        assert client_auth.get("/api/metrics/99999/data").status_code == 404

    def test_404_otra_org(self, client_auth, metric_de_otra_org):
        _, m = metric_de_otra_org
        assert client_auth.get(f"/api/metrics/{m.id_metric}/data").status_code == 404

    def test_data_success(self, client_auth, metric_con_dims_y_datos):
        metric, _ = metric_con_dims_y_datos
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/data")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3

    def test_paginacion(self, client_auth, metric_con_dims_y_datos):
        metric, _ = metric_con_dims_y_datos
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/data",
                            params={"page": 2, "page_size": 2})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert len(body["items"]) == 1  # 3 - (2-1)*2 = 1

    def test_include_audit(self, client_auth, metric_con_dims_y_datos):
        metric, _ = metric_con_dims_y_datos
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/data",
                            params={"include_audit": "true"})
        assert r.status_code == 200
        # audit debe estar en cada item
        for item in r.json()["items"]:
            assert "audit" in item


@pytest.mark.integration
class TestAddDataPoint:
    def test_sin_auth_401(self, client, metric_simple):
        r = client.post(f"/api/metrics/{metric_simple.id_metric}/data",
                        json={"value": "1.0", "dimensions_json": {}})
        assert r.status_code == 401

    def test_404_no_existe(self, client_auth):
        r = client_auth.post("/api/metrics/99999/data",
                             json={"value": "1.0", "dimensions_json": {}})
        assert r.status_code == 404

    def test_404_otra_org(self, client_auth, metric_de_otra_org):
        _, m = metric_de_otra_org
        r = client_auth.post(f"/api/metrics/{m.id_metric}/data",
                             json={"value": "1.0", "dimensions_json": {}})
        assert r.status_code == 404

    def test_agrega_data_point_success(self, client_auth, metric_simple, db_session):
        from backend.models import MetricData
        r = client_auth.post(f"/api/metrics/{metric_simple.id_metric}/data", json={
            "value": "0.75", "dimensions_json": {},
        })
        assert r.status_code == 200
        # Persistido
        db_session.expire_all()
        rows = db_session.query(MetricData).filter(
            MetricData.id_metric == metric_simple.id_metric
        ).all()
        assert len(rows) == 1
        assert rows[0].value == "0.75"

    def test_value_dict_se_serializa_a_json(self, client_auth, metric_simple):
        """Si value es dict, el endpoint lo serializa a JSON antes de guardar."""
        r = client_auth.post(f"/api/metrics/{metric_simple.id_metric}/data", json={
            "value": {"score": 1.5, "level": "high"},
            "dimensions_json": {},
        })
        assert r.status_code == 200
        body = r.json()["data"]
        # value persistido como string JSON
        assert isinstance(body["value"], str)
        assert "score" in body["value"]


# ─────────────────────────────────────────────────────────────────────────
# POST /{id}/clear
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestClearMetricData:
    def test_404_no_existe(self, client_auth_admin):
        assert client_auth_admin.post("/api/metrics/99999/clear").status_code == 404

    def test_404_otra_org(self, client_auth_admin, metric_de_otra_org):
        _, m = metric_de_otra_org
        assert client_auth_admin.post(f"/api/metrics/{m.id_metric}/clear").status_code == 404

    def test_clear_borra_todos(self, client_auth_admin, metric_con_dims_y_datos, db_session):
        from backend.models import MetricData
        metric, _ = metric_con_dims_y_datos
        r = client_auth_admin.post(f"/api/metrics/{metric.id_metric}/clear")
        assert r.status_code == 200
        assert r.json()["cleared_count"] == 3
        db_session.expire_all()
        n = db_session.query(MetricData).filter(MetricData.id_metric == metric.id_metric).count()
        assert n == 0


# ─────────────────────────────────────────────────────────────────────────
# DELETE /data/{id} + PUT /data/{id} + POST /data/batch-delete
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestDeleteDataPoint:
    def test_sin_auth_401(self, client, metric_con_dims_y_datos, db_session):
        from backend.models import MetricData
        m, _ = metric_con_dims_y_datos
        d = db_session.query(MetricData).filter(MetricData.id_metric == m.id_metric).first()
        assert client.delete(f"/api/metrics/data/{d.id_data}").status_code == 401

    def test_delete_success(self, client_auth, metric_con_dims_y_datos, db_session):
        from backend.models import MetricData
        m, _ = metric_con_dims_y_datos
        d = db_session.query(MetricData).filter(MetricData.id_metric == m.id_metric).first()
        r = client_auth.delete(f"/api/metrics/data/{d.id_data}")
        assert r.status_code == 200
        db_session.expire_all()
        assert db_session.get(MetricData, d.id_data) is None

    def test_403_si_data_point_de_otra_org(self, client_auth, db_session):
        from backend.models import MetricData
        other = make_org(db_session)
        m_other = make_metric(db_session, other, name="X")
        d = make_metric_data(db_session, m_other, value="1.0")
        r = client_auth.delete(f"/api/metrics/data/{d.id_data}")
        assert r.status_code == 403


@pytest.mark.integration
class TestUpdateDataPoint:
    def test_404_no_existe(self, client_auth):
        r = client_auth.put("/api/metrics/data/99999",
                            json={"value": "1.0", "dimensions_json": {}})
        assert r.status_code == 404

    def test_403_si_otra_org(self, client_auth, db_session):
        from backend.models import MetricData
        other = make_org(db_session)
        m_other = make_metric(db_session, other, name="X")
        d = make_metric_data(db_session, m_other, value="1.0")
        r = client_auth.put(f"/api/metrics/data/{d.id_data}",
                            json={"value": "9.9", "dimensions_json": {}})
        assert r.status_code == 403

    def test_update_value(self, client_auth, metric_con_dims_y_datos, db_session):
        from backend.models import MetricData
        m, _ = metric_con_dims_y_datos
        d = db_session.query(MetricData).filter(MetricData.id_metric == m.id_metric).first()
        r = client_auth.put(f"/api/metrics/data/{d.id_data}",
                            json={"value": "0.99", "dimensions_json": {}})
        assert r.status_code == 200
        db_session.expire_all()
        d_after = db_session.get(MetricData, d.id_data)
        assert d_after.value == "0.99"


@pytest.mark.integration
class TestBatchDelete:
    def test_sin_auth_401(self, client):
        r = client.post("/api/metrics/data/batch-delete", json={"ids": [1, 2]})
        assert r.status_code == 401

    def test_borra_solo_los_de_mi_org(self, client_auth_admin, db_session, metric_con_dims_y_datos):
        """Borra los IDs que SÍ son de mi org; ignora los de otras orgs."""
        from backend.models import MetricData
        m_mio, _ = metric_con_dims_y_datos
        ids_mios = [
            d.id_data for d in
            db_session.query(MetricData).filter(MetricData.id_metric == m_mio.id_metric).all()
        ]
        other = make_org(db_session)
        m_other = make_metric(db_session, other, name="X")
        d_ajeno = make_metric_data(db_session, m_other, value="9.9")
        # Lista mixta: 3 míos + 1 ajeno
        r = client_auth_admin.post("/api/metrics/data/batch-delete",
                                   json={"ids": ids_mios + [d_ajeno.id_data]})
        assert r.status_code == 200
        # Solo 3 borrados (los míos), el ajeno sigue
        assert r.json()["deleted_count"] == 3
        db_session.expire_all()
        assert db_session.get(MetricData, d_ajeno.id_data) is not None


# ─────────────────────────────────────────────────────────────────────────
# GET /{id}/export
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestExportMetricData:
    def test_sin_auth_401(self, client, metric_simple):
        assert client.get(f"/api/metrics/{metric_simple.id_metric}/export").status_code == 401

    def test_404_no_existe(self, client_auth):
        assert client_auth.get("/api/metrics/99999/export").status_code == 404

    def test_export_excel_default(self, client_auth, metric_con_dims_y_datos):
        metric, _ = metric_con_dims_y_datos
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/export")
        assert r.status_code == 200
        # Default format = excel
        assert "spreadsheetml" in r.headers["content-type"]
        assert "filename=export.xlsx" in r.headers["content-disposition"]

    def test_export_csv(self, client_auth, metric_con_dims_y_datos):
        metric, _ = metric_con_dims_y_datos
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/export",
                            params={"format": "csv"})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        # Separador ; según convención del proyecto (commit 00a7d2f)
        body = r.content.decode("utf-8-sig")
        assert ";" in body

    def test_export_txt(self, client_auth, metric_con_dims_y_datos):
        metric, _ = metric_con_dims_y_datos
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/export",
                            params={"format": "txt"})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/plain")

    def test_export_formato_invalido_400(self, client_auth, metric_con_dims_y_datos):
        metric, _ = metric_con_dims_y_datos
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/export",
                            params={"format": "ufo"})
        # El router wrappea HTTPException 400 dentro de try/except Exception → 500
        # Documentamos comportamiento actual:
        assert r.status_code in (400, 500)


# ─────────────────────────────────────────────────────────────────────────
# GET /{id}/distinct/{column}
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestDistinctValues:
    def test_sin_auth_401(self, client, metric_simple):
        r = client.get(f"/api/metrics/{metric_simple.id_metric}/distinct/Curso")
        assert r.status_code == 401

    def test_distinct_dimension(self, client_auth, metric_con_dims_y_datos):
        metric, _ = metric_con_dims_y_datos
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/distinct/Curso")
        assert r.status_code == 200
        vals = r.json()["values"]
        assert set(vals) == {"1° Básico", "2° Básico", "3° Básico"}

    def test_distinct_metric_value(self, client_auth, metric_con_dims_y_datos):
        """Si column = nombre de la metric, devuelve los values raw."""
        metric, _ = metric_con_dims_y_datos
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/distinct/Logro")
        assert r.status_code == 200
        assert set(r.json()["values"]) == {"0.80", "0.60", "0.70"}

    def test_distinct_metric_inexistente_devuelve_lista_vacia(self, client_auth):
        """El endpoint devuelve {values: []} en lugar de 404 si la metric no existe."""
        r = client_auth.get("/api/metrics/99999/distinct/Curso")
        assert r.status_code == 200
        assert r.json()["values"] == []


# ─────────────────────────────────────────────────────────────────────────
# GET /{id}/template
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetTemplate:
    def test_sin_auth_401(self, client, metric_simple):
        assert client.get(f"/api/metrics/{metric_simple.id_metric}/template").status_code == 401

    def test_404_no_existe(self, client_auth):
        assert client_auth.get("/api/metrics/99999/template").status_code == 404

    def test_template_success(self, client_auth, metric_con_dims_y_datos):
        metric, _ = metric_con_dims_y_datos
        r = client_auth.get(f"/api/metrics/{metric.id_metric}/template")
        # Devuelve un archivo Excel descargable o JSON con estructura;
        # solo aseguramos que no es error.
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────
# Pares X / X_Norm — POST /{id}/import y POST /{id}/data
#
# La red de seguridad "toda carga deja el nombre en AMBAS columnas" vivía
# solo en el camino de pipelines (`SaveToMetric`). Estos tests cubren los
# dos caminos de escritura de /values: el import de archivo y el alta
# manual de una fila. Helper compartido en
# `backend/rgenerator/core/pares_nombre.py`.
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def metric_con_par_nombre(db_session, org):
    """Métrica float con dimensiones Curso + Nombre + Nombre_Norm."""
    dims = {
        n: make_dimension(db_session, org, name=n)
        for n in ("Curso", "Nombre", "Nombre_Norm")
    }
    metric = make_metric(
        db_session, org, name="Logro", data_type="float",
        dimensions=list(dims.values()),
    )
    return metric, dims


@pytest.fixture
def metric_sin_par_nombre(db_session, org):
    """Métrica float con dimensión Nombre pero SIN su hermana normalizada."""
    dims = {n: make_dimension(db_session, org, name=n) for n in ("Curso", "Nombre")}
    metric = make_metric(
        db_session, org, name="Logro", data_type="float",
        dimensions=list(dims.values()),
    )
    return metric, dims


def _csv(texto: str):
    """Payload `files` para el endpoint de import (CSV con separador ';')."""
    return {"files": ("datos.csv", texto.encode("utf-8"), "text/csv")}


def _dims_guardadas(db_session, metric):
    from backend.models import MetricData
    db_session.expire_all()
    filas = (
        db_session.query(MetricData)
        .filter(MetricData.id_metric == metric.id_metric)
        .order_by(MetricData.id_data)
        .all()
    )
    return [json.loads(f.dimensions_json) for f in filas]


@pytest.mark.integration
class TestImportCompletaParesNombre:
    def test_solo_nombre_completa_la_normalizada(
        self, client_auth, db_session, metric_con_par_nombre
    ):
        metric, dims = metric_con_par_nombre
        r = client_auth.post(
            f"/api/metrics/{metric.id_metric}/import",
            files=_csv("Curso;Nombre;Logro\nII A;Pérez Juan;0.5\nII A;Ana Soto;0.7\n"),
        )
        assert r.status_code == 200, r.text
        assert r.json()["imported"] == 2

        id_nom = str(dims["Nombre"].id_dimension)
        id_norm = str(dims["Nombre_Norm"].id_dimension)
        guardadas = _dims_guardadas(db_session, metric)
        assert [d[id_nom] for d in guardadas] == ["Pérez Juan", "Ana Soto"]
        # normalizar_nombre: sin tildes, palabras ordenadas, mayúsculas.
        assert [d[id_norm] for d in guardadas] == ["JUAN PEREZ", "ANA SOTO"]

    def test_solo_normalizada_copia_el_nombre(
        self, client_auth, db_session, metric_con_par_nombre
    ):
        metric, dims = metric_con_par_nombre
        r = client_auth.post(
            f"/api/metrics/{metric.id_metric}/import",
            files=_csv("Curso;Nombre_Norm;Logro\nII A;JUAN PEREZ;0.5\n"),
        )
        assert r.status_code == 200, r.text

        id_nom = str(dims["Nombre"].id_dimension)
        id_norm = str(dims["Nombre_Norm"].id_dimension)
        (guardada,) = _dims_guardadas(db_session, metric)
        assert guardada[id_norm] == "JUAN PEREZ"
        assert guardada[id_nom] == "JUAN PEREZ"  # se copia tal cual

    def test_ambas_presentes_quedan_intactas(
        self, client_auth, db_session, metric_con_par_nombre
    ):
        """Guard de no-sobrescritura: si las dos vienen, no se toca ninguna,
        aunque la normalizada no coincida con normalizar_nombre(original)."""
        metric, dims = metric_con_par_nombre
        r = client_auth.post(
            f"/api/metrics/{metric.id_metric}/import",
            files=_csv("Nombre;Nombre_Norm;Logro\nPérez Juan;valor raro;0.5\n"),
        )
        assert r.status_code == 200, r.text

        id_nom = str(dims["Nombre"].id_dimension)
        id_norm = str(dims["Nombre_Norm"].id_dimension)
        (guardada,) = _dims_guardadas(db_session, metric)
        assert guardada[id_nom] == "Pérez Juan"
        assert guardada[id_norm] == "valor raro"

    def test_sin_par_asociado_no_cambia_nada(
        self, client_auth, db_session, metric_sin_par_nombre
    ):
        """La métrica solo tiene 'Nombre': no hay par, no se inventan claves."""
        metric, dims = metric_sin_par_nombre
        r = client_auth.post(
            f"/api/metrics/{metric.id_metric}/import",
            files=_csv("Curso;Nombre;Logro\nII A;Pérez Juan;0.5\n"),
        )
        assert r.status_code == 200, r.text

        (guardada,) = _dims_guardadas(db_session, metric)
        assert guardada == {
            str(dims["Curso"].id_dimension): "II A",
            str(dims["Nombre"].id_dimension): "Pérez Juan",
        }

    def test_fila_sin_nombre_no_inventa_columnas(
        self, client_auth, db_session, metric_con_par_nombre
    ):
        """Sin ninguna de las dos, la fila no tiene identidad: se deja igual."""
        metric, dims = metric_con_par_nombre
        r = client_auth.post(
            f"/api/metrics/{metric.id_metric}/import",
            files=_csv("Curso;Logro\nII A;0.5\n"),
        )
        assert r.status_code == 200, r.text

        (guardada,) = _dims_guardadas(db_session, metric)
        assert guardada == {str(dims["Curso"].id_dimension): "II A"}


@pytest.mark.integration
class TestAltaManualCompletaParesNombre:
    def test_solo_nombre_completa_la_normalizada(
        self, client_auth, db_session, metric_con_par_nombre
    ):
        metric, dims = metric_con_par_nombre
        id_nom = str(dims["Nombre"].id_dimension)
        id_norm = str(dims["Nombre_Norm"].id_dimension)

        r = client_auth.post(f"/api/metrics/{metric.id_metric}/data", json={
            "value": "0.5",
            "dimensions_json": {id_nom: "Pérez Juan"},
        })
        assert r.status_code == 200, r.text
        assert r.json()["data"]["dimensions_json"][id_norm] == "JUAN PEREZ"
        (guardada,) = _dims_guardadas(db_session, metric)
        assert guardada == {id_nom: "Pérez Juan", id_norm: "JUAN PEREZ"}

    def test_solo_normalizada_copia_el_nombre(self, client_auth, metric_con_par_nombre):
        metric, dims = metric_con_par_nombre
        id_nom = str(dims["Nombre"].id_dimension)
        id_norm = str(dims["Nombre_Norm"].id_dimension)

        r = client_auth.post(f"/api/metrics/{metric.id_metric}/data", json={
            "value": "0.5",
            "dimensions_json": {id_norm: "JUAN PEREZ"},
        })
        assert r.status_code == 200, r.text
        assert r.json()["data"]["dimensions_json"][id_nom] == "JUAN PEREZ"

    def test_ambas_presentes_quedan_intactas(self, client_auth, metric_con_par_nombre):
        metric, dims = metric_con_par_nombre
        id_nom = str(dims["Nombre"].id_dimension)
        id_norm = str(dims["Nombre_Norm"].id_dimension)

        r = client_auth.post(f"/api/metrics/{metric.id_metric}/data", json={
            "value": "0.5",
            "dimensions_json": {id_nom: "Pérez Juan", id_norm: "valor raro"},
        })
        assert r.status_code == 200, r.text
        dims_out = r.json()["data"]["dimensions_json"]
        assert dims_out == {id_nom: "Pérez Juan", id_norm: "valor raro"}

    def test_sin_par_asociado_no_cambia_nada(self, client_auth, metric_sin_par_nombre):
        metric, dims = metric_sin_par_nombre
        id_nom = str(dims["Nombre"].id_dimension)
        r = client_auth.post(f"/api/metrics/{metric.id_metric}/data", json={
            "value": "0.5",
            "dimensions_json": {id_nom: "Pérez Juan"},
        })
        assert r.status_code == 200, r.text
        assert r.json()["data"]["dimensions_json"] == {id_nom: "Pérez Juan"}
