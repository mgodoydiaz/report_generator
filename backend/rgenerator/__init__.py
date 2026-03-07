"""
rgenerator
Librería para ejecutar ETL y generar reportes académicos.
"""

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
