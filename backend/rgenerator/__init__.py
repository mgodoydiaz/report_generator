"""
rgenerator
Librería para ejecutar ETL y generar reportes académicos.
"""

from . import etl, reports, tooling  # noqa: F401
from ._version import __version__  # noqa: F401

__all__ = ["etl", "tooling", "reports", "__version__"]
