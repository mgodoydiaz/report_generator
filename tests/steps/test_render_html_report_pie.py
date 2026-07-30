"""Tests del pie/autor por defecto en el motor HTML de informes.

Ningún informe debe salir con un nombre personal hardcodeado: los esquemas
dejan `leftfooter` / `theauthor` vacíos y el runtime cae al nombre de la
organización dueña de los datos (`resolver_nombre_organizacion`).

Equivalente del motor v2: `tests/reports/test_dispatch_v2.py::TestPieDeOrganizacion`.

WeasyPrint y Jinja2 se stubean para que estos tests corran en cualquier
entorno (WeasyPrint no está instalado en Windows).
"""
from __future__ import annotations

import sys
import types

import pytest

from backend.rgenerator.core.context import RunContext
from backend.rgenerator.core.report_steps import (
    RenderHtmlReport,
    resolver_nombre_organizacion,
)


# ───────────────────────── resolver_nombre_organizacion ──────────────────────


@pytest.mark.unit
class TestResolverNombreOrganizacion:
    def test_sin_sesion_devuelve_default(self):
        assert resolver_nombre_organizacion(None, 1) == ""

    def test_sin_org_id_devuelve_default(self):
        assert resolver_nombre_organizacion(object(), None) == ""

    def test_default_personalizable(self):
        assert resolver_nombre_organizacion(None, None, default="7") == "7"

    def test_query_que_falla_no_rompe(self):
        class _DbRota:
            def query(self, *a, **k):
                raise RuntimeError("sesión cerrada")

        assert resolver_nombre_organizacion(_DbRota(), 1) == ""


@pytest.mark.integration
class TestResolverNombreOrganizacionConDB:
    def test_devuelve_el_nombre_de_la_org(self, db_session, org):
        assert resolver_nombre_organizacion(db_session, org.id) == org.name

    def test_org_inexistente_conserva_default(self, db_session):
        assert resolver_nombre_organizacion(db_session, 999_999) == ""


# ───────────────────────────── stubs de render ───────────────────────────────


@pytest.fixture
def weasyprint_stub(monkeypatch):
    """Reemplaza `weasyprint` por un stub que captura el HTML renderizado."""
    capturado: dict = {}

    class _FakeHTML:
        def __init__(self, string=None, base_url=None):
            capturado["html"] = string
            capturado["base_url"] = base_url

        def write_pdf(self):
            return b"%PDF-stub"

    monkeypatch.setitem(sys.modules, "weasyprint", types.SimpleNamespace(HTML=_FakeHTML))
    return capturado


@pytest.fixture
def jinja_kwargs_stub(monkeypatch):
    """Reemplaza `jinja2.Environment` para capturar los kwargs del render.

    Permite verificar variables que la plantilla actual no imprime (ej.
    `theauthor`, que hoy es metadata no visible).
    """
    import jinja2

    capturado: dict = {}

    class _FakeTemplate:
        def render(self, **kwargs):
            capturado.update(kwargs)
            return "<html></html>"

    class _FakeEnv:
        def __init__(self, *args, **kwargs):
            pass

        def get_template(self, name):
            capturado["_template_name"] = name
            return _FakeTemplate()

    monkeypatch.setattr(jinja2, "Environment", _FakeEnv)
    return capturado


def _ctx(tmp_path, db=None, org_id=None) -> RunContext:
    aux = tmp_path / "aux_files"
    aux.mkdir(parents=True, exist_ok=True)
    out = tmp_path / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return RunContext(
        evaluation="TEST",
        run_id="run-test",
        db=db,
        org_id=org_id,
        base_dir=tmp_path,
        aux_dir=aux,
        outputs_dir=out,
    )


def _schema(**variables) -> dict:
    base = {"documenttitle": "Informe de prueba", "leftfooter": "", "theauthor": ""}
    base.update(variables)
    return {
        "variables_documento": base,
        "secciones_fijas": [],
        "secciones_dinamicas": [],
    }


# ──────────────────────── RenderHtmlReport: pie de página ────────────────────


@pytest.mark.integration
class TestRenderHtmlReportPie:
    def test_pie_vacio_cae_al_nombre_de_la_org(
        self, tmp_path, weasyprint_stub, db_session, org
    ):
        ctx = _ctx(tmp_path, db=db_session, org_id=org.id)
        RenderHtmlReport(report_schema=_schema()).run(ctx)

        assert f'<div class="fb-left">{org.name}</div>' in weasyprint_stub["html"]
        assert ctx.outputs["report_pdf"].exists()

    def test_pie_explicito_gana(self, tmp_path, weasyprint_stub, db_session, org):
        ctx = _ctx(tmp_path, db=db_session, org_id=org.id)
        RenderHtmlReport(report_schema=_schema(leftfooter="Colegio X")).run(ctx)

        assert '<div class="fb-left">Colegio X</div>' in weasyprint_stub["html"]
        assert org.name not in weasyprint_stub["html"]

    def test_sin_db_el_pie_queda_vacio(self, tmp_path, weasyprint_stub):
        ctx = _ctx(tmp_path, db=None, org_id=None)
        RenderHtmlReport(report_schema=_schema()).run(ctx)

        assert '<div class="fb-left"></div>' in weasyprint_stub["html"]

    def test_org_inexistente_el_pie_queda_vacio(
        self, tmp_path, weasyprint_stub, db_session
    ):
        ctx = _ctx(tmp_path, db=db_session, org_id=999_999)
        RenderHtmlReport(report_schema=_schema()).run(ctx)

        assert '<div class="fb-left"></div>' in weasyprint_stub["html"]

    def test_theauthor_tambien_cae_al_nombre_de_la_org(
        self, tmp_path, weasyprint_stub, jinja_kwargs_stub, db_session, org
    ):
        ctx = _ctx(tmp_path, db=db_session, org_id=org.id)
        RenderHtmlReport(report_schema=_schema()).run(ctx)

        assert jinja_kwargs_stub["theauthor"] == org.name
        assert jinja_kwargs_stub["leftfooter"] == org.name

    def test_theauthor_explicito_gana(
        self, tmp_path, weasyprint_stub, jinja_kwargs_stub, db_session, org
    ):
        ctx = _ctx(tmp_path, db=db_session, org_id=org.id)
        RenderHtmlReport(report_schema=_schema(theauthor="Equipo Pedagógico")).run(ctx)

        assert jinja_kwargs_stub["theauthor"] == "Equipo Pedagógico"

    def test_sin_db_theauthor_queda_vacio(
        self, tmp_path, weasyprint_stub, jinja_kwargs_stub
    ):
        ctx = _ctx(tmp_path, db=None, org_id=None)
        RenderHtmlReport(report_schema=_schema()).run(ctx)

        assert jinja_kwargs_stub["theauthor"] == ""
        assert jinja_kwargs_stub["leftfooter"] == ""
