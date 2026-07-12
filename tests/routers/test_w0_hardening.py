"""Tests de los fixes de seguridad W0 (plan maestro).

Cubre: sanitización de uploads (W0.1), JWT_SECRET obligatorio (W0.4),
rate limiting de login (W0.5) e invalidación de cache en writers (W0.7).
El evaluador seguro (W0.2) tiene su propia suite en
tests/steps/test_safe_eval.py.
"""
from __future__ import annotations

import subprocess
import sys
import time

import pytest

from tests.factories import make_dimension, make_metric, make_metric_data


# ─────────────────────────────────────────────────────────────────────────
# W0.1 — Uploads: path traversal y tamaño
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def pipeline_row(db_session, org):
    from backend.models import Pipeline
    p = Pipeline(
        pipeline="Pipeline Test",
        description="",
        config_json="{}",
        org_id=org.id,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.mark.integration
class TestUploadSeguridad:
    def test_input_key_con_traversal_rechazado(self, client_auth, pipeline_row):
        res = client_auth.post(
            f"/api/pipelines/{pipeline_row.pipeline_id}/upload",
            data={"input_key": "../../../etc"},
            files=[("files", ("ok.txt", b"data"))],
        )
        assert "error" in res.json()
        assert "input_key" in res.json()["error"]

    @pytest.mark.parametrize("input_key", ["estudiantes", "preguntas", "mi_rol-2"])
    def test_input_keys_legitimos_pasan(self, client_auth, pipeline_row, input_key, tmp_path, monkeypatch):
        from backend.routers import pipelines as mod
        monkeypatch.setattr(mod, "UPLOADS_DIR", tmp_path)
        res = client_auth.post(
            f"/api/pipelines/{pipeline_row.pipeline_id}/upload",
            data={"input_key": input_key},
            files=[("files", ("datos.xlsx", b"contenido"))],
        )
        body = res.json()
        assert body.get("status") == "success", body
        assert (tmp_path / str(pipeline_row.pipeline_id) / input_key / "datos.xlsx").exists()

    def test_filename_con_traversal_se_reduce_a_basename(self, client_auth, pipeline_row, tmp_path, monkeypatch):
        from backend.routers import pipelines as mod
        monkeypatch.setattr(mod, "UPLOADS_DIR", tmp_path)
        res = client_auth.post(
            f"/api/pipelines/{pipeline_row.pipeline_id}/upload",
            data={"input_key": "estudiantes"},
            files=[("files", ("../../../../evil.txt", b"x"))],
        )
        body = res.json()
        assert body.get("status") == "success", body
        # Quedó DENTRO del directorio del rol, como basename
        esperado = tmp_path / str(pipeline_row.pipeline_id) / "estudiantes" / "evil.txt"
        assert esperado.exists()
        # Y nada escapó fuera del árbol de uploads
        assert not (tmp_path.parent / "evil.txt").exists()

    def test_archivo_gigante_rechazado(self, client_auth, pipeline_row, tmp_path, monkeypatch):
        from backend.routers import pipelines as mod
        monkeypatch.setattr(mod, "UPLOADS_DIR", tmp_path)
        monkeypatch.setattr(mod, "MAX_UPLOAD_BYTES", 10)  # 10 bytes para el test
        res = client_auth.post(
            f"/api/pipelines/{pipeline_row.pipeline_id}/upload",
            data={"input_key": "estudiantes"},
            files=[("files", ("grande.bin", b"0123456789ABCDEF"))],
        )
        body = res.json()
        assert "error" in body and "supera el máximo" in body["error"]
        assert not (tmp_path / str(pipeline_row.pipeline_id) / "estudiantes" / "grande.bin").exists()


# ─────────────────────────────────────────────────────────────────────────
# W0.4 — JWT_SECRET obligatorio en arranque
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_backend_auth_no_importa_sin_jwt_secret(tmp_path):
    """Importar backend.auth sin JWT_SECRET debe fallar (no default silencioso).

    Corre en subproceso, con cwd en un directorio temporal para que
    load_dotenv() no encuentre el .env del repo (que sí trae JWT_SECRET).
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    code = (
        "import os;"
        "os.environ.pop('JWT_SECRET', None);"
        "os.environ['DATABASE_URL'] = 'sqlite:///:memory:';"
        "import backend.auth"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True,
        env={"PATH": "", "PYTHONPATH": str(repo_root)},
        cwd=str(tmp_path),
    )
    assert proc.returncode != 0
    assert "JWT_SECRET" in proc.stderr


# ─────────────────────────────────────────────────────────────────────────
# W0.5 — Rate limiting de login
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestLoginRateLimit:
    def test_bloquea_tras_max_intentos_fallidos(self, client, user):
        from backend.routers import auth as auth_router
        for _ in range(auth_router._LOGIN_MAX_ATTEMPTS):
            res = client.post("/api/auth/login",
                              json={"email": user.email, "password": "incorrecta"})
            assert res.status_code == 401
        res = client.post("/api/auth/login",
                          json={"email": user.email, "password": "incorrecta"})
        assert res.status_code == 429
        assert "Retry-After" in res.headers
        # Incluso con la password CORRECTA sigue bloqueado (la ventana manda)
        res = client.post("/api/auth/login",
                          json={"email": user.email, "password": "test123"})
        assert res.status_code == 429

    def test_login_exitoso_resetea_contador(self, client, user):
        from backend.routers import auth as auth_router
        for _ in range(auth_router._LOGIN_MAX_ATTEMPTS - 1):
            client.post("/api/auth/login",
                        json={"email": user.email, "password": "incorrecta"})
        res = client.post("/api/auth/login",
                          json={"email": user.email, "password": "test123"})
        assert res.status_code == 200
        # Contador limpio: de nuevo hay margen completo
        res = client.post("/api/auth/login",
                          json={"email": user.email, "password": "incorrecta"})
        assert res.status_code == 401


@pytest.mark.unit
class TestSlidingWindowLimiter:
    def test_ventana_expira(self):
        from backend.rate_limit import SlidingWindowLimiter
        lim = SlidingWindowLimiter(max_attempts=2, window_seconds=0.05)
        lim.register_failure("k")
        lim.register_failure("k")
        assert lim.is_blocked("k") is True
        time.sleep(0.06)
        assert lim.is_blocked("k") is False

    def test_reset_y_retry_after(self):
        from backend.rate_limit import SlidingWindowLimiter
        lim = SlidingWindowLimiter(max_attempts=1, window_seconds=60)
        lim.register_failure("k")
        assert lim.is_blocked("k")
        assert 0 < lim.retry_after_seconds("k") <= 60
        lim.reset("k")
        assert not lim.is_blocked("k")


# ─────────────────────────────────────────────────────────────────────────
# W0.7 — Invalidación del cache de DataFrames al escribir MetricData
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestCacheInvalidacion:
    def test_post_data_invalida_cache_de_la_metrica(self, client_auth, db_session, org):
        from backend.routers import tables as tables_mod

        dim = make_dimension(db_session, org, name="Curso")
        metric = make_metric(
            db_session, org, name="Metric Cache Test", data_type="float",
            dimensions=[dim],
        )
        make_metric_data(db_session, metric, value="0.5",
                         dimensions_json={str(dim.id_dimension): "II A"})

        # Sembrar una entrada de cache para esta métrica
        clave = tables_mod._metric_df_cache_key(org.id, metric.id_metric, None)
        tables_mod._METRIC_DF_CACHE[clave] = (time.time(), __import__("pandas").DataFrame())
        assert any(k[1] == metric.id_metric for k in tables_mod._METRIC_DF_CACHE)

        res = client_auth.post(
            f"/api/metrics/{metric.id_metric}/data",
            json={"value": "0.7", "dimensions_json": {str(dim.id_dimension): "II B"}},
        )
        assert res.status_code == 200, res.text

        # La entrada de esa métrica ya no está
        assert not any(k[1] == metric.id_metric for k in tables_mod._METRIC_DF_CACHE)

    def test_clear_invalida_cache(self, client_auth, db_session, org):
        from backend.routers import tables as tables_mod

        metric = make_metric(db_session, org, name="Metric Clear Test", data_type="float")
        clave = tables_mod._metric_df_cache_key(org.id, metric.id_metric, None)
        tables_mod._METRIC_DF_CACHE[clave] = (time.time(), __import__("pandas").DataFrame())

        res = client_auth.post(f"/api/metrics/{metric.id_metric}/clear")
        assert res.status_code == 200, res.text
        assert not any(k[1] == metric.id_metric for k in tables_mod._METRIC_DF_CACHE)
