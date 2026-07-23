"""
rgenerator
Librería para ejecutar ETL y generar reportes académicos.

Ruta de import CANÓNICA: `backend.rgenerator.*`. La ruta corta
`rgenerator.*` (vía install editable o backend/ en sys.path) creaba una
segunda instancia de cada módulo: isinstance/except entre clases de rutas
distintas falla silenciosamente. El guard de abajo la bloquea con error
explícito (descubierto 2026-07-22 testeando StepExecutionError).
"""

if not __name__.startswith("backend."):
    raise ImportError(
        "Importa este paquete como `backend.rgenerator.*` (con la raíz del "
        "repo en sys.path). La ruta corta `rgenerator.*` crea instancias "
        "duplicadas de los módulos y rompe isinstance/except entre clases. "
        "Ver tests/regresion/test_import_canonico.py."
    )

from . import core, tooling  # noqa: F401
from ._version import __version__  # noqa: F401

import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LIB_DIR = os.path.join(BASE_DIR, 'backend', 'rgenerator')
INPUT_DIR = os.path.join(BASE_DIR, 'data', 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'output')
TMP_DIR = os.path.join(BASE_DIR, 'data', 'tmp')

sys.path.append(BASE_DIR)

__all__ = ["core", "tooling", "__version__"]
