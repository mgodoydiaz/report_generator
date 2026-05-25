"""Tests del router /api/tables y sus helpers puros (B7).

Cubre:
- Validación del schema Pydantic (TableConfig, TableCreate, TableColumn,
  ColorScale variants).
- Helpers `_apply_format` y `_resolve_color_for_value`.

Los tests E2E del CRUD vs DB se hacen vía curl al container Docker
(ver `tests/routers/test_tables_router_e2e.sh` cuando se sumen).
"""
from __future__ import annotations

import pytest

# Tests requieren pydantic + sqlalchemy + fastapi (entorno backend). En la
# env Python 3.13 host esos no están — saltea limpio para que los tests
# del engine/etl se sigan corriendo localmente sin levantar el container.
pytest.importorskip("pydantic")
pytest.importorskip("sqlalchemy")
pytest.importorskip("fastapi")

from pydantic import ValidationError  # noqa: E402

from backend.schemas_table import (  # noqa: E402
    ColorScaleDiverging,
    ColorScaleLinkedIndicator,
    ColorScaleSequential,
    TableColumn,
    TableConfig,
    TableCreate,
    TableDataSource,
    TableUpdate,
)
from backend.routers.tables import _apply_format, _resolve_color_for_value  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────


class TestTableColumn:
    def test_minimal(self):
        c = TableColumn(key="Logro", header="Logro")
        assert c.format == "text"
        assert c.agg is None
        assert c.color_scale is None
        assert c.pinned is False
        assert c.hidden is False

    def test_format_invalido_lanza(self):
        with pytest.raises(ValidationError):
            TableColumn(key="x", header="X", format="weird")

    def test_agg_invalido_lanza(self):
        with pytest.raises(ValidationError):
            TableColumn(key="x", header="X", agg="weird")

    def test_color_scale_linked_indicator(self):
        c = TableColumn(key="Logro", header="Logro", color_scale={
            "kind": "linked_indicator", "indicator_id": 5, "level_field": "Nivel"
        })
        assert isinstance(c.color_scale, ColorScaleLinkedIndicator)
        assert c.color_scale.indicator_id == 5

    def test_color_scale_diverging_defaults(self):
        c = TableColumn(key="Avance", header="Avance", color_scale={"kind": "diverging"})
        assert isinstance(c.color_scale, ColorScaleDiverging)
        assert c.color_scale.midpoint == 0.0
        assert c.color_scale.min_color == "#ef4444"

    def test_color_scale_sequential(self):
        c = TableColumn(key="x", header="X", color_scale={
            "kind": "sequential", "base_color": "#000000"
        })
        assert isinstance(c.color_scale, ColorScaleSequential)


class TestTableConfig:
    def test_minimal_valid(self):
        cfg = TableConfig(data_source={"metric_id": 6})
        assert cfg.version == 1
        assert cfg.data_source.metric_id == 6
        assert cfg.columns == []
        assert cfg.behavior.pagination.page_size == 50

    def test_completo(self):
        cfg = TableConfig(
            data_source={"metric_id": 6, "filters": {"Año": 2026}},
            columns=[
                {"key": "Curso", "header": "Curso", "format": "text"},
                {
                    "key": "Logro", "header": "Logro", "format": "percent",
                    "agg": "mean",
                    "color_scale": {"kind": "linked_indicator",
                                    "indicator_id": 5, "level_field": "Nivel Logro"},
                },
            ],
            behavior={
                "grouping": {"by": "Curso"},
                "sorting": [{"column": "Logro", "dir": "desc"}],
                "pagination": {"page_size": 25},
                "search": False,
            },
        )
        assert len(cfg.columns) == 2
        assert cfg.behavior.grouping.by == "Curso"
        assert cfg.behavior.sorting[0].dir == "desc"
        assert cfg.behavior.pagination.page_size == 25
        assert cfg.behavior.search is False

    def test_metric_id_obligatorio(self):
        with pytest.raises(ValidationError):
            TableConfig(data_source={})

    def test_serializable(self):
        cfg = TableConfig(data_source={"metric_id": 6})
        d = cfg.model_dump()
        assert d["data_source"]["metric_id"] == 6
        # Roundtrip
        cfg2 = TableConfig(**d)
        assert cfg2.data_source.metric_id == 6


