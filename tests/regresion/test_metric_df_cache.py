"""Regresión: cache TTL de _load_metric_to_df + invalidación automática.

Feature commit 6e83156: cache LRU+TTL para que dashboards con múltiples
charts/tablas sobre la misma métrica no re-carguen MetricData.

Necesitamos validar:
1. invalidate_metric_df_cache(metric_id=N) borra solo esa key.
2. invalidate_metric_df_cache() (sin arg) limpia todo.
3. Event listeners SQLAlchemy invalidan automáticamente tras
   INSERT/UPDATE/DELETE en MetricData.
"""
from __future__ import annotations

import pytest

from backend.routers.tables import (
    _METRIC_DF_CACHE,
    invalidate_metric_df_cache,
)


@pytest.mark.unit
class TestInvalidateExplicito:
    def test_invalidate_total_limpia_todo(self):
        _METRIC_DF_CACHE[(1, 99, None)] = (0.0, "fake_df")
        _METRIC_DF_CACHE[(1, 100, None)] = (0.0, "fake_df")
        invalidate_metric_df_cache()
        assert len(_METRIC_DF_CACHE) == 0

    def test_invalidate_por_metric_id_borra_solo_esa(self):
        _METRIC_DF_CACHE[(1, 99, None)] = (0.0, "df_99")
        _METRIC_DF_CACHE[(1, 100, None)] = (0.0, "df_100")
        _METRIC_DF_CACHE[(2, 99, None)] = (0.0, "df_99_org2")
        invalidate_metric_df_cache(metric_id=99)
        # Las 2 entries con metric_id=99 deben haber salido,
        # la de metric_id=100 sigue.
        remaining = list(_METRIC_DF_CACHE.keys())
        assert all(k[1] != 99 for k in remaining)
        assert (1, 100, None) in _METRIC_DF_CACHE
        # Cleanup
        invalidate_metric_df_cache()


@pytest.mark.integration
class TestEventListenerInvalida:
    def test_insert_metric_data_invalida_cache(self, db_session):
        from tests.factories import (
            make_metric, make_metric_data, make_org,
        )
        org = make_org(db_session)
        m = make_metric(db_session, org)
        # Pre-cargar el cache manualmente
        _METRIC_DF_CACHE[(org.id, m.id_metric, None)] = (0.0, "stale_df")
        # Insertar MetricData → after_insert listener debe invalidar
        make_metric_data(db_session, m, value="1.0", dimensions_json={"3": "X"})
        # La entry para esa metric debe haber sido removida
        assert (org.id, m.id_metric, None) not in _METRIC_DF_CACHE

    def test_delete_metric_data_invalida_cache(self, db_session):
        from backend.models import MetricData
        from tests.factories import (
            make_metric, make_metric_data, make_org,
        )
        org = make_org(db_session)
        m = make_metric(db_session, org)
        md = make_metric_data(db_session, m, value="1.0")
        # Pre-cargar cache
        _METRIC_DF_CACHE[(org.id, m.id_metric, None)] = (0.0, "stale_df")
        # Borrar la fila
        db_session.delete(md)
        db_session.commit()
        # Cache invalidado para esa metric
        assert (org.id, m.id_metric, None) not in _METRIC_DF_CACHE
