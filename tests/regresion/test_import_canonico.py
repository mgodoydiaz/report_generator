"""Guardia: la ruta canónica del paquete ETL es `backend.rgenerator.*`.

El paquete backend/rgenerator/ era importable por dos rutas (`rgenerator.*`
vía install editable o backend/ en sys.path, y `backend.rgenerator.*` vía
la raíz del repo). Python crea DOS instancias de cada módulo — una por
ruta — por lo que isinstance/except entre clases de rutas distintas falla
silenciosamente (descubierto 2026-07-22: el except StepExecutionError del
router no atrapaba la excepción del runner si las rutas no coincidían).

Unificación 2026-07-22:
  1. Todos los imports externos usan `backend.rgenerator.*`.
  2. Los imports internos del paquete son RELATIVOS (inmunes a la ruta).
  3. backend/rgenerator/__init__.py levanta ImportError si se carga por
     la ruta corta.
  4. Este test falla si alguien reintroduce la ruta corta en el código.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent

# `from rgenerator...` / `import rgenerator...` al inicio de línea
# (con indentación permitida: imports dentro de funciones también cuentan).
_PATRON_RUTA_CORTA = re.compile(r"^\s*(from|import)\s+rgenerator\b", re.MULTILINE)

_DIRS_AUDITADOS = ("backend", "tests", "scripts")
_EXCLUIR = ("__pycache__", ".venv", "node_modules")


def _archivos_python():
    for base in _DIRS_AUDITADOS:
        for path in (ROOT / base).rglob("*.py"):
            if any(part in _EXCLUIR for part in path.parts):
                continue
            yield path


@pytest.mark.unit
def test_ningun_archivo_usa_la_ruta_corta():
    """Ningún .py del repo debe importar `rgenerator.*` a secas."""
    infractores = []
    propio = Path(__file__).resolve()
    for path in _archivos_python():
        if path.resolve() == propio:
            continue
        try:
            contenido = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            contenido = path.read_text(encoding="latin-1")
        for m in _PATRON_RUTA_CORTA.finditer(contenido):
            linea = contenido.count("\n", 0, m.start()) + 1
            infractores.append(f"{path.relative_to(ROOT)}:{linea}")
    assert not infractores, (
        "Imports con la ruta corta `rgenerator.*` detectados (usar "
        "`backend.rgenerator.*` o imports relativos dentro del paquete):\n  "
        + "\n  ".join(infractores)
    )


@pytest.mark.unit
def test_ruta_corta_levanta_import_error():
    """El guard del __init__ bloquea la carga por la ruta corta en runtime."""
    import importlib
    import sys

    # Simular el escenario que creaba la instancia duplicada: backend/ en
    # sys.path (como hacía el conftest viejo y como pasa al correr
    # `python backend/api.py`).
    backend_dir = str(ROOT / "backend")
    sys.path.insert(0, backend_dir)
    try:
        sys.modules.pop("rgenerator", None)
        with pytest.raises(ImportError, match="backend.rgenerator"):
            importlib.import_module("rgenerator")
    finally:
        sys.path.remove(backend_dir)
        sys.modules.pop("rgenerator", None)


@pytest.mark.unit
def test_ruta_canonica_importa_y_es_unica():
    import sys

    import backend.rgenerator.core.step as paso_canonico

    assert paso_canonico.__name__ == "backend.rgenerator.core.step"
    # La instancia corta no debe existir en sys.modules tras importar la canónica
    assert "rgenerator.core.step" not in sys.modules
