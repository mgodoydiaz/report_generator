"""
database.py — SQLAlchemy engine, session factory y base declarativa.

Uso en routers:
    from backend.database import get_db
    def mi_endpoint(db: Session = Depends(get_db)): ...
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mgodoy:holapocompadre977@localhost:5432/rgenerator_dev"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # reconecta si la conexión se cayó
    pool_size=5,
    max_overflow=10,
    echo=os.getenv("DEBUG", "false").lower() == "true",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: abre una sesión y la cierra al terminar el request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Crea todas las tablas si no existen. Llamar desde api.py en startup."""
    from backend import models  # noqa: F401 — importar para registrar modelos
    Base.metadata.create_all(bind=engine)
