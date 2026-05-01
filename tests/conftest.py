"""Configuración compartida de pytest para el proyecto.

Agrega `backend/` y la raíz del repo al PYTHONPATH para que los tests puedan
importar `rgenerator.tooling.X` y `backend.X` sin necesidad de `pip install -e .`
(útil cuando el entorno conda local tiene problemas).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

for p in (str(ROOT), str(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)