class TestTableCreate:
    def test_create_valido(self):
        payload = TableCreate(
            name="Logro DIA Lectura",
            description="Tabla resumen por curso",
            config={"data_source": {"metric_id": 6}},
        )
        assert payload.is_draft is True
        assert payload.config.data_source.metric_id == 6

    def test_name_obligatorio(self):
        with pytest.raises(ValidationError):
            TableCreate(config={"data_source": {"metric_id": 6}})


class TestTableUpdate:
    def test_partial(self):
        upd = TableUpdate(name="Nuevo nombre")
        assert upd.name == "Nuevo nombre"
        assert upd.config is None
        assert upd.is_draft is None


class TestSourceKey:
    """Multi-agg sobre la misma columna fuente (B7 v2)."""

    def test_source_key_default_es_key(self):
        c = TableColumn(key="Logro", header="Logro")
        assert c.source_key is None
        assert c.resolved_source_key() == "Logro"

    def test_source_key_explicito(self):
        c = TableColumn(key="Logro_mean", header="Logro Mean", source_key="Logro", agg="mean")
        assert c.source_key == "Logro"
        assert c.resolved_source_key() == "Logro"
        assert c.key == "Logro_mean"

    def test_multiagg_misma_fuente_distintas_keys(self):
        """3 columnas pueden derivar del mismo Logro con distinto agg."""
        cfg = TableConfig(
            data_source={"metric_id": 6},
            columns=[
                {"key": "Curso", "header": "Curso"},
                {"key": "Logro_mean", "source_key": "Logro", "header": "Mean", "agg": "mean"},
                {"key": "Logro_max", "source_key": "Logro", "header": "Max", "agg": "max"},
                {"key": "Logro_std", "source_key": "Logro", "header": "Std", "agg": "std"},
            ],
            behavior={"grouping": {"by": "Curso"}},
        )
        sources = [c.resolved_source_key() for c in cfg.columns]
        keys = [c.key for c in cfg.columns]
        # 3 fuentes "Logro" pero 3 keys distintas
        assert sources.count("Logro") == 3
        assert len(set(keys)) == len(keys)  # todas únicas

    def test_agg_std_aceptado(self):
        # std no estaba en v1
        c = TableColumn(key="x", header="X", agg="std")
        assert c.agg == "std"


# ─────────────────────────────────────────────────────────────────────────
# Helpers de formato
# ─────────────────────────────────────────────────────────────────────────


class TestApplyFormat:
    def test_text(self):
        assert _apply_format("hola", "text") == "hola"
        assert _apply_format(123, "text") == "123"

    def test_int(self):
        assert _apply_format(42, "int") == "42"
        assert _apply_format(42.7, "int") == "42"
        assert _apply_format("x", "int") == "x"

    def test_float_default_1_decimal(self):
        assert _apply_format(3.14159, "float") == "3.1"
        assert _apply_format(3.14159, "float", decimals=3) == "3.142"

    def test_percent(self):
        assert _apply_format(0.4567, "percent") == "45.7%"
        assert _apply_format(0.5, "percent", decimals=0) == "50%"

    def test_none_y_nan(self):
        import math
        assert _apply_format(None, "percent") == ""
        assert _apply_format(float("nan"), "float") == ""

    def test_date_passthrough(self):
        assert _apply_format("2026-05-04", "date") == "2026-05-04"


# ─────────────────────────────────────────────────────────────────────────
# Color scales
# ─────────────────────────────────────────────────────────────────────────


