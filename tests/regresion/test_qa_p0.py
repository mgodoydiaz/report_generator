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


@pytest.mark.unit
class TestFiltroTemporalDIA:
    """P0-2: el filtro 'Año' del informe DIA se capturaba pero nunca se aplicaba."""

    def _df(self):
        import pandas as pd

        return pd.DataFrame(
            {
                "Hito": ["DIAGNOSTICO", "INTERMEDIO", "DIAGNOSTICO", "INTERMEDIO"],
                "Año": ["2024", "2024", "2025", "2025"],
                "Rend": [1, 2, 3, 4],
            }
        )

    def test_filtra_por_anio_escalar(self):
        from rgenerator.reports.dia.crear_informe import _filtrar_temporal

        out = _filtrar_temporal(self._df(), "Año", "2025")
        assert out["Rend"].tolist() == [3, 4]

    def test_filtra_por_anio_lista_multivalor(self):
        """Los filtros del dashboard llegan como lista."""
        from rgenerator.reports.dia.crear_informe import _filtrar_temporal

        out = _filtrar_temporal(self._df(), "Año", ["2024"])
        assert out["Rend"].tolist() == [1, 2]

    def test_none_lista_vacia_o_columna_inexistente_no_filtran(self):
        from rgenerator.reports.dia.crear_informe import _filtrar_temporal

        df = self._df()
        assert len(_filtrar_temporal(df, "Año", None)) == 4
        assert len(_filtrar_temporal(df, "Año", [])) == 4
        assert len(_filtrar_temporal(df, "NoExiste", "x")) == 4

    def test_hito_y_anio_combinados(self):
        from rgenerator.reports.dia.crear_informe import _filtrar_temporal

        out = _filtrar_temporal(
            _filtrar_temporal(self._df(), "Hito", "INTERMEDIO"), "Año", "2025"
        )
        assert out["Rend"].tolist() == [4]


@pytest.mark.unit
class TestMatchesCompartido:
    """Semántica única de filtros (reports/filtering.py) — P0-1 / H1."""

    def test_escalar(self):
        from rgenerator.reports.filtering import matches

        assert matches("5A", "5A")
        assert not matches("5A", "5B")

    def test_lista_multivalor_es_pertenencia(self):
        from rgenerator.reports.filtering import matches

        assert matches("5A", ["5A", "5B"])
        assert not matches("6A", ["5A", "5B"])

    def test_lista_vacia_no_restringe(self):
        from rgenerator.reports.filtering import matches

        assert matches("cualquiera", [])


@pytest.mark.integration
class TestBuildRecordsFiltros:
    """P0-1: el motor v1 devolvía 0 registros con filtros multi-valor del
    dashboard. H6: metric cross-org vinculada jamás debe proyectar datos."""

    @pytest.fixture
    def escenario(self, db_session, org):
        from tests.factories import make_dimension, make_indicator, make_metric, make_metric_data

        dim = make_dimension(db_session, org, name="Curso")
        metric = make_metric(db_session, org, name="Rendimiento", dimensions=[dim])
        for curso, val in [("5A", 60), ("5B", 70), ("6A", 80)]:
            make_metric_data(
                db_session, metric, value=val,
                dimensions_json={str(dim.id_dimension): curso},
            )
        indicator = make_indicator(db_session, org, metrics=[metric])
        return dim, metric, indicator

    def test_filtro_multivalor_devuelve_los_cursos_seleccionados(self, db_session, org, escenario):
        from rgenerator.core.report_steps import _build_records

        dim, _, indicator = escenario
        recs = _build_records(
            db_session, indicator, org.id,
            filters={str(dim.id_dimension): ["5A", "5B"]},
        )
        assert len(recs) == 2

    def test_filtro_escalar_sigue_funcionando(self, db_session, org, escenario):
        from rgenerator.core.report_steps import _build_records

        dim, _, indicator = escenario
        recs = _build_records(
            db_session, indicator, org.id,
            filters={str(dim.id_dimension): "6A"},
        )
        assert len(recs) == 1

    def test_metric_cross_org_no_proyecta_datos(self, db_session, org, escenario):
        from tests.factories import make_metric, make_metric_data, make_org
        from backend.models import IndicatorMetric
        from rgenerator.core.report_steps import _build_records

        _, _, indicator = escenario
        otra_org = make_org(db_session, name="Org Ajena QA")
        metric_ajena = make_metric(db_session, otra_org, name="Secreta")
        make_metric_data(db_session, metric_ajena, value=99)
        db_session.add(IndicatorMetric(
            id_indicator=indicator.id_indicator, id_metric=metric_ajena.id_metric
        ))
        db_session.commit()

        recs = _build_records(db_session, indicator, org.id)
        assert len(recs) == 3  # solo los datos de la org propia


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
