"""Tests del registro de informes custom y de POST /api/reports/custom/{nombre}.

El registro se auto-descubre con `pkgutil` sobre
`backend/rgenerator/reports/custom/`. Los tests del endpoint mockean
`generar` para no requerir weasyprint/matplotlib.
"""
from __future__ import annotations

from types import ModuleType
from unittest.mock import patch

import pytest

from backend.rgenerator.reports import custom as custom_reports
from tests.factories import make_indicator, make_org


@pytest.mark.unit
class TestRegistry:
    def test_descubre_los_cuatro_informes_iniciales(self):
        registry = custom_reports.get_registry(refresh=True)
        assert set(registry) == {"simce", "simce_panguipulli", "dia", "pdl_idel"}

    def test_modulos_con_underscore_no_se_registran(self):
        # _ejemplo.py existe en la carpeta pero es plantilla, no informe
        assert "_ejemplo" not in custom_reports.get_registry()

    def test_todos_exponen_generar_callable(self):
        for nombre, mod in custom_reports.get_registry().items():
            assert callable(getattr(mod, "generar", None)), nombre

    def test_listar_informes_trae_metadata_completa(self):
        informes = {i["nombre"]: i for i in custom_reports.listar_informes()}
        pdl = informes["pdl_idel"]
        assert pdl["label"] == "Informe PDL IDEL-Woodcock"
        assert pdl["descripcion"]
        assert pdl["formato"] == "pdf"
        assert pdl["mime"] == "application/pdf"
        assert pdl["engine_types"] == ["pdl_idel"]
        assert pdl["requiere_filtro_temporal"] == []
        assert pdl["filename"] == "informe_pdl_idel.pdf"

    def test_orden_alfabetico(self):
        nombres = [i["nombre"] for i in custom_reports.listar_informes()]
        assert nombres == sorted(nombres)

    def test_filtros_temporales_por_tipo(self):
        informes = {i["nombre"]: i for i in custom_reports.listar_informes()}
        assert informes["simce"]["requiere_filtro_temporal"] == ["Mes", "N Prueba", "Numero_Prueba"]
        assert informes["simce_panguipulli"]["requiere_filtro_temporal"] == ["Mes", "N Prueba", "Numero_Prueba"]
        assert informes["dia"]["requiere_filtro_temporal"] == ["Hito", "Año"]

    def test_obtener_modulo_inexistente_levanta_keyerror_util(self):
        with pytest.raises(KeyError) as exc:
            custom_reports.obtener_modulo("no_existe")
        assert "no registrado" in str(exc.value)
        assert "simce" in str(exc.value)

    def test_aplica_a_filtra_por_engine_type(self):
        pdl = custom_reports.obtener_modulo("pdl_idel")
        assert custom_reports.aplica_a(pdl, "pdl_idel") is True
        assert custom_reports.aplica_a(pdl, "simce") is False
        assert custom_reports.aplica_a(pdl, None) is False

    def test_engine_types_none_aplica_a_todos(self):
        universal = ModuleType("universal")
        universal.generar = lambda *a, **k: b""
        universal.ENGINE_TYPES = None
        assert custom_reports.aplica_a(universal, None) is True
        assert custom_reports.aplica_a(universal, "cualquiera") is True

    def test_informes_para_engine_type(self):
        nombres = [i["nombre"] for i in custom_reports.informes_para("dia")]
        assert nombres == ["dia"]
        assert custom_reports.informes_para(None) == []

    def test_filename_default_cuando_no_se_declara(self):
        mod = ModuleType("sin_filename")
        mod.generar = lambda *a, **k: b""
        assert custom_reports.nombre_archivo("sin_filename", mod) == "informe_sin_filename.pdf"
        mod.FORMATO = "word"
        assert custom_reports.nombre_archivo("sin_filename", mod) == "informe_sin_filename.docx"

    def test_modulo_sin_generar_se_ignora(self, monkeypatch, capsys):
        """Un módulo sin `generar` no entra al registro (y avisa por consola)."""
        import importlib

        real_import = importlib.import_module

        def fake_import(nombre, *a, **k):
            mod = real_import(nombre, *a, **k)
            if nombre.endswith(".dia"):
                falso = ModuleType(nombre)
                falso.LABEL = "roto"
                return falso
            return mod

        monkeypatch.setattr(importlib, "import_module", fake_import)
        registry = custom_reports.get_registry(refresh=True)
        assert "dia" not in registry
        assert "simce" in registry  # los demás siguen registrados
        assert "sin generar()" in capsys.readouterr().out
        # Restaurar el registro real para los siguientes tests
        monkeypatch.undo()
        custom_reports.get_registry(refresh=True)

    def test_modulo_roto_no_tumba_el_resto(self, monkeypatch, capsys):
        import importlib

        real_import = importlib.import_module

        def fake_import(nombre, *a, **k):
            if nombre.endswith(".simce"):
                raise ImportError("dependencia faltante de prueba")
            return real_import(nombre, *a, **k)

        monkeypatch.setattr(importlib, "import_module", fake_import)
        registry = custom_reports.get_registry(refresh=True)
        assert "simce" not in registry
        assert "pdl_idel" in registry
        assert "no importable" in capsys.readouterr().out
        monkeypatch.undo()
        custom_reports.get_registry(refresh=True)