class TestResolveColor:
    def test_linked_indicator_match(self):
        scale = {"kind": "linked_indicator", "indicator_id": 5, "level_field": "Nivel Logro"}
        cache = {5: [
            {"name": "Inicial",     "color": "#ef4444"},
            {"name": "Intermedio",  "color": "#f59e0b"},
            {"name": "Avanzado",    "color": "#22c55e"},
        ]}
        row = {"Nivel Logro": "Intermedio"}
        assert _resolve_color_for_value(0.5, scale, row, cache) == "#f59e0b"

    def test_linked_indicator_case_insensitive(self):
        scale = {"kind": "linked_indicator", "indicator_id": 5, "level_field": "N"}
        cache = {5: [{"name": "AVANZADO", "color": "#0f0"}]}
        assert _resolve_color_for_value(1, scale, {"N": "avanzado"}, cache) == "#0f0"

    def test_linked_indicator_sin_match(self):
        scale = {"kind": "linked_indicator", "indicator_id": 5, "level_field": "N"}
        cache = {5: [{"name": "X", "color": "#fff"}]}
        assert _resolve_color_for_value(1, scale, {"N": "Z"}, cache) is None

    def test_diverging(self):
        scale = {
            "kind": "diverging", "min_color": "#f00",
            "neutral_color": "#fff", "max_color": "#0f0", "midpoint": 0,
        }
        assert _resolve_color_for_value(-0.1, scale, {}, {}) == "#f00"
        assert _resolve_color_for_value(0, scale, {}, {}) == "#fff"
        assert _resolve_color_for_value(0.1, scale, {}, {}) == "#0f0"

    def test_diverging_midpoint_no_cero(self):
        scale = {"kind": "diverging", "min_color": "#f00",
                 "neutral_color": "#fff", "max_color": "#0f0", "midpoint": 0.5}
        assert _resolve_color_for_value(0.4, scale, {}, {}) == "#f00"
        assert _resolve_color_for_value(0.6, scale, {}, {}) == "#0f0"

    def test_sequential(self):
        scale = {"kind": "sequential", "base_color": "#3b82f6"}
        assert _resolve_color_for_value(0.5, scale, {}, {}) == "#3b82f6"

    def test_nan_devuelve_none(self):
        scale = {"kind": "diverging", "min_color": "#f00",
                 "neutral_color": "#fff", "max_color": "#0f0", "midpoint": 0}
        assert _resolve_color_for_value(None, scale, {}, {}) is None
        assert _resolve_color_for_value(float("nan"), scale, {}, {}) is None


# ═════════════════════════════════════════════════════════════════════════
# Endpoints E2E — agregados en Sprint 5 (cobertura 29% → 70%+)
# ═════════════════════════════════════════════════════════════════════════

import json  # noqa: E402

from tests.factories import (  # noqa: E402
    make_dimension,
    make_metric,
    make_metric_data,
    make_org,
)


# ─────────────────────────────────────────────────────────────────────────
# Fixtures locales
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def metric_con_datos_tabla(db_session, org):
    """Metric 'Logro' (float) + dim 'Curso' + 4 filas. Reutilizable para
    las pruebas del endpoint /data y /preview."""
    dim_curso = make_dimension(db_session, org, name="Curso")
    metric = make_metric(
        db_session, org, name="Logro", data_type="float",
        dimensions=[dim_curso],
    )
    for curso, val in [
        ("1° Básico", "0.80"), ("1° Básico", "0.60"),
        ("2° Básico", "0.70"), ("2° Básico", "0.50"),
    ]:
        make_metric_data(
            db_session, metric, value=val,
            dimensions_json={str(dim_curso.id_dimension): curso},
        )
    return metric


def _spec_tabla(db_session, org, *, metric_id, columns=None, behavior=None):
    """Helper genérico — crea un Spec tipo Tablas con la config dada."""
    from backend.models import Spec
    cfg = {
        "version": 1,
        "data_source": {"metric_id": metric_id, "filters": {},
                        "derived_fields_override": []},
        "columns": columns or [
            {"key": "Curso", "header": "Curso", "format": "text"},
            {"key": "Logro", "header": "Logro", "format": "percent", "decimals": 1},
        ],
        "behavior": behavior or {},
    }
    meta = {"description": "test", "is_draft": True, "updated_at": "2026-01-01"}
    spec = Spec(
        name="Tabla de Prueba",
        type="Tablas",
        metadata_=json.dumps(meta),
        charts_list="[]",
        tables_list=json.dumps([cfg]),
        org_id=org.id,
    )
    db_session.add(spec)
    db_session.commit()
    db_session.refresh(spec)
    return spec


@pytest.fixture
def tabla_creada(db_session, org, metric_con_datos_tabla):
    return _spec_tabla(db_session, org, metric_id=metric_con_datos_tabla.id_metric)


@pytest.fixture
def otra_org_con_tabla(db_session):
    from backend.models import Spec
    other = make_org(db_session, name="Otra Org Tabla")
    cfg = {
        "version": 1,
        "data_source": {"metric_id": 999, "filters": {}, "derived_fields_override": []},
        "columns": [], "behavior": {},
    }
    spec = Spec(
        name="Tabla Otra Org", type="Tablas",
        metadata_=json.dumps({"description": "", "is_draft": True}),
        charts_list="[]", tables_list=json.dumps([cfg]),
        org_id=other.id,
    )
    db_session.add(spec)
    db_session.commit()
    db_session.refresh(spec)
    return other, spec


