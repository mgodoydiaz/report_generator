"""Tests del despacho por modos (contrato del motor único, §2 y plan §5.2).

Cubre los dos endpoints que cambian:

    GET  /api/indicators/{id}/report-options  → campo `motor` de las cards
    POST /api/indicators/{id}/export-pdf      → despacho al módulo custom

y el blindaje del punto delicado de §2.3: los módulos reciben los filtros
por NOMBRE DE COLUMNA ("Mes", "Año", "Asignatura"), nunca por id de
dimensión — con ids `data.py` armaría columnas `_12` y el informe saldría
silenciosamente vacío.
"""
from __future__ import annotations

import json
from types import ModuleType
from unittest.mock import patch

import pytest

from tests.factories import (
    make_dimension, make_indicator, make_metric, make_metric_data,
)

FAKE_PDF = b"%PDF-1.4 despacho\n"
LAYOUT = json.dumps({"sections": [{"type": "kpi"}], "branding": {
    "center_header": ["Fundación PHP", "Octubre 2020"],
}})


def _cards(client_auth, indicator_id) -> dict:
    body = client_auth.get(f"/api/indicators/{indicator_id}/report-options").json()
    return {c["id"]: c for c in body["grupos"]["periodo"]}


@pytest.fixture
def indicador_sin_modulo(db_session, org):
    """Indicador genérico (sin engine_type ni nombre que lo infiera)."""
    dims = {n: make_dimension(db_session, org, name=n)
            for n in ("Curso", "Año", "Mes")}
    metric = make_metric(
        db_session, org, name="Resultados por Estudiante", data_type="object",
        fields=[{"name": "Logro", "type": "float"}], dimensions=list(dims.values()),
    )
    ident = {n: str(d.id_dimension) for n, d in dims.items()}
    from datetime import date
    from backend.rgenerator.reports.periodos import NUMERO_A_MES
    hoy = date.today()
    make_metric_data(db_session, metric, value={"Logro": 0.5}, dimensions_json={
        ident["Curso"]: "II A", ident["Año"]: str(hoy.year),
        ident["Mes"]: NUMERO_A_MES[hoy.month],
    })
    return make_indicator(
        # Nombre ASCII a propósito: `Content-Disposition` se emite en
        # latin-1 y un nombre con tilde revienta el TestClient (bug
        # preexistente del endpoint, ajeno a este piloto).
        db_session, org, name="Ensayo Generico", metrics=[metric],
        pdf_layout=LAYOUT, pdf_layout_historico=LAYOUT,
    )


@pytest.fixture
def modulo_parcial(monkeypatch):
    """Registro custom reemplazado por un módulo que NO sirve `semestral`.

    Es el caso de IDEL (decisión 7): 3 versiones anuales que no se reparten
    por semestre. Se simula acá porque en el piloto solo SIMCE declara
    `MODOS`.
    """
    from backend.rgenerator.reports import custom as custom_reports

    stub = ModuleType("backend.rgenerator.reports.custom.stub_parcial")
    stub.LABEL = "Informe stub"
    stub.DESCRIPCION = "stub"
    stub.FORMATO = "pdf"
    stub.ENGINE_TYPES = ["simce"]
    stub.MODOS = ["ultima_prueba", "anual", "personalizado"]
    stub.MOTIVO_MODO_NO_DISPONIBLE = {
        "semestral": "Este instrumento no se reparte por semestre.",
    }
    stub.generar = lambda *a, **k: FAKE_PDF

    monkeypatch.setattr(custom_reports, "_registry", {"stub_parcial": stub})
    yield stub


# ─────────────────────────────────────────────────────────────────────────
# report-options: campo `motor` y motivos
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestReportOptionsConModulo:
    def test_indicador_con_modulo_marca_el_motor(
        self, client_auth, simce_indicator_historico
    ):
        cards = _cards(client_auth, simce_indicator_historico.id_indicator)
        for card in cards.values():
            assert card["motor"] == "custom:simce"

    def test_indicador_sin_modulo_sigue_en_weasyprint(
        self, client_auth, indicador_sin_modulo
    ):
        cards = _cards(client_auth, indicador_sin_modulo.id_indicator)
        for card in cards.values():
            assert card["motor"] == "weasyprint"

    def test_sin_modulo_el_pdf_layout_sigue_siendo_requisito(
        self, client_auth, db_session, org
    ):
        ind = make_indicator(db_session, org, name="Ensayo Sin Layout")
        cards = _cards(client_auth, ind.id_indicator)
        assert cards["periodo_ultima_prueba"]["disponible"] is False
        assert "Editor de Layout" in cards["periodo_ultima_prueba"]["motivo_no_disponible"]

    def test_con_modulo_las_4_cards_salen_sin_pdf_layout(
        self, client_auth, simce_indicator_historico, db_session
    ):
        """Regresión del hueco 0/4 del inventario: el módulo trae sus secciones."""
        simce_indicator_historico.pdf_layout = "{}"
        simce_indicator_historico.pdf_layout_historico = "{}"
        db_session.commit()
        cards = _cards(client_auth, simce_indicator_historico.id_indicator)
        for cid in ("periodo_ultima_prueba", "periodo_semestral",
                    "periodo_anual", "periodo_personalizado"):
            assert cards[cid]["disponible"] is True, cards[cid]["motivo_no_disponible"]

    def test_modo_no_declarado_deshabilita_la_card_con_motivo(
        self, client_auth, simce_indicator_historico, modulo_parcial
    ):
        cards = _cards(client_auth, simce_indicator_historico.id_indicator)
        semestral = cards["periodo_semestral"]
        assert semestral["motor"] == "custom:stub_parcial"
        assert semestral["disponible"] is False
        assert semestral["motivo_no_disponible"] == (
            modulo_parcial.MOTIVO_MODO_NO_DISPONIBLE["semestral"]
        )
        assert cards["periodo_anual"]["disponible"] is True


