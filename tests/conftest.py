"""Configuración compartida de pytest.

CRITICAL: setea env vars ANTES de cualquier `from backend.X import` para
que `backend/database.py` no falle al inicializarse (requiere DATABASE_URL).

Provee fixtures para tests de integración:
  - engine: SQLite in-memory + tablas creadas con Base.metadata.create_all
  - db_session: sesión SQLAlchemy con rollback automático
  - client: TestClient FastAPI con get_db override
  - org, user, auth_headers, client_auth: para tests que requieren autenticación

Los tests unit que no necesitan estas fixtures siguen funcionando igual.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────
# 1) PYTHONPATH: backend/ y raíz del repo
# ─────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

# Solo la RAÍZ del repo va al sys.path. backend/ NO se agrega: hacerlo
# permitía importar el paquete como `rgenerator.*` (ruta corta), creando
# una segunda instancia de cada módulo con clases incompatibles con las de
# `backend.rgenerator.*` (ver tests/regresion/test_import_canonico.py).
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ─────────────────────────────────────────────────────────────────────────
# 2) ENV VARS de test — DEBE ir antes de importar backend.database
# ─────────────────────────────────────────────────────────────────────────
# DATABASE_URL placeholder: el engine "real" no se usa porque cada test
# override get_db con la sesión de SQLite. Pero `backend.database` lo lee
# al importarse y falla si no existe.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod")
os.environ.setdefault("JWT_EXPIRE_HOURS", "1")
os.environ.setdefault("ENVIRONMENT", "test")

# ─────────────────────────────────────────────────────────────────────────
# 3) Imports — ahora sí, después de env vars
# ─────────────────────────────────────────────────────────────────────────
import pytest  # noqa: E402

from datetime import date  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────
# 3b) Fecha de referencia CONGELADA
#
# El resolver de períodos (`backend/rgenerator/reports/periodos.py`) decide
# "año en curso" y "semestre en curso" a partir de un `hoy`. Si ese `hoy`
# fuera el del reloj, cualquier test que siembre datos de un mes fijo
# empezaría a fallar apenas el calendario cruza el semestre (pasó al entrar
# agosto: los datos ABRIL/MAYO quedaron fuera del "2º semestre en curso").
#
# Por eso TODA la suite corre con `hoy` = 15-06-2026: 1er semestre del
# calendario escolar chileno (meses 1–7). Los fixtures que siembran datos
# usan la fixture `hoy` — nunca `date.today()` — para quedar dentro de ese
# período.
# ─────────────────────────────────────────────────────────────────────────
FECHA_HOY_TEST = date(2026, 6, 15)


@pytest.fixture
def hoy() -> date:
    """Fecha de referencia congelada de la suite (ver `FECHA_HOY_TEST`)."""
    return FECHA_HOY_TEST


@pytest.fixture(autouse=True)
def _congelar_hoy(monkeypatch):
    """Congela `periodos.hoy()`, la única fuente de "hoy" del backend.

    No-op si el backend no está instalado (entorno Python host puro).
    """
    try:
        from backend.rgenerator.reports import periodos
    except ImportError:
        return
    monkeypatch.setattr(periodos, "hoy", lambda: FECHA_HOY_TEST)


# ─────────────────────────────────────────────────────────────────────────
# 4) Fixtures de DB / Cliente / Auth
#
# Saltean limpio si las deps backend no están (entorno Python host puro).
# Los tests que dependen de ellas usan `client`/`db_session`/etc., pytest
# las skipea solo si fallan al construirse.
# ─────────────────────────────────────────────────────────────────────────
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    _HAS_SQLA = True
except ImportError:
    _HAS_SQLA = False


@pytest.fixture(scope="session")
def engine():
    """Engine SQLite in-memory compartido por toda la sesión de tests.

    Usa `StaticPool` para que TODAS las conexiones (la de los tests y la
    de la app vía dependency override) vean la MISMA DB in-memory. Sin
    esto, SQLite crea una DB por conexión y los datos del setup no son
    visibles desde el endpoint bajo test.
    """
    if not _HAS_SQLA:
        pytest.skip("sqlalchemy no disponible")
    from sqlalchemy.pool import StaticPool

    # Importar Base + todos los modelos para que se registren las tablas
    from backend.database import Base
    from backend import models  # noqa: F401 — registra modelos en Base

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine):
    """Sesión SQLAlchemy aislada por test usando SAVEPOINT anidado.

    El test corre dentro de una transacción "outer" (que rollback al final).
    Los `db.commit()` que hagan los endpoints solo cierran un SAVEPOINT
    anidado, no la transaction outer. Esto permite que el endpoint vea sus
    propios cambios pero al terminar el test todo se descarta.

    Patrón estándar de SQLAlchemy para tests: ver
    https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites
    """
    from sqlalchemy import event

    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = SessionLocal()

    # Iniciar SAVEPOINT al comenzar. Si el código bajo test hace commit(),
    # se cierra el SAVEPOINT, no la outer transaction. Re-iniciamos uno nuevo.
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(session, transaction_):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    # Invalidar cache TTL de _load_metric_to_df para no leak entre tests.
    try:
        from backend.routers.tables import invalidate_metric_df_cache
        invalidate_metric_df_cache()
    except ImportError:
        pass

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        try:
            from backend.routers.tables import invalidate_metric_df_cache
            invalidate_metric_df_cache()
        except ImportError:
            pass


@pytest.fixture
def client(db_session):
    """TestClient FastAPI con get_db override apuntando al db_session de test."""
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi no disponible")

    from backend.api import app
    from backend.database import get_db

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass  # NO cerrar — la fixture db_session lo maneja

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


# ─────────────────────────────────────────────────────────────────────────
# Auth fixtures
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def org(db_session):
    """Organización por defecto para tests."""
    from backend.models import Organization
    o = Organization(name="Org de Test", slug="test-org", is_active=True)
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    return o


@pytest.fixture
def user(db_session, org):
    """Usuario editor vinculado a `org` con password conocido."""
    from backend.auth import hash_password
    from backend.models import User
    u = User(
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("test123"),
        org_id=org.id,
        role="editor",
        is_active=True,
        is_superadmin=False,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def auth_headers(user):
    """`{"Authorization": "Bearer <jwt>"}` válido para `user`."""
    from backend.auth import create_access_token
    token = create_access_token(user_id=user.id, org_id=user.org_id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client_auth(client, auth_headers):
    """TestClient con headers Authorization pre-cargados — atajo cómodo."""
    client.headers.update(auth_headers)
    return client


@pytest.fixture
def admin_user(db_session, org):
    """Usuario **admin** vinculado a `org` (misma org que `user`).

    Para endpoints protegidos con `require_admin`, donde el `user` editor
    por defecto recibe 403.
    """
    from backend.auth import hash_password
    from backend.models import User
    u = User(
        name="Test Admin",
        email="admin@example.com",
        password_hash=hash_password("test123"),
        org_id=org.id,
        role="admin",
        is_active=True,
        is_superadmin=False,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def viewer_user(db_session, org):
    """Usuario **viewer** (solo lectura) vinculado a `org`."""
    from backend.auth import hash_password
    from backend.models import User
    u = User(
        name="Test Viewer",
        email="viewer@example.com",
        password_hash=hash_password("test123"),
        org_id=org.id,
        role="viewer",
        is_active=True,
        is_superadmin=False,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def auth_headers_admin(admin_user):
    """`{"Authorization": "Bearer <jwt>"}` válido para `admin_user`."""
    from backend.auth import create_access_token
    token = create_access_token(
        user_id=admin_user.id, org_id=admin_user.org_id, role=admin_user.role
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_viewer(viewer_user):
    """`{"Authorization": "Bearer <jwt>"}` válido para `viewer_user`."""
    from backend.auth import create_access_token
    token = create_access_token(
        user_id=viewer_user.id, org_id=viewer_user.org_id, role=viewer_user.role
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client_auth_admin(client, auth_headers_admin):
    """TestClient autenticado como **admin** de `org`.

    NOTA: comparte la instancia de `client` con `client_auth` /
    `client_auth_viewer`; no pedir dos de estos fixtures en el mismo test
    (el último en resolverse pisa el header Authorization).
    """
    client.headers.update(auth_headers_admin)
    return client


@pytest.fixture
def client_auth_viewer(client, auth_headers_viewer):
    """TestClient autenticado como **viewer** de `org` (ver nota en `client_auth_admin`)."""
    client.headers.update(auth_headers_viewer)
    return client


# ─────────────────────────────────────────────────────────────────────────
# Indicadores SIMCE de prueba
#
# Vivían como fixture local de `tests/reports/test_dispatch_v2.py`; se
# promovieron acá (contrato del motor único, N9) porque los tests del
# despacho por modos y los del módulo SIMCE necesitan el mismo montaje.
# ─────────────────────────────────────────────────────────────────────────

#: Dimensiones mínimas de un indicador SIMCE.
_DIMS_SIMCE = ("Curso", "RUT", "Nombre", "Asignatura", "Mes", "N Prueba", "Año")


def _montar_simce(db_session, org, filas, *, achievement_levels=None, **kwargs):
    """Indicador SIMCE con metrics `estudiantes` + `preguntas` y `filas` de datos.

    Args:
        filas: lista de dicts con keys `curso`, `mes`, `n_prueba`, `anio`,
            `rut`, `nombre`, `asignatura`, `rend`, `simce`, `logro`.
    """
    from tests.factories import (
        make_dimension, make_indicator, make_metric, make_metric_data,
    )

    dims = {n: make_dimension(db_session, org, name=n) for n in _DIMS_SIMCE}
    dims["Logro"] = make_dimension(db_session, org, name="Logro")
    dims["Pregunta"] = make_dimension(db_session, org, name="Pregunta")
    dims["Habilidad"] = make_dimension(db_session, org, name="Habilidad")

    m_est = make_metric(
        db_session, org, name="Resultados SIMCE por Estudiante", data_type="object",
        fields=[{"name": "Buenas", "type": "int"}, {"name": "Rend", "type": "float"},
                {"name": "Simce", "type": "float"}],
        dimensions=list(dims.values()),
    )
    m_preg = make_metric(
        db_session, org, name="Resultados SIMCE por Pregunta", data_type="object",
        fields=[{"name": "Logro", "type": "float"}],
        dimensions=list(dims.values()),
    )
    ident = {n: str(d.id_dimension) for n, d in dims.items()}

    for fila in filas:
        base = {
            ident["Curso"]: fila.get("curso", "II A"),
            ident["RUT"]: fila.get("rut", "1-1"),
            ident["Nombre"]: fila.get("nombre", "Test"),
            ident["Asignatura"]: fila.get("asignatura", "Lenguaje"),
            ident["Mes"]: fila.get("mes", "ABRIL"),
            ident["N Prueba"]: str(fila.get("n_prueba", 1)),
            ident["Año"]: str(fila.get("anio", FECHA_HOY_TEST.year)),
            ident["Logro"]: fila.get("logro", "Insuficiente"),
        }
        make_metric_data(
            db_session, m_est,
            value={"Buenas": 8, "Rend": fila.get("rend", 0.5),
                   "Simce": fila.get("simce", 250)},
            dimensions_json=base,
        )
        make_metric_data(
            db_session, m_preg, value={"Logro": fila.get("logro_pregunta", 0.6)},
            dimensions_json={
                **base,
                ident["Pregunta"]: fila.get("pregunta", "1"),
                ident["Habilidad"]: fila.get("habilidad", "Inferir"),
            },
        )

    import json as _json
    return make_indicator(
        db_session, org, name=kwargs.pop("name", "SIMCE Test"),
        metrics=[m_est, m_preg], report_engine_type="simce",
        # La columna es Text: el JSON va serializado, igual que en la DB real.
        achievement_levels=_json.dumps(achievement_levels or [], ensure_ascii=False),
        **kwargs,
    )


@pytest.fixture
def simce_indicator(db_session, org):
    """Indicador SIMCE mínimo con metrics estudiantes + preguntas (1 prueba)."""
    return _montar_simce(
        db_session, org,
        [{"curso": "II A", "mes": "ABRIL", "n_prueba": 1,
          "anio": FECHA_HOY_TEST.year}],
    )


@pytest.fixture
def simce_indicator_historico(db_session, org, hoy):
    """Indicador SIMCE con 2 meses del año en curso y el año anterior.

    Sirve para probar la evolución (≥2 puntos temporales), la comparación
    con el período anterior y el riesgo persistente (mismo alumno en nivel
    Insuficiente en dos meses consecutivos).

    ABRIL y MAYO caen en el 1er semestre de `FECHA_HOY_TEST`: los modos
    semestral/anual del resolver encuentran datos siempre.
    """
    anio = hoy.year
    filas = []
    for mes, n in (("ABRIL", 1), ("MAYO", 2)):
        for rut, nombre, rend, logro in (
            ("1-1", "Alumno Uno", 0.30, "Insuficiente"),
            ("2-2", "Alumno Dos", 0.80, "Adecuado"),
        ):
            filas.append({
                "curso": "II A", "mes": mes, "n_prueba": n, "anio": anio,
                "rut": rut, "nombre": nombre, "rend": rend,
                "simce": int(rend * 400), "logro": logro,
            })
    # Año anterior: alimenta la columna comparada del cuadro resumen.
    filas.append({
        "curso": "II A", "mes": "NOVIEMBRE", "n_prueba": 5, "anio": anio - 1,
        "rut": "1-1", "nombre": "Alumno Uno", "rend": 0.40,
        "simce": 200, "logro": "Insuficiente",
    })
    return _montar_simce(
        db_session, org, filas, name="SIMCE Histórico",
        achievement_levels=[
            {"name": "Insuficiente", "color": "#dc2626", "order": 1},
            {"name": "Elemental", "color": "#eab308", "order": 2},
            {"name": "Adecuado", "color": "#22c55e", "order": 3},
        ],
    )


# ─────────────────────────────────────────────────────────────────────────
# Rate limiter de login — estado global in-memory que NO debe filtrar
# fallos entre tests (varios tests hacen logins inválidos a propósito).
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_login_limiters():
    yield
    try:
        from backend.routers import auth as auth_router
        auth_router._limiter_cuenta.clear()
        auth_router._limiter_ip.clear()
    except ImportError:
        pass