# ─────────────────────────────────────────────────────────────────────────
# GET /api/tables/  +  POST /api/tables/
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestListTables:
    def test_sin_auth_401(self, client):
        assert client.get("/api/tables/").status_code == 401

    def test_lista_vacia(self, client_auth):
        r = client_auth.get("/api/tables/")
        assert r.status_code == 200
        assert r.json() == []

    def test_lista_devuelve_tablas_de_mi_org(self, client_auth, tabla_creada):
        r = client_auth.get("/api/tables/")
        assert r.status_code == 200
        names = [t["name"] for t in r.json()]
        assert "Tabla de Prueba" in names

    def test_multi_tenancy(self, client_auth, tabla_creada, otra_org_con_tabla):
        r = client_auth.get("/api/tables/")
        names = [t["name"] for t in r.json()]
        assert "Tabla Otra Org" not in names


@pytest.mark.integration
class TestCreateTable:
    def _payload(self, metric_id):
        return {
            "name": "Mi Tabla", "description": "desc",
            "config": {
                "data_source": {"metric_id": metric_id, "filters": {}},
                "columns": [{"key": "Curso", "header": "Curso"}],
            },
        }

    def test_sin_auth_401(self, client, metric_con_datos_tabla):
        r = client.post("/api/tables/", json=self._payload(metric_con_datos_tabla.id_metric))
        assert r.status_code == 401

    def test_crear_basico(self, client_auth, metric_con_datos_tabla):
        r = client_auth.post("/api/tables/", json=self._payload(metric_con_datos_tabla.id_metric))
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "success"
        assert "id_spec" in r.json()

    def test_crear_422_si_falta_metric_id(self, client_auth):
        r = client_auth.post("/api/tables/", json={
            "name": "X", "config": {"data_source": {}, "columns": []},
        })
        assert r.status_code == 422

    def test_crear_422_si_columna_format_invalido(self, client_auth, metric_con_datos_tabla):
        payload = self._payload(metric_con_datos_tabla.id_metric)
        payload["config"]["columns"] = [{"key": "x", "header": "X", "format": "weird"}]
        r = client_auth.post("/api/tables/", json=payload)
        assert r.status_code == 422

    def test_tabla_creada_persiste_org_id(self, client_auth, db_session, org, metric_con_datos_tabla):
        from backend.models import Spec
        r = client_auth.post("/api/tables/", json=self._payload(metric_con_datos_tabla.id_metric))
        sid = r.json()["id_spec"]
        spec = db_session.get(Spec, sid)
        assert spec.org_id == org.id
        assert spec.type == "Tablas"


# ─────────────────────────────────────────────────────────────────────────
# GET /api/tables/{id}, PUT, DELETE, duplicate
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetTable:
    def test_sin_auth_401(self, client, tabla_creada):
        assert client.get(f"/api/tables/{tabla_creada.id_spec}").status_code == 401

    def test_get_exitoso(self, client_auth, tabla_creada):
        r = client_auth.get(f"/api/tables/{tabla_creada.id_spec}")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Tabla de Prueba"
        assert "config" in body

    def test_404_no_existe(self, client_auth):
        assert client_auth.get("/api/tables/99999").status_code == 404

    def test_404_otra_org(self, client_auth, otra_org_con_tabla):
        _, other = otra_org_con_tabla
        assert client_auth.get(f"/api/tables/{other.id_spec}").status_code == 404


@pytest.mark.integration
class TestUpdateTable:
    def test_sin_auth_401(self, client, tabla_creada):
        r = client.put(f"/api/tables/{tabla_creada.id_spec}", json={"name": "X"})
        assert r.status_code == 401

    def test_404_no_existe(self, client_auth):
        r = client_auth.put("/api/tables/99999", json={"name": "X"})
        assert r.status_code == 404

    def test_404_otra_org(self, client_auth, otra_org_con_tabla):
        _, other = otra_org_con_tabla
        r = client_auth.put(f"/api/tables/{other.id_spec}", json={"name": "Hack"})
        assert r.status_code == 404

    def test_update_name(self, client_auth, tabla_creada):
        r = client_auth.put(f"/api/tables/{tabla_creada.id_spec}", json={"name": "Renombrada"})
        assert r.status_code == 200
        assert client_auth.get(f"/api/tables/{tabla_creada.id_spec}").json()["name"] == "Renombrada"

    def test_update_description(self, client_auth, tabla_creada):
        r = client_auth.put(f"/api/tables/{tabla_creada.id_spec}", json={"description": "nueva"})
        assert r.status_code == 200
        assert client_auth.get(f"/api/tables/{tabla_creada.id_spec}").json()["description"] == "nueva"

    def test_update_is_draft(self, client_auth, tabla_creada):
        r = client_auth.put(f"/api/tables/{tabla_creada.id_spec}", json={"is_draft": False})
        assert r.status_code == 200
        assert client_auth.get(f"/api/tables/{tabla_creada.id_spec}").json()["is_draft"] is False

    def test_update_config(self, client_auth, tabla_creada, metric_con_datos_tabla):
        new_cfg = {
            "data_source": {"metric_id": metric_con_datos_tabla.id_metric, "filters": {}},
            "columns": [{"key": "Logro", "header": "Logro", "format": "percent"}],
        }
        r = client_auth.put(f"/api/tables/{tabla_creada.id_spec}", json={"config": new_cfg})
        assert r.status_code == 200
        g = client_auth.get(f"/api/tables/{tabla_creada.id_spec}").json()
        assert len(g["config"]["columns"]) == 1