# ─────────────────────────────────────────────────────────────────────────
# export-pdf: despacho al módulo
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestExportPDFDelegaAlModulo:
    def _exportar(self, client_auth, indicator_id, body):
        with patch(
            "backend.rgenerator.reports.custom.simce.generar",
            return_value=FAKE_PDF,
        ) as mock:
            resp = client_auth.post(
                f"/api/indicators/{indicator_id}/export-pdf", json=body
            )
        return resp, mock

    def test_delega_con_el_modo_correcto(self, client_auth, simce_indicator_historico):
        resp, mock = self._exportar(
            client_auth, simce_indicator_historico.id_indicator,
            {"periodo": {"tipo": "anual", "filtros": {"Asignatura": "Lenguaje"}}},
        )
        assert resp.status_code == 200, resp.text
        assert resp.content == FAKE_PDF
        assert mock.call_args.kwargs["modo"] == "anual"

    def test_los_filtros_van_por_nombre_de_columna(
        self, client_auth, simce_indicator_historico
    ):
        """§2.3: con ids de dimensión el informe saldría vacío en silencio."""
        from datetime import date
        _, mock = self._exportar(
            client_auth, simce_indicator_historico.id_indicator,
            {"periodo": {"tipo": "ultima_prueba",
                         "filtros": {"Asignatura": "Lenguaje"}}},
        )
        filtros = mock.call_args.kwargs["filtros"]
        assert filtros["Asignatura"] == "Lenguaje"
        assert filtros["Mes"] == "MAYO"
        assert filtros["Año"] == str(date.today().year)
        # Ninguna clave es un id de dimensión
        assert not [k for k in filtros if str(k).isdigit()]

    def test_filtros_del_body_por_id_se_traducen(
        self, client_auth, db_session, simce_indicator_historico
    ):
        from backend.models import Dimension
        dim = db_session.query(Dimension).filter(
            Dimension.name == "Asignatura",
            Dimension.org_id == simce_indicator_historico.org_id,
        ).first()
        _, mock = self._exportar(
            client_auth, simce_indicator_historico.id_indicator,
            {"filters": {str(dim.id_dimension): "Lenguaje"},
             "periodo": {"tipo": "anual"}},
        )
        assert mock.call_args.kwargs["filtros"]["Asignatura"] == "Lenguaje"

    def test_el_encabezado_lleva_el_periodo_resuelto(
        self, client_auth, simce_indicator_historico, db_session
    ):
        simce_indicator_historico.pdf_layout_historico = LAYOUT
        db_session.commit()
        _, mock = self._exportar(
            client_auth, simce_indicator_historico.id_indicator,
            {"periodo": {"tipo": "anual", "filtros": {"Asignatura": "Lenguaje"}}},
        )
        header = mock.call_args.kwargs["overrides"]["branding"]["center_header"]
        assert header[0] == "Fundación PHP"
        assert header[-1] != "Octubre 2020"     # la línea stale se reemplaza

    def test_modo_no_soportado_400(
        self, client_auth, simce_indicator_historico, modulo_parcial
    ):
        resp = client_auth.post(
            f"/api/indicators/{simce_indicator_historico.id_indicator}/export-pdf",
            json={"periodo": {"tipo": "semestral"}},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == (
            modulo_parcial.MOTIVO_MODO_NO_DISPONIBLE["semestral"]
        )

    def test_datos_insuficientes_da_400_con_el_texto(
        self, client_auth, simce_indicator_historico
    ):
        from backend.rgenerator.reports.errores import DatosInsuficientes
        with patch(
            "backend.rgenerator.reports.custom.simce.generar",
            side_effect=DatosInsuficientes("No hay datos de MARZO."),
        ):
            resp = client_auth.post(
                f"/api/indicators/{simce_indicator_historico.id_indicator}/export-pdf",
                json={"periodo": {"tipo": "anual",
                                  "filtros": {"Asignatura": "Lenguaje"}}},
            )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "No hay datos de MARZO."

    def test_error_inesperado_da_500_saneado(
        self, client_auth, simce_indicator_historico
    ):
        with patch(
            "backend.rgenerator.reports.custom.simce.generar",
            side_effect=RuntimeError("stack interno"),
        ):
            resp = client_auth.post(
                f"/api/indicators/{simce_indicator_historico.id_indicator}/export-pdf",
                json={"periodo": {"tipo": "anual",
                                  "filtros": {"Asignatura": "Lenguaje"}}},
            )
        assert resp.status_code == 500
        assert "stack interno" not in resp.text

    def test_sin_periodo_no_hay_despacho(
        self, client_auth, simce_indicator_historico, db_session
    ):
        """El body legacy (`tipo` + `filters`) sigue yendo por el motor v1."""
        simce_indicator_historico.pdf_layout = LAYOUT
        db_session.commit()
        with patch(
            "backend.rgenerator.core.report_steps.build_pdf_bytes",
            return_value=FAKE_PDF,
        ) as v1, patch(
            "backend.rgenerator.reports.custom.simce.generar",
        ) as modulo:
            resp = client_auth.post(
                f"/api/indicators/{simce_indicator_historico.id_indicator}/export-pdf",
                json={"tipo": "evaluacion"},
            )
        assert resp.status_code == 200, resp.text
        assert v1.called and not modulo.called


# ─────────────────────────────────────────────────────────────────────────
# Fallback v1 intacto
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestFallbackV1:
    def test_indicador_sin_modulo_usa_build_pdf_bytes(
        self, client_auth, indicador_sin_modulo
    ):
        with patch(
            "backend.rgenerator.core.report_steps.build_pdf_bytes",
            return_value=FAKE_PDF,
        ) as mock:
            resp = client_auth.post(
                f"/api/indicators/{indicador_sin_modulo.id_indicator}/export-pdf",
                json={"periodo": {"tipo": "anual"}},
            )
        assert resp.status_code == 200, resp.text
        assert mock.called

    def test_engine_explicito_gana_sobre_el_modulo(
        self, client_auth, simce_indicator_historico, db_session
    ):
        """§2.2: `body.engine` es un override consciente para comparar v1."""
        simce_indicator_historico.pdf_layout_historico = LAYOUT
        db_session.commit()
        with patch(
            "backend.rgenerator.core.report_steps.build_pdf_bytes",
            return_value=FAKE_PDF,
        ) as v1, patch(
            "backend.rgenerator.reports.custom.simce.generar",
        ) as modulo:
            resp = client_auth.post(
                f"/api/indicators/{simce_indicator_historico.id_indicator}/export-pdf",
                json={"engine": "weasyprint",
                      "periodo": {"tipo": "anual",
                                  "filtros": {"Asignatura": "Lenguaje"}}},
            )
        assert resp.status_code == 200, resp.text
        assert v1.called and not modulo.called


# ─────────────────────────────────────────────────────────────────────────
# Retrocompatibilidad del informe "formato oficial"
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestRetrocompatFormatoOficial:
    def test_reports_custom_simce_no_manda_modo(self, client_auth, simce_indicator):
        """`POST /api/reports/custom/simce` sigue produciendo el informe de hoy."""
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            return_value=b"%PDF-1.4\n",
        ) as mock:
            resp = client_auth.post("/api/reports/custom/simce", json={
                "indicator_id": simce_indicator.id_indicator,
                "filtros": {"Mes": "ABRIL"},
            })
        assert resp.status_code == 200, resp.text
        # El camino clásico lee el esquema de disco: NO pasa `esquema`.
        assert "esquema" not in mock.call_args.kwargs

    def test_metadata_suma_las_dos_claves_nuevas(self):
        from backend.rgenerator.reports import custom as custom_reports
        meta = custom_reports.metadata("simce")
        assert meta["modos"] == ["ultima_prueba", "semestral", "anual", "personalizado"]
        assert meta["motivos_modo"] == {}

    def test_modulo_sin_modos_no_cambia_de_comportamiento(self):
        from backend.rgenerator.reports import custom as custom_reports
        meta = custom_reports.metadata("dia")
        assert meta["modos"] == []
        assert custom_reports.soporta_modo(
            custom_reports.obtener_modulo("dia"), "anual"
        ) is False


@pytest.mark.unit
class TestHelpersDelRegistro:
    def test_soporta_modo_con_none_es_false(self):
        from backend.rgenerator.reports import custom as custom_reports
        from backend.rgenerator.reports.custom import simce
        assert custom_reports.soporta_modo(simce, None) is False
        assert custom_reports.soporta_modo(simce, "anual") is True

    def test_motivo_generico_cuando_el_modulo_no_lo_explica(self):
        from backend.rgenerator.reports import custom as custom_reports
        from backend.rgenerator.reports.custom import simce
        assert custom_reports.motivo_modo(simce, "trimestral") == (
            custom_reports.MOTIVO_MODO_GENERICO
        )

    def test_modulo_de_indicador_sin_engine_type(self):
        from backend.rgenerator.reports import custom as custom_reports
        assert custom_reports.modulo_de_indicador(None) is None
        assert custom_reports.modulo_de_indicador("calculo_veloz") is None

    def test_modulo_de_indicador_simce(self):
        from backend.rgenerator.reports import custom as custom_reports
        mod = custom_reports.modulo_de_indicador("simce")
        assert custom_reports.nombre_de(mod) == "simce"
