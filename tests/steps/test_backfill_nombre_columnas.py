"""Tests del retiro del par `Nombre` / `Nombre_Norm` en el guardado.

Historia: primero existió la red de seguridad "toda carga deja el nombre en
AMBAS columnas". El 2026-08-07 el dueño retiró `Nombre_Norm` como dato
persistido: la identidad se calcula al vuelo en lectura
(`normalizar_nombre`) y `Nombre` es la única fuente de verdad visible.

Cubre las dos mitades del estado actual:

1. `SaveToMetric` — ya NO completa el par: guarda `Nombre` tal cual,
   DESCARTA cualquier columna `X_Norm` entrante (pipelines viejos) y
   excluye las dimensiones `X_Norm` aún asociadas a la métrica.
2. `scripts/backfill_nombre_columnas.py` — script HISTÓRICO de reparación
   de datos ya cargados con la convención vieja; sigue funcionando para
   los datos que la traen (sus tests se conservan tal cual).
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from tests.factories import (
    make_dimension,
    make_metric,
    make_metric_data,
    make_org,
)

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

def _montar_metrica_con_nombres(db, org, *, con_norm=True):
    """Métrica con dimensiones Curso + Nombre (+ Nombre_Norm)."""
    dim_curso = make_dimension(db, org, name="Curso")
    dim_nombre = make_dimension(db, org, name="Nombre")
    dims = [dim_curso, dim_nombre]
    dim_norm = None
    if con_norm:
        dim_norm = make_dimension(db, org, name="Nombre_Norm")
        dims.append(dim_norm)
    metric = make_metric(db, org, name="Logro", data_type="float", dimensions=dims)
    return metric, dim_curso, dim_nombre, dim_norm


def _dims_de(fila):
    return json.loads(fila.dimensions_json)


class _CtxFalso:
    """RunContext mínimo para ejercitar SaveToMetric sin el runner completo."""

    def __init__(self, db, org_id, artifacts):
        self.db = db
        self.org_id = org_id
        self.user_id = None
        self.artifacts = artifacts
        self.outputs = {}


# ─────────────────────────────────────────────────────────────────────────
# 1) SaveToMetric
# ─────────────────────────────────────────────────────────────────────────

class TestSaveToMetricNoPersisteNombreNorm:

    def _guardar(self, db, org, metric, df):
        from backend.rgenerator.core.metric_steps import SaveToMetric
        from backend.models import MetricData

        ctx = _CtxFalso(db, org.id, {"datos": df})
        step = SaveToMetric(metric_id=metric.id_metric, input_key="datos")
        step.run(ctx)
        filas = db.query(MetricData).filter(
            MetricData.id_metric == metric.id_metric
        ).all()
        return filas, step

    def test_solo_nombre_no_inventa_la_normalizada(self, db_session):
        """El par ya no se completa: `Nombre` se guarda tal cual y la
        dimensión `Nombre_Norm` (aunque siga asociada) queda fuera."""
        org = make_org(db_session)
        metric, _, dim_nombre, dim_norm = _montar_metrica_con_nombres(db_session, org)
        df = pd.DataFrame([{"Curso": "I A", "Nombre": "José Pérez", "Logro": 0.5}])

        filas, _ = self._guardar(db_session, org, metric, df)

        dims = _dims_de(filas[0])
        assert dims[str(dim_nombre.id_dimension)] == "José Pérez"
        assert str(dim_norm.id_dimension) not in dims

    def test_columna_nombre_norm_entrante_se_descarta_con_warning(self, db_session):
        """(c) Un DataFrame de un pipeline viejo trae `Nombre_Norm`: la
        columna se DESCARTA (no se persiste) y se emite warning informativo."""
        org = make_org(db_session)
        metric, dim_curso, dim_nombre, dim_norm = _montar_metrica_con_nombres(
            db_session, org
        )
        df = pd.DataFrame([
            {"Curso": "I A", "Nombre_Norm": "JOSE PEREZ", "Logro": 0.5},
        ])

        filas, step = self._guardar(db_session, org, metric, df)

        dims = _dims_de(filas[0])
        assert dims == {str(dim_curso.id_dimension): "I A"}
        assert str(dim_norm.id_dimension) not in dims
        assert str(dim_nombre.id_dimension) not in dims  # no se copia nada
        assert any("Nombre_Norm" in log and "descartan" in log for log in step.logs)

    def test_nombre_se_guarda_y_norm_entrante_se_ignora(self, db_session):
        org = make_org(db_session)
        metric, _, dim_nombre, dim_norm = _montar_metrica_con_nombres(db_session, org)
        df = pd.DataFrame([{
            "Curso": "I A", "Nombre": "José Pérez",
            "Nombre_Norm": "CLAVE PROPIA", "Logro": 0.5,
        }])

        filas, _ = self._guardar(db_session, org, metric, df)

        dims = _dims_de(filas[0])
        assert dims[str(dim_nombre.id_dimension)] == "José Pérez"
        assert str(dim_norm.id_dimension) not in dims

    def test_fila_sin_ninguna_columna_queda_intacta(self, db_session):
        org = make_org(db_session)
        metric, _, dim_nombre, dim_norm = _montar_metrica_con_nombres(db_session, org)
        df = pd.DataFrame([{"Curso": "7 A", "Logro": 0.5}])

        filas, _ = self._guardar(db_session, org, metric, df)

        dims = _dims_de(filas[0])
        assert str(dim_nombre.id_dimension) not in dims
        assert str(dim_norm.id_dimension) not in dims

    def test_metrica_sin_dimension_norm_no_rompe(self, db_session):
        """Métricas sin la dimensión legacy funcionan idéntico que siempre."""
        org = make_org(db_session)
        metric, _, dim_nombre, _ = _montar_metrica_con_nombres(
            db_session, org, con_norm=False
        )
        df = pd.DataFrame([{"Curso": "I A", "Nombre": "José Pérez", "Logro": 0.5}])

        filas, _ = self._guardar(db_session, org, metric, df)

        dims = _dims_de(filas[0])
        assert dims[str(dim_nombre.id_dimension)] == "José Pérez"
        assert len(dims) == 2  # Curso + Nombre, nada inventado


# ─────────────────────────────────────────────────────────────────────────
# 2) Script de backfill
# ─────────────────────────────────────────────────────────────────────────

class TestBackfillNombreColumnas:
    """Los 4 estados posibles de una fila + dry-run + multi-tenancy."""

    def _sembrar_cuatro_estados(self, db, org):
        metric, dim_curso, dim_nombre, dim_norm = _montar_metrica_con_nombres(db, org)
        k_curso = str(dim_curso.id_dimension)
        k_nombre = str(dim_nombre.id_dimension)
        k_norm = str(dim_norm.id_dimension)

        filas = {
            "solo_nombre": make_metric_data(
                db, metric, value=0.5,
                dimensions_json={k_curso: "I A", k_nombre: "José Pérez"},
            ),
            "solo_norm": make_metric_data(
                db, metric, value=0.6,
                dimensions_json={k_curso: "I A", k_norm: "JOSE PEREZ"},
            ),
            "ambas": make_metric_data(
                db, metric, value=0.7,
                dimensions_json={
                    k_curso: "I A", k_nombre: "Ana Soto", k_norm: "CLAVE PROPIA",
                },
            ),
            "ninguna": make_metric_data(
                db, metric, value=0.8, dimensions_json={k_curso: "7 A"},
            ),
        }
        return metric, (k_nombre, k_norm), filas

    def test_repara_los_dos_estados_a_medias(self, db_session):
        from scripts.backfill_nombre_columnas import backfill

        org = make_org(db_session)
        _, (k_nombre, k_norm), filas = self._sembrar_cuatro_estados(db_session, org)

        resumen = backfill(db_session, org.id, aplicar=True)

        assert resumen["revisadas"] == 4
        assert resumen["normalizadas_norm"] == 1
        assert resumen["copiadas_nombre"] == 1
        assert resumen["ya_completas"] == 1
        assert resumen["sin_identidad"] == 1

        for fila in filas.values():
            db_session.refresh(fila)

        # Solo Nombre → se normaliza con la función canónica.
        d = _dims_de(filas["solo_nombre"])
        assert d[k_nombre] == "José Pérez"
        assert d[k_norm] == "JOSE PEREZ"

        # Solo Norm → se copia a Nombre.
        d = _dims_de(filas["solo_norm"])
        assert d[k_nombre] == "JOSE PEREZ"
        assert d[k_norm] == "JOSE PEREZ"

        # Ambas → intacta.
        d = _dims_de(filas["ambas"])
        assert d[k_nombre] == "Ana Soto"
        assert d[k_norm] == "CLAVE PROPIA"

        # Ninguna → irreparable, sin inventar valores.
        d = _dims_de(filas["ninguna"])
        assert k_nombre not in d and k_norm not in d

    def test_dry_run_no_escribe(self, db_session):
        from scripts.backfill_nombre_columnas import backfill

        org = make_org(db_session)
        _, (k_nombre, k_norm), filas = self._sembrar_cuatro_estados(db_session, org)

        resumen = backfill(db_session, org.id, aplicar=False)

        # El resumen reporta lo que HARÍA...
        assert resumen["normalizadas_norm"] == 1
        assert resumen["copiadas_nombre"] == 1

        # ...pero la DB no cambió.
        db_session.rollback()
        db_session.refresh(filas["solo_nombre"])
        db_session.refresh(filas["solo_norm"])
        assert k_norm not in _dims_de(filas["solo_nombre"])
        assert k_nombre not in _dims_de(filas["solo_norm"])

    def test_org_sin_dimensiones_sale_limpio(self, db_session):
        from scripts.backfill_nombre_columnas import backfill

        org = make_org(db_session)
        make_metric(db_session, org, name="Otra métrica")

        assert backfill(db_session, org.id, aplicar=True) is None

    def test_org_solo_con_nombre_sin_norm_sale_limpio(self, db_session):
        """Falta una de las dos dimensiones → no hay par que completar."""
        from scripts.backfill_nombre_columnas import backfill

        org = make_org(db_session)
        _montar_metrica_con_nombres(db_session, org, con_norm=False)

        assert backfill(db_session, org.id, aplicar=True) is None

    def test_multi_tenancy_no_toca_otra_org(self, db_session):
        from scripts.backfill_nombre_columnas import backfill

        org_a = make_org(db_session)
        org_b = make_org(db_session)
        _, _, filas_a = self._sembrar_cuatro_estados(db_session, org_a)
        _, (kb_nombre, kb_norm), filas_b = self._sembrar_cuatro_estados(
            db_session, org_b
        )

        resumen = backfill(db_session, org_a.id, aplicar=True)
        assert resumen["revisadas"] == 4  # solo las de org_a

        # Las filas de org_b siguen a medias.
        db_session.refresh(filas_b["solo_nombre"])
        db_session.refresh(filas_b["solo_norm"])
        assert kb_norm not in _dims_de(filas_b["solo_nombre"])
        assert kb_nombre not in _dims_de(filas_b["solo_norm"])

    def test_dimensiones_se_resuelven_por_nombre_no_por_id(self, db_session):
        """Los ids de dimensión difieren entre orgs: el script debe resolver
        por nombre dentro de la org, nunca hardcodear 7/22."""
        from scripts.backfill_nombre_columnas import _resolver_dimensiones

        org_a = make_org(db_session)
        org_b = make_org(db_session)
        _montar_metrica_con_nombres(db_session, org_a)
        _montar_metrica_con_nombres(db_session, org_b)

        id_nombre_a, id_norm_a = _resolver_dimensiones(db_session, org_a.id)
        id_nombre_b, id_norm_b = _resolver_dimensiones(db_session, org_b.id)

        assert None not in (id_nombre_a, id_norm_a, id_nombre_b, id_norm_b)
        assert id_nombre_a != id_nombre_b
        assert id_norm_a != id_norm_b

    def test_ignora_metricas_sin_dimensiones_de_nombre(self, db_session):
        """Las métricas "por Pregunta" son agregados sin estudiante: no
        deben contarse como filas irreparables ni revisarse."""
        from scripts.backfill_nombre_columnas import backfill

        org = make_org(db_session)
        self._sembrar_cuatro_estados(db_session, org)

        dim_pregunta = make_dimension(db_session, org, name="N° Pregunta")
        metric_preg = make_metric(
            db_session, org, name="Logro por pregunta", dimensions=[dim_pregunta]
        )
        for n in range(5):
            make_metric_data(
                db_session, metric_preg, value=0.5,
                dimensions_json={str(dim_pregunta.id_dimension): str(n)},
            )

        resumen = backfill(db_session, org.id, aplicar=True)

        # Solo las 4 filas de la métrica de estudiantes.
        assert resumen["revisadas"] == 4
        assert resumen["sin_identidad"] == 1
        assert metric_preg.id_metric not in resumen["por_metrica"]

    def test_nombre_solo_con_espacios_cuenta_como_sin_identidad(self, db_session):
        from scripts.backfill_nombre_columnas import backfill

        org = make_org(db_session)
        metric, dim_curso, dim_nombre, dim_norm = _montar_metrica_con_nombres(
            db_session, org
        )
        make_metric_data(
            db_session, metric, value=0.5,
            dimensions_json={
                str(dim_curso.id_dimension): "I A",
                str(dim_nombre.id_dimension): "   ",
            },
        )

        resumen = backfill(db_session, org.id, aplicar=True)
        assert resumen["sin_identidad"] == 1
        assert resumen["normalizadas_norm"] == 0
