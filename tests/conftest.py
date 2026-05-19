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
BACKEND = ROOT / "backend"

for p in (str(ROOT), str(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

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
    """Sesión SQLAlchemy aislada por test.

    Cada test corre dentro de una transacción que se rollback al final →
    los tests no se contaminan entre sí. Mucho más rápido que recrear las
    tablas en cada test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = SessionLocal()

    # Invalidar cache TTL de _load_metric_to_df para que no se filtren
    # datos entre tests (event listeners de SQLAlchemy escriben al cache
    # global del módulo).
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