@pytest.mark.integration
class TestEndpointCustom:
    def test_listado_requiere_auth(self, client):
        assert client.get("/api/reports/custom/informes").status_code == 401

    def test_listado_ok(self, client_auth):
        r = client_auth.get("/api/reports/custom/informes")
        assert r.status_code == 200
        assert {i["nombre"] for i in r.json()} == {
            "simce", "simce_panguipulli", "dia", "pdl_idel"
        }

    def test_nombre_no_registrado_404(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="X", report_engine_type="dia")
        r = client_auth.post("/api/reports/custom/inventado", json={
            "indicator_id": ind.id_indicator,
        })
        assert r.status_code == 404
        assert "no registrado" in r.json()["detail"]

    def test_indicador_de_otra_org_404(self, client_auth, db_session):
        otra = make_org(db_session, name="Org Ajena Custom")
        ajeno = make_indicator(db_session, otra, name="Ajeno DIA", report_engine_type="dia")
        r = client_auth.post("/api/reports/custom/dia", json={
            "indicator_id": ajeno.id_indicator,
        })
        assert r.status_code == 404

    def test_engine_type_incompatible_400(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Lectura IDEL", report_engine_type="pdl_idel")
        r = client_auth.post("/api/reports/custom/dia", json={
            "indicator_id": ind.id_indicator,
        })
        assert r.status_code == 400
        detalle = r.json()["detail"]
        assert "no aplica" in detalle
        assert "pdl_idel" in detalle

    def test_ok_devuelve_binario_con_filename_del_modulo(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="DIA Lectura", report_engine_type="dia")
        fake = b"%PDF-1.4 custom\n"
        with patch(
            "backend.rgenerator.reports.custom.dia.generar", return_value=fake
        ):
            r = client_auth.post("/api/reports/custom/dia", json={
                "indicator_id": ind.id_indicator,
                "filtros": {"Hito": "CIERRE"},
            })
        assert r.status_code == 200, r.text
        assert r.content == fake
        assert r.headers["content-type"] == "application/pdf"
        assert "informe_dia.pdf" in r.headers["content-disposition"]

    def test_valueerror_del_informe_es_400(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="DIA Lectura", report_engine_type="dia")
        with patch(
            "backend.rgenerator.reports.custom.dia.generar",
            side_effect=ValueError("El indicator DIA debe tener metrics asociadas"),
        ):
            r = client_auth.post("/api/reports/custom/dia", json={
                "indicator_id": ind.id_indicator,
            })
        assert r.status_code == 400
        assert "metrics" in r.json()["detail"]

    def test_error_inesperado_es_500_saneado(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="DIA Lectura", report_engine_type="dia")
        with patch(
            "backend.rgenerator.reports.custom.dia.generar",
            side_effect=RuntimeError("stack interno con detalles sensibles"),
        ):
            r = client_auth.post("/api/reports/custom/dia", json={
                "indicator_id": ind.id_indicator,
            })
        assert r.status_code == 500
        assert "sensibles" not in r.json()["detail"]

    def test_engine_type_inferido_por_nombre_habilita_el_informe(self, client_auth, db_session, org):
        """Sin report_engine_type explícito, la heurística por nombre decide."""
        ind = make_indicator(db_session, org, name="SIMCE Lenguaje 2026")
        with patch(
            "backend.rgenerator.reports.custom.simce.generar", return_value=b"%PDF-1.4\n"
        ):
            r = client_auth.post("/api/reports/custom/simce", json={
                "indicator_id": ind.id_indicator,
                "filtros": {"Mes": "ABRIL"},
            })
        assert r.status_code == 200, r.text
