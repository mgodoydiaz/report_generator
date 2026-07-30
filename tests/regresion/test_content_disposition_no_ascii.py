"""Regresión: `Content-Disposition` con nombres no-ASCII (RFC 6266/5987).

Starlette codifica las cabeceras en latin-1. Con un indicador llamado con
tilde o ñ ("Cálculo Veloz" existe en la DB canónica), export-pdf emitía
`filename` con bytes no-ASCII: el TestClient reventaba con
UnicodeDecodeError y en un navegador real el nombre llegaba mal
codificado. El fix (`backend.http_utils.content_disposition`) translitera
el fallback ASCII y manda el nombre real en `filename*` percent-encoded.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from backend.http_utils import content_disposition
from tests.factories import make_indicator

FAKE_PDF = b"%PDF-1.4 regresion\n"
LAYOUT = json.dumps({"sections": [{"type": "kpi"}]})


@pytest.mark.unit
class TestContentDispositionHelper:
    def test_ascii_puro_no_agrega_filename_star(self):
        assert content_disposition("informe_SIMCE.pdf") == (
            'attachment; filename="informe_SIMCE.pdf"'
        )

    def test_tilde_se_translitera_y_el_nombre_real_va_en_filename_star(self):
        valor = content_disposition("informe_Cálculo_Veloz.pdf")
        assert 'filename="informe_Calculo_Veloz.pdf"' in valor
        assert "filename*=UTF-8''informe_C%C3%A1lculo_Veloz.pdf" in valor

    def test_enie_se_translitera(self):
        assert 'filename="ano.pdf"' in content_disposition("año.pdf")

    def test_siempre_codificable_en_latin1(self):
        # Es la invariante que Starlette exige: la cabecera nunca revienta,
        # ni siquiera con caracteres sin transliteración ASCII posible.
        content_disposition("Cálculo Veloz ñandú 日本語.pdf").encode("latin-1")

    def test_sin_ningun_caracter_ascii_usa_fallback(self):
        assert 'filename="descarga"' in content_disposition("日本語")

    def test_disposition_inline(self):
        assert content_disposition("a.pdf", disposition="inline").startswith(
            'inline; filename="a.pdf"'
        )


@pytest.mark.integration
class TestExportPDFConNombreConTilde:
    def test_export_pdf_responde_200_y_cabecera_decodificable(
        self, client_auth, db_session, org
    ):
        ind = make_indicator(
            db_session, org, name="Cálculo Veloz",
            pdf_layout=LAYOUT, pdf_layout_historico=LAYOUT,
        )
        with patch(
            "backend.rgenerator.core.report_steps.build_pdf_bytes",
            return_value=FAKE_PDF,
        ):
            resp = client_auth.post(
                f"/api/indicators/{ind.id_indicator}/export-pdf",
                json={"tipo": "evaluacion"},
            )
        assert resp.status_code == 200, resp.text
        cd = resp.headers["content-disposition"]
        cd.encode("latin-1")  # antes reventaba acá con UnicodeDecodeError
        assert 'filename="informe_Calculo_Veloz.pdf"' in cd
        assert "filename*=UTF-8''informe_C%C3%A1lculo_Veloz.pdf" in cd
