"""
logging_config.py — Configuración centralizada de logging para el backend.

Uso en cualquier módulo de producción:

    from backend.logging_config import get_logger
    logger = get_logger(__name__)

    logger.info("Operación completada")
    logger.warning("Situación inesperada pero recuperable")
    logger.error("Error no controlado", exc_info=True)  # incluye el traceback

El nivel se controla con la variable de entorno ``LOG_LEVEL`` (default
``INFO``). ``setup_logging()`` es idempotente: se invoca en el arranque de la
app (``backend/api.py``) y también, de forma perezosa, la primera vez que se
pide un logger vía ``get_logger`` — así los scripts y tests que importan
``get_logger`` obtienen handlers ya configurados sin depender del arranque de
FastAPI.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional

_CONFIGURED = False

DEFAULT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: Optional[str] = None) -> None:
    """Configura el root logger una sola vez.

    - El nivel se toma del argumento ``level``, o de ``LOG_LEVEL``, o INFO.
    - Agrega un ``StreamHandler`` a stdout con formato estándar solo si el root
      no tiene ya uno, para no duplicar líneas cuando uvicorn/pytest ya
      configuraron logging.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(log_level)

    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(DEFAULT_FORMAT, DEFAULT_DATEFMT))
        root.addHandler(handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger nombrado, garantizando que el logging esté configurado."""
    setup_logging()
    return logging.getLogger(name)