@pytest.mark.integration
class TestDeleteTable:
    def test_sin_auth_401(self, client, tabla_creada):
        assert client.delete(f"/api/tables/{tabla_creada.id_spec}").status_code == 401

    def test_404_no_existe(self, client_auth):
        assert client_auth.delete("/api/tables/99999").status_code == 404

    def test_404_otra_org(self, client_auth, otra_org_con_tabla):
        _, other = otra_org_con_tabla
        assert client_auth.delete(f"/api/tables/{other.id_spec}").status_code == 404

    def test_delete_exitoso(self, client_auth, tabla_creada):
        sid = tabla_creada.id_spec
        assert client_auth.delete(f"/api/tables/{sid}").status_code == 200
        assert client_auth.get(f"/api/tables/{sid}").status_code == 404


@pytest.mark.integration
class TestDuplicateTable:
    def test_sin_auth_401(self, client, tabla_creada):
        r = client.post(f"/api/tables/{tabla_creada.id_spec}/duplicate")
        assert r.status_code == 401

    def test_404_no_existe(self, client_auth):
        r = client_auth.post("/api/tables/99999/duplicate")
        assert r.status_code == 404

    def test_duplicate_exitoso_con_sufijo(self, client_auth, tabla_creada):
        r = client_auth.post(f"/api/tables/{tabla_creada.id_spec}/duplicate")
        assert r.status_code == 200
        new_id = r.json()["id_spec"]
        assert new_id != tabla_creada.id_spec
        copia = client_auth.get(f"/api/tables/{new_id}").json()
        assert copia["name"] == "Tabla de Prueba (Copia)"


# ─────────────────────────────────────────────────────────────────────────
# GET /api/tables/{id}/data  +  POST /api/tables/preview
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetTableData:
    def test_sin_auth_401(self, client, tabla_creada):
        assert client.get(f"/api/tables/{tabla_creada.id_spec}/data").status_code == 401

    def test_404_no_existe(self, client_auth):
        assert client_auth.get("/api/tables/99999/data").status_code == 404

    def test_404_otra_org(self, client_auth, otra_org_con_tabla):
        _, other = otra_org_con_tabla
        assert client_auth.get(f"/api/tables/{other.id_spec}/data").status_code == 404

    def test_data_success(self, client_auth, tabla_creada):
        r = client_auth.get(f"/api/tables/{tabla_creada.id_spec}/data")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "rows" in body and "columns" in body
        assert body["total_rows"] == 4
        assert body["limit"] == 50

    def test_data_limit_y_offset(self, client_auth, tabla_creada):
        r = client_auth.get(f"/api/tables/{tabla_creada.id_spec}/data",
                            params={"limit": 2, "offset": 1})
        assert r.status_code == 200
        body = r.json()
        assert body["limit"] == 2
        assert body["offset"] == 1
        assert len(body["rows"]) == 2

    def test_data_include_styles_false(self, client_auth, tabla_creada):
        r = client_auth.get(f"/api/tables/{tabla_creada.id_spec}/data",
                            params={"include_styles": "false"})
        assert r.status_code == 200

    def test_data_extra_filters_aplica(self, client_auth, tabla_creada):
        filt = json.dumps({"Curso": "1° Básico"})
        r = client_auth.get(f"/api/tables/{tabla_creada.id_spec}/data",
                            params={"extra_filters": filt})
        assert r.status_code == 200
        assert r.json()["total_rows"] == 2

    def test_data_extra_filters_invalido_se_ignora(self, client_auth, tabla_creada):
        r = client_auth.get(f"/api/tables/{tabla_creada.id_spec}/data",
                            params={"extra_filters": "{not-json"})
        assert r.status_code == 200

    def test_400_si_tables_list_vacia(self, client_auth, db_session, org):
        from backend.models import Spec
        spec = Spec(
            name="Empty", type="Tablas",
            metadata_=json.dumps({}), charts_list="[]", tables_list="[]",
            org_id=org.id,
        )
        db_session.add(spec)
        db_session.commit()
        db_session.refresh(spec)
        r = client_auth.get(f"/api/tables/{spec.id_spec}/data")
        assert r.status_code == 400

    def test_422_limit_fuera_de_rango(self, client_auth, tabla_creada):
        """Query param limit tiene ge=1 le=2000."""
        r = client_auth.get(f"/api/tables/{tabla_creada.id_spec}/data",
                            params={"limit": 5000})
        assert r.status_code == 422


