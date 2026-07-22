"""Regresión: hallazgos P0 del QA maestro de dev3 (docs/qa/QA_MAESTRO.md).

P0-4 — Los errores de un step de pipeline llegaban al usuario aplastados
       como "Error interno del servidor" (routers/pipelines.py). Fix:
       PipelineRunner.step() envuelve el fallo en StepExecutionError y el
       router lo devuelve con el mensaje original del step (que suele ser
       accionable), reservando el mensaje genérico para errores no
       controlados.

P0-5 — routers/reports.py usaba `traceback.print_exc()` sin importar
       `traceback` → NameError enmascaraba el error real del informe Word
       y el detalle interno (`{tipo}: {mensaje}`) se filtraba en el 500.
       Fix: logger.error(exc_info=True) + mensaje genérico en el detail.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

# NOTA: importar desde `rgenerator.*` (no `backend.rgenerator.*`): el paquete
# es importable por ambas rutas y Python crea DOS instancias de módulo — las
# clases de excepción solo coinciden si usamos la misma ruta que usa el código
# de producción (pipeline_tools y routers usan `rgenerator.*`).
from rgenerator.core.step import Step, StepExecutionError, WaitingForInputException
from rgenerator.tooling import pipeline_tools
from rgenerator.tooling.pipeline_tools import PipelineRunner


@dataclass
class _BoomStep(Step):
    """Step de prueba que falla como fallaría un ETL con datos malos."""

    name: str = "boom"

    def run(self, ctx):
        raise ValueError("Columna llave 'RUT' no existe en 'estudiantes'")


@dataclass
class _WaitingStep(Step):
    name: str = "waiting"

    def run(self, ctx):
        raise WaitingForInputException("waiting", {"files": ["estudiantes"]})


def _runner_con(step: Step) -> PipelineRunner:
    runner = PipelineRunner({"pipeline": []}, org_id=1)
    runner.pipeline = [step]
    runner.total_steps = 1
    return runner


@pytest.mark.unit
class TestStepExecutionError:
    def test_fallo_de_step_envuelve_excepcion_original(self):
        """El mensaje accionable del step debe viajar en la excepción."""
        runner = _runner_con(_BoomStep())
        with pytest.raises(StepExecutionError) as exc:
            runner.step()
        assert "Columna llave 'RUT' no existe en 'estudiantes'" in str(exc.value)
        assert exc.value.step_name == "_BoomStep"
        assert exc.value.step_index == 0
        assert isinstance(exc.value.original, ValueError)
        assert runner.status == "FAILED"

    def test_waiting_for_input_no_se_envuelve(self):
        """La pausa interactiva no es un error: mantiene su contrato."""
        runner = _runner_con(_WaitingStep())
        result = runner.step()
        assert result["status"] == "waiting_input"
        assert runner.status == "WAITING_INPUT"


@pytest.mark.integration
class TestRunPropagaErrorDeStep:
    """Contrato del router: POST /run devuelve el mensaje del step, no el genérico."""

    @pytest.fixture
    def pipeline_que_falla(self, db_session, org, monkeypatch):
        import json

        from backend.models import Pipeline

        monkeypatch.setitem(pipeline_tools.STEP_MAPPING, "_BoomTest", _BoomStep)
        cfg = {"context": {}, "pipeline": [{"step": "_BoomTest", "params": {}}]}
        p = Pipeline(
            pipeline="Pipeline Boom",
            description="falla en el primer step",
            config_json=json.dumps(cfg),
            org_id=org.id,
        )
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)
        return p

    def test_run_devuelve_mensaje_legible_del_step(self, client_auth, pipeline_que_falla):
        resp = client_auth.post(f"/api/pipelines/{pipeline_que_falla.pipeline_id}/run")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "failed"
        assert "Columna llave 'RUT' no existe en 'estudiantes'" in body["error"]
        assert body["step_name"] == "_BoomStep"
        assert "Error interno del servidor" not in body["error"]


@pytest.mark.integration
class TestWordReportErrorSaneado:
    """P0-5: fallo interno cargando datos → 500 con mensaje genérico, sin NameError."""

    def test_error_de_carga_no_filtra_detalle_interno(self, client_auth, monkeypatch):
        import backend.routers.reports as reports_router
        from backend.rgenerator.reports import word as word_reports

        monkeypatch.setattr(word_reports, "obtener_modulo", lambda nombre: object())

        def _boom(*args, **kwargs):
            raise RuntimeError("detalle interno secreto: DSN=postgres://...")

        monkeypatch.setattr(reports_router, "cargar_dataframes_indicator", _boom)

        resp = client_auth.post(
            "/api/reports/word/cualquiera", json={"indicator_id": 1, "filtros": {}}
        )
        assert resp.status_code == 500
        detail = resp.json()["detail"]
        assert detail == "Error cargando datos del informe"
        assert "secreto" not in detail
