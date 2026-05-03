"""Tests del stub RunDIAPDFExtraction.

El step está intencionalmente sin implementar — registra el nombre en
STEP_MAPPING para reservar el slot, pero ejecutarlo debe lanzar
NotImplementedError con un mensaje claro que apunte al doc de migración.
"""
from __future__ import annotations

import pytest


def test_step_registrado_en_pipeline_mapping():
    from rgenerator.tooling.pipeline_tools import STEP_MAPPING
    assert "RunDIAPDFExtraction" in STEP_MAPPING


def test_run_lanza_not_implemented_con_mensaje_util():
    from rgenerator.core.pdf_steps import RunDIAPDFExtraction

    step = RunDIAPDFExtraction(
        input_key="preguntas_pdf",
        output_key="df_preguntas",
    )
    with pytest.raises(NotImplementedError) as exc_info:
        step.run(ctx=None)
    msg = str(exc_info.value)
    # Debe apuntar al doc de migración para que quien tope con esto sepa
    # adónde ir.
    assert "script_dia_artesanal_referencia" in msg
    assert "B6b" in msg


def test_se_puede_instanciar_sin_args_para_carga_dinamica():
    """El runner instancia con `**params`; debe aceptar kwargs vacíos."""
    from rgenerator.core.pdf_steps import RunDIAPDFExtraction
    step = RunDIAPDFExtraction()
    assert step.name == "RunDIAPDFExtraction"