@pytest.mark.integration
class TestGetTableDataConGrouping:
    """Behavior.grouping reduce filas y aplica agg por columna."""

    def test_grouping_por_curso_mean(self, client_auth, db_session, org, metric_con_datos_tabla):
        spec = _spec_tabla(
            db_session, org, metric_id=metric_con_datos_tabla.id_metric,
            columns=[
                {"key": "Curso", "header": "Curso", "format": "text"},
                {"key": "Logro", "header": "Logro", "format": "percent", "agg": "mean"},
            ],
            behavior={"grouping": {"by": "Curso"}},
        )
        r = client_auth.get(f"/api/tables/{spec.id_spec}/data")
        assert r.status_code == 200, r.text
        # 4 filas raw → 2 cursos
        assert r.json()["total_rows"] == 2

    def test_sorting_desc_por_logro(self, client_auth, db_session, org, metric_con_datos_tabla):
        spec = _spec_tabla(
            db_session, org, metric_id=metric_con_datos_tabla.id_metric,
            columns=[
                {"key": "Curso", "header": "Curso"},
                {"key": "Logro", "header": "Logro", "format": "percent"},
            ],
            behavior={"sorting": [{"column": "Logro", "dir": "desc"}]},
        )
        r = client_auth.get(f"/api/tables/{spec.id_spec}/data")
        assert r.status_code == 200
        rows = r.json()["rows"]
        # Primera fila debería ser la de Logro más alto (0.80)
        first_row_logro = rows[0].get("Logro", "")
        # Como format=percent, queda "80.0%" — extraemos solo el número
        assert "80" in str(first_row_logro)


@pytest.mark.integration
class TestPreviewTable:
    def test_sin_auth_401(self, client):
        r = client.post("/api/tables/preview", json={
            "config": {"data_source": {"metric_id": 1}, "columns": []},
        })
        assert r.status_code == 401

    def test_preview_success(self, client_auth, metric_con_datos_tabla):
        r = client_auth.post("/api/tables/preview", json={
            "config": {
                "data_source": {"metric_id": metric_con_datos_tabla.id_metric, "filters": {}},
                "columns": [
                    {"key": "Curso", "header": "Curso"},
                    {"key": "Logro", "header": "Logro", "format": "percent"},
                ],
            },
        })
        assert r.status_code == 200, r.text
        assert r.json()["total_rows"] == 4

    def test_preview_422_config_invalida(self, client_auth):
        """Sin metric_id en data_source → 422."""
        r = client_auth.post("/api/tables/preview", json={
            "config": {"data_source": {}, "columns": []},
        })
        assert r.status_code == 422

    def test_preview_con_extra_filters(self, client_auth, metric_con_datos_tabla):
        r = client_auth.post("/api/tables/preview", json={
            "config": {
                "data_source": {"metric_id": metric_con_datos_tabla.id_metric, "filters": {}},
                "columns": [{"key": "Logro", "header": "Logro"}],
            },
            "extra_filters": {"Curso": "1° Básico"},
        })
        assert r.status_code == 200
        assert r.json()["total_rows"] == 2

    def test_preview_con_limit_offset(self, client_auth, metric_con_datos_tabla):
        r = client_auth.post("/api/tables/preview", json={
            "config": {
                "data_source": {"metric_id": metric_con_datos_tabla.id_metric, "filters": {}},
                "columns": [{"key": "Logro", "header": "Logro"}],
            },
            "limit": 2, "offset": 0,
        })
        assert r.status_code == 200
        assert r.json()["limit"] == 2
